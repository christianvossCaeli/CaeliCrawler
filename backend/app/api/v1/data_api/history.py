"""Historical data and crawl history endpoints.

Note: Municipality-specific history has been deprecated.
Use the Entity system with EntityType.slug="municipality" for entity-level analytics.
Entity history is available through the audit/versioning system.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import DataSource, Document, ExtractedData
from app.models.crawl_job import CrawlJob, JobStatus

router = APIRouter()


@router.get("/history/crawls")
async def get_crawl_history(
    source_id: UUID | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Get history of crawl jobs with results summary."""
    query = (
        select(CrawlJob)
        .where(CrawlJob.status.in_([JobStatus.COMPLETED, JobStatus.FAILED]))
        .order_by(CrawlJob.started_at.desc())
        .limit(limit)
    )

    if source_id:
        query = query.where(CrawlJob.source_id == source_id)

    result = await session.execute(query)
    jobs = result.scalars().all()

    if not jobs:
        return {"total_crawls": 0, "crawls": []}

    job_ids = [job.id for job in jobs]
    source_ids = list({job.source_id for job in jobs if job.source_id})

    # Batch load sources to avoid N+1 query
    sources_result = await session.execute(
        select(DataSource).where(DataSource.id.in_(source_ids))
    )
    sources_map = {s.id: s for s in sources_result.scalars().all()}

    # Batch load document counts using GROUP BY
    doc_counts_result = await session.execute(
        select(Document.crawl_job_id, func.count())
        .where(Document.crawl_job_id.in_(job_ids))
        .group_by(Document.crawl_job_id)
    )
    doc_counts_map = {row[0]: row[1] for row in doc_counts_result.all()}

    # Batch load extraction counts using GROUP BY
    extraction_counts_result = await session.execute(
        select(Document.crawl_job_id, func.count())
        .select_from(ExtractedData)
        .join(Document)
        .where(Document.crawl_job_id.in_(job_ids))
        .group_by(Document.crawl_job_id)
    )
    extraction_counts_map = {row[0]: row[1] for row in extraction_counts_result.all()}

    crawls = []
    for job in jobs:
        source = sources_map.get(job.source_id)
        doc_count = doc_counts_map.get(job.id, 0)
        extraction_count = extraction_counts_map.get(job.id, 0)

        crawls.append({
            "job_id": str(job.id),
            "source_name": source.name if source else None,
            "source_municipality": None,  # Legacy - location_name no longer on DataSource
            "status": job.status.value,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "documents_found": job.documents_found or 0,
            "documents_new": job.documents_new or 0,
            "documents_stored": doc_count or 0,
            "extractions_created": extraction_count or 0,
            "error_count": job.error_count or 0,
            "errors": job.error_log[:3] if job.error_log else [],
        })

    return {
        "total_crawls": len(crawls),
        "crawls": crawls,
    }
