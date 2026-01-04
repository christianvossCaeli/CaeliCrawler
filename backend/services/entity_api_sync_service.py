"""Entity API Sync Service.

This service handles synchronization of data from external APIs to Entities.
It supports different update strategies (merge, replace, upsert) and tracks
changes for audit purposes.
"""

import contextlib
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Entity, EntityType

logger = structlog.get_logger()


class EntityAPISyncService:
    """Service for synchronizing API data with Entities.

    This service is used by the EntityAPICrawler to update Entities
    based on data fetched from external APIs.

    Update Strategies:
        - merge: Update existing fields, keep fields not in API response
        - replace: Replace all fields with API data
        - upsert: Create if not exists, update if exists
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.logger = structlog.get_logger(service="EntityAPISyncService")

    async def sync_from_api_response(
        self,
        items: list[dict[str, Any]],
        field_mapping: dict[str, str],
        entity_type_slug: str,
        update_strategy: str = "merge",
        source_id: str | None = None,
        admin_level_1: str | None = None,
        country: str = "DE",
    ) -> dict[str, Any]:
        """
        Synchronize API response data with Entities.

        Args:
            items: List of items from API response
            field_mapping: Mapping from API fields to Entity fields
                Example: {"auctionId": "external_id", "name": "name"}
            entity_type_slug: Target EntityType slug
            update_strategy: "merge", "replace", or "upsert"
            source_id: DataSource ID for tracking
            admin_level_1: Default admin_level_1 for new entities
            country: Default country code

        Returns:
            Dict with sync statistics:
                - processed: Total items processed
                - created: New entities created
                - updated: Existing entities updated
                - skipped: Items skipped (no changes)
                - errors: List of errors
        """
        result = {
            "processed": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": [],
        }

        # Get or validate EntityType
        entity_type = await self._get_entity_type(entity_type_slug)
        if not entity_type:
            result["errors"].append(
                {
                    "type": "config_error",
                    "message": f"EntityType '{entity_type_slug}' not found",
                }
            )
            return result

        # Determine the ID field for matching
        id_field = self._get_id_field(field_mapping)

        for i, item in enumerate(items):
            try:
                sync_result = await self._sync_single_item(
                    item=item,
                    field_mapping=field_mapping,
                    entity_type=entity_type,
                    update_strategy=update_strategy,
                    id_field=id_field,
                    source_id=source_id,
                    admin_level_1=admin_level_1,
                    country=country,
                )

                result["processed"] += 1

                if sync_result == "created":
                    result["created"] += 1
                elif sync_result == "updated":
                    result["updated"] += 1
                elif sync_result == "skipped":
                    result["skipped"] += 1

                # Flush periodically to avoid memory issues
                if (i + 1) % 100 == 0:
                    await self.session.flush()
                    self.logger.debug(
                        "Sync progress",
                        processed=i + 1,
                        total=len(items),
                    )

            except Exception as e:
                result["errors"].append(
                    {
                        "type": "item_error",
                        "index": i,
                        "message": str(e),
                    }
                )
                self.logger.warning(
                    "Failed to sync item",
                    index=i,
                    error=str(e),
                )

        # Final flush
        await self.session.flush()

        self.logger.info(
            "API sync completed",
            entity_type=entity_type_slug,
            processed=result["processed"],
            created=result["created"],
            updated=result["updated"],
            skipped=result["skipped"],
            errors=len(result["errors"]),
        )

        return result

    async def _get_entity_type(self, slug: str) -> EntityType | None:
        """Get EntityType by slug."""
        result = await self.session.execute(select(EntityType).where(EntityType.slug == slug))
        return result.scalar_one_or_none()

    def _get_id_field(self, field_mapping: dict[str, str]) -> str:
        """Determine which field to use for entity identification."""
        # Priority: external_id > id > name
        if "external_id" in field_mapping:
            return "external_id"
        if "id" in field_mapping:
            return "external_id"  # Map id to external_id
        return "name"

    async def _sync_single_item(
        self,
        item: dict[str, Any],
        field_mapping: dict[str, str],
        entity_type: EntityType,
        update_strategy: str,
        id_field: str,
        source_id: str | None,
        admin_level_1: str | None,
        country: str,
    ) -> str:
        """
        Sync a single API item with an Entity.

        Returns:
            "created", "updated", or "skipped"
        """
        # Map API fields to Entity fields
        entity_data = self._map_fields(item, field_mapping, admin_level_1, country)

        if not entity_data.get("name"):
            raise ValueError("No name field mapped from API data")

        # Try to find existing entity
        existing_entity = await self._find_existing_entity(
            entity_type_id=entity_type.id,
            id_field=id_field,
            id_value=entity_data.get(id_field) or entity_data.get("name"),
        )

        if existing_entity:
            # Update existing entity
            if update_strategy == "upsert" or update_strategy == "merge":
                has_changes = self._update_entity(
                    entity=existing_entity,
                    data=entity_data,
                    strategy=update_strategy,
                    source_id=source_id,
                )
                return "updated" if has_changes else "skipped"
            elif update_strategy == "replace":
                self._replace_entity(existing_entity, entity_data, source_id)
                return "updated"
            else:
                return "skipped"
        else:
            # Create new entity (only for upsert strategy or if entity doesn't exist)
            if update_strategy in ("upsert", "merge"):
                await self._create_entity(
                    entity_type=entity_type,
                    data=entity_data,
                    source_id=source_id,
                )
                return "created"
            return "skipped"

    def _map_fields(
        self,
        item: dict[str, Any],
        field_mapping: dict[str, str],
        default_admin_level_1: str | None,
        default_country: str,
    ) -> dict[str, Any]:
        """Map API fields to Entity fields using the field_mapping."""
        entity_data = {
            "core_attributes": {},
        }

        # Standard field mappings
        standard_fields = [
            "name",
            "external_id",
            "admin_level_1",
            "admin_level_2",
            "latitude",
            "longitude",
            "country",
            "website",
        ]

        for entity_field, api_field in field_mapping.items():
            value = item.get(api_field)

            if value is None:
                continue

            if entity_field in standard_fields:
                # Standard Entity fields
                if entity_field in ("latitude", "longitude"):
                    with contextlib.suppress(ValueError, TypeError):
                        entity_data[entity_field] = float(value)
                elif entity_field == "country":
                    entity_data["country"] = str(value).upper()[:2]
                else:
                    entity_data[entity_field] = str(value)
            else:
                # Additional fields go to core_attributes
                entity_data["core_attributes"][entity_field] = value

        # Apply defaults
        if not entity_data.get("admin_level_1") and default_admin_level_1:
            entity_data["admin_level_1"] = default_admin_level_1

        if not entity_data.get("country"):
            entity_data["country"] = default_country

        return entity_data

    async def _find_existing_entity(
        self,
        entity_type_id,
        id_field: str,
        id_value: str,
    ) -> Entity | None:
        """Find existing entity by ID field."""
        if not id_value:
            return None

        if id_field == "external_id":
            result = await self.session.execute(
                select(Entity).where(
                    Entity.entity_type_id == entity_type_id,
                    Entity.external_id == str(id_value),
                )
            )
        else:  # name
            result = await self.session.execute(
                select(Entity).where(
                    Entity.entity_type_id == entity_type_id,
                    Entity.name == str(id_value),
                )
            )

        return result.scalar_one_or_none()

    def _update_entity(
        self,
        entity: Entity,
        data: dict[str, Any],
        strategy: str,
        source_id: str | None,
    ) -> bool:
        """Update entity fields. Returns True if any changes were made."""
        has_changes = False

        # Update standard fields
        for field in ["name", "external_id", "admin_level_1", "admin_level_2", "latitude", "longitude", "country"]:
            new_value = data.get(field)
            if new_value is not None:
                current_value = getattr(entity, field, None)
                if current_value != new_value:
                    setattr(entity, field, new_value)
                    has_changes = True

        # Update core_attributes
        new_attrs = data.get("core_attributes", {})
        if new_attrs:
            current_attrs = entity.core_attributes or {}

            if strategy == "merge":
                # Merge: update/add fields, keep existing
                merged = {**current_attrs, **new_attrs}
                if merged != current_attrs:
                    entity.core_attributes = merged
                    has_changes = True
            else:
                # Replace core_attributes entirely
                if new_attrs != current_attrs:
                    entity.core_attributes = new_attrs
                    has_changes = True

        # Track sync metadata
        if has_changes:
            entity.updated_at = datetime.utcnow()
            if source_id:
                meta = entity.core_attributes or {}
                meta["_last_api_sync"] = {
                    "source_id": source_id,
                    "synced_at": datetime.utcnow().isoformat(),
                }
                entity.core_attributes = meta

        return has_changes

    def _replace_entity(
        self,
        entity: Entity,
        data: dict[str, Any],
        source_id: str | None,
    ):
        """Replace entity fields entirely."""
        for field in ["name", "external_id", "admin_level_1", "admin_level_2", "latitude", "longitude", "country"]:
            value = data.get(field)
            if value is not None:
                setattr(entity, field, value)

        # Replace core_attributes
        new_attrs = data.get("core_attributes", {})
        if source_id:
            new_attrs["_last_api_sync"] = {
                "source_id": source_id,
                "synced_at": datetime.utcnow().isoformat(),
            }
        entity.core_attributes = new_attrs
        entity.updated_at = datetime.utcnow()

    async def _create_entity(
        self,
        entity_type: EntityType,
        data: dict[str, Any],
        source_id: str | None,
    ) -> Entity:
        """Create a new entity."""
        from services.smart_query.utils import generate_slug

        core_attrs = data.get("core_attributes", {})
        if source_id:
            core_attrs["_created_from_api"] = {
                "source_id": source_id,
                "created_at": datetime.utcnow().isoformat(),
            }

        entity = Entity(
            entity_type_id=entity_type.id,
            name=data["name"],
            slug=generate_slug(data["name"]),
            external_id=data.get("external_id"),
            admin_level_1=data.get("admin_level_1"),
            admin_level_2=data.get("admin_level_2"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            country=data.get("country", "DE"),
            core_attributes=core_attrs,
            is_active=True,
        )

        self.session.add(entity)
        return entity
