"""Email notification channel using SMTP."""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import aiosmtplib

from app.config import settings
from app.models.notification import Notification, NotificationChannel
from services.notifications.channels.base import NotificationChannelBase

logger = logging.getLogger(__name__)


class EmailChannel(NotificationChannelBase):
    """Email notification channel using SMTP."""

    channel_type = NotificationChannel.EMAIL

    async def send(self, notification: Notification, config: dict[str, Any]) -> bool:
        """Send email notification.

        Args:
            notification: The notification to send
            config: Email configuration with 'recipients' list

        Returns:
            True if email was sent successfully
        """
        recipients: list[str] = config.get("recipients", [])
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

    async def validate_config(self, config: dict[str, Any]) -> bool:
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

    def _create_message(self, notification: Notification, recipients: list[str]) -> MIMEMultipart:
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

        lines.extend(
            [
                "",
                "Diese Nachricht wurde automatisch von CaeliCrawler gesendet.",
            ]
        )

        return "\n".join(lines)

    def _render_html(self, notification: Notification) -> str:
        """Render HTML email content."""
        event_color = self._get_event_color(notification.event_type.value)
        event_label = self._get_event_type_label(notification.event_type.value)

        # Build action URL if we have a related entity
        action_url = None
        action_text = None
        if notification.related_entity_type and notification.related_entity_id:
            base_url = settings.frontend_url.rstrip("/")
            if notification.related_entity_type == "document":
                action_url = f"{base_url}/documents?document_id={notification.related_entity_id}"
                action_text = "Dokument anzeigen"
            elif notification.related_entity_type == "crawl_job":
                action_url = f"{base_url}/crawler?job_id={notification.related_entity_id}"
                action_text = "Crawl-Job anzeigen"
            elif notification.related_entity_type == "data_source":
                action_url = f"{base_url}/sources?id={notification.related_entity_id}"
                action_text = "Quelle anzeigen"
            elif notification.related_entity_type == "summary":
                action_url = f"{base_url}/summaries?id={notification.related_entity_id}"
                action_text = "Zusammenfassung anzeigen"

        # Build action button HTML if we have a URL
        action_button = ""
        if action_url and action_text:
            action_button = f"""
            <div style="text-align: center; margin: 25px 0;">
                <a href="{action_url}" style="
                    display: inline-block;
                    background: #113634;
                    color: #ffffff;
                    text-decoration: none;
                    padding: 12px 28px;
                    border-radius: 6px;
                    font-weight: 500;
                    font-size: 14px;
                ">{action_text}</a>
            </div>
            """

        return f"""
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{notification.title}</title>
</head>
<body style="
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    line-height: 1.6;
    color: #333333;
    background-color: #f5f5f5;
">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="
        background-color: #f5f5f5;
        padding: 20px 0;
    ">
        <tr>
            <td align="center">
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="
                    max-width: 600px;
                    width: 100%;
                    background-color: #ffffff;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                ">
                    <!-- Header -->
                    <tr>
                        <td style="
                            background: linear-gradient(135deg, #113634 0%, #1a4d4a 100%);
                            padding: 30px 40px;
                            text-align: center;
                        ">
                            <h1 style="
                                margin: 0;
                                color: #ffffff;
                                font-size: 22px;
                                font-weight: 600;
                                letter-spacing: -0.3px;
                            ">CaeliCrawler</h1>
                            <p style="
                                margin: 8px 0 0 0;
                                color: rgba(255,255,255,0.85);
                                font-size: 13px;
                            ">Automatische Benachrichtigung</p>
                        </td>
                    </tr>

                    <!-- Event Badge & Title -->
                    <tr>
                        <td style="padding: 30px 40px 0 40px;">
                            <span style="
                                display: inline-block;
                                background: {event_color};
                                color: #ffffff;
                                padding: 5px 14px;
                                border-radius: 20px;
                                font-size: 12px;
                                font-weight: 500;
                                text-transform: uppercase;
                                letter-spacing: 0.3px;
                            ">{event_label}</span>
                            <h2 style="
                                margin: 15px 0 0 0;
                                color: #1a1a1a;
                                font-size: 20px;
                                font-weight: 600;
                            ">{notification.title}</h2>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding: 20px 40px;">
                            <p style="
                                margin: 0;
                                color: #4a4a4a;
                                font-size: 15px;
                                line-height: 1.7;
                            ">{notification.body.replace(chr(10), "<br>")}</p>
                            {action_button}
                        </td>
                    </tr>

                    <!-- Metadata -->
                    <tr>
                        <td style="padding: 0 40px 30px 40px;">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="
                                background: #f8f9fa;
                                border-radius: 8px;
                                padding: 15px 20px;
                            ">
                                <tr>
                                    <td style="padding: 15px 20px;">
                                        <p style="
                                            margin: 0;
                                            color: #666666;
                                            font-size: 13px;
                                        ">
                                            <strong>Zeitpunkt:</strong> {notification.created_at.strftime("%d.%m.%Y um %H:%M Uhr")}
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="
                            background: #f8f9fa;
                            padding: 25px 40px;
                            border-top: 1px solid #eaeaea;
                        ">
                            <p style="
                                margin: 0;
                                color: #888888;
                                font-size: 12px;
                                text-align: center;
                            ">
                                Diese Nachricht wurde automatisch von CaeliCrawler gesendet.<br>
                                Sie erhalten diese E-Mail aufgrund Ihrer Benachrichtigungseinstellungen.
                            </p>
                            <p style="
                                margin: 15px 0 0 0;
                                color: #aaaaaa;
                                font-size: 11px;
                                text-align: center;
                            ">
                                © {notification.created_at.year} Caeli Wind GmbH
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
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

    def _get_event_type_label(self, event_type: str) -> str:
        """Get human-readable German label for event type."""
        labels = {
            "NEW_DOCUMENT": "Neue Dokumente",
            "DOCUMENT_CHANGED": "Dokument geändert",
            "DOCUMENT_REMOVED": "Dokument entfernt",
            "CRAWL_STARTED": "Crawl gestartet",
            "CRAWL_COMPLETED": "Crawl abgeschlossen",
            "CRAWL_FAILED": "Crawl fehlgeschlagen",
            "AI_ANALYSIS_COMPLETED": "Analyse abgeschlossen",
            "HIGH_CONFIDENCE_RESULT": "Relevantes Ergebnis",
            "SOURCE_STATUS_CHANGED": "Status geändert",
            "SOURCE_ERROR": "Fehler aufgetreten",
            "SUMMARY_UPDATED": "Zusammenfassung aktualisiert",
            "SUMMARY_RELEVANT_CHANGES": "Relevante Änderungen",
        }
        return labels.get(event_type, event_type)


async def send_verification_email(email: str, verification_url: str, email_id: str) -> bool:
    """
    Send email address verification email.

    Args:
        email: Email address to verify
        verification_url: Full URL for verification
        email_id: ID of the email address record

    Returns:
        True if email was sent successfully
    """
    message = MIMEMultipart("alternative")
    message["Subject"] = "E-Mail-Adresse bestätigen - CaeliCrawler"
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = email

    # Plain text version
    text_content = f"""
