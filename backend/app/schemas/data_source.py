"""DataSource schemas for API validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.data_source import SourceStatus, SourceType


class CrawlConfig(BaseModel):
    """Crawl configuration for a data source."""

    # CSS selectors for finding content
    content_selector: Optional[str] = Field(None, description="CSS selector for main content")
    link_selector: Optional[str] = Field(None, description="CSS selector for document links")
    title_selector: Optional[str] = Field(None, description="CSS selector for titles")
    date_selector: Optional[str] = Field(None, description="CSS selector for dates")

    # Crawl behavior
    max_depth: int = Field(default=3, ge=1, le=10, description="Maximum crawl depth")
    max_pages: int = Field(default=100, ge=1, le=10000, description="Maximum pages to crawl")
    follow_external_links: bool = Field(default=False, description="Follow external links")

    # URL filtering (regex patterns)
    url_include_patterns: List[str] = Field(
        default_factory=list,
        description="Regex patterns - URLs must match at least one (if set)",
    )
    url_exclude_patterns: List[str] = Field(
        default_factory=list,
        description="Regex patterns - URLs matching any will be skipped",
    )

    # File types to download
    download_extensions: List[str] = Field(
        default=["pdf", "doc", "docx"],
        description="File extensions to download",
    )

    # Custom headers
    headers: Dict[str, str] = Field(default_factory=dict, description="Custom HTTP headers")

    # JavaScript rendering
    render_javascript: bool = Field(default=False, description="Use Playwright for JS rendering")
    wait_for_selector: Optional[str] = Field(None, description="Wait for selector before scraping")

    # News/RSS Crawler settings
    crawl_type: Optional[str] = Field(None, description="Crawl type: auto, rss, html, news")
    news_path: Optional[str] = Field(None, description="Path to news section (e.g., /aktuelles)")
    rss_url: Optional[str] = Field(None, description="RSS feed URL")
    max_articles: int = Field(default=50, ge=1, le=500, description="Maximum articles to fetch")
    filter_keywords: List[str] = Field(default_factory=list, description="Keywords to filter articles")

    # API-specific settings (for CUSTOM_API)
    api_type: Optional[str] = Field(None, description="API type: govdata, dip_bundestag, fragdenstaat")
    search_query: Optional[str] = Field(None, description="Search query for API")
    wahlperiode: Optional[int] = Field(None, description="Legislative period (for DIP)")
    vorgangstyp: Optional[str] = Field(None, description="Process type (for DIP)")
    max_results: int = Field(default=100, ge=1, le=1000, description="Maximum results from API")

    # Entity API settings (for REST_API and SPARQL_API source types)
    # These APIs are used to keep Entities up-to-date
    entity_api_type: Optional[str] = Field(
        None,
        description="Entity API type: rest or sparql"
    )
    entity_api_endpoint: Optional[str] = Field(
        None,
        description="API endpoint path (appended to base_url)"
    )
    entity_api_method: str = Field(
        default="GET",
        description="HTTP method for REST API"
    )
    entity_api_query: Optional[str] = Field(
        None,
        description="SPARQL query string (for SPARQL_API)"
    )
    entity_api_template: Optional[str] = Field(
        None,
        description="Predefined API template name (e.g., 'caeli_auction_windparks')"
    )
    entity_field_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping from API fields to Entity fields (e.g., {'auctionId': 'external_id'})"
    )
    entity_type_slug: Optional[str] = Field(
        None,
        description="Target EntityType slug for updates"
    )
    entity_update_strategy: str = Field(
        default="merge",
        description="Update strategy: merge (update existing), replace (overwrite), upsert (create or update)"
    )
    entity_id_field: Optional[str] = Field(
        None,
        description="API field used to identify existing entities (default: external_id from field_mapping)"
    )

    # SharePoint settings (for SHAREPOINT source type)
    site_url: Optional[str] = Field(
        None,
        description="SharePoint site URL (e.g., 'contoso.sharepoint.com:/sites/Documents')"
    )
    drive_name: Optional[str] = Field(
        None,
        description="Name of the document library (default: first available)"
    )
    folder_path: Optional[str] = Field(
        None,
        description="Path within the drive to crawl (default: root)"
    )
    file_extensions: List[str] = Field(
        default_factory=lambda: [".pdf", ".docx", ".doc", ".xlsx", ".pptx"],
        description="File extensions to include (e.g., ['.pdf', '.docx'])"
    )
    recursive: bool = Field(
        default=True,
        description="Whether to include files from subfolders"
    )
    exclude_patterns: List[str] = Field(
        default_factory=lambda: ["~$*", "*.tmp", ".DS_Store"],
        description="File patterns to exclude (glob syntax)"
    )
    max_files: int = Field(
        default=1000,
        ge=1,
        le=10000,
        description="Maximum number of files to crawl"
    )

    model_config = {"extra": "allow"}  # Allow additional fields


class DataSourceBase(BaseModel):
    """Base data source schema."""

    name: str = Field(..., min_length=1, max_length=255, description="Source name")
    source_type: SourceType = Field(..., description="Type of data source")
    base_url: str = Field(..., description="Base URL for the source")
    api_endpoint: Optional[str] = Field(None, description="API endpoint (for API sources)")

    crawl_config: CrawlConfig = Field(default_factory=CrawlConfig, description="Crawl configuration")
    extra_data: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    priority: int = Field(default=0, description="Crawl priority (higher = more important)")
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for filtering/categorization (e.g., ['nrw', 'kommunal', 'windkraft'])",
    )


class CategoryLink(BaseModel):
    """Schema for category link in data source."""
    id: UUID
    name: str
    slug: str
    is_primary: bool = False


class DataSourceCreate(DataSourceBase):
    """Schema for creating a data source."""

    # Legacy single category (for backwards compatibility)
    category_id: Optional[UUID] = Field(None, description="Primary category ID (legacy)")
    # New: multiple categories
    category_ids: Optional[List[UUID]] = Field(None, description="List of category IDs")
    auth_config: Optional[Dict[str, Any]] = Field(None, description="Authentication configuration")


class DataSourceUpdate(BaseModel):
    """Schema for updating a data source."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    source_type: Optional[SourceType] = None
    base_url: Optional[str] = None
    api_endpoint: Optional[str] = None

    crawl_config: Optional[CrawlConfig] = None
    auth_config: Optional[Dict[str, Any]] = None
    extra_data: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None
    status: Optional[SourceStatus] = None
    tags: Optional[List[str]] = Field(None, description="Tags for filtering/categorization")

    # Category management (N:M)
    category_ids: Optional[List[UUID]] = Field(None, description="List of category IDs (replaces existing)")
    primary_category_id: Optional[UUID] = Field(None, description="Primary category ID")


