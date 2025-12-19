"""Entity schemas for API validation."""

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


def normalize_name(name: str) -> str:
    """Normalize name for search (lowercase, no special chars)."""
    normalized = name.lower()
    normalized = re.sub(
        r"[äöüß]",
        lambda m: {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}[m.group()],
        normalized,
    )
    normalized = re.sub(r"[^a-z0-9\s]", "", normalized)
    return normalized.strip()


class EntityBase(BaseModel):
    """Base entity schema with common fields."""

    name: str = Field(..., min_length=1, max_length=500, description="Primary name")
    external_id: Optional[str] = Field(None, max_length=255, description="External reference (AGS, UUID, etc.)")

    # Hierarchy (optional)
    parent_id: Optional[UUID] = Field(None, description="Parent entity ID")

    # Core attributes (type-specific)
    core_attributes: Dict[str, Any] = Field(default_factory=dict, description="Type-specific attributes")

    # Geo-coordinates (optional)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

    is_active: bool = Field(default=True, description="Whether entity is active")


class EntityCreate(EntityBase):
    """Schema for creating a new entity."""

    entity_type_id: UUID = Field(..., description="Entity type ID")
    slug: Optional[str] = Field(None, description="URL-friendly slug (auto-generated if not provided)")

    # Ownership (optional)
    owner_id: Optional[UUID] = Field(None, description="Owner user ID (optional)")

    @field_validator("slug", mode="before")
    @classmethod
    def generate_slug_if_empty(cls, v, info):
        if not v and "name" in info.data:
            return generate_slug(info.data["name"])
        return v


class EntityUpdate(BaseModel):
    """Schema for updating an entity."""

    name: Optional[str] = Field(None, min_length=1, max_length=500)
    external_id: Optional[str] = Field(None, max_length=255)
    parent_id: Optional[UUID] = None
    core_attributes: Optional[Dict[str, Any]] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    is_active: Optional[bool] = None

    # Ownership (optional)
    owner_id: Optional[UUID] = Field(None, description="Owner user ID")


class EntityBrief(BaseModel):
    """Brief entity info for nested responses."""

    id: UUID
    name: str
    slug: str
    entity_type_slug: str

    model_config = {"from_attributes": True}


class UserBrief(BaseModel):
    """Brief user info for entity ownership."""

    id: UUID
    full_name: str
    email: str

    model_config = {"from_attributes": True}


class EntityResponse(EntityBase):
    """Schema for entity response."""

    id: UUID
    entity_type_id: UUID
    slug: str
    name_normalized: str
    hierarchy_path: Optional[str]
    hierarchy_level: int
    created_at: datetime
    updated_at: datetime

    # Ownership
    created_by_id: Optional[UUID] = Field(None, description="User who created this entity")
    owner_id: Optional[UUID] = Field(None, description="User who owns this entity")
    created_by: Optional[UserBrief] = Field(None, description="Creator user info")
    owner: Optional[UserBrief] = Field(None, description="Owner user info")

    # Nested info
    entity_type_name: Optional[str] = Field(None, description="Entity type display name")
    entity_type_slug: Optional[str] = Field(None, description="Entity type slug")
    parent_name: Optional[str] = Field(None, description="Parent entity name")

    # Computed fields
    facet_count: int = Field(default=0, description="Number of facet values")
    relation_count: int = Field(default=0, description="Number of relations")
    source_count: int = Field(default=0, description="Number of data sources")
    children_count: int = Field(default=0, description="Number of child entities")

    model_config = {"from_attributes": True}


class EntityListResponse(BaseModel):
    """Schema for entity list response."""

    items: List[EntityResponse]
    total: int
    page: int
    per_page: int
    pages: int


class EntityHierarchy(BaseModel):
    """Entity with hierarchy info."""

    id: UUID
    name: str
    slug: str
    hierarchy_level: int
    children: List["EntityHierarchy"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# For recursive model
EntityHierarchy.model_rebuild()
