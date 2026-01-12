"""Schedule operations for Smart Query Service.

Operations:
- update_crawl_schedule: Update the crawl schedule of a category
"""

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category
from app.schemas.category import _validate_cron_expression

from .base import OperationResult, WriteOperation, register_operation

logger = structlog.get_logger()


@register_operation("update_crawl_schedule")
class UpdateCrawlScheduleOperation(WriteOperation):
    """Update the crawl schedule of a category.

    Supports identifying the category by:
    - category_id: UUID of the category
    - category_name: Name of the category
    - category_slug: Slug of the category

    Parameters:
    - schedule_cron: Cron expression (5 or 6 fields)
    - schedule_enabled: Whether the schedule is enabled (default: True)

    Examples:
        # Update schedule by category name
        command = {
            "schedule_data": {
                "category_name": "Goldkurs-Analyse",
                "schedule_cron": "*/15 * * * *",  # Every 15 minutes
                "schedule_enabled": True
            }
        }

        # Update schedule by category ID
        command = {
            "schedule_data": {
                "category_id": "550e8400-e29b-41d4-a716-446655440000",
                "schedule_cron": "0 */2 * * *",  # Every 2 hours
            }
        }

        # Disable schedule
        command = {
            "schedule_data": {
                "category_slug": "bundesliga-tabelle",
                "schedule_enabled": False
            }
        }
    """

    def validate(self, command: dict[str, Any]) -> str | None:
        """Validate command data before execution."""
        schedule_data = command.get("schedule_data", {})

        # Check that at least one identifier is provided
        if not any(
            [
                schedule_data.get("category_id"),
                schedule_data.get("category_name"),
                schedule_data.get("category_slug"),
            ]
        ):
            return "category_id, category_name oder category_slug erforderlich"

        # Validate cron expression if provided
        if cron := schedule_data.get("schedule_cron"):
            try:
                validated = _validate_cron_expression(cron)
                if validated is None:
                    return f"Ungültiger Cron-Ausdruck: {cron}"
            except ValueError as e:
                return f"Ungültiger Cron-Ausdruck: {e}"

        return None

    async def execute(
        self,
        session: AsyncSession,
        command: dict[str, Any],
        user_id: UUID | None = None,
    ) -> OperationResult:
        """Execute the schedule update operation."""
        schedule_data = command.get("schedule_data", {})

        category_id = schedule_data.get("category_id")
        category_name = schedule_data.get("category_name")
        category_slug = schedule_data.get("category_slug")

        try:
            # Find category by ID, name, or slug
            category = None

            if category_id:
                try:
                    cat_uuid = UUID(category_id) if isinstance(category_id, str) else category_id
                    category = await session.get(Category, cat_uuid)
                except (ValueError, TypeError):
                    return OperationResult(
                        success=False,
                        message=f"Ungültige Category-ID: {category_id}",
                        operation="update_crawl_schedule",
                        error="invalid_category_id",
                    )

            elif category_name:
                result = await session.execute(select(Category).where(Category.name == category_name))
                category = result.scalar_one_or_none()

            elif category_slug:
                result = await session.execute(select(Category).where(Category.slug == category_slug))
                category = result.scalar_one_or_none()

            if not category:
                identifier = category_id or category_name or category_slug
                return OperationResult(
                    success=False,
                    message=f"Kategorie nicht gefunden: {identifier}",
                    operation="update_crawl_schedule",
                    error="category_not_found",
                )

            # Track what was updated
            updates = []

            # Update schedule_cron if provided
            if "schedule_cron" in schedule_data:
                cron = schedule_data["schedule_cron"]
                validated_cron = _validate_cron_expression(cron)
                if validated_cron:
                    old_cron = category.schedule_cron
                    category.schedule_cron = validated_cron
                    updates.append(f"schedule_cron: '{old_cron}' → '{validated_cron}'")

            # Update schedule_enabled if provided
            if "schedule_enabled" in schedule_data:
                old_enabled = category.schedule_enabled
                category.schedule_enabled = bool(schedule_data["schedule_enabled"])
                updates.append(f"schedule_enabled: {old_enabled} → {category.schedule_enabled}")

            # Update schedule_owner_id to current user
            if user_id:
                category.schedule_owner_id = user_id

            await session.flush()

            logger.info(
                "Updated crawl schedule",
                category_id=str(category.id),
                category_name=category.name,
                schedule_cron=category.schedule_cron,
                schedule_enabled=category.schedule_enabled,
                updates=updates,
            )

            return OperationResult(
                success=True,
                message=f"Schedule für '{category.name}' aktualisiert: {category.schedule_cron}",
                operation="update_crawl_schedule",
                data={
                    "category_id": str(category.id),
                    "category_name": category.name,
                    "schedule_cron": category.schedule_cron,
                    "schedule_enabled": category.schedule_enabled,
                    "updates": updates,
                },
            )

        except Exception as e:
            logger.error(
                "Failed to update crawl schedule",
                error=str(e),
                category_id=category_id,
                category_name=category_name,
            )
            return OperationResult(
                success=False,
                message=f"Fehler beim Aktualisieren des Schedules: {e}",
                operation="update_crawl_schedule",
                error=str(e),
            )
