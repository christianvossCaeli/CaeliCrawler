"""Public API endpoints for data export."""

import csv
import io
import ipaddress
import json
import os
import socket
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import ExtractedData, Document, DataSource, DataSourceCategory, Category
from app.models.export_job import ExportJob
from app.models.user import User
from app.core.deps import get_current_user

router = APIRouter()

# Export directory (should match workers/export_tasks.py)
EXPORT_DIR = os.environ.get("EXPORT_DIR", "/tmp/exports")


# =============================================================================
# Pydantic Models for Async Export
# =============================================================================

class AsyncExportRequest(BaseModel):
    """Request body for starting an async export."""
    entity_type: str = "municipality"
    format: str = "json"  # json, csv, excel
    location_filter: Optional[str] = None
    facet_types: Optional[List[str]] = None
    position_keywords: Optional[List[str]] = None
    country: Optional[str] = None
    include_facets: bool = True
    filename: Optional[str] = None


class ExportJobResponse(BaseModel):
    """Response for export job status."""
    id: str
    status: str
    export_format: str
    total_records: Optional[int]
    processed_records: Optional[int]
    progress_percent: Optional[int]
    progress_message: Optional[str]
    file_size: Optional[int]
    error_message: Optional[str]
    created_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    is_downloadable: bool


# =============================================================================
# SSRF Protection
# =============================================================================

# Blocked IP ranges for SSRF protection
BLOCKED_IP_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),      # Localhost
    ipaddress.ip_network("10.0.0.0/8"),       # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),    # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),   # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),   # Link-local (AWS/Azure/GCP metadata)
    ipaddress.ip_network("0.0.0.0/8"),        # Current network
    ipaddress.ip_network("100.64.0.0/10"),    # Carrier-grade NAT
    ipaddress.ip_network("192.0.0.0/24"),     # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),     # TEST-NET-1
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),   # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),      # Multicast
    ipaddress.ip_network("240.0.0.0/4"),      # Reserved
]


def validate_webhook_url(url: str) -> Tuple[bool, str]:
    """
    Validate URL for SSRF protection.

    Returns (is_safe, error_message).
    """
    try:
        parsed = urlparse(url)

        # Only allow https for webhooks (security best practice)
        if parsed.scheme != "https":
            return False, "Only HTTPS URLs are allowed for webhooks"

        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid URL: no hostname"

        # Block localhost variations
        blocked_hostnames = {"localhost", "127.0.0.1", "::1", "0.0.0.0", "[::1]"}
        if hostname.lower() in blocked_hostnames:
            return False, "Localhost URLs are not allowed"

        # Block internal hostnames
        if hostname.endswith(".local") or hostname.endswith(".internal"):
            return False, "Internal hostnames are not allowed"

        # Try to resolve and check IP
        try:
            ip = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip)

            for blocked_range in BLOCKED_IP_RANGES:
                if ip_obj in blocked_range:
                    return False, "URL resolves to blocked IP range (internal network)"
        except socket.gaierror:
            # Can't resolve - allow but log warning
            pass

        return True, ""

    except Exception as e:
        return False, f"Invalid URL: {str(e)}"


async def _bulk_load_related_data(
    session: AsyncSession,
    extractions: List[ExtractedData]
) -> tuple[Dict[UUID, Document], Dict[UUID, DataSource], Dict[UUID, Category]]:
    """Bulk-load all related documents, sources, and categories for extractions.

    Returns dictionaries mapping IDs to their respective objects.
    This eliminates N+1 query problems by loading all data in 3 queries instead of 3N.
    """
    if not extractions:
        return {}, {}, {}

    # Collect all unique IDs
    doc_ids = {ext.document_id for ext in extractions if ext.document_id}
    cat_ids = {ext.category_id for ext in extractions if ext.category_id}

    # Bulk-load documents with their sources (single query with join)
    docs_result = await session.execute(
        select(Document)
        .options(selectinload(Document.source))
        .where(Document.id.in_(doc_ids))
    )
    docs_by_id: Dict[UUID, Document] = {doc.id: doc for doc in docs_result.scalars().all()}

    # Extract sources from loaded documents
    sources_by_id: Dict[UUID, DataSource] = {
        doc.source.id: doc.source
        for doc in docs_by_id.values()
        if doc.source
    }

    # Bulk-load categories
    cats_result = await session.execute(
        select(Category).where(Category.id.in_(cat_ids))
    )
    cats_by_id: Dict[UUID, Category] = {cat.id: cat for cat in cats_result.scalars().all()}

    return docs_by_id, sources_by_id, cats_by_id


