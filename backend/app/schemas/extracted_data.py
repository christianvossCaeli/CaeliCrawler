"""ExtractedData schemas for API validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EntityReference(BaseModel):
    """
    Schema for AI-extracted entity references.

    Represents a reference to an entity found in the document.
    Example: A regional planning document might reference a municipality.
    """

    entity_type: str = Field(..., description="Entity type slug (e.g., 'territorial-entity', 'person')")
    entity_name: str = Field(..., description="Entity name as found in the document")
    entity_id: Optional[UUID] = Field(None, description="UUID of matched Entity (if resolved)")
    role: str = Field(default="primary", description="Role: 'primary', 'secondary', 'decision_maker'")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence score 0.0-1.0")


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

    # Entity references (new generic system)
    entity_references: List[EntityReference] = Field(default_factory=list)
    primary_entity_id: Optional[UUID] = None

    # Computed fields for display
    final_content: Dict[str, Any] = Field(default_factory=dict)
    document_title: Optional[str] = None
    document_url: Optional[str] = None
    source_name: Optional[str] = None

    model_config = {"from_attributes": True}

    def get_entity_by_type(self, entity_type: str) -> Optional["EntityReference"]:
        """Get first entity reference of a specific type."""
        for ref in self.entity_references:
            if ref.entity_type == entity_type:
                return ref
        return None

    def get_all_entities_by_type(self, entity_type: str) -> List["EntityReference"]:
        """Get all entity references of a specific type."""
        return [ref for ref in self.entity_references if ref.entity_type == entity_type]


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


# =============================================================================
# Display Configuration Schemas
# =============================================================================


class DisplayColumn(BaseModel):
    """Configuration for a single result display column."""

    key: str = Field(..., description="Data key to display (e.g., 'document', 'entity_references.territorial-entity')")
    label: str = Field(..., description="Column header label")
    type: str = Field(default="text", description="Column type: 'text', 'document_link', 'entity_link', 'confidence', 'date'")
    width: Optional[str] = Field(None, description="Column width (e.g., '150px', '20%')")
    sortable: bool = Field(default=True, description="Whether column is sortable")


class DisplayFieldsConfig(BaseModel):
    """
    Configuration for result display columns.

    Used by the frontend to dynamically render the results table.
    """

    columns: List[DisplayColumn] = Field(
        default_factory=list,
        description="List of columns to display",
    )
    entity_reference_columns: List[str] = Field(
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
