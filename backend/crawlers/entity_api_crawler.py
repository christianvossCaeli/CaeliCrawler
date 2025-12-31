"""Entity API Crawler for REST and SPARQL API DataSources.

This crawler fetches data from external APIs and updates Entities accordingly.
It supports both REST APIs (like Caeli Auction) and SPARQL endpoints (like Wikidata).
"""

import json
from typing import TYPE_CHECKING, Any

import structlog

from .base import BaseCrawler, CrawlResult

if TYPE_CHECKING:
    from app.models import CrawlJob, DataSource

logger = structlog.get_logger()


class EntityAPICrawler(BaseCrawler):
    """Crawler for REST and SPARQL APIs that update Entities.

    This crawler is used for DataSources with source_type REST_API or SPARQL_API.
    It fetches data from external APIs and synchronizes it with existing Entities.

    Configuration via crawl_config:
        - entity_api_type: "rest" or "sparql"
        - entity_api_endpoint: API endpoint path
        - entity_api_method: HTTP method (default: GET)
        - entity_api_query: SPARQL query (for SPARQL_API)
        - entity_api_template: Predefined template name
        - entity_field_mapping: Dict mapping API fields to Entity fields
        - entity_type_slug: Target EntityType slug
        - entity_update_strategy: "merge", "replace", or "upsert"
        - entity_id_field: Field used to identify existing entities
    """

    def __init__(self):
        super().__init__()
        self._api_fetcher = None

    async def _get_api_fetcher(self):
        """Lazy-load the API fetcher to avoid circular imports."""
        if self._api_fetcher is None:
            from services.smart_query.api_fetcher import ExternalAPIFetcher
            self._api_fetcher = ExternalAPIFetcher()
        return self._api_fetcher

    async def crawl(self, source: "DataSource", job: "CrawlJob") -> CrawlResult:
        """
        Crawl an API and update Entities.

        Args:
            source: The DataSource with API configuration
            job: The CrawlJob tracking this operation

        Returns:
            CrawlResult with statistics about the sync
        """
        from app.models.data_source import SourceType

        result = CrawlResult()
        config = source.crawl_config or {}

        # Get configuration
        api_type = config.get("entity_api_type", "rest")
        template = config.get("entity_api_template")
        field_mapping = config.get("entity_field_mapping", {})
        entity_type_slug = config.get("entity_type_slug")
        update_strategy = config.get("entity_update_strategy", "merge")

        if source.source_type == SourceType.SPARQL_API:
            api_type = "sparql"
        elif source.source_type == SourceType.REST_API:
            api_type = "rest"

        self.logger.info(
            "Starting Entity API crawl",
            source_id=str(source.id),
            source_name=source.name,
            api_type=api_type,
            template=template,
            entity_type_slug=entity_type_slug,
        )

        try:
            # Build API configuration
            api_config = self._build_api_config(source, config)

            # Fetch data from API
            fetcher = await self._get_api_fetcher()
            fetch_result = await fetcher.fetch(api_config)

            if not fetch_result.success:
                result.errors.append({
                    "type": "api_fetch_error",
                    "message": fetch_result.error,
                })
                self.logger.error(
                    "API fetch failed",
                    source_id=str(source.id),
                    error=fetch_result.error,
                )
                return result

            result.pages_crawled = 1
            result.documents_found = len(fetch_result.items)

            self.logger.info(
                "API fetch successful",
                source_id=str(source.id),
                items_count=len(fetch_result.items),
            )

            # Sync entities if we have items and an entity type
            if fetch_result.items and entity_type_slug:
                sync_result = await self._sync_entities(
                    items=fetch_result.items,
                    field_mapping=field_mapping,
                    entity_type_slug=entity_type_slug,
                    update_strategy=update_strategy,
                    source=source,
                    config=config,
                )

                result.documents_processed = sync_result.get("processed", 0)
                result.documents_new = sync_result.get("created", 0)
                result.documents_updated = sync_result.get("updated", 0)
                result.stats["sync_result"] = sync_result

                if sync_result.get("errors"):
                    result.errors.extend(sync_result["errors"])

            # Store content hash for change detection
            content_hash = self._compute_content_hash(fetch_result.items)
            result.stats["content_hash"] = content_hash
            result.stats["total_items"] = len(fetch_result.items)

            self.logger.info(
                "Entity API crawl completed",
                source_id=str(source.id),
                items_found=result.documents_found,
                entities_created=result.documents_new,
                entities_updated=result.documents_updated,
            )

            return result

        except Exception as e:
            self.logger.error(
                "Entity API crawl failed",
                source_id=str(source.id),
                error=str(e),
                exc_info=True,
            )
            result.errors.append({
                "type": "crawl_error",
                "message": str(e),
            })
            return result

        finally:
            # Close the API fetcher
            if self._api_fetcher:
                await self._api_fetcher.close()
                self._api_fetcher = None

    async def detect_changes(self, source: "DataSource") -> bool:
        """
        Detect if there are changes in the API without full sync.

        Fetches the API and compares content hash with stored hash.

        Args:
            source: The DataSource to check

        Returns:
            True if changes were detected
        """
        config = source.crawl_config or {}

        try:
            # Build API configuration
            api_config = self._build_api_config(source, config)

            # Fetch data from API
            fetcher = await self._get_api_fetcher()
            fetch_result = await fetcher.fetch(api_config)

            if not fetch_result.success:
                self.logger.warning(
                    "Change detection fetch failed",
                    source_id=str(source.id),
                    error=fetch_result.error,
                )
                return True  # Assume changes on error

            # Compute hash and compare
            new_hash = self._compute_content_hash(fetch_result.items)
            old_hash = source.content_hash

            has_changes = new_hash != old_hash

            self.logger.debug(
                "Change detection result",
                source_id=str(source.id),
                has_changes=has_changes,
                old_hash=old_hash[:8] if old_hash else None,
                new_hash=new_hash[:8] if new_hash else None,
            )

            return has_changes

        except Exception as e:
            self.logger.warning(
                "Change detection failed",
                source_id=str(source.id),
                error=str(e),
            )
            return True  # Assume changes on error

        finally:
            if self._api_fetcher:
                await self._api_fetcher.close()
                self._api_fetcher = None

    def _build_api_config(
        self,
        source: "DataSource",
        config: dict[str, Any]
    ) -> dict[str, Any]:
        """Build API configuration from DataSource and crawl_config."""
        from app.models.data_source import SourceType

        api_config = {
            "type": "rest" if source.source_type == SourceType.REST_API else "sparql",
        }

        # Use template if specified
        template = config.get("entity_api_template")
        if template:
            api_config["template"] = template

        # REST API configuration
        if source.source_type == SourceType.REST_API:
            api_config["base_url"] = source.base_url
            api_config["endpoint"] = config.get("entity_api_endpoint", "")
            api_config["method"] = config.get("entity_api_method", "GET")

            # Auth configuration from DataSource
            if source.auth_config:
                api_config["auth_config"] = source.auth_config

        # SPARQL API configuration
        elif source.source_type == SourceType.SPARQL_API:
            api_config["type"] = "sparql"
            query = config.get("entity_api_query")
            if query:
                api_config["query"] = query
            country = config.get("country", "DE")
            api_config["country"] = country

        return api_config

    async def _sync_entities(
        self,
        items: list[dict[str, Any]],
        field_mapping: dict[str, str],
        entity_type_slug: str,
        update_strategy: str,
        source: "DataSource",
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Synchronize API data with Entities.

        Args:
            items: List of items from API
            field_mapping: Mapping from API fields to Entity fields
            entity_type_slug: Target EntityType slug
            update_strategy: "merge", "replace", or "upsert"
            source: The DataSource
            config: crawl_config

        Returns:
            Dict with sync statistics
        """
        from app.database import get_session_context
        from services.entity_api_sync_service import EntityAPISyncService

        result = {
            "processed": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": [],
        }

        try:
            async with get_session_context() as session:
                sync_service = EntityAPISyncService(session)

                sync_result = await sync_service.sync_from_api_response(
                    items=items,
                    field_mapping=field_mapping,
                    entity_type_slug=entity_type_slug,
                    update_strategy=update_strategy,
                    source_id=str(source.id),
                    admin_level_1=config.get("admin_level_1"),
                    country=config.get("country", "DE"),
                )

                result.update(sync_result)
                await session.commit()

        except Exception as e:
            self.logger.error(
                "Entity sync failed",
                error=str(e),
                exc_info=True,
            )
            result["errors"].append({
                "type": "sync_error",
                "message": str(e),
            })

        return result

    def _compute_content_hash(self, items: list[dict[str, Any]]) -> str:
        """Compute hash of API response for change detection."""
        # Sort items by a stable key if possible
        try:
            # Try to sort by common ID fields
            for id_field in ["id", "external_id", "auctionId", "ags"]:
                if items and id_field in items[0]:
                    items = sorted(items, key=lambda x: str(x.get(id_field, "")))
                    break
        except Exception:  # noqa: S110
            pass  # Keep original order

        content = json.dumps(items, sort_keys=True, default=str)
        return self.compute_text_hash(content)
