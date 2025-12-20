"""Base classes for external API integration."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar, Generic
import hashlib
import json

import httpx
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


@dataclass
class ExternalAPIRecord:
    """Standardized record from an external API.

    This is the common format that all API clients must convert their
    responses to. It provides a unified interface for the sync service.
    """

    external_id: str
    """Unique identifier from the external API."""

    name: str
    """Display name for the entity."""

    raw_data: Dict[str, Any]
    """Complete raw data from the API response."""

    location_hints: List[str] = field(default_factory=list)
    """Location-related fields for entity linking (e.g., municipality names)."""

    modified_at: Optional[datetime] = None
    """Last modification timestamp from the API (if available)."""

    def compute_hash(self) -> str:
        """Compute SHA256 hash of the raw data for change detection."""
        return hashlib.sha256(
            json.dumps(self.raw_data, sort_keys=True, default=str).encode()
        ).hexdigest()


@dataclass
class SyncResult:
    """Result of a sync operation."""

    records_fetched: int = 0
    """Total records retrieved from the API."""

    entities_created: int = 0
    """New entities created."""

    entities_updated: int = 0
    """Existing entities updated due to changes."""

    entities_unchanged: int = 0
    """Entities that had no changes."""

    entities_linked: int = 0
    """Entities successfully linked to other entities (e.g., municipalities)."""

    records_missing: int = 0
    """Records not found in API (previously existed)."""

    records_archived: int = 0
    """Records archived due to extended absence."""

    errors: List[Dict[str, Any]] = field(default_factory=list)
    """List of errors encountered during sync."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "records_fetched": self.records_fetched,
            "entities_created": self.entities_created,
            "entities_updated": self.entities_updated,
            "entities_unchanged": self.entities_unchanged,
            "entities_linked": self.entities_linked,
            "records_missing": self.records_missing,
            "records_archived": self.records_archived,
            "error_count": len(self.errors),
        }


@dataclass
class APIResponse(Generic[T]):
    """Generic API response wrapper with pagination support."""

    data: List[T]
    """List of records."""

    total_count: Optional[int] = None
    """Total number of records available (for pagination)."""

    has_more: bool = False
    """Whether more records are available."""

    next_cursor: Optional[str] = None
    """Cursor for fetching next page (if applicable)."""


class BaseExternalAPIClient(ABC):
    """Abstract base class for external API clients.

    All external API clients must inherit from this class and implement
    the required methods. This ensures a consistent interface for the
    sync service.

    Attributes:
        API_NAME: Human-readable name of the API.
        DEFAULT_DELAY: Default delay between requests (rate limiting).
        DEFAULT_TIMEOUT: Default request timeout in seconds.
    """

    API_NAME: str = "BaseExternalAPI"
    DEFAULT_DELAY: float = 0.5
    DEFAULT_TIMEOUT: int = 60

    def __init__(
        self,
        auth_token: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """Initialize the API client.

        Args:
            auth_token: Authentication token/credentials.
            base_url: Override the default base URL.
            timeout: Override the default timeout.
        """
        self.auth_token = auth_token
        self.base_url = base_url
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "BaseExternalAPIClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers including authentication.

        Override this method to customize headers for specific APIs.
        """
        return {
            "Accept": "application/json",
            "User-Agent": f"CaeliCrawler/{self.API_NAME}Client/1.0",
        }

    async def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, etc.).
            url: Full URL to request.
            params: Query parameters.
            json_data: JSON body data.

        Returns:
            Parsed JSON response.

        Raises:
            httpx.HTTPStatusError: If the request fails.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        response = await self._client.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            headers=self._get_headers(),
        )

        logger.debug(
            "api_request",
            api=self.API_NAME,
            method=method,
            url=url,
            status=response.status_code,
        )

        response.raise_for_status()
        return response.json()

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a GET request.

        Args:
            endpoint: API endpoint (relative to base_url).
            params: Query parameters.

        Returns:
            Parsed JSON response.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        return await self._request("GET", url, params=params)

    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a POST request.

        Args:
            endpoint: API endpoint (relative to base_url).
            data: JSON body data.
            params: Query parameters.

        Returns:
            Parsed JSON response.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        return await self._request("POST", url, params=params, json_data=data)

    @abstractmethod
    async def fetch_all_records(self) -> List[ExternalAPIRecord]:
        """Fetch all records from the API.

        This is the main method that sync service calls. It should:
        1. Handle pagination if the API has it
        2. Convert all responses to ExternalAPIRecord format
        3. Handle rate limiting appropriately

        Returns:
            List of standardized ExternalAPIRecord objects.
        """
        pass

    async def fetch_record(self, external_id: str) -> Optional[ExternalAPIRecord]:
        """Fetch a single record by its external ID.

        Override this method if the API supports fetching individual records.
        This is useful for incremental updates.

        Args:
            external_id: The external ID of the record.

        Returns:
            The record if found, None otherwise.
        """
        # Default implementation: fetch all and filter
        all_records = await self.fetch_all_records()
        for record in all_records:
            if record.external_id == external_id:
                return record
        return None

    async def test_connection(self) -> bool:
        """Test the API connection.

        Override this method to implement a lightweight connection test.

        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            records = await self.fetch_all_records()
            return True
        except Exception as e:
            logger.warning(
                "api_connection_test_failed",
                api=self.API_NAME,
                error=str(e),
            )
            return False
