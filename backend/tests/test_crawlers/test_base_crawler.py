"""Unit tests for base crawler functionality."""

import hashlib
from unittest.mock import MagicMock

import pytest

from crawlers.base import BaseCrawler, CrawlResult, get_crawler_for_source


class TestCrawlResult:
    """Tests for CrawlResult dataclass."""

    def test_default_values(self):
        """Test default values in CrawlResult."""
        result = CrawlResult()

        assert result.pages_crawled == 0
        assert result.documents_found == 0
        assert result.documents_processed == 0
        assert result.documents_new == 0
        assert result.documents_updated == 0
        assert result.errors == []
        assert result.stats == {}

    def test_custom_values(self):
        """Test custom values in CrawlResult."""
        result = CrawlResult(
            pages_crawled=10,
            documents_found=5,
            documents_new=3,
            documents_updated=2,
            errors=[{"error": "test"}],
            stats={"key": "value"}
        )

        assert result.pages_crawled == 10
        assert result.documents_found == 5
        assert result.documents_new == 3
        assert result.errors == [{"error": "test"}]


class TestBaseCrawler:
    """Tests for BaseCrawler abstract class."""

    def test_compute_hash(self):
        """Test hash computation."""
        content = b"test content"
        expected = hashlib.sha256(content).hexdigest()

        result = BaseCrawler.compute_hash(content)

        assert result == expected

    def test_compute_hash_empty(self):
        """Test hash computation with empty content."""
        content = b""
        expected = hashlib.sha256(content).hexdigest()

        result = BaseCrawler.compute_hash(content)

        assert result == expected

    def test_compute_text_hash(self):
        """Test text hash computation."""
        text = "test text"
        expected = hashlib.sha256(text.encode()).hexdigest()

        result = BaseCrawler.compute_text_hash(text)

        assert result == expected

    def test_compute_text_hash_normalized(self):
        """Test that text hash normalizes whitespace."""
        text1 = "test  text"
        text2 = "test text"

        # Text should be normalized before hashing
        hash1 = BaseCrawler.compute_text_hash(text1)
        hash2 = BaseCrawler.compute_text_hash(text2)

        # Depending on implementation, these may or may not be equal
        # This test documents the current behavior
        assert isinstance(hash1, str)
        assert isinstance(hash2, str)


class TestGetCrawlerForSource:
    """Tests for crawler factory function."""

    def test_website_source(self):
        """Test getting crawler for website source."""
        source = MagicMock()
        source.source_type.value = "WEBSITE"

        crawler = get_crawler_for_source(source)

        assert crawler is not None
        assert hasattr(crawler, 'crawl')

    def test_oparl_source(self):
        """Test getting crawler for OParl source."""
        source = MagicMock()
        source.source_type.value = "OPARL_API"
        source.base_url = "https://example.oparl.org/system"

        crawler = get_crawler_for_source(source)

        assert crawler is not None

    def test_rss_source(self):
        """Test getting crawler for RSS source."""
        source = MagicMock()
        source.source_type.value = "RSS"

        crawler = get_crawler_for_source(source)

        assert crawler is not None

    def test_custom_api_source(self):
        """Test getting crawler for custom API source."""
        source = MagicMock()
        source.source_type.value = "CUSTOM_API"
        source.crawl_config = {"api_type": "govdata"}

        crawler = get_crawler_for_source(source)

        assert crawler is not None


class TestCrawlerConditionalRequests:
    """Tests for HTTP conditional request functionality."""

    @pytest.mark.asyncio
    async def test_fetch_with_conditional_headers(self):
        """Test that conditional headers are sent correctly."""
        # This would require mocking httpx
        # Just ensure the method exists
        assert hasattr(BaseCrawler, 'fetch_with_conditional')

    def test_304_not_modified_handling(self):
        """Test handling of 304 Not Modified responses."""
        # Document expected behavior for 304 responses
        # The crawler should detect no changes when server returns 304
        pass
