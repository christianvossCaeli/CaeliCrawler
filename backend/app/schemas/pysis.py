"""PySis integration schemas for API validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# === Field Definition (used in templates) ===

class PySisFieldDefinition(BaseModel):
    """Definition of a single field within a template."""

    internal_name: str = Field(..., min_length=1, description="Display name, e.g., 'Ansprechpartner Gemeinde'")
    pysis_field_name: str = Field(..., min_length=1, description="PySis API field name")
    field_type: str = Field(default="text", description="Field type: text, number, date, boolean, list")
    ai_extraction_prompt: Optional[str] = Field(None, description="Custom AI prompt for extracting this field")


# === Template Schemas ===

class PySisFieldTemplateCreate(BaseModel):
    """Schema for creating a new field template."""

    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    fields: List[PySisFieldDefinition] = Field(default_factory=list, description="Field definitions")


class PySisFieldTemplateUpdate(BaseModel):
    """Schema for updating a template."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    fields: Optional[List[PySisFieldDefinition]] = None
    is_active: Optional[bool] = None


class PySisFieldTemplateResponse(BaseModel):
    """Schema for template response."""

    id: UUID
    name: str
    description: Optional[str]
    fields: List[PySisFieldDefinition]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PySisFieldTemplateListResponse(BaseModel):
    """Schema for template list response."""

    items: List[PySisFieldTemplateResponse]
    total: int


# === Process Schemas ===

class PySisProcessCreate(BaseModel):
    """Schema for creating a new process link."""

    pysis_process_id: str = Field(..., min_length=1, description="External PySis process ID")
    name: Optional[str] = Field(None, max_length=255, description="Optional display name")
    description: Optional[str] = Field(None, description="Notes about this process")
    template_id: Optional[UUID] = Field(None, description="Template to apply on creation")


class PySisProcessUpdate(BaseModel):
    """Schema for updating a process."""

    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None


class PySisProcessResponse(BaseModel):
    """Schema for process response."""

    id: UUID
    entity_name: Optional[str] = None
    pysis_process_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    template_id: Optional[UUID] = None
    last_synced_at: Optional[datetime] = None
    sync_status: str
    sync_error: Optional[str] = None
    field_count: int = Field(default=0, description="Number of fields in this process")
    created_at: datetime
    updated_at: datetime
    extra: Optional[Dict[str, Any]] = Field(None, description="Additional response data")

    model_config = {"from_attributes": True}


class PySisProcessListResponse(BaseModel):
    """Schema for process list response."""

    items: List[PySisProcessResponse]
    total: int


class PySisProcessDetailResponse(PySisProcessResponse):
    """Schema for detailed process response with fields."""

    fields: List["PySisFieldResponse"] = Field(default_factory=list)


# === Field Schemas ===

class PySisFieldCreate(BaseModel):
    """Schema for creating a new field."""

    internal_name: str = Field(..., min_length=1, max_length=255, description="Display name")
    pysis_field_name: str = Field(..., min_length=1, max_length=255, description="PySis API field name")
    field_type: str = Field(default="text", description="Field type")
    ai_extraction_enabled: bool = Field(default=True, description="Enable AI extraction")
    ai_extraction_prompt: Optional[str] = Field(None, description="Custom AI prompt")


class PySisFieldUpdate(BaseModel):
    """Schema for updating a field."""

    internal_name: Optional[str] = Field(None, min_length=1, max_length=255)
    field_type: Optional[str] = None
    ai_extraction_enabled: Optional[bool] = None
    ai_extraction_prompt: Optional[str] = None


class PySisFieldValueUpdate(BaseModel):
    """Schema for updating a field's value."""

    value: Optional[str] = Field(None, description="New value for the field")
    source: str = Field(default="MANUAL", description="Value source: MANUAL or AI")


class PySisFieldResponse(BaseModel):
    """Schema for field response."""

    id: UUID
    process_id: UUID
    internal_name: str
    pysis_field_name: str
    field_type: str
    ai_extraction_enabled: bool
    ai_extraction_prompt: Optional[str]
    current_value: Optional[str]
    ai_extracted_value: Optional[str]
    manual_value: Optional[str]
    value_source: str
    pysis_value: Optional[str]
    needs_push: bool
    confidence_score: Optional[float]
    last_pushed_at: Optional[datetime]
    last_pulled_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# === Sync Schemas ===

class PySisSyncRequest(BaseModel):
    """Schema for sync request."""

    field_ids: Optional[List[UUID]] = Field(None, description="Specific field IDs to sync (all if None)")


class PySisSyncResult(BaseModel):
    """Schema for sync result."""

    success: bool
    fields_synced: int
    errors: List[str] = Field(default_factory=list)
    synced_at: datetime


class PySisPullResult(BaseModel):
    """Schema for pull result."""

    success: bool
    fields_updated: int = 0
    fields_created: int = 0
    process_data: Optional[Dict[str, Any]] = Field(None, description="Raw data from PySis")
    errors: List[str] = Field(default_factory=list)


# === AI Generation Schemas ===

class PySisGenerateRequest(BaseModel):
    """Schema for AI generation request."""

    field_ids: Optional[List[UUID]] = Field(None, description="Specific field IDs to generate (all if None)")


class PySisGenerateResult(BaseModel):
    """Schema for AI generation result."""

    success: bool
    fields_generated: int
    errors: List[str] = Field(default_factory=list)


# === Apply Template Schema ===

class ApplyTemplateRequest(BaseModel):
    """Schema for applying a template to a process."""

    template_id: UUID = Field(..., description="Template ID to apply")
    overwrite_existing: bool = Field(default=False, description="Overwrite existing fields with same pysis_field_name")


# === Test Connection Schema ===

class PySisTestConnectionResult(BaseModel):
    """Schema for connection test result."""

    connected: bool
    token_obtained: bool = False
    api_base_url: str
    process_data: Optional[Dict[str, Any]] = None
    process_fields: Optional[List[str]] = None
    error: Optional[str] = None


# === Field History Schemas ===

class PySisFieldHistoryResponse(BaseModel):
    """Schema for field history entry."""

    id: UUID
    field_id: UUID
    value: Optional[str]
    source: str
    confidence_score: Optional[float]
    action: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PySisFieldHistoryListResponse(BaseModel):
    """Schema for field history list."""

    items: List[PySisFieldHistoryResponse]
    total: int


# === Accept/Reject AI Suggestion Schemas ===

class AcceptAISuggestionRequest(BaseModel):
    """Schema for accepting an AI suggestion."""

    push_to_pysis: bool = Field(default=False, description="Also push to PySis after accepting")


class AcceptAISuggestionResult(BaseModel):
    """Schema for accept result."""

    success: bool
    field_id: UUID
    accepted_value: Optional[str]
    message: str


# === Analyze for Facets Schemas ===

class PySisAnalyzeForFacetsRequest(BaseModel):
    """Schema for facet analysis from PySis fields."""

    include_empty_fields: bool = Field(
        default=False,
        description="Include empty fields in analysis",
    )
    min_field_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for fields to include",
    )


class PySisAnalyzeForFacetsResult(BaseModel):
    """Schema for facet analysis result."""

    success: bool
    task_id: UUID = Field(..., description="AI Task ID for progress tracking")
    message: str
    fields_analyzed: int = Field(default=0, description="Number of fields analyzed")


# Update forward references
PySisProcessDetailResponse.model_rebuild()
