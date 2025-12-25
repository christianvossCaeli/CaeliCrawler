"""AnalysisTemplate CRUD endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import AnalysisTemplate, Category, EntityType, FacetType
from app.core.validators import validate_facet_config_slugs
from app.models.user import User
from app.schemas.analysis_template import (
    AnalysisTemplateCreate,
    AnalysisTemplateUpdate,
    AnalysisTemplateResponse,
    AnalysisTemplateListResponse,
    generate_slug,
)
from app.schemas.common import MessageResponse
from app.core.exceptions import NotFoundError, ConflictError
from app.core.deps import require_editor, require_admin

router = APIRouter()


@router.get("/templates", response_model=AnalysisTemplateListResponse)
async def list_analysis_templates(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    category_id: Optional[UUID] = Query(default=None),
    entity_type_id: Optional[UUID] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """List all analysis templates with pagination."""
    query = select(AnalysisTemplate)

    if category_id:
        query = query.where(AnalysisTemplate.category_id == category_id)
    if entity_type_id:
        query = query.where(AnalysisTemplate.primary_entity_type_id == entity_type_id)
    if is_active is not None:
        query = query.where(AnalysisTemplate.is_active == is_active)
    if search:
        query = query.where(
            AnalysisTemplate.name.ilike(f"%{search}%") |
            AnalysisTemplate.slug.ilike(f"%{search}%")
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(AnalysisTemplate.display_order, AnalysisTemplate.name).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    templates = result.scalars().all()

    # Enrich with related info
    items = []
    for t in templates:
        category = await session.get(Category, t.category_id) if t.category_id else None
        entity_type = await session.get(EntityType, t.primary_entity_type_id)

        item = AnalysisTemplateResponse.model_validate(t)
        item.category_name = category.name if category else None
        item.primary_entity_type_name = entity_type.name if entity_type else None
        item.primary_entity_type_slug = entity_type.slug if entity_type else None
        items.append(item)

    return AnalysisTemplateListResponse(items=items, total=total)


@router.post("/templates", response_model=AnalysisTemplateResponse, status_code=201)
async def create_analysis_template(
    data: AnalysisTemplateCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Create a new analysis template."""
    # Verify entity type exists
    entity_type = await session.get(EntityType, data.primary_entity_type_id)
    if not entity_type:
        raise NotFoundError("EntityType", str(data.primary_entity_type_id))

    # Validate facet_config slugs
    if data.facet_config:
        facet_configs = [fc.model_dump() if hasattr(fc, 'model_dump') else fc for fc in data.facet_config]
        _, invalid_slugs = await validate_facet_config_slugs(session, facet_configs)
        if invalid_slugs:
            raise ConflictError(
                "Invalid facet type slugs in facet_config",
                detail=f"The following facet type slugs do not exist: {', '.join(sorted(invalid_slugs))}",
            )

    # Generate slug if not provided
    slug = data.slug or generate_slug(data.name)

    # Check for exact duplicate
    existing = await session.execute(
        select(AnalysisTemplate).where(
            (AnalysisTemplate.name == data.name) | (AnalysisTemplate.slug == slug)
        )
    )
    if existing.scalar():
        raise ConflictError(
            "Analysis Template already exists",
            detail=f"A template with name '{data.name}' or slug '{slug}' already exists",
        )

    # Check for duplicate by configuration (same entity type + category + facet config)
    from app.utils.similarity import find_duplicate_analysis_template
    facet_configs = [fc.model_dump() if hasattr(fc, 'model_dump') else fc for fc in data.facet_config]
    duplicate = await find_duplicate_analysis_template(
        session,
        name=data.name,
        primary_entity_type_id=data.primary_entity_type_id,
        category_id=data.category_id,
        facet_config=facet_configs,
    )
    if duplicate:
        existing_template, reason = duplicate
        raise ConflictError(
            "Ähnliches AnalysisTemplate existiert bereits",
            detail=f"{reason}. Verwenden Sie das bestehende Template statt ein neues zu erstellen.",
        )

    template = AnalysisTemplate(
        name=data.name,
        slug=slug,
        description=data.description,
        category_id=data.category_id,
        primary_entity_type_id=data.primary_entity_type_id,
        facet_config=[fc.model_dump() for fc in data.facet_config],
        aggregation_config=data.aggregation_config.model_dump() if data.aggregation_config else {},
        display_config=data.display_config.model_dump() if data.display_config else {},
        extraction_prompt_template=data.extraction_prompt_template,
        is_default=data.is_default,
        is_active=data.is_active,
        display_order=data.display_order,
        is_system=False,
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)

    item = AnalysisTemplateResponse.model_validate(template)
    item.primary_entity_type_name = entity_type.name
    item.primary_entity_type_slug = entity_type.slug

    return item


