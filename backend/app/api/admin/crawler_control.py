"""Admin API endpoints for crawler control operations."""

from datetime import date
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query, Request

logger = structlog.get_logger(__name__)
from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.audit import AuditContext  # noqa: E402
from app.core.deps import require_admin, require_editor  # noqa: E402
from app.core.exceptions import NotFoundError, ValidationError  # noqa: E402
from app.core.rate_limit import check_rate_limit  # noqa: E402
from app.database import get_session  # noqa: E402
from app.models import (  # noqa: E402
    Category,
    CrawlJob,
    DataSource,
    JobStatus,
    SourceStatus,
    SourceType,
    User,
)
from app.models.audit_log import AuditAction  # noqa: E402
from app.schemas.common import MessageResponse  # noqa: E402
from app.schemas.crawl_job import (  # noqa: E402
    CrawlerStatusResponse,
    CrawlJobStats,
    StartCrawlRequest,
    StartCrawlResponse,
)

router = APIRouter()


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

    from app.models import DataSourceCategory
    from workers.crawl_tasks import create_crawl_job

    job_ids = []

    if crawl_request.source_ids:
        # Crawl specific sources - create jobs for ALL assigned categories
        # Batch fetch all requested sources to avoid N+1 query
        sources_result = await session.execute(
            select(DataSource).where(DataSource.id.in_(crawl_request.source_ids))
        )
        sources = {s.id: s for s in sources_result.scalars().all()}

        # Check if all requested sources exist
        for source_id in crawl_request.source_ids:
            if source_id not in sources:
                raise NotFoundError("Data Source", str(source_id))

        # Batch fetch all category associations
        cat_result = await session.execute(
            select(DataSourceCategory.data_source_id, DataSourceCategory.category_id)
            .where(DataSourceCategory.data_source_id.in_(crawl_request.source_ids))
        )
        source_categories = {}
        for row in cat_result.fetchall():
            source_categories.setdefault(row[0], []).append(row[1])

        # Create jobs for each source
        for source_id in crawl_request.source_ids:
            source = sources[source_id]
            category_ids = source_categories.get(source_id, [])

            # If no N:M assignments found, skip source (no category = no crawl)
            if not category_ids:
                logger.warning(f"Source {source.name} has no category assignments, skipping")
                continue

            # Create a job for each category
            for cat_id in category_ids:
                create_crawl_job.delay(str(source_id), str(cat_id), str(current_user.id))
                job_ids.append(source_id)

    else:
        # Build query with filters
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
                raise ValidationError(f"Invalid status: {crawl_request.status}") from None
        else:
            # Default: only active/pending sources
            query = query.where(DataSource.status.in_([SourceStatus.ACTIVE, SourceStatus.PENDING]))

        # Source type filter
        if crawl_request.source_type:
            try:
                type_enum = SourceType(crawl_request.source_type)
                query = query.where(DataSource.source_type == type_enum)
            except ValueError:
                raise ValidationError(f"Invalid source type: {crawl_request.source_type}") from None

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

        # If filtering by specific category, use that for all sources
        if crawl_request.category_id:
            for source in sources:
                create_crawl_job.delay(str(source.id), str(crawl_request.category_id), str(current_user.id))
                job_ids.append(source.id)
        else:
            # Get N:M category assignments for all sources
            source_ids = [s.id for s in sources]
            cat_result = await session.execute(
                select(DataSourceCategory.data_source_id, DataSourceCategory.category_id)
                .where(DataSourceCategory.data_source_id.in_(source_ids))
            )
            source_categories = {}
            for row in cat_result.fetchall():
                source_categories.setdefault(row[0], []).append(row[1])

            for source in sources:
                category_ids = source_categories.get(source.id, [])
                if not category_ids:
                    logger.warning(f"Source {source.name} has no category assignments, skipping")
                    continue
                for cat_id in category_ids:
                    create_crawl_job.delay(str(source.id), str(cat_id), str(current_user.id))
                    job_ids.append(source.id)

    # Audit log for crawler start
    if job_ids:
        async with AuditContext(session, current_user, http_request) as audit:
            # Get category name if available
            category_name = None
            if crawl_request.category_id:
                cat = await session.get(Category, crawl_request.category_id)
                category_name = cat.name if cat else None

            audit.track_action(
                action=AuditAction.CRAWLER_START,
                entity_type="CrawlJob",
                entity_name=category_name or "Multiple Sources",
                changes={
                    "jobs_created": len(job_ids),
                    "category_id": str(crawl_request.category_id) if crawl_request.category_id else None,
                    "category_name": category_name,
                    "source_count": len(set(job_ids)),
                    "filters": {
                        "country": crawl_request.country,
                        "status": crawl_request.status,
                        "source_type": crawl_request.source_type,
                        "search": crawl_request.search,
                        "limit": crawl_request.limit,
                    },
                },
            )
            await session.commit()

    return StartCrawlResponse(
        jobs_created=len(job_ids),
        job_ids=job_ids,
        message=f"Started {len(job_ids)} crawl job(s)",
    )


