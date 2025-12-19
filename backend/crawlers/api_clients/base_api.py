"""Base API client with common functionality for all API integrations."""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional, TypeVar, Generic
from dataclasses import dataclass, field

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()

T = TypeVar("T")


@dataclass
class APIResponse(Generic[T]):
    """Standardized API response wrapper."""

    data: List[T]
    total_count: Optional[int] = None
    page: int = 1
    per_page: int = 100
    has_more: bool = False
    next_url: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class APIDocument:
    """Standardized document representation from any API."""

    source_id: str
    title: str
    url: str
    document_type: str = "UNKNOWN"
    content: Optional[str] = None
    file_url: Optional[str] = None
    mime_type: Optional[str] = None
    published_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Source-specific identifiers
    external_id: Optional[str] = None
    parent_id: Optional[str] = None

    # Classification
    categories: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    # Geographic info
    location: Optional[str] = None
    geo_coordinates: Optional[tuple] = None


class BaseAPIClient(ABC):
    """
    Abstract base class for all API clients.

    Provides common functionality like:
    - HTTP client management with connection pooling
    - Rate limiting
    - Retry logic
    - Pagination handling
    - Error handling
    """

    # Override in subclasses
    BASE_URL: str = ""
    API_NAME: str = "BaseAPI"
    DEFAULT_TIMEOUT: int = 60
    DEFAULT_DELAY: float = 1.0
    MAX_RETRIES: int = 3

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        delay: Optional[float] = None,
    ):
        self.api_key = api_key
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.delay = delay or self.DEFAULT_DELAY
        self._client: Optional[httpx.AsyncClient] = None
        self.logger = logger.bind(api=self.API_NAME)

    async def __aenter__(self):
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers=self._get_default_headers(),
                follow_redirects=True,
            )
        return self._client

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for requests."""
        headers = {
            "User-Agent": settings.crawler_user_agent,
            "Accept": "application/json",
        }
        if self.api_key:
            headers.update(self._get_auth_headers())
        return headers

    def _get_auth_headers(self) -> Dict[str, str]:
        """Override in subclasses for API-specific auth."""
        return {}

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """Make HTTP request with retry logic."""
        client = await self._ensure_client()

        # Ensure full URL
        if not url.startswith("http"):
            url = f"{self.BASE_URL.rstrip('/')}/{url.lstrip('/')}"

        try:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
            )

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                self.logger.warning(
                    "Rate limited, waiting",
                    retry_after=retry_after,
                    url=url,
                )
                await asyncio.sleep(retry_after)
                return await self._request(method, url, params, json_data, retry_count)

            response.raise_for_status()

            # Handle empty responses
            if not response.content:
                return {}

            return response.json()

        except httpx.HTTPStatusError as e:
            self.logger.error(
                "HTTP error",
                status_code=e.response.status_code,
                url=url,
                error=str(e),
            )
            if retry_count < self.MAX_RETRIES and e.response.status_code >= 500:
                await asyncio.sleep(self.delay * (retry_count + 1))
                return await self._request(method, url, params, json_data, retry_count + 1)
            raise

        except httpx.RequestError as e:
            self.logger.error("Request error", url=url, error=str(e))
            if retry_count < self.MAX_RETRIES:
                await asyncio.sleep(self.delay * (retry_count + 1))
                return await self._request(method, url, params, json_data, retry_count + 1)
            raise

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Make GET request."""
        result = await self._request("GET", url, params=params)
        await asyncio.sleep(self.delay)  # Rate limiting
        return result

    async def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Make POST request."""
        result = await self._request("POST", url, params=params, json_data=data)
        await asyncio.sleep(self.delay)
        return result

    @abstractmethod
    async def search(
        self,
        query: str,
        **kwargs,
    ) -> APIResponse[APIDocument]:
        """Search for documents. Must be implemented by subclasses."""
        pass

    @abstractmethod
    async def get_document(self, document_id: str) -> Optional[APIDocument]:
        """Get single document by ID. Must be implemented by subclasses."""
        pass

    async def paginate(
        self,
        initial_url: str,
        params: Optional[Dict[str, Any]] = None,
        max_pages: int = 100,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Generic pagination handler.

        Override _extract_pagination_info() in subclasses for API-specific pagination.
        """
        current_url = initial_url
        current_params = params or {}
        page = 0

        while current_url and page < max_pages:
            data = await self.get(current_url, current_params)
            if not data:
                break

            yield data

            # Get next page info
            next_url, next_params = self._extract_pagination_info(data, current_params)
            current_url = next_url
            current_params = next_params or {}
            page += 1

    def _extract_pagination_info(
        self,
        response: Dict[str, Any],
        current_params: Dict[str, Any],
    ) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Extract pagination info from response.

        Override in subclasses for API-specific pagination handling.
        Returns (next_url, next_params) tuple.
        """
        # Default: try common pagination patterns

        # Pattern 1: links.next
        if "links" in response:
            next_url = response["links"].get("next")
            if next_url:
                return next_url, None

        # Pattern 2: next_page_url
        if "next_page_url" in response:
            return response["next_page_url"], None

        # Pattern 3: offset-based
        if "offset" in current_params and "total" in response:
            offset = current_params.get("offset", 0)
            limit = current_params.get("limit", 100)
            total = response.get("total", 0)

            if offset + limit < total:
                new_params = {**current_params, "offset": offset + limit}
                return None, new_params

        return None, None

    @staticmethod
    def parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime from various formats."""
        if not date_str:
            return None

        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
            "%d.%m.%Y",
        ]

        # Handle timezone suffix
        date_str = date_str.replace("+00:00", "Z").replace("+0000", "Z")

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None
