"""External API fetcher for Smart Query Service.

Supports fetching data from external APIs like Wikidata SPARQL
and REST APIs (e.g., Caeli Auction API) to create entities in bulk.
"""

from __future__ import annotations

import asyncio
import base64
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

# Wikidata SPARQL endpoint
WIKIDATA_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

# Default timeout for API requests (in seconds)
DEFAULT_TIMEOUT = 120  # Erhöht für große Queries

# Rate limiting: wait between requests (in seconds)
RATE_LIMIT_DELAY = 2.0  # Erhöht um Wikidata nicht zu überlasten

# Default page size for pagination
DEFAULT_PAGE_SIZE = 500  # Reduziert für stabilere Requests


# ============================================================================
# Data classes (defined before classes that use them)
# ============================================================================


@dataclass
class FetchResult:
    """Result of an API fetch operation."""

    success: bool
    items: list[dict[str, Any]] = field(default_factory=list)
    total_count: int = 0
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class WikidataResult:
    """A single result from a Wikidata SPARQL query."""

    id: str
    label: str
    data: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# REST API Client for external REST APIs (like Caeli Auction)
# ============================================================================


class RESTAPIClient:
    """Client for fetching data from REST APIs with various auth methods."""

    def __init__(
        self,
        base_url: str,
        timeout: int = DEFAULT_TIMEOUT,
        auth_config: dict[str, Any] | None = None,
    ):
        """Initialize REST API client.

        Args:
            base_url: Base URL of the API
            timeout: Request timeout in seconds
            auth_config: Authentication configuration:
                - type: "basic", "bearer", "header", or None
                - For basic: { "type": "basic", "credentials": "base64_encoded" }
                         or { "type": "basic", "username": "...", "password": "..." }
                         or { "type": "basic", "env_var": "CAELI_AUCTION_MARKETPLACE_API_AUTH" }
                - For bearer: { "type": "bearer", "token": "..." }
                - For header: { "type": "header", "name": "X-Api-Key", "value": "..." }
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.auth_config = auth_config or {}
        self._client: httpx.AsyncClient | None = None

    def _build_headers(self) -> dict[str, str]:
        """Build request headers including authentication."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "CaeliCrawler/1.0 (https://caeli-wind.de)",
        }

        auth_type = self.auth_config.get("type")

        if auth_type == "basic":
            # Get credentials from various sources
            credentials = self.auth_config.get("credentials")

            if not credentials and self.auth_config.get("env_var"):
                # Load from environment variable
                credentials = os.environ.get(self.auth_config["env_var"], "")

            if not credentials and self.auth_config.get("username"):
                # Build from username/password
                username = self.auth_config.get("username", "")
                password = self.auth_config.get("password", "")
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()

            if credentials:
                headers["Authorization"] = f"Basic {credentials}"

        elif auth_type == "bearer":
            token = self.auth_config.get("token")
            if not token and self.auth_config.get("env_var"):
                token = os.environ.get(self.auth_config["env_var"], "")
            if token:
                headers["Authorization"] = f"Bearer {token}"

        elif auth_type == "header":
            header_name = self.auth_config.get("name", "X-Api-Key")
            header_value = self.auth_config.get("value")
            if not header_value and self.auth_config.get("env_var"):
                header_value = os.environ.get(self.auth_config["env_var"], "")
            if header_value:
                headers[header_name] = header_value

        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers=self._build_headers(),
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def fetch(
        self,
        endpoint: str = "",
        params: dict[str, Any] | None = None,
        method: str = "GET",
    ) -> FetchResult:
        """Fetch data from a REST API endpoint.

        Args:
            endpoint: API endpoint path (appended to base_url)
            params: Query parameters
            method: HTTP method

        Returns:
            FetchResult with items from the API
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}" if endpoint else self.base_url

        try:
            client = await self._get_client()

            if method.upper() == "GET":
                response = await client.get(url, params=params)
            elif method.upper() == "POST":
                response = await client.post(url, json=params)
            else:
                return FetchResult(
                    success=False,
                    error=f"Unsupported HTTP method: {method}",
                )

            response.raise_for_status()

            data = response.json()

            # Handle different response formats
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # Check common response wrapper keys
                for key in ["data", "items", "results", "records", "auctions", "entries"]:
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        break
                else:
                    # Single object response - wrap in list
                    items = [data]

            logger.info(
                "REST API fetch successful",
                url=url,
                items_count=len(items),
            )

            return FetchResult(
                success=True,
                items=items,
                total_count=len(items),
            )

        except httpx.TimeoutException:
            logger.error("REST API request timed out", url=url)
            return FetchResult(
                success=False,
                error="Request timed out",
            )
        except httpx.HTTPStatusError as e:
            logger.error("REST API HTTP error", url=url, status=e.response.status_code)
            return FetchResult(
                success=False,
                error=f"HTTP error: {e.response.status_code}",
            )
        except Exception as e:
            logger.error("REST API request failed", url=url, error=str(e))
            return FetchResult(
                success=False,
                error=str(e),
            )


class WikidataSPARQLClient:
    """Client for fetching data from Wikidata SPARQL endpoint."""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.endpoint = WIKIDATA_SPARQL_ENDPOINT
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "User-Agent": "CaeliCrawler/1.0 (https://caeli-wind.de; contact@caeli-wind.de)",
                    "Accept": "application/sparql-results+json",
                },
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def execute_query(
        self,
        query: str,
        limit: int = 1000,
        offset: int = 0,
    ) -> FetchResult:
        """Execute a SPARQL query against Wikidata.

        Args:
            query: SPARQL query string
            limit: Maximum results per request
            offset: Offset for pagination

        Returns:
            FetchResult with items from the query
        """
        # Add LIMIT and OFFSET if not in query
        if "LIMIT" not in query.upper():
            query = f"{query}\nLIMIT {limit}"
        if "OFFSET" not in query.upper() and offset > 0:
            query = f"{query}\nOFFSET {offset}"

        try:
            client = await self._get_client()
            response = await client.get(
                self.endpoint,
                params={"query": query, "format": "json"},
            )
            response.raise_for_status()

            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])

            items = []
            for binding in bindings:
                item = {}
                for key, value_data in binding.items():
                    # Extract the value from Wikidata's binding format
                    value = value_data.get("value", "")
                    value_type = value_data.get("type", "literal")

                    # Clean up URIs to extract IDs
                    if value_type == "uri" and "wikidata.org" in value:  # noqa: SIM102
                        # Extract Q-number from URI
                        if "/entity/" in value:
                            value = value.split("/entity/")[-1]

                    item[key] = value

                items.append(item)

            logger.info(
                "Wikidata query executed",
                result_count=len(items),
                offset=offset,
            )

            return FetchResult(
                success=True,
                items=items,
                total_count=len(items),
            )

        except httpx.TimeoutException:
            logger.error("Wikidata query timed out")
            return FetchResult(
                success=False,
                error="Query timed out. Try a smaller result set or simpler query.",
            )
        except httpx.HTTPStatusError as e:
            logger.error("Wikidata HTTP error", status=e.response.status_code)
            return FetchResult(
                success=False,
                error=f"HTTP error: {e.response.status_code}",
            )
        except Exception as e:
            logger.error("Wikidata query failed", error=str(e))
            return FetchResult(
                success=False,
                error=str(e),
            )

    async def fetch_all_paginated(
        self,
        query: str,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_results: int | None = None,
        progress_callback: Callable | None = None,
    ) -> FetchResult:
        """Fetch all results from a query using pagination.

        Args:
            query: SPARQL query string (without LIMIT/OFFSET)
            page_size: Number of results per page
            max_results: Maximum total results (None for unlimited)
            progress_callback: Optional callback for progress updates

        Returns:
            FetchResult with all items
        """
        all_items = []
        offset = 0
        warnings = []

        while True:
            # Check max results
            if max_results and len(all_items) >= max_results:
                warnings.append(f"Stopped at max_results limit: {max_results}")
                break

            result = await self.execute_query(query, limit=page_size, offset=offset)

            if not result.success:
                if all_items:
                    # Partial success
                    warnings.append(f"Fetch stopped at offset {offset}: {result.error}")
                    break
                return result

            all_items.extend(result.items)

            if progress_callback:
                await progress_callback(len(all_items), offset)

            # Check if we got fewer results than page_size (last page)
            if len(result.items) < page_size:
                break

            offset += page_size

            # Rate limiting
            await asyncio.sleep(RATE_LIMIT_DELAY)

        logger.info(
            "Wikidata paginated fetch complete",
            total_items=len(all_items),
            pages_fetched=offset // page_size + 1,
        )

        return FetchResult(
            success=True,
            items=all_items,
            total_count=len(all_items),
            warnings=warnings,
        )


# Predefined SPARQL queries for common use cases

GERMAN_MUNICIPALITIES_QUERY = """
SELECT DISTINCT
    ?gemeinde
    ?gemeindeLabel
    ?ags
    ?einwohner
    ?flaeche
    ?lat
    ?lon
    ?bundesland
    ?bundeslandLabel
    ?website
