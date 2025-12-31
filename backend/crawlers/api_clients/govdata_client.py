"""
GovData.de API Client (CKAN-based).

GovData is the German national Open Government Data portal.
It aggregates datasets from federal, state, and municipal authorities.
See: https://www.govdata.de/

The API is based on CKAN (Comprehensive Knowledge Archive Network).
API Documentation: https://www.govdata.de/ckan-api
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from crawlers.api_clients.base_api import APIDocument, APIResponse, BaseAPIClient


@dataclass
class GovDataDataset:
    """GovData dataset (CKAN package) representation."""

    id: str
    name: str  # URL-safe name/slug
    title: str
    notes: str | None = None  # Description

    # Organization
    organization_id: str | None = None
    organization_name: str | None = None
    organization_title: str | None = None

    # Classification
    groups: list[dict[str, str]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)

    # License
    license_id: str | None = None
    license_title: str | None = None
    license_url: str | None = None

    # Resources (files, APIs)
    resources: list[dict[str, Any]] = field(default_factory=list)
    num_resources: int = 0

    # Metadata
    author: str | None = None
    author_email: str | None = None
    maintainer: str | None = None
    maintainer_email: str | None = None

    # Temporal coverage
    temporal_start: datetime | None = None
    temporal_end: datetime | None = None

    # Geographic coverage
    spatial: str | None = None
    spatial_text: str | None = None

    # URLs
    url: str | None = None

    # Dates
    created: datetime | None = None
    modified: datetime | None = None

    # State
    state: str = "active"
    is_private: bool = False

    # DCAT-AP.de specific
    dcat_type: str | None = None
    political_geocoding_uri: str | None = None
    political_geocoding_level_uri: str | None = None

    # Extra fields
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class GovDataResource:
    """A single resource (file/API) within a dataset."""

    id: str
    name: str
    url: str
    format: str

    description: str | None = None
    mimetype: str | None = None
    size: int | None = None
    hash: str | None = None

    created: datetime | None = None
    modified: datetime | None = None

    # Resource type
    resource_type: str | None = None
    cache_url: str | None = None
    cache_last_updated: datetime | None = None


@dataclass
class GovDataOrganization:
    """GovData organization representation."""

    id: str
    name: str
    title: str
    description: str | None = None
    image_url: str | None = None
    state: str = "active"
    package_count: int = 0
    created: datetime | None = None


class GovDataClient(BaseAPIClient):
    """
    Client for the GovData.de CKAN API.

    Example usage:
        async with GovDataClient() as client:
            # Search datasets
            results = await client.search("Windenergie", rows=50)

            # Get specific dataset
            dataset = await client.get_dataset("example-dataset")

            # List organizations
            async for org in client.get_organizations():
                print(org.title)

            # Search by geographic area
            results = await client.search_by_location("Nordrhein-Westfalen")

            # Search by category
            results = await client.search_by_category("umwelt")
    """

    BASE_URL = "https://ckan.govdata.de/api/3/action"
    API_NAME = "GovData"
    DEFAULT_DELAY = 0.5

    # GovData categories (DCAT-AP.de)
    CATEGORIES = {
        "bevoelkerung": "Bevölkerung und Gesellschaft",
        "bildung": "Bildung, Kultur und Sport",
        "energie": "Energie",
        "gesundheit": "Gesundheit",
        "geo": "Internationale Themen",
        "justiz": "Justiz, Rechtssystem und öffentliche Sicherheit",
        "landwirtschaft": "Landwirtschaft, Fischerei, Forstwirtschaft und Nahrungsmittel",
        "regierung": "Regierung und öffentlicher Sektor",
        "regionen": "Regionen und Städte",
        "umwelt": "Umwelt",
        "verkehr": "Verkehr",
        "wirtschaft": "Wirtschaft und Finanzen",
        "wissenschaft": "Wissenschaft und Technologie",
    }

    # Political levels
    POLITICAL_LEVELS = {
        "bund": "http://dcat-ap.de/def/politicalGeocoding/Level/federal",
        "land": "http://dcat-ap.de/def/politicalGeocoding/Level/state",
        "kommune": "http://dcat-ap.de/def/politicalGeocoding/Level/municipality",
    }

    async def search(
        self,
        query: str,
        rows: int = 100,
        start: int = 0,
        sort: str = "score desc, metadata_modified desc",
        filter_query: str | None = None,
        organization: str | None = None,
        groups: list[str] | None = None,
        tags: list[str] | None = None,
        res_format: str | None = None,
        **kwargs,
    ) -> APIResponse[APIDocument]:
        """
        Search for datasets.

        Args:
            query: Search query (Solr syntax supported)
            rows: Number of results per page (max 1000)
            start: Offset for pagination
            sort: Sort order
            filter_query: Additional Solr filter query
            organization: Filter by organization name
            groups: Filter by group names
            tags: Filter by tags
            res_format: Filter by resource format (e.g., "PDF", "CSV")
        """
        params = {
            "q": query or "*:*",
            "rows": min(rows, 1000),
            "start": start,
            "sort": sort,
        }

        # Build filter query
        fq_parts = []
        if filter_query:
            fq_parts.append(filter_query)
        if organization:
            fq_parts.append(f"organization:{organization}")
        if groups:
            fq_parts.append(f"groups:({' OR '.join(groups)})")
        if tags:
            fq_parts.append(f"tags:({' OR '.join(tags)})")
        if res_format:
            fq_parts.append(f"res_format:{res_format}")

        if fq_parts:
            params["fq"] = " AND ".join(fq_parts)

        data = await self.get("package_search", params)
        if not data or not data.get("success"):
            return APIResponse(data=[], total_count=0)

        result = data.get("result", {})
        datasets = [self._parse_dataset(d) for d in result.get("results", [])]
        documents = [self._dataset_to_document(d) for d in datasets]

        return APIResponse(
            data=documents,
            total_count=result.get("count", 0),
            page=(start // rows) + 1 if rows > 0 else 1,
            per_page=rows,
            has_more=start + rows < result.get("count", 0),
            raw_response=result,
        )

    async def search_by_category(
        self,
        category: str,
        query: str = "",
        **kwargs,
    ) -> APIResponse[APIDocument]:
        """
        Search within a specific category.

        Args:
            category: Category key (e.g., "umwelt", "energie")
            query: Additional search query
        """
        if category not in self.CATEGORIES:
            self.logger.warning("Unknown category", category=category)

        return await self.search(
            query=query,
            groups=[category],
            **kwargs,
        )

    async def search_by_location(
        self,
        location: str,
        query: str = "",
        political_level: str | None = None,
        **kwargs,
    ) -> APIResponse[APIDocument]:
        """
        Search datasets by geographic location.

        Args:
            location: Location name (e.g., "Nordrhein-Westfalen", "Köln")
            query: Additional search query
            political_level: Filter by level ("bund", "land", "kommune")
        """
        fq_parts = []

        # Text search in spatial fields
        if location:
            fq_parts.append(f"(spatial_text:{location} OR extras_spatial-text:{location})")

        if political_level and political_level in self.POLITICAL_LEVELS:
            level_uri = self.POLITICAL_LEVELS[political_level]
            fq_parts.append(f"extras_politicalGeocodingLevelURI:{level_uri}")

        filter_query = " AND ".join(fq_parts) if fq_parts else None

        return await self.search(
            query=query,
            filter_query=filter_query,
            **kwargs,
        )

    async def search_by_format(
        self,
        formats: list[str],
        query: str = "",
        **kwargs,
    ) -> APIResponse[APIDocument]:
        """
        Search datasets by resource format.

        Args:
            formats: List of formats (e.g., ["PDF", "CSV", "JSON"])
            query: Additional search query
        """
        format_query = " OR ".join(f"res_format:{f.upper()}" for f in formats)
        return await self.search(
            query=query,
            filter_query=f"({format_query})",
            **kwargs,
        )

    async def get_dataset(self, dataset_id: str) -> GovDataDataset | None:
        """
        Get a single dataset by ID or name.

        Args:
            dataset_id: Dataset ID (UUID) or name (slug)
        """
        data = await self.get("package_show", {"id": dataset_id})
        if not data or not data.get("success"):
            return None

        return self._parse_dataset(data.get("result", {}))

    async def get_document(self, document_id: str) -> APIDocument | None:
        """Get dataset and convert to APIDocument."""
        dataset = await self.get_dataset(document_id)
        if dataset:
            return self._dataset_to_document(dataset)
        return None

    async def get_organizations(
        self,
        sort: str = "package_count desc",
        all_fields: bool = True,
    ) -> AsyncIterator[GovDataOrganization]:
        """
        Get all organizations.

        Args:
            sort: Sort order
            all_fields: Include full organization details
        """
        params = {
            "sort": sort,
            "all_fields": all_fields,
        }

        data = await self.get("organization_list", params)
        if not data or not data.get("success"):
            return

        for org_data in data.get("result", []):
            if isinstance(org_data, str):
                # If all_fields=False, we get just names
                yield GovDataOrganization(id=org_data, name=org_data, title=org_data)
            else:
                yield self._parse_organization(org_data)

    async def get_organization(self, org_id: str) -> GovDataOrganization | None:
        """Get a single organization by ID or name."""
        data = await self.get("organization_show", {"id": org_id})
        if not data or not data.get("success"):
            return None

        return self._parse_organization(data.get("result", {}))

    async def get_groups(self) -> AsyncIterator[dict[str, Any]]:
        """Get all groups (categories)."""
        data = await self.get("group_list", {"all_fields": True})
        if not data or not data.get("success"):
            return

        for group in data.get("result", []):
            yield group

    async def get_tags(self, query: str | None = None) -> list[str]:
        """
        Get available tags.

        Args:
            query: Filter tags containing this string
        """
        params = {}
        if query:
            params["query"] = query

        data = await self.get("tag_list", params)
        if not data or not data.get("success"):
            return []

        return data.get("result", [])

    async def get_recently_changed(
        self,
        limit: int = 50,
    ) -> list[GovDataDataset]:
        """Get recently modified datasets."""
        data = await self.get("recently_changed_packages_activity_list", {"limit": limit})
        if not data or not data.get("success"):
            return []

        datasets = []
        for activity in data.get("result", []):
            pkg_data = activity.get("data", {}).get("package")
            if pkg_data:
                datasets.append(self._parse_dataset(pkg_data))

        return datasets

    async def iterate_all_datasets(
        self,
        query: str = "*:*",
        batch_size: int = 100,
        max_datasets: int = 10000,
        **search_kwargs,
    ) -> AsyncIterator[GovDataDataset]:
        """
        Iterate through all datasets matching a query.

        Args:
            query: Search query
            batch_size: Number of datasets per request
            max_datasets: Maximum total datasets to retrieve
        """
        start = 0
        total_retrieved = 0

        while total_retrieved < max_datasets:
            response = await self.search(
                query=query,
                rows=batch_size,
                start=start,
                **search_kwargs,
            )

            if not response.data:
                break

            for doc in response.data:
                dataset = await self.get_dataset(doc.source_id)
                if dataset:
                    yield dataset
                    total_retrieved += 1

                    if total_retrieved >= max_datasets:
                        return

            if not response.has_more:
                break

            start += batch_size

    def _parse_dataset(self, data: dict[str, Any]) -> GovDataDataset:
        """Parse CKAN package data into GovDataDataset."""
        org = data.get("organization") or {}
        extras = {e["key"]: e["value"] for e in data.get("extras", [])}

        return GovDataDataset(
            id=data.get("id", ""),
            name=data.get("name", ""),
            title=data.get("title", ""),
            notes=data.get("notes"),
            organization_id=org.get("id"),
            organization_name=org.get("name"),
            organization_title=org.get("title"),
            groups=[{"name": g.get("name"), "title": g.get("title")} for g in data.get("groups", [])],
            tags=[t.get("name", t) if isinstance(t, dict) else t for t in data.get("tags", [])],
            license_id=data.get("license_id"),
            license_title=data.get("license_title"),
            license_url=data.get("license_url"),
            resources=data.get("resources", []),
            num_resources=data.get("num_resources", len(data.get("resources", []))),
            author=data.get("author"),
            author_email=data.get("author_email"),
            maintainer=data.get("maintainer"),
            maintainer_email=data.get("maintainer_email"),
            temporal_start=self.parse_datetime(extras.get("temporal_start")),
            temporal_end=self.parse_datetime(extras.get("temporal_end")),
            spatial=data.get("spatial"),
            spatial_text=extras.get("spatial-text") or extras.get("spatial_text"),
            url=data.get("url"),
            created=self.parse_datetime(data.get("metadata_created")),
            modified=self.parse_datetime(data.get("metadata_modified")),
            state=data.get("state", "active"),
            is_private=data.get("private", False),
            dcat_type=extras.get("dcat_type"),
            political_geocoding_uri=extras.get("politicalGeocodingURI"),
            political_geocoding_level_uri=extras.get("politicalGeocodingLevelURI"),
            extras=extras,
        )

    def _parse_organization(self, data: dict[str, Any]) -> GovDataOrganization:
        """Parse CKAN organization data."""
        return GovDataOrganization(
            id=data.get("id", ""),
            name=data.get("name", ""),
            title=data.get("title", data.get("name", "")),
            description=data.get("description"),
            image_url=data.get("image_url"),
            state=data.get("state", "active"),
            package_count=data.get("package_count", 0),
            created=self.parse_datetime(data.get("created")),
        )

    def _dataset_to_document(self, dataset: GovDataDataset) -> APIDocument:
        """Convert GovDataDataset to generic APIDocument."""
        # Find primary resource (prefer PDF, then CSV, then any)
        file_url = None
        mime_type = None
        doc_type = "Dataset"

        for res in dataset.resources:
            fmt = res.get("format", "").upper()
            if fmt == "PDF":
                file_url = res.get("url")
                mime_type = res.get("mimetype", "application/pdf")
                doc_type = "PDF"
                break
            elif fmt in ("CSV", "JSON", "XML") and not file_url:
                file_url = res.get("url")
                mime_type = res.get("mimetype")
                doc_type = fmt

        # Get categories from groups
        categories = [g.get("title") or g.get("name") for g in dataset.groups]

        return APIDocument(
            source_id=dataset.id,
            external_id=dataset.name,
            title=dataset.title,
            url=f"https://www.govdata.de/web/guest/suchen/-/details/{dataset.name}",
            content=dataset.notes,
            document_type=doc_type,
            file_url=file_url,
            mime_type=mime_type,
            published_date=dataset.created,
            modified_date=dataset.modified,
            tags=dataset.tags,
            categories=categories,
            location=dataset.spatial_text,
            metadata={
                "organization": dataset.organization_title,
                "organization_id": dataset.organization_id,
                "license": dataset.license_title,
                "license_id": dataset.license_id,
                "num_resources": dataset.num_resources,
                "resource_formats": list({r.get("format", "").upper() for r in dataset.resources}),
                "temporal_start": dataset.temporal_start.isoformat() if dataset.temporal_start else None,
                "temporal_end": dataset.temporal_end.isoformat() if dataset.temporal_end else None,
                "political_level": dataset.political_geocoding_level_uri,
            },
        )
