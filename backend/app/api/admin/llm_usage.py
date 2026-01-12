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
            headers={"Content-Disposition": f"attachment; filename=llm_usage_{period}.json"},
        )
    else:
        # CSV format - export all data in sections
        output = io.StringIO()
        writer = csv.writer(output)

        # Section 1: Summary
        writer.writerow(["=== SUMMARY ==="])
        writer.writerow(["period_start", "period_end"])
        writer.writerow([analytics.period_start.isoformat(), analytics.period_end.isoformat()])
        writer.writerow([])
        writer.writerow(
            [
                "total_requests",
                "total_tokens",
                "prompt_tokens",
                "completion_tokens",
                "cost_cents",
                "cost_usd",
                "avg_duration_ms",
                "error_count",
                "error_rate",
            ]
        )
        s = analytics.summary
        writer.writerow(
            [
                s.total_requests,
                s.total_tokens,
                s.total_prompt_tokens,
                s.total_completion_tokens,
                s.total_cost_cents,
                f"{s.total_cost_cents / 100:.2f}",
                f"{s.avg_duration_ms:.1f}",
                s.error_count,
                f"{s.error_rate:.4f}",
            ]
        )
        writer.writerow([])

        # Section 2: Daily Trend
        writer.writerow(["=== DAILY TREND ==="])
        writer.writerow(["date", "requests", "tokens", "cost_cents", "cost_usd", "errors"])
        for trend in analytics.daily_trend:
            writer.writerow(
                [
                    trend.day.isoformat(),
                    trend.request_count,
                    trend.total_tokens,
                    trend.cost_cents,
                    f"{trend.cost_cents / 100:.2f}",
                    trend.error_count,
                ]
            )
        writer.writerow([])

        # Section 3: By Model
        writer.writerow(["=== BY MODEL ==="])
        writer.writerow(["model", "provider", "requests", "tokens", "cost_cents", "cost_usd", "avg_tokens_per_request"])
        for m in analytics.by_model:
            writer.writerow(
                [
                    m.model,
                    m.provider.value,
                    m.request_count,
                    m.total_tokens,
                    m.cost_cents,
                    f"{m.cost_cents / 100:.2f}",
                    f"{m.avg_tokens_per_request:.1f}",
                ]
            )
        writer.writerow([])

        # Section 4: By Task Type
        writer.writerow(["=== BY TASK TYPE ==="])
        writer.writerow(["task_type", "requests", "tokens", "cost_cents", "cost_usd", "avg_duration_ms"])
        for t in analytics.by_task:
            writer.writerow(
                [
                    t.task_type.value,
                    t.request_count,
                    t.total_tokens,
                    t.cost_cents,
                    f"{t.cost_cents / 100:.2f}",
                    f"{t.avg_duration_ms:.1f}",
                ]
            )
        writer.writerow([])

        # Section 5: By Category
        writer.writerow(["=== BY CATEGORY ==="])
        writer.writerow(["category_id", "category_name", "requests", "tokens", "cost_cents", "cost_usd"])
        for c in analytics.by_category:
            writer.writerow(
                [
                    str(c.category_id) if c.category_id else "",
                    c.category_name or "(uncategorized)",
                    c.request_count,
                    c.total_tokens,
                    c.cost_cents,
                    f"{c.cost_cents / 100:.2f}",
                ]
            )
        writer.writerow([])

        # Section 6: By User
        writer.writerow(["=== BY USER ==="])
        writer.writerow(
            [
                "user_id",
                "user_email",
                "user_name",
                "requests",
                "tokens",
                "prompt_tokens",
                "completion_tokens",
                "cost_cents",
                "cost_usd",
                "models_used",
                "has_credentials",
            ]
        )
        for u in analytics.by_user:
            writer.writerow(
                [
                    str(u.user_id) if u.user_id else "(system)",
                    u.user_email or "",
                    u.user_name or "",
                    u.request_count,
                    u.total_tokens,
                    u.prompt_tokens,
                    u.completion_tokens,
                    u.cost_cents,
                    f"{u.cost_cents / 100:.2f}",
                    ";".join(u.models_used),
                    u.has_credentials,
                ]
            )
        writer.writerow([])

        # Section 7: Top Consumers
        writer.writerow(["=== TOP CONSUMERS ==="])
        writer.writerow(["task_name", "task_type", "requests", "tokens", "cost_cents", "cost_usd"])
        for tc in analytics.top_consumers:
            writer.writerow(
                [
                    tc.task_name,
                    tc.task_type.value,
                    tc.request_count,
                    tc.total_tokens,
                    tc.cost_cents,
                    f"{tc.cost_cents / 100:.2f}",
                ]
            )

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),  # UTF-8 BOM for Excel compatibility
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=llm_usage_{period}.csv"},
        )
