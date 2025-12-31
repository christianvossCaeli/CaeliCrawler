"""Summary Execution model for execution history and cached data.

Tracks each execution of a custom summary including the cached widget data,
relevance scoring, and execution metadata.
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.custom_summary import CustomSummary


class ExecutionStatus(str, enum.Enum):
    """Status of a summary execution."""

    PENDING = "pending"  # Queued for execution
    RUNNING = "running"  # Currently executing
    COMPLETED = "completed"  # Successfully completed
    FAILED = "failed"  # Execution failed
    SKIPPED = "skipped"  # Skipped due to no relevant changes


class SummaryExecution(Base):
    """
    Execution history and cached data for custom summaries.

    Each execution stores:
    - Trigger information (who/what triggered it)
    - Cached widget data (for quick display)
    - Relevance scoring (if check_relevance enabled)
    - Timing and error information
    """

    __tablename__ = "summary_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    summary_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("custom_summaries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Status
    status: Mapped[ExecutionStatus] = mapped_column(
        Enum(ExecutionStatus, name="summary_execution_status_enum"),
        nullable=False,
        default=ExecutionStatus.PENDING,
        index=True,
    )

    # Trigger info
    triggered_by: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="manual",
        comment="Who triggered: manual, cron, crawl_event, api",
    )
    trigger_details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional trigger context (e.g., crawl_job_id)",
    )
    # Example:
    # {
    #     "crawl_job_id": "uuid",
    #     "category_id": "uuid",
    #     "source_name": "..."
    # }

    # Cached results (per widget)
    cached_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Cached data per widget for quick rendering",
    )
    # Example:
    # {
    #     "widget_uuid1": {
    #         "data": [...],
    #         "total": 18,
    #         "query_time_ms": 45
    #     },
    #     "widget_uuid2": {
    #         "data": [...],
    #         "total": 5,
    #         "query_time_ms": 23
    #     }
    # }

    # Relevance check results
    relevance_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="KI-calculated relevance score (0-1)",
    )
    relevance_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="KI explanation for relevance decision",
    )

    # Change detection
    data_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="SHA256 hash of cached_data for change detection",
    )
    has_changes: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether data changed compared to previous execution",
    )

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Execution start time",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Execution completion time",
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Total execution duration in milliseconds",
    )

    # Error handling
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if execution failed",
    )

    # Auto-expand suggestions
    expansion_suggestions: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Auto-expand widget suggestions discovered during execution",
    )
    # Example:
    # [
    #     {"widget_type": "stat_card", "title": "...", "reason": "...", "confidence": 0.8}
    # ]

    # Celery integration
    celery_task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Celery task ID for tracking",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    summary: Mapped["CustomSummary"] = relationship(
        "CustomSummary",
        back_populates="executions",
    )

    # Indexes
    __table_args__ = (
        Index("ix_summary_executions_summary_created", "summary_id", "created_at"),
        Index("ix_summary_executions_status_created", "status", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<SummaryExecution(id={self.id}, summary_id={self.summary_id}, status={self.status})>"
