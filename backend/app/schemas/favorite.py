"""Favorite schemas for API validation."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class FavoriteCreate(BaseModel):
    """Schema for adding a favorite."""

    entity_id: UUID = Field(..., description="Entity ID to favorite")


class FavoriteEntityBrief(BaseModel):
    """Brief entity info for favorite response."""

    id: UUID
    name: str
    slug: str
    entity_type_id: UUID
    entity_type_slug: Optional[str] = None
    entity_type_name: Optional[str] = None
    entity_type_icon: Optional[str] = None
    entity_type_color: Optional[str] = None
    hierarchy_path: Optional[str] = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class FavoriteResponse(BaseModel):
    """Schema for favorite response."""

    id: UUID
    user_id: UUID
    entity_id: UUID
    created_at: datetime
    entity: FavoriteEntityBrief

    model_config = {"from_attributes": True}


class FavoriteListResponse(BaseModel):
    """Schema for favorites list response."""

    items: List[FavoriteResponse]
    total: int
    page: int
    per_page: int
    pages: int


class FavoriteCheckResponse(BaseModel):
    """Schema for checking if entity is favorited."""

    entity_id: UUID
    is_favorited: bool
    favorite_id: Optional[UUID] = None
