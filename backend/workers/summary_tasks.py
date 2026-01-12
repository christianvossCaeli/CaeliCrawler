"""Celery tasks for custom summary scheduling.

This module provides background tasks for:
- Periodic checking of scheduled summaries
- Executing summaries based on their cron schedules
- Triggering summaries on crawl events
- Cleanup of old executions
- Checking for updates from data sources
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import structlog

from app.utils.cron import croniter_for_expression, get_schedule_timezone
from workers.async_runner import run_async
from workers.celery_app import celery_app

logger = structlog.get_logger(__name__)

# Redis key prefix for check-updates progress tracking
CHECK_UPDATES_PROGRESS_PREFIX = "summary:check_updates:"


def calculate_next_run(cron_expression: str, from_time: datetime = None) -> datetime:
    """Calculate the next run time from a cron expression.

    Args:
        cron_expression: The cron expression to use.
        from_time: The base time to calculate from. If None, uses current time.
                   This is important to avoid skipping scheduled times if
                   execution is delayed.

    Returns:
        The next scheduled run time.
    """
    schedule_tz = get_schedule_timezone()
    base_time = from_time or datetime.now(schedule_tz)

    # Ensure base_time has timezone info
    if base_time.tzinfo is None:
        base_time = schedule_tz.localize(base_time)

    cron = croniter_for_expression(cron_expression, base_time)
    return cron.get_next(datetime)


@celery_app.task(
    bind=True,
    name="workers.summary_tasks.check_scheduled_summaries",
    max_retries=3,
    default_retry_delay=30,
    retry_backoff=True,
    retry_backoff_max=300,
    autoretry_for=(Exception,),
    retry_jitter=True,
)
def check_scheduled_summaries(self):
    """Check and execute scheduled summaries.

    This task runs periodically (default: every 60 seconds) and triggers
    execution for any summary that is due based on its schedule_cron.
    """
    from sqlalchemy import select

    from app.database import get_celery_session_context
    from app.models import CustomSummary
    from app.models.custom_summary import SummaryStatus, SummaryTriggerType

    async def _check_and_execute():
        async with get_celery_session_context() as session:
            schedule_tz = get_schedule_timezone()
            now = datetime.now(schedule_tz)

            # Get all summaries due for execution (cron trigger type)
            result = await session.execute(
                select(CustomSummary)
                .where(
                    CustomSummary.schedule_enabled.is_(True),
                    CustomSummary.trigger_type == SummaryTriggerType.CRON,
                    CustomSummary.status == SummaryStatus.ACTIVE,
                    CustomSummary.next_run_at <= now,
                )
                .with_for_update(skip_locked=True)
            )
            summaries = result.scalars().all()

            if not summaries:
                logger.debug("summary_schedule_check_completed", total_due=0, triggered=0)
                return

            trigger_summaries = []
            for summary in summaries:
                if not summary.schedule_cron:
                    continue
                try:
                    # Calculate next run from the SCHEDULED time, not current time
                    # This ensures we don't skip scheduled windows if execution is delayed
                    # Example: If scheduled for 10:00 and we check at 10:02,
                    # next run should be calculated from 10:00, not 10:02
                    base_time = summary.next_run_at or now
                    summary.next_run_at = calculate_next_run(summary.schedule_cron, base_time)
                    trigger_summaries.append(summary)
                except Exception as exc:
                    logger.warning(
                        "summary_schedule_invalid",
                        summary_id=str(summary.id),
                        summary_name=summary.name,
                        cron=summary.schedule_cron,
                        error=str(exc),
                    )

            await session.commit()

            triggered = 0
            for summary in trigger_summaries:
                execute_summary_task.delay(str(summary.id), "cron")
                triggered += 1

                logger.info(
                    "summary_scheduled_execution_triggered",
                    summary_id=str(summary.id),
                    summary_name=summary.name,
                    next_run_at=summary.next_run_at.isoformat() if summary.next_run_at else None,
                )

            logger.info(
                "summary_schedule_check_completed",
                total_due=len(summaries),
                triggered=triggered,
            )

    run_async(_check_and_execute())


@celery_app.task(
    bind=True,
    name="workers.summary_tasks.execute_summary_task",
    max_retries=3,
    default_retry_delay=60,  # 1 minute
    retry_backoff=True,
    retry_backoff_max=600,  # 10 minutes max
    retry_jitter=True,
    acks_late=True,  # Acknowledge after completion for reliability
    reject_on_worker_lost=True,  # Requeue if worker dies
)
def execute_summary_task(self, summary_id: str, triggered_by: str = "manual", trigger_details: dict = None):
    """Execute a single summary.

    This task:
    1. Loads the summary with all widgets
    2. Executes queries for each widget
    3. Checks relevance (if enabled)
    4. Caches results
    5. Emits notification if relevant changes detected

    Args:
        summary_id: UUID of the CustomSummary to execute.
        triggered_by: Who/what triggered (manual, cron, crawl_event).
        trigger_details: Additional context (e.g., crawl_job_id).
    """
    from app.database import get_celery_session_context
    from app.models import CustomSummary
    from app.models.custom_summary import SummaryStatus
    from app.models.summary_execution import ExecutionStatus
    from services.summaries import SummaryExecutor, should_notify_user

    async def _execute():
        async with get_celery_session_context() as session:
            summary = await session.get(CustomSummary, UUID(summary_id))

            if not summary:
                logger.error(
                    "summary_not_found",
                    summary_id=summary_id,
                )
                return {"success": False, "error": "Summary not found"}

            if summary.status not in (SummaryStatus.ACTIVE, SummaryStatus.DRAFT):
                logger.warning(
                    "summary_not_active",
                    summary_id=summary_id,
                    summary_name=summary.name,
                    status=summary.status.value,
                )
                return {"success": False, "error": "Summary is not active"}

            logger.info(
                "summary_execution_started",
                summary_id=summary_id,
                summary_name=summary.name,
                triggered_by=triggered_by,
            )

            try:
                executor = SummaryExecutor(session)
                execution = await executor.execute_summary(
                    summary_id=UUID(summary_id),
                    triggered_by=triggered_by,
                    trigger_details=trigger_details,
                    force=False,  # Respect relevance check for scheduled executions
                )

                # Always emit SUMMARY_UPDATED event for successful completions
                if execution.status == ExecutionStatus.COMPLETED:
                    from workers.notification_tasks import emit_event

                    emit_event.delay(
                        "SUMMARY_UPDATED",
                        {
                            "summary_id": str(summary.id),
                            "summary_name": summary.name,
                            "user_id": str(summary.user_id),
                            "execution_id": str(execution.id),
                            "has_changes": execution.has_changes,
                            "triggered_by": triggered_by,
                        },
                    )

                # Check if we should notify the user
                if execution.status == ExecutionStatus.COMPLETED and execution.has_changes:
                    from services.summaries.relevance_checker import RelevanceCheckResult

                    # Create a result object for notification check
                    result = RelevanceCheckResult(
                        should_update=True,
                        score=execution.relevance_score or 0.5,
                        reason=execution.relevance_reason or "Changes detected",
                    )

                    if should_notify_user(result, notification_threshold=0.5):
                        # Emit notification
                        from workers.notification_tasks import emit_event

                        emit_event.delay(
                            "SUMMARY_RELEVANT_CHANGES",
                            {
                                "summary_id": str(summary.id),
                                "summary_name": summary.name,
                                "user_id": str(summary.user_id),
                                "execution_id": str(execution.id),
                                "relevance_score": execution.relevance_score,
                                "relevance_reason": execution.relevance_reason,
                            },
                        )
                        logger.info(
                            "summary_notification_triggered",
                            summary_id=summary_id,
                            execution_id=str(execution.id),
                        )

                logger.info(
                    "summary_execution_completed",
                    summary_id=summary_id,
                    summary_name=summary.name,
                    execution_id=str(execution.id),
                    status=execution.status.value,
                    has_changes=execution.has_changes,
                    duration_ms=execution.duration_ms,
                )

                return {
                    "success": True,
                    "execution_id": str(execution.id),
                    "status": execution.status.value,
                    "has_changes": execution.has_changes,
                    "duration_ms": execution.duration_ms,
                }

            except Exception as e:
                logger.exception(
                    "summary_execution_failed",
                    summary_id=summary_id,
                    summary_name=summary.name if summary else "unknown",
                    error=str(e),
                )
                # Re-raise to trigger Celery retry
                raise self.retry(exc=e) from None

    return run_async(_execute())


@celery_app.task(
    bind=True,
    name="workers.summary_tasks.on_crawl_completed",
    max_retries=3,
    default_retry_delay=30,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    acks_late=True,
    reject_on_worker_lost=True,
)
def on_crawl_completed(self, crawl_job_id: str, category_id: str):
    """Event handler: Trigger summaries when a crawl completes.

    This task is called after a crawl job completes and triggers:
    1. Summaries configured with trigger_type=CRAWL_CATEGORY for this category
    2. Summaries configured with trigger_type=AUTO that reference matching entity types

    Args:
        crawl_job_id: UUID of the completed crawl job.
        category_id: UUID of the category that was crawled.
    """
    from sqlalchemy import select

    from app.database import get_celery_session_context
    from app.models import CustomSummary
    from app.models.custom_summary import SummaryStatus, SummaryTriggerType
    from services.summaries.source_resolver import find_summaries_for_category_crawl

    async def _trigger_summaries():
        async with get_celery_session_context() as session:
            triggered_ids: set[UUID] = set()  # Track to avoid double-triggering
            triggered = 0

            # 1. Find summaries triggered by CRAWL_CATEGORY (direct link)
            result = await session.execute(
                select(CustomSummary).where(
                    CustomSummary.trigger_type == SummaryTriggerType.CRAWL_CATEGORY,
                    CustomSummary.trigger_category_id == UUID(category_id),
                    CustomSummary.status == SummaryStatus.ACTIVE,
                )
            )
            direct_summaries = result.scalars().all()

            for summary in direct_summaries:
                execute_summary_task.delay(
                    str(summary.id),
                    "crawl_event",
                    {"crawl_job_id": crawl_job_id, "category_id": category_id},
                )
                triggered_ids.add(summary.id)
                triggered += 1

                logger.info(
                    "summary_triggered_by_crawl",
                    summary_id=str(summary.id),
                    summary_name=summary.name,
                    crawl_job_id=crawl_job_id,
                    category_id=category_id,
                    trigger_type="CRAWL_CATEGORY",
                )

            # 2. Find AUTO summaries with matching entity types
            auto_matches = await find_summaries_for_category_crawl(session, UUID(category_id))

            auto_triggered_count = 0
            for summary, matched_entity_types in auto_matches:
                # Skip if already triggered via CRAWL_CATEGORY
                if summary.id in triggered_ids:
                    logger.debug(
                        "summary_already_triggered",
                        summary_id=str(summary.id),
                        reason="already triggered via CRAWL_CATEGORY",
                    )
                    continue

                # Trigger the summary
                execute_summary_task.delay(
                    str(summary.id),
                    "crawl_event",
                    {
                        "crawl_job_id": crawl_job_id,
                        "category_id": category_id,
                        "trigger_reason": "auto_entity_match",
                        "matched_entity_types": matched_entity_types,
                    },
                )
                triggered_ids.add(summary.id)
                triggered += 1
                auto_triggered_count += 1

                # Update last_auto_trigger_reason for transparency
                summary.last_auto_trigger_reason = f"Matched: {', '.join(matched_entity_types)}"

                logger.info(
                    "summary_triggered_by_crawl",
                    summary_id=str(summary.id),
                    summary_name=summary.name,
                    crawl_job_id=crawl_job_id,
                    category_id=category_id,
                    trigger_type="AUTO",
                    matched_entity_types=matched_entity_types,
                )

            # Batch commit all AUTO trigger reason updates
            if auto_triggered_count > 0:
                await session.commit()

            if triggered == 0:
                logger.debug(
                    "crawl_completed_no_summaries_to_trigger",
                    crawl_job_id=crawl_job_id,
                    category_id=category_id,
                )

            return {"triggered": triggered, "direct": len(direct_summaries), "auto": len(auto_matches)}

    try:
        return run_async(_trigger_summaries())
    except Exception as e:
        logger.exception(
            "on_crawl_completed_failed",
            crawl_job_id=crawl_job_id,
            category_id=category_id,
            error=str(e),
        )
        raise self.retry(exc=e) from None


@celery_app.task(
    bind=True,
    name="workers.summary_tasks.on_preset_completed",
    max_retries=3,
    default_retry_delay=30,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    acks_late=True,
    reject_on_worker_lost=True,
)
def on_preset_completed(self, preset_id: str):
    """Event handler: Trigger summaries when a crawl preset completes.

    This task is called after a crawl preset execution completes and
    triggers any summaries configured with trigger_type=crawl_preset.

    Args:
        preset_id: UUID of the completed crawl preset.
    """
    from sqlalchemy import select

    from app.database import get_celery_session_context
    from app.models import CustomSummary
    from app.models.custom_summary import SummaryStatus, SummaryTriggerType

    async def _trigger_summaries():
        async with get_celery_session_context() as session:
            # Find summaries triggered by this preset
            result = await session.execute(
                select(CustomSummary).where(
                    CustomSummary.trigger_type == SummaryTriggerType.CRAWL_PRESET,
                    CustomSummary.trigger_preset_id == UUID(preset_id),
                    CustomSummary.status == SummaryStatus.ACTIVE,
                )
            )
            summaries = result.scalars().all()

            if not summaries:
                logger.debug(
                    "preset_completed_no_summaries_to_trigger",
                    preset_id=preset_id,
                )
                return {"triggered": 0}

            triggered = 0
            for summary in summaries:
                execute_summary_task.delay(
                    str(summary.id),
                    "crawl_event",
                    {"preset_id": preset_id},
                )
                triggered += 1

                logger.info(
                    "summary_triggered_by_preset",
                    summary_id=str(summary.id),
                    summary_name=summary.name,
                    preset_id=preset_id,
                )

            return {"triggered": triggered}

    try:
        return run_async(_trigger_summaries())
    except Exception as e:
        logger.exception(
            "on_preset_completed_failed",
            preset_id=preset_id,
            error=str(e),
        )
        raise self.retry(exc=e) from None


@celery_app.task(
    bind=True,
    name="workers.summary_tasks.cleanup_old_executions",
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
)
def cleanup_old_executions(self, max_age_days: int = 30):
    """Cleanup old summary executions.

    This task runs daily and removes old execution records
    while keeping the most recent ones for each summary.

    Args:
        max_age_days: Maximum age of executions to keep (default: 30 days).
    """
    from sqlalchemy import delete, select

    from app.database import get_celery_session_context
    from app.models import SummaryExecution

    async def _cleanup():
        async with get_celery_session_context() as session:
            cutoff_date = datetime.now(UTC) - timedelta(days=max_age_days)

            # Get executions to keep (most recent 10 per summary)
            # This is a subquery to find the IDs to KEEP
            (select(SummaryExecution.id).where(SummaryExecution.created_at >= cutoff_date))

            # For older executions, keep only the most recent 5 per summary
            # This is complex in SQL, so we'll do it in two steps

            # Step 1: Delete old executions (older than cutoff)
            # But keep at least 5 per summary
            result = await session.execute(
                select(SummaryExecution.id, SummaryExecution.summary_id, SummaryExecution.created_at)
                .where(SummaryExecution.created_at < cutoff_date)
                .order_by(SummaryExecution.summary_id, SummaryExecution.created_at.desc())
            )
            old_executions = result.all()

            # Group by summary and keep newest 5
            from collections import defaultdict

            by_summary = defaultdict(list)
            for exec_id, summary_id, _created_at in old_executions:
                by_summary[summary_id].append(exec_id)

            delete_ids = []
            for _summary_id, exec_ids in by_summary.items():
                # Keep first 5 (newest), delete the rest
                if len(exec_ids) > 5:
                    delete_ids.extend(exec_ids[5:])

            if delete_ids:
                await session.execute(delete(SummaryExecution).where(SummaryExecution.id.in_(delete_ids)))
                await session.commit()

            logger.info(
                "summary_execution_cleanup_completed",
                deleted_count=len(delete_ids),
                cutoff_date=cutoff_date.isoformat(),
            )

            return {"deleted": len(delete_ids)}

    try:
        return run_async(_cleanup())
    except Exception as e:
        logger.exception(
            "cleanup_old_executions_failed",
            max_age_days=max_age_days,
            error=str(e),
        )
        raise self.retry(exc=e) from None


def _get_redis_client():
    """Get Redis client for progress tracking."""
    from workers.celery_app import celery_app

    return celery_app.backend.client


def _update_check_progress(
    task_id: str,
    status: str,
    total_sources: int,
    completed_sources: int = 0,
    current_source: str | None = None,
    message: str = "",
    error: str | None = None,
):
    """Update progress in Redis for a check-updates task."""
    import json

    redis = _get_redis_client()
    key = f"{CHECK_UPDATES_PROGRESS_PREFIX}{task_id}"
    data = {
        "status": status,
        "total_sources": total_sources,
        "completed_sources": completed_sources,
        "current_source": current_source,
        "message": message,
        "error": error,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    redis.setex(key, 3600, json.dumps(data))  # Expire after 1 hour


def get_check_progress(task_id: str) -> dict[str, Any] | None:
    """Get progress for a check-updates task from Redis."""
    import json

    redis = _get_redis_client()
    key = f"{CHECK_UPDATES_PROGRESS_PREFIX}{task_id}"
    data = redis.get(key)
    if data:
        return json.loads(data)
    return None


@celery_app.task(
    bind=True,
    name="workers.summary_tasks.check_summary_updates",
    max_retries=2,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=300,
    time_limit=1800,  # 30 minutes max
    soft_time_limit=1500,  # 25 minutes soft limit
    acks_late=True,
    reject_on_worker_lost=True,
)
def check_summary_updates(
    self,
    summary_id: str,
    source_ids: list[str],
    source_names: list[str],
    user_id: str,
    external_api_ids: list[str] = None,
):
    """
    Check for updates by crawling relevant data sources, syncing external APIs,
    and refreshing the summary.

    This task:
    1. Creates crawl jobs for all provided data sources
    2. Syncs all provided external APIs
    3. Tracks progress as each source completes
    4. After all jobs complete, executes the summary with force=True

    Args:
        summary_id: UUID of the CustomSummary
        source_ids: List of DataSource UUIDs to crawl
        source_names: List of source names for progress display
        user_id: UUID of the user who triggered this
        external_api_ids: List of APIConfiguration UUIDs to sync (optional)
    """
    import time

    from sqlalchemy import select

    from app.database import get_celery_session_context
    from app.models import CrawlJob, JobStatus
    from app.models.data_source_category import DataSourceCategory
    from workers.crawl_tasks import create_crawl_job

    external_api_ids = external_api_ids or []
    task_id = self.request.id
    total_sources = len(source_ids) + len(external_api_ids)

    # Initialize progress
    _update_check_progress(
        task_id=task_id,
        status="pending",
        total_sources=total_sources,
        message=f"Starte Prüfung von {total_sources} Quellen...",
    )

    logger.info(
        "check_summary_updates_started",
        summary_id=summary_id,
        source_count=total_sources,
        task_id=task_id,
    )

    async def _check_updates():
        async with get_celery_session_context() as session:
            # Create crawl jobs for each data source
            job_ids = []
            source_to_name = dict(zip(source_ids, source_names, strict=False))

            _update_check_progress(
                task_id=task_id,
                status="crawling",
                total_sources=total_sources,
                completed_sources=0,
                message=f"Starte Aktualisierung von {total_sources} Quellen...",
            )

            # 1. Process DataSource crawl jobs
            for i, source_id in enumerate(source_ids):
                # Get the primary category for this source
                cat_result = await session.execute(
                    select(DataSourceCategory.category_id)
                    .where(DataSourceCategory.data_source_id == UUID(source_id))
                    .limit(1)
                )
                cat_row = cat_result.first()
                if not cat_row:
                    logger.warning(
                        "source_has_no_category",
                        source_id=source_id,
                    )
                    continue

                category_id = str(cat_row[0])

                # Create crawl job (will skip if already running)
                job_id = create_crawl_job(source_id, category_id, force=False)
                if job_id:
                    job_ids.append((job_id, source_id))

                _update_check_progress(
                    task_id=task_id,
                    status="crawling",
                    total_sources=total_sources,
                    completed_sources=0,
                    current_source=source_to_name.get(source_id, source_id),
                    message=f"Jobs erstellt: {i + 1} von {len(source_ids)} Crawl-Jobs",
                )

            # 2. Sync external APIs
            api_sync_results = []
            if external_api_ids:
                from app.models.api_configuration import APIConfiguration
                from external_apis.sync_service import ExternalAPISyncService

                for i, api_id in enumerate(external_api_ids):
                    # Use selectinload to eagerly load data_source relationship
                    from sqlalchemy.orm import selectinload

                    api_result = await session.execute(
                        select(APIConfiguration)
                        .options(selectinload(APIConfiguration.data_source))
                        .where(APIConfiguration.id == UUID(api_id))
                    )
                    api_config = api_result.scalar_one_or_none()
                    if not api_config:
                        logger.warning("api_configuration_not_found", api_id=api_id)
                        continue

                    config_name = api_config.data_source.name if api_config.data_source else f"API {api_id[:8]}"
                    api_name = f"API: {config_name}"
                    _update_check_progress(
                        task_id=task_id,
                        status="crawling",
                        total_sources=total_sources,
                        completed_sources=len(job_ids) + i,
                        current_source=api_name,
                        message=f"Synchronisiere {api_name}...",
                    )

                    try:
                        async with ExternalAPISyncService(session) as sync_service:
                            result = await sync_service.sync_source(api_config)
                            api_sync_results.append(
                                {
                                    "api_id": api_id,
                                    "success": True,
                                    "created": result.entities_created,
                                    "updated": result.entities_updated,
                                }
                            )
                            logger.info(
                                "external_api_synced",
                                api_id=api_id,
                                api_name=config_name,
                                created=result.entities_created,
                                updated=result.entities_updated,
                            )
                    except Exception as e:
                        logger.error(
                            "external_api_sync_failed",
                            api_id=api_id,
                            error=str(e),
                        )
                        api_sync_results.append(
                            {
                                "api_id": api_id,
                                "success": False,
                                "error": str(e),
                            }
                        )

            total_jobs = len(job_ids) + len(api_sync_results)
            if total_jobs == 0 and not external_api_ids:
                _update_check_progress(
                    task_id=task_id,
                    status="completed",
                    total_sources=total_sources,
                    completed_sources=total_sources,
                    message="Keine neuen Jobs erstellt (alle bereits aktiv)",
                )
                # Still execute the summary to refresh with existing data
                execute_summary_task.delay(summary_id, "check_updates", {"task_id": task_id})
                return {"success": True, "jobs_created": 0}

            # External APIs are already synced, count them as completed
            api_completed = len(api_sync_results)

            # Wait for crawl jobs to complete
            crawl_completed = 0
            max_wait_seconds = 1200  # 20 minutes max wait
            poll_interval = 5  # Check every 5 seconds
            elapsed = 0

            while job_ids and crawl_completed < len(job_ids) and elapsed < max_wait_seconds:
                await session.expire_all()

                crawl_completed = 0
                for job_id, _source_id in job_ids:
                    job = await session.get(CrawlJob, UUID(job_id))
                    if job and job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                        crawl_completed += 1

                current_source_name = None
                for job_id, source_id in job_ids:
                    job = await session.get(CrawlJob, UUID(job_id))
                    if job and job.status == JobStatus.RUNNING:
                        current_source_name = source_to_name.get(source_id, source_id)
                        break

                total_completed = api_completed + crawl_completed
                _update_check_progress(
                    task_id=task_id,
                    status="crawling",
                    total_sources=total_sources,
                    completed_sources=total_completed,
                    current_source=current_source_name,
                    message=f"{total_completed} von {total_sources} Quellen geprüft",
                )

                if crawl_completed < len(job_ids):
                    time.sleep(poll_interval)
                    elapsed += poll_interval

            # All jobs done (or timeout), now update the summary
            total_completed = api_completed + crawl_completed
            _update_check_progress(
                task_id=task_id,
                status="updating",
                total_sources=total_sources,
                completed_sources=total_completed,
                message="Aktualisiere Zusammenfassung...",
            )

            # Execute summary with force=True to ensure update
            from app.models import CustomSummary
            from services.summaries import SummaryExecutor

            summary = await session.get(CustomSummary, UUID(summary_id))
            if summary:
                executor = SummaryExecutor(session)
                execution = await executor.execute_summary(
                    summary_id=UUID(summary_id),
                    triggered_by="check_updates",
                    trigger_details={
                        "task_id": task_id,
                        "crawls_completed": crawl_completed,
                        "apis_synced": api_completed,
                    },
                    force=True,
                )

                _update_check_progress(
                    task_id=task_id,
                    status="completed",
                    total_sources=total_sources,
                    completed_sources=total_completed,
                    message=f"Fertig! {total_completed} Quellen geprüft, Zusammenfassung aktualisiert.",
                )

                logger.info(
                    "check_summary_updates_completed",
                    summary_id=summary_id,
                    task_id=task_id,
                    crawls_completed=crawl_completed,
                    apis_synced=api_completed,
                    execution_id=str(execution.id),
                )

                return {
                    "success": True,
                    "crawl_jobs": len(job_ids),
                    "crawls_completed": crawl_completed,
                    "apis_synced": api_completed,
                    "execution_id": str(execution.id),
                }
            else:
                _update_check_progress(
                    task_id=task_id,
                    status="failed",
                    total_sources=total_sources,
                    completed_sources=total_completed,
                    message="Zusammenfassung nicht gefunden",
                    error="Summary not found",
                )
                return {"success": False, "error": "Summary not found"}

    try:
        return run_async(_check_updates())
    except celery_app.SoftTimeLimitExceeded:
        # Graceful handling of timeout - update progress and log
        logger.warning(
            "check_summary_updates_timeout",
            summary_id=summary_id,
            task_id=task_id,
            soft_limit=1500,
        )
        _update_check_progress(
            task_id=task_id,
            status="failed",
            total_sources=total_sources,
            completed_sources=0,
            message="Zeitüberschreitung bei der Aktualisierung (25 Minuten)",
            error="Task timed out after 25 minutes",
        )
        raise
    except Exception as e:
        logger.exception(
            "check_summary_updates_failed",
            summary_id=summary_id,
            task_id=task_id,
            error=str(e),
        )
        _update_check_progress(
            task_id=task_id,
            status="failed",
            total_sources=total_sources,
            completed_sources=0,
            message="Fehler bei der Aktualisierung",
            error=str(e),
        )
        raise self.retry(exc=e) from None
