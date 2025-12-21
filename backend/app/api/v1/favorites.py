"""API endpoints for User Favorites management."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import Entity, EntityType, User
from app.models.user_favorite import UserFavorite
from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError, ConflictError
from app.schemas.common import MessageResponse
from app.schemas.favorite import (
    FavoriteCheckResponse,
    FavoriteCreate,
    FavoriteEntityBrief,
    FavoriteListResponse,
    FavoriteResponse,
)

router = APIRouter()


@router.get("", response_model=FavoriteListResponse)
async def list_favorites(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    entity_type_slug: Optional[str] = Query(default=None, description="Filter by entity type slug"),
    search: Optional[str] = Query(default=None, description="Search in entity name"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    List user's favorite entities with pagination.

    Supports filtering by entity type and search in entity name.
    """
    # Base query
    query = (
        select(UserFavorite)
        .where(UserFavorite.user_id == current_user.id)
        .options(selectinload(UserFavorite.entity).selectinload(Entity.entity_type))
    )

    # Filter by entity type
    if entity_type_slug:
        subq = select(EntityType.id).where(EntityType.slug == entity_type_slug)
        query = query.join(Entity).where(Entity.entity_type_id.in_(subq))

    # Search in entity name
    if search:
        if not entity_type_slug:
            query = query.join(Entity, isouter=True)
        query = query.where(Entity.name.ilike(f"%{search}%"))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    # Paginate and order by created_at desc
    query = (
        query.order_by(UserFavorite.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await session.execute(query)
    favorites = result.scalars().all()

    items = []
    for fav in favorites:
        entity = fav.entity
        entity_type = entity.entity_type if entity else None

        items.append(
            FavoriteResponse(
                id=fav.id,
                user_id=fav.user_id,
                entity_id=fav.entity_id,
                created_at=fav.created_at,
                entity=FavoriteEntityBrief(
                    id=entity.id,
                    name=entity.name,
                    slug=entity.slug,
                    entity_type_id=entity.entity_type_id,
                    entity_type_slug=entity_type.slug if entity_type else None,
                    entity_type_name=entity_type.name if entity_type else None,
                    entity_type_icon=entity_type.icon if entity_type else None,
                    entity_type_color=entity_type.color if entity_type else None,
                    hierarchy_path=entity.hierarchy_path,
                    is_active=entity.is_active,
                ),
            )
        )

    return FavoriteListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.post("", response_model=FavoriteResponse, status_code=201)
async def add_favorite(
    data: FavoriteCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Add an entity to favorites.

    Returns 409 Conflict if the entity is already favorited.
    """
    # Verify entity exists
    entity = await session.get(Entity, data.entity_id)
    if not entity:
        raise NotFoundError("Entity", str(data.entity_id))

    # Check if already favorited
    existing = await session.execute(
        select(UserFavorite).where(
            UserFavorite.user_id == current_user.id,
            UserFavorite.entity_id == data.entity_id,
        )
    )
    if existing.scalar():
        raise ConflictError(
            "Already favorited",
            detail="This entity is already in your favorites",
        )

    # Get entity type for response
    entity_type = await session.get(EntityType, entity.entity_type_id)

    # Create favorite
    favorite = UserFavorite(
        user_id=current_user.id,
        entity_id=data.entity_id,
    )
    session.add(favorite)
    await session.commit()
    await session.refresh(favorite)

    return FavoriteResponse(
        id=favorite.id,
        user_id=favorite.user_id,
        entity_id=favorite.entity_id,
        created_at=favorite.created_at,
        entity=FavoriteEntityBrief(
            id=entity.id,
            name=entity.name,
            slug=entity.slug,
            entity_type_id=entity.entity_type_id,
            entity_type_slug=entity_type.slug if entity_type else None,
            entity_type_name=entity_type.name if entity_type else None,
            entity_type_icon=entity_type.icon if entity_type else None,
            entity_type_color=entity_type.color if entity_type else None,
            hierarchy_path=entity.hierarchy_path,
            is_active=entity.is_active,
        ),
    )


@router.get("/check/{entity_id}", response_model=FavoriteCheckResponse)
async def check_favorite(
    entity_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Check if an entity is in the user's favorites.

    Returns the favorite status and favorite ID if favorited.
    """
    result = await session.execute(
        select(UserFavorite).where(
            UserFavorite.user_id == current_user.id,
            UserFavorite.entity_id == entity_id,
        )
    )
    favorite = result.scalar()

    return FavoriteCheckResponse(
        entity_id=entity_id,
        is_favorited=favorite is not None,
        favorite_id=favorite.id if favorite else None,
    )


@router.delete("/{favorite_id}", response_model=MessageResponse)
async def remove_favorite(
    favorite_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Remove an entity from favorites by favorite ID.
    """
    result = await session.execute(
        select(UserFavorite).where(
            UserFavorite.id == favorite_id,
            UserFavorite.user_id == current_user.id,
        )
    )
    favorite = result.scalar()

    if not favorite:
        raise NotFoundError("Favorite", str(favorite_id))

    await session.delete(favorite)
    await session.commit()

    return MessageResponse(message="Favorite removed successfully")


@router.delete("/entity/{entity_id}", response_model=MessageResponse)
async def remove_favorite_by_entity(
    entity_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Remove an entity from favorites by entity ID.

    Convenience endpoint for removing a favorite without knowing the favorite ID.
    """
    result = await session.execute(
        delete(UserFavorite).where(
            UserFavorite.user_id == current_user.id,
            UserFavorite.entity_id == entity_id,
        )
    )

    if result.rowcount == 0:
        raise NotFoundError("Favorite", str(entity_id))

    await session.commit()
    return MessageResponse(message="Favorite removed successfully")
