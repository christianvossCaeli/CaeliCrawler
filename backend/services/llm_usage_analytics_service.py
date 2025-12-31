"""
LLM Usage Analytics Service.

Provides aggregated analytics and reporting for LLM usage data.
"""

from datetime import UTC, date, datetime
from uuid import UUID

import structlog
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.llm_usage import (
    LLMProvider,
    LLMTaskType,
    LLMUsageRecord,
)
from app.schemas.llm_usage import (
    LLMCostProjection,
    LLMUsageAnalyticsResponse,
    LLMUsageByCategory,
    LLMUsageByModel,
    LLMUsageByTask,
    LLMUsageSummary,
    LLMUsageTopConsumer,
    LLMUsageTrend,
)

logger = structlog.get_logger(__name__)


class LLMUsageAnalyticsService:
    """Service for computing LLM usage analytics."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_analytics(
        self,
        start_date: datetime,
        end_date: datetime,
        provider: LLMProvider | None = None,
        model: str | None = None,
        task_type: LLMTaskType | None = None,
        category_id: UUID | None = None,
    ) -> LLMUsageAnalyticsResponse:
        """Get comprehensive analytics for a time period."""

        # Build base filter
        base_filter = and_(
            LLMUsageRecord.created_at >= start_date,
            LLMUsageRecord.created_at < end_date,
        )
        if provider:
            base_filter = and_(base_filter, LLMUsageRecord.provider == provider)
        if model:
            base_filter = and_(base_filter, LLMUsageRecord.model == model)
        if task_type:
            base_filter = and_(base_filter, LLMUsageRecord.task_type == task_type)
        if category_id:
            base_filter = and_(base_filter, LLMUsageRecord.category_id == category_id)

        # Get all analytics in parallel
        summary = await self._get_summary(base_filter)
        by_model = await self._get_by_model(base_filter)
        by_task = await self._get_by_task(base_filter)
        by_category = await self._get_by_category(base_filter)
        daily_trend = await self._get_daily_trend(start_date, end_date, base_filter)
        top_consumers = await self._get_top_consumers(base_filter)

        return LLMUsageAnalyticsResponse(
            period_start=start_date,
            period_end=end_date,
            summary=summary,
            by_model=by_model,
            by_task=by_task,
            by_category=by_category,
            daily_trend=daily_trend,
            top_consumers=top_consumers,
        )

    async def _get_summary(self, base_filter) -> LLMUsageSummary:
        """Get summary statistics."""
        query = select(
            func.count(LLMUsageRecord.id).label("total_requests"),
            func.coalesce(func.sum(LLMUsageRecord.total_tokens), 0).label(
                "total_tokens"
            ),
            func.coalesce(func.sum(LLMUsageRecord.prompt_tokens), 0).label(
                "total_prompt_tokens"
            ),
            func.coalesce(func.sum(LLMUsageRecord.completion_tokens), 0).label(
                "total_completion_tokens"
            ),
            func.coalesce(func.sum(LLMUsageRecord.estimated_cost_cents), 0).label(
                "total_cost_cents"
            ),
            func.coalesce(func.avg(LLMUsageRecord.duration_ms), 0).label(
                "avg_duration_ms"
            ),
            func.sum(case((LLMUsageRecord.is_error, 1), else_=0)).label(
                "error_count"
            ),
        ).where(base_filter)

        result = await self.session.execute(query)
        row = result.one()

        total_requests = row.total_requests or 0
        error_count = row.error_count or 0
        error_rate = error_count / total_requests if total_requests > 0 else 0

        return LLMUsageSummary(
            total_requests=total_requests,
            total_tokens=row.total_tokens or 0,
            total_prompt_tokens=row.total_prompt_tokens or 0,
            total_completion_tokens=row.total_completion_tokens or 0,
            total_cost_cents=row.total_cost_cents or 0,
            avg_duration_ms=float(row.avg_duration_ms or 0),
            error_count=error_count,
            error_rate=error_rate,
        )

    async def _get_by_model(self, base_filter) -> list[LLMUsageByModel]:
        """Get usage breakdown by model."""
        query = (
            select(
                LLMUsageRecord.model,
                LLMUsageRecord.provider,
                func.count(LLMUsageRecord.id).label("request_count"),
                func.sum(LLMUsageRecord.total_tokens).label("total_tokens"),
                func.sum(LLMUsageRecord.estimated_cost_cents).label("cost_cents"),
            )
            .where(base_filter)
            .group_by(LLMUsageRecord.model, LLMUsageRecord.provider)
            .order_by(func.sum(LLMUsageRecord.total_tokens).desc())
        )

        result = await self.session.execute(query)
        return [
            LLMUsageByModel(
                model=row.model,
                provider=row.provider,
                request_count=row.request_count,
                total_tokens=row.total_tokens or 0,
                cost_cents=row.cost_cents or 0,
                avg_tokens_per_request=(
                    row.total_tokens / row.request_count
                    if row.request_count > 0
                    else 0
                ),
            )
            for row in result.all()
        ]

    async def _get_by_task(self, base_filter) -> list[LLMUsageByTask]:
        """Get usage breakdown by task type."""
        query = (
            select(
                LLMUsageRecord.task_type,
                func.count(LLMUsageRecord.id).label("request_count"),
                func.sum(LLMUsageRecord.total_tokens).label("total_tokens"),
                func.sum(LLMUsageRecord.estimated_cost_cents).label("cost_cents"),
                func.avg(LLMUsageRecord.duration_ms).label("avg_duration_ms"),
            )
            .where(base_filter)
            .group_by(LLMUsageRecord.task_type)
            .order_by(func.sum(LLMUsageRecord.total_tokens).desc())
        )

        result = await self.session.execute(query)
        return [
            LLMUsageByTask(
                task_type=row.task_type,
                request_count=row.request_count,
                total_tokens=row.total_tokens or 0,
                cost_cents=row.cost_cents or 0,
                avg_duration_ms=float(row.avg_duration_ms or 0),
            )
            for row in result.all()
        ]

    async def _get_by_category(self, base_filter) -> list[LLMUsageByCategory]:
        """Get usage breakdown by category."""
        query = (
            select(
                LLMUsageRecord.category_id,
                Category.name.label("category_name"),
                func.count(LLMUsageRecord.id).label("request_count"),
                func.sum(LLMUsageRecord.total_tokens).label("total_tokens"),
                func.sum(LLMUsageRecord.estimated_cost_cents).label("cost_cents"),
            )
            .outerjoin(Category, LLMUsageRecord.category_id == Category.id)
            .where(base_filter)
            .group_by(LLMUsageRecord.category_id, Category.name)
            .order_by(func.sum(LLMUsageRecord.total_tokens).desc())
            .limit(20)
        )

        result = await self.session.execute(query)
        return [
            LLMUsageByCategory(
                category_id=row.category_id,
                category_name=row.category_name,
                request_count=row.request_count,
                total_tokens=row.total_tokens or 0,
                cost_cents=row.cost_cents or 0,
            )
            for row in result.all()
        ]

    async def _get_daily_trend(
        self, start_date: datetime, end_date: datetime, base_filter
    ) -> list[LLMUsageTrend]:
        """Get daily usage trend."""
        # Use a single expression variable to ensure GROUP BY matches SELECT
        day_trunc = func.date_trunc("day", LLMUsageRecord.created_at)
        query = (
            select(
                day_trunc.label("day"),
                func.count(LLMUsageRecord.id).label("request_count"),
                func.sum(LLMUsageRecord.total_tokens).label("total_tokens"),
                func.sum(LLMUsageRecord.estimated_cost_cents).label("cost_cents"),
                func.sum(case((LLMUsageRecord.is_error, 1), else_=0)).label(
                    "error_count"
                ),
            )
            .where(base_filter)
            .group_by(day_trunc)
            .order_by(day_trunc)
        )

        result = await self.session.execute(query)
        return [
            LLMUsageTrend(
                day=row.day.date() if row.day else date.today(),
                request_count=row.request_count,
                total_tokens=row.total_tokens or 0,
                cost_cents=row.cost_cents or 0,
                error_count=row.error_count or 0,
            )
            for row in result.all()
        ]

    async def _get_top_consumers(
        self, base_filter, limit: int = 10
    ) -> list[LLMUsageTopConsumer]:
        """Get top token-consuming tasks."""
        query = (
            select(
                LLMUsageRecord.task_name,
                LLMUsageRecord.task_type,
                func.count(LLMUsageRecord.id).label("request_count"),
                func.sum(LLMUsageRecord.total_tokens).label("total_tokens"),
                func.sum(LLMUsageRecord.estimated_cost_cents).label("cost_cents"),
            )
            .where(and_(base_filter, LLMUsageRecord.task_name.isnot(None)))
            .group_by(LLMUsageRecord.task_name, LLMUsageRecord.task_type)
            .order_by(func.sum(LLMUsageRecord.total_tokens).desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return [
            LLMUsageTopConsumer(
                task_name=row.task_name or "Unknown",
                task_type=row.task_type,
                request_count=row.request_count,
                total_tokens=row.total_tokens or 0,
                cost_cents=row.cost_cents or 0,
            )
            for row in result.all()
        ]

    async def get_cost_projection(self) -> LLMCostProjection:
        """Get cost projection for current month."""
        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        days_elapsed = (now - month_start).days + 1
        days_in_month = 30  # Approximation

        # Get current month cost
        query = select(
            func.coalesce(func.sum(LLMUsageRecord.estimated_cost_cents), 0)
        ).where(LLMUsageRecord.created_at >= month_start)

        result = await self.session.execute(query)
        current_cost = result.scalar() or 0

        daily_avg = current_cost / days_elapsed if days_elapsed > 0 else 0
        projected = int(daily_avg * days_in_month)

        # Check if any budget has warnings
        from app.models.llm_budget import LLMBudgetConfig

        budget_query = select(LLMBudgetConfig).where(
            and_(
                LLMBudgetConfig.is_active,
                LLMBudgetConfig.budget_type == "global",
            )
        )
        budget_result = await self.session.execute(budget_query)
        global_budget = budget_result.scalar_one_or_none()

        budget_limit = None
        budget_warning = False
        if global_budget:
            budget_limit = global_budget.monthly_limit_cents
            usage_percent = (
                current_cost / budget_limit * 100 if budget_limit > 0 else 0
            )
            budget_warning = usage_percent >= global_budget.warning_threshold_percent

        return LLMCostProjection(
            current_month_cost_cents=current_cost,
            projected_month_cost_cents=projected,
            daily_avg_cost_cents=int(daily_avg),
            budget_warning=budget_warning,
            budget_limit_cents=budget_limit,
        )

    async def get_document_usage(self, document_id: UUID) -> dict | None:
        """Get usage details for a specific document."""
        query = (
            select(
                func.count(LLMUsageRecord.id).label("request_count"),
                func.sum(LLMUsageRecord.total_tokens).label("total_tokens"),
                func.sum(LLMUsageRecord.estimated_cost_cents).label("cost_cents"),
                func.min(LLMUsageRecord.created_at).label("first_request"),
                func.max(LLMUsageRecord.created_at).label("last_request"),
            )
            .where(LLMUsageRecord.document_id == document_id)
        )

        result = await self.session.execute(query)
        row = result.one()

        if row.request_count == 0:
            return None

        return {
            "document_id": str(document_id),
            "request_count": row.request_count,
            "total_tokens": row.total_tokens or 0,
            "cost_cents": row.cost_cents or 0,
            "first_request": row.first_request.isoformat() if row.first_request else None,
            "last_request": row.last_request.isoformat() if row.last_request else None,
        }
