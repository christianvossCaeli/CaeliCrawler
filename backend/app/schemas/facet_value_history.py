"""FacetValueHistory schemas for time-series data API validation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.facet_value import FacetValueSourceType

# =============================================================================
# Request Schemas
# =============================================================================


class HistoryDataPointCreate(BaseModel):
    """Schema for creating a single history data point."""

    recorded_at: datetime = Field(..., description="When this value was recorded/measured")
    value: float = Field(..., description="The numeric value")
    value_label: str | None = Field(None, description="Formatted value for display")
    track_key: str = Field(default="default", description="Track identifier")
    annotations: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (notes, trend, etc.)",
    )
    source_type: FacetValueSourceType = Field(
        default=FacetValueSourceType.MANUAL,
        description="How this value was created",
    )
    source_url: str | None = Field(None, description="Original URL where found")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")


class HistoryDataPointUpdate(BaseModel):
    """Schema for updating a history data point."""

    value: float | None = Field(None, description="The numeric value")
    value_label: str | None = Field(None, description="Formatted value")
    annotations: dict[str, Any] | None = Field(None, description="Metadata")
    human_verified: bool | None = Field(None, description="Mark as verified")


class HistoryBulkImport(BaseModel):
    """Schema for bulk importing history data points."""

    data_points: list[HistoryDataPointCreate] = Field(..., description="List of data points to import")
    skip_duplicates: bool = Field(default=True, description="Skip existing data points")


# =============================================================================
# Response Schemas
# =============================================================================


class HistoryDataPointResponse(BaseModel):
    """Response schema for a single history data point."""

    id: UUID
    entity_id: UUID
    facet_type_id: UUID
    track_key: str
    recorded_at: datetime
    value: float
    value_label: str | None
    annotations: dict[str, Any]
    source_type: FacetValueSourceType
    source_document_id: UUID | None
    source_url: str | None
    confidence_score: float
    ai_model_used: str | None
    human_verified: bool
    verified_by: str | None
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HistoryTrackConfig(BaseModel):
    """Configuration for a history track from the FacetType schema."""

    key: str = Field(..., description="Track key")
    label: str = Field(..., description="Display label")
    color: str = Field(default="#1976D2", description="Line color")
    style: str = Field(default="solid", description="Line style: solid, dashed, dotted")


class HistoryTrackResponse(BaseModel):
    """Response for a single track with all its data points."""

    track_key: str
    label: str
    color: str
    style: str = "solid"
    data_points: list[HistoryDataPointResponse]
    point_count: int = Field(default=0, description="Number of data points")


class DateRange(BaseModel):
    """Date range for history data."""

    from_date: datetime | None = Field(None, description="Start of range")
    to_date: datetime | None = Field(None, description="End of range")


class HistoryStatistics(BaseModel):
    """Statistics calculated from history data."""

    total_points: int = Field(default=0, description="Total data points")
    min_value: float | None = Field(None, description="Minimum value")
    max_value: float | None = Field(None, description="Maximum value")
    avg_value: float | None = Field(None, description="Average value")
    latest_value: float | None = Field(None, description="Most recent value")
    oldest_value: float | None = Field(None, description="Oldest value")
    trend: str = Field(
        default="stable",
        description="Trend direction: up, down, stable",
    )
    change_percent: float | None = Field(None, description="Percentage change from oldest to latest")
    change_absolute: float | None = Field(None, description="Absolute change from oldest to latest")


class EntityHistoryResponse(BaseModel):
    """Complete history response for an entity+facet combination."""

    entity_id: UUID
    entity_name: str
    facet_type_id: UUID
    facet_type_slug: str
    facet_type_name: str

    # From FacetType value_schema
    unit: str = Field(default="", description="Unit of measurement")
    unit_label: str = Field(default="", description="Display label for unit")
    precision: int = Field(default=2, description="Decimal precision")

    # Data
    tracks: list[HistoryTrackResponse] = Field(default_factory=list, description="Data grouped by track")
    date_range: DateRange = Field(default_factory=DateRange, description="Actual data range")
    statistics: HistoryStatistics = Field(default_factory=HistoryStatistics, description="Calculated statistics")

    # Pagination info for large datasets
    total_points: int = Field(default=0, description="Total points across all tracks")


class HistoryBulkImportResponse(BaseModel):
    """Response for bulk import operation."""

    created: int = Field(default=0, description="Number of points created")
    skipped: int = Field(default=0, description="Number of duplicates skipped")
    errors: list[str] = Field(default_factory=list, description="Error messages")


# =============================================================================
# Aggregation Schemas
# =============================================================================


class AggregatedDataPoint(BaseModel):
    """Aggregated data point for interval-based queries."""

    interval_start: datetime
    interval_end: datetime
    track_key: str
    value: float = Field(..., description="Aggregated value (avg, sum, etc.)")
    point_count: int = Field(default=1, description="Points in this interval")
    min_value: float | None = None
    max_value: float | None = None


class AggregatedHistoryResponse(BaseModel):
    """Response for aggregated history data."""

    entity_id: UUID
    facet_type_id: UUID
    interval: str = Field(..., description="Aggregation interval: day, week, month, year")
    method: str = Field(default="avg", description="Aggregation method: avg, sum, min, max")
    data: list[AggregatedDataPoint]
    date_range: DateRange


# =============================================================================
# Query Parameter Schemas
# =============================================================================


class HistoryQueryParams(BaseModel):
    """Query parameters for history endpoint."""

    from_date: datetime | None = Field(None, description="Start date filter")
    to_date: datetime | None = Field(None, description="End date filter")
    tracks: list[str] | None = Field(None, description="Filter by track keys")
    interval: str | None = Field(None, description="Aggregation interval: day, week, month, quarter, year")
    limit: int = Field(default=1000, ge=1, le=10000, description="Max points to return")
