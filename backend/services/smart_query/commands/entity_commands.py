"""Entity-related commands for Smart Query."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Entity, EntityType
from .base import BaseCommand, CommandResult
from .registry import default_registry

logger = structlog.get_logger()


@default_registry.register("create_entity")
class CreateEntityCommand(BaseCommand):
    """Command to create a new entity."""

    async def validate(self) -> Optional[str]:
        """Validate entity creation data."""
        entity_data = self.data.get("entity_data", {})

        if not entity_data.get("name"):
            return "Entity-Name erforderlich"

        entity_type = self.data.get("entity_type")
        if not entity_type:
            return "Entity-Typ erforderlich"

        return None

    async def execute(self) -> CommandResult:
        """Create the entity."""
        from services.smart_query.entity_operations import create_entity_from_command

        entity_type = self.data.get("entity_type", "municipality")
        entity_data = self.data.get("entity_data", {})

        entity, message = await create_entity_from_command(
            self.session, entity_type, entity_data
        )

        if entity:
            return CommandResult.success_result(
                message=message,
                created_items=[{
                    "type": "entity",
                    "id": str(entity.id),
                    "name": entity.name,
                    "entity_type": entity_type,
                }],
            )
        else:
            return CommandResult.failure(message=message)


@default_registry.register("update_entity")
class UpdateEntityCommand(BaseCommand):
    """Command to update an existing entity."""

    async def validate(self) -> Optional[str]:
        """Validate update data."""
        update_data = self.data.get("update_data", {})

        if not update_data.get("entity_id") and not update_data.get("entity_name"):
            return "Entity-ID oder Entity-Name erforderlich"

        if not update_data.get("updates"):
            return "Keine Updates angegeben"

        return None

    async def execute(self) -> CommandResult:
        """Update the entity."""
        from services.smart_query.entity_operations import find_entity_by_name

        update_data = self.data.get("update_data", {})
        entity_id = update_data.get("entity_id")
        entity_name = update_data.get("entity_name")

        # Find entity
        if entity_id:
            entity = await self.session.get(Entity, UUID(str(entity_id)))
        elif entity_name:
            entity = await find_entity_by_name(self.session, entity_name)
        else:
            return CommandResult.failure(message="Entity nicht gefunden")

        if not entity:
            return CommandResult.failure(message="Entity nicht gefunden")

        # Apply updates
        updates = update_data.get("updates", {})
        if "name" in updates:
            entity.name = updates["name"]
        if "core_attributes" in updates:
            entity.core_attributes = {
                **(entity.core_attributes or {}),
                **updates["core_attributes"]
            }
        if "external_id" in updates:
            entity.external_id = updates["external_id"]

        await self.session.flush()

        return CommandResult.success_result(
            message=f"Entity '{entity.name}' aktualisiert",
            updated_items=[{
                "type": "entity",
                "id": str(entity.id),
                "name": entity.name,
            }],
            entity_id=str(entity.id),
        )


@default_registry.register("delete_entity")
class DeleteEntityCommand(BaseCommand):
    """Command to soft-delete an entity."""

    async def validate(self) -> Optional[str]:
        """Validate delete data."""
        delete_data = self.data.get("delete_entity_data", {})

        if not delete_data.get("entity_id") and not delete_data.get("entity_name"):
            return "Entity-ID oder Entity-Name erforderlich"

        return None

    async def execute(self) -> CommandResult:
        """Soft-delete the entity."""
        from services.smart_query.entity_operations import find_entity_by_name

        delete_data = self.data.get("delete_entity_data", {})
        entity_id = delete_data.get("entity_id")
        entity_name = delete_data.get("entity_name")
        reason = delete_data.get("reason", "Gelöscht über Smart Query")

        # Find entity
        if entity_id:
            entity = await self.session.get(Entity, UUID(str(entity_id)))
        elif entity_name:
            entity = await find_entity_by_name(self.session, entity_name)
        else:
            return CommandResult.failure(message="Entity nicht gefunden")

        if not entity:
            return CommandResult.failure(
                message=f"Entity nicht gefunden: {entity_name or entity_id}"
            )

        if not entity.is_active:
            return CommandResult.failure(
                message=f"Entity '{entity.name}' ist bereits inaktiv/gelöscht"
            )

        # Soft-delete
        entity.is_active = False
        if entity.core_attributes is None:
            entity.core_attributes = {}
        entity.core_attributes["_deletion_reason"] = reason
        entity.core_attributes["_deleted_at"] = datetime.now(timezone.utc).isoformat()

        await self.session.flush()

        logger.info(
            "Entity soft-deleted via Command",
            entity_id=str(entity.id),
            entity_name=entity.name,
            reason=reason,
        )

        return CommandResult.success_result(
            message=f"Entity '{entity.name}' wurde gelöscht (kann wiederhergestellt werden)",
            deleted_items=[{
                "type": "entity",
                "id": str(entity.id),
                "name": entity.name,
            }],
        )


@default_registry.register("create_entity_type")
class CreateEntityTypeCommand(BaseCommand):
    """Command to create a new entity type."""

    async def validate(self) -> Optional[str]:
        """Validate entity type data."""
        entity_type_data = self.data.get("entity_type_data", {})

        if not entity_type_data.get("name"):
            return "Name für Entity-Typ erforderlich"

        return None

    async def execute(self) -> CommandResult:
        """Create the entity type."""
        from services.smart_query.entity_operations import create_entity_type_from_command

        entity_type_data = self.data.get("entity_type_data", {})

        # Add ownership if user is provided
        if self.current_user_id:
            entity_type_data["created_by_id"] = self.current_user_id
            entity_type_data["owner_id"] = self.current_user_id
            entity_type_data.setdefault("is_public", False)

        entity_type, message = await create_entity_type_from_command(
            self.session, entity_type_data
        )

        if entity_type:
            return CommandResult.success_result(
                message=message,
                created_items=[{
                    "type": "entity_type",
                    "id": str(entity_type.id),
                    "name": entity_type.name,
                    "slug": entity_type.slug,
                    "icon": entity_type.icon,
                    "color": entity_type.color,
                }],
            )
        else:
            return CommandResult.failure(message=message)
