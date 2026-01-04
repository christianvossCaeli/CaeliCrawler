"""Export and history operations for Smart Query Service.

Operations:
- export: Export entities and facets (CSV, JSON, Excel)
- undo: Undo the last operation
- get_history: Get operation history
"""

import csv
import io
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..entity_operations import find_entity_by_name
from .base import OperationResult, WriteOperation, register_operation

logger = structlog.get_logger()


@register_operation("export")
class ExportOperation(WriteOperation):
    """Export entities and facets to various formats."""

    async def execute(
        self,
        session: AsyncSession,
        command: dict[str, Any],
        user_id: UUID | None = None,
    ) -> OperationResult:
        from app.models import Entity, EntityType, FacetType, FacetValue

        export_data = command.get("export_data", {})
        export_format = export_data.get("format", "json").lower()
        query_filter = export_data.get("query_filter", {})
        include_facets = export_data.get("include_facets", True)
        filename = export_data.get("filename", "smart_query_export")

        entity_type_slug = query_filter.get("entity_type", "territorial_entity")
        location_filter = query_filter.get("location_filter")
        facet_type_slugs = query_filter.get("facet_types", [])
        position_keywords = query_filter.get("position_keywords", [])
        country = query_filter.get("country")

        # Build entity query
        entity_query = select(Entity).where(Entity.is_active.is_(True))

        # Filter by entity type
        et_result = await session.execute(select(EntityType).where(EntityType.slug == entity_type_slug))
        entity_type = et_result.scalar_one_or_none()
        if entity_type:
            entity_query = entity_query.where(Entity.entity_type_id == entity_type.id)
        else:
            return OperationResult(
                success=False,
                message=f"Entity-Typ '{entity_type_slug}' nicht gefunden",
            )

        # Filter by location
        if location_filter:
            from ..geographic_utils import resolve_geographic_alias

            resolved_location = resolve_geographic_alias(location_filter)
            entity_query = entity_query.where(Entity.admin_level_1 == resolved_location)

        # Filter by country
        if country:
            entity_query = entity_query.where(Entity.country == country)

        # Filter by position keywords (for person entities)
        if position_keywords and entity_type_slug == "person":
            from sqlalchemy import or_

            position_conditions = []
            for keyword in position_keywords:
                position_conditions.append(Entity.core_attributes["position"].astext.ilike(f"%{keyword}%"))
            if position_conditions:
                entity_query = entity_query.where(or_(*position_conditions))

        # Execute query
        result = await session.execute(entity_query.limit(5000))
        entities = result.scalars().all()

        if not entities:
            return OperationResult(
                success=True,
                message="Keine Entities für Export gefunden",
                data={"format": export_format, "record_count": 0, "data": []},
            )

        # Load facet types for filtering
        facet_type_map = {}
        if facet_type_slugs and include_facets:
            for ft_slug in facet_type_slugs:
                ft_result = await session.execute(select(FacetType).where(FacetType.slug == ft_slug))
                ft = ft_result.scalar_one_or_none()
                if ft:
                    facet_type_map[ft_slug] = ft

        # Bulk load facets if requested
        entity_ids = [e.id for e in entities]
        facets_by_entity: dict[UUID, list[dict]] = {eid: [] for eid in entity_ids}

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
                facets_by_entity[fv.entity_id].append(
                    {
                        "type": str(fv.facet_type_id),
                        "value": fv.value,
                        "text": fv.text_representation,
                        "date": fv.event_date.isoformat() if fv.event_date else None,
                    }
                )

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
            return OperationResult(
                success=True,
                message=f"Export erstellt: {len(export_records)} {entity_type.name_plural or entity_type.name}",
                data={
                    "format": "json",
                    "record_count": len(export_records),
                    "data": export_records,
                    "filename": f"{filename}.json",
                },
            )

        elif export_format == "csv":
            output = io.StringIO()
            if export_records:
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

            return OperationResult(
                success=True,
                message=f"CSV-Export erstellt: {len(export_records)} Datensätze",
                data={
                    "format": "csv",
                    "record_count": len(export_records),
                    "data": csv_content,
                    "filename": f"{filename}.csv",
                    "content_type": "text/csv",
                },
            )

        elif export_format == "excel":
            return OperationResult(
                success=True,
                message=f"Excel-Export vorbereitet: {len(export_records)} Datensätze",
                data={
                    "format": "excel",
                    "record_count": len(export_records),
                    "data": export_records[:100],
                    "filename": f"{filename}.xlsx",
                    "note": "Für vollständigen Excel-Export, nutze den dedizierten Export-Endpoint",
                },
            )

        else:
            return OperationResult(
                success=False,
                message=f"Unbekanntes Export-Format: {export_format}. Unterstützt: csv, json, excel",
            )


@register_operation("undo")
class UndoOperation(WriteOperation):
    """Undo the last operation using ChangeTracker."""

    async def execute(
        self,
        session: AsyncSession,
        command: dict[str, Any],
        user_id: UUID | None = None,
    ) -> OperationResult:
        from services.change_tracker import ChangeTracker

        undo_data = command.get("undo_data", {})
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
                    return OperationResult(
                        success=False,
                        message=f"Entity '{entity_name}' nicht gefunden",
                    )
            else:
                return OperationResult(
                    success=False,
                    message="Für Facet-UNDO ist eine Facet-ID erforderlich",
                )

        if not target_id:
            return OperationResult(
                success=False,
                message="Entity-ID oder Entity-Name erforderlich",
            )

        tracker = ChangeTracker(session)
        success, message, restored_values = await tracker.undo_last_change(entity_type, target_id)

        return OperationResult(
            success=success,
            message=message,
            data={"restored_values": restored_values},
        )


@register_operation("get_history")
class GetHistoryOperation(WriteOperation):
    """Get change history for an entity."""

    async def execute(
        self,
        session: AsyncSession,
        command: dict[str, Any],
        user_id: UUID | None = None,
    ) -> OperationResult:
        from services.change_tracker import ChangeTracker

        history_data = command.get("history_data", {})
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
                    return OperationResult(
                        success=False,
                        message=f"Entity '{entity_name}' nicht gefunden",
                        data={"history": []},
                    )
            else:
                return OperationResult(
                    success=False,
                    message="Für Facet-Historie ist eine Facet-ID erforderlich",
                    data={"history": []},
                )

        if not target_id:
            return OperationResult(
                success=False,
                message="Entity-ID oder Entity-Name erforderlich",
                data={"history": []},
            )

        tracker = ChangeTracker(session)
        history = await tracker.get_change_history(entity_type, target_id, limit=limit)

        if not history:
            return OperationResult(
                success=True,
                message=f"Keine Änderungshistorie für '{entity_display_name}' gefunden",
                data={"history": []},
            )

        return OperationResult(
            success=True,
            message=f"Änderungshistorie für '{entity_display_name}': {len(history)} Einträge",
            data={"history": history},
        )