@router.post("/jobs/{job_id}/retry", response_model=MessageResponse)
async def retry_job(
    job_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Retry a failed or cancelled crawl job by creating a new job with the same parameters."""
    from workers.crawl_tasks import create_crawl_job

    job = await session.get(CrawlJob, job_id)
    if not job:
        raise NotFoundError("Crawl Job", str(job_id))

    if job.status not in (JobStatus.FAILED, JobStatus.CANCELLED):
        raise ValidationError("Can only retry failed or cancelled jobs")

    # Get source and category for audit log
    source = await session.get(DataSource, job.source_id) if job.source_id else None
    category = await session.get(Category, job.category_id) if job.category_id else None

    # Create a new crawl job with the same source and category
    create_crawl_job.delay(str(job.source_id), str(job.category_id), str(current_user.id))

    async with AuditContext(session, current_user, request) as audit:
        audit.track_action(
            action=AuditAction.CRAWLER_START,
            entity_type="CrawlJob",
            entity_name=source.name if source else str(job_id),
            changes={
                "retry_of_job": str(job_id),
                "source_name": source.name if source else None,
                "category_name": category.name if category else None,
                "original_status": job.status.value,
            },
        )
        await session.commit()

    return MessageResponse(message="Job retry started")


@router.post("/jobs/{job_id}/cancel", response_model=MessageResponse)
async def cancel_job(
    job_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Cancel a running or pending crawl job."""
    from workers.celery_app import celery_app

    job = await session.get(CrawlJob, job_id)
    if not job:
        raise NotFoundError("Crawl Job", str(job_id))

    if job.status not in (JobStatus.RUNNING, JobStatus.PENDING):
        raise ValidationError("Can only cancel running or pending jobs")

    # Get source and category names for audit
    source = await session.get(DataSource, job.source_id) if job.source_id else None
    category = await session.get(Category, job.category_id) if job.category_id else None

    async with AuditContext(session, current_user, request) as audit:
        # Revoke Celery task if running
        if job.celery_task_id and job.status == JobStatus.RUNNING:
            celery_app.control.revoke(job.celery_task_id, terminate=True)

        job.status = JobStatus.CANCELLED

        audit.track_action(
            action=AuditAction.CRAWLER_STOP,
            entity_type="CrawlJob",
            entity_id=job.id,
            entity_name=source.name if source else str(job_id),
            changes={
                "cancelled": True,
                "source_name": source.name if source else None,
                "category_name": category.name if category else None,
                "pages_crawled": job.pages_crawled,
                "documents_found": job.documents_found,
            },
        )

        await session.commit()

    return MessageResponse(message="Job cancelled")


@router.delete("/jobs/{job_id}", response_model=MessageResponse)
async def delete_job(
    job_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Delete a completed, failed, or cancelled crawl job."""
    job = await session.get(CrawlJob, job_id)
    if not job:
        raise NotFoundError("Crawl Job", str(job_id))

    if job.status not in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        raise ValidationError("Can only delete completed, failed, or cancelled jobs")

    # Get source and category names for audit
    source = await session.get(DataSource, job.source_id) if job.source_id else None
    category = await session.get(Category, job.category_id) if job.category_id else None

    async with AuditContext(session, current_user, request) as audit:
        audit.track_action(
            action=AuditAction.DELETE,
            entity_type="CrawlJob",
            entity_id=job.id,
            entity_name=source.name if source else str(job_id),
            changes={
                "deleted": True,
                "status": job.status.value,
                "source_name": source.name if source else None,
                "category_name": category.name if category else None,
                "pages_crawled": job.pages_crawled,
                "documents_found": job.documents_found,
            },
        )

        await session.delete(job)
        await session.commit()

    return MessageResponse(message="Job deleted")


@router.get("/stats", response_model=CrawlJobStats)
async def get_crawler_stats(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Get overall crawler statistics (optimized: 3 queries instead of 7)."""
    from app.models import Document

    # Query 1: All job stats in one query using conditional aggregation
    job_stats = (await session.execute(
        select(
            func.count(CrawlJob.id).label("total"),
            func.count().filter(CrawlJob.status == JobStatus.RUNNING).label("running"),
            func.count().filter(CrawlJob.status == JobStatus.COMPLETED).label("completed"),
            func.count().filter(CrawlJob.status == JobStatus.FAILED).label("failed"),
            func.sum(CrawlJob.pages_crawled).label("total_pages"),
            func.avg(
                func.extract('epoch', CrawlJob.completed_at) -
                func.extract('epoch', CrawlJob.started_at)
            ).filter(
                CrawlJob.status == JobStatus.COMPLETED,
                CrawlJob.started_at.isnot(None),
                CrawlJob.completed_at.isnot(None),
            ).label("avg_duration"),
        )
    )).one()

    # Query 2: Total documents
    total_documents = (await session.execute(select(func.count(Document.id)))).scalar()

    return CrawlJobStats(
        total_jobs=job_stats.total or 0,
        running_jobs=job_stats.running or 0,
        completed_jobs=job_stats.completed or 0,
        failed_jobs=job_stats.failed or 0,
        total_documents=total_documents or 0,
        total_pages_crawled=job_stats.total_pages or 0,
        avg_duration_seconds=float(job_stats.avg_duration) if job_stats.avg_duration else None,
    )


@router.get("/status", response_model=CrawlerStatusResponse)
async def get_crawler_status(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Get current crawler status (optimized: 2 queries instead of 5)."""
    from workers.celery_app import celery_app

    today = date.today()

    # Query 1: All counts in one query using conditional aggregation
    job_counts = (await session.execute(
        select(
            func.count().filter(CrawlJob.status == JobStatus.RUNNING).label("running"),
            func.count().filter(CrawlJob.status == JobStatus.PENDING).label("pending"),
            func.count().filter(
                CrawlJob.status == JobStatus.COMPLETED,
                func.date(CrawlJob.completed_at) == today
            ).label("completed_today"),
            func.count().filter(
                CrawlJob.status == JobStatus.FAILED,
                func.date(CrawlJob.completed_at) == today
            ).label("failed_today"),
        )
    )).one()

    running_jobs = job_counts.running or 0
    pending_jobs = job_counts.pending or 0
    completed_today = job_counts.completed_today or 0
    failed_today = job_counts.failed_today or 0

    # Query 2: Last completed job (separate for ORDER BY + LIMIT)
    last_completed = (await session.execute(
        select(CrawlJob.completed_at)
        .where(CrawlJob.status == JobStatus.COMPLETED)
        .order_by(CrawlJob.completed_at.desc())
        .limit(1)
    )).scalar()

    # Get Celery worker status
    celery_connected = False
    worker_count = 0
    try:
        inspector = celery_app.control.inspect()
        ping_result = inspector.ping()
        if ping_result:
            worker_count = len(ping_result)
            celery_connected = True
        else:
            # Fallback: check active tasks
            active_tasks = inspector.active() or {}
            celery_connected = len(active_tasks) > 0
            worker_count = len(active_tasks)
    except Exception:
        celery_connected = False
        worker_count = 0

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
        worker_count=worker_count,
    )


@router.post("/reanalyze", response_model=MessageResponse)
async def reanalyze_documents(
    request: Request,
    category_id: UUID | None = Query(default=None),
    reanalyze_all: bool = Query(default=False, description="Re-analyze all documents, not just low confidence"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """
    Re-analyze documents with the updated AI prompt.

    - If category_id is provided, only re-analyzes documents in that category
    - If reanalyze_all=True, re-analyzes ALL documents (otherwise only low confidence)
    """
    from sqlalchemy import delete

    from app.models import ExtractedData
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
            delete(ExtractedData).where(ExtractedData.document_id == UUID(doc_id))
        )

    # Queue for re-analysis
    for doc_id in document_ids:
        analyze_document.delay(doc_id)

    # Get category name for audit
    category_name = None
    if category_id:
        cat = await session.get(Category, category_id)
        category_name = cat.name if cat else None

    async with AuditContext(session, current_user, request) as audit:
        audit.track_action(
            action=AuditAction.CRAWLER_START,
            entity_type="ReanalysisJob",
            entity_name=category_name or "All Documents",
            changes={
                "documents_queued": len(document_ids),
                "category_id": str(category_id) if category_id else None,
                "category_name": category_name,
                "reanalyze_all": reanalyze_all,
                "mode": "all" if reanalyze_all else "low_confidence_only",
            },
        )
        await session.commit()

    return MessageResponse(
        message=f"Queued {len(document_ids)} documents for re-analysis"
    )
