"""FacetType schemas for API validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.utils.text import create_slug as generate_slug
from app.models.facet_type import ValueType, AggregationMethod, TimeFilter


class FacetTypeBase(BaseModel):
    """Base facet type schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Display name")
    name_plural: str = Field(..., min_length=1, max_length=255, description="Plural form")
    description: Optional[str] = Field(None, description="Description")

    # Value configuration with enum validation
    value_type: ValueType = Field(
        default=ValueType.STRUCTURED,
        description="Type: text, structured, list, reference, number, boolean"
    )
    value_schema: Optional[Dict[str, Any]] = Field(None, description="JSON Schema for value structure")

    # Applicable entity types
    applicable_entity_type_slugs: List[str] = Field(
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
    deduplication_fields: List[str] = Field(default_factory=list, description="Fields for deduplication")

    # Time-based configuration with enum validation
    is_time_based: bool = Field(default=False, description="Has date/time component")
    time_field_path: Optional[str] = Field(None, description="JSON path to date field")
    default_time_filter: TimeFilter = Field(
        default=TimeFilter.ALL,
        description="Default filter: all, future_only, past_only"
    )

    # AI extraction
    ai_extraction_enabled: bool = Field(default=True, description="Enable AI extraction")
    ai_extraction_prompt: Optional[str] = Field(None, description="AI prompt template")

    is_active: bool = Field(default=True, description="Whether facet type is active")


class FacetTypeCreate(FacetTypeBase):
    """Schema for creating a new facet type."""

    slug: Optional[str] = Field(None, description="URL-friendly slug (auto-generated if not provided)")

    @field_validator("slug", mode="before")
    @classmethod
    def generate_slug_if_empty(cls, v, info):
        if not v and "name" in info.data:
            return generate_slug(info.data["name"])
        return v


class FacetTypeUpdate(BaseModel):
    """Schema for updating a facet type."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    name_plural: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    value_type: Optional[ValueType] = None
    value_schema: Optional[Dict[str, Any]] = None
    applicable_entity_type_slugs: Optional[List[str]] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    display_order: Optional[int] = None
    aggregation_method: Optional[AggregationMethod] = None
    deduplication_fields: Optional[List[str]] = None
    is_time_based: Optional[bool] = None
    time_field_path: Optional[str] = None
    default_time_filter: Optional[TimeFilter] = None
    ai_extraction_enabled: Optional[bool] = None
    ai_extraction_prompt: Optional[str] = None
    is_active: Optional[bool] = None


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
    description: Optional[str] = None
    value_type: str = Field(description="Type: text, structured, list, reference, etc.")
    value_schema: Optional[Dict[str, Any]] = None
    applicable_entity_type_slugs: List[str] = Field(default_factory=list)
    icon: str = Field(default="mdi-tag")
    color: str = Field(default="#607D8B")
    display_order: int = Field(default=0)
    aggregation_method: str = Field(default="dedupe")
    deduplication_fields: List[str] = Field(default_factory=list)
    is_time_based: bool = Field(default=False)
    time_field_path: Optional[str] = None
    default_time_filter: str = Field(default="all")
    ai_extraction_enabled: bool = Field(default=True)
    ai_extraction_prompt: Optional[str] = None
    is_active: bool = Field(default=True)

    # Computed fields
    value_count: int = Field(default=0, description="Number of facet values of this type")

    model_config = {"from_attributes": True}


class FacetTypeListResponse(BaseModel):
    """Schema for facet type list response."""

    items: List[FacetTypeResponse]
    total: int
    page: int
    per_page: int
    pages: int


class FacetTypeSchemaGenerateRequest(BaseModel):
    """Request schema for AI-powered facet type schema generation."""

    name: str = Field(..., min_length=1, description="Name of the facet type")
    name_plural: Optional[str] = Field(None, description="Plural form of the name")
    description: Optional[str] = Field(None, description="Description of what this facet captures")
    applicable_entity_types: List[str] = Field(
        default_factory=list,
        description="Entity type names this facet applies to (e.g. 'Gemeinde', 'Person')",
    )


class FacetTypeSchemaGenerateResponse(BaseModel):
    """Response schema for AI-generated facet type configuration."""

    value_type: str = Field(default="structured", description="Recommended value type")
    value_schema: Optional[Dict[str, Any]] = Field(None, description="Generated JSON Schema")
    deduplication_fields: List[str] = Field(default_factory=list, description="Suggested deduplication fields")
    is_time_based: bool = Field(default=False, description="Whether facet has time component")
    time_field_path: Optional[str] = Field(None, description="JSON path to date field if time-based")
    ai_extraction_prompt: Optional[str] = Field(None, description="Generated AI extraction prompt")
    icon: Optional[str] = Field(None, description="Suggested icon")
    color: Optional[str] = Field(None, description="Suggested color")
