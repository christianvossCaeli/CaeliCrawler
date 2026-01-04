"""Admin API endpoints for audit log."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.database import get_session
from app.models.audit_log import AuditAction, AuditLog
from app.models.user import User

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================


class AuditLogResponse(BaseModel):
    """Audit log entry response."""

    id: UUID
    user_id: UUID | None = None
    user_email: str | None = None
    action: AuditAction
    entity_type: str
    entity_id: UUID | None = None
    entity_name: str | None = None
    changes: dict[str, Any]
    ip_address: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    """Paginated audit log list."""

    items: list[AuditLogResponse]
    total: int
    page: int
    per_page: int
    pages: int


class AuditStatsResponse(BaseModel):
    """Audit log statistics."""

    total_entries: int
    entries_today: int
    entries_this_week: int
    actions_breakdown: dict[str, int]
    top_users: list[dict[str, Any]]
    top_entity_types: list[dict[str, Any]]


class AuditLogDeleteResponse(BaseModel):
    """Response for audit log deletion."""

    deleted_count: int
    message: str


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    action: AuditAction | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    user_id: UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    sort_by: str | None = Query(default=None, description="Sort by field (action, entity_type, user_email, created_at)"),
    sort_order: str | None = Query(default="desc", description="Sort order (asc, desc)"),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """
    List audit log entries with filtering, pagination and sorting.

    Admin only.
    """
    # Build query
    query = select(AuditLog)

    # Apply filters
    conditions = []
    if action:
        conditions.append(AuditLog.action == action)
    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)
    if entity_id:
        conditions.append(AuditLog.entity_id == entity_id)
    if user_id:
        conditions.append(AuditLog.user_id == user_id)
    if start_date:
        conditions.append(AuditLog.created_at >= start_date)
    if end_date:
        conditions.append(AuditLog.created_at <= end_date)

    if conditions:
        query = query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    # Handle sorting
    sort_desc = sort_order == "desc"
    sort_column_map = {
        "action": AuditLog.action,
        "entity_type": AuditLog.entity_type,
        "user_email": AuditLog.user_email,
        "created_at": AuditLog.created_at,
    }

    if sort_by and sort_by in sort_column_map:
        order_col = sort_column_map[sort_by]
        if sort_desc:
            query = query.order_by(order_col.desc().nulls_last(), AuditLog.created_at.desc())
        else:
            query = query.order_by(order_col.asc().nulls_last(), AuditLog.created_at.desc())
    else:
        # Default ordering
        query = query.order_by(desc(AuditLog.created_at))

    # Apply pagination
    query = query.offset((page - 1) * per_page).limit(per_page)

    # Execute query
    result = await session.execute(query)
    logs = list(result.scalars().all())

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.get("/entity/{entity_type}/{entity_id}", response_model=AuditLogListResponse)
async def get_entity_audit_history(
    entity_type: str,
    entity_id: UUID,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """
    Get audit history for a specific entity.

    Admin only.
    """
    query = select(AuditLog).where(
        and_(
            AuditLog.entity_type == entity_type,
            AuditLog.entity_id == entity_id,
        )
    )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    # Apply pagination and ordering
    query = query.order_by(desc(AuditLog.created_at))
    query = query.offset((page - 1) * per_page).limit(per_page)

    # Execute query
    result = await session.execute(query)
    logs = list(result.scalars().all())

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.get("/user/{user_id}", response_model=AuditLogListResponse)
async def get_user_audit_history(
    user_id: UUID,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """
    Get audit history for a specific user.

    Admin only.
    """
    query = select(AuditLog).where(AuditLog.user_id == user_id)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    # Apply pagination and ordering
    query = query.order_by(desc(AuditLog.created_at))
    query = query.offset((page - 1) * per_page).limit(per_page)

    # Execute query
    result = await session.execute(query)
    logs = list(result.scalars().all())

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """
    Get audit log statistics (optimized: 4 queries instead of 6).

    Admin only. All stats are based on last 30 days for performance.
    """
    from datetime import timedelta

    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_ago = now - timedelta(days=30)

    # Query 1: All counts in one query using conditional aggregation (last 30 days)
    counts = (await session.execute(
        select(
            func.count(AuditLog.id).label("total"),
            func.count().filter(AuditLog.created_at >= today_start).label("today"),
            func.count().filter(AuditLog.created_at >= week_start).label("week"),
        ).where(AuditLog.created_at >= month_ago)
    )).one()

    # Query 2: Actions breakdown (last 30 days for performance)
    actions_result = await session.execute(
        select(AuditLog.action, func.count(AuditLog.id))
        .where(AuditLog.created_at >= month_ago)
        .group_by(AuditLog.action)
    )
    actions_breakdown = {
        action.value: count for action, count in actions_result.all()
    }

    # Query 3: Top users (last 30 days)
    top_users_result = await session.execute(
        select(AuditLog.user_email, func.count(AuditLog.id).label("count"))
        .where(
            and_(
                AuditLog.created_at >= month_ago,
                AuditLog.user_email.isnot(None),
            )
        )
        .group_by(AuditLog.user_email)
        .order_by(desc("count"))
        .limit(10)
    )
    top_users = [
        {"email": email, "count": count}
        for email, count in top_users_result.all()
    ]

    # Query 4: Top entity types (last 30 days)
    top_entities_result = await session.execute(
        select(AuditLog.entity_type, func.count(AuditLog.id).label("count"))
        .where(AuditLog.created_at >= month_ago)
        .group_by(AuditLog.entity_type)
        .order_by(desc("count"))
        .limit(10)
    )
    top_entity_types = [
        {"entity_type": entity_type, "count": count}
        for entity_type, count in top_entities_result.all()
    ]

    return AuditStatsResponse(
        total_entries=counts.total or 0,
        entries_today=counts.today or 0,
        entries_this_week=counts.week or 0,
        actions_breakdown=actions_breakdown,
        top_users=top_users,
        top_entity_types=top_entity_types,
    )


@router.delete("", response_model=AuditLogDeleteResponse)
async def clear_audit_logs(
    before_date: datetime | None = Query(
        default=None,
        description="Delete logs before this date. If not provided, deletes ALL logs."
    ),
    action: AuditAction | None = Query(
        default=None,
        description="Only delete logs with this action type"
    ),
    entity_type: str | None = Query(
        default=None,
        description="Only delete logs for this entity type"
    ),
    confirm: bool = Query(
        default=False,
        description="Must be true to confirm deletion"
    ),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """
    Clear audit logs with optional filters.

    **WARNING**: This operation is irreversible!

    Admin only. Requires `confirm=true` parameter.

    **Options:**
    - No parameters: Deletes ALL audit logs
    - `before_date`: Only delete logs older than this date
    - `action`: Only delete logs with specific action type
    - `entity_type`: Only delete logs for specific entity type

    Filters can be combined.
    """
    from app.core.audit import AuditContext

    if not confirm:
        from app.core.exceptions import ValidationError
        raise ValidationError(
            "Deletion not confirmed",
            detail="Set confirm=true to confirm deletion of audit logs"
        )

    # Build delete query with filters
    from sqlalchemy import delete

    conditions = []
    if before_date:
        conditions.append(AuditLog.created_at < before_date)
    if action:
        conditions.append(AuditLog.action == action)
    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)

    # Count records to delete first
    count_query = select(func.count(AuditLog.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    count = (await session.execute(count_query)).scalar() or 0

    if count == 0:
        return AuditLogDeleteResponse(
            deleted_count=0,
            message="No audit logs matched the criteria"
        )

    # Delete matching records
    delete_query = delete(AuditLog)
    if conditions:
        delete_query = delete_query.where(and_(*conditions))

    await session.execute(delete_query)

    # Log the deletion itself (this creates a new audit entry about the clearing)
    async with AuditContext(session, current_user, None) as audit:
        audit.track_action(
            action=AuditAction.DELETE,
            entity_type="AuditLog",
            entity_name="Audit Log Clearing",
            changes={
                "deleted_count": count,
                "filters": {
                    "before_date": before_date.isoformat() if before_date else None,
                    "action": action.value if action else None,
                    "entity_type": entity_type,
                },
            },
        )

    await session.commit()

    # Build message
    filter_parts = []
    if before_date:
        filter_parts.append(f"before {before_date.strftime('%Y-%m-%d %H:%M')}")
    if action:
        filter_parts.append(f"action={action.value}")
    if entity_type:
        filter_parts.append(f"entity_type={entity_type}")

    filter_str = " with filters: " + ", ".join(filter_parts) if filter_parts else ""

    return AuditLogDeleteResponse(
        deleted_count=count,
        message=f"Successfully deleted {count} audit log entries{filter_str}"
    )
