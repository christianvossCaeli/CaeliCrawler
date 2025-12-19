"""Base class for notification channels (Strategy Pattern)."""

from abc import ABC, abstractmethod
from typing import Any, Dict

from app.models.notification import Notification, NotificationChannel


class NotificationChannelBase(ABC):
    """Base class for notification channels.

    Implements the Strategy Pattern for different notification delivery methods.
    Each channel implementation handles a specific delivery mechanism (email, webhook, etc.).
    """

    channel_type: NotificationChannel

    @abstractmethod
    async def send(self, notification: Notification, config: Dict[str, Any]) -> bool:
        """Send notification through this channel.

        Args:
            notification: The notification to send
            config: Channel-specific configuration from the notification rule

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate channel-specific configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if configuration is valid, False otherwise
        """
        pass

    def get_channel_type(self) -> NotificationChannel:
        """Get the channel type for this implementation."""
        return self.channel_type
