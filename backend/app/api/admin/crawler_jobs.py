"""Admin API endpoints for crawl job management."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.core.deps import require_editor
from app.core.query_helpers import batch_fetch_by_ids
from app.models import CrawlJob, DataSource, Category, JobStatus, User
from app.schemas.crawl_job import (
    CrawlJobResponse,
    CrawlJobListResponse,
    CrawlJobDetailResponse,
    JobLogResponse,
    JobLogEntry,
    RunningJobInfo,
    RunningJobsResponse,
)
from app.core.exceptions import NotFoundError

router = APIRouter()


@router.get("/jobs", response_model=CrawlJobListResponse)
async def list_jobs(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None, description="Single status or comma-separated list (e.g. 'COMPLETED,FAILED')"),
    category_id: Optional[UUID] = Query(default=None),
    source_id: Optional[UUID] = Query(default=None),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """List all crawl jobs with pagination."""
    query = select(CrawlJob)

    if status:
        # Support comma-separated status values
        status_values = [s.strip() for s in status.split(",")]
        valid_statuses = []
        for s in status_values:
            try:
                valid_statuses.append(JobStatus(s))
            except ValueError:
                pass  # Ignore invalid status values
        if len(valid_statuses) == 1:
            query = query.where(CrawlJob.status == valid_statuses[0])
        elif len(valid_statuses) > 1:
            query = query.where(CrawlJob.status.in_(valid_statuses))
        elif len(status_values) > 0:
            # All provided status values were invalid - return empty result
            query = query.where(False)
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
    source_ids = {job.source_id for job in jobs if job.source_id}
    category_ids = {job.category_id for job in jobs if job.category_id}

    sources_dict = await batch_fetch_by_ids(session, DataSource, source_ids)
    categories_dict = await batch_fetch_by_ids(session, Category, category_ids)

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


@router.get("/jobs/{job_id}/log", response_model=JobLogResponse)
async def get_job_log(
    job_id: UUID,
    limit: int = Query(default=30, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Get live crawl log for a running job."""
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
    source_ids = {job.source_id for job in running_jobs if job.source_id}
    category_ids = {job.category_id for job in running_jobs if job.category_id}

    sources_dict = await batch_fetch_by_ids(session, DataSource, source_ids)
    categories_dict = await batch_fetch_by_ids(session, Category, category_ids)

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
