"""API endpoints for Facet Value History (Time-Series Data)."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditContext
from app.core.deps import require_editor
from app.core.exceptions import ConflictError, NotFoundError
from app.database import get_session
from app.models.audit_log import AuditAction
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.facet_value_history import (
    AggregatedHistoryResponse,
    EntityHistoryResponse,
    HistoryBulkImport,
    HistoryBulkImportResponse,
    HistoryDataPointCreate,
    HistoryDataPointResponse,
    HistoryDataPointUpdate,
)
from services.facet_history_service import FacetHistoryService

router = APIRouter()


@router.get("/entity/{entity_id}/history/{facet_type_id}", response_model=EntityHistoryResponse)
async def get_entity_history(
    entity_id: UUID,
    facet_type_id: UUID,
    from_date: datetime | None = Query(default=None, description="Start date filter"),
    to_date: datetime | None = Query(default=None, description="End date filter"),
    tracks: list[str] | None = Query(default=None, description="Filter by track keys"),
    limit: int = Query(default=1000, ge=1, le=10000, description="Max points to return"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get history data for an entity+facet combination.

    Returns time-series data with statistics and trend information.
    Supports filtering by date range and track keys.
    """
    service = FacetHistoryService(session)

    try:
        return await service.get_history(
            entity_id=entity_id,
            facet_type_id=facet_type_id,
            from_date=from_date,
            to_date=to_date,
            track_keys=tracks,
            limit=limit,
        )
    except ValueError as e:
        raise NotFoundError("Entity or FacetType", str(e)) from None


@router.get("/entity/{entity_id}/history/{facet_type_id}/aggregated", response_model=AggregatedHistoryResponse)
async def get_entity_history_aggregated(
    entity_id: UUID,
    facet_type_id: UUID,
    interval: str = Query(default="month", pattern="^(day|week|month|quarter|year)$"),
    method: str = Query(default="avg", pattern="^(avg|sum|min|max)$"),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    tracks: list[str] | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """
    Get aggregated history data.

    Aggregates data points by time interval (day, week, month, quarter, year)
    using the specified method (avg, sum, min, max).
    """
    service = FacetHistoryService(session)

    try:
        return await service.aggregate_history(
            entity_id=entity_id,
            facet_type_id=facet_type_id,
            interval=interval,
            method=method,
            from_date=from_date,
            to_date=to_date,
            track_keys=tracks,
        )
    except ValueError as e:
        raise NotFoundError("Entity or FacetType", str(e)) from None


@router.post("/entity/{entity_id}/history/{facet_type_id}", response_model=HistoryDataPointResponse, status_code=201)
async def add_history_data_point(
    entity_id: UUID,
    facet_type_id: UUID,
    data: HistoryDataPointCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Add a single data point to the history.

    Requires Editor role.
    """
    service = FacetHistoryService(session)

    try:
        async with AuditContext(session, current_user, request) as audit:
            data_point = await service.add_data_point(
                entity_id=entity_id,
                facet_type_id=facet_type_id,
                recorded_at=data.recorded_at,
                value=data.value,
                track_key=data.track_key,
                value_label=data.value_label,
                annotations=data.annotations,
                source_type=data.source_type,
                source_url=data.source_url,
                confidence_score=data.confidence_score,
            )

            audit.track_action(
                action=AuditAction.CREATE,
                entity_type="FacetValueHistory",
                entity_id=data_point.id,
                entity_name=f"History point at {data.recorded_at}",
                changes={
                    "entity_id": str(entity_id),
                    "facet_type_id": str(facet_type_id),
                    "track_key": data.track_key,
                    "value": data.value,
                    "recorded_at": data.recorded_at.isoformat(),
                },
            )

            await session.commit()
            await session.refresh(data_point)

        return HistoryDataPointResponse.model_validate(data_point)

    except ValueError as e:
        raise ConflictError("Invalid data", detail=str(e)) from None


@router.post("/entity/{entity_id}/history/{facet_type_id}/bulk", response_model=HistoryBulkImportResponse)
async def add_history_data_points_bulk(
    entity_id: UUID,
    facet_type_id: UUID,
    data: HistoryBulkImport,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Bulk import multiple history data points.

    Requires Editor role. Optionally skips duplicates.
    """
    service = FacetHistoryService(session)

    try:
        async with AuditContext(session, current_user, request) as audit:
            result = await service.add_data_points_bulk(
                entity_id=entity_id,
                facet_type_id=facet_type_id,
                data_points=data.data_points,
                skip_duplicates=data.skip_duplicates,
            )

            audit.track_action(
                action=AuditAction.CREATE,
                entity_type="FacetValueHistory",
                entity_id=entity_id,  # Using entity_id as reference
                entity_name=f"Bulk import: {result.created} points",
                changes={
                    "entity_id": str(entity_id),
                    "facet_type_id": str(facet_type_id),
                    "created": result.created,
                    "skipped": result.skipped,
                },
            )

            await session.commit()

        return result

    except ValueError as e:
        raise ConflictError("Invalid data", detail=str(e)) from None


@router.put("/entity/{entity_id}/history/{facet_type_id}/{point_id}", response_model=HistoryDataPointResponse)
async def update_history_data_point(
    entity_id: UUID,
    facet_type_id: UUID,
    point_id: UUID,
    data: HistoryDataPointUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Update a history data point.

    Requires Editor role.
    """
    service = FacetHistoryService(session)

    async with AuditContext(session, current_user, request) as audit:
        data_point = await service.update_data_point(
            data_point_id=point_id,
            value=data.value,
            value_label=data.value_label,
            annotations=data.annotations,
            human_verified=data.human_verified,
            verified_by=current_user.email if data.human_verified else None,
        )

        if not data_point:
            raise NotFoundError("HistoryDataPoint", str(point_id))

        audit.track_action(
            action=AuditAction.UPDATE,
            entity_type="FacetValueHistory",
            entity_id=point_id,
            entity_name=f"History point at {data_point.recorded_at}",
            changes=data.model_dump(exclude_unset=True),
        )

        await session.commit()
        await session.refresh(data_point)

    return HistoryDataPointResponse.model_validate(data_point)


@router.delete("/entity/{entity_id}/history/{facet_type_id}/{point_id}", response_model=MessageResponse)
async def delete_history_data_point(
    entity_id: UUID,
    facet_type_id: UUID,
    point_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Delete a single history data point.

    Requires Editor role.
    """
    service = FacetHistoryService(session)

    async with AuditContext(session, current_user, request) as audit:
        deleted = await service.delete_data_point(point_id)

        if not deleted:
            raise NotFoundError("HistoryDataPoint", str(point_id))

        audit.track_action(
            action=AuditAction.DELETE,
            entity_type="FacetValueHistory",
            entity_id=point_id,
            entity_name=f"History point {point_id}",
            changes={"deleted": True},
        )

        await session.commit()

    return MessageResponse(message="History data point deleted successfully")
