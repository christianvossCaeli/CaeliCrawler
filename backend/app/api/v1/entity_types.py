"""API endpoints for Entity Type management."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import EntityType, Entity, FacetType, RelationType, AnalysisTemplate
from app.models.user import User
from app.core.audit import AuditContext
from app.models.audit_log import AuditAction
from app.schemas.entity_type import (
    EntityTypeCreate,
    EntityTypeUpdate,
    EntityTypeResponse,
    EntityTypeListResponse,
    generate_slug,
)
from app.schemas.common import MessageResponse
from app.core.exceptions import NotFoundError, ConflictError
from app.core.deps import get_current_user_optional, require_editor, require_admin

router = APIRouter()


@router.get("", response_model=EntityTypeListResponse)
async def list_entity_types(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    is_active: Optional[bool] = Query(default=None),
    is_primary: Optional[bool] = Query(default=None),
    is_public: Optional[bool] = Query(default=None, description="Filter by public/private visibility"),
    include_private: bool = Query(default=True, description="Include user's private entity types"),
    search: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """List all entity types with pagination and visibility filtering.

    Visibility rules:
    - Public entity types (is_public=True) are visible to everyone
    - Private entity types are only visible to their owner/creator
    - System entity types are always public
    """
    query = select(EntityType)

    # Visibility filtering
    if is_public is not None:
        # Explicit filter requested
        query = query.where(EntityType.is_public.is_(is_public))
    elif include_private and current_user:
        # Show public + user's own private types
        query = query.where(
            or_(
                EntityType.is_public.is_(True),
                EntityType.owner_id == current_user.id,
                EntityType.created_by_id == current_user.id,
            )
        )
    else:
        # Only public entity types
        query = query.where(EntityType.is_public.is_(True))

    if is_active is not None:
        query = query.where(EntityType.is_active.is_(is_active))
    if is_primary is not None:
        query = query.where(EntityType.is_primary.is_(is_primary))
    if search:
        # Escape SQL wildcards to prevent injection
        safe_search = search.replace('%', '\\%').replace('_', '\\_')
        query = query.where(
            EntityType.name.ilike(f"%{safe_search}%", escape='\\') |
            EntityType.slug.ilike(f"%{safe_search}%", escape='\\')
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(EntityType.display_order, EntityType.name).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    entity_types = result.scalars().all()

    if not entity_types:
        return EntityTypeListResponse(
            items=[],
            total=total,
            page=page,
            per_page=per_page,
            pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
        )

    # Batch count entities (1 query instead of N)
    entity_type_ids = [et.id for et in entity_types]
    entity_counts_map: dict = {}
    if entity_type_ids:
        entity_counts_result = await session.execute(
            select(Entity.entity_type_id, func.count(Entity.id))
            .where(Entity.entity_type_id.in_(entity_type_ids))
            .group_by(Entity.entity_type_id)
        )
        entity_counts_map = dict(entity_counts_result.fetchall())

    # Build response items using pre-fetched data
    items = []
    for et in entity_types:
        item = EntityTypeResponse.model_validate(et)
        item.entity_count = entity_counts_map.get(et.id, 0)
        items.append(item)

    return EntityTypeListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.post("", response_model=EntityTypeResponse, status_code=201)
async def create_entity_type(
    data: EntityTypeCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Create a new entity type.

    New entity types are private by default (is_public=False).
    The creating user becomes the owner.
    """
    # Generate slug if not provided
    slug = data.slug or generate_slug(data.name)

    # Check for exact duplicate
    existing = await session.execute(
        select(EntityType).where(
            (EntityType.name == data.name) | (EntityType.slug == slug)
        )
    )
    if existing.scalar():
        raise ConflictError(
            "Entity Type already exists",
            detail=f"An entity type with name '{data.name}' or slug '{slug}' already exists",
        )

    # Check for hierarchy mapping (e.g., "Stadt" should use territorial_entity)
    from app.utils.similarity import get_hierarchy_mapping, find_similar_entity_types
    hierarchy_mapping = get_hierarchy_mapping(data.name)
    if hierarchy_mapping:
        parent_slug = hierarchy_mapping["parent_type_slug"]
        level_name = hierarchy_mapping["level_name"]
        raise ConflictError(
            "Hierarchischer EntityType existiert bereits",
            detail=f"'{data.name}' ist ein Hierarchie-Level von '{parent_slug}' ({level_name}). "
                   f"Verwenden Sie stattdessen den bestehenden Typ '{parent_slug}'.",
        )

    # Check for semantically similar EntityTypes (AI-based)
    similar_types = await find_similar_entity_types(session, data.name)
    if similar_types:
        existing_type, score, _ = similar_types[0]
        raise ConflictError(
            "Semantisch ähnlicher EntityType existiert bereits",
            detail=f"'{existing_type.name}' ({existing_type.slug}) ist semantisch ähnlich ({int(score*100)}%). "
                   f"Verwenden Sie diesen statt einen neuen zu erstellen.",
        )

    async with AuditContext(session, current_user, request) as audit:
        entity_type = EntityType(
            name=data.name,
            slug=slug,
            name_plural=data.name_plural or f"{data.name}s",
            description=data.description,
            icon=data.icon,
            color=data.color,
            is_primary=data.is_primary,
            supports_hierarchy=data.supports_hierarchy,
            hierarchy_config=data.hierarchy_config,
            attribute_schema=data.attribute_schema,
            display_order=data.display_order,
            is_active=data.is_active,
            is_public=data.is_public,
            is_system=False,
            created_by_id=current_user.id if current_user else None,
            owner_id=current_user.id if current_user else None,
        )
        session.add(entity_type)
        await session.flush()

        # Generate embedding for semantic similarity search
        from app.utils.similarity import generate_embedding
        embedding = await generate_embedding(entity_type.name)
        if embedding:
            entity_type.name_embedding = embedding

        audit.track_action(
            action=AuditAction.CREATE,
            entity_type="EntityType",
            entity_id=entity_type.id,
            entity_name=entity_type.name,
            changes={
                "name": entity_type.name,
                "slug": entity_type.slug,
                "is_public": entity_type.is_public,
                "is_primary": entity_type.is_primary,
                "supports_hierarchy": entity_type.supports_hierarchy,
            },
        )

        await session.commit()
        await session.refresh(entity_type)

    return EntityTypeResponse.model_validate(entity_type)


