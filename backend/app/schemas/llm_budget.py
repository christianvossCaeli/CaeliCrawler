"""Schemas for LLM budget management API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.llm_budget import BudgetType, LimitIncreaseRequestStatus

# === Response Models ===


class LLMBudgetConfigResponse(BaseModel):
    """Budget configuration response."""

    id: UUID
    name: str
    budget_type: BudgetType
    reference_id: UUID | None = None
    reference_value: str | None = None
    monthly_limit_cents: int
    warning_threshold_percent: int
    critical_threshold_percent: int
    alert_emails: list[str]
    is_active: bool
    blocks_on_limit: bool = False
    last_warning_sent_at: datetime | None = None
    last_critical_sent_at: datetime | None = None
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BudgetStatusResponse(BaseModel):
    """Current status of a budget."""

    budget_id: UUID
    budget_name: str
    budget_type: BudgetType
    monthly_limit_cents: int
    current_usage_cents: int
    usage_percent: float
    warning_threshold_percent: int
    critical_threshold_percent: int
    is_warning: bool = Field(description="Has reached warning threshold")
    is_critical: bool = Field(description="Has reached critical threshold")
    is_blocked: bool = Field(default=False, description="Usage >= 100% and budget blocks on limit")
    blocks_on_limit: bool = Field(default=False, description="Whether this budget blocks LLM access when exhausted")
    projected_month_end_cents: int = Field(description="Projected cost by end of month")


class BudgetAlertResponse(BaseModel):
    """Budget alert history item."""

    id: UUID
    budget_id: UUID
    alert_type: str
    threshold_percent: int
    current_usage_cents: int
    budget_limit_cents: int
    usage_percent: float
    email_sent: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BudgetStatusListResponse(BaseModel):
    """List of all budget statuses."""

    budgets: list[BudgetStatusResponse]
    any_warning: bool = Field(description="Any budget has reached warning threshold")
    any_critical: bool = Field(description="Any budget has reached critical threshold")
    any_blocked: bool = Field(default=False, description="Any blocking budget has been exhausted")


# === Request Models ===


class LLMBudgetConfigCreate(BaseModel):
    """Create a new budget configuration."""

    name: str = Field(min_length=1, max_length=255)
    budget_type: BudgetType
    reference_id: UUID | None = Field(
        default=None,
        description="Category ID for category-specific budgets",
    )
    reference_value: str | None = Field(
        default=None,
        max_length=100,
        description="Task type or model name for type-specific budgets",
    )
    monthly_limit_cents: int = Field(gt=0, description="Monthly limit in USD cents")
    warning_threshold_percent: int = Field(default=80, ge=1, le=99, description="Warning threshold percentage")
    critical_threshold_percent: int = Field(default=95, ge=1, le=100, description="Critical threshold percentage")
    alert_emails: list[str] = Field(default_factory=list, description="Email addresses for alerts")
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool = Field(default=True)
    blocks_on_limit: bool = Field(
        default=False,
        description="If true, reaching 100% usage blocks LLM access",
    )

    @field_validator("alert_emails")
    @classmethod
    def validate_emails(cls, v: list[str]) -> list[str]:
        """Validate email format."""
        import re

        email_pattern = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
        for email in v:
            if not email_pattern.match(email):
                raise ValueError(f"Invalid email format: {email}")
        return v

    @field_validator("critical_threshold_percent")
    @classmethod
    def validate_thresholds(cls, v: int, info) -> int:
        """Ensure critical threshold is greater than warning threshold."""
        warning = info.data.get("warning_threshold_percent", 80)
        if v <= warning:
            raise ValueError("Critical threshold must be greater than warning threshold")
        return v


class LLMBudgetConfigUpdate(BaseModel):
    """Update an existing budget configuration."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    monthly_limit_cents: int | None = Field(default=None, gt=0)
    warning_threshold_percent: int | None = Field(default=None, ge=1, le=99)
    critical_threshold_percent: int | None = Field(default=None, ge=1, le=100)
    alert_emails: list[str] | None = None
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None
    blocks_on_limit: bool | None = None

    @field_validator("alert_emails")
    @classmethod
    def validate_emails(cls, v: list[str] | None) -> list[str] | None:
        """Validate email format."""
        if v is None:
            return v
        import re

        email_pattern = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
        for email in v:
            if not email_pattern.match(email):
                raise ValueError(f"Invalid email format: {email}")
        return v


# === User Budget Status ===


class UserBudgetStatusResponse(BaseModel):
    """Current budget status for a user."""

    budget_id: UUID
    monthly_limit_cents: int
    current_usage_cents: int
    usage_percent: float
    is_warning: bool = Field(description="Usage >= 80%")
    is_critical: bool = Field(description="Usage >= 95%")
    is_blocked: bool = Field(description="Usage >= 100% - LLM functions blocked")


# === Limit Increase Requests ===


class LimitIncreaseRequestCreate(BaseModel):
    """Create a limit increase request."""

    requested_limit_cents: int = Field(gt=0, description="Requested new monthly limit in USD cents")
    reason: str = Field(min_length=10, max_length=1000, description="Reason for requesting increase")


class LimitIncreaseRequestResponse(BaseModel):
    """Limit increase request response."""

    id: UUID
    user_id: UUID
    budget_id: UUID
    requested_limit_cents: int
    current_limit_cents: int
    reason: str
    status: LimitIncreaseRequestStatus
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    admin_notes: str | None = None
    created_at: datetime
    user_email: str | None = Field(default=None, description="User email for admin view")

    model_config = {"from_attributes": True}


class LimitIncreaseRequestListResponse(BaseModel):
    """List of limit increase requests."""

    requests: list[LimitIncreaseRequestResponse]
    total: int
    pending_count: int


class AdminLimitRequestAction(BaseModel):
    """Admin action on a limit request."""

    notes: str | None = Field(default=None, max_length=1000, description="Admin notes on the decision")
