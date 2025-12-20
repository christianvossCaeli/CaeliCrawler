"""Reminder models for the assistant reminder system."""

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.entity import Entity
    from app.models.user import User


class ReminderRepeat(str, enum.Enum):
    """Repeat intervals for reminders."""

    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ReminderStatus(str, enum.Enum):
    """Status of a reminder."""

    PENDING = "pending"
    SENT = "sent"
    DISMISSED = "dismissed"
    CANCELLED = "cancelled"


class Reminder(Base):
    """Assistant reminders for scheduled notifications."""

    __tablename__ = "assistant_reminders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # User reference
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional entity reference
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    entity_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    entity_name: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    # Reminder content
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Scheduling
    remind_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    repeat: Mapped[ReminderRepeat] = mapped_column(
        Enum(ReminderRepeat, name="reminder_repeat"),
        default=ReminderRepeat.NONE,
        nullable=False,
    )

    # Status
    status: Mapped[ReminderStatus] = mapped_column(
        Enum(ReminderStatus, name="reminder_status"),
        default=ReminderStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Tracking
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    dismissed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Additional data
    extra_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
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
    user: Mapped["User"] = relationship(
        "User",
        back_populates="reminders",
    )
    entity: Mapped[Optional["Entity"]] = relationship(
        "Entity",
        back_populates="reminders",
    )

    def __repr__(self) -> str:
        return f"<Reminder {self.id} for user {self.user_id} at {self.remind_at}>"

    @property
    def is_due(self) -> bool:
        """Check if the reminder is due."""
        return (
            self.status == ReminderStatus.PENDING
            and self.remind_at <= datetime.now(timezone.utc)
        )

    def mark_sent(self) -> None:
        """Mark the reminder as sent."""
        self.status = ReminderStatus.SENT
        self.sent_at = datetime.now(timezone.utc)

    def dismiss(self) -> None:
        """Dismiss the reminder."""
        self.status = ReminderStatus.DISMISSED
        self.dismissed_at = datetime.now(timezone.utc)

    def cancel(self) -> None:
        """Cancel the reminder."""
        self.status = ReminderStatus.CANCELLED