@router.get("/json")
async def export_json(
    category_id: Optional[UUID] = Query(default=None),
    source_id: Optional[UUID] = Query(default=None),
    min_confidence: Optional[float] = Query(default=None, ge=0, le=1),
    human_verified_only: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
):
    """Export extracted data as JSON."""
    query = select(ExtractedData)

    if category_id:
        query = query.where(ExtractedData.category_id == category_id)
    if source_id:
        query = query.join(Document).where(Document.source_id == source_id)
    if min_confidence is not None:
        query = query.where(ExtractedData.confidence_score >= min_confidence)
    if human_verified_only:
        query = query.where(ExtractedData.human_verified.is_(True))

    result = await session.execute(query)
    extractions = result.scalars().all()

    # Bulk-load all related data in 2-3 queries instead of 3N queries
    docs_by_id, sources_by_id, cats_by_id = await _bulk_load_related_data(
        session, extractions
    )

    export_data = []
    for ext in extractions:
        doc = docs_by_id.get(ext.document_id)
        source = sources_by_id.get(doc.source_id) if doc and doc.source_id else None
        category = cats_by_id.get(ext.category_id)

        export_data.append({
            "id": str(ext.id),
            "document_id": str(ext.document_id),
            "document_url": doc.original_url if doc else None,
            "document_title": doc.title if doc else None,
            "source_name": source.name if source else None,
            "category_name": category.name if category else None,
            "extraction_type": ext.extraction_type,
            "extracted_content": ext.final_content,
            "confidence_score": ext.confidence_score,
            "human_verified": ext.human_verified,
            "created_at": ext.created_at.isoformat(),
        })

    return StreamingResponse(
        iter([json.dumps(export_data, indent=2, ensure_ascii=False)]),
        media_type="application/json",
        headers={
            "Content-Disposition": "attachment; filename=caelichrawler_export.json"
        },
    )


@router.get("/csv")
async def export_csv(
    category_id: Optional[UUID] = Query(default=None),
    source_id: Optional[UUID] = Query(default=None),
    min_confidence: Optional[float] = Query(default=None, ge=0, le=1),
    human_verified_only: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
):
    """Export extracted data as CSV."""
    query = select(ExtractedData)

    if category_id:
        query = query.where(ExtractedData.category_id == category_id)
    if source_id:
        query = query.join(Document).where(Document.source_id == source_id)
    if min_confidence is not None:
        query = query.where(ExtractedData.confidence_score >= min_confidence)
    if human_verified_only:
        query = query.where(ExtractedData.human_verified.is_(True))

    result = await session.execute(query)
    extractions = result.scalars().all()

    # Bulk-load all related data in 2-3 queries instead of 3N queries
    docs_by_id, sources_by_id, cats_by_id = await _bulk_load_related_data(
        session, extractions
    )

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "id",
        "document_url",
        "document_title",
        "source_name",
        "category_name",
        "extraction_type",
        "confidence_score",
        "human_verified",
        "extracted_content",
        "created_at",
    ])

    for ext in extractions:
        doc = docs_by_id.get(ext.document_id)
        source = sources_by_id.get(doc.source_id) if doc and doc.source_id else None
        category = cats_by_id.get(ext.category_id)

        writer.writerow([
            str(ext.id),
            doc.original_url if doc else "",
            doc.title if doc else "",
            source.name if source else "",
            category.name if category else "",
            ext.extraction_type,
            ext.confidence_score or "",
            ext.human_verified,
            json.dumps(ext.final_content, ensure_ascii=False),
            ext.created_at.isoformat(),
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=caelichrawler_export.csv"
        },
    )


