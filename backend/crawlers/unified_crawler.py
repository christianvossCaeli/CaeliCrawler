"""
Unified Crawler Service.

Provides a single interface to all supported data sources:
- OParl (German municipal council APIs)
- GovData.de (German Open Data Portal)
- DIP Bundestag (Parliamentary documents)
- FragDenStaat (FOI requests)
- RSS/Atom Feeds
- Generic websites
"""

from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Type
from dataclasses import dataclass, field

import structlog

from crawlers.base import BaseCrawler, CrawlResult
from crawlers.api_clients.base_api import BaseAPIClient, APIDocument, APIResponse
from crawlers.api_clients.oparl_client import OparlClient, KNOWN_OPARL_ENDPOINTS
from crawlers.api_clients.govdata_client import GovDataClient
from crawlers.api_clients.dip_bundestag_client import DIPBundestagClient
from crawlers.api_clients.fragdenstaat_client import FragDenStaatClient
from crawlers.rss_crawler import RSSCrawler, GERMAN_GOVERNMENT_FEEDS

logger = structlog.get_logger()


class DataSourceType(str, Enum):
    """Supported data source types."""

    OPARL = "oparl"
    GOVDATA = "govdata"
    DIP_BUNDESTAG = "dip_bundestag"
    FRAGDENSTAAT = "fragdenstaat"
    RSS = "rss"
    WEBSITE = "website"
    CUSTOM_API = "custom_api"


@dataclass
class UnifiedSearchQuery:
    """Unified search query across all data sources."""

    query: str
    sources: List[DataSourceType] = field(default_factory=lambda: list(DataSourceType))

    # Common filters
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    location: Optional[str] = None
    categories: Optional[List[str]] = None
    tags: Optional[List[str]] = None

    # Pagination
    limit: int = 50
    offset: int = 0

    # Source-specific options
    oparl_body_url: Optional[str] = None
    govdata_organization: Optional[str] = None
    dip_wahlperiode: Optional[int] = None
    dip_document_type: Optional[str] = None
    fragdenstaat_jurisdiction: Optional[str] = None
    fragdenstaat_status: Optional[str] = None


@dataclass
class UnifiedSearchResult:
    """Unified search result from all sources."""

    documents: List[APIDocument]
    total_count: int
    sources_searched: List[str]
    source_counts: Dict[str, int]
    errors: Dict[str, str] = field(default_factory=dict)


