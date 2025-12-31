"""Export job model for tracking async exports."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class ExportJob(Base):
    """Model for tracking async export jobs."""

    __tablename__ = "export_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Job metadata
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    celery_task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # Export configuration (stored as JSON)
    export_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    export_format: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="json",
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="pending, processing, completed, failed, cancelled",
    )

    # Progress tracking
    total_records: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    processed_records: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=0,
    )
    progress_percent: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=0,
    )
    progress_message: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Result
    file_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    file_size: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    download_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="export_jobs",
    )

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_export_jobs_user_status", "user_id", "status"),
        Index("ix_export_jobs_created_status", "created_at", "status"),
    )

    def __repr__(self) -> str:
        return f"<ExportJob(id={self.id}, status={self.status}, format={self.export_format})>"

    @property
    def is_finished(self) -> bool:
        """Check if job is in a terminal state."""
        return self.status in ("completed", "failed", "cancelled")

    @property
    def is_downloadable(self) -> bool:
        """Check if export file is available for download."""
        return self.status == "completed" and self.file_path is not None

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "status": self.status,
            "export_format": self.export_format,
            "total_records": self.total_records,
            "processed_records": self.processed_records,
            "progress_percent": self.progress_percent,
            "progress_message": self.progress_message,
            "file_size": self.file_size,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "is_downloadable": self.is_downloadable,
        }