@router.get("/templates/{template_id}", response_model=AnalysisTemplateResponse)
async def get_analysis_template(
    template_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a single analysis template by ID."""
    template = await session.get(AnalysisTemplate, template_id)
    if not template:
        raise NotFoundError("AnalysisTemplate", str(template_id))

    category = await session.get(Category, template.category_id) if template.category_id else None
    entity_type = await session.get(EntityType, template.primary_entity_type_id)

    response = AnalysisTemplateResponse.model_validate(template)
    response.category_name = category.name if category else None
    response.primary_entity_type_name = entity_type.name if entity_type else None
    response.primary_entity_type_slug = entity_type.slug if entity_type else None

    return response


@router.get("/templates/by-slug/{slug}", response_model=AnalysisTemplateResponse)
async def get_analysis_template_by_slug(
    slug: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a single analysis template by slug."""
    result = await session.execute(
        select(AnalysisTemplate).where(AnalysisTemplate.slug == slug)
    )
    template = result.scalar()
    if not template:
        raise NotFoundError("AnalysisTemplate", slug)

    category = await session.get(Category, template.category_id) if template.category_id else None
    entity_type = await session.get(EntityType, template.primary_entity_type_id)

    response = AnalysisTemplateResponse.model_validate(template)
    response.category_name = category.name if category else None
    response.primary_entity_type_name = entity_type.name if entity_type else None
    response.primary_entity_type_slug = entity_type.slug if entity_type else None

    return response


@router.put("/templates/{template_id}", response_model=AnalysisTemplateResponse)
async def update_analysis_template(
    template_id: UUID,
    data: AnalysisTemplateUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Update an analysis template."""
    template = await session.get(AnalysisTemplate, template_id)
    if not template:
        raise NotFoundError("AnalysisTemplate", str(template_id))

    # Validate facet_config slugs if being updated
    if data.facet_config:
        facet_configs = [fc.model_dump() if hasattr(fc, 'model_dump') else fc for fc in data.facet_config]
        _, invalid_slugs = await validate_facet_config_slugs(session, facet_configs)
        if invalid_slugs:
            raise ConflictError(
                "Invalid facet type slugs in facet_config",
                detail=f"The following facet type slugs do not exist: {', '.join(sorted(invalid_slugs))}",
            )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)

    # Handle nested configs
    if "facet_config" in update_data and update_data["facet_config"]:
        update_data["facet_config"] = [fc.model_dump() if hasattr(fc, 'model_dump') else fc for fc in update_data["facet_config"]]
    if "aggregation_config" in update_data and update_data["aggregation_config"]:
        update_data["aggregation_config"] = update_data["aggregation_config"].model_dump() if hasattr(update_data["aggregation_config"], 'model_dump') else update_data["aggregation_config"]
    if "display_config" in update_data and update_data["display_config"]:
        update_data["display_config"] = update_data["display_config"].model_dump() if hasattr(update_data["display_config"], 'model_dump') else update_data["display_config"]

    for field, value in update_data.items():
        setattr(template, field, value)

    await session.commit()
    await session.refresh(template)

    return AnalysisTemplateResponse.model_validate(template)


@router.delete("/templates/{template_id}", response_model=MessageResponse)
async def delete_analysis_template(
    template_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """Delete an analysis template."""
    template = await session.get(AnalysisTemplate, template_id)
    if not template:
        raise NotFoundError("AnalysisTemplate", str(template_id))

    if template.is_system:
        raise ConflictError(
            "Cannot delete system template",
            detail=f"Template '{template.name}' is a system template and cannot be deleted",
        )

    await session.delete(template)
    await session.commit()

    return MessageResponse(message=f"Analysis template '{template.name}' deleted successfully")
