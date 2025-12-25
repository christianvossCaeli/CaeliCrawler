"""Notification models for the notification system."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.notification_rule import NotificationRule
    from app.models.user import User


class NotificationChannel(str, enum.Enum):
    """Supported notification channels."""

    EMAIL = "EMAIL"
    WEBHOOK = "WEBHOOK"
    IN_APP = "IN_APP"
    MS_TEAMS = "MS_TEAMS"  # For future extension


class NotificationEventType(str, enum.Enum):
    """Types of events that can trigger notifications."""

    # Document events
    NEW_DOCUMENT = "NEW_DOCUMENT"
    DOCUMENT_CHANGED = "DOCUMENT_CHANGED"
    DOCUMENT_REMOVED = "DOCUMENT_REMOVED"

    # Crawl events
    CRAWL_STARTED = "CRAWL_STARTED"
    CRAWL_COMPLETED = "CRAWL_COMPLETED"
    CRAWL_FAILED = "CRAWL_FAILED"

    # AI events
    AI_ANALYSIS_COMPLETED = "AI_ANALYSIS_COMPLETED"
    HIGH_CONFIDENCE_RESULT = "HIGH_CONFIDENCE_RESULT"

    # Data source events
    SOURCE_STATUS_CHANGED = "SOURCE_STATUS_CHANGED"
    SOURCE_ERROR = "SOURCE_ERROR"

    # Summary events
    SUMMARY_UPDATED = "SUMMARY_UPDATED"
    SUMMARY_RELEVANT_CHANGES = "SUMMARY_RELEVANT_CHANGES"


class NotificationStatus(str, enum.Enum):
    """Status of a notification."""

    PENDING = "PENDING"
    QUEUED = "QUEUED"
    SENT = "SENT"
    FAILED = "FAILED"
    READ = "READ"  # For In-App notifications


class Notification(Base):
    """Notification history and queue."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # References
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notification_rules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Event info
    event_type: Mapped[NotificationEventType] = mapped_column(
        Enum(NotificationEventType, name="notification_event_type"),
        nullable=False,
        index=True,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel"),
        nullable=False,
    )

    # Content
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Related entities (for navigation)
    related_entity_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )  # "document", "crawl_job", "data_source", etc.
    related_entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Payload (original event data)
    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Status
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status"),
        default=NotificationStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Delivery info
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Email-specific
    email_recipient: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    email_message_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="notifications",
    )
    rule: Mapped[Optional["NotificationRule"]] = relationship(
        "NotificationRule",
        back_populates="notifications",
    )

    def __repr__(self) -> str:
        return f"<Notification {self.id} [{self.event_type}] -> {self.channel}>"
