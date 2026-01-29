"""Service for persisting security events to the database.

This service provides a reliable way to store security-relevant events
for compliance, auditing, and incident response purposes.

Events are written asynchronously to avoid impacting request latency.
"""

import asyncio
from datetime import datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.security_event import (
    SecurityEvent,
    SecurityEventSeverity,
    SecurityEventType,
)

logger = structlog.get_logger(__name__)


class SecurityEventService:
    """Service for managing security events.

    Uses fire-and-forget pattern for writes to avoid blocking requests.
    """

    @staticmethod
    async def log_event(
        event_type: SecurityEventType,
        message: str,
        severity: SecurityEventSeverity = SecurityEventSeverity.INFO,
        user_id: str | None = None,
        user_email: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        endpoint: str | None = None,
        method: str | None = None,
        request_id: str | None = None,
        details: dict | None = None,
        success: bool | None = None,
    ) -> None:
        """Log a security event to the database.

        This method runs asynchronously and doesn't block the caller.

        Args:
            event_type: Type of security event
            message: Human-readable description
            severity: Event severity level
            user_id: UUID of the user (if authenticated)
            user_email: Email of the user (if known)
            ip_address: Client IP address
            user_agent: Client User-Agent header
            endpoint: API endpoint path
            method: HTTP method
            request_id: Unique request identifier
            details: Additional structured data
            success: Whether the action succeeded
        """
        try:
            async with async_session_maker() as session:
                event = SecurityEvent(
                    event_type=event_type,
                    severity=severity,
                    user_id=user_id,
                    user_email=user_email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    endpoint=endpoint,
                    method=method,
                    request_id=request_id,
                    message=message,
                    details=details,
                    success=success,
                )
                session.add(event)
                await session.commit()
        except Exception as e:
            # Log to structlog if database write fails
            # Never raise - security logging should not break the application
            logger.error(
                "Failed to persist security event",
                event_type=event_type.value if event_type else None,
                error=str(e),
            )

    @staticmethod
    def log_event_background(
        event_type: SecurityEventType,
        message: str,
        **kwargs,
    ) -> None:
        """Fire-and-forget security event logging.

        Creates a background task to persist the event without blocking.
        Use this for non-critical events where we don't need confirmation.
        """
        try:
            asyncio.create_task(
                SecurityEventService.log_event(event_type, message, **kwargs)
            )
        except RuntimeError:
            # No event loop running (e.g., during shutdown)
            # Fall back to sync logging
            logger.warning(
                "Cannot create background task for security event",
                event_type=event_type.value,
                message=message,
            )

    @staticmethod
    async def get_recent_events(
        session: AsyncSession,
        event_types: list[SecurityEventType] | None = None,
        severity: SecurityEventSeverity | None = None,
        user_id: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[SecurityEvent]:
        """Query recent security events.

        Args:
            session: Database session
            event_types: Filter by event types
            severity: Filter by minimum severity
            user_id: Filter by user ID
            since: Only events after this timestamp
            limit: Maximum number of events to return

        Returns:
            List of security events, newest first
        """
        query = select(SecurityEvent).order_by(SecurityEvent.created_at.desc())

        if event_types:
            query = query.where(SecurityEvent.event_type.in_(event_types))

        if severity:
            # Get events with this severity or higher
            severity_order = [
                SecurityEventSeverity.INFO,
                SecurityEventSeverity.WARNING,
                SecurityEventSeverity.ERROR,
                SecurityEventSeverity.CRITICAL,
            ]
            min_index = severity_order.index(severity)
            allowed_severities = severity_order[min_index:]
            query = query.where(SecurityEvent.severity.in_(allowed_severities))

        if user_id:
            query = query.where(SecurityEvent.user_id == user_id)

        if since:
            query = query.where(SecurityEvent.created_at >= since)

        query = query.limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_failed_login_count(
        session: AsyncSession,
        ip_address: str,
        since: datetime,
    ) -> int:
        """Count failed login attempts from an IP address.

        Useful for detecting brute force attacks.
        """
        query = (
            select(SecurityEvent)
            .where(SecurityEvent.event_type == SecurityEventType.LOGIN_FAILURE)
            .where(SecurityEvent.ip_address == ip_address)
            .where(SecurityEvent.created_at >= since)
        )
        result = await session.execute(query)
        return len(result.scalars().all())


# Singleton instance for easy import
security_event_service = SecurityEventService()
