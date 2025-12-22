"""Write command execution for Smart Query Service."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .entity_operations import (
    create_entity_type_from_command,
    create_entity_from_command,
    create_facet_from_command,
    create_relation_from_command,
    find_entity_by_name,
    bulk_create_entities_from_api_data,
)
from .category_setup import create_category_setup_with_ai
from .crawl_operations import execute_crawl_command

logger = structlog.get_logger()


async def save_operation_to_history(
    session: AsyncSession,
    user_id: UUID,
    command_text: str,
    operation: str,
    interpretation: Dict[str, Any],
    result_summary: Dict[str, Any],
    was_successful: bool,
) -> None:
    """Save a Smart Query operation to history for the user.

    Handles deduplication: if the same command was executed before,
    updates execution_count instead of creating a new record.
    """
    from app.models.smart_query_operation import SmartQueryOperation, OperationType

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
            existing_op.last_executed_at = datetime.now(timezone.utc)
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
    command: Dict[str, Any],
    current_user_id: Optional[UUID] = None,
    original_question: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a write command and return the result.

    Args:
        session: Database session
        command: The interpreted command to execute
        current_user_id: ID of the user executing the command
        original_question: The original natural language question (for history)
    """
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
                entity_type_data.setdefault("is_public", True)  # Always visible in frontend
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

        elif operation == "discover_sources":
            discover_data = command.get("discover_sources_data", {})
            discover_result = await execute_discover_sources(session, discover_data)
            result["message"] = discover_result.get("message", "Datenquellen-Suche abgeschlossen")
            result["success"] = discover_result.get("success", False)
            result["sources_found"] = discover_result.get("sources_found", [])
            result["sources_count"] = discover_result.get("sources_count", 0)
            result["search_strategy"] = discover_result.get("search_strategy")
            result["stats"] = discover_result.get("stats")
            result["imported_count"] = discover_result.get("imported_count", 0)

        elif operation == "fetch_and_create_from_api":
            fetch_data = command.get("fetch_and_create_data", {})
            fetch_result = await execute_fetch_and_create_from_api(session, fetch_data)
            result["message"] = fetch_result.get("message", "API-Import abgeschlossen")
            result["success"] = fetch_result.get("success", False)
            result["created_count"] = fetch_result.get("created_count", 0)
            result["existing_count"] = fetch_result.get("existing_count", 0)
            result["error_count"] = fetch_result.get("error_count", 0)
            result["total_fetched"] = fetch_result.get("total_fetched", 0)
            result["entity_type"] = fetch_result.get("entity_type")
            result["parent_type"] = fetch_result.get("parent_type")
            if fetch_result.get("errors"):
                result["errors"] = fetch_result["errors"][:10]  # Limit error list
            if fetch_result.get("warnings"):
                result["warnings"] = fetch_result["warnings"]

        elif operation == "combined":
            # Support both "operations" and "combined_operations" keys
            operations_list = command.get("operations", []) or command.get("combined_operations", [])
            combined_result = await execute_combined_operations(session, operations_list, current_user_id)
            result["message"] = combined_result.get("message", "Kombinierte Operationen ausgeführt")
            result["success"] = combined_result.get("success", False)
            result["created_items"] = combined_result.get("created_items", [])
            result["operation_results"] = combined_result.get("operation_results", [])

        elif operation == "analyze_pysis_for_facets":
            pysis_data = command.get("pysis_data", {})
            pysis_result = await execute_pysis_analyze(session, pysis_data)
            result["message"] = pysis_result.get("message", "PySis-Analyse gestartet")
            result["success"] = pysis_result.get("success", False)
            result["task_id"] = pysis_result.get("task_id")

        elif operation == "enrich_facets_from_pysis":
            pysis_data = command.get("pysis_data", {})
            pysis_result = await execute_pysis_enrich(session, pysis_data)
            result["message"] = pysis_result.get("message", "Facet-Anreicherung gestartet")
            result["success"] = pysis_result.get("success", False)
            result["task_id"] = pysis_result.get("task_id")

        elif operation == "update_entity":
            update_data = command.get("update_data", {})
            update_result = await execute_entity_update(session, update_data)
            result["message"] = update_result.get("message", "Entity aktualisiert")
            result["success"] = update_result.get("success", False)
            if update_result.get("entity_id"):
                result["updated_items"] = [{"type": "entity", "id": update_result["entity_id"]}]

        elif operation == "create_facet_type":
            facet_type_data = command.get("facet_type_data", {})
            ft_result = await execute_facet_type_create(session, facet_type_data)
            result["message"] = ft_result.get("message", "Facet-Typ erstellt")
            result["success"] = ft_result.get("success", False)
            if ft_result.get("facet_type_id"):
                result["created_items"].append({
                    "type": "facet_type",
                    "id": ft_result["facet_type_id"],
                    "name": ft_result.get("facet_type_name"),
                    "slug": ft_result.get("facet_type_slug"),
                })

        elif operation == "assign_facet_type":
            assign_data = command.get("assign_facet_type_data", {})
            assign_result = await execute_facet_type_assign(session, assign_data)
            result["message"] = assign_result.get("message", "Facet-Typ zugewiesen")
            result["success"] = assign_result.get("success", False)

        elif operation == "add_history_point":
            history_data = command.get("history_point_data", {})
            history_result = await execute_add_history_point(session, history_data)
            result["message"] = history_result.get("message", "Datenpunkt hinzugefügt")
            result["success"] = history_result.get("success", False)
            if history_result.get("data_point_id"):
                result["created_items"].append({
                    "type": "history_data_point",
                    "id": history_result["data_point_id"],
                    "entity_id": history_result.get("entity_id"),
                    "facet_type": history_result.get("facet_type"),
                    "value": history_result.get("value"),
                    "recorded_at": history_result.get("recorded_at"),
                })

        elif operation == "batch_operation":
            batch_data = command.get("batch_operation_data", {})
            dry_run = batch_data.get("dry_run", True)
            batch_result = await execute_batch_operation(session, batch_data, dry_run=dry_run)
            result["message"] = batch_result.get("message", "Batch-Operation ausgeführt")
            result["success"] = batch_result.get("success", False)
            result["affected_count"] = batch_result.get("affected_count", 0)
            result["preview"] = batch_result.get("preview", [])
            result["dry_run"] = dry_run

        elif operation == "delete_entity":
            delete_data = command.get("delete_entity_data", {})
            delete_result = await execute_delete_entity(session, delete_data)
            result["message"] = delete_result.get("message", "Entity gelöscht")
            result["success"] = delete_result.get("success", False)
            result["deleted_items"] = delete_result.get("deleted_items", [])
            result["requires_confirmation"] = delete_data.get("requires_confirmation", True)

        elif operation == "delete_facet":
            delete_data = command.get("delete_facet_data", {})
            delete_result = await execute_delete_facet(session, delete_data)
            result["message"] = delete_result.get("message", "Facet gelöscht")
            result["success"] = delete_result.get("success", False)
            result["deleted_items"] = delete_result.get("deleted_items", [])
            result["requires_confirmation"] = delete_data.get("requires_confirmation", True)

        elif operation == "batch_delete":
            delete_data = command.get("batch_delete_data", {})
            dry_run = delete_data.get("dry_run", True)
            delete_result = await execute_batch_delete(session, delete_data, dry_run=dry_run)
            result["message"] = delete_result.get("message", "Batch-Löschung ausgeführt")
            result["success"] = delete_result.get("success", False)
            result["affected_count"] = delete_result.get("affected_count", 0)
            result["preview"] = delete_result.get("preview", [])
            result["dry_run"] = dry_run
            result["requires_confirmation"] = delete_data.get("requires_confirmation", True)

        elif operation == "export_query_result":
            export_data = command.get("export_data", {})
            export_result = await execute_export(session, export_data)
            result["message"] = export_result.get("message", "Export vorbereitet")
            result["success"] = export_result.get("success", False)
            result["export_format"] = export_result.get("format")
            result["record_count"] = export_result.get("record_count", 0)
            result["download_url"] = export_result.get("download_url")
            result["export_data"] = export_result.get("data")  # Inline data for JSON

        elif operation == "undo_change":
            undo_data = command.get("undo_data", {})
            undo_result = await execute_undo(session, undo_data)
            result["message"] = undo_result.get("message", "Änderung rückgängig gemacht")
            result["success"] = undo_result.get("success", False)
            result["restored_values"] = undo_result.get("restored_values")

        elif operation == "get_change_history":
            history_data = command.get("history_data", {})
            history_result = await execute_get_history(session, history_data)
            result["message"] = history_result.get("message", "Änderungshistorie")
            result["success"] = history_result.get("success", False)
            result["history"] = history_result.get("history", [])

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
        try:
            await session.commit()
        except Exception:
            pass  # History save failure shouldn't affect main result

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
        "created_items": [],
        "warnings": [],
    }

    try:
        for i, op in enumerate(operations):
            op_type = op.get("operation")
            op_result = None

            logger.info(f"Executing combined operation {i+1}/{len(operations)}", operation=op_type)

            if op_type == "create_category_setup":
                # Support both nested and flat format from AI
                setup_data = op.get("category_setup_data", {})
                category_slug = op.get("category_slug") or setup_data.get("category_slug")

                if category_slug:
                    # Link to existing category instead of creating new one
                    op_result = await execute_link_existing_category(session, category_slug)
                else:
                    user_intent = setup_data.get("user_intent", setup_data.get("purpose", ""))
                    geographic_filter = setup_data.get("geographic_filter", {})
                    op_result = await create_category_setup_with_ai(
                        session, user_intent, geographic_filter, current_user_id
                    )

            elif op_type == "start_crawl":
                crawl_data = op.get("crawl_command_data", {})
                op_result = await execute_crawl_command(session, crawl_data)

            elif op_type == "discover_sources":
                discover_data = op.get("discover_sources_data", {})
                op_result = await execute_discover_sources(session, discover_data)

            elif op_type == "create_entity_type":
                # Support both nested and flat format from AI
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

            elif op_type == "fetch_and_create_from_api":
                fetch_data = op.get("fetch_and_create_data", {})
                op_result = await execute_fetch_and_create_from_api(session, fetch_data)

            elif op_type == "assign_facet_types" or op_type == "assign_facet_type":
                # Support both nested and flat format from AI
                assign_data = op.get("assign_facet_types_data") or op.get("assign_facet_type_data", {})
                # If flat format: take facet_type and entity_type directly from op
                if not assign_data and (op.get("facet_type") or op.get("entity_type")):
                    assign_data = {
                        "facet_type_slug": op.get("facet_type"),
                        "entity_type_slug": op.get("entity_type"),
                    }
                op_result = await execute_assign_facet_types(session, assign_data)

            elif op_type == "link_category_entity_types":
                link_data = op.get("link_data", {})
                op_result = await execute_link_category_entity_types(session, link_data)

            elif op_type == "create_relation":
                # Support flat format from AI: relation_type, from_entity_type, to_entity_type
                relation_data = op.get("relation_data", {})
                if not relation_data:
                    relation_data = {
                        "relation_type": op.get("relation_type"),
                        "source_type": op.get("from_entity_type"),
                        "target_type": op.get("to_entity_type"),
                    }
                op_result = await execute_create_relation_type(session, relation_data)

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


