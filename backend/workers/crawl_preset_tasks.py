"""Celery tasks for crawl preset scheduling.

This module provides background tasks for:
- Periodic checking of scheduled crawl presets
- Executing crawl presets based on their cron schedules
"""

from datetime import datetime, timezone
from uuid import UUID

import structlog
from app.utils.cron import croniter_for_expression

from workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


def calculate_next_run(cron_expression: str) -> datetime:
    """Calculate the next run time from a cron expression."""
    cron = croniter_for_expression(cron_expression, datetime.now(timezone.utc))
    return cron.get_next(datetime)


@celery_app.task(name="workers.crawl_preset_tasks.check_scheduled_presets")
def check_scheduled_presets():
    """Check and execute scheduled crawl presets.

    This task runs periodically (default: every few seconds) and triggers
    execution for any preset that is due based on its schedule_cron.
    """
    from app.database import get_celery_session_context
    from app.models import CrawlPreset, PresetStatus
    from sqlalchemy import select
    import asyncio

    async def _check_and_execute():
        async with get_celery_session_context() as session:
            now = datetime.now(timezone.utc)

            # Get all presets due for execution
            result = await session.execute(
                select(CrawlPreset).where(
                    CrawlPreset.schedule_enabled.is_(True),
                    CrawlPreset.status == PresetStatus.ACTIVE,
                    CrawlPreset.next_run_at <= now,
                )
            )
            presets = result.scalars().all()

            triggered = 0
            for preset in presets:
                # Trigger async execution task
                execute_crawl_preset.delay(str(preset.id))
                triggered += 1

                # Update next_run_at immediately to prevent duplicate triggers
                if preset.schedule_cron:
                    preset.next_run_at = calculate_next_run(preset.schedule_cron)
                    await session.commit()

                logger.info(
                    "crawl_preset_scheduled_execution_triggered",
                    preset_id=str(preset.id),
                    preset_name=preset.name,
                    next_run_at=preset.next_run_at.isoformat() if preset.next_run_at else None,
                )

            logger.info(
                "crawl_preset_schedule_check_completed",
                total_due=len(presets),
                triggered=triggered,
            )

    asyncio.run(_check_and_execute())


@celery_app.task(
    bind=True,
    name="workers.crawl_preset_tasks.execute_crawl_preset",
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
    retry_backoff=True,
    retry_backoff_max=1800,  # 30 minutes max
)
def execute_crawl_preset(self, preset_id: str):
    """Execute a single crawl preset.

    This task:
    1. Loads the preset configuration
    2. Finds matching data sources using the stored filters
    3. Creates crawl jobs for each matched source
    4. Updates execution statistics

    Args:
        preset_id: UUID of the CrawlPreset to execute.
    """
    from app.database import get_celery_session_context
    from app.models import CrawlPreset, PresetStatus
    from services.smart_query.crawl_operations import find_sources_for_crawl, start_crawl_jobs
    import asyncio

    async def _execute():
        async with get_celery_session_context() as session:
            preset = await session.get(CrawlPreset, UUID(preset_id))

            if not preset:
                logger.error(
                    "crawl_preset_not_found",
                    preset_id=preset_id,
                )
                return {"success": False, "error": "Preset not found"}

            if preset.status != PresetStatus.ACTIVE:
                logger.warning(
                    "crawl_preset_not_active",
                    preset_id=preset_id,
                    preset_name=preset.name,
                    status=preset.status.value,
                )
                return {"success": False, "error": "Preset is not active"}

            logger.info(
                "crawl_preset_execution_started",
                preset_id=preset_id,
                preset_name=preset.name,
                filters=preset.filters,
            )

            try:
                # Find matching sources using the preset's filter configuration
                sources = await find_sources_for_crawl(
                    session,
                    preset.filters,
                    limit=10000,
                )

                if not sources:
                    logger.info(
                        "crawl_preset_no_sources_matched",
                        preset_id=preset_id,
                        preset_name=preset.name,
                    )
                    return {
                        "success": True,
                        "jobs_created": 0,
                        "sources_matched": 0,
                        "message": "No sources matched the preset filters",
                    }

                # Start crawl jobs for all matched sources
                job_ids = await start_crawl_jobs(
                    session,
                    sources,
                    force=False,  # Respect crawl cooldown for scheduled executions
                )

                # Update execution statistics
                preset.last_scheduled_run_at = datetime.now(timezone.utc)
                await session.commit()

                logger.info(
                    "crawl_preset_execution_completed",
                    preset_id=preset_id,
                    preset_name=preset.name,
                    sources_matched=len(sources),
                    jobs_created=len(job_ids),
                )

                return {
                    "success": True,
                    "jobs_created": len(job_ids),
                    "job_ids": [str(jid) for jid in job_ids],
                    "sources_matched": len(sources),
                    "message": f"Started {len(job_ids)} crawl jobs",
                }

            except Exception as e:
                logger.exception(
                    "crawl_preset_execution_failed",
                    preset_id=preset_id,
                    preset_name=preset.name,
                    error=str(e),
                )
                # Re-raise to trigger Celery retry
                raise self.retry(exc=e)

    return asyncio.run(_execute())


@celery_app.task(name="workers.crawl_preset_tasks.cleanup_archived_presets")
def cleanup_archived_presets():
    """Cleanup old archived presets.

    This task runs weekly and removes archived presets that
    haven't been used in the last 90 days.
    """
    from app.database import get_celery_session_context
    from app.models import CrawlPreset, PresetStatus
    from sqlalchemy import select, delete
    from datetime import timedelta
    import asyncio

    async def _cleanup():
        async with get_celery_session_context() as session:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)

            # Delete old archived presets that haven't been used
            result = await session.execute(
                delete(CrawlPreset).where(
                    CrawlPreset.status == PresetStatus.ARCHIVED,
                    CrawlPreset.is_favorite.is_(False),  # Never delete favorites
                    CrawlPreset.last_used_at < cutoff_date,
                ).returning(CrawlPreset.id)
            )
            deleted_ids = result.scalars().all()
            await session.commit()

            logger.info(
                "crawl_preset_cleanup_completed",
                deleted_count=len(deleted_ids),
                cutoff_date=cutoff_date.isoformat(),
            )

    asyncio.run(_cleanup())
