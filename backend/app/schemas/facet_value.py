"""FacetValue schemas for API validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# Import enum from model to avoid duplication
from app.models.facet_value import FacetValueSourceType


class FacetValueBase(BaseModel):
    """Base facet value schema with common fields."""

    value: Dict[str, Any] = Field(..., description="Structured value")
    text_representation: Optional[str] = Field(None, description="Text for search/display (auto-generated if not provided)")

    # Time-based fields
    event_date: Optional[datetime] = Field(None, description="Date of the event/action")
    valid_from: Optional[datetime] = Field(None, description="When this value becomes valid")
    valid_until: Optional[datetime] = Field(None, description="When this value expires")

    # Source tracking
    source_type: FacetValueSourceType = Field(
        default=FacetValueSourceType.DOCUMENT,
        description="How this value was created"
    )
    source_url: Optional[str] = Field(None, description="Original URL where this was found")

    # AI metadata
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="AI confidence")

    is_active: bool = Field(default=True, description="Whether value is active")


class FacetValueCreate(FacetValueBase):
    """Schema for creating a new facet value."""

    entity_id: UUID = Field(..., description="Entity ID")
    facet_type_id: UUID = Field(..., description="Facet type ID")
    category_id: Optional[UUID] = Field(None, description="Category context")
    source_document_id: Optional[UUID] = Field(None, description="Source document ID")
    ai_model_used: Optional[str] = Field(None, description="AI model used for extraction")


class FacetValueUpdate(BaseModel):
    """Schema for updating a facet value."""

    value: Optional[Dict[str, Any]] = None
    text_representation: Optional[str] = None
    event_date: Optional[datetime] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    source_url: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    human_verified: Optional[bool] = None
    human_corrections: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class FacetValueResponse(FacetValueBase):
    """Schema for facet value response."""

    id: UUID
    entity_id: UUID
    facet_type_id: UUID
    category_id: Optional[UUID]
    source_document_id: Optional[UUID]
    ai_model_used: Optional[str]

    # Verification
    human_verified: bool
    verified_by: Optional[str]
    verified_at: Optional[datetime]
    human_corrections: Optional[Dict[str, Any]]

    # Occurrence tracking
    occurrence_count: int
    first_seen: datetime
    last_seen: datetime

    created_at: datetime
    updated_at: datetime

    # Nested info
    entity_name: Optional[str] = Field(None, description="Entity name")
    facet_type_slug: Optional[str] = Field(None, description="Facet type slug")
    facet_type_name: Optional[str] = Field(None, description="Facet type name")
    category_name: Optional[str] = Field(None, description="Category name")
    document_title: Optional[str] = Field(None, description="Source document title")
    document_url: Optional[str] = Field(None, description="Source document URL")

    model_config = {"from_attributes": True}


class FacetValueListResponse(BaseModel):
    """Schema for facet value list response."""

    items: List[FacetValueResponse]
    total: int
    page: int
    per_page: int
    pages: int


class FacetValueAggregated(BaseModel):
    """Aggregated facet values grouped by type."""

    facet_type_id: UUID
    facet_type_slug: str
    facet_type_name: str
    facet_type_icon: Optional[str] = None
    facet_type_color: Optional[str] = None
    display_order: int = Field(default=0, description="Display order for sorting")
    value_count: int
    verified_count: int
    avg_confidence: float
    latest_value: Optional[datetime] = None
    sample_values: List[Dict[str, Any]] = Field(default_factory=list)


class EntityFacetsSummary(BaseModel):
    """Summary of facets for an entity."""

    entity_id: UUID
    entity_name: str
    entity_type_slug: Optional[str] = None
    total_facet_values: int = Field(default=0, description="Total facet values")
    verified_count: int = Field(default=0, description="Number of verified values")
    facet_type_count: int = Field(default=0, description="Number of facet types with values")
    facets_by_type: List[FacetValueAggregated] = Field(
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
    value: Dict[str, Any]
    text_representation: str
    headline: Optional[str] = Field(None, description="Highlighted search match")
    rank: float = Field(default=0.0, description="Search relevance score")
    confidence_score: float
    human_verified: bool
    source_type: str
    created_at: datetime


class FacetValueSearchResponse(BaseModel):
    """Response for facet value search."""

    items: List[FacetValueSearchResult]
    total: int
    page: int
    per_page: int
    pages: int
    query: str
    search_time_ms: float = Field(default=0.0, description="Search execution time")
