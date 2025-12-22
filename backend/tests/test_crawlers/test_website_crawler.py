"""Unit tests for WebsiteCrawler functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from crawlers.website_crawler import (
    WebsiteCrawler,
    get_shared_http_client,
    close_shared_http_client,
)


class TestWebsiteCrawlerUrlPatterns:
    """Tests for URL pattern filtering functionality."""

    def setup_method(self):
        """Set up test instance."""
        self.crawler = WebsiteCrawler()

    def test_should_crawl_url_no_patterns(self):
        """Test that all URLs pass when no patterns are set."""
        self.crawler._compile_url_patterns({}, None)

        assert self.crawler._should_crawl_url("https://example.com/news/article")
        assert self.crawler._should_crawl_url("https://example.com/about")
        assert self.crawler._should_crawl_url("https://example.com/contact")

    def test_should_crawl_url_with_include_patterns(self):
        """Test URL filtering with include patterns."""
        config = {"url_include_patterns": [r"/news/", r"/aktuelles/"]}
        self.crawler._compile_url_patterns(config, None)

        # Should match include patterns
        assert self.crawler._should_crawl_url("https://example.com/news/article")
        assert self.crawler._should_crawl_url("https://example.com/aktuelles/2024")

        # Should NOT match include patterns
        assert not self.crawler._should_crawl_url("https://example.com/about")
        assert not self.crawler._should_crawl_url("https://example.com/contact")

    def test_should_crawl_url_with_exclude_patterns(self):
        """Test URL filtering with exclude patterns."""
        config = {"url_exclude_patterns": [r"/login", r"/admin", r"\.pdf$"]}
        self.crawler._compile_url_patterns(config, None)

        # Should be excluded
        assert not self.crawler._should_crawl_url("https://example.com/login")
        assert not self.crawler._should_crawl_url("https://example.com/admin/dashboard")
        assert not self.crawler._should_crawl_url("https://example.com/doc.pdf")

        # Should NOT be excluded
        assert self.crawler._should_crawl_url("https://example.com/news/article")
        assert self.crawler._should_crawl_url("https://example.com/about")

    def test_should_crawl_url_exclude_takes_priority(self):
        """Test that exclude patterns take priority over include."""
        config = {
            "url_include_patterns": [r"/news/"],
            "url_exclude_patterns": [r"/news/private/"],
        }
        self.crawler._compile_url_patterns(config, None)

        # Matches include but also exclude - should be excluded
        assert not self.crawler._should_crawl_url("https://example.com/news/private/article")

        # Matches include only - should pass
        assert self.crawler._should_crawl_url("https://example.com/news/public/article")

    def test_should_crawl_url_case_insensitive(self):
        """Test that pattern matching is case insensitive."""
        config = {"url_include_patterns": [r"/news/"]}
        self.crawler._compile_url_patterns(config, None)

        assert self.crawler._should_crawl_url("https://example.com/NEWS/article")
        assert self.crawler._should_crawl_url("https://example.com/News/article")
        assert self.crawler._should_crawl_url("https://example.com/news/article")

    def test_compile_url_patterns_invalid_regex(self):
        """Test handling of invalid regex patterns."""
        config = {"url_include_patterns": [r"[invalid regex", r"/valid/"]}
        self.crawler._compile_url_patterns(config, None)

        # Should only have the valid pattern
        assert len(self.crawler.url_include_patterns) == 1

    def test_compile_url_patterns_from_category(self):
        """Test that category patterns are used when source has none."""
        category = MagicMock()
        category.name = "Test Category"
        category.url_include_patterns = [r"/news/"]
        category.url_exclude_patterns = [r"/archive/"]

        self.crawler._compile_url_patterns({}, category)

        assert len(self.crawler.url_include_patterns) == 1
        assert len(self.crawler.url_exclude_patterns) == 1

    def test_compile_url_patterns_source_overrides_category(self):
        """Test that source patterns override category patterns."""
        category = MagicMock()
        category.name = "Test Category"
        category.url_include_patterns = [r"/category-pattern/"]
        category.url_exclude_patterns = [r"/category-exclude/"]

        config = {"url_include_patterns": [r"/source-pattern/"]}
        self.crawler._compile_url_patterns(config, category)

        # Source include patterns should be used
        assert len(self.crawler.url_include_patterns) == 1
        # Category exclude patterns should still be used (source has none)
        assert len(self.crawler.url_exclude_patterns) == 1

    def test_filtered_urls_count(self):
        """Test that filtered URLs are counted."""
        config = {"url_include_patterns": [r"/news/"]}
        self.crawler._compile_url_patterns(config, None)

        # Reset counter
        self.crawler.filtered_urls_count = 0

        # These should be filtered
        self.crawler._should_crawl_url("https://example.com/about")
        self.crawler._should_crawl_url("https://example.com/contact")

        assert self.crawler.filtered_urls_count == 2


class TestWebsiteCrawlerHtmlExtraction:
    """Tests for HTML content extraction."""

    def setup_method(self):
        """Set up test instance."""
        self.crawler = WebsiteCrawler()

    def test_get_page_title_from_title_tag(self):
        """Test extracting title from <title> tag."""
        from bs4 import BeautifulSoup

        html = "<html><head><title>Test Page Title</title></head><body></body></html>"
        soup = BeautifulSoup(html, "lxml")

        title = self.crawler._get_page_title(soup)
        assert title == "Test Page Title"

    def test_get_page_title_from_h1(self):
        """Test extracting title from <h1> when no <title>."""
        from bs4 import BeautifulSoup

        html = "<html><head></head><body><h1>Heading Title</h1></body></html>"
        soup = BeautifulSoup(html, "lxml")

        title = self.crawler._get_page_title(soup)
        assert title == "Heading Title"

    def test_get_page_title_none(self):
        """Test returning None when no title found."""
        from bs4 import BeautifulSoup

        html = "<html><head></head><body><p>Just text</p></body></html>"
        soup = BeautifulSoup(html, "lxml")

        title = self.crawler._get_page_title(soup)
        assert title is None

    def test_extract_html_text_removes_scripts(self):
        """Test that scripts are removed from extracted text."""
        from bs4 import BeautifulSoup

        html = """
        <html>
            <body>
                <p>Visible text</p>
                <script>alert('malicious');</script>
                <p>More text</p>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "lxml")

        text = self.crawler._extract_html_text(soup)

        assert "Visible text" in text
        assert "More text" in text
        assert "alert" not in text
        assert "malicious" not in text

    def test_extract_html_text_removes_navigation(self):
        """Test that nav/header/footer are removed."""
        from bs4 import BeautifulSoup

        html = """
        <html>
            <body>
                <header>Site Header</header>
                <nav>Navigation Menu</nav>
                <main>Main Content</main>
                <footer>Site Footer</footer>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "lxml")

        text = self.crawler._extract_html_text(soup)

        assert "Main Content" in text
        assert "Site Header" not in text
        assert "Navigation Menu" not in text
        assert "Site Footer" not in text


class TestWebsiteCrawlerRetry:
    """Tests for retry functionality."""

    def setup_method(self):
        """Set up test instance."""
        self.crawler = WebsiteCrawler()

    @pytest.mark.asyncio
    async def test_fetch_with_retry_success(self):
        """Test successful fetch on first try."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        response = await self.crawler._fetch_with_retry(mock_client, "https://example.com")

        assert response == mock_response
        mock_client.get.assert_called_once_with("https://example.com")

    @pytest.mark.asyncio
    async def test_fetch_with_retry_recovers_from_timeout(self):
        """Test that fetch retries on timeout and eventually succeeds."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        # Fail twice with timeout, then succeed
        mock_client.get = AsyncMock(
            side_effect=[
                httpx.TimeoutException("Timeout 1"),
                httpx.TimeoutException("Timeout 2"),
                mock_response,
            ]
        )

        response = await self.crawler._fetch_with_retry(mock_client, "https://example.com")

        assert response == mock_response
        assert mock_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_fetch_with_retry_fails_after_max_attempts(self):
        """Test that fetch raises after max retry attempts."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.TimeoutException("Persistent timeout")
        )

        with pytest.raises(httpx.TimeoutException):
            await self.crawler._fetch_with_retry(mock_client, "https://example.com")

        # Should have tried 3 times (initial + 2 retries)
        assert mock_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_fetch_with_retry_does_not_retry_http_errors(self):
        """Test that HTTP errors (4xx, 5xx) are not retried."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "404 Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404),
            )
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with pytest.raises(httpx.HTTPStatusError):
            await self.crawler._fetch_with_retry(mock_client, "https://example.com")

        # Should NOT retry on HTTP errors
        assert mock_client.get.call_count == 1


class TestSharedHttpClient:
    """Tests for shared HTTP client singleton."""

    @pytest.mark.asyncio
    async def test_get_shared_client_creates_client(self):
        """Test that get_shared_http_client creates a client."""
        # Close any existing client first
        await close_shared_http_client()

        client = await get_shared_http_client()

        assert client is not None
        assert isinstance(client, httpx.AsyncClient)
        assert not client.is_closed

        # Clean up
        await close_shared_http_client()

    @pytest.mark.asyncio
    async def test_get_shared_client_returns_same_instance(self):
        """Test that get_shared_http_client returns the same instance."""
        await close_shared_http_client()

        client1 = await get_shared_http_client()
        client2 = await get_shared_http_client()

        assert client1 is client2

        await close_shared_http_client()

    @pytest.mark.asyncio
    async def test_close_shared_client(self):
        """Test that close_shared_http_client closes the client."""
        client = await get_shared_http_client()

        await close_shared_http_client()

        # Getting a new client should create a new instance
        new_client = await get_shared_http_client()
        assert new_client is not client

        await close_shared_http_client()


class TestWebsiteCrawlerConfiguration:
    """Tests for crawler configuration."""

    def test_default_configuration(self):
        """Test default crawler configuration."""
        crawler = WebsiteCrawler()

        assert crawler.capture_html_content is True
        assert crawler.html_min_relevance_score == 0.2
        assert crawler.visited_urls == set()
        assert crawler.document_urls == set()
        assert crawler.html_documents == []

    def test_reset_state_between_crawls(self):
        """Test that state is properly reset."""
        crawler = WebsiteCrawler()

        # Simulate previous crawl state
        crawler.visited_urls = {"https://old.com"}
        crawler.document_urls = {"https://old.com/doc.pdf"}
        crawler.html_documents = [{"url": "https://old.com"}]
        crawler.filtered_urls_count = 5

        # Compile patterns (which should reset filter count)
        crawler._compile_url_patterns({}, None)

        assert crawler.filtered_urls_count == 0
        assert crawler.url_include_patterns == []
        assert crawler.url_exclude_patterns == []
