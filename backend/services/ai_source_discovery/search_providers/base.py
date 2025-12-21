"""Base class for search providers."""

from abc import ABC, abstractmethod
from typing import List
from urllib.parse import urlparse

from ..models import SearchResult


class BaseSearchProvider(ABC):
    """Abstract base class for web search providers."""

    @abstractmethod
    async def search(
        self,
        queries: List[str],
        num_results: int = 10,
    ) -> List[SearchResult]:
        """
        Execute web search for the given queries.

        Args:
            queries: List of search queries
            num_results: Number of results per query

        Returns:
            List of SearchResult objects
        """
        pass

    def _detect_source_type(self, url: str) -> str:
        """Detect the type of source based on URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Wikipedia
        if "wikipedia.org" in domain:
            return "wikipedia"

        # Government/Official
        if any(tld in domain for tld in [".gov", ".gov.de", ".gov.uk", ".gv.at"]):
            return "government"

        # Open Data Portals
        if any(portal in domain for portal in ["data.gov", "govdata.de", "data.europa.eu", "opendata"]):
            return "open_data"

        # Known API providers
        if any(api in domain for api in ["api.", "wikidata.org"]):
            return "api"

        # Default
        return "website"

    def _calculate_confidence(self, result: dict, query: str) -> float:
        """Calculate confidence score for a search result."""
        confidence = 0.5

        title = result.get("title", "").lower()
        snippet = result.get("snippet", "").lower()
        query_lower = query.lower()

        # Title contains query terms
        query_terms = query_lower.split()
        title_matches = sum(1 for term in query_terms if term in title)
        confidence += title_matches * 0.1

        # Snippet contains query terms
        snippet_matches = sum(1 for term in query_terms if term in snippet)
        confidence += snippet_matches * 0.05

        # Source type bonus
        url = result.get("link", "")
        source_type = self._detect_source_type(url)
        if source_type in ["wikipedia", "government", "open_data"]:
            confidence += 0.15
        elif source_type == "api":
            confidence += 0.2

        return min(confidence, 1.0)
