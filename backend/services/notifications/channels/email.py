"""Email notification channel using SMTP."""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List

import aiosmtplib

from app.config import settings
from app.models.notification import Notification, NotificationChannel
from services.notifications.channels.base import NotificationChannelBase

logger = logging.getLogger(__name__)


class EmailChannel(NotificationChannelBase):
    """Email notification channel using SMTP."""

    channel_type = NotificationChannel.EMAIL

    async def send(self, notification: Notification, config: Dict[str, Any]) -> bool:
        """Send email notification.

        Args:
            notification: The notification to send
            config: Email configuration with 'recipients' list

        Returns:
            True if email was sent successfully
        """
        recipients: List[str] = config.get("recipients", [])
        if not recipients:
            logger.warning(f"No recipients for notification {notification.id}")
            return False

        message = self._create_message(notification, recipients)

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username or None,
                password=settings.smtp_password or None,
                use_tls=settings.smtp_use_tls,
                start_tls=settings.smtp_use_tls and not settings.smtp_use_ssl,
                timeout=settings.smtp_timeout,
            )
            logger.info(f"Email sent for notification {notification.id} to {recipients}")
            return True
        except aiosmtplib.SMTPException as e:
            logger.error(f"SMTP error sending notification {notification.id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email for notification {notification.id}: {e}")
            return False

    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate email channel configuration.

        Args:
            config: Configuration with email_address_ids or recipients

        Returns:
            True if configuration is valid
        """
        # Either email_address_ids or recipients should be present
        has_addresses = bool(config.get("email_address_ids"))
        has_recipients = bool(config.get("recipients"))
        include_primary = config.get("include_primary", True)

        return has_addresses or has_recipients or include_primary

    def _create_message(
        self, notification: Notification, recipients: List[str]
    ) -> MIMEMultipart:
        """Create MIME message for email.

        Args:
            notification: The notification containing content
            recipients: List of email addresses

        Returns:
            Configured MIMEMultipart message
        """
        message = MIMEMultipart("alternative")
        message["Subject"] = notification.title
        message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        message["To"] = ", ".join(recipients)

        # Plain text version
        text_content = self._render_plain_text(notification)
        message.attach(MIMEText(text_content, "plain", "utf-8"))

        # HTML version
        html_content = self._render_html(notification)
        message.attach(MIMEText(html_content, "html", "utf-8"))

        return message

    def _render_plain_text(self, notification: Notification) -> str:
        """Render plain text email content."""
        lines = [
            notification.title,
            "=" * len(notification.title),
            "",
            notification.body,
            "",
            "---",
            f"Event: {notification.event_type.value}",
            f"Zeitpunkt: {notification.created_at.strftime('%d.%m.%Y %H:%M')}",
        ]

        if notification.related_entity_type and notification.related_entity_id:
            lines.append(f"Bezug: {notification.related_entity_type} ({notification.related_entity_id})")

        lines.extend([
            "",
            "Diese Nachricht wurde automatisch von CaeliCrawler gesendet.",
        ])

        return "\n".join(lines)

    def _render_html(self, notification: Notification) -> str:
        """Render HTML email content."""
        event_color = self._get_event_color(notification.event_type.value)

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: #113634;
            color: white;
            padding: 20px;
            border-radius: 8px 8px 0 0;
        }}
        .content {{
            background: #f9f9f9;
            padding: 20px;
            border: 1px solid #e0e0e0;
            border-top: none;
        }}
        .event-badge {{
            display: inline-block;
            background: {event_color};
            color: white;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            margin-bottom: 10px;
        }}
        .footer {{
            background: #f0f0f0;
            padding: 15px 20px;
            border-radius: 0 0 8px 8px;
            font-size: 12px;
            color: #666;
            border: 1px solid #e0e0e0;
            border-top: none;
        }}
        .meta {{
            font-size: 13px;
            color: #666;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #e0e0e0;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1 style="margin: 0; font-size: 20px;">{notification.title}</h1>
    </div>
    <div class="content">
        <span class="event-badge">{notification.event_type.value}</span>
        <p>{notification.body.replace(chr(10), '<br>')}</p>
        <div class="meta">
            <strong>Zeitpunkt:</strong> {notification.created_at.strftime('%d.%m.%Y %H:%M')} Uhr
        </div>
    </div>
    <div class="footer">
        Diese Nachricht wurde automatisch von CaeliCrawler gesendet.
    </div>
</body>
</html>
"""

    def _get_event_color(self, event_type: str) -> str:
        """Get color for event type badge."""
        colors = {
            "NEW_DOCUMENT": "#4CAF50",
            "DOCUMENT_CHANGED": "#2196F3",
            "DOCUMENT_REMOVED": "#f44336",
            "CRAWL_STARTED": "#9C27B0",
            "CRAWL_COMPLETED": "#4CAF50",
            "CRAWL_FAILED": "#f44336",
            "AI_ANALYSIS_COMPLETED": "#00BCD4",
            "HIGH_CONFIDENCE_RESULT": "#FF9800",
            "SOURCE_STATUS_CHANGED": "#607D8B",
            "SOURCE_ERROR": "#f44336",
        }
        return colors.get(event_type, "#757575")
