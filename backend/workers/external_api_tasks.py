"""Celery tasks for external API synchronization.

This module provides background tasks for:
- Periodic sync of all enabled external APIs
- Manual sync triggers for individual APIs
- Cleanup of archived records
"""

from datetime import datetime, timezone
from uuid import UUID

import structlog

from workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="workers.external_api_tasks.sync_all_external_apis")
def sync_all_external_apis():
    """Check and sync all enabled external API sources.

    This task runs periodically (default: every 4 hours) and triggers
    sync for any external API that is due based on its sync_interval_hours.
    """
    from app.database import get_celery_session_context
    from external_apis.models.external_api_config import ExternalAPIConfig
    from sqlalchemy import select
    import asyncio

    async def _check_and_sync():
        async with get_celery_session_context() as session:
            # Get all enabled configs
            result = await session.execute(
                select(ExternalAPIConfig).where(
                    ExternalAPIConfig.sync_enabled.is_(True),
                    ExternalAPIConfig.is_active.is_(True),
                )
            )
            configs = result.scalars().all()

            triggered = 0
            for config in configs:
                if config.is_due_for_sync():
                    # Trigger async sync task
                    sync_external_api.delay(str(config.id))
                    triggered += 1
                    logger.info(
                        "external_api_sync_triggered",
                        config_id=str(config.id),
                        config_name=config.name,
                    )

            logger.info(
                "external_api_sync_check_completed",
                total_configs=len(configs),
                triggered=triggered,
            )

    asyncio.run(_check_and_sync())


@celery_app.task(
    bind=True,
    name="workers.external_api_tasks.sync_external_api",
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
    retry_backoff=True,
    retry_backoff_max=1800,  # 30 minutes max
)
def sync_external_api(self, config_id: str):
    """Sync a single external API source.

    This task fetches all records from the configured API,
    creates/updates entities, and handles missing records.

    Args:
        config_id: UUID of the ExternalAPIConfig to sync.
    """
    from app.database import get_celery_session_context
    from external_apis.models.external_api_config import ExternalAPIConfig
    from external_apis.sync_service import ExternalAPISyncService
    import asyncio

    async def _sync():
        async with get_celery_session_context() as session:
            config = await session.get(ExternalAPIConfig, UUID(config_id))

            if not config:
                logger.error(
                    "external_api_config_not_found",
                    config_id=config_id,
                )
                return None

            if not config.is_active or not config.sync_enabled:
                logger.warning(
                    "external_api_config_disabled",
                    config_id=config_id,
                    config_name=config.name,
                )
                return None

            logger.info(
                "external_api_sync_starting",
                config_id=config_id,
                config_name=config.name,
                api_type=config.api_type,
            )

            try:
                service = ExternalAPISyncService(session)
                result = await service.sync_source(config)

                logger.info(
                    "external_api_sync_completed",
                    config_id=config_id,
                    config_name=config.name,
                    records_fetched=result.records_fetched,
                    entities_created=result.entities_created,
                    entities_updated=result.entities_updated,
                    entities_linked=result.entities_linked,
                    records_missing=result.records_missing,
                    errors=len(result.errors),
                )

                # Emit notification event
                _emit_sync_notification(config, result)

                return result.to_dict()

            except Exception as e:
                logger.error(
                    "external_api_sync_failed",
                    config_id=config_id,
                    config_name=config.name,
                    error=str(e),
                )
                raise

    try:
        return asyncio.run(_sync())
    except Exception as e:
        # Retry on failure
        logger.warning(
            "external_api_sync_retrying",
            config_id=config_id,
            attempt=self.request.retries + 1,
            error=str(e),
        )
        raise self.retry(exc=e)


@celery_app.task(name="workers.external_api_tasks.cleanup_archived_records")
def cleanup_archived_records(days_old: int = 90):
    """Clean up old archived sync records.

    This task removes sync records that have been archived for a long time.
    The associated entities are NOT deleted (they might be referenced elsewhere).

    Args:
        days_old: Delete records archived more than this many days ago.
    """
    from app.database import get_celery_session_context
    from external_apis.models.sync_record import RecordStatus, SyncRecord
    from sqlalchemy import delete
    from datetime import timedelta
    import asyncio

    async def _cleanup():
        async with get_celery_session_context() as session:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days_old)

            result = await session.execute(
                delete(SyncRecord).where(
                    SyncRecord.sync_status == RecordStatus.ARCHIVED.value,
                    SyncRecord.updated_at < cutoff,
                )
            )
            deleted = result.rowcount
            await session.commit()

            logger.info(
                "archived_sync_records_cleaned",
                deleted=deleted,
                days_threshold=days_old,
            )

            return deleted

    return asyncio.run(_cleanup())


@celery_app.task(name="workers.external_api_tasks.test_external_api")
def test_external_api(config_id: str) -> dict:
    """Test connection to an external API.

    This task attempts to connect to the API and fetch records
    without storing anything. Useful for testing configurations.

    Args:
        config_id: UUID of the ExternalAPIConfig to test.

    Returns:
        Dictionary with test results.
    """
    from app.database import get_celery_session_context
    from external_apis.models.external_api_config import ExternalAPIConfig
    from external_apis.sync_service import ExternalAPISyncService
    import asyncio

    async def _test():
        async with get_celery_session_context() as session:
            config = await session.get(ExternalAPIConfig, UUID(config_id))

            if not config:
                return {
                    "success": False,
                    "error": "Configuration not found",
                }

            try:
                service = ExternalAPISyncService(session)
                client = await service._get_client(config)

                async with client:
                    records = await client.fetch_all_records()

                return {
                    "success": True,
                    "records_fetched": len(records),
                    "sample_record": (
                        {
                            "external_id": records[0].external_id,
                            "name": records[0].name,
                            "location_hints": records[0].location_hints[:3],
                        }
                        if records
                        else None
                    ),
                }

            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }

    return asyncio.run(_test())


def _emit_sync_notification(config, result):
    """Emit notification event for sync completion.

    Args:
        config: ExternalAPIConfig that was synced.
        result: SyncResult from the sync operation.
    """
    try:
        from workers.notification_tasks import emit_event

        event_type = "EXTERNAL_API_SYNCED"
        if result.errors:
            event_type = "EXTERNAL_API_SYNC_PARTIAL"
        if result.records_fetched == 0:
            event_type = "EXTERNAL_API_SYNC_EMPTY"

        emit_event.delay(
            event_type,
            {
                "entity_type": "external_api_config",
                "entity_id": str(config.id),
                "config_name": config.name,
                "api_type": config.api_type,
                "records_fetched": result.records_fetched,
                "entities_created": result.entities_created,
                "entities_updated": result.entities_updated,
                "entities_linked": result.entities_linked,
                "records_missing": result.records_missing,
                "error_count": len(result.errors),
            },
        )

    except Exception as e:
        logger.warning(
            "sync_notification_failed",
            error=str(e),
        )
