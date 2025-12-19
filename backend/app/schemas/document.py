"""Document schemas for API validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.document import ProcessingStatus


class DocumentResponse(BaseModel):
    """Schema for document response."""

    id: UUID
    source_id: UUID
    category_id: UUID
    crawl_job_id: Optional[UUID]
    document_type: str
    original_url: str
    title: Optional[str]
    file_path: Optional[str]
    file_hash: str
    file_size: int
    page_count: Optional[int]
    processing_status: ProcessingStatus
    processing_error: Optional[str]
    discovered_at: datetime
    downloaded_at: Optional[datetime]
    processed_at: Optional[datetime]
    document_date: Optional[datetime]

    # Related info
    source_name: Optional[str] = None
    category_name: Optional[str] = None
    has_extracted_data: bool = False
    extraction_count: int = 0

    model_config = {"from_attributes": True}


class DocumentDetailResponse(DocumentResponse):
    """Detailed document response with text content."""

    raw_text: Optional[str] = None
    extracted_data: List[Dict[str, Any]] = Field(default_factory=list)


class DocumentListResponse(BaseModel):
    """Schema for document list response."""

    items: List[DocumentResponse]
    total: int
    page: int
    per_page: int
    pages: int


class DocumentSearchParams(BaseModel):
    """Parameters for document search."""

    query: Optional[str] = Field(None, description="Full-text search query")
    category_id: Optional[UUID] = Field(None, description="Filter by category")
    source_id: Optional[UUID] = Field(None, description="Filter by source")
    document_type: Optional[str] = Field(None, description="Filter by document type")
    processing_status: Optional[ProcessingStatus] = Field(None, description="Filter by status")
    from_date: Optional[datetime] = Field(None, description="Documents discovered after this date")
    to_date: Optional[datetime] = Field(None, description="Documents discovered before this date")
    has_extracted_data: Optional[bool] = Field(None, description="Filter by extraction status")
    min_confidence: Optional[float] = Field(None, ge=0, le=1, description="Minimum confidence score")


class DocumentStats(BaseModel):
    """Statistics for documents."""

    total: int
    by_status: Dict[str, int]
    by_type: Dict[str, int]
    by_category: Dict[str, int]
    total_size_bytes: int
    avg_page_count: Optional[float]
