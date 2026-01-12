"""Schemas for entity attachments."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AttachmentSearchResult(BaseModel):
    """Single search result for attachment full-text search."""

    id: UUID
    entity_id: UUID
    entity_name: str
    filename: str
    content_type: str
    file_size: int
    description: str | None = None
    analysis_status: str
    headline: str | None = Field(None, description="Search match highlight with <mark> tags")
    rank: float = Field(0.0, description="Search relevance score (0.0 to 1.0)")
    created_at: datetime
    analyzed_at: datetime | None = None
    is_image: bool = False
    is_pdf: bool = False


class AttachmentSearchResponse(BaseModel):
    """Response for attachment search endpoint."""

    items: list[AttachmentSearchResult]
    total: int
    page: int
    per_page: int
    pages: int
    query: str
    search_time_ms: float = Field(..., description="Search execution time in milliseconds")


class AttachmentBase(BaseModel):
    """Base attachment schema."""

    id: UUID
    entity_id: UUID
    filename: str
    content_type: str
    file_size: int
    description: str | None = None
    analysis_status: str
    analysis_result: dict | None = None
    analysis_error: str | None = None
    analyzed_at: datetime | None = None
    ai_model_used: str | None = None
    uploaded_by_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    is_image: bool = False
    is_pdf: bool = False


class AttachmentListResponse(BaseModel):
    """Response for listing attachments."""

    items: list[AttachmentBase]
    total: int
