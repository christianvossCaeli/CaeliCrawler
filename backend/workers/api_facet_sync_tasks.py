"""Celery tasks for scheduled API-to-Facet synchronization.

This module provides background tasks for:
- Periodic checking of scheduled API configuration syncs (facet mode)
- Executing API-to-Facet synchronization based on cron schedules
"""

from datetime import UTC, datetime
from uuid import UUID

import structlog

from app.utils.cron import croniter_for_expression, get_schedule_timezone
from workers.async_runner import run_async
from workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


def calculate_next_run(cron_expression: str) -> datetime:
    """Calculate the next run time from a cron expression."""
    schedule_tz = get_schedule_timezone()
    cron = croniter_for_expression(cron_expression, datetime.now(schedule_tz))
    return cron.get_next(datetime)


@celery_app.task(name="workers.api_facet_sync_tasks.check_scheduled_api_syncs")
def check_scheduled_api_syncs():
    """Check and execute scheduled API configuration syncs (facet mode).

    This task runs periodically (default: every minute) and triggers
    sync execution for any APIConfiguration that is due based on its next_run_at.
    Only configurations with import_mode=FACETS or BOTH are checked.
    """
    from sqlalchemy import select

    from app.database import get_celery_session_context
    from app.models.api_configuration import APIConfiguration, ImportMode

    async def _check_and_execute():
        async with get_celery_session_context() as session:
            schedule_tz = get_schedule_timezone()
            now = datetime.now(schedule_tz)

            # Get all configurations due for execution
            # Only configurations with:
            # - sync_enabled = true
            # - is_active = true
            # - next_run_at <= now
            # - import_mode in (FACETS, BOTH)
            # - facet_mappings is not empty
            result = await session.execute(
                select(APIConfiguration)
                .where(
                    APIConfiguration.sync_enabled.is_(True),
                    APIConfiguration.is_active.is_(True),
                    APIConfiguration.next_run_at <= now,
                    APIConfiguration.import_mode.in_([
                        ImportMode.FACETS.value,
                        ImportMode.BOTH.value,
                    ]),
                    APIConfiguration.facet_mappings != {},
                )
                .with_for_update(skip_locked=True)
            )
            configs = result.scalars().all()

            if not configs:
                return

            trigger_configs = []
            for config in configs:
                # Calculate next run based on sync_interval_hours
                # For more complex scheduling, you could add a schedule_cron field
                next_run = datetime.now(UTC)
                from datetime import timedelta
                next_run = next_run + timedelta(hours=config.sync_interval_hours)
                config.next_run_at = next_run
                trigger_configs.append(config)

            await session.commit()

            triggered = 0
            for config in trigger_configs:
                sync_api_config_to_facets.delay(str(config.id))
                triggered += 1

                logger.info(
                    "api_facet_sync_triggered",
                    config_id=str(config.id),
                    data_source_id=str(config.data_source_id),
                    next_run_at=config.next_run_at.isoformat() if config.next_run_at else None,
                )

            if triggered > 0:
                logger.info(
                    "api_facet_sync_check_completed",
                    total_due=len(configs),
                    triggered=triggered,
                )

    run_async(_check_and_execute())


