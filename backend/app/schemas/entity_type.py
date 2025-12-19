"""EntityType schemas for API validation."""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


def generate_slug(name: str) -> str:
    """Generate URL-friendly slug from name."""
    slug = name.lower()
    slug = re.sub(
        r"[äöüß]",
        lambda m: {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}[m.group()],
        slug,
    )
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


class EntityTypeBase(BaseModel):
    """Base entity type schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Display name")
    name_plural: str = Field(..., min_length=1, max_length=255, description="Plural form")
    description: Optional[str] = Field(None, description="Description")

    # UI Configuration
    icon: str = Field(default="mdi-help-circle", description="Material Design Icon name")
    color: str = Field(default="#607D8B", description="Hex color for UI")
    display_order: int = Field(default=0, description="Order in UI lists")

    # Capabilities
    is_primary: bool = Field(default=False, description="Can serve as primary aggregation level")
    supports_hierarchy: bool = Field(default=False, description="Has hierarchical structure")
    hierarchy_config: Optional[Dict[str, Any]] = Field(
        None,
        description='Hierarchy configuration {"levels": ["country", "admin_level_1", ...]}',
    )

    # Schema
    attribute_schema: Optional[Dict[str, Any]] = Field(
        None,
        description="JSON Schema defining core_attributes structure",
    )

    is_active: bool = Field(default=True, description="Whether entity type is active")

    # Visibility
    is_public: bool = Field(
        default=False,
        description="If true, visible to all users. If false, only visible to owner.",
    )


class EntityTypeCreate(EntityTypeBase):
    """Schema for creating a new entity type."""

    slug: Optional[str] = Field(None, description="URL-friendly slug (auto-generated if not provided)")

    @field_validator("slug", mode="before")
    @classmethod
    def generate_slug_if_empty(cls, v, info):
        if not v and "name" in info.data:
            return generate_slug(info.data["name"])
        return v


class EntityTypeUpdate(BaseModel):
    """Schema for updating an entity type."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    name_plural: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    display_order: Optional[int] = None
    is_primary: Optional[bool] = None
    supports_hierarchy: Optional[bool] = None
    hierarchy_config: Optional[Dict[str, Any]] = None
    attribute_schema: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None


class EntityTypeResponse(EntityTypeBase):
    """Schema for entity type response."""

    id: UUID
    slug: str
    is_system: bool
    created_at: datetime
    updated_at: datetime

    # Ownership
    created_by_id: Optional[UUID] = Field(None, description="User who created this entity type")
    owner_id: Optional[UUID] = Field(None, description="User who owns this entity type")

    # Computed fields
    entity_count: int = Field(default=0, description="Number of entities of this type")

    model_config = {"from_attributes": True}


class EntityTypeListResponse(BaseModel):
    """Schema for entity type list response."""

    items: List[EntityTypeResponse]
    total: int