E-Mail-Adresse bestätigen
=========================

Bitte bestätigen Sie Ihre E-Mail-Adresse für CaeliCrawler-Benachrichtigungen.

Klicken Sie auf folgenden Link oder kopieren Sie ihn in Ihren Browser:

{verification_url}

Dieser Link ist 24 Stunden gültig.

Falls Sie diese E-Mail nicht angefordert haben, können Sie sie ignorieren.

---
CaeliCrawler - Automatische Datenquellen-Überwachung
    """

    # HTML version
    html_content = f"""
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>E-Mail-Adresse bestätigen</title>
</head>
<body style="
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    line-height: 1.6;
    color: #333333;
    background-color: #f5f5f5;
">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="
        background-color: #f5f5f5;
        padding: 20px 0;
    ">
        <tr>
            <td align="center">
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="
                    max-width: 600px;
                    width: 100%;
                    background-color: #ffffff;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                ">
                    <!-- Header -->
                    <tr>
                        <td style="
                            background: linear-gradient(135deg, #113634 0%, #1a4d4a 100%);
                            padding: 30px 40px;
                            text-align: center;
                        ">
                            <h1 style="
                                margin: 0;
                                color: #ffffff;
                                font-size: 22px;
                                font-weight: 600;
                            ">CaeliCrawler</h1>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px;">
                            <h2 style="
                                margin: 0 0 20px 0;
                                color: #1a1a1a;
                                font-size: 20px;
                                font-weight: 600;
                            ">E-Mail-Adresse bestätigen</h2>

                            <p style="
                                margin: 0 0 25px 0;
                                color: #4a4a4a;
                                font-size: 15px;
                            ">
                                Bitte bestätigen Sie Ihre E-Mail-Adresse <strong>{email}</strong>
                                für CaeliCrawler-Benachrichtigungen.
                            </p>

                            <div style="text-align: center; margin: 30px 0;">
                                <a href="{verification_url}" style="
                                    display: inline-block;
                                    background: #113634;
                                    color: #ffffff;
                                    text-decoration: none;
                                    padding: 14px 32px;
                                    border-radius: 6px;
                                    font-weight: 500;
                                    font-size: 15px;
                                ">E-Mail bestätigen</a>
                            </div>

                            <p style="
                                margin: 25px 0 0 0;
                                color: #888888;
                                font-size: 13px;
                            ">
                                Falls der Button nicht funktioniert, kopieren Sie diesen Link in Ihren Browser:<br>
                                <a href="{verification_url}" style="color: #113634; word-break: break-all;">
                                    {verification_url}
                                </a>
                            </p>

                            <p style="
                                margin: 20px 0 0 0;
                                color: #888888;
                                font-size: 13px;
                            ">
                                Dieser Link ist 24 Stunden gültig.
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="
                            background: #f8f9fa;
                            padding: 25px 40px;
                            border-top: 1px solid #eaeaea;
                        ">
                            <p style="
                                margin: 0;
                                color: #888888;
                                font-size: 12px;
                                text-align: center;
                            ">
                                Falls Sie diese E-Mail nicht angefordert haben, können Sie sie ignorieren.
                            </p>
                            <p style="
                                margin: 15px 0 0 0;
                                color: #aaaaaa;
                                font-size: 11px;
                                text-align: center;
                            ">
                                © Caeli Wind GmbH
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

    message.attach(MIMEText(text_content, "plain", "utf-8"))
    message.attach(MIMEText(html_content, "html", "utf-8"))

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
        logger.info(f"Verification email sent to {email}")
        return True
    except aiosmtplib.SMTPException as e:
        logger.error(f"SMTP error sending verification email to {email}: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {e}")
        return False