@celery_app.task(
    bind=True,
    name="workers.api_facet_sync_tasks.sync_api_config_to_facets",
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
    retry_backoff=True,
    retry_backoff_max=1800,  # 30 minutes max
)
def sync_api_config_to_facets(self, config_id: str):
    """Execute facet sync for a single API configuration.

    This task:
    1. Loads the configuration
    2. Fetches data from the external API
    3. Matches API records to entities
    4. Creates/updates FacetValueHistory entries

    Args:
        config_id: UUID of the APIConfiguration to sync.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.database import get_celery_session_context
    from app.models.api_configuration import APIConfiguration, ImportMode
    from services.api_facet_sync_service import APIFacetSyncService

    async def _sync():
        async with get_celery_session_context() as session:
            # Use selectinload to eagerly load data_source relationship
            result = await session.execute(
                select(APIConfiguration)
                .options(selectinload(APIConfiguration.data_source))
                .where(APIConfiguration.id == UUID(config_id))
            )
            config = result.scalar_one_or_none()

            if not config:
                logger.error(
                    "api_configuration_not_found",
                    config_id=config_id,
                )
                return {"success": False, "error": "Configuration not found"}

            if not config.is_active:
                logger.warning(
                    "api_configuration_not_active",
                    config_id=config_id,
                    data_source_id=str(config.data_source_id),
                )
                return {"success": False, "error": "Configuration is not active"}

            # Verify this is a facet sync config
            if config.import_mode not in [ImportMode.FACETS.value, ImportMode.BOTH.value]:
                logger.warning(
                    "api_configuration_wrong_mode",
                    config_id=config_id,
                    import_mode=config.import_mode,
                )
                return {"success": False, "error": f"Wrong import mode: {config.import_mode}"}

            logger.info(
                "api_facet_sync_starting",
                config_id=config_id,
                data_source_id=str(config.data_source_id),
                api_url=config.get_full_url(),
            )

            try:
                service = APIFacetSyncService(session)
                result = await service.sync_config(config)

                await session.commit()

                # Emit notification
                _emit_sync_notification(config, result.to_dict())

                logger.info(
                    "api_facet_sync_completed",
                    config_id=config_id,
                    data_source_id=str(config.data_source_id),
                    **result.to_dict(),
                )

                return result.to_dict()

            except Exception as e:
                logger.exception(
                    "api_facet_sync_failed",
                    config_id=config_id,
                    data_source_id=str(config.data_source_id),
                    error=str(e),
                )

                # Update config status
                from app.models.api_configuration import SyncStatus
                config.last_sync_status = SyncStatus.FAILED.value
                config.last_sync_stats = {"error": str(e)}
                await session.commit()

                # Retry the task
                raise self.retry(exc=e) from None

    return run_async(_sync())


def _emit_sync_notification(config, result: dict):
    """Emit notification for sync completion."""
    try:
        from workers.notification_tasks import emit_event

        if result.get("errors"):
            event_type = "API_FACET_SYNC_PARTIAL" if result.get("success") else "API_FACET_SYNC_FAILED"
        else:
            event_type = "API_FACET_SYNC_COMPLETED"

        emit_event.delay(
            event_type,
            {
                "entity_type": "api_configuration",
                "entity_id": str(config.id),
                "data_source_id": str(config.data_source_id),
                "records_fetched": result.get("records_fetched", 0),
                "entities_matched": result.get("entities_matched", 0),
                "history_points_added": result.get("history_points_added", 0),
            },
        )
    except Exception:  # noqa: S110
        # Don't fail sync if notification fails
        pass


@celery_app.task(name="workers.api_facet_sync_tasks.sync_api_config_now")
def sync_api_config_now(config_id: str):
    """Immediately sync an API configuration (manual trigger).

    This is a simplified version without retry logic, used for
    manual/on-demand sync requests from the UI.

    Args:
        config_id: UUID of the APIConfiguration to sync.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.database import get_celery_session_context
    from app.models.api_configuration import APIConfiguration, ImportMode
    from services.api_facet_sync_service import APIFacetSyncService

    async def _sync():
        async with get_celery_session_context() as session:
            # Use selectinload to eagerly load data_source relationship
            result = await session.execute(
                select(APIConfiguration)
                .options(selectinload(APIConfiguration.data_source))
                .where(APIConfiguration.id == UUID(config_id))
            )
            config = result.scalar_one_or_none()

            if not config:
                return {"success": False, "error": "Configuration not found"}

            if not config.is_active:
                return {"success": False, "error": "Configuration is not active"}

            # Verify this is a facet sync config
            if config.import_mode not in [ImportMode.FACETS.value, ImportMode.BOTH.value]:
                return {"success": False, "error": f"Wrong import mode: {config.import_mode}"}

            service = APIFacetSyncService(session)
            result = await service.sync_config(config)

            await session.commit()

            return result.to_dict()

    return run_async(_sync())
