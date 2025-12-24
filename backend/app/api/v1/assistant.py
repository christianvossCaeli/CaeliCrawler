"""API endpoints for the AI Chat Assistant."""

import json
import time
from typing import AsyncGenerator, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Request, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.user import User, UserRole
from app.core.rate_limit import check_rate_limit
from app.schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    ActionExecuteRequest,
    ActionExecuteResponse,
    AttachmentInfo,
    AttachmentUploadResponse,
    BatchActionRequest,
    BatchActionResponse,
    BatchStatusResponse,
    ConversationMessage,
    SlashCommand,
    SLASH_COMMANDS,
)
from app.core.deps import get_current_user_optional, get_current_user
from app.utils.validation import AssistantConstants
from services.assistant_service import AssistantService

# In-memory storage for attachments with timestamps for cleanup
# Structure: {attachment_id: {"data": {...}, "created_at": timestamp}}
_attachment_store: Dict[str, Dict] = {}

# In-memory storage for batch job status with timestamps
# Structure: {batch_id: {"data": {...}, "created_at": timestamp}}
_batch_store: Dict[str, Dict] = {}

# Cleanup interval in seconds (1 hour)
_CLEANUP_INTERVAL_SECONDS = AssistantConstants.ATTACHMENT_EXPIRY_HOURS * 3600
_last_cleanup_time = time.time()

# Maximum number of entries to prevent memory exhaustion
_MAX_ATTACHMENTS = 1000  # Max concurrent temp attachments across all users
_MAX_BATCHES = 500  # Max concurrent batch jobs
_BATCH_TIMEOUT_SECONDS = 1800  # 30 minutes timeout for running batches


def _cleanup_expired_stores() -> None:
    """Clean up expired entries from in-memory stores.

    Called periodically during request handling to prevent memory leaks.
    Removes entries older than ATTACHMENT_EXPIRY_HOURS.
    Also enforces max size limits by evicting oldest entries.
    """
    global _last_cleanup_time
    current_time = time.time()

    # Only run cleanup every 5 minutes to avoid performance impact
    if current_time - _last_cleanup_time < 300:
        return

    _last_cleanup_time = current_time
    expiry_threshold = current_time - _CLEANUP_INTERVAL_SECONDS

    # Clean up attachments
    expired_attachments = [
        key for key, value in _attachment_store.items()
        if value.get("created_at", 0) < expiry_threshold
    ]
    for key in expired_attachments:
        del _attachment_store[key]

    # Enforce max size for attachments - evict oldest if over limit
    if len(_attachment_store) > _MAX_ATTACHMENTS:
        sorted_attachments = sorted(
            _attachment_store.items(),
            key=lambda x: x[1].get("created_at", 0)
        )
        evict_count = len(_attachment_store) - _MAX_ATTACHMENTS
        for key, _ in sorted_attachments[:evict_count]:
            del _attachment_store[key]

    # Clean up completed/failed batch jobs (keep running ones)
    expired_batches = [
        key for key, value in _batch_store.items()
        if value.get("created_at", 0) < expiry_threshold
        and value.get("status") in ("completed", "failed", "cancelled")
    ]
    for key in expired_batches:
        del _batch_store[key]

    # Timeout stale running batches (mark as failed after 30 minutes)
    batch_timeout_threshold = current_time - _BATCH_TIMEOUT_SECONDS
    stale_running_batches = [
        key for key, value in _batch_store.items()
        if value.get("status") == "running"
        and value.get("created_at", 0) < batch_timeout_threshold
    ]
    for key in stale_running_batches:
        _batch_store[key]["status"] = "failed"
        _batch_store[key]["message"] = "Batch-Operation hat das Timeout überschritten"

    # Enforce max size for batches - evict oldest completed/failed
    if len(_batch_store) > _MAX_BATCHES:
        # Only evict non-running batches
        completed_batches = sorted(
            [(k, v) for k, v in _batch_store.items()
             if v.get("status") in ("completed", "failed", "cancelled")],
            key=lambda x: x[1].get("created_at", 0)
        )
        evict_count = len(_batch_store) - _MAX_BATCHES
        for key, _ in completed_batches[:evict_count]:
            del _batch_store[key]

router = APIRouter()


# ============================================================================
# Chat Endpoint
# ============================================================================


