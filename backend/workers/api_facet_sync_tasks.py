"""Celery tasks for scheduled API-to-Facet synchronization.

This module provides background tasks for:
- Periodic checking of scheduled API template syncs
- Executing API-to-Facet synchronization based on cron schedules
"""

from datetime import datetime, timezone
from uuid import UUID

import structlog
from app.utils.cron import croniter_for_expression, get_schedule_timezone

from workers.celery_app import celery_app
from workers.async_runner import run_async

logger = structlog.get_logger(__name__)


def calculate_next_run(cron_expression: str) -> datetime:
    """Calculate the next run time from a cron expression."""
    schedule_tz = get_schedule_timezone()
    cron = croniter_for_expression(cron_expression, datetime.now(schedule_tz))
    return cron.get_next(datetime)


@celery_app.task(name="workers.api_facet_sync_tasks.check_scheduled_api_syncs")
def check_scheduled_api_syncs():
    """Check and execute scheduled API template syncs.

    This task runs periodically (default: every minute) and triggers
    sync execution for any APITemplate that is due based on its schedule_cron.
    """
    from app.database import get_celery_session_context
    from app.models.api_template import APITemplate, TemplateStatus
    from sqlalchemy import select
    import asyncio

    async def _check_and_execute():
        async with get_celery_session_context() as session:
            schedule_tz = get_schedule_timezone()
            now = datetime.now(schedule_tz)

            # Get all templates due for execution
            # Only templates with:
            # - schedule_enabled = true
            # - status = ACTIVE
            # - next_run_at <= now
            # - facet_mapping is not empty (has sync config)
            result = await session.execute(
                select(APITemplate)
                .where(
                    APITemplate.schedule_enabled.is_(True),
                    APITemplate.status == TemplateStatus.ACTIVE,
                    APITemplate.next_run_at <= now,
                    APITemplate.facet_mapping != {},
                )
                .with_for_update(skip_locked=True)
            )
            templates = result.scalars().all()

            if not templates:
                return

            trigger_templates = []
            for template in templates:
                if not template.schedule_cron:
                    continue
                try:
                    template.next_run_at = calculate_next_run(template.schedule_cron)
                    trigger_templates.append(template)
                except Exception as exc:
                    logger.warning(
                        "api_template_schedule_invalid",
                        template_id=str(template.id),
                        template_name=template.name,
                        cron=template.schedule_cron,
                        error=str(exc),
                    )

            await session.commit()

            triggered = 0
            for template in trigger_templates:
                sync_api_template_to_facets.delay(str(template.id))
                triggered += 1

                logger.info(
                    "api_facet_sync_triggered",
                    template_id=str(template.id),
                    template_name=template.name,
                    next_run_at=template.next_run_at.isoformat() if template.next_run_at else None,
                )

            if triggered > 0:
                logger.info(
                    "api_facet_sync_check_completed",
                    total_due=len(templates),
                    triggered=triggered,
                )

    run_async(_check_and_execute())


@celery_app.task(
    bind=True,
    name="workers.api_facet_sync_tasks.sync_api_template_to_facets",
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
    retry_backoff=True,
    retry_backoff_max=1800,  # 30 minutes max
)
def sync_api_template_to_facets(self, template_id: str):
    """Execute facet sync for a single API template.

    This task:
    1. Loads the template configuration
    2. Fetches data from the external API
    3. Matches API records to entities
    4. Creates/updates FacetValueHistory entries

    Args:
        template_id: UUID of the APITemplate to sync.
    """
    from app.database import get_celery_session_context
    from app.models.api_template import APITemplate, TemplateStatus
    from services.api_facet_sync_service import APIFacetSyncService
    import asyncio

    async def _sync():
        async with get_celery_session_context() as session:
            template = await session.get(APITemplate, UUID(template_id))

            if not template:
                logger.error(
                    "api_template_not_found",
                    template_id=template_id,
                )
                return {"success": False, "error": "Template not found"}

            if template.status != TemplateStatus.ACTIVE:
                logger.warning(
                    "api_template_not_active",
                    template_id=template_id,
                    template_name=template.name,
                    status=template.status.value,
                )
                return {"success": False, "error": "Template is not active"}

            logger.info(
                "api_facet_sync_starting",
                template_id=template_id,
                template_name=template.name,
                api_url=template.full_url,
            )

            try:
                service = APIFacetSyncService(session)
                result = await service.sync_template(template)

                await session.commit()

                # Emit notification
                _emit_sync_notification(template, result.to_dict())

                logger.info(
                    "api_facet_sync_completed",
                    template_id=template_id,
                    template_name=template.name,
                    **result.to_dict(),
                )

                return result.to_dict()

            except Exception as e:
                logger.exception(
                    "api_facet_sync_failed",
                    template_id=template_id,
                    template_name=template.name,
                    error=str(e),
                )

                # Update template status
                template.last_sync_status = "failed"
                template.last_sync_stats = {"error": str(e)}
                await session.commit()

                # Retry the task
                raise self.retry(exc=e)

    return run_async(_sync())


def _emit_sync_notification(template, result: dict):
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
                "entity_type": "api_template",
                "entity_id": str(template.id),
                "template_name": template.name,
                "records_fetched": result.get("records_fetched", 0),
                "entities_matched": result.get("entities_matched", 0),
                "history_points_added": result.get("history_points_added", 0),
            },
        )
    except Exception:
        # Don't fail sync if notification fails
        pass


@celery_app.task(name="workers.api_facet_sync_tasks.sync_api_template_now")
def sync_api_template_now(template_id: str):
    """Immediately sync an API template (manual trigger).

    This is a simplified version without retry logic, used for
    manual/on-demand sync requests from the UI.

    Args:
        template_id: UUID of the APITemplate to sync.
    """
    from app.database import get_celery_session_context
    from app.models.api_template import APITemplate, TemplateStatus
    from services.api_facet_sync_service import APIFacetSyncService
    import asyncio

    async def _sync():
        async with get_celery_session_context() as session:
            template = await session.get(APITemplate, UUID(template_id))

            if not template:
                return {"success": False, "error": "Template not found"}

            if template.status != TemplateStatus.ACTIVE:
                return {"success": False, "error": f"Template not active: {template.status.value}"}

            service = APIFacetSyncService(session)
            result = await service.sync_template(template)

            await session.commit()

            return result.to_dict()

    return run_async(_sync())
