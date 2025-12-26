"""Custom Summary schemas for API validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# --- Enums ---

class SummaryStatus(str, Enum):
    """Status of a custom summary."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class SummaryTriggerType(str, Enum):
    """Trigger type for summary updates."""

    MANUAL = "manual"
    CRON = "cron"
    CRAWL_CATEGORY = "crawl_category"
    CRAWL_PRESET = "crawl_preset"


class SummaryWidgetType(str, Enum):
    """Types of dashboard widgets (compatible with Chart.js)."""

    TABLE = "table"
    BAR_CHART = "bar_chart"
    LINE_CHART = "line_chart"
    PIE_CHART = "pie_chart"
    STAT_CARD = "stat_card"
    TEXT = "text"
    COMPARISON = "comparison"
    TIMELINE = "timeline"
    MAP = "map"
    CALENDAR = "calendar"


class ExecutionStatus(str, Enum):
    """Status of a summary execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# --- AI Interpreted Config Schemas ---

class InterpretedWidgetConfig(BaseModel):
    """Schema for AI-interpreted widget configuration."""

    widget_type: SummaryWidgetType
    title: str = Field(..., min_length=1, max_length=255)
    subtitle: Optional[str] = Field(None, max_length=500)
    entity_type: Optional[str] = Field(None, max_length=100)
    facet_types: List[str] = Field(default_factory=list, max_length=20)
    filters: Dict[str, Any] = Field(default_factory=dict)
    limit: Optional[int] = Field(None, ge=1, le=1000)
    sort_by: Optional[str] = Field(None, max_length=100)
    sort_order: Optional[str] = Field(None, pattern="^(asc|desc)$")
    aggregate: Optional[str] = Field(None, pattern="^(count|sum|avg|min|max)$")
    group_by: Optional[str] = Field(None, max_length=100)
    visualization: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class InterpretedConfig(BaseModel):
    """
    Schema for AI-interpreted configuration.

    Validates the structure returned by the AI interpreter to ensure
    it contains valid, expected values before creating database records.
    """

    theme: str = Field(..., min_length=1, max_length=255, description="Detected topic/theme")
    summary_name: str = Field(..., min_length=1, max_length=255, description="Suggested summary name")
    description: Optional[str] = Field(None, max_length=2000)
    widgets: List[InterpretedWidgetConfig] = Field(
        default_factory=list,
        max_length=20,
        description="Suggested widgets (max 20)"
    )
    suggested_schedule: Optional[str] = Field(
        None,
        max_length=50,
        pattern="^(hourly|daily|weekly|monthly|none)?$",
        description="Suggested update schedule"
    )
    entity_types_detected: List[str] = Field(
        default_factory=list,
        max_length=50,
        description="Entity types found in prompt"
    )
    facet_types_detected: List[str] = Field(
        default_factory=list,
        max_length=100,
        description="Facet types found in prompt"
    )
    confidence_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="AI confidence in interpretation"
    )

    model_config = {"extra": "ignore"}  # Allow extra fields from AI but ignore them


# --- Widget Schemas ---

class WidgetPosition(BaseModel):
    """Grid position for a widget."""

    x: int = Field(default=0, ge=0, description="X position in grid")
    y: int = Field(default=0, ge=0, description="Y position in grid")
    w: int = Field(default=2, ge=1, le=4, description="Width in grid columns")
    h: int = Field(default=2, ge=1, le=6, description="Height in grid rows")


class WidgetQueryConfig(BaseModel):
    """Query configuration for a widget."""

    entity_type: Optional[str] = Field(None, description="Entity type slug")
    facet_types: List[str] = Field(default_factory=list, description="Facet type slugs to include")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Filter conditions")
    sort_by: Optional[str] = Field(None, description="Field to sort by (prefix with - for desc)")
    sort_order: Optional[str] = Field(None, pattern="^(asc|desc)$", description="Sort order")
    limit: Optional[int] = Field(None, ge=1, le=1000, description="Result limit")
    aggregate: Optional[str] = Field(None, description="Aggregation: count, sum, avg")
    group_by: Optional[str] = Field(None, description="Field to group by")


class WidgetVisualizationConfig(BaseModel):
    """Visualization configuration for a widget (Chart.js compatible)."""

    # Table config
    columns: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Table column definitions: [{field, label, sortable, width}]"
    )
    show_pagination: bool = Field(default=True)
    rows_per_page: int = Field(default=10, ge=5, le=100)

    # Chart config (Chart.js)
    x_axis: Optional[Dict[str, Any]] = Field(None, description="X-axis config: {field, label}")
    y_axis: Optional[Dict[str, Any]] = Field(None, description="Y-axis config: {field, label}")
    color: Optional[str] = Field(None, description="Primary color (hex)")
    colors: Optional[List[str]] = Field(None, description="Color palette for multi-series")
    horizontal: bool = Field(default=False, description="Horizontal bar chart")
    stacked: bool = Field(default=False, description="Stacked chart")
    show_legend: bool = Field(default=True)
    show_labels: bool = Field(default=False, description="Show data labels")

    # Stat card config
    trend: Optional[str] = Field(None, pattern="^(up|down|neutral)$")
    trend_value: Optional[str] = Field(None, description="Trend display value")
    format: Optional[str] = Field(None, description="Number format")

    # Text widget
    content: Optional[str] = Field(None, description="Markdown content for text widget")


# Grid configuration constants
GRID_COLUMNS = 4
MAX_GRID_ROWS = 100  # Reasonable limit to prevent abuse


class SummaryWidgetCreate(BaseModel):
    """Schema for creating a widget."""

    widget_type: SummaryWidgetType
    title: str = Field(..., min_length=1, max_length=255)
    subtitle: Optional[str] = Field(None, max_length=500)
    position_x: int = Field(default=0, ge=0, le=GRID_COLUMNS - 1)
    position_y: int = Field(default=0, ge=0, le=MAX_GRID_ROWS)
    width: int = Field(default=2, ge=1, le=GRID_COLUMNS)
    height: int = Field(default=2, ge=1, le=6)
    query_config: WidgetQueryConfig = Field(default_factory=WidgetQueryConfig)
    visualization_config: WidgetVisualizationConfig = Field(default_factory=WidgetVisualizationConfig)

    @model_validator(mode="after")
    def validate_position_within_grid(self) -> "SummaryWidgetCreate":
        """Ensure widget fits within the grid boundaries."""
        if self.position_x + self.width > GRID_COLUMNS:
            raise ValueError(
                f"Widget extends beyond grid boundary: position_x ({self.position_x}) + "
                f"width ({self.width}) = {self.position_x + self.width}, max is {GRID_COLUMNS}"
            )
        return self


class SummaryWidgetUpdate(BaseModel):
    """Schema for updating a widget."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    subtitle: Optional[str] = Field(None, max_length=500)
    position_x: Optional[int] = Field(None, ge=0, le=GRID_COLUMNS - 1)
    position_y: Optional[int] = Field(None, ge=0, le=MAX_GRID_ROWS)
    width: Optional[int] = Field(None, ge=1, le=GRID_COLUMNS)
    height: Optional[int] = Field(None, ge=1, le=6)
    query_config: Optional[Dict[str, Any]] = None
    visualization_config: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_position_within_grid(self) -> "SummaryWidgetUpdate":
        """
        Validate that position + width doesn't exceed grid when both are provided.
        Note: Full validation happens at API level with existing widget data.
        """
        if self.position_x is not None and self.width is not None:
            if self.position_x + self.width > GRID_COLUMNS:
                raise ValueError(
                    f"Widget extends beyond grid boundary: position_x ({self.position_x}) + "
                    f"width ({self.width}) = {self.position_x + self.width}, max is {GRID_COLUMNS}"
                )
        return self


