"""Pydantic schemas for unified API Configuration."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================================
# APIConfiguration Schemas
# ============================================================================


class APIConfigurationBase(BaseModel):
    """Base schema for APIConfiguration."""

    # Connection Configuration
    api_type: str = Field(
        default="rest",
        pattern="^(rest|graphql|sparql|oparl)$",
        description="API protocol type",
    )
    endpoint: str = Field(
        default="",
        max_length=1000,
        description="API endpoint path (appended to DataSource.base_url)",
    )
    auth_type: str = Field(
        default="none",
        pattern="^(none|basic|bearer|api_key|oauth2)$",
    )
    auth_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Authentication config (env var references, not secrets)",
    )
    request_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional request config (headers, params, pagination)",
    )

    # Import Mode
    import_mode: str = Field(
        default="entities",
        pattern="^(entities|facets|both)$",
        description="What to import: entities, facets, or both",
    )

    # Entity Configuration
    entity_type_slug: str | None = Field(
        None,
        max_length=100,
        description="Target EntityType slug (e.g., wind_project)",
    )
    id_field: str = Field(
        default="id",
        max_length=255,
        description="API field containing unique identifier",
    )
    name_field: str = Field(
        default="name",
        max_length=255,
        description="API field containing entity name",
    )
    field_mappings: dict[str, Any] = Field(
        default_factory=dict,
        description="Mapping from API fields to entity fields",
    )
    location_fields: list[str] = Field(
        default_factory=list,
        description="API fields containing location data",
    )

    # Facet Configuration
    facet_mappings: dict[str, Any] = Field(
        default_factory=dict,
        description="Mapping from API fields to FacetTypes",
    )
    entity_matching: dict[str, Any] = Field(
        default_factory=dict,
        description="How to match API records to entities",
    )

    # Sync Configuration
    sync_enabled: bool = True
    sync_interval_hours: int = Field(default=24, ge=1, le=8760)  # 1 hour to 1 year

    # Lifecycle Management
    mark_missing_inactive: bool = True
    inactive_after_days: int = Field(default=7, ge=1, le=365)

    # AI Features
    ai_linking_enabled: bool = True
    link_to_entity_types: list[str] = Field(default_factory=list)

    # KI-Discovery Features
    keywords: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    is_template: bool = False
    documentation_url: str | None = None


class APIConfigurationCreate(APIConfigurationBase):
    """Schema for creating an APIConfiguration."""

    data_source_id: UUID = Field(
        ...,
        description="Required link to DataSource",
    )


class APIConfigurationUpdate(BaseModel):
    """Schema for updating an APIConfiguration."""

    # Connection
    api_type: str | None = Field(None, pattern="^(rest|graphql|sparql|oparl)$")
    endpoint: str | None = Field(None, max_length=1000)
    auth_type: str | None = Field(None, pattern="^(none|basic|bearer|api_key|oauth2)$")
    auth_config: dict[str, Any] | None = None
    request_config: dict[str, Any] | None = None

    # Import Mode
    import_mode: str | None = Field(None, pattern="^(entities|facets|both)$")

    # Entity Configuration
    entity_type_slug: str | None = Field(None, max_length=100)
    id_field: str | None = Field(None, max_length=255)
    name_field: str | None = Field(None, max_length=255)
    field_mappings: dict[str, Any] | None = None
    location_fields: list[str] | None = None

    # Facet Configuration
    facet_mappings: dict[str, Any] | None = None
    entity_matching: dict[str, Any] | None = None

    # Sync Configuration
    sync_enabled: bool | None = None
    sync_interval_hours: int | None = Field(None, ge=1, le=8760)

    # Lifecycle Management
    mark_missing_inactive: bool | None = None
    inactive_after_days: int | None = Field(None, ge=1, le=365)

    # AI Features
    ai_linking_enabled: bool | None = None
    link_to_entity_types: list[str] | None = None

    # KI-Discovery Features
    keywords: list[str] | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    is_template: bool | None = None
    documentation_url: str | None = None

    # Status
    is_active: bool | None = None


class APIConfigurationResponse(APIConfigurationBase):
    """Schema for APIConfiguration response."""

    id: UUID
    data_source_id: UUID
    data_source_name: str | None = None  # From related DataSource
    full_url: str | None = None  # Computed from DataSource.base_url + endpoint
    last_sync_at: datetime | None = None
    last_sync_status: str | None = None
    last_sync_error: str | None = None
    last_sync_stats: dict[str, Any] | None = None
    next_run_at: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class APIConfigurationDetail(APIConfigurationResponse):
    """Detailed schema including sync statistics and data source info."""

    total_sync_records: int = 0
    active_records: int = 0
    missing_records: int = 0
    archived_records: int = 0
    total_entities: int = 0

    # Additional data source info (data_source_name inherited from parent)
    data_source_base_url: str | None = None


# ============================================================================
# SyncRecord Schemas (updated for new FK)
# ============================================================================


class SyncRecordBase(BaseModel):
    """Base schema for SyncRecord."""

    external_id: str
    sync_status: str
    first_seen_at: datetime
    last_seen_at: datetime
    missing_since: datetime | None = None


class SyncRecordResponse(SyncRecordBase):
    """Schema for SyncRecord response."""

    id: UUID
    api_configuration_id: UUID
    entity_id: UUID | None = None
    last_modified_at: datetime | None = None
    content_hash: str
    linked_entity_ids: list[UUID] = Field(default_factory=list)
    linking_metadata: dict[str, Any] | None = None
    last_error: str | None = None
    error_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SyncRecordDetail(SyncRecordResponse):
    """Detailed schema including raw data."""

    raw_data: dict[str, Any] = Field(default_factory=dict)


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
    task_id: str | None = None


class TestConnectionResponse(BaseModel):
    """Response schema for connection test."""

    success: bool
    records_fetched: int | None = None
    sample_record: dict[str, Any] | None = None
    error: str | None = None
    error_type: str | None = None


class SyncStatsResponse(BaseModel):
    """Response schema for sync statistics."""

    config_id: str
    data_source_id: str
    last_sync_at: datetime | None = None
    last_sync_status: str | None = None
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

    items: list[SyncRecordResponse]
    total: int
    page: int = 1
    page_size: int = 50


class APIConfigurationListResponse(BaseModel):
    """List of API configurations."""

    items: list[APIConfigurationResponse]
    total: int
    page: int = 1
    page_size: int = 50
    pages: int = 1
