"""Dashboard schemas for API validation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# Widget configuration schemas
class WidgetPosition(BaseModel):
    """Position of a widget in the grid."""

    x: int = Field(ge=0, le=3, description="Column position (0-3)")
    y: int = Field(ge=0, description="Row position")
    w: int = Field(ge=1, le=4, default=1, description="Width in columns (1-4)")
    h: int = Field(ge=1, le=4, default=1, description="Height in rows (1-4)")


class WidgetConfig(BaseModel):
    """Configuration for a single widget."""

    id: str = Field(..., min_length=1, max_length=100, description="Unique widget ID")
    type: str = Field(..., min_length=1, max_length=50, description="Widget type")
    enabled: bool = Field(default=True, description="Whether widget is shown")
    position: WidgetPosition = Field(default_factory=WidgetPosition)
    config: dict[str, Any] = Field(
        default_factory=dict, description="Widget-specific configuration (refresh interval, etc.)"
    )


class DashboardPreferencesUpdate(BaseModel):
    """Request body for updating dashboard preferences."""

    widgets: list[WidgetConfig] = Field(..., min_length=0, max_length=20, description="List of widget configurations")


class DashboardPreferencesResponse(BaseModel):
    """Response containing dashboard preferences."""

    widgets: list[WidgetConfig] = Field(default_factory=list)
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# Dashboard statistics schemas
class EntityStats(BaseModel):
    """Entity statistics for dashboard."""

    total: int = Field(description="Total number of entities")
    by_type: dict[str, int] = Field(default_factory=dict, description="Entity count by type")
    active: int = Field(description="Number of active entities")
    inactive: int = Field(description="Number of inactive entities")


class FacetStats(BaseModel):
    """Facet value statistics for dashboard."""

    total: int = Field(description="Total number of facet values")
    verified: int = Field(description="Number of verified facet values")
    verification_rate: float = Field(ge=0, le=100, description="Percentage of verified facet values")
    by_type: dict[str, int] = Field(default_factory=dict, description="Facet count by type")


class DocumentStats(BaseModel):
    """Document processing statistics for dashboard."""

    total: int = Field(description="Total number of documents")
    by_status: dict[str, int] = Field(default_factory=dict, description="Document count by processing status")
    processing_rate: float = Field(ge=0, le=100, description="Percentage of successfully processed documents")


class CrawlerStats(BaseModel):
    """Crawler statistics for dashboard."""

    total_jobs: int = Field(description="Total number of crawl jobs")
    running_jobs: int = Field(description="Currently running jobs")
    completed_jobs: int = Field(description="Completed jobs")
    failed_jobs: int = Field(description="Failed jobs")
    total_documents: int = Field(description="Total crawled documents")
    avg_duration_seconds: float | None = Field(None, description="Average job duration in seconds")


class AITaskStats(BaseModel):
    """AI task statistics for dashboard."""

    total: int = Field(description="Total AI tasks")
    running: int = Field(description="Running tasks")
    completed: int = Field(description="Completed tasks")
    failed: int = Field(description="Failed tasks")
    avg_confidence: float | None = Field(None, description="Average confidence score")


class DashboardStatsResponse(BaseModel):
    """Complete dashboard statistics response."""

    entities: EntityStats
    facets: FacetStats
    documents: DocumentStats
    crawler: CrawlerStats
    ai_tasks: AITaskStats
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Activity feed schemas
class ActivityItem(BaseModel):
    """A single activity item for the feed."""

    id: UUID
    action: str = Field(description="Action type (CREATE, UPDATE, DELETE, etc.)")
    entity_type: str | None = Field(None, description="Type of entity affected")
    entity_id: UUID | None = Field(None, description="ID of affected entity")
    entity_name: str | None = Field(None, description="Name of affected entity")
    user_email: str | None = Field(None, description="User who performed the action")
    message: str = Field(description="Human-readable activity description")
    timestamp: datetime = Field(description="When the activity occurred")


class ActivityFeedResponse(BaseModel):
    """Response containing activity feed items."""

    items: list[ActivityItem] = Field(default_factory=list)
    total: int = Field(description="Total number of activities")
    has_more: bool = Field(default=False, description="Whether more items are available")


# Insights schemas
class InsightItem(BaseModel):
    """A single insight item."""

    type: str = Field(description="Insight type (new_entities, new_facets, etc.)")
    title: str = Field(description="Insight title")
    count: int = Field(description="Number of items")
    message: str = Field(description="Human-readable description")
    entity_type: str | None = Field(None, description="Related entity type if applicable")
    link: str | None = Field(None, description="Optional link to more details")


class InsightsResponse(BaseModel):
    """Response containing user insights."""

    items: list[InsightItem] = Field(default_factory=list)
    last_login: datetime | None = Field(None, description="User's last login time")
    period_days: int = Field(default=7, description="Period covered by insights")


# Chart data schemas
class ChartDataPoint(BaseModel):
    """A single data point for charts."""

    label: str = Field(description="Label (category name, date, etc.)")
    value: float = Field(description="Numeric value")
    color: str | None = Field(None, description="Optional color for this point")


class ChartDataResponse(BaseModel):
    """Response containing chart data."""

    chart_type: str = Field(description="Type of chart (pie, bar, line, etc.)")
    title: str = Field(description="Chart title")
    data: list[ChartDataPoint] = Field(default_factory=list)
    total: float | None = Field(None, description="Optional total value")
