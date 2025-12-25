"""Celery tasks for API template validation."""

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog

from workers.celery_app import celery_app
from workers.async_runner import run_async

logger = structlog.get_logger()


@celery_app.task(
    bind=True,
    name="workers.api_template_tasks.validate_template",
    max_retries=2,
    default_retry_delay=30,
    retry_backoff=True,
    soft_time_limit=120,  # 2 minutes soft limit
    time_limit=180,  # 3 minutes hard limit
)
def validate_template(self, template_id: str):
    """
    Validate a single API template.

    Args:
        template_id: UUID of the template to validate
    """
    from app.database import get_celery_session_context
    from app.models.api_template import APITemplate, TemplateStatus
    from services.ai_source_discovery.api_validator import APIValidator
    from services.ai_source_discovery.models import APISuggestion

    async def _validate():
        async with get_celery_session_context() as session:
            template = await session.get(APITemplate, UUID(template_id))
            if not template:
                logger.warning("Template not found", template_id=template_id)
                return

            logger.info(
                "Validating API template",
                template_id=template_id,
                name=template.name,
            )

            # Convert template to APISuggestion for validation
            suggestion = APISuggestion(
                api_name=template.name,
                base_url=template.base_url,
                endpoint=template.endpoint,
                description=template.description or "",
                api_type=template.api_type,
                auth_required=template.auth_required,
                confidence=template.confidence,
            )

            try:
                async with APIValidator() as validator:
                    result = await validator.validate_suggestion(suggestion)

                # Update template with validation results
                template.last_validated = datetime.now(timezone.utc)

                if result.is_valid:
                    template.status = TemplateStatus.ACTIVE
                    template.validation_item_count = result.item_count
                    template.last_validation_error = None

                    # Update field mapping if we found a better one
                    if result.field_mapping and not template.field_mapping:
                        template.field_mapping = result.field_mapping

                    logger.info(
                        "Template validation successful",
                        template_id=template_id,
                        name=template.name,
                        item_count=result.item_count,
                    )
                else:
                    template.status = TemplateStatus.FAILED
                    template.last_validation_error = result.error_message

                    logger.warning(
                        "Template validation failed",
                        template_id=template_id,
                        name=template.name,
                        error=result.error_message,
                    )

                await session.commit()

            except Exception as e:
                logger.error(
                    "Template validation error",
                    template_id=template_id,
                    error=str(e),
                )
                template.status = TemplateStatus.FAILED
                template.last_validation_error = str(e)
                template.last_validated = datetime.now(timezone.utc)
                await session.commit()
                raise

    run_async(_validate())


@celery_app.task(
    bind=True,
    name="workers.api_template_tasks.validate_all_templates",
    soft_time_limit=1800,  # 30 minutes soft limit
    time_limit=2100,  # 35 minutes hard limit
)
def validate_all_templates(self, only_active: bool = True):
    """
    Validate all API templates.

    Args:
        only_active: Only validate ACTIVE templates (default: True)
    """
    from app.database import get_celery_session_context
    from app.models.api_template import APITemplate, TemplateStatus
    from sqlalchemy import select

    async def _validate_all():
        async with get_celery_session_context() as session:
            query = select(APITemplate)

            if only_active:
                query = query.where(APITemplate.status == TemplateStatus.ACTIVE)

            result = await session.execute(query)
            templates = result.scalars().all()

            logger.info(
                "Starting batch template validation",
                template_count=len(templates),
                only_active=only_active,
            )

            validated_count = 0
            failed_count = 0

            for template in templates:
                try:
                    # Queue individual validation task
                    validate_template.delay(str(template.id))
                    validated_count += 1
                except Exception as e:
                    logger.error(
                        "Failed to queue template validation",
                        template_id=str(template.id),
                        error=str(e),
                    )
                    failed_count += 1

            logger.info(
                "Batch template validation queued",
                queued=validated_count,
                failed=failed_count,
            )

            return {"queued": validated_count, "failed": failed_count}

    return run_async(_validate_all())


@celery_app.task(
    bind=True,
    name="workers.api_template_tasks.cleanup_failed_templates",
    soft_time_limit=300,
    time_limit=360,
)
def cleanup_failed_templates(self, days_failed: int = 30):
    """
    Deactivate templates that have been failing for too long.

    Args:
        days_failed: Number of days a template must be failing to be deactivated
    """
    from app.database import get_celery_session_context
    from app.models.api_template import APITemplate, TemplateStatus
    from sqlalchemy import select, and_

    async def _cleanup():
        async with get_celery_session_context() as session:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_failed)

            query = select(APITemplate).where(
                and_(
                    APITemplate.status == TemplateStatus.FAILED,
                    APITemplate.last_validated < cutoff_date,
                )
            )

            result = await session.execute(query)
            templates = result.scalars().all()

            deactivated_count = 0
            for template in templates:
                template.status = TemplateStatus.INACTIVE
                deactivated_count += 1
                logger.info(
                    "Deactivating long-failed template",
                    template_id=str(template.id),
                    name=template.name,
                    last_validated=template.last_validated.isoformat() if template.last_validated else None,
                )

            await session.commit()

            logger.info(
                "Failed template cleanup complete",
                deactivated=deactivated_count,
                cutoff_days=days_failed,
            )

            return {"deactivated": deactivated_count}

    return run_async(_cleanup())
