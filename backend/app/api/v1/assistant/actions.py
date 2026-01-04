"""Action execution and batch operation API endpoints for the AI Chat Assistant."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import assistant_batch_cache
from app.core.deps import get_current_user
from app.core.rate_limit import check_rate_limit
from app.database import get_session
from app.models.user import User, UserRole
from app.schemas.assistant import (
    ActionExecuteRequest,
    ActionExecuteResponse,
    BatchActionRequest,
    BatchActionResponse,
    BatchStatusResponse,
)
from services.assistant_service import AssistantService

router = APIRouter(tags=["assistant-actions"])


@router.post("/create-facet-type")
async def create_facet_type_via_assistant(
    data: dict,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Create a new facet type via the assistant.

    This endpoint is called after the user confirms facet type creation.
    Requires EDITOR or ADMIN role.
    Uses the unified Smart Query write executor.
    """
    from services.smart_query.write_executor import execute_facet_type_create

    # Check permissions
    allowed_roles = [UserRole.ADMIN, UserRole.EDITOR]
    if not current_user.is_superuser and current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail="Keine Berechtigung zum Erstellen von Facet-Typen. Erforderliche Rolle: EDITOR oder ADMIN"
        )

    name = data.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Name ist erforderlich")

    # Use unified Smart Query executor
    result = await execute_facet_type_create(session, data)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Fehler beim Erstellen"))

    await session.commit()

    return {
        "success": True,
        "message": result.get("message", f"Facet-Typ '{name}' wurde erstellt"),
        "facet_type": {
            "id": result.get("facet_type_id"),
            "name": result.get("facet_type_name"),
            "slug": result.get("facet_type_slug"),
        }
    }


@router.post("/execute-action", response_model=ActionExecuteResponse)
async def execute_action(
    http_request: Request,
    request: ActionExecuteRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ActionExecuteResponse:
    """
    Execute a confirmed action from the assistant.

    This endpoint is called after the user confirms an action preview.
    Currently supports:
    - `update_entity`: Update entity fields

    The action must have been previously returned by the `/chat` endpoint
    as an `action_preview` response type.

    Requires EDITOR or ADMIN role.
    """
    # Rate limiting
    await check_rate_limit(http_request, "assistant_execute", identifier=str(current_user.id))

    # Check if user has edit permissions
    allowed_roles = [UserRole.ADMIN, UserRole.EDITOR]
    if not current_user.is_superuser and current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail="Sie haben keine Berechtigung zum Bearbeiten. Erforderliche Rolle: EDITOR oder ADMIN"
        )

    assistant = AssistantService(session)
    result = await assistant.execute_action(
        action=request.action,
        context=request.context
    )

    return ActionExecuteResponse(
        success=result.get("success", False),
        message=result.get("message", ""),
        affected_entity_id=result.get("affected_entity_id"),
        affected_entity_name=result.get("affected_entity_name"),
        refresh_required=result.get("refresh_required", True)
    )


@router.post("/batch-action", response_model=BatchActionResponse)
async def batch_action(
    http_request: Request,
    request: BatchActionRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> BatchActionResponse:
    """
    Execute or preview a batch action on multiple entities.

    ## Supported Action Types
    - `add_facet`: Add a facet to matching entities
    - `update_field`: Update a field on matching entities
    - `add_relation`: Add a relation to matching entities
    - `remove_facet`: Remove a facet from matching entities

    ## Target Filter
    Filter entities by various criteria:
    - `entity_type`: Type of entity (e.g., "territorial_entity")
    - `location.admin_level_1`: State/region filter
    - `has_facet`: Filter by existing facet

    ## Dry Run
    Set `dry_run=true` (default) to preview affected entities without executing.
    Set `dry_run=false` to execute the batch action.

    Requires EDITOR or ADMIN role.
    """
    # Rate limiting (batch operations are expensive)
    await check_rate_limit(http_request, "assistant_batch", identifier=str(current_user.id))

    # Check permissions
    allowed_roles = [UserRole.ADMIN, UserRole.EDITOR]
    if not current_user.is_superuser and current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail="Keine Berechtigung für Batch-Operationen. Erforderliche Rolle: EDITOR oder ADMIN"
        )

    assistant = AssistantService(session)
    result = await assistant.execute_batch_action(
        action_type=request.action_type,
        target_filter=request.target_filter,
        action_data=request.action_data,
        dry_run=request.dry_run
    )

    # Store batch status if not dry run (TTLCache handles cleanup and size limits)
    if not request.dry_run and result.get("batch_id"):
        assistant_batch_cache.set(result["batch_id"], {
            "status": "running",
            "processed": 0,
            "total": result.get("affected_count", 0),
            "errors": [],
        })

    return BatchActionResponse(
        success=result.get("success", True),
        affected_count=result.get("affected_count", 0),
        preview=result.get("preview", []),
        batch_id=result.get("batch_id"),
        message=result.get("message", "")
    )


@router.get("/batch-action/{batch_id}/status", response_model=BatchStatusResponse)
async def get_batch_status(
    batch_id: str,
    current_user: User = Depends(get_current_user),
) -> BatchStatusResponse:
    """
    Get the status of a running or completed batch operation.

    Returns progress information and any errors that occurred.
    """
    status = assistant_batch_cache.get(batch_id)
    if status is None:
        raise HTTPException(
            status_code=404,
            detail=f"Batch-Operation nicht gefunden: {batch_id}"
        )

    return BatchStatusResponse(
        batch_id=batch_id,
        status=status.get("status", "pending"),
        processed=status.get("processed", 0),
        total=status.get("total", 0),
        errors=status.get("errors", []),
        message=status.get("message", "")
    )


@router.post("/batch-action/{batch_id}/cancel")
async def cancel_batch(
    batch_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Cancel a running batch operation.

    Note: Already processed items cannot be rolled back.
    """
    status = assistant_batch_cache.get(batch_id)
    if status is None:
        raise HTTPException(
            status_code=404,
            detail=f"Batch-Operation nicht gefunden: {batch_id}"
        )

    # Update the status and re-store
    status["status"] = "cancelled"
    status["message"] = "Batch-Operation wurde abgebrochen"
    assistant_batch_cache.set(batch_id, status)

    return {"success": True, "message": "Batch-Operation abgebrochen"}
