"""Admin API endpoints for category management."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import Category, DataSource, Document
from app.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryListResponse,
    CategoryStats,
    generate_slug,
)
from app.schemas.common import MessageResponse
from app.core.exceptions import NotFoundError, ConflictError

router = APIRouter()


@router.get("", response_model=CategoryListResponse)
async def list_categories(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    is_active: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """List all categories with pagination."""
    query = select(Category)

    if is_active is not None:
        query = query.where(Category.is_active == is_active)

    if search:
        query = query.where(
            Category.name.ilike(f"%{search}%") |
            Category.description.ilike(f"%{search}%")
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(Category.name).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    categories = result.scalars().all()

    # Get counts for each category
    items = []
    for cat in categories:
        # Count sources
        source_count = (await session.execute(
            select(func.count()).where(DataSource.category_id == cat.id)
        )).scalar()

        # Count documents
        doc_count = (await session.execute(
            select(func.count()).where(Document.category_id == cat.id)
        )).scalar()

        item = CategoryResponse.model_validate(cat)
        item.source_count = source_count
        item.document_count = doc_count
        items.append(item)

    return CategoryListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(
    data: CategoryCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new category."""
    # Generate slug if not provided
    slug = data.slug or generate_slug(data.name)

    # Check for duplicate name or slug
    existing = await session.execute(
        select(Category).where(
            (Category.name == data.name) | (Category.slug == slug)
        )
    )
    if existing.scalar():
        raise ConflictError(
            "Category already exists",
            detail=f"A category with name '{data.name}' or slug '{slug}' already exists",
        )

    category = Category(
        name=data.name,
        slug=slug,
        description=data.description,
        purpose=data.purpose,
        search_terms=data.search_terms,
        document_types=data.document_types,
        ai_extraction_prompt=data.ai_extraction_prompt,
        schedule_cron=data.schedule_cron,
        is_active=data.is_active,
    )
    session.add(category)
    await session.commit()
    await session.refresh(category)

    return CategoryResponse.model_validate(category)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a single category by ID."""
    category = await session.get(Category, category_id)
    if not category:
        raise NotFoundError("Category", str(category_id))

    # Get counts
    source_count = (await session.execute(
        select(func.count()).where(DataSource.category_id == category.id)
    )).scalar()

    doc_count = (await session.execute(
        select(func.count()).where(Document.category_id == category.id)
    )).scalar()

    response = CategoryResponse.model_validate(category)
    response.source_count = source_count
    response.document_count = doc_count

    return response


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    data: CategoryUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update a category."""
    category = await session.get(Category, category_id)
    if not category:
        raise NotFoundError("Category", str(category_id))

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    await session.commit()
    await session.refresh(category)

    return CategoryResponse.model_validate(category)


@router.delete("/{category_id}", response_model=MessageResponse)
async def delete_category(
    category_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Delete a category and all related data."""
    category = await session.get(Category, category_id)
    if not category:
        raise NotFoundError("Category", str(category_id))

    await session.delete(category)
    await session.commit()

    return MessageResponse(message=f"Category '{category.name}' deleted successfully")


@router.get("/{category_id}/stats", response_model=CategoryStats)
async def get_category_stats(
    category_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get statistics for a category."""
    from app.models import CrawlJob, ExtractedData, JobStatus

    category = await session.get(Category, category_id)
    if not category:
        raise NotFoundError("Category", str(category_id))

    source_count = (await session.execute(
        select(func.count()).where(DataSource.category_id == category_id)
    )).scalar()

    doc_count = (await session.execute(
        select(func.count()).where(Document.category_id == category_id)
    )).scalar()

    extracted_count = (await session.execute(
        select(func.count()).where(ExtractedData.category_id == category_id)
    )).scalar()

    # Get last crawl
    last_job = (await session.execute(
        select(CrawlJob)
        .where(CrawlJob.category_id == category_id)
        .where(CrawlJob.status == JobStatus.COMPLETED)
        .order_by(CrawlJob.completed_at.desc())
        .limit(1)
    )).scalar()

    # Count active jobs
    active_jobs = (await session.execute(
        select(func.count())
        .where(CrawlJob.category_id == category_id)
        .where(CrawlJob.status == JobStatus.RUNNING)
    )).scalar()

    return CategoryStats(
        id=category.id,
        name=category.name,
        source_count=source_count,
        document_count=doc_count,
        extracted_count=extracted_count,
        last_crawl=last_job.completed_at if last_job else None,
        active_jobs=active_jobs,
    )
