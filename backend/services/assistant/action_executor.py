"""Assistant Service - Action Execution Logic.

This module handles execution of user actions including:
- Single entity updates
- Batch operations on multiple entities
- Action preview and confirmation workflow
- Inline edits

Exports:
    - execute_action: Execute confirmed single action
    - execute_batch_action: Execute batch operation
    - preview_inline_edit: Preview inline edit action
    - handle_batch_action_intent: Process batch action from chat
"""

import json
from typing import Any
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Entity
from app.schemas.assistant import (
    ActionChange,
    ActionDetails,
    ActionPreviewResponse,
    AssistantContext,
    AssistantResponseData,
    BatchActionChatResponse,
    BatchActionPreview,
    ErrorResponseData,
    SuggestedAction,
)
from services.assistant.common import validate_entity_context
from services.smart_query.write_executor import execute_batch_operation
from services.translations import Translator

logger = structlog.get_logger()


async def execute_action(
    db: AsyncSession,
    action: ActionDetails,
    context: AssistantContext
) -> dict[str, Any]:
    """Execute a confirmed action.

    Args:
        db: Database session
        action: Action details to execute
        context: Application context

    Returns:
        Dict with success status and details
    """
    if action.type == "update_entity":
        try:
            entity_id = UUID(action.target_id)
            result = await db.execute(
                select(Entity).where(Entity.id == entity_id)
            )
            entity = result.scalar_one_or_none()

            if not entity:
                return {"success": False, "message": "Entity nicht gefunden"}

            # Apply changes
            for field, change in action.changes.items():
                if hasattr(entity, field):
                    setattr(entity, field, change.to_value)

            await db.commit()

            return {
                "success": True,
                "message": f"'{entity.name}' wurde aktualisiert.",
                "affected_entity_id": str(entity.id),
                "affected_entity_name": entity.name,
                "refresh_required": True
            }

        except Exception as e:
            await db.rollback()
            logger.error("execute_action_error", error=str(e))
            return {"success": False, "message": f"Fehler: {str(e)}"}

    return {"success": False, "message": f"Unbekannte Aktion: {action.type}"}


async def execute_batch_action(
    db: AsyncSession,
    action_type: str,
    target_filter: dict[str, Any],
    action_data: dict[str, Any],
    dry_run: bool = True
) -> dict[str, Any]:
    """Execute a batch action on multiple entities.

    Uses the unified Smart Query batch executor.

    Args:
        db: Database session
        action_type: Type of action (add_facet, update_field, etc.)
        target_filter: Filter for target entities
        action_data: Data for the action
        dry_run: If True, only preview changes

    Returns:
        Dict with success, affected_count, preview, batch_id
    """
    try:
        # Convert target_filter to Smart Query format
        sq_target_filter = {
            "entity_type": target_filter.get("entity_type"),
        }

        # Handle location filter
        if "location" in target_filter:
            loc_filter = target_filter["location"]
            if isinstance(loc_filter, dict) and "admin_level_1" in loc_filter:
                sq_target_filter["location_filter"] = loc_filter["admin_level_1"]

        # Handle additional filters
        additional = {}
        for key, value in target_filter.items():
            if key not in ("entity_type", "location"):
                additional[key] = value
        if additional:
            sq_target_filter["additional_filters"] = additional

        # Convert action_data to Smart Query format
        sq_action_data = {
            "facet_type": action_data.get("facet_type"),
            "facet_value": action_data.get("value"),
            "field_name": action_data.get("field"),
            "field_value": action_data.get("value"),
            "relation_type": action_data.get("relation_type"),
            "relation_target": action_data.get("target"),
        }

        # Build batch_data for Smart Query executor
        batch_data = {
            "action_type": action_type,
            "target_filter": sq_target_filter,
            "action_data": sq_action_data,
        }

        # Execute via unified Smart Query executor
        result = await execute_batch_operation(db, batch_data, dry_run=dry_run)

        # Add batch_id for non-dry-run operations
        if not dry_run and result.get("success"):
            result["batch_id"] = str(uuid4())
        else:
            result["batch_id"] = None

        # Ensure preview is properly formatted
        preview = result.get("preview", [])
        if preview and isinstance(preview[0], dict):
            # Already in dict format from Smart Query
            result["preview"] = preview

        if not dry_run:
            await db.commit()

        return result

    except Exception as e:
        await db.rollback()
        logger.error("batch_action_error", error=str(e))
        return {
            "success": False,
            "affected_count": 0,
            "preview": [],
            "batch_id": None,
            "message": f"Fehler: {str(e)}"
        }


