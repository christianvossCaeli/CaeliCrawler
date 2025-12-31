"""API Import Fetcher Service.

Handles fetching data from various external APIs:
- Wikidata SPARQL
- OParl (German council information systems)
- Custom REST APIs
"""

from typing import Any
from urllib.parse import urlparse

import httpx
import structlog

logger = structlog.get_logger()

# Default timeout for API requests
DEFAULT_TIMEOUT = 30.0


async def fetch_api_preview(
    api_type: str,
    api_url: str,
    params: dict[str, Any],
    sample_size: int = 10,
) -> tuple[list[dict[str, Any]], int, dict[str, str], list[str]]:
    """
    Fetch a preview of data from an external API.

    Args:
        api_type: Type of API (wikidata, oparl, custom)
        api_url: API endpoint URL
        params: API-specific parameters
        sample_size: Number of items to return in preview

    Returns:
        Tuple of (items, total_available, field_mapping, suggested_tags)
    """
    if api_type == "wikidata":
        return await _fetch_wikidata_preview(api_url, params, sample_size)
    elif api_type == "oparl":
        return await _fetch_oparl_preview(api_url, params, sample_size)
    elif api_type == "custom":
        return await _fetch_custom_preview(api_url, params, sample_size)
    else:
        raise ValueError(f"Unknown API type: {api_type}")


async def fetch_all_from_api(
    api_type: str,
    api_url: str,
    params: dict[str, Any],
    field_mapping: dict[str, str],
    max_items: int = 1000,
) -> list[dict[str, Any]]:
    """
    Fetch all data from an external API.

    Args:
        api_type: Type of API (wikidata, oparl, custom)
        api_url: API endpoint URL
        params: API-specific parameters
        field_mapping: Mapping from API fields to DataSource fields
        max_items: Maximum number of items to fetch

    Returns:
        List of items with standardized field names
    """
    if api_type == "wikidata":
        return await _fetch_all_wikidata(api_url, params, field_mapping, max_items)
    elif api_type == "oparl":
        return await _fetch_all_oparl(api_url, params, field_mapping, max_items)
    elif api_type == "custom":
        return await _fetch_all_custom(api_url, params, field_mapping, max_items)
    else:
        raise ValueError(f"Unknown API type: {api_type}")


# =============================================================================
# Wikidata SPARQL
# =============================================================================

async def _fetch_wikidata_preview(
    api_url: str,
    params: dict[str, Any],
    sample_size: int,
) -> tuple[list[dict[str, Any]], int, dict[str, str], list[str]]:
    """Fetch preview from Wikidata SPARQL endpoint."""
    sparql_query = params.get("sparql_query", "")
    if not sparql_query:
        raise ValueError("sparql_query parameter is required for Wikidata")

    # Add LIMIT to query for preview
    preview_query = sparql_query.strip()
    # Remove existing LIMIT if present and add our own
    import re
    preview_query = re.sub(r'\s+LIMIT\s+\d+\s*$', '', preview_query, flags=re.IGNORECASE)
    preview_query = f"{preview_query} LIMIT {sample_size}"

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        response = await client.get(
            api_url,
            params={"query": preview_query, "format": "json"},
            headers={"Accept": "application/sparql-results+json"},
        )
        response.raise_for_status()
        data = response.json()

    results = data.get("results", {}).get("bindings", [])

    # Parse results
    items = []
    for row in results:
        item = {
            "name": row.get("itemLabel", {}).get("value", ""),
            "base_url": row.get("website", {}).get("value", ""),
            "source_type": "WEBSITE",
            "suggested_tags": [],
            "extra_data": {
                "wikidata_id": row.get("item", {}).get("value", "").split("/")[-1],
            },
        }
        if item["base_url"]:
            items.append(item)

    # Estimate total (run count query)
    count_query = sparql_query.strip()
    count_query = re.sub(r'\s+LIMIT\s+\d+\s*$', '', count_query, flags=re.IGNORECASE)
    count_query = f"SELECT (COUNT(*) as ?count) WHERE {{ {count_query.replace('SELECT', '').split('WHERE')[0]} }}"

    total = len(items)  # Default to sample size if count fails
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            count_response = await client.get(
                api_url,
                params={"query": count_query, "format": "json"},
                headers={"Accept": "application/sparql-results+json"},
            )
            if count_response.status_code == 200:
                count_data = count_response.json()
                count_results = count_data.get("results", {}).get("bindings", [])
                if count_results:
                    total = int(count_results[0].get("count", {}).get("value", total))
    except Exception as e:
        logger.warning("Failed to get count from Wikidata", error=str(e))

    field_mapping = {
        "itemLabel": "name",
        "website": "base_url",
        "item": "wikidata_id",
    }

    return items, total, field_mapping, ["wikidata"]


async def _fetch_all_wikidata(
    api_url: str,
    params: dict[str, Any],
    field_mapping: dict[str, str],
    max_items: int,
) -> list[dict[str, Any]]:
    """Fetch all results from Wikidata SPARQL endpoint."""
    sparql_query = params.get("sparql_query", "")
    if not sparql_query:
        raise ValueError("sparql_query parameter is required for Wikidata")

    # Update LIMIT in query
    import re
    full_query = re.sub(r'\s+LIMIT\s+\d+\s*$', '', sparql_query.strip(), flags=re.IGNORECASE)
    full_query = f"{full_query} LIMIT {max_items}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            api_url,
            params={"query": full_query, "format": "json"},
            headers={"Accept": "application/sparql-results+json"},
        )
        response.raise_for_status()
        data = response.json()

    results = data.get("results", {}).get("bindings", [])

    items = []
    for row in results:
        website = row.get("website", {}).get("value", "")
        if not website:
            continue

        item = {
            "name": row.get("itemLabel", {}).get("value", ""),
            "base_url": website,
            "source_type": "WEBSITE",
            "extra_data": {
                "wikidata_id": row.get("item", {}).get("value", "").split("/")[-1],
            },
        }
        items.append(item)

    return items


