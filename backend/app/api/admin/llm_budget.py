"""
Admin API endpoints for LLM budget management.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.database import get_session
from app.models.user import User
from app.schemas.llm_budget import (
    BudgetStatusListResponse,
    LLMBudgetConfigCreate,
    LLMBudgetConfigResponse,
    LLMBudgetConfigUpdate,
)
from services.llm_budget_service import LLMBudgetService

router = APIRouter(
    prefix="/llm-budget",
    tags=["Admin - LLM Budget"],
)


@router.get("", response_model=list[LLMBudgetConfigResponse])
async def list_budgets(
    active_only: bool = Query(False, description="Only return active budgets"),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    List all budget configurations.

    Returns all configured budgets with their settings.
    """
    service = LLMBudgetService(db)
    return await service.list_budgets(active_only=active_only)


@router.get("/status", response_model=BudgetStatusListResponse)
async def get_budget_status(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    Get current status of all active budgets.

    Returns current usage, thresholds, and warning status for each budget.
    """
    service = LLMBudgetService(db)
    return await service.get_budget_status()


@router.get("/alerts")
async def get_alert_history(
    budget_id: UUID | None = Query(None, description="Filter by budget ID"),
    limit: int = Query(50, ge=1, le=200),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    Get budget alert history.

    Returns past alerts that were triggered for budgets.
    """
    service = LLMBudgetService(db)
    return await service.get_alert_history(budget_id=budget_id, limit=limit)


@router.get("/{budget_id}", response_model=LLMBudgetConfigResponse)
async def get_budget(
    budget_id: UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    Get a specific budget configuration.
    """
    service = LLMBudgetService(db)
    budget = await service.get_budget(budget_id)

    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    return budget


@router.post("", response_model=LLMBudgetConfigResponse, status_code=201)
async def create_budget(
    data: LLMBudgetConfigCreate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    Create a new budget configuration.

    Configure monthly limits, warning thresholds, and email alerts.
    """
    service = LLMBudgetService(db)
    return await service.create_budget(data)


@router.put("/{budget_id}", response_model=LLMBudgetConfigResponse)
async def update_budget(
    budget_id: UUID,
    data: LLMBudgetConfigUpdate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    Update an existing budget configuration.
    """
    service = LLMBudgetService(db)
    budget = await service.update_budget(budget_id, data)

    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    return budget


@router.delete("/{budget_id}", status_code=204)
async def delete_budget(
    budget_id: UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    Delete a budget configuration.

    This will also delete all associated alert history.
    """
    service = LLMBudgetService(db)
    success = await service.delete_budget(budget_id)

    if not success:
        raise HTTPException(status_code=404, detail="Budget not found")


@router.post("/check-alerts")
async def trigger_budget_check(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    Manually trigger budget check and send alerts.

    This is normally run by a scheduled task, but can be triggered manually.
    Returns list of alerts that were triggered.
    """
    service = LLMBudgetService(db)
    alerts = await service.check_and_send_alerts()

    return {
        "checked": True,
        "alerts_triggered": len(alerts),
        "alerts": alerts,
    }