WHERE {
    ?gemeinde wdt:P31/wdt:P279* wd:Q262166 .  # Instance of (or subclass): Gemeinde in Deutschland
    ?gemeinde wdt:P439 ?ags .                  # Amtlicher Gemeindeschluessel

    OPTIONAL { ?gemeinde wdt:P1082 ?einwohner . }  # Population
    OPTIONAL { ?gemeinde wdt:P2046 ?flaeche . }    # Area
    OPTIONAL { ?gemeinde wdt:P856 ?website . }     # Official website
    OPTIONAL {
        ?gemeinde wdt:P625 ?coords .
        BIND(geof:latitude(?coords) AS ?lat)
        BIND(geof:longitude(?coords) AS ?lon)
    }

    # Get Bundesland through administrative hierarchy
    ?gemeinde wdt:P131+ ?bundesland .
    ?bundesland wdt:P31 wd:Q1221156 .  # Instance of: Bundesland

    SERVICE wikibase:label { bd:serviceParam wikibase:language "de,en" }
}
ORDER BY ?bundeslandLabel ?gemeindeLabel
"""

GERMAN_BUNDESLAENDER_QUERY = """
SELECT DISTINCT
    ?bundesland
    ?bundeslandLabel
    ?einwohner
    ?flaeche
    ?hauptstadt
    ?hauptstadtLabel
    ?lat
    ?lon
    ?website
