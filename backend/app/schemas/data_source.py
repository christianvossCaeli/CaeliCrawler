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

    # API-specific settings
    api_type: Optional[str] = Field(None, description="API type: govdata, dip_bundestag, fragdenstaat")
    search_query: Optional[str] = Field(None, description="Search query for API")
    wahlperiode: Optional[int] = Field(None, description="Legislative period (for DIP)")
    vorgangstyp: Optional[str] = Field(None, description="Process type (for DIP)")
    max_results: int = Field(default=100, ge=1, le=1000, description="Maximum results from API")

    model_config = {"extra": "allow"}  # Allow additional fields


class DataSourceBase(BaseModel):
    """Base data source schema."""

    name: str = Field(..., min_length=1, max_length=255, description="Source name")
    source_type: SourceType = Field(..., description="Type of data source")
    base_url: str = Field(..., description="Base URL for the source")
    api_endpoint: Optional[str] = Field(None, description="API endpoint (for API sources)")

    # Location for clustering results (international)
    country: Optional[str] = Field(None, max_length=2, description="ISO 3166-1 alpha-2 country code")
    location_id: Optional[UUID] = Field(None, description="FK to locations table")
    location_name: Optional[str] = Field(None, max_length=255, description="Location name")
    region: Optional[str] = Field(None, max_length=255, description="Region")
    admin_level_1: Optional[str] = Field(None, max_length=100, description="State/Bundesland/Region")

    crawl_config: CrawlConfig = Field(default_factory=CrawlConfig, description="Crawl configuration")
    extra_data: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    priority: int = Field(default=0, description="Crawl priority (higher = more important)")


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

    # Location for clustering (international)
    country: Optional[str] = Field(None, max_length=2)
    location_id: Optional[UUID] = None
    location_name: Optional[str] = Field(None, max_length=255)
    region: Optional[str] = Field(None, max_length=255)
    admin_level_1: Optional[str] = Field(None, max_length=100)

    crawl_config: Optional[CrawlConfig] = None
    auth_config: Optional[Dict[str, Any]] = None
    extra_data: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None
    status: Optional[SourceStatus] = None

    # Category management (N:M)
    category_ids: Optional[List[UUID]] = Field(None, description="List of category IDs (replaces existing)")
    primary_category_id: Optional[UUID] = Field(None, description="Primary category ID")


class DataSourceResponse(DataSourceBase):
    """Schema for data source response."""

    id: UUID
    # Legacy category_id (nullable for N:M transition)
    category_id: Optional[UUID] = None
    location_id: Optional[UUID] = None
    country: Optional[str] = None
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
    extra_data: Dict[str, Any] = Field(default_factory=dict)


class DataSourceBulkImport(BaseModel):
    """Schema for bulk importing data sources."""

    category_id: UUID
    sources: List[DataSourceBulkImportItem] = Field(..., min_length=1, max_length=1000)
    skip_duplicates: bool = Field(default=True, description="Skip sources with duplicate URLs")


class DataSourceBulkImportResult(BaseModel):
    """Result of bulk import operation."""

    imported: int
    skipped: int
    errors: List[Dict[str, str]]
