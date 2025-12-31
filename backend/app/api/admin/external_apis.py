"""Admin API endpoints for API Configuration management.

Provides CRUD operations for APIConfiguration and sync management.
This module handles the unified API configuration that combines
entity imports and facet syncing functionality.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import AuditContext
from app.core.deps import require_admin
from app.core.rate_limit import check_rate_limit
from app.database import get_session
from app.models import User
from app.models.api_configuration import APIConfiguration, ImportMode
from app.models.audit_log import AuditAction
from app.schemas.api_configuration import (
    APIConfigurationCreate,
    APIConfigurationDetail,
    APIConfigurationListResponse,
    APIConfigurationResponse,
    APIConfigurationUpdate,
    SyncRecordDetail,
    SyncRecordListResponse,
    SyncRecordResponse,
    SyncStatsResponse,
    TestConnectionResponse,
    TriggerSyncRequest,
    TriggerSyncResponse,
)
from app.schemas.common import MessageResponse
from external_apis.models.sync_record import RecordStatus, SyncRecord

router = APIRouter(tags=["API Configuration"])


# ============================================================================
# APIConfiguration CRUD
# ============================================================================


@router.get("", response_model=APIConfigurationListResponse)
async def list_api_configurations(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    is_active: bool | None = Query(None),
    api_type: str | None = Query(None),
    import_mode: str | None = Query(None),
    data_source_id: UUID | None = Query(None),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """List all API configurations with pagination."""
    base_query = select(APIConfiguration)

    # Apply filters
    if is_active is not None:
        base_query = base_query.where(APIConfiguration.is_active == is_active)
    if api_type:
        base_query = base_query.where(APIConfiguration.api_type == api_type)
    if import_mode:
        base_query = base_query.where(APIConfiguration.import_mode == import_mode)
    if data_source_id:
        base_query = base_query.where(APIConfiguration.data_source_id == data_source_id)

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    # Apply pagination and ordering
    query = (
        base_query
        .options(selectinload(APIConfiguration.data_source))
        .order_by(APIConfiguration.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await session.execute(query)
    configs = result.scalars().all()

    items = []
    for config in configs:
        response = APIConfigurationResponse.model_validate(config)
        if config.data_source:
            response.data_source_name = config.data_source.name
            response.full_url = config.get_full_url()
        items.append(response)

    return APIConfigurationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.post("", response_model=APIConfigurationResponse, status_code=201)
async def create_api_configuration(
    data: APIConfigurationCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Create a new API configuration."""
    import uuid

    # Verify data source exists
    from app.models import DataSource
    data_source = await session.get(DataSource, data.data_source_id)
    if not data_source:
        raise HTTPException(status_code=404, detail="DataSource not found")

    # Check if data source already has an API config
    existing_query = select(APIConfiguration).where(
        APIConfiguration.data_source_id == data.data_source_id
    )
    existing_result = await session.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="DataSource already has an API configuration"
        )

    config = APIConfiguration(
        id=uuid.uuid4(),
        data_source_id=data.data_source_id,
        api_type=data.api_type,
        endpoint=data.endpoint,
        auth_type=data.auth_type,
        auth_config=data.auth_config,
        request_config=data.request_config,
        import_mode=data.import_mode,
        entity_type_slug=data.entity_type_slug,
        id_field=data.id_field,
        name_field=data.name_field,
        field_mappings=data.field_mappings,
        location_fields=data.location_fields,
        facet_mappings=data.facet_mappings,
        entity_matching=data.entity_matching,
        sync_enabled=data.sync_enabled,
        sync_interval_hours=data.sync_interval_hours,
        mark_missing_inactive=data.mark_missing_inactive,
        inactive_after_days=data.inactive_after_days,
        ai_linking_enabled=data.ai_linking_enabled,
        link_to_entity_types=data.link_to_entity_types,
        keywords=data.keywords,
        confidence=data.confidence,
        is_template=data.is_template,
        documentation_url=data.documentation_url,
    )

    async with AuditContext(session, current_user, request) as audit:
        session.add(config)
        await session.flush()

        audit.track_action(
            action=AuditAction.CREATE,
            entity_type="APIConfiguration",
            entity_id=config.id,
            entity_name=f"API Config for {data_source.name}",
            changes={
                "data_source_id": str(config.data_source_id),
                "api_type": config.api_type,
                "import_mode": config.import_mode,
                "entity_type_slug": config.entity_type_slug,
                "sync_enabled": config.sync_enabled,
            },
        )

        await session.commit()
        await session.refresh(config)

    response = APIConfigurationResponse.model_validate(config)
    response.data_source_name = data_source.name
    response.full_url = config.get_full_url()
    return response


