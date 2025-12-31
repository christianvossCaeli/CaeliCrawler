"""User Session model for tracking active sessions and refresh tokens."""

import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class DeviceType(str, enum.Enum):
    """Device types for session tracking."""

    DESKTOP = "DESKTOP"
    MOBILE = "MOBILE"
    TABLET = "TABLET"
    API = "API"
    UNKNOWN = "UNKNOWN"


class UserSession(Base):
    """
    Track active user sessions with device info and refresh tokens.

    Features:
    - Refresh token storage (hashed)
    - Device tracking (user agent parsing)
    - Session revocation
    - Concurrent session management
    """

    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # User relationship
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Refresh token (hashed for security)
    refresh_token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    # Token family ID for rotation detection
    token_family: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        default=uuid.uuid4,
        comment="Token family for refresh token rotation detection",
    )

    # Session status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoke_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Device information
    device_type: Mapped[DeviceType] = mapped_column(
        Enum(DeviceType, name="device_type"),
        default=DeviceType.UNKNOWN,
        nullable=False,
    )
    device_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Parsed device name (e.g., 'Chrome on Windows')",
    )
    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="Supports IPv6",
    )

    # Location (optional, from IP)
    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Approximate location from IP",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="sessions",
        lazy="selectin",
    )

    # Indexes
    __table_args__ = (
        Index("ix_user_sessions_user_active", "user_id", "is_active"),
        Index("ix_user_sessions_expires", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<UserSession {self.device_name or 'Unknown'} for user {self.user_id}>"

    @property
    def is_expired(self) -> bool:
        """Check if session/refresh token is expired."""
        return datetime.now(UTC) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if session is valid (active and not expired)."""
        return self.is_active and not self.is_expired

    def revoke(self, reason: str = "manual") -> None:
        """Revoke this session."""
        self.is_active = False
        self.revoked_at = datetime.now(UTC)
        self.revoke_reason = reason

    def update_last_used(self, ip_address: str | None = None) -> None:
        """Update last used timestamp."""
        self.last_used_at = datetime.now(UTC)
        if ip_address:
            self.ip_address = ip_address


def parse_user_agent(user_agent: str | None) -> tuple[DeviceType, str]:
    """
    Parse user agent string to extract device type and name.

    Returns:
        Tuple of (DeviceType, device_name)
    """
    if not user_agent:
        return DeviceType.UNKNOWN, "Unknown Device"

    ua_lower = user_agent.lower()

    # Detect device type
    device_type = DeviceType.DESKTOP
    if any(x in ua_lower for x in ["mobile", "android", "iphone", "ipod"]):
        device_type = DeviceType.MOBILE
    elif any(x in ua_lower for x in ["tablet", "ipad"]):
        device_type = DeviceType.TABLET
    elif any(x in ua_lower for x in ["python", "curl", "postman", "insomnia"]):
        device_type = DeviceType.API

    # Extract browser/client name
    device_name = "Unknown Browser"

    if "firefox" in ua_lower:
        device_name = "Firefox"
    elif "edg" in ua_lower:
        device_name = "Edge"
    elif "chrome" in ua_lower:
        device_name = "Chrome"
    elif "safari" in ua_lower:
        device_name = "Safari"
    elif "opera" in ua_lower or "opr" in ua_lower:
        device_name = "Opera"
    elif "python" in ua_lower:
        device_name = "Python Client"
    elif "curl" in ua_lower:
        device_name = "cURL"
    elif "postman" in ua_lower:
        device_name = "Postman"

    # Add OS info
    os_name = ""
    if "windows" in ua_lower:
        os_name = "Windows"
    elif "mac os" in ua_lower or "macos" in ua_lower:
        os_name = "macOS"
    elif "linux" in ua_lower:
        os_name = "Linux"
    elif "android" in ua_lower:
        os_name = "Android"
    elif "iphone" in ua_lower or "ipad" in ua_lower:
        os_name = "iOS"

    if os_name:
        device_name = f"{device_name} on {os_name}"

    return device_type, device_name
