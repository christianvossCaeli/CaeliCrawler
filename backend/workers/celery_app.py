"""Celery application configuration."""

from datetime import timedelta

from celery import Celery
from celery.schedules import crontab
from celery.signals import (
    task_failure,
    task_retry,
    task_success,
    worker_process_init,
)

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

# Note: nest_asyncio is ONLY applied in worker processes (see worker_process_init signal)
# NOT at module import time, because the backend uses uvloop which is incompatible

# Create Celery app
celery_app = Celery(
    "caelichrawler",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "workers.crawl_tasks",
        "workers.processing_tasks",
        "workers.ai_tasks",
        "workers.notification_tasks",
        "workers.external_api_tasks",
        "workers.export_tasks",
        "workers.api_template_tasks",
        "workers.crawl_preset_tasks",
        "workers.api_facet_sync_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.schedule_timezone,
    enable_utc=True,

    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,

    # Result backend settings
    result_expires=86400,  # 24 hours

    # Task routing
    task_routes={
        "workers.crawl_tasks.*": {"queue": "crawl"},
        "workers.processing_tasks.*": {"queue": "processing"},
        "workers.ai_tasks.*": {"queue": "ai"},
        "workers.notification_tasks.*": {"queue": "notification"},
        "workers.export_tasks.*": {"queue": "processing"},
        "workers.api_template_tasks.*": {"queue": "processing"},
        "workers.crawl_preset_tasks.*": {"queue": "crawl"},
        "workers.api_facet_sync_tasks.*": {"queue": "processing"},
    },

    # Default queue
    task_default_queue="default",

    # Beat schedule for periodic tasks
    beat_schedule={
        "check-scheduled-crawls": {
            "task": "workers.crawl_tasks.check_scheduled_crawls",
            "schedule": timedelta(seconds=5),  # High-frequency for seconds-level schedules
        },
        "cleanup-old-jobs": {
            "task": "workers.crawl_tasks.cleanup_old_jobs",
            "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
        },
        "process-pending-documents": {
            "task": "workers.processing_tasks.process_pending_documents",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
        },
        # Notification tasks
        "process-notification-digests": {
            "task": "workers.notification_tasks.process_digests",
            "schedule": crontab(minute=0),  # Every hour at :00
        },
        "retry-failed-notifications": {
            "task": "workers.notification_tasks.retry_failed",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
        },
        "cleanup-old-notifications": {
            "task": "workers.notification_tasks.cleanup_old",
            "schedule": crontab(hour=4, minute=0),  # Daily at 4 AM
        },
        "send-pending-notifications": {
            "task": "workers.notification_tasks.send_pending",
            "schedule": crontab(minute="*/2"),  # Every 2 minutes
        },
        # External API sync tasks
        "sync-external-apis": {
            "task": "workers.external_api_tasks.sync_all_external_apis",
            "schedule": crontab(minute=0, hour="*/4"),  # Every 4 hours
        },
        "cleanup-archived-sync-records": {
            "task": "workers.external_api_tasks.cleanup_archived_records",
            "schedule": crontab(hour=5, minute=0),  # Daily at 5 AM
        },
        # Export cleanup
        "cleanup-old-exports": {
            "task": "workers.export_tasks.cleanup_old_exports",
            "schedule": crontab(hour=6, minute=0),  # Daily at 6 AM
        },
        # API Template validation
        "validate-api-templates": {
            "task": "workers.api_template_tasks.validate_all_templates",
            "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
        },
        "cleanup-failed-templates": {
            "task": "workers.api_template_tasks.cleanup_failed_templates",
            "schedule": crontab(hour=3, minute=30, day_of_week=0),  # Weekly on Sunday at 3:30 AM
        },
        # Crawl Preset scheduling
        "check-scheduled-presets": {
            "task": "workers.crawl_preset_tasks.check_scheduled_presets",
            "schedule": timedelta(seconds=5),  # High-frequency for seconds-level schedules
        },
        "cleanup-archived-presets": {
            "task": "workers.crawl_preset_tasks.cleanup_archived_presets",
            "schedule": crontab(hour=4, minute=30, day_of_week=0),  # Weekly on Sunday at 4:30 AM
        },
        # API Facet Sync scheduling
        "check-scheduled-api-syncs": {
            "task": "workers.api_facet_sync_tasks.check_scheduled_api_syncs",
            "schedule": crontab(minute="*"),  # Every minute
        },
    },
)

# Task priorities
celery_app.conf.task_queue_max_priority = 10
celery_app.conf.task_default_priority = 5


@worker_process_init.connect
def configure_worker(**kwargs):
    """Configure worker process on initialization."""
    # Apply nest_asyncio ONLY in worker processes
    # This is necessary because Celery tasks use asyncio.run() with asyncpg
    # which requires nested event loop support
    import nest_asyncio
    nest_asyncio.apply()

    # Reset the database engine for this worker process
    # This ensures each worker has its own connection pool
    from app.database import reset_celery_engine
    reset_celery_engine()


# =============================================================================
# Task Signal Handlers for Monitoring
# =============================================================================


@task_success.connect
def handle_task_success(sender=None, result=None, **kwargs):
    """Log successful task completion for monitoring."""
    logger.info(
        "task_completed",
        task_name=sender.name if sender else "unknown",
        task_id=kwargs.get("task_id"),
        result_type=type(result).__name__ if result else None,
    )


@task_failure.connect
def handle_task_failure(sender=None, task_id=None, exception=None, traceback=None, **kwargs):
    """Log task failures for monitoring and alerting."""
    logger.error(
        "task_failed",
        task_name=sender.name if sender else "unknown",
        task_id=task_id,
        exception_type=type(exception).__name__ if exception else None,
        exception_message=str(exception) if exception else None,
    )

    # Emit notification for critical task failures
    try:
        from workers.notification_tasks import emit_event
        if sender and sender.name in (
            "workers.crawl_tasks.crawl_source",
            "workers.ai_tasks.analyze_document",
            "workers.ai_tasks.extract_pysis_fields",
        ):
            emit_event.delay(
                "SYSTEM_ERROR",
                {
                    "entity_type": "celery_task",
                    "entity_id": task_id,
                    "task_name": sender.name,
                    "error": str(exception) if exception else "Unknown error",
                }
            )
    except Exception:
        # Don't fail if notification can't be sent
        pass


@task_retry.connect
def handle_task_retry(sender=None, reason=None, **kwargs):
    """Log task retries for monitoring."""
    request = kwargs.get("request")
    logger.warning(
        "task_retry",
        task_name=sender.name if sender else "unknown",
        task_id=request.id if request else None,
        retry_count=request.retries if request else None,
        reason=str(reason) if reason else None,
    )
