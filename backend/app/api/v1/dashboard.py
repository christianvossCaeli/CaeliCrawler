"""API endpoints for the Dashboard."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.user import User
from app.schemas.dashboard import (
    ActivityFeedResponse,
    ChartDataResponse,
    DashboardPreferencesResponse,
    DashboardPreferencesUpdate,
    DashboardStatsResponse,
    InsightsResponse,
)
from app.core.deps import get_current_user
from services.dashboard_service import DashboardService

router = APIRouter()


@router.get("/preferences", response_model=DashboardPreferencesResponse)
async def get_dashboard_preferences(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get the current user's dashboard widget preferences."""
    service = DashboardService(session)
    return await service.get_preferences(current_user.id)


@router.put("/preferences", response_model=DashboardPreferencesResponse)
async def update_dashboard_preferences(
    update: DashboardPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update the current user's dashboard widget preferences."""
    service = DashboardService(session)
    return await service.update_preferences(current_user.id, update)


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get aggregated statistics for the dashboard."""
    service = DashboardService(session)
    return await service.get_stats()


@router.get("/activity", response_model=ActivityFeedResponse)
async def get_activity_feed(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get recent activity from the audit log."""
    service = DashboardService(session)
    return await service.get_activity_feed(limit=limit, offset=offset)


@router.get("/insights", response_model=InsightsResponse)
async def get_user_insights(
    period_days: int = Query(default=7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get personalized insights for the current user."""
    service = DashboardService(session)
    return await service.get_insights(current_user, period_days=period_days)


@router.get("/charts/{chart_type}", response_model=ChartDataResponse)
async def get_chart_data(
    chart_type: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get data for a specific chart.

    Available chart types:
    - entity-distribution: Entity distribution by type (pie chart)
    - facet-distribution: Facet values by type (bar chart)
    - crawler-trend: Crawler jobs over time (line chart)
    """
    service = DashboardService(session)
    return await service.get_chart_data(chart_type)
