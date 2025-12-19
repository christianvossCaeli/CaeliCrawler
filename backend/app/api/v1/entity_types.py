"""API endpoints for Entity Type management."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import EntityType, Entity
from app.models.user import User
from app.schemas.entity_type import (
    EntityTypeCreate,
    EntityTypeUpdate,
    EntityTypeResponse,
    EntityTypeListResponse,
    generate_slug,
)
from app.schemas.common import MessageResponse
from app.core.exceptions import NotFoundError, ConflictError
from app.core.deps import get_current_user_optional

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
        query = query.where(EntityType.is_public == is_public)
    elif include_private and current_user:
        # Show public + user's own private types
        query = query.where(
            or_(
                EntityType.is_public == True,
                EntityType.owner_id == current_user.id,
                EntityType.created_by_id == current_user.id,
            )
        )
    else:
        # Only public entity types
        query = query.where(EntityType.is_public == True)

    if is_active is not None:
        query = query.where(EntityType.is_active == is_active)
    if is_primary is not None:
        query = query.where(EntityType.is_primary == is_primary)
    if search:
        query = query.where(
            EntityType.name.ilike(f"%{search}%") |
            EntityType.slug.ilike(f"%{search}%")
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(EntityType.display_order, EntityType.name).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    entity_types = result.scalars().all()

    # Get entity counts
    items = []
    for et in entity_types:
        entity_count = (await session.execute(
            select(func.count()).where(Entity.entity_type_id == et.id)
        )).scalar()

        item = EntityTypeResponse.model_validate(et)
        item.entity_count = entity_count
        items.append(item)

    return EntityTypeListResponse(items=items, total=total)


@router.post("", response_model=EntityTypeResponse, status_code=201)
async def create_entity_type(
    data: EntityTypeCreate,
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Create a new entity type.

    New entity types are private by default (is_public=False).
    The creating user becomes the owner.
    """
    # Generate slug if not provided
    slug = data.slug or generate_slug(data.name)

    # Check for duplicate
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
    session: AsyncSession = Depends(get_session),
):
    """Update an entity type."""
    entity_type = await session.get(EntityType, entity_type_id)
    if not entity_type:
        raise NotFoundError("EntityType", str(entity_type_id))

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entity_type, field, value)

    await session.commit()
    await session.refresh(entity_type)

    return EntityTypeResponse.model_validate(entity_type)


@router.delete("/{entity_type_id}", response_model=MessageResponse)
async def delete_entity_type(
    entity_type_id: UUID,
    session: AsyncSession = Depends(get_session),
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

    await session.delete(entity_type)
    await session.commit()

    return MessageResponse(message=f"Entity type '{entity_type.name}' deleted successfully")
