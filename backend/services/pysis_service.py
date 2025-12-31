"""
PySis API Service for field synchronization.

Handles OAuth2 authentication via Azure AD and provides
methods for pulling/pushing process data to PySis.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()


@dataclass
class PySisTokenCache:
    """Cached OAuth2 token with expiry tracking."""

    access_token: str
    expires_at: datetime


class PySisService:
    """
    Service for interacting with PySis API.

    Handles OAuth2 authentication via Azure AD client credentials flow
    and provides methods for pulling/pushing process data.
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        tenant_id: str | None = None,
        api_base_url: str | None = None,
        scope: str | None = None,
    ):
        self.client_id = client_id or settings.pysis_client_id
        self.client_secret = client_secret or settings.pysis_client_secret
        self.tenant_id = tenant_id or settings.pysis_tenant_id
        self.api_base_url = api_base_url or settings.pysis_api_base_url
        self.scope = scope or settings.pysis_scope
        self._token_cache: PySisTokenCache | None = None
        self.logger = logger.bind(service="PySisService")

    @property
    def is_configured(self) -> bool:
        """Check if all required credentials are configured."""
        return bool(
            self.client_id
            and self.client_secret
            and self.tenant_id
            and self.api_base_url
        )

    async def _get_access_token(self) -> str:
        """
        Get OAuth2 access token from Azure AD.

        Uses client credentials flow with token caching.
        """
        # Check cache first (with 5 min buffer before expiry)
        if self._token_cache and self._token_cache.expires_at > datetime.now(UTC) + timedelta(minutes=5):
            return self._token_cache.access_token

        if not self.is_configured:
            raise ValueError("PySis API credentials not configured")

        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

        self.logger.info("Requesting OAuth token", tenant_id=self.tenant_id)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": self.scope,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            # Cache token (subtract 5 min buffer for safety)
            expires_in = data.get("expires_in", 3600)
            self._token_cache = PySisTokenCache(
                access_token=data["access_token"],
                expires_at=datetime.now(UTC) + timedelta(seconds=expires_in - 300),
            )

            self.logger.info("OAuth token obtained", expires_in=expires_in)
            return self._token_cache.access_token

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Make authenticated request to PySis API."""
        token = await self._get_access_token()
        url = f"{self.api_base_url}{endpoint}"

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"

        self.logger.debug(
            "PySis API request",
            method=method,
            endpoint=endpoint,
        )

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                url,
                headers=headers,
                timeout=30.0,
                **kwargs,
            )
            response.raise_for_status()

            # Handle empty responses
            if response.status_code == 204 or not response.content:
                return {}

            return response.json()

    async def list_processes(self) -> list[dict[str, Any]]:
        """
        List all available processes from PySis.

        Tries multiple possible endpoints:
        - /processes
        - /stats/processes
        - /process

        Returns:
            List of process objects with id, name, etc.
        """
        self.logger.info("Listing processes from PySis")

        # Try different possible endpoints
        endpoints = ["/processes", "/stats/processes", "/process"]

        for endpoint in endpoints:
            try:
                result = await self._request("GET", endpoint)
                # API might return list directly or wrapped in items/data
                if isinstance(result, list):
                    return result
                if "items" in result:
                    return result["items"]
                if "data" in result:
                    return result["data"]
                # If it's a dict with process-like keys, wrap it
                if result:
                    return [result] if "id" in result else list(result.values())
            except Exception as e:
                self.logger.debug(f"Endpoint {endpoint} failed: {e}")
                continue

        # No endpoint worked
        self.logger.warning("No list processes endpoint found in PySis API")
        return []

    async def get_process(self, process_id: str) -> dict[str, Any]:
        """
        Pull current process data from PySis.

        GET /stats/process/{process_id}

        Args:
            process_id: The PySis process UUID

        Returns:
            Dict containing all process fields and their values
        """
        self.logger.info("Fetching process from PySis", process_id=process_id)
        return await self._request("GET", f"/stats/process/{process_id}")

    async def update_process(
        self,
        process_id: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Push field updates to PySis.

        PATCH /stats/process/{process_id}

        Args:
            process_id: The PySis process UUID
            fields: Dict of field names to values to update

        Returns:
            Updated process data
        """
        self.logger.info(
            "Updating process in PySis",
            process_id=process_id,
            field_count=len(fields),
        )
        return await self._request(
            "PATCH",
            f"/stats/process/{process_id}",
            json=fields,
        )

    async def get_process_field(
        self,
        process_id: str,
        field_name: str,
    ) -> Any:
        """Get a specific field value from PySis process."""
        data = await self.get_process(process_id)
        return data.get(field_name)

    async def update_process_field(
        self,
        process_id: str,
        field_name: str,
        value: Any,
    ) -> dict[str, Any]:
        """Update a specific field in PySis process."""
        return await self.update_process(process_id, {field_name: value})

    async def test_connection(self, process_id: str | None = None) -> dict[str, Any]:
        """
        Test the PySis connection.

        Args:
            process_id: Optional process ID to test with

        Returns:
            Dict with connection status and process data if available
        """
        try:
            # First test if we can get a token (side effect: validates credentials)
            _token = await self._get_access_token()

            result = {
                "connected": True,
                "token_obtained": True,
                "api_base_url": self.api_base_url,
            }

            # If process_id provided, try to fetch it
            if process_id:
                try:
                    process_data = await self.get_process(process_id)
                    result["process_data"] = process_data
                    result["process_fields"] = list(process_data.keys())
                except httpx.HTTPStatusError as e:
                    result["process_error"] = str(e)

            return result

        except Exception as e:
            self.logger.error("PySis connection test failed", error=str(e))
            return {
                "connected": False,
                "error": str(e),
                "api_base_url": self.api_base_url,
            }


# Singleton instance
_pysis_service: PySisService | None = None


def get_pysis_service() -> PySisService:
    """Get PySis service singleton instance."""
    global _pysis_service
    if _pysis_service is None:
        _pysis_service = PySisService()
    return _pysis_service
