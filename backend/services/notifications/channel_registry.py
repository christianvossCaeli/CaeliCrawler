"""Registry for notification channels (Strategy Pattern)."""

import logging
from typing import Dict, Optional

from app.config import Settings, settings
from app.models.notification import NotificationChannel
from services.notifications.channels.base import NotificationChannelBase
from services.notifications.channels.email import EmailChannel
from services.notifications.channels.webhook import WebhookChannel
from services.notifications.channels.in_app import InAppChannel

logger = logging.getLogger(__name__)


class NotificationChannelRegistry:
    """Registry for notification channels.

    Manages channel implementations and provides access by channel type.
    Implements the Strategy Pattern for notification delivery.
    """

    def __init__(self):
        """Initialize empty channel registry."""
        self._channels: Dict[NotificationChannel, NotificationChannelBase] = {}

    def register(self, channel: NotificationChannelBase) -> None:
        """Register a notification channel.

        Args:
            channel: Channel implementation to register
        """
        self._channels[channel.channel_type] = channel
        logger.debug(f"Registered notification channel: {channel.channel_type.value}")

    def unregister(self, channel_type: NotificationChannel) -> None:
        """Unregister a notification channel.

        Args:
            channel_type: Type of channel to unregister
        """
        if channel_type in self._channels:
            del self._channels[channel_type]
            logger.debug(f"Unregistered notification channel: {channel_type.value}")

    def get(self, channel_type: NotificationChannel) -> Optional[NotificationChannelBase]:
        """Get channel implementation by type.

        Args:
            channel_type: Type of channel to retrieve

        Returns:
            Channel implementation or None if not registered
        """
        return self._channels.get(channel_type)

    def has(self, channel_type: NotificationChannel) -> bool:
        """Check if a channel type is registered.

        Args:
            channel_type: Type of channel to check

        Returns:
            True if channel is registered
        """
        return channel_type in self._channels

    def get_all(self) -> Dict[NotificationChannel, NotificationChannelBase]:
        """Get all registered channels.

        Returns:
            Dictionary of channel type to implementation
        """
        return self._channels.copy()

    def get_available_types(self) -> list[NotificationChannel]:
        """Get list of available channel types.

        Returns:
            List of registered channel types
        """
        return list(self._channels.keys())

    @classmethod
    def create_default(cls, app_settings: Optional[Settings] = None) -> "NotificationChannelRegistry":
        """Create registry with default channels.

        Args:
            app_settings: Application settings (uses global settings if not provided)

        Returns:
            Configured registry with all default channels
        """
        if app_settings is None:
            app_settings = settings

        registry = cls()

        # Register default channels
        registry.register(EmailChannel())
        registry.register(WebhookChannel())
        registry.register(InAppChannel())

        logger.info(
            f"Created notification channel registry with channels: "
            f"{[c.value for c in registry.get_available_types()]}"
        )

        return registry


# Global registry instance (lazy initialization)
_default_registry: Optional[NotificationChannelRegistry] = None


def get_channel_registry() -> NotificationChannelRegistry:
    """Get the default channel registry.

    Returns:
        The global channel registry instance
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = NotificationChannelRegistry.create_default()
    return _default_registry
