"""Celery tasks for notification operations."""

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from workers.async_runner import run_async
from workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    bind=True,
    name="workers.notification_tasks.send_notification",
    max_retries=5,
    default_retry_delay=30,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def send_notification(self, notification_id: str):
    """Send a single notification.

    Args:
        notification_id: UUID of the notification to send
    """
    from app.database import get_celery_session_context
    from services.notifications.notification_service import NotificationService

    async def _send():
        async with get_celery_session_context() as session:
            service = NotificationService(session)
            success = await service.send_notification(notification_id)
            return success

    result = run_async(_send())

    logger.info(
        "Notification send task completed",
        notification_id=notification_id,
        success=result,
    )
    return result


@celery_app.task(name="workers.notification_tasks.emit_event")
def emit_event(event_type: str, payload: dict[str, Any]):
    """Emit a notification event and create notifications for matching rules.

    This task is called from other tasks (crawl, processing, AI) when
    events occur that may trigger notifications.

    Args:
        event_type: String value of NotificationEventType
        payload: Event data dictionary
    """
    from app.database import get_celery_session_context
    from app.models.notification import NotificationEventType
    from services.notifications.notification_service import NotificationService

    async def _emit():
        async with get_celery_session_context() as session:
            service = NotificationService(session)

            try:
                event = NotificationEventType(event_type)
            except ValueError:
                logger.error(
                    "Invalid event type",
                    event_type=event_type,
                )
                return []

            notification_ids = await service.emit_event(event, payload)

            # Queue each notification for sending
            for nid in notification_ids:
                send_notification.delay(nid)

            return notification_ids

    notification_ids = run_async(_emit())

    logger.info(
        "Event emitted",
        event_type=event_type,
        notifications_created=len(notification_ids),
    )
    return notification_ids


@celery_app.task(name="workers.notification_tasks.process_digests")
def process_digests():
    """Process digest notifications for all users.

    This task runs periodically (hourly) to send digest summaries
    instead of individual notifications.
    """
    from sqlalchemy import func, select

    from app.database import get_celery_session_context
    from app.models.notification import Notification, NotificationStatus
    from app.models.notification_rule import NotificationRule

    async def _process():
        async with get_celery_session_context() as session:
            now = datetime.now(UTC)
            processed_count = 0

            # Find rules with digest enabled
            result = await session.execute(
                select(NotificationRule).where(
                    NotificationRule.digest_enabled.is_(True),
                    NotificationRule.is_active.is_(True),
                )
            )
            rules = result.scalars().all()

            for rule in rules:
                should_send = False

                if rule.digest_frequency == "hourly":
                    should_send = True
                elif rule.digest_frequency == "daily":
                    # Check if it's the configured time
                    if rule.user.notification_digest_time:
                        digest_hour = int(rule.user.notification_digest_time.split(":")[0])
                        if now.hour == digest_hour:
                            should_send = True
                    elif now.hour == 8:  # Default 8 AM
                        should_send = True
                elif rule.digest_frequency == "weekly":  # noqa: SIM102
                    # Send on Monday
                    if now.weekday() == 0 and now.hour == 8:
                        should_send = True

                if not should_send:
                    continue

                # Check if digest was already sent recently
                if rule.last_digest_sent:
                    if rule.digest_frequency == "hourly":
                        cutoff = now - timedelta(minutes=50)
                    elif rule.digest_frequency == "daily":
                        cutoff = now - timedelta(hours=20)
                    else:  # weekly
                        cutoff = now - timedelta(days=6)

                    if rule.last_digest_sent > cutoff:
                        continue

                # Count pending notifications for this rule
                count_result = await session.execute(
                    select(func.count(Notification.id)).where(
                        Notification.rule_id == rule.id,
                        Notification.status == NotificationStatus.PENDING,
                    )
                )
                pending_count = count_result.scalar() or 0

                if pending_count > 0:
                    # TODO: Create and send digest notification
                    # For now, just send individual notifications
                    pending_result = await session.execute(
                        select(Notification).where(
                            Notification.rule_id == rule.id,
                            Notification.status == NotificationStatus.PENDING,
                        ).limit(100)
                    )
                    for notification in pending_result.scalars():
                        send_notification.delay(str(notification.id))
                        processed_count += 1

                    rule.last_digest_sent = now

            await session.commit()
            return processed_count

    count = run_async(_process())

    logger.info(
        "Digest processing completed",
        processed_count=count,
    )
    return count


@celery_app.task(name="workers.notification_tasks.retry_failed")
def retry_failed():
    """Retry failed notifications that haven't exceeded max retries.

    This task runs periodically to pick up failed notifications
    and queue them for retry.
    """
    from app.database import get_celery_session_context
    from services.notifications.notification_service import NotificationService

    async def _retry():
        async with get_celery_session_context() as session:
            service = NotificationService(session)
            notifications = await service.get_failed_for_retry()

            for notification in notifications:
                send_notification.delay(str(notification.id))

            return len(notifications)

    count = run_async(_retry())

    logger.info(
        "Retry task completed",
        queued_for_retry=count,
    )
    return count


@celery_app.task(name="workers.notification_tasks.cleanup_old")
def cleanup_old():
    """Clean up old notifications.

    This task runs daily to delete old sent/failed notifications
    to prevent database bloat.
    """
    from app.database import get_celery_session_context
    from services.notifications.notification_service import NotificationService

    async def _cleanup():
        async with get_celery_session_context() as session:
            service = NotificationService(session)
            deleted_count = await service.cleanup_old_notifications(days=90)
            return deleted_count

    count = run_async(_cleanup())

    logger.info(
        "Cleanup task completed",
        deleted_count=count,
    )
    return count


@celery_app.task(name="workers.notification_tasks.send_pending")
def send_pending():
    """Send all pending notifications.

    This task can be called to process any notifications that
    are stuck in pending state.
    """
    from app.database import get_celery_session_context
    from services.notifications.notification_service import NotificationService

    async def _send_pending():
        async with get_celery_session_context() as session:
            service = NotificationService(session)
            notifications = await service.get_pending_notifications()

            for notification in notifications:
                send_notification.delay(str(notification.id))

            return len(notifications)

    count = run_async(_send_pending())

    logger.info(
        "Send pending task completed",
        queued_count=count,
    )
    return count
