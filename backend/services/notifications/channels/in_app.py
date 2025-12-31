"""In-App notification channel for web UI notifications."""

import logging
from datetime import UTC, datetime
from typing import Any

from app.models.notification import Notification, NotificationChannel, NotificationStatus
from services.notifications.channels.base import NotificationChannelBase

logger = logging.getLogger(__name__)


class InAppChannel(NotificationChannelBase):
    """In-App notification channel.

    In-App notifications are stored in the database and displayed in the web UI.
    This channel simply marks the notification as sent/ready for display.
    """

    channel_type = NotificationChannel.IN_APP

    async def send(self, notification: Notification, config: dict[str, Any]) -> bool:
        """Mark notification as ready for in-app display.

        For in-app notifications, we don't need to send anything externally.
        The notification is already stored in the database and will be
        retrieved by the frontend via API polling or WebSocket.

        Args:
            notification: The notification to mark as sent
            config: In-App configuration (currently unused)

        Returns:
            Always True since no external delivery is needed
        """
        # In-App notifications are "sent" by simply being stored
        # The frontend will poll for them via the notifications API
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.now(UTC)

        logger.info(f"In-App notification {notification.id} marked as ready for display")
        return True

    async def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate in-app channel configuration.

        In-App channel doesn't require any specific configuration.

        Args:
            config: Configuration dictionary (currently unused)

        Returns:
            Always True
        """
        return True
