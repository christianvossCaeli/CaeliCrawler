"""Celery application configuration."""

from datetime import timedelta

import structlog
from celery import Celery
from celery.schedules import crontab
from celery.signals import (
    task_failure,
    task_retry,
    task_revoked,
    task_success,
    worker_process_init,
    worker_process_shutdown,
    worker_shutdown,
)

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
        "workers.ai_tasks",  # Now a package with sub-modules
        "workers.notification_tasks",
        "workers.external_api_tasks",
        "workers.export_tasks",
        "workers.crawl_preset_tasks",
        "workers.api_facet_sync_tasks",
        "workers.summary_tasks",
        "workers.maintenance_tasks",
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

    # Dead Letter Queue (DLQ) configuration
    # Failed tasks after max_retries are sent to DLQ for later analysis
    # Note: task_reject_on_worker_lost is already set above
    task_acks_on_failure_or_timeout=False,

    # Task routing with DLQ support
    # Note: Requires RabbitMQ with dead letter exchange configured:
    # rabbitmqctl set_policy DLX ".*" '{"dead-letter-exchange":"dlx"}' --apply-to queues
    task_routes={
        "workers.crawl_tasks.*": {"queue": "crawl"},
        "workers.processing_tasks.*": {"queue": "processing"},
        "workers.ai_tasks.*": {"queue": "ai"},
        "workers.notification_tasks.*": {"queue": "notification"},
        "workers.export_tasks.*": {"queue": "processing"},
        "workers.crawl_preset_tasks.*": {"queue": "crawl"},
        "workers.api_facet_sync_tasks.*": {"queue": "processing"},
        "workers.summary_tasks.*": {"queue": "processing"},
        "workers.maintenance_tasks.*": {"queue": "default"},  # Lightweight, runs on default
    },

    # Queue declarations with dead letter exchange
    task_queues={
        "default": {
            "exchange": "default",
            "routing_key": "default",
            "queue_arguments": {
                "x-dead-letter-exchange": "dlx",
                "x-dead-letter-routing-key": "dlq",
            },
        },
        "crawl": {
            "exchange": "crawl",
            "routing_key": "crawl",
            "queue_arguments": {
                "x-dead-letter-exchange": "dlx",
                "x-dead-letter-routing-key": "dlq.crawl",
            },
        },
        "ai": {
            "exchange": "ai",
            "routing_key": "ai",
            "queue_arguments": {
                "x-dead-letter-exchange": "dlx",
                "x-dead-letter-routing-key": "dlq.ai",
            },
        },
        "processing": {
            "exchange": "processing",
            "routing_key": "processing",
            "queue_arguments": {
                "x-dead-letter-exchange": "dlx",
                "x-dead-letter-routing-key": "dlq.processing",
            },
        },
    },

    # Default queue
    task_default_queue="default",

    # Beat schedule for periodic tasks
    # NOTE: Task frequencies are tuned to balance responsiveness with connection usage
    # Higher frequencies = more DB connections, lower frequencies = slower response
    beat_schedule={
        # Category-based scheduled crawls (only for categories with schedule_enabled=True)
        "check-scheduled-crawls": {
            "task": "workers.crawl_tasks.check_scheduled_crawls",
            "schedule": timedelta(seconds=30),
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
        # Crawl Preset scheduling
        "check-scheduled-presets": {
            "task": "workers.crawl_preset_tasks.check_scheduled_presets",
            "schedule": timedelta(seconds=30),  # Reduced from 5s to prevent connection exhaustion
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
        # Custom Summary scheduling
        "check-scheduled-summaries": {
            "task": "workers.summary_tasks.check_scheduled_summaries",
            "schedule": timedelta(seconds=60),  # Every minute
        },
        "cleanup-summary-executions": {
            "task": "workers.summary_tasks.cleanup_old_executions",
            "schedule": crontab(hour=3, minute=30),  # Daily at 3:30 AM
        },
        # Database connection maintenance
        "cleanup-idle-connections": {
            "task": "workers.maintenance_tasks.cleanup_idle_connections",
            "schedule": timedelta(minutes=5),  # Every 5 minutes - safety net for orphaned connections
        },
        "log-connection-stats": {
            "task": "workers.maintenance_tasks.log_connection_stats",
            "schedule": timedelta(minutes=15),  # Every 15 minutes - for monitoring
        },
        # LLM Usage maintenance tasks
        "aggregate-llm-usage-monthly": {
            "task": "workers.maintenance_tasks.aggregate_llm_usage",
            "schedule": crontab(day_of_month=1, hour=3, minute=0),  # Monthly on 1st at 3 AM
        },
        "check-llm-budgets-daily": {
            "task": "workers.maintenance_tasks.check_llm_budgets",
            "schedule": crontab(hour=8, minute=0),  # Daily at 8 AM
        },
    },
)

# Task priorities
celery_app.conf.task_queue_max_priority = 10
celery_app.conf.task_default_priority = 5


@worker_process_init.connect
def configure_worker(**kwargs):
    """Configure worker process on initialization."""
    # NOTE: We intentionally DO NOT apply nest_asyncio anymore.
    # nest_asyncio was causing issues with asyncpg connections getting
    # "attached to a different loop". Instead, each task uses run_async()
    # which creates a fresh event loop per task execution.

    # Reset the database engine for this worker process
    # This ensures each worker has its own connection pool
    from app.database import reset_celery_engine
    reset_celery_engine()

    logger.info("worker_process_initialized", pid=kwargs.get("pid"))


@worker_process_shutdown.connect
def cleanup_worker_process(**kwargs):
    """Clean up database connections when worker process shuts down."""
    import asyncio

    from app.database import dispose_celery_engine_async

    logger.info("worker_process_shutting_down", pid=kwargs.get("pid"))

    try:
        # Create a new event loop for cleanup since the existing one may be closed
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(dispose_celery_engine_async())
        finally:
            loop.close()
    except Exception as e:
        logger.warning("worker_process_cleanup_error", error=str(e))


@worker_shutdown.connect
def cleanup_worker(**kwargs):
    """Clean up when the worker itself shuts down."""
    logger.info("worker_shutting_down")


@task_revoked.connect
def handle_task_revoked(sender=None, request=None, terminated=False, signum=None, expired=False, **kwargs):
    """Log when tasks are revoked (cancelled)."""
    logger.warning(
        "task_revoked",
        task_name=sender.name if sender else "unknown",
        task_id=request.id if request else None,
        terminated=terminated,
        expired=expired,
    )


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
            "workers.ai_tasks.analyze_entity_data_for_facets",
            "workers.ai_tasks.analyze_attachment_task",
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
    except Exception:  # noqa: S110
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
