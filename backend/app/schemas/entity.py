"""Entity schemas for API validation."""

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.utils.text import create_slug as generate_slug

# Regex pattern for valid slugs: lowercase letters, numbers, and hyphens only
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SLUG_MAX_LENGTH = 100


class EntityBase(BaseModel):
    """Base entity schema with common fields."""

    name: str = Field(..., min_length=1, max_length=500, description="Primary name")
    external_id: str | None = Field(None, max_length=255, description="External reference (AGS, UUID, etc.)")

    # Hierarchy (optional)
    parent_id: UUID | None = Field(None, description="Parent entity ID")

    # Location fields for filtering
    country: str | None = Field(None, max_length=2, description="ISO 3166-1 alpha-2 country code (DE, GB, etc.)")
    admin_level_1: str | None = Field(None, max_length=100, description="First-level admin division (Bundesland, Region)")
    admin_level_2: str | None = Field(None, max_length=100, description="Second-level admin division (Landkreis, District)")

    # Core attributes (type-specific)
    core_attributes: dict[str, Any] = Field(default_factory=dict, description="Type-specific attributes")

    # Geo-coordinates (optional, for point locations)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)

    # GeoJSON geometry (optional, for complex shapes)
    geometry: dict[str, Any] | None = Field(None, description="GeoJSON geometry for boundaries/regions")

    is_active: bool = Field(default=True, description="Whether entity is active")


class EntityCreate(EntityBase):
    """Schema for creating a new entity."""

    entity_type_id: UUID = Field(..., description="Entity type ID")
    slug: str | None = Field(
        None,
        max_length=SLUG_MAX_LENGTH,
        description="URL-friendly slug (auto-generated if not provided)"
    )

    # Ownership (optional)
    owner_id: UUID | None = Field(None, description="Owner user ID (optional)")

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


class EntityUpdate(BaseModel):
    """Schema for updating an entity."""

    name: str | None = Field(None, min_length=1, max_length=500)
    external_id: str | None = Field(None, max_length=255)
    parent_id: UUID | None = None

    # Location fields
    country: str | None = Field(None, max_length=2)
    admin_level_1: str | None = Field(None, max_length=100)
    admin_level_2: str | None = Field(None, max_length=100)

    core_attributes: dict[str, Any] | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    geometry: dict[str, Any] | None = Field(None, description="GeoJSON geometry for boundaries/regions")
    is_active: bool | None = None

    # Ownership (optional)
    owner_id: UUID | None = Field(None, description="Owner user ID")


class EntityBrief(BaseModel):
    """Brief entity info for nested responses."""

    id: UUID
    name: str
    slug: str
    entity_type_slug: str | None = None
    entity_type_name: str | None = None
    hierarchy_path: str | None = None

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
    hierarchy_path: str | None
    hierarchy_level: int
    created_at: datetime
    updated_at: datetime

    # Ownership
    created_by_id: UUID | None = Field(None, description="User who created this entity")
    owner_id: UUID | None = Field(None, description="User who owns this entity")
    created_by: UserBrief | None = Field(None, description="Creator user info")
    owner: UserBrief | None = Field(None, description="Owner user info")

    # Nested info
    entity_type_name: str | None = Field(None, description="Entity type display name")
    entity_type_slug: str | None = Field(None, description="Entity type slug")
    parent_name: str | None = Field(None, description="Parent entity name")
    parent_slug: str | None = Field(None, description="Parent entity slug")

    # Computed fields
    facet_count: int = Field(default=0, description="Number of facet values")
    relation_count: int = Field(default=0, description="Number of relations")
    children_count: int = Field(default=0, description="Number of child entities")

    # External source info (for entities imported from APIs)
    api_configuration_id: UUID | None = Field(None, description="ID of the API configuration")
    external_source_name: str | None = Field(None, description="Name of the data source")
    external_id: str | None = Field(None, description="ID in the external system")

    model_config = {"from_attributes": True}


class EntityListResponse(BaseModel):
    """Schema for entity list response."""

    items: list[EntityResponse]
    total: int
    page: int
    per_page: int
    pages: int


class EntityHierarchyNode(BaseModel):
    """Single node in entity hierarchy tree."""

    id: str
    name: str
    slug: str
    external_id: str | None = None
    hierarchy_level: int
    children: list["EntityHierarchyNode"] = Field(default_factory=list)
    children_count: int = 0

    model_config = {"from_attributes": True}


# For recursive model
EntityHierarchyNode.model_rebuild()


class EntityHierarchy(BaseModel):
    """Entity hierarchy response with tree structure."""

    entity_type_id: UUID
    entity_type_slug: str
    entity_type_name: str
    root_id: UUID | None = None
    tree: list[dict[str, Any]] = Field(default_factory=list)
    total_nodes: int = 0

    model_config = {"from_attributes": True}


class LocationFilterOptionsResponse(BaseModel):
    """Response for location filter options."""

    countries: list[str] = Field(default_factory=list, description="Available countries")
    admin_level_1: list[str] = Field(default_factory=list, description="Available admin level 1 values (states)")
    admin_level_2: list[str] = Field(default_factory=list, description="Available admin level 2 values (districts)")


class FilterableAttribute(BaseModel):
    """Schema for a filterable attribute."""

    key: str = Field(..., description="Attribute key in core_attributes")
    title: str = Field(..., description="Human-readable title")
    description: str | None = Field(None, description="Attribute description")
    type: str = Field(..., description="Attribute data type (string, integer, number)")
    format: str | None = Field(None, description="Format specification (e.g., date, email)")


class AttributeFilterOptionsResponse(BaseModel):
    """Response for attribute filter options."""

    entity_type_slug: str = Field(..., description="Entity type slug")
    entity_type_name: str = Field(..., description="Entity type name")
    attributes: list[FilterableAttribute] = Field(default_factory=list, description="Filterable attributes")
    attribute_values: dict[str, list[str]] | None = Field(
        None, description="Distinct values for requested attribute"
    )


class EntityDocumentsResponse(BaseModel):
    """Response for entity documents."""

    entity_id: UUID
    entity_name: str
    items: list[dict[str, Any]] = Field(default_factory=list)
    total: int
    page: int
    per_page: int
    pages: int


class EntitySourcesResponse(BaseModel):
    """Response for entity sources."""

    entity_id: UUID
    entity_name: str
    items: list[dict[str, Any]] = Field(default_factory=list)
    total: int


class EntityExternalDataResponse(BaseModel):
    """Response for entity external data."""

    entity_id: UUID
    entity_name: str
    has_external_data: bool = False
    api_configuration_id: UUID | None = None
    external_source_name: str | None = None
    external_id: str | None = None
    raw_data: dict[str, Any] | None = None
    last_synced_at: datetime | None = None


class GeoJSONFeature(BaseModel):
    """GeoJSON Feature for entity map display."""

    type: str = "Feature"
    geometry: dict[str, Any]
    properties: dict[str, Any]


class GeoJSONFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection for entity map display."""

    type: str = "FeatureCollection"
    features: list[GeoJSONFeature]
    total_with_coords: int = Field(0, description="Total entities with coordinates")
    total_without_coords: int = Field(0, description="Total entities without coordinates")
