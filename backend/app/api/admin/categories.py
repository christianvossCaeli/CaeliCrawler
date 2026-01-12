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

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import AuditContext
from app.core.deps import get_current_user_optional, require_admin, require_editor
from app.core.exceptions import ConflictError, NotFoundError
from app.database import get_session
from app.models import Category, DataSource, Document
from app.models.audit_log import AuditAction
from app.models.data_source_category import DataSourceCategory
from app.models.user import User
from app.schemas.category import (
    CategoryAiSetupPreview,
    CategoryAiSetupRequest,
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategoryStats,
    CategoryUpdate,
    EntityTypeSuggestion,
    FacetTypeSuggestion,
    generate_slug,
)
from app.schemas.common import ErrorResponse, MessageResponse

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
    scheduled_only: bool = Query(
        default=False,
        description="Filter to only show categories with active schedule",
    ),
    is_public: bool | None = Query(
        default=None,
        description="Filter by visibility. True = only public, False = only private, None = based on include_private",
    ),
    include_private: bool = Query(
        default=True,
        description="Include user's own private categories (requires authentication)",
    ),
    search: str | None = Query(
        default=None,
        description="Search in category name and description (case-insensitive)",
        examples=["windkraft", "analyse"],
    ),
    has_documents: bool | None = Query(
        default=None,
        description="Filter by presence of documents (true = with documents, false = without documents)",
    ),
    language: str | None = Query(
        default=None,
        description="Filter by language code (ISO 639-1) in category languages",
        examples=["de", "en"],
    ),
    sort_by: str | None = Query(
        default="name",
        description="Sort by field (name, purpose, schedule_enabled, source_count, document_count)",
        examples=["name", "document_count"],
    ),
    sort_order: str | None = Query(
        default="asc",
        description="Sort order (asc, desc)",
        examples=["asc", "desc"],
    ),
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
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
    - `scheduled_only`: Filter to categories with active schedule
    - `is_public`: Explicit visibility filter
    - `search`: Full-text search in name/description
    """
    # Eagerly load created_by and owner to avoid lazy loading in Pydantic validation
    query = select(Category).options(
        selectinload(Category.created_by),
        selectinload(Category.owner),
    )

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

    if scheduled_only:
        query = query.where(Category.schedule_enabled.is_(True))

    if search:
        # Escape SQL wildcards to prevent injection
        safe_search = search.replace("%", "\\%").replace("_", "\\_")
        query = query.where(
            Category.name.ilike(f"%{safe_search}%", escape="\\")
            | Category.description.ilike(f"%{safe_search}%", escape="\\")
            | Category.purpose.ilike(f"%{safe_search}%", escape="\\")
        )

    if has_documents is not None:
        doc_exists = select(Document.id).where(Document.category_id == Category.id).exists()
        query = query.where(doc_exists) if has_documents else query.where(~doc_exists)

    if language:
        query = query.where(Category.languages.contains([language.lower()]))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Handle sorting
    sort_desc = sort_order == "desc"
    sort_column_map = {
        "name": Category.name,
        "purpose": Category.purpose,
        "schedule_enabled": Category.schedule_enabled,
    }

    if sort_by in sort_column_map:
        order_col = sort_column_map[sort_by]
        if sort_desc:
            query = query.order_by(order_col.desc().nulls_last())
        else:
            query = query.order_by(order_col.asc().nulls_last())
    else:
        # Default sorting by name
        query = query.order_by(Category.name.asc())

    # Paginate
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    categories = result.scalars().all()

    # Batch fetch counts to avoid N+1 queries
    category_ids = [cat.id for cat in categories]

    source_counts: dict = {}
    doc_counts: dict = {}

    # Only run batch queries if there are categories
    if category_ids:
        # Get source counts in a single query
        source_counts_result = await session.execute(
            select(DataSourceCategory.category_id, func.count(DataSourceCategory.id).label("count"))
            .where(DataSourceCategory.category_id.in_(category_ids))
            .group_by(DataSourceCategory.category_id)
        )
        source_counts = {row[0]: row[1] for row in source_counts_result.fetchall()}

        # Get document counts in a single query
        doc_counts_result = await session.execute(
            select(Document.category_id, func.count(Document.id).label("count"))
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
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
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
    - `schedule_cron` must be a valid 5- or 6-field cron expression (seconds optional)
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
    existing = await session.execute(select(Category).where((Category.name == data.name) | (Category.slug == slug)))
    if existing.scalar():
        raise ConflictError(
            "Category already exists",
            detail=f"A category with name '{data.name}' or slug '{slug}' already exists",
        )

    async with AuditContext(session, current_user, request) as audit:
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
            schedule_enabled=data.schedule_enabled,
            is_public=data.is_public,
            target_entity_type_id=data.target_entity_type_id,
            created_by_id=current_user.id if current_user else None,
            owner_id=current_user.id if current_user else None,
        )
        session.add(category)
        await session.flush()  # Get ID before audit

        # Generate embedding for semantic similarity search
        from app.utils.similarity import generate_embedding

        embedding = await generate_embedding(category.name)
        if embedding:
            category.name_embedding = embedding

        # Audit log with detailed info
        audit.track_action(
            action=AuditAction.CREATE,
            entity_type="Category",
            entity_id=category.id,
            entity_name=category.name,
            changes={
                "name": category.name,
                "slug": category.slug,
                "purpose": category.purpose,
                "is_public": category.is_public,
                "schedule_enabled": category.schedule_enabled,
                "languages": category.languages,
                "search_terms": category.search_terms[:5] if category.search_terms else [],
                "extraction_handler": category.extraction_handler,
            },
        )

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
    _: User = Depends(require_editor),
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
    source_count = (
        await session.execute(select(func.count()).where(DataSourceCategory.category_id == category.id))
    ).scalar()

    doc_count = (await session.execute(select(func.count()).where(Document.category_id == category.id))).scalar()

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
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
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
        "schedule_enabled": false,
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

    # Capture old state for audit
    old_data = {
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "purpose": category.purpose,
        "schedule_enabled": category.schedule_enabled,
        "is_public": category.is_public,
        "languages": category.languages,
        "search_terms": category.search_terms,
        "schedule_cron": category.schedule_cron,
        "extraction_handler": category.extraction_handler,
    }

    async with AuditContext(session, current_user, request) as audit:
        # Update fields
        update_data = data.model_dump(exclude_unset=True)

        # If name changes, regenerate embedding
        if "name" in update_data:
            from app.utils.similarity import generate_embedding

            embedding = await generate_embedding(update_data["name"])
            if embedding:
                update_data["name_embedding"] = embedding

        for field, value in update_data.items():
            setattr(category, field, value)

        # Capture new state
        new_data = {
            "name": category.name,
            "slug": category.slug,
            "description": category.description,
            "purpose": category.purpose,
            "schedule_enabled": category.schedule_enabled,
            "is_public": category.is_public,
            "languages": category.languages,
            "search_terms": category.search_terms,
            "schedule_cron": category.schedule_cron,
            "extraction_handler": category.extraction_handler,
        }

        # Track update with diff
        audit.track_update(category, old_data, new_data)

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
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
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

    # Get counts for audit before deletion
    source_count = (
        await session.execute(select(func.count()).where(DataSourceCategory.category_id == category.id))
    ).scalar()
    doc_count = (await session.execute(select(func.count()).where(Document.category_id == category.id))).scalar()

    category_name = category.name

    async with AuditContext(session, current_user, request) as audit:
        audit.track_action(
            action=AuditAction.DELETE,
            entity_type="Category",
            entity_id=category.id,
            entity_name=category_name,
            changes={
                "deleted": True,
                "name": category_name,
                "slug": category.slug,
                "purpose": category.purpose,
                "source_count": source_count,
                "document_count": doc_count,
            },
        )

        await session.delete(category)
        await session.commit()

    return MessageResponse(message=f"Category '{category_name}' deleted successfully")


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
    _: User = Depends(require_editor),
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
    source_count = (
        await session.execute(select(func.count()).where(DataSourceCategory.category_id == category_id))
    ).scalar()

    doc_count = (await session.execute(select(func.count()).where(Document.category_id == category_id))).scalar()

    extracted_count = (
        await session.execute(select(func.count()).where(ExtractedData.category_id == category_id))
    ).scalar()

    # Get last crawl
    last_job = (
        await session.execute(
            select(CrawlJob)
            .where(CrawlJob.category_id == category_id)
            .where(CrawlJob.status == JobStatus.COMPLETED)
            .order_by(CrawlJob.completed_at.desc())
            .limit(1)
        )
    ).scalar()

    # Count active jobs
    active_jobs = (
        await session.execute(
            select(func.count()).where(CrawlJob.category_id == category_id).where(CrawlJob.status == JobStatus.RUNNING)
        )
    ).scalar()

    return CategoryStats(
        id=category.id,
        name=category.name,
        source_count=source_count,
        document_count=doc_count,
        extracted_count=extracted_count,
        last_crawl=last_job.completed_at if last_job else None,
        active_jobs=active_jobs,
    )


@router.post(
    "/preview-ai-setup",
    response_model=CategoryAiSetupPreview,
    summary="Preview AI Setup",
    description="Generate AI-powered suggestions for EntityType, FacetTypes, and extraction prompt.",
    responses={
        200: {
            "description": "AI setup preview with suggestions",
            "model": CategoryAiSetupPreview,
        },
        503: {
            "description": "AI service not available",
            "model": ErrorResponse,
        },
    },
)
async def preview_ai_setup(
    data: CategoryAiSetupRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Generate AI-powered suggestions for category setup.

    **This endpoint does NOT save anything to the database.**

    Based on the category name and purpose, the AI generates:
    - **EntityType**: Suggested entity type with schema
    - **FacetTypes**: Suggested facet types for data extraction
    - **Extraction Prompt**: AI prompt for document analysis
    - **Search Terms**: Keywords for crawling
    - **URL Patterns**: Include/exclude patterns for filtering

    The user can then review, modify, and confirm these suggestions
    before saving the category.

    **Example Request:**
    ```json
    {
        "name": "Windkraft-Restriktionen",
        "purpose": "Identifiziere Hindernisse für Windkraftprojekte in kommunalen Dokumenten"
    }
    ```
    """
    import structlog

    from app.models import EntityType, FacetType
    from services.smart_query.ai_generation import (
        ai_generate_category_config,
        ai_generate_crawl_config,
        ai_generate_entity_type_config,
    )
    from services.smart_query.utils import generate_slug as sq_generate_slug

    logger = structlog.get_logger()

    try:
        # Combine name and purpose for AI context
        user_intent = f"{data.name}: {data.purpose}"
        if data.description:
            user_intent += f" ({data.description})"

        # Step 1: Generate EntityType configuration
        et_config = await ai_generate_entity_type_config(
            user_intent=user_intent,
            geographic_context="Deutschland",
        )

        # Create EntityType suggestion
        et_name = et_config.get("name", data.name)
        et_slug = sq_generate_slug(et_name)

        # Check if similar EntityType already exists
        existing_et = await session.execute(
            select(EntityType).where(or_(EntityType.name == et_name, EntityType.slug == et_slug))
        )
        et_exists = existing_et.scalar()

        suggested_entity_type = EntityTypeSuggestion(
            id=et_exists.id if et_exists else None,
            name=et_name,
            slug=et_slug,
            name_plural=et_config.get("name_plural", et_name),
            description=et_config.get("description", data.purpose),
            icon=et_config.get("icon", "mdi-folder"),
            color=et_config.get("color", "#2196F3"),
            attribute_schema=et_config.get("attribute_schema", {}),
            is_new=not et_exists,
        )

        # Step 2: Generate Category configuration (with extraction prompt)
        cat_config = await ai_generate_category_config(
            user_intent=user_intent,
            entity_type_name=et_name,
            entity_type_description=suggested_entity_type.description,
        )

        # Step 3: Generate Crawl configuration
        search_terms = cat_config.get("search_terms", [])
        crawl_config = await ai_generate_crawl_config(
            user_intent=user_intent,
            search_focus=et_config.get("search_focus", "general"),
            search_terms=search_terms,
        )

        # Get existing EntityTypes for alternative selection
        existing_entity_types_result = await session.execute(
            select(EntityType).where(EntityType.is_active.is_(True)).order_by(EntityType.name).limit(20)
        )
        existing_entity_types = [
            EntityTypeSuggestion(
                id=et.id,
                name=et.name,
                slug=et.slug,
                name_plural=et.name_plural or et.name,
                description=et.description or "",
                icon=et.icon or "mdi-folder",
                color=et.color or "#2196F3",
                attribute_schema=et.attribute_schema or {},
                is_new=False,
            )
            for et in existing_entity_types_result.scalars().all()
        ]

        # Get existing FacetTypes that might be reusable
        existing_facet_types_result = await session.execute(
            select(FacetType).where(FacetType.is_active.is_(True)).order_by(FacetType.name).limit(30)
        )
        existing_facet_types = [
            FacetTypeSuggestion(
                id=ft.id,
                name=ft.name,
                slug=ft.slug,
                name_plural=ft.name_plural or ft.name,
                description=ft.description or "",
                value_type=ft.value_type or "text",
                value_schema=ft.value_schema or {},
                icon=ft.icon or "mdi-tag",
                color=ft.color or "#4CAF50",
                is_new=False,
                selected=False,  # Not selected by default for existing
            )
            for ft in existing_facet_types_result.scalars().all()
        ]

        # Generate suggested FacetTypes based on category purpose
        # These are common facet types that are useful for most analyses
        suggested_facet_types = [
            FacetTypeSuggestion(
                id=None,
                name="Pain Point",
                slug="pain_point",
                name_plural="Pain Points",
                description="Probleme, Bedenken und Hindernisse",
                value_type="object",
                value_schema={
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "type": {"type": "string"},
                        "severity": {"type": "string", "enum": ["niedrig", "mittel", "hoch"]},
                    },
                },
                icon="mdi-alert-circle",
                color="#F44336",
                is_new=True,
                selected=True,
            ),
            FacetTypeSuggestion(
                id=None,
                name="Positive Signal",
                slug="positive_signal",
                name_plural="Positive Signale",
                description="Positive Entwicklungen und Chancen",
                value_type="object",
                value_schema={
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "type": {"type": "string"},
                    },
                },
                icon="mdi-thumb-up",
                color="#4CAF50",
                is_new=True,
                selected=True,
            ),
            FacetTypeSuggestion(
                id=None,
                name="Kontakt",
                slug="contact",
                name_plural="Kontakte",
                description="Ansprechpartner und Entscheidungsträger",
                value_type="object",
                value_schema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "role": {"type": "string"},
                        "email": {"type": "string"},
                        "phone": {"type": "string"},
                    },
                },
                icon="mdi-account",
                color="#2196F3",
                is_new=True,
                selected=True,
            ),
        ]

        # Check which suggested FacetTypes already exist and mark them
        for i, ft in enumerate(suggested_facet_types):
            existing_ft = await session.execute(select(FacetType).where(FacetType.slug == ft.slug))
            existing = existing_ft.scalar()
            if existing:
                suggested_facet_types[i] = FacetTypeSuggestion(
                    id=existing.id,
                    name=existing.name,
                    slug=existing.slug,
                    name_plural=existing.name_plural or existing.name,
                    description=existing.description or ft.description,
                    value_type=existing.value_type or ft.value_type,
                    value_schema=existing.value_schema or ft.value_schema,
                    icon=existing.icon or ft.icon,
                    color=existing.color or ft.color,
                    is_new=False,
                    selected=True,  # Still selected since it's useful
                )

        return CategoryAiSetupPreview(
            suggested_entity_type=suggested_entity_type,
            existing_entity_types=existing_entity_types,
            suggested_facet_types=suggested_facet_types,
            existing_facet_types=existing_facet_types,
            suggested_extraction_prompt=cat_config.get("ai_extraction_prompt", ""),
            suggested_search_terms=search_terms,
            suggested_url_include_patterns=crawl_config.get("url_include_patterns", []),
            suggested_url_exclude_patterns=crawl_config.get("url_exclude_patterns", []),
            reasoning=crawl_config.get("reasoning", ""),
        )

    except ValueError as e:
        # Azure OpenAI not configured
        raise HTTPException(
            status_code=503,
            detail=f"AI-Service nicht verfügbar: {str(e)}",
        ) from None
    except RuntimeError as e:
        # AI generation failed
        raise HTTPException(
            status_code=503,
            detail=str(e),
        ) from None
    except Exception as e:
        logger.error("AI setup preview failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Fehler bei der KI-Generierung: {str(e)}",
        ) from None


