"""Website crawler using Scrapy and Playwright."""

import asyncio
import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
import structlog
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.services.crawler_progress import crawler_progress
from crawlers.base import BaseCrawler, CrawlResult
from crawlers.robots_txt import RobotsTxtChecker
from services.relevance_checker import check_relevance

logger = structlog.get_logger()

# Module-level HTTP client storage with loop tracking
_http_client: httpx.AsyncClient | None = None
_http_client_loop_id: int | None = None


async def get_shared_http_client() -> httpx.AsyncClient:
    """Get or create shared HTTP client with connection pooling.

    Uses a singleton pattern to reuse connections across crawl operations,
    improving performance by avoiding TCP handshake overhead.

    IMPORTANT: Tracks the event loop ID and recreates the client if the loop
    changes (e.g., when running in Celery tasks with new event loops).
    """
    global _http_client, _http_client_loop_id

    try:
        current_loop = asyncio.get_running_loop()
        current_loop_id = id(current_loop)
    except RuntimeError:
        current_loop_id = None

    # Check if we need to recreate the client (loop changed or client closed)
    needs_recreation = (
        _http_client is None
        or _http_client.is_closed
        or _http_client_loop_id != current_loop_id
    )

    if needs_recreation:
        # Close old client if it exists and is on a different loop
        if _http_client is not None and not _http_client.is_closed:
            try:  # noqa: SIM105
                await _http_client.aclose()
            except Exception:  # noqa: S110
                pass  # Ignore errors when closing stale client

        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
                keepalive_expiry=30.0,
            ),
            headers={"User-Agent": settings.crawler_user_agent},
            follow_redirects=True,
        )
        _http_client_loop_id = current_loop_id

    return _http_client


async def close_shared_http_client() -> None:
    """Close the shared HTTP client. Call during shutdown."""
    global _http_client, _http_client_loop_id
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None
        _http_client_loop_id = None


