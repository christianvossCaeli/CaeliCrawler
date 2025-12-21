"""
API Validator for KI-First Discovery.

Validates API suggestions by making HTTP requests and analyzing responses.
"""

import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx
import structlog

from app.core.retry import API_RETRY_CONFIG, retry_async
from .models import (
    APISuggestion,
    APIValidationResult,
)

logger = structlog.get_logger()

# Timeout settings
VALIDATION_TIMEOUT = 30.0  # seconds
FULL_FETCH_TIMEOUT = 60.0  # seconds

# SSRF Protection - blocked hosts and patterns
BLOCKED_HOSTS = {
    "localhost",
    "127.0.0.1",
    "::1",
    "[::1]",
    "0.0.0.0",
}

BLOCKED_HOST_PATTERNS = [
    "internal",
    "intranet",
    "local",
    "private",
    "corp",
]


def is_safe_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Check if URL is safe (not internal/private).

    Returns:
        Tuple of (is_safe, error_message)
    """
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""

        # Check blocked hosts
        if host.lower() in BLOCKED_HOSTS:
            return False, f"Blocked host: {host}"

        # Check blocked patterns
        for pattern in BLOCKED_HOST_PATTERNS:
            if pattern in host.lower():
                return False, f"Blocked pattern in host: {pattern}"

        # Check private IP ranges
        if host.startswith("10.") or host.startswith("192.168."):
            return False, f"Private IP range: {host}"

        if host.startswith("172."):
            parts = host.split(".")
            if len(parts) >= 2:
                second_octet = int(parts[1])
                if 16 <= second_octet <= 31:
                    return False, f"Private IP range: {host}"

        return True, None

    except Exception as e:
        return False, f"URL parsing error: {str(e)}"


class APIValidator:
    """Validates API suggestions by testing endpoints."""

    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            timeout=VALIDATION_TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": "CaeliCrawler/1.0 (API Validator)",
                "Accept": "application/json, */*",
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def validate_suggestion(
        self,
        suggestion: APISuggestion,
    ) -> APIValidationResult:
        """
        Validate a single API suggestion.

        Args:
            suggestion: The API suggestion to validate

        Returns:
            APIValidationResult with validation details
        """
        start_time = time.time()

        # Safety check
        is_safe, error_msg = is_safe_url(suggestion.full_url)
        if not is_safe:
            return APIValidationResult(
                suggestion=suggestion,
                is_valid=False,
                error_message=f"SSRF Protection: {error_msg}",
                validation_time_ms=int((time.time() - start_time) * 1000),
            )

        # Skip if auth required (we can't test without credentials)
        if suggestion.auth_required:
            return APIValidationResult(
                suggestion=suggestion,
                is_valid=False,
                error_message="API requires authentication",
                validation_time_ms=int((time.time() - start_time) * 1000),
            )

        try:
            result = await self._test_endpoint(suggestion)
            result.validation_time_ms = int((time.time() - start_time) * 1000)
            return result

        except Exception as e:
            logger.warning(
                "API validation failed",
                api_name=suggestion.api_name,
                url=suggestion.full_url,
                error=str(e),
            )
            return APIValidationResult(
                suggestion=suggestion,
                is_valid=False,
                error_message=str(e),
                validation_time_ms=int((time.time() - start_time) * 1000),
            )

    async def _test_endpoint(
        self,
        suggestion: APISuggestion,
    ) -> APIValidationResult:
        """
        Make HTTP request to test the endpoint.
        """
        if not self.client:
            raise RuntimeError("APIValidator must be used as async context manager")

        url = suggestion.full_url
        logger.info("Testing API endpoint", api_name=suggestion.api_name, url=url)

        # Handle different API types
        if suggestion.api_type == "SPARQL":
            return await self._test_sparql_endpoint(suggestion)

        # Standard REST/JSON endpoint
        response = await retry_async(
            self._make_request,
            url,
            config=API_RETRY_CONFIG,
        )

        return self._analyze_response(suggestion, response)

    async def _make_request(self, url: str) -> httpx.Response:
        """Make HTTP GET request."""
        return await self.client.get(url)

    async def _make_sparql_request(self, url: str, query: str) -> httpx.Response:
        """Make SPARQL query request."""
        return await self.client.get(
            url,
            params={"query": query, "format": "json"},
            headers={"Accept": "application/sparql-results+json"},
        )

    async def _test_sparql_endpoint(
        self,
        suggestion: APISuggestion,
    ) -> APIValidationResult:
        """
        Test SPARQL endpoint (e.g., Wikidata).
        """
        # For SPARQL, we need to construct a simple test query
        test_query = "SELECT ?item WHERE { ?item ?p ?o } LIMIT 1"

        response = await retry_async(
            self._make_sparql_request,
            suggestion.base_url,
            test_query,
            config=API_RETRY_CONFIG,
        )

        if response.status_code == 200:
            try:
                data = response.json()
                if "results" in data and "bindings" in data["results"]:
                    return APIValidationResult(
                        suggestion=suggestion,
                        is_valid=True,
                        status_code=200,
                        response_type="application/sparql-results+json",
                        item_count=len(data["results"]["bindings"]),
                    )
                else:
                    return APIValidationResult(
                        suggestion=suggestion,
                        is_valid=False,
                        status_code=200,
                        error_message="SPARQL response missing results.bindings",
                    )
            except ValueError as e:
                logger.warning(
                    "SPARQL response JSON parse error",
                    api_name=suggestion.api_name,
                    error=str(e),
                )
                return APIValidationResult(
                    suggestion=suggestion,
                    is_valid=False,
                    status_code=200,
                    error_message=f"Invalid JSON in SPARQL response: {str(e)}",
                )

        return APIValidationResult(
            suggestion=suggestion,
            is_valid=False,
            status_code=response.status_code,
            error_message=f"SPARQL endpoint test failed: {response.status_code}",
        )

    def _analyze_response(
        self,
        suggestion: APISuggestion,
        response: httpx.Response,
    ) -> APIValidationResult:
        """
        Analyze HTTP response to determine if API is valid.
        """
        content_type = response.headers.get("content-type", "")

        # Check status code
        if response.status_code != 200:
            error_msg = f"HTTP {response.status_code}"
            if response.status_code == 401:
                error_msg = "Authentication required (401)"
            elif response.status_code == 403:
                error_msg = "Access forbidden (403)"
            elif response.status_code == 404:
                error_msg = "Endpoint not found (404)"
            elif response.status_code >= 500:
                error_msg = f"Server error ({response.status_code})"

            return APIValidationResult(
                suggestion=suggestion,
                is_valid=False,
                status_code=response.status_code,
                response_type=content_type,
                error_message=error_msg,
            )

        # Try to parse as JSON
        if "json" in content_type.lower() or "javascript" in content_type.lower():
            try:
                data = response.json()
                return self._analyze_json_response(suggestion, data, content_type)
            except Exception as e:
                return APIValidationResult(
                    suggestion=suggestion,
                    is_valid=False,
                    status_code=200,
                    response_type=content_type,
                    error_message=f"Invalid JSON: {str(e)}",
                )

        # Not JSON - try anyway (some APIs don't set correct content-type)
        try:
            data = response.json()
            return self._analyze_json_response(suggestion, data, content_type)
        except Exception:
            return APIValidationResult(
                suggestion=suggestion,
                is_valid=False,
                status_code=200,
                response_type=content_type,
                error_message=f"Response is not JSON (Content-Type: {content_type})",
            )

    def _analyze_json_response(
        self,
        suggestion: APISuggestion,
        data: Any,
        content_type: str,
    ) -> APIValidationResult:
        """
        Analyze JSON response structure.
        """
        items, data_path = self._extract_items(data)

        if not items:
            return APIValidationResult(
                suggestion=suggestion,
                is_valid=False,
                status_code=200,
                response_type=content_type,
                error_message="No items found in response",
            )

        # Get sample data (first 3 items)
        sample_data = items[:3] if len(items) > 3 else items

        # Try to detect field mapping
        field_mapping = self._detect_field_mapping(items[0] if items else {})

        return APIValidationResult(
            suggestion=suggestion,
            is_valid=True,
            status_code=200,
            response_type=content_type,
            item_count=len(items),
            sample_data=sample_data,
            field_mapping=field_mapping,
        )

    def _extract_items(self, data: Any) -> Tuple[List[Dict], str]:
        """
        Extract list of items from JSON response.

        Handles various response structures:
        - Direct array: [...]
        - data field: {"data": [...]}
        - items/results/records field

        Returns:
            Tuple of (items list, data path)
        """
        # Direct array
        if isinstance(data, list):
            return data, ""

        if not isinstance(data, dict):
            return [], ""

        # Common wrapper fields
        wrapper_fields = [
            "data", "items", "results", "records", "entries",
            "teams", "matches", "bodies", "members", "list",
        ]

        for field in wrapper_fields:
            if field in data and isinstance(data[field], list):
                return data[field], field

        # Check for nested data
        for key, value in data.items():
            if isinstance(value, list) and len(value) > 0:
                if isinstance(value[0], dict):
                    return value, key

        # Single object might be valid for some APIs
        if len(data) > 2:  # Has multiple fields
            return [data], ""

        return [], ""

    def _detect_field_mapping(self, sample: Dict[str, Any]) -> Dict[str, str]:
        """
        Try to automatically detect field mapping from sample item.
        """
        mapping = {}

        if not sample:
            return mapping

        # Name field detection
        name_fields = [
            "name", "title", "label", "teamName", "displayName",
            "shortName", "fullName", "bezeichnung", "Name", "Title",
        ]
        for field in name_fields:
            if field in sample:
                mapping[field] = "name"
                break

        # URL/Website field detection
        url_fields = [
            "url", "website", "homepage", "link", "web", "webseite",
            "Website", "URL", "teamIconUrl", "imageUrl", "logoUrl",
        ]
        for field in url_fields:
            if field in sample:
                value = sample[field]
                if isinstance(value, str) and (
                    value.startswith("http") or value.startswith("www")
                ):
                    mapping[field] = "base_url"
                    break

        # ID field detection
        id_fields = [
            "id", "ID", "teamId", "itemId", "externalId", "code",
        ]
        for field in id_fields:
            if field in sample:
                mapping[field] = "external_id"
                break

        return mapping

    async def validate_all(
        self,
        suggestions: List[APISuggestion],
    ) -> List[APIValidationResult]:
        """
        Validate multiple API suggestions.

        Args:
            suggestions: List of API suggestions to validate

        Returns:
            List of validation results
        """
        results = []

        for suggestion in suggestions:
            result = await self.validate_suggestion(suggestion)
            results.append(result)

            # Log progress
            status = "VALID" if result.is_valid else "INVALID"
            logger.info(
                f"API validation: {status}",
                api_name=suggestion.api_name,
                items=result.item_count,
                error=result.error_message,
            )

        return results


async def validate_api_suggestions(
    suggestions: List[APISuggestion],
) -> List[APIValidationResult]:
    """
    Convenience function to validate API suggestions.

    Usage:
        results = await validate_api_suggestions(suggestions)
    """
    async with APIValidator() as validator:
        return await validator.validate_all(suggestions)
