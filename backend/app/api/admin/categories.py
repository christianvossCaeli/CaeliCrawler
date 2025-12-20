"""Admin API endpoints for category management.

This module provides CRUD operations for Categories (Analysethemen).
Categories define crawling and analysis configurations for document collection.

API Endpoints:
    GET    /categories              - List all categories with pagination
    POST   /categories              - Create a new category
    GET    /categories/{id}         - Get a single category
    PUT    /categories/{id}         - Update a category
    DELETE /categories/{id}         - Delete a category
    GET    /categories/{id}/stats   - Get category statistics
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import Category, DataSource, Document
from app.models.data_source_category import DataSourceCategory
from app.models.user import User
from app.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryListResponse,
    CategoryStats,
    generate_slug,
)
from app.schemas.common import MessageResponse, ErrorResponse
from app.core.exceptions import NotFoundError, ConflictError, CategoryNotFoundError, CategoryDuplicateError
from app.core.deps import get_current_user_optional

router = APIRouter(prefix="", tags=["Categories"])


@router.get(
    "",
    response_model=CategoryListResponse,
    summary="List Categories",
    description="Retrieve a paginated list of categories with optional filtering.",
    responses={
        200: {
            "description": "List of categories with pagination metadata",
            "model": CategoryListResponse,
        },
    },
)
async def list_categories(
    page: int = Query(
        default=1,
        ge=1,
        description="Page number (1-based)",
        examples=[1, 2, 3],
    ),
    per_page: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page (max 100)",
        examples=[10, 20, 50],
    ),
    is_active: Optional[bool] = Query(
        default=None,
        description="Filter by active status. True = only active, False = only inactive, None = all",
    ),
    is_public: Optional[bool] = Query(
        default=None,
        description="Filter by visibility. True = only public, False = only private, None = based on include_private",
    ),
    include_private: bool = Query(
        default=True,
        description="Include user's own private categories (requires authentication)",
    ),
    search: Optional[str] = Query(
        default=None,
        description="Search in category name and description (case-insensitive)",
        examples=["windkraft", "analyse"],
    ),
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    List all categories with pagination and visibility filtering.

    **Visibility Rules:**
    - Public categories (`is_public=True`) are visible to everyone
    - Private categories are only visible to their owner/creator
    - Anonymous users only see public categories

    **Pagination:**
    - Results are sorted alphabetically by name
    - Default: 20 items per page, max 100

    **Filtering:**
    - `is_active`: Filter by crawling status
    - `is_public`: Explicit visibility filter
    - `search`: Full-text search in name/description
    """
    query = select(Category)

    # Visibility filtering
    if is_public is not None:
        # Explicit filter requested
        query = query.where(Category.is_public.is_(is_public))
    elif include_private and current_user:
        # Show public + user's own private categories
        query = query.where(
            or_(
                Category.is_public.is_(True),
                Category.owner_id == current_user.id,
                Category.created_by_id == current_user.id,
            )
        )
    else:
        # Only public categories
        query = query.where(Category.is_public.is_(True))

    if is_active is not None:
        query = query.where(Category.is_active.is_(is_active))

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

    # Batch fetch counts to avoid N+1 queries
    category_ids = [cat.id for cat in categories]

    # Get source counts in a single query
    source_counts_result = await session.execute(
        select(
            DataSourceCategory.category_id,
            func.count(DataSourceCategory.id).label("count")
        )
        .where(DataSourceCategory.category_id.in_(category_ids))
        .group_by(DataSourceCategory.category_id)
    )
    source_counts = {row[0]: row[1] for row in source_counts_result.fetchall()}

    # Get document counts in a single query
    doc_counts_result = await session.execute(
        select(
            Document.category_id,
            func.count(Document.id).label("count")
        )
        .where(Document.category_id.in_(category_ids))
        .group_by(Document.category_id)
    )
    doc_counts = {row[0]: row[1] for row in doc_counts_result.fetchall()}

    # Build response items
    items = []
    for cat in categories:
        item = CategoryResponse.model_validate(cat)
        item.source_count = source_counts.get(cat.id, 0)
        item.document_count = doc_counts.get(cat.id, 0)
        items.append(item)

    return CategoryListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=201,
    summary="Create Category",
    description="Create a new category for document crawling and analysis.",
    responses={
        201: {
            "description": "Category created successfully",
            "model": CategoryResponse,
        },
        409: {
            "description": "Category with same name or slug already exists",
            "model": ErrorResponse,
        },
        422: {
            "description": "Validation error (invalid regex, cron expression, etc.)",
            "model": ErrorResponse,
        },
    },
)
async def create_category(
    data: CategoryCreate,
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Create a new category for document crawling and analysis.

    **Default Behavior:**
    - New categories are **private** by default (`is_public=False`)
    - The creating user becomes the **owner**
    - A URL-friendly **slug** is auto-generated from the name if not provided
    - Default schedule: daily at 2 AM (`0 2 * * *`)
    - Default language: German (`de`)

    **Validation:**
    - `url_include_patterns` and `url_exclude_patterns` must be valid regex
    - `schedule_cron` must be a valid 5-field cron expression
    - `languages` must be 2-letter ISO 639-1 codes
    - `extraction_handler` must be 'default' or 'event'

    **Example Request:**
    ```json
    {
        "name": "Windkraft NRW",
        "purpose": "Analysiere Windkraft-Dokumente",
        "languages": ["de"],
        "search_terms": ["windkraft", "windenergie"],
        "extraction_handler": "default"
    }
    ```
    """
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
        url_include_patterns=data.url_include_patterns,
        url_exclude_patterns=data.url_exclude_patterns,
        languages=data.languages,
        ai_extraction_prompt=data.ai_extraction_prompt,
        extraction_handler=data.extraction_handler,
        schedule_cron=data.schedule_cron,
        is_active=data.is_active,
        is_public=data.is_public,
        target_entity_type_id=data.target_entity_type_id,
        created_by_id=current_user.id if current_user else None,
        owner_id=current_user.id if current_user else None,
    )
    session.add(category)
    await session.commit()
    await session.refresh(category)

    return CategoryResponse.model_validate(category)


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Get Category",
    description="Retrieve a single category by its ID.",
    responses={
        200: {
            "description": "Category found",
            "model": CategoryResponse,
        },
        404: {
            "description": "Category not found",
            "model": ErrorResponse,
        },
    },
)
async def get_category(
    category_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """
    Get a single category by ID.

    Returns the full category data including:
    - Configuration (name, purpose, search terms, etc.)
    - URL filtering patterns
    - Language and extraction settings
    - Computed counts (sources, documents)

    **Note:** Private categories are only returned if the user is the owner.
    """
    category = await session.get(Category, category_id)
    if not category:
        raise NotFoundError("Category", str(category_id))

    # Get counts via junction table (N:M relationship)
    source_count = (await session.execute(
        select(func.count()).where(DataSourceCategory.category_id == category.id)
    )).scalar()

    doc_count = (await session.execute(
        select(func.count()).where(Document.category_id == category.id)
    )).scalar()

    response = CategoryResponse.model_validate(category)
    response.source_count = source_count
    response.document_count = doc_count

    return response


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Update Category",
    description="Update an existing category. All fields are optional.",
    responses={
        200: {
            "description": "Category updated successfully",
            "model": CategoryResponse,
        },
        404: {
            "description": "Category not found",
            "model": ErrorResponse,
        },
        409: {
            "description": "Category with same name already exists",
            "model": ErrorResponse,
        },
        422: {
            "description": "Validation error",
            "model": ErrorResponse,
        },
    },
)
async def update_category(
    category_id: UUID,
    data: CategoryUpdate,
    session: AsyncSession = Depends(get_session),
):
    """
    Update an existing category.

    **Partial Updates:**
    - Only provided fields are updated
    - Omitted fields retain their current values
    - Use `null` to explicitly clear optional fields

    **Validation:**
    - Same validation rules as create apply
    - Name uniqueness is checked if name is changed

    **Example Request:**
    ```json
    {
        "is_active": false,
        "schedule_cron": "0 3 * * *"
    }
    ```
    """
    category = await session.get(Category, category_id)
    if not category:
        raise NotFoundError("Category", str(category_id))

    # Check for duplicate name if being changed
    if data.name and data.name != category.name:
        existing = await session.execute(
            select(Category).where(
                Category.name == data.name,
                Category.id != category_id,
            )
        )
        if existing.scalar():
            raise ConflictError(
                "Category name already exists",
                detail=f"A category with name '{data.name}' already exists",
            )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    await session.commit()
    await session.refresh(category)

    return CategoryResponse.model_validate(category)


@router.delete(
    "/{category_id}",
    response_model=MessageResponse,
    summary="Delete Category",
    description="Delete a category and all its related data.",
    responses={
        200: {
            "description": "Category deleted successfully",
            "model": MessageResponse,
        },
        404: {
            "description": "Category not found",
            "model": ErrorResponse,
        },
    },
)
async def delete_category(
    category_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """
    Delete a category and all related data.

    **Cascade Behavior:**
    - All documents in this category are deleted
    - All extracted data is deleted
    - Data source links (N:M) are removed
    - Crawl jobs history is retained for auditing

    **Warning:** This action cannot be undone.
    """
    category = await session.get(Category, category_id)
    if not category:
        raise NotFoundError("Category", str(category_id))

    await session.delete(category)
    await session.commit()

    return MessageResponse(message=f"Category '{category.name}' deleted successfully")


@router.get(
    "/{category_id}/stats",
    response_model=CategoryStats,
    summary="Get Category Statistics",
    description="Get detailed statistics for a specific category.",
    responses={
        200: {
            "description": "Category statistics",
            "model": CategoryStats,
        },
        404: {
            "description": "Category not found",
            "model": ErrorResponse,
        },
    },
)
async def get_category_stats(
    category_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """
    Get detailed statistics for a category.

    **Returned Metrics:**
    - `source_count`: Number of linked data sources
    - `document_count`: Total crawled documents
    - `extracted_count`: Documents with AI extractions
    - `last_crawl`: Timestamp of last successful crawl
    - `active_jobs`: Currently running crawl jobs

    **Use Cases:**
    - Dashboard overview
    - Monitoring crawl progress
    - Identifying inactive categories
    """
    from app.models import CrawlJob, ExtractedData, JobStatus

    category = await session.get(Category, category_id)
    if not category:
        raise NotFoundError("Category", str(category_id))

    # Count sources via junction table (N:M relationship)
    source_count = (await session.execute(
        select(func.count()).where(DataSourceCategory.category_id == category_id)
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
