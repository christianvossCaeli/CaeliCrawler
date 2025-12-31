"""Service for syncing API data to Facet values.

This service fetches data from external APIs and updates FacetValueHistory
entries for matched entities. It bridges the gap between the API configuration
system and the facet history system.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Entity, EntityType, FacetType
from app.models.api_configuration import APIConfiguration, AuthType, ImportMode, SyncStatus
from app.models.facet_value import FacetValueSourceType
from services.facet_history_service import FacetHistoryService
from services.smart_query.api_fetcher import FetchResult, RESTAPIClient

logger = structlog.get_logger()


class APIFacetSyncResult:
    """Result of an API-to-Facet sync operation."""

    def __init__(self):
        self.success: bool = False
        self.records_fetched: int = 0
        self.entities_matched: int = 0
        self.entities_not_found: int = 0
        self.facets_created: int = 0
        self.facets_updated: int = 0
        self.history_points_added: int = 0
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "records_fetched": self.records_fetched,
            "entities_matched": self.entities_matched,
            "entities_not_found": self.entities_not_found,
            "facets_created": self.facets_created,
            "facets_updated": self.facets_updated,
            "history_points_added": self.history_points_added,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class APIFacetSyncService:
    """
    Service for syncing API data to FacetValues/FacetValueHistory.

    This service:
    1. Fetches data from external APIs (REST, etc.)
    2. Matches API records to existing entities
    3. Updates or creates FacetValueHistory entries

    Example usage:
        service = APIFacetSyncService(session)
        result = await service.sync_config(config)
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.history_service = FacetHistoryService(session)

    async def sync_config(self, config: APIConfiguration) -> APIFacetSyncResult:
        """
        Execute a full sync for an API configuration (facet mode).

        This method is used for APIConfigurations with import_mode=FACETS or BOTH.
        It fetches data from the API and updates facet values on matched entities.

        Steps:
        1. Fetch data from the API
        2. For each record, match to an entity
        3. For each facet_mapping, create a history data point

        Args:
            config: The APIConfiguration to sync

        Returns:
            APIFacetSyncResult with sync statistics
        """
        result = APIFacetSyncResult()

        try:
            # Validate config has facet_mappings
            if not config.facet_mappings:
                result.warnings.append("Configuration has no facet_mappings configured")
                return result

            if not config.entity_matching:
                result.warnings.append("Configuration has no entity_matching configured")
                return result

            # Get the full URL for logging
            full_url = config.get_full_url()

            # Step 1: Fetch API data
            logger.info(
                "api_facet_sync_starting",
                config_id=str(config.id),
                data_source_id=str(config.data_source_id),
                api_url=full_url,
            )

            fetch_result = await self._fetch_api_data(config)
            if not fetch_result.success:
                result.errors.append({
                    "stage": "fetch",
                    "error": fetch_result.error or "Unknown fetch error",
                })
                return result

            result.records_fetched = len(fetch_result.items)

            if result.records_fetched == 0:
                result.warnings.append("API returned no records")
                result.success = True
                return result

            # Step 2: Get entity matching configuration
            entity_matching = config.entity_matching
            match_by = entity_matching.get("match_by", "name")
            api_match_field = entity_matching.get("api_field", "name")
            entity_type_slug = entity_matching.get("entity_type_slug")

            # Step 3: Get facet mapping configuration
            facet_mappings = config.facet_mappings

            # Pre-load facet types
            facet_type_slugs = []
            for mapping in facet_mappings.values():
                if isinstance(mapping, dict) and mapping.get("facet_type_slug"):
                    facet_type_slugs.append(mapping["facet_type_slug"])
                elif isinstance(mapping, str):
                    facet_type_slugs.append(mapping)

            facet_types_cache = await self._load_facet_types(facet_type_slugs)

            # Step 4: Process each record
            for record in fetch_result.items:
                try:
                    # Find matching entity
                    match_value = record.get(api_match_field)
                    if not match_value:
                        logger.debug(
                            "api_record_no_match_field",
                            api_field=api_match_field,
                            record_keys=list(record.keys()),
                        )
                        continue

                    entity = await self._find_entity(
                        match_by=match_by,
                        match_value=match_value,
                        entity_type_slug=entity_type_slug,
                    )

                    if not entity:
                        result.entities_not_found += 1
                        logger.debug(
                            "entity_not_found_for_api_record",
                            match_by=match_by,
                            match_value=match_value,
                            entity_type_slug=entity_type_slug,
                        )
                        continue

                    result.entities_matched += 1

                    # Create facet history points
                    sync_counts = await self._sync_facets_for_entity(
                        entity=entity,
                        record=record,
                        facet_mappings=facet_mappings,
                        facet_types_cache=facet_types_cache,
                        source_url=full_url,
                    )

                    result.history_points_added += sync_counts["history_points"]
                    result.facets_created += sync_counts.get("created", 0)
                    result.facets_updated += sync_counts.get("updated", 0)

                except Exception as e:
                    result.errors.append({
                        "stage": "process_record",
                        "record": str(record.get(api_match_field, "unknown")),
                        "error": str(e),
                    })
                    logger.warning(
                        "api_record_processing_failed",
                        error=str(e),
                        record=record.get(api_match_field),
                    )

            # Update config statistics
            config.last_sync_at = datetime.now(UTC)
            config.last_sync_status = SyncStatus.SUCCESS.value if not result.errors else SyncStatus.PARTIAL.value
            config.last_sync_stats = result.to_dict()

            await self.session.flush()
            result.success = True

            logger.info(
                "api_facet_sync_completed",
                config_id=str(config.id),
                records_fetched=result.records_fetched,
                entities_matched=result.entities_matched,
                history_points_added=result.history_points_added,
            )

        except Exception as e:
            logger.exception(
                "api_facet_sync_failed",
                config_id=str(config.id),
                error=str(e),
            )
            result.errors.append({
                "stage": "sync",
                "error": str(e),
            })
            config.last_sync_status = SyncStatus.FAILED.value

        return result

    async def _fetch_api_data(self, config: APIConfiguration) -> FetchResult:
        """Fetch data from the API configured in the configuration."""
        # Get base URL from data source
        base_url = ""
        if config.data_source:
            base_url = config.data_source.base_url or ""

        # Determine if auth is required
        auth_config = None
        if config.auth_type != AuthType.NONE.value:
            auth_config = config.auth_config

        client = RESTAPIClient(
            base_url=base_url,
            auth_config=auth_config,
        )

        try:
            return await client.fetch(endpoint=config.endpoint)
        finally:
            await client.close()

    async def _find_entity(
        self,
        match_by: str,
        match_value: Any,
        entity_type_slug: str | None = None,
    ) -> Entity | None:
        """
        Find an entity based on the matching configuration.

        Args:
            match_by: How to match ("name" or "external_id")
            match_value: The value to match against
            entity_type_slug: Optional entity type filter

        Returns:
            Matched entity or None
        """
        if not match_value:
            return None

        query = select(Entity).where(Entity.is_active.is_(True))

        if match_by == "external_id":
            query = query.where(Entity.external_id == str(match_value))
        elif match_by == "name":
            # Case-insensitive name matching
            query = query.where(func.lower(Entity.name) == func.lower(str(match_value)))
        elif match_by == "name_contains":
            # Fuzzy matching - entity name contains the API value
            query = query.where(
                func.lower(Entity.name).contains(func.lower(str(match_value)))
            )
        else:
            logger.warning(f"Unknown match_by value: {match_by}")
            return None

        if entity_type_slug:
            query = query.join(EntityType).where(EntityType.slug == entity_type_slug)

        result = await self.session.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def _load_facet_types(
        self,
        slugs: list[str],
    ) -> dict[str, FacetType]:
        """Pre-load facet types by slug."""
        if not slugs:
            return {}

        result = await self.session.execute(
            select(FacetType).where(FacetType.slug.in_(slugs))
        )
        facet_types = result.scalars().all()

        return {ft.slug: ft for ft in facet_types}

    async def _sync_facets_for_entity(
        self,
        entity: Entity,
        record: dict[str, Any],
        facet_mappings: dict[str, Any],
        facet_types_cache: dict[str, FacetType],
        source_url: str,
    ) -> dict[str, int]:
        """
        Create/update facet values for an entity from an API record.

        Args:
            entity: The entity to update
            record: The API record data
            facet_mappings: Mapping from API fields to facet types
            facet_types_cache: Pre-loaded facet types
            source_url: URL of the source API

        Returns:
            Counts of created/updated items
        """
        counts = {"history_points": 0, "created": 0, "updated": 0}

        for api_field, mapping_config in facet_mappings.items():
            api_value = record.get(api_field)
            if api_value is None:
                continue

            # Handle both string and dict config formats
            if isinstance(mapping_config, str):
                facet_type_slug = mapping_config
                track_key = "default"
                is_history = True
            else:
                facet_type_slug = mapping_config.get("facet_type_slug")
                track_key = mapping_config.get("track_key", "default")
                is_history = mapping_config.get("is_history", True)

            if not facet_type_slug:
                continue

            facet_type = facet_types_cache.get(facet_type_slug)
            if not facet_type:
                logger.warning(
                    "facet_type_not_found",
                    slug=facet_type_slug,
                    entity=entity.name,
                )
                continue

            # Only process history facets for now
            if facet_type.value_type == "history" and is_history:
                try:
                    # Convert value to float
                    numeric_value = float(api_value)

                    await self.history_service.add_data_point(
                        entity_id=entity.id,
                        facet_type_id=facet_type.id,
                        recorded_at=datetime.now(UTC),
                        value=numeric_value,
                        track_key=track_key,
                        annotations={
                            "api_record": record,
                            "api_field": api_field,
                        },
                        source_type=FacetValueSourceType.IMPORT,
                        source_url=source_url,
                    )
                    counts["history_points"] += 1

                except (ValueError, TypeError) as e:
                    logger.warning(
                        "failed_to_add_history_point",
                        entity=entity.name,
                        facet_type=facet_type_slug,
                        value=api_value,
                        error=str(e),
                    )

        return counts

    async def sync_config_by_id(self, config_id: UUID) -> APIFacetSyncResult:
        """
        Sync a configuration by its ID.

        Args:
            config_id: The configuration UUID

        Returns:
            APIFacetSyncResult
        """
        config = await self.session.get(APIConfiguration, config_id)

        if not config:
            result = APIFacetSyncResult()
            result.errors.append({"stage": "load", "error": "Configuration not found"})
            return result

        if not config.is_active:
            result = APIFacetSyncResult()
            result.errors.append({
                "stage": "validate",
                "error": "Configuration is not active",
            })
            return result

        # Verify this config is meant for facet sync
        if config.import_mode not in [ImportMode.FACETS.value, ImportMode.BOTH.value]:
            result = APIFacetSyncResult()
            result.errors.append({
                "stage": "validate",
                "error": f"Configuration import_mode is {config.import_mode}, expected 'facets' or 'both'",
            })
            return result

        return await self.sync_config(config)

    # Keep backward compatibility aliases
    async def sync_template(self, config: APIConfiguration) -> APIFacetSyncResult:
        """Backward compatibility alias for sync_config."""
        return await self.sync_config(config)

    async def sync_template_by_id(self, config_id: UUID) -> APIFacetSyncResult:
        """Backward compatibility alias for sync_config_by_id."""
        return await self.sync_config_by_id(config_id)
