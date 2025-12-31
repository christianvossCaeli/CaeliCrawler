"""Base crawler class and utilities."""

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import httpx
import structlog

if TYPE_CHECKING:
    from app.models import CrawlJob, DataSource

logger = structlog.get_logger()


@dataclass
class CrawlResult:
    """Result of a crawl operation."""

    pages_crawled: int = 0
    documents_found: int = 0
    documents_processed: int = 0
    documents_new: int = 0
    documents_updated: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)


class BaseCrawler(ABC):
    """Abstract base class for all crawlers."""

    def __init__(self):
        self.logger = structlog.get_logger(crawler=self.__class__.__name__)

    @abstractmethod
    async def crawl(self, source: "DataSource", job: "CrawlJob") -> CrawlResult:
        """
        Perform the crawl operation.

        Args:
            source: The data source to crawl
            job: The crawl job tracking this operation

        Returns:
            CrawlResult with statistics about the crawl
        """
        pass

    @abstractmethod
    async def detect_changes(self, source: "DataSource") -> bool:
        """
        Detect if there are changes on the source without full crawl.

        Args:
            source: The data source to check

        Returns:
            True if changes were detected
        """
        pass

    @staticmethod
    def compute_hash(content: bytes) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def compute_text_hash(text: str) -> str:
        """Compute SHA256 hash of text content."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def fetch_with_conditional(
        self,
        url: str,
        last_modified: str | None = None,
        etag: str | None = None,
        timeout: int = 30,
    ) -> tuple[bytes | None, dict[str, str], bool]:
        """
        Fetch URL with HTTP conditional request headers.

        Uses If-Modified-Since and If-None-Match headers to avoid
        downloading unchanged content (HTTP 304 Not Modified).

        Args:
            url: URL to fetch
            last_modified: Previous Last-Modified header value
            etag: Previous ETag header value
            timeout: Request timeout in seconds

        Returns:
            Tuple of (content, headers, was_modified):
            - content: Response bytes or None if 304
            - headers: Response headers dict
            - was_modified: True if content changed, False if 304
        """
        headers = {}
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        if etag:
            headers["If-None-Match"] = etag

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=headers,
                    follow_redirects=True,
                    timeout=timeout,
                )

                response_headers = dict(response.headers)

                if response.status_code == 304:
                    self.logger.debug(
                        "Content not modified (304)",
                        url=url,
                    )
                    return None, response_headers, False

                response.raise_for_status()
                return response.content, response_headers, True

        except httpx.HTTPStatusError as e:
            self.logger.warning(
                "HTTP error during conditional fetch",
                url=url,
                status_code=e.response.status_code,
            )
            raise
        except httpx.RequestError as e:
            self.logger.warning(
                "Request error during conditional fetch",
                url=url,
                error=str(e),
            )
            raise


def get_crawler_for_source(source: "DataSource") -> BaseCrawler:
    """
    Get the appropriate crawler for a data source.

    Args:
        source: The data source

    Returns:
        An instance of the appropriate crawler
    """
    from app.models import SourceType
    from crawlers.api_crawler import APICrawler
    from crawlers.entity_api_crawler import EntityAPICrawler
    from crawlers.news_crawler import NewsCrawler
    from crawlers.oparl_crawler import OparlCrawler
    from crawlers.sharepoint_crawler import SharePointCrawler
    from crawlers.website_crawler import WebsiteCrawler

    crawl_config = source.crawl_config or {}

    # SharePoint uses SharePointCrawler
    if source.source_type == SourceType.SHAREPOINT:
        return SharePointCrawler()

    # REST_API and SPARQL_API use EntityAPICrawler for Entity updates
    if source.source_type in (SourceType.REST_API, SourceType.SPARQL_API):
        return EntityAPICrawler()

    # For CUSTOM_API, check if it's a known API type
    if source.source_type == SourceType.CUSTOM_API:
        api_type = crawl_config.get("api_type", "").lower()

        # Use specialized API crawler for known API types
        if api_type in ("govdata", "dip_bundestag", "fragdenstaat"):
            return APICrawler()

    # For WEBSITE, check if it's a news crawl
    if source.source_type == SourceType.WEBSITE:
        crawl_type = crawl_config.get("crawl_type", "").lower()
        if crawl_type in ("news", "rss", "aktuelles"):
            return NewsCrawler()

    # RSS always uses news crawler
    if source.source_type == SourceType.RSS:
        return NewsCrawler()

    crawler_map = {
        SourceType.OPARL_API: OparlCrawler,
        SourceType.WEBSITE: WebsiteCrawler,
        SourceType.CUSTOM_API: WebsiteCrawler,  # Fallback for unknown custom APIs
    }

    crawler_class = crawler_map.get(source.source_type, WebsiteCrawler)
    return crawler_class()
