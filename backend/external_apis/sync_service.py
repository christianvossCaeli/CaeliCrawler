"""External API synchronization service.

This service handles the synchronization of data from external APIs:
- Fetching all records from configured APIs
- Detecting new, changed, and missing records
- Creating and updating entities
- Linking entities to municipalities via AI
- Managing record lifecycle (active, missing, archived)
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Optional
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Entity, EntityType
from app.models.api_configuration import APIConfiguration, SyncStatus
from external_apis.base import (
    BaseExternalAPIClient,
    ExternalAPIRecord,
    SyncResult,
)
from external_apis.entity_linking import EntityLinkingService
from external_apis.models.sync_record import RecordStatus, SyncRecord
from services.entity_facet_service import get_or_create_entity

logger = structlog.get_logger(__name__)


class ExternalAPISyncService:
    """Service for synchronizing external API data with entities.

    This service orchestrates the complete sync process:
    1. Fetch all records from the external API
    2. Compare with existing sync records to detect changes
    3. Create new entities for new records
    4. Update entities for changed records
    5. Link entities to municipalities (using AI if enabled)
    6. Mark records as missing if not found in API
    7. Archive records that have been missing too long

    Usage:
        async with ExternalAPISyncService(session) as service:
            result = await service.sync_source(config)
    """

    # Registry of API client classes by api_type
    CLIENT_REGISTRY: dict[str, type[BaseExternalAPIClient]] = {}

    @classmethod
    def register_client(cls, api_type: str, client_class: type[BaseExternalAPIClient]) -> None:
        """Register an API client class for a specific api_type.

        Args:
            api_type: The api_type string that maps to this client.
            client_class: The client class to use for this api_type.
        """
        cls.CLIENT_REGISTRY[api_type] = client_class
        logger.info(
            "api_client_registered",
            api_type=api_type,
            client_class=client_class.__name__,
        )

    def __init__(self, session: AsyncSession):
        """Initialize the sync service.

        Args:
            session: Database session for all operations.
        """
        self.session = session
        self.linking_service = EntityLinkingService(session)
        self._entity_type_cache: dict[str, EntityType] = {}

    async def __aenter__(self) -> "ExternalAPISyncService":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        pass

    async def sync_source(self, config: APIConfiguration) -> SyncResult:
        """Perform full synchronization for an API configuration.

        This is the main entry point for syncing. It handles:
        - Getting the appropriate API client
        - Fetching all records
        - Processing each record (create/update)
        - Entity linking
        - Handling missing records

        Args:
            config: The APIConfiguration to sync.

        Returns:
            SyncResult with statistics about the sync operation.

        Raises:
            ValueError: If no client is registered for the api_type.
        """
        result = SyncResult()
        start_time = datetime.now(UTC)

        logger.info(
            "sync_starting",
            config_id=str(config.id),
            api_type=config.api_type,
            data_source_id=str(config.data_source_id),
        )

        try:
            # Get appropriate client
            client = await self._get_client(config)

            # Fetch all records from API
            async with client:
                records = await client.fetch_all_records()
                result.records_fetched = len(records)

            logger.info(
                "records_fetched",
                config_id=str(config.id),
                count=len(records),
            )

            # Get target entity type
            entity_type = await self._get_entity_type(config.entity_type_slug)
            if not entity_type:
                raise ValueError(f"Entity type not found: {config.entity_type_slug}")

            # Track which external IDs we've seen
            seen_ids: set[str] = set()

            # Process each record
            for record in records:
                seen_ids.add(record.external_id)

                try:
                    sync_result = await self._process_record(config, record, entity_type)

                    if sync_result["created"]:
                        result.entities_created += 1
                    elif sync_result["updated"]:
                        result.entities_updated += 1
                    else:
                        result.entities_unchanged += 1

                    if sync_result["linked"]:
                        result.entities_linked += 1

                except Exception as e:
                    logger.error(
                        "record_processing_error",
                        config_id=str(config.id),
                        external_id=record.external_id,
                        error=str(e),
                    )
                    result.errors.append(
                        {
                            "external_id": record.external_id,
                            "error": str(e),
                            "type": type(e).__name__,
                        }
                    )

            # Handle missing records
            missing_count, archived_count = await self._handle_missing_records(config, seen_ids)
            result.records_missing = missing_count
            result.records_archived = archived_count

            # Update config with sync status
            config.last_sync_at = datetime.now(UTC)
            config.last_sync_status = SyncStatus.SUCCESS.value
            config.last_sync_error = None
            config.last_sync_stats = result.to_dict()

            await self.session.commit()

            duration = (datetime.now(UTC) - start_time).total_seconds()
            logger.info(
                "sync_completed",
                config_id=str(config.id),
                duration_seconds=duration,
                **result.to_dict(),
            )

        except Exception as e:
            logger.error(
                "sync_failed",
                config_id=str(config.id),
                error=str(e),
            )

            config.last_sync_at = datetime.now(UTC)
            config.last_sync_status = SyncStatus.FAILED.value
            config.last_sync_error = str(e)

            await self.session.commit()
            raise

        return result

    async def _get_client(self, config: APIConfiguration) -> BaseExternalAPIClient:
        """Get the appropriate API client for a config.

        Args:
            config: The APIConfiguration.

        Returns:
            Configured API client instance.

        Raises:
            ValueError: If no client is registered for the api_type.
        """
        client_class = self.CLIENT_REGISTRY.get(config.api_type)

        if not client_class:
            raise ValueError(
                f"No client registered for api_type: {config.api_type}. "
                f"Available types: {list(self.CLIENT_REGISTRY.keys())}"
            )

        return client_class(
            auth_token=config.get_auth_token(),
            base_url=config.get_full_url(),
        )

    async def _get_entity_type(self, slug: str) -> EntityType | None:
        """Get entity type by slug with caching.

        Args:
            slug: Entity type slug.

        Returns:
            EntityType if found, None otherwise.
        """
        if slug not in self._entity_type_cache:
            result = await self.session.execute(
                select(EntityType).where(
                    EntityType.slug == slug,
                    EntityType.is_active.is_(True),
                )
            )
            entity_type = result.scalar_one_or_none()
            if entity_type:
                self._entity_type_cache[slug] = entity_type

        return self._entity_type_cache.get(slug)

    async def _process_record(
        self,
        config: APIConfiguration,
        record: ExternalAPIRecord,
        entity_type: EntityType,
    ) -> dict[str, bool]:
        """Process a single record from the API.

        Args:
            config: The APIConfiguration.
            record: The API record to process.
            entity_type: Target entity type.

        Returns:
            Dictionary with 'created', 'updated', 'linked' flags.
        """
        result = {"created": False, "updated": False, "linked": False}

        # Check for existing sync record
        sync_record = await self._get_sync_record(config.id, record.external_id)
        content_hash = record.compute_hash()

        if sync_record:
            # Existing record - check for changes
            was_updated = sync_record.mark_seen(content_hash, record.raw_data)
            result["updated"] = was_updated

            if was_updated and sync_record.entity_id:
                # Update the entity
                await self._update_entity(sync_record.entity_id, record, config)
                # Update facet values
                if config.facet_mappings:
                    await self._update_facet_values(sync_record.entity_id, record, config)
        else:
            # New record - create entity and sync record
            entity = await self._create_entity(record, entity_type, config)
            result["created"] = True

            # Create sync record
            sync_record = SyncRecord(
                api_configuration_id=config.id,
                external_id=record.external_id,
                entity_id=entity.id,
                content_hash=content_hash,
                raw_data=record.raw_data,
                last_modified_at=record.modified_at,
            )
            self.session.add(sync_record)

            # Create facet values from API data
            if config.facet_mappings:
                await self._create_facet_values(entity.id, record, config)

            # Try to link to municipality
            if config.ai_linking_enabled and record.location_hints:
                linked = await self._link_entity_to_locations(
                    entity.id,
                    record.location_hints,
                    config.link_to_entity_types or ["territorial_entity"],
                )
                if linked:
                    result["linked"] = True
                    sync_record.linked_entity_ids = linked
                    sync_record.linking_metadata = {
                        "method": "ai_linking",
                        "hints": record.location_hints,
                        "linked_count": len(linked),
                    }

        return result

    async def _get_sync_record(self, config_id: UUID, external_id: str) -> SyncRecord | None:
        """Get existing sync record for an external ID.

        Args:
            config_id: APIConfiguration ID.
            external_id: External ID from the API.

        Returns:
            SyncRecord if found, None otherwise.
        """
        result = await self.session.execute(
            select(SyncRecord).where(
                SyncRecord.api_configuration_id == config_id,
                SyncRecord.external_id == external_id,
            )
        )
        return result.scalar_one_or_none()

    async def _create_entity(
        self,
        record: ExternalAPIRecord,
        entity_type: EntityType,
        config: APIConfiguration,
    ) -> Entity:
        """Create a new entity from an API record.

        Args:
            record: The API record.
            entity_type: Target entity type.
            config: The APIConfiguration.

        Returns:
            Created Entity.
        """
        # Map fields from raw_data to core_attributes
        core_attributes = self._map_fields(record.raw_data, config.field_mappings)

        # Extract coordinates if available
        latitude = None
        longitude = None
        for hint in record.location_hints:
            if hint.startswith("geo:"):
                try:
                    coords = hint[4:].split(",")
                    latitude = float(coords[0])
                    longitude = float(coords[1])
                except (ValueError, IndexError):
                    pass

        entity = await get_or_create_entity(
            self.session,
            entity_type_slug=entity_type.slug,
            name=record.name,
            external_id=record.external_id,
            core_attributes=core_attributes,
            latitude=latitude,
            longitude=longitude,
        )

        # Set API source reference
        entity.api_configuration_id = config.id
        entity.last_seen_at = datetime.now(UTC)

        logger.debug(
            "entity_created",
            entity_id=str(entity.id),
            external_id=record.external_id,
            name=record.name,
        )

        return entity

    async def _update_entity(
        self,
        entity_id: UUID,
        record: ExternalAPIRecord,
        config: APIConfiguration,
    ) -> None:
        """Update an existing entity from an API record.

        Args:
            entity_id: ID of the entity to update.
            record: The API record with new data.
            config: The APIConfiguration.
        """
        entity = await self.session.get(Entity, entity_id)
        if not entity:
            return

        # Update core attributes with mapped fields
        new_attributes = self._map_fields(record.raw_data, config.field_mappings)
        entity.core_attributes = {**entity.core_attributes, **new_attributes}

        # Update name if changed
        if entity.name != record.name:
            entity.name = record.name
            from services.entity_facet_service import normalize_name

            entity.name_normalized = normalize_name(record.name)

        entity.last_seen_at = datetime.now(UTC)

        logger.debug(
            "entity_updated",
            entity_id=str(entity_id),
            external_id=record.external_id,
        )

    def _map_fields(self, raw_data: dict[str, Any], mappings: dict[str, str]) -> dict[str, Any]:
        """Map API fields to entity core_attributes.

        The mapping format is: {"api_field": "attribute_path"}
        Nested paths like "core_attributes.status" are supported.

        Args:
            raw_data: Raw data from API.
            mappings: Field mapping configuration.

        Returns:
            Dictionary of mapped attributes.
        """
        result: dict[str, Any] = {}

        for api_field, attr_path in mappings.items():
            value = self._get_nested_value(raw_data, api_field)
            if value is not None:
                # Handle nested paths in target (e.g., "core_attributes.status")
                if "." in attr_path:
                    parts = attr_path.split(".")
                    if parts[0] == "core_attributes" and len(parts) > 1:
                        result[parts[1]] = value
                else:
                    result[attr_path] = value

        return result

    def _get_nested_value(self, data: dict[str, Any], path: str) -> Any | None:
        """Get a value from nested dictionary using dot notation.

        Args:
            data: Dictionary to get value from.
            path: Dot-notation path (e.g., "location.city").

        Returns:
            Value if found, None otherwise.
        """
        parts = path.split(".")
        current = data

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current

    async def _link_entity_to_locations(
        self,
        entity_id: UUID,
        location_hints: list[str],
        link_types: list[str],
    ) -> list[UUID]:
        """Link an entity to location-based entities.

        Args:
            entity_id: ID of the entity to link.
            location_hints: Location-related strings from API.
            link_types: Entity types to link to.

        Returns:
            List of linked entity IDs.
        """
        linked_ids = []

        try:
            results = await self.linking_service.link_entity_to_locations(entity_id, location_hints, link_types)

            for _type_slug, ids in results.items():
                linked_ids.extend(ids)

        except Exception as e:
            logger.warning(
                "entity_linking_failed",
                entity_id=str(entity_id),
                error=str(e),
            )

        return linked_ids

    async def _handle_missing_records(self, config: APIConfiguration, seen_ids: set[str]) -> tuple[int, int]:
        """Handle records that were not found in the current API response.

        This marks records as missing and archives them if they've been
        missing for too long.

        Args:
            config: The APIConfiguration.
            seen_ids: Set of external IDs found in this sync.

        Returns:
            Tuple of (missing_count, archived_count).
        """
        if not config.mark_missing_inactive:
            return 0, 0

        # Find active records not in seen_ids
        result = await self.session.execute(
            select(SyncRecord).where(
                SyncRecord.api_configuration_id == config.id,
                SyncRecord.external_id.notin_(seen_ids),
                SyncRecord.sync_status.in_([RecordStatus.ACTIVE.value, RecordStatus.UPDATED.value]),
            )
        )
        missing_records = result.scalars().all()

        missing_count = 0
        archived_count = 0
        now = datetime.now(UTC)
        archive_threshold = now - timedelta(days=config.inactive_after_days)

        for record in missing_records:
            record.mark_missing()
            missing_count += 1

            # Check if should be archived
            if record.missing_since and record.missing_since < archive_threshold:
                record.mark_archived()
                archived_count += 1

                # Deactivate the entity
                if record.entity_id:
                    entity = await self.session.get(Entity, record.entity_id)
                    if entity:
                        entity.is_active = False
                        logger.info(
                            "entity_archived",
                            entity_id=str(record.entity_id),
                            external_id=record.external_id,
                            missing_days=config.inactive_after_days,
                        )

        if missing_count > 0:
            logger.info(
                "missing_records_processed",
                config_id=str(config.id),
                missing=missing_count,
                archived=archived_count,
            )

        return missing_count, archived_count

    async def _create_facet_values(
        self,
        entity_id: UUID,
        record: ExternalAPIRecord,
        config: APIConfiguration,
    ) -> int:
        """Create FacetValues for an entity from API data.

        Args:
            entity_id: ID of the entity to add facets to.
            record: The API record with raw data.
            config: The APIConfiguration with facet_mappings.

        Returns:
            Number of facet values created.
        """
        from app.models import FacetValue
        from app.models.facet_value import FacetValueSourceType

        created_count = 0

        for api_field, facet_config in config.facet_mappings.items():
            # Handle both simple string and dict config
            if isinstance(facet_config, str):
                facet_slug = facet_config
            else:
                facet_slug = facet_config.get("facet_type_slug", facet_config)

            value = self._get_nested_value(record.raw_data, api_field)
            if value is None:
                continue

            # Get FacetType by slug
            facet_type = await self._get_facet_type(facet_slug)
            if not facet_type:
                logger.warning(
                    "facet_type_not_found",
                    slug=facet_slug,
                    api_field=api_field,
                )
                continue

            # Convert value based on facet type
            facet_value = self._convert_value_for_facet(value, facet_type)
            if facet_value is None:
                continue

            # Ensure value is a dict for JSONB storage
            if not isinstance(facet_value, dict):
                facet_value = {"value": facet_value}

            # Create text representation
            text_repr = self._get_text_representation(facet_value, facet_type)

            # Create FacetValue
            fv = FacetValue(
                entity_id=entity_id,
                facet_type_id=facet_type.id,
                value=facet_value,
                text_representation=text_repr,
                source_type=FacetValueSourceType.IMPORT,
                source_url=f"api_config:{config.id}",
                confidence_score=1.0,  # API data is authoritative
                human_verified=False,
                occurrence_count=1,
                is_active=True,
            )
            self.session.add(fv)
            created_count += 1

        logger.debug(
            "facet_values_created",
            entity_id=str(entity_id),
            count=created_count,
        )

        return created_count

    async def _update_facet_values(
        self,
        entity_id: UUID,
        record: ExternalAPIRecord,
        config: APIConfiguration,
    ) -> int:
        """Update existing FacetValues for an entity from API data.

        Args:
            entity_id: ID of the entity to update facets for.
            record: The API record with raw data.
            config: The APIConfiguration with facet_mappings.

        Returns:
            Number of facet values updated.
        """
        from app.models import FacetValue
        from app.models.facet_value import FacetValueSourceType

        updated_count = 0
        source_url = f"api_config:{config.id}"

        for api_field, facet_config in config.facet_mappings.items():
            # Handle both simple string and dict config
            if isinstance(facet_config, str):
                facet_slug = facet_config
            else:
                facet_slug = facet_config.get("facet_type_slug", facet_config)

            value = self._get_nested_value(record.raw_data, api_field)
            if value is None:
                continue

            # Get FacetType by slug
            facet_type = await self._get_facet_type(facet_slug)
            if not facet_type:
                continue

            # Convert value based on facet type
            facet_value = self._convert_value_for_facet(value, facet_type)
            if facet_value is None:
                continue

            # Ensure value is a dict for JSONB storage
            if not isinstance(facet_value, dict):
                facet_value = {"value": facet_value}

            # Check if FacetValue exists (by source_url)
            result = await self.session.execute(
                select(FacetValue).where(
                    FacetValue.entity_id == entity_id,
                    FacetValue.facet_type_id == facet_type.id,
                    FacetValue.source_url == source_url,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                if existing.value != facet_value:
                    existing.value = facet_value
                    existing.text_representation = self._get_text_representation(facet_value, facet_type)
                    updated_count += 1
            else:
                # Create new FacetValue
                text_repr = self._get_text_representation(facet_value, facet_type)
                fv = FacetValue(
                    entity_id=entity_id,
                    facet_type_id=facet_type.id,
                    value=facet_value,
                    text_representation=text_repr,
                    source_type=FacetValueSourceType.IMPORT,
                    source_url=source_url,
                    confidence_score=1.0,
                    human_verified=False,
                    occurrence_count=1,
                    is_active=True,
                )
                self.session.add(fv)
                updated_count += 1

        return updated_count

    def _get_text_representation(
        self,
        value: dict[str, Any],
        facet_type: "FacetType",  # noqa: F821
    ) -> str:
        """Generate text representation for a facet value.

        Args:
            value: The facet value dict.
            facet_type: The FacetType.

        Returns:
            Human-readable text representation.
        """

        # Extract the actual value
        actual_value = value.get("value", value)

        if isinstance(actual_value, bool):
            return "Ja" if actual_value else "Nein"
        elif isinstance(actual_value, (int, float)):
            # Format number based on facet type
            if "percent" in facet_type.slug or "irr" in facet_type.slug:
                return f"{actual_value}%"
            elif "mw" in facet_type.slug or "power" in facet_type.slug:
                return f"{actual_value} MW"
            elif "ha" in facet_type.slug or "area" in facet_type.slug:
                return f"{actual_value} ha"
            elif "height" in facet_type.slug:
                return f"{actual_value} m"
            elif "speed" in facet_type.slug:
                return f"{actual_value} m/s"
            elif "hours" in facet_type.slug:
                return f"{actual_value} h"
            elif "count" in facet_type.slug or "wea" in facet_type.slug:
                return str(int(actual_value))
            return str(actual_value)
        elif isinstance(actual_value, str):
            return actual_value
        elif isinstance(actual_value, dict):
            # Try to extract meaningful text from dict
            return str(actual_value.get("name", actual_value.get("value", str(actual_value))))
        else:
            return str(actual_value)

    async def _get_facet_type(self, slug: str) -> Optional["FacetType"]:  # noqa: F821
        """Get FacetType by slug with caching.

        Args:
            slug: FacetType slug.

        Returns:
            FacetType if found, None otherwise.
        """
        from app.models import FacetType

        cache_key = f"facet_{slug}"
        if cache_key not in self._entity_type_cache:
            result = await self.session.execute(
                select(FacetType).where(
                    FacetType.slug == slug,
                    FacetType.is_active.is_(True),
                )
            )
            facet_type = result.scalar_one_or_none()
            if facet_type:
                self._entity_type_cache[cache_key] = facet_type

        return self._entity_type_cache.get(cache_key)

    def _convert_value_for_facet(
        self,
        value: Any,
        facet_type: "FacetType",  # noqa: F821
    ) -> Any | None:
        """Convert a raw value to the appropriate type for a FacetType.

        Args:
            value: Raw value from API.
            facet_type: Target FacetType.

        Returns:
            Converted value or None if conversion fails.
        """
        try:
            if facet_type.value_type == "text":
                return str(value) if value is not None else None
            elif facet_type.value_type == "number":
                if isinstance(value, (int, float)):
                    return value
                return float(value) if value else None
            elif facet_type.value_type == "boolean":
                if isinstance(value, bool):
                    return value
                return str(value).lower() in ("true", "1", "yes", "ja")
            elif facet_type.value_type == "structured":
                return value if isinstance(value, dict) else {"value": value}
            else:
                return value
        except (ValueError, TypeError) as e:
            logger.warning(
                "facet_value_conversion_failed",
                value=str(value)[:100],
                facet_type=facet_type.slug,
                error=str(e),
            )
            return None


# Register default clients
def _register_default_clients():
    """Register default API client implementations."""
    from external_apis.clients.auction_client import CaeliAuctionClient

    ExternalAPISyncService.register_client("auction", CaeliAuctionClient)


# Auto-register when module is imported
_register_default_clients()
