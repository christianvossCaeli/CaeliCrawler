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


def _extract_action_value(change_data: Any, default: str = "") -> str:
    """Extract value from ActionChange, dict, or return as-is.

    This helper reduces code duplication when extracting values from
    action.changes which can be ActionChange objects or plain dicts.
    """
    if isinstance(change_data, ActionChange):
        return change_data.to_value
    elif isinstance(change_data, dict):
        return change_data.get("to_value", change_data.get("value", default))
    elif change_data is not None:
        return str(change_data)
    return default


async def execute_action(
    db: AsyncSession,
    action: ActionDetails,
    context: AssistantContext
) -> dict[str, Any]:
    """Execute a confirmed action.

    Supports various action types:
    - update_entity: Update entity fields
    - add_facet_value: Add a facet value to an entity
    - update_facet_value: Update an existing facet value
    - add_relation: Add a relation between entities
    - remove_relation: Remove a relation
    - update_widget: Update widget configuration
    - add_widget: Add a new widget to summary
    - remove_widget: Remove a widget from summary

    Args:
        db: Database session
        action: Action details to execute
        context: Application context

    Returns:
        Dict with success status and details
    """
    action_type = action.type

    try:
        # Entity field update
        if action_type == "update_entity":
            return await _execute_update_entity(db, action)

        # Facet value operations
        elif action_type == "add_facet_value":
            return await _execute_add_facet_value(db, action, context)

        elif action_type == "update_facet_value":
            return await _execute_update_facet_value(db, action, context)

        # Relation operations
        elif action_type == "add_relation":
            return await _execute_add_relation(db, action, context)

        elif action_type == "remove_relation":
            return await _execute_remove_relation(db, action, context)

        # Widget operations (for summaries)
        elif action_type == "update_widget":
            return await _execute_update_widget(db, action, context)

        elif action_type == "add_widget":
            return await _execute_add_widget(db, action, context)

        elif action_type == "remove_widget":
            return await _execute_remove_widget(db, action, context)

        else:
            return {"success": False, "message": f"Unbekannte Aktion: {action_type}"}

    except Exception as e:
        await db.rollback()
        logger.error("execute_action_error", action_type=action_type, error=str(e))
        return {"success": False, "message": f"Fehler: {str(e)}"}


async def _execute_update_entity(
    db: AsyncSession,
    action: ActionDetails
) -> dict[str, Any]:
    """Execute entity field update."""
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


async def _execute_add_facet_value(
    db: AsyncSession,
    action: ActionDetails,
    context: AssistantContext
) -> dict[str, Any]:
    """Add a facet value to an entity."""
    from app.models import FacetType, FacetValue

    entity_id = UUID(action.target_id)
    result = await db.execute(
        select(Entity).where(Entity.id == entity_id)
    )
    entity = result.scalar_one_or_none()

    if not entity:
        return {"success": False, "message": "Entity nicht gefunden"}

    # Get facet type and value from action data using helper
    facet_type_slug = _extract_action_value(action.changes.get("facet_type"))
    facet_value = _extract_action_value(action.changes.get("value"))

    if not facet_type_slug or not facet_value:
        return {"success": False, "message": "Facet-Typ oder Wert fehlt"}

    # Find facet type
    ft_result = await db.execute(
        select(FacetType).where(FacetType.slug == facet_type_slug)
    )
    facet_type = ft_result.scalar_one_or_none()

    if not facet_type:
        return {"success": False, "message": f"Facet-Typ '{facet_type_slug}' nicht gefunden"}

    # Create facet value
    new_facet = FacetValue(
        entity_id=entity.id,
        facet_type_id=facet_type.id,
        value=facet_value
    )
    db.add(new_facet)
    await db.commit()

    return {
        "success": True,
        "message": f"Facet '{facet_type.name}' mit Wert '{facet_value}' hinzugefügt.",
        "affected_entity_id": str(entity.id),
        "affected_entity_name": entity.name,
        "refresh_required": True
    }


async def _execute_update_facet_value(
    db: AsyncSession,
    action: ActionDetails,
    context: AssistantContext
) -> dict[str, Any]:
    """Update an existing facet value."""
    from app.models import FacetValue

    facet_value_id = action.target_id
    result = await db.execute(
        select(FacetValue).where(FacetValue.id == UUID(facet_value_id))
    )
    facet_value = result.scalar_one_or_none()

    if not facet_value:
        return {"success": False, "message": "Facet-Wert nicht gefunden"}

    # Get new value
    new_value_change = action.changes.get("value", {})
    if isinstance(new_value_change, ActionChange):
        new_value = new_value_change.to_value
        old_value = new_value_change.from_value
    elif isinstance(new_value_change, dict):
        new_value = new_value_change.get("to_value", "")
        old_value = new_value_change.get("from_value", facet_value.value)
    else:
        return {"success": False, "message": "Neuer Wert fehlt"}

    facet_value.value = new_value
    await db.commit()

    return {
        "success": True,
        "message": f"Facet-Wert von '{old_value}' zu '{new_value}' geändert.",
        "affected_entity_id": str(facet_value.entity_id),
        "refresh_required": True
    }


