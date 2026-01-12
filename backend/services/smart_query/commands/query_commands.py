"""Query commands for Smart Query.

Commands for querying entity/facet data with visualization support.
"""

from uuid import UUID

import structlog

from app.schemas.visualization import (
    QueryDataConfig,
    QueryFilters,
    TimeRangeConfig,
)

from ..data_query_service import DataQueryService
from ..visualization_selector import VisualizationSelector
from .base import BaseCommand, CommandResult
from .registry import default_registry

logger = structlog.get_logger()


@default_registry.register("query_data")
class QueryDataCommand(BaseCommand):
    """
    Command to query internal entity and facet data.

    Supports:
    - Entity type filtering
    - Facet value retrieval (regular and history)
    - Time range filtering for history facets
    - AI-powered visualization selection

    Example Command:
        {
            "operation": "query_data",
            "query_config": {
                "entity_type": "fussballverein",
                "facet_types": ["tabellen-punkte", "tabellen-position"],
                "filters": {
                    "tags": ["bundesliga-1"]
                },
                "time_range": {
                    "latest_only": true
                },
                "sort_by": "tabellen-position",
                "sort_order": "asc",
                "limit": 18
            },
            "visualization_hint": "table",
            "user_query": "Zeige mir die Bundesliga-Tabelle"
        }
    """

    operation_name = "query_data"

    async def validate(self) -> str | None:
        """Validate query configuration."""
        config = self.data.get("query_config", {})

        if not config.get("entity_type"):
            return "entity_type ist erforderlich"

        return None

    async def execute(self) -> CommandResult:
        """Execute the query and return results with visualization."""
        config_data = self.data.get("query_config", {})
        user_query = self.data.get("user_query", "")
        visualization_hint = self.data.get("visualization_hint")
        include_external = self.data.get("include_external", False)

        # Build query config
        filters = QueryFilters(
            tags=config_data.get("filters", {}).get("tags", []),
            admin_level_1=config_data.get("filters", {}).get("admin_level_1"),
            country=config_data.get("filters", {}).get("country"),
            core_attributes=config_data.get("filters", {}).get("core_attributes", {}),
            entity_names=config_data.get("filters", {}).get("entity_names", []),
            entity_ids=config_data.get("filters", {}).get("entity_ids", []),
        )

        time_range = None
        if config_data.get("time_range"):
            tr = config_data["time_range"]
            time_range = TimeRangeConfig(
                from_date=tr.get("from"),
                to_date=tr.get("to"),
                latest_only=tr.get("latest_only", False),
            )

        config = QueryDataConfig(
            entity_type=config_data.get("entity_type", ""),
            facet_types=config_data.get("facet_types", []),
            include_core_attributes=config_data.get("include_core_attributes", True),
            filters=filters,
            time_range=time_range,
            sort_by=config_data.get("sort_by"),
            sort_order=config_data.get("sort_order", "asc"),
            limit=config_data.get("limit", 100),
            offset=config_data.get("offset", 0),
        )

        # Execute query
        query_service = DataQueryService(self.session)
        response = await query_service.query_data(config, user_query)

        if not response.success:
            return CommandResult.failure(message=response.error or "Abfrage fehlgeschlagen")

        # Select visualization
        if response.data:
            selector = VisualizationSelector()
            visualization = await selector.select_visualization(
                data=response.data,
                user_query=user_query,
                facet_types=config.facet_types,
                user_hint=visualization_hint,
            )
            response.visualization = visualization

        # If no internal data and include_external is True, try external
        if not response.data and include_external:
            logger.info(
                "No internal data found, attempting external query",
                entity_type=config.entity_type,
            )
            # Could trigger external query here - for now just note it
            response.explanation = "Keine internen Daten gefunden. Externe API-Abfrage nicht konfiguriert."

        # Build result
        return CommandResult.success_result(
            message=f"{response.returned_count} Ergebnisse gefunden",
            data=response.data,
            total_count=response.total_count,
            returned_count=response.returned_count,
            data_source=response.data_source,
            entity_type=response.entity_type,
            visualization=response.visualization.model_dump() if response.visualization else None,
            explanation=response.explanation,
            source_info=response.source_info.model_dump() if response.source_info else None,
            suggested_actions=[a.model_dump() for a in response.suggested_actions],
        )


