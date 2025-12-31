"""Batch operations for Smart Query Service.

Operations:
- batch_operation: Execute batch operations on multiple entities
- batch_delete: Batch delete entities or facets
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import OperationResult, WriteOperation, register_operation

logger = structlog.get_logger()


@register_operation("batch_operation")
class BatchOperation(WriteOperation):
    """Execute batch operations on multiple entities.

    Supports: add_facet, update_field, add_relation, remove_facet
    """

    def validate(self, command: dict[str, Any]) -> str | None:
        batch_data = command.get("batch_data", {})
        if not batch_data.get("action_type"):
            return "action_type erforderlich"
        return None

    async def execute(
        self,
        session: AsyncSession,
        command: dict[str, Any],
        user_id: UUID | None = None,
    ) -> OperationResult:
        from app.models import Entity, EntityType, FacetType, FacetValue
        from app.models.facet_value import FacetValueSourceType

        batch_data = command.get("batch_data", {})
        dry_run = command.get("dry_run", True)

        action_type = batch_data.get("action_type")
        target_filter = batch_data.get("target_filter", {})
        action_data = batch_data.get("action_data", {})

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
                return OperationResult(
                    success=False,
                    message=f"Entity-Typ '{entity_type_slug}' nicht gefunden",
                )

        # Filter by location
        location_filter = target_filter.get("location_filter")
        if location_filter:
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
        result = await session.execute(query.limit(1000))
        entities = result.scalars().all()

        if not entities:
            return OperationResult(
                success=True,
                message="Keine passenden Entities gefunden",
                data={"affected_count": 0, "preview": [], "dry_run": dry_run},
            )

        # Build preview
        preview = [
            {
                "entity_id": str(e.id),
                "entity_name": e.name,
                "entity_type": entity_type_slug or "unknown",
            }
            for e in entities[:20]
        ]

        if dry_run:
            return OperationResult(
                success=True,
                message=f"{len(entities)} Entities würden bearbeitet werden (Vorschau)",
                data={"affected_count": len(entities), "preview": preview, "dry_run": True},
            )

        # Execute the actual operation
        affected = 0

        if action_type == "add_facet":
            facet_type_slug = action_data.get("facet_type")
            facet_value = action_data.get("facet_value", {})

            ft_result = await session.execute(
                select(FacetType).where(FacetType.slug == facet_type_slug)
            )
            facet_type = ft_result.scalar_one_or_none()
            if not facet_type:
                return OperationResult(
                    success=False,
                    message=f"Facet-Typ '{facet_type_slug}' nicht gefunden",
                )

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
                return OperationResult(success=False, message="field_name erforderlich")

            for entity in entities:
                if entity.core_attributes is None:
                    entity.core_attributes = {}
                entity.core_attributes[field_name] = field_value
                affected += 1

        elif action_type == "remove_facet":
            facet_type_slug = action_data.get("facet_type")

            ft_result = await session.execute(
                select(FacetType).where(FacetType.slug == facet_type_slug)
            )
            facet_type = ft_result.scalar_one_or_none()
            if not facet_type:
                return OperationResult(
                    success=False,
                    message=f"Facet-Typ '{facet_type_slug}' nicht gefunden",
                )

            for entity in entities:
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
            return OperationResult(
                success=False,
                message=f"Unbekannter action_type: {action_type}",
            )

        await session.flush()

        return OperationResult(
            success=True,
            message=f"Batch-Operation ausgeführt: {affected} Änderungen",
            data={"affected_count": affected, "preview": preview, "dry_run": False},
        )


@register_operation("batch_delete")
class BatchDeleteOperation(WriteOperation):
    """Batch delete entities or facets."""

    async def execute(
        self,
        session: AsyncSession,
        command: dict[str, Any],
        user_id: UUID | None = None,
    ) -> OperationResult:
        from app.models import Entity, EntityType, FacetType, FacetValue

        delete_data = command.get("delete_data", {})
        dry_run = command.get("dry_run", True)

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
                return OperationResult(
                    success=False,
                    message=f"Entity-Typ '{entity_type_slug}' nicht gefunden",
                )

        # Filter by location
        if location_filter:
            from ..geographic_utils import resolve_geographic_alias
            resolved_location = resolve_geographic_alias(location_filter)
            entity_query = entity_query.where(Entity.admin_level_1 == resolved_location)

        # Additional filters
        for key, value in additional_filters.items():
            if key == "is_active" and value is False:
                entity_query = entity_query.where(Entity.is_active.is_(False))
            else:
                entity_query = entity_query.where(
                    Entity.core_attributes[key].astext == str(value)
                )

        # Execute entity query
        result = await session.execute(entity_query.limit(1000))
        entities = result.scalars().all()

        if not entities:
            return OperationResult(
                success=True,
                message="Keine passenden Entities gefunden",
                data={"affected_count": 0, "preview": [], "dry_run": dry_run},
            )

        preview: list[dict[str, Any]] = []
        affected_count = 0

        if delete_type == "entities":
            for entity in entities[:20]:
                preview.append({
                    "type": "entity",
                    "id": str(entity.id),
                    "name": entity.name,
                    "entity_type": entity_type_slug or "unknown",
                })
            affected_count = len(entities)

            if dry_run:
                return OperationResult(
                    success=True,
                    message=f"{affected_count} Entities würden gelöscht werden (Vorschau)",
                    data={"affected_count": affected_count, "preview": preview, "dry_run": True},
                )

            # Execute soft-delete
            for entity in entities:
                entity.is_active = False
                if entity.core_attributes is None:
                    entity.core_attributes = {}
                entity.core_attributes["_deletion_reason"] = reason
                entity.core_attributes["_deleted_at"] = str(datetime.now(UTC).isoformat())

        elif delete_type == "facets":
            if not facet_type_slug:
                return OperationResult(
                    success=False,
                    message="facet_type erforderlich für Facet-Löschung",
                )

            ft_result = await session.execute(
                select(FacetType).where(FacetType.slug == facet_type_slug)
            )
            facet_type = ft_result.scalar_one_or_none()
            if not facet_type:
                return OperationResult(
                    success=False,
                    message=f"Facet-Typ '{facet_type_slug}' nicht gefunden",
                )

            entity_ids = [e.id for e in entities]
            facet_query = select(FacetValue).where(
                and_(
                    FacetValue.entity_id.in_(entity_ids),
                    FacetValue.facet_type_id == facet_type.id,
                    FacetValue.is_active.is_(True),
                )
            )

            if date_before:
                try:
                    date_limit = datetime.strptime(date_before, "%Y-%m-%d").replace(tzinfo=UTC)
                    facet_query = facet_query.where(FacetValue.event_date < date_limit)
                except ValueError:
                    pass

            facet_result = await session.execute(facet_query.limit(1000))
            facets = facet_result.scalars().all()

            for facet in facets[:20]:
                preview.append({
                    "type": "facet",
                    "id": str(facet.id),
                    "entity_id": str(facet.entity_id),
                    "facet_type": facet_type_slug,
                    "text": facet.text_representation[:50] if facet.text_representation else None,
                })
            affected_count = len(facets)

            if dry_run:
                return OperationResult(
                    success=True,
                    message=f"{affected_count} Facets würden gelöscht werden (Vorschau)",
                    data={"affected_count": affected_count, "preview": preview, "dry_run": True},
                )

            for facet in facets:
                await session.delete(facet)

        else:
            return OperationResult(
                success=False,
                message=f"Unbekannter delete_type: {delete_type}",
            )

        await session.flush()

        logger.info(
            "Batch delete executed via Smart Query",
            delete_type=delete_type,
            affected_count=affected_count,
            reason=reason,
        )

        return OperationResult(
            success=True,
            message=f"Batch-Löschung ausgeführt: {affected_count} {delete_type} gelöscht",
            data={"affected_count": affected_count, "preview": preview, "dry_run": False},
        )
