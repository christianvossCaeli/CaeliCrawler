"""Admin API endpoints for API-to-Facet synchronization.

These endpoints allow managing scheduled API syncs that automatically
update FacetValueHistory from external APIs.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_editor
from app.database import get_session
from app.models import User
from app.models.api_configuration import APIConfiguration, ImportMode
from app.schemas.common import MessageResponse

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class FacetMappingItem(BaseModel):
    """Single facet mapping configuration."""
    facet_type_slug: str
    is_history: bool = True
    track_key: str = "default"


class EntityMatchingConfig(BaseModel):
    """Entity matching configuration."""
    match_by: str = Field(default="name", pattern="^(name|external_id|name_contains)$")
    api_field: str
    entity_type_slug: str | None = None


class APIFacetSyncResponse(BaseModel):
    """API facet sync configuration response."""
    id: UUID
    data_source_id: UUID
    data_source_name: str | None = None
    api_type: str
    endpoint: str
    full_url: str
    auth_type: str
    entity_matching: dict[str, Any]
    facet_mappings: dict[str, Any]
    sync_enabled: bool
    sync_interval_hours: int
    next_run_at: datetime | None
    last_sync_at: datetime | None
    last_sync_status: str | None
    last_sync_stats: dict[str, Any] | None
    is_active: bool
    import_mode: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SyncTriggerResponse(BaseModel):
    """Response after triggering a sync."""
    message: str
    task_id: str
    config_id: UUID
    config_name: str


class SyncStatsResponse(BaseModel):
    """Sync statistics response."""
    total_configs: int
    configs_with_schedule: int
    last_24h_syncs: int
    last_24h_history_points: int


# =============================================================================
# Helper Functions
# =============================================================================


def _config_to_response(config: APIConfiguration) -> APIFacetSyncResponse:
    """Convert APIConfiguration to response model."""
    return APIFacetSyncResponse(
        id=config.id,
        data_source_id=config.data_source_id,
        data_source_name=config.data_source.name if config.data_source else None,
        api_type=config.api_type,
        endpoint=config.endpoint,
        full_url=config.get_full_url(),
        auth_type=config.auth_type,
        entity_matching=config.entity_matching or {},
        facet_mappings=config.facet_mappings or {},
        sync_enabled=config.sync_enabled,
        sync_interval_hours=config.sync_interval_hours,
        next_run_at=config.next_run_at,
        last_sync_at=config.last_sync_at,
        last_sync_status=config.last_sync_status,
        last_sync_stats=config.last_sync_stats,
        is_active=config.is_active,
        import_mode=config.import_mode,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=list[APIFacetSyncResponse])
async def list_api_facet_syncs(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
    sync_enabled: bool | None = None,
    is_active: bool | None = None,
):
    """
    List all API configurations with facet sync capability.

    Only returns APIConfigurations with import_mode FACETS or BOTH.
    """
    from sqlalchemy.orm import selectinload

    query = select(APIConfiguration).options(
        selectinload(APIConfiguration.data_source)
    ).where(
        APIConfiguration.import_mode.in_([
            ImportMode.FACETS.value,
            ImportMode.BOTH.value,
        ]),
        APIConfiguration.facet_mappings != {},
    )

    if sync_enabled is not None:
        query = query.where(APIConfiguration.sync_enabled == sync_enabled)

    if is_active is not None:
        query = query.where(APIConfiguration.is_active == is_active)

    query = query.order_by(APIConfiguration.created_at.desc())

    result = await session.execute(query)
    configs = result.scalars().all()

    return [_config_to_response(c) for c in configs]


@router.get("/stats", response_model=SyncStatsResponse)
async def get_sync_stats(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
):
    """Get statistics about API facet syncs."""
    # Base filter for facet-enabled configs
    base_filter = [
        APIConfiguration.import_mode.in_([
            ImportMode.FACETS.value,
            ImportMode.BOTH.value,
        ]),
        APIConfiguration.facet_mappings != {},
    ]

    # Count total configs
    total_result = await session.execute(
        select(func.count(APIConfiguration.id)).where(*base_filter)
    )
    total_configs = total_result.scalar_one()

    # Count configs with schedule enabled
    scheduled_result = await session.execute(
        select(func.count(APIConfiguration.id)).where(
            *base_filter,
            APIConfiguration.sync_enabled.is_(True),
        )
    )
    configs_with_schedule = scheduled_result.scalar_one()

    # Count syncs in last 24 hours
    yesterday = datetime.now(UTC) - timedelta(days=1)
    recent_result = await session.execute(
        select(func.count(APIConfiguration.id)).where(
            *base_filter,
            APIConfiguration.last_sync_at >= yesterday,
        )
    )
    last_24h_syncs = recent_result.scalar_one()

    # Sum history points from last 24h syncs
    stats_result = await session.execute(
        select(APIConfiguration.last_sync_stats).where(
            *base_filter,
            APIConfiguration.last_sync_at >= yesterday,
            APIConfiguration.last_sync_stats.isnot(None),
        )
    )
    stats_list = stats_result.scalars().all()
    last_24h_history_points = sum(
        (s.get("history_points_added", 0) if s else 0) for s in stats_list
    )

    return SyncStatsResponse(
        total_configs=total_configs,
        configs_with_schedule=configs_with_schedule,
        last_24h_syncs=last_24h_syncs,
        last_24h_history_points=last_24h_history_points,
    )


@router.get("/{config_id}", response_model=APIFacetSyncResponse)
async def get_api_facet_sync(
    config_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
):
    """Get a specific API facet sync configuration."""
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(APIConfiguration).options(
            selectinload(APIConfiguration.data_source)
        ).where(APIConfiguration.id == config_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    if config.import_mode not in [ImportMode.FACETS.value, ImportMode.BOTH.value]:
        raise HTTPException(
            status_code=400,
            detail="Configuration is not configured for facet sync"
        )

    if not config.facet_mappings:
        raise HTTPException(
            status_code=400,
            detail="Configuration has no facet_mappings"
        )

    return _config_to_response(config)


@router.post("/{config_id}/sync-now", response_model=SyncTriggerResponse)
async def trigger_sync_now(
    config_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
):
    """Manually trigger a facet sync for an API configuration."""
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(APIConfiguration).options(
            selectinload(APIConfiguration.data_source)
        ).where(APIConfiguration.id == config_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    if config.import_mode not in [ImportMode.FACETS.value, ImportMode.BOTH.value]:
        raise HTTPException(
            status_code=400,
            detail="Configuration is not configured for facet sync"
        )

    if not config.facet_mappings:
        raise HTTPException(
            status_code=400,
            detail="Configuration has no facet_mappings configured",
        )

    if not config.is_active:
        raise HTTPException(
            status_code=400,
            detail="Configuration is not active",
        )

    from workers.api_facet_sync_tasks import sync_api_config_now

    task = sync_api_config_now.delay(str(config.id))

    config_name = config.data_source.name if config.data_source else f"Config {str(config.id)[:8]}"

    return SyncTriggerResponse(
        message=f"Sync für '{config_name}' gestartet",
        task_id=task.id,
        config_id=config.id,
        config_name=config_name,
    )


@router.put("/{config_id}/schedule", response_model=APIFacetSyncResponse)
async def update_schedule(
    config_id: UUID,
    sync_enabled: bool,
    sync_interval_hours: int | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
):
    """Update the sync schedule for an API configuration."""
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(APIConfiguration).options(
            selectinload(APIConfiguration.data_source)
        ).where(APIConfiguration.id == config_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    config.sync_enabled = sync_enabled

    if sync_interval_hours is not None:
        if sync_interval_hours < 1 or sync_interval_hours > 8760:
            raise HTTPException(
                status_code=400,
                detail="sync_interval_hours must be between 1 and 8760 (1 year)"
            )
        config.sync_interval_hours = sync_interval_hours

    if sync_enabled:
        # Calculate next run
        config.next_run_at = datetime.now(UTC) + timedelta(
            hours=config.sync_interval_hours
        )
    else:
        config.next_run_at = None

    await session.commit()
    await session.refresh(config)

    return _config_to_response(config)


@router.delete("/{config_id}", response_model=MessageResponse)
async def delete_api_facet_sync(
    config_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
):
    """Delete an API configuration (and its facet sync settings)."""
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(APIConfiguration).options(
            selectinload(APIConfiguration.data_source)
        ).where(APIConfiguration.id == config_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    config_name = config.data_source.name if config.data_source else f"Config {str(config.id)[:8]}"

    await session.delete(config)
    await session.commit()

    return MessageResponse(message=f"Configuration '{config_name}' gelöscht")
