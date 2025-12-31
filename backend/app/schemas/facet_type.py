"""FacetType schemas for API validation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.facet_type import AggregationMethod, TimeFilter, ValueType
from app.utils.text import create_slug as generate_slug


class FacetTypeBase(BaseModel):
    """Base facet type schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Display name")
    name_plural: str = Field(..., min_length=1, max_length=255, description="Plural form")
    description: str | None = Field(None, description="Description")

    # Value configuration with enum validation
    value_type: ValueType = Field(
        default=ValueType.STRUCTURED,
        description="Type: text, structured, list, reference, number, boolean"
    )
    value_schema: dict[str, Any] | None = Field(None, description="JSON Schema for value structure")

    # Applicable entity types
    applicable_entity_type_slugs: list[str] = Field(
        default_factory=list,
        description="Entity type slugs this facet applies to (empty = all)",
    )

    # UI Configuration
    icon: str = Field(default="mdi-tag", description="Material Design Icon name")
    color: str = Field(default="#607D8B", description="Hex color for UI")
    display_order: int = Field(default=0, description="Order in UI lists")

    # Aggregation configuration with enum validation
    aggregation_method: AggregationMethod = Field(
        default=AggregationMethod.DEDUPE,
        description="Method: count, sum, avg, list, dedupe, latest, min, max"
    )
    deduplication_fields: list[str] = Field(default_factory=list, description="Fields for deduplication")

    # Time-based configuration with enum validation
    is_time_based: bool = Field(default=False, description="Has date/time component")
    time_field_path: str | None = Field(None, description="JSON path to date field")
    default_time_filter: TimeFilter = Field(
        default=TimeFilter.ALL,
        description="Default filter: all, future_only, past_only"
    )

    # AI extraction
    ai_extraction_enabled: bool = Field(default=True, description="Enable AI extraction")
    ai_extraction_prompt: str | None = Field(None, description="AI prompt template")

    # Entity reference configuration
    allows_entity_reference: bool = Field(
        default=False,
        description="Can this FacetType reference another Entity?"
    )
    target_entity_type_slugs: list[str] = Field(
        default_factory=list,
        description="Allowed entity type slugs for reference (empty = all)"
    )
    auto_create_entity: bool = Field(
        default=False,
        description="Automatically create Entity if none found during matching?"
    )

    is_active: bool = Field(default=True, description="Whether facet type is active")


class FacetTypeCreate(FacetTypeBase):
    """Schema for creating a new facet type."""

    slug: str | None = Field(None, description="URL-friendly slug (auto-generated if not provided)")

    @field_validator("slug", mode="before")
    @classmethod
    def generate_slug_if_empty(cls, v, info):
        if not v and "name" in info.data:
            return generate_slug(info.data["name"])
        return v


class FacetTypeUpdate(BaseModel):
    """Schema for updating a facet type."""

    name: str | None = Field(None, min_length=1, max_length=255)
    name_plural: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    value_type: ValueType | None = None
    value_schema: dict[str, Any] | None = None
    applicable_entity_type_slugs: list[str] | None = None
    icon: str | None = None
    color: str | None = None
    display_order: int | None = None
    aggregation_method: AggregationMethod | None = None
    deduplication_fields: list[str] | None = None
    is_time_based: bool | None = None
    time_field_path: str | None = None
    default_time_filter: TimeFilter | None = None
    ai_extraction_enabled: bool | None = None
    ai_extraction_prompt: str | None = None
    allows_entity_reference: bool | None = None
    target_entity_type_slugs: list[str] | None = None
    auto_create_entity: bool | None = None
    is_active: bool | None = None


class FacetTypeResponse(BaseModel):
    """Schema for facet type response.

    Note: Uses string types for enums to allow reading existing data that may
    contain values not in the current enum (for backwards compatibility).
    """

    id: UUID
    slug: str
    is_system: bool
    created_at: datetime
    updated_at: datetime

    # Fields from base (using permissive types for response)
    name: str
    name_plural: str
    description: str | None = None
    value_type: str = Field(description="Type: text, structured, list, reference, etc.")
    value_schema: dict[str, Any] | None = None
    applicable_entity_type_slugs: list[str] = Field(default_factory=list)
    icon: str = Field(default="mdi-tag")
    color: str = Field(default="#607D8B")
    display_order: int = Field(default=0)
    aggregation_method: str = Field(default="dedupe")
    deduplication_fields: list[str] = Field(default_factory=list)
    is_time_based: bool = Field(default=False)
    time_field_path: str | None = None
    default_time_filter: str = Field(default="all")
    ai_extraction_enabled: bool = Field(default=True)
    ai_extraction_prompt: str | None = None
    allows_entity_reference: bool = Field(default=False)
    target_entity_type_slugs: list[str] = Field(default_factory=list)
    auto_create_entity: bool = Field(default=False)
    is_active: bool = Field(default=True)

    # Computed fields
    value_count: int = Field(default=0, description="Number of facet values of this type")

    model_config = {"from_attributes": True}


class FacetTypeListResponse(BaseModel):
    """Schema for facet type list response."""

    items: list[FacetTypeResponse]
    total: int
    page: int
    per_page: int
    pages: int


class FacetTypeSchemaGenerateRequest(BaseModel):
    """Request schema for AI-powered facet type schema generation."""

    name: str = Field(..., min_length=1, description="Name of the facet type")
    name_plural: str | None = Field(None, description="Plural form of the name")
    description: str | None = Field(None, description="Description of what this facet captures")
    applicable_entity_types: list[str] = Field(
        default_factory=list,
        description="Entity type names this facet applies to (e.g. 'Gemeinde', 'Person')",
    )


class FacetTypeSchemaGenerateResponse(BaseModel):
    """Response schema for AI-generated facet type configuration."""

    value_type: str = Field(default="structured", description="Recommended value type")
    value_schema: dict[str, Any] | None = Field(None, description="Generated JSON Schema")
    deduplication_fields: list[str] = Field(default_factory=list, description="Suggested deduplication fields")
    is_time_based: bool = Field(default=False, description="Whether facet has time component")
    time_field_path: str | None = Field(None, description="JSON path to date field if time-based")
    ai_extraction_prompt: str | None = Field(None, description="Generated AI extraction prompt")
    icon: str | None = Field(None, description="Suggested icon")
    color: str | None = Field(None, description="Suggested color")
