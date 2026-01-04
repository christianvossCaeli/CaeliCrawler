"""LLM Usage tracking models for analytics.

This module provides models for tracking LLM API usage across all providers
(Azure OpenAI, OpenAI, Anthropic Claude) with detailed metrics for cost analysis,
performance monitoring, and usage patterns.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LLMProvider(str, Enum):
    """LLM Provider types."""

    AZURE_OPENAI = "AZURE_OPENAI"
    OPENAI = "OPENAI"
    ANTHROPIC = "ANTHROPIC"


class LLMTaskType(str, Enum):
    """Task types for LLM calls."""

    SUMMARIZE = "SUMMARIZE"
    EXTRACT = "EXTRACT"
    CLASSIFY = "CLASSIFY"
    EMBEDDING = "EMBEDDING"
    VISION = "VISION"
    CHAT = "CHAT"
    PLAN_MODE = "PLAN_MODE"
    DISCOVERY = "DISCOVERY"
    ENTITY_ANALYSIS = "ENTITY_ANALYSIS"
    ATTACHMENT_ANALYSIS = "ATTACHMENT_ANALYSIS"
    RELEVANCE_CHECK = "RELEVANCE_CHECK"
    CUSTOM = "CUSTOM"


class LLMUsageRecord(Base):
    """
    Track individual LLM API calls for analytics.

    Stores detailed usage metrics for cost tracking,
    performance analysis, and usage patterns.
    """

    __tablename__ = "llm_usage_records"
    __table_args__ = (
        Index("ix_llm_usage_created_at", "created_at"),
        Index("ix_llm_usage_provider_model", "provider", "model"),
        Index("ix_llm_usage_task_type", "task_type"),
        Index("ix_llm_usage_category_id", "category_id"),
        # Note: date_trunc index removed - requires IMMUTABLE function wrapper
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Provider & Model
    provider: Mapped[LLMProvider] = mapped_column(
        SQLEnum(LLMProvider, name="llm_provider", create_constraint=True),
        nullable=False,
        index=True,
    )
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Model name/deployment (e.g., gpt-4.1-mini, claude-opus-4-5)",
    )

    # Task context
    task_type: Mapped[LLMTaskType] = mapped_column(
        SQLEnum(LLMTaskType, name="llm_task_type", create_constraint=True),
        nullable=False,
        index=True,
    )
    task_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Human-readable task name for detailed tracking",
    )

    # Token usage
    prompt_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Input tokens consumed",
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Output tokens generated",
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total tokens (prompt + completion)",
    )

    # Cost calculation (in USD cents to avoid floating point issues)
    estimated_cost_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Estimated cost in USD cents",
    )

    # Performance metrics
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Request duration in milliseconds",
    )

    # Request context
    request_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Unique request identifier for tracing",
    )

    # Related entities (optional, for drill-down analytics)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Additional metadata
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",  # Keep DB column name as 'metadata'
        JSONB,
        default=dict,
        nullable=False,
        comment="Additional context (source_id, batch_size, etc.)",
    )

    # Error tracking
    is_error: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether the request failed",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<LLMUsageRecord(id={self.id}, provider={self.provider}, "
            f"model={self.model}, tokens={self.total_tokens})>"
        )


class LLMUsageMonthlyAggregate(Base):
    """
    Monthly aggregated LLM usage data.

    Used for long-term storage and efficient querying of historical data.
    Detail records older than 90 days are aggregated into this table.
    """

    __tablename__ = "llm_usage_monthly_aggregates"
    __table_args__ = (
        Index(
            "ix_llm_usage_monthly_year_month",
            "year_month",
        ),
        Index(
            "ix_llm_usage_monthly_provider_model",
            "provider",
            "model",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Time period
    year_month: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        comment="Year-month in format YYYY-MM",
    )

    # Grouping dimensions
    provider: Mapped[LLMProvider] = mapped_column(
        SQLEnum(LLMProvider, name="llm_provider", create_constraint=False),
        nullable=False,
    )
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    task_type: Mapped[LLMTaskType] = mapped_column(
        SQLEnum(LLMTaskType, name="llm_task_type", create_constraint=False),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Aggregated metrics
    request_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    total_prompt_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    total_completion_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    total_cost_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    error_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    avg_duration_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<LLMUsageMonthlyAggregate(year_month={self.year_month}, "
            f"provider={self.provider}, model={self.model}, "
            f"tokens={self.total_tokens})>"
        )