WHERE {
    ?bundesland wdt:P31 wd:Q1221156 .  # Instance of: Bundesland

    OPTIONAL { ?bundesland wdt:P1082 ?einwohner . }
    OPTIONAL { ?bundesland wdt:P2046 ?flaeche . }
    OPTIONAL { ?bundesland wdt:P36 ?hauptstadt . }
    OPTIONAL { ?bundesland wdt:P856 ?website . }  # Official website
    OPTIONAL {
        ?bundesland wdt:P625 ?coords .
        BIND(geof:latitude(?coords) AS ?lat)
        BIND(geof:longitude(?coords) AS ?lon)
    }

    SERVICE wikibase:label { bd:serviceParam wikibase:language "de,en" }
}
ORDER BY ?bundeslandLabel
"""

UK_COUNCILS_QUERY = """
SELECT DISTINCT
    ?council
    ?councilLabel
    ?gss_code
    ?einwohner
    ?lat
    ?lon
    ?region
    ?regionLabel
    ?website
WHERE {
    # UK local authorities (councils)
    VALUES ?councilType {
        wd:Q21451686   # civil parish
        wd:Q1136601    # unitary authority
        wd:Q769683     # London borough
        wd:Q1003712    # metropolitan borough
        wd:Q180673     # non-metropolitan district
    }
    ?council wdt:P31 ?councilType .
    ?council wdt:P17 wd:Q145 .  # Country: UK

    OPTIONAL { ?council wdt:P836 ?gss_code . }  # GSS code
    OPTIONAL { ?council wdt:P1082 ?einwohner . }
    OPTIONAL { ?council wdt:P856 ?website . }   # Official website
    OPTIONAL {
        ?council wdt:P625 ?coords .
        BIND(geof:latitude(?coords) AS ?lat)
        BIND(geof:longitude(?coords) AS ?lon)
    }
    OPTIONAL { ?council wdt:P131 ?region . }

    SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}
