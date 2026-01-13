"""
Admin API endpoints for LLM usage analytics.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
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


class RecalculateCostsResponse(BaseModel):
    """Response for cost recalculation endpoint."""

    total_records: int
    updated_records: int
    total_cost_before_cents: int
    total_cost_after_cents: int
    models_processed: dict[str, int]

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


class PricingDebugInfo(BaseModel):
    """Debug info for pricing lookup."""

    model: str
    record_count: int
    sample_prompt_tokens: int
    sample_completion_tokens: int
    pricing_found: dict[str, float]
    normalized_name: str
    base_model: str | None
    calculated_cost_cents: int


@router.get("/debug-pricing")
async def debug_pricing(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> list[PricingDebugInfo]:
    """
    Debug endpoint to see how pricing is resolved for each model.

    Shows which models are used, how they're normalized, and what pricing is applied.
    """
    from sqlalchemy import func, select

    from app.models.llm_usage import LLMUsageRecord
    from services.llm_usage_tracker import (
        _extract_base_model,
        _normalize_model_name,
        get_model_pricing,
    )

    # Get distinct models with counts and sample token values
    query = select(
        LLMUsageRecord.model,
        func.count(LLMUsageRecord.id).label("count"),
        func.avg(LLMUsageRecord.prompt_tokens).label("avg_prompt"),
        func.avg(LLMUsageRecord.completion_tokens).label("avg_completion"),
    ).group_by(LLMUsageRecord.model)

    result = await db.execute(query)
    rows = result.all()

    debug_info = []
    for row in rows:
        model = row.model
        pricing = get_model_pricing(model)
        normalized = _normalize_model_name(model)
        base = _extract_base_model(model)

        avg_prompt = int(row.avg_prompt or 0)
        avg_completion = int(row.avg_completion or 0)

        # Calculate what cost would be
        input_cost = (avg_prompt / 1_000_000) * pricing["input"]
        output_cost = (avg_completion / 1_000_000) * pricing["output"]
        calc_cost = int((input_cost + output_cost) * 100 + 0.5)

        debug_info.append(
            PricingDebugInfo(
                model=model,
                record_count=row.count,
                sample_prompt_tokens=avg_prompt,
                sample_completion_tokens=avg_completion,
                pricing_found=pricing,
                normalized_name=normalized,
                base_model=base,
                calculated_cost_cents=calc_cost,
            )
        )

    return debug_info


@router.post("/recalculate-costs", response_model=RecalculateCostsResponse)
async def recalculate_costs(
    only_zero_costs: bool = Query(
        True,
        description="Only recalculate records with zero costs (recommended)",
    ),
    period: str = Query(
        "all",
        description="Period to recalculate: 24h, 7d, 30d, 90d, all",
        pattern="^(24h|7d|30d|90d|all)$",
    ),
    dry_run: bool = Query(
        False,
        description="If true, only show what would be updated without making changes",
    ),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    Recalculate estimated costs for LLM usage records.

    Uses current model pricing to recalculate costs based on stored token counts.
    Useful after adding/updating model pricing or fixing pricing mismatches.

    By default, only recalculates records with zero costs to avoid overwriting
    intentionally set values.
    """
    from collections import defaultdict

    from sqlalchemy import select

    from app.models.llm_usage import LLMUsageRecord
    from services.llm_usage_tracker import get_model_pricing

    # Build time filter
    now = datetime.now(UTC)
    period_map = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
    }

    # Build query
    query = select(LLMUsageRecord)

    if period != "all":
        delta = period_map.get(period, timedelta(days=7))
        start_date = now - delta
        query = query.where(LLMUsageRecord.created_at >= start_date)

    if only_zero_costs:
        query = query.where(LLMUsageRecord.estimated_cost_cents == 0)

    result = await db.execute(query)
    records = result.scalars().all()

    total_records = len(records)
    updated_records = 0
    total_cost_before = 0
    total_cost_after = 0
    models_processed: dict[str, int] = defaultdict(int)

    for record in records:
        total_cost_before += record.estimated_cost_cents or 0

        # Get current pricing for this model
        pricing = get_model_pricing(record.model)

        # Calculate new cost
        input_cost = (record.prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (record.completion_tokens / 1_000_000) * pricing["output"]
        new_cost_cents = int((input_cost + output_cost) * 100 + 0.5)

        total_cost_after += new_cost_cents
        models_processed[record.model] += 1

        # Update if cost changed and not dry run
        if new_cost_cents != record.estimated_cost_cents:
            if not dry_run:
                record.estimated_cost_cents = new_cost_cents
            updated_records += 1

    if not dry_run:
        await db.commit()

    return RecalculateCostsResponse(
        total_records=total_records,
        updated_records=updated_records,
        total_cost_before_cents=total_cost_before,
        total_cost_after_cents=total_cost_after,
        models_processed=dict(models_processed),
    )
