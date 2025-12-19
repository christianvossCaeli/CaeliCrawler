"""Main notification service for managing notifications."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationEventType,
    NotificationStatus,
)
from app.models.notification_rule import NotificationRule
from app.models.user import User
from app.models.user_email import UserEmailAddress
from services.notifications.channel_registry import (
    NotificationChannelRegistry,
    get_channel_registry,
)
from services.notifications.event_dispatcher import NotificationEventDispatcher

logger = logging.getLogger(__name__)


class NotificationService:
    """Main service for notification management.

    Provides high-level methods for:
    - Emitting events
    - Sending notifications
    - Managing notification state
    """

    def __init__(
        self,
        session: AsyncSession,
        channel_registry: Optional[NotificationChannelRegistry] = None,
    ):
        """Initialize notification service.

        Args:
            session: Database session
            channel_registry: Channel registry (uses default if not provided)
        """
        self.session = session
        self.channel_registry = channel_registry or get_channel_registry()
        self.dispatcher = NotificationEventDispatcher()

    async def emit_event(
        self,
        event_type: NotificationEventType,
        payload: Dict[str, Any],
    ) -> List[str]:
        """Emit an event and process notifications.

        Args:
            event_type: Type of event that occurred
            payload: Event data

        Returns:
            List of created notification IDs
        """
        return await self.dispatcher.dispatch_event(
            self.session, event_type, payload
        )

    async def send_notification(self, notification_id: str) -> bool:
        """Send a single notification.

        Args:
            notification_id: ID of notification to send

        Returns:
            True if sent successfully
        """
        notification = await self.session.get(
            Notification,
            UUID(notification_id),
            options=[selectinload(Notification.rule)],
        )

        if not notification:
            logger.warning(f"Notification not found: {notification_id}")
            return False

        if notification.status in (NotificationStatus.SENT, NotificationStatus.READ):
            logger.debug(f"Notification {notification_id} already sent")
            return True

        channel = self.channel_registry.get(notification.channel)
        if not channel:
            notification.status = NotificationStatus.FAILED
            notification.error_message = f"Unknown channel: {notification.channel}"
            await self.session.commit()
            logger.error(f"Unknown channel for notification {notification_id}")
            return False

        # Build channel configuration
        config = await self._build_channel_config(notification)

        # Mark as queued
        notification.status = NotificationStatus.QUEUED
        await self.session.commit()

        # Send via channel
        success = await channel.send(notification, config)

        if success:
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.now(timezone.utc)
            notification.error_message = None
        else:
            notification.retry_count += 1
            if notification.retry_count >= settings.notification_retry_max:
                notification.status = NotificationStatus.FAILED
                notification.error_message = "Max retries exceeded"
            else:
                notification.status = NotificationStatus.PENDING

        await self.session.commit()

        logger.info(
            f"Notification {notification_id} send {'succeeded' if success else 'failed'}"
        )
        return success

    async def _build_channel_config(
        self, notification: Notification
    ) -> Dict[str, Any]:
        """Build channel-specific configuration for notification.

        Args:
            notification: Notification to build config for

        Returns:
            Channel configuration dictionary
        """
        config: Dict[str, Any] = {}

        # Get config from rule if available
        if notification.rule:
            config = notification.rule.channel_config.copy()

        # Handle email-specific configuration
        if notification.channel == NotificationChannel.EMAIL:
            config["recipients"] = await self._resolve_email_recipients(
                notification, config
            )

        return config

    async def _resolve_email_recipients(
        self,
        notification: Notification,
        config: Dict[str, Any],
    ) -> List[str]:
        """Resolve email recipients from configuration.

        Args:
            notification: Notification being sent
            config: Channel configuration

        Returns:
            List of email addresses
        """
        recipients: List[str] = []

        # Get specified email address IDs
        email_address_ids = config.get("email_address_ids", [])
        if email_address_ids:
            result = await self.session.execute(
                select(UserEmailAddress).where(
                    UserEmailAddress.id.in_([UUID(id) for id in email_address_ids]),
                    UserEmailAddress.is_verified == True,
                )
            )
            recipients.extend([ea.email for ea in result.scalars().all()])

        # Include primary email if configured or no specific addresses
        include_primary = config.get("include_primary", True)
        if include_primary or not recipients:
            user = await self.session.get(User, notification.user_id)
            if user and user.email:
                if user.email not in recipients:
                    recipients.append(user.email)

        # Store recipient for tracking
        if recipients:
            notification.email_recipient = recipients[0]

        return recipients

    async def mark_as_read(self, notification_id: str, user_id: UUID) -> bool:
        """Mark a notification as read.

        Args:
            notification_id: ID of notification
            user_id: User ID (for authorization)

        Returns:
            True if successfully marked as read
        """
        notification = await self.session.get(Notification, UUID(notification_id))

        if not notification:
            return False

        if notification.user_id != user_id:
            return False

        notification.read_at = datetime.now(timezone.utc)
        if notification.status == NotificationStatus.SENT:
            notification.status = NotificationStatus.READ

        await self.session.commit()
        return True

    async def mark_all_as_read(self, user_id: UUID) -> int:
        """Mark all notifications as read for a user.

        Args:
            user_id: User ID

        Returns:
            Number of notifications marked as read
        """
        from sqlalchemy import update

        result = await self.session.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
            .values(
                read_at=datetime.now(timezone.utc),
                status=NotificationStatus.READ,
            )
        )
        await self.session.commit()

        return result.rowcount

    async def get_unread_count(self, user_id: UUID) -> int:
        """Get count of unread notifications for a user.

        Args:
            user_id: User ID

        Returns:
            Count of unread notifications
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.channel == NotificationChannel.IN_APP,
                Notification.read_at.is_(None),
                Notification.status.in_([
                    NotificationStatus.SENT,
                    NotificationStatus.PENDING,
                    NotificationStatus.QUEUED,
                ]),
            )
        )
        return result.scalar() or 0

    async def get_pending_notifications(
        self, limit: int = 100
    ) -> List[Notification]:
        """Get pending notifications for sending.

        Args:
            limit: Maximum number to retrieve

        Returns:
            List of pending notifications
        """
        result = await self.session.execute(
            select(Notification)
            .where(Notification.status == NotificationStatus.PENDING)
            .order_by(Notification.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_failed_for_retry(self, limit: int = 100) -> List[Notification]:
        """Get failed notifications that can be retried.

        Args:
            limit: Maximum number to retrieve

        Returns:
            List of notifications to retry
        """
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=settings.notification_retry_delay
        )

        result = await self.session.execute(
            select(Notification)
            .where(
                Notification.status == NotificationStatus.PENDING,
                Notification.retry_count > 0,
                Notification.retry_count < settings.notification_retry_max,
                Notification.created_at < cutoff,
            )
            .order_by(Notification.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def cleanup_old_notifications(self, days: int = 90) -> int:
        """Delete old sent/failed notifications.

        Args:
            days: Delete notifications older than this many days

        Returns:
            Number of deleted notifications
        """
        from datetime import timedelta
        from sqlalchemy import delete

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.session.execute(
            delete(Notification).where(
                Notification.status.in_([
                    NotificationStatus.SENT,
                    NotificationStatus.FAILED,
                    NotificationStatus.READ,
                ]),
                Notification.created_at < cutoff,
            )
        )
        await self.session.commit()

        logger.info(f"Cleaned up {result.rowcount} old notifications")
        return result.rowcount
