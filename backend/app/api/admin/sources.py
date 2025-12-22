"""Admin API endpoints for data source management."""

import ipaddress
import socket
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.core.deps import require_editor, require_admin
from app.core.audit import AuditContext
from app.models.audit_log import AuditAction
from app.models import DataSource, Document, Category, SourceStatus, SourceType, DataSourceCategory, User
from app.schemas.data_source import (
    CategoryLink,
    DataSourceCreate,
    DataSourceUpdate,
    DataSourceResponse,
    DataSourceListResponse,
    DataSourceBulkImport,
    DataSourceBulkImportResult,
    SourceCountsResponse,
    CategoryCount,
    TypeCount,
    StatusCount,
    TagsResponse,
    TagCount,
)
from app.schemas.common import MessageResponse
from app.core.exceptions import NotFoundError, ConflictError


# =============================================================================
# SSRF Protection for Crawler URLs
# =============================================================================

# IP ranges that should NOT be crawled (internal networks, cloud metadata, etc.)
BLOCKED_CRAWLER_IP_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),      # Localhost
    ipaddress.ip_network("10.0.0.0/8"),       # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),    # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),   # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),   # Link-local (cloud metadata)
    ipaddress.ip_network("0.0.0.0/8"),        # Current network
]

# Hostnames that should never be crawled
BLOCKED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "metadata.google.internal",
    "metadata.google.com",
}


def validate_crawler_url(url: str, allow_http: bool = True) -> Tuple[bool, str]:
    """
    Validate a URL for safe crawling (SSRF protection).

    Args:
        url: The URL to validate
        allow_http: Whether to allow HTTP (not just HTTPS)

    Returns:
        Tuple of (is_safe, error_message)
    """
    try:
        parsed = urlparse(url)

        # Check scheme
        allowed_schemes = ["https"]
        if allow_http:
            allowed_schemes.append("http")

        if parsed.scheme not in allowed_schemes:
            return False, f"URL scheme must be one of: {', '.join(allowed_schemes)}"

        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid URL: no hostname"

        # Check blocked hostnames
        if hostname.lower() in BLOCKED_HOSTNAMES:
            return False, f"Hostname '{hostname}' is not allowed"

        # Check for internal hostnames
        if hostname.endswith(".local") or hostname.endswith(".internal"):
            return False, "Internal hostnames are not allowed"

        # Try to resolve and check IP
        try:
            ip = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip)

            for blocked_range in BLOCKED_CRAWLER_IP_RANGES:
                if ip_obj in blocked_range:
                    return False, f"URL resolves to blocked IP range (internal network)"
        except socket.gaierror:
            # Can't resolve - allow for now, will fail at crawl time
            pass

        return True, ""

    except Exception as e:
        return False, f"Invalid URL: {str(e)}"


async def get_categories_for_source(
    session: AsyncSession,
    source_id: UUID,
) -> list[CategoryLink]:
    """Load all categories linked to a data source."""
    result = await session.execute(
        select(DataSourceCategory, Category)
        .join(Category, DataSourceCategory.category_id == Category.id)
        .where(DataSourceCategory.data_source_id == source_id)
        .order_by(DataSourceCategory.is_primary.desc(), Category.name)
    )
    links = []
    for dsc, cat in result.all():
        links.append(CategoryLink(
            id=cat.id,
            name=cat.name,
            slug=cat.slug,
            is_primary=dsc.is_primary,
        ))
    return links


