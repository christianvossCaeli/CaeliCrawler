"""CrawlJob schemas for API validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.crawl_job import JobStatus


class CrawlJobCreate(BaseModel):
    """Schema for creating a crawl job."""

    source_id: Optional[UUID] = Field(None, description="Specific source to crawl")
    category_id: Optional[UUID] = Field(None, description="Crawl all sources in category")
    priority: int = Field(default=0, description="Job priority")

    def model_post_init(self, __context):
        if not self.source_id and not self.category_id:
            raise ValueError("Either source_id or category_id must be provided")


class CrawlJobResponse(BaseModel):
    """Schema for crawl job response."""

    id: UUID
    source_id: UUID
    category_id: UUID
    status: JobStatus
    scheduled_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    pages_crawled: int
    documents_found: int
    documents_processed: int
    documents_new: int
    documents_updated: int
    error_count: int
    celery_task_id: Optional[str]

    # Computed
    duration_seconds: Optional[float] = None
    source_name: Optional[str] = None
    category_name: Optional[str] = None

    model_config = {"from_attributes": True}


class CrawlJobListResponse(BaseModel):
    """Schema for crawl job list response."""

    items: List[CrawlJobResponse]
    total: int
    page: int
    per_page: int
    pages: int


class CrawlJobStats(BaseModel):
    """Statistics for crawl jobs."""

    total_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_documents: int
    total_pages_crawled: int
    avg_duration_seconds: Optional[float]


class CrawlJobDetailResponse(CrawlJobResponse):
    """Detailed crawl job response with error log."""

    error_log: List[Dict[str, Any]] = Field(default_factory=list)
    stats: Dict[str, Any] = Field(default_factory=dict)


class StartCrawlRequest(BaseModel):
    """Request to start a crawl operation."""

    source_ids: Optional[List[UUID]] = Field(None, description="Specific sources to crawl")
    category_id: Optional[UUID] = Field(None, description="Crawl all sources in category")
    force: bool = Field(default=False, description="Force crawl even if recently crawled")

    # Additional filters for flexible crawl selection
    country: Optional[str] = Field(None, description="Filter by country code (DE, GB, etc.)")
    status: Optional[str] = Field(None, description="Filter by source status (ACTIVE, PENDING, ERROR)")
    source_type: Optional[str] = Field(None, description="Filter by source type (WEBSITE, OPARL_API, RSS)")
    search: Optional[str] = Field(None, description="Filter by name or URL")
    limit: Optional[int] = Field(None, ge=1, le=10000, description="Maximum number of sources to crawl")


class StartCrawlResponse(BaseModel):
    """Response from starting a crawl operation."""

    jobs_created: int
    job_ids: List[UUID]
    message: str
