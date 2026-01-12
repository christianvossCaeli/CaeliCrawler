"""API endpoints for entity attachments."""

import time
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.audit import AuditContext
from app.core.deps import get_current_user, get_current_user_optional
from app.database import get_session
from app.models.audit_log import AuditAction
from app.models.entity_attachment import EntityAttachment
from app.models.user import User, UserRole
from app.schemas.attachment import AttachmentSearchResponse, AttachmentSearchResult
from app.utils.file_validation import (
    FileValidationError,
    StreamingUploadHandler,
    validate_file_type,
)
from services.attachment_service import AttachmentService

router = APIRouter()

# Allowed MIME types
ALLOWED_TYPES = {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "application/pdf",
}


@router.get("/search", response_model=AttachmentSearchResponse)
async def search_attachments(
    q: str = Query(..., min_length=2, description="Search query"),
    entity_id: UUID | None = Query(None, description="Filter by entity"),
    content_type: str | None = Query(None, description="Filter by content type (e.g., image/png)"),
    analysis_status: str | None = Query(None, description="Filter by status (PENDING, ANALYZING, COMPLETED, FAILED)"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AttachmentSearchResponse:
    """
    Full-text search across attachment content.

    Searches in:
    - Filename
    - Description
    - AI-extracted description
    - AI-extracted text content (OCR for images, text extraction for PDFs)

    Uses PostgreSQL full-text search with German language support.
    Results are ranked by relevance and include highlighted snippets.
    """
    start_time = time.time()

    # Build search query
    search_query = func.plainto_tsquery("german", q)

    # Base query with ranking
    query = (
        select(
            EntityAttachment,
            func.ts_rank(EntityAttachment.search_vector, search_query).label("rank"),
            func.ts_headline(
                "german",
                func.coalesce(EntityAttachment.description, "")
                + " "
                + func.coalesce(EntityAttachment.analysis_result["description"].astext, ""),
                search_query,
                "StartSel=<mark>, StopSel=</mark>, MaxWords=50, MinWords=20",
            ).label("headline"),
        )
        .where(EntityAttachment.search_vector.isnot(None))
        .where(EntityAttachment.search_vector.op("@@")(search_query))
    )

    # Apply filters
    if entity_id:
        query = query.where(EntityAttachment.entity_id == entity_id)
    if content_type:
        query = query.where(EntityAttachment.content_type == content_type)
    if analysis_status:
        query = query.where(EntityAttachment.analysis_status == analysis_status)

    # Order by rank
    query = query.order_by(func.ts_rank(EntityAttachment.search_vector, search_query).desc())

    # Pagination
    query = query.offset((page - 1) * per_page).limit(per_page)

    # Load entity relationship for entity_name
    query = query.options(selectinload(EntityAttachment.entity))

    result = await session.execute(query)
    rows = result.all()

    # Count total (without pagination)
    count_query = (
        select(func.count())
        .select_from(EntityAttachment)
        .where(EntityAttachment.search_vector.isnot(None))
        .where(EntityAttachment.search_vector.op("@@")(search_query))
    )
    if entity_id:
        count_query = count_query.where(EntityAttachment.entity_id == entity_id)
    if content_type:
        count_query = count_query.where(EntityAttachment.content_type == content_type)
    if analysis_status:
        count_query = count_query.where(EntityAttachment.analysis_status == analysis_status)

    total = (await session.execute(count_query)).scalar() or 0

    # Build response
    items = []
    for row in rows:
        att = row[0]
        items.append(
            AttachmentSearchResult(
                id=att.id,
                entity_id=att.entity_id,
                entity_name=att.entity.name if att.entity else "Unknown",
                filename=att.filename,
                content_type=att.content_type,
                file_size=att.file_size,
                description=att.description,
                analysis_status=att.analysis_status.value,
                headline=row[2],
                rank=round(row[1] or 0.0, 4),
                created_at=att.created_at,
                analyzed_at=att.analyzed_at,
                is_image=att.is_image,
                is_pdf=att.is_pdf,
            )
        )

    return AttachmentSearchResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 1,
        query=q,
        search_time_ms=round((time.time() - start_time) * 1000, 2),
    )


@router.post("/entities/{entity_id}/attachments")
async def upload_attachment(
    entity_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    description: str | None = Query(None, max_length=500),
    auto_analyze: bool = Query(False, description="Start AI analysis immediately"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Upload a file attachment to an entity.

    Supports:
    - Images: PNG, JPEG, GIF, WebP
    - Documents: PDF

    Maximum file size: 20MB
    """
    # Calculate thresholds from config
    max_size = settings.attachment_max_size_mb * 1024 * 1024
    stream_threshold = settings.attachment_stream_threshold_mb * 1024 * 1024

    # Process upload with streaming (memory-efficient for large files)
    handler = StreamingUploadHandler(
        threshold_bytes=stream_threshold,
        temp_dir=settings.attachment_temp_dir,
    )

    try:
        await handler.process_upload(file)

        # Validate size
        if handler.size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"Datei zu gross. Maximum: {settings.attachment_max_size_mb}MB",
            )

        # Validate actual file type via magic bytes (only reads header, efficient)
        try:
            validated_type = validate_file_type(
                handler.get_header(16),
                claimed_type=file.content_type or "application/octet-stream",
                allowed_types=ALLOWED_TYPES,
            )
        except FileValidationError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None

        # Get content for service
        content = handler.get_content()

        service = AttachmentService(session)

        try:
            attachment = await service.upload_attachment(
                entity_id=entity_id,
                filename=file.filename or "unnamed",
                content=content,
                content_type=validated_type,
                user_id=current_user.id,
                description=description,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None

    finally:
        handler.cleanup()

    # Audit log for attachment upload
    async with AuditContext(session, current_user, request) as audit:
        audit.track_action(
            action=AuditAction.CREATE,
            entity_type="Attachment",
            entity_id=attachment.id,
            entity_name=attachment.filename,
            changes={
                "filename": attachment.filename,
                "content_type": attachment.content_type,
                "file_size": attachment.file_size,
                "entity_id": str(entity_id),
                "auto_analyze": auto_analyze,
            },
        )
        await session.commit()

    result: dict[str, Any] = {
        "success": True,
        "attachment": {
            "id": str(attachment.id),
            "filename": attachment.filename,
            "content_type": attachment.content_type,
            "file_size": attachment.file_size,
            "analysis_status": attachment.analysis_status.value,
            "created_at": attachment.created_at.isoformat(),
        },
    }

    # Start analysis if requested
    if auto_analyze:
        try:
            from services.attachment_analysis_service import AttachmentAnalysisService

            analysis_service = AttachmentAnalysisService(session)
            task = await analysis_service.analyze_attachment(attachment.id)
            result["analysis_task_id"] = str(task.id)
        except Exception as e:
            # Analysis start failed, but upload succeeded
            result["analysis_error"] = str(e)

    return result


@router.get("/entities/{entity_id}/attachments")
async def list_attachments(
    entity_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """
    List all attachments for an entity.
    """
    service = AttachmentService(session)
    attachments = await service.get_attachments(entity_id)

    return {
        "items": [
            {
                "id": str(att.id),
                "filename": att.filename,
                "content_type": att.content_type,
                "file_size": att.file_size,
                "description": att.description,
                "analysis_status": att.analysis_status.value,
                "analysis_result": att.analysis_result,
                "analyzed_at": att.analyzed_at.isoformat() if att.analyzed_at else None,
                "uploaded_by_id": str(att.uploaded_by_id) if att.uploaded_by_id else None,
                "created_at": att.created_at.isoformat(),
                "is_image": att.is_image,
                "is_pdf": att.is_pdf,
            }
            for att in attachments
        ],
        "total": len(attachments),
    }


@router.get("/entities/{entity_id}/attachments/{attachment_id}")
async def get_attachment(
    entity_id: UUID,
    attachment_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Get attachment metadata."""
    service = AttachmentService(session)
    attachment = await service.get_attachment(attachment_id)

    if not attachment or attachment.entity_id != entity_id:
        raise HTTPException(status_code=404, detail="Attachment nicht gefunden")

    return {
        "id": str(attachment.id),
        "entity_id": str(attachment.entity_id),
        "filename": attachment.filename,
        "content_type": attachment.content_type,
        "file_size": attachment.file_size,
        "description": attachment.description,
        "analysis_status": attachment.analysis_status.value,
        "analysis_result": attachment.analysis_result,
        "analysis_error": attachment.analysis_error,
        "analyzed_at": attachment.analyzed_at.isoformat() if attachment.analyzed_at else None,
        "ai_model_used": attachment.ai_model_used,
        "uploaded_by_id": str(attachment.uploaded_by_id) if attachment.uploaded_by_id else None,
        "created_at": attachment.created_at.isoformat(),
        "is_image": attachment.is_image,
        "is_pdf": attachment.is_pdf,
    }


@router.get("/entities/{entity_id}/attachments/{attachment_id}/download")
async def download_attachment(
    entity_id: UUID,
    attachment_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Download attachment file."""
    service = AttachmentService(session)
    attachment = await service.get_attachment(attachment_id)

    if not attachment or attachment.entity_id != entity_id:
        raise HTTPException(status_code=404, detail="Attachment nicht gefunden")

    try:
        content = await service.get_file_content(attachment)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Datei nicht gefunden") from None

    return StreamingResponse(
        iter([content]),
        media_type=attachment.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{attachment.filename}"',
            "Content-Length": str(len(content)),
        },
    )


@router.get("/entities/{entity_id}/attachments/{attachment_id}/thumbnail")
async def get_thumbnail(
    entity_id: UUID,
    attachment_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Get thumbnail for image attachments."""
    service = AttachmentService(session)
    attachment = await service.get_attachment(attachment_id)

    if not attachment or attachment.entity_id != entity_id:
        raise HTTPException(status_code=404, detail="Attachment nicht gefunden")

    if not attachment.is_image:
        raise HTTPException(status_code=400, detail="Keine Bildvorschau verfuegbar")

    thumb_path = service.get_thumbnail_path_for_attachment(attachment)

    if not thumb_path or not thumb_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail nicht gefunden")

    return FileResponse(
        thumb_path,
        media_type=attachment.content_type,
    )


@router.delete("/entities/{entity_id}/attachments/{attachment_id}")
async def delete_attachment(
    entity_id: UUID,
    attachment_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Delete an attachment."""
    # Check permissions
    if not current_user.is_superuser and current_user.role not in [
        UserRole.ADMIN,
        UserRole.EDITOR,
    ]:
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    service = AttachmentService(session)
    attachment = await service.get_attachment(attachment_id)

    if not attachment or attachment.entity_id != entity_id:
        raise HTTPException(status_code=404, detail="Attachment nicht gefunden")

    filename = attachment.filename

    async with AuditContext(session, current_user, request) as audit:
        audit.track_action(
            action=AuditAction.DELETE,
            entity_type="Attachment",
            entity_id=attachment_id,
            entity_name=filename,
            changes={
                "deleted": True,
                "filename": filename,
                "entity_id": str(entity_id),
                "file_size": attachment.file_size,
            },
        )
        # Note: delete_attachment handles its own commit
        success = await service.delete_attachment(attachment_id)
        await session.commit()

    return {"success": success, "message": "Attachment geloescht"}


@router.post("/entities/{entity_id}/attachments/{attachment_id}/analyze")
async def start_analysis(
    entity_id: UUID,
    attachment_id: UUID,
    extract_facets: bool = Query(True, description="Extract facet suggestions"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Start AI analysis for an attachment.

    Returns an AITask ID for tracking progress.
    """
    service = AttachmentService(session)
    attachment = await service.get_attachment(attachment_id)

    if not attachment or attachment.entity_id != entity_id:
        raise HTTPException(status_code=404, detail="Attachment nicht gefunden")

    try:
        from services.attachment_analysis_service import AttachmentAnalysisService

        analysis_service = AttachmentAnalysisService(session)
        task = await analysis_service.analyze_attachment(
            attachment_id=attachment_id,
            extract_facets=extract_facets,
        )

        return {
            "success": True,
            "task_id": str(task.id),
            "message": f"Analyse von '{attachment.filename}' gestartet",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analyse fehlgeschlagen: {str(e)}") from None


@router.patch("/entities/{entity_id}/attachments/{attachment_id}")
async def update_attachment(
    entity_id: UUID,
    attachment_id: UUID,
    description: str | None = Query(None, max_length=500),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Update attachment metadata (description)."""
    service = AttachmentService(session)
    attachment = await service.get_attachment(attachment_id)

    if not attachment or attachment.entity_id != entity_id:
        raise HTTPException(status_code=404, detail="Attachment nicht gefunden")

    if description is not None:
        attachment = await service.update_description(attachment_id, description)

    return {
        "success": True,
        "attachment": {
            "id": str(attachment.id),
            "description": attachment.description,
        },
    }


@router.post("/entities/{entity_id}/attachments/{attachment_id}/apply-facets")
async def apply_facet_suggestions(
    entity_id: UUID,
    attachment_id: UUID,
    facet_indices: list[int] = Query(..., description="Indices of facet suggestions to apply"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Apply selected facet suggestions from attachment analysis.

    Takes indices of facet_suggestions array from analysis_result
    and creates actual FacetValues.
    """
    from sqlalchemy import select

    from app.models import FacetType, FacetValue
    from app.models.facet_value import FacetValueSourceType

    service = AttachmentService(session)
    attachment = await service.get_attachment(attachment_id)

    if not attachment or attachment.entity_id != entity_id:
        raise HTTPException(status_code=404, detail="Attachment nicht gefunden")

    if not attachment.analysis_result:
        raise HTTPException(status_code=400, detail="Keine Analyse-Ergebnisse vorhanden")

    suggestions = attachment.analysis_result.get("facet_suggestions", [])
    if not suggestions:
        raise HTTPException(status_code=400, detail="Keine Facet-Vorschlaege vorhanden")

    # Validate indices
    valid_indices = [i for i in facet_indices if 0 <= i < len(suggestions)]
    if not valid_indices:
        raise HTTPException(status_code=400, detail="Keine gueltigen Indizes angegeben")

    # Get facet types for validation
    ft_ids = set()
    for idx in valid_indices:
        suggestion = suggestions[idx]
        if "facet_type_id" in suggestion:
            ft_ids.add(UUID(suggestion["facet_type_id"]))
        elif "facet_type_slug" in suggestion:
            # Need to look up by slug
            pass

    # Load facet types by slug
    slugs = [
        suggestions[idx].get("facet_type_slug") for idx in valid_indices if suggestions[idx].get("facet_type_slug")
    ]
    ft_result = await session.execute(select(FacetType).where(FacetType.slug.in_(slugs)))
    facet_types_by_slug = {ft.slug: ft for ft in ft_result.scalars().all()}

    # Load facet types by ID
    if ft_ids:
        ft_id_result = await session.execute(select(FacetType).where(FacetType.id.in_(ft_ids)))
        facet_types_by_id = {str(ft.id): ft for ft in ft_id_result.scalars().all()}
    else:
        facet_types_by_id = {}

    created = []
    errors = []
    facet_values_for_embedding = []

    for idx in valid_indices:
        suggestion = suggestions[idx]
        try:
            # Resolve facet type
            ft = None
            if "facet_type_id" in suggestion:
                ft = facet_types_by_id.get(suggestion["facet_type_id"])
            if not ft and "facet_type_slug" in suggestion:
                ft = facet_types_by_slug.get(suggestion["facet_type_slug"])

            if not ft:
                errors.append(f"Facet-Typ nicht gefunden fuer Index {idx}")
                continue

            # Create facet value
            value = suggestion.get("value", {})
            text_repr = (
                suggestion.get("text_representation") or str(value.get("text", value.get("description", "")))[:500]
            )

            # Check for semantically similar FacetValues (AI-based)
            from app.utils.similarity import find_similar_facet_values

            similar_values = await find_similar_facet_values(
                session,
                entity_id=entity_id,
                facet_type_id=ft.id,
                text_representation=text_repr,
                threshold=0.85,
            )
            if similar_values:
                existing_fv, score, reason = similar_values[0]
                errors.append(f"Index {idx}: Ähnlicher FacetValue existiert bereits - {reason}")
                continue

            facet_value = FacetValue(
                entity_id=entity_id,
                facet_type_id=ft.id,
                value=value,
                text_representation=text_repr,
                confidence_score=suggestion.get("confidence", 0.7),
                source_type=FacetValueSourceType.ATTACHMENT,
                source_attachment_id=attachment_id,
                ai_model_used=attachment.ai_model_used,
            )
            session.add(facet_value)
            await session.flush()

            # Track for embedding generation
            facet_values_for_embedding.append((facet_value, text_repr))

            created.append(
                {
                    "facet_type": ft.name,
                    "text": text_repr[:100],
                }
            )

        except Exception as e:
            errors.append(f"Fehler bei Index {idx}: {str(e)}")

    # Generate embeddings for created facet values
    from app.utils.similarity import generate_embedding

    for facet_value, text_repr in facet_values_for_embedding:
        embedding = await generate_embedding(text_repr)
        if embedding:
            facet_value.text_embedding = embedding

    await session.commit()

    return {
        "success": True,
        "created_count": len(created),
        "created": created,
        "errors": errors if errors else None,
    }