async def get_categories_for_sources_bulk(
    session: AsyncSession,
    source_ids: List[UUID],
) -> Dict[UUID, List[CategoryLink]]:
    """
    Bulk-load all categories for multiple data sources.

    Returns a dict mapping source_id -> list of CategoryLink.
    This avoids N+1 queries when listing multiple sources.
    """
    if not source_ids:
        return {}

    result = await session.execute(
        select(DataSourceCategory, Category)
        .join(Category, DataSourceCategory.category_id == Category.id)
        .where(DataSourceCategory.data_source_id.in_(source_ids))
        .order_by(DataSourceCategory.is_primary.desc(), Category.name)
    )

    categories_by_source: Dict[UUID, List[CategoryLink]] = defaultdict(list)
    for dsc, cat in result.all():
        categories_by_source[dsc.data_source_id].append(CategoryLink(
            id=cat.id,
            name=cat.name,
            slug=cat.slug,
            is_primary=dsc.is_primary,
        ))

    return categories_by_source


async def sync_source_categories(
    session: AsyncSession,
    source: DataSource,
    category_ids: list[UUID],
    primary_category_id: UUID | None = None,
) -> None:
    """Sync categories for a data source (replace existing)."""
    # Delete existing links
    await session.execute(
        select(DataSourceCategory).where(
            DataSourceCategory.data_source_id == source.id
        )
    )
    existing = (await session.execute(
        select(DataSourceCategory).where(DataSourceCategory.data_source_id == source.id)
    )).scalars().all()
    for link in existing:
        await session.delete(link)

    # Create new links (N:M via junction table only)
    for i, cat_id in enumerate(category_ids):
        is_primary = cat_id == primary_category_id if primary_category_id else (i == 0)
        link = DataSourceCategory(
            data_source_id=source.id,
            category_id=cat_id,
            is_primary=is_primary,
        )
        session.add(link)

    await session.flush()


def build_source_response(
    source: DataSource,
    categories: list[CategoryLink],
    document_count: int = 0,
    job_count: int = 0,
) -> DataSourceResponse:
    """Build a DataSourceResponse from a DataSource model."""
    category_name = None
    primary_category_id = None
    if categories:
        primary = next((c for c in categories if c.is_primary), categories[0])
        category_name = primary.name
        primary_category_id = primary.id

    return DataSourceResponse(
        id=source.id,
        name=source.name,
        source_type=source.source_type,
        base_url=source.base_url,
        api_endpoint=source.api_endpoint,
        category_id=primary_category_id,  # From junction table, not legacy field
        crawl_config=source.crawl_config,
        extra_data=source.extra_data,
        priority=source.priority,
        tags=source.tags or [],
        status=source.status,
        last_crawl=source.last_crawl,
        last_change_detected=source.last_change_detected,
        error_message=source.error_message,
        created_at=source.created_at,
        updated_at=source.updated_at,
        document_count=document_count,
        job_count=job_count,
        category_name=category_name,
        categories=categories,
    )


router = APIRouter()


@router.get("", response_model=DataSourceListResponse)
async def list_sources(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=10000),
    category_id: Optional[UUID] = Query(default=None, description="Filter by category (N:M)"),
    status: Optional[SourceStatus] = Query(default=None),
    source_type: Optional[SourceType] = Query(default=None),
    search: Optional[str] = Query(default=None),
    tags: Optional[List[str]] = Query(default=None, description="Filter by tags (OR logic)"),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """List all data sources with pagination and filters."""
    from sqlalchemy import or_

    query = select(DataSource)

    # Filter by category via N:M junction table
    if category_id:
        source_ids_in_cat = (
            select(DataSourceCategory.data_source_id)
            .where(DataSourceCategory.category_id == category_id)
        )
        query = query.where(DataSource.id.in_(source_ids_in_cat))

    if status:
        query = query.where(DataSource.status == status)
    if source_type:
        query = query.where(DataSource.source_type == source_type)
    if search:
        query = query.where(
            DataSource.name.ilike(f"%{search}%") |
            DataSource.base_url.ilike(f"%{search}%")
        )
    # Filter by tags (OR logic - source must have at least one of the tags)
    if tags:
        tag_conditions = [DataSource.tags.contains([tag]) for tag in tags]
        query = query.where(or_(*tag_conditions))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(DataSource.name).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    sources = result.scalars().all()

    # Bulk-load document counts and categories to avoid N+1 queries
    source_ids = [s.id for s in sources]

    # Single query for all document counts
    doc_counts_result = await session.execute(
        select(Document.source_id, func.count(Document.id))
        .where(Document.source_id.in_(source_ids))
        .group_by(Document.source_id)
    )
    doc_counts = dict(doc_counts_result.all())

    # Bulk-load all categories
    categories_by_source = await get_categories_for_sources_bulk(session, source_ids)

    # Build responses
    items = []
    for source in sources:
        doc_count = doc_counts.get(source.id, 0)
        categories = categories_by_source.get(source.id, [])

        # Build response using helper to avoid lazy-loading issues
        item = build_source_response(source, categories, document_count=doc_count)
        items.append(item)

    return DataSourceListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.post("", response_model=DataSourceResponse, status_code=201)