async def execute_pysis_analyze(
    session: AsyncSession,
    pysis_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute PySis analysis for facets."""
    from services.pysis_facet_service import PySisFacetService

    entity_id = pysis_data.get("entity_id")
    entity_name = pysis_data.get("entity_name")
    process_id = pysis_data.get("process_id")

    # Find entity by name if no ID provided
    if not entity_id and entity_name:
        entity = await find_entity_by_name(session, entity_name)
        if entity:
            entity_id = entity.id
        else:
            return {"success": False, "message": f"Entity '{entity_name}' nicht gefunden"}

    if not entity_id:
        return {"success": False, "message": "Entity-ID oder Entity-Name erforderlich"}

    try:
        service = PySisFacetService(session)
        task = await service.analyze_for_facets(
            entity_id=UUID(str(entity_id)) if isinstance(entity_id, str) else entity_id,
            process_id=UUID(str(process_id)) if process_id else None,
            include_empty=pysis_data.get("include_empty", False),
            min_confidence=pysis_data.get("min_confidence", 0.0),
        )
        return {
            "success": True,
            "message": f"PySis-Analyse gestartet",
            "task_id": str(task.id),
        }
    except ValueError as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        logger.error("PySis analyze failed", error=str(e))
        return {"success": False, "message": f"Fehler: {str(e)}"}


async def execute_pysis_enrich(
    session: AsyncSession,
    pysis_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute facet enrichment from PySis data."""
    from services.pysis_facet_service import PySisFacetService

    entity_id = pysis_data.get("entity_id")
    entity_name = pysis_data.get("entity_name")
    facet_type_id = pysis_data.get("facet_type_id")
    overwrite = pysis_data.get("overwrite", False)

    # Find entity by name if no ID provided
    if not entity_id and entity_name:
        entity = await find_entity_by_name(session, entity_name)
        if entity:
            entity_id = entity.id
        else:
            return {"success": False, "message": f"Entity '{entity_name}' nicht gefunden"}

    if not entity_id:
        return {"success": False, "message": "Entity-ID oder Entity-Name erforderlich"}

    try:
        service = PySisFacetService(session)
        task = await service.enrich_facets_from_pysis(
            entity_id=UUID(str(entity_id)) if isinstance(entity_id, str) else entity_id,
            facet_type_id=UUID(str(facet_type_id)) if facet_type_id else None,
            overwrite=overwrite,
        )
        return {
            "success": True,
            "message": f"Facet-Anreicherung gestartet",
            "task_id": str(task.id),
        }
    except ValueError as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        logger.error("PySis enrich failed", error=str(e))
        return {"success": False, "message": f"Fehler: {str(e)}"}


async def execute_entity_update(
    session: AsyncSession,
    update_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Update an existing entity."""
    from app.models import Entity

    entity_id = update_data.get("entity_id")
    entity_name = update_data.get("entity_name")

    # Find entity
    if entity_id:
        entity = await session.get(Entity, UUID(str(entity_id)))
    elif entity_name:
        entity = await find_entity_by_name(session, entity_name)
    else:
        return {"success": False, "message": "Entity-ID oder Entity-Name erforderlich"}

    if not entity:
        return {"success": False, "message": "Entity nicht gefunden"}

    # Update fields
    updates = update_data.get("updates", {})
    if "name" in updates:
        entity.name = updates["name"]
    if "core_attributes" in updates:
        entity.core_attributes = {**(entity.core_attributes or {}), **updates["core_attributes"]}
    if "external_id" in updates:
        entity.external_id = updates["external_id"]

    await session.flush()

    return {
        "success": True,
        "message": f"Entity '{entity.name}' aktualisiert",
        "entity_id": str(entity.id),
    }


async def execute_facet_type_create(
    session: AsyncSession,
    facet_type_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a new FacetType.

    This is the unified executor for FacetType creation, used by both
    the Smart Query system and the REST API endpoint.
    """
    from app.models import FacetType
    from sqlalchemy import select, or_
    from .utils import generate_slug

    name = facet_type_data.get("name")
    if not name:
        return {"success": False, "message": "Name für Facet-Typ erforderlich"}

    # Use provided slug or generate from name
    slug = facet_type_data.get("slug")
    if not slug:
        slug = generate_slug(name)

    # Check if name or slug already exists
    existing = await session.execute(
        select(FacetType).where(
            or_(FacetType.slug == slug, FacetType.name == name)
        )
    )
    if existing.scalar_one_or_none():
        return {"success": False, "message": f"Facet-Typ mit Name '{name}' oder Slug '{slug}' existiert bereits"}

    # Validate applicable_entity_type_slugs
    applicable_slugs = facet_type_data.get("applicable_entity_type_slugs") or []
    if applicable_slugs:
        from app.core.validators import validate_entity_type_slugs
        _, invalid_slugs = await validate_entity_type_slugs(session, applicable_slugs)
        if invalid_slugs:
            return {
                "success": False,
                "message": f"Ungültige Entity-Typ-Slugs: {', '.join(sorted(invalid_slugs))}",
            }

    # Create FacetType with all supported fields
    facet_type = FacetType(
        name=name,
        name_plural=facet_type_data.get("name_plural") or (f"{name}s" if not name.endswith("s") else name),
        slug=slug,
        description=facet_type_data.get("description") or f"Facet-Typ: {name}",
        icon=facet_type_data.get("icon") or "mdi-tag",
        color=facet_type_data.get("color") or "#2196F3",
        value_type=facet_type_data.get("value_type") or "structured",
        value_schema=facet_type_data.get("value_schema"),
        applicable_entity_type_slugs=facet_type_data.get("applicable_entity_type_slugs") or [],
        display_order=facet_type_data.get("display_order"),
        aggregation_method=facet_type_data.get("aggregation_method"),
        deduplication_fields=facet_type_data.get("deduplication_fields"),
        is_time_based=facet_type_data.get("is_time_based", False),
        time_field_path=facet_type_data.get("time_field_path"),
        default_time_filter=facet_type_data.get("default_time_filter"),
        ai_extraction_enabled=facet_type_data.get("ai_extraction_enabled", True),
        ai_extraction_prompt=facet_type_data.get("ai_extraction_prompt") or f"Extrahiere {name} aus dem Dokument.",
        is_active=facet_type_data.get("is_active", True),
        is_system=False,
    )

    session.add(facet_type)
    await session.flush()

    return {
        "success": True,
        "message": f"Facet-Typ '{name}' erstellt",
        "facet_type_id": str(facet_type.id),
        "facet_type_name": facet_type.name,
        "facet_type_slug": facet_type.slug,
    }


async def execute_facet_type_assign(
    session: AsyncSession,
    assign_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Assign a FacetType to EntityTypes."""
    from app.models import FacetType
    from sqlalchemy import select

    facet_type_slug = assign_data.get("facet_type_slug")
    target_slugs = assign_data.get("target_entity_type_slugs", [])

    if not facet_type_slug:
        return {"success": False, "message": "Facet-Typ-Slug erforderlich"}

    if not target_slugs:
        return {"success": False, "message": "Mindestens ein Entity-Typ-Slug erforderlich"}

    # Find FacetType
    result = await session.execute(
        select(FacetType).where(FacetType.slug == facet_type_slug)
    )
    facet_type = result.scalar_one_or_none()

    if not facet_type:
        return {"success": False, "message": f"Facet-Typ '{facet_type_slug}' nicht gefunden"}

    # Update applicable_entity_type_slugs
    existing_slugs = facet_type.applicable_entity_type_slugs or []
    new_slugs = list(set(existing_slugs + target_slugs))
    facet_type.applicable_entity_type_slugs = new_slugs

    await session.flush()

    return {
        "success": True,
        "message": f"Facet-Typ '{facet_type.name}' zugewiesen an: {', '.join(target_slugs)}",
    }


async def execute_batch_operation(
    session: AsyncSession,
    batch_data: Dict[str, Any],
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Execute a batch operation on multiple entities.

    Supports: add_facet, update_field, add_relation, remove_facet
    """
    from app.models import Entity, EntityType, FacetType, FacetValue
    from app.models.facet_value import FacetValueSourceType
    from sqlalchemy import select, and_

    action_type = batch_data.get("action_type")
    target_filter = batch_data.get("target_filter", {})
    action_data = batch_data.get("action_data", {})

    if not action_type:
        return {"success": False, "message": "action_type erforderlich"}

    # Build entity query based on filter
    query = select(Entity)

    # Filter by entity type
    entity_type_slug = target_filter.get("entity_type")
    if entity_type_slug:
        et_result = await session.execute(
            select(EntityType).where(EntityType.slug == entity_type_slug)
        )
        entity_type = et_result.scalar_one_or_none()
        if entity_type:
            query = query.where(Entity.entity_type_id == entity_type.id)
        else:
            return {"success": False, "message": f"Entity-Typ '{entity_type_slug}' nicht gefunden"}

    # Filter by location (simplified - checks core_attributes)
    location_filter = target_filter.get("location_filter")
    if location_filter:
        # This is a simplified filter - in reality you'd want to check location relations
        query = query.where(
            Entity.core_attributes["admin_level_1"].astext == location_filter
        )

    # Additional filters
    additional = target_filter.get("additional_filters", {})
    for key, value in additional.items():
        query = query.where(
            Entity.core_attributes[key].astext == value
        )

    # Execute query
    result = await session.execute(query.limit(1000))  # Safety limit
    entities = result.scalars().all()

    if not entities:
        return {
            "success": True,
            "message": "Keine passenden Entities gefunden",
            "affected_count": 0,
            "preview": [],
        }

    # Build preview
    preview = [
        {
            "entity_id": str(e.id),
            "entity_name": e.name,
            "entity_type": entity_type_slug or "unknown",
        }
        for e in entities[:20]  # Limit preview to 20
    ]

    if dry_run:
        return {
            "success": True,
            "message": f"{len(entities)} Entities würden bearbeitet werden (Vorschau)",
            "affected_count": len(entities),
            "preview": preview,
            "dry_run": True,
        }

    # Execute the actual operation
    affected = 0

    if action_type == "add_facet":
        facet_type_slug = action_data.get("facet_type")
        facet_value = action_data.get("facet_value", {})

        # Find FacetType
        ft_result = await session.execute(
            select(FacetType).where(FacetType.slug == facet_type_slug)
        )
        facet_type = ft_result.scalar_one_or_none()
        if not facet_type:
            return {"success": False, "message": f"Facet-Typ '{facet_type_slug}' nicht gefunden"}

        for entity in entities:
            fv = FacetValue(
                entity_id=entity.id,
                facet_type_id=facet_type.id,
                value=facet_value,
                text_representation=facet_value.get("description", str(facet_value)[:100]),
                confidence_score=1.0,
                human_verified=False,
                source_type=FacetValueSourceType.SMART_QUERY,
            )
            session.add(fv)
            affected += 1

    elif action_type == "update_field":
        field_name = action_data.get("field_name")
        field_value = action_data.get("field_value")

        if not field_name:
            return {"success": False, "message": "field_name erforderlich"}

        for entity in entities:
            if entity.core_attributes is None:
                entity.core_attributes = {}
            entity.core_attributes[field_name] = field_value
            affected += 1

    elif action_type == "remove_facet":
        facet_type_slug = action_data.get("facet_type")

        # Find FacetType
        ft_result = await session.execute(
            select(FacetType).where(FacetType.slug == facet_type_slug)
        )
        facet_type = ft_result.scalar_one_or_none()
        if not facet_type:
            return {"success": False, "message": f"Facet-Typ '{facet_type_slug}' nicht gefunden"}

        for entity in entities:
            # Find and delete facets
            fv_result = await session.execute(
                select(FacetValue).where(
                    and_(
                        FacetValue.entity_id == entity.id,
                        FacetValue.facet_type_id == facet_type.id
                    )
                )
            )
            facet_values = fv_result.scalars().all()
            for fv in facet_values:
                session.delete(fv)
                affected += 1

    else:
        return {"success": False, "message": f"Unbekannter action_type: {action_type}"}

    await session.flush()

    return {
        "success": True,
        "message": f"Batch-Operation ausgeführt: {affected} Änderungen",
        "affected_count": affected,
        "preview": preview,
        "dry_run": False,
    }


async def execute_delete_entity(
    session: AsyncSession,
    delete_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Delete a single entity (soft-delete by setting is_active=False).

    This is a reversible operation - the entity is marked as inactive
    but not permanently removed from the database.
    """
    from app.models import Entity

    entity_id = delete_data.get("entity_id")
    entity_name = delete_data.get("entity_name")
    reason = delete_data.get("reason", "Gelöscht über Smart Query")

    # Find entity
    entity = None
    if entity_id:
        entity = await session.get(Entity, UUID(str(entity_id)))
    elif entity_name:
        entity = await find_entity_by_name(session, entity_name)

    if not entity:
        return {
            "success": False,
            "message": f"Entity nicht gefunden: {entity_name or entity_id}",
            "deleted_items": [],
        }

    if not entity.is_active:
        return {
            "success": False,
            "message": f"Entity '{entity.name}' ist bereits inaktiv/gelöscht",
            "deleted_items": [],
        }

    # Soft-delete: Set is_active to False
    entity.is_active = False

    # Store deletion reason in core_attributes
    if entity.core_attributes is None:
        entity.core_attributes = {}
    entity.core_attributes["_deletion_reason"] = reason
    entity.core_attributes["_deleted_at"] = str(datetime.now(timezone.utc).isoformat())

    await session.flush()

    logger.info(
        "Entity soft-deleted via Smart Query",
        entity_id=str(entity.id),
        entity_name=entity.name,
        reason=reason,
    )

    return {
        "success": True,
        "message": f"Entity '{entity.name}' wurde gelöscht (kann wiederhergestellt werden)",
        "deleted_items": [
            {
                "type": "entity",
                "id": str(entity.id),
                "name": entity.name,
                "entity_type": delete_data.get("entity_type", "unknown"),
            }
        ],
    }


async def execute_delete_facet(
    session: AsyncSession,
    delete_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Delete facet(s) from an entity.

    Supports:
    - Deleting a specific facet by ID
    - Deleting all facets of a type from an entity
    - Deleting a facet matching a description
    """
    from app.models import Entity, FacetType, FacetValue
    from sqlalchemy import select, and_

    entity_id = delete_data.get("entity_id")
    entity_name = delete_data.get("entity_name")
    facet_type_slug = delete_data.get("facet_type")
    facet_id = delete_data.get("facet_id")
    facet_description = delete_data.get("facet_description")
    delete_all_of_type = delete_data.get("delete_all_of_type", False)

    # Find entity
    entity = None
    if entity_id:
        entity = await session.get(Entity, UUID(str(entity_id)))
    elif entity_name:
        entity = await find_entity_by_name(session, entity_name)

    if not entity:
        return {
            "success": False,
            "message": f"Entity nicht gefunden: {entity_name or entity_id}",
            "deleted_items": [],
        }

    deleted_items = []

    # Case 1: Delete specific facet by ID
    if facet_id:
        facet = await session.get(FacetValue, UUID(str(facet_id)))
        if facet and facet.entity_id == entity.id:
            await session.delete(facet)
            deleted_items.append({
                "type": "facet",
                "id": str(facet.id),
                "facet_type": facet_type_slug,
                "text": facet.text_representation,
            })
        else:
            return {
                "success": False,
                "message": "Facet nicht gefunden oder gehört nicht zur angegebenen Entity",
                "deleted_items": [],
            }

    # Case 2: Delete by facet type
    elif facet_type_slug:
        # Find FacetType
        ft_result = await session.execute(
            select(FacetType).where(FacetType.slug == facet_type_slug)
        )
        facet_type = ft_result.scalar_one_or_none()
        if not facet_type:
            return {
                "success": False,
                "message": f"Facet-Typ '{facet_type_slug}' nicht gefunden",
                "deleted_items": [],
            }

        # Build query for facets
        query = select(FacetValue).where(
            and_(
                FacetValue.entity_id == entity.id,
                FacetValue.facet_type_id == facet_type.id,
                FacetValue.is_active.is_(True),
            )
        )

        # Filter by description if provided
        if facet_description and not delete_all_of_type:
            query = query.where(
                FacetValue.text_representation.ilike(f"%{facet_description}%")
            )

        result = await session.execute(query)
        facets = result.scalars().all()

        if not facets:
            return {
                "success": False,
                "message": f"Keine passenden Facets vom Typ '{facet_type_slug}' gefunden",
                "deleted_items": [],
            }

        # Delete all matching or just first if not delete_all_of_type
        facets_to_delete = facets if delete_all_of_type else facets[:1]

        for facet in facets_to_delete:
            await session.delete(facet)
            deleted_items.append({
                "type": "facet",
                "id": str(facet.id),
                "facet_type": facet_type_slug,
                "text": facet.text_representation[:100] if facet.text_representation else None,
            })

    else:
        return {
            "success": False,
            "message": "Facet-ID oder Facet-Typ erforderlich",
            "deleted_items": [],
        }

    await session.flush()

    logger.info(
        "Facets deleted via Smart Query",
        entity_id=str(entity.id),
        entity_name=entity.name,
        deleted_count=len(deleted_items),
    )

    return {
        "success": True,
        "message": f"{len(deleted_items)} Facet(s) von '{entity.name}' gelöscht",
        "deleted_items": deleted_items,
    }


async def execute_batch_delete(
    session: AsyncSession,
    delete_data: Dict[str, Any],
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Execute batch deletion of entities or facets.

    Supports:
    - Deleting all entities matching filters (soft-delete)
    - Deleting all facets of a type matching filters
    """
    from app.models import Entity, EntityType, FacetType, FacetValue
    from sqlalchemy import select, and_
    from datetime import datetime

    delete_type = delete_data.get("delete_type", "facets")
    target_filter = delete_data.get("target_filter", {})
    reason = delete_data.get("reason", "Batch-Löschung über Smart Query")

    entity_type_slug = target_filter.get("entity_type")
    location_filter = target_filter.get("location_filter")
    facet_type_slug = target_filter.get("facet_type")
    date_before = target_filter.get("date_before")
    additional_filters = target_filter.get("additional_filters", {})

    # Build base entity query
    entity_query = select(Entity).where(Entity.is_active.is_(True))

    # Filter by entity type
    entity_type = None
    if entity_type_slug:
        et_result = await session.execute(
            select(EntityType).where(EntityType.slug == entity_type_slug)
        )
        entity_type = et_result.scalar_one_or_none()
        if entity_type:
            entity_query = entity_query.where(Entity.entity_type_id == entity_type.id)
        else:
            return {"success": False, "message": f"Entity-Typ '{entity_type_slug}' nicht gefunden"}

    # Filter by location
    if location_filter:
        # Resolve alias
        from .geographic_utils import resolve_geographic_alias
        resolved_location = resolve_geographic_alias(location_filter)
        entity_query = entity_query.where(Entity.admin_level_1 == resolved_location)

    # Additional filters
    for key, value in additional_filters.items():
        if key == "is_active" and value is False:
            # Special case: find inactive entities
            entity_query = entity_query.where(Entity.is_active.is_(False))
        else:
            entity_query = entity_query.where(
                Entity.core_attributes[key].astext == str(value)
            )

    # Execute entity query
    result = await session.execute(entity_query.limit(1000))  # Safety limit
    entities = result.scalars().all()

    if not entities:
        return {
            "success": True,
            "message": "Keine passenden Entities gefunden",
            "affected_count": 0,
            "preview": [],
        }

    # Build preview
    preview = []
    affected_count = 0

    if delete_type == "entities":
        # Delete entities (soft-delete)
        for entity in entities[:20]:  # Preview limit
            preview.append({
                "type": "entity",
                "id": str(entity.id),
                "name": entity.name,
                "entity_type": entity_type_slug or "unknown",
            })
        affected_count = len(entities)

        if dry_run:
            return {
                "success": True,
                "message": f"{affected_count} Entities würden gelöscht werden (Vorschau)",
                "affected_count": affected_count,
                "preview": preview,
                "dry_run": True,
            }

        # Execute soft-delete
        for entity in entities:
            entity.is_active = False
            if entity.core_attributes is None:
                entity.core_attributes = {}
            entity.core_attributes["_deletion_reason"] = reason
            entity.core_attributes["_deleted_at"] = str(datetime.now(timezone.utc).isoformat())

    elif delete_type == "facets":
        # Delete facets from entities
        if not facet_type_slug:
            return {"success": False, "message": "facet_type erforderlich für Facet-Löschung"}

        # Find FacetType
        ft_result = await session.execute(
            select(FacetType).where(FacetType.slug == facet_type_slug)
        )
        facet_type = ft_result.scalar_one_or_none()
        if not facet_type:
            return {"success": False, "message": f"Facet-Typ '{facet_type_slug}' nicht gefunden"}

        # Find all matching facets
        entity_ids = [e.id for e in entities]
        facet_query = select(FacetValue).where(
            and_(
                FacetValue.entity_id.in_(entity_ids),
                FacetValue.facet_type_id == facet_type.id,
                FacetValue.is_active.is_(True),
            )
        )

        # Filter by date if provided
        if date_before:
            try:
                from datetime import datetime
                date_limit = datetime.strptime(date_before, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                facet_query = facet_query.where(FacetValue.event_date < date_limit)
            except ValueError:
                pass  # Ignore invalid date

        facet_result = await session.execute(facet_query.limit(1000))
        facets = facet_result.scalars().all()

        for facet in facets[:20]:  # Preview limit
            preview.append({
                "type": "facet",
                "id": str(facet.id),
                "entity_id": str(facet.entity_id),
                "facet_type": facet_type_slug,
                "text": facet.text_representation[:50] if facet.text_representation else None,
            })
        affected_count = len(facets)

        if dry_run:
            return {
                "success": True,
                "message": f"{affected_count} Facets würden gelöscht werden (Vorschau)",
                "affected_count": affected_count,
                "preview": preview,
                "dry_run": True,
            }

        # Execute delete
        for facet in facets:
            await session.delete(facet)

    else:
        return {"success": False, "message": f"Unbekannter delete_type: {delete_type}"}

    await session.flush()

    logger.info(
        "Batch delete executed via Smart Query",
        delete_type=delete_type,
        affected_count=affected_count,
        reason=reason,
    )

    return {
        "success": True,
        "message": f"Batch-Löschung ausgeführt: {affected_count} {delete_type} gelöscht",
        "affected_count": affected_count,
        "preview": preview,
        "dry_run": False,
    }


async def execute_export(
    session: AsyncSession,
    export_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute entity export based on query filters.

    Supports formats: csv, json, excel
    Returns data inline for JSON, or a preview for CSV/Excel.
    """
    import csv
    import io
    import json
    from app.models import Entity, EntityType, FacetType, FacetValue
    from sqlalchemy import select, and_

    export_format = export_data.get("format", "json").lower()
    query_filter = export_data.get("query_filter", {})
    include_facets = export_data.get("include_facets", True)
    include_relations = export_data.get("include_relations", False)
    filename = export_data.get("filename", "smart_query_export")

    entity_type_slug = query_filter.get("entity_type", "territorial_entity")
    location_filter = query_filter.get("location_filter")
    facet_type_slugs = query_filter.get("facet_types", [])
    position_keywords = query_filter.get("position_keywords", [])
    country = query_filter.get("country")

    # Build entity query
    entity_query = select(Entity).where(Entity.is_active.is_(True))

    # Filter by entity type
    et_result = await session.execute(
        select(EntityType).where(EntityType.slug == entity_type_slug)
    )
    entity_type = et_result.scalar_one_or_none()
    if entity_type:
        entity_query = entity_query.where(Entity.entity_type_id == entity_type.id)
    else:
        return {"success": False, "message": f"Entity-Typ '{entity_type_slug}' nicht gefunden"}

    # Filter by location
    if location_filter:
        from .geographic_utils import resolve_geographic_alias
        resolved_location = resolve_geographic_alias(location_filter)
        entity_query = entity_query.where(Entity.admin_level_1 == resolved_location)

    # Filter by country
    if country:
        entity_query = entity_query.where(Entity.country == country)

    # Filter by position keywords
    if position_keywords and entity_type_slug == "person":
        from sqlalchemy import or_
        position_conditions = []
        for keyword in position_keywords:
            position_conditions.append(
                Entity.core_attributes["position"].astext.ilike(f"%{keyword}%")
            )
        if position_conditions:
            entity_query = entity_query.where(or_(*position_conditions))

    # Execute query
    result = await session.execute(entity_query.limit(5000))  # Export limit
    entities = result.scalars().all()

    if not entities:
        return {
            "success": True,
            "message": "Keine Entities für Export gefunden",
            "format": export_format,
            "record_count": 0,
            "data": [],
        }

    # Load facet types for filtering
    facet_type_map = {}
    if facet_type_slugs and include_facets:
        for ft_slug in facet_type_slugs:
            ft_result = await session.execute(
                select(FacetType).where(FacetType.slug == ft_slug)
            )
            ft = ft_result.scalar_one_or_none()
            if ft:
                facet_type_map[ft_slug] = ft

    # Bulk load facets if requested
    entity_ids = [e.id for e in entities]
    facets_by_entity: Dict[UUID, List[Dict]] = {eid: [] for eid in entity_ids}

    if include_facets:
        facet_query = select(FacetValue).where(
            FacetValue.entity_id.in_(entity_ids),
            FacetValue.is_active.is_(True),
        )
        if facet_type_map:
            facet_type_ids = [ft.id for ft in facet_type_map.values()]
            facet_query = facet_query.where(FacetValue.facet_type_id.in_(facet_type_ids))

        fv_result = await session.execute(facet_query)
        for fv in fv_result.scalars().all():
            facets_by_entity[fv.entity_id].append({
                "type": str(fv.facet_type_id),
                "value": fv.value,
                "text": fv.text_representation,
                "date": fv.event_date.isoformat() if fv.event_date else None,
            })

    # Build export data
    export_records = []
    for entity in entities:
        record = {
            "id": str(entity.id),
            "name": entity.name,
            "slug": entity.slug,
            "entity_type": entity_type_slug,
            "country": entity.country,
            "admin_level_1": entity.admin_level_1,
            **{k: v for k, v in (entity.core_attributes or {}).items() if not k.startswith("_")},
        }

        if include_facets:
            record["facets"] = facets_by_entity.get(entity.id, [])
            record["facet_count"] = len(record["facets"])

        export_records.append(record)

    # Format output
    if export_format == "json":
        return {
            "success": True,
            "message": f"Export erstellt: {len(export_records)} {entity_type.name_plural or entity_type.name}",
            "format": "json",
            "record_count": len(export_records),
            "data": export_records,
            "filename": f"{filename}.json",
        }

    elif export_format == "csv":
        # Create CSV in memory
        output = io.StringIO()
        if export_records:
            # Flatten facets for CSV
            flat_records = []
            for record in export_records:
                flat_record = {k: v for k, v in record.items() if k != "facets"}
                if include_facets and record.get("facets"):
                    flat_record["facet_texts"] = "; ".join(
                        f.get("text", "") for f in record["facets"] if f.get("text")
                    )
                flat_records.append(flat_record)

            fieldnames = list(flat_records[0].keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(flat_records)

        csv_content = output.getvalue()

        return {
            "success": True,
            "message": f"CSV-Export erstellt: {len(export_records)} Datensätze",
            "format": "csv",
            "record_count": len(export_records),
            "data": csv_content,
            "filename": f"{filename}.csv",
            "content_type": "text/csv",
        }

    elif export_format == "excel":
        # For Excel, we return the data structure and let the API handle XLSX generation
        # Since openpyxl might not be installed, we'll return a JSON preview
        return {
            "success": True,
            "message": f"Excel-Export vorbereitet: {len(export_records)} Datensätze. Verwende /api/v1/export/excel Endpoint.",
            "format": "excel",
            "record_count": len(export_records),
            "data": export_records[:100],  # Preview only
            "filename": f"{filename}.xlsx",
            "note": "Für vollständigen Excel-Export, nutze den dedizierten Export-Endpoint",
        }

    else:
        return {
            "success": False,
            "message": f"Unbekanntes Export-Format: {export_format}. Unterstützt: csv, json, excel",
        }


async def execute_undo(
    session: AsyncSession,
    undo_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute UNDO operation to revert the last change.

    Uses the ChangeTracker service to restore previous state.
    """
    from services.change_tracker import ChangeTracker

    entity_name = undo_data.get("entity_name")
    entity_id = undo_data.get("entity_id")
    entity_type = undo_data.get("entity_type", "Entity")

    # Find entity by name if no ID provided
    target_id = None
    if entity_id:
        target_id = UUID(str(entity_id))
    elif entity_name:
        if entity_type == "Entity":
            entity = await find_entity_by_name(session, entity_name)
            if entity:
                target_id = entity.id
            else:
                return {"success": False, "message": f"Entity '{entity_name}' nicht gefunden"}
        else:
            return {"success": False, "message": "Für Facet-UNDO ist eine Facet-ID erforderlich"}

    if not target_id:
        return {"success": False, "message": "Entity-ID oder Entity-Name erforderlich"}

    # Use ChangeTracker to undo
    tracker = ChangeTracker(session)
    success, message, restored_values = await tracker.undo_last_change(entity_type, target_id)

    return {
        "success": success,
        "message": message,
        "restored_values": restored_values,
    }


async def execute_get_history(
    session: AsyncSession,
    history_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Get change history for an entity.

    Uses the ChangeTracker service to retrieve version history.
    """
    from services.change_tracker import ChangeTracker

    entity_name = history_data.get("entity_name")
    entity_id = history_data.get("entity_id")
    entity_type = history_data.get("entity_type", "Entity")
    limit = history_data.get("limit", 10)

    # Find entity by name if no ID provided
    target_id = None
    entity_display_name = entity_name

    if entity_id:
        target_id = UUID(str(entity_id))
    elif entity_name:
        if entity_type == "Entity":
            entity = await find_entity_by_name(session, entity_name)
            if entity:
                target_id = entity.id
                entity_display_name = entity.name
            else:
                return {"success": False, "message": f"Entity '{entity_name}' nicht gefunden", "history": []}
        else:
            return {"success": False, "message": "Für Facet-Historie ist eine Facet-ID erforderlich", "history": []}

    if not target_id:
        return {"success": False, "message": "Entity-ID oder Entity-Name erforderlich", "history": []}

    # Use ChangeTracker to get history
    tracker = ChangeTracker(session)
    history = await tracker.get_change_history(entity_type, target_id, limit=limit)

    if not history:
        return {
            "success": True,
            "message": f"Keine Änderungshistorie für '{entity_display_name}' gefunden",
            "history": [],
        }

    return {
        "success": True,
        "message": f"Änderungshistorie für '{entity_display_name}': {len(history)} Einträge",
        "history": history,
    }


async def execute_discover_sources(
    session: AsyncSession,
    discover_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute AI-powered data source discovery.

    Uses the AISourceDiscoveryService to search the internet for data sources
    matching a natural language prompt, and optionally imports them.

    Args:
        session: Database session
        discover_data: Dict with keys:
            - prompt: Natural language search prompt (required)
            - max_results: Maximum sources to find (default: 50)
            - search_depth: quick, standard, or deep (default: standard)
            - auto_import: Whether to import found sources (default: False)
            - category_ids: Categories to assign to imported sources (optional)

    Returns:
        Dict with discovery results, sources found, and import status
    """
    from services.ai_source_discovery import AISourceDiscoveryService
    from app.models import DataSource, DataSourceCategory

    prompt = discover_data.get("prompt")
    if not prompt:
        return {
            "success": False,
            "message": "Suchbegriff (prompt) erforderlich",
            "sources_found": [],
            "sources_count": 0,
        }

    max_results = discover_data.get("max_results", 50)
    search_depth = discover_data.get("search_depth", "standard")
    auto_import = discover_data.get("auto_import", False)
    category_ids = discover_data.get("category_ids", [])

    try:
        # Run discovery
        service = AISourceDiscoveryService()
        discovery_result = await service.discover_sources(
            prompt=prompt,
            max_results=max_results,
            search_depth=search_depth,
        )

        # Convert sources to serializable format
        sources_list = []
        for source in discovery_result.sources:
            sources_list.append({
                "name": source.name,
                "base_url": source.base_url,
                "source_type": source.source_type,
                "tags": source.tags,
                "confidence": source.confidence,
                "metadata": source.metadata,
            })

        result = {
            "success": True,
            "message": f"{len(sources_list)} Datenquellen gefunden für '{prompt}'",
            "sources_found": sources_list,
            "sources_count": len(sources_list),
            "search_strategy": {
                "queries": discovery_result.search_strategy.search_queries if discovery_result.search_strategy else [],
                "base_tags": discovery_result.search_strategy.base_tags if discovery_result.search_strategy else [],
            } if discovery_result.search_strategy else None,
            "stats": {
                "pages_searched": discovery_result.stats.pages_searched,
                "sources_extracted": discovery_result.stats.sources_extracted,
                "duplicates_removed": discovery_result.stats.duplicates_removed,
            } if discovery_result.stats else None,
            "warnings": discovery_result.warnings,
            "imported_count": 0,
        }

        # Auto-import if requested
        if auto_import and sources_list:
            imported_count = 0
            for source_data in sources_list:
                try:
                    # Check if URL already exists
                    from sqlalchemy import select
                    existing = await session.execute(
                        select(DataSource).where(DataSource.base_url == source_data["base_url"])
                    )
                    if existing.scalar_one_or_none():
                        continue

                    # Create new DataSource
                    new_source = DataSource(
                        name=source_data["name"],
                        base_url=source_data["base_url"],
                        source_type=source_data.get("source_type", "WEBSITE"),
                        tags=source_data.get("tags", []),
                        status="ACTIVE",
                        crawl_config={
                            "max_depth": 3,
                            "max_pages": 100,
                            "render_javascript": False,
                        },
                    )
                    session.add(new_source)
                    await session.flush()

                    # Link to categories if provided
                    for i, cat_id in enumerate(category_ids):
                        try:
                            assoc = DataSourceCategory(
                                data_source_id=new_source.id,
                                category_id=UUID(str(cat_id)),
                                is_primary=(i == 0),
                            )
                            session.add(assoc)
                        except Exception:
                            pass

                    imported_count += 1

                except Exception as e:
                    logger.warning(
                        "Failed to import source",
                        source=source_data.get("name"),
                        error=str(e),
                    )

            result["imported_count"] = imported_count
            result["message"] = f"{len(sources_list)} Datenquellen gefunden, {imported_count} importiert"

            await session.commit()

        return result

    except Exception as e:
        logger.error("Source discovery failed", error=str(e), exc_info=True)
        return {
            "success": False,
            "message": f"Fehler bei der Datenquellen-Suche: {str(e)}",
            "sources_found": [],
            "sources_count": 0,
        }


async def execute_fetch_and_create_from_api(
    session: AsyncSession,
    fetch_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Fetch data from an external API and create entities.

    This operation supports:
    - Wikidata SPARQL queries for German municipalities, Bundeslaender, UK councils, etc.
    - REST APIs with predefined templates (e.g., Caeli Auction Windparks)
    - Automatic parent entity creation for hierarchies
    - Bulk entity creation with proper hierarchy setup
    - Entity matching to link imported items to existing entities (e.g., Windpark -> Gemeinde)

    Args:
        session: Database session
        fetch_data: Dict with keys:
            - api_config: API configuration
                - type: "sparql", "rest"
                - template: Predefined template name (e.g., "caeli_auction_windparks")
                - query: SPARQL query or predefined query name
                - country: Country code for predefined queries
                - pagination: { limit, max_results }
            - entity_type: Target entity type slug
            - field_mapping: Mapping from API fields to entity fields
            - parent_config: Optional parent entity configuration
                - field: API field containing parent name
                - entity_type: Parent entity type slug
            - create_entity_type: Whether to create the entity type if missing
            - entity_type_config: Config for new entity type
            - match_to_parent: Whether to fuzzy match items to parent entities by name

    Returns:
        Dict with fetch and create results
    """
    from .api_fetcher import ExternalAPIFetcher, get_predefined_query, get_predefined_rest_template

    api_config = fetch_data.get("api_config", {})
    entity_type_slug = fetch_data.get("entity_type", "territorial_entity")
    field_mapping = fetch_data.get("field_mapping", {})
    parent_config = fetch_data.get("parent_config")
    create_entity_type_flag = fetch_data.get("create_entity_type", False)
    entity_type_config = fetch_data.get("entity_type_config", {})
    match_to_parent = fetch_data.get("match_to_gemeinde", False) or fetch_data.get("match_to_parent", False)

    # NEW: Hierarchical import parameters for same-entity-type hierarchies
    # hierarchy_level: Explicit level to set (1=Bundesland, 2=Gemeinde within territorial-entity)
    # parent_field: API field containing parent name for lookup WITHIN SAME entity type
    hierarchy_level = fetch_data.get("hierarchy_level")
    parent_field = fetch_data.get("parent_field")

    # Check for predefined REST API template
    template_name = api_config.get("template", "")
    if template_name:
        template_config = get_predefined_rest_template(template_name)
        if template_config:
            logger.info(f"Using predefined REST API template: {template_name}")
            # Merge template config into api_config (explicit config takes precedence)
            for key, value in template_config.items():
                if key not in api_config or not api_config[key]:
                    api_config[key] = value

            # Use template's field_mapping if not provided
            # REST templates use API_field -> entity_field format
            # Code expects entity_field -> API_field format - so we invert
            if not field_mapping and template_config.get("field_mapping"):
                template_mapping = template_config["field_mapping"]
                field_mapping = {v: k for k, v in template_mapping.items()}

            # Add name_template to field_mapping if present in template
            if template_config.get("name_template"):
                if field_mapping is None:
                    field_mapping = {}
                field_mapping["name_template"] = template_config["name_template"]

            # Use template's entity_type_config if not provided
            if not entity_type_config and template_config.get("entity_type_config"):
                entity_type_config = template_config["entity_type_config"]
                entity_type_slug = entity_type_config.get("slug", entity_type_slug)
                create_entity_type_flag = True  # Auto-create from template

            # For windpark templates, auto-enable parent matching (to Gemeinden)
            if "windpark" in template_name.lower():
                match_to_parent = True

    # Build parent_match_config if matching is enabled
    # This allows fuzzy matching of entities to parent entities by name
    parent_match_config = None
    if match_to_parent:
        # Try to get config from template
        match_field = None
        parent_entity_type = "territorial_entity"  # Default to Gemeinden

        if template_name:
            template_config = get_predefined_rest_template(template_name)
            if template_config:
                match_field = template_config.get("gemeinde_match_field") or template_config.get("parent_match_field")
                parent_entity_type = template_config.get("parent_entity_type", "territorial_entity")

        parent_match_config = {
            "field": match_field or "areaName",  # Field containing name to match
            "admin_level_field": "administrativeDivisionLevel1",  # For filtering by region
            "parent_entity_type": parent_entity_type,  # Entity type to match against
        }

    result = {
        "success": False,
        "message": "",
        "total_fetched": 0,
        "created_count": 0,
        "existing_count": 0,
        "error_count": 0,
        "matched_count": 0,  # Count of entities matched to Gemeinden
        "errors": [],
        "warnings": [],
        "entity_type": entity_type_slug,
        "parent_type": parent_config.get("entity_type") if parent_config else None,
    }

    try:
        # Step 1: Ensure entity type exists
        from app.models import EntityType
        from sqlalchemy import select

        et_result = await session.execute(
            select(EntityType).where(EntityType.slug == entity_type_slug)
        )
        entity_type = et_result.scalar_one_or_none()

        if not entity_type:
            if create_entity_type_flag and entity_type_config:
                # Create the entity type
                entity_type, et_message = await create_entity_type_from_command(
                    session, entity_type_config
                )
                if not entity_type:
                    result["message"] = f"Entity-Typ konnte nicht erstellt werden: {et_message}"
                    return result
                result["warnings"].append(f"Entity-Typ '{entity_type_slug}' erstellt")
            else:
                result["message"] = f"Entity-Typ '{entity_type_slug}' nicht gefunden"
                return result

        # Step 2: Ensure parent entity type exists (if configured)
        if parent_config:
            parent_type_slug = parent_config.get("entity_type")
            if parent_type_slug:
                pet_result = await session.execute(
                    select(EntityType).where(EntityType.slug == parent_type_slug)
                )
                parent_entity_type = pet_result.scalar_one_or_none()

                if not parent_entity_type:
                    # Create parent entity type - use provided config or defaults
                    parent_type_config = parent_config.get("parent_type_config") or parent_config.get("entity_type_config") or {
                        "name": parent_type_slug.replace("-", " ").title(),
                        "name_plural": parent_type_slug.replace("-", " ").title() + "s",
                        "slug": parent_type_slug,
                        "icon": "mdi-map-marker",
                        "color": "#FF9800",
                        "is_primary": False,
                        "is_public": True,
                        "supports_hierarchy": False,
                    }
                    parent_entity_type, pet_message = await create_entity_type_from_command(
                        session, parent_type_config
                    )
                    if parent_entity_type:
                        result["warnings"].append(f"Parent Entity-Typ '{parent_type_slug}' erstellt")

        # Step 3: Fetch data from API
        fetcher = ExternalAPIFetcher()

        try:
            # Apply default field mappings for predefined queries
            query = api_config.get("query", "")
            country = api_config.get("country", "DE")

            # Set default field mappings based on query type
            if not field_mapping:
                if "gemeinden" in query.lower() or "municipalities" in query.lower():
                    if country == "DE":
                        field_mapping = {
                            "name": "gemeindeLabel",
                            "external_id": "ags",
                            "admin_level_1": "bundeslandLabel",
                            "population": "einwohner",
                            "area": "flaeche",
                            "latitude": "lat",
                            "longitude": "lon",
                            "website": "website",  # Official website URL
                            "country": "DE",
                        }
                    elif country == "AT":
                        field_mapping = {
                            "name": "gemeindeLabel",
                            "external_id": "gkz",
                            "admin_level_1": "bundeslandLabel",
                            "population": "einwohner",
                            "area": "flaeche",
                            "latitude": "lat",
                            "longitude": "lon",
                            "website": "website",  # Official website URL
                            "country": "AT",
                        }
                elif "bundeslaender" in query.lower() or "states" in query.lower():
                    field_mapping = {
                        "name": "bundeslandLabel",
                        "population": "einwohner",
                        "area": "flaeche",
                        "latitude": "lat",
                        "longitude": "lon",
                        "website": "website",  # Official website URL
                        "country": country,
                    }
                elif "councils" in query.lower() or "parishes" in query.lower() or "uk-local-authorit" in query.lower() or "local_authorit" in query.lower():
                    field_mapping = {
                        "name": "councilLabel",
                        "external_id": "gss_code",
                        "admin_level_1": "regionLabel",
                        "population": "einwohner",
                        "latitude": "lat",
                        "longitude": "lon",
                        "website": "website",  # Official website URL
                        "country": "GB",
                    }

            # Set default hierarchy for municipalities
            # For hierarchical entity types (like territorial-entity), we use parent_field
            # to link to the parent WITHIN THE SAME entity type, not separate entity types
            if "gemeinden" in query.lower() or "municipalities" in query.lower():
                # Check if target entity type is hierarchical
                et_check = await session.execute(
                    select(EntityType).where(EntityType.slug == entity_type_slug)
                )
                entity_type_obj = et_check.scalar_one_or_none()

                if entity_type_obj and entity_type_obj.supports_hierarchy:
                    # Use same-entity-type hierarchy via parent_field
                    if hierarchy_level is None:
                        hierarchy_level = 2  # Gemeinden are level 2
                    if parent_field is None:
                        parent_field = "bundeslandLabel" if country in ["DE", "AT"] else "regionLabel"
                    logger.info(
                        "Using hierarchical parent linking within same entity type",
                        entity_type=entity_type_slug,
                        hierarchy_level=hierarchy_level,
                        parent_field=parent_field,
                    )
                elif not parent_config:
                    # Fall back to separate entity types (legacy behavior)
                    parent_config = {
                        "field": "bundeslandLabel" if country in ["DE", "AT"] else "regionLabel",
                        "entity_type": "bundesland" if country in ["DE", "AT"] else "region",
                        "create_parent_type": True,
                        "parent_type_config": {
                            "name": "Bundesland" if country == "DE" else ("Bundesland" if country == "AT" else "Region"),
                            "name_plural": "Bundesländer" if country in ["DE", "AT"] else "Regions",
                            "slug": "bundesland" if country in ["DE", "AT"] else "region",
                            "description": "Deutsche Bundesländer" if country == "DE" else ("Österreichische Bundesländer" if country == "AT" else "UK Regions"),
                            "icon": "mdi-map-marker-radius",
                            "color": "#FF9800",
                            "is_primary": False,
                            "is_public": True,
                            "supports_hierarchy": False,
                        }
                    }

            # For Bundesländer/regions at level 1 (no parent needed within same type)
            if "bundeslaender" in query.lower() or "states" in query.lower():
                if hierarchy_level is None:
                    hierarchy_level = 1  # Top-level entities

            logger.info(
                "Fetching data from external API",
                api_type=api_config.get("type"),
                query_type=query[:50] if len(query) > 50 else query,
                country=country,
            )

            fetch_result = await fetcher.fetch(api_config)

            if not fetch_result.success:
                result["message"] = f"API-Fetch fehlgeschlagen: {fetch_result.error}"
                result["errors"].append(fetch_result.error)
                return result

            result["total_fetched"] = fetch_result.total_count
            result["warnings"].extend(fetch_result.warnings)

            if not fetch_result.items:
                result["success"] = True
                result["message"] = "API lieferte keine Daten"
                return result

            logger.info(
                "API fetch successful",
                items_count=len(fetch_result.items),
            )

        finally:
            await fetcher.close()

        # Step 4: AI-based analysis of API response (if no explicit field_mapping)
        # This allows the AI to intelligently determine field mappings, DataSource creation, etc.
        use_ai_analysis = fetch_data.get("use_ai_analysis", True)  # Default: enabled

        if use_ai_analysis and not field_mapping and fetch_result.items:
            try:
                from .ai_generation import ai_analyze_api_response

                logger.info("Starting AI analysis of API response...")

                ai_result = await ai_analyze_api_response(
                    api_items=fetch_result.items,
                    user_intent=fetch_data.get("user_intent", ""),
                    api_type=api_config.get("type", "unknown"),
                    target_entity_type=entity_type_slug,
                    sample_size=5,
                )

                # Apply AI-generated field mapping
                if ai_result.get("field_mapping"):
                    field_mapping = ai_result["field_mapping"]
                    result["ai_analysis"] = {
                        "detected_type": ai_result.get("analysis", {}).get("detected_entity_type"),
                        "confidence": ai_result.get("analysis", {}).get("confidence"),
                        "reasoning": ai_result.get("reasoning"),
                    }
                    result["warnings"].extend(ai_result.get("warnings", []))

                    logger.info(
                        "AI analysis applied",
                        field_mapping_keys=list(field_mapping.keys()),
                        detected_type=ai_result.get("analysis", {}).get("detected_entity_type"),
                    )

                # Apply AI-suggested parent config if not set
                ai_parent_config = ai_result.get("parent_config", {})
                if not parent_config and ai_parent_config.get("use_hierarchy"):
                    parent_config = {
                        "field": ai_parent_config.get("parent_field"),
                        "entity_type": ai_parent_config.get("parent_entity_type", "bundesland"),
                        "create_parent_type": ai_parent_config.get("create_parent_if_missing", True),
                    }

                # Apply AI-suggested entity type config if creating new type
                ai_et_suggestion = ai_result.get("entity_type_suggestion", {})
                if create_entity_type_flag and not entity_type_config and ai_et_suggestion:
                    entity_type_config = ai_et_suggestion

            except ValueError as e:
                # AI not configured - use fallback
                logger.warning("AI analysis skipped - not configured", error=str(e))
                result["warnings"].append("KI-Analyse übersprungen - Azure OpenAI nicht konfiguriert")
            except Exception as e:
                logger.warning("AI analysis failed, using fallback", error=str(e))
                result["warnings"].append(f"KI-Analyse fehlgeschlagen: {str(e)}")

        # Step 5: Bulk create entities
        create_result = await bulk_create_entities_from_api_data(
            session=session,
            entity_type_slug=entity_type_slug,
            items=fetch_result.items,
            field_mapping=field_mapping,
            parent_config=parent_config,
            parent_match_config=parent_match_config,
            api_config=api_config,  # For automatic DataSource creation
            hierarchy_level=hierarchy_level,  # Explicit hierarchy level (1=Bundesland, 2=Gemeinde)
            parent_field=parent_field,  # API field for parent lookup within same entity type
        )

        result["created_count"] = create_result["created_count"]
        result["existing_count"] = create_result["existing_count"]
        result["error_count"] = create_result["error_count"]
        result["errors"].extend(create_result["errors"])
        result["matched_count"] = create_result.get("parents_matched", 0)
        result["hierarchy_matched_count"] = create_result.get("hierarchy_parents_matched", 0)
        result["data_sources_created"] = create_result.get("data_sources_created", 0)
        result["hierarchy_level"] = hierarchy_level

        # Commit changes
        await session.commit()

        result["success"] = True
        matched_info = f", {result['matched_count']} mit Parent-Entities verknüpft" if result["matched_count"] > 0 else ""
        hierarchy_info = f", {result['hierarchy_matched_count']} hierarchisch verknüpft" if result.get("hierarchy_matched_count", 0) > 0 else ""
        ds_info = f", {result['data_sources_created']} Datenquellen erstellt" if result.get("data_sources_created", 0) > 0 else ""
        level_info = f" (Level {hierarchy_level})" if hierarchy_level else ""
        result["message"] = (
            f"API-Import abgeschlossen{level_info}: {result['created_count']} erstellt, "
            f"{result['existing_count']} existierten bereits, "
            f"{result['error_count']} Fehler{matched_info}{hierarchy_info}{ds_info}"
        )

        logger.info(
            "Fetch and create completed",
            entity_type=entity_type_slug,
            total_fetched=result["total_fetched"],
            created=result["created_count"],
            existing=result["existing_count"],
            errors=result["error_count"],
        )

        return result

    except Exception as e:
        logger.error("Fetch and create failed", error=str(e), exc_info=True)
        await session.rollback()
        result["message"] = f"Fehler: {str(e)}"
        return result


async def execute_assign_facet_types(
    session: AsyncSession,
    assign_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Assign facet types to entity types.

    FacetType has applicable_entity_type_slugs array - we add entity type slugs to it.

    Supports two formats:
    1. Single facet to multiple entity types:
       - facet_type_slug: "pain_point"
       - target_entity_type_slugs: ["territorial_entity", "windpark"]

    2. Multiple facets to single entity type:
       - entity_type_slug: "territorial_entity"
       - facet_type_slugs: ["pain_point", "contact"]

    Args:
        assign_data: Dict with keys (see above)

    Returns:
        Dict with assignment results
    """
    from app.models import EntityType, FacetType
    from sqlalchemy import select

    # Support both formats
    facet_type_slug = assign_data.get("facet_type_slug")  # Single facet
    target_entity_type_slugs = assign_data.get("target_entity_type_slugs", [])  # Multiple targets

    entity_type_slug = assign_data.get("entity_type_slug")  # Single target
    facet_type_slugs = assign_data.get("facet_type_slugs", [])  # Multiple facets

    auto_detect = assign_data.get("auto_detect", False)

    result = {
        "success": False,
        "message": "",
        "assigned_facets": [],
        "assigned_to_entity_types": [],
    }

    try:
        # Format 1: Single facet to multiple entity types
        if facet_type_slug and target_entity_type_slugs:
            ft_result = await session.execute(
                select(FacetType).where(FacetType.slug == facet_type_slug)
            )
            facet_type = ft_result.scalar_one_or_none()

            if not facet_type:
                result["message"] = f"Facet-Typ '{facet_type_slug}' nicht gefunden"
                return result

            # Verify entity types exist
            for et_slug in target_entity_type_slugs:
                et_result = await session.execute(
                    select(EntityType).where(EntityType.slug == et_slug)
                )
                if et_result.scalar_one_or_none():
                    # Add to applicable_entity_type_slugs if not already there
                    current_slugs = list(facet_type.applicable_entity_type_slugs or [])
                    if et_slug not in current_slugs:
                        current_slugs.append(et_slug)
                        facet_type.applicable_entity_type_slugs = current_slugs
                        result["assigned_to_entity_types"].append(et_slug)

            result["assigned_facets"].append(facet_type_slug)
            await session.flush()
            result["success"] = True
            result["message"] = f"Facet '{facet_type_slug}' für {len(result['assigned_to_entity_types'])} Entity-Types aktiviert"
            return result

        # Format 2: Multiple facets to single entity type
        if entity_type_slug:
            # Verify entity type exists
            et_result = await session.execute(
                select(EntityType).where(EntityType.slug == entity_type_slug)
            )
            entity_type = et_result.scalar_one_or_none()

            if not entity_type:
                result["message"] = f"Entity-Typ '{entity_type_slug}' nicht gefunden"
                return result

            # Get facet types
            if auto_detect or not facet_type_slugs:
                ft_result = await session.execute(
                    select(FacetType).where(FacetType.is_active == True)
                )
                facet_types = list(ft_result.scalars().all())
            else:
                ft_result = await session.execute(
                    select(FacetType).where(FacetType.slug.in_(facet_type_slugs))
                )
                facet_types = list(ft_result.scalars().all())

            for facet_type in facet_types:
                current_slugs = list(facet_type.applicable_entity_type_slugs or [])
                if entity_type_slug not in current_slugs:
                    current_slugs.append(entity_type_slug)
                    facet_type.applicable_entity_type_slugs = current_slugs
                    result["assigned_facets"].append(facet_type.slug)

            await session.flush()
            result["success"] = True
            result["message"] = f"{len(result['assigned_facets'])} Facet-Types für '{entity_type_slug}' aktiviert"
            return result

        result["message"] = "Keine gültige Konfiguration: entity_type_slug oder facet_type_slug + target_entity_type_slugs erforderlich"
        return result

    except Exception as e:
        logger.error("Assign facet types failed", error=str(e), exc_info=True)
        result["message"] = f"Fehler: {str(e)}"
        return result


async def execute_link_category_entity_types(
    session: AsyncSession,
    link_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Link entity types to categories.

    Args:
        link_data: Dict with keys:
            - category_slug: Target category slug
            - entity_type_slugs: List of entity type slugs to link
            - auto_detect: Whether to auto-detect matching categories

    Returns:
        Dict with linking results
    """
    from app.models import EntityType, Category, CategoryEntityType
    from sqlalchemy import select

    category_slug = link_data.get("category_slug")
    entity_type_slugs = link_data.get("entity_type_slugs", [])
    auto_detect = link_data.get("auto_detect", False)

    result = {
        "success": False,
        "message": "",
        "linked_entity_types": [],
        "linked_categories": [],
    }

    try:
        if auto_detect:
            # Get all active categories
            cat_result = await session.execute(
                select(Category).where(Category.is_active == True)
            )
            categories = list(cat_result.scalars().all())
        else:
            cat_result = await session.execute(
                select(Category).where(Category.slug == category_slug)
            )
            categories = list(cat_result.scalars().all())

        if not categories:
            result["message"] = "Keine passenden Kategorien gefunden"
            return result

        # Get entity types
        et_result = await session.execute(
            select(EntityType).where(EntityType.slug.in_(entity_type_slugs))
        )
        entity_types = list(et_result.scalars().all())

        if not entity_types:
            result["message"] = "Keine passenden Entity-Types gefunden"
            return result

        # Create links
        for category in categories:
            for entity_type in entity_types:
                # Check if link already exists
                existing = await session.execute(
                    select(CategoryEntityType).where(
                        CategoryEntityType.category_id == category.id,
                        CategoryEntityType.entity_type_id == entity_type.id
                    )
                )
                if not existing.scalar_one_or_none():
                    link = CategoryEntityType(
                        category_id=category.id,
                        entity_type_id=entity_type.id,
                        is_primary=(entity_type.slug == "territorial_entity"),
                    )
                    session.add(link)
                    result["linked_entity_types"].append(entity_type.slug)
                    result["linked_categories"].append(category.slug)

        await session.flush()
        result["success"] = True
        result["message"] = f"{len(set(result['linked_entity_types']))} Entity-Types mit {len(set(result['linked_categories']))} Kategorien verknüpft"

        return result

    except Exception as e:
        logger.error("Link category entity types failed", error=str(e), exc_info=True)
        result["message"] = f"Fehler: {str(e)}"
        return result


async def execute_link_existing_category(
    session: AsyncSession,
    category_slug: str,
) -> Dict[str, Any]:
    """Link to an existing category by slug.

    This is used when the AI references an existing category instead of creating a new one.
    """
    from app.models import Category
    from sqlalchemy import select

    result = {
        "success": False,
        "message": "",
        "category_id": None,
        "category_slug": None,
    }

    try:
        cat_result = await session.execute(
            select(Category).where(Category.slug == category_slug)
        )
        category = cat_result.scalar_one_or_none()

        if not category:
            result["message"] = f"Kategorie '{category_slug}' nicht gefunden"
            return result

        result["success"] = True
        result["message"] = f"Kategorie '{category.name}' verknüpft"
        result["category_id"] = str(category.id)
        result["category_slug"] = category.slug
        result["category_name"] = category.name
        return result

    except Exception as e:
        logger.error("Link existing category failed", error=str(e), exc_info=True)
        result["message"] = f"Fehler: {str(e)}"
        return result


async def execute_create_relation_type(
    session: AsyncSession,
    relation_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Create or verify a relation type between entity types.

    Args:
        relation_data: Dict with keys:
            - relation_type: Existing relation type slug
            - source_type: Source entity type slug
            - target_type: Target entity type slug

    Returns:
        Dict with result
    """
    from app.models import RelationType, EntityType
    from sqlalchemy import select

    result = {
        "success": False,
        "message": "",
    }

    relation_type_slug = relation_data.get("relation_type")
    source_type_slug = relation_data.get("source_type")
    target_type_slug = relation_data.get("target_type")

    try:
        # Find the existing relation type
        rt_result = await session.execute(
            select(RelationType).where(RelationType.slug == relation_type_slug)
        )
        relation_type = rt_result.scalar_one_or_none()

        if not relation_type:
            result["message"] = f"Relation-Typ '{relation_type_slug}' nicht gefunden"
            return result

        # Verify entity types exist
        source_result = await session.execute(
            select(EntityType).where(EntityType.slug == source_type_slug)
        )
        source_type = source_result.scalar_one_or_none()

        target_result = await session.execute(
            select(EntityType).where(EntityType.slug == target_type_slug)
        )
        target_type = target_result.scalar_one_or_none()

        if not source_type:
            result["message"] = f"Quell-Entity-Typ '{source_type_slug}' nicht gefunden"
            return result

        if not target_type:
            result["message"] = f"Ziel-Entity-Typ '{target_type_slug}' nicht gefunden"
            return result

        result["success"] = True
        result["message"] = f"Relation '{relation_type.name}' ({source_type.name} → {target_type.name}) verifiziert"
        result["relation_type_slug"] = relation_type_slug
        result["source_type_slug"] = source_type_slug
        result["target_type_slug"] = target_type_slug
        return result

    except Exception as e:
        logger.error("Create relation type failed", error=str(e), exc_info=True)
        result["message"] = f"Fehler: {str(e)}"
        return result


async def execute_add_history_point(
    session: AsyncSession,
    history_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Add a data point to a history-type facet.

    Args:
        session: Database session
        history_data: Dict containing:
            - entity_id or entity_name: Target entity
            - facet_type: Facet type slug (must be value_type=history)
            - value: Numeric value
            - recorded_at: Timestamp (optional, defaults to now)
            - track_key: Track identifier (optional, defaults to "default")
            - note: Optional note for the data point

    Returns:
        Dict with result
    """
    from datetime import datetime
    from app.models import Entity, FacetType
    from services.facet_history_service import FacetHistoryService
    from sqlalchemy import select

    entity_id = history_data.get("entity_id")
    entity_name = history_data.get("entity_name")
    facet_type_slug = history_data.get("facet_type")
    value = history_data.get("value")
    recorded_at = history_data.get("recorded_at")
    track_key = history_data.get("track_key", "default")
    note = history_data.get("note")

    result = {
        "success": False,
        "message": "",
        "data_point_id": None,
    }

    # Validate required fields
    if value is None:
        result["message"] = "Wert (value) erforderlich"
        return result

    if not facet_type_slug:
        result["message"] = "Facet-Typ erforderlich"
        return result

    # Find entity
    entity = None
    if entity_id:
        entity = await session.get(Entity, UUID(str(entity_id)))
    elif entity_name:
        entity = await find_entity_by_name(session, entity_name)

    if not entity:
        result["message"] = f"Entity nicht gefunden: {entity_name or entity_id}"
        return result

    # Find FacetType
    ft_result = await session.execute(
        select(FacetType).where(FacetType.slug == facet_type_slug)
    )
    facet_type = ft_result.scalar_one_or_none()

    if not facet_type:
        result["message"] = f"Facet-Typ '{facet_type_slug}' nicht gefunden"
        return result

    if facet_type.value_type.value != "history":
        result["message"] = f"Facet-Typ '{facet_type_slug}' ist kein History-Typ (aktuell: {facet_type.value_type.value})"
        return result

    # Parse recorded_at if provided, otherwise use current time
    if recorded_at:
        if isinstance(recorded_at, str):
            try:
                recorded_at = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
            except ValueError:
                result["message"] = f"Ungültiges Datumsformat: {recorded_at}"
                return result
    else:
        recorded_at = datetime.utcnow()

    # Build annotations
    annotations = {}
    if note:
        annotations["note"] = note

    try:
        # Add the data point using the service
        service = FacetHistoryService(session)
        data_point = await service.add_data_point(
            entity_id=entity.id,
            facet_type_id=facet_type.id,
            value=float(value),
            recorded_at=recorded_at,
            track_key=track_key,
            annotations=annotations,
            source_type="MANUAL",
        )

        logger.info(
            "History data point added via Smart Query",
            entity_id=str(entity.id),
            entity_name=entity.name,
            facet_type=facet_type_slug,
            value=value,
            recorded_at=str(recorded_at),
        )

        return {
            "success": True,
            "message": f"Datenpunkt für '{entity.name}' hinzugefügt: {value} am {recorded_at.strftime('%d.%m.%Y')}",
            "data_point_id": str(data_point.id),
            "entity_id": str(entity.id),
            "facet_type": facet_type_slug,
            "value": value,
            "recorded_at": recorded_at.isoformat(),
        }

    except Exception as e:
        logger.error("Add history point failed", error=str(e), exc_info=True)
        result["message"] = f"Fehler: {str(e)}"
        return result
