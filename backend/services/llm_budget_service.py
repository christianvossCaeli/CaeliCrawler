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

from app.models.llm_budget import BudgetType, LLMBudgetAlert, LLMBudgetConfig
from app.models.llm_usage import LLMUsageRecord
from app.schemas.llm_budget import (
    BudgetStatusListResponse,
    BudgetStatusResponse,
    LLMBudgetConfigCreate,
    LLMBudgetConfigResponse,
    LLMBudgetConfigUpdate,
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
        result = await self.session.execute(
            select(LLMBudgetConfig).where(LLMBudgetConfig.id == budget_id)
        )
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

    async def update_budget(
        self, budget_id: UUID, data: LLMBudgetConfigUpdate
    ) -> LLMBudgetConfigResponse | None:
        """Update an existing budget configuration."""
        result = await self.session.execute(
            select(LLMBudgetConfig).where(LLMBudgetConfig.id == budget_id)
        )
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
        result = await self.session.execute(
            select(LLMBudgetConfig).where(LLMBudgetConfig.id == budget_id)
        )
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
        result = await self.session.execute(
            select(LLMBudgetConfig).where(LLMBudgetConfig.is_active)
        )
        budgets = result.scalars().all()

        # Get current month usage
        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        days_elapsed = (now - month_start).days + 1
        days_in_month = 30

        statuses = []
        any_warning = False
        any_critical = False

        for budget in budgets:
            # Build query based on budget type
            usage_query = select(
                func.coalesce(func.sum(LLMUsageRecord.estimated_cost_cents), 0)
            ).where(LLMUsageRecord.created_at >= month_start)

            if budget.budget_type == BudgetType.CATEGORY and budget.reference_id:
                usage_query = usage_query.where(
                    LLMUsageRecord.category_id == budget.reference_id
                )
            elif budget.budget_type == BudgetType.TASK_TYPE and budget.reference_value:
                usage_query = usage_query.where(
                    LLMUsageRecord.task_type == budget.reference_value
                )
            elif budget.budget_type == BudgetType.MODEL and budget.reference_value:
                usage_query = usage_query.where(
                    LLMUsageRecord.model == budget.reference_value
                )
            # GLOBAL type has no additional filter

            result = await self.session.execute(usage_query)
            current_usage = result.scalar() or 0

            usage_percent = (
                current_usage / budget.monthly_limit_cents * 100
                if budget.monthly_limit_cents > 0
                else 0
            )

            is_warning = usage_percent >= budget.warning_threshold_percent
            is_critical = usage_percent >= budget.critical_threshold_percent

            if is_warning:
                any_warning = True
            if is_critical:
                any_critical = True

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
                    projected_month_end_cents=projected,
                )
            )

        return BudgetStatusListResponse(
            budgets=statuses,
            any_warning=any_warning,
            any_critical=any_critical,
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
                select(LLMBudgetConfig).where(
                    LLMBudgetConfig.id == budget_status.budget_id
                )
            )
            budget = result.scalar_one()

            # Determine alert type
            alert_type = "critical" if budget_status.is_critical else "warning"

            # Check if we already sent this type of alert recently (within 24 hours)
            if alert_type == "warning" and budget.last_warning_sent_at:
                hours_since = (
                    datetime.now(UTC) - budget.last_warning_sent_at
                ).total_seconds() / 3600
                if hours_since < 24:
                    continue
            elif alert_type == "critical" and budget.last_critical_sent_at:
                hours_since = (
                    datetime.now(UTC) - budget.last_critical_sent_at
                ).total_seconds() / 3600
                if hours_since < 24:
                    continue

            # Create alert record
            alert = LLMBudgetAlert(
                budget_id=budget.id,
                alert_type=alert_type,
                threshold_percent=(
                    budget.critical_threshold_percent
                    if alert_type == "critical"
                    else budget.warning_threshold_percent
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

            triggered_alerts.append({
                "budget_id": str(budget.id),
                "budget_name": budget.name,
                "alert_type": alert_type,
                "usage_percent": budget_status.usage_percent,
                "email_sent": email_sent,
            })

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

        subject = (
            f"[{'KRITISCH' if alert_type == 'critical' else 'Warnung'}] "
            f"LLM Budget-Alarm: {budget.name}"
        )

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
                    start_tls=settings.smtp_use_tls and not getattr(settings, 'smtp_use_ssl', False),
                    timeout=getattr(settings, 'smtp_timeout', 30),
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

    async def get_alert_history(
        self, budget_id: UUID | None = None, limit: int = 50
    ) -> list[dict]:
        """Get alert history."""
        query = (
            select(LLMBudgetAlert)
            .order_by(LLMBudgetAlert.created_at.desc())
            .limit(limit)
        )

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
