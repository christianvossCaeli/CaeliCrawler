"""EntityAttachment model for storing files attached to entities."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.entity import Entity
    from app.models.user import User


class AttachmentAnalysisStatus(str, enum.Enum):
    """Analysis status for an attachment."""

    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EntityAttachment(Base):
    """
    File attachment linked directly to an entity.

    Supports images (PNG, JPEG, GIF, WebP) and PDFs.
    Files are stored on the local filesystem with metadata in the database.
    """

    __tablename__ = "entity_attachments"

    __table_args__ = (
        Index("ix_entity_attachments_entity_status", "entity_id", "analysis_status"),
        Index("ix_entity_attachments_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # File metadata
    filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Original filename",
    )
    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="MIME type (image/png, application/pdf, etc.)",
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="File size in bytes",
    )
    file_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Relative path to file in storage",
    )
    file_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="SHA256 hash for deduplication",
    )

    # User tracking
    uploaded_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Analysis
    analysis_status: Mapped[AttachmentAnalysisStatus] = mapped_column(
        Enum(AttachmentAnalysisStatus, name="attachment_analysis_status"),
        default=AttachmentAnalysisStatus.PENDING,
        nullable=False,
        index=True,
    )
    analysis_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="AI analysis result (description, extracted text, entities, etc.)",
    )
    analysis_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    analyzed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ai_model_used: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    # Optional description/notes
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="User-provided description or notes",
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

    # Relationships
    entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="attachments",
    )
    uploaded_by: Mapped[Optional["User"]] = relationship("User")

    @property
    def is_image(self) -> bool:
        """Check if attachment is an image."""
        return self.content_type.startswith("image/")

    @property
    def is_pdf(self) -> bool:
        """Check if attachment is a PDF."""
        return self.content_type == "application/pdf"

    @property
    def thumbnail_path(self) -> Optional[str]:
        """Get thumbnail path for images."""
        if self.is_image and "." in self.file_path:
            base, ext = self.file_path.rsplit(".", 1)
            return f"{base}_thumb.{ext}"
        return None

    def __repr__(self) -> str:
        return f"<EntityAttachment(id={self.id}, filename={self.filename}, entity={self.entity_id})>"
