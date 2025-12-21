"""Serper.dev search provider - Google Search API."""

from typing import List

import httpx
import structlog

from app.config import settings
from .base import BaseSearchProvider
from ..models import SearchResult

logger = structlog.get_logger()


class SerperSearchProvider(BaseSearchProvider):
    """
    Serper.dev - Google Search API provider.

    Pricing: $50/Monat for 50,000 searches
    Documentation: https://serper.dev/docs
    """

    API_URL = "https://google.serper.dev/search"
    TIMEOUT = 30.0

    def __init__(self):
        self.api_key = getattr(settings, "serper_api_key", None)

    async def search(
        self,
        queries: List[str],
        num_results: int = 10,
    ) -> List[SearchResult]:
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
                            results.append(SearchResult(
                                url=url,
                                title=item.get("title", ""),
                                snippet=item.get("snippet", ""),
                                source_type=self._detect_source_type(url),
                                confidence=self._calculate_confidence(item, query),
                            ))

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

    def _get_mock_results(self, queries: List[str]) -> List[SearchResult]:
        """Return mock results for testing without API key."""
        mock_results = [
            SearchResult(
                url="https://de.wikipedia.org/wiki/Fu%C3%9Fball-Bundesliga",
                title="Fußball-Bundesliga - Wikipedia",
                snippet="Die Fußball-Bundesliga ist die höchste Spielklasse im deutschen Fußball...",
                source_type="wikipedia",
                confidence=0.9,
            ),
            SearchResult(
                url="https://www.bundesliga.com/de/bundesliga",
                title="Bundesliga | Die offizielle Seite",
                snippet="Alle News, Spielpläne, Tabellen und Statistiken zur Bundesliga...",
                source_type="website",
                confidence=0.85,
            ),
            SearchResult(
                url="https://www.transfermarkt.de/1-bundesliga/startseite/wettbewerb/L1",
                title="1. Bundesliga - Transfermarkt",
                snippet="Alle Vereine der 1. Bundesliga im Überblick...",
                source_type="website",
                confidence=0.8,
            ),
        ]
        return mock_results
