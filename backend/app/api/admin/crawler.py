"""Admin API endpoints for crawler control."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.core.deps import require_editor, require_admin
from app.core.rate_limit import check_rate_limit
from app.models import CrawlJob, DataSource, Category, JobStatus, SourceStatus, SourceType, AITask, AITaskStatus, AITaskType, User
from app.schemas.crawl_job import (
    CrawlJobResponse,
    CrawlJobListResponse,
    CrawlJobDetailResponse,
    CrawlJobStats,
    StartCrawlRequest,
    StartCrawlResponse,
    CrawlerStatusResponse,
    JobLogResponse,
    JobLogEntry,
    RunningJobInfo,
    RunningJobsResponse,
    AITaskInfo,
    AITaskListResponse,
    RunningAITasksResponse,
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
    _: User = Depends(require_editor),
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

    # Batch fetch sources and categories to avoid N+1 queries
    source_ids = list({job.source_id for job in jobs if job.source_id})
    category_ids = list({job.category_id for job in jobs if job.category_id})

    sources_dict = {}
    categories_dict = {}

    if source_ids:
        sources_result = await session.execute(
            select(DataSource).where(DataSource.id.in_(source_ids))
        )
        sources_dict = {s.id: s for s in sources_result.scalars().all()}

    if category_ids:
        categories_result = await session.execute(
            select(Category).where(Category.id.in_(category_ids))
        )
        categories_dict = {c.id: c for c in categories_result.scalars().all()}

    # Enrich with names
    items = []
    for job in jobs:
        source = sources_dict.get(job.source_id)
        category = categories_dict.get(job.category_id)

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
    _: User = Depends(require_editor),
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
    crawl_request: StartCrawlRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
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
    # Rate limit: 5 crawl starts per minute (resource intensive)
    await check_rate_limit(http_request, "crawler_start", identifier=str(current_user.id))

    from workers.crawl_tasks import create_crawl_job

    job_ids = []

    if crawl_request.source_ids:
        # Crawl specific sources - create jobs for ALL assigned categories
        for source_id in crawl_request.source_ids:
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
        if crawl_request.category_id:
            category = await session.get(Category, crawl_request.category_id)
            if not category:
                raise NotFoundError("Category", str(crawl_request.category_id))
            # Join with junction table to find sources linked to this category
            query = (
                select(DataSource)
                .join(DataSourceCategory, DataSource.id == DataSourceCategory.data_source_id)
                .where(DataSourceCategory.category_id == crawl_request.category_id)
            )

        # Country filter
        if crawl_request.country:
            query = query.where(DataSource.country == crawl_request.country.upper())

        # Status filter
        if crawl_request.status:
            try:
                status_enum = SourceStatus(crawl_request.status)
                query = query.where(DataSource.status == status_enum)
            except ValueError:
                raise ValidationError(f"Invalid status: {crawl_request.status}")
        else:
            # Default: only active/pending sources
            query = query.where(DataSource.status.in_([SourceStatus.ACTIVE, SourceStatus.PENDING]))

        # Source type filter
        if crawl_request.source_type:
            try:
                type_enum = SourceType(crawl_request.source_type)
                query = query.where(DataSource.source_type == type_enum)
            except ValueError:
                raise ValidationError(f"Invalid source type: {crawl_request.source_type}")

        # Search filter
        if crawl_request.search:
            search_term = f"%{crawl_request.search}%"
            query = query.where(
                DataSource.name.ilike(search_term) |
                DataSource.base_url.ilike(search_term)
            )

        # Apply limit
        if crawl_request.limit:
            query = query.limit(crawl_request.limit)

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
            cat_id = crawl_request.category_id or source.category_id
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
    _: User = Depends(require_editor),
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
    _: User = Depends(require_editor),
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
    _: User = Depends(require_admin),
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
    from sqlalchemy import delete
    for doc_id in document_ids:
        await session.execute(
            delete(ExtractedData).where(ExtractedData.document_id == UUID(doc_id))
        )

    # Queue for re-analysis
    for doc_id in document_ids:
        analyze_document.delay(doc_id)

    await session.commit()

    return MessageResponse(
        message=f"Queued {len(document_ids)} documents for re-analysis"
    )


@router.get("/status", response_model=CrawlerStatusResponse)
async def get_crawler_status(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Get current crawler status (running jobs, queued jobs, etc.)."""
    from datetime import date
    from workers.celery_app import celery_app

    running_jobs = (await session.execute(
        select(func.count()).where(CrawlJob.status == JobStatus.RUNNING)
    )).scalar() or 0

    pending_jobs = (await session.execute(
        select(func.count()).where(CrawlJob.status == JobStatus.PENDING)
    )).scalar() or 0

    # Jobs completed/failed today
    today = date.today()
    completed_today = (await session.execute(
        select(func.count()).where(
            CrawlJob.status == JobStatus.COMPLETED,
            func.date(CrawlJob.completed_at) == today
        )
    )).scalar() or 0

    failed_today = (await session.execute(
        select(func.count()).where(
            CrawlJob.status == JobStatus.FAILED,
            func.date(CrawlJob.completed_at) == today
        )
    )).scalar() or 0

    # Last completed job
    last_completed = (await session.execute(
        select(CrawlJob.completed_at)
        .where(CrawlJob.status == JobStatus.COMPLETED)
        .order_by(CrawlJob.completed_at.desc())
        .limit(1)
    )).scalar()

    # Get Celery worker status
    celery_connected = False
    try:
        inspector = celery_app.control.inspect()
        active_tasks = inspector.active() or {}
        celery_connected = len(active_tasks) > 0 or inspector.ping() is not None
    except Exception:
        celery_connected = False

    # Determine overall status
    if running_jobs > 0:
        status = "crawling"
    elif pending_jobs > 0:
        status = "pending"
    else:
        status = "idle"

    return CrawlerStatusResponse(
        status=status,
        running_jobs=running_jobs,
        pending_jobs=pending_jobs,
        completed_today=completed_today,
        failed_today=failed_today,
        last_completed_at=last_completed,
        celery_connected=celery_connected,
    )