class WebsiteCrawler(BaseCrawler):
    """
    General-purpose website crawler.

    Supports both static HTML pages and JavaScript-rendered pages (via Playwright).
    """

    def __init__(self, respect_robots: bool = True):
        """
        Initialize the website crawler.

        Args:
            respect_robots: If True, respects robots.txt directives (default: True)
        """
        super().__init__()
        self.visited_urls: set[str] = set()
        self.document_urls: set[str] = set()
        self.html_documents: list[dict[str, Any]] = []  # Captured HTML pages
        self.url_include_patterns: list[re.Pattern] = []
        self.url_exclude_patterns: list[re.Pattern] = []
        self.filtered_urls_count: int = 0
        self.robots_blocked_count: int = 0
        self.capture_html_content: bool = True  # Enable HTML content capture by default
        self.html_min_relevance_score: float = 0.2  # Minimum relevance score to capture

        # robots.txt compliance
        self.respect_robots = respect_robots
        self.robots_checker = RobotsTxtChecker(
            user_agent=settings.crawler_user_agent,
            respect_robots=respect_robots,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _fetch_with_retry(
        self, client: httpx.AsyncClient, url: str
    ) -> httpx.Response:
        """Fetch URL with automatic retry on transient errors.

        Retries up to 3 times with exponential backoff (1s, 2s, 4s) on:
        - Connection errors (network issues)
        - Timeout errors

        Does NOT retry on HTTP errors (4xx, 5xx) as those are typically
        permanent failures that won't resolve with retry.
        """
        response = await client.get(url)
        response.raise_for_status()
        return response

    def _compile_url_patterns(self, config: dict[str, Any], category=None) -> None:
        """
        Compile URL include/exclude regex patterns from config and category.

        Priority: Source config patterns override category patterns.
        If source has patterns, use those. Otherwise, use category patterns.
        """
        self.url_include_patterns = []
        self.url_exclude_patterns = []
        self.filtered_urls_count = 0

        # Get patterns from source config (takes priority)
        include_patterns = config.get("url_include_patterns", [])
        exclude_patterns = config.get("url_exclude_patterns", [])

        # If source has no patterns, use category patterns
        if not include_patterns and category and category.url_include_patterns:
            include_patterns = category.url_include_patterns
            self.logger.info(
                "Using category URL include patterns",
                category=category.name,
                pattern_count=len(include_patterns),
            )

        if not exclude_patterns and category and category.url_exclude_patterns:
            exclude_patterns = category.url_exclude_patterns
            self.logger.info(
                "Using category URL exclude patterns",
                category=category.name,
                pattern_count=len(exclude_patterns),
            )

        for pattern in include_patterns:
            try:
                self.url_include_patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                self.logger.warning("Invalid include pattern", pattern=pattern, error=str(e))

        for pattern in exclude_patterns:
            try:
                self.url_exclude_patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                self.logger.warning("Invalid exclude pattern", pattern=pattern, error=str(e))

    def _should_crawl_url(self, url: str) -> bool:
        """
        Check if URL should be crawled based on include/exclude patterns.

        Note: This does NOT check robots.txt (async operation).
        Use _should_crawl_url_full() for complete check including robots.txt.

        Returns True if URL passes all pattern filters.
        """
        # Check exclude patterns first (blacklist)
        for pattern in self.url_exclude_patterns:
            if pattern.search(url):
                self.filtered_urls_count += 1
                return False

        # Check include patterns (whitelist) - if set, URL must match at least one
        if self.url_include_patterns and not any(pattern.search(url) for pattern in self.url_include_patterns):
            self.filtered_urls_count += 1
            return False

        return True

    async def _should_crawl_url_full(self, url: str) -> bool:
        """
        Check if URL should be crawled based on all criteria including robots.txt.

        This is the full async version that also checks robots.txt compliance.

        Returns True if URL passes all filters AND robots.txt allows it.
        """
        # First check pattern filters (fast, synchronous)
        if not self._should_crawl_url(url):
            return False

        # Then check robots.txt (async, may need network request)
        if self.respect_robots and not await self.robots_checker.can_fetch(url):
            self.robots_blocked_count += 1
            self.logger.debug("url_blocked_by_robots_txt", url=url)
            return False

        return True

    def _extract_html_text(self, soup: BeautifulSoup) -> str:
        """Extract clean text from HTML for relevance checking."""
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()

        return soup.get_text(separator="\n", strip=True)

    def _get_page_title(self, soup: BeautifulSoup) -> str | None:
        """Extract page title from HTML."""
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)
        h1_tag = soup.find("h1")
        if h1_tag:
            return h1_tag.get_text(strip=True)
        return None

    async def _check_and_capture_html(
        self,
        url: str,
        html_content: str,
        soup: BeautifulSoup,
        category,
    ) -> bool:
        """
        Check HTML page for relevance and capture if relevant.

        Returns True if page was captured.
        """
        if not self.capture_html_content:
            return False

        # Extract text for relevance check
        text = self._extract_html_text(soup)
        title = self._get_page_title(soup)

        # Check relevance
        relevance = check_relevance(text, title=title, category=category)

        if relevance.score >= self.html_min_relevance_score:
            # Store for later document creation
            self.html_documents.append({
                "url": url,
                "title": title,
                "html_content": html_content,
                "text_content": text,
                "relevance_score": relevance.score,
                "matched_keywords": relevance.matched_keywords,
            })

            self.logger.info(
                "Captured relevant HTML page",
                url=url,
                title=title,
                score=relevance.score,
                keywords=relevance.matched_keywords[:5],
            )
            return True

        return False

    async def crawl(self, source, job) -> CrawlResult:
        """Crawl a website for documents."""
        from app.database import get_session_context
        from app.models import Category, Document, ProcessingStatus

        result = CrawlResult()
        config = source.crawl_config or {}

        max_depth = config.get("max_depth", 3)
        max_pages = config.get("max_pages", 100)
        download_extensions = config.get(
            "download_extensions",
            ["pdf", "doc", "docx", "xls", "xlsx"],
        )
        render_javascript = config.get("render_javascript", False)

        self.visited_urls = set()
        self.document_urls = set()
        self.html_documents = []
        self.filtered_urls_count = 0
        self.robots_blocked_count = 0

        # Config for HTML content capture
        self.capture_html_content = config.get("capture_html_content", True)
        self.html_min_relevance_score = config.get("html_min_relevance_score", 0.2)

        # Config for robots.txt compliance (default: True for ethical crawling)
        self.respect_robots = config.get("respect_robots", True)
        self.robots_checker.respect_robots = self.respect_robots

        # Load category for URL patterns and document storage
        # Use job.category_id - each job crawls with its own category's patterns
        category = None
        async with get_session_context() as session:
            category = await session.get(Category, job.category_id)

        # Compile URL filter patterns from job's category
        self._compile_url_patterns(config, category)

        try:
            self.logger.info(
                "Starting website crawl",
                url=source.base_url,
                max_depth=max_depth,
                render_js=render_javascript,
                include_patterns=len(self.url_include_patterns),
                exclude_patterns=len(self.url_exclude_patterns),
            )

            if render_javascript:
                await self._crawl_with_playwright(
                    source.base_url, max_depth, max_pages, download_extensions, result, job, category
                )
            else:
                await self._crawl_with_httpx(
                    source.base_url, max_depth, max_pages, download_extensions, result, job, category
                )

            # Save found documents
            from sqlalchemy import select
            async with get_session_context() as session:
                for doc_url in self.document_urls:
                    # Determine document type from URL
                    ext = doc_url.split(".")[-1].lower().split("?")[0]
                    doc_type = ext.upper() if ext in download_extensions else "HTML"

                    # Create hash from URL
                    file_hash = self.compute_text_hash(doc_url)

                    # Check if exists for this category (same doc can exist for different categories)
                    existing = await session.execute(
                        select(Document).where(
                            Document.source_id == source.id,
                            Document.category_id == job.category_id,
                            Document.file_hash == file_hash,
                        )
                    )
                    if existing.scalar():
                        continue

                    doc = Document(
                        source_id=source.id,
                        category_id=job.category_id,  # Use job's category, not source's
                        crawl_job_id=job.id,
                        document_type=doc_type,
                        original_url=doc_url,
                        file_hash=file_hash,
                        processing_status=ProcessingStatus.PENDING,
                    )
                    session.add(doc)
                    result.documents_new += 1

                # Save captured HTML pages as documents
                for html_doc in self.html_documents:
                    # Create hash from URL for deduplication
                    file_hash = self.compute_text_hash(html_doc["url"])

                    # Check if already exists for this category
                    existing = await session.execute(
                        select(Document).where(
                            Document.source_id == source.id,
                            Document.category_id == job.category_id,
                            Document.file_hash == file_hash,
                        )
                    )
                    if existing.scalar():
                        continue

                    # Save HTML content to file
                    storage_path = Path(settings.document_storage_path)
                    category_path = storage_path / str(job.category_id)
                    category_path.mkdir(parents=True, exist_ok=True)

                    doc_id = hashlib.sha256(html_doc["url"].encode()).hexdigest()[:16]
                    html_file = category_path / f"{doc_id}.html"
                    html_file.write_text(html_doc["html_content"], encoding="utf-8")

                    # Create document with pre-extracted text
                    doc = Document(
                        source_id=source.id,
                        category_id=job.category_id,  # Use job's category
                        crawl_job_id=job.id,
                        document_type="HTML",
                        original_url=html_doc["url"],
                        title=html_doc["title"],
                        file_path=str(html_file),
                        file_hash=file_hash,
                        file_size=len(html_doc["html_content"]),
                        raw_text=html_doc["text_content"].replace('\x00', ''),  # Pre-extracted text
                        processing_status=ProcessingStatus.COMPLETED,  # Skip download, go to analysis
                        downloaded_at=datetime.now(UTC),
                        processed_at=datetime.now(UTC),
                    )
                    session.add(doc)
                    await session.flush()  # Get the doc.id
                    result.documents_new += 1

                    # Queue for AI analysis (relevance already checked during crawl)
                    from workers.ai_tasks import analyze_document as analyze_doc_task
                    analyze_doc_task.delay(str(doc.id), skip_relevance_check=True)

                    self.logger.info(
                        "Saved HTML document and queued for AI analysis",
                        url=html_doc["url"],
                        title=html_doc["title"],
                        relevance_score=html_doc["relevance_score"],
                        document_id=str(doc.id),
                    )

                await session.commit()

            result.documents_found = len(self.document_urls) + len(self.html_documents)
            result.documents_processed = result.documents_new
            result.stats = {
                "pages_visited": len(self.visited_urls),
                "documents_found": len(self.document_urls),
                "html_pages_captured": len(self.html_documents),
                "urls_filtered": self.filtered_urls_count,
                "urls_blocked_by_robots": self.robots_blocked_count,
            }

        except Exception as e:
            self.logger.exception("Website crawl failed", error=str(e))
            result.errors.append({
                "error": str(e),
                "type": type(e).__name__,
            })

        return result

    async def _crawl_with_httpx(
        self,
        start_url: str,
        max_depth: int,
        max_pages: int,
        download_extensions: list[str],
        result: CrawlResult,
        job,
        category=None,
    ):
        """Crawl using httpx for static pages.

        Uses shared HTTP client with connection pooling for improved performance.
        Includes automatic retry with exponential backoff for transient errors.
        """
        queue = [(start_url, 0)]  # (url, depth)
        base_domain = urlparse(start_url).netloc

        # Use shared client with connection pooling
        client = await get_shared_http_client()

        while queue and len(self.visited_urls) < max_pages:
            url, depth = queue.pop(0)

            if url in self.visited_urls:
                continue
            if depth > max_depth:
                continue

            # Check URL filter patterns and robots.txt (but always allow the start URL to discover links)
            is_start_url = url == start_url
            if not is_start_url and not await self._should_crawl_url_full(url):
                await crawler_progress.log_url(job.id, url, status="filtered")
                continue

            # Check if it's a document
            ext = url.split(".")[-1].lower().split("?")[0]
            if ext in download_extensions:
                self.document_urls.add(url)
                self.visited_urls.add(url)
                # Log document found and update live stats
                await crawler_progress.log_url(job.id, url, status="document", doc_found=True)
                await crawler_progress.increment_documents(job.id)
                continue

            try:
                # Use retry-enabled fetch method
                response = await self._fetch_with_retry(client, url)
                self.visited_urls.add(url)
                result.pages_crawled += 1

                # Log the URL being crawled and update live stats
                await crawler_progress.log_url(job.id, url, status="fetched")
                await crawler_progress.increment_pages(job.id)

                # Parse HTML
                html_content = response.text
                soup = BeautifulSoup(html_content, "lxml")

                # Check and capture HTML content if relevant
                if self.capture_html_content:
                    await self._check_and_capture_html(url, html_content, soup, category)

                # Find all links
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    full_url = urljoin(url, href)

                    # Check if same domain
                    if urlparse(full_url).netloc != base_domain:
                        continue

                    # Check if document (PDF, DOC, etc.) - always collect these
                    link_ext = full_url.split(".")[-1].lower().split("?")[0]
                    if link_ext in download_extensions:
                        if full_url not in self.document_urls:
                            self.document_urls.add(full_url)
                            await crawler_progress.increment_documents(job.id)
                        continue

                    # Check URL filter patterns for non-document links
                    # Note: robots.txt is checked when URL is dequeued, not here
                    if not self._should_crawl_url(full_url):
                        continue

                    # Add to crawl queue
                    if full_url not in self.visited_urls:
                        queue.append((full_url, depth + 1))

                # Rate limiting
                await asyncio.sleep(settings.crawler_default_delay)

            except Exception as e:
                self.logger.warning("Failed to fetch page", url=url, error=str(e))
                await crawler_progress.log_url(job.id, url, status="error")

    async def _crawl_with_playwright(
        self,
        start_url: str,
        max_depth: int,
        max_pages: int,
        download_extensions: list[str],
        result: CrawlResult,
        job,
        category=None,
    ):
        """Crawl using Playwright for JavaScript-rendered pages."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            self.logger.error("Playwright not installed, falling back to httpx")
            await self._crawl_with_httpx(
                start_url, max_depth, max_pages, download_extensions, result, job, category
            )
            return

        queue = [(start_url, 0)]
        base_domain = urlparse(start_url).netloc

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_extra_http_headers({
                "User-Agent": settings.crawler_user_agent
            })

            while queue and len(self.visited_urls) < max_pages:
                url, depth = queue.pop(0)

                if url in self.visited_urls:
                    continue
                if depth > max_depth:
                    continue

                # Check URL filter patterns and robots.txt (but always allow the start URL to discover links)
                is_start_url = url == start_url
                if not is_start_url and not await self._should_crawl_url_full(url):
                    continue

                # Check if it's a document
                ext = url.split(".")[-1].lower().split("?")[0]
                if ext in download_extensions:
                    self.document_urls.add(url)
                    self.visited_urls.add(url)
                    continue

                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    self.visited_urls.add(url)
                    result.pages_crawled += 1

                    # Update live stats
                    await crawler_progress.log_url(job.id, url, status="fetched")
                    await crawler_progress.increment_pages(job.id)

                    # Get page content and check relevance
                    if self.capture_html_content:
                        html_content = await page.content()
                        soup = BeautifulSoup(html_content, "lxml")
                        await self._check_and_capture_html(url, html_content, soup, category)

                    # Get all links
                    links = await page.eval_on_selector_all(
                        "a[href]",
                        "elements => elements.map(el => el.href)"
                    )

                    for link_url in links:
                        if not link_url:
                            continue

                        # Check if same domain
                        if urlparse(link_url).netloc != base_domain:
                            continue

                        # Check if document (PDF, DOC, etc.) - always collect these
                        link_ext = link_url.split(".")[-1].lower().split("?")[0]
                        if link_ext in download_extensions:
                            if link_url not in self.document_urls:
                                self.document_urls.add(link_url)
                                await crawler_progress.increment_documents(job.id)
                            continue

                        # Check URL filter patterns for non-document links
                        if not self._should_crawl_url(link_url):
                            continue

                        # Add to crawl queue
                        if link_url not in self.visited_urls:
                            queue.append((link_url, depth + 1))

                    # Rate limiting
                    await asyncio.sleep(settings.crawler_default_delay)

                except Exception as e:
                    self.logger.warning("Failed to fetch page", url=url, error=str(e))
                    await crawler_progress.log_url(job.id, url, status="error")

            await browser.close()

    async def detect_changes(self, source) -> bool:
        """
        Detect changes using HTTP conditional requests (304 Not Modified).

        Uses If-Modified-Since and If-None-Match headers to efficiently
        check if content has changed without downloading the full response.

        Returns:
            True if changes detected or headers suggest modification
            False if 304 Not Modified received
        """
        try:
            # Use conditional fetch with stored headers
            content, headers, was_modified = await self.fetch_with_conditional(
                source.base_url,
                last_modified=source.last_modified_header,
                etag=source.etag_header,
            )

            if not was_modified:
                # 304 Not Modified - no changes
                self.logger.debug(
                    "No changes detected (304)",
                    url=source.base_url,
                )
                return False

            # Content was fetched - compare hash if we have one
            if content:
                new_hash = self.compute_hash(content)
                if source.content_hash and source.content_hash == new_hash:
                    # Content hash same despite no 304 - no real change
                    return False

            return True

        except Exception as e:
            self.logger.error("Change detection failed", error=str(e))
            # On error, assume changes to be safe
            return True

    async def update_source_headers(self, source, headers: dict) -> None:
        """
        Update source with new HTTP headers after successful fetch.

        Should be called after a successful crawl to store Last-Modified and ETag
        for future conditional requests.
        """
        from app.database import get_session_context

        last_modified = headers.get("last-modified")
        etag = headers.get("etag")

        if last_modified or etag:
            async with get_session_context() as session:
                from sqlalchemy import update

                from app.models import DataSource

                await session.execute(
                    update(DataSource)
                    .where(DataSource.id == source.id)
                    .values(
                        last_modified_header=last_modified,
                        etag_header=etag,
                    )
                )
                await session.commit()

                self.logger.debug(
                    "Updated source headers",
                    source_id=str(source.id),
                    last_modified=last_modified,
                    etag=etag,
                )
