"""Admin API endpoints for audit log."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.audit_log import AuditLog, AuditAction
from app.models.user import User
from app.core.deps import require_admin

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================


class AuditLogResponse(BaseModel):
    """Audit log entry response."""

    id: UUID
    user_id: Optional[UUID] = None
    user_email: Optional[str] = None
    action: AuditAction
    entity_type: str
    entity_id: Optional[UUID] = None
    entity_name: Optional[str] = None
    changes: Dict[str, Any]
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Paginated audit log list."""

    items: List[AuditLogResponse]
    total: int
    page: int
    per_page: int
    pages: int


class AuditStatsResponse(BaseModel):
    """Audit log statistics."""

    total_entries: int
    entries_today: int
    entries_this_week: int
    actions_breakdown: Dict[str, int]
    top_users: List[Dict[str, Any]]
    top_entity_types: List[Dict[str, Any]]


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    action: Optional[AuditAction] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """
    List audit log entries with filtering and pagination.

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
    Get audit log statistics.

    Admin only.
    """
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    # Total entries
    total_result = await session.execute(select(func.count(AuditLog.id)))
    total_entries = total_result.scalar() or 0

    # Entries today
    today_result = await session.execute(
        select(func.count(AuditLog.id)).where(AuditLog.created_at >= today_start)
    )
    entries_today = today_result.scalar() or 0

    # Entries this week
    week_result = await session.execute(
        select(func.count(AuditLog.id)).where(AuditLog.created_at >= week_start)
    )
    entries_this_week = week_result.scalar() or 0

    # Actions breakdown
    actions_result = await session.execute(
        select(AuditLog.action, func.count(AuditLog.id))
        .group_by(AuditLog.action)
    )
    actions_breakdown = {
        action.value: count for action, count in actions_result.all()
    }

    # Top users (last 30 days)
    month_ago = now - timedelta(days=30)
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

    # Top entity types (last 30 days)
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
        total_entries=total_entries,
        entries_today=entries_today,
        entries_this_week=entries_this_week,
        actions_breakdown=actions_breakdown,
        top_users=top_users,
        top_entity_types=top_entity_types,
    )
