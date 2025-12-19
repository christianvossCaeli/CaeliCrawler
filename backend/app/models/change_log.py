"""ChangeLog model for tracking detected changes."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.data_source import DataSource


class ChangeType(str, enum.Enum):
    """Type of detected change."""

    NEW_DOCUMENT = "NEW_DOCUMENT"
    CONTENT_CHANGED = "CONTENT_CHANGED"
    REMOVED = "REMOVED"
    METADATA_CHANGED = "METADATA_CHANGED"


class ChangeLog(Base):
    """
    Change detection log.

    Records all detected changes for tracking and notification purposes.
    Similar to ChangeTower functionality.
    """

    __tablename__ = "change_log"

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

    # Change details
    change_type: Mapped[ChangeType] = mapped_column(
        Enum(ChangeType, name="change_type"),
        nullable=False,
        index=True,
    )
    affected_url: Mapped[str] = mapped_column(Text, nullable=False)

    # Hash comparison
    old_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    new_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Additional details
    details: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Notification tracking
    notification_sent: Mapped[bool] = mapped_column(default=False, nullable=False)
    notification_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Timestamps
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    source: Mapped["DataSource"] = relationship(
        "DataSource",
        back_populates="change_logs",
    )

    def __repr__(self) -> str:
        return f"<ChangeLog(id={self.id}, type={self.change_type}, url={self.affected_url[:50]}...)>"