ORDER BY ?regionLabel ?councilLabel
"""

AUSTRIA_GEMEINDEN_QUERY = """
SELECT DISTINCT
    ?gemeinde
    ?gemeindeLabel
    ?gkz
    ?einwohner
    ?flaeche
    ?lat
    ?lon
    ?bundesland
    ?bundeslandLabel
    ?website
WHERE {
    ?gemeinde wdt:P31 wd:Q667509 .  # Instance of: Gemeinde Oesterreichs

    OPTIONAL { ?gemeinde wdt:P964 ?gkz . }        # Gemeindekennzahl
    OPTIONAL { ?gemeinde wdt:P1082 ?einwohner . }
    OPTIONAL { ?gemeinde wdt:P2046 ?flaeche . }
    OPTIONAL { ?gemeinde wdt:P856 ?website . }    # Official website
    OPTIONAL {
        ?gemeinde wdt:P625 ?coords .
        BIND(geof:latitude(?coords) AS ?lat)
        BIND(geof:longitude(?coords) AS ?lon)
    }

    # Get Bundesland
    ?gemeinde wdt:P131+ ?bundesland .
    ?bundesland wdt:P31 wd:Q261543 .  # Instance of: Bundesland Oesterreichs

    SERVICE wikibase:label { bd:serviceParam wikibase:language "de,en" }
}
ORDER BY ?bundeslandLabel ?gemeindeLabel
"""

AUSTRIA_BUNDESLAENDER_QUERY = """
SELECT DISTINCT
    ?bundesland
    ?bundeslandLabel
    ?iso_code
    ?einwohner
    ?flaeche
    ?lat
    ?lon
    ?website
    ?hauptstadt
    ?hauptstadtLabel
WHERE {
    ?bundesland wdt:P31 wd:Q261543 .  # Instance of: Bundesland Österreichs

    OPTIONAL { ?bundesland wdt:P300 ?iso_code . }    # ISO 3166-2 code
    OPTIONAL { ?bundesland wdt:P1082 ?einwohner . }
    OPTIONAL { ?bundesland wdt:P2046 ?flaeche . }
    OPTIONAL { ?bundesland wdt:P856 ?website . }     # Official website
    OPTIONAL { ?bundesland wdt:P36 ?hauptstadt . }   # Capital
    OPTIONAL {
        ?bundesland wdt:P625 ?coords .
        BIND(geof:latitude(?coords) AS ?lat)
        BIND(geof:longitude(?coords) AS ?lon)
    }

    SERVICE wikibase:label { bd:serviceParam wikibase:language "de,en" }
}
ORDER BY ?bundeslandLabel
"""

UK_REGIONS_QUERY = """
SELECT DISTINCT
    ?region
    ?regionLabel
    ?gss_code
    ?einwohner
    ?flaeche
    ?lat
    ?lon
    ?website
    ?country
    ?countryLabel
WHERE {
    # UK regions and countries
    VALUES ?regionType {
        wd:Q15979307   # ceremonial county of England
        wd:Q1136601    # unitary authority
        wd:Q106652     # constituent country (England, Scotland, Wales, NI)
        wd:Q1349639    # region of England
    }
    ?region wdt:P31 ?regionType .
    ?region wdt:P17 wd:Q145 .  # Country: UK

    OPTIONAL { ?region wdt:P836 ?gss_code . }     # GSS code
    OPTIONAL { ?region wdt:P1082 ?einwohner . }
    OPTIONAL { ?region wdt:P2046 ?flaeche . }
    OPTIONAL { ?region wdt:P856 ?website . }      # Official website
    OPTIONAL { ?region wdt:P131 ?country . }
    OPTIONAL {
        ?region wdt:P625 ?coords .
        BIND(geof:latitude(?coords) AS ?lat)
        BIND(geof:longitude(?coords) AS ?lon)
    }

    SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}
