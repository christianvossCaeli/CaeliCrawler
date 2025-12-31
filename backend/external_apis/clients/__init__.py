"""External API client implementations."""

from external_apis.clients.auction_client import CaeliAuctionClient
from external_apis.clients.sharepoint_client import (
    SharePointAuthError,
    SharePointClient,
    SharePointConfigError,
    SharePointError,
    SharePointNotFoundError,
    SharePointPermissionError,
    SharePointRateLimitError,
    parse_sharepoint_site_url,
)

__all__ = [
    "CaeliAuctionClient",
    "SharePointClient",
    "SharePointError",
    "SharePointAuthError",
    "SharePointConfigError",
    "SharePointNotFoundError",
    "SharePointPermissionError",
    "SharePointRateLimitError",
    "parse_sharepoint_site_url",
]