@router.post("/chat", response_model=AssistantChatResponse)
async def chat(
    http_request: Request,
    request: AssistantChatRequest,
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> AssistantChatResponse:
    """
    Send a message to the AI assistant and get a response.

    The assistant can:
    - Answer questions about entities, facets, and relations
    - Execute searches using natural language
    - Suggest navigation to specific entities
    - Preview and execute inline edits (in write mode)
    - Provide contextual help

    ## Context
    The `context` object tells the assistant about the current app state:
    - `current_route`: The current page URL
    - `current_entity_id`: ID of the entity being viewed (if on detail page)
    - `current_entity_type`: Type of the current entity
    - `view_mode`: Current view mode (dashboard, list, detail, edit)

    ## Modes
    - `read`: Default mode, only allows queries and navigation
    - `write`: Allows inline edits with preview/confirmation flow

    ## Slash Commands
    - `/help [topic]` - Get help
    - `/search <query>` - Search entities
    - `/create <details>` - Create new data (redirects to Smart Query)
    - `/summary` - Summarize current entity
    - `/navigate <entity>` - Navigate to an entity

    ## Response Types
    The response contains different data based on the intent:
    - `query_result`: Search results
    - `action_preview`: Preview of an edit operation (requires confirmation)
    - `navigation`: Suggested navigation target
    - `redirect_to_smart_query`: Redirect for complex operations
    - `help`: Help information
    - `error`: Error message
    """
    # Rate limiting
    user_id = str(current_user.id) if current_user else None
    await check_rate_limit(http_request, "assistant_chat", identifier=user_id)

    # Load attachments if provided
    attachments = []
    for attachment_id in request.attachment_ids:
        attachment_data = get_attachment(attachment_id)
        if attachment_data:
            attachments.append({
                "id": attachment_id,
                "content": attachment_data["content"],
                "filename": attachment_data["filename"],
                "content_type": attachment_data["content_type"],
                "size": attachment_data["size"],
            })

    assistant = AssistantService(session)
    return await assistant.process_message(
        message=request.message,
        context=request.context,
        conversation_history=request.conversation_history,
        mode=request.mode,
        language=request.language,
        attachments=attachments
    )


# ============================================================================
# Streaming Chat Endpoint (SSE)
# ============================================================================


@router.post("/chat-stream")
async def chat_stream(
    http_request: Request,
    request: AssistantChatRequest,
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> StreamingResponse:
    """
    Send a message to the AI assistant and receive a streaming response.

    This endpoint uses Server-Sent Events (SSE) to stream the response
    in real-time as it's generated.

    ## Event Types
    The stream sends JSON events with the following types:
    - `status`: Processing status updates (e.g., "Searching...", "Analyzing...")
    - `intent`: The classified intent type
    - `token`: Individual tokens from LLM response (for real-time text display)
    - `item`: Individual result items (streamed one by one)
    - `complete`: Final response data
    - `error`: Error information

    ## Example Event Format
    ```
    data: {"type": "status", "message": "Searching..."}

    data: {"type": "token", "content": "I "}

    data: {"type": "complete", "data": {...}}

    data: [DONE]
    ```
    """
    # Rate limiting
    user_id = str(current_user.id) if current_user else None
    await check_rate_limit(http_request, "assistant_stream", identifier=user_id)

    # Load attachments if provided
    attachments = []
    for attachment_id in request.attachment_ids:
        attachment_data = get_attachment(attachment_id)
        if attachment_data:
            attachments.append({
                "id": attachment_id,
                "content": attachment_data["content"],
                "filename": attachment_data["filename"],
                "content_type": attachment_data["content_type"],
                "size": attachment_data["size"],
            })

    assistant = AssistantService(session)

    async def generate() -> AsyncGenerator[str, None]:
        try:
            async for chunk in assistant.process_message_stream(
                message=request.message,
                context=request.context,
                conversation_history=request.conversation_history,
                mode=request.mode,
                language=request.language,
                attachments=attachments
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            error_data = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


# ============================================================================
# Attachment Upload Endpoint
# ============================================================================

# Allowed MIME types for attachments
ALLOWED_ATTACHMENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "application/pdf",
}

# Maximum file size from constants
MAX_ATTACHMENT_SIZE = AssistantConstants.ATTACHMENT_MAX_SIZE_MB * 1024 * 1024


@router.post("/upload", response_model=AttachmentUploadResponse)
async def upload_attachment(
    http_request: Request,
    file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> AttachmentUploadResponse:
    """
    Upload a file attachment for the assistant chat.

    Supports the following file types:
    - Images: PNG, JPEG, GIF, WebP
    - Documents: PDF

    Maximum file size: 10MB

    Returns an attachment ID that can be included in chat requests.
    """
    # Rate limiting
    user_id = str(current_user.id) if current_user else None
    await check_rate_limit(http_request, "assistant_upload", identifier=user_id)

    # Validate content type
    if file.content_type not in ALLOWED_ATTACHMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Nicht unterstützter Dateityp: {file.content_type}. "
                   f"Erlaubt: Bilder (PNG, JPEG, GIF, WebP) und PDF."
        )

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > MAX_ATTACHMENT_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Datei zu groß. Maximum: {MAX_ATTACHMENT_SIZE // (1024 * 1024)}MB"
        )

    # Run periodic cleanup
    _cleanup_expired_stores()

    # Check if we're at capacity (prevent memory exhaustion)
    if len(_attachment_store) >= _MAX_ATTACHMENTS:
        raise HTTPException(
            status_code=503,
            detail="Server temporär überlastet. Bitte versuchen Sie es später erneut."
        )

    # Generate unique ID
    attachment_id = str(uuid4())

    # Store attachment with timestamp for cleanup
    _attachment_store[attachment_id] = {
        "content": content,
        "filename": file.filename or "unnamed",
        "content_type": file.content_type,
        "size": len(content),
        "created_at": time.time(),
    }

    return AttachmentUploadResponse(
        success=True,
        attachment=AttachmentInfo(
            attachment_id=attachment_id,
            filename=file.filename or "unnamed",
            content_type=file.content_type,
            size=len(content),
        )
    )


@router.delete("/upload/{attachment_id}")
async def delete_attachment(
    attachment_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    """
    Delete an uploaded attachment.

    This is optional - attachments are automatically cleaned up after 1 hour.
    """
    if attachment_id in _attachment_store:
        del _attachment_store[attachment_id]
        return {"success": True, "message": "Attachment gelöscht"}
    return {"success": False, "message": "Attachment nicht gefunden"}


def get_attachment(attachment_id: str) -> Optional[Dict]:
    """Get attachment content by ID (for internal use)."""
    return _attachment_store.get(attachment_id)


# ============================================================================
# Save Temp Attachments to Entity
# ============================================================================


@router.post("/save-to-entity-attachments")
async def save_temp_attachments_to_entity(
    entity_id: str = Body(...),
    attachment_ids: List[str] = Body(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Save temporary chat attachments as permanent entity attachments.

    This endpoint converts temporary attachments (uploaded for image analysis)
    into permanent EntityAttachments linked to a specific entity.

    Args:
        entity_id: UUID of the target entity
        attachment_ids: List of temporary attachment IDs to save

    Returns:
        success: bool
        saved_count: Number of attachments saved
        attachment_ids: List of new permanent attachment IDs
    """
    from uuid import UUID
    from services.attachment_service import AttachmentService

    # Validate entity_id
    try:
        entity_uuid = UUID(entity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Ungueltige Entity-ID")

    attachment_service = AttachmentService(session)
    saved_ids = []
    errors = []

    for temp_id in attachment_ids:
        # Get temp attachment data
        temp_data = get_attachment(temp_id)
        if not temp_data:
            errors.append(f"Attachment {temp_id} nicht gefunden oder abgelaufen")
            continue

        try:
            # Save as permanent entity attachment
            attachment = await attachment_service.upload_attachment(
                entity_id=entity_uuid,
                filename=temp_data["filename"],
                content=temp_data["content"],
                content_type=temp_data["content_type"],
                user_id=current_user.id if current_user else None,
                description="Aus Chat-Bildanalyse gespeichert",
            )
            saved_ids.append(str(attachment.id))

            # Remove from temp store after successful save
            if temp_id in _attachment_store:
                del _attachment_store[temp_id]

        except ValueError as e:
            errors.append(f"Fehler bei {temp_data['filename']}: {str(e)}")
        except Exception as e:
            errors.append(f"Unerwarteter Fehler bei {temp_data['filename']}: {str(e)}")

    await session.commit()

    return {
        "success": len(saved_ids) > 0,
        "saved_count": len(saved_ids),
        "attachment_ids": saved_ids,
        "errors": errors if errors else None,
        "message": f"{len(saved_ids)} Attachment(s) gespeichert" + (
            f", {len(errors)} Fehler" if errors else ""
        ),
    }


# ============================================================================
# Action Execution Endpoint
# ============================================================================


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


# ============================================================================
# Slash Commands Info
# ============================================================================


@router.get("/commands", response_model=List[SlashCommand])
async def get_commands() -> List[SlashCommand]:
    """
    Get list of available slash commands.

    Returns all slash commands that can be used in the assistant chat.
    """
    return SLASH_COMMANDS


# ============================================================================
# Suggested Actions
# ============================================================================


@router.get("/suggestions")
async def get_suggestions(
    route: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get contextual suggestions based on current location.

    Returns suggested queries and actions based on where the user is in the app.
    Dynamically includes available facet types in suggestions.
    """
    from sqlalchemy import select
    from app.models import FacetType, EntityType as EntityTypeModel

    # Load active facet types for dynamic suggestions
    facet_result = await session.execute(
        select(FacetType)
        .where(FacetType.is_active.is_(True))
        .order_by(FacetType.display_order)
        .limit(5)
    )
    facet_types = facet_result.scalars().all()
    primary_facet = facet_types[0] if facet_types else None

    suggestions = []

    if entity_id:
        # On entity detail page
        suggestions = [
            {"label": "Zusammenfassung", "query": "/summary"},
        ]
        # Add dynamic facet suggestions
        for ft in facet_types[:2]:
            suggestions.append({"label": ft.name, "query": f"Zeige {ft.name_plural or ft.name}"})
        suggestions.append({"label": "Relationen", "query": "Zeige alle Relationen"})
    elif entity_type:
        # On entity list page - load entity type name
        type_result = await session.execute(
            select(EntityTypeModel).where(EntityTypeModel.slug == entity_type)
        )
        et = type_result.scalar_one_or_none()
        type_name = et.name_plural if et else entity_type

        suggestions = [
            {"label": f"Alle {type_name}", "query": f"Zeige alle {type_name}"},
        ]
        # Add dynamic facet filter suggestions
        if primary_facet:
            suggestions.append({
                "label": f"Mit {primary_facet.name_plural or primary_facet.name}",
                "query": f"{type_name} mit {primary_facet.name_plural or primary_facet.name}"
            })
        suggestions.append({"label": "Suchen", "query": "/search "})
    elif "dashboard" in route or route == "/":
        # On dashboard
        suggestions = [
            {"label": "Übersicht", "query": "Zeige mir eine Übersicht"},
        ]
        # Add dynamic facet suggestions
        for ft in facet_types[:2]:
            suggestions.append({
                "label": f"Aktuelle {ft.name_plural or ft.name}",
                "query": f"Zeige aktuelle {ft.name_plural or ft.name}"
            })
        suggestions.append({"label": "Hilfe", "query": "/help"})
    else:
        # Default
        suggestions = [
            {"label": "Hilfe", "query": "/help"},
            {"label": "Suchen", "query": "/search "},
        ]

    return {"suggestions": suggestions, "available_facet_types": [
        {"slug": ft.slug, "name": ft.name, "name_plural": ft.name_plural, "icon": ft.icon}
        for ft in facet_types
    ]}


# ============================================================================
# Insights
# ============================================================================


@router.get("/insights")
async def get_insights(
    route: str,
    view_mode: str = "unknown",
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    language: str = Query("de", description="Language for insights: de or en"),
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    """
    Get proactive insights based on current context.

    Returns contextual insights and suggestions based on:
    - Current view mode (dashboard, list, detail)
    - Current entity being viewed
    - Recent data changes
    - Data quality indicators

    Maximum 3 insights are returned, sorted by priority.
    """
    from services.insights_service import InsightsService
    from app.schemas.assistant import AssistantContext, ViewMode

    # Build context
    context = AssistantContext(
        current_route=route,
        current_entity_id=entity_id,
        current_entity_type=entity_type,
        current_entity_name=None,
        view_mode=ViewMode(view_mode) if view_mode in [e.value for e in ViewMode] else ViewMode.UNKNOWN,
        available_actions=[]
    )

    # Get user's last login for new data detection
    last_login = None
    if current_user:
        last_login = current_user.last_login

    # Validate language
    valid_language = language if language in ("de", "en") else "de"

    # Get insights
    insights_service = InsightsService(session)
    insights = await insights_service.get_user_insights(
        context=context,
        user_id=current_user.id if current_user else None,
        last_login=last_login,
        language=valid_language
    )

    return {"insights": insights}


# ============================================================================
# Batch Operations
# ============================================================================


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

    # Run periodic cleanup
    _cleanup_expired_stores()

    # Store batch status if not dry run
    if not request.dry_run and result.get("batch_id"):
        # Check if we're at capacity (prevent memory exhaustion)
        if len(_batch_store) >= _MAX_BATCHES:
            raise HTTPException(
                status_code=503,
                detail="Zu viele gleichzeitige Batch-Operationen. Bitte warten Sie."
            )
        _batch_store[result["batch_id"]] = {
            "status": "running",
            "processed": 0,
            "total": result.get("affected_count", 0),
            "errors": [],
            "created_at": time.time(),
        }

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
    if batch_id not in _batch_store:
        raise HTTPException(
            status_code=404,
            detail=f"Batch-Operation nicht gefunden: {batch_id}"
        )

    status = _batch_store[batch_id]
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
    if batch_id not in _batch_store:
        raise HTTPException(
            status_code=404,
            detail=f"Batch-Operation nicht gefunden: {batch_id}"
        )

    _batch_store[batch_id]["status"] = "cancelled"
    _batch_store[batch_id]["message"] = "Batch-Operation wurde abgebrochen"

    return {"success": True, "message": "Batch-Operation abgebrochen"}


# ============================================================================
# Conversational Wizards
# ============================================================================


@router.get("/wizards")
async def get_available_wizards(
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    """
    Get list of available wizard types.

    Returns all wizard definitions that can be started.
    Each wizard provides a guided, step-by-step workflow.
    """
    from services.wizard_service import WizardService

    wizard_service = WizardService(session)
    wizards = await wizard_service.get_available_wizards()
    return {"wizards": wizards}


@router.post("/wizards/start")
async def start_wizard(
    wizard_type: str = Query(..., description="Type of wizard to start"),
    context: Optional[dict] = Body(None, description="Optional context to pre-fill wizard values"),
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    """
    Start a new wizard session.

    ## Wizard Types
    - `create_entity`: Create a new entity with guided input
    - `add_pain_point`: Add a pain point to an entity
    - `quick_search`: Search with advanced filters

    ## Context
    Optional context can pre-fill wizard values:
    - `current_entity_id`: Pre-select entity for entity-related wizards
    - `current_entity_type`: Pre-select entity type

    Returns the first step of the wizard.
    """
    from services.wizard_service import WizardService
    from app.schemas.assistant import WizardResponse

    wizard_service = WizardService(session)
    try:
        response = await wizard_service.start_wizard(wizard_type, context)
        return response.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/wizards/{wizard_id}/respond")
async def wizard_respond(
    wizard_id: str,
    response: dict,
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    """
    Submit a response for the current wizard step.

    The response dict should contain:
    - `value`: The user's response to the current step

    Returns the next step or completion result.
    """
    from services.wizard_service import WizardService

    wizard_service = WizardService(session)
    try:
        wizard_response, result = await wizard_service.process_wizard_response(
            wizard_id, response.get("value")
        )
        return {
            "wizard_response": wizard_response.model_dump(),
            "result": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/wizards/{wizard_id}/back")
async def wizard_back(
    wizard_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    """
    Go back to the previous wizard step.

    Only available if not on the first step.
    """
    from services.wizard_service import WizardService

    wizard_service = WizardService(session)
    try:
        response = await wizard_service.go_back(wizard_id)
        return response.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/wizards/{wizard_id}/cancel")
async def wizard_cancel(
    wizard_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    """
    Cancel an active wizard session.

    The wizard state will be discarded.
    """
    from services.wizard_service import WizardService

    wizard_service = WizardService(session)
    await wizard_service.cancel_wizard(wizard_id)
    return {"success": True, "message": "Wizard abgebrochen"}


# ============================================================================
# Reminders
# ============================================================================


@router.get("/reminders")
async def list_reminders(
    status: Optional[str] = Query(None, description="Filter by status: pending, sent, dismissed"),
    include_past: bool = Query(False, description="Include past reminders"),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    List reminders for the current user.

    Returns upcoming and recent reminders.
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select, or_
    from app.models.reminder import Reminder, ReminderStatus

    # Build query
    query = select(Reminder).where(Reminder.user_id == current_user.id)

    # Filter by status
    if status:
        try:
            status_enum = ReminderStatus(status)
            query = query.where(Reminder.status == status_enum)
        except ValueError:
            pass

    # Filter out past reminders unless requested
    if not include_past:
        # Show pending reminders or recently sent/dismissed (within 24h)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        query = query.where(
            or_(
                Reminder.status == ReminderStatus.PENDING,
                Reminder.sent_at >= cutoff,
                Reminder.dismissed_at >= cutoff,
            )
        )

    query = query.order_by(Reminder.remind_at.asc()).limit(limit)

    result = await session.execute(query)
    reminders = result.scalars().all()

    return {
        "items": [
            {
                "id": str(r.id),
                "message": r.message,
                "title": r.title,
                "remind_at": r.remind_at.isoformat(),
                "repeat": r.repeat.value,
                "status": r.status.value,
                "entity_id": str(r.entity_id) if r.entity_id else None,
                "entity_type": r.entity_type,
                "entity_name": r.entity_name,
                "created_at": r.created_at.isoformat(),
            }
            for r in reminders
        ],
        "total": len(reminders),
    }


@router.post("/reminders")
async def create_reminder(
    data: dict,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Create a new reminder.

    ## Request Body
    - `message`: The reminder message (required)
    - `remind_at`: ISO datetime when to trigger (required)
    - `title`: Optional title
    - `entity_id`: Optional entity to link
    - `entity_type`: Entity type if entity_id provided
    - `repeat`: Repeat interval: none, daily, weekly, monthly

    Returns the created reminder.
    """
    from datetime import datetime
    from app.models.reminder import Reminder, ReminderRepeat, ReminderStatus
    from app.models.entity import Entity
    from sqlalchemy import select

    # Parse remind_at
    remind_at_str = data.get("remind_at")
    if not remind_at_str:
        raise HTTPException(status_code=400, detail="remind_at ist erforderlich")

    try:
        if isinstance(remind_at_str, str):
            remind_at = datetime.fromisoformat(remind_at_str.replace("Z", "+00:00"))
        else:
            remind_at = remind_at_str
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Ungültiges Datumsformat für remind_at")

    # Parse repeat
    repeat_str = data.get("repeat", "none")
    try:
        repeat = ReminderRepeat(repeat_str)
    except ValueError:
        repeat = ReminderRepeat.NONE

    # Get entity info if provided
    entity_id = data.get("entity_id")
    entity_type = data.get("entity_type")
    entity_name = None

    if entity_id:
        from uuid import UUID
        try:
            entity_uuid = UUID(entity_id)
            result = await session.execute(
                select(Entity).where(Entity.id == entity_uuid)
            )
            entity = result.scalar_one_or_none()
            if entity:
                entity_name = entity.name
                entity_type = entity_type or entity.entity_type.slug if entity.entity_type else None
        except (ValueError, TypeError):
            pass

    # Create reminder
    reminder = Reminder(
        user_id=current_user.id,
        message=data.get("message", "Erinnerung"),
        title=data.get("title"),
        remind_at=remind_at,
        repeat=repeat,
        status=ReminderStatus.PENDING,
        entity_id=entity_id if entity_id else None,
        entity_type=entity_type,
        entity_name=entity_name,
    )

    session.add(reminder)
    await session.commit()
    await session.refresh(reminder)

    return {
        "success": True,
        "reminder": {
            "id": str(reminder.id),
            "message": reminder.message,
            "title": reminder.title,
            "remind_at": reminder.remind_at.isoformat(),
            "repeat": reminder.repeat.value,
            "status": reminder.status.value,
            "entity_id": str(reminder.entity_id) if reminder.entity_id else None,
            "entity_type": reminder.entity_type,
            "entity_name": reminder.entity_name,
            "created_at": reminder.created_at.isoformat(),
        },
        "message": f"Erinnerung erstellt für {reminder.remind_at.strftime('%d.%m.%Y %H:%M')}",
    }


@router.delete("/reminders/{reminder_id}")
async def delete_reminder(
    reminder_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Delete/cancel a reminder.
    """
    from uuid import UUID
    from sqlalchemy import select
    from app.models.reminder import Reminder

    try:
        reminder_uuid = UUID(reminder_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Ungültige Reminder-ID")

    result = await session.execute(
        select(Reminder).where(
            Reminder.id == reminder_uuid,
            Reminder.user_id == current_user.id,
        )
    )
    reminder = result.scalar_one_or_none()

    if not reminder:
        raise HTTPException(status_code=404, detail="Erinnerung nicht gefunden")

    reminder.cancel()
    await session.commit()

    return {"success": True, "message": "Erinnerung gelöscht"}


@router.post("/reminders/{reminder_id}/dismiss")
async def dismiss_reminder(
    reminder_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Dismiss a reminder (mark as acknowledged).
    """
    from uuid import UUID
    from sqlalchemy import select
    from app.models.reminder import Reminder

    try:
        reminder_uuid = UUID(reminder_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Ungültige Reminder-ID")

    result = await session.execute(
        select(Reminder).where(
            Reminder.id == reminder_uuid,
            Reminder.user_id == current_user.id,
        )
    )
    reminder = result.scalar_one_or_none()

    if not reminder:
        raise HTTPException(status_code=404, detail="Erinnerung nicht gefunden")

    reminder.dismiss()
    await session.commit()

    return {"success": True, "message": "Erinnerung bestätigt"}


@router.post("/reminders/{reminder_id}/snooze")
async def snooze_reminder(
    reminder_id: str,
    data: dict,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Snooze a reminder to a new time.

    Request body:
    - `remind_at`: New datetime to remind (ISO format)
    """
    from uuid import UUID
    from datetime import datetime
    from sqlalchemy import select
    from app.models.reminder import Reminder, ReminderStatus

    try:
        reminder_uuid = UUID(reminder_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Ungültige Reminder-ID")

    if "remind_at" not in data:
        raise HTTPException(status_code=400, detail="remind_at ist erforderlich")

    try:
        new_remind_at = datetime.fromisoformat(data["remind_at"].replace("Z", "+00:00"))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Ungültiges Datumsformat")

    result = await session.execute(
        select(Reminder).where(
            Reminder.id == reminder_uuid,
            Reminder.user_id == current_user.id,
        )
    )
    reminder = result.scalar_one_or_none()

    if not reminder:
        raise HTTPException(status_code=404, detail="Erinnerung nicht gefunden")

    # Update remind_at and ensure status is pending
    reminder.remind_at = new_remind_at
    reminder.status = ReminderStatus.PENDING
    await session.commit()

    return {
        "success": True,
        "message": f"Erinnerung verschoben auf {new_remind_at.strftime('%d.%m.%Y %H:%M')}",
        "remind_at": new_remind_at.isoformat(),
    }


@router.get("/reminders/due")
async def get_due_reminders(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get all due (pending and past remind_at) reminders for the current user.

    Used for displaying reminder notifications in the UI.
    """
    from datetime import datetime, timezone
    from sqlalchemy import select, and_
    from app.models.reminder import Reminder, ReminderStatus

    result = await session.execute(
        select(Reminder).where(
            and_(
                Reminder.user_id == current_user.id,
                Reminder.status == ReminderStatus.PENDING,
                Reminder.remind_at <= datetime.now(timezone.utc),
            )
        ).order_by(Reminder.remind_at.asc())
    )
    reminders = result.scalars().all()

    return {
        "items": [
            {
                "id": str(r.id),
                "message": r.message,
                "title": r.title,
                "remind_at": r.remind_at.isoformat(),
                "entity_id": str(r.entity_id) if r.entity_id else None,
                "entity_type": r.entity_type,
                "entity_name": r.entity_name,
            }
            for r in reminders
        ],
        "count": len(reminders),
    }
