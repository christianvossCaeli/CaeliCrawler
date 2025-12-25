"""Facet-related commands for Smart Query."""

from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FacetType, FacetValue, Entity
from .base import BaseCommand, CommandResult
from .registry import default_registry

logger = structlog.get_logger()


@default_registry.register("create_facet")
class CreateFacetCommand(BaseCommand):
    """Command to create a new facet value."""

    async def validate(self) -> Optional[str]:
        """Validate facet creation data."""
        facet_data = self.data.get("facet_data", {})

        if not facet_data.get("facet_type"):
            return "Facet-Typ erforderlich"

        if not facet_data.get("entity_id") and not facet_data.get("entity_name"):
            return "Entity-ID oder Entity-Name erforderlich"

        return None

    async def execute(self) -> CommandResult:
        """Create the facet value."""
        from services.smart_query.entity_operations import create_facet_from_command

        facet_data = self.data.get("facet_data", {})

        facet, message = await create_facet_from_command(self.session, facet_data)

        if facet:
            return CommandResult.success_result(
                message=message,
                created_items=[{
                    "type": "facet_value",
                    "id": str(facet.id),
                    "facet_type": facet_data.get("facet_type"),
                }],
            )
        else:
            return CommandResult.failure(message=message)


@default_registry.register("create_facet_type")
class CreateFacetTypeCommand(BaseCommand):
    """Command to create a new facet type."""

    async def validate(self) -> Optional[str]:
        """Validate facet type data."""
        facet_type_data = self.data.get("facet_type_data", {})

        if not facet_type_data.get("name"):
            return "Name für Facet-Typ erforderlich"

        return None

    async def execute(self) -> CommandResult:
        """Create the facet type."""
        from services.smart_query.utils import generate_slug
        from app.utils.similarity import find_similar_facet_types

        facet_type_data = self.data.get("facet_type_data", {})
        name = facet_type_data.get("name")

        # Use provided slug or generate from name
        slug = facet_type_data.get("slug")
        if not slug:
            slug = generate_slug(name)

        # Check if name or slug already exists (exact match)
        existing = await self.session.execute(
            select(FacetType).where(
                or_(FacetType.slug == slug, FacetType.name == name)
            )
        )
        exact_match = existing.scalar_one_or_none()
        if exact_match:
            return CommandResult.success_result(
                message=f"Facet-Typ '{exact_match.name}' existiert bereits",
                created_items=[{
                    "type": "facet_type",
                    "id": str(exact_match.id),
                    "name": exact_match.name,
                    "slug": exact_match.slug,
                    "existing": True,
                }],
                facet_type_id=str(exact_match.id),
                facet_type_name=exact_match.name,
                facet_type_slug=exact_match.slug,
            )

        # Check for semantically similar types
        similar_types = await find_similar_facet_types(self.session, name, threshold=0.7)
        if similar_types:
            best_match, score, reason = similar_types[0]
            logger.info(
                "Found similar FacetType instead of creating duplicate",
                requested_name=name,
                matched_name=best_match.name,
                similarity_score=score,
                reason=reason,
            )
            return CommandResult.success_result(
                message=f"Ähnlicher Facet-Typ '{best_match.name}' gefunden ({reason})",
                created_items=[{
                    "type": "facet_type",
                    "id": str(best_match.id),
                    "name": best_match.name,
                    "slug": best_match.slug,
                    "existing": True,
                    "similarity_reason": reason,
                }],
                facet_type_id=str(best_match.id),
                facet_type_name=best_match.name,
                facet_type_slug=best_match.slug,
            )

        # Determine value_type
        value_type = facet_type_data.get("value_type") or "structured"

        # Special handling for HISTORY value type
        is_time_based = facet_type_data.get("is_time_based", False)
        time_field_path = facet_type_data.get("time_field_path")
        deduplication_fields = facet_type_data.get("deduplication_fields")

        if value_type == "history":
            # History facets are always time-based
            is_time_based = True
            time_field_path = time_field_path or "recorded_at"
            # Disable deduplication for history - each data point is unique
            deduplication_fields = None

        # Create FacetType with all supported fields
        facet_type = FacetType(
            name=name,
            name_plural=facet_type_data.get("name_plural") or (f"{name}s" if not name.endswith("s") else name),
            slug=slug,
            description=facet_type_data.get("description") or f"Facet-Typ: {name}",
            icon=facet_type_data.get("icon") or ("mdi-chart-line" if value_type == "history" else "mdi-tag"),
            color=facet_type_data.get("color") or "#2196F3",
            value_type=value_type,
            value_schema=facet_type_data.get("value_schema"),
            applicable_entity_type_slugs=facet_type_data.get("applicable_entity_type_slugs") or [],
            display_order=facet_type_data.get("display_order"),
            aggregation_method=facet_type_data.get("aggregation_method"),
            deduplication_fields=deduplication_fields,
            is_time_based=is_time_based,
            time_field_path=time_field_path,
            default_time_filter=facet_type_data.get("default_time_filter"),
            ai_extraction_enabled=facet_type_data.get("ai_extraction_enabled", True),
            ai_extraction_prompt=facet_type_data.get("ai_extraction_prompt") or f"Extrahiere {name} aus dem Dokument.",
            is_active=facet_type_data.get("is_active", True),
            is_system=False,
        )

        self.session.add(facet_type)
        await self.session.flush()

        return CommandResult.success_result(
            message=f"Facet-Typ '{name}' erstellt",
            created_items=[{
                "type": "facet_type",
                "id": str(facet_type.id),
                "name": facet_type.name,
                "slug": facet_type.slug,
            }],
            facet_type_id=str(facet_type.id),
            facet_type_name=facet_type.name,
            facet_type_slug=facet_type.slug,
        )


