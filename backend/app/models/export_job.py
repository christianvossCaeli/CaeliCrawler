"""Export job model for tracking async exports."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.database import Base


class ExportJob(Base):
    """Model for tracking async export jobs."""

    __tablename__ = "export_jobs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Job metadata
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    celery_task_id = Column(String(255), nullable=True, index=True)

    # Export configuration (stored as JSON)
    export_config = Column(JSON, nullable=False, default=dict)
    export_format = Column(String(20), nullable=False, default="json")

    # Status tracking
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
    )  # pending, processing, completed, failed, cancelled

    # Progress tracking
    total_records = Column(Integer, nullable=True)
    processed_records = Column(Integer, nullable=True, default=0)
    progress_percent = Column(Integer, nullable=True, default=0)
    progress_message = Column(String(255), nullable=True)

    # Result
    file_path = Column(Text, nullable=True)
    file_size = Column(Integer, nullable=True)
    download_url = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="export_jobs")

    def __repr__(self):
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
