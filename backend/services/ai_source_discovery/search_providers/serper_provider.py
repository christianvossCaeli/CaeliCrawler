"""Serper.dev search provider - Google Search API."""

import httpx
import structlog

from ..models import SearchResult
from .base import BaseSearchProvider

logger = structlog.get_logger()


class SerperSearchProvider(BaseSearchProvider):
    """
    Serper.dev - Google Search API provider.

    Pricing: $50/Monat for 50,000 searches
    Documentation: https://serper.dev/docs

    Example usage with user credentials:
        from services.credentials_resolver import get_serper_key

        api_key = await get_serper_key(session, user_id)
        provider = SerperSearchProvider(api_key=api_key)
        results = await provider.search(["query"])
    """

    API_URL = "https://google.serper.dev/search"
    TIMEOUT = 30.0

    def __init__(self, api_key: str | None = None):
        """Initialize Serper provider.

        Args:
            api_key: Serper API key. Required for search to work.
                     If None, search will return empty results.
        """
        self.api_key = api_key

    async def search(
        self,
        queries: list[str],
        num_results: int = 10,
    ) -> list[SearchResult]:
        """
        Execute web search using Serper.dev API.

        Args:
            queries: List of search queries
            num_results: Number of results per query

        Returns:
            List of SearchResult objects
        """
        if not self.api_key:
            logger.warning("Serper API key not configured, using fallback mock data")
            return self._get_mock_results(queries)

        results = []
        seen_urls = set()

        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            for query in queries:
                try:
                    response = await client.post(
                        self.API_URL,
                        headers={
                            "X-API-KEY": self.api_key,
                            "Content-Type": "application/json",
                        },
                        json={
                            "q": query,
                            "num": num_results,
                            "gl": "de",  # Germany
                            "hl": "de",  # German language
                        },
                    )
                    response.raise_for_status()
                    data = response.json()

                    for item in data.get("organic", []):
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
                        "Serper search completed",
                        query=query,
                        results_count=len(data.get("organic", [])),
                    )

                except httpx.HTTPError as e:
                    logger.error(
                        "Serper API request failed",
                        query=query,
                        error=str(e),
                    )
                except Exception as e:
                    logger.error(
                        "Unexpected error during Serper search",
                        query=query,
                        error=str(e),
                    )

        return results

    def _get_mock_results(self, queries: list[str]) -> list[SearchResult]:
        """Return empty results when no API key is configured."""
        logger.error(
            "Serper API key not provided - web search disabled. "
            "User must configure Serper credentials under Settings > API Credentials.",
            queries=queries,
        )
        return []