class AssignSourcesByTagsRequest(BaseModel):
    """Request to assign sources by tags."""

    tags: list[str] = Field(..., min_length=1, description="Tags to filter sources by")
    match_mode: str = Field(default="all", pattern="^(all|any)$", description="Match mode: 'all' (AND) or 'any' (OR)")
    mode: str = Field(
        default="add",
        pattern="^(add|replace)$",
        description="Assignment mode: 'add' (keep existing) or 'replace' (remove existing)",
    )


class AssignSourcesByTagsResponse(BaseModel):
    """Response for source assignment operation."""

    assigned: int
    already_assigned: int
    removed: int = 0
    total_in_category: int


@router.post(
    "/{category_id}/assign-sources-by-tags",
    response_model=AssignSourcesByTagsResponse,
    summary="Assign Sources by Tags",
    description="Bulk-assign data sources to this category based on tags.",
    responses={
        200: {
            "description": "Sources assigned successfully",
            "model": AssignSourcesByTagsResponse,
        },
        404: {
            "description": "Category not found",
            "model": ErrorResponse,
        },
    },
)
async def assign_sources_by_tags(
    category_id: UUID,
    assign_request: AssignSourcesByTagsRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Bulk-assign DataSources to a category based on tags.

    **Match Modes:**
    - `all`: Source must have ALL specified tags (AND logic)
    - `any`: Source must have at least ONE of the specified tags (OR logic)

    **Assignment Modes:**
    - `add`: Add new sources, keep existing assignments
    - `replace`: Remove all existing assignments, add new sources

    **Example Request:**
    ```json
    {
        "tags": ["nrw", "kommunal"],
        "match_mode": "all",
        "mode": "add"
    }
    ```

    This will assign all sources that have BOTH "nrw" AND "kommunal" tags
    to the specified category.
    """

    # Verify category exists
    category = await session.get(Category, category_id)
    if not category:
        raise NotFoundError("Category", str(category_id))

    # Build query for sources matching tags
    query = select(DataSource)

    if assign_request.match_mode == "all":
        # AND logic: source must have ALL tags
        for tag in assign_request.tags:
            query = query.where(DataSource.tags.contains([tag]))
    else:
        # OR logic: source must have at least one tag
        tag_conditions = [DataSource.tags.contains([tag]) for tag in assign_request.tags]
        query = query.where(or_(*tag_conditions))

    result = await session.execute(query)
    matching_sources = result.scalars().all()

    # Get existing assignments
    existing_result = await session.execute(
        select(DataSourceCategory.data_source_id).where(DataSourceCategory.category_id == category_id)
    )
    existing_source_ids = {row[0] for row in existing_result.fetchall()}

    # Batch fetch existing category counts for all matching sources (avoid N+1)
    matching_source_ids = [s.id for s in matching_sources]
    source_category_counts: dict = {}
    if matching_source_ids:
        counts_result = await session.execute(
            select(DataSourceCategory.data_source_id, func.count(DataSourceCategory.id).label("count"))
            .where(DataSourceCategory.data_source_id.in_(matching_source_ids))
            .group_by(DataSourceCategory.data_source_id)
        )
        source_category_counts = {row[0]: row[1] for row in counts_result.fetchall()}

    assigned = 0
    already_assigned = 0
    removed = 0
    assigned_source_names = []

    async with AuditContext(session, current_user, http_request) as audit:
        # Handle replace mode - remove existing assignments first
        if assign_request.mode == "replace":
            delete_result = await session.execute(
                select(DataSourceCategory).where(DataSourceCategory.category_id == category_id)
            )
            existing_links = delete_result.scalars().all()
            for link in existing_links:
                await session.delete(link)
                removed += 1
            existing_source_ids = set()

        # Assign matching sources
        for source in matching_sources:
            if source.id in existing_source_ids:
                already_assigned += 1
                continue

            # Check if this is the first category for the source (using batch-fetched counts)
            existing_cats_count = source_category_counts.get(source.id, 0)

            link = DataSourceCategory(
                data_source_id=source.id,
                category_id=category_id,
                is_primary=(existing_cats_count == 0),  # Primary if first category
            )
            session.add(link)
            assigned += 1
            if len(assigned_source_names) < 10:
                assigned_source_names.append(source.name)

        # Audit log for bulk operation
        if assigned > 0 or removed > 0:
            audit.track_action(
                action=AuditAction.UPDATE,
                entity_type="Category",
                entity_id=category_id,
                entity_name=category.name,
                changes={
                    "operation": "assign_sources_by_tags",
                    "tags": assign_request.tags,
                    "match_mode": assign_request.match_mode,
                    "mode": assign_request.mode,
                    "assigned": assigned,
                    "removed": removed,
                    "already_assigned": already_assigned,
                    "sample_sources": assigned_source_names,
                },
            )

        await session.commit()

    # Get total count in category
    total_in_category = (
        await session.execute(select(func.count()).where(DataSourceCategory.category_id == category_id))
    ).scalar()

    return AssignSourcesByTagsResponse(
        assigned=assigned,
        already_assigned=already_assigned,
        removed=removed,
        total_in_category=total_in_category,
    )


# ============================================
# Assign Sources by IDs
# ============================================


class AssignSourcesByIdsRequest(BaseModel):
    """Request body for assigning sources by IDs."""

    source_ids: list[UUID] = Field(..., description="Source IDs to assign")


@router.post(
    "/{category_id}/assign-sources",
    response_model=AssignSourcesByTagsResponse,
    summary="Assign Sources by IDs",
    description="Assign data sources to this category by their IDs.",
    responses={
        200: {
            "description": "Sources assigned successfully",
            "model": AssignSourcesByTagsResponse,
        },
        404: {
            "description": "Category not found",
            "model": ErrorResponse,
        },
    },
)
async def assign_sources_by_ids(
    category_id: UUID,
    assign_request: AssignSourcesByIdsRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Assign DataSources to a category by their IDs.

    This endpoint allows direct assignment of specific sources to a category,
    useful for single-source assignment or manual selection.
    """
    # Verify category exists
    category = await session.get(Category, category_id)
    if not category:
        raise NotFoundError("Category", str(category_id))

    # Get existing assignments
    existing_result = await session.execute(
        select(DataSourceCategory.data_source_id).where(DataSourceCategory.category_id == category_id)
    )
    existing_source_ids = {row[0] for row in existing_result.fetchall()}

    # Batch fetch existing category counts for all sources
    source_category_counts: dict = {}
    if assign_request.source_ids:
        counts_result = await session.execute(
            select(DataSourceCategory.data_source_id, func.count(DataSourceCategory.id).label("count"))
            .where(DataSourceCategory.data_source_id.in_(assign_request.source_ids))
            .group_by(DataSourceCategory.data_source_id)
        )
        source_category_counts = {row[0]: row[1] for row in counts_result.fetchall()}

    assigned = 0
    already_assigned = 0
    assigned_source_names = []

    async with AuditContext(session, current_user, http_request) as audit:
        for source_id in assign_request.source_ids:
            if source_id in existing_source_ids:
                already_assigned += 1
                continue

            # Verify source exists
            source = await session.get(DataSource, source_id)
            if not source:
                continue

            # Check if this is the first category for the source
            existing_cats_count = source_category_counts.get(source_id, 0)

            link = DataSourceCategory(
                data_source_id=source_id,
                category_id=category_id,
                is_primary=(existing_cats_count == 0),
            )
            session.add(link)
            assigned += 1
            if len(assigned_source_names) < 10:
                assigned_source_names.append(source.name)

        if assigned > 0:
            audit.track_action(
                action=AuditAction.UPDATE,
                entity_type="Category",
                entity_id=category_id,
                entity_name=category.name,
                changes={
                    "operation": "assign_sources_by_ids",
                    "assigned": assigned,
                    "already_assigned": already_assigned,
                    "sample_sources": assigned_source_names,
                },
            )

        await session.commit()

    # Get total count in category
    total_in_category = (
        await session.execute(select(func.count()).where(DataSourceCategory.category_id == category_id))
    ).scalar()

    return AssignSourcesByTagsResponse(
        assigned=assigned,
        already_assigned=already_assigned,
        removed=0,
        total_in_category=total_in_category,
    )


# ============================================
# Category Sources (Get/List)
# ============================================


class CategorySourceItem(BaseModel):
    """A source assigned to a category."""

    id: UUID
    name: str
    base_url: str | None = None
    status: str | None = None
    source_type: str | None = None
    tags: list[str] = []
    document_count: int = 0


class CategorySourcesResponse(BaseModel):
    """Response for category sources list."""

    items: list[CategorySourceItem]
    total: int
    page: int
    per_page: int


@router.get(
    "/{category_id}/sources",
    response_model=CategorySourcesResponse,
    summary="List Category Sources",
    description="Get paginated list of sources assigned to this category.",
)
async def list_category_sources(
    category_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(25, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Search query for name or URL"),
    tags: list[str] | None = Query(None, description="Filter by tags"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Get sources assigned to a category with pagination and filters.

    Supports:
    - Pagination (page, per_page)
    - Search by name or URL
    - Filter by tags (AND logic)
    """
    # Verify category exists
    category = await session.get(Category, category_id)
    if not category:
        raise NotFoundError("Category", str(category_id))

    # Base query: sources assigned to this category
    query = (
        select(DataSource)
        .join(DataSourceCategory, DataSource.id == DataSourceCategory.data_source_id)
        .where(DataSourceCategory.category_id == category_id)
    )

    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                DataSource.name.ilike(search_term),
                DataSource.base_url.ilike(search_term),
            )
        )

    # Apply tags filter (AND logic)
    if tags:
        for tag in tags:
            query = query.where(DataSource.tags.contains([tag]))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(DataSource.name)

    result = await session.execute(query)
    sources = result.scalars().all()

    # Get document counts for sources
    source_ids = [s.id for s in sources]
    doc_counts: dict = {}
    if source_ids:
        counts_result = await session.execute(
            select(Document.data_source_id, func.count(Document.id).label("count"))
            .where(Document.data_source_id.in_(source_ids))
            .group_by(Document.data_source_id)
        )
        doc_counts = {row[0]: row[1] for row in counts_result.fetchall()}

    items = [
        CategorySourceItem(
            id=source.id,
            name=source.name,
            base_url=source.base_url,
            status=source.status.value if source.status else None,
            source_type=source.source_type.value if source.source_type else None,
            tags=source.tags or [],
            document_count=doc_counts.get(source.id, 0),
        )
        for source in sources
    ]

    return CategorySourcesResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


# ============================================
# Category Sources Tags
# ============================================


class CategorySourcesTagsResponse(BaseModel):
    """Response for available tags in category sources."""

    tags: list[str]


@router.get(
    "/{category_id}/sources/tags",
    response_model=CategorySourcesTagsResponse,
    summary="Get Tags in Category Sources",
    description="Get all unique tags from sources assigned to this category.",
)
async def get_category_sources_tags(
    category_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Get unique tags from sources assigned to a category."""
    # Verify category exists
    category = await session.get(Category, category_id)
    if not category:
        raise NotFoundError("Category", str(category_id))

    # Get all tags from assigned sources
    query = (
        select(DataSource.tags)
        .join(DataSourceCategory, DataSource.id == DataSourceCategory.data_source_id)
        .where(DataSourceCategory.category_id == category_id)
        .where(DataSource.tags.isnot(None))
    )

    result = await session.execute(query)
    all_tags_lists = result.scalars().all()

    # Flatten and deduplicate
    unique_tags = set()
    for tags_list in all_tags_lists:
        if tags_list:
            unique_tags.update(tags_list)

    return CategorySourcesTagsResponse(tags=sorted(unique_tags))


# ============================================
# Unassign Source
# ============================================


@router.delete(
    "/{category_id}/sources/{source_id}",
    response_model=MessageResponse,
    summary="Unassign Source from Category",
    description="Remove a source from this category.",
)
async def unassign_source(
    category_id: UUID,
    source_id: UUID,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Remove a source assignment from a category."""
    # Verify category exists
    category = await session.get(Category, category_id)
    if not category:
        raise NotFoundError("Category", str(category_id))

    # Find and delete the assignment
    result = await session.execute(
        select(DataSourceCategory).where(
            DataSourceCategory.category_id == category_id,
            DataSourceCategory.data_source_id == source_id,
        )
    )
    link = result.scalar_one_or_none()

    if not link:
        raise NotFoundError("Source assignment", f"{source_id} in category {category_id}")

    # Get source name for audit
    source = await session.get(DataSource, source_id)
    source_name = source.name if source else str(source_id)

    async with AuditContext(session, current_user, http_request) as audit:
        await session.delete(link)

        audit.track_action(
            action=AuditAction.UPDATE,
            entity_type="Category",
            entity_id=category_id,
            entity_name=category.name,
            changes={
                "operation": "unassign_source",
                "source_id": str(source_id),
                "source_name": source_name,
            },
        )

        await session.commit()

    return MessageResponse(message=f"Source '{source_name}' removed from category")


class UnassignSourcesBulkRequest(BaseModel):
    """Request body for bulk unassigning sources."""

    source_ids: list[UUID] = Field(..., description="Source IDs to unassign")


class UnassignSourcesBulkResponse(BaseModel):
    """Response for bulk unassign operation."""

    removed: int = Field(..., description="Number of sources successfully unassigned")
    not_found: int = Field(..., description="Number of sources not found in category")
    message: str = Field(..., description="Human-readable result message")


@router.post(
    "/{category_id}/unassign-sources",
    response_model=UnassignSourcesBulkResponse,
    summary="Bulk Unassign Sources from Category",
    description="Remove multiple sources from this category at once.",
)
async def unassign_sources_bulk(
    category_id: UUID,
    body: UnassignSourcesBulkRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Remove multiple source assignments from a category."""
    # Verify category exists
    category = await session.get(Category, category_id)
    if not category:
        raise NotFoundError("Category", str(category_id))

    if not body.source_ids:
        return UnassignSourcesBulkResponse(removed=0, not_found=0, message="No sources specified")

    # Find existing assignments
    result = await session.execute(
        select(DataSourceCategory).where(
            DataSourceCategory.category_id == category_id,
            DataSourceCategory.data_source_id.in_(body.source_ids),
        )
    )
    links = result.scalars().all()

    found_ids = {link.data_source_id for link in links}
    not_found_count = len(body.source_ids) - len(found_ids)

    if not links:
        return UnassignSourcesBulkResponse(
            removed=0,
            not_found=not_found_count,
            message="No matching source assignments found",
        )

    async with AuditContext(session, current_user, http_request) as audit:
        # Delete all found links
        for link in links:
            await session.delete(link)

        audit.track_action(
            action=AuditAction.UPDATE,
            entity_type="Category",
            entity_id=category_id,
            entity_name=category.name,
            changes={
                "operation": "bulk_unassign_sources",
                "source_ids": [str(sid) for sid in found_ids],
                "removed_count": len(links),
            },
        )

        await session.commit()

    return UnassignSourcesBulkResponse(
        removed=len(links),
        not_found=not_found_count,
        message=f"{len(links)} source(s) removed from category",
    )
