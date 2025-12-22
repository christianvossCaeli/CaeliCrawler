"""Admin API endpoints for document processing operations."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.core.deps import require_editor, require_admin
from app.core.audit import AuditContext
from app.models.audit_log import AuditAction
from app.models import Document, ProcessingStatus, User
from app.schemas.common import MessageResponse
from app.core.exceptions import NotFoundError, ValidationError

router = APIRouter()


@router.post("/documents/{document_id}/process", response_model=MessageResponse)
async def process_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Manually trigger processing for a single document."""
    from workers.processing_tasks import process_document as process_doc_task

    document = await session.get(Document, document_id)
    if not document:
        raise NotFoundError("Document", str(document_id))

    # Reset status if failed/filtered
    if document.processing_status in (ProcessingStatus.FAILED, ProcessingStatus.FILTERED):
        document.processing_status = ProcessingStatus.PENDING
        document.processing_error = None
        await session.commit()

    # Queue for processing
    process_doc_task.delay(str(document_id))

    return MessageResponse(message="Document queued for processing")


@router.post("/documents/{document_id}/analyze", response_model=MessageResponse)
async def analyze_document(
    document_id: UUID,
    skip_relevance_check: bool = Query(default=False, description="Skip relevance pre-filter"),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Manually trigger AI analysis for a single document."""
    from workers.ai_tasks import analyze_document as analyze_doc_task

    document = await session.get(Document, document_id)
    if not document:
        raise NotFoundError("Document", str(document_id))

    if not document.raw_text:
        raise ValidationError("Document has no extracted text - process it first")

    # Reset filtered status if skipping relevance check
    if skip_relevance_check and document.processing_status == ProcessingStatus.FILTERED:
        document.processing_status = ProcessingStatus.COMPLETED
        document.processing_error = None
        await session.commit()

    # Queue for AI analysis
    analyze_doc_task.delay(str(document_id), skip_relevance_check=skip_relevance_check)

    return MessageResponse(message="Document queued for AI analysis")


@router.post("/documents/process-pending", response_model=MessageResponse)
async def process_all_pending(
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Trigger processing for all pending documents."""
    from workers.processing_tasks import process_pending_documents

    # Count pending documents for audit
    pending_count = (await session.execute(
        select(func.count()).where(Document.processing_status == ProcessingStatus.PENDING)
    )).scalar() or 0

    process_pending_documents.delay()

    async with AuditContext(session, current_user, request) as audit:
        audit.track_action(
            action=AuditAction.CRAWLER_START,
            entity_type="ProcessingJob",
            entity_name="Process All Pending",
            changes={
                "pending_documents": pending_count,
                "action": "process_pending",
            },
        )
        await session.commit()

    return MessageResponse(message="Processing task queued")


@router.post("/documents/stop-all", response_model=MessageResponse)
async def stop_all_processing(
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """
    Stop all document processing.

    - Purges pending processing tasks from queue
    - Resets PROCESSING documents back to PENDING
    """
    from workers.celery_app import celery_app

    # Purge pending tasks from the processing queue
    celery_app.control.purge()

    # Reset documents stuck in PROCESSING back to PENDING
    result = await session.execute(
        update(Document)
        .where(Document.processing_status == ProcessingStatus.PROCESSING)
        .values(processing_status=ProcessingStatus.PENDING)
        .returning(Document.id)
    )
    reset_count = len(result.fetchall())

    async with AuditContext(session, current_user, request) as audit:
        audit.track_action(
            action=AuditAction.CRAWLER_STOP,
            entity_type="ProcessingJob",
            entity_name="Stop All Processing",
            changes={
                "action": "stop_all",
                "documents_reset": reset_count,
                "queue_purged": True,
            },
        )
        await session.commit()

    return MessageResponse(
        message=f"Processing stopped. {reset_count} documents reset to pending.",
        data={"reset_count": reset_count}
    )


@router.post("/documents/reanalyze-filtered", response_model=MessageResponse)
async def reanalyze_filtered_documents(
    request: Request,
    limit: int = Query(default=100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """
    Re-analyze all FILTERED documents, skipping relevance check.

    Useful when keywords don't match but you want AI analysis anyway.
    """
    from workers.ai_tasks import analyze_document as analyze_doc_task

    # Get filtered documents with raw_text
    result = await session.execute(
        select(Document.id)
        .where(Document.processing_status == ProcessingStatus.FILTERED)
        .where(Document.raw_text.isnot(None))
        .limit(limit)
    )
    doc_ids = [row[0] for row in result.fetchall()]

    # Queue for AI analysis with skip_relevance_check
    for doc_id in doc_ids:
        analyze_doc_task.delay(str(doc_id), skip_relevance_check=True)

    async with AuditContext(session, current_user, request) as audit:
        audit.track_action(
            action=AuditAction.CRAWLER_START,
            entity_type="ReanalysisJob",
            entity_name="Reanalyze Filtered",
            changes={
                "documents_queued": len(doc_ids),
                "limit": limit,
                "mode": "filtered_skip_relevance",
            },
        )
        await session.commit()

    return MessageResponse(
        message=f"Queued {len(doc_ids)} filtered documents for re-analysis",
        data={"queued_count": len(doc_ids)}
    )
