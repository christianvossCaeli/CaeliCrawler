"""Admin API endpoints for crawler control."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import CrawlJob, DataSource, Category, JobStatus, SourceStatus, SourceType, AITask, AITaskStatus, AITaskType
from app.schemas.crawl_job import (
    CrawlJobResponse,
    CrawlJobListResponse,
    CrawlJobDetailResponse,
    CrawlJobStats,
    StartCrawlRequest,
    StartCrawlResponse,
)
from app.schemas.common import MessageResponse
from app.core.exceptions import NotFoundError, ValidationError

router = APIRouter()


@router.get("/jobs", response_model=CrawlJobListResponse)
async def list_jobs(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status: Optional[JobStatus] = Query(default=None),
    category_id: Optional[UUID] = Query(default=None),
    source_id: Optional[UUID] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """List all crawl jobs with pagination."""
    query = select(CrawlJob)

    if status:
        query = query.where(CrawlJob.status == status)
    if category_id:
        query = query.where(CrawlJob.category_id == category_id)
    if source_id:
        query = query.where(CrawlJob.source_id == source_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate (newest first)
    query = query.order_by(CrawlJob.scheduled_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    jobs = result.scalars().all()

    # Enrich with names
    items = []
    for job in jobs:
        source = await session.get(DataSource, job.source_id)
        category = await session.get(Category, job.category_id)

        item = CrawlJobResponse.model_validate(job)
        item.source_name = source.name if source else None
        item.category_name = category.name if category else None
        item.duration_seconds = job.duration_seconds
        items.append(item)

    return CrawlJobListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.get("/jobs/{job_id}", response_model=CrawlJobDetailResponse)
async def get_job(
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get detailed info about a crawl job."""
    job = await session.get(CrawlJob, job_id)
    if not job:
        raise NotFoundError("Crawl Job", str(job_id))

    source = await session.get(DataSource, job.source_id)
    category = await session.get(Category, job.category_id)

    response = CrawlJobDetailResponse.model_validate(job)
    response.source_name = source.name if source else None
    response.category_name = category.name if category else None
    response.duration_seconds = job.duration_seconds

    return response


@router.post("/start", response_model=StartCrawlResponse)
async def start_crawl(
    request: StartCrawlRequest,
    session: AsyncSession = Depends(get_session),
):
    """Start crawling for specific sources or a whole category.

    Supports multiple filter options:
    - source_ids: Specific sources to crawl
    - category_id: All sources in a category
    - country: Filter by country code (DE, GB, etc.)
    - status: Filter by source status
    - source_type: Filter by source type
    - search: Filter by name or URL
    - limit: Maximum number of sources to crawl
    """
    from workers.crawl_tasks import create_crawl_job

    job_ids = []

    if request.source_ids:
        # Crawl specific sources - create jobs for ALL assigned categories
        for source_id in request.source_ids:
            source = await session.get(DataSource, source_id)
            if not source:
                raise NotFoundError("Data Source", str(source_id))

            # Get all categories this source is assigned to via N:M relationship
            from app.models import DataSourceCategory
            cat_result = await session.execute(
                select(DataSourceCategory.category_id)
                .where(DataSourceCategory.data_source_id == source_id)
            )
            category_ids = [row[0] for row in cat_result.fetchall()]

            # If no N:M assignments, fall back to primary category
            if not category_ids:
                category_ids = [source.category_id]

            # Create a job for each category
            for cat_id in category_ids:
                create_crawl_job.delay(str(source_id), str(cat_id))
                job_ids.append(source_id)

    else:
        # Build query with filters
        from app.models import DataSourceCategory
        query = select(DataSource)

        # Category filter - use junction table (N:M relationship)
        if request.category_id:
            category = await session.get(Category, request.category_id)
            if not category:
                raise NotFoundError("Category", str(request.category_id))
            # Join with junction table to find sources linked to this category
            query = (
                select(DataSource)
                .join(DataSourceCategory, DataSource.id == DataSourceCategory.data_source_id)
                .where(DataSourceCategory.category_id == request.category_id)
            )

        # Country filter
        if request.country:
            query = query.where(DataSource.country == request.country.upper())

        # Status filter
        if request.status:
            try:
                status_enum = SourceStatus(request.status)
                query = query.where(DataSource.status == status_enum)
            except ValueError:
                raise ValidationError(f"Invalid status: {request.status}")
        else:
            # Default: only active/pending sources
            query = query.where(DataSource.status.in_([SourceStatus.ACTIVE, SourceStatus.PENDING]))

        # Source type filter
        if request.source_type:
            try:
                type_enum = SourceType(request.source_type)
                query = query.where(DataSource.source_type == type_enum)
            except ValueError:
                raise ValidationError(f"Invalid source type: {request.source_type}")

        # Search filter
        if request.search:
            search_term = f"%{request.search}%"
            query = query.where(
                DataSource.name.ilike(search_term) |
                DataSource.base_url.ilike(search_term)
            )

        # Apply limit
        if request.limit:
            query = query.limit(request.limit)

        # Execute query
        result = await session.execute(query)
        sources = result.scalars().all()

        if not sources:
            return StartCrawlResponse(
                jobs_created=0,
                job_ids=[],
                message="No sources found matching the filters",
            )

        for source in sources:
            # If filtering by category, use that category_id
            # Otherwise, fall back to legacy category_id (if set)
            cat_id = request.category_id or source.category_id
            if cat_id:
                create_crawl_job.delay(str(source.id), str(cat_id))
                job_ids.append(source.id)

    return StartCrawlResponse(
        jobs_created=len(job_ids),
        job_ids=job_ids,
        message=f"Started {len(job_ids)} crawl job(s)",
    )


