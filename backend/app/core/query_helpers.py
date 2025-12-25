"""Query helper utilities to avoid N+1 queries and reduce code duplication."""

from dataclasses import dataclass
from typing import Any, Dict, Generic, List, Optional, Set, Tuple, Type, TypeVar, Union
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import Select

T = TypeVar("T", bound=DeclarativeBase)
R = TypeVar("R")  # Response type


@dataclass
class PaginationParams:
    """Standard pagination parameters."""
    page: int = 1
    per_page: int = 50

    @property
    def offset(self) -> int:
        """Calculate offset for SQL query."""
        return (self.page - 1) * self.per_page

    def total_pages(self, total: int) -> int:
        """Calculate total pages from total items."""
        if self.per_page <= 0:
            return 0
        return (total + self.per_page - 1) // self.per_page


@dataclass
class PaginatedResult(Generic[T]):
    """Generic paginated result container."""
    items: List[T]
    total: int
    page: int
    per_page: int
    pages: int

    @classmethod
    def empty(cls, pagination: PaginationParams) -> "PaginatedResult":
        """Create an empty paginated result."""
        return cls(
            items=[],
            total=0,
            page=pagination.page,
            per_page=pagination.per_page,
            pages=0,
        )


async def paginate_query(
    session: AsyncSession,
    query: Select,
    pagination: PaginationParams,
) -> Tuple[List[Any], int]:
    """
    Execute a query with pagination and return items + total count.

    This is a reusable helper to avoid duplicating pagination logic
    across all API endpoints.

    Args:
        session: Database session
        query: SQLAlchemy Select query (before pagination applied)
        pagination: Pagination parameters

    Returns:
        Tuple of (items list, total count)

    Example:
        query = select(Entity).where(Entity.is_active == True)
        items, total = await paginate_query(session, query, PaginationParams(page=1, per_page=50))
    """
    # Count total items (before pagination)
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    # Apply pagination
    paginated_query = query.offset(pagination.offset).limit(pagination.per_page)
    result = await session.execute(paginated_query)
    items = list(result.scalars().all())

    return items, total


async def paginate_query_with_result(
    session: AsyncSession,
    query: Select,
    pagination: PaginationParams,
) -> PaginatedResult:
    """
    Execute a query with pagination and return a PaginatedResult.

    Convenience wrapper around paginate_query that returns a
    structured result object.

    Args:
        session: Database session
        query: SQLAlchemy Select query
        pagination: Pagination parameters

    Returns:
        PaginatedResult with items, total, page info
    """
    items, total = await paginate_query(session, query, pagination)

    return PaginatedResult(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=pagination.total_pages(total),
    )


async def batch_fetch_by_ids(
    session: AsyncSession,
    model: Type[T],
    ids: Union[Set[UUID], List[UUID]],
    *,
    id_field: str = "id",
) -> Dict[UUID, T]:
    """
    Batch fetch entities by their IDs to avoid N+1 queries.

    This is a common pattern used when you have a list of related IDs
    and need to efficiently fetch all related entities in a single query.

    Args:
        session: Database session
        model: SQLAlchemy model class to query
        ids: Set or list of UUIDs to fetch
        id_field: Name of the ID field (default: "id")

    Returns:
        Dictionary mapping ID -> entity for found entities

    Example:
        # Instead of:
        for job in jobs:
            source = await session.get(DataSource, job.source_id)  # N+1!

        # Use:
        source_ids = {job.source_id for job in jobs}
        sources_dict = await batch_fetch_by_ids(session, DataSource, source_ids)
        for job in jobs:
            source = sources_dict.get(job.source_id)
    """
    if not ids:
        return {}

    # Convert to set to remove duplicates
    id_set = set(ids)

    # Get the ID column dynamically
    id_column = getattr(model, id_field)

    result = await session.execute(
        select(model).where(id_column.in_(id_set))
    )
    entities = result.scalars().all()

    return {getattr(entity, id_field): entity for entity in entities}


async def batch_fetch_sources_and_categories(
    session: AsyncSession,
    jobs: List[Any],
) -> tuple[Dict[UUID, Any], Dict[UUID, Any]]:
    """
    Batch fetch DataSources and Categories for a list of CrawlJobs.

    This is a specialized helper for the common pattern in crawler.py
    where we need to enrich job responses with source and category names.

    Args:
        session: Database session
        jobs: List of CrawlJob instances

    Returns:
        Tuple of (sources_dict, categories_dict)
    """
    from app.models import DataSource, Category

    # Collect unique IDs
    source_ids: Set[UUID] = set()
    category_ids: Set[UUID] = set()

    for job in jobs:
        if job.source_id:
            source_ids.add(job.source_id)
        if job.category_id:
            category_ids.add(job.category_id)

    # Batch fetch in parallel
    sources_dict = await batch_fetch_by_ids(session, DataSource, source_ids)
    categories_dict = await batch_fetch_by_ids(session, Category, category_ids)

    return sources_dict, categories_dict


def enrich_job_with_names(
    job: Any,
    sources_dict: Dict[UUID, Any],
    categories_dict: Dict[UUID, Any],
) -> Dict[str, Any]:
    """
    Enrich a CrawlJob with source and category names.

    Args:
        job: CrawlJob instance
        sources_dict: Dictionary of source_id -> DataSource
        categories_dict: Dictionary of category_id -> Category

    Returns:
        Dictionary with job data and additional name fields
    """
    source = sources_dict.get(job.source_id) if job.source_id else None
    category = categories_dict.get(job.category_id) if job.category_id else None

    # Calculate duration if applicable
    duration = None
    if job.started_at and job.completed_at:
        duration = (job.completed_at - job.started_at).total_seconds()

    return {
        **{k: v for k, v in job.__dict__.items() if not k.startswith("_")},
        "source_name": source.name if source else None,
        "category_name": category.name if category else None,
        "duration_seconds": duration,
    }