@router.get("/changes")
async def get_changes_feed(
    since: Optional[str] = Query(default=None, description="ISO datetime to get changes since"),
    category_id: Optional[UUID] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
):
    """Get a feed of recent changes (for polling)."""
    from datetime import datetime, timezone
    from app.models import ChangeLog

    query = select(ChangeLog)

    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            query = query.where(ChangeLog.detected_at > since_dt)
        except ValueError:
            pass

    if category_id:
        # Filter via junction table (N:M relationship)
        query = (
            query
            .join(DataSource, ChangeLog.source_id == DataSource.id)
            .join(DataSourceCategory, DataSource.id == DataSourceCategory.data_source_id)
            .where(DataSourceCategory.category_id == category_id)
        )

    query = query.order_by(ChangeLog.detected_at.desc()).limit(limit)

    result = await session.execute(query)
    changes = result.scalars().all()

    return {
        "changes": [
            {
                "id": str(c.id),
                "source_id": str(c.source_id),
                "change_type": c.change_type.value,
                "affected_url": c.affected_url,
                "detected_at": c.detected_at.isoformat(),
                "details": c.details,
            }
            for c in changes
        ],
        "count": len(changes),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/webhook/test")
async def test_webhook(
    url: str = Query(..., description="Webhook URL to test"),
    current_user: User = Depends(get_current_user),  # Require authentication
):
    """
    Test a webhook endpoint.

    **Security:**
    - Requires authentication
    - Only HTTPS URLs allowed
    - Internal/private IP ranges are blocked (SSRF protection)
    """
    import httpx

    # SSRF Protection: Validate URL before making request
    is_safe, error_msg = validate_webhook_url(url)
    if not is_safe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid webhook URL: {error_msg}",
        )

    test_payload = {
        "event": "test",
        "message": "This is a test webhook from CaeliCrawler",
        "timestamp": "2024-01-01T00:00:00Z",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=test_payload,
                timeout=10,
            )
            return {
                "success": response.is_success,
                "status_code": response.status_code,
                "response": response.text[:500] if response.text else None,
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# =============================================================================
# Async Export Endpoints
# =============================================================================

@router.post("/async", response_model=ExportJobResponse)
async def start_async_export(
    request: AsyncExportRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Start an asynchronous export job.

    This endpoint creates an export job that runs in the background,
    suitable for large datasets (>5000 records).

    Use GET /export/async/{job_id} to check status.
    Use GET /export/async/{job_id}/download to download when complete.
    """
    from uuid import uuid4
    from workers.export_tasks import async_entity_export

    # Create export job record
    job_id = uuid4()
    export_config = {
        "format": request.format,
        "query_filter": {
            "entity_type": request.entity_type,
            "location_filter": request.location_filter,
            "facet_types": request.facet_types or [],
            "position_keywords": request.position_keywords or [],
            "country": request.country,
        },
        "include_facets": request.include_facets,
        "filename": request.filename or f"export_{job_id}",
    }

    export_job = ExportJob(
        id=job_id,
        user_id=current_user.id,
        export_config=export_config,
        export_format=request.format,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    session.add(export_job)
    await session.commit()

    # Start Celery task
    task = async_entity_export.delay(
        str(job_id),
        export_config,
        str(current_user.id),
    )

    # Update job with task ID
    await session.execute(
        update(ExportJob)
        .where(ExportJob.id == job_id)
        .values(celery_task_id=task.id)
    )
    await session.commit()

    await session.refresh(export_job)

    return ExportJobResponse(**export_job.to_dict())


@router.get("/async/{job_id}", response_model=ExportJobResponse)
async def get_export_job_status(
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get the status of an export job.

    Returns progress information while running, or download info when complete.
    """
    result = await session.execute(
        select(ExportJob).where(ExportJob.id == job_id)
    )
    export_job = result.scalar_one_or_none()

    if not export_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export job not found",
        )

    # Check ownership
    if export_job.user_id and export_job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this export job",
        )

    # If job is processing, try to get progress from Celery
    if export_job.status == "processing" and export_job.celery_task_id:
        try:
            from workers.celery_app import celery_app
            task_result = celery_app.AsyncResult(export_job.celery_task_id)
            if task_result.state == "PROGRESS":
                meta = task_result.info or {}
                export_job.progress_percent = meta.get("progress", 0)
                export_job.progress_message = meta.get("message", "")
        except Exception:
            pass

    return ExportJobResponse(**export_job.to_dict())


@router.get("/async/{job_id}/download")
async def download_export(
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Download a completed export file.

    Returns the exported file if the job is complete.
    """
    result = await session.execute(
        select(ExportJob).where(ExportJob.id == job_id)
    )
    export_job = result.scalar_one_or_none()

    if not export_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export job not found",
        )

    # Check ownership
    if export_job.user_id and export_job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this export job",
        )

    if export_job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Export is not ready. Status: {export_job.status}",
        )

    if not export_job.file_path or not os.path.exists(export_job.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file not found. It may have expired.",
        )

    # Determine content type
    content_types = {
        "json": "application/json",
        "csv": "text/csv",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    content_type = content_types.get(export_job.export_format, "application/octet-stream")

    # Get filename from config
    filename = os.path.basename(export_job.file_path)

    return FileResponse(
        path=export_job.file_path,
        media_type=content_type,
        filename=filename,
    )


@router.delete("/async/{job_id}")
async def cancel_export_job(
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Cancel a running export job.
    """
    result = await session.execute(
        select(ExportJob).where(ExportJob.id == job_id)
    )
    export_job = result.scalar_one_or_none()

    if not export_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export job not found",
        )

    # Check ownership
    if export_job.user_id and export_job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this export job",
        )

    if export_job.is_finished:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel a finished job. Status: {export_job.status}",
        )

    # Revoke Celery task if running
    if export_job.celery_task_id:
        try:
            from workers.celery_app import celery_app
            celery_app.control.revoke(export_job.celery_task_id, terminate=True)
        except Exception:
            pass

    # Update status
    export_job.status = "cancelled"
    export_job.completed_at = datetime.now(timezone.utc)
    await session.commit()

    return {"message": "Export job cancelled", "job_id": str(job_id)}


@router.get("/async", response_model=List[ExportJobResponse])
async def list_export_jobs(
    status_filter: Optional[str] = Query(default=None, description="Filter by status"),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    List export jobs for the current user.
    """
    query = select(ExportJob).where(ExportJob.user_id == current_user.id)

    if status_filter:
        query = query.where(ExportJob.status == status_filter)

    query = query.order_by(ExportJob.created_at.desc()).limit(limit)

    result = await session.execute(query)
    jobs = result.scalars().all()

    return [ExportJobResponse(**job.to_dict()) for job in jobs]
