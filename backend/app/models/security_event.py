"""Security Event model for persistent security audit logging.

This model stores security-relevant events in the database for compliance
and incident response purposes. Events are immutable (append-only).

Security events include:
- Authentication attempts (successful and failed)
- Authorization denials
- Rate limit violations
- Suspicious activities
- Configuration changes
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SecurityEventSeverity(str, Enum):
    """Severity level of security events."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SecurityEventType(str, Enum):
    """Types of security events tracked in the system."""

    # Authentication events
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILURE = "LOGIN_FAILURE"
    LOGOUT = "LOGOUT"
    TOKEN_REFRESH = "TOKEN_REFRESH"
    TOKEN_REVOKED = "TOKEN_REVOKED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PASSWORD_RESET_REQUESTED = "PASSWORD_RESET_REQUESTED"
    EMAIL_VERIFICATION = "EMAIL_VERIFICATION"

    # Authorization events
    ACCESS_DENIED = "ACCESS_DENIED"
    PERMISSION_ESCALATION_ATTEMPT = "PERMISSION_ESCALATION_ATTEMPT"
    ADMIN_ACTION = "ADMIN_ACTION"

    # Rate limiting events
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    RATE_LIMIT_WARNING = "RATE_LIMIT_WARNING"

    # Suspicious activity
    SUSPICIOUS_REQUEST = "SUSPICIOUS_REQUEST"
    INVALID_INPUT = "INVALID_INPUT"
    SSRF_ATTEMPT = "SSRF_ATTEMPT"

    # Session events
    SESSION_CREATED = "SESSION_CREATED"
    SESSION_TERMINATED = "SESSION_TERMINATED"
    CONCURRENT_SESSION_LIMIT = "CONCURRENT_SESSION_LIMIT"

    # Configuration events
    SECURITY_CONFIG_CHANGED = "SECURITY_CONFIG_CHANGED"
    API_KEY_CREATED = "API_KEY_CREATED"
    API_KEY_REVOKED = "API_KEY_REVOKED"


class SecurityEvent(Base):
    """Persistent security event log entry.

    This table is append-only. Events should never be deleted or modified
    to maintain audit trail integrity.
    """

    __tablename__ = "security_events"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Event classification
    event_type: Mapped[SecurityEventType] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    severity: Mapped[SecurityEventSeverity] = mapped_column(
        String(20),
        nullable=False,
        default=SecurityEventSeverity.INFO,
        index=True,
    )

    # Timestamp (immutable)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Actor information
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    user_email: Mapped[str | None] = mapped_column(String(255))
    ip_address: Mapped[str | None] = mapped_column(String(45))  # IPv6 compatible
    user_agent: Mapped[str | None] = mapped_column(Text)

    # Request context
    endpoint: Mapped[str | None] = mapped_column(String(500))
    method: Mapped[str | None] = mapped_column(String(10))
    request_id: Mapped[str | None] = mapped_column(String(36), index=True)

    # Event details
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB)

    # Outcome
    success: Mapped[bool | None] = mapped_column()

    __table_args__ = (
        # Composite index for time-based queries with filtering
        Index("ix_security_events_type_created", "event_type", "created_at"),
        Index("ix_security_events_severity_created", "severity", "created_at"),
        Index("ix_security_events_user_created", "user_id", "created_at"),
        # Partial index for failed events (most often queried)
        Index(
            "ix_security_events_failures",
            "event_type",
            "created_at",
            postgresql_where=(success == False),  # noqa: E712
        ),
    )

    def __repr__(self) -> str:
        return f"<SecurityEvent {self.event_type} at {self.created_at}>"