@default_registry.register("query_external")
class QueryExternalCommand(BaseCommand):
    """
    Command to query external APIs directly.

    This bypasses internal entity storage and fetches data live
    from external APIs based on:
    - Free-text prompt (AI finds appropriate API)
    - Specific API template ID
    - Direct API URL

    Example Command:
        {
            "operation": "query_external",
            "query_config": {
                "prompt": "Aktuelle Bundesliga Tabelle",
                "save_to_entities": false
            },
            "visualization_hint": null,
            "user_query": "Zeige mir die aktuelle Bundesliga-Tabelle live"
        }
    """

    operation_name = "query_external"

    async def validate(self) -> str | None:
        """Validate external query configuration."""
        config = self.data.get("query_config", {})

        # Need at least one of: prompt, api_configuration_id, or api_url
        if not any(
            [
                config.get("prompt"),
                config.get("api_configuration_id"),
                config.get("api_url"),
            ]
        ):
            return "Mindestens prompt, api_configuration_id oder api_url ist erforderlich"

        return None

    async def execute(self) -> CommandResult:
        """Execute external API query."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from app.models.api_configuration import APIConfiguration

        config_data = self.data.get("query_config", {})
        user_query = self.data.get("user_query", config_data.get("prompt", ""))
        visualization_hint = self.data.get("visualization_hint")

        # Determine which API to use
        api_url = config_data.get("api_url")
        api_configuration_id = config_data.get("api_configuration_id")
        prompt = config_data.get("prompt")

        api_config = None
        api_name = "Externe API"

        # Option 1: Direct URL
        if api_url:
            api_name = api_url.split("/")[2] if "/" in api_url else "Externe API"

        # Option 2: Configuration ID
        elif api_configuration_id:
            result = await self.session.execute(
                select(APIConfiguration)
                .options(selectinload(APIConfiguration.data_source))
                .where(APIConfiguration.id == UUID(api_configuration_id))
            )
            api_config = result.scalar_one_or_none()
            if not api_config:
                return CommandResult.failure(message=f"API-Konfiguration '{api_configuration_id}' nicht gefunden")
            api_url = api_config.get_full_url()
            api_name = api_config.data_source.name if api_config.data_source else f"API {str(api_config.id)[:8]}"

        # Option 3: Search by prompt
        elif prompt:
            # Find matching configuration by keywords
            result = await self.session.execute(
                select(APIConfiguration)
                .options(selectinload(APIConfiguration.data_source))
                .where(
                    APIConfiguration.is_active,
                    APIConfiguration.is_template,
                )
            )
            configs = result.scalars().all()

            for cfg in configs:
                if cfg.matches_prompt(prompt):
                    api_config = cfg
                    api_url = cfg.get_full_url()
                    api_name = cfg.data_source.name if cfg.data_source else f"API {str(cfg.id)[:8]}"
                    break

            if not api_url:
                # Use AI Source Discovery service
                try:
                    from services.ai_source_discovery import AISourceDiscoveryService

                    # Get user's search API credentials
                    serpapi_key = None
                    serper_key = None

                    if self.current_user_id:
                        from services.credentials_resolver import get_serpapi_key, get_serper_key

                        serpapi_key = await get_serpapi_key(self.session, self.current_user_id)
                        serper_key = await get_serper_key(self.session, self.current_user_id)

                    discovery_service = AISourceDiscoveryService(
                        session=self.session,
                        serpapi_key=serpapi_key,
                        serper_key=serper_key,
                    )
                    discovery_result = await discovery_service.discover_sources(
                        prompt=prompt,
                        max_results=5,
                        search_depth="quick",
                    )

                    api_sources = discovery_result.get("api_sources", [])
                    if api_sources:
                        api_url = api_sources[0].get("url")
                        api_name = api_sources[0].get("name", "Entdeckte API")
                    else:
                        return CommandResult.failure(
                            message="Keine passende API für diese Anfrage gefunden. "
                            "Versuche es mit query_data für interne Daten."
                        )
                except ImportError:
                    return CommandResult.failure(message="AI Source Discovery nicht verfügbar")

        # Fetch data from API
        try:
            from ..api_fetcher import RESTAPIClient

            client = RESTAPIClient()
            api_data = await client.fetch(api_url)

            if not api_data:
                return CommandResult.failure(message=f"Keine Daten von {api_name} erhalten")

            # Ensure it's a list
            if isinstance(api_data, dict):
                # Check if it has a data/items key
                for key in ["data", "items", "results", "records"]:
                    if key in api_data and isinstance(api_data[key], list):
                        api_data = api_data[key]
                        break
                else:
                    api_data = [api_data]

            # Select visualization
            selector = VisualizationSelector()
            visualization = await selector.select_visualization(
                data=api_data,
                user_query=user_query,
                user_hint=visualization_hint,
            )

            # Build response
            return CommandResult.success_result(
                message=f"{len(api_data)} Ergebnisse von {api_name}",
                data=api_data,
                raw_data=api_data,
                total_count=len(api_data),
                data_source="external_api",
                api_name=api_name,
                api_url=api_url,
                template_id=None,  # External API, no template
                visualization=visualization.model_dump() if visualization else None,
                explanation=f"Live-Daten von {api_name}",
                source_info={
                    "type": "live_api",
                    "api_name": api_name,
                    "api_url": api_url,
                },
                suggested_actions=[
                    {
                        "label": "In Entities speichern",
                        "action": "save_to_entities",
                        "icon": "mdi-content-save",
                        "params": {
                            "api_url": api_url,
                            "data": api_data[:5],  # Sample
                        },
                    },
                    {
                        "label": "Automatisch tracken",
                        "action": "setup_api_sync",
                        "icon": "mdi-sync",
                        "params": {
                            "api_url": api_url,
                            "api_name": api_name,
                        },
                    },
                ],
            )

        except Exception as e:
            logger.error(
                "External API query failed",
                api_url=api_url,
                error=str(e),
            )
            return CommandResult.failure(message=f"API-Abfrage fehlgeschlagen: {str(e)}")


@default_registry.register("query_facet_history")
class QueryFacetHistoryCommand(BaseCommand):
    """
    Command to query facet history (time-series) data.

    Specialized command for querying FacetValueHistory data
    with time range filtering and aggregation options.

    Example Command:
        {
            "operation": "query_facet_history",
            "query_config": {
                "entity_type": "fussballverein",
                "facet_type": "tabellen-punkte",
                "entity_names": ["FC Bayern München", "Borussia Dortmund"],
                "from_date": "2024-01-01",
                "to_date": "2024-12-31"
            },
            "visualization_hint": "line_chart"
        }
    """

    operation_name = "query_facet_history"

    async def validate(self) -> str | None:
        """Validate history query configuration."""
        config = self.data.get("query_config", {})

        if not config.get("entity_type"):
            return "entity_type ist erforderlich"

        if not config.get("facet_type"):
            return "facet_type ist erforderlich"

        return None

    async def execute(self) -> CommandResult:
        """Execute facet history query."""
        from datetime import datetime

        config_data = self.data.get("query_config", {})
        user_query = self.data.get("user_query", "")
        visualization_hint = self.data.get("visualization_hint")

        entity_type = config_data.get("entity_type")
        facet_type = config_data.get("facet_type")
        entity_names = config_data.get("entity_names", [])
        entity_ids = config_data.get("entity_ids", [])

        # Parse dates
        from_date = None
        to_date = None
        if config_data.get("from_date"):
            from_date = datetime.fromisoformat(config_data["from_date"])
        if config_data.get("to_date"):
            to_date = datetime.fromisoformat(config_data["to_date"])

        # Convert entity_ids to UUIDs if provided
        uuid_ids = None
        if entity_ids:
            uuid_ids = [UUID(eid) for eid in entity_ids]

        # Execute history query
        query_service = DataQueryService(self.session)
        result = await query_service.query_facet_history(
            entity_type_slug=entity_type,
            facet_type_slug=facet_type,
            entity_ids=uuid_ids,
            entity_names=entity_names if entity_names else None,
            from_date=from_date,
            to_date=to_date,
        )

        if "error" in result:
            return CommandResult.failure(message=result["error"])

        data = result.get("data", [])

        # Flatten data for visualization
        flat_data = []
        for entity_data in data:
            for point in entity_data.get("history", []):
                flat_data.append(
                    {
                        "entity_name": entity_data["entity_name"],
                        "entity_id": entity_data["entity_id"],
                        **point,
                    }
                )

        # Select visualization
        if flat_data:
            selector = VisualizationSelector()
            visualization = await selector.select_visualization(
                data=flat_data,
                user_query=user_query or f"Verlauf von {facet_type}",
                facet_types=[facet_type],
                user_hint=visualization_hint or "line_chart",
            )
        else:
            visualization = None

        return CommandResult.success_result(
            message=f"History für {len(data)} Entities abgerufen",
            data=data,
            flat_data=flat_data,
            total_entities=result.get("total_entities", 0),
            facet_type=facet_type,
            entity_type=entity_type,
            data_source="facet_history",
            visualization=visualization.model_dump() if visualization else None,
            source_info={
                "type": "facet_history",
            },
        )
