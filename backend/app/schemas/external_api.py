"""Pydantic schemas for External API integration."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# ExternalAPIConfig Schemas
# ============================================================================


class ExternalAPIConfigBase(BaseModel):
    """Base schema for ExternalAPIConfig."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    api_type: str = Field(..., min_length=1, max_length=100)
    api_base_url: str = Field(..., min_length=1, max_length=1000)
    api_endpoint: str = Field(..., min_length=1, max_length=1000)
    auth_type: str = Field(default="none", pattern="^(none|basic|bearer|api_key|oauth2)$")
    auth_config: Dict[str, Any] = Field(default_factory=dict)
    sync_interval_hours: int = Field(default=4, ge=1, le=168)  # 1 hour to 1 week
    sync_enabled: bool = True
    entity_type_slug: str = Field(..., min_length=1, max_length=100)
    id_field: str = Field(default="id", max_length=255)
    name_field: str = Field(default="name", max_length=255)
    field_mappings: Dict[str, str] = Field(default_factory=dict)
    location_fields: List[str] = Field(default_factory=list)
    request_config: Dict[str, Any] = Field(default_factory=dict)
    mark_missing_inactive: bool = True
    inactive_after_days: int = Field(default=7, ge=1, le=365)
    ai_linking_enabled: bool = True
    link_to_entity_types: List[str] = Field(default_factory=lambda: ["municipality"])


class ExternalAPIConfigCreate(ExternalAPIConfigBase):
    """Schema for creating an ExternalAPIConfig."""

    data_source_id: Optional[UUID] = None


class ExternalAPIConfigUpdate(BaseModel):
    """Schema for updating an ExternalAPIConfig."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    api_base_url: Optional[str] = Field(None, min_length=1, max_length=1000)
    api_endpoint: Optional[str] = Field(None, min_length=1, max_length=1000)
    auth_type: Optional[str] = Field(None, pattern="^(none|basic|bearer|api_key|oauth2)$")
    auth_config: Optional[Dict[str, Any]] = None
    sync_interval_hours: Optional[int] = Field(None, ge=1, le=168)
    sync_enabled: Optional[bool] = None
    entity_type_slug: Optional[str] = Field(None, min_length=1, max_length=100)
    id_field: Optional[str] = Field(None, max_length=255)
    name_field: Optional[str] = Field(None, max_length=255)
    field_mappings: Optional[Dict[str, str]] = None
    location_fields: Optional[List[str]] = None
    request_config: Optional[Dict[str, Any]] = None
    mark_missing_inactive: Optional[bool] = None
    inactive_after_days: Optional[int] = Field(None, ge=1, le=365)
    ai_linking_enabled: Optional[bool] = None
    link_to_entity_types: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ExternalAPIConfigResponse(ExternalAPIConfigBase):
    """Schema for ExternalAPIConfig response."""

    id: UUID
    data_source_id: Optional[UUID] = None
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    last_sync_error: Optional[str] = None
    last_sync_stats: Optional[Dict[str, Any]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExternalAPIConfigDetail(ExternalAPIConfigResponse):
    """Detailed schema including sync statistics."""

    total_sync_records: int = 0
    active_records: int = 0
    missing_records: int = 0
    archived_records: int = 0
    total_entities: int = 0


# ============================================================================
# SyncRecord Schemas
# ============================================================================


class SyncRecordBase(BaseModel):
    """Base schema for SyncRecord."""

    external_id: str
    sync_status: str
    first_seen_at: datetime
    last_seen_at: datetime
    missing_since: Optional[datetime] = None


class SyncRecordResponse(SyncRecordBase):
    """Schema for SyncRecord response."""

    id: UUID
    external_api_config_id: UUID
    entity_id: Optional[UUID] = None
    last_modified_at: Optional[datetime] = None
    content_hash: str
    linked_entity_ids: List[UUID] = Field(default_factory=list)
    linking_metadata: Optional[Dict[str, Any]] = None
    last_error: Optional[str] = None
    error_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SyncRecordDetail(SyncRecordResponse):
    """Detailed schema including raw data."""

    raw_data: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# API Operation Schemas
# ============================================================================


class TriggerSyncRequest(BaseModel):
    """Request schema for triggering a sync."""

    force: bool = Field(
        default=False,
        description="Force sync even if not due yet",
    )


class TriggerSyncResponse(BaseModel):
    """Response schema for sync trigger."""

    message: str
    config_id: str
    task_id: Optional[str] = None


class TestConnectionResponse(BaseModel):
    """Response schema for connection test."""

    success: bool
    records_fetched: Optional[int] = None
    sample_record: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None


class SyncStatsResponse(BaseModel):
    """Response schema for sync statistics."""

    config_id: str
    config_name: str
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    total_records: int = 0
    active_records: int = 0
    missing_records: int = 0
    archived_records: int = 0
    total_entities: int = 0
    linked_entities: int = 0


# ============================================================================
# Pagination and List Schemas
# ============================================================================


class SyncRecordListResponse(BaseModel):
    """Paginated list of sync records."""

    items: List[SyncRecordResponse]
    total: int
    page: int = 1
    page_size: int = 50


class ExternalAPIConfigListResponse(BaseModel):
    """List of external API configurations."""

    items: List[ExternalAPIConfigResponse]
    total: int
