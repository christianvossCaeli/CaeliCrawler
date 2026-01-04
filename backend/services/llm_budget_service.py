"""
LLM Budget Management Service.

Provides budget management, status checking, and alert functionality
for LLM API usage.
"""

from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_budget import (
    BudgetType,
    LimitIncreaseRequestStatus,
    LLMBudgetAlert,
    LLMBudgetConfig,
    LLMBudgetLimitRequest,
)
from app.models.llm_usage import LLMUsageRecord
from app.models.user import User
from app.schemas.llm_budget import (
    AdminLimitRequestAction,
    BudgetStatusListResponse,
    BudgetStatusResponse,
    LimitIncreaseRequestCreate,
    LimitIncreaseRequestListResponse,
    LimitIncreaseRequestResponse,
    LLMBudgetConfigCreate,
    LLMBudgetConfigResponse,
    LLMBudgetConfigUpdate,
    UserBudgetStatusResponse,
)

logger = structlog.get_logger(__name__)


class LLMBudgetService:
    """Service for managing LLM budgets."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_budgets(self, active_only: bool = False) -> list[LLMBudgetConfigResponse]:
        """List all budget configurations."""
        query = select(LLMBudgetConfig).order_by(LLMBudgetConfig.created_at.desc())

        if active_only:
            query = query.where(LLMBudgetConfig.is_active)

        result = await self.session.execute(query)
        budgets = result.scalars().all()

        return [LLMBudgetConfigResponse.model_validate(b) for b in budgets]

    async def get_budget(self, budget_id: UUID) -> LLMBudgetConfigResponse | None:
        """Get a specific budget configuration."""
        result = await self.session.execute(select(LLMBudgetConfig).where(LLMBudgetConfig.id == budget_id))
        budget = result.scalar_one_or_none()

        if not budget:
            return None

        return LLMBudgetConfigResponse.model_validate(budget)

    async def create_budget(self, data: LLMBudgetConfigCreate) -> LLMBudgetConfigResponse:
        """Create a new budget configuration."""
        budget = LLMBudgetConfig(
            name=data.name,
            budget_type=data.budget_type,
            reference_id=data.reference_id,
            reference_value=data.reference_value,
            monthly_limit_cents=data.monthly_limit_cents,
            warning_threshold_percent=data.warning_threshold_percent,
            critical_threshold_percent=data.critical_threshold_percent,
            alert_emails=data.alert_emails,
            description=data.description,
            is_active=data.is_active,
        )

        self.session.add(budget)
        await self.session.commit()
        await self.session.refresh(budget)

        logger.info(
            "Budget created",
            budget_id=str(budget.id),
            name=budget.name,
            limit_cents=budget.monthly_limit_cents,
        )

        return LLMBudgetConfigResponse.model_validate(budget)

    async def update_budget(self, budget_id: UUID, data: LLMBudgetConfigUpdate) -> LLMBudgetConfigResponse | None:
        """Update an existing budget configuration."""
        result = await self.session.execute(select(LLMBudgetConfig).where(LLMBudgetConfig.id == budget_id))
        budget = result.scalar_one_or_none()

        if not budget:
            return None

        # Update fields if provided
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(budget, field, value)

        await self.session.commit()
        await self.session.refresh(budget)

        logger.info("Budget updated", budget_id=str(budget_id))

        return LLMBudgetConfigResponse.model_validate(budget)

    async def delete_budget(self, budget_id: UUID) -> bool:
        """Delete a budget configuration."""
        result = await self.session.execute(select(LLMBudgetConfig).where(LLMBudgetConfig.id == budget_id))
        budget = result.scalar_one_or_none()

        if not budget:
            return False

        await self.session.delete(budget)
        await self.session.commit()

        logger.info("Budget deleted", budget_id=str(budget_id))

        return True

    async def get_budget_status(self) -> BudgetStatusListResponse:
        """Get current status of all active budgets."""
        # Get all active budgets
        result = await self.session.execute(select(LLMBudgetConfig).where(LLMBudgetConfig.is_active))
        budgets = result.scalars().all()

        # Get current month usage
        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        days_elapsed = (now - month_start).days + 1
        days_in_month = 30

        statuses = []
        any_warning = False
        any_critical = False
        any_blocked = False

        for budget in budgets:
            # Build query based on budget type
            usage_query = select(func.coalesce(func.sum(LLMUsageRecord.estimated_cost_cents), 0)).where(
                LLMUsageRecord.created_at >= month_start
            )

            if budget.budget_type == BudgetType.CATEGORY and budget.reference_id:
                usage_query = usage_query.where(LLMUsageRecord.category_id == budget.reference_id)
            elif budget.budget_type == BudgetType.TASK_TYPE and budget.reference_value:
                usage_query = usage_query.where(LLMUsageRecord.task_type == budget.reference_value)
            elif budget.budget_type == BudgetType.MODEL and budget.reference_value:
                usage_query = usage_query.where(LLMUsageRecord.model == budget.reference_value)
            # GLOBAL type has no additional filter

            result = await self.session.execute(usage_query)
            current_usage = result.scalar() or 0

            usage_percent = current_usage / budget.monthly_limit_cents * 100 if budget.monthly_limit_cents > 0 else 0

            is_warning = usage_percent >= budget.warning_threshold_percent
            is_critical = usage_percent >= budget.critical_threshold_percent
            is_blocked = usage_percent >= 100 and budget.blocks_on_limit

            if is_warning:
                any_warning = True
            if is_critical:
                any_critical = True
            if is_blocked:
                any_blocked = True

            # Calculate projection
            daily_avg = current_usage / days_elapsed if days_elapsed > 0 else 0
            projected = int(daily_avg * days_in_month)

            statuses.append(
                BudgetStatusResponse(
                    budget_id=budget.id,
                    budget_name=budget.name,
                    budget_type=budget.budget_type,
                    monthly_limit_cents=budget.monthly_limit_cents,
                    current_usage_cents=current_usage,
                    usage_percent=usage_percent,
                    warning_threshold_percent=budget.warning_threshold_percent,
                    critical_threshold_percent=budget.critical_threshold_percent,
                    is_warning=is_warning,
                    is_critical=is_critical,
                    is_blocked=is_blocked,
                    blocks_on_limit=budget.blocks_on_limit,
                    projected_month_end_cents=projected,
                )
            )

        return BudgetStatusListResponse(
            budgets=statuses,
            any_warning=any_warning,
            any_critical=any_critical,
            any_blocked=any_blocked,
        )

    async def check_and_send_alerts(self) -> list[dict]:
        """
        Check all budgets and send alerts if thresholds are exceeded.

        Returns list of alerts that were triggered.
        """
        status = await self.get_budget_status()
        triggered_alerts = []

        for budget_status in status.budgets:
            if not budget_status.is_warning and not budget_status.is_critical:
                continue

            # Get the budget config for alert settings
            result = await self.session.execute(
                select(LLMBudgetConfig).where(LLMBudgetConfig.id == budget_status.budget_id)
            )
            budget = result.scalar_one()

            # Determine alert type
            alert_type = "critical" if budget_status.is_critical else "warning"

            # Check if we already sent this type of alert recently (within 24 hours)
            if alert_type == "warning" and budget.last_warning_sent_at:
                hours_since = (datetime.now(UTC) - budget.last_warning_sent_at).total_seconds() / 3600
                if hours_since < 24:
                    continue
            elif alert_type == "critical" and budget.last_critical_sent_at:
                hours_since = (datetime.now(UTC) - budget.last_critical_sent_at).total_seconds() / 3600
                if hours_since < 24:
                    continue

            # Create alert record
            alert = LLMBudgetAlert(
                budget_id=budget.id,
                alert_type=alert_type,
                threshold_percent=(
                    budget.critical_threshold_percent if alert_type == "critical" else budget.warning_threshold_percent
                ),
                current_usage_cents=budget_status.current_usage_cents,
                budget_limit_cents=budget_status.monthly_limit_cents,
                usage_percent=budget_status.usage_percent,
                recipients=budget.alert_emails,
            )

            # Try to send email
            email_sent = False
            email_error = None
            if budget.alert_emails:
                try:
                    await self._send_budget_alert_email(
                        budget=budget,
                        alert_type=alert_type,
                        usage_percent=budget_status.usage_percent,
                        current_usage_cents=budget_status.current_usage_cents,
                    )
                    email_sent = True
                except Exception as e:
                    email_error = str(e)
                    logger.error(
                        "Failed to send budget alert email",
                        error=str(e),
                        budget_id=str(budget.id),
                    )

            alert.email_sent = email_sent
            alert.email_error = email_error

            self.session.add(alert)

            # Update last sent timestamp
            if alert_type == "warning":
                budget.last_warning_sent_at = datetime.now(UTC)
            else:
                budget.last_critical_sent_at = datetime.now(UTC)

            triggered_alerts.append(
                {
                    "budget_id": str(budget.id),
                    "budget_name": budget.name,
                    "alert_type": alert_type,
                    "usage_percent": budget_status.usage_percent,
                    "email_sent": email_sent,
                }
            )

            logger.warning(
                "Budget alert triggered",
                budget_id=str(budget.id),
                budget_name=budget.name,
                alert_type=alert_type,
                usage_percent=budget_status.usage_percent,
            )

        await self.session.commit()
        return triggered_alerts

    async def _send_budget_alert_email(
        self,
        budget: LLMBudgetConfig,
        alert_type: str,
        usage_percent: float,
        current_usage_cents: int,
    ) -> None:
        """Send budget alert email using SMTP."""
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        import aiosmtplib

        from app.config import settings

        if not settings.smtp_host:
            logger.warning(
                "SMTP not configured, budget alert email not sent",
                budget_name=budget.name,
                alert_type=alert_type,
            )
            return

        subject = f"[{'KRITISCH' if alert_type == 'critical' else 'Warnung'}] LLM Budget-Alarm: {budget.name}"

        alert_color = "#dc3545" if alert_type == "critical" else "#ffc107"
        alert_label = "KRITISCH" if alert_type == "critical" else "Warnung"

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: #113634;
            color: white;
            padding: 20px;
            border-radius: 8px 8px 0 0;
        }}
        .content {{
            background: #f9f9f9;
            padding: 20px;
            border: 1px solid #e0e0e0;
            border-top: none;
        }}
        .alert-badge {{
            display: inline-block;
            background: {alert_color};
            color: white;
            padding: 6px 16px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 15px;
        }}
        .stats {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }}
        .stat-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }}
        .stat-row:last-child {{
            border-bottom: none;
        }}
        .stat-label {{
            color: #666;
        }}
        .stat-value {{
            font-weight: bold;
        }}
        .progress-bar {{
            background: #e0e0e0;
            border-radius: 4px;
            height: 20px;
            margin: 15px 0;
            overflow: hidden;
        }}
        .progress-fill {{
            background: {alert_color};
            height: 100%;
            width: {min(usage_percent, 100)}%;
            transition: width 0.3s;
        }}
        .footer {{
            background: #f0f0f0;
            padding: 15px 20px;
            border-radius: 0 0 8px 8px;
            font-size: 12px;
            color: #666;
            border: 1px solid #e0e0e0;
            border-top: none;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1 style="margin: 0; font-size: 20px;">LLM Budget-Alarm</h1>
    </div>
    <div class="content">
        <span class="alert-badge">{alert_label}</span>
        <p>Das Budget <strong>{budget.name}</strong> hat die {alert_label.lower()}-Schwelle überschritten.</p>

        <div class="stats">
            <div class="stat-row">
                <span class="stat-label">Aktueller Verbrauch:</span>
                <span class="stat-value">${current_usage_cents / 100:.2f}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Monatliches Limit:</span>
                <span class="stat-value">${budget.monthly_limit_cents / 100:.2f}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Auslastung:</span>
                <span class="stat-value">{usage_percent:.1f}%</span>
            </div>
        </div>

        <div class="progress-bar">
            <div class="progress-fill"></div>
        </div>

        <p style="font-size: 14px; color: #666;">
            Bitte überprüfen Sie die LLM-Nutzung und passen Sie bei Bedarf das Budget an.
        </p>
    </div>
    <div class="footer">
        Diese Nachricht wurde automatisch von CaeliCrawler gesendet.
    </div>
</body>
</html>
"""

        plain_body = f"""
LLM Budget-Alarm

Budget: {budget.name}
Status: {alert_label}

Aktueller Verbrauch: ${current_usage_cents / 100:.2f}
Monatliches Limit: ${budget.monthly_limit_cents / 100:.2f}
Auslastung: {usage_percent:.1f}%

Bitte überprüfen Sie die LLM-Nutzung und passen Sie bei Bedarf das Budget an.

---
Diese Nachricht wurde automatisch von CaeliCrawler gesendet.
"""

        for email in budget.alert_emails:
            try:
                message = MIMEMultipart("alternative")
                message["Subject"] = subject
                message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
                message["To"] = email

                message.attach(MIMEText(plain_body, "plain", "utf-8"))
                message.attach(MIMEText(html_body, "html", "utf-8"))

                await aiosmtplib.send(
                    message,
                    hostname=settings.smtp_host,
                    port=settings.smtp_port,
                    username=settings.smtp_username or None,
                    password=settings.smtp_password or None,
                    use_tls=settings.smtp_use_tls,
                    start_tls=settings.smtp_use_tls and not getattr(settings, "smtp_use_ssl", False),
                    timeout=getattr(settings, "smtp_timeout", 30),
                )

                logger.info(
                    "Budget alert email sent",
                    budget_name=budget.name,
                    recipient=email,
                    alert_type=alert_type,
                )

            except Exception as e:
                logger.error(
                    "Failed to send budget alert email",
                    error=str(e),
                    recipient=email,
                    budget_name=budget.name,
                )
                raise

    async def get_alert_history(self, budget_id: UUID | None = None, limit: int = 50) -> list[dict]:
        """Get alert history."""
        query = select(LLMBudgetAlert).order_by(LLMBudgetAlert.created_at.desc()).limit(limit)

        if budget_id:
            query = query.where(LLMBudgetAlert.budget_id == budget_id)

        result = await self.session.execute(query)
        alerts = result.scalars().all()

        return [
            {
                "id": str(alert.id),
                "budget_id": str(alert.budget_id),
                "alert_type": alert.alert_type,
                "threshold_percent": alert.threshold_percent,
                "current_usage_cents": alert.current_usage_cents,
                "budget_limit_cents": alert.budget_limit_cents,
                "usage_percent": alert.usage_percent,
                "email_sent": alert.email_sent,
                "created_at": alert.created_at.isoformat(),
            }
            for alert in alerts
        ]

    # === User Budget Methods ===

    async def get_user_budget(self, user_id: UUID) -> LLMBudgetConfig | None:
        """Get the budget configuration for a specific user."""
        result = await self.session.execute(
            select(LLMBudgetConfig).where(
                LLMBudgetConfig.budget_type == BudgetType.USER,
                LLMBudgetConfig.reference_id == user_id,
                LLMBudgetConfig.is_active,
            )
        )
        return result.scalar_one_or_none()

    async def get_user_budget_status(self, user_id: UUID) -> UserBudgetStatusResponse | None:
        """Get current budget status for a user."""
        budget = await self.get_user_budget(user_id)
        if not budget:
            return None

        # Get current month usage for this user
        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        usage_query = select(func.coalesce(func.sum(LLMUsageRecord.estimated_cost_cents), 0)).where(
            LLMUsageRecord.created_at >= month_start,
            LLMUsageRecord.user_id == user_id,
        )

        result = await self.session.execute(usage_query)
        current_usage = result.scalar() or 0

        usage_percent = current_usage / budget.monthly_limit_cents * 100 if budget.monthly_limit_cents > 0 else 0

        return UserBudgetStatusResponse(
            budget_id=budget.id,
            monthly_limit_cents=budget.monthly_limit_cents,
            current_usage_cents=current_usage,
            usage_percent=usage_percent,
            is_warning=usage_percent >= budget.warning_threshold_percent,
            is_critical=usage_percent >= budget.critical_threshold_percent,
            is_blocked=usage_percent >= 100,
        )

    async def check_user_can_use_llm(self, user_id: UUID) -> tuple[bool, str | None]:
        """
        Check if a user can use LLM functions.

        Checks both user-specific budgets and any blocking budgets (GLOBAL, etc.)

        Returns:
            tuple: (can_use: bool, reason: str | None)
                   If can_use is False, reason contains the blocking message.
        """
        # Check user-specific budget first
        user_status = await self.get_user_budget_status(user_id)

        if user_status is not None and user_status.is_blocked:
            return False, (
                f"Your monthly LLM budget is exhausted. "
                f"Used: ${user_status.current_usage_cents / 100:.2f} / "
                f"${user_status.monthly_limit_cents / 100:.2f}. "
                f"Please request a limit increase or wait until next month."
            )

        # Check all blocking budgets (GLOBAL, CATEGORY, etc.)
        budget_status = await self.get_budget_status()
        for budget in budget_status.budgets:
            if budget.is_blocked:
                return False, (
                    f"LLM budget '{budget.budget_name}' is exhausted. "
                    f"Used: ${budget.current_usage_cents / 100:.2f} / "
                    f"${budget.monthly_limit_cents / 100:.2f}. "
                    f"Please contact an administrator."
                )

        return True, None

    async def update_user_budget_limit(self, user_id: UUID, new_limit_cents: int) -> UserBudgetStatusResponse:
        """
        Update a user's budget limit directly.

        Used by admins for self-service limit updates.

        Args:
            user_id: The user's ID
            new_limit_cents: New monthly limit in USD cents

        Returns:
            Updated budget status

        Raises:
            ValueError: If no budget exists for the user
        """
        budget = await self.get_user_budget(user_id)

        if not budget:
            raise ValueError(
                "No budget configured for this user. Please contact an administrator to set up a budget first."
            )

        # Update the limit
        budget.monthly_limit_cents = new_limit_cents

        # Return updated status
        return await self.get_user_budget_status(user_id)

    # === Limit Increase Request Methods ===

    async def create_limit_request(
        self, user_id: UUID, data: LimitIncreaseRequestCreate
    ) -> LimitIncreaseRequestResponse:
        """Create a new limit increase request."""
        budget = await self.get_user_budget(user_id)

        if not budget:
            raise ValueError("No budget configured for this user")

        if data.requested_limit_cents <= budget.monthly_limit_cents:
            raise ValueError("Requested limit must be greater than current limit")

        # Check for pending request
        existing = await self.session.execute(
            select(LLMBudgetLimitRequest).where(
                LLMBudgetLimitRequest.user_id == user_id,
                LLMBudgetLimitRequest.status == LimitIncreaseRequestStatus.PENDING,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("You already have a pending limit increase request")

        request = LLMBudgetLimitRequest(
            user_id=user_id,
            budget_id=budget.id,
            requested_limit_cents=data.requested_limit_cents,
            current_limit_cents=budget.monthly_limit_cents,
            reason=data.reason,
            status=LimitIncreaseRequestStatus.PENDING,
        )

        self.session.add(request)
        await self.session.flush()

        logger.info(
            "Limit increase request created",
            request_id=str(request.id),
            user_id=str(user_id),
            requested_cents=data.requested_limit_cents,
        )

        return LimitIncreaseRequestResponse.model_validate(request)

    async def get_user_limit_requests(self, user_id: UUID) -> list[LimitIncreaseRequestResponse]:
        """Get all limit requests for a specific user."""
        result = await self.session.execute(
            select(LLMBudgetLimitRequest)
            .where(LLMBudgetLimitRequest.user_id == user_id)
            .order_by(LLMBudgetLimitRequest.created_at.desc())
        )
        requests = result.scalars().all()

        return [LimitIncreaseRequestResponse.model_validate(r) for r in requests]

    async def list_limit_requests(
        self,
        status: LimitIncreaseRequestStatus | None = None,
        limit: int = 50,
    ) -> LimitIncreaseRequestListResponse:
        """List all limit increase requests (admin view)."""
        query = (
            select(LLMBudgetLimitRequest, User.email)
            .join(User, LLMBudgetLimitRequest.user_id == User.id)
            .order_by(LLMBudgetLimitRequest.created_at.desc())
            .limit(limit)
        )

        if status:
            query = query.where(LLMBudgetLimitRequest.status == status)

        result = await self.session.execute(query)
        rows = result.all()

        # Count pending
        pending_count_result = await self.session.execute(
            select(func.count(LLMBudgetLimitRequest.id)).where(
                LLMBudgetLimitRequest.status == LimitIncreaseRequestStatus.PENDING
            )
        )
        pending_count = pending_count_result.scalar() or 0

        # Total count
        total_result = await self.session.execute(select(func.count(LLMBudgetLimitRequest.id)))
        total = total_result.scalar() or 0

        requests = []
        for request, user_email in rows:
            response = LimitIncreaseRequestResponse.model_validate(request)
            response.user_email = user_email
            requests.append(response)

        return LimitIncreaseRequestListResponse(
            requests=requests,
            total=total,
            pending_count=pending_count,
        )

    async def get_limit_request(self, request_id: UUID) -> LimitIncreaseRequestResponse | None:
        """Get a specific limit request."""
        result = await self.session.execute(
            select(LLMBudgetLimitRequest, User.email)
            .join(User, LLMBudgetLimitRequest.user_id == User.id)
            .where(LLMBudgetLimitRequest.id == request_id)
        )
        row = result.one_or_none()

        if not row:
            return None

        request, user_email = row
        response = LimitIncreaseRequestResponse.model_validate(request)
        response.user_email = user_email
        return response

    async def approve_limit_request(
        self,
        request_id: UUID,
        admin_id: UUID,
        action: AdminLimitRequestAction | None = None,
    ) -> LimitIncreaseRequestResponse:
        """Approve a limit increase request."""
        result = await self.session.execute(select(LLMBudgetLimitRequest).where(LLMBudgetLimitRequest.id == request_id))
        request = result.scalar_one_or_none()

        if not request:
            raise ValueError("Request not found")

        if request.status != LimitIncreaseRequestStatus.PENDING:
            raise ValueError("Request is not pending")

        # Update the budget
        budget_result = await self.session.execute(
            select(LLMBudgetConfig).where(LLMBudgetConfig.id == request.budget_id)
        )
        budget = budget_result.scalar_one_or_none()

        if budget:
            budget.monthly_limit_cents = request.requested_limit_cents
            budget.updated_at = datetime.now(UTC)

        # Update the request
        request.status = LimitIncreaseRequestStatus.APPROVED
        request.reviewed_by = admin_id
        request.reviewed_at = datetime.now(UTC)
        if action and action.notes:
            request.admin_notes = action.notes

        await self.session.flush()

        logger.info(
            "Limit increase request approved",
            request_id=str(request_id),
            admin_id=str(admin_id),
            new_limit_cents=request.requested_limit_cents,
        )

        return LimitIncreaseRequestResponse.model_validate(request)

    async def deny_limit_request(
        self,
        request_id: UUID,
        admin_id: UUID,
        action: AdminLimitRequestAction | None = None,
    ) -> LimitIncreaseRequestResponse:
        """Deny a limit increase request."""
        result = await self.session.execute(select(LLMBudgetLimitRequest).where(LLMBudgetLimitRequest.id == request_id))
        request = result.scalar_one_or_none()

        if not request:
            raise ValueError("Request not found")

        if request.status != LimitIncreaseRequestStatus.PENDING:
            raise ValueError("Request is not pending")

        # Update the request
        request.status = LimitIncreaseRequestStatus.DENIED
        request.reviewed_by = admin_id
        request.reviewed_at = datetime.now(UTC)
        if action and action.notes:
            request.admin_notes = action.notes

        await self.session.flush()

        logger.info(
            "Limit increase request denied",
            request_id=str(request_id),
            admin_id=str(admin_id),
        )

        return LimitIncreaseRequestResponse.model_validate(request)
