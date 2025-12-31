"""
Admin API endpoints for LLM usage analytics.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.database import get_session
from app.models.llm_usage import LLMProvider, LLMTaskType
from app.models.user import User
from app.schemas.llm_usage import (
    LLMCostProjection,
    LLMUsageAnalyticsResponse,
)
from services.llm_usage_analytics_service import LLMUsageAnalyticsService

router = APIRouter(
    prefix="/llm-usage",
    tags=["Admin - LLM Usage"],
)


@router.get("/analytics", response_model=LLMUsageAnalyticsResponse)
async def get_llm_analytics(
    period: str = Query(
        "7d",
        description="Period: 24h, 7d, 30d, 90d",
        pattern="^(24h|7d|30d|90d)$",
    ),
    provider: LLMProvider | None = Query(None, description="Filter by provider"),
    model: str | None = Query(None, description="Filter by model"),
    task_type: LLMTaskType | None = Query(None, description="Filter by task type"),
    category_id: UUID | None = Query(None, description="Filter by category"),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    Get comprehensive LLM usage analytics.

    Returns summary statistics, breakdowns by model and task type,
    daily trends, and top token consumers.
    """
    now = datetime.now(UTC)

    period_map = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
    }

    delta = period_map.get(period, timedelta(days=7))
    start_date = now - delta

    service = LLMUsageAnalyticsService(db)
    return await service.get_analytics(
        start_date=start_date,
        end_date=now,
        provider=provider,
        model=model,
        task_type=task_type,
        category_id=category_id,
    )


@router.get("/cost-projection", response_model=LLMCostProjection)
async def get_cost_projection(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    Get cost projection for current month.

    Returns current month spending, projected end-of-month cost,
    and budget warning status.
    """
    service = LLMUsageAnalyticsService(db)
    return await service.get_cost_projection()


@router.get("/by-category")
async def get_usage_by_category(
    period: str = Query("30d", pattern="^(24h|7d|30d|90d)$"),
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    Get usage breakdown by category.

    Returns top categories by token consumption.
    """
    now = datetime.now(UTC)
    period_map = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
    }
    start_date = now - period_map.get(period, timedelta(days=30))

    service = LLMUsageAnalyticsService(db)
    analytics = await service.get_analytics(start_date=start_date, end_date=now)
    return analytics.by_category[:limit]


@router.get("/document/{document_id}")
async def get_document_usage(
    document_id: UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    Get usage details for a specific document.

    Returns token consumption and cost for processing a single document.
    """
    service = LLMUsageAnalyticsService(db)
    usage = await service.get_document_usage(document_id)

    if not usage:
        return {"document_id": str(document_id), "message": "No usage data found"}

    return usage


@router.get("/export")
async def export_usage_data(
    period: str = Query("30d", pattern="^(24h|7d|30d|90d)$"),
    format: str = Query("csv", pattern="^(csv|json)$"),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    Export usage data as CSV or JSON.

    Downloads aggregated usage data for the specified period.
    """
    import csv
    import io
    import json

    now = datetime.now(UTC)
    period_map = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
    }
    start_date = now - period_map.get(period, timedelta(days=30))

    service = LLMUsageAnalyticsService(db)
    analytics = await service.get_analytics(start_date=start_date, end_date=now)

    if format == "json":
        content = json.dumps(analytics.model_dump(), indent=2, default=str)
        return StreamingResponse(
            io.BytesIO(content.encode()),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=llm_usage_{period}.json"
            },
        )
    else:
        # CSV format - export daily trend
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            ["date", "requests", "tokens", "cost_cents", "cost_usd", "errors"]
        )
        for trend in analytics.daily_trend:
            writer.writerow([
                trend.date.isoformat(),
                trend.request_count,
                trend.total_tokens,
                trend.cost_cents,
                f"{trend.cost_cents / 100:.2f}",
                trend.error_count,
            ])

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=llm_usage_{period}.csv"
            },
        )