@router.get("/{entity_type_id}", response_model=EntityTypeResponse)
async def get_entity_type(
    entity_type_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a single entity type by ID."""
    entity_type = await session.get(EntityType, entity_type_id)
    if not entity_type:
        raise NotFoundError("EntityType", str(entity_type_id))

    entity_count = (await session.execute(
        select(func.count()).where(Entity.entity_type_id == entity_type.id)
    )).scalar()

    response = EntityTypeResponse.model_validate(entity_type)
    response.entity_count = entity_count

    return response


@router.get("/by-slug/{slug}", response_model=EntityTypeResponse)
async def get_entity_type_by_slug(
    slug: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a single entity type by slug."""
    result = await session.execute(
        select(EntityType).where(EntityType.slug == slug)
    )
    entity_type = result.scalar()
    if not entity_type:
        raise NotFoundError("EntityType", slug)

    entity_count = (await session.execute(
        select(func.count()).where(Entity.entity_type_id == entity_type.id)
    )).scalar()

    response = EntityTypeResponse.model_validate(entity_type)
    response.entity_count = entity_count

    return response


@router.put("/{entity_type_id}", response_model=EntityTypeResponse)
async def update_entity_type(
    entity_type_id: UUID,
    data: EntityTypeUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Update an entity type."""
    entity_type = await session.get(EntityType, entity_type_id)
    if not entity_type:
        raise NotFoundError("EntityType", str(entity_type_id))

    # Capture old state
    old_data = {
        "name": entity_type.name,
        "slug": entity_type.slug,
        "is_public": entity_type.is_public,
        "is_active": entity_type.is_active,
        "is_primary": entity_type.is_primary,
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
            setattr(entity_type, field, value)

        new_data = {
            "name": entity_type.name,
            "slug": entity_type.slug,
            "is_public": entity_type.is_public,
            "is_active": entity_type.is_active,
            "is_primary": entity_type.is_primary,
        }

        audit.track_update(entity_type, old_data, new_data)

        await session.commit()
        await session.refresh(entity_type)

    return EntityTypeResponse.model_validate(entity_type)


@router.delete("/{entity_type_id}", response_model=MessageResponse)
async def delete_entity_type(
    entity_type_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Delete an entity type."""
    entity_type = await session.get(EntityType, entity_type_id)
    if not entity_type:
        raise NotFoundError("EntityType", str(entity_type_id))

    if entity_type.is_system:
        raise ConflictError(
            "Cannot delete system entity type",
            detail=f"Entity type '{entity_type.name}' is a system type and cannot be deleted",
        )

    # Check for existing entities
    entity_count = (await session.execute(
        select(func.count()).where(Entity.entity_type_id == entity_type.id)
    )).scalar()

    if entity_count > 0:
        raise ConflictError(
            "Cannot delete entity type with existing entities",
            detail=f"Entity type '{entity_type.name}' has {entity_count} entities. Delete them first.",
        )

    # Check for RelationType dependencies (source or target)
    relation_type_count = (await session.execute(
        select(func.count()).where(
            or_(
                RelationType.source_entity_type_id == entity_type.id,
                RelationType.target_entity_type_id == entity_type.id,
            )
        )
    )).scalar()

    if relation_type_count > 0:
        raise ConflictError(
            "Cannot delete entity type with existing relation types",
            detail=f"Entity type '{entity_type.name}' is used by {relation_type_count} relation type(s). Delete them first.",
        )

    # Check for AnalysisTemplate dependencies
    analysis_template_count = (await session.execute(
        select(func.count()).where(
            AnalysisTemplate.primary_entity_type_id == entity_type.id
        )
    )).scalar()

    if analysis_template_count > 0:
        raise ConflictError(
            "Cannot delete entity type with existing analysis templates",
            detail=f"Entity type '{entity_type.name}' is used by {analysis_template_count} analysis template(s). Delete them first.",
        )

    # Clean up FacetType references to this entity type slug
    slug_to_remove = entity_type.slug
    facet_types_with_ref = await session.execute(
        select(FacetType).where(
            FacetType.applicable_entity_type_slugs.any(slug_to_remove)
        )
    )
    for facet_type in facet_types_with_ref.scalars():
        facet_type.applicable_entity_type_slugs = [
            s for s in facet_type.applicable_entity_type_slugs if s != slug_to_remove
        ]

    entity_type_name = entity_type.name

    async with AuditContext(session, current_user, request) as audit:
        audit.track_action(
            action=AuditAction.DELETE,
            entity_type="EntityType",
            entity_id=entity_type_id,
            entity_name=entity_type_name,
            changes={
                "deleted": True,
                "name": entity_type_name,
                "slug": slug_to_remove,
            },
        )

        await session.delete(entity_type)
        await session.commit()

    return MessageResponse(message=f"Entity type '{entity_type_name}' deleted successfully")
