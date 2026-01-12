"""SerpAPI search provider - Google Search API (same as caeli-google-news-fetch)."""

import httpx
import structlog

from ..models import SearchResult
from .base import BaseSearchProvider

logger = structlog.get_logger()


class SerpAPISearchProvider(BaseSearchProvider):
    """
    SerpAPI - Google Search API provider.

    Same API as used in caeli-google-news-fetch Contao module.
    Pricing: ~$50/month for 5,000 searches
    Documentation: https://serpapi.com/search-api

    Example usage with user credentials:
        from services.credentials_resolver import get_serpapi_key

        api_key = await get_serpapi_key(session, user_id)
        provider = SerpAPISearchProvider(api_key=api_key)
        results = await provider.search(["query"])
    """

    API_URL = "https://serpapi.com/search.json"
    TIMEOUT = 30.0

    def __init__(self, api_key: str | None = None):
        """Initialize SerpAPI provider.

        Args:
            api_key: SerpAPI API key. Required for search to work.
                     If None, search will return empty results.
        """
        self.api_key = api_key
        self.had_error = False
        self.last_error: str | None = None

    async def search(
        self,
        queries: list[str],
        num_results: int = 10,
    ) -> list[SearchResult]:
        """
        Execute web search using SerpAPI.

        Args:
            queries: List of search queries
            num_results: Number of results per query

        Returns:
            List of SearchResult objects
        """
        self.had_error = False
        self.last_error = None

        if not self.api_key:
            self.had_error = True
            self.last_error = "SerpAPI API key not configured"
            logger.error(
                "SerpAPI API key not provided - web search disabled. "
                "User must configure SerpAPI credentials under Settings > API Credentials."
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

                    if data.get("error") or data.get("search_metadata", {}).get("status") == "Error":
                        error_message = data.get("error") or data.get("search_metadata", {}).get("error", "Unknown error")
                        self.had_error = True
                        self.last_error = f"SerpAPI error: {error_message}"
                        logger.error(
                            "SerpAPI returned error payload",
                            query=query,
                            error=error_message,
                        )
                        continue

                    # Extract organic results
                    for item in data.get("organic_results", []):
                        url = item.get("link", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            results.append(
                                SearchResult(
                                    url=url,
                                    title=item.get("title", ""),
                                    snippet=item.get("snippet", ""),
                                    source_type=self._detect_source_type(url),
                                    confidence=self._calculate_confidence(item, query),
                                )
                            )

                    logger.debug(
                        "SerpAPI search completed",
                        query=query,
                        results_count=len(data.get("organic_results", [])),
                    )

                except httpx.HTTPStatusError as e:
                    self.had_error = True
                    self.last_error = f"SerpAPI HTTP {e.response.status_code}"
                    logger.error(
                        "SerpAPI request failed",
                        query=query,
                        status_code=e.response.status_code,
                        error=str(e),
                    )
                except httpx.HTTPError as e:
                    self.had_error = True
                    self.last_error = f"SerpAPI network error: {e}"
                    logger.error(
                        "SerpAPI network error",
                        query=query,
                        error=str(e),
                    )
                except Exception as e:
                    self.had_error = True
                    self.last_error = f"SerpAPI unexpected error: {e}"
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
        elif "/api/" in url_lower or "api." in url_lower or ".json" in url_lower or ".xml" in url_lower:
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
