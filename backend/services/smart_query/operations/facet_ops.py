"""Facet operations for Smart Query Service.

Operations:
- create_facet_type: Create a new FacetType
- assign_facet_type: Assign a FacetType to EntityTypes
- delete_facet: Delete facets from an entity
- add_history_point: Add a data point to a history facet
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .base import WriteOperation, OperationResult, register_operation
from ..entity_operations import find_entity_by_name
from ..utils import generate_slug

logger = structlog.get_logger()


@register_operation("create_facet_type")
class CreateFacetTypeOperation(WriteOperation):
    """Create a new FacetType."""

    def validate(self, command: Dict[str, Any]) -> Optional[str]:
        facet_type_data = command.get("facet_type_data", {})
        if not facet_type_data.get("name"):
            return "Name für Facet-Typ erforderlich"
        return None

    async def execute(
        self,
        session: AsyncSession,
        command: Dict[str, Any],
        user_id: Optional[UUID] = None,
    ) -> OperationResult:
        from app.models import FacetType
        from app.utils.similarity import find_similar_facet_types

        facet_type_data = command.get("facet_type_data", {})
        name = facet_type_data.get("name")

        # Use provided slug or generate from name
        slug = facet_type_data.get("slug")
        if not slug:
            slug = generate_slug(name)

        # Check if name or slug already exists (exact match)
        existing = await session.execute(
            select(FacetType).where(
                or_(FacetType.slug == slug, FacetType.name == name)
            )
        )
        exact_match = existing.scalar_one_or_none()
        if exact_match:
            return OperationResult(
                success=True,
                message=f"Facet-Typ '{exact_match.name}' existiert bereits",
                created_items=[
                    {
                        "type": "facet_type",
                        "id": str(exact_match.id),
                        "name": exact_match.name,
                        "slug": exact_match.slug,
                        "existing": True,
                    }
                ],
            )

        # Check for semantically similar types
        similar_types = await find_similar_facet_types(session, name, threshold=0.7)
        if similar_types:
            best_match, score, reason = similar_types[0]
            logger.info(
                "Found similar FacetType instead of creating duplicate",
                requested_name=name,
                matched_name=best_match.name,
                similarity_score=score,
                reason=reason,
            )
            return OperationResult(
                success=True,
                message=f"Ähnlicher Facet-Typ '{best_match.name}' gefunden ({reason})",
                created_items=[
                    {
                        "type": "facet_type",
                        "id": str(best_match.id),
                        "name": best_match.name,
                        "slug": best_match.slug,
                        "existing": True,
                        "similarity_reason": reason,
                    }
                ],
            )

        # Validate applicable_entity_type_slugs
        applicable_slugs = facet_type_data.get("applicable_entity_type_slugs") or []
        if applicable_slugs:
            from app.core.validators import validate_entity_type_slugs
            _, invalid_slugs = await validate_entity_type_slugs(session, applicable_slugs)
            if invalid_slugs:
                return OperationResult(
                    success=False,
                    message=f"Ungültige Entity-Typ-Slugs: {', '.join(sorted(invalid_slugs))}",
                )

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

        # Generate embedding for semantic similarity search
        from app.utils.similarity import generate_embedding
        embedding = await generate_embedding(name)
        if embedding:
            facet_type.name_embedding = embedding

        return OperationResult(
            success=True,
            message=f"Facet-Typ '{name}' erstellt",
            created_items=[
                {
                    "type": "facet_type",
                    "id": str(facet_type.id),
                    "name": facet_type.name,
                    "slug": facet_type.slug,
                }
            ],
        )


@register_operation("assign_facet_type")
class AssignFacetTypeOperation(WriteOperation):
    """Assign a FacetType to EntityTypes."""

    def validate(self, command: Dict[str, Any]) -> Optional[str]:
        assign_data = command.get("assign_facet_type_data", {})
        if not assign_data.get("facet_type_slug"):
            return "Facet-Typ-Slug erforderlich"
        if not assign_data.get("target_entity_type_slugs"):
            return "Mindestens ein Entity-Typ-Slug erforderlich"
        return None

    async def execute(
        self,
        session: AsyncSession,
        command: Dict[str, Any],
        user_id: Optional[UUID] = None,
    ) -> OperationResult:
        from app.models import FacetType

        assign_data = command.get("assign_facet_type_data", {})
        facet_type_slug = assign_data.get("facet_type_slug")
        target_slugs = assign_data.get("target_entity_type_slugs", [])

        # Find FacetType
        result = await session.execute(
            select(FacetType).where(FacetType.slug == facet_type_slug)
        )
        facet_type = result.scalar_one_or_none()

        if not facet_type:
            return OperationResult(
                success=False,
                message=f"Facet-Typ '{facet_type_slug}' nicht gefunden",
            )

        # Update applicable_entity_type_slugs
        existing_slugs = facet_type.applicable_entity_type_slugs or []
        new_slugs = list(set(existing_slugs + target_slugs))
        facet_type.applicable_entity_type_slugs = new_slugs

        await session.flush()

        return OperationResult(
            success=True,
            message=f"Facet-Typ '{facet_type.name}' zugewiesen an: {', '.join(target_slugs)}",
        )


@register_operation("delete_facet")
class DeleteFacetOperation(WriteOperation):
    """Delete facet(s) from an entity."""

    async def execute(
        self,
        session: AsyncSession,
        command: Dict[str, Any],
        user_id: Optional[UUID] = None,
    ) -> OperationResult:
        from app.models import Entity, FacetType, FacetValue

        delete_data = command.get("delete_data", {})
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
            return OperationResult(
                success=False,
                message=f"Entity nicht gefunden: {entity_name or entity_id}",
            )

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
                return OperationResult(
                    success=False,
                    message="Facet nicht gefunden oder gehört nicht zur angegebenen Entity",
                )

        # Case 2: Delete by facet type
        elif facet_type_slug:
            # Find FacetType
            ft_result = await session.execute(
                select(FacetType).where(FacetType.slug == facet_type_slug)
            )
            facet_type = ft_result.scalar_one_or_none()
            if not facet_type:
                return OperationResult(
                    success=False,
                    message=f"Facet-Typ '{facet_type_slug}' nicht gefunden",
                )

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
                return OperationResult(
                    success=False,
                    message=f"Keine passenden Facets vom Typ '{facet_type_slug}' gefunden",
                )

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
            return OperationResult(
                success=False,
                message="Facet-ID oder Facet-Typ erforderlich",
            )

        await session.flush()

        logger.info(
            "Facets deleted via Smart Query",
            entity_id=str(entity.id),
            entity_name=entity.name,
            deleted_count=len(deleted_items),
        )

        return OperationResult(
            success=True,
            message=f"{len(deleted_items)} Facet(s) von '{entity.name}' gelöscht",
            created_items=deleted_items,
        )


@register_operation("add_history_point")
class AddHistoryPointOperation(WriteOperation):
    """Add a data point to a history-type facet."""

    def validate(self, command: Dict[str, Any]) -> Optional[str]:
        history_data = command.get("history_point_data", {})
        if history_data.get("value") is None:
            return "Wert (value) erforderlich"
        if not history_data.get("facet_type"):
            return "Facet-Typ erforderlich"
        if not history_data.get("entity_id") and not history_data.get("entity_name"):
            return "Entity-ID oder Entity-Name erforderlich"
        return None

    async def execute(
        self,
        session: AsyncSession,
        command: Dict[str, Any],
        user_id: Optional[UUID] = None,
    ) -> OperationResult:
        from app.models import Entity, FacetType
        from services.facet_history_service import FacetHistoryService

        history_data = command.get("history_point_data", {})
        entity_id = history_data.get("entity_id")
        entity_name = history_data.get("entity_name")
        facet_type_slug = history_data.get("facet_type")
        value = history_data.get("value")
        recorded_at = history_data.get("recorded_at")
        track_key = history_data.get("track_key", "default")
        note = history_data.get("note")

        # Find entity
        entity = None
        if entity_id:
            entity = await session.get(Entity, UUID(str(entity_id)))
        elif entity_name:
            entity = await find_entity_by_name(session, entity_name)

        if not entity:
            return OperationResult(
                success=False,
                message=f"Entity nicht gefunden: {entity_name or entity_id}",
            )

        # Find FacetType
        ft_result = await session.execute(
            select(FacetType).where(FacetType.slug == facet_type_slug)
        )
        facet_type = ft_result.scalar_one_or_none()

        if not facet_type:
            return OperationResult(
                success=False,
                message=f"Facet-Typ '{facet_type_slug}' nicht gefunden",
            )

        if facet_type.value_type.value != "history":
            return OperationResult(
                success=False,
                message=f"Facet-Typ '{facet_type_slug}' ist kein History-Typ (aktuell: {facet_type.value_type.value})",
            )

        # Parse recorded_at if provided
        if recorded_at:
            if isinstance(recorded_at, str):
                try:
                    recorded_at = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
                except ValueError:
                    return OperationResult(
                        success=False,
                        message=f"Ungültiges Datumsformat: {recorded_at}",
                    )
        else:
            recorded_at = datetime.utcnow()

        # Build annotations
        annotations = {}
        if note:
            annotations["note"] = note

        try:
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
            )

            return OperationResult(
                success=True,
                message=f"Datenpunkt für '{entity.name}' hinzugefügt: {value} am {recorded_at.strftime('%d.%m.%Y')}",
                created_items=[
                    {
                        "type": "history_point",
                        "id": str(data_point.id),
                        "entity_id": str(entity.id),
                        "facet_type": facet_type_slug,
                        "value": value,
                    }
                ],
            )

        except Exception as e:
            logger.error("Add history point failed", error=str(e), exc_info=True)
            return OperationResult(
                success=False,
                message=f"Fehler: {str(e)}",
            )