class UnifiedCrawlerService:
    """
    Unified service for crawling all supported data sources.

    Example usage:
        service = UnifiedCrawlerService()

        # Search across all sources
        results = await service.search(UnifiedSearchQuery(
            query="Windenergie",
            sources=[DataSourceType.GOVDATA, DataSourceType.DIP_BUNDESTAG],
            location="Nordrhein-Westfalen"
        ))

        # Get available data sources
        sources = service.get_available_sources()

        # Crawl a specific source
        result = await service.crawl_source(source_config)
    """

    def __init__(self):
        self.logger = logger.bind(service="UnifiedCrawler")
        self._clients: Dict[DataSourceType, BaseAPIClient] = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Close all API clients."""
        for client in self._clients.values():
            await client.close()
        self._clients.clear()

    # === Client Management ===

    async def get_govdata_client(self) -> GovDataClient:
        """Get GovData client."""
        if DataSourceType.GOVDATA not in self._clients:
            client = GovDataClient()
            await client._ensure_client()
            self._clients[DataSourceType.GOVDATA] = client
        return self._clients[DataSourceType.GOVDATA]

    async def get_dip_client(self) -> DIPBundestagClient:
        """Get DIP Bundestag client."""
        if DataSourceType.DIP_BUNDESTAG not in self._clients:
            client = DIPBundestagClient()
            await client._ensure_client()
            self._clients[DataSourceType.DIP_BUNDESTAG] = client
        return self._clients[DataSourceType.DIP_BUNDESTAG]

    async def get_fragdenstaat_client(self) -> FragDenStaatClient:
        """Get FragDenStaat client."""
        if DataSourceType.FRAGDENSTAAT not in self._clients:
            client = FragDenStaatClient()
            await client._ensure_client()
            self._clients[DataSourceType.FRAGDENSTAAT] = client
        return self._clients[DataSourceType.FRAGDENSTAAT]

    async def get_oparl_client(self, system_url: str) -> OparlClient:
        """Get OParl client for specific system."""
        key = f"oparl_{system_url}"
        if key not in self._clients:
            client = OparlClient(system_url)
            await client._ensure_client()
            self._clients[key] = client
        return self._clients[key]

    # === Unified Search ===

    async def search(self, query: UnifiedSearchQuery) -> UnifiedSearchResult:
        """
        Search across multiple data sources.

        Args:
            query: Unified search query with filters
        """
        all_documents = []
        source_counts = {}
        errors = {}
        sources_searched = []

        for source_type in query.sources:
            try:
                self.logger.info("Searching source", source=source_type.value, query=query.query)
                sources_searched.append(source_type.value)

                if source_type == DataSourceType.GOVDATA:
                    results = await self._search_govdata(query)
                elif source_type == DataSourceType.DIP_BUNDESTAG:
                    results = await self._search_dip(query)
                elif source_type == DataSourceType.FRAGDENSTAAT:
                    results = await self._search_fragdenstaat(query)
                elif source_type == DataSourceType.OPARL:
                    results = await self._search_oparl(query)
                else:
                    continue

                all_documents.extend(results.data)
                source_counts[source_type.value] = results.total_count or len(results.data)

            except Exception as e:
                self.logger.error("Search failed", source=source_type.value, error=str(e))
                errors[source_type.value] = str(e)

        return UnifiedSearchResult(
            documents=all_documents,
            total_count=sum(source_counts.values()),
            sources_searched=sources_searched,
            source_counts=source_counts,
            errors=errors,
        )

    async def _search_govdata(self, query: UnifiedSearchQuery) -> APIResponse[APIDocument]:
        """Search GovData."""
        client = await self.get_govdata_client()

        kwargs = {
            "rows": query.limit,
            "start": query.offset,
        }

        if query.govdata_organization:
            kwargs["organization"] = query.govdata_organization

        if query.categories:
            kwargs["groups"] = query.categories

        if query.tags:
            kwargs["tags"] = query.tags

        if query.location:
            return await client.search_by_location(query.location, query.query, **kwargs)

        return await client.search(query.query, **kwargs)

    async def _search_dip(self, query: UnifiedSearchQuery) -> APIResponse[APIDocument]:
        """Search DIP Bundestag."""
        client = await self.get_dip_client()

        kwargs = {
            "rows": query.limit,
            "offset": query.offset,
        }

        if query.dip_wahlperiode:
            kwargs["wahlperiode"] = query.dip_wahlperiode

        if query.date_from:
            kwargs["datum_start"] = query.date_from.date()

        if query.date_to:
            kwargs["datum_end"] = query.date_to.date()

        doc_type = query.dip_document_type or "drucksache"
        return await client.search(query.query, document_type=doc_type, **kwargs)

    async def _search_fragdenstaat(self, query: UnifiedSearchQuery) -> APIResponse[APIDocument]:
        """Search FragDenStaat."""
        client = await self.get_fragdenstaat_client()

        kwargs = {
            "limit": query.limit,
            "offset": query.offset,
        }

        if query.fragdenstaat_jurisdiction:
            kwargs["jurisdiction"] = query.fragdenstaat_jurisdiction

        if query.fragdenstaat_status:
            kwargs["status"] = query.fragdenstaat_status

        if query.date_from:
            kwargs["created_after"] = query.date_from

        if query.date_to:
            kwargs["created_before"] = query.date_to

        if query.tags:
            kwargs["tags"] = query.tags

        return await client.search(query.query, **kwargs)

    async def _search_oparl(self, query: UnifiedSearchQuery) -> APIResponse[APIDocument]:
        """Search OParl (limited - OParl doesn't have a search API)."""
        if not query.oparl_body_url:
            # Without a specific body, we can't search effectively
            return APIResponse(data=[], total_count=0)

        client = await self.get_oparl_client(query.oparl_body_url)
        return await client.search(query.query)

    # === Data Source Discovery ===

    def get_available_sources(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all available pre-configured data sources."""
        return {
            "oparl": [
                {
                    "name": ep["name"],
                    "url": ep["url"],
                    "state": ep.get("state"),
                    "type": "oparl",
                }
                for ep in KNOWN_OPARL_ENDPOINTS
            ],
            "rss": [
                {
                    "name": feed["name"],
                    "url": feed["url"],
                    "category": feed.get("category"),
                    "type": "rss",
                }
                for feed in GERMAN_GOVERNMENT_FEEDS
            ],
            "govdata": [
                {
                    "name": "GovData.de",
                    "url": "https://www.govdata.de/",
                    "api_url": "https://ckan.govdata.de/api/3/action",
                    "type": "govdata",
                    "description": "German Open Government Data Portal",
                }
            ],
            "dip_bundestag": [
                {
                    "name": "DIP Bundestag",
                    "url": "https://dip.bundestag.de/",
                    "api_url": "https://search.dip.bundestag.de/api/v1",
                    "type": "dip_bundestag",
                    "description": "Parliamentary Documentation System",
                }
            ],
            "fragdenstaat": [
                {
                    "name": "FragDenStaat",
                    "url": "https://fragdenstaat.de/",
                    "api_url": "https://fragdenstaat.de/api/v1",
                    "type": "fragdenstaat",
                    "description": "Freedom of Information Portal",
                }
            ],
        }

    async def get_govdata_categories(self) -> Dict[str, str]:
        """Get available GovData categories."""
        return GovDataClient.CATEGORIES

    async def get_govdata_organizations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get GovData organizations."""
        client = await self.get_govdata_client()
        orgs = []
        async for org in client.get_organizations():
            orgs.append({
                "id": org.id,
                "name": org.name,
                "title": org.title,
                "package_count": org.package_count,
            })
            if len(orgs) >= limit:
                break
        return orgs

    async def get_fragdenstaat_jurisdictions(self) -> List[Dict[str, Any]]:
        """Get FragDenStaat jurisdictions."""
        client = await self.get_fragdenstaat_client()
        return await client.get_jurisdictions()

    async def get_oparl_bodies(self, system_url: str) -> List[Dict[str, Any]]:
        """Get bodies from an OParl system."""
        client = await self.get_oparl_client(system_url)
        bodies = []
        async for body in client.get_bodies():
            bodies.append({
                "id": body.id,
                "name": body.name,
                "short_name": body.short_name,
                "ags": body.ags,
                "website": body.website,
            })
        return bodies

    # === Source-Specific Iteration ===

    async def iterate_govdata_datasets(
        self,
        query: str = "*:*",
        category: Optional[str] = None,
        location: Optional[str] = None,
        max_datasets: int = 1000,
    ) -> AsyncIterator[APIDocument]:
        """Iterate through GovData datasets."""
        client = await self.get_govdata_client()

        if category:
            async for dataset in client.iterate_all_datasets(
                query=query,
                max_datasets=max_datasets,
                groups=[category],
            ):
                yield client._dataset_to_document(dataset)
        elif location:
            # Search by location in batches
            offset = 0
            total = 0
            while total < max_datasets:
                response = await client.search_by_location(
                    location=location,
                    query=query,
                    rows=100,
                    start=offset,
                )
                for doc in response.data:
                    yield doc
                    total += 1
                    if total >= max_datasets:
                        return

                if not response.has_more:
                    break
                offset += 100
        else:
            async for dataset in client.iterate_all_datasets(
                query=query,
                max_datasets=max_datasets,
            ):
                yield client._dataset_to_document(dataset)

    async def iterate_dip_drucksachen(
        self,
        wahlperiode: int = 20,
        drucksachetyp: Optional[str] = None,
        max_documents: int = 1000,
    ) -> AsyncIterator[APIDocument]:
        """Iterate through Bundestag Drucksachen."""
        client = await self.get_dip_client()

        async for drucksache in client.iterate_drucksachen(
            wahlperiode=wahlperiode,
            drucksachetyp=drucksachetyp,
            max_documents=max_documents,
        ):
            yield client._drucksache_to_document(drucksache)

    async def iterate_kleine_anfragen(
        self,
        wahlperiode: int = 20,
        max_documents: int = 50000,
    ) -> AsyncIterator[APIDocument]:
        """Iterate through all Kleine Anfragen."""
        client = await self.get_dip_client()

        async for vorgang in client.iterate_kleine_anfragen(
            wahlperiode=wahlperiode,
            max_documents=max_documents,
        ):
            yield client._vorgang_to_document(vorgang)

    async def iterate_foi_requests(
        self,
        jurisdiction: Optional[str] = None,
        status: Optional[str] = None,
        max_requests: int = 1000,
    ) -> AsyncIterator[APIDocument]:
        """Iterate through FOI requests."""
        client = await self.get_fragdenstaat_client()

        async for request in client.iterate_requests(
            jurisdiction=jurisdiction,
            status=status,
            max_requests=max_requests,
        ):
            yield client._request_to_document(request)

    async def iterate_oparl_papers(
        self,
        system_url: str,
        modified_since: Optional[datetime] = None,
        max_papers: int = 10000,
    ) -> AsyncIterator[APIDocument]:
        """Iterate through OParl papers from all bodies in a system."""
        client = await self.get_oparl_client(system_url)
        total = 0

        async for body in client.get_bodies():
            self.logger.info("Processing OParl body", body=body.name)

            async for paper in client.get_papers(
                body=body,
                modified_since=modified_since,
                max_pages=100,
            ):
                yield client._paper_to_document(paper)
                total += 1
                if total >= max_papers:
                    return


# Convenience function for quick searches
async def quick_search(
    query: str,
    sources: Optional[List[str]] = None,
    limit: int = 20,
) -> List[APIDocument]:
    """
    Quick search across default sources.

    Args:
        query: Search query
        sources: List of source types ("govdata", "dip", "fragdenstaat")
        limit: Maximum results per source
    """
    source_types = []
    if sources:
        for s in sources:
            if s == "govdata":
                source_types.append(DataSourceType.GOVDATA)
            elif s == "dip":
                source_types.append(DataSourceType.DIP_BUNDESTAG)
            elif s == "fragdenstaat":
                source_types.append(DataSourceType.FRAGDENSTAAT)
    else:
        source_types = [
            DataSourceType.GOVDATA,
            DataSourceType.DIP_BUNDESTAG,
            DataSourceType.FRAGDENSTAAT,
        ]

    async with UnifiedCrawlerService() as service:
        result = await service.search(UnifiedSearchQuery(
            query=query,
            sources=source_types,
            limit=limit,
        ))
        return result.documents
