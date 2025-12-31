"""Document schemas for API validation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.document import ProcessingStatus


class DocumentResponse(BaseModel):
    """Schema for document response."""

    id: UUID
    source_id: UUID
    category_id: UUID
    crawl_job_id: UUID | None
    document_type: str
    original_url: str
    title: str | None
    file_path: str | None
    file_hash: str
    file_size: int
    page_count: int | None
    processing_status: ProcessingStatus
    processing_error: str | None
    discovered_at: datetime
    downloaded_at: datetime | None
    processed_at: datetime | None
    document_date: datetime | None

    # Page-based analysis tracking
    page_analysis_status: str | None = None
    relevant_pages: list[int] | None = None
    analyzed_pages: list[int] | None = None
    total_relevant_pages: int | None = None
    page_analysis_note: str | None = None

    # Related info
    source_name: str | None = None
    category_name: str | None = None
    has_extracted_data: bool = False
    extraction_count: int = 0

    model_config = {"from_attributes": True}


class DocumentDetailResponse(DocumentResponse):
    """Detailed document response with text content."""

    raw_text: str | None = None
    extracted_data: list[dict[str, Any]] = Field(default_factory=list)


class DocumentListResponse(BaseModel):
    """Schema for document list response."""

    items: list[DocumentResponse]
    total: int
    page: int
    per_page: int
    pages: int


class DocumentProcessingStatsResponse(BaseModel):
    """Aggregated document counts by processing status."""

    total: int
    by_status: dict[str, int] = Field(default_factory=dict)


class DocumentSearchParams(BaseModel):
    """Parameters for document search."""

    query: str | None = Field(None, description="Full-text search query")
    category_id: UUID | None = Field(None, description="Filter by category")
    source_id: UUID | None = Field(None, description="Filter by source")
    document_type: str | None = Field(None, description="Filter by document type")
    processing_status: ProcessingStatus | None = Field(None, description="Filter by status")
    from_date: datetime | None = Field(None, description="Documents discovered after this date")
    to_date: datetime | None = Field(None, description="Documents discovered before this date")
    has_extracted_data: bool | None = Field(None, description="Filter by extraction status")
    min_confidence: float | None = Field(None, ge=0, le=1, description="Minimum confidence score")


class DocumentStats(BaseModel):
    """Statistics for documents."""

    total: int
    by_status: dict[str, int]
    by_type: dict[str, int]
    by_category: dict[str, int]
    total_size_bytes: int
    avg_page_count: float | None
