"""Webhook notification channel for HTTP callbacks."""

import ipaddress
import logging
import socket
from typing import Any
from urllib.parse import urlparse, urlunparse

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


def is_safe_webhook_url(url: str) -> tuple[bool, str, str | None]:
    """
    Validate webhook URL for SSRF protection.

    Returns (is_safe, error_message, resolved_ip).
    The resolved_ip should be used for the actual request to prevent DNS rebinding attacks.
    """
    try:
        parsed = urlparse(url)

        # Only allow https
        if parsed.scheme != "https":
            return False, "Only HTTPS URLs are allowed", None

        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid URL: no hostname", None

        # Block localhost
        if hostname.lower() in {"localhost", "127.0.0.1", "::1", "0.0.0.0"}:
            return False, "Localhost URLs are not allowed", None

        # Block internal hostnames
        if hostname.endswith(".local") or hostname.endswith(".internal"):
            return False, "Internal hostnames are not allowed", None

        # Resolve and check IP - REQUIRED for DNS rebinding protection
        try:
            resolved_ip = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(resolved_ip)

            for blocked_range in BLOCKED_IP_RANGES:
                if ip_obj in blocked_range:
                    return False, "URL resolves to blocked IP range", None

            # Return the resolved IP to pin the connection
            return True, "", resolved_ip
        except socket.gaierror:
            # Can't resolve - this is now an error since we need IP pinning
            return False, "Cannot resolve hostname", None

    except Exception as e:
        return False, f"Invalid URL: {str(e)}", None


def create_pinned_url(original_url: str, resolved_ip: str) -> tuple[str, str]:
    """
    Create a URL with IP instead of hostname for DNS rebinding protection.

    Returns (pinned_url, original_hostname) for setting Host header.
    """
    parsed = urlparse(original_url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    # Replace hostname with IP in URL
    netloc = f"{resolved_ip}:{port}" if port not in (80, 443) else resolved_ip
    pinned = urlunparse((
        parsed.scheme,
        netloc,
        parsed.path,
        parsed.params,
        parsed.query,
        parsed.fragment,
    ))

    return pinned, parsed.hostname


class WebhookChannel(NotificationChannelBase):
    """Webhook notification channel for HTTP POST callbacks."""

    channel_type = NotificationChannel.WEBHOOK

    async def send(self, notification: Notification, config: dict[str, Any]) -> bool:
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

        # SSRF Protection: Validate URL and get resolved IP
        is_safe, error_msg, resolved_ip = is_safe_webhook_url(url)
        if not is_safe or not resolved_ip:
            logger.error(
                f"Blocked unsafe webhook URL for notification {notification.id}: {error_msg}"
            )
            return False

        # Create pinned URL to prevent DNS rebinding attacks
        pinned_url, original_hostname = create_pinned_url(url, resolved_ip)

        headers = self._build_headers(config)
        # Add Host header with original hostname for server routing
        headers["Host"] = original_hostname
        payload = self._build_payload(notification)

        try:
            # Use pinned URL with resolved IP to prevent DNS rebinding
            async with httpx.AsyncClient(verify=True) as client:
                response = await client.post(
                    pinned_url,
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

    async def validate_config(self, config: dict[str, Any]) -> bool:
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
        is_safe, error_msg, _ = is_safe_webhook_url(url)
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

    def _build_headers(self, config: dict[str, Any]) -> dict[str, str]:
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

    def _build_payload(self, notification: Notification) -> dict[str, Any]:
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
