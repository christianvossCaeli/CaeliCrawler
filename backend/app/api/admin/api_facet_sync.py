"""Admin API endpoints for API-to-Facet synchronization.

These endpoints allow managing scheduled API syncs that automatically
update FacetValueHistory from external APIs.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.core.deps import require_editor
from app.models import User
from app.models.api_template import APITemplate, TemplateStatus
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
    entity_type_slug: Optional[str] = None


class APIFacetSyncCreate(BaseModel):
    """Create API facet sync configuration."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    api_url: str = Field(..., min_length=1)
    auth_required: bool = False
    auth_config: Optional[Dict[str, Any]] = None
    entity_matching: EntityMatchingConfig
    facet_mapping: Dict[str, FacetMappingItem]
    schedule_cron: Optional[str] = None
    schedule_enabled: bool = False
    keywords: List[str] = Field(default_factory=list)


class APIFacetSyncUpdate(BaseModel):
    """Update API facet sync configuration."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    api_url: Optional[str] = None
    auth_required: Optional[bool] = None
    auth_config: Optional[Dict[str, Any]] = None
    entity_matching: Optional[EntityMatchingConfig] = None
    facet_mapping: Optional[Dict[str, FacetMappingItem]] = None
    schedule_cron: Optional[str] = None
    schedule_enabled: Optional[bool] = None
    keywords: Optional[List[str]] = None


class APIFacetSyncResponse(BaseModel):
    """API facet sync configuration response."""
    id: UUID
    name: str
    description: Optional[str]
    api_url: str
    auth_required: bool
    entity_matching: Dict[str, Any]
    facet_mapping: Dict[str, Any]
    schedule_enabled: bool
    schedule_cron: Optional[str]
    next_run_at: Optional[datetime]
    last_sync_at: Optional[datetime]
    last_sync_status: Optional[str]
    last_sync_stats: Optional[Dict[str, Any]]
    status: str
    usage_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SyncTriggerResponse(BaseModel):
    """Response after triggering a sync."""
    message: str
    task_id: str
    template_id: UUID
    template_name: str


class SyncStatsResponse(BaseModel):
    """Sync statistics response."""
    total_syncs: int
    syncs_with_schedule: int
    last_24h_syncs: int
    last_24h_history_points: int


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=List[APIFacetSyncResponse])
async def list_api_facet_syncs(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
    schedule_enabled: Optional[bool] = None,
    status_filter: Optional[str] = None,
):
    """
    List all API facet sync configurations.

    Only returns APITemplates that have facet_mapping configured.
    """
    query = select(APITemplate).where(APITemplate.facet_mapping != {})

    if schedule_enabled is not None:
        query = query.where(APITemplate.schedule_enabled == schedule_enabled)

    if status_filter:
        query = query.where(APITemplate.status == TemplateStatus(status_filter))

    query = query.order_by(APITemplate.created_at.desc())

    result = await session.execute(query)
    templates = result.scalars().all()

    return [
        APIFacetSyncResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            api_url=t.full_url,
            auth_required=t.auth_required,
            entity_matching=t.entity_matching or {},
            facet_mapping=t.facet_mapping or {},
            schedule_enabled=t.schedule_enabled,
            schedule_cron=t.schedule_cron,
            next_run_at=t.next_run_at,
            last_sync_at=t.last_sync_at,
            last_sync_status=t.last_sync_status,
            last_sync_stats=t.last_sync_stats,
            status=t.status.value,
            usage_count=t.usage_count,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in templates
    ]


@router.get("/stats", response_model=SyncStatsResponse)
async def get_sync_stats(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
):
    """Get statistics about API facet syncs."""
    from datetime import timedelta
    from sqlalchemy import func

    # Count total syncs
    total_result = await session.execute(
        select(func.count(APITemplate.id)).where(APITemplate.facet_mapping != {})
    )
    total_syncs = total_result.scalar_one()

    # Count syncs with schedule
    scheduled_result = await session.execute(
        select(func.count(APITemplate.id)).where(
            APITemplate.facet_mapping != {},
            APITemplate.schedule_enabled.is_(True),
        )
    )
    syncs_with_schedule = scheduled_result.scalar_one()

    # Count syncs in last 24 hours
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_result = await session.execute(
        select(func.count(APITemplate.id)).where(
            APITemplate.facet_mapping != {},
            APITemplate.last_sync_at >= yesterday,
        )
    )
    last_24h_syncs = recent_result.scalar_one()

    # Sum history points from last 24h syncs
    stats_result = await session.execute(
        select(APITemplate.last_sync_stats).where(
            APITemplate.facet_mapping != {},
            APITemplate.last_sync_at >= yesterday,
            APITemplate.last_sync_stats.isnot(None),
        )
    )
    stats_list = stats_result.scalars().all()
    last_24h_history_points = sum(
        (s.get("history_points_added", 0) if s else 0) for s in stats_list
    )

    return SyncStatsResponse(
        total_syncs=total_syncs,
        syncs_with_schedule=syncs_with_schedule,
        last_24h_syncs=last_24h_syncs,
        last_24h_history_points=last_24h_history_points,
    )


@router.get("/{sync_id}", response_model=APIFacetSyncResponse)
async def get_api_facet_sync(
    sync_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
):
    """Get a specific API facet sync configuration."""
    template = await session.get(APITemplate, sync_id)

    if not template:
        raise HTTPException(status_code=404, detail="Sync configuration not found")

    if not template.facet_mapping:
        raise HTTPException(status_code=404, detail="Template has no facet sync configuration")

    return APIFacetSyncResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        api_url=template.full_url,
        auth_required=template.auth_required,
        entity_matching=template.entity_matching or {},
        facet_mapping=template.facet_mapping or {},
        schedule_enabled=template.schedule_enabled,
        schedule_cron=template.schedule_cron,
        next_run_at=template.next_run_at,
        last_sync_at=template.last_sync_at,
        last_sync_status=template.last_sync_status,
        last_sync_stats=template.last_sync_stats,
        status=template.status.value,
        usage_count=template.usage_count,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.post("/{sync_id}/sync-now", response_model=SyncTriggerResponse)
async def trigger_sync_now(
    sync_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
):
    """Manually trigger a sync for an API template."""
    template = await session.get(APITemplate, sync_id)

    if not template:
        raise HTTPException(status_code=404, detail="Sync configuration not found")

    if not template.facet_mapping:
        raise HTTPException(
            status_code=400,
            detail="Template has no facet_mapping configured",
        )

    if template.status != TemplateStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail=f"Template not active (status: {template.status.value})",
        )

    from workers.api_facet_sync_tasks import sync_api_template_now

    task = sync_api_template_now.delay(str(template.id))

    return SyncTriggerResponse(
        message=f"Sync für '{template.name}' gestartet",
        task_id=task.id,
        template_id=template.id,
        template_name=template.name,
    )


@router.put("/{sync_id}/schedule", response_model=APIFacetSyncResponse)
async def update_schedule(
    sync_id: UUID,
    schedule_enabled: bool,
    schedule_cron: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
):
    """Update the schedule for an API facet sync."""
    template = await session.get(APITemplate, sync_id)

    if not template:
        raise HTTPException(status_code=404, detail="Sync configuration not found")

    if schedule_enabled and not schedule_cron and not template.schedule_cron:
        raise HTTPException(
            status_code=400,
            detail="schedule_cron required when enabling schedule",
        )

    # Validate cron expression
    if schedule_cron:
        from app.utils.cron import croniter_for_expression, get_schedule_timezone

        try:
            schedule_tz = get_schedule_timezone()
            cron = croniter_for_expression(schedule_cron, datetime.now(schedule_tz))
            template.schedule_cron = schedule_cron
            template.next_run_at = cron.get_next(datetime)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid cron expression: {schedule_cron} - {str(e)}",
            )

    template.schedule_enabled = schedule_enabled

    if not schedule_enabled:
        template.next_run_at = None

    await session.commit()
    await session.refresh(template)

    return APIFacetSyncResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        api_url=template.full_url,
        auth_required=template.auth_required,
        entity_matching=template.entity_matching or {},
        facet_mapping=template.facet_mapping or {},
        schedule_enabled=template.schedule_enabled,
        schedule_cron=template.schedule_cron,
        next_run_at=template.next_run_at,
        last_sync_at=template.last_sync_at,
        last_sync_status=template.last_sync_status,
        last_sync_stats=template.last_sync_stats,
        status=template.status.value,
        usage_count=template.usage_count,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.delete("/{sync_id}", response_model=MessageResponse)
async def delete_api_facet_sync(
    sync_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_editor),
):
    """Delete an API facet sync configuration."""
    template = await session.get(APITemplate, sync_id)

    if not template:
        raise HTTPException(status_code=404, detail="Sync configuration not found")

    await session.delete(template)
    await session.commit()

    return MessageResponse(message=f"Sync '{template.name}' gelöscht")