async def preview_inline_edit(
    db: AsyncSession,
    message: str,
    context: AssistantContext,
    intent_data: dict[str, Any]
) -> ActionPreviewResponse:
    """Handle inline edit requests - return preview for confirmation.

    Args:
        db: Database session
        message: User message
        context: Application context
        intent_data: Extracted intent data

    Returns:
        ActionPreviewResponse with preview details
    """
    if not context.current_entity_id:
        return ActionPreviewResponse(
            message="Keine Entity ausgewählt. Navigiere zuerst zu einer Entity-Detailseite.",
            action=ActionDetails(type="none"),
            requires_confirmation=False
        )

    field = intent_data.get("field_to_edit", "name")
    new_value = intent_data.get("new_value", "")

    if not new_value:
        return ActionPreviewResponse(
            message="Ich konnte den neuen Wert nicht erkennen. Bitte formuliere um, z.B. 'Ändere den Namen zu Neuer Name'",
            action=ActionDetails(type="none"),
            requires_confirmation=False
        )

    # Get current entity
    try:
        entity = await validate_entity_context(db, context.current_entity_id)

        if not entity:
            return ActionPreviewResponse(
                message="Entity nicht gefunden.",
                action=ActionDetails(type="none"),
                requires_confirmation=False
            )

        # Determine the field and current value
        current_value = getattr(entity, field, None)
        if current_value is None and field == "name":
            current_value = entity.name

        return ActionPreviewResponse(
            message=f"Soll ich '{field}' von '{current_value}' zu '{new_value}' ändern?",
            action=ActionDetails(
                type="update_entity",
                target_id=str(entity.id),
                target_name=entity.name,
                target_type=context.current_entity_type,
                changes={
                    field: ActionChange(
                        field=field,
                        from_value=current_value,
                        to_value=new_value
                    )
                }
            ),
            requires_confirmation=True
        )

    except Exception as e:
        logger.error("inline_edit_error", error=str(e))
        return ActionPreviewResponse(
            message=f"Fehler: {str(e)}",
            action=ActionDetails(type="none"),
            requires_confirmation=False
        )


async def handle_batch_action_intent(
    db: AsyncSession,
    message: str,
    context: AssistantContext,
    intent_data: dict[str, Any],
    translator: Translator
) -> tuple[AssistantResponseData, list[SuggestedAction]]:
    """Handle a batch action intent from chat.

    Args:
        db: Database session
        message: User message
        context: Application context
        intent_data: Extracted intent data
        translator: Translator instance

    Returns:
        Tuple of (response_data, suggested_actions)
    """
    extracted = intent_data.get("extracted_data", {})

    # Parse batch action parameters
    action_type = extracted.get("batch_action_type", "add_facet")
    target_filter_raw = extracted.get("batch_target_filter", {})
    action_data_raw = extracted.get("batch_action_data", {})

    # Convert string representations to dicts if needed
    if isinstance(target_filter_raw, str):
        try:
            target_filter = json.loads(target_filter_raw)
        except (json.JSONDecodeError, ValueError, TypeError):
            target_filter = {"entity_type": target_filter_raw}
    else:
        target_filter = target_filter_raw or {}

    if isinstance(action_data_raw, str):
        try:
            action_data = json.loads(action_data_raw)
        except (json.JSONDecodeError, ValueError, TypeError):
            action_data = {"value": action_data_raw}
    else:
        action_data = action_data_raw or {}

    # Validate filter
    if not target_filter:
        return ErrorResponseData(
            message=translator.t(
                "batch_missing_filter",
                default="Bitte gib an, welche Entities bearbeitet werden sollen (z.B. 'alle Gemeinden in NRW')."
            ),
            error_code="missing_filter"
        ), []

    # Execute dry run to get preview
    try:
        result = await execute_batch_action(
            action_type=action_type,
            target_filter=target_filter,
            action_data=action_data,
            dry_run=True,
            db=db
        )

        if not result.get("success"):
            return ErrorResponseData(
                message=result.get("message", "Fehler bei der Batch-Vorschau"),
                error_code="batch_preview_error"
            ), []

        affected_count = result.get("affected_count", 0)
        preview = result.get("preview", [])

        if affected_count == 0:
            return ErrorResponseData(
                message=translator.t(
                    "batch_no_matches",
                    default="Keine passenden Entities für die Batch-Operation gefunden."
                ),
                error_code="no_matches"
            ), []

        # Return batch preview response
        return BatchActionChatResponse(
            message=translator.t(
                "batch_preview_message",
                count=affected_count,
                default=f"{affected_count} Entities würden bearbeitet werden."
            ),
            affected_count=affected_count,
            preview=[
                BatchActionPreview(
                    entity_id=p.get("entity_id", ""),
                    entity_name=p.get("entity_name", ""),
                    entity_type=p.get("entity_type", "")
                )
                for p in preview
            ],
            action_type=action_type,
            action_data=action_data,
            target_filter=target_filter,
            requires_confirmation=True
        ), []

    except Exception as e:
        logger.error("batch_intent_error", error=str(e))
        return ErrorResponseData(
            message=f"Fehler bei der Batch-Verarbeitung: {str(e)}",
            error_code="batch_error"
        ), []


def parse_batch_filter(filter_data: Any) -> dict[str, Any]:
    """Parse and normalize batch filter data.

    Args:
        filter_data: Raw filter data (dict or string)

    Returns:
        Normalized filter dictionary
    """
    if isinstance(filter_data, str):
        try:
            return json.loads(filter_data)
        except (json.JSONDecodeError, ValueError, TypeError):
            return {"entity_type": filter_data}

    if isinstance(filter_data, dict):
        return filter_data

    return {}


def parse_action_data(action_data: Any) -> dict[str, Any]:
    """Parse and normalize action data.

    Args:
        action_data: Raw action data (dict or string)

    Returns:
        Normalized action data dictionary
    """
    if isinstance(action_data, str):
        try:
            return json.loads(action_data)
        except (json.JSONDecodeError, ValueError, TypeError):
            return {"value": action_data}

    if isinstance(action_data, dict):
        return action_data

    return {}
