"""Unit tests for the crawler filter pipeline."""

import pytest
from crawlers.filters import (
    FilterResult,
    URLPatternFilter,
    FileSizeFilter,
    FilterPipeline,
)


class TestURLPatternFilter:
    """Tests for URL pattern filtering."""

    def test_include_pattern_match(self):
        """Test that URLs matching include patterns pass."""
        filter_ = URLPatternFilter(include_patterns=[r"/news/", r"/aktuelles/"])

        result = filter_.check("https://example.com/news/article-1")
        assert result.should_process is True
        assert result.reason == "url_passed"

    def test_include_pattern_no_match(self):
        """Test that URLs not matching include patterns are filtered."""
        filter_ = URLPatternFilter(include_patterns=[r"/news/"])

        result = filter_.check("https://example.com/about/team")
        assert result.should_process is False
        assert result.reason == "url_not_in_include_patterns"

    def test_exclude_pattern_match(self):
        """Test that URLs matching exclude patterns are filtered."""
        filter_ = URLPatternFilter(exclude_patterns=[r"\.pdf$", r"/login/"])

        result = filter_.check("https://example.com/document.pdf")
        assert result.should_process is False
        assert result.reason == "url_excluded_by_pattern"

    def test_exclude_pattern_no_match(self):
        """Test that URLs not matching exclude patterns pass."""
        filter_ = URLPatternFilter(exclude_patterns=[r"\.pdf$"])

        result = filter_.check("https://example.com/page.html")
        assert result.should_process is True

    def test_exclude_takes_precedence(self):
        """Test that exclude patterns are checked before include."""
        filter_ = URLPatternFilter(
            include_patterns=[r"/documents/"],
            exclude_patterns=[r"\.pdf$"]
        )

        # Should be excluded even though it matches include pattern
        result = filter_.check("https://example.com/documents/file.pdf")
        assert result.should_process is False

    def test_no_patterns_passes_all(self):
        """Test that no patterns configured passes all URLs."""
        filter_ = URLPatternFilter()

        result = filter_.check("https://anything.com/any/path")
        assert result.should_process is True

    def test_invalid_regex_handled(self):
        """Test that invalid regex patterns are handled gracefully."""
        # Invalid regex should not crash, just log warning
        filter_ = URLPatternFilter(include_patterns=["[invalid("])

        # Should pass since no valid include patterns
        result = filter_.check("https://example.com/page")
        assert result.should_process is True

    def test_case_insensitive_matching(self):
        """Test that URL matching is case insensitive."""
        filter_ = URLPatternFilter(include_patterns=[r"/NEWS/"])

        result = filter_.check("https://example.com/news/article")
        assert result.should_process is True


class TestFileSizeFilter:
    """Tests for file size filtering."""

    def test_size_within_limits(self):
        """Test that content within limits passes."""
        filter_ = FileSizeFilter(min_size_bytes=100, max_size_bytes=10000)

        content = b"x" * 500  # 500 bytes
        result = filter_.check("url", content=content)

        assert result.should_process is True
        assert result.details["size"] == 500

    def test_size_too_small(self):
        """Test that tiny content is filtered."""
        filter_ = FileSizeFilter(min_size_bytes=100)

        content = b"x" * 50  # 50 bytes
        result = filter_.check("url", content=content)

        assert result.should_process is False
        assert "too_small" in result.reason

    def test_size_too_large(self):
        """Test that large content is filtered."""
        filter_ = FileSizeFilter(max_size_bytes=1000)

        content = b"x" * 2000  # 2000 bytes
        result = filter_.check("url", content=content)

        assert result.should_process is False
        assert "too_large" in result.reason

    def test_no_content_passes(self):
        """Test that no content passes (can't check size)."""
        filter_ = FileSizeFilter()

        result = filter_.check("url", content=None)
        assert result.should_process is True
        assert result.reason == "no_content_to_check"

    def test_default_limits(self):
        """Test default size limits."""
        filter_ = FileSizeFilter()

        # Default min is 100 bytes
        small_content = b"x" * 50
        result = filter_.check("url", content=small_content)
        assert result.should_process is False

        # Default max is 50MB
        normal_content = b"x" * 1000
        result = filter_.check("url", content=normal_content)
        assert result.should_process is True


class TestFilterPipeline:
    """Tests for the filter pipeline."""

    def test_empty_pipeline_passes_all(self):
        """Test that empty pipeline passes all content."""
        pipeline = FilterPipeline()

        result = pipeline.process("url")
        assert result.should_process is True
        assert result.reason == "no_filters"

    def test_all_filters_pass(self):
        """Test that content passing all filters is accepted."""
        pipeline = FilterPipeline([
            URLPatternFilter(include_patterns=[r".*"]),  # Pass all
            FileSizeFilter(min_size_bytes=10),
        ])

        content = b"x" * 100
        result = pipeline.process("https://example.com", content=content)

        assert result.should_process is True
        assert result.reason == "passed_all_filters"

    def test_first_failure_stops_pipeline(self):
        """Test that first filter failure stops the pipeline."""
        pipeline = FilterPipeline([
            URLPatternFilter(include_patterns=[r"/special/"]),  # Will fail
            FileSizeFilter(),  # Should not be reached
        ])

        result = pipeline.process("https://example.com/other/")

        assert result.should_process is False
        assert result.filter_name == "url_pattern"

    def test_score_averaging(self):
        """Test that scores are averaged across filters."""
        pipeline = FilterPipeline([
            URLPatternFilter(),  # Default score 0.5
            FileSizeFilter(),    # Default score 0.5
        ])

        content = b"x" * 200
        result = pipeline.process("https://example.com", content=content)

        assert result.should_process is True
        assert result.relevance_score == 0.5  # Average of 0.5 and 0.5

    def test_add_filter_chaining(self):
        """Test that add_filter returns self for chaining."""
        pipeline = FilterPipeline()

        result = (
            pipeline
            .add_filter(URLPatternFilter())
            .add_filter(FileSizeFilter())
        )

        assert result is pipeline
        assert len(pipeline.filters) == 2

    def test_create_default_pipeline(self):
        """Test default pipeline creation."""
        pipeline = FilterPipeline.create_default(
            url_include_patterns=[r"/news/"],
            url_exclude_patterns=[r"\.pdf$"]
        )

        # Should have URL, size, and keyword filters
        assert len(pipeline.filters) == 3


class TestFilterResult:
    """Tests for FilterResult dataclass."""

    def test_default_values(self):
        """Test default values in FilterResult."""
        result = FilterResult(should_process=True, reason="test")

        assert result.relevance_score == 0.5
        assert result.filter_name == ""
        assert result.details == {}

    def test_custom_values(self):
        """Test custom values in FilterResult."""
        result = FilterResult(
            should_process=False,
            reason="filtered",
            relevance_score=0.3,
            filter_name="test_filter",
            details={"key": "value"}
        )

        assert result.should_process is False
        assert result.reason == "filtered"
        assert result.relevance_score == 0.3
        assert result.filter_name == "test_filter"
        assert result.details == {"key": "value"}