# =============================================================================
# OParl API
# =============================================================================

async def _fetch_oparl_preview(
    api_url: str,
    params: dict[str, Any],
    sample_size: int,
) -> tuple[list[dict[str, Any]], int, dict[str, str], list[str]]:
    """Fetch preview from OParl API."""
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        response = await client.get(api_url)
        response.raise_for_status()
        data = response.json()

    # OParl returns a list of systems/bodies
    bodies = data if isinstance(data, list) else data.get("data", [])

    items = []
    for body in bodies[:sample_size]:
        # OParl body has: id, name, website, system (URL)
        website = body.get("website") or body.get("system")
        if not website:
            continue

        item = {
            "name": body.get("name", body.get("shortName", "")),
            "base_url": website,
            "source_type": "OPARL_API",
            "suggested_tags": ["oparl"],
            "extra_data": {
                "oparl_id": body.get("id", ""),
                "oparl_system": body.get("system", ""),
            },
        }
        items.append(item)

    total = len(bodies) if isinstance(bodies, list) else len(items)

    field_mapping = {
        "name": "name",
        "website": "base_url",
        "system": "api_endpoint",
    }

    return items, total, field_mapping, ["de", "oparl", "ratsinformation"]


async def _fetch_all_oparl(
    api_url: str,
    params: dict[str, Any],
    field_mapping: dict[str, str],
    max_items: int,
) -> list[dict[str, Any]]:
    """Fetch all bodies from OParl API."""
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        response = await client.get(api_url)
        response.raise_for_status()
        data = response.json()

    bodies = data if isinstance(data, list) else data.get("data", [])

    items = []
    for body in bodies[:max_items]:
        website = body.get("website") or body.get("system")
        if not website:
            continue

        item = {
            "name": body.get("name", body.get("shortName", "")),
            "base_url": website,
            "source_type": "OPARL_API",
            "extra_data": {
                "oparl_id": body.get("id", ""),
                "oparl_system": body.get("system", ""),
            },
        }
        items.append(item)

    return items


# =============================================================================
# Custom REST API
# =============================================================================

async def _fetch_custom_preview(
    api_url: str,
    params: dict[str, Any],
    sample_size: int,
) -> tuple[list[dict[str, Any]], int, dict[str, str], list[str]]:
    """Fetch preview from a custom REST API."""
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        response = await client.get(api_url, params=params.get("query_params", {}))
        response.raise_for_status()
        data = response.json()

    # Try to find the data array
    items_data = data
    if isinstance(data, dict):
        # Try common keys for the data array
        for key in ["data", "items", "results", "records", "entries"]:
            if key in data and isinstance(data[key], list):
                items_data = data[key]
                break

    if not isinstance(items_data, list):
        raise ValueError("Could not find data array in API response")

    # Get field mapping from params or auto-detect
    name_field = params.get("name_field", "name")
    url_field = params.get("url_field", "url")

    items = []
    for record in items_data[:sample_size]:
        if not isinstance(record, dict):
            continue

        name = record.get(name_field, "")
        url = record.get(url_field, "")

        if not url:
            # Try to find any URL-like field
            for _key, value in record.items():
                if isinstance(value, str) and value.startswith("http"):
                    url = value
                    break

        if url:
            item = {
                "name": name or urlparse(url).netloc,
                "base_url": url,
                "source_type": "WEBSITE",
                "suggested_tags": [],
                "extra_data": record,
            }
            items.append(item)

    total = len(items_data) if isinstance(items_data, list) else len(items)

    # Auto-detect field mapping
    field_mapping = {
        name_field: "name",
        url_field: "base_url",
    }

    return items, total, field_mapping, []


async def _fetch_all_custom(
    api_url: str,
    params: dict[str, Any],
    field_mapping: dict[str, str],
    max_items: int,
) -> list[dict[str, Any]]:
    """Fetch all data from a custom REST API."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(api_url, params=params.get("query_params", {}))
        response.raise_for_status()
        data = response.json()

    # Try to find the data array
    items_data = data
    if isinstance(data, dict):
        for key in ["data", "items", "results", "records", "entries"]:
            if key in data and isinstance(data[key], list):
                items_data = data[key]
                break

    if not isinstance(items_data, list):
        raise ValueError("Could not find data array in API response")

    # Get field mapping
    name_field = field_mapping.get("name", "name")
    url_field = field_mapping.get("url", "url")

    # Reverse the field mapping to get API field names
    reverse_mapping = {v: k for k, v in field_mapping.items()}
    api_name_field = reverse_mapping.get("name", name_field)
    api_url_field = reverse_mapping.get("base_url", url_field)

    items = []
    for record in items_data[:max_items]:
        if not isinstance(record, dict):
            continue

        name = record.get(api_name_field, "")
        url = record.get(api_url_field, "")

        if url:
            item = {
                "name": name or urlparse(url).netloc,
                "base_url": url,
                "source_type": "WEBSITE",
                "extra_data": record,
            }
            items.append(item)

    return items
