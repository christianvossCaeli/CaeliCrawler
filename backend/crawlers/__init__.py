"""
CaeliCrawler - Crawlers and API Clients.

Supported data sources:
- OParl: German municipal council information systems
- GovData: German Open Government Data Portal (CKAN)
- DIP Bundestag: Parliamentary documentation system
- FragDenStaat: Freedom of Information requests
- RSS/Atom: News feeds and official gazettes
- Websites: General web scraping with Playwright support
"""

from crawlers.base import BaseCrawler, CrawlResult, get_crawler_for_source
from crawlers.oparl_crawler import OparlCrawler
from crawlers.website_crawler import WebsiteCrawler
from crawlers.rss_crawler import RSSCrawler, GERMAN_GOVERNMENT_FEEDS
from crawlers.unified_crawler import (
    UnifiedCrawlerService,
    DataSourceType,
    UnifiedSearchQuery,
    UnifiedSearchResult,
    quick_search,
)

from crawlers.api_clients import (
    BaseAPIClient,
    OparlClient,
    GovDataClient,
    DIPBundestagClient,
    FragDenStaatClient,
)
from crawlers.api_clients.oparl_client import KNOWN_OPARL_ENDPOINTS

__all__ = [
    # Base
    "BaseCrawler",
    "CrawlResult",
    "get_crawler_for_source",

    # Crawlers
    "OparlCrawler",
    "WebsiteCrawler",
    "RSSCrawler",

    # Unified Service
    "UnifiedCrawlerService",
    "DataSourceType",
    "UnifiedSearchQuery",
    "UnifiedSearchResult",
    "quick_search",

    # API Clients
    "BaseAPIClient",
    "OparlClient",
    "GovDataClient",
    "DIPBundestagClient",
    "FragDenStaatClient",

    # Constants
    "KNOWN_OPARL_ENDPOINTS",
    "GERMAN_GOVERNMENT_FEEDS",
]
