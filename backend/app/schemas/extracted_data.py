"""ExtractedData schemas for API validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ExtractedDataResponse(BaseModel):
    """Schema for extracted data response."""

    id: UUID
    document_id: UUID
    category_id: UUID
    extraction_type: str
    extracted_content: Dict[str, Any]
    confidence_score: Optional[float]
    ai_model_used: Optional[str]
    ai_prompt_version: Optional[str]
    tokens_used: Optional[int]
    human_verified: bool
    human_corrections: Optional[Dict[str, Any]]
    verified_by: Optional[str]
    verified_at: Optional[datetime]
    relevance_score: Optional[float]
    created_at: datetime
    updated_at: datetime

    # Computed
    final_content: Dict[str, Any] = Field(default_factory=dict)
    document_title: Optional[str] = None
    document_url: Optional[str] = None
    source_name: Optional[str] = None

    model_config = {"from_attributes": True}


class ExtractedDataListResponse(BaseModel):
    """Schema for extracted data list response."""

    items: List[ExtractedDataResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ExtractedDataUpdate(BaseModel):
    """Schema for updating extracted data (human corrections)."""

    corrections: Dict[str, Any] = Field(..., description="Human corrections to extracted data")


class ExtractedDataVerify(BaseModel):
    """Schema for verifying extracted data."""

    verified: bool = Field(default=True, description="Mark as verified")
    verified_by: str = Field(..., min_length=1, description="Name of verifier")
    corrections: Optional[Dict[str, Any]] = Field(None, description="Optional corrections")


class ExtractedDataSearchParams(BaseModel):
    """Parameters for searching extracted data."""

    category_id: Optional[UUID] = None
    source_id: Optional[UUID] = None
    extraction_type: Optional[str] = None
    min_confidence: Optional[float] = Field(None, ge=0, le=1)
    human_verified: Optional[bool] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


class ExtractedDataExport(BaseModel):
    """Schema for exported data."""

    id: UUID
    document_id: UUID
    document_url: str
    document_title: Optional[str]
    source_name: str
    category_name: str
    extraction_type: str
    extracted_content: Dict[str, Any]
    confidence_score: Optional[float]
    human_verified: bool
    created_at: datetime


class ExtractionStats(BaseModel):
    """Statistics for extractions."""

    total: int
    verified: int
    unverified: int
    avg_confidence: Optional[float]
    by_type: Dict[str, int]
    by_category: Dict[str, int]
    high_confidence_count: int  # >= 0.8
    low_confidence_count: int   # < 0.5