async def _execute_add_relation(
    db: AsyncSession,
    action: ActionDetails,
    context: AssistantContext
) -> dict[str, Any]:
    """Add a relation between two entities."""
    from app.models import EntityRelation, RelationType

    source_entity_id = UUID(action.target_id)

    # Get relation details from action using helper
    relation_type_slug = _extract_action_value(action.changes.get("relation_type"))
    target_entity_id = _extract_action_value(action.changes.get("target_entity_id"))

    if not relation_type_slug or not target_entity_id:
        return {"success": False, "message": "Relationstyp oder Ziel-Entity fehlt"}

    # Find relation type
    rt_result = await db.execute(
        select(RelationType).where(RelationType.slug == relation_type_slug)
    )
    relation_type = rt_result.scalar_one_or_none()

    if not relation_type:
        return {"success": False, "message": f"Relationstyp '{relation_type_slug}' nicht gefunden"}

    # Validate target entity exists
    target_result = await db.execute(
        select(Entity).where(Entity.id == UUID(target_entity_id))
    )
    target_entity = target_result.scalar_one_or_none()

    if not target_entity:
        return {"success": False, "message": "Ziel-Entity nicht gefunden"}

    # Create relation
    new_relation = EntityRelation(
        source_entity_id=source_entity_id,
        target_entity_id=UUID(target_entity_id),
        relation_type_id=relation_type.id
    )
    db.add(new_relation)
    await db.commit()

    return {
        "success": True,
        "message": f"Relation '{relation_type.name}' zu '{target_entity.name}' hinzugefügt.",
        "affected_entity_id": str(source_entity_id),
        "refresh_required": True
    }


async def _execute_remove_relation(
    db: AsyncSession,
    action: ActionDetails,
    context: AssistantContext
) -> dict[str, Any]:
    """Remove a relation between entities."""
    from app.models import EntityRelation

    relation_id = action.target_id
    result = await db.execute(
        select(EntityRelation).where(EntityRelation.id == UUID(relation_id))
    )
    relation = result.scalar_one_or_none()

    if not relation:
        return {"success": False, "message": "Relation nicht gefunden"}

    source_entity_id = relation.source_entity_id
    await db.delete(relation)
    await db.commit()

    return {
        "success": True,
        "message": "Relation wurde entfernt.",
        "affected_entity_id": str(source_entity_id),
        "refresh_required": True
    }


async def _execute_update_widget(
    db: AsyncSession,
    action: ActionDetails,
    context: AssistantContext
) -> dict[str, Any]:
    """Update widget configuration in a summary."""
    from app.models import CustomSummaryWidget

    widget_id = action.target_id
    result = await db.execute(
        select(CustomSummaryWidget).where(CustomSummaryWidget.id == UUID(widget_id))
    )
    widget = result.scalar_one_or_none()

    if not widget:
        return {"success": False, "message": "Widget nicht gefunden"}

    # Apply changes from action
    for field, change in action.changes.items():
        if isinstance(change, ActionChange):
            new_value = change.to_value
        elif isinstance(change, dict):
            new_value = change.get("to_value", change.get("value"))
        else:
            new_value = change

        # Handle specific fields
        if field == "chart_type" and hasattr(widget, "config"):
            config = widget.config or {}
            config["chart_type"] = new_value
            widget.config = config
        elif field == "title":
            widget.title = new_value
        elif hasattr(widget, field):
            setattr(widget, field, new_value)

    await db.commit()

    return {
        "success": True,
        "message": f"Widget '{widget.title}' wurde aktualisiert.",
        "affected_entity_id": str(widget.id),
        "refresh_required": True
    }


async def _execute_add_widget(
    db: AsyncSession,
    action: ActionDetails,
    context: AssistantContext
) -> dict[str, Any]:
    """Add a new widget to a summary."""
    from app.models import CustomSummaryWidget

    # Get summary ID from context
    page_data = context.page_data
    if not page_data or not page_data.summary_id:
        return {"success": False, "message": "Kein Summary ausgewählt"}

    summary_id = UUID(page_data.summary_id)

    # Get widget details from action using helper
    widget_type = _extract_action_value(action.changes.get("widget_type"), "chart")
    widget_title = _extract_action_value(action.changes.get("title"), "Neues Widget")

    # Calculate position (add at end)
    from sqlalchemy import func
    count_result = await db.execute(
        select(func.count()).select_from(CustomSummaryWidget).where(
            CustomSummaryWidget.summary_id == summary_id
        )
    )
    widget_count = count_result.scalar() or 0

    new_widget = CustomSummaryWidget(
        summary_id=summary_id,
        title=widget_title,
        widget_type=widget_type,
        position=widget_count,
        config={}
    )
    db.add(new_widget)
    await db.commit()

    return {
        "success": True,
        "message": f"Widget '{widget_title}' wurde hinzugefügt.",
        "affected_entity_id": str(new_widget.id),
        "refresh_required": True
    }


async def _execute_remove_widget(
    db: AsyncSession,
    action: ActionDetails,
    context: AssistantContext
) -> dict[str, Any]:
    """Remove a widget from a summary."""
    from app.models import CustomSummaryWidget

    widget_id = action.target_id
    result = await db.execute(
        select(CustomSummaryWidget).where(CustomSummaryWidget.id == UUID(widget_id))
    )
    widget = result.scalar_one_or_none()

    if not widget:
        return {"success": False, "message": "Widget nicht gefunden"}

    widget_title = widget.title
    await db.delete(widget)
    await db.commit()

    return {
        "success": True,
        "message": f"Widget '{widget_title}' wurde entfernt.",
        "refresh_required": True
    }


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
