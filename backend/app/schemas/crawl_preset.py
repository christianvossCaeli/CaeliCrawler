"""Crawl Preset schemas for API validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PresetStatus(str, Enum):
    """Status of a crawl preset."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class CrawlPresetFilters(BaseModel):
    """Filter configuration for a crawl preset."""

    # Category filter
    category_id: Optional[UUID] = Field(None, description="Filter by specific category")

    # Tag-based filters
    tags: Optional[List[str]] = Field(None, description="Filter by tags (e.g., ['nrw', 'bayern'])")

    # Entity-based filters
    entity_type: Optional[List[str]] = Field(None, description="Filter by entity type slugs (multi-select)")
    admin_level_1: Optional[str] = Field(None, description="Filter by admin level 1 (e.g., Bundesland) - deprecated, use tags")
    entity_filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Entity-specific filters including core_attributes operators"
    )

    # Standard source filters
    country: Optional[str] = Field(None, description="Filter by country code (DE, GB, etc.)")
    source_type: Optional[List[str]] = Field(None, description="Filter by source types (WEBSITE, OPARL_API, RSS, etc.)")
    status: Optional[str] = Field(None, description="Filter by source status (ACTIVE, PENDING, ERROR)")
    search: Optional[str] = Field(None, description="Filter by name or URL search term")

    # Limits
    limit: Optional[int] = Field(None, ge=1, le=10000, description="Maximum number of sources to crawl")


class CrawlPresetCreate(BaseModel):
    """Schema for creating a crawl preset."""

    name: str = Field(..., min_length=1, max_length=255, description="User-defined name for the preset")
    description: Optional[str] = Field(None, max_length=2000, description="Optional description")
    filters: CrawlPresetFilters = Field(default_factory=CrawlPresetFilters)

    # Scheduling options
    schedule_cron: Optional[str] = Field(
        None,
        max_length=100,
        description="Cron expression for scheduled execution (5 or 6 fields, e.g., '0 6 * * 1' for Monday 6 AM)"
    )
    schedule_enabled: bool = Field(default=False, description="Whether scheduled execution is enabled")


class CrawlPresetUpdate(BaseModel):
    """Schema for updating a crawl preset."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    filters: Optional[CrawlPresetFilters] = None
    schedule_cron: Optional[str] = Field(None, max_length=100)
    schedule_enabled: Optional[bool] = None
    is_favorite: Optional[bool] = None
    status: Optional[PresetStatus] = None


class CrawlPresetResponse(BaseModel):
    """Schema for crawl preset response."""

    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    filters: Dict[str, Any]
    filter_summary: str = Field(description="Human-readable summary of filters")

    # Scheduling
    schedule_cron: Optional[str]
    schedule_enabled: bool
    next_run_at: Optional[datetime]

    # Statistics
    usage_count: int
    last_used_at: Optional[datetime]
    last_scheduled_run_at: Optional[datetime]

    # Meta
    is_favorite: bool
    status: PresetStatus

    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CrawlPresetListResponse(BaseModel):
    """Schema for crawl preset list response."""

    items: List[CrawlPresetResponse]
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

    preset_id: UUID
    jobs_created: int
    job_ids: List[UUID]
    sources_matched: int
    message: str


class CrawlPresetFromFiltersRequest(BaseModel):
    """Request to create a preset from current filter selection."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    filters: CrawlPresetFilters
    schedule_cron: Optional[str] = None
    schedule_enabled: bool = False


class CrawlPresetSchedulePreset(BaseModel):
    """Common schedule presets for UI convenience."""

    label: str
    cron: str
    description: str


# Predefined schedule options for frontend
SCHEDULE_PRESETS: List[CrawlPresetSchedulePreset] = [
    CrawlPresetSchedulePreset(label="daily", cron="0 6 * * *", description="Daily at 6:00 AM"),
    CrawlPresetSchedulePreset(label="weekly_monday", cron="0 8 * * 1", description="Weekly on Monday at 8:00 AM"),
    CrawlPresetSchedulePreset(label="weekly_friday", cron="0 18 * * 5", description="Weekly on Friday at 6:00 PM"),
    CrawlPresetSchedulePreset(label="monthly", cron="0 0 1 * *", description="Monthly on the 1st at midnight"),
    CrawlPresetSchedulePreset(label="every_6_hours", cron="0 */6 * * *", description="Every 6 hours"),
]
