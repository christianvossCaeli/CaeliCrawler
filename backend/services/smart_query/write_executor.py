"""Write command execution for Smart Query Service."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .entity_operations import (
    create_entity_type_from_command,
    create_entity_from_command,
    create_facet_from_command,
    create_relation_from_command,
    find_entity_by_name,
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

    entity_type_slug = query_filter.get("entity_type", "municipality")
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
