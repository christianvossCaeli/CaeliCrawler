"""ExtractedData schemas for API validation."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class EntityReference(BaseModel):
    """
    Schema for AI-extracted entity references.

    Represents a reference to an entity found in the document.
    Example: A regional planning document might reference a municipality.
    """

    entity_type: str = Field(..., description="Entity type slug (e.g., 'territorial-entity', 'person')")
    entity_name: str = Field(..., description="Entity name as found in the document")
    entity_id: UUID | None = Field(None, description="UUID of matched Entity (if resolved)")
    role: str = Field(default="primary", description="Role: 'primary', 'secondary', 'decision_maker'")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence score 0.0-1.0")


class ExtractedDataResponse(BaseModel):
    """Schema for extracted data response."""

    id: UUID
    document_id: UUID
    category_id: UUID
    extraction_type: str
    extracted_content: dict[str, Any]
    confidence_score: float | None
    ai_model_used: str | None
    ai_prompt_version: str | None
    tokens_used: int | None
    human_verified: bool
    human_corrections: dict[str, Any] | None
    verified_by: str | None
    verified_at: datetime | None
    # Rejection fields
    is_rejected: bool = False
    rejected_by: str | None = None
    rejected_at: datetime | None = None
    rejection_reason: str | None = None
    relevance_score: float | None
    created_at: datetime
    updated_at: datetime

    # Entity references (new generic system)
    entity_references: list[EntityReference] = Field(default_factory=list)
    primary_entity_id: UUID | None = None

    @field_validator("entity_references", mode="before")
    @classmethod
    def convert_none_to_empty_list(cls, v):
        """Convert None to empty list for entity_references."""
        if v is None:
            return []
        return v

    # Computed fields for display
    final_content: dict[str, Any] = Field(default_factory=dict)
    document_title: str | None = None
    document_url: str | None = None
    source_name: str | None = None

    model_config = {"from_attributes": True}

    def get_entity_by_type(self, entity_type: str) -> Optional["EntityReference"]:
        """Get first entity reference of a specific type."""
        for ref in self.entity_references:
            if ref.entity_type == entity_type:
                return ref
        return None

    def get_all_entities_by_type(self, entity_type: str) -> list["EntityReference"]:
        """Get all entity references of a specific type."""
        return [ref for ref in self.entity_references if ref.entity_type == entity_type]


class ExtractedDataListResponse(BaseModel):
    """Schema for extracted data list response."""

    items: list[ExtractedDataResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ExtractedDataUpdate(BaseModel):
    """Schema for updating extracted data (human corrections)."""

    corrections: dict[str, Any] = Field(..., description="Human corrections to extracted data")


class ExtractedDataVerify(BaseModel):
    """Schema for verifying extracted data."""

    verified: bool = Field(default=True, description="Mark as verified")
    verified_by: str | None = Field(
        default=None,
        description="Deprecated: verifier is derived from the authenticated user",
    )
    corrections: dict[str, Any] | None = Field(None, description="Optional corrections")


class ExtractedDataReject(BaseModel):
    """Schema for rejecting extracted data."""

    rejected: bool = Field(default=True, description="Mark as rejected")
    reason: str | None = Field(None, description="Optional rejection reason", max_length=1000)
    cascade_to_facets: bool = Field(
        default=True,
        description="Also deactivate related facet values from the same document",
    )


class ExtractedDataRejectResponse(BaseModel):
    """Response for reject operation with cascade information."""

    extraction: "ExtractedDataResponse"
    deactivated_facets_count: int = Field(description="Number of facet values that were deactivated")
    protected_facets_count: int = Field(
        description="Number of facet values that were protected (already verified/corrected)"
    )


class ExtractedDataBulkVerify(BaseModel):
    """Schema for bulk verifying extracted data."""

    ids: list[UUID] = Field(..., description="List of extraction IDs to verify", min_length=1, max_length=100)


class ExtractedDataBulkVerifyResponse(BaseModel):
    """Response for bulk verify operation."""

    verified_ids: list[UUID] = Field(default_factory=list, description="Successfully verified IDs")
    failed_ids: list[UUID] = Field(default_factory=list, description="Failed verification IDs")
    verified_count: int = Field(..., description="Number of successfully verified extractions")
    failed_count: int = Field(..., description="Number of failed verifications")


class ExtractedDataBulkReject(BaseModel):
    """Schema for bulk rejecting extracted data."""

    ids: list[UUID] = Field(..., description="List of extraction IDs to reject", min_length=1, max_length=100)
    cascade_to_facets: bool = Field(default=True, description="Whether to deactivate related facet values")


class ExtractedDataBulkRejectResponse(BaseModel):
    """Response for bulk reject operation."""

    rejected_ids: list[UUID] = Field(default_factory=list, description="Successfully rejected IDs")
    failed_ids: list[UUID] = Field(default_factory=list, description="Failed rejection IDs")
    rejected_count: int = Field(..., description="Number of successfully rejected extractions")
    failed_count: int = Field(..., description="Number of failed rejections")
    total_deactivated_facets: int = Field(default=0, description="Total facet values deactivated")
    total_protected_facets: int = Field(default=0, description="Total facet values that were protected")


class ExtractedDataSearchParams(BaseModel):
    """Parameters for searching extracted data."""

    category_id: UUID | None = None
    source_id: UUID | None = None
    extraction_type: str | None = None
    min_confidence: float | None = Field(None, ge=0, le=1)
    human_verified: bool | None = None
    from_date: datetime | None = None
    to_date: datetime | None = None


class ExtractedDataExport(BaseModel):
    """Schema for exported data."""

    id: UUID
    document_id: UUID
    document_url: str
    document_title: str | None
    source_name: str
    category_name: str
    extraction_type: str
    extracted_content: dict[str, Any]
    confidence_score: float | None
    human_verified: bool
    created_at: datetime


class ExtractionStats(BaseModel):
    """Statistics for extractions."""

    total: int
    verified: int
    unverified: int
    avg_confidence: float | None
    by_type: dict[str, int]
    by_category: dict[str, int]
    high_confidence_count: int  # >= 0.8
    low_confidence_count: int  # < 0.5


# =============================================================================
# Display Configuration Schemas
# =============================================================================


class DisplayColumn(BaseModel):
    """Configuration for a single result display column."""

    key: str = Field(..., description="Data key to display (e.g., 'document', 'entity_references.territorial-entity')")
    label: str = Field(..., description="Column header label")
    type: str = Field(
        default="text", description="Column type: 'text', 'document_link', 'entity_link', 'confidence', 'date'"
    )
    width: str | None = Field(None, description="Column width (e.g., '150px', '20%')")
    sortable: bool = Field(default=True, description="Whether column is sortable")


class DisplayFieldsConfig(BaseModel):
    """
    Configuration for result display columns.

    Used by the frontend to dynamically render the results table.
    """

    columns: list[DisplayColumn] = Field(
        default_factory=list,
        description="List of columns to display",
    )
    entity_reference_columns: list[str] = Field(
        default_factory=list,
        description="Entity types to show as separate columns (e.g., ['territorial-entity', 'person'])",
    )

    @classmethod
    def default_config(cls) -> "DisplayFieldsConfig":
        """Return default display configuration."""
        return cls(
            columns=[
                DisplayColumn(key="document", label="Dokument", type="document_link", width="220px"),
                DisplayColumn(key="confidence_score", label="Konfidenz", type="confidence", width="110px"),
                DisplayColumn(key="relevance_score", label="Relevanz", type="confidence", width="110px"),
                DisplayColumn(key="created_at", label="Erfasst", type="date", width="100px"),
            ],
            entity_reference_columns=[],
        )
