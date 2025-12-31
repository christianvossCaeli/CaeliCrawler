"""FacetValue schemas for API validation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# Import enum from model to avoid duplication
from app.models.facet_value import FacetValueSourceType


class FacetValueBase(BaseModel):
    """Base facet value schema with common fields."""

    value: dict[str, Any] = Field(..., description="Structured value")
    text_representation: str | None = Field(None, description="Text for search/display (auto-generated if not provided)")

    # Time-based fields
    event_date: datetime | None = Field(None, description="Date of the event/action")
    valid_from: datetime | None = Field(None, description="When this value becomes valid")
    valid_until: datetime | None = Field(None, description="When this value expires")

    # Source tracking
    source_type: FacetValueSourceType = Field(
        default=FacetValueSourceType.DOCUMENT,
        description="How this value was created"
    )
    source_url: str | None = Field(None, description="Original URL where this was found")

    # Entity reference (optional link to another entity)
    target_entity_id: UUID | None = Field(
        None,
        description="Optional reference to another Entity (e.g., Person for contact facet)"
    )

    # AI metadata
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="AI confidence")

    is_active: bool = Field(default=True, description="Whether value is active")


class FacetValueCreate(FacetValueBase):
    """Schema for creating a new facet value."""

    entity_id: UUID = Field(..., description="Entity ID")
    facet_type_id: UUID = Field(..., description="Facet type ID")
    category_id: UUID | None = Field(None, description="Category context")
    source_document_id: UUID | None = Field(None, description="Source document ID")
    ai_model_used: str | None = Field(None, description="AI model used for extraction")


class FacetValueUpdate(BaseModel):
    """Schema for updating a facet value."""

    value: dict[str, Any] | None = None
    text_representation: str | None = None
    event_date: datetime | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    source_url: str | None = None
    target_entity_id: UUID | None = None
    confidence_score: float | None = Field(None, ge=0.0, le=1.0)
    human_verified: bool | None = None
    human_corrections: dict[str, Any] | None = None
    is_active: bool | None = None


class FacetValueResponse(FacetValueBase):
    """Schema for facet value response."""

    id: UUID
    entity_id: UUID
    facet_type_id: UUID
    category_id: UUID | None
    source_document_id: UUID | None
    ai_model_used: str | None

    # Verification
    human_verified: bool
    verified_by: str | None
    verified_at: datetime | None
    human_corrections: dict[str, Any] | None

    # Occurrence tracking
    occurrence_count: int
    first_seen: datetime
    last_seen: datetime

    created_at: datetime
    updated_at: datetime

    # Nested info
    entity_name: str | None = Field(None, description="Entity name")
    facet_type_slug: str | None = Field(None, description="Facet type slug")
    facet_type_name: str | None = Field(None, description="Facet type name")
    category_name: str | None = Field(None, description="Category name")
    document_title: str | None = Field(None, description="Source document title")
    document_url: str | None = Field(None, description="Source document URL")

    # Target entity info (for referenced entities)
    target_entity_name: str | None = Field(None, description="Referenced entity name")
    target_entity_slug: str | None = Field(None, description="Referenced entity slug")
    target_entity_type_slug: str | None = Field(None, description="Referenced entity type slug")

    model_config = {"from_attributes": True}


class FacetValueListResponse(BaseModel):
    """Schema for facet value list response."""

    items: list[FacetValueResponse]
    total: int
    page: int
    per_page: int
    pages: int


class FacetValueAggregated(BaseModel):
    """Aggregated facet values grouped by type."""

    facet_type_id: UUID
    facet_type_slug: str
    facet_type_name: str
    facet_type_icon: str | None = None
    facet_type_color: str | None = None
    facet_type_value_type: str | None = Field(
        default=None, description="Value type (text, number, structured, history)"
    )
    value_schema: dict[str, Any] | None = Field(
        default=None, description="JSON Schema for the facet value structure including display config"
    )
    display_order: int = Field(default=0, description="Display order for sorting")
    value_count: int
    verified_count: int
    avg_confidence: float
    latest_value: datetime | None = None
    sample_values: list[dict[str, Any]] = Field(default_factory=list)


class EntityFacetsSummary(BaseModel):
    """Summary of facets for an entity."""

    entity_id: UUID
    entity_name: str
    entity_type_slug: str | None = None
    total_facet_values: int = Field(default=0, description="Total facet values")
    verified_count: int = Field(default=0, description="Number of verified values")
    facet_type_count: int = Field(default=0, description="Number of facet types with values")
    facets_by_type: list[FacetValueAggregated] = Field(
        default_factory=list,
        description="Facets aggregated by type",
    )


class FacetValueSearchResult(BaseModel):
    """Search result for a facet value with relevance ranking."""

    id: UUID
    entity_id: UUID
    entity_name: str
    facet_type_id: UUID
    facet_type_slug: str
    facet_type_name: str
    value: dict[str, Any]
    text_representation: str
    headline: str | None = Field(None, description="Highlighted search match")
    rank: float = Field(default=0.0, description="Search relevance score")
    confidence_score: float
    human_verified: bool
    source_type: str
    created_at: datetime


class FacetValueSearchResponse(BaseModel):
    """Response for facet value search."""

    items: list[FacetValueSearchResult]
    total: int
    page: int
    per_page: int
    pages: int
    query: str
    search_time_ms: float = Field(default=0.0, description="Search execution time")
