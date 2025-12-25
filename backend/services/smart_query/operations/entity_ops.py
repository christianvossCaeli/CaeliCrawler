"""Entity operations for Smart Query Service.

Operations:
- update_entity: Update an existing entity
- delete_entity: Soft-delete an entity
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .base import WriteOperation, OperationResult, register_operation
from ..entity_operations import find_entity_by_name

logger = structlog.get_logger()


@register_operation("update_entity")
class UpdateEntityOperation(WriteOperation):
    """Update an existing entity."""

    def validate(self, command: Dict[str, Any]) -> Optional[str]:
        update_data = command.get("update_data", {})
        if not update_data.get("entity_id") and not update_data.get("entity_name"):
            return "Entity-ID oder Entity-Name erforderlich"
        return None

    async def execute(
        self,
        session: AsyncSession,
        command: Dict[str, Any],
        user_id: Optional[UUID] = None,
    ) -> OperationResult:
        from app.models import Entity

        update_data = command.get("update_data", {})
        entity_id = update_data.get("entity_id")
        entity_name = update_data.get("entity_name")

        # Find entity
        if entity_id:
            entity = await session.get(Entity, UUID(str(entity_id)))
        elif entity_name:
            entity = await find_entity_by_name(session, entity_name)
        else:
            return OperationResult(
                success=False,
                message="Entity-ID oder Entity-Name erforderlich",
            )

        if not entity:
            return OperationResult(success=False, message="Entity nicht gefunden")

        # Update fields
        updates = update_data.get("updates", {})
        if "name" in updates:
            new_name = updates["name"]
            # Check for duplicate name before updating
            from app.utils.text import normalize_name
            from sqlalchemy import select, and_
            new_normalized = normalize_name(new_name)

            existing = await session.execute(
                select(Entity).where(
                    and_(
                        Entity.entity_type_id == entity.entity_type_id,
                        Entity.name_normalized == new_normalized,
                        Entity.id != entity.id,
                        Entity.is_active.is_(True),
                    )
                )
            )
            if existing.scalar():
                return OperationResult(
                    success=False,
                    message=f"Entity mit Namen '{new_name}' existiert bereits in diesem Typ",
                )
            entity.name = new_name
            entity.name_normalized = new_normalized
        if "core_attributes" in updates:
            entity.core_attributes = {**(entity.core_attributes or {}), **updates["core_attributes"]}
        if "external_id" in updates:
            entity.external_id = updates["external_id"]

        await session.flush()

        return OperationResult(
            success=True,
            message=f"Entity '{entity.name}' aktualisiert",
            created_items=[{"type": "entity", "id": str(entity.id), "updated": True}],
        )


@register_operation("delete_entity")
class DeleteEntityOperation(WriteOperation):
    """Soft-delete an entity (set is_active=False)."""

    def validate(self, command: Dict[str, Any]) -> Optional[str]:
        delete_data = command.get("delete_data", {})
        if not delete_data.get("entity_id") and not delete_data.get("entity_name"):
            return "Entity-ID oder Entity-Name erforderlich"
        return None

    async def execute(
        self,
        session: AsyncSession,
        command: Dict[str, Any],
        user_id: Optional[UUID] = None,
    ) -> OperationResult:
        from app.models import Entity

        delete_data = command.get("delete_data", {})
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
            return OperationResult(
                success=False,
                message=f"Entity nicht gefunden: {entity_name or entity_id}",
            )

        if not entity.is_active:
            return OperationResult(
                success=False,
                message=f"Entity '{entity.name}' ist bereits inaktiv/gelöscht",
            )

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

        return OperationResult(
            success=True,
            message=f"Entity '{entity.name}' wurde gelöscht (kann wiederhergestellt werden)",
            created_items=[
                {
                    "type": "entity",
                    "id": str(entity.id),
                    "name": entity.name,
                    "deleted": True,
                }
            ],
        )
