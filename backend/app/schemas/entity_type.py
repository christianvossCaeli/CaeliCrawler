"""EntityType schemas for API validation."""

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.utils.text import create_slug as generate_slug

# Regex pattern for valid slugs: lowercase letters, numbers, and hyphens only
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SLUG_MAX_LENGTH = 100


class EntityTypeBase(BaseModel):
    """Base entity type schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Display name")
    name_plural: str = Field(..., min_length=1, max_length=255, description="Plural form")
    description: str | None = Field(None, description="Description")

    # UI Configuration
    icon: str = Field(default="mdi-help-circle", description="Material Design Icon name")
    color: str = Field(default="#607D8B", description="Hex color for UI")
    display_order: int = Field(default=0, description="Order in UI lists")

    # Capabilities
    is_primary: bool = Field(default=False, description="Can serve as primary aggregation level")
    supports_hierarchy: bool = Field(default=False, description="Has hierarchical structure")
    supports_pysis: bool = Field(default=False, description="Supports PySis data enrichment")
    hierarchy_config: dict[str, Any] | None = Field(
        None,
        description='Hierarchy configuration {"levels": ["country", "admin_level_1", ...]}',
    )

    # Schema
    attribute_schema: dict[str, Any] | None = Field(
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

    slug: str | None = Field(
        None, max_length=SLUG_MAX_LENGTH, description="URL-friendly slug (auto-generated if not provided)"
    )

    @field_validator("slug", mode="before")
    @classmethod
    def generate_slug_if_empty(cls, v, info):
        if not v and "name" in info.data:
            return generate_slug(info.data["name"])
        return v

    @field_validator("slug", mode="after")
    @classmethod
    def validate_slug_format(cls, v):
        if v is not None:
            if len(v) > SLUG_MAX_LENGTH:
                raise ValueError(f"Slug must be at most {SLUG_MAX_LENGTH} characters")
            if not SLUG_PATTERN.match(v):
                raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        return v


class EntityTypeUpdate(BaseModel):
    """Schema for updating an entity type."""

    name: str | None = Field(None, min_length=1, max_length=255)
    name_plural: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    display_order: int | None = None
    is_primary: bool | None = None
    supports_hierarchy: bool | None = None
    supports_pysis: bool | None = None
    hierarchy_config: dict[str, Any] | None = None
    attribute_schema: dict[str, Any] | None = None
    is_active: bool | None = None
    is_public: bool | None = None


class EntityTypeResponse(EntityTypeBase):
    """Schema for entity type response."""

    id: UUID
    slug: str
    is_system: bool
    created_at: datetime
    updated_at: datetime

    # Ownership
    created_by_id: UUID | None = Field(None, description="User who created this entity type")
    owner_id: UUID | None = Field(None, description="User who owns this entity type")

    # Computed fields
    entity_count: int = Field(default=0, description="Number of entities of this type")

    model_config = {"from_attributes": True}


class EntityTypeListResponse(BaseModel):
    """Schema for entity type list response."""

    items: list[EntityTypeResponse]
    total: int
    page: int = Field(default=1, description="Current page number")
    per_page: int = Field(default=50, description="Items per page")
    pages: int = Field(default=1, description="Total number of pages")
