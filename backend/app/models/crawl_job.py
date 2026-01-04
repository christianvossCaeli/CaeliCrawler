"""CrawlJob model for tracking crawl operations."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.data_source import DataSource
    from app.models.document import Document
    from app.models.user import User


class JobStatus(str, enum.Enum):
    """Status of a crawl job."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CrawlJob(Base):
    """
    Crawl job tracking.

    Each crawl operation creates a job record to track progress and results.
    """

    __tablename__ = "crawl_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # User who initiated this crawl (for API key resolution)
    # Nullable for backward compatibility with existing jobs
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Status
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"),
        default=JobStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Timing
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Statistics
    pages_crawled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    documents_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    documents_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    documents_new: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    documents_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Error tracking
    error_log: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Detailed statistics
    stats: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Celery task ID for tracking
    celery_task_id: Mapped[str | None] = mapped_column(
        nullable=True,
        index=True,
    )

    # Relationships
    source: Mapped["DataSource"] = relationship(
        "DataSource",
        back_populates="crawl_jobs",
    )
    category: Mapped["Category"] = relationship("Category")
    user: Mapped["User | None"] = relationship("User")
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="crawl_job",
    )

    @property
    def duration_seconds(self) -> float | None:
        """Calculate job duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_running(self) -> bool:
        """Check if job is currently running."""
        return self.status == JobStatus.RUNNING

    def __repr__(self) -> str:
        return f"<CrawlJob(id={self.id}, status={self.status})>"
