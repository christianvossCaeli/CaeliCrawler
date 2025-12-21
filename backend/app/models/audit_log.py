"""AuditLog model for tracking all user actions."""

import enum
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class AuditAction(str, enum.Enum):
    """Types of auditable actions."""

    # CRUD operations
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"

    # Authentication
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    PASSWORD_RESET = "PASSWORD_RESET"

    # Session Management
    SESSION_REVOKE = "SESSION_REVOKE"
    SESSION_REVOKE_ALL = "SESSION_REVOKE_ALL"
    TOKEN_REFRESH = "TOKEN_REFRESH"

    # Data Operations
    EXPORT = "EXPORT"
    VIEW = "VIEW"
    IMPORT = "IMPORT"
    VERIFY = "VERIFY"

    # Crawler Operations
    CRAWLER_START = "CRAWLER_START"
    CRAWLER_STOP = "CRAWLER_STOP"

    # Admin Operations
    USER_CREATE = "USER_CREATE"
    USER_UPDATE = "USER_UPDATE"
    USER_DELETE = "USER_DELETE"
    ROLE_CHANGE = "ROLE_CHANGE"

    # Security Events
    SECURITY_ALERT = "SECURITY_ALERT"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"


class AuditLog(Base):
    """
    Central audit log for tracking all user actions.

    Records who did what, when, and to which entity.
    Changes are stored as JSON diffs for UPDATE actions.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Who performed the action
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Denormalized email for when user is deleted",
    )

    # What action was performed
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action"),
        nullable=False,
        index=True,
    )

    # Which entity was affected
    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Model name: Category, DataSource, Entity, etc.",
    )
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    entity_name: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Human-readable entity identifier",
    )

    # Change details
    changes: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="JSON diff of changes: {field: {old: x, new: y}}",
    )

    # Request context
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        comment="Client IP address (supports IPv6)",
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Client user agent string",
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        lazy="selectin",
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_user_action", "user_id", "action"),
        Index("ix_audit_logs_created_at_desc", created_at.desc()),
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action.value} {self.entity_type} by {self.user_email}>"
