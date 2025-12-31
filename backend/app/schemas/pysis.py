"""PySis integration schemas for API validation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# === Field Definition (used in templates) ===

class PySisFieldDefinition(BaseModel):
    """Definition of a single field within a template."""

    internal_name: str = Field(..., min_length=1, description="Display name, e.g., 'Ansprechpartner Gemeinde'")
    pysis_field_name: str = Field(..., min_length=1, description="PySis API field name")
    field_type: str = Field(default="text", description="Field type: text, number, date, boolean, list")
    ai_extraction_prompt: str | None = Field(None, description="Custom AI prompt for extracting this field")


# === Template Schemas ===

class PySisFieldTemplateCreate(BaseModel):
    """Schema for creating a new field template."""

    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: str | None = Field(None, description="Template description")
    fields: list[PySisFieldDefinition] = Field(default_factory=list, description="Field definitions")


class PySisFieldTemplateUpdate(BaseModel):
    """Schema for updating a template."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    fields: list[PySisFieldDefinition] | None = None
    is_active: bool | None = None


class PySisFieldTemplateResponse(BaseModel):
    """Schema for template response."""

    id: UUID
    name: str
    description: str | None
    fields: list[PySisFieldDefinition]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PySisFieldTemplateListResponse(BaseModel):
    """Schema for template list response."""

    items: list[PySisFieldTemplateResponse]
    total: int


# === Process Schemas ===

class PySisProcessCreate(BaseModel):
    """Schema for creating a new process link."""

    pysis_process_id: str = Field(..., min_length=1, description="External PySis process ID")
    name: str | None = Field(None, max_length=255, description="Optional display name")
    description: str | None = Field(None, description="Notes about this process")
    template_id: UUID | None = Field(None, description="Template to apply on creation")


class PySisProcessUpdate(BaseModel):
    """Schema for updating a process."""

    name: str | None = Field(None, max_length=255)
    description: str | None = None


class PySisProcessResponse(BaseModel):
    """Schema for process response."""

    id: UUID
    entity_name: str | None = None
    pysis_process_id: str
    name: str | None = None
    description: str | None = None
    template_id: UUID | None = None
    last_synced_at: datetime | None = None
    sync_status: str
    sync_error: str | None = None
    field_count: int = Field(default=0, description="Number of fields in this process")
    created_at: datetime
    updated_at: datetime
    extra: dict[str, Any] | None = Field(None, description="Additional response data")

    model_config = {"from_attributes": True}


class PySisProcessListResponse(BaseModel):
    """Schema for process list response."""

    items: list[PySisProcessResponse]
    total: int


class PySisProcessDetailResponse(PySisProcessResponse):
    """Schema for detailed process response with fields."""

    fields: list["PySisFieldResponse"] = Field(default_factory=list)


# === Field Schemas ===

class PySisFieldCreate(BaseModel):
    """Schema for creating a new field."""

    internal_name: str = Field(..., min_length=1, max_length=255, description="Display name")
    pysis_field_name: str = Field(..., min_length=1, max_length=255, description="PySis API field name")
    field_type: str = Field(default="text", description="Field type")
    ai_extraction_enabled: bool = Field(default=True, description="Enable AI extraction")
    ai_extraction_prompt: str | None = Field(None, description="Custom AI prompt")


class PySisFieldUpdate(BaseModel):
    """Schema for updating a field."""

    internal_name: str | None = Field(None, min_length=1, max_length=255)
    field_type: str | None = None
    ai_extraction_enabled: bool | None = None
    ai_extraction_prompt: str | None = None


class PySisFieldValueUpdate(BaseModel):
    """Schema for updating a field's value."""

    value: str | None = Field(None, description="New value for the field")
    source: str = Field(default="MANUAL", description="Value source: MANUAL or AI")


class PySisFieldResponse(BaseModel):
    """Schema for field response."""

    id: UUID
    process_id: UUID
    internal_name: str
    pysis_field_name: str
    field_type: str
    ai_extraction_enabled: bool
    ai_extraction_prompt: str | None
    current_value: str | None
    ai_extracted_value: str | None
    manual_value: str | None
    value_source: str
    pysis_value: str | None
    needs_push: bool
    confidence_score: float | None
    last_pushed_at: datetime | None
    last_pulled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# === Sync Schemas ===

class PySisSyncRequest(BaseModel):
    """Schema for sync request."""

    field_ids: list[UUID] | None = Field(None, description="Specific field IDs to sync (all if None)")


class PySisSyncResult(BaseModel):
    """Schema for sync result."""

    success: bool
    fields_synced: int
    errors: list[str] = Field(default_factory=list)
    synced_at: datetime


class PySisPullResult(BaseModel):
    """Schema for pull result."""

    success: bool
    fields_updated: int = 0
    fields_created: int = 0
    process_data: dict[str, Any] | None = Field(None, description="Raw data from PySis")
    errors: list[str] = Field(default_factory=list)


# === AI Generation Schemas ===

class PySisGenerateRequest(BaseModel):
    """Schema for AI generation request."""

    field_ids: list[UUID] | None = Field(None, description="Specific field IDs to generate (all if None)")


class PySisGenerateResult(BaseModel):
    """Schema for AI generation result."""

    success: bool
    fields_generated: int
    errors: list[str] = Field(default_factory=list)


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
    process_data: dict[str, Any] | None = None
    process_fields: list[str] | None = None
    error: str | None = None


# === Field History Schemas ===

class PySisFieldHistoryResponse(BaseModel):
    """Schema for field history entry."""

    id: UUID
    field_id: UUID
    value: str | None
    source: str
    confidence_score: float | None
    action: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PySisFieldHistoryListResponse(BaseModel):
    """Schema for field history list."""

    items: list[PySisFieldHistoryResponse]
    total: int


# === Accept/Reject AI Suggestion Schemas ===

class AcceptAISuggestionRequest(BaseModel):
    """Schema for accepting an AI suggestion."""

    push_to_pysis: bool = Field(default=False, description="Also push to PySis after accepting")


class AcceptAISuggestionResult(BaseModel):
    """Schema for accept result."""

    success: bool
    field_id: UUID
    accepted_value: str | None
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
