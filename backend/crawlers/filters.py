"""Crawl filter pipeline for content relevance filtering."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import structlog

from services.relevance_checker import RelevanceChecker

logger = structlog.get_logger()


@dataclass
class FilterResult:
    """Result of a filter check."""

    should_process: bool
    reason: str
    relevance_score: float = 0.5
    filter_name: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


class CrawlFilter(ABC):
    """Abstract base class for crawl filters."""

    name: str = "base_filter"

    @abstractmethod
    def check(
        self,
        url: str,
        content: Optional[bytes] = None,
        text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FilterResult:
        """
        Check if content should be processed.

        Args:
            url: Document URL
            content: Raw binary content (optional)
            text: Extracted text content (optional)
            metadata: Additional metadata like title, headers (optional)

        Returns:
            FilterResult indicating if content should be processed
        """
        pass


class URLPatternFilter(CrawlFilter):
    """Filter URLs based on regex patterns."""

    name = "url_pattern"

    def __init__(
        self,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ):
        self.include_patterns = []
        self.exclude_patterns = []

        for pattern in (include_patterns or []):
            try:
                self.include_patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error:
                logger.warning("Invalid include pattern", pattern=pattern)

        for pattern in (exclude_patterns or []):
            try:
                self.exclude_patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error:
                logger.warning("Invalid exclude pattern", pattern=pattern)

    def check(
        self,
        url: str,
        content: Optional[bytes] = None,
        text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FilterResult:
        # Check exclude patterns first (blacklist)
        for pattern in self.exclude_patterns:
            if pattern.search(url):
                return FilterResult(
                    should_process=False,
                    reason=f"url_excluded_by_pattern",
                    relevance_score=0.0,
                    filter_name=self.name,
                    details={"pattern": pattern.pattern},
                )

        # Check include patterns (whitelist) - if set, must match at least one
        if self.include_patterns:
            if not any(p.search(url) for p in self.include_patterns):
                return FilterResult(
                    should_process=False,
                    reason="url_not_in_include_patterns",
                    relevance_score=0.0,
                    filter_name=self.name,
                )

        return FilterResult(
            should_process=True,
            reason="url_passed",
            relevance_score=0.5,
            filter_name=self.name,
        )


class FileSizeFilter(CrawlFilter):
    """Filter documents based on file size."""

    name = "file_size"

    def __init__(
        self,
        min_size_bytes: int = 100,  # Skip tiny files (likely errors)
        max_size_bytes: int = 50 * 1024 * 1024,  # 50MB max
    ):
        self.min_size = min_size_bytes
        self.max_size = max_size_bytes

    def check(
        self,
        url: str,
        content: Optional[bytes] = None,
        text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FilterResult:
        if content is None:
            # Can't check size without content
            return FilterResult(
                should_process=True,
                reason="no_content_to_check",
                filter_name=self.name,
            )

        size = len(content)

        if size < self.min_size:
            return FilterResult(
                should_process=False,
                reason=f"file_too_small_{size}_bytes",
                relevance_score=0.0,
                filter_name=self.name,
                details={"size": size, "min_required": self.min_size},
            )

        if size > self.max_size:
            return FilterResult(
                should_process=False,
                reason=f"file_too_large_{size}_bytes",
                relevance_score=0.0,
                filter_name=self.name,
                details={"size": size, "max_allowed": self.max_size},
            )

        return FilterResult(
            should_process=True,
            reason="size_ok",
            relevance_score=0.5,
            filter_name=self.name,
            details={"size": size},
        )


class KeywordFilter(CrawlFilter):
    """Filter documents based on keyword relevance."""

    name = "keyword"

    def __init__(
        self,
        keywords: Optional[List[str]] = None,
        min_keywords: int = 2,
        min_score: float = 0.2,
    ):
        self.checker = RelevanceChecker(keywords=keywords, min_keywords=min_keywords)
        self.min_score = min_score

    @classmethod
    def from_category(cls, category, min_score: float = 0.2) -> "KeywordFilter":
        """Create a KeywordFilter from a Category model."""
        keywords = None
        if category and hasattr(category, "search_terms") and category.search_terms:
            keywords = category.search_terms
        return cls(keywords=keywords, min_score=min_score)

    def check(
        self,
        url: str,
        content: Optional[bytes] = None,
        text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FilterResult:
        if not text:
            # Can't check keywords without text
            return FilterResult(
                should_process=True,
                reason="no_text_to_check",
                filter_name=self.name,
            )

        title = (metadata or {}).get("title")
        result = self.checker.check(text, title)

        if not result.is_relevant and result.score < self.min_score:
            return FilterResult(
                should_process=False,
                reason=result.reason,
                relevance_score=result.score,
                filter_name=self.name,
                details={
                    "matched_keywords": result.matched_keywords,
                    "score": result.score,
                },
            )

        return FilterResult(
            should_process=True,
            reason=result.reason,
            relevance_score=result.score,
            filter_name=self.name,
            details={
                "matched_keywords": result.matched_keywords,
                "score": result.score,
            },
        )


class FilterPipeline:
    """
    Runs multiple filters in sequence.

    Stops on first rejection (fail-fast) for efficiency.
    """

    def __init__(self, filters: Optional[List[CrawlFilter]] = None):
        self.filters = filters or []
        self.logger = structlog.get_logger(component="filter_pipeline")

    def add_filter(self, filter_: CrawlFilter) -> "FilterPipeline":
        """Add a filter to the pipeline. Returns self for chaining."""
        self.filters.append(filter_)
        return self

    def process(
        self,
        url: str,
        content: Optional[bytes] = None,
        text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FilterResult:
        """
        Run all filters on the content.

        Returns the first rejection or a success result with combined score.
        """
        if not self.filters:
            return FilterResult(
                should_process=True,
                reason="no_filters",
                relevance_score=0.5,
            )

        scores = []
        for filter_ in self.filters:
            result = filter_.check(url, content, text, metadata)

            if not result.should_process:
                self.logger.debug(
                    "Document filtered out",
                    url=url,
                    filter=result.filter_name,
                    reason=result.reason,
                )
                return result

            scores.append(result.relevance_score)

        # All filters passed - average the scores
        avg_score = sum(scores) / len(scores) if scores else 0.5

        return FilterResult(
            should_process=True,
            reason="passed_all_filters",
            relevance_score=avg_score,
            details={"filters_passed": len(self.filters)},
        )

    @classmethod
    def create_default(
        cls,
        category=None,
        url_include_patterns: Optional[List[str]] = None,
        url_exclude_patterns: Optional[List[str]] = None,
    ) -> "FilterPipeline":
        """
        Create a default filter pipeline.

        Includes:
        1. URL pattern filter (if patterns provided)
        2. File size filter
        3. Keyword filter (from category or defaults)
        """
        pipeline = cls()

        # URL patterns (if configured)
        if url_include_patterns or url_exclude_patterns:
            pipeline.add_filter(URLPatternFilter(
                include_patterns=url_include_patterns,
                exclude_patterns=url_exclude_patterns,
            ))

        # File size (always check)
        pipeline.add_filter(FileSizeFilter())

        # Keyword relevance
        pipeline.add_filter(KeywordFilter.from_category(category))

        return pipeline
