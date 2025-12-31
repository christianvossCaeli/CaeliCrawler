"""Notification rule model for user-defined notification rules."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.notification import NotificationChannel, NotificationEventType

if TYPE_CHECKING:
    from app.models.notification import Notification
    from app.models.user import User


class NotificationRule(Base):
    """User-defined notification rules."""

    __tablename__ = "notification_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Rule configuration
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Event type
    event_type: Mapped[NotificationEventType] = mapped_column(
        Enum(NotificationEventType, name="notification_event_type", create_type=False),
        nullable=False,
        index=True,
    )

    # Channel
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel", create_type=False),
        nullable=False,
    )

    # Filter conditions (JSONB for flexibility)
    conditions: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    # Example conditions:
    # {
    #     "category_ids": ["uuid1", "uuid2"],  # Only specific categories
    #     "source_ids": ["uuid1"],              # Only specific sources
    #     "min_confidence": 0.7,                # Minimum confidence score
    #     "keywords": ["Windkraft", "Solarpark"], # Keywords to match
    #     "location_filter": {"country": "DE", "admin_level_1": "NRW"}
    # }

    # Channel-specific configuration
    channel_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    # For EMAIL: {"email_address_ids": ["uuid1", "uuid2"], "include_primary": true}
    # For WEBHOOK: {"url": "https://...", "auth": {"type": "bearer", "token": "xxx"}, "headers": {}}
    # For IN_APP: {}
    # For MS_TEAMS: {"webhook_url": "https://..."}

    # Digest settings
    digest_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    digest_frequency: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )  # "hourly", "daily", "weekly"
    last_digest_sent: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Statistics
    trigger_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    last_triggered: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
        back_populates="notification_rules",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="rule",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<NotificationRule {self.name} [{self.event_type}]>"
