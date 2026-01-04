"""User LLM usage and budget endpoints.

These endpoints allow users to view their LLM usage status and
request limit increases.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_session
from app.models.user import User, UserRole
from app.schemas.llm_budget import (
    LimitIncreaseRequestCreate,
    LimitIncreaseRequestResponse,
    UserBudgetStatusResponse,
)
from services.llm_budget_service import LLMBudgetService

router = APIRouter(prefix="/me/llm", tags=["User LLM Usage"])


class AdminSelfLimitUpdate(BaseModel):
    """Admin self-service limit update."""

    new_limit_cents: int = Field(gt=0, description="New monthly limit in USD cents")


@router.get(
    "/usage",
    response_model=UserBudgetStatusResponse | None,
    summary="Get my LLM usage status",
    description="Returns the current LLM usage status for the authenticated user, "
    "including budget limits and warning/blocking status. "
    "Returns null if no budget is configured for the user.",
)
async def get_my_llm_usage(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserBudgetStatusResponse | None:
    """Get current user's LLM budget status."""
    service = LLMBudgetService(session)
    return await service.get_user_budget_status(current_user.id)


@router.post(
    "/limit-request",
    response_model=LimitIncreaseRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request limit increase",
    description="Submit a request to increase your monthly LLM budget limit. "
    "The request will be reviewed by an administrator.",
)
async def request_limit_increase(
    data: LimitIncreaseRequestCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LimitIncreaseRequestResponse:
    """Request an increase to the user's LLM budget limit."""
    service = LLMBudgetService(session)

    try:
        request = await service.create_limit_request(current_user.id, data)
        await session.commit()
        return request
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None


@router.get(
    "/limit-requests",
    response_model=list[LimitIncreaseRequestResponse],
    summary="Get my limit requests",
    description="Returns all limit increase requests submitted by the authenticated user.",
)
async def get_my_limit_requests(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[LimitIncreaseRequestResponse]:
    """Get all limit requests for the current user."""
    service = LLMBudgetService(session)
    return await service.get_user_limit_requests(current_user.id)


@router.put(
    "/limit",
    response_model=UserBudgetStatusResponse,
    summary="Update own limit (admin only)",
    description="Allows administrators to directly update their own monthly LLM budget limit "
    "without going through the request approval workflow. "
    "Non-admin users receive a 403 error.",
)
async def update_own_limit(
    data: AdminSelfLimitUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserBudgetStatusResponse:
    """
    Admin self-service limit update.

    Admins can directly set their own budget limit for self-regulation
    without needing approval from another admin.
    """
    # Only admins can use this endpoint
    if current_user.role != UserRole.ADMIN and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update their own limit directly. Please use the limit request workflow.",
        )

    service = LLMBudgetService(session)

    try:
        result = await service.update_user_budget_limit(
            user_id=current_user.id,
            new_limit_cents=data.new_limit_cents,
        )
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None
