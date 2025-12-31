"""Device token model for push notification registration."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class DevicePlatform(str, enum.Enum):
    """Supported device platforms for push notifications."""

    IOS = "ios"
    ANDROID = "android"
    WEB = "web"


class DeviceToken(Base):
    """Device token for push notifications."""

    __tablename__ = "device_tokens"

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

    # Token data
    token: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
        index=True,
    )
    platform: Mapped[DevicePlatform] = mapped_column(
        Enum(DevicePlatform, name="device_platform"),
        nullable=False,
    )
    device_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )  # e.g., "iPhone 15 Pro", "iPad Air"

    # Device metadata
    app_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # e.g., "1.0.0"
    os_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # e.g., "iOS 18.1"

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Timestamps
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
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
        back_populates="device_tokens",
    )

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_device_tokens_user_active", "user_id", "is_active"),
        Index("ix_device_tokens_platform", "platform"),
    )

    def __repr__(self) -> str:
        return f"<DeviceToken {self.platform.value} ({self.device_name or 'Unknown'})>"
