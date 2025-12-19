"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init

from app.config import settings

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
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Berlin",
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
    },

    # Default queue
    task_default_queue="default",

    # Beat schedule for periodic tasks
    beat_schedule={
        "check-scheduled-crawls": {
            "task": "workers.crawl_tasks.check_scheduled_crawls",
            "schedule": crontab(minute="*/15"),  # Every 15 minutes
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
