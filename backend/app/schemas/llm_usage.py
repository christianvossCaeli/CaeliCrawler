"""Schemas for LLM usage analytics API."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.llm_usage import LLMProvider, LLMTaskType

# === Response Models ===


class LLMUsageSummary(BaseModel):
    """Summary statistics for a time period."""

    total_requests: int = Field(description="Total number of API requests")
    total_tokens: int = Field(description="Total tokens consumed")
    total_prompt_tokens: int = Field(description="Total input tokens")
    total_completion_tokens: int = Field(description="Total output tokens")
    total_cost_cents: int = Field(description="Total estimated cost in USD cents")
    avg_duration_ms: float = Field(description="Average request duration in milliseconds")
    error_count: int = Field(description="Number of failed requests")
    error_rate: float = Field(description="Error rate as decimal (0-1)")


class LLMUsageByModel(BaseModel):
    """Usage breakdown by model."""

    model: str = Field(description="Model name/deployment")
    provider: LLMProvider = Field(description="LLM provider")
    request_count: int = Field(description="Number of requests")
    total_tokens: int = Field(description="Total tokens consumed")
    cost_cents: int = Field(description="Estimated cost in USD cents")
    avg_tokens_per_request: float = Field(description="Average tokens per request")


class LLMUsageByTask(BaseModel):
    """Usage breakdown by task type."""

    task_type: LLMTaskType = Field(description="Type of task")
    request_count: int = Field(description="Number of requests")
    total_tokens: int = Field(description="Total tokens consumed")
    cost_cents: int = Field(description="Estimated cost in USD cents")
    avg_duration_ms: float = Field(description="Average request duration")


class LLMUsageByCategory(BaseModel):
    """Usage breakdown by category."""

    category_id: UUID | None = Field(description="Category ID (null for uncategorized)")
    category_name: str | None = Field(description="Category name")
    request_count: int = Field(description="Number of requests")
    total_tokens: int = Field(description="Total tokens consumed")
    cost_cents: int = Field(description="Estimated cost in USD cents")


class LLMUsageTrend(BaseModel):
    """Daily usage trend data point."""

    day: date = Field(description="Date of the data point")
    request_count: int = Field(description="Number of requests")
    total_tokens: int = Field(description="Total tokens consumed")
    cost_cents: int = Field(description="Estimated cost in USD cents")
    error_count: int = Field(description="Number of errors")


class LLMUsageTopConsumer(BaseModel):
    """Top token consumers."""

    task_name: str = Field(description="Task name")
    task_type: LLMTaskType = Field(description="Task type")
    request_count: int = Field(description="Number of requests")
    total_tokens: int = Field(description="Total tokens consumed")
    cost_cents: int = Field(description="Estimated cost in USD cents")


class LLMUsageByUser(BaseModel):
    """Usage breakdown by user (API credential owner)."""

    user_id: UUID | None = Field(description="User ID (null for system/legacy usage)")
    user_email: str | None = Field(description="User email")
    user_name: str | None = Field(description="User full name")
    request_count: int = Field(description="Number of requests")
    total_tokens: int = Field(description="Total tokens consumed")
    prompt_tokens: int = Field(description="Total input tokens")
    completion_tokens: int = Field(description="Total output tokens")
    cost_cents: int = Field(description="Estimated cost in USD cents")
    models_used: list[str] = Field(default_factory=list, description="List of models used")
    has_credentials: bool = Field(default=False, description="Whether user has API credentials configured")


class LLMUsageAnalyticsResponse(BaseModel):
    """Complete analytics response."""

    period_start: datetime = Field(description="Start of the analysis period")
    period_end: datetime = Field(description="End of the analysis period")
    summary: LLMUsageSummary = Field(description="Summary statistics")
    by_model: list[LLMUsageByModel] = Field(description="Breakdown by model")
    by_task: list[LLMUsageByTask] = Field(description="Breakdown by task type")
    by_category: list[LLMUsageByCategory] = Field(default_factory=list, description="Breakdown by category")
    by_user: list[LLMUsageByUser] = Field(default_factory=list, description="Breakdown by user")
    daily_trend: list[LLMUsageTrend] = Field(description="Daily usage trend")
    top_consumers: list[LLMUsageTopConsumer] = Field(description="Top token-consuming tasks")


class LLMCostProjection(BaseModel):
    """Cost projection based on current usage."""

    current_month_cost_cents: int = Field(description="Current month cost so far")
    projected_month_cost_cents: int = Field(description="Projected cost by end of month")
    daily_avg_cost_cents: int = Field(description="Average daily cost")
    budget_warning: bool = Field(default=False, description="Whether any budget warning is active")
    budget_limit_cents: int | None = Field(default=None, description="Global budget limit if set")


# === Request/Query Models ===


class LLMUsageQueryParams(BaseModel):
    """Query parameters for analytics endpoints."""

    period: str = Field(
        default="7d",
        description="Time period: 24h, 7d, 30d, 90d",
        pattern="^(24h|7d|30d|90d)$",
    )
    provider: LLMProvider | None = Field(default=None, description="Filter by provider")
    model: str | None = Field(default=None, description="Filter by model")
    task_type: LLMTaskType | None = Field(default=None, description="Filter by task type")
    category_id: UUID | None = Field(default=None, description="Filter by category")


class LLMUsageExportParams(BaseModel):
    """Parameters for exporting usage data."""

    period: str = Field(default="30d", description="Time period to export")
    format: str = Field(
        default="csv",
        description="Export format: csv, json",
        pattern="^(csv|json)$",
    )
    include_metadata: bool = Field(default=False, description="Include additional metadata fields")
