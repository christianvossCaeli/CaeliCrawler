"""API endpoints for Smart Query History management."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.database import get_session
from app.models import User
from app.models.smart_query_operation import OperationType, SmartQueryOperation
from app.schemas.common import MessageResponse
from app.schemas.smart_query_operation import (
    SmartQueryExecuteResponse,
    SmartQueryFavoriteToggleResponse,
    SmartQueryOperationListResponse,
    SmartQueryOperationResponse,
    SmartQueryOperationUpdate,
)

router = APIRouter()


@router.get("", response_model=SmartQueryOperationListResponse)
async def list_history(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    favorites_only: bool = Query(default=False, description="Show only favorites"),
    operation_type: str | None = Query(default=None, description="Filter by operation type"),
    search: str | None = Query(default=None, description="Search in command text"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    List user's Smart Query operation history with pagination.

    Supports filtering by favorites and operation type.
    """
    # Base query
    query = select(SmartQueryOperation).where(SmartQueryOperation.user_id == current_user.id)

    # Filter favorites only
    if favorites_only:
        query = query.where(SmartQueryOperation.is_favorite)

    # Filter by operation type
    if operation_type:
        try:
            op_type = OperationType(operation_type)
            query = query.where(SmartQueryOperation.operation_type == op_type)
        except ValueError:
            pass  # Invalid operation type, ignore filter

    # Search in command text or display name
    if search:
        # Escape SQL wildcards to prevent injection
        safe_search = search.replace('%', '\\%').replace('_', '\\_')
        query = query.where(
            or_(
                SmartQueryOperation.command_text.ilike(f"%{safe_search}%", escape='\\'),
                SmartQueryOperation.display_name.ilike(f"%{safe_search}%", escape='\\'),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    # Paginate and order by last_executed_at desc
    query = (
        query.order_by(SmartQueryOperation.last_executed_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await session.execute(query)
    operations = result.scalars().all()

    items = [
        SmartQueryOperationResponse(
            id=op.id,
            user_id=op.user_id,
            command_text=op.command_text,
            command_hash=op.command_hash,
            operation_type=op.operation_type,
            interpretation=op.interpretation,
            result_summary=op.result_summary,
            display_name=op.display_name,
            is_favorite=op.is_favorite,
            execution_count=op.execution_count,
            was_successful=op.was_successful,
            created_at=op.created_at,
            last_executed_at=op.last_executed_at,
        )
        for op in operations
    ]

    return SmartQueryOperationListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.get("/{operation_id}", response_model=SmartQueryOperationResponse)
async def get_operation(
    operation_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get a specific operation by ID."""
    result = await session.execute(
        select(SmartQueryOperation).where(
            SmartQueryOperation.id == operation_id,
            SmartQueryOperation.user_id == current_user.id,
        )
    )
    operation = result.scalar()

    if not operation:
        raise NotFoundError("Operation", str(operation_id))

    return SmartQueryOperationResponse(
        id=operation.id,
        user_id=operation.user_id,
        command_text=operation.command_text,
        command_hash=operation.command_hash,
        operation_type=operation.operation_type,
        interpretation=operation.interpretation,
        result_summary=operation.result_summary,
        display_name=operation.display_name,
        is_favorite=operation.is_favorite,
        execution_count=operation.execution_count,
        was_successful=operation.was_successful,
        created_at=operation.created_at,
        last_executed_at=operation.last_executed_at,
    )


@router.patch("/{operation_id}", response_model=SmartQueryOperationResponse)
async def update_operation(
    operation_id: UUID,
    data: SmartQueryOperationUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update operation (e.g., rename or toggle favorite)."""
    result = await session.execute(
        select(SmartQueryOperation).where(
            SmartQueryOperation.id == operation_id,
            SmartQueryOperation.user_id == current_user.id,
        )
    )
    operation = result.scalar()

    if not operation:
        raise NotFoundError("Operation", str(operation_id))

    if data.is_favorite is not None:
        operation.is_favorite = data.is_favorite
    if data.display_name is not None:
        operation.display_name = data.display_name

    await session.commit()
    await session.refresh(operation)

    return SmartQueryOperationResponse(
        id=operation.id,
        user_id=operation.user_id,
        command_text=operation.command_text,
        command_hash=operation.command_hash,
        operation_type=operation.operation_type,
        interpretation=operation.interpretation,
        result_summary=operation.result_summary,
        display_name=operation.display_name,
        is_favorite=operation.is_favorite,
        execution_count=operation.execution_count,
        was_successful=operation.was_successful,
        created_at=operation.created_at,
        last_executed_at=operation.last_executed_at,
    )


@router.post("/{operation_id}/toggle-favorite", response_model=SmartQueryFavoriteToggleResponse)
async def toggle_favorite(
    operation_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Toggle favorite status for an operation."""
    result = await session.execute(
        select(SmartQueryOperation).where(
            SmartQueryOperation.id == operation_id,
            SmartQueryOperation.user_id == current_user.id,
        )
    )
    operation = result.scalar()

    if not operation:
        raise NotFoundError("Operation", str(operation_id))

    operation.is_favorite = not operation.is_favorite
    await session.commit()

    return SmartQueryFavoriteToggleResponse(
        id=operation.id,
        is_favorite=operation.is_favorite,
        message="Zu Favoriten hinzugefügt" if operation.is_favorite else "Aus Favoriten entfernt",
    )


@router.post("/{operation_id}/execute", response_model=SmartQueryExecuteResponse)
async def execute_from_history(
    operation_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Re-execute a saved operation from history.

    Uses the stored interpretation, no re-parsing needed.
    """
    from services.smart_query.write_executor import execute_write_command

    result = await session.execute(
        select(SmartQueryOperation).where(
            SmartQueryOperation.id == operation_id,
            SmartQueryOperation.user_id == current_user.id,
        )
    )
    operation = result.scalar()

    if not operation:
        raise NotFoundError("Operation", str(operation_id))

    # Execute using saved interpretation
    try:
        exec_result = await execute_write_command(
            session=session,
            command=operation.interpretation,
            current_user_id=current_user.id,
        )

        # Update operation stats
        operation.execution_count += 1
        operation.last_executed_at = datetime.now(UTC)
        operation.was_successful = exec_result.get("success", False)
        operation.result_summary = {
            "message": exec_result.get("message", ""),
            "success": exec_result.get("success", False),
            "created_items": exec_result.get("created_items", []),
        }

        await session.commit()

        return SmartQueryExecuteResponse(
            operation_id=operation.id,
            success=exec_result.get("success", False),
            message=exec_result.get("message", "Ausführung abgeschlossen"),
            result=exec_result,
        )
    except Exception as e:
        operation.execution_count += 1
        operation.last_executed_at = datetime.now(UTC)
        operation.was_successful = False
        await session.commit()

        return SmartQueryExecuteResponse(
            operation_id=operation.id,
            success=False,
            message=f"Fehler bei Ausführung: {str(e)}",
            result={"error": str(e)},
        )


@router.delete("/{operation_id}", response_model=MessageResponse)
async def delete_operation(
    operation_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Delete a single operation from history."""
    result = await session.execute(
        select(SmartQueryOperation).where(
            SmartQueryOperation.id == operation_id,
            SmartQueryOperation.user_id == current_user.id,
        )
    )
    operation = result.scalar()

    if not operation:
        raise NotFoundError("Operation", str(operation_id))

    await session.delete(operation)
    await session.commit()

    return MessageResponse(message="Operation aus History gelöscht")


@router.delete("", response_model=MessageResponse)
async def clear_history(
    include_favorites: bool = Query(default=False, description="Also delete favorites"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Clear all history items.

    By default, favorites are preserved. Set include_favorites=true to delete everything.
    """
    query = delete(SmartQueryOperation).where(SmartQueryOperation.user_id == current_user.id)

    if not include_favorites:
        query = query.where(not SmartQueryOperation.is_favorite)

    result = await session.execute(query)
    await session.commit()

    return MessageResponse(message=f"{result.rowcount} Einträge aus History gelöscht")
