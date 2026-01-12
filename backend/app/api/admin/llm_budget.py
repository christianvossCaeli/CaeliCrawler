"""
Admin API endpoints for LLM budget management.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.database import get_session
from app.models.audit_log import AuditAction
from app.models.llm_budget import LimitIncreaseRequestStatus
from app.models.user import User
from app.services.audit_service import create_audit_log
from app.schemas.llm_budget import (
    AdminLimitRequestAction,
    BudgetStatusListResponse,
    LimitIncreaseRequestListResponse,
    LimitIncreaseRequestResponse,
    LLMBudgetConfigCreate,
    LLMBudgetConfigResponse,
    LLMBudgetConfigUpdate,
)
from services.llm_budget_service import LLMBudgetService

router = APIRouter(
    prefix="/llm-budget",
    tags=["Admin - LLM Budget"],
)


# === List and Status Endpoints (static paths first) ===


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


# === Limit Increase Request Endpoints (must come before /{budget_id}) ===


@router.get(
    "/limit-requests",
    response_model=LimitIncreaseRequestListResponse,
    summary="List limit increase requests",
)
async def list_limit_requests(
    status: LimitIncreaseRequestStatus | None = Query(None, description="Filter by request status"),
    limit: int = Query(50, ge=1, le=200),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    List all limit increase requests.

    Returns requests with user information for admin review.
    """
    service = LLMBudgetService(db)
    return await service.list_limit_requests(status=status, limit=limit)


@router.get(
    "/limit-requests/{request_id}",
    response_model=LimitIncreaseRequestResponse,
    summary="Get limit request details",
)
async def get_limit_request(
    request_id: UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    Get details of a specific limit increase request.
    """
    service = LLMBudgetService(db)
    request = await service.get_limit_request(request_id)

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    return request


@router.post(
    "/limit-requests/{request_id}/approve",
    response_model=LimitIncreaseRequestResponse,
    summary="Approve limit request",
)
async def approve_limit_request(
    request_id: UUID,
    action: AdminLimitRequestAction | None = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    Approve a limit increase request.

    This updates the user's budget to the requested limit.
    """
    service = LLMBudgetService(db)

    try:
        result = await service.approve_limit_request(
            request_id=request_id,
            admin_id=admin.id,
            action=action,
        )

        # Create audit log entry
        await create_audit_log(
            session=db,
            action=AuditAction.UPDATE,
            entity_type="LimitIncreaseRequest",
            entity_id=request_id,
            entity_name="approved",
            user=admin,
        )

        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        ) from None


@router.post(
    "/limit-requests/{request_id}/deny",
    response_model=LimitIncreaseRequestResponse,
    summary="Deny limit request",
)
async def deny_limit_request(
    request_id: UUID,
    action: AdminLimitRequestAction | None = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    Deny a limit increase request.

    The user's budget remains unchanged.
    """
    service = LLMBudgetService(db)

    try:
        result = await service.deny_limit_request(
            request_id=request_id,
            admin_id=admin.id,
            action=action,
        )

        # Create audit log entry
        await create_audit_log(
            session=db,
            action=AuditAction.UPDATE,
            entity_type="LimitIncreaseRequest",
            entity_id=request_id,
            entity_name="denied",
            user=admin,
        )

        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        ) from None


# === Single Budget CRUD Endpoints (dynamic path must come last) ===


@router.post("", response_model=LLMBudgetConfigResponse, status_code=201)
async def create_budget(
    data: LLMBudgetConfigCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    Create a new budget configuration.

    Configure monthly limits, warning thresholds, and email alerts.
    """
    service = LLMBudgetService(db)
    result = await service.create_budget(data)

    # Create audit log entry
    await create_audit_log(
        session=db,
        action=AuditAction.CREATE,
        entity_type="LLMBudget",
        entity_id=result.id,
        entity_name=data.name,
        user=current_user,
    )
    await db.commit()

    return result


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


@router.put("/{budget_id}", response_model=LLMBudgetConfigResponse)
async def update_budget(
    budget_id: UUID,
    data: LLMBudgetConfigUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    Update an existing budget configuration.
    """
    service = LLMBudgetService(db)
    budget = await service.update_budget(budget_id, data)

    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    # Create audit log entry
    await create_audit_log(
        session=db,
        action=AuditAction.UPDATE,
        entity_type="LLMBudget",
        entity_id=budget_id,
        entity_name=budget.name,
        user=current_user,
    )
    await db.commit()

    return budget


@router.delete("/{budget_id}", status_code=204)
async def delete_budget(
    budget_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    Delete a budget configuration.

    This will also delete all associated alert history.
    """
    service = LLMBudgetService(db)

    # Get budget name before deletion for audit log
    budget = await service.get_budget(budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    budget_name = budget.name

    # Create audit log entry
    await create_audit_log(
        session=db,
        action=AuditAction.DELETE,
        entity_type="LLMBudget",
        entity_id=budget_id,
        entity_name=budget_name,
        user=current_user,
    )

    success = await service.delete_budget(budget_id)

    if not success:
        raise HTTPException(status_code=404, detail="Budget not found")
