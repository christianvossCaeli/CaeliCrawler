"""SerpAPI search provider - Google Search API (same as caeli-google-news-fetch)."""

from typing import List

import httpx
import structlog

from app.config import settings
from .base import BaseSearchProvider
from ..models import SearchResult

logger = structlog.get_logger()


class SerpAPISearchProvider(BaseSearchProvider):
    """
    SerpAPI - Google Search API provider.

    Same API as used in caeli-google-news-fetch Contao module.
    Pricing: ~$50/month for 5,000 searches
    Documentation: https://serpapi.com/search-api
    """

    API_URL = "https://serpapi.com/search.json"
    TIMEOUT = 30.0

    def __init__(self):
        self.api_key = getattr(settings, "serpapi_api_key", None)

    async def search(
        self,
        queries: List[str],
        num_results: int = 10,
    ) -> List[SearchResult]:
        """
        Execute web search using SerpAPI.

        Args:
            queries: List of search queries
            num_results: Number of results per query

        Returns:
            List of SearchResult objects
        """
        if not self.api_key:
            logger.error(
                "SERPAPI_API_KEY not configured - web search disabled. "
                "Set SERPAPI_API_KEY environment variable for AI Source Discovery."
            )
            return []

        results = []
        seen_urls = set()

        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            for query in queries:
                try:
                    response = await client.get(
                        self.API_URL,
                        params={
                            "engine": "google",
                            "q": query,
                            "location": "Germany",
                            "google_domain": "google.de",
                            "gl": "de",
                            "hl": "de",
                            "num": num_results,
                            "api_key": self.api_key,
                            "output": "json",
                        },
                        headers={
                            "User-Agent": "CaeliCrawler/1.0 (Data Discovery)",
                        },
                    )
                    response.raise_for_status()
                    data = response.json()

                    # Extract organic results
                    for item in data.get("organic_results", []):
                        url = item.get("link", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            results.append(SearchResult(
                                url=url,
                                title=item.get("title", ""),
                                snippet=item.get("snippet", ""),
                                source_type=self._detect_source_type(url),
                                confidence=self._calculate_confidence(item, query),
                            ))

                    logger.debug(
                        "SerpAPI search completed",
                        query=query,
                        results_count=len(data.get("organic_results", [])),
                    )

                except httpx.HTTPStatusError as e:
                    logger.error(
                        "SerpAPI request failed",
                        query=query,
                        status_code=e.response.status_code,
                        error=str(e),
                    )
                except httpx.HTTPError as e:
                    logger.error(
                        "SerpAPI network error",
                        query=query,
                        error=str(e),
                    )
                except Exception as e:
                    logger.error(
                        "Unexpected error during SerpAPI search",
                        query=query,
                        error=str(e),
                    )

        logger.info(
            "SerpAPI search completed",
            total_queries=len(queries),
            total_results=len(results),
        )
        return results

    def _detect_source_type(self, url: str) -> str:
        """Detect source type from URL."""
        url_lower = url.lower()

        if "wikipedia.org" in url_lower:
            return "wikipedia"
        elif "/api/" in url_lower or "api." in url_lower:
            return "api"
        elif ".json" in url_lower or ".xml" in url_lower:
            return "api"
        elif any(x in url_lower for x in ["github.com", "gitlab.com"]):
            return "repository"
        else:
            return "website"

    def _calculate_confidence(self, item: dict, query: str) -> float:
        """Calculate confidence score based on result relevance."""
        confidence = 0.5

        title = item.get("title", "").lower()
        snippet = item.get("snippet", "").lower()
        query_terms = query.lower().split()

        # Boost for query terms in title
        title_matches = sum(1 for term in query_terms if term in title)
        confidence += title_matches * 0.1

        # Boost for query terms in snippet
        snippet_matches = sum(1 for term in query_terms if term in snippet)
        confidence += snippet_matches * 0.05

        # Boost for certain source types
        url = item.get("link", "").lower()
        if "wikipedia.org" in url:
            confidence += 0.15
        elif ".gov" in url or ".org" in url:
            confidence += 0.1

        return min(1.0, confidence)
