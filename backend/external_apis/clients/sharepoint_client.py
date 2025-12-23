"""SharePoint Online Client using Microsoft Graph API.

This client provides access to SharePoint Online document libraries
via the Microsoft Graph API with Azure AD authentication.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import httpx
import structlog

from app.config import settings
from external_apis.base import BaseExternalAPIClient, ExternalAPIRecord

logger = structlog.get_logger(__name__)


# =============================================================================
# Custom Exceptions
# =============================================================================


class SharePointError(Exception):
    """Base exception for SharePoint errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class SharePointAuthError(SharePointError):
    """Authentication failed."""

    pass


class SharePointNotFoundError(SharePointError):
    """Resource not found (site, drive, file)."""

    pass


class SharePointPermissionError(SharePointError):
    """Insufficient permissions."""

    pass


class SharePointRateLimitError(SharePointError):
    """Rate limit exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class SharePointConfigError(SharePointError):
    """Configuration error."""

    pass


# =============================================================================
# URL Parsing Utility
# =============================================================================


def parse_sharepoint_site_url(site_url: str) -> Tuple[str, str]:
    """Parse SharePoint site URL into hostname and path.

    Supported formats:
    - "contoso.sharepoint.com:/sites/Documents"
    - "contoso.sharepoint.com/sites/Documents"
    - "https://contoso.sharepoint.com/sites/Documents"

    Args:
        site_url: SharePoint site URL in any supported format.

    Returns:
        Tuple of (hostname, site_path)

    Raises:
        SharePointConfigError: If URL format is invalid.
    """
    if not site_url:
        raise SharePointConfigError("Site URL is empty")

    # Remove https:// prefix if present
    url = site_url.replace("https://", "").replace("http://", "")

    # Check for ":/" separator (Graph API format)
    if ":/" in url:
        parts = url.split(":/", 1)
        return parts[0], "/" + parts[1]

    # Check for ".sharepoint.com/"
    if ".sharepoint.com/" in url:
        parts = url.split(".sharepoint.com/", 1)
        hostname = parts[0] + ".sharepoint.com"
        site_path = "/" + parts[1]
        return hostname, site_path

    raise SharePointConfigError(
        f"Invalid SharePoint site URL format: {site_url}. "
        "Expected format: 'tenant.sharepoint.com:/sites/SiteName' or "
        "'https://tenant.sharepoint.com/sites/SiteName'"
    )


@dataclass
class SharePointTokenCache:
    """Cached OAuth2 token with expiry tracking."""

    access_token: str
    expires_at: datetime


@dataclass
class SharePointFile:
    """Represents a file from SharePoint."""

    id: str
    name: str
    size: int
    mime_type: str
    web_url: str
    download_url: Optional[str]
    created_at: Optional[datetime]
    modified_at: Optional[datetime]
    created_by: Optional[str]
    modified_by: Optional[str]
    parent_path: str
    site_id: str
    drive_id: str


@dataclass
class SharePointSite:
    """Represents a SharePoint site."""

    id: str
    name: str
    display_name: str
    web_url: str


@dataclass
class SharePointDrive:
    """Represents a SharePoint document library (drive)."""

    id: str
    name: str
    drive_type: str
    web_url: str
    site_id: str


class SharePointClient(BaseExternalAPIClient):
    """Client for Microsoft Graph API / SharePoint Online.

    Uses OAuth2 Client Credentials flow for authentication.
    Provides methods to list sites, drives, and files, and to download documents.

    Environment variables:
        SHAREPOINT_TENANT_ID: Azure AD Tenant ID
        SHAREPOINT_CLIENT_ID: Azure AD App Registration Client ID
        SHAREPOINT_CLIENT_SECRET: Azure AD App Registration Client Secret
    """

    API_NAME = "SharePoint"
    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
    DEFAULT_DELAY = 0.2  # Graph API has generous rate limits
    DEFAULT_TIMEOUT = 60

    def __init__(
        self,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """Initialize the SharePoint client.

        Args:
            tenant_id: Azure AD Tenant ID. If not provided, reads from settings.
            client_id: Azure AD Client ID. If not provided, reads from settings.
            client_secret: Azure AD Client Secret. If not provided, reads from settings.
            timeout: Request timeout in seconds.
        """
        self._tenant_id = tenant_id or settings.sharepoint_tenant_id
        self._client_id = client_id or settings.sharepoint_client_id
        self._client_secret = client_secret or settings.sharepoint_client_secret
        self._token_cache: Optional[SharePointTokenCache] = None

        super().__init__(
            auth_token=None,  # We handle auth separately via OAuth
            base_url=self.GRAPH_BASE_URL,
            timeout=timeout,
        )

    @property
    def is_configured(self) -> bool:
        """Check if all required credentials are configured."""
        return bool(
            self._tenant_id
            and self._client_id
            and self._client_secret
        )

    async def _get_access_token(self) -> str:
        """Get OAuth2 access token from Azure AD.

        Uses client credentials flow with token caching.

        Raises:
            SharePointConfigError: If credentials not configured.
            SharePointAuthError: If authentication fails.
        """
        # Check cache first (with 5 min buffer before expiry)
        if self._token_cache:
            if self._token_cache.expires_at > datetime.now(timezone.utc) + timedelta(minutes=5):
                return self._token_cache.access_token

        if not self.is_configured:
            raise SharePointConfigError(
                "SharePoint API credentials not configured. "
                "Set SHAREPOINT_TENANT_ID, SHAREPOINT_CLIENT_ID, and SHAREPOINT_CLIENT_SECRET."
            )

        token_url = f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token"

        logger.info(
            "requesting_sharepoint_oauth_token",
            tenant_id=self._tenant_id[:8] + "..." if self._tenant_id else None,
        )

        try:
            async with httpx.AsyncClient() as token_client:
                response = await token_client.post(
                    token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "scope": "https://graph.microsoft.com/.default",
                    },
                    timeout=30.0,
                )

                if response.status_code == 401:
                    raise SharePointAuthError(
                        "Invalid client credentials",
                        details=response.json() if response.content else {},
                    )
                elif response.status_code == 400:
                    error_data = response.json() if response.content else {}
                    raise SharePointAuthError(
                        f"Authentication error: {error_data.get('error_description', 'Unknown error')}",
                        details=error_data,
                    )

                response.raise_for_status()
                data = response.json()

                # Cache token (subtract 5 min buffer for safety)
                expires_in = data.get("expires_in", 3600)
                self._token_cache = SharePointTokenCache(
                    access_token=data["access_token"],
                    expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in - 300),
                )

                logger.info(
                    "sharepoint_oauth_token_obtained",
                    expires_in=expires_in,
                )
                return self._token_cache.access_token

        except httpx.TimeoutException as e:
            raise SharePointAuthError(f"Token request timed out: {e}")
        except httpx.HTTPStatusError as e:
            raise SharePointAuthError(f"Token request failed: {e}")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers - note: auth is added per-request."""
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": f"CaeliCrawler/{self.API_NAME}Client/1.0",
        }

    async def _graph_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Make an authenticated request to Microsoft Graph API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint (relative to Graph base URL).
            params: Query parameters.
            json_data: JSON body data.
            max_retries: Maximum number of retries for transient errors.

        Returns:
            Parsed JSON response.

        Raises:
            SharePointNotFoundError: If resource not found (404).
            SharePointPermissionError: If access denied (403).
            SharePointRateLimitError: If rate limit exceeded (429).
            SharePointError: For other API errors.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        url = f"{self.GRAPH_BASE_URL}{endpoint}"
        last_exception: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                token = await self._get_access_token()
                headers = self._get_headers()
                headers["Authorization"] = f"Bearer {token}"

                response = await self._client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=headers,
                )

                logger.debug(
                    "graph_api_request",
                    method=method,
                    endpoint=endpoint,
                    status=response.status_code,
                    attempt=attempt + 1,
                )

                # Handle specific status codes
                if response.status_code == 404:
                    raise SharePointNotFoundError(
                        f"Resource not found: {endpoint}",
                        details=response.json() if response.content else {},
                    )
                elif response.status_code == 403:
                    raise SharePointPermissionError(
                        f"Access denied: {endpoint}",
                        details=response.json() if response.content else {},
                    )
                elif response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    if attempt < max_retries:
                        logger.warning(
                            "graph_api_rate_limited",
                            endpoint=endpoint,
                            retry_after=retry_after,
                            attempt=attempt + 1,
                        )
                        await asyncio.sleep(retry_after)
                        continue
                    raise SharePointRateLimitError(
                        "Rate limit exceeded",
                        retry_after=retry_after,
                    )
                elif response.status_code >= 500:
                    # Server error - retry with exponential backoff
                    if attempt < max_retries:
                        wait_time = (2 ** attempt) + 0.5
                        logger.warning(
                            "graph_api_server_error",
                            endpoint=endpoint,
                            status=response.status_code,
                            retry_in=wait_time,
                            attempt=attempt + 1,
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    response.raise_for_status()

                response.raise_for_status()

                if response.status_code == 204 or not response.content:
                    return {}

                return response.json()

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = (2 ** attempt) + 0.5
                    logger.warning(
                        "graph_api_connection_error",
                        endpoint=endpoint,
                        error=str(e),
                        retry_in=wait_time,
                        attempt=attempt + 1,
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise SharePointError(f"Connection error after {max_retries} retries: {e}")

        # Should not reach here, but just in case
        if last_exception:
            raise SharePointError(f"Request failed: {last_exception}")
        raise SharePointError("Request failed for unknown reason")

    async def _graph_request_binary(
        self,
        endpoint: str,
        max_retries: int = 3,
    ) -> bytes:
        """Make an authenticated request that returns binary data with retry logic.

        Args:
            endpoint: API endpoint (relative to Graph base URL).
            max_retries: Maximum number of retries for transient errors.

        Returns:
            Binary response content.

        Raises:
            SharePointNotFoundError: If resource not found (404).
            SharePointPermissionError: If access denied (403).
            SharePointError: For other API errors.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        url = f"{self.GRAPH_BASE_URL}{endpoint}"

        for attempt in range(max_retries + 1):
            try:
                token = await self._get_access_token()
                headers = self._get_headers()
                headers["Authorization"] = f"Bearer {token}"

                response = await self._client.get(
                    url,
                    headers=headers,
                    follow_redirects=True,
                )

                logger.debug(
                    "graph_api_binary_request",
                    endpoint=endpoint,
                    status=response.status_code,
                    content_length=len(response.content) if response.content else 0,
                    attempt=attempt + 1,
                )

                if response.status_code == 404:
                    raise SharePointNotFoundError(f"File not found: {endpoint}")
                elif response.status_code == 403:
                    raise SharePointPermissionError(f"Access denied: {endpoint}")
                elif response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    if attempt < max_retries:
                        logger.warning(
                            "graph_api_binary_rate_limited",
                            endpoint=endpoint,
                            retry_after=retry_after,
                            attempt=attempt + 1,
                        )
                        await asyncio.sleep(retry_after)
                        continue
                    raise SharePointRateLimitError("Rate limit exceeded", retry_after=retry_after)
                elif response.status_code >= 500:
                    if attempt < max_retries:
                        wait_time = (2 ** attempt) + 0.5
                        logger.warning(
                            "graph_api_binary_server_error",
                            endpoint=endpoint,
                            status=response.status_code,
                            retry_in=wait_time,
                            attempt=attempt + 1,
                        )
                        await asyncio.sleep(wait_time)
                        continue

                response.raise_for_status()
                return response.content

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                if attempt < max_retries:
                    wait_time = (2 ** attempt) + 0.5
                    logger.warning(
                        "graph_api_binary_connection_error",
                        endpoint=endpoint,
                        error=str(e),
                        retry_in=wait_time,
                        attempt=attempt + 1,
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise SharePointError(f"Connection error: {e}")

        raise SharePointError("Binary request failed")

    async def _fetch_paginated_url(
        self,
        url: str,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Fetch a paginated URL (handles @odata.nextLink) with retry logic.

        Args:
            url: Full URL or relative endpoint.
            max_retries: Maximum number of retries for transient errors.

        Returns:
            Parsed JSON response.
        """
        if not url.startswith("http"):
            # Relative endpoint - use standard request method
            return await self._graph_request("GET", url)

        # Full URL from @odata.nextLink - apply retry logic
        for attempt in range(max_retries + 1):
            try:
                token = await self._get_access_token()
                headers = self._get_headers()
                headers["Authorization"] = f"Bearer {token}"
                response = await self._client.get(url, headers=headers)

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    if attempt < max_retries:
                        logger.warning(
                            "graph_api_paginated_rate_limited",
                            url=url[:100],
                            retry_after=retry_after,
                            attempt=attempt + 1,
                        )
                        await asyncio.sleep(retry_after)
                        continue
                    raise SharePointRateLimitError("Rate limit exceeded", retry_after=retry_after)
                elif response.status_code >= 500:
                    if attempt < max_retries:
                        wait_time = (2 ** attempt) + 0.5
                        logger.warning(
                            "graph_api_paginated_server_error",
                            url=url[:100],
                            status=response.status_code,
                            retry_in=wait_time,
                            attempt=attempt + 1,
                        )
                        await asyncio.sleep(wait_time)
                        continue

                response.raise_for_status()
                return response.json()

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                if attempt < max_retries:
                    wait_time = (2 ** attempt) + 0.5
                    logger.warning(
                        "graph_api_paginated_connection_error",
                        url=url[:100],
                        error=str(e),
                        retry_in=wait_time,
                        attempt=attempt + 1,
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise SharePointError(f"Connection error: {e}")

        raise SharePointError("Paginated request failed")

    # -------------------------------------------------------------------------
    # Sites
    # -------------------------------------------------------------------------

    async def search_sites(self, query: str = "*") -> List[SharePointSite]:
        """Search for SharePoint sites.

        Args:
            query: Search query. Use "*" to list all sites.

        Returns:
            List of SharePointSite objects.
        """
        logger.info("searching_sharepoint_sites", query=query)

        data = await self._graph_request(
            "GET",
            "/sites",
            params={"search": query},
        )

        sites = []
        for item in data.get("value", []):
            sites.append(SharePointSite(
                id=item["id"],
                name=item.get("name", ""),
                display_name=item.get("displayName", item.get("name", "")),
                web_url=item.get("webUrl", ""),
            ))

        logger.info("sharepoint_sites_found", count=len(sites))
        return sites

    async def get_site_by_url(self, hostname: str, site_path: str) -> SharePointSite:
        """Get a SharePoint site by its URL components.

        Args:
            hostname: SharePoint hostname (e.g., "contoso.sharepoint.com")
            site_path: Site path (e.g., "/sites/Documents")

        Returns:
            SharePointSite object.
        """
        logger.debug(
            "getting_sharepoint_site",
            hostname=hostname,
            site_path=site_path,
        )

        # URL encode the path for the API
        endpoint = f"/sites/{hostname}:{site_path}"

        data = await self._graph_request("GET", endpoint)

        return SharePointSite(
            id=data["id"],
            name=data.get("name", ""),
            display_name=data.get("displayName", data.get("name", "")),
            web_url=data.get("webUrl", ""),
        )

    # -------------------------------------------------------------------------
    # Drives (Document Libraries)
    # -------------------------------------------------------------------------

    async def list_drives(self, site_id: str) -> List[SharePointDrive]:
        """List all document libraries (drives) in a site.

        Args:
            site_id: SharePoint site ID.

        Returns:
            List of SharePointDrive objects.
        """
        logger.debug("listing_sharepoint_drives", site_id=site_id)

        data = await self._graph_request(
            "GET",
            f"/sites/{site_id}/drives",
        )

        drives = []
        for item in data.get("value", []):
            drives.append(SharePointDrive(
                id=item["id"],
                name=item.get("name", ""),
                drive_type=item.get("driveType", ""),
                web_url=item.get("webUrl", ""),
                site_id=site_id,
            ))

        logger.debug("sharepoint_drives_found", count=len(drives))
        return drives

    async def get_drive_by_name(self, site_id: str, drive_name: str) -> Optional[SharePointDrive]:
        """Get a specific drive by name.

        Args:
            site_id: SharePoint site ID.
            drive_name: Name of the document library.

        Returns:
            SharePointDrive if found, None otherwise.
        """
        drives = await self.list_drives(site_id)
        for drive in drives:
            if drive.name.lower() == drive_name.lower():
                return drive
        return None

    # -------------------------------------------------------------------------
    # Files
    # -------------------------------------------------------------------------

    async def list_files(
        self,
        site_id: str,
        drive_id: str,
        folder_path: str = "",
        recursive: bool = False,
        file_extensions: Optional[List[str]] = None,
    ) -> List[SharePointFile]:
        """List files in a drive or folder.

        Args:
            site_id: SharePoint site ID.
            drive_id: Drive (document library) ID.
            folder_path: Path within the drive (empty for root).
            recursive: Whether to include files in subfolders.
            file_extensions: Filter by file extensions (e.g., [".pdf", ".docx"]).

        Returns:
            List of SharePointFile objects.
        """
        logger.debug(
            "listing_sharepoint_files",
            site_id=site_id,
            drive_id=drive_id,
            folder_path=folder_path,
            recursive=recursive,
        )

        files: List[SharePointFile] = []
        folders_to_process = [folder_path]

        while folders_to_process:
            current_folder = folders_to_process.pop(0)

            # Build endpoint
            if current_folder:
                # Remove leading/trailing slashes and encode
                clean_path = current_folder.strip("/")
                endpoint = f"/sites/{site_id}/drives/{drive_id}/root:/{clean_path}:/children"
            else:
                endpoint = f"/sites/{site_id}/drives/{drive_id}/root/children"

            # Handle pagination
            next_link: Optional[str] = endpoint
            while next_link:
                data = await self._fetch_paginated_url(next_link)

                for item in data.get("value", []):
                    if "folder" in item:
                        # It's a folder
                        if recursive:
                            folder_rel_path = item.get("parentReference", {}).get("path", "")
                            # Extract path after /root:
                            if "/root:" in folder_rel_path:
                                parent = folder_rel_path.split("/root:")[-1]
                            else:
                                parent = ""
                            child_path = f"{parent}/{item['name']}".lstrip("/")
                            folders_to_process.append(child_path)
                    elif "file" in item:
                        # It's a file
                        file_obj = self._parse_file_item(item, site_id, drive_id)

                        # Apply extension filter
                        if file_extensions:
                            ext = "." + file_obj.name.rsplit(".", 1)[-1].lower() if "." in file_obj.name else ""
                            if ext not in [e.lower() for e in file_extensions]:
                                continue

                        files.append(file_obj)

                # Check for next page
                next_link = data.get("@odata.nextLink")

        logger.info("sharepoint_files_found", count=len(files))
        return files

    def _parse_file_item(
        self,
        item: Dict[str, Any],
        site_id: str,
        drive_id: str,
    ) -> SharePointFile:
        """Parse a file item from Graph API response."""
        # Extract parent path
        parent_ref = item.get("parentReference", {})
        parent_path = parent_ref.get("path", "")
        if "/root:" in parent_path:
            parent_path = parent_path.split("/root:")[-1]
        else:
            parent_path = ""

        # Parse timestamps
        created_at = self._parse_timestamp(item.get("createdDateTime"))
        modified_at = self._parse_timestamp(item.get("lastModifiedDateTime"))

        # Extract user info
        created_by = None
        if "createdBy" in item and "user" in item["createdBy"]:
            created_by = item["createdBy"]["user"].get("displayName")

        modified_by = None
        if "lastModifiedBy" in item and "user" in item["lastModifiedBy"]:
            modified_by = item["lastModifiedBy"]["user"].get("displayName")

        return SharePointFile(
            id=item["id"],
            name=item["name"],
            size=item.get("size", 0),
            mime_type=item.get("file", {}).get("mimeType", "application/octet-stream"),
            web_url=item.get("webUrl", ""),
            download_url=item.get("@microsoft.graph.downloadUrl"),
            created_at=created_at,
            modified_at=modified_at,
            created_by=created_by,
            modified_by=modified_by,
            parent_path=parent_path,
            site_id=site_id,
            drive_id=drive_id,
        )

    def _parse_timestamp(self, value: Optional[str]) -> Optional[datetime]:
        """Parse ISO timestamp from Graph API."""
        if not value:
            return None
        try:
            # Graph API uses ISO format with Z suffix
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    async def get_file_metadata(
        self,
        site_id: str,
        drive_id: str,
        item_id: str,
    ) -> SharePointFile:
        """Get metadata for a specific file.

        Args:
            site_id: SharePoint site ID.
            drive_id: Drive ID.
            item_id: File item ID.

        Returns:
            SharePointFile object with full metadata.
        """
        data = await self._graph_request(
            "GET",
            f"/sites/{site_id}/drives/{drive_id}/items/{item_id}",
        )

        return self._parse_file_item(data, site_id, drive_id)

    async def get_file_by_path(
        self,
        site_id: str,
        drive_id: str,
        file_path: str,
    ) -> Optional[SharePointFile]:
        """Get a file by its path within a drive.

        Args:
            site_id: SharePoint site ID.
            drive_id: Drive ID.
            file_path: Path to the file, e.g., "/Documents/Report.pdf".

        Returns:
            SharePointFile object if found, None otherwise.
        """
        # Normalize path - ensure it starts with / but doesn't have trailing /
        file_path = file_path.strip()
        if not file_path.startswith("/"):
            file_path = "/" + file_path
        file_path = file_path.rstrip("/")

        # URL-encode the path for the API call (preserve slashes)
        encoded_path = quote(file_path, safe="/")

        try:
            data = await self._graph_request(
                "GET",
                f"/sites/{site_id}/drives/{drive_id}/root:{encoded_path}",
            )

            # Check if it's a file (not a folder)
            if "file" not in data:
                logger.warning(
                    "sharepoint_path_is_not_file",
                    path=file_path,
                )
                return None

            return self._parse_file_item(data, site_id, drive_id)

        except SharePointNotFoundError:
            logger.warning(
                "sharepoint_file_not_found",
                path=file_path,
            )
            return None

    async def download_file(
        self,
        site_id: str,
        drive_id: str,
        item_id: str,
    ) -> bytes:
        """Download file content.

        Args:
            site_id: SharePoint site ID.
            drive_id: Drive ID.
            item_id: File item ID.

        Returns:
            File content as bytes.
        """
        logger.debug(
            "downloading_sharepoint_file",
            site_id=site_id,
            drive_id=drive_id,
            item_id=item_id,
        )

        return await self._graph_request_binary(
            f"/sites/{site_id}/drives/{drive_id}/items/{item_id}/content"
        )

    async def download_file_by_url(
        self,
        download_url: str,
        max_retries: int = 3,
    ) -> bytes:
        """Download file directly via download URL with retry logic.

        This uses the pre-authenticated download URL from SharePointFile.download_url
        which is faster than going through the API.

        Args:
            download_url: Pre-authenticated download URL.
            max_retries: Maximum number of retries for transient errors.

        Returns:
            File content as bytes.

        Raises:
            SharePointError: If download fails after retries.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        for attempt in range(max_retries + 1):
            try:
                response = await self._client.get(download_url, follow_redirects=True)

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    if attempt < max_retries:
                        logger.warning(
                            "download_url_rate_limited",
                            retry_after=retry_after,
                            attempt=attempt + 1,
                        )
                        await asyncio.sleep(retry_after)
                        continue
                    raise SharePointRateLimitError("Rate limit exceeded", retry_after=retry_after)
                elif response.status_code >= 500:
                    if attempt < max_retries:
                        wait_time = (2 ** attempt) + 0.5
                        logger.warning(
                            "download_url_server_error",
                            status=response.status_code,
                            retry_in=wait_time,
                            attempt=attempt + 1,
                        )
                        await asyncio.sleep(wait_time)
                        continue

                response.raise_for_status()
                return response.content

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                if attempt < max_retries:
                    wait_time = (2 ** attempt) + 0.5
                    logger.warning(
                        "download_url_connection_error",
                        error=str(e),
                        retry_in=wait_time,
                        attempt=attempt + 1,
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise SharePointError(f"Download failed: {e}")

        raise SharePointError("Download failed after retries")

    # -------------------------------------------------------------------------
    # Delta (Change Detection)
    # -------------------------------------------------------------------------

    async def get_delta(
        self,
        site_id: str,
        drive_id: str,
        delta_token: Optional[str] = None,
    ) -> tuple[List[SharePointFile], Optional[str]]:
        """Get changed files using delta query.

        This is more efficient than listing all files when checking for changes.

        Args:
            site_id: SharePoint site ID.
            drive_id: Drive ID.
            delta_token: Previous delta token (None for initial sync).

        Returns:
            Tuple of (changed files, new delta token).
        """
        if delta_token:
            endpoint = f"/sites/{site_id}/drives/{drive_id}/root/delta?token={delta_token}"
        else:
            endpoint = f"/sites/{site_id}/drives/{drive_id}/root/delta"

        files: List[SharePointFile] = []
        next_link: Optional[str] = endpoint
        new_delta_token: Optional[str] = None

        while next_link:
            data = await self._fetch_paginated_url(next_link)

            for item in data.get("value", []):
                # Skip deleted items and folders
                if "deleted" in item or "folder" in item:
                    continue
                if "file" in item:
                    files.append(self._parse_file_item(item, site_id, drive_id))

            # Get next page or delta link
            next_link = data.get("@odata.nextLink")
            if "@odata.deltaLink" in data:
                # Extract token from delta link
                delta_link = data["@odata.deltaLink"]
                if "token=" in delta_link:
                    new_delta_token = delta_link.split("token=")[-1]

        return files, new_delta_token

    # -------------------------------------------------------------------------
    # BaseExternalAPIClient Interface
    # -------------------------------------------------------------------------

    async def fetch_all_records(self) -> List[ExternalAPIRecord]:
        """Fetch all files as ExternalAPIRecord objects.

        This is mainly for compatibility with the sync service.
        For crawling, use the SharePointCrawler instead.
        """
        if not settings.sharepoint_default_site_url:
            logger.warning("sharepoint_default_site_url_not_configured")
            return []

        try:
            hostname, site_path = parse_sharepoint_site_url(
                settings.sharepoint_default_site_url
            )
        except SharePointConfigError as e:
            logger.error("invalid_sharepoint_site_url", error=str(e))
            return []

        try:
            site = await self.get_site_by_url(hostname, site_path)
            drives = await self.list_drives(site.id)

            if not drives:
                return []

            # Use first drive
            drive = drives[0]
            files = await self.list_files(site.id, drive.id, recursive=True)

            records = []
            for file in files:
                records.append(ExternalAPIRecord(
                    external_id=file.id,
                    name=file.name,
                    raw_data={
                        "id": file.id,
                        "name": file.name,
                        "size": file.size,
                        "mime_type": file.mime_type,
                        "web_url": file.web_url,
                        "parent_path": file.parent_path,
                        "site_id": file.site_id,
                        "drive_id": file.drive_id,
                    },
                    location_hints=[],
                    modified_at=file.modified_at,
                ))

            return records

        except Exception as e:
            logger.error("sharepoint_fetch_all_records_error", error=str(e))
            raise

    async def test_connection(self) -> bool:
        """Test the SharePoint connection."""
        try:
            # Try to get token and list sites
            await self._get_access_token()
            await self.search_sites("*")
            return True
        except Exception as e:
            logger.warning(
                "sharepoint_connection_test_failed",
                error=str(e),
            )
            return False