@default_registry.register("delete_facet")
class DeleteFacetCommand(BaseCommand):
    """Command to delete facet(s) from an entity."""

    async def validate(self) -> Optional[str]:
        """Validate delete data."""
        delete_data = self.data.get("delete_facet_data", {})

        has_entity = delete_data.get("entity_id") or delete_data.get("entity_name")
        has_facet_spec = delete_data.get("facet_id") or delete_data.get("facet_type")

        if not has_entity:
            return "Entity-ID oder Entity-Name erforderlich"

        if not has_facet_spec:
            return "Facet-ID oder Facet-Typ erforderlich"

        return None

    async def execute(self) -> CommandResult:
        """Delete the facet(s)."""
        from services.smart_query.entity_operations import find_entity_by_name

        delete_data = self.data.get("delete_facet_data", {})
        entity_id = delete_data.get("entity_id")
        entity_name = delete_data.get("entity_name")
        facet_type_slug = delete_data.get("facet_type")
        facet_id = delete_data.get("facet_id")
        facet_description = delete_data.get("facet_description")
        delete_all_of_type = delete_data.get("delete_all_of_type", False)

        # Find entity
        entity = None
        if entity_id:
            entity = await self.session.get(Entity, UUID(str(entity_id)))
        elif entity_name:
            entity = await find_entity_by_name(self.session, entity_name)

        if not entity:
            return CommandResult.failure(
                message=f"Entity nicht gefunden: {entity_name or entity_id}"
            )

        deleted_items = []

        # Case 1: Delete specific facet by ID
        if facet_id:
            facet = await self.session.get(FacetValue, UUID(str(facet_id)))
            if facet and facet.entity_id == entity.id:
                await self.session.delete(facet)
                deleted_items.append({
                    "type": "facet",
                    "id": str(facet.id),
                    "facet_type": facet_type_slug,
                    "text": facet.text_representation,
                })
            else:
                return CommandResult.failure(
                    message="Facet nicht gefunden oder gehört nicht zur angegebenen Entity"
                )

        # Case 2: Delete by facet type
        elif facet_type_slug:
            # Find FacetType
            ft_result = await self.session.execute(
                select(FacetType).where(FacetType.slug == facet_type_slug)
            )
            facet_type = ft_result.scalar_one_or_none()
            if not facet_type:
                return CommandResult.failure(
                    message=f"Facet-Typ '{facet_type_slug}' nicht gefunden"
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

            result = await self.session.execute(query)
            facets = result.scalars().all()

            if not facets:
                return CommandResult.failure(
                    message=f"Keine passenden Facets vom Typ '{facet_type_slug}' gefunden"
                )

            # Delete all matching or just first if not delete_all_of_type
            facets_to_delete = facets if delete_all_of_type else facets[:1]

            for facet in facets_to_delete:
                await self.session.delete(facet)
                deleted_items.append({
                    "type": "facet",
                    "id": str(facet.id),
                    "facet_type": facet_type_slug,
                    "text": facet.text_representation[:100] if facet.text_representation else None,
                })

        await self.session.flush()

        logger.info(
            "Facets deleted via Command",
            entity_id=str(entity.id),
            entity_name=entity.name,
            deleted_count=len(deleted_items),
        )

        return CommandResult.success_result(
            message=f"{len(deleted_items)} Facet(s) von '{entity.name}' gelöscht",
            deleted_items=deleted_items,
        )


@default_registry.register("assign_facet_type")
class AssignFacetTypeCommand(BaseCommand):
    """Command to assign a facet type to entity types."""

    async def validate(self) -> Optional[str]:
        """Validate assignment data."""
        assign_data = self.data.get("assign_facet_type_data", {})

        if not assign_data.get("facet_type_slug"):
            return "Facet-Typ-Slug erforderlich"

        if not assign_data.get("target_entity_type_slugs"):
            return "Mindestens ein Entity-Typ-Slug erforderlich"

        return None

    async def execute(self) -> CommandResult:
        """Assign the facet type."""
        assign_data = self.data.get("assign_facet_type_data", {})
        facet_type_slug = assign_data.get("facet_type_slug")
        target_slugs = assign_data.get("target_entity_type_slugs", [])

        # Find FacetType
        result = await self.session.execute(
            select(FacetType).where(FacetType.slug == facet_type_slug)
        )
        facet_type = result.scalar_one_or_none()

        if not facet_type:
            return CommandResult.failure(
                message=f"Facet-Typ '{facet_type_slug}' nicht gefunden"
            )

        # Update applicable_entity_type_slugs
        existing_slugs = facet_type.applicable_entity_type_slugs or []
        new_slugs = list(set(existing_slugs + target_slugs))
        facet_type.applicable_entity_type_slugs = new_slugs

        await self.session.flush()

        return CommandResult.success_result(
            message=f"Facet-Typ '{facet_type.name}' zugewiesen an: {', '.join(target_slugs)}",
        )


@default_registry.register("add_history_point")
class AddHistoryDataPointCommand(BaseCommand):
    """Command to add a data point to a history-type facet."""

    async def validate(self) -> Optional[str]:
        """Validate history data point data."""
        point_data = self.data.get("history_point_data", {})

        if not point_data.get("entity_id") and not point_data.get("entity_name"):
            return "Entity-ID oder Entity-Name erforderlich"

        if not point_data.get("facet_type"):
            return "Facet-Typ erforderlich"

        if point_data.get("value") is None:
            return "Wert (value) erforderlich"

        return None

    async def execute(self) -> CommandResult:
        """Add the history data point."""
        from datetime import datetime
        from services.smart_query.entity_operations import find_entity_by_name
        from services.facet_history_service import FacetHistoryService

        point_data = self.data.get("history_point_data", {})
        entity_id = point_data.get("entity_id")
        entity_name = point_data.get("entity_name")
        facet_type_slug = point_data.get("facet_type")
        value = point_data.get("value")
        recorded_at = point_data.get("recorded_at")
        track_key = point_data.get("track_key", "default")
        note = point_data.get("note")

        # Find entity
        entity = None
        if entity_id:
            entity = await self.session.get(Entity, UUID(str(entity_id)))
        elif entity_name:
            entity = await find_entity_by_name(self.session, entity_name)

        if not entity:
            return CommandResult.failure(
                message=f"Entity nicht gefunden: {entity_name or entity_id}"
            )

        # Find FacetType
        result = await self.session.execute(
            select(FacetType).where(FacetType.slug == facet_type_slug)
        )
        facet_type = result.scalar_one_or_none()

        if not facet_type:
            return CommandResult.failure(
                message=f"Facet-Typ '{facet_type_slug}' nicht gefunden"
            )

        if facet_type.value_type.value != "history":
            return CommandResult.failure(
                message=f"Facet-Typ '{facet_type_slug}' ist kein History-Typ (aktuell: {facet_type.value_type.value})"
            )

        # Parse recorded_at if provided, otherwise use current time
        if recorded_at:
            if isinstance(recorded_at, str):
                try:
                    recorded_at = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
                except ValueError:
                    return CommandResult.failure(
                        message=f"Ungültiges Datumsformat: {recorded_at}"
                    )
        else:
            recorded_at = datetime.utcnow()

        # Build annotations
        annotations = {}
        if note:
            annotations["note"] = note

        # Add the data point using the service
        service = FacetHistoryService(self.session)
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
            "History data point added via Command",
            entity_id=str(entity.id),
            entity_name=entity.name,
            facet_type=facet_type_slug,
            value=value,
            recorded_at=str(recorded_at),
        )

        return CommandResult.success_result(
            message=f"Datenpunkt für '{entity.name}' hinzugefügt: {value} am {recorded_at.strftime('%d.%m.%Y')}",
            created_items=[{
                "type": "history_data_point",
                "id": str(data_point.id),
                "entity_id": str(entity.id),
                "facet_type": facet_type_slug,
                "value": value,
                "recorded_at": recorded_at.isoformat(),
            }],
        )