class SummaryWidgetResponse(BaseModel):
    """Schema for widget response."""

    id: UUID
    widget_type: SummaryWidgetType
    title: str
    subtitle: Optional[str]
    position: WidgetPosition
    query_config: Dict[str, Any]
    visualization_config: Dict[str, Any]
    display_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_position(cls, widget: Any) -> "SummaryWidgetResponse":
        """Create response from ORM object with position transformation."""
        return cls(
            id=widget.id,
            widget_type=widget.widget_type,
            title=widget.title,
            subtitle=widget.subtitle,
            position=WidgetPosition(
                x=widget.position_x,
                y=widget.position_y,
                w=widget.width,
                h=widget.height,
            ),
            query_config=widget.query_config,
            visualization_config=widget.visualization_config,
            display_order=widget.display_order,
            created_at=widget.created_at,
            updated_at=widget.updated_at,
        )


# --- Execution Schemas ---

class SummaryExecutionResponse(BaseModel):
    """Schema for execution response."""

    id: UUID
    status: ExecutionStatus
    triggered_by: str
    trigger_details: Optional[Dict[str, Any]]
    has_changes: bool
    relevance_score: Optional[float]
    relevance_reason: Optional[str]
    duration_ms: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class SummaryExecutionDetailResponse(SummaryExecutionResponse):
    """Schema for execution detail with cached data."""

    cached_data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


