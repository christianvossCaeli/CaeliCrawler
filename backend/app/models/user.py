"""User model for authentication and authorization."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.custom_summary import CustomSummary
    from app.models.device_token import DeviceToken
    from app.models.notification import Notification
    from app.models.notification_rule import NotificationRule
    from app.models.reminder import Reminder
    from app.models.smart_query_operation import SmartQueryOperation
    from app.models.user_api_credentials import UserApiCredentials, UserLLMConfig
    from app.models.user_dashboard import UserDashboardPreference
    from app.models.user_email import UserEmailAddress
    from app.models.user_favorite import UserFavorite
    from app.models.user_session import UserSession


class UserRole(str, enum.Enum):
    """User roles for authorization."""

    VIEWER = "VIEWER"
    EDITOR = "EDITOR"
    ADMIN = "ADMIN"


class User(Base):
    """User account for authentication."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Authentication
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Profile
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Authorization
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        default=UserRole.VIEWER,
        nullable=False,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Session tracking
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Email verification
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    email_verification_token: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    email_verification_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # User preferences
    language: Mapped[str] = mapped_column(
        String(5),
        default="de",
        nullable=False,
    )  # ISO 639-1 language code (de, en)

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

    # Notification preferences
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    notification_digest_time: Mapped[str | None] = mapped_column(
        String(5),
        nullable=True,
    )  # e.g., "08:00" for daily digests

    # Relationships
    email_addresses: Mapped[list["UserEmailAddress"]] = relationship(
        "UserEmailAddress",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notification_rules: Mapped[list["NotificationRule"]] = relationship(
        "NotificationRule",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(UserSession.last_used_at)",
    )
    reminders: Mapped[list["Reminder"]] = relationship(
        "Reminder",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    dashboard_preferences: Mapped[Optional["UserDashboardPreference"]] = relationship(
        "UserDashboardPreference",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    export_jobs: Mapped[list["ExportJob"]] = relationship(  # noqa: F821
        "ExportJob",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    favorites: Mapped[list["UserFavorite"]] = relationship(
        "UserFavorite",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(UserFavorite.created_at)",
    )
    device_tokens: Mapped[list["DeviceToken"]] = relationship(
        "DeviceToken",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(DeviceToken.created_at)",
    )
    smart_query_operations: Mapped[list["SmartQueryOperation"]] = relationship(
        "SmartQueryOperation",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(SmartQueryOperation.last_executed_at)",
    )
    custom_summaries: Mapped[list["CustomSummary"]] = relationship(
        "CustomSummary",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(CustomSummary.updated_at)",
    )
    api_credentials: Mapped[list["UserApiCredentials"]] = relationship(
        "UserApiCredentials",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    llm_configs: Mapped[list["UserLLMConfig"]] = relationship(
        "UserLLMConfig",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    @property
    def active_sessions_count(self) -> int:
        """Get count of active sessions."""
        return sum(1 for s in self.sessions if s.is_valid)
