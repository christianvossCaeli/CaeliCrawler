"""Change tracking service for UNDO functionality in Smart Query.

Uses the existing EntityVersion model for diff-based tracking.
Provides UNDO capability for entity and facet changes made via Smart Query.
"""

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Entity, FacetValue
from app.models.entity_version import EntityVersion

logger = structlog.get_logger()

# Snapshot interval - store full snapshot every N versions
SNAPSHOT_INTERVAL = 10


class ChangeTracker:
    """Service for tracking and undoing changes made via Smart Query."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_entity_change(
        self,
        entity: Entity,
        changes: dict[str, Any],
        user_id: UUID | None = None,
        user_email: str | None = None,
        reason: str | None = None,
    ) -> EntityVersion:
        """Record a change to an entity.

        Args:
            entity: The entity that was changed
            changes: Dict of {field: {"old": old_value, "new": new_value}}
            user_id: Optional user who made the change
            user_email: Optional user email (denormalized)
            reason: Optional reason for the change

        Returns:
            The created EntityVersion record
        """
        # Get the latest version number
        latest_version = await self._get_latest_version("Entity", entity.id)
        new_version_number = (latest_version.version_number + 1) if latest_version else 1

        # Determine if we need a snapshot
        snapshot = None
        if new_version_number % SNAPSHOT_INTERVAL == 0:
            snapshot = self._create_entity_snapshot(entity)

        # Create version record
        version = EntityVersion(
            entity_type="Entity",
            entity_id=entity.id,
            version_number=new_version_number,
            diff=changes,
            snapshot=snapshot,
            user_id=user_id,
            user_email=user_email,
            change_reason=reason or "Smart Query Änderung",
        )

        self.session.add(version)
        await self.session.flush()

        logger.info(
            "Entity change recorded",
            entity_id=str(entity.id),
            entity_name=entity.name,
            version=new_version_number,
            changes=list(changes.keys()),
        )

        return version

    async def record_facet_change(
        self,
        facet: FacetValue,
        change_type: str,  # "create", "update", "delete"
        old_values: dict[str, Any] | None = None,
        user_id: UUID | None = None,
        user_email: str | None = None,
        reason: str | None = None,
    ) -> EntityVersion:
        """Record a change to a facet.

        Args:
            facet: The facet that was changed
            change_type: Type of change (create, update, delete)
            old_values: Previous values (for update/delete)
            user_id: Optional user who made the change
            user_email: Optional user email
            reason: Optional reason for the change

        Returns:
            The created EntityVersion record
        """
        # Get the latest version number for this facet
        latest_version = await self._get_latest_version("FacetValue", facet.id)
        new_version_number = (latest_version.version_number + 1) if latest_version else 1

        # Build diff based on change type
        if change_type == "create":
            diff = {
                "_operation": "create",
                "entity_id": str(facet.entity_id),
                "facet_type_id": str(facet.facet_type_id),
                "value": facet.value,
                "text_representation": facet.text_representation,
            }
        elif change_type == "delete":
            diff = {
                "_operation": "delete",
                "entity_id": str(facet.entity_id),
                "facet_type_id": str(facet.facet_type_id),
                "value": old_values.get("value") if old_values else facet.value,
                "text_representation": old_values.get("text_representation")
                if old_values
                else facet.text_representation,
            }
        else:  # update
            diff = {
                "_operation": "update",
                **{k: {"old": old_values.get(k), "new": getattr(facet, k, None)} for k in (old_values or {})},
            }

        # Create version record
        version = EntityVersion(
            entity_type="FacetValue",
            entity_id=facet.id,
            version_number=new_version_number,
            diff=diff,
            snapshot=None,  # Facets are small, no snapshots needed
            user_id=user_id,
            user_email=user_email,
            change_reason=reason or f"Smart Query {change_type}",
        )

        self.session.add(version)
        await self.session.flush()

        logger.info(
            "Facet change recorded",
            facet_id=str(facet.id),
            change_type=change_type,
            version=new_version_number,
        )

        return version

    async def undo_last_change(
        self,
        entity_type: str,
        entity_id: UUID,
    ) -> tuple[bool, str, dict[str, Any] | None]:
        """Undo the last change to an entity or facet.

        Args:
            entity_type: "Entity" or "FacetValue"
            entity_id: ID of the entity/facet

        Returns:
            Tuple of (success, message, restored_values)
        """
        # Get the latest version
        latest_version = await self._get_latest_version(entity_type, entity_id)

        if not latest_version:
            return False, "Keine Änderungshistorie gefunden", None

        diff = latest_version.diff

        if entity_type == "Entity":
            return await self._undo_entity_change(entity_id, diff, latest_version)
        elif entity_type == "FacetValue":
            return await self._undo_facet_change(entity_id, diff, latest_version)
        else:
            return False, f"Unbekannter entity_type: {entity_type}", None

    async def _undo_entity_change(
        self,
        entity_id: UUID,
        diff: dict[str, Any],
        version: EntityVersion,
    ) -> tuple[bool, str, dict[str, Any] | None]:
        """Undo an entity change by restoring old values."""
        entity = await self.session.get(Entity, entity_id)

        if not entity:
            return False, "Entity nicht gefunden", None

        restored = {}

        for field, change in diff.items():
            if field.startswith("_"):
                continue  # Skip metadata fields

            if isinstance(change, dict) and "old" in change:
                old_value = change["old"]

                if field == "name":
                    entity.name = old_value
                elif field == "is_active":
                    entity.is_active = old_value
                elif field == "core_attributes":
                    entity.core_attributes = old_value
                elif field == "external_id":
                    entity.external_id = old_value

                restored[field] = old_value

        # Delete the version record (or mark as undone)
        await self.session.delete(version)
        await self.session.flush()

        logger.info(
            "Entity change undone",
            entity_id=str(entity_id),
            entity_name=entity.name,
            restored_fields=list(restored.keys()),
        )

        return True, f"Änderung rückgängig gemacht für '{entity.name}'", restored

    async def _undo_facet_change(
        self,
        facet_id: UUID,
        diff: dict[str, Any],
        version: EntityVersion,
    ) -> tuple[bool, str, dict[str, Any] | None]:
        """Undo a facet change."""
        operation = diff.get("_operation", "update")

        if operation == "create":
            # Undo create = delete the facet
            facet = await self.session.get(FacetValue, facet_id)
            if facet:
                await self.session.delete(facet)
                await self.session.delete(version)
                await self.session.flush()
                return True, "Facet-Erstellung rückgängig gemacht", {"deleted": True}
            return False, "Facet nicht gefunden", None

        elif operation == "delete":
            # Undo delete = recreate the facet

            text_repr = diff.get("text_representation", "")

            facet = FacetValue(
                id=facet_id,
                entity_id=UUID(diff["entity_id"]),
                facet_type_id=UUID(diff["facet_type_id"]),
                value=diff.get("value", {}),
                text_representation=text_repr,
                is_active=True,
            )
            self.session.add(facet)
            await self.session.flush()

            # Regenerate embedding for restored facet
            from app.utils.similarity import generate_embedding

            embedding = await generate_embedding(text_repr)
            if embedding:
                facet.text_embedding = embedding

            await self.session.delete(version)
            await self.session.flush()

            return True, "Facet-Löschung rückgängig gemacht", {"restored": True}

        else:  # update
            facet = await self.session.get(FacetValue, facet_id)
            if not facet:
                return False, "Facet nicht gefunden", None

            restored = {}
            for field, change in diff.items():
                if field.startswith("_"):
                    continue
                if isinstance(change, dict) and "old" in change:
                    setattr(facet, field, change["old"])
                    restored[field] = change["old"]

            # If text_representation was restored, regenerate embedding
            if "text_representation" in restored:
                from app.utils.similarity import generate_embedding

                embedding = await generate_embedding(restored["text_representation"])
                if embedding:
                    facet.text_embedding = embedding

            await self.session.delete(version)
            await self.session.flush()

            return True, "Facet-Änderung rückgängig gemacht", restored

    async def get_change_history(
        self,
        entity_type: str,
        entity_id: UUID,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get the change history for an entity.

        Args:
            entity_type: "Entity" or "FacetValue"
            entity_id: ID of the entity
            limit: Maximum number of versions to return

        Returns:
            List of version records as dicts
        """
        result = await self.session.execute(
            select(EntityVersion)
            .where(
                EntityVersion.entity_type == entity_type,
                EntityVersion.entity_id == entity_id,
            )
            .order_by(desc(EntityVersion.version_number))
            .limit(limit)
        )

        versions = result.scalars().all()

        return [
            {
                "version_number": v.version_number,
                "diff": v.diff,
                "user_email": v.user_email,
                "change_reason": v.change_reason,
                "created_at": v.created_at.isoformat() if v.created_at else None,
                "can_undo": i == 0,  # Only latest can be undone
            }
            for i, v in enumerate(versions)
        ]

    async def get_recent_changes(
        self,
        user_id: UUID | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get recent changes across all entities.

        Args:
            user_id: Optional filter by user
            limit: Maximum number of changes to return

        Returns:
            List of recent changes
        """
        query = select(EntityVersion).order_by(desc(EntityVersion.created_at)).limit(limit)

        if user_id:
            query = query.where(EntityVersion.user_id == user_id)

        result = await self.session.execute(query)
        versions = result.scalars().all()

        return [
            {
                "id": str(v.id),
                "entity_type": v.entity_type,
                "entity_id": str(v.entity_id),
                "version_number": v.version_number,
                "diff": v.diff,
                "user_email": v.user_email,
                "change_reason": v.change_reason,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ]

    async def _get_latest_version(
        self,
        entity_type: str,
        entity_id: UUID,
    ) -> EntityVersion | None:
        """Get the latest version record for an entity."""
        result = await self.session.execute(
            select(EntityVersion)
            .where(
                EntityVersion.entity_type == entity_type,
                EntityVersion.entity_id == entity_id,
            )
            .order_by(desc(EntityVersion.version_number))
            .limit(1)
        )
        return result.scalar_one_or_none()

    def _create_entity_snapshot(self, entity: Entity) -> dict[str, Any]:
        """Create a full snapshot of an entity."""
        return {
            "id": str(entity.id),
            "name": entity.name,
            "slug": entity.slug,
            "external_id": entity.external_id,
            "entity_type_id": str(entity.entity_type_id),
            "core_attributes": entity.core_attributes,
            "country": entity.country,
            "admin_level_1": entity.admin_level_1,
            "is_active": entity.is_active,
        }


async def get_change_tracker(session: AsyncSession) -> ChangeTracker:
    """Factory function for ChangeTracker."""
    return ChangeTracker(session)
