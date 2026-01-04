"""LLM Budget configuration models.

This module provides models for managing budget limits and alerts
for LLM API usage across different scopes (global, category, task type).
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BudgetType(str, Enum):
    """Budget scope types."""

    GLOBAL = "GLOBAL"
    CATEGORY = "CATEGORY"
    TASK_TYPE = "TASK_TYPE"
    MODEL = "MODEL"
    USER = "USER"  # Per-user budget with hard blocking


class LimitIncreaseRequestStatus(str, Enum):
    """Status of limit increase requests."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"


class LLMBudgetConfig(Base):
    """
    Budget configuration for LLM usage.

    Allows setting monthly limits with warning thresholds
    and email notifications when budgets are exceeded.
    """

    __tablename__ = "llm_budget_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Budget identification
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable budget name (e.g., 'Monthly Global', 'Category: Wind Energy')",
    )

    # Budget scope
    budget_type: Mapped[BudgetType] = mapped_column(
        SQLEnum(BudgetType, name="budget_type", create_constraint=True),
        nullable=False,
        index=True,
    )
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Reference ID for category/model-specific budgets",
    )
    reference_value: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Reference value for task_type or model budgets",
    )

    # Budget limits (in USD cents)
    monthly_limit_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Monthly budget limit in USD cents",
    )

    # Warning thresholds
    warning_threshold_percent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=80,
        comment="Percentage at which to send warning (e.g., 80 for 80%)",
    )
    critical_threshold_percent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=95,
        comment="Percentage at which to send critical alert (e.g., 95 for 95%)",
    )

    # Notification settings
    alert_emails: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
        comment="List of email addresses to notify on budget alerts",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    # Blocking behavior
    blocks_on_limit: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="If true, reaching 100% usage blocks LLM access for affected scope",
    )

    # Tracking last alert sent to avoid spam
    last_warning_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_critical_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Notes
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional description or notes",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<LLMBudgetConfig(id={self.id}, name={self.name}, "
            f"type={self.budget_type}, limit=${self.monthly_limit_cents / 100:.2f})>"
        )


class LLMBudgetAlert(Base):
    """
    History of budget alerts sent.

    Tracks when alerts were sent to avoid duplicate notifications
    and provide an audit trail.
    """

    __tablename__ = "llm_budget_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Related budget
    budget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("llm_budget_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Alert details
    alert_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Alert type: 'warning' or 'critical'",
    )
    threshold_percent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    current_usage_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    budget_limit_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    usage_percent: Mapped[float] = mapped_column(
        nullable=False,
    )

    # Notification details
    recipients: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
    )
    email_sent: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )
    email_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<LLMBudgetAlert(budget_id={self.budget_id}, "
            f"type={self.alert_type}, usage={self.usage_percent:.1f}%)>"
        )


class LLMBudgetLimitRequest(Base):
    """
    User requests for budget limit increases.

    When a user's budget is exhausted or nearing the limit,
    they can request an increase which must be approved by an admin.
    """

    __tablename__ = "llm_budget_limit_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Requesting user
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Related budget
    budget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("llm_budget_configs.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Request details
    requested_limit_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Requested new monthly limit in USD cents",
    )
    current_limit_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Limit at time of request in USD cents",
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="User's reason for requesting increase",
    )

    # Status
    status: Mapped[LimitIncreaseRequestStatus] = mapped_column(
        SQLEnum(
            LimitIncreaseRequestStatus,
            name="limit_increase_request_status",
            create_constraint=True,
        ),
        default=LimitIncreaseRequestStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Admin response
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    admin_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Admin notes on approval/denial",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<LLMBudgetLimitRequest(id={self.id}, user_id={self.user_id}, "
            f"status={self.status}, requested=${self.requested_limit_cents / 100:.2f})>"
        )
