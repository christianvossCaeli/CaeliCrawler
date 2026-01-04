"""Redis-based notification broadcasting for real-time SSE updates.

This service uses Redis Pub/Sub to broadcast notification events to all
connected SSE clients, enabling real-time updates without polling.
"""

import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import redis.asyncio as redis
import structlog

from app.config import settings

logger = structlog.get_logger()


class NotificationBroadcaster:
    """
    Redis Pub/Sub based broadcaster for notification events.

    Publishes events when notifications are created/updated and provides
    an async generator for SSE endpoints to subscribe to user-specific channels.
    """

    # Redis channel patterns
    USER_CHANNEL = "notifications:user:{user_id}"
    GLOBAL_CHANNEL = "notifications:global"

    # Event types
    EVENT_NEW = "new_notification"
    EVENT_READ = "notification_read"
    EVENT_READ_ALL = "all_read"
    EVENT_COUNT_UPDATE = "count_update"

    def __init__(self):
        self._redis: redis.Redis | None = None
        self._pubsub_connections: dict[str, redis.client.PubSub] = {}

    async def get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    async def broadcast_new_notification(
        self,
        user_id: UUID,
        notification_data: dict[str, Any],
    ) -> None:
        """
        Broadcast a new notification to the user's channel.

        Args:
            user_id: ID of the user receiving the notification
            notification_data: Serialized notification data
        """
        r = await self.get_redis()
        channel = self.USER_CHANNEL.format(user_id=str(user_id))

        event = {
            "type": self.EVENT_NEW,
            "data": notification_data,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        await r.publish(channel, json.dumps(event))
        logger.debug(f"Broadcast new notification to user {user_id}")

    async def broadcast_read(
        self,
        user_id: UUID,
        notification_id: UUID,
    ) -> None:
        """Broadcast that a notification was marked as read."""
        r = await self.get_redis()
        channel = self.USER_CHANNEL.format(user_id=str(user_id))

        event = {
            "type": self.EVENT_READ,
            "data": {"id": str(notification_id)},
            "timestamp": datetime.now(UTC).isoformat(),
        }

        await r.publish(channel, json.dumps(event))

    async def broadcast_all_read(
        self,
        user_id: UUID,
    ) -> None:
        """Broadcast that all notifications were marked as read."""
        r = await self.get_redis()
        channel = self.USER_CHANNEL.format(user_id=str(user_id))

        event = {
            "type": self.EVENT_READ_ALL,
            "data": {},
            "timestamp": datetime.now(UTC).isoformat(),
        }

        await r.publish(channel, json.dumps(event))

    async def broadcast_count_update(
        self,
        user_id: UUID,
        unread_count: int,
    ) -> None:
        """Broadcast updated unread count."""
        r = await self.get_redis()
        channel = self.USER_CHANNEL.format(user_id=str(user_id))

        event = {
            "type": self.EVENT_COUNT_UPDATE,
            "data": {"unread_count": unread_count},
            "timestamp": datetime.now(UTC).isoformat(),
        }

        await r.publish(channel, json.dumps(event))

    async def subscribe(
        self,
        user_id: UUID,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Subscribe to notification events for a user.

        Yields events as they are published. This is designed to be used
        with SSE endpoints.

        Args:
            user_id: ID of the user to subscribe for

        Yields:
            Event dictionaries with type, data, and timestamp
        """
        r = await self.get_redis()
        pubsub = r.pubsub()

        channel = self.USER_CHANNEL.format(user_id=str(user_id))

        try:
            await pubsub.subscribe(channel)
            logger.debug(f"Subscribed to notifications for user {user_id}")

            while True:
                try:
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True),
                        timeout=30.0,  # Timeout for heartbeat
                    )

                    if message and message["type"] == "message":
                        event = json.loads(message["data"])
                        yield event

                except asyncio.TimeoutError:
                    # Yield heartbeat to keep connection alive
                    yield {"type": "heartbeat", "data": {}, "timestamp": datetime.now(UTC).isoformat()}

        except asyncio.CancelledError:
            logger.debug(f"SSE subscription cancelled for user {user_id}")
            raise
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None


# Global instance
notification_broadcaster = NotificationBroadcaster()
