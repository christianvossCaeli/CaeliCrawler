"""External API Integration Framework.

This module provides a standardized framework for integrating external APIs
into the CaeliCrawler system. Unlike crawlers that scrape websites, external
APIs provide structured data that can be synchronized directly to entities.

Key components:
- BaseExternalAPIClient: Abstract base for API clients
- ExternalAPISyncService: Handles synchronization logic
- EntityLinkingService: AI-powered entity linking
- CaeliAuctionClient: Specific client for Caeli Auction API

Usage:
    from external_apis import ExternalAPISyncService
    from external_apis.clients import CaeliAuctionClient

    service = ExternalAPISyncService(session)
    result = await service.sync_source(config)
"""

from external_apis.base import (
    BaseExternalAPIClient,
    ExternalAPIRecord,
    SyncResult,
)

__all__ = [
    "BaseExternalAPIClient",
    "ExternalAPIRecord",
    "SyncResult",
]