@router.get("/jobs/{job_id}/log", response_model=JobLogResponse)
async def get_job_log(
    job_id: UUID,
    limit: int = Query(default=30, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Get live crawl log for a running job."""
    from datetime import datetime
    from app.services.crawler_progress import crawler_progress

    job = await session.get(CrawlJob, job_id)
    if not job:
        raise NotFoundError("Crawl Job", str(job_id))

    # Get recent log entries from Redis
    raw_entries = await crawler_progress.get_log(job_id, limit=limit + 1)
    has_more = len(raw_entries) > limit
    raw_entries = raw_entries[:limit]

    # Convert to JobLogEntry format
    entries = []
    for entry in raw_entries:
        entries.append(JobLogEntry(
            timestamp=datetime.fromisoformat(entry.get("timestamp", datetime.now().isoformat())),
            level=entry.get("level", "INFO"),
            message=entry.get("message", entry.get("url", "")),
            details=entry.get("details"),
        ))

    return JobLogResponse(
        job_id=job_id,
        entries=entries,
        total=len(entries),
        has_more=has_more,
    )


@router.get("/running", response_model=RunningJobsResponse)
async def get_running_jobs(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Get all currently running crawl jobs with live progress."""
    from app.services.crawler_progress import crawler_progress

    result = await session.execute(
        select(CrawlJob).where(CrawlJob.status == JobStatus.RUNNING)
    )
    running_jobs = result.scalars().all()

    # Batch fetch sources and categories to avoid N+1 queries
    source_ids = list({job.source_id for job in running_jobs if job.source_id})
    category_ids = list({job.category_id for job in running_jobs if job.category_id})

    sources_dict = {}
    categories_dict = {}

    if source_ids:
        sources_result = await session.execute(
            select(DataSource).where(DataSource.id.in_(source_ids))
        )
        sources_dict = {s.id: s for s in sources_result.scalars().all()}

    if category_ids:
        categories_result = await session.execute(
            select(Category).where(Category.id.in_(category_ids))
        )
        categories_dict = {c.id: c for c in categories_result.scalars().all()}

    jobs = []
    for job in running_jobs:
        source = sources_dict.get(job.source_id)
        category = categories_dict.get(job.category_id)
        live_stats = await crawler_progress.get_stats(job.id)

        # Calculate progress percentage if we have total pages estimate
        progress_percent = None
        if live_stats.get("total_pages"):
            progress_percent = (live_stats.get("pages_crawled", 0) / live_stats["total_pages"]) * 100

        jobs.append(RunningJobInfo(
            id=job.id,
            source_id=job.source_id,
            source_name=source.name if source else None,
            category_id=job.category_id,
            category_name=category.name if category else None,
            status=job.status.value,
            started_at=job.started_at,
            pages_crawled=live_stats.get("pages_crawled", job.pages_crawled),
            documents_found=live_stats.get("documents_found", job.documents_found),
            progress_percent=progress_percent,
            celery_task_id=job.celery_task_id,
        ))

    return RunningJobsResponse(
        jobs=jobs,
        total=len(jobs),
    )


@router.get("/ai-tasks", response_model=AITaskListResponse)
async def list_ai_tasks(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status: Optional[AITaskStatus] = Query(default=None),
    task_type: Optional[AITaskType] = Query(default=None),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
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

    # Batch fetch processes to avoid N+1 queries
    process_ids = list({task.process_id for task in tasks if task.process_id})
    processes_dict = {}
    if process_ids:
        processes_result = await session.execute(
            select(PySisProcess).where(PySisProcess.id.in_(process_ids))
        )
        processes_dict = {p.id: p for p in processes_result.scalars().all()}

    # Enrich with process info
    items = []
    for task in tasks:
        source_name = None
        category_name = None
        if task.process_id:
            process = processes_dict.get(task.process_id)
            if process:
                source_name = process.name
                category_name = process.entity_name

        items.append(AITaskInfo(
            id=task.id,
            task_type=task.task_type.value,
            status=task.status.value,
            source_name=source_name,
            category_name=category_name,
            created_at=task.scheduled_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            error_message=task.error_message,
            progress_percent=task.progress_percent,
            celery_task_id=task.celery_task_id,
        ))

    return AITaskListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.get("/ai-tasks/running", response_model=RunningAITasksResponse)
async def get_running_ai_tasks(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Get all currently running AI tasks."""
    from app.models.pysis import PySisProcess

    result = await session.execute(
        select(AITask).where(AITask.status == AITaskStatus.RUNNING)
    )
    running_tasks = result.scalars().all()

    # Batch fetch processes to avoid N+1 queries
    process_ids = list({task.process_id for task in running_tasks if task.process_id})
    processes_dict = {}
    if process_ids:
        processes_result = await session.execute(
            select(PySisProcess).where(PySisProcess.id.in_(process_ids))
        )
        processes_dict = {p.id: p for p in processes_result.scalars().all()}

    tasks = []
    for task in running_tasks:
        source_name = None
        category_name = None
        if task.process_id:
            process = processes_dict.get(task.process_id)
            if process:
                source_name = process.name
                category_name = process.entity_name

        tasks.append(AITaskInfo(
            id=task.id,
            task_type=task.task_type.value,
            status=task.status.value,
            source_name=source_name,
            category_name=category_name,
            created_at=task.scheduled_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            error_message=task.error_message,
            progress_percent=task.progress_percent,
            celery_task_id=task.celery_task_id,
        ))

    return RunningAITasksResponse(
        tasks=tasks,
        total=len(tasks),
    )


@router.post("/ai-tasks/{task_id}/cancel", response_model=MessageResponse)
async def cancel_ai_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Cancel a running AI task."""
    task = await session.get(AITask, task_id)
    if not task:
        raise NotFoundError("AI Task", str(task_id))

    if task.status != AITaskStatus.RUNNING:
        raise ValidationError("Can only cancel running tasks")

    # Revoke Celery task - import here to avoid issues when Celery isn't running
    if task.celery_task_id:
        from workers.celery_app import celery_app
        celery_app.control.revoke(task.celery_task_id, terminate=True)

    task.status = AITaskStatus.CANCELLED
    await session.commit()

    return MessageResponse(message="AI Task cancelled")


@router.post("/documents/{document_id}/process", response_model=MessageResponse)
async def process_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
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
    _: User = Depends(require_editor),
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
    _: User = Depends(require_admin),
):
    """Trigger processing for all pending documents."""
    from workers.processing_tasks import process_pending_documents

    process_pending_documents.delay()

    return MessageResponse(message="Processing task queued")


@router.post("/documents/stop-all", response_model=MessageResponse)
async def stop_all_processing(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
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
    _: User = Depends(require_admin),
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
