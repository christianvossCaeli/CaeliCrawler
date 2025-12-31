"""AITask model for tracking AI extraction operations."""

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AITaskStatus(str, enum.Enum):
    """Status of an AI task."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AITaskType(str, enum.Enum):
    """Type of AI task."""

    DOCUMENT_ANALYSIS = "DOCUMENT_ANALYSIS"
    PYSIS_EXTRACTION = "PYSIS_EXTRACTION"
    PYSIS_TO_FACETS = "PYSIS_TO_FACETS"
    BATCH_ANALYSIS = "BATCH_ANALYSIS"
    ENTITY_DATA_ANALYSIS = "ENTITY_DATA_ANALYSIS"  # Analyse von Entity-Daten für Facet-Anreicherung
    ATTACHMENT_ANALYSIS = "ATTACHMENT_ANALYSIS"  # Analyse von User-Attachments (Bilder, PDFs)


class AITask(Base):
    """
    AI task tracking.

    Each AI operation creates a task record to track progress and results.
    """

    __tablename__ = "ai_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Task type
    task_type: Mapped[AITaskType] = mapped_column(
        Enum(AITaskType, name="ai_task_type"),
        nullable=False,
        index=True,
    )

    # Status
    status: Mapped[AITaskStatus] = mapped_column(
        Enum(AITaskStatus, name="ai_task_status"),
        default=AITaskStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Description
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable task name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed task description",
    )

    # Related entities (optional, depending on task type)
    process_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pysis_processes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="PySis process ID for extraction tasks",
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Document ID for analysis tasks",
    )

    # Timing
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Progress
    progress_current: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_item: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Currently processing item name",
    )

    # Results
    fields_extracted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    error_details: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Result data for preview/staging (e.g., proposed facet changes before approval)
    result_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Structured result data (e.g., preview of proposed changes)",
    )

    # Entity reference (for entity-based tasks)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Entity ID for entity-based tasks",
    )

    # Celery task ID for tracking
    celery_task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # Relationships
    process: Mapped[Optional["PySisProcess"]] = relationship(
        "PySisProcess",
        lazy="selectin",
    )

    @property
    def duration_seconds(self) -> float | None:
        """Calculate task duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.now(self.started_at.tzinfo) - self.started_at).total_seconds()
        return None

    @property
    def is_running(self) -> bool:
        """Check if task is currently running."""
        return self.status == AITaskStatus.RUNNING

    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if self.progress_total > 0:
            return (self.progress_current / self.progress_total) * 100
        return 0.0

    def __repr__(self) -> str:
        return f"<AITask(id={self.id}, type={self.task_type}, status={self.status})>"


# Import here to avoid circular imports
from app.models.pysis import PySisProcess  # noqa: E402