# --- Share Schemas ---

class SummaryShareCreate(BaseModel):
    """Schema for creating a share link."""

    password: Optional[str] = Field(None, min_length=4, max_length=50, description="Optional access password")
    expires_days: Optional[int] = Field(None, ge=1, le=365, description="Days until expiration")
    allow_export: bool = Field(default=False, description="Allow recipient to export")


class SummaryShareResponse(BaseModel):
    """Schema for share link response."""

    id: UUID
    share_token: str
    share_url: str
    has_password: bool
    expires_at: Optional[datetime]
    allow_export: bool
    view_count: int
    last_viewed_at: Optional[datetime]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SharedSummaryAccessRequest(BaseModel):
    """Request to access a shared summary."""

    password: Optional[str] = Field(None, description="Access password if required")


class SharedSummaryResponse(BaseModel):
    """Response for shared summary access."""

    summary_name: str
    summary_description: Optional[str]
    widgets: List[SummaryWidgetResponse]
    data: Dict[str, Any] = Field(description="Cached data per widget")
    last_updated: Optional[datetime]
    allow_export: bool


# --- Summary Schemas ---

class SummaryCreateFromPrompt(BaseModel):
    """Schema for creating a summary from natural language prompt."""

    prompt: str = Field(..., min_length=10, max_length=2000, description="Natural language description")
    name: Optional[str] = Field(None, max_length=255, description="Optional custom name (KI suggests if not provided)")


class SummaryCreate(BaseModel):
    """Schema for manual summary creation."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    original_prompt: str = Field(..., min_length=10, max_length=2000)
    interpreted_config: Dict[str, Any] = Field(default_factory=dict)
    layout_config: Dict[str, Any] = Field(default_factory=dict)
    trigger_type: SummaryTriggerType = Field(default=SummaryTriggerType.MANUAL)
    schedule_cron: Optional[str] = Field(None, max_length=100)
    trigger_category_id: Optional[UUID] = None
    trigger_preset_id: Optional[UUID] = None


class SummaryUpdate(BaseModel):
    """Schema for updating a summary."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    layout_config: Optional[Dict[str, Any]] = None
    trigger_type: Optional[SummaryTriggerType] = None
    schedule_cron: Optional[str] = Field(None, max_length=100)
    trigger_category_id: Optional[UUID] = None
    trigger_preset_id: Optional[UUID] = None
    schedule_enabled: Optional[bool] = None
    check_relevance: Optional[bool] = None
    relevance_threshold: Optional[float] = Field(None, ge=0, le=1)
    auto_expand: Optional[bool] = None
    is_favorite: Optional[bool] = None
    status: Optional[SummaryStatus] = None


