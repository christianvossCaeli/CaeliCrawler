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
    LLMUsageByUser,
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
        by_user = await self._get_by_user(base_filter)
        daily_trend = await self._get_daily_trend(start_date, end_date, base_filter)
        top_consumers = await self._get_top_consumers(base_filter)

        return LLMUsageAnalyticsResponse(
            period_start=start_date,
            period_end=end_date,
            summary=summary,
            by_model=by_model,
            by_task=by_task,
            by_category=by_category,
            by_user=by_user,
            daily_trend=daily_trend,
            top_consumers=top_consumers,
        )

    async def _get_summary(self, base_filter) -> LLMUsageSummary:
        """Get summary statistics with dynamically calculated costs."""
        from services.llm_usage_tracker import get_model_pricing

        # First get basic stats
        basic_query = select(
            func.count(LLMUsageRecord.id).label("total_requests"),
            func.coalesce(func.sum(LLMUsageRecord.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(LLMUsageRecord.prompt_tokens), 0).label("total_prompt_tokens"),
            func.coalesce(func.sum(LLMUsageRecord.completion_tokens), 0).label("total_completion_tokens"),
            func.coalesce(func.avg(LLMUsageRecord.duration_ms), 0).label("avg_duration_ms"),
            func.sum(case((LLMUsageRecord.is_error, 1), else_=0)).label("error_count"),
        ).where(base_filter)

        result = await self.session.execute(basic_query)
        row = result.one()

        total_requests = int(row.total_requests or 0)
        error_count = int(row.error_count or 0)
        error_rate = error_count / total_requests if total_requests > 0 else 0

        # Calculate costs dynamically per model to avoid rounding issues
        cost_query = (
            select(
                LLMUsageRecord.model,
                func.sum(LLMUsageRecord.prompt_tokens).label("prompt_tokens"),
                func.sum(LLMUsageRecord.completion_tokens).label("completion_tokens"),
            )
            .where(base_filter)
            .group_by(LLMUsageRecord.model)
        )

        cost_result = await self.session.execute(cost_query)
        total_cost_cents = 0.0

        for model_row in cost_result.all():
            pricing = get_model_pricing(model_row.model or "default")
            prompt_tokens = int(model_row.prompt_tokens or 0)
            completion_tokens = int(model_row.completion_tokens or 0)

            # Calculate cost with full precision
            input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
            output_cost = (completion_tokens / 1_000_000) * pricing["output"]
            total_cost_cents += (input_cost + output_cost) * 100

        return LLMUsageSummary(
            total_requests=total_requests,
            total_tokens=int(row.total_tokens or 0),
            total_prompt_tokens=int(row.total_prompt_tokens or 0),
            total_completion_tokens=int(row.total_completion_tokens or 0),
            total_cost_cents=int(total_cost_cents + 0.5),  # Round at the end
            avg_duration_ms=float(row.avg_duration_ms or 0),
            error_count=error_count,
            error_rate=error_rate,
        )

    async def _get_by_model(self, base_filter) -> list[LLMUsageByModel]:
        """Get usage breakdown by model with dynamically calculated costs."""
        from services.llm_usage_tracker import get_model_pricing

        query = (
            select(
                LLMUsageRecord.model,
                LLMUsageRecord.provider,
                func.count(LLMUsageRecord.id).label("request_count"),
                func.sum(LLMUsageRecord.total_tokens).label("total_tokens"),
                func.sum(LLMUsageRecord.prompt_tokens).label("prompt_tokens"),
                func.sum(LLMUsageRecord.completion_tokens).label("completion_tokens"),
            )
            .where(base_filter)
            .group_by(LLMUsageRecord.model, LLMUsageRecord.provider)
            .order_by(func.sum(LLMUsageRecord.total_tokens).desc())
        )

        result = await self.session.execute(query)
        models = []

        for row in result.all():
            pricing = get_model_pricing(row.model or "default")
            prompt_tokens = int(row.prompt_tokens or 0)
            completion_tokens = int(row.completion_tokens or 0)
            total_tokens = int(row.total_tokens or 0)
            request_count = int(row.request_count or 0)

            # Calculate cost with full precision
            input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
            output_cost = (completion_tokens / 1_000_000) * pricing["output"]
            cost_cents = int((input_cost + output_cost) * 100 + 0.5)

            models.append(
                LLMUsageByModel(
                    model=row.model,
                    provider=row.provider,
                    request_count=request_count,
                    total_tokens=total_tokens,
                    cost_cents=cost_cents,
                    avg_tokens_per_request=(total_tokens / request_count if request_count > 0 else 0),
                )
            )

        return models

    async def _get_by_task(self, base_filter) -> list[LLMUsageByTask]:
        """Get usage breakdown by task type with dynamically calculated costs."""
        from services.llm_usage_tracker import get_model_pricing

        query = (
            select(
                LLMUsageRecord.task_type,
                LLMUsageRecord.model,
                func.count(LLMUsageRecord.id).label("request_count"),
                func.sum(LLMUsageRecord.total_tokens).label("total_tokens"),
                func.sum(LLMUsageRecord.prompt_tokens).label("prompt_tokens"),
                func.sum(LLMUsageRecord.completion_tokens).label("completion_tokens"),
                func.avg(LLMUsageRecord.duration_ms).label("avg_duration_ms"),
            )
            .where(base_filter)
            .group_by(LLMUsageRecord.task_type, LLMUsageRecord.model)
        )

        result = await self.session.execute(query)

        # Aggregate by task_type, calculating costs per model
        task_data: dict = {}
        for row in result.all():
            task_type = row.task_type
            if task_type not in task_data:
                task_data[task_type] = {
                    "request_count": 0,
                    "total_tokens": 0,
                    "cost_cents": 0.0,
                    "duration_sum": 0.0,
                    "duration_count": 0,
                }

            pricing = get_model_pricing(row.model or "default")
            prompt_tokens = int(row.prompt_tokens or 0)
            completion_tokens = int(row.completion_tokens or 0)
            request_count = int(row.request_count or 0)
            input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
            output_cost = (completion_tokens / 1_000_000) * pricing["output"]

            task_data[task_type]["request_count"] += request_count
            task_data[task_type]["total_tokens"] += int(row.total_tokens or 0)
            task_data[task_type]["cost_cents"] += (input_cost + output_cost) * 100
            if row.avg_duration_ms:
                task_data[task_type]["duration_sum"] += float(row.avg_duration_ms) * request_count
                task_data[task_type]["duration_count"] += request_count

        tasks = []
        for task_type, data in task_data.items():
            avg_duration = data["duration_sum"] / data["duration_count"] if data["duration_count"] > 0 else 0
            tasks.append(
                LLMUsageByTask(
                    task_type=task_type,
                    request_count=data["request_count"],
                    total_tokens=data["total_tokens"],
                    cost_cents=int(data["cost_cents"] + 0.5),
                    avg_duration_ms=avg_duration,
                )
            )

        return sorted(tasks, key=lambda x: x.total_tokens, reverse=True)

    async def _get_by_category(self, base_filter) -> list[LLMUsageByCategory]:
        """Get usage breakdown by category with dynamically calculated costs."""
        from services.llm_usage_tracker import get_model_pricing

        query = (
            select(
                LLMUsageRecord.category_id,
                Category.name.label("category_name"),
                LLMUsageRecord.model,
                func.count(LLMUsageRecord.id).label("request_count"),
                func.sum(LLMUsageRecord.total_tokens).label("total_tokens"),
                func.sum(LLMUsageRecord.prompt_tokens).label("prompt_tokens"),
                func.sum(LLMUsageRecord.completion_tokens).label("completion_tokens"),
            )
            .outerjoin(Category, LLMUsageRecord.category_id == Category.id)
            .where(base_filter)
            .group_by(LLMUsageRecord.category_id, Category.name, LLMUsageRecord.model)
        )

        result = await self.session.execute(query)

        # Aggregate by category, calculating costs per model
        cat_data: dict = {}
        for row in result.all():
            key = (row.category_id, row.category_name)
            if key not in cat_data:
                cat_data[key] = {"request_count": 0, "total_tokens": 0, "cost_cents": 0.0}

            pricing = get_model_pricing(row.model or "default")
            prompt_tokens = int(row.prompt_tokens or 0)
            completion_tokens = int(row.completion_tokens or 0)
            input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
            output_cost = (completion_tokens / 1_000_000) * pricing["output"]

            cat_data[key]["request_count"] += int(row.request_count or 0)
            cat_data[key]["total_tokens"] += int(row.total_tokens or 0)
            cat_data[key]["cost_cents"] += (input_cost + output_cost) * 100

        categories = [
            LLMUsageByCategory(
                category_id=cat_id,
                category_name=cat_name,
                request_count=data["request_count"],
                total_tokens=data["total_tokens"],
                cost_cents=int(data["cost_cents"] + 0.5),
            )
            for (cat_id, cat_name), data in cat_data.items()
        ]

        return sorted(categories, key=lambda x: x.total_tokens, reverse=True)[:20]

    async def _get_by_user(self, base_filter) -> list[LLMUsageByUser]:
        """Get usage breakdown by user with dynamically calculated costs."""
        from app.models.user import User
        from app.models.user_api_credentials import ApiCredentialType, UserApiCredentials
        from services.llm_usage_tracker import get_model_pricing

        # Get usage grouped by user and model for cost calculation
        query = (
            select(
                LLMUsageRecord.user_id,
                User.email.label("user_email"),
                User.full_name.label("user_name"),
                LLMUsageRecord.model,
                func.count(LLMUsageRecord.id).label("request_count"),
                func.sum(LLMUsageRecord.total_tokens).label("total_tokens"),
                func.sum(LLMUsageRecord.prompt_tokens).label("prompt_tokens"),
                func.sum(LLMUsageRecord.completion_tokens).label("completion_tokens"),
            )
            .outerjoin(User, LLMUsageRecord.user_id == User.id)
            .where(base_filter)
            .group_by(LLMUsageRecord.user_id, User.email, User.full_name, LLMUsageRecord.model)
        )

        result = await self.session.execute(query)

        # Aggregate by user, calculating costs per model
        user_data: dict = {}
        for row in result.all():
            key = (row.user_id, row.user_email, row.user_name)
            if key not in user_data:
                user_data[key] = {
                    "request_count": 0,
                    "total_tokens": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "cost_cents": 0.0,
                    "models_used": set(),
                }

            pricing = get_model_pricing(row.model or "default")
            prompt_tokens = int(row.prompt_tokens or 0)
            completion_tokens = int(row.completion_tokens or 0)
            input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
            output_cost = (completion_tokens / 1_000_000) * pricing["output"]

            user_data[key]["request_count"] += int(row.request_count or 0)
            user_data[key]["total_tokens"] += int(row.total_tokens or 0)
            user_data[key]["prompt_tokens"] += prompt_tokens
            user_data[key]["completion_tokens"] += completion_tokens
            user_data[key]["cost_cents"] += (input_cost + output_cost) * 100
            if row.model:
                user_data[key]["models_used"].add(row.model)

        # Get users with configured credentials
        user_ids = [key[0] for key in user_data if key[0]]
        users_with_creds: set[UUID] = set()

        if user_ids:
            cred_query = (
                select(UserApiCredentials.user_id)
                .where(
                    and_(
                        UserApiCredentials.user_id.in_(user_ids),
                        UserApiCredentials.is_active,
                        UserApiCredentials.credential_type == ApiCredentialType.AZURE_OPENAI,
                    )
                )
                .distinct()
            )
            cred_result = await self.session.execute(cred_query)
            users_with_creds = {row[0] for row in cred_result.all()}

        users = [
            LLMUsageByUser(
                user_id=user_id,
                user_email=email,
                user_name=name,
                request_count=data["request_count"],
                total_tokens=data["total_tokens"],
                prompt_tokens=data["prompt_tokens"],
                completion_tokens=data["completion_tokens"],
                cost_cents=int(data["cost_cents"] + 0.5),
                models_used=list(data["models_used"]),
                has_credentials=user_id in users_with_creds if user_id else False,
            )
            for (user_id, email, name), data in user_data.items()
        ]

        return sorted(users, key=lambda x: x.cost_cents, reverse=True)[:20]

    async def _get_daily_trend(self, start_date: datetime, end_date: datetime, base_filter) -> list[LLMUsageTrend]:
        """Get daily usage trend with dynamically calculated costs."""
        from services.llm_usage_tracker import get_model_pricing

        day_trunc = func.date_trunc("day", LLMUsageRecord.created_at)
        query = (
            select(
                day_trunc.label("day"),
                LLMUsageRecord.model,
                func.count(LLMUsageRecord.id).label("request_count"),
                func.sum(LLMUsageRecord.total_tokens).label("total_tokens"),
                func.sum(LLMUsageRecord.prompt_tokens).label("prompt_tokens"),
                func.sum(LLMUsageRecord.completion_tokens).label("completion_tokens"),
                func.sum(case((LLMUsageRecord.is_error, 1), else_=0)).label("error_count"),
            )
            .where(base_filter)
            .group_by(day_trunc, LLMUsageRecord.model)
            .order_by(day_trunc)
        )

        result = await self.session.execute(query)

        # Aggregate by day, calculating costs per model
        day_data: dict = {}
        for row in result.all():
            day = row.day.date() if row.day else date.today()
            if day not in day_data:
                day_data[day] = {"request_count": 0, "total_tokens": 0, "cost_cents": 0.0, "error_count": 0}

            pricing = get_model_pricing(row.model or "default")
            prompt_tokens = int(row.prompt_tokens or 0)
            completion_tokens = int(row.completion_tokens or 0)
            input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
            output_cost = (completion_tokens / 1_000_000) * pricing["output"]

            day_data[day]["request_count"] += int(row.request_count or 0)
            day_data[day]["total_tokens"] += int(row.total_tokens or 0)
            day_data[day]["cost_cents"] += (input_cost + output_cost) * 100
            day_data[day]["error_count"] += int(row.error_count or 0)

        return [
            LLMUsageTrend(
                day=day,
                request_count=data["request_count"],
                total_tokens=data["total_tokens"],
                cost_cents=int(data["cost_cents"] + 0.5),
                error_count=data["error_count"],
            )
            for day, data in sorted(day_data.items())
        ]

    async def _get_top_consumers(self, base_filter, limit: int = 10) -> list[LLMUsageTopConsumer]:
        """Get top token-consuming tasks with dynamically calculated costs."""
        from services.llm_usage_tracker import get_model_pricing

        query = (
            select(
                LLMUsageRecord.task_name,
                LLMUsageRecord.task_type,
                LLMUsageRecord.model,
                func.count(LLMUsageRecord.id).label("request_count"),
                func.sum(LLMUsageRecord.total_tokens).label("total_tokens"),
                func.sum(LLMUsageRecord.prompt_tokens).label("prompt_tokens"),
                func.sum(LLMUsageRecord.completion_tokens).label("completion_tokens"),
            )
            .where(and_(base_filter, LLMUsageRecord.task_name.isnot(None)))
            .group_by(LLMUsageRecord.task_name, LLMUsageRecord.task_type, LLMUsageRecord.model)
        )

        result = await self.session.execute(query)

        # Aggregate by task, calculating costs per model
        task_data: dict = {}
        for row in result.all():
            key = (row.task_name, row.task_type)
            if key not in task_data:
                task_data[key] = {"request_count": 0, "total_tokens": 0, "cost_cents": 0.0}

            pricing = get_model_pricing(row.model or "default")
            prompt_tokens = int(row.prompt_tokens or 0)
            completion_tokens = int(row.completion_tokens or 0)
            input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
            output_cost = (completion_tokens / 1_000_000) * pricing["output"]

            task_data[key]["request_count"] += int(row.request_count or 0)
            task_data[key]["total_tokens"] += int(row.total_tokens or 0)
            task_data[key]["cost_cents"] += (input_cost + output_cost) * 100

        consumers = [
            LLMUsageTopConsumer(
                task_name=task_name or "Unknown",
                task_type=task_type,
                request_count=data["request_count"],
                total_tokens=data["total_tokens"],
                cost_cents=int(data["cost_cents"] + 0.5),
            )
            for (task_name, task_type), data in task_data.items()
        ]

        return sorted(consumers, key=lambda x: x.total_tokens, reverse=True)[:limit]

    async def get_cost_projection(self) -> LLMCostProjection:
        """Get cost projection for current month."""
        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        days_elapsed = (now - month_start).days + 1
        days_in_month = 30  # Approximation

        # Get current month cost
        query = select(func.coalesce(func.sum(LLMUsageRecord.estimated_cost_cents), 0)).where(
            LLMUsageRecord.created_at >= month_start
        )

        result = await self.session.execute(query)
        current_cost = int(result.scalar() or 0)

        daily_avg = current_cost / days_elapsed if days_elapsed > 0 else 0
        projected = int(daily_avg * days_in_month)

        # Check if any budget has warnings
        from app.models.llm_budget import BudgetType, LLMBudgetConfig

        budget_query = select(LLMBudgetConfig).where(
            and_(
                LLMBudgetConfig.is_active,
                LLMBudgetConfig.budget_type == BudgetType.GLOBAL,
            )
        )
        budget_result = await self.session.execute(budget_query)
        global_budget = budget_result.scalar_one_or_none()

        budget_limit = None
        budget_warning = False
        if global_budget:
            budget_limit = global_budget.monthly_limit_cents
            usage_percent = current_cost / budget_limit * 100 if budget_limit > 0 else 0
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
        query = select(
            func.count(LLMUsageRecord.id).label("request_count"),
            func.sum(LLMUsageRecord.total_tokens).label("total_tokens"),
            func.sum(LLMUsageRecord.estimated_cost_cents).label("cost_cents"),
            func.min(LLMUsageRecord.created_at).label("first_request"),
            func.max(LLMUsageRecord.created_at).label("last_request"),
        ).where(LLMUsageRecord.document_id == document_id)

        result = await self.session.execute(query)
        row = result.one()

        if row.request_count == 0:
            return None

        return {
            "document_id": str(document_id),
            "request_count": int(row.request_count or 0),
            "total_tokens": int(row.total_tokens or 0),
            "cost_cents": int(row.cost_cents or 0),
            "first_request": row.first_request.isoformat() if row.first_request else None,
            "last_request": row.last_request.isoformat() if row.last_request else None,
        }
