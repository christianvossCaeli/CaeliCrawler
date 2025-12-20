"""Admin API endpoints for external API management.

Provides CRUD operations for ExternalAPIConfig and sync management.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.core.deps import require_admin
from app.models import User
from app.schemas.external_api import (
    ExternalAPIConfigCreate,
    ExternalAPIConfigDetail,
    ExternalAPIConfigListResponse,
    ExternalAPIConfigResponse,
    ExternalAPIConfigUpdate,
    SyncRecordDetail,
    SyncRecordListResponse,
    SyncRecordResponse,
    SyncStatsResponse,
    TestConnectionResponse,
    TriggerSyncRequest,
    TriggerSyncResponse,
)
from external_apis.models.external_api_config import ExternalAPIConfig
from external_apis.models.sync_record import RecordStatus, SyncRecord

router = APIRouter(tags=["External APIs"])


# ============================================================================
# ExternalAPIConfig CRUD
# ============================================================================


@router.get("", response_model=ExternalAPIConfigListResponse)
async def list_external_api_configs(
    is_active: Optional[bool] = Query(None),
    api_type: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """List all external API configurations."""
    query = select(ExternalAPIConfig)

    if is_active is not None:
        query = query.where(ExternalAPIConfig.is_active == is_active)
    if api_type:
        query = query.where(ExternalAPIConfig.api_type == api_type)

    query = query.order_by(ExternalAPIConfig.name)

    result = await session.execute(query)
    configs = result.scalars().all()

    return ExternalAPIConfigListResponse(
        items=[ExternalAPIConfigResponse.model_validate(c) for c in configs],
        total=len(configs),
    )


@router.post("", response_model=ExternalAPIConfigResponse, status_code=201)
async def create_external_api_config(
    data: ExternalAPIConfigCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """Create a new external API configuration."""
    import uuid

    config = ExternalAPIConfig(
        id=uuid.uuid4(),
        name=data.name,
        description=data.description,
        api_type=data.api_type,
        api_base_url=data.api_base_url,
        api_endpoint=data.api_endpoint,
        auth_type=data.auth_type,
        auth_config=data.auth_config,
        sync_interval_hours=data.sync_interval_hours,
        sync_enabled=data.sync_enabled,
        entity_type_slug=data.entity_type_slug,
        id_field=data.id_field,
        name_field=data.name_field,
        field_mappings=data.field_mappings,
        location_fields=data.location_fields,
        request_config=data.request_config,
        mark_missing_inactive=data.mark_missing_inactive,
        inactive_after_days=data.inactive_after_days,
        ai_linking_enabled=data.ai_linking_enabled,
        link_to_entity_types=data.link_to_entity_types,
        data_source_id=data.data_source_id,
    )

    session.add(config)
    await session.commit()
    await session.refresh(config)

    return ExternalAPIConfigResponse.model_validate(config)


@router.get("/{config_id}", response_model=ExternalAPIConfigDetail)
async def get_external_api_config(
    config_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """Get a single external API configuration with statistics."""
    config = await session.get(ExternalAPIConfig, config_id)
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
    ).where(SyncRecord.external_api_config_id == config_id)

    stats_result = await session.execute(stats_query)
    stats = stats_result.one()

    # Count entities
    from app.models import Entity

    entity_count_result = await session.execute(
        select(func.count(Entity.id)).where(
            Entity.external_source_id == config_id
        )
    )
    total_entities = entity_count_result.scalar() or 0

    response = ExternalAPIConfigDetail.model_validate(config)
    response.total_sync_records = stats.total or 0
    response.active_records = stats.active or 0
    response.missing_records = stats.missing or 0
    response.archived_records = stats.archived or 0
    response.total_entities = total_entities

    return response


@router.patch("/{config_id}", response_model=ExternalAPIConfigResponse)
async def update_external_api_config(
    config_id: UUID,
    data: ExternalAPIConfigUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """Update an external API configuration."""
    config = await session.get(ExternalAPIConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    await session.commit()
    await session.refresh(config)

    return ExternalAPIConfigResponse.model_validate(config)


@router.delete("/{config_id}", status_code=204)
async def delete_external_api_config(
    config_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """Delete an external API configuration.

    Note: This will also delete all associated sync records.
    Entities created by this config will NOT be deleted but will
    have their external_source_id set to NULL.
    """
    config = await session.get(ExternalAPIConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    await session.delete(config)
    await session.commit()


# ============================================================================
# Sync Operations
# ============================================================================


@router.post("/{config_id}/sync", response_model=TriggerSyncResponse)
async def trigger_sync(
    config_id: UUID,
    request: Optional[TriggerSyncRequest] = None,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """Trigger a manual sync for an external API."""
    config = await session.get(ExternalAPIConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    if not config.is_active:
        raise HTTPException(status_code=400, detail="Configuration is inactive")

    from workers.external_api_tasks import sync_external_api

    task = sync_external_api.delay(str(config_id))

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
    config = await session.get(ExternalAPIConfig, config_id)
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
    """Get synchronization statistics for an external API."""
    config = await session.get(ExternalAPIConfig, config_id)
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
    ).where(SyncRecord.external_api_config_id == config_id)

    stats_result = await session.execute(stats_query)
    stats = stats_result.one()

    # Count entities
    from app.models import Entity

    entity_count_result = await session.execute(
        select(func.count(Entity.id)).where(
            Entity.external_source_id == config_id
        )
    )
    total_entities = entity_count_result.scalar() or 0

    return SyncStatsResponse(
        config_id=str(config_id),
        config_name=config.name,
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
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """List sync records for an external API configuration."""
    # Verify config exists
    config = await session.get(ExternalAPIConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # Build query
    query = select(SyncRecord).where(
        SyncRecord.external_api_config_id == config_id
    )

    if status:
        query = query.where(SyncRecord.sync_status == status)

    # Get total count
    count_result = await session.execute(
        select(func.count(SyncRecord.id)).where(
            SyncRecord.external_api_config_id == config_id,
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

    if not record or record.external_api_config_id != config_id:
        raise HTTPException(status_code=404, detail="Sync record not found")

    return SyncRecordDetail.model_validate(record)


@router.delete("/{config_id}/records/{record_id}", status_code=204)
async def delete_sync_record(
    config_id: UUID,
    record_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """Delete a single sync record.

    Note: This does NOT delete the associated entity.
    """
    record = await session.get(SyncRecord, record_id)

    if not record or record.external_api_config_id != config_id:
        raise HTTPException(status_code=404, detail="Sync record not found")

    await session.delete(record)
    await session.commit()


# ============================================================================
# Utility Endpoints
# ============================================================================


@router.get("/types/available", response_model=List[str])
async def list_available_api_types(
    _: User = Depends(require_admin),
):
    """List available API client types.

    Returns the api_type values that have registered client implementations.
    """
    from external_apis.sync_service import ExternalAPISyncService

    return list(ExternalAPISyncService.CLIENT_REGISTRY.keys())
