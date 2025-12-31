"""Write command execution for Smart Query Service.

This module provides the main entry point for executing write commands.
Most operations are delegated to the operations/ module using the Command Pattern.

Core operations that are handled directly:
- create_entity
- create_facet
- create_relation
- create_entity_type
- create_category_setup
- start_crawl
- combined (orchestrates multiple operations)

All other operations are handled by registered handlers in operations/.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .category_setup import create_category_setup_with_ai
from .crawl_operations import execute_crawl_command
from .entity_operations import (
    create_entity_from_command,
    create_entity_type_from_command,
    create_facet_from_command,
    create_relation_from_command,
)

logger = structlog.get_logger()


async def execute_facet_type_create(
    session: AsyncSession,
    facet_type_data: dict[str, Any],
) -> dict[str, Any]:
    """Create a new FacetType via the operations registry.

    This is a convenience wrapper for the create_facet_type operation.

    Args:
        session: Database session
        facet_type_data: FacetType data including name, slug, value_type, etc.

    Returns:
        Dict with success, message, and facet_type_id if successful
    """
    from .operations import execute_operation

    command = {
        "operation": "create_facet_type",
        "facet_type_data": facet_type_data,
    }

    result = await execute_operation(session, command, user_id=None)

    response = {
        "success": result.success,
        "message": result.message,
    }

    if result.success and result.created_items:
        for item in result.created_items:
            if item.get("type") == "facet_type":
                response["facet_type_id"] = item.get("id")
                response["facet_type_slug"] = item.get("slug")
                break

    return response


async def execute_batch_operation(
    session: AsyncSession,
    batch_data: dict[str, Any],
    dry_run: bool = True,
) -> dict[str, Any]:
    """Execute a batch operation on multiple entities.

    This is a convenience wrapper for the batch_operation handler.

    Args:
        session: Database session
        batch_data: Contains action_type, target_filter, action_data
        dry_run: If True, only preview changes without executing

    Returns:
        Dict with success, affected_count, preview, and message
    """
    from .operations import execute_operation

    command = {
        "operation": "batch_operation",
        "batch_data": batch_data,
        "dry_run": dry_run,
    }

    result = await execute_operation(session, command, user_id=None)

    return {
        "success": result.success,
        "message": result.message,
        "affected_count": result.data.get("affected_count", 0) if result.data else 0,
        "preview": result.data.get("preview", []) if result.data else [],
        "dry_run": result.data.get("dry_run", dry_run) if result.data else dry_run,
    }


async def save_operation_to_history(
    session: AsyncSession,
    user_id: UUID,
    command_text: str,
    operation: str,
    interpretation: dict[str, Any],
    result_summary: dict[str, Any],
    was_successful: bool,
) -> None:
    """Save a Smart Query operation to history for the user.

    Handles deduplication: if the same command was executed before,
    updates execution_count instead of creating a new record.
    """
    from app.models.smart_query_operation import OperationType, SmartQueryOperation

    try:
        # Map operation string to OperationType enum
        operation_type_map = {
            "start_crawl": OperationType.START_CRAWL,
            "create_category_setup": OperationType.CREATE_CATEGORY_SETUP,
            "create_entity": OperationType.CREATE_ENTITY,
            "create_entity_type": OperationType.CREATE_ENTITY_TYPE,
            "create_facet": OperationType.CREATE_FACET,
            "create_relation": OperationType.CREATE_RELATION,
            "fetch_and_create_from_api": OperationType.FETCH_AND_CREATE_FROM_API,
            "discover_sources": OperationType.DISCOVER_SOURCES,
            "combined": OperationType.COMBINED,
            "query_data": OperationType.OTHER,
            "query_external": OperationType.OTHER,
            "query_facet_history": OperationType.OTHER,
            "setup_api_facet_sync": OperationType.OTHER,
            "trigger_api_sync": OperationType.OTHER,
        }
        op_type = operation_type_map.get(operation, OperationType.OTHER)

        # Compute hash for deduplication
        command_hash = SmartQueryOperation.compute_hash(command_text)

        # Check if this exact command exists for this user
        existing = await session.execute(
            select(SmartQueryOperation).where(
                SmartQueryOperation.user_id == user_id,
                SmartQueryOperation.command_hash == command_hash,
            )
        )
        existing_op = existing.scalar()

        if existing_op:
            # Update existing record
            existing_op.execution_count += 1
            existing_op.last_executed_at = datetime.now(UTC)
            existing_op.was_successful = was_successful
            existing_op.result_summary = result_summary
            existing_op.interpretation = interpretation
            logger.info(
                "Updated Smart Query history",
                operation_id=str(existing_op.id),
                execution_count=existing_op.execution_count,
            )
        else:
            # Create new record
            new_op = SmartQueryOperation(
                user_id=user_id,
                command_text=command_text,
                command_hash=command_hash,
                operation_type=op_type,
                interpretation=interpretation,
                result_summary=result_summary,
                was_successful=was_successful,
            )
            session.add(new_op)
            logger.info(
                "Saved new Smart Query to history",
                operation_type=op_type.value,
                command_text=command_text[:100],
            )

    except Exception as e:
        # Don't fail the main operation if history saving fails
        logger.warning("Failed to save Smart Query to history", error=str(e))


async def execute_write_command(
    session: AsyncSession,
    command: dict[str, Any],
    current_user_id: UUID | None = None,
    original_question: str | None = None,
) -> dict[str, Any]:
    """Execute a write command and return the result.

    This is the main entry point for Smart Query write operations.
    Operations are either:
    1. Handled by registered operation handlers in operations/
    2. Handled directly here for core operations

    Args:
        session: Database session
        command: The interpreted command to execute
        current_user_id: ID of the user executing the command
        original_question: The original natural language question (for history)
    """
    from .operations import OPERATIONS_REGISTRY, execute_operation

    operation = command.get("operation", "none")

    if operation == "none":
        return {"success": False, "message": "Keine Schreib-Operation erkannt"}

    result = {
        "success": False,
        "operation": operation,
        "message": "",
        "created_items": [],
    }

    try:
        # Check if operation has a registered handler
        if operation in OPERATIONS_REGISTRY:
            # Delegate to the Command Pattern handler
            op_result = await execute_operation(session, command, current_user_id)
            result["success"] = op_result.success
            result["message"] = op_result.message
            result["created_items"] = op_result.created_items
            if op_result.data:
                result.update(op_result.data)

        # Core operations handled directly
        elif operation == "create_entity":
            entity_type = command.get("entity_type", "territorial_entity")
            entity_data = command.get("entity_data", {})
            entity, message = await create_entity_from_command(session, entity_type, entity_data)
            result["message"] = message
            if entity:
                result["success"] = True
                result["created_items"].append({
                    "type": "entity",
                    "id": str(entity.id),
                    "name": entity.name,
                    "entity_type": entity_type,
                })

        elif operation == "create_facet":
            facet_data = command.get("facet_data", {})
            facet, message = await create_facet_from_command(session, facet_data)
            result["message"] = message
            if facet:
                result["success"] = True
                result["created_items"].append({
                    "type": "facet_value",
                    "id": str(facet.id),
                    "facet_type": facet_data.get("facet_type"),
                })

        elif operation == "create_relation":
            relation_data = command.get("relation_data", {})
            relation, message = await create_relation_from_command(session, relation_data)
            result["message"] = message
            if relation:
                result["success"] = True
                result["created_items"].append({
                    "type": "relation",
                    "id": str(relation.id),
                })

        elif operation == "create_entity_type":
            entity_type_data = command.get("entity_type_data", {})
            # Add ownership if user is provided
            if current_user_id:
                entity_type_data["created_by_id"] = current_user_id
                entity_type_data["owner_id"] = current_user_id
                entity_type_data.setdefault("is_public", True)
            entity_type, message = await create_entity_type_from_command(session, entity_type_data)
            result["message"] = message
            if entity_type:
                result["success"] = True
                result["created_items"].append({
                    "type": "entity_type",
                    "id": str(entity_type.id),
                    "name": entity_type.name,
                    "slug": entity_type.slug,
                    "icon": entity_type.icon,
                    "color": entity_type.color,
                })

        elif operation == "create_category_setup":
            setup_data = command.get("category_setup_data", {})
            user_intent = setup_data.get("user_intent", setup_data.get("purpose", ""))
            geographic_filter = setup_data.get("geographic_filter", {})

            # Use the AI-powered generation
            setup_result = await create_category_setup_with_ai(
                session,
                user_intent=user_intent,
                geographic_filter=geographic_filter,
                current_user_id=current_user_id,
            )

            result["message"] = setup_result.get("message", "Category-Setup erstellt")
            result["success"] = setup_result.get("success", False)
            result["steps"] = setup_result.get("steps", [])
            result["search_terms"] = setup_result.get("search_terms", [])
            result["url_patterns"] = setup_result.get("url_patterns", {})
            result["ai_extraction_prompt"] = setup_result.get("ai_extraction_prompt", "")

            if setup_result.get("entity_type_id"):
                result["created_items"].append({
                    "type": "entity_type",
                    "id": setup_result["entity_type_id"],
                    "name": setup_result["entity_type_name"],
                    "slug": setup_result["entity_type_slug"],
                })
            if setup_result.get("category_id"):
                result["created_items"].append({
                    "type": "category",
                    "id": setup_result["category_id"],
                    "name": setup_result["category_name"],
                    "slug": setup_result["category_slug"],
                })
            if setup_result.get("linked_data_source_count"):
                result["linked_sources_count"] = setup_result["linked_data_source_count"]

            # AI Discovery results
            result["discovered_data_source_count"] = setup_result.get("discovered_data_source_count", 0)
            result["ai_discovered_sources"] = setup_result.get("ai_discovered_sources", [])
            result["entity_type_name"] = setup_result.get("entity_type_name")
            result["category_name"] = setup_result.get("category_name")

            # Seed entity results
            result["seed_entities_count"] = setup_result.get("seed_entities_count", 0)
            result["seed_entities_created"] = setup_result.get("seed_entities_created", [])
            result["seed_relations_count"] = setup_result.get("seed_relations_count", 0)
            result["hierarchy_parent_id"] = setup_result.get("hierarchy_parent_id")

            if setup_result.get("warnings"):
                result["warnings"] = setup_result["warnings"]

        elif operation == "start_crawl":
            crawl_data = command.get("crawl_command_data", {})
            crawl_result = await execute_crawl_command(session, crawl_data)
            result["message"] = crawl_result.get("message", "Crawl gestartet")
            result["success"] = crawl_result.get("success", False)
            result["crawl_jobs"] = crawl_result.get("jobs", [])
            result["sources_count"] = crawl_result.get("sources_count", 0)

        elif operation == "combined":
            # Support both "operations" and "combined_operations" keys
            operations_list = command.get("operations", []) or command.get("combined_operations", [])
            combined_result = await execute_combined_operations(session, operations_list, current_user_id)
            result["message"] = combined_result.get("message", "Kombinierte Operationen ausgeführt")
            result["success"] = combined_result.get("success", False)
            result["created_items"] = combined_result.get("created_items", [])
            result["operation_results"] = combined_result.get("operation_results", [])

        else:
            result["message"] = f"Unbekannte Operation: {operation}"

        if result["success"]:
            await session.commit()
        else:
            await session.rollback()

    except Exception as e:
        logger.error("Write command execution failed", error=str(e))
        await session.rollback()
        result["message"] = f"Fehler: {str(e)}"

    # Save to history if user is authenticated and we have a question
    if current_user_id and original_question:
        result_summary = {
            "message": result.get("message", ""),
            "success": result.get("success", False),
            "created_items": result.get("created_items", []),
        }
        await save_operation_to_history(
            session=session,
            user_id=current_user_id,
            command_text=original_question,
            operation=operation,
            interpretation=command,
            result_summary=result_summary,
            was_successful=result.get("success", False),
        )
        # Commit the history save (separate from main operation)
        try:  # noqa: SIM105
            await session.commit()
        except Exception:  # noqa: S110
            pass  # History save failure shouldn't affect main result

    return result


async def execute_combined_operations(
    session: AsyncSession,
    operations: list[dict[str, Any]],
    current_user_id: UUID | None = None,
) -> dict[str, Any]:
    """Execute multiple operations sequentially.

    This function orchestrates multiple operations, using registered handlers
    where available and falling back to direct execution for core operations.
    """
    from .operations import OPERATIONS_REGISTRY, execute_operation

    result = {
        "success": False,
        "message": "",
        "operation_results": [],
        "created_items": [],
        "warnings": [],
    }

    try:
        for i, op in enumerate(operations):
            op_type = op.get("operation")
            op_result = None

            logger.info(f"Executing combined operation {i+1}/{len(operations)}", operation=op_type)

            # Check if operation has a registered handler
            if op_type in OPERATIONS_REGISTRY:
                handler_result = await execute_operation(session, op, current_user_id)
                op_result = {
                    "success": handler_result.success,
                    "message": handler_result.message,
                    **(handler_result.data or {}),
                }

            # Core operations handled directly
            elif op_type == "create_category_setup":
                setup_data = op.get("category_setup_data", {})
                category_slug = op.get("category_slug") or setup_data.get("category_slug")

                if category_slug:
                    # Link to existing category - use registered handler
                    from .operations import execute_operation
                    link_command = {"operation": "link_existing_category", "category_slug": category_slug}
                    handler_result = await execute_operation(session, link_command, current_user_id)
                    op_result = {
                        "success": handler_result.success,
                        "message": handler_result.message,
                        **(handler_result.data or {}),
                    }
                else:
                    user_intent = setup_data.get("user_intent", setup_data.get("purpose", ""))
                    geographic_filter = setup_data.get("geographic_filter", {})
                    op_result = await create_category_setup_with_ai(
                        session, user_intent, geographic_filter, current_user_id
                    )

            elif op_type == "start_crawl":
                crawl_data = op.get("crawl_command_data", {})
                op_result = await execute_crawl_command(session, crawl_data)

            elif op_type == "create_entity_type":
                entity_type_data = op.get("entity_type_data") or op.get("entity_type_config", {})
                entity_type, message = await create_entity_type_from_command(session, entity_type_data)
                op_result = {
                    "success": entity_type is not None,
                    "message": message,
                    "entity_type_id": str(entity_type.id) if entity_type else None,
                    "entity_type_slug": entity_type.slug if entity_type else None,
                }

            elif op_type == "create_entity":
                entity_type = op.get("entity_type", "territorial_entity")
                entity_data = op.get("entity_data", {})
                entity, message = await create_entity_from_command(session, entity_type, entity_data)
                op_result = {
                    "success": entity is not None,
                    "message": message,
                    "entity_id": str(entity.id) if entity else None,
                }

            elif op_type == "create_relation":
                relation_data = op.get("relation_data", {})
                if not relation_data:
                    relation_data = {
                        "relation_type": op.get("relation_type"),
                        "source_type": op.get("from_entity_type"),
                        "target_type": op.get("to_entity_type"),
                    }
                # Use registered handler
                relation_command = {"operation": "create_relation_type", "relation_type_data": relation_data}
                handler_result = await execute_operation(session, relation_command, current_user_id)
                op_result = {
                    "success": handler_result.success,
                    "message": handler_result.message,
                    **(handler_result.data or {}),
                }

            else:
                op_result = {"success": False, "message": f"Unbekannte Operation: {op_type}"}

            result["operation_results"].append({
                "operation": op_type,
                "index": i,
                **op_result,
            })

            # Collect created items from each operation
            if op_result.get("entity_type_id"):
                result["created_items"].append({
                    "type": "entity_type",
                    "id": op_result["entity_type_id"],
                    "name": op_result.get("entity_type_name"),
                })
            if op_result.get("entity_id"):
                result["created_items"].append({
                    "type": "entity",
                    "id": op_result["entity_id"],
                })
            if op_result.get("category_id"):
                result["created_items"].append({
                    "type": "category",
                    "id": op_result["category_id"],
                })

            # If an operation fails, stop and rollback
            if not op_result.get("success", False):
                result["message"] = f"Operation {i+1} ({op_type}) fehlgeschlagen: {op_result.get('message')}"
                await session.rollback()
                return result

        # All operations successful
        await session.flush()
        result["success"] = True
        result["message"] = f"Alle {len(operations)} Operationen erfolgreich ausgeführt"

        return result

    except Exception as e:
        logger.error("Combined operations failed", error=str(e), exc_info=True)
        await session.rollback()
        result["message"] = f"Fehler: {str(e)}"
        return result