@router.get("/{config_id}", response_model=APIConfigurationDetail)
async def get_api_configuration(
    config_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """Get a single API configuration with statistics."""
    config = await session.get(APIConfiguration, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # Get sync record statistics
    stats_query = select(
        func.count(SyncRecord.id).label("total"),
        func.sum(
            func.cast(
                SyncRecord.sync_status == RecordStatus.ACTIVE.value, Integer
            )
        ).label("active"),
        func.sum(
            func.cast(
                SyncRecord.sync_status == RecordStatus.MISSING.value, Integer
            )
        ).label("missing"),
        func.sum(
            func.cast(
                SyncRecord.sync_status == RecordStatus.ARCHIVED.value, Integer
            )
        ).label("archived"),
    ).where(SyncRecord.api_configuration_id == config_id)

    stats_result = await session.execute(stats_query)
    stats = stats_result.one()

    # Count entities managed by this config
    from app.models import Entity

    entity_count_result = await session.execute(
        select(func.count(Entity.id)).where(
            Entity.api_configuration_id == config_id
        )
    )
    total_entities = entity_count_result.scalar() or 0

    # Get data source info
    from app.models import DataSource
    data_source = await session.get(DataSource, config.data_source_id)

    response = APIConfigurationDetail.model_validate(config)
    response.total_sync_records = stats.total or 0
    response.active_records = stats.active or 0
    response.missing_records = stats.missing or 0
    response.archived_records = stats.archived or 0
    response.total_entities = total_entities
    response.data_source_name = data_source.name if data_source else None
    response.data_source_base_url = data_source.base_url if data_source else None

    return response


@router.patch("/{config_id}", response_model=APIConfigurationResponse)
async def update_api_configuration(
    config_id: UUID,
    data: APIConfigurationUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Update an API configuration."""
    # Load config with data_source relationship
    result = await session.execute(
        select(APIConfiguration)
        .options(selectinload(APIConfiguration.data_source))
        .where(APIConfiguration.id == config_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # Capture old state for audit
    old_data = {
        "api_type": config.api_type,
        "import_mode": config.import_mode,
        "sync_enabled": config.sync_enabled,
        "is_active": config.is_active,
    }

    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)

    async with AuditContext(session, current_user, request) as audit:
        for field, value in update_data.items():
            setattr(config, field, value)

        new_data = {
            "api_type": config.api_type,
            "import_mode": config.import_mode,
            "sync_enabled": config.sync_enabled,
            "is_active": config.is_active,
        }

        audit.track_update(config, old_data, new_data)

        await session.commit()
        await session.refresh(config)

    response = APIConfigurationResponse.model_validate(config)
    if config.data_source:
        response.data_source_name = config.data_source.name
        response.full_url = config.get_full_url()
    return response


@router.delete("/{config_id}", response_model=MessageResponse)
async def delete_api_configuration(
    config_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Delete an API configuration.

    Note: This will also delete all associated sync records.
    Entities created by this config will NOT be deleted but will
    have their api_configuration_id set to NULL.
    """
    config = await session.get(APIConfiguration, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # Get data source name for audit
    from app.models import DataSource
    data_source = await session.get(DataSource, config.data_source_id)
    name = f"API Config for {data_source.name}" if data_source else str(config_id)

    async with AuditContext(session, current_user, request) as audit:
        audit.track_action(
            action=AuditAction.DELETE,
            entity_type="APIConfiguration",
            entity_id=config_id,
            entity_name=name,
            changes={
                "deleted": True,
                "api_type": config.api_type,
                "import_mode": config.import_mode,
                "data_source_id": str(config.data_source_id),
            },
        )

        await session.delete(config)
        await session.commit()

    return MessageResponse(message="API configuration deleted successfully")


# ============================================================================
# Sync Operations
# ============================================================================


@router.post("/{config_id}/sync", response_model=TriggerSyncResponse)
async def trigger_sync(
    config_id: UUID,
    http_request: Request,
    sync_request: TriggerSyncRequest | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Trigger a manual sync for an API configuration."""
    # Rate limit: 10 syncs per minute
    await check_rate_limit(http_request, "api_sync", identifier=str(current_user.id))

    config = await session.get(APIConfiguration, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    if not config.is_active:
        raise HTTPException(status_code=400, detail="Configuration is inactive")

    # Determine which sync task to use based on import_mode
    if config.import_mode in [ImportMode.ENTITIES.value, ImportMode.BOTH.value]:
        from workers.external_api_tasks import sync_external_api
        task = sync_external_api.delay(str(config_id))
    else:
        from workers.api_facet_sync_tasks import sync_api_config_to_facets
        task = sync_api_config_to_facets.delay(str(config_id))

    async with AuditContext(session, current_user, http_request) as audit:
        audit.track_action(
            action=AuditAction.IMPORT,
            entity_type="APIConfiguration",
            entity_id=config_id,
            entity_name=f"Sync {config.api_type}",
            changes={
                "action": "trigger_sync",
                "import_mode": config.import_mode,
                "api_type": config.api_type,
                "task_id": task.id,
            },
        )
        await session.commit()

    return TriggerSyncResponse(
        message="Sync triggered successfully",
        config_id=str(config_id),
        task_id=task.id,
    )


@router.post("/{config_id}/test", response_model=TestConnectionResponse)
async def test_connection(
    config_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """Test connection to an external API."""
    config = await session.get(APIConfiguration, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    from workers.external_api_tasks import test_external_api

    # Run synchronously for immediate feedback
    result = test_external_api.apply(args=[str(config_id)]).get(timeout=60)

    return TestConnectionResponse(**result)


@router.get("/{config_id}/stats", response_model=SyncStatsResponse)
async def get_sync_stats(
    config_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """Get synchronization statistics for an API configuration."""
    config = await session.get(APIConfiguration, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # Count sync records by status
    stats_query = select(
        func.count(SyncRecord.id).label("total"),
        func.sum(
            func.cast(
                SyncRecord.sync_status == RecordStatus.ACTIVE.value, Integer
            )
        ).label("active"),
        func.sum(
            func.cast(
                SyncRecord.sync_status == RecordStatus.MISSING.value, Integer
            )
        ).label("missing"),
        func.sum(
            func.cast(
                SyncRecord.sync_status == RecordStatus.ARCHIVED.value, Integer
            )
        ).label("archived"),
        func.sum(
            func.cast(
                func.array_length(SyncRecord.linked_entity_ids, 1) > 0, Integer
            )
        ).label("linked"),
    ).where(SyncRecord.api_configuration_id == config_id)

    stats_result = await session.execute(stats_query)
    stats = stats_result.one()

    # Count entities
    from app.models import Entity

    entity_count_result = await session.execute(
        select(func.count(Entity.id)).where(
            Entity.api_configuration_id == config_id
        )
    )
    total_entities = entity_count_result.scalar() or 0

    return SyncStatsResponse(
        config_id=str(config_id),
        data_source_id=str(config.data_source_id),
        last_sync_at=config.last_sync_at,
        last_sync_status=config.last_sync_status,
        total_records=stats.total or 0,
        active_records=stats.active or 0,
        missing_records=stats.missing or 0,
        archived_records=stats.archived or 0,
        total_entities=total_entities,
        linked_entities=stats.linked or 0,
    )


# ============================================================================
# SyncRecord Operations
# ============================================================================


@router.get("/{config_id}/records", response_model=SyncRecordListResponse)
async def list_sync_records(
    config_id: UUID,
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """List sync records for an API configuration."""
    # Verify config exists
    config = await session.get(APIConfiguration, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # Build query
    query = select(SyncRecord).where(
        SyncRecord.api_configuration_id == config_id
    )

    if status:
        query = query.where(SyncRecord.sync_status == status)

    # Get total count
    count_result = await session.execute(
        select(func.count(SyncRecord.id)).where(
            SyncRecord.api_configuration_id == config_id,
            *([SyncRecord.sync_status == status] if status else []),
        )
    )
    total = count_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    query = query.order_by(SyncRecord.last_seen_at.desc())

    result = await session.execute(query)
    records = result.scalars().all()

    return SyncRecordListResponse(
        items=[SyncRecordResponse.model_validate(r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{config_id}/records/{record_id}", response_model=SyncRecordDetail)
async def get_sync_record(
    config_id: UUID,
    record_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """Get a single sync record with full details including raw data."""
    record = await session.get(SyncRecord, record_id)

    if not record or record.api_configuration_id != config_id:
        raise HTTPException(status_code=404, detail="Sync record not found")

    return SyncRecordDetail.model_validate(record)


@router.delete("/{config_id}/records/{record_id}", response_model=MessageResponse)
async def delete_sync_record(
    config_id: UUID,
    record_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Delete a single sync record.

    Note: This does NOT delete the associated entity.
    """
    record = await session.get(SyncRecord, record_id)

    if not record or record.api_configuration_id != config_id:
        raise HTTPException(status_code=404, detail="Sync record not found")

    external_id = record.external_id

    async with AuditContext(session, current_user, request) as audit:
        audit.track_action(
            action=AuditAction.DELETE,
            entity_type="SyncRecord",
            entity_id=record_id,
            entity_name=external_id,
            changes={
                "deleted": True,
                "external_id": external_id,
                "config_id": str(config_id),
                "sync_status": record.sync_status,
            },
        )

        await session.delete(record)
        await session.commit()

    return MessageResponse(message=f"Sync record '{external_id}' deleted successfully")


# ============================================================================
# Utility Endpoints
# ============================================================================


@router.get("/types/available", response_model=list[str])
async def list_available_api_types(
    _: User = Depends(require_admin),
):
    """List available API client types.

    Returns the api_type values that have registered client implementations.
    """
    from external_apis.sync_service import ExternalAPISyncService

    return list(ExternalAPISyncService.CLIENT_REGISTRY.keys())


@router.get("/import-modes/available", response_model=list[str])
async def list_import_modes(
    _: User = Depends(require_admin),
):
    """List available import modes."""
    return [mode.value for mode in ImportMode]


# ============================================================================
# Discovery Integration
# ============================================================================


class SaveFromDiscoveryRequest(BaseModel):
    """Request to save a discovered API as a configuration."""
    name: str
    description: str | None = None
    api_type: str = "rest"
    base_url: str
    endpoint: str
    documentation_url: str | None = None
    auth_required: bool = False
    field_mapping: dict = Field(default_factory=dict)
    keywords: list[str] = Field(default_factory=list)
    default_tags: list[str] = Field(default_factory=list)
    confidence: float = 0.8
    validation_item_count: int | None = None


@router.post("/save-from-discovery", response_model=APIConfigurationResponse, status_code=201)
async def save_api_from_discovery(
    request: SaveFromDiscoveryRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_admin),
):
    """
    Save a discovered API as a new APIConfiguration.

    This endpoint is used by the AI Discovery feature to save APIs
    that were discovered and validated. It creates both a DataSource
    and an APIConfiguration with is_template=True for reuse.
    """
    from app.models.data_source import DataSource, SourceType

    # Check for duplicate name
    existing = await session.execute(
        select(DataSource).where(DataSource.name == request.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Eine Datenquelle mit dem Namen '{request.name}' existiert bereits"
        )

    # Create DataSource
    data_source = DataSource(
        name=request.name,
        description=request.description or "Via AI-Discovery erstellt",
        base_url=request.base_url,
        source_type=SourceType.REST_API,
        is_active=True,
    )
    session.add(data_source)
    await session.flush()

    # Create APIConfiguration
    api_config = APIConfiguration(
        data_source_id=data_source.id,
        api_type=request.api_type.lower(),
        endpoint=request.endpoint,
        auth_type="none" if not request.auth_required else "api_key",
        auth_config={},
        request_config={},
        import_mode=ImportMode.ENTITIES.value,
        field_mappings=request.field_mapping,
        keywords=request.keywords,
        documentation_url=request.documentation_url,
        is_template=True,
        is_active=True,
        confidence=request.confidence,
        sync_enabled=False,
    )
    session.add(api_config)
    await session.commit()
    await session.refresh(api_config)
    await session.refresh(data_source)

    return APIConfigurationResponse(
        id=api_config.id,
        data_source_id=data_source.id,
        data_source_name=data_source.name,
        api_type=api_config.api_type,
        endpoint=api_config.endpoint,
        full_url=api_config.get_full_url(),
        import_mode=api_config.import_mode,
        sync_enabled=api_config.sync_enabled,
        sync_interval_hours=api_config.sync_interval_hours,
        is_active=api_config.is_active,
        is_template=api_config.is_template,
        created_at=api_config.created_at,
        updated_at=api_config.updated_at,
    )
