"""Crawl Preset schemas for API validation."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CrawlPresetFilters(BaseModel):
    """Filter configuration for a crawl preset."""

    # Category filter (required - defines what analysis topic to use)
    category_id: UUID = Field(..., description="Category/analysis topic for the crawl (required)")

    # Entity-based selection (NEW)
    entity_ids: list[UUID] | None = Field(
        None, description="Explicit entity IDs to crawl sources for (fixed selection)"
    )
    entity_selection_mode: Literal["fixed", "dynamic"] | None = Field(
        None,
        description="Selection mode: 'fixed' stores entity IDs, 'dynamic' uses entity_filters at runtime",
    )

    # Tag-based filters
    tags: list[str] | None = Field(None, description="Filter by tags (e.g., ['nrw', 'bayern'])")

    # Entity-based filters
    entity_type: list[str] | None = Field(None, description="Filter by entity type slugs (multi-select)")
    admin_level_1: str | None = Field(
        None, description="Filter by admin level 1 (e.g., Bundesland) - deprecated, use tags"
    )
    entity_filters: dict[str, Any] | None = Field(
        None, description="Entity-specific filters including core_attributes operators"
    )

    # Standard source filters
    country: str | None = Field(None, description="Filter by country code (DE, GB, etc.)")
    source_type: list[str] | None = Field(None, description="Filter by source types (WEBSITE, OPARL_API, RSS, etc.)")
    status: str | None = Field(None, description="Filter by source status (ACTIVE, PENDING, ERROR)")
    search: str | None = Field(None, description="Filter by name or URL search term")

    # Limits
    limit: int | None = Field(None, ge=1, le=10000, description="Maximum number of sources to crawl")


class CrawlPresetCreate(BaseModel):
    """Schema for creating a crawl preset."""

    name: str = Field(..., min_length=1, max_length=255, description="User-defined name for the preset")
    description: str | None = Field(None, max_length=2000, description="Optional description")
    filters: CrawlPresetFilters = Field(..., description="Filter configuration (category_id required)")

    # Scheduling options
    schedule_cron: str | None = Field(
        None,
        max_length=100,
        description="Cron expression for scheduled execution (5 or 6 fields, e.g., '0 6 * * 1' for Monday 6 AM)",
    )
    schedule_enabled: bool = Field(default=False, description="Whether scheduled execution is enabled")


class CrawlPresetUpdate(BaseModel):
    """Schema for updating a crawl preset."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    filters: CrawlPresetFilters | None = None
    schedule_cron: str | None = Field(None, max_length=100)
    schedule_enabled: bool | None = None
    is_favorite: bool | None = None


class CrawlPresetResponse(BaseModel):
    """Schema for crawl preset response."""

    id: UUID
    user_id: UUID
    name: str
    description: str | None
    filters: dict[str, Any]
    filter_summary: str = Field(description="Human-readable summary of filters")

    # Scheduling
    schedule_cron: str | None
    schedule_enabled: bool
    next_run_at: datetime | None

    # Statistics
    usage_count: int
    last_used_at: datetime | None
    last_scheduled_run_at: datetime | None

    # Meta
    is_favorite: bool

    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CrawlPresetListResponse(BaseModel):
    """Schema for crawl preset list response."""

    items: list[CrawlPresetResponse]
    total: int
    page: int
    per_page: int
    pages: int


class CrawlPresetFavoriteToggleResponse(BaseModel):
    """Schema for favorite toggle response."""

    id: UUID
    is_favorite: bool
    message: str


class CrawlPresetExecuteRequest(BaseModel):
    """Request to execute a crawl preset."""

    force: bool = Field(default=False, description="Force crawl even if recently crawled")


class CrawlPresetExecuteResponse(BaseModel):
    """Response from executing a crawl preset."""

    preset_id: UUID | None = Field(None, description="Preset ID if executed from preset or newly created")
    jobs_created: int
    job_ids: list[UUID]
    sources_matched: int
    message: str


class CrawlPresetFromFiltersRequest(BaseModel):
    """Request to create a preset from current filter selection."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    filters: CrawlPresetFilters = Field(..., description="Filter configuration (category_id required)")
    schedule_cron: str | None = None
    schedule_enabled: bool = False


class CrawlPresetSchedulePreset(BaseModel):
    """Common schedule presets for UI convenience."""

    label: str
    cron: str
    description: str


# Predefined schedule options for frontend
SCHEDULE_PRESETS: list[CrawlPresetSchedulePreset] = [
    CrawlPresetSchedulePreset(label="daily", cron="0 6 * * *", description="Daily at 6:00 AM"),
    CrawlPresetSchedulePreset(label="weekly_monday", cron="0 8 * * 1", description="Weekly on Monday at 8:00 AM"),
    CrawlPresetSchedulePreset(label="weekly_friday", cron="0 18 * * 5", description="Weekly on Friday at 6:00 PM"),
    CrawlPresetSchedulePreset(label="monthly", cron="0 0 1 * *", description="Monthly on the 1st at midnight"),
    CrawlPresetSchedulePreset(label="every_6_hours", cron="0 */6 * * *", description="Every 6 hours"),
]


# Entity-based crawl schemas
class EntitySourcePreviewItem(BaseModel):
    """Single source item in entity crawl preview."""

    id: str
    name: str
    url: str


class EntityCrawlRequest(BaseModel):
    """Request to start a crawl for selected entities."""

    entity_ids: list[UUID] = Field(..., min_length=1, description="List of entity IDs to crawl sources for")
    category_id: UUID = Field(..., description="Category/analysis topic for the crawl")
    save_as_preset: bool = Field(default=False, description="Whether to save the selection as a preset")
    preset_name: str | None = Field(None, max_length=255, description="Name for the preset (required if save_as_preset)")
    selection_mode: Literal["fixed", "dynamic"] = Field(
        default="fixed", description="How to store the selection: 'fixed' saves IDs, 'dynamic' saves filters"
    )
    force: bool = Field(default=False, description="Force crawl even if recently crawled")


class EntityCrawlPreviewRequest(BaseModel):
    """Request to preview sources for entity selection."""

    entity_ids: list[UUID] = Field(..., min_length=1, description="List of entity IDs")
    category_id: UUID | None = Field(None, description="Optional category filter")


class EntityCrawlPreviewResponse(BaseModel):
    """Response for entity crawl preview."""

    entity_count: int = Field(description="Number of entities in selection")
    sources_count: int = Field(description="Number of DataSources found for entities")
    sources_preview: list[EntitySourcePreviewItem] = Field(description="Preview of matching sources (limited)")
    entities_without_sources: int = Field(description="Number of entities with no associated sources")
    has_more: bool = Field(description="Whether there are more sources than shown")
