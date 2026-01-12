"""Attachment handling API endpoints for the AI Chat Assistant."""

from uuid import uuid4

from fastapi import APIRouter, Body, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import assistant_attachment_cache
from app.core.deps import get_current_user, get_current_user_optional
from app.core.rate_limit import check_rate_limit
from app.database import get_session
from app.models.user import User
from app.schemas.assistant import AttachmentInfo, AttachmentUploadResponse
from app.utils.file_validation import (
    FileValidationError,
    StreamingUploadHandler,
    validate_file_type,
)
from app.utils.validation import AssistantConstants

router = APIRouter(tags=["assistant-attachments"])

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
    current_user: User | None = Depends(get_current_user_optional),
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

    # Process upload with streaming (memory-efficient for larger files)
    # Use 2MB threshold for assistant attachments (smaller than entity attachments)
    handler = StreamingUploadHandler(threshold_bytes=2 * 1024 * 1024)

    try:
        await handler.process_upload(file)

        # Validate file size
        if handler.size > MAX_ATTACHMENT_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Datei zu groß. Maximum: {MAX_ATTACHMENT_SIZE // (1024 * 1024)}MB",
            )

        # Validate actual file type via magic bytes (prevents content_type spoofing)
        try:
            validated_type = validate_file_type(
                handler.get_header(16),
                claimed_type=file.content_type or "application/octet-stream",
                allowed_types=ALLOWED_ATTACHMENT_TYPES,
            )
        except FileValidationError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None

        # Get content for cache storage
        content = handler.get_content()

        # Generate unique ID
        attachment_id = str(uuid4())

        # Store attachment in cache (TTLCache handles cleanup and size limits automatically)
        assistant_attachment_cache.set(
            attachment_id,
            {
                "content": content,
                "filename": file.filename or "unnamed",
                "content_type": validated_type,
                "size": handler.size,
            },
        )

        return AttachmentUploadResponse(
            success=True,
            attachment=AttachmentInfo(
                attachment_id=attachment_id,
                filename=file.filename or "unnamed",
                content_type=validated_type,
                size=handler.size,
            ),
        )

    finally:
        handler.cleanup()


@router.delete("/upload/{attachment_id}")
async def delete_attachment(
    attachment_id: str,
    current_user: User | None = Depends(get_current_user_optional),
) -> dict:
    """
    Delete an uploaded attachment.

    This is optional - attachments are automatically cleaned up after 1 hour.
    """
    if assistant_attachment_cache.delete(attachment_id):
        return {"success": True, "message": "Attachment gelöscht"}
    return {"success": False, "message": "Attachment nicht gefunden"}


def get_attachment(attachment_id: str) -> dict | None:
    """Get attachment content by ID (for internal use)."""
    return assistant_attachment_cache.get(attachment_id)


@router.post("/save-to-entity-attachments")
async def save_temp_attachments_to_entity(
    entity_id: str = Body(...),
    attachment_ids: list[str] = Body(...),
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
        raise HTTPException(status_code=400, detail="Ungueltige Entity-ID") from None

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
            assistant_attachment_cache.delete(temp_id)

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
        "message": f"{len(saved_ids)} Attachment(s) gespeichert" + (f", {len(errors)} Fehler" if errors else ""),
    }
