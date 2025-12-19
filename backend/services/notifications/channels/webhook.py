"""Webhook notification channel for HTTP callbacks."""

import ipaddress
import logging
import socket
from typing import Any, Dict, Tuple
from urllib.parse import urlparse

import httpx

from app.models.notification import Notification, NotificationChannel
from services.notifications.channels.base import NotificationChannelBase

logger = logging.getLogger(__name__)


# =============================================================================
# SSRF Protection for Webhook URLs
# =============================================================================

BLOCKED_IP_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),      # Localhost
    ipaddress.ip_network("10.0.0.0/8"),       # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),    # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),   # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),   # Link-local (cloud metadata)
    ipaddress.ip_network("0.0.0.0/8"),        # Current network
]


def is_safe_webhook_url(url: str) -> Tuple[bool, str]:
    """
    Validate webhook URL for SSRF protection.

    Returns (is_safe, error_message).
    """
    try:
        parsed = urlparse(url)

        # Only allow https
        if parsed.scheme != "https":
            return False, "Only HTTPS URLs are allowed"

        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid URL: no hostname"

        # Block localhost
        if hostname.lower() in {"localhost", "127.0.0.1", "::1", "0.0.0.0"}:
            return False, "Localhost URLs are not allowed"

        # Block internal hostnames
        if hostname.endswith(".local") or hostname.endswith(".internal"):
            return False, "Internal hostnames are not allowed"

        # Resolve and check IP
        try:
            ip = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip)

            for blocked_range in BLOCKED_IP_RANGES:
                if ip_obj in blocked_range:
                    return False, "URL resolves to blocked IP range"
        except socket.gaierror:
            pass  # Can't resolve, allow

        return True, ""
    except Exception as e:
        return False, f"Invalid URL: {str(e)}"


class WebhookChannel(NotificationChannelBase):
    """Webhook notification channel for HTTP POST callbacks."""

    channel_type = NotificationChannel.WEBHOOK

    async def send(self, notification: Notification, config: Dict[str, Any]) -> bool:
        """Send notification via HTTP webhook.

        Args:
            notification: The notification to send
            config: Webhook configuration with 'url', optional 'auth' and 'headers'

        Returns:
            True if webhook call was successful
        """
        url = config.get("url")
        if not url:
            logger.warning(f"No webhook URL for notification {notification.id}")
            return False

        # SSRF Protection: Validate URL before making request
        is_safe, error_msg = is_safe_webhook_url(url)
        if not is_safe:
            logger.error(
                f"Blocked unsafe webhook URL for notification {notification.id}: {error_msg}"
            )
            return False

        headers = self._build_headers(config)
        payload = self._build_payload(notification)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=30.0,
                )

                if response.is_success:
                    logger.info(f"Webhook sent for notification {notification.id} to {url}")
                    return True
                else:
                    logger.warning(
                        f"Webhook failed for notification {notification.id}: "
                        f"status={response.status_code}, body={response.text[:200]}"
                    )
                    return False

        except httpx.TimeoutException:
            logger.error(f"Webhook timeout for notification {notification.id} to {url}")
            return False
        except httpx.RequestError as e:
            logger.error(f"Webhook request error for notification {notification.id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send webhook for notification {notification.id}: {e}")
            return False

    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate webhook channel configuration.

        Args:
            config: Configuration with 'url' and optional auth settings

        Returns:
            True if configuration is valid
        """
        url = config.get("url", "")
        if not url:
            return False

        # SSRF Protection: Validate URL
        is_safe, error_msg = is_safe_webhook_url(url)
        if not is_safe:
            logger.warning(f"Invalid webhook URL: {error_msg}")
            return False

        # Validate auth config if present
        auth = config.get("auth", {})
        if auth:
            auth_type = auth.get("type")
            if auth_type == "bearer" and not auth.get("token"):
                return False
            if auth_type == "basic" and (not auth.get("username") or not auth.get("password")):
                return False

        return True

    def _build_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Build HTTP headers for webhook request.

        Args:
            config: Webhook configuration

        Returns:
            Headers dictionary
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "CaeliCrawler-Webhook/1.0",
        }

        # Add custom headers
        custom_headers = config.get("headers", {})
        headers.update(custom_headers)

        # Handle authentication
        auth = config.get("auth", {})
        auth_type = auth.get("type")

        if auth_type == "bearer":
            token = auth.get("token", "")
            headers["Authorization"] = f"Bearer {token}"
        elif auth_type == "basic":
            import base64
            username = auth.get("username", "")
            password = auth.get("password", "")
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        elif auth_type == "api_key":
            key_name = auth.get("key_name", "X-API-Key")
            key_value = auth.get("key_value", "")
            headers[key_name] = key_value

        return headers

    def _build_payload(self, notification: Notification) -> Dict[str, Any]:
        """Build JSON payload for webhook.

        Args:
            notification: The notification to send

        Returns:
            Payload dictionary
        """
        payload = {
            "event_type": notification.event_type.value,
            "notification_id": str(notification.id),
            "title": notification.title,
            "body": notification.body,
            "timestamp": notification.created_at.isoformat(),
            "data": notification.payload,
        }

        if notification.related_entity_type:
            payload["related_entity"] = {
                "type": notification.related_entity_type,
                "id": str(notification.related_entity_id) if notification.related_entity_id else None,
            }

        return payload