ORDER BY ?countryLabel ?regionLabel
"""


def get_predefined_query(query_type: str, country: str = "DE") -> str | None:
    """Get a predefined SPARQL query for common entity types.

    Args:
        query_type: Type of entities to query (gemeinden, bundeslaender, councils)
        country: Country code (DE, GB, AT)

    Returns:
        SPARQL query string or None if not found
    """
    queries = {
        # Deutschland
        ("gemeinden", "DE"): GERMAN_MUNICIPALITIES_QUERY,
        ("municipalities", "DE"): GERMAN_MUNICIPALITIES_QUERY,
        ("bundeslaender", "DE"): GERMAN_BUNDESLAENDER_QUERY,
        ("states", "DE"): GERMAN_BUNDESLAENDER_QUERY,
        # UK
        ("councils", "GB"): UK_COUNCILS_QUERY,
        ("parishes", "GB"): UK_COUNCILS_QUERY,
        ("local_authorities", "GB"): UK_COUNCILS_QUERY,
        ("local-authorities", "GB"): UK_COUNCILS_QUERY,
        ("uk-local-authority", "GB"): UK_COUNCILS_QUERY,
        ("uk-local-authorities", "GB"): UK_COUNCILS_QUERY,
        ("uk_local_authority", "GB"): UK_COUNCILS_QUERY,
        ("uk_local_authorities", "GB"): UK_COUNCILS_QUERY,
        ("municipalities", "GB"): UK_COUNCILS_QUERY,
        ("regions", "GB"): UK_REGIONS_QUERY,
        ("counties", "GB"): UK_REGIONS_QUERY,
        # Österreich
        ("gemeinden", "AT"): AUSTRIA_GEMEINDEN_QUERY,
        ("municipalities", "AT"): AUSTRIA_GEMEINDEN_QUERY,
        ("bundeslaender", "AT"): AUSTRIA_BUNDESLAENDER_QUERY,
        ("states", "AT"): AUSTRIA_BUNDESLAENDER_QUERY,
    }

    return queries.get((query_type.lower(), country.upper()))


class ExternalAPIFetcher:
    """Unified external API fetcher supporting multiple API types."""

    def __init__(self):
        self.wikidata_client = WikidataSPARQLClient()
        self._rest_clients: dict[str, RESTAPIClient] = {}

    async def close(self):
        """Close all clients."""
        await self.wikidata_client.close()
        for client in self._rest_clients.values():
            await client.close()
        self._rest_clients.clear()

    def _get_rest_client(
        self,
        base_url: str,
        auth_config: dict[str, Any] | None = None,
    ) -> RESTAPIClient:
        """Get or create a REST API client."""
        cache_key = f"{base_url}:{hash(str(auth_config))}"
        if cache_key not in self._rest_clients:
            self._rest_clients[cache_key] = RESTAPIClient(
                base_url=base_url,
                auth_config=auth_config,
            )
        return self._rest_clients[cache_key]

    async def fetch(
        self,
        api_config: dict[str, Any],
        progress_callback: Callable | None = None,
    ) -> FetchResult:
        """Fetch data from an external API.

        Args:
            api_config: Configuration dict with:
                - type: API type (sparql, rest, etc.)
                - base_url: Base URL for REST APIs
                - endpoint: API endpoint path
                - query: Query string or predefined query name (for SPARQL)
                - auth_config: Authentication configuration (for REST)
                - pagination: Pagination config
                - country: Country filter for predefined queries
                - template: Predefined template name (e.g., "caeli_auction_windparks")
            progress_callback: Optional callback for progress updates

        Returns:
            FetchResult with fetched items
        """
        api_type = api_config.get("type", "sparql")
        template = api_config.get("template", "")

        # Check for predefined REST templates
        if template:
            predefined = get_predefined_rest_template(template)
            if predefined:
                # Merge predefined config with provided config (user config takes precedence)
                merged_config = {**predefined, **api_config}
                api_type = merged_config.get("type", "rest")
                api_config = merged_config
            else:
                return FetchResult(
                    success=False,
                    error=f"Unknown API template: {template}",
                )

        if api_type == "sparql":
            query = api_config.get("query", "")
            country = api_config.get("country", "DE")
            pagination = api_config.get("pagination", {})
            page_size = pagination.get("limit", DEFAULT_PAGE_SIZE)
            max_results = pagination.get("max_results")

            # Check for predefined query
            if not query.strip().upper().startswith("SELECT"):
                predefined = get_predefined_query(query, country)
                if predefined:
                    query = predefined
                else:
                    return FetchResult(
                        success=False,
                        error=f"Unknown predefined query: {query}",
                    )

            return await self.wikidata_client.fetch_all_paginated(
                query=query,
                page_size=page_size,
                max_results=max_results,
                progress_callback=progress_callback,
            )

        elif api_type == "rest":
            base_url = api_config.get("base_url", "")
            endpoint = api_config.get("endpoint", "")
            auth_config = api_config.get("auth_config")
            params = api_config.get("params", {})
            method = api_config.get("method", "GET")

            if not base_url:
                return FetchResult(
                    success=False,
                    error="REST API requires base_url",
                )

            client = self._get_rest_client(base_url, auth_config)
            return await client.fetch(endpoint, params, method)

        else:
            return FetchResult(
                success=False,
                error=f"Unsupported API type: {api_type}",
            )


# ============================================================================
# Predefined REST API Templates
# ============================================================================

# Template configurations for common REST APIs
PREDEFINED_REST_TEMPLATES: dict[str, dict[str, Any]] = {
    # Caeli Auction Windpark API - fetches wind farm auction listings
    "caeli_auction_windparks": {
        "type": "rest",
        "base_url": os.environ.get(
            "CAELI_AUCTION_MARKETPLACE_API_URL",
            "https://auction.caeli-wind.de/api/auction-platform/v4/public-marketplace",
        ),
        "endpoint": "",
        "auth_config": {
            "type": "basic",
            "env_var": "CAELI_AUCTION_MARKETPLACE_API_AUTH",
        },
        "method": "GET",
        "description": "Caeli Auction Windpark-Auktionen",
        "field_mapping": {
            # API field -> Entity field
            "auctionId": "external_id",
            "areaName": "area_name",  # z.B. "Gummersbach Teil I - Aggertalsperre"
            "administrativeDivisionLevel1": "admin_level_1",  # Bundesland
            "power": "leistung_mw",
            "areaSize": "flaeche_ha",
            "fullUsageHours": "volllaststunden",
            "averageWindSpeed": "windgeschwindigkeit_ms",
            "weaCount": "anzahl_wea",
            "weaHubHeight": "nabenhoehe_m",
            "availableFrom": "verfuegbar_ab",
            "status": "status",
            "property": "property",
            "isHighlight": "is_highlight",
            "regionCode": "region_code",
            "customerType": "customer_type",
            "internalRateOfReturnBeforeRent": "rendite_prozent",
        },
        "name_template": "Windpark {areaName}",  # Nutze areaName statt auctionId
        "gemeinde_match_field": "areaName",  # Feld für Gemeinde-Matching
        "keywords": ["windpark", "windparks", "auktion", "auction", "caeli", "wind", "windenergie"],
        "entity_type_config": {
            "name": "Windpark",
            "name_plural": "Windparks",
            "slug": "windpark",
            "description": "Windpark-Auktionen von der Caeli Auction Plattform",
            "icon": "mdi-wind-turbine",
            "color": "#4CAF50",
            "is_primary": False,
            "is_public": True,  # Sichtbar im Frontend
            "supports_hierarchy": False,  # Windparks nutzen Relationen, keine Hierarchie
        },
    },
}


def get_predefined_rest_template(template_name: str) -> dict[str, Any] | None:
    """Get a predefined REST API template configuration.

    Args:
        template_name: Name of the template (e.g., "caeli_auction_windparks")

    Returns:
        Template configuration dict or None if not found
    """
    return PREDEFINED_REST_TEMPLATES.get(template_name.lower())
