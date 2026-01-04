"""Caeli Wind Auction Marketplace API Client."""

from datetime import datetime
from typing import Any

import structlog

from app.config import settings
from external_apis.base import BaseExternalAPIClient, ExternalAPIRecord

logger = structlog.get_logger(__name__)


class CaeliAuctionClient(BaseExternalAPIClient):
    """Client for Caeli Wind Auction Marketplace API.

    This client connects to the Caeli Wind auction platform to fetch
    wind project listings that are available for auction.

    Environment variables:
        CAELI_AUCTION_MARKETPLACE_API_URL: API base URL
        CAELI_AUCTION_MARKETPLACE_API_AUTH: Base64-encoded Basic Auth credentials
    """

    API_NAME = "CaeliAuction"
    DEFAULT_DELAY = 0.5
    DEFAULT_TIMEOUT = 60

    def __init__(
        self,
        auth_token: str | None = None,
        base_url: str | None = None,
        timeout: int | None = None,
    ):
        """Initialize the Caeli Auction API client.

        Args:
            auth_token: Base64-encoded Basic Auth token. If not provided,
                        reads from CAELI_AUCTION_MARKETPLACE_API_AUTH env var.
            base_url: API base URL. If not provided, reads from
                      CAELI_AUCTION_MARKETPLACE_API_URL env var.
            timeout: Request timeout in seconds.
        """
        # Get from settings/env if not provided
        self._auth_token = auth_token or getattr(settings, "caeli_auction_marketplace_api_auth", None)
        self._base_url = base_url or getattr(
            settings,
            "caeli_auction_marketplace_api_url",
            "https://auction.caeli-wind.de/api/auction-platform/v4/public-marketplace",
        )

        super().__init__(
            auth_token=self._auth_token,
            base_url=self._base_url,
            timeout=timeout,
        )

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": f"CaeliCrawler/{self.API_NAME}Client/1.0",
        }

        if self._auth_token:
            headers["Authorization"] = f"Basic {self._auth_token}"

        return headers

    async def fetch_all_records(self) -> list[ExternalAPIRecord]:
        """Fetch all auction/project listings from the marketplace.

        Returns:
            List of ExternalAPIRecord objects representing wind projects.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        logger.info("fetching_auction_records", api=self.API_NAME, url=self._base_url)

        try:
            response = await self._client.get(
                self._base_url,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()

            logger.debug(
                "auction_api_response",
                status=response.status_code,
                data_type=type(data).__name__,
            )

            records = []
            items = self._extract_items(data)

            for item in items:
                try:
                    record = self._parse_item(item)
                    records.append(record)
                except Exception as e:
                    logger.warning(
                        "failed_to_parse_auction_item",
                        error=str(e),
                        item_id=item.get("id", "unknown"),
                    )

            logger.info(
                "auction_records_fetched",
                count=len(records),
                api=self.API_NAME,
            )

            return records

        except Exception as e:
            logger.error(
                "auction_api_error",
                error=str(e),
                api=self.API_NAME,
            )
            raise

    def _extract_items(self, data: Any) -> list[dict[str, Any]]:
        """Extract list of items from API response.

        The API may return data in different formats:
        - Direct list: [...]
        - Wrapped in object: {"items": [...], ...}
        - Wrapped in data: {"data": [...], ...}
        - Paginated: {"results": [...], "total": ..., ...}

        Args:
            data: Raw API response.

        Returns:
            List of item dictionaries.
        """
        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            # Try common wrapper keys
            for key in ["items", "data", "results", "records", "listings", "projects"]:
                if key in data and isinstance(data[key], list):
                    return data[key]

            # If it looks like a single item, wrap it
            if "id" in data:
                return [data]

        logger.warning(
            "unexpected_api_response_format",
            data_type=type(data).__name__,
            keys=list(data.keys()) if isinstance(data, dict) else None,
        )
        return []

    def _parse_item(self, item: dict[str, Any]) -> ExternalAPIRecord:
        """Parse a single item from the API response.

        Args:
            item: Raw item dictionary from API.

        Returns:
            Standardized ExternalAPIRecord.
        """
        # Extract ID - try multiple possible field names
        external_id = str(
            item.get("id") or item.get("auctionId") or item.get("projectId") or item.get("uuid") or item.get("_id")
        )

        # Extract name - prefer areaName for auction data
        name = (
            item.get("areaName")
            or item.get("name")
            or item.get("title")
            or item.get("projectName")
            or item.get("description", "")[:100]
            or f"Windprojekt {external_id}"
        )

        # Extract location hints for entity linking
        location_hints = self._extract_location_hints(item)

        # Extract modification timestamp if available
        modified_at = self._parse_timestamp(
            item.get("updatedAt") or item.get("modifiedAt") or item.get("lastModified") or item.get("updated_at")
        )

        return ExternalAPIRecord(
            external_id=external_id,
            name=name,
            raw_data=item,
            location_hints=location_hints,
            modified_at=modified_at,
        )

    def _extract_location_hints(self, item: dict[str, Any]) -> list[str]:
        """Extract location-related fields for entity linking.

        Args:
            item: Raw item dictionary.

        Returns:
            List of location hint strings.
        """
        hints = []

        # Direct location fields
        location_fields = [
            "location",
            "municipality",
            "gemeinde",
            "city",
            "stadt",
            "region",
            "state",
            "bundesland",
            "address",
            "adresse",
            "site",
            "standort",
            "area",
            "gebiet",
            "district",
            "kreis",
            "landkreis",
            # Auction API specific fields
            "administrativeDivisionLevel1",
            "administrativeDivisionLevel2",
            "administrativeDivisionLevel3",
            "areaName",
        ]

        for field in location_fields:
            value = item.get(field)
            if value and isinstance(value, str) and value.strip():
                hints.append(value.strip())

        # Nested location object
        if "location" in item and isinstance(item["location"], dict):
            loc = item["location"]
            for key in ["name", "municipality", "city", "address"]:
                if key in loc and loc[key]:
                    hints.append(str(loc[key]))

        # Address object
        if "address" in item and isinstance(item["address"], dict):
            addr = item["address"]
            for key in ["city", "municipality", "postalCode", "street"]:
                if key in addr and addr[key]:
                    hints.append(str(addr[key]))

        # Coordinates (for potential future geocoding)
        lat = item.get("latitude") or item.get("lat")
        lon = item.get("longitude") or item.get("lon") or item.get("lng")
        if lat and lon:
            hints.append(f"geo:{lat},{lon}")

        return hints

    def _parse_timestamp(self, value: Any) -> datetime | None:
        """Parse a timestamp value to datetime.

        Args:
            value: Timestamp value (string, int, or datetime).

        Returns:
            Parsed datetime or None.
        """
        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, (int, float)):
            # Unix timestamp
            try:
                return datetime.fromtimestamp(value)
            except (ValueError, OSError):
                return None

        if isinstance(value, str):
            # Try ISO format
            for fmt in [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
            ]:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue

        return None

    async def test_connection(self) -> bool:
        """Test the API connection.

        Returns:
            True if connection is successful.
        """
        try:
            if not self._client:
                async with self:
                    response = await self._client.get(
                        self._base_url,
                        headers=self._get_headers(),
                        timeout=10,
                    )
                    return response.status_code == 200
            else:
                response = await self._client.get(
                    self._base_url,
                    headers=self._get_headers(),
                    timeout=10,
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(
                "auction_api_connection_test_failed",
                error=str(e),
            )
            return False