class SummaryResponse(BaseModel):
    """Schema for summary response."""

    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    original_prompt: str
    interpreted_config: Dict[str, Any]
    layout_config: Dict[str, Any]
    status: SummaryStatus
    trigger_type: SummaryTriggerType
    schedule_cron: Optional[str]
    trigger_category_id: Optional[UUID]
    trigger_preset_id: Optional[UUID]
    schedule_enabled: bool
    next_run_at: Optional[datetime]
    check_relevance: bool
    relevance_threshold: float
    auto_expand: bool
    is_favorite: bool
    execution_count: int
    last_executed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SummaryDetailResponse(SummaryResponse):
    """Schema for summary detail with widgets and last execution."""

    widgets: List[SummaryWidgetResponse] = Field(default_factory=list)
    last_execution: Optional[SummaryExecutionDetailResponse] = None
    # Cache expiration metadata
    cache_expired: Optional[bool] = Field(
        None,
        description="True if cached data is older than TTL (default: 24h)"
    )
    cache_age_hours: Optional[float] = Field(
        None,
        description="Age of cached data in hours"
    )


class SummaryListResponse(BaseModel):
    """Schema for summary list response."""

    items: List[SummaryResponse]
    total: int
    page: int
    per_page: int
    pages: int


class SummaryFromPromptResponse(BaseModel):
    """Response after creating summary from prompt."""

    id: UUID
    name: str
    interpretation: Dict[str, Any] = Field(description="KI-interpreted configuration")
    widgets_created: int
    message: str


class SummaryExecuteRequest(BaseModel):
    """Request to execute a summary."""

    force: bool = Field(default=False, description="Skip relevance check and force execution")


class SummaryExecuteResponse(BaseModel):
    """Response from executing a summary."""

    execution_id: UUID
    status: ExecutionStatus
    has_changes: bool
    cached_data: Optional[Dict[str, Any]] = Field(None, description="Data if completed")
    message: str


class SummaryFavoriteToggleResponse(BaseModel):
    """Response for favorite toggle."""

    id: UUID
    is_favorite: bool
    message: str


# --- Schedule Presets (für UI) ---

class SummarySchedulePreset(BaseModel):
    """Common schedule presets for UI convenience."""

    label: str
    cron: str
    description: str


# Predefined schedule options for frontend
SCHEDULE_PRESETS: List[SummarySchedulePreset] = [
    SummarySchedulePreset(label="hourly", cron="0 * * * *", description="Every hour"),
    SummarySchedulePreset(label="daily_morning", cron="0 8 * * *", description="Daily at 8:00 AM"),
    SummarySchedulePreset(label="daily_evening", cron="0 18 * * *", description="Daily at 6:00 PM"),
    SummarySchedulePreset(label="weekly_monday", cron="0 9 * * 1", description="Weekly on Monday at 9:00 AM"),
    SummarySchedulePreset(label="monthly", cron="0 0 1 * *", description="Monthly on the 1st"),
]


# --- Check Updates Schemas ---

class CheckUpdatesStatus(str, Enum):
    """Status of a check-updates task."""

    PENDING = "pending"
    CRAWLING = "crawling"
    UPDATING = "updating"
    COMPLETED = "completed"
    FAILED = "failed"


class SummaryCheckUpdatesResponse(BaseModel):
    """Response from starting a check-updates task."""

    task_id: str = Field(..., description="Celery task ID for progress polling")
    source_count: int = Field(..., description="Number of sources to check")
    message: str = Field(..., description="Human-readable status message")


class CheckUpdatesProgressResponse(BaseModel):
    """Response for check-updates progress polling."""

    status: CheckUpdatesStatus = Field(..., description="Current task status")
    total_sources: int = Field(..., description="Total number of sources to crawl")
    completed_sources: int = Field(default=0, description="Number of sources already crawled")
    current_source: Optional[str] = Field(None, description="Name of currently crawling source")
    message: str = Field(..., description="Human-readable progress message")
    error: Optional[str] = Field(None, description="Error message if failed")
