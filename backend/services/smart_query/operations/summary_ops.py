"""Custom Summary operations for Smart Query Service.

Operations:
- create_custom_summary: Create a new custom summary from natural language
"""

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .base import OperationResult, WriteOperation, register_operation

logger = structlog.get_logger()


@register_operation("create_custom_summary")
class CreateCustomSummaryOperation(WriteOperation):
    """
    Create a custom summary from a natural language description.

    Uses the AI interpreter to generate widgets and configuration
    from a user prompt.

    By default, summaries are created with AUTO trigger type, which means
    they automatically update when matching entity types are crawled.

    Command structure:
        {
            "operation": "create_custom_summary",
            "prompt": "Zeige mir eine Übersicht aller Goldkurse der letzten Woche",
            "name": "Goldkurs-Übersicht",  # optional
            "schedule": "daily"  # optional: daily, weekly, hourly, auto (default), none
        }
    """

    def validate(self, command: dict[str, Any]) -> str | None:
        if not command.get("prompt"):
            return "Ein Prompt/Beschreibung für die Zusammenfassung ist erforderlich"

        prompt = command.get("prompt", "")
        if len(prompt) < 10:
            return "Der Prompt muss mindestens 10 Zeichen lang sein"
        if len(prompt) > 2000:
            return "Der Prompt darf maximal 2000 Zeichen lang sein"

        schedule = command.get("schedule")
        if schedule and schedule not in ("daily", "weekly", "hourly", "monthly", "auto", "none", None):
            return f"Ungültiger Schedule: {schedule}. Erlaubt: daily, weekly, hourly, monthly, auto, none"

        return None

    async def execute(
        self,
        session: AsyncSession,
        command: dict[str, Any],
        user_id: UUID | None = None,
    ) -> OperationResult:
        from app.models import User
        from app.models.custom_summary import CustomSummary, SummaryStatus, SummaryTriggerType, SummaryWidget
        from app.schemas.custom_summary import SummaryWidgetType
        from app.utils.similarity import find_duplicate_custom_summary
        from services.summaries.ai_interpreter import interpret_summary_prompt
        from services.summaries.source_resolver import update_summary_auto_trigger_entity_types

        if not user_id:
            return OperationResult(
                success=False,
                message="Benutzer-ID erforderlich",
            )

        # Get user for AI interpreter
        user = await session.get(User, user_id)
        if not user:
            return OperationResult(
                success=False,
                message="Benutzer nicht gefunden",
            )

        prompt = command.get("prompt", "")
        name = command.get("name")
        schedule_type = command.get("schedule", "auto")  # Default to AUTO

        try:
            # Call AI interpreter to parse the prompt
            interpretation = await interpret_summary_prompt(
                prompt=prompt,
                session=session,
                user_name=user.email,
            )
        except Exception as e:
            logger.warning("AI interpretation failed, using fallback", error=str(e))
            # Fallback to basic interpretation
            interpretation = {
                "name": name or "Neue Zusammenfassung",
                "description": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                "theme": {"primary_entity_type": None, "context": "custom"},
                "widgets": [],
                "suggested_schedule": {"type": schedule_type},
                "overall_reasoning": f"Fallback-Modus: {str(e)}",
            }

        # Use user-provided name or AI-suggested name
        summary_name = name or interpretation.get("name", "Neue Zusammenfassung")

        # Check for duplicate name
        duplicate = await find_duplicate_custom_summary(
            session,
            user_id=user_id,
            name=summary_name,
        )
        if duplicate:
            existing, reason = duplicate
            return OperationResult(
                success=False,
                message=f"Ähnliche Zusammenfassung existiert bereits: {reason}",
            )

        # Determine trigger type and cron from schedule
        trigger_type = SummaryTriggerType.AUTO  # Default to AUTO
        schedule_cron = None
        schedule_enabled = True  # Enable by default for AUTO

        # Handle explicit schedule parameter
        if schedule_type == "none":
            trigger_type = SummaryTriggerType.MANUAL
            schedule_enabled = False
        elif schedule_type == "auto":
            trigger_type = SummaryTriggerType.AUTO
            schedule_enabled = True
        elif schedule_type in ("hourly", "daily", "weekly", "monthly"):
            trigger_type = SummaryTriggerType.CRON
            cron_mapping = {
                "hourly": "0 * * * *",
                "daily": "0 8 * * *",
                "weekly": "0 9 * * 1",
                "monthly": "0 8 1 * *",
            }
            schedule_cron = cron_mapping.get(schedule_type, "0 8 * * *")
            schedule_enabled = True
        elif ai_schedule := interpretation.get("suggested_schedule", {}):
            # Use AI suggestion if no explicit schedule
            if ai_schedule.get("type") in ("daily", "weekly", "hourly", "monthly"):
                trigger_type = SummaryTriggerType.CRON
                schedule_cron = ai_schedule.get("cron", "0 8 * * *")
                schedule_enabled = True

        # Create the summary
        summary = CustomSummary(
            user_id=user_id,
            name=summary_name,
            description=interpretation.get("description"),
            original_prompt=prompt,
            interpreted_config=interpretation,
            layout_config={"columns": 4, "row_height": 100},
            status=SummaryStatus.DRAFT,
            trigger_type=trigger_type,
            schedule_cron=schedule_cron,
            schedule_enabled=schedule_enabled,
            check_relevance=True,
            auto_expand=interpretation.get("auto_expand_suggestion", {}).get("enabled", False),
        )
        session.add(summary)
        await session.flush()

        # Create widgets from AI interpretation
        widgets_created = 0
        ai_widgets = interpretation.get("widgets", [])

        # Limit widgets to prevent resource exhaustion
        max_widgets = 10
        if len(ai_widgets) > max_widgets:
            ai_widgets = ai_widgets[:max_widgets]

        for i, widget_data in enumerate(ai_widgets):
            position = widget_data.get("position", {})
            widget_type_str = widget_data.get("widget_type", "table")

            try:
                widget_type = SummaryWidgetType(widget_type_str)
            except ValueError:
                widget_type = SummaryWidgetType.TABLE

            widget = SummaryWidget(
                summary_id=summary.id,
                widget_type=widget_type,
                title=widget_data.get("title", f"Widget {i + 1}"),
                subtitle=widget_data.get("subtitle"),
                position_x=position.get("x", 0),
                position_y=position.get("y", 0),
                width=position.get("w", 2),
                height=position.get("h", 2),
                query_config=widget_data.get("query_config", {}),
                visualization_config=widget_data.get("visualization_config", {}),
                display_order=i,
            )
            session.add(widget)
            widgets_created += 1

        await session.flush()

        # Update auto_trigger_entity_types for AUTO trigger
        if trigger_type == SummaryTriggerType.AUTO:
            # Refresh to get the newly created widgets
            await session.refresh(summary, ["widgets"])
            entity_types = update_summary_auto_trigger_entity_types(summary)
            logger.debug(
                "auto_trigger_entity_types_set",
                summary_id=str(summary.id),
                entity_types=entity_types,
            )

        await session.flush()

        logger.info(
            "summary_created_via_smart_query",
            summary_id=str(summary.id),
            user_id=str(user_id),
            widgets_created=widgets_created,
            trigger_type=trigger_type.value,
        )

        # Build response message
        trigger_info = ""
        if trigger_type == SummaryTriggerType.AUTO:
            trigger_info = " (automatische Aktualisierung bei relevanten Crawls)"
        elif schedule_cron:
            schedule_names = {
                "0 * * * *": "stündlich",
                "0 8 * * *": "täglich um 8 Uhr",
                "0 9 * * 1": "wöchentlich montags",
                "0 8 1 * *": "monatlich am 1.",
            }
            trigger_info = f" (Aktualisierung: {schedule_names.get(schedule_cron, schedule_cron)})"

        return OperationResult(
            success=True,
            message=f"Zusammenfassung '{summary_name}' mit {widgets_created} Widgets erstellt{trigger_info}",
            operation="create_custom_summary",
            created_items=[
                {
                    "type": "custom_summary",
                    "id": str(summary.id),
                    "name": summary_name,
                    "widgets_count": widgets_created,
                }
            ],
            data={
                "summary_id": str(summary.id),
                "name": summary_name,
                "widgets_created": widgets_created,
                "trigger_type": trigger_type.value,
                "schedule_cron": schedule_cron,
                "link": f"/custom-summaries/{summary.id}",
            },
        )
