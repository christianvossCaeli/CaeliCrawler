"""Write command execution for Smart Query Service."""

from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .entity_operations import (
    create_entity_type_from_command,
    create_entity_from_command,
    create_facet_from_command,
    create_relation_from_command,
)
from .category_setup import create_category_setup_with_ai
from .crawl_operations import execute_crawl_command

logger = structlog.get_logger()


async def execute_write_command(
    session: AsyncSession,
    command: Dict[str, Any],
    current_user_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    """Execute a write command and return the result."""
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
        if operation == "create_entity":
            entity_type = command.get("entity_type", "municipality")
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
                entity_type_data.setdefault("is_public", False)
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

            # Use the new AI-powered generation (3 LLM calls)
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

    return result


async def execute_combined_operations(
    session: AsyncSession,
    operations: List[Dict[str, Any]],
    current_user_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    """Execute multiple operations sequentially."""
    result = {
        "success": False,
        "message": "",
        "operation_results": [],
        "warnings": [],
    }

    try:
        for i, op in enumerate(operations):
            op_type = op.get("operation")
            op_result = None

            logger.info(f"Executing combined operation {i+1}/{len(operations)}", operation=op_type)

            if op_type == "create_category_setup":
                setup_data = op.get("category_setup_data", {})
                user_intent = setup_data.get("user_intent", setup_data.get("purpose", ""))
                geographic_filter = setup_data.get("geographic_filter", {})
                op_result = await create_category_setup_with_ai(
                    session, user_intent, geographic_filter, current_user_id
                )

            elif op_type == "start_crawl":
                crawl_data = op.get("crawl_command_data", {})
                op_result = await execute_crawl_command(session, crawl_data)

            elif op_type == "create_entity_type":
                entity_type_data = op.get("entity_type_data", {})
                entity_type, message = await create_entity_type_from_command(session, entity_type_data)
                op_result = {
                    "success": entity_type is not None,
                    "message": message,
                    "entity_type_id": str(entity_type.id) if entity_type else None,
                }

            elif op_type == "create_entity":
                entity_type = op.get("entity_type", "municipality")
                entity_data = op.get("entity_data", {})
                entity, message = await create_entity_from_command(session, entity_type, entity_data)
                op_result = {
                    "success": entity is not None,
                    "message": message,
                    "entity_id": str(entity.id) if entity else None,
                }

            else:
                op_result = {"success": False, "message": f"Unbekannte Operation: {op_type}"}

            result["operation_results"].append({
                "operation": op_type,
                "index": i,
                **op_result,
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