async def create_source(
    data: DataSourceCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Create a new data source.

    **Security**: URL is validated against SSRF attacks (internal networks blocked).
    """
    # SSRF Protection: Validate URL before creating source
    is_safe, error_msg = validate_crawler_url(data.base_url)
    if not is_safe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid URL: {error_msg}",
        )

    # Also validate API endpoint if provided
    if data.api_endpoint:
        is_safe, error_msg = validate_crawler_url(data.api_endpoint)
        if not is_safe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid API endpoint URL: {error_msg}",
            )

    # Determine category IDs - support both legacy single and new multi-category
    category_ids = data.category_ids or []
    if data.category_id and data.category_id not in category_ids:
        category_ids.insert(0, data.category_id)

    if not category_ids:
        raise NotFoundError("Category", "No category specified")

    # Verify all categories exist
    for cat_id in category_ids:
        category = await session.get(Category, cat_id)
        if not category:
            raise NotFoundError("Category", str(cat_id))

    # Primary category is the first one
    primary_category_id = category_ids[0]

    # Check for duplicate URL (globally now, not per-category)
    existing = await session.execute(
        select(DataSource).where(DataSource.base_url == data.base_url)
    )
    if existing.scalar():
        raise ConflictError(
            "Data source already exists",
            detail=f"A source with URL '{data.base_url}' already exists",
        )

    async with AuditContext(session, current_user, request) as audit:
        source = DataSource(
            category_id=primary_category_id,  # Legacy field
            name=data.name,
            source_type=data.source_type,
            base_url=data.base_url,
            api_endpoint=data.api_endpoint,
            crawl_config=data.crawl_config.model_dump() if data.crawl_config else {},
            auth_config=data.auth_config,
            extra_data=data.extra_data,
            priority=data.priority,
            tags=data.tags,
        )
        session.add(source)
        await session.flush()  # Get ID

        # Create N:M category links
        await sync_source_categories(session, source, category_ids, primary_category_id)

        # Audit log
        audit.track_action(
            action=AuditAction.CREATE,
            entity_type="DataSource",
            entity_id=source.id,
            entity_name=source.name,
            changes={
                "name": source.name,
                "base_url": source.base_url,
                "source_type": source.source_type.value if source.source_type else None,
                "tags": source.tags or [],
                "category_ids": [str(c) for c in category_ids],
                "priority": source.priority,
            },
        )

        await session.commit()
        await session.refresh(source)

    # Load categories for response
    categories = await get_categories_for_source(session, source.id)

    return build_source_response(source, categories)


class SourceBriefResponse(BaseModel):
    """Brief response for source listing (used in tag-based search)."""
    id: UUID
    name: str
    base_url: str
    source_type: SourceType
    tags: List[str]
    category_ids: List[UUID]

    model_config = {"from_attributes": True}


@router.get("/by-tags", response_model=List[SourceBriefResponse])
async def get_sources_by_tags(
    tags: List[str] = Query(..., min_length=1, description="Tags to filter by"),
    match_mode: str = Query(default="all", regex="^(all|any)$", description="Match mode: 'all' (AND) or 'any' (OR)"),
    exclude_category_id: Optional[UUID] = Query(default=None, description="Exclude sources already in this category"),
    limit: int = Query(default=1000, ge=1, le=5000),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """
    Find DataSources by tags with AND/OR logic.

    **match_mode:**
    - `all`: Source must have ALL specified tags (AND logic)
    - `any`: Source must have at least ONE of the specified tags (OR logic)

    **exclude_category_id:**
    If provided, excludes sources that are already linked to this category.

    This endpoint is useful for:
    - Finding sources to assign to a category
    - Tag-based filtering and management
    """
    from sqlalchemy import and_, or_

    query = select(DataSource)

    if match_mode == "all":
        # AND logic: source must have ALL tags
        for tag in tags:
            query = query.where(DataSource.tags.contains([tag]))
    else:
        # OR logic: source must have at least one tag
        tag_conditions = [DataSource.tags.contains([tag]) for tag in tags]
        query = query.where(or_(*tag_conditions))

    # Exclude sources already in the specified category
    if exclude_category_id:
        sources_in_category = (
            select(DataSourceCategory.data_source_id)
            .where(DataSourceCategory.category_id == exclude_category_id)
        )
        query = query.where(~DataSource.id.in_(sources_in_category))

    query = query.order_by(DataSource.name).limit(limit)
    result = await session.execute(query)
    sources = result.scalars().all()

    # Bulk load category IDs for response
    source_ids = [s.id for s in sources]
    category_mapping = await get_categories_for_sources_bulk(session, source_ids)

    return [
        SourceBriefResponse(
            id=s.id,
            name=s.name,
            base_url=s.base_url,
            source_type=s.source_type,
            tags=s.tags or [],
            category_ids=[cat.id for cat in category_mapping.get(s.id, [])],
        )
        for s in sources
    ]


@router.get("/{source_id}", response_model=DataSourceResponse)
async def get_source(
    source_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Get a single data source by ID."""
    source = await session.get(DataSource, source_id)
    if not source:
        raise NotFoundError("Data Source", str(source_id))

    doc_count = (await session.execute(
        select(func.count()).where(Document.source_id == source.id)
    )).scalar()

    # Load categories via N:M
    categories = await get_categories_for_source(session, source.id)

    return build_source_response(source, categories, document_count=doc_count)


@router.put("/{source_id}", response_model=DataSourceResponse)
async def update_source(
    source_id: UUID,
    data: DataSourceUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Update a data source.

    **Security**: URL changes are validated against SSRF attacks.
    """
    source = await session.get(DataSource, source_id)
    if not source:
        raise NotFoundError("Data Source", str(source_id))

    # Capture old state for audit
    old_data = {
        "name": source.name,
        "base_url": source.base_url,
        "source_type": source.source_type.value if source.source_type else None,
        "status": source.status.value if source.status else None,
        "tags": source.tags or [],
        "priority": source.priority,
    }

    update_data = data.model_dump(exclude_unset=True)

    # SSRF Protection: Validate URLs if being updated
    if "base_url" in update_data:
        is_safe, error_msg = validate_crawler_url(update_data["base_url"])
        if not is_safe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid URL: {error_msg}",
            )

    if "api_endpoint" in update_data and update_data["api_endpoint"]:
        is_safe, error_msg = validate_crawler_url(update_data["api_endpoint"])
        if not is_safe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid API endpoint URL: {error_msg}",
            )

    async with AuditContext(session, current_user, request) as audit:
        # Handle N:M category updates
        category_ids = update_data.pop("category_ids", None)
        primary_category_id = update_data.pop("primary_category_id", None)

        if category_ids is not None:
            # Verify all categories exist
            for cat_id in category_ids:
                category = await session.get(Category, cat_id)
                if not category:
                    raise NotFoundError("Category", str(cat_id))

            await sync_source_categories(session, source, category_ids, primary_category_id)

        # Handle crawl_config specially
        if "crawl_config" in update_data and update_data["crawl_config"]:
            update_data["crawl_config"] = update_data["crawl_config"].model_dump()

        for field, value in update_data.items():
            setattr(source, field, value)

        # Capture new state
        new_data = {
            "name": source.name,
            "base_url": source.base_url,
            "source_type": source.source_type.value if source.source_type else None,
            "status": source.status.value if source.status else None,
            "tags": source.tags or [],
            "priority": source.priority,
        }

        # Track update with diff
        audit.track_update(source, old_data, new_data)

        await session.commit()
        await session.refresh(source)

    # Load categories for response
    categories = await get_categories_for_source(session, source.id)

    return build_source_response(source, categories)


@router.delete("/{source_id}", response_model=MessageResponse)
async def delete_source(
    source_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Delete a data source and all related data."""
    source = await session.get(DataSource, source_id)
    if not source:
        raise NotFoundError("Data Source", str(source_id))

    # Get document count for audit
    doc_count = (await session.execute(
        select(func.count()).where(Document.source_id == source.id)
    )).scalar()

    # Load categories for audit
    categories = await get_categories_for_source(session, source.id)

    name = source.name
    base_url = source.base_url

    async with AuditContext(session, current_user, request) as audit:
        audit.track_action(
            action=AuditAction.DELETE,
            entity_type="DataSource",
            entity_id=source.id,
            entity_name=name,
            changes={
                "deleted": True,
                "name": name,
                "base_url": base_url,
                "source_type": source.source_type.value if source.source_type else None,
                "tags": source.tags or [],
                "document_count": doc_count,
                "categories": [c.name for c in categories],
            },
        )

        await session.delete(source)
        await session.commit()

    return MessageResponse(message=f"Data source '{name}' deleted successfully")


@router.post("/bulk-import", response_model=DataSourceBulkImportResult)
async def bulk_import_sources(
    data: DataSourceBulkImport,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """
    Bulk import data sources from a list with N:M category support and tags.

    **Security**: All URLs are validated against SSRF attacks (internal networks blocked).

    Features:
    - Multiple categories per source (N:M relation)
    - Default tags applied to all sources
    - Per-source tags merged with default tags
    - CSV format support: Name;URL;SourceType;Tags
    """
    # Verify all categories exist
    categories = []
    for cat_id in data.category_ids:
        category = await session.get(Category, cat_id)
        if not category:
            raise NotFoundError("Category", str(cat_id))
        categories.append(category)

    imported = 0
    skipped = 0
    errors = []
    imported_names = []

    for item in data.sources:
        try:
            # SSRF Protection: Validate URL before importing
            is_safe, error_msg = validate_crawler_url(item.base_url)
            if not is_safe:
                errors.append({
                    "url": item.base_url,
                    "error": f"SSRF Protection: {error_msg}",
                })
                continue

            # Check for duplicate by URL across all sources (not per-category)
            if data.skip_duplicates:
                existing = await session.execute(
                    select(DataSource).where(
                        DataSource.base_url == item.base_url,
                    )
                )
                if existing.scalar():
                    skipped += 1
                    continue

            # Combine default_tags with item-specific tags (no duplicates)
            combined_tags = list(set(data.default_tags + item.tags))

            source = DataSource(
                name=item.name,
                source_type=item.source_type,
                base_url=item.base_url,
                tags=combined_tags,
                extra_data=item.extra_data,
            )
            session.add(source)
            await session.flush()  # Get the source ID

            # Create N:M category associations
            for idx, category in enumerate(categories):
                assoc = DataSourceCategory(
                    data_source_id=source.id,
                    category_id=category.id,
                    is_primary=(idx == 0),  # First category is primary
                )
                session.add(assoc)

            imported += 1
            if len(imported_names) < 10:
                imported_names.append(source.name)

        except Exception as e:
            errors.append({
                "url": item.base_url,
                "error": str(e),
            })

    # Audit log for bulk operation
    if imported > 0:
        async with AuditContext(session, current_user, request) as audit:
            audit.track_action(
                action=AuditAction.IMPORT,
                entity_type="DataSource",
                entity_name="Bulk Import",
                changes={
                    "operation": "bulk_import",
                    "imported": imported,
                    "skipped": skipped,
                    "errors": len(errors),
                    "categories": [c.name for c in categories],
                    "default_tags": data.default_tags,
                    "sample_sources": imported_names,
                },
            )

            await session.commit()
    else:
        await session.commit()

    return DataSourceBulkImportResult(
        imported=imported,
        skipped=skipped,
        errors=errors,
    )


@router.post("/{source_id}/reset", response_model=MessageResponse)
async def reset_source(
    source_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Reset a source status (clear errors, set to pending)."""
    source = await session.get(DataSource, source_id)
    if not source:
        raise NotFoundError("Data Source", str(source_id))

    source.status = SourceStatus.PENDING
    source.error_message = None
    await session.commit()

    return MessageResponse(message=f"Source '{source.name}' reset to pending")


@router.get("/meta/counts", response_model=SourceCountsResponse)
async def get_source_counts(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """
    Get aggregated counts for sidebar navigation.

    Returns counts grouped by:
    - categories (with category details)
    - source types
    - status
    """
    # Total count
    total_result = await session.execute(
        select(func.count(DataSource.id))
    )
    total = total_result.scalar() or 0

    # Counts by category (via N:M junction table)
    category_counts_query = (
        select(
            Category.id,
            Category.name,
            Category.slug,
            func.count(DataSourceCategory.data_source_id).label("count")
        )
        .join(DataSourceCategory, Category.id == DataSourceCategory.category_id)
        .group_by(Category.id, Category.name, Category.slug)
        .order_by(func.count(DataSourceCategory.data_source_id).desc())
    )
    category_result = await session.execute(category_counts_query)
    categories = [
        CategoryCount(
            id=str(row.id),
            name=row.name,
            slug=row.slug,
            count=row.count,
        )
        for row in category_result.all()
    ]

    # Counts by source type
    type_counts_query = (
        select(DataSource.source_type, func.count(DataSource.id).label("count"))
        .group_by(DataSource.source_type)
        .order_by(func.count(DataSource.id).desc())
    )
    type_result = await session.execute(type_counts_query)
    types = [
        TypeCount(type=row.source_type.value if row.source_type else None, count=row.count)
        for row in type_result.all()
    ]

    # Counts by status
    status_counts_query = (
        select(DataSource.status, func.count(DataSource.id).label("count"))
        .group_by(DataSource.status)
        .order_by(func.count(DataSource.id).desc())
    )
    status_result = await session.execute(status_counts_query)
    statuses = [
        StatusCount(status=row.status.value if row.status else None, count=row.count)
        for row in status_result.all()
    ]

    return SourceCountsResponse(
        total=total,
        categories=categories,
        types=types,
        statuses=statuses,
    )


@router.get("/meta/tags", response_model=TagsResponse)
async def get_available_tags(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """
    Get all unique tags currently used across DataSources.

    Returns a list of tags with their usage counts, sorted by frequency.
    This allows the UI to offer autocomplete suggestions based on existing tags.
    """
    # PostgreSQL: unnest the JSONB tags array and count occurrences
    # This is more efficient than loading all sources and counting in Python
    result = await session.execute(
        select(
            func.jsonb_array_elements_text(DataSource.tags).label("tag"),
            func.count().label("count"),
        )
        .where(DataSource.tags != [])  # Skip sources with no tags
        .group_by(func.jsonb_array_elements_text(DataSource.tags))
        .order_by(func.count().desc())
    )

    tags = [
        TagCount(tag=row.tag, count=row.count)
        for row in result.all()
    ]

    return TagsResponse(tags=tags)