@router.post("/jobs/{job_id}/cancel", response_model=MessageResponse)
async def cancel_job(
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Cancel a running crawl job."""
    from workers.celery_app import celery_app

    job = await session.get(CrawlJob, job_id)
    if not job:
        raise NotFoundError("Crawl Job", str(job_id))

    if job.status != JobStatus.RUNNING:
        raise ValidationError("Can only cancel running jobs")

    # Revoke Celery task
    if job.celery_task_id:
        celery_app.control.revoke(job.celery_task_id, terminate=True)

    job.status = JobStatus.CANCELLED
    await session.commit()

    return MessageResponse(message="Job cancelled")


@router.get("/stats", response_model=CrawlJobStats)
async def get_crawler_stats(
    session: AsyncSession = Depends(get_session),
):
    """Get overall crawler statistics."""
    from app.models import Document

    total_jobs = (await session.execute(select(func.count(CrawlJob.id)))).scalar()

    running_jobs = (await session.execute(
        select(func.count()).where(CrawlJob.status == JobStatus.RUNNING)
    )).scalar()

    completed_jobs = (await session.execute(
        select(func.count()).where(CrawlJob.status == JobStatus.COMPLETED)
    )).scalar()

    failed_jobs = (await session.execute(
        select(func.count()).where(CrawlJob.status == JobStatus.FAILED)
    )).scalar()

    total_documents = (await session.execute(select(func.count(Document.id)))).scalar()

    total_pages = (await session.execute(
        select(func.sum(CrawlJob.pages_crawled))
    )).scalar() or 0

    # Average duration of completed jobs
    avg_duration = (await session.execute(
        select(func.avg(
            func.extract('epoch', CrawlJob.completed_at) -
            func.extract('epoch', CrawlJob.started_at)
        )).where(
            CrawlJob.status == JobStatus.COMPLETED,
            CrawlJob.started_at.isnot(None),
            CrawlJob.completed_at.isnot(None),
        )
    )).scalar()

    return CrawlJobStats(
        total_jobs=total_jobs,
        running_jobs=running_jobs,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        total_documents=total_documents,
        total_pages_crawled=total_pages,
        avg_duration_seconds=float(avg_duration) if avg_duration else None,
    )


@router.post("/reanalyze", response_model=MessageResponse)
async def reanalyze_documents(
    category_id: Optional[UUID] = Query(default=None),
    reanalyze_all: bool = Query(default=False, description="Re-analyze all documents, not just low confidence"),
    session: AsyncSession = Depends(get_session),
):
    """
    Re-analyze documents with the updated AI prompt.

    - If category_id is provided, only re-analyzes documents in that category
    - If reanalyze_all=True, re-analyzes ALL documents (otherwise only low confidence)
    """
    from app.models import ExtractedData, Document
    from workers.ai_tasks import analyze_document

    # Build query
    query = select(ExtractedData.document_id).distinct()

    if category_id:
        query = query.where(ExtractedData.category_id == category_id)

    if not reanalyze_all:
        # Only low confidence (< 0.7)
        query = query.where(ExtractedData.confidence_score < 0.7)

    result = await session.execute(query)
    document_ids = [str(row[0]) for row in result.fetchall()]

    # Delete existing extractions
    for doc_id in document_ids:
        await session.execute(
            select(ExtractedData).where(ExtractedData.document_id == doc_id)
        )

    # Queue for re-analysis
    for doc_id in document_ids:
        analyze_document.delay(doc_id)

    await session.commit()

    return MessageResponse(
        message=f"Queued {len(document_ids)} documents for re-analysis"
    )


@router.get("/status", response_model=dict)
async def get_crawler_status(
    session: AsyncSession = Depends(get_session),
):
    """Get current crawler status (running jobs, queued jobs, etc.)."""
    from workers.celery_app import celery_app

    running_jobs = (await session.execute(
        select(CrawlJob).where(CrawlJob.status == JobStatus.RUNNING)
    )).scalars().all()

    pending_jobs = (await session.execute(
        select(CrawlJob).where(CrawlJob.status == JobStatus.PENDING)
    )).scalars().all()

    # Get Celery worker status
    try:
        inspector = celery_app.control.inspect()
        active_tasks = inspector.active() or {}
        reserved_tasks = inspector.reserved() or {}
        worker_count = len(active_tasks)
    except Exception:
        active_tasks = {}
        reserved_tasks = {}
        worker_count = 0

    return {
        "running_jobs": len(running_jobs),
        "pending_jobs": len(pending_jobs),
        "worker_count": worker_count,
        "active_tasks": sum(len(tasks) for tasks in active_tasks.values()),
        "queued_tasks": sum(len(tasks) for tasks in reserved_tasks.values()),
    }


@router.get("/jobs/{job_id}/log")
async def get_job_log(
    job_id: UUID,
    limit: int = Query(default=30, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Get live crawl log for a running job."""
    from app.services.crawler_progress import crawler_progress

    job = await session.get(CrawlJob, job_id)
    if not job:
        raise NotFoundError("Crawl Job", str(job_id))

    # Get recent log entries from Redis
    log_entries = await crawler_progress.get_log(job_id, limit=limit)
    current_url = await crawler_progress.get_current_url(job_id)

    source = await session.get(DataSource, job.source_id)

    return {
        "job_id": str(job_id),
        "source_name": source.name if source else None,
        "status": job.status.value,
        "current_url": current_url,
        "pages_crawled": job.pages_crawled,
        "documents_found": job.documents_found,
        "documents_new": job.documents_new,
        "error_count": job.error_count,
        "log_entries": log_entries,
    }


@router.get("/running")
async def get_running_jobs(
    session: AsyncSession = Depends(get_session),
):
    """Get all currently running crawl jobs with live progress."""
    from app.services.crawler_progress import crawler_progress

    result = await session.execute(
        select(CrawlJob).where(CrawlJob.status == JobStatus.RUNNING)
    )
    running_jobs = result.scalars().all()

    jobs = []
    for job in running_jobs:
        source = await session.get(DataSource, job.source_id)
        category = await session.get(Category, job.category_id)
        current_url = await crawler_progress.get_current_url(job.id)
        recent_log = await crawler_progress.get_log(job.id, limit=5)
        live_stats = await crawler_progress.get_stats(job.id)

        jobs.append({
            "id": str(job.id),
            "source_id": str(job.source_id),
            "source_name": source.name if source else None,
            "base_url": source.base_url if source else None,
            "category_id": str(job.category_id),
            "category_name": category.name if category else None,
            "status": job.status.value,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "pages_crawled": live_stats.get("pages_crawled", job.pages_crawled),
            "documents_found": live_stats.get("documents_found", job.documents_found),
            "documents_new": job.documents_new,
            "error_count": job.error_count,
            "current_url": current_url,
            "recent_urls": [e.get("url") for e in recent_log[:3]],
        })

    return {
        "running_count": len(jobs),
        "jobs": jobs,
    }


@router.get("/ai-tasks")
async def list_ai_tasks(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status: Optional[AITaskStatus] = Query(default=None),
    task_type: Optional[AITaskType] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """List all AI tasks with pagination."""
    from app.models.pysis import PySisProcess

    query = select(AITask)

    if status:
        query = query.where(AITask.status == status)
    if task_type:
        query = query.where(AITask.task_type == task_type)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate (newest first)
    query = query.order_by(AITask.scheduled_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    tasks = result.scalars().all()

    # Enrich with process info
    items = []
    for task in tasks:
        process_name = None
        location_name = None
        if task.process_id:
            process = await session.get(PySisProcess, task.process_id)
            if process:
                process_name = process.name
                location_name = process.location_name

        items.append({
            "id": str(task.id),
            "task_type": task.task_type.value,
            "status": task.status.value,
            "name": task.name,
            "description": task.description,
            "process_id": str(task.process_id) if task.process_id else None,
            "process_name": process_name,
            "location_name": location_name,
            "scheduled_at": task.scheduled_at.isoformat() if task.scheduled_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "progress_current": task.progress_current,
            "progress_total": task.progress_total,
            "progress_percent": task.progress_percent,
            "current_item": task.current_item,
            "fields_extracted": task.fields_extracted,
            "avg_confidence": task.avg_confidence,
            "duration_seconds": task.duration_seconds,
            "error_message": task.error_message,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page if per_page > 0 else 0,
    }


@router.get("/ai-tasks/running")
async def get_running_ai_tasks(
    session: AsyncSession = Depends(get_session),
):
    """Get all currently running AI tasks."""
    from app.models.pysis import PySisProcess

    result = await session.execute(
        select(AITask).where(AITask.status == AITaskStatus.RUNNING)
    )
    running_tasks = result.scalars().all()

    tasks = []
    for task in running_tasks:
        process_name = None
        location_name = None
        if task.process_id:
            process = await session.get(PySisProcess, task.process_id)
            if process:
                process_name = process.name
                location_name = process.location_name

        tasks.append({
            "id": str(task.id),
            "task_type": task.task_type.value,
            "name": task.name,
            "process_name": process_name,
            "location_name": location_name,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "progress_current": task.progress_current,
            "progress_total": task.progress_total,
            "progress_percent": task.progress_percent,
            "current_item": task.current_item,
            "duration_seconds": task.duration_seconds,
        })

    return {
        "running_count": len(tasks),
        "tasks": tasks,
    }


@router.post("/ai-tasks/{task_id}/cancel", response_model=MessageResponse)
async def cancel_ai_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Cancel a running AI task."""
    from workers.celery_app import celery_app

    task = await session.get(AITask, task_id)
    if not task:
        raise NotFoundError("AI Task", str(task_id))

    if task.status != AITaskStatus.RUNNING:
        raise ValidationError("Can only cancel running tasks")

    # Revoke Celery task
    if task.celery_task_id:
        celery_app.control.revoke(task.celery_task_id, terminate=True)

    task.status = AITaskStatus.CANCELLED
    await session.commit()

    return MessageResponse(message="AI Task cancelled")


@router.post("/documents/{document_id}/process", response_model=MessageResponse)
async def process_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Manually trigger processing for a single document."""
    from app.models import Document, ProcessingStatus
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
):
    """Manually trigger AI analysis for a single document."""
    from app.models import Document, ProcessingStatus
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
    session: AsyncSession = Depends(get_session),
):
    """Trigger processing for all pending documents."""
    from workers.processing_tasks import process_pending_documents

    process_pending_documents.delay()

    return MessageResponse(message="Processing task queued")


@router.post("/documents/stop-all", response_model=MessageResponse)
async def stop_all_processing(
    session: AsyncSession = Depends(get_session),
):
    """
    Stop all document processing.

    - Purges pending processing tasks from queue
    - Resets PROCESSING documents back to PENDING
    """
    from workers.celery_app import celery_app
    from sqlalchemy import update

    # Purge pending tasks from the processing queue
    celery_app.control.purge()

    # Reset documents stuck in PROCESSING back to PENDING
    from app.models import Document, ProcessingStatus

    result = await session.execute(
        update(Document)
        .where(Document.processing_status == ProcessingStatus.PROCESSING)
        .values(processing_status=ProcessingStatus.PENDING)
        .returning(Document.id)
    )
    reset_count = len(result.fetchall())
    await session.commit()

    return MessageResponse(
        message=f"Processing stopped. {reset_count} documents reset to pending.",
        data={"reset_count": reset_count}
    )


@router.post("/documents/reanalyze-filtered", response_model=MessageResponse)
async def reanalyze_filtered_documents(
    limit: int = Query(default=100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
):
    """
    Re-analyze all FILTERED documents, skipping relevance check.

    Useful when keywords don't match but you want AI analysis anyway.
    """
    from workers.ai_tasks import analyze_document as analyze_doc_task
    from app.models import Document, ProcessingStatus
    from sqlalchemy import select

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

    return MessageResponse(
        message=f"Queued {len(doc_ids)} filtered documents for re-analysis",
        data={"queued_count": len(doc_ids)}
    )
