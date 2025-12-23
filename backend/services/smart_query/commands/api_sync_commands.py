"""API Sync commands for Smart Query.

Commands for setting up scheduled API-to-Facet synchronization.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EntityType, FacetType
from app.models.api_template import APITemplate, APIType, TemplateStatus
from app.utils.cron import croniter_for_expression, get_schedule_timezone
from .base import BaseCommand, CommandResult
from .registry import default_registry

logger = structlog.get_logger()


@default_registry.register("setup_api_facet_sync")
class SetupAPIFacetSyncCommand(BaseCommand):
    """
    Command to set up scheduled API-to-Facet synchronization.

    This command creates an APITemplate configured for automatic
    facet synchronization from an external API.

    Example Command:
        {
            "operation": "setup_api_facet_sync",
            "sync_config": {
                "name": "Bundesliga Tabelle Sync",
                "api_url": "https://api.openligadb.de/getbltable/bl1/2024",
                "schedule_cron": "0 6 * * 1",
                "entity_matching": {
                    "match_by": "name",
                    "api_field": "teamName",
                    "entity_type_slug": "fussballverein"
                },
                "facet_mapping": {
                    "points": {
                        "facet_type_slug": "tabellen-punkte",
                        "is_history": true
                    },
                    "position": {
                        "facet_type_slug": "tabellen-position",
                        "is_history": true
                    }
                }
            }
        }
    """

    async def validate(self) -> Optional[str]:
        """Validate sync configuration."""
        config = self.data.get("sync_config", {})

        if not config.get("name"):
            return "Name für die Sync-Konfiguration erforderlich"

        if not config.get("api_url"):
            return "API URL erforderlich"

        if not config.get("entity_matching"):
            return "Entity-Matching Konfiguration erforderlich"

        entity_matching = config["entity_matching"]
        if not entity_matching.get("api_field"):
            return "API-Feld für Entity-Matching erforderlich"

        if not config.get("facet_mapping"):
            return "Facet-Mapping erforderlich"

        # Validate facet mapping structure
        facet_mapping = config["facet_mapping"]
        for api_field, mapping in facet_mapping.items():
            if not mapping.get("facet_type_slug"):
                return f"facet_type_slug fehlt für API-Feld '{api_field}'"

        # Validate cron expression if provided
        schedule_cron = config.get("schedule_cron")
        if schedule_cron:
            try:
                schedule_tz = get_schedule_timezone()
                croniter_for_expression(schedule_cron, datetime.now(schedule_tz))
            except Exception as e:
                return f"Ungültige Cron-Expression: {schedule_cron} - {str(e)}"

        return None

    async def execute(self) -> CommandResult:
        """Create the API facet sync configuration."""
        config = self.data.get("sync_config", {})

        name = config["name"]
        api_url = config["api_url"]
        description = config.get("description", f"Automatischer Sync: {name}")
        schedule_cron = config.get("schedule_cron")
        entity_matching = config["entity_matching"]
        facet_mapping = config["facet_mapping"]
        keywords = config.get("keywords", [])

        # Parse URL
        parsed = urlparse(api_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        endpoint = parsed.path
        if parsed.query:
            endpoint += f"?{parsed.query}"

        # Validate entity type exists (if specified)
        entity_type_slug = entity_matching.get("entity_type_slug")
        if entity_type_slug:
            et_result = await self.session.execute(
                select(EntityType).where(EntityType.slug == entity_type_slug)
            )
            if not et_result.scalar_one_or_none():
                return CommandResult.failure(
                    message=f"Entity-Typ '{entity_type_slug}' nicht gefunden"
                )

        # Check and create missing FacetTypes
        created_facet_types = []
        for api_field, mapping in facet_mapping.items():
            ft_slug = mapping.get("facet_type_slug")

            ft_result = await self.session.execute(
                select(FacetType).where(FacetType.slug == ft_slug)
            )
            existing_ft = ft_result.scalar_one_or_none()

            if not existing_ft:
                # Create the facet type
                is_history = mapping.get("is_history", True)
                ft_name = ft_slug.replace("-", " ").replace("_", " ").title()

                new_ft = FacetType(
                    slug=ft_slug,
                    name=ft_name,
                    name_plural=ft_name,
                    value_type="history" if is_history else "number",
                    is_time_based=is_history,
                    applicable_entity_type_slugs=[entity_type_slug] if entity_type_slug else [],
                )
                self.session.add(new_ft)
                created_facet_types.append(ft_name)

                logger.info(
                    "facet_type_created_for_sync",
                    slug=ft_slug,
                    name=ft_name,
                    value_type="history" if is_history else "number",
                )

        # Check if template with same name already exists
        existing_template = await self.session.execute(
            select(APITemplate).where(APITemplate.name == name)
        )
        if existing_template.scalar_one_or_none():
            return CommandResult.failure(
                message=f"API-Template mit Name '{name}' existiert bereits"
            )

        # Create APITemplate with facet sync config
        template = APITemplate(
            name=name,
            description=description,
            api_type=APIType.REST,
            base_url=base_url,
            endpoint=endpoint,
            auth_required=False,  # Can be extended later
            auth_config=None,
            field_mapping={},  # Not used for facet sync
            facet_mapping=facet_mapping,
            entity_matching=entity_matching,
            keywords=keywords,
            default_tags=[],
            schedule_enabled=bool(schedule_cron),
            schedule_cron=schedule_cron,
            status=TemplateStatus.ACTIVE,
            source="smart_query",
            confidence=0.9,
        )

        # Calculate next run time if scheduling is enabled
        if schedule_cron:
            schedule_tz = get_schedule_timezone()
            cron = croniter_for_expression(schedule_cron, datetime.now(schedule_tz))
            template.next_run_at = cron.get_next(datetime)

        self.session.add(template)
        await self.session.flush()

        # Build response message
        message_parts = [f"API-Facet-Sync '{name}' konfiguriert."]

        if created_facet_types:
            message_parts.append(f"Facet-Typen erstellt: {', '.join(created_facet_types)}.")

        if schedule_cron and template.next_run_at:
            message_parts.append(
                f"Nächster Sync: {template.next_run_at.strftime('%d.%m.%Y %H:%M')}."
            )

        logger.info(
            "api_facet_sync_configured",
            template_id=str(template.id),
            name=name,
            api_url=api_url,
            schedule_cron=schedule_cron,
            facet_count=len(facet_mapping),
        )

        return CommandResult.success_result(
            message=" ".join(message_parts),
            created_items=[
                {
                    "type": "api_template",
                    "id": str(template.id),
                    "name": name,
                    "api_url": template.full_url,
                    "schedule_enabled": template.schedule_enabled,
                    "next_run": template.next_run_at.isoformat() if template.next_run_at else None,
                }
            ],
        )


@default_registry.register("trigger_api_sync")
class TriggerAPISyncCommand(BaseCommand):
    """
    Command to manually trigger an API-to-Facet sync.

    Example Command:
        {
            "operation": "trigger_api_sync",
            "template_id": "uuid-here"
        }
        or
        {
            "operation": "trigger_api_sync",
            "template_name": "Bundesliga Tabelle Sync"
        }
    """

    async def validate(self) -> Optional[str]:
        """Validate trigger request."""
        if not self.data.get("template_id") and not self.data.get("template_name"):
            return "template_id oder template_name erforderlich"
        return None

    async def execute(self) -> CommandResult:
        """Trigger the sync."""
        from workers.api_facet_sync_tasks import sync_api_template_now

        template_id = self.data.get("template_id")
        template_name = self.data.get("template_name")

        # Find template
        if template_id:
            from uuid import UUID
            template = await self.session.get(APITemplate, UUID(template_id))
        else:
            result = await self.session.execute(
                select(APITemplate).where(APITemplate.name == template_name)
            )
            template = result.scalar_one_or_none()

        if not template:
            return CommandResult.failure(
                message=f"API-Template nicht gefunden"
            )

        if template.status != TemplateStatus.ACTIVE:
            return CommandResult.failure(
                message=f"API-Template nicht aktiv (Status: {template.status.value})"
            )

        if not template.facet_mapping:
            return CommandResult.failure(
                message="API-Template hat kein facet_mapping konfiguriert"
            )

        # Trigger async sync
        task = sync_api_template_now.delay(str(template.id))

        logger.info(
            "api_sync_triggered_manually",
            template_id=str(template.id),
            template_name=template.name,
            task_id=task.id,
        )

        return CommandResult.success_result(
            message=f"Sync für '{template.name}' gestartet.",
            created_items=[
                {
                    "type": "celery_task",
                    "id": task.id,
                    "template_id": str(template.id),
                    "template_name": template.name,
                }
            ],
        )