class DataSourceResponse(DataSourceBase):
    """Schema for data source response."""

    id: UUID
    # Legacy category_id (nullable for N:M transition)
    category_id: Optional[UUID] = None
    status: SourceStatus
    last_crawl: Optional[datetime]
    last_change_detected: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    # Computed fields
    document_count: int = Field(default=0, description="Number of documents")
    job_count: int = Field(default=0, description="Number of crawl jobs")
    category_name: Optional[str] = Field(default=None, description="Primary category name (legacy)")

    # N:M categories
    categories: List[CategoryLink] = Field(default_factory=list, description="All linked categories")

    model_config = {"from_attributes": True}


class DataSourceListResponse(BaseModel):
    """Schema for data source list response."""

    items: List[DataSourceResponse]
    total: int
    page: int
    per_page: int
    pages: int


class DataSourceBulkImportItem(BaseModel):
    """Single item for bulk import."""

    name: str = Field(..., min_length=1, max_length=255)
    base_url: str
    source_type: SourceType = Field(default=SourceType.WEBSITE)
    tags: List[str] = Field(default_factory=list, description="Tags for this specific source")
    extra_data: Dict[str, Any] = Field(default_factory=dict)


class DataSourceBulkImport(BaseModel):
    """Schema for bulk importing data sources."""

    category_ids: List[UUID] = Field(..., min_length=1, description="Categories to assign (N:M)")
    default_tags: List[str] = Field(default_factory=list, description="Tags applied to all sources")
    sources: List[DataSourceBulkImportItem] = Field(..., min_length=1, max_length=1000)
    skip_duplicates: bool = Field(default=True, description="Skip sources with duplicate URLs")


class DataSourceBulkImportResult(BaseModel):
    """Result of bulk import operation."""

    imported: int
    skipped: int
    errors: List[Dict[str, str]]


# =============================================================================
# Meta Endpoints Response Models
# =============================================================================


class CategoryCount(BaseModel):
    """Category with source count."""

    id: str
    name: str
    slug: str
    count: int


class TypeCount(BaseModel):
    """Source type with count."""

    type: Optional[str]
    count: int


class StatusCount(BaseModel):
    """Source status with count."""

    status: Optional[str]
    count: int


class SourceCountsResponse(BaseModel):
    """Response for source counts endpoint."""

    total: int = Field(..., description="Total number of sources")
    categories: List[CategoryCount] = Field(default_factory=list, description="Counts by category")
    types: List[TypeCount] = Field(default_factory=list, description="Counts by source type")
    statuses: List[StatusCount] = Field(default_factory=list, description="Counts by status")


class TagCount(BaseModel):
    """Tag with usage count."""

    tag: str
    count: int


class TagsResponse(BaseModel):
    """Response for available tags endpoint."""

    tags: List[TagCount] = Field(default_factory=list, description="Tags with usage counts")
