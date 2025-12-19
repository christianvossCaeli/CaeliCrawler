"""Celery tasks for crawling operations."""

import hashlib
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from celery import shared_task
import structlog

from workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(bind=True, name="workers.crawl_tasks.crawl_source")
def crawl_source(self, source_id: str, job_id: str, force: bool = False):
    """
    Crawl a single data source.

    Args:
        source_id: UUID of the data source to crawl
        job_id: UUID of the crawl job
        force: Force crawl even if recently crawled
    """
    from app.database import get_celery_session_context
    from app.models import DataSource, CrawlJob, JobStatus, SourceStatus
    import asyncio

    async def _crawl():
        async with get_celery_session_context() as session:
            # Get source and job
            source = await session.get(DataSource, UUID(source_id))
            job = await session.get(CrawlJob, UUID(job_id))

            if not source or not job:
                logger.error("Source or job not found", source_id=source_id, job_id=job_id)
                return

            # Update job status
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            job.celery_task_id = self.request.id
            await session.commit()

            logger.info(
                "Starting crawl",
                source_id=source_id,
                source_name=source.name,
                source_type=source.source_type.value,
            )

            try:
                # Import appropriate crawler based on source type
                from crawlers.base import get_crawler_for_source

                crawler = get_crawler_for_source(source)
                result = await crawler.crawl(source, job)

                # Update job with results
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                job.pages_crawled = result.pages_crawled
                job.documents_found = result.documents_found
                job.documents_processed = result.documents_processed
                job.documents_new = result.documents_new
                job.documents_updated = result.documents_updated
                job.stats = result.stats

                # Update source
                source.last_crawl = datetime.utcnow()
                source.status = SourceStatus.ACTIVE
                source.error_message = None

                logger.info(
                    "Crawl completed",
                    source_id=source_id,
                    documents_found=result.documents_found,
                    documents_new=result.documents_new,
                )

                # Trigger document processing immediately if new documents were found
                if result.documents_new > 0:
                    from workers.processing_tasks import process_pending_documents
                    process_pending_documents.delay()
                    logger.info(
                        "Triggered document processing after crawl",
                        documents_new=result.documents_new,
                    )

                # Emit notification events
                from workers.notification_tasks import emit_event
                emit_event.delay(
                    "CRAWL_COMPLETED",
                    {
                        "entity_type": "crawl_job",
                        "entity_id": str(job.id),
                        "source_id": source_id,
                        "source_name": source.name,
                        "category_id": str(source.category_id) if source.category_id else None,
                        "documents_found": result.documents_found,
                        "documents_new": result.documents_new,
                    }
                )

                if result.documents_new > 0:
                    emit_event.delay(
                        "NEW_DOCUMENT",
                        {
                            "entity_type": "data_source",
                            "entity_id": source_id,
                            "source_name": source.name,
                            "category_id": str(source.category_id) if source.category_id else None,
                            "count": result.documents_new,
                        }
                    )

            except Exception as e:
                logger.exception("Crawl failed", source_id=source_id, error=str(e))
                job.status = JobStatus.FAILED
                job.completed_at = datetime.utcnow()
                job.error_count += 1
                job.error_log.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": str(e),
                    "type": type(e).__name__,
                })

                source.status = SourceStatus.ERROR
                source.error_message = str(e)

                # Emit notification event for failed crawl
                from workers.notification_tasks import emit_event
                emit_event.delay(
                    "CRAWL_FAILED",
                    {
                        "entity_type": "crawl_job",
                        "entity_id": str(job.id),
                        "source_id": source_id,
                        "source_name": source.name,
                        "category_id": str(source.category_id) if source.category_id else None,
                        "error": str(e),
                    }
                )

            await session.commit()

    asyncio.run(_crawl())


@celery_app.task(name="workers.crawl_tasks.check_scheduled_crawls")
def check_scheduled_crawls():
    """Check for sources due for scheduled crawling."""
    from app.database import get_celery_session_context
    from app.models import Category, DataSource, DataSourceCategory, SourceStatus
    from sqlalchemy import select
    import asyncio
    from croniter import croniter

    async def _check():
        async with get_celery_session_context() as session:
            # Get all active categories
            result = await session.execute(
                select(Category).where(Category.is_active == True)
            )
            categories = result.scalars().all()

            jobs_created = 0
            now = datetime.utcnow()

            for category in categories:
                # Check if category is due based on cron schedule
                cron = croniter(category.schedule_cron, now - timedelta(hours=1))
                next_run = cron.get_next(datetime)

                if next_run <= now:
                    # Get sources via junction table (N:M relationship)
                    source_result = await session.execute(
                        select(DataSource)
                        .join(DataSourceCategory, DataSource.id == DataSourceCategory.data_source_id)
                        .where(
                            DataSourceCategory.category_id == category.id,
                            DataSource.status.in_([SourceStatus.ACTIVE, SourceStatus.PENDING]),
                        )
                    )
                    sources = source_result.scalars().all()

                    for source in sources:
                        # Check if source was crawled recently (within cron interval)
                        if source.last_crawl:
                            prev_run = croniter(category.schedule_cron, source.last_crawl).get_prev(datetime)
                            if source.last_crawl >= prev_run:
                                continue  # Already crawled this period

                        # Create crawl job
                        from workers.crawl_tasks import create_crawl_job
                        create_crawl_job.delay(str(source.id), str(category.id))
                        jobs_created += 1

            logger.info("Scheduled crawl check completed", jobs_created=jobs_created)

    asyncio.run(_check())


@celery_app.task(name="workers.crawl_tasks.create_crawl_job")
def create_crawl_job(source_id: str, category_id: str):
    """Create a new crawl job and start crawling."""
    from app.database import get_celery_session_context
    from app.models import CrawlJob, JobStatus
    import asyncio

    async def _create():
        async with get_celery_session_context() as session:
            job = CrawlJob(
                source_id=UUID(source_id),
                category_id=UUID(category_id),
                status=JobStatus.PENDING,
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)

            # Start crawl task
            crawl_source.delay(source_id, str(job.id))

            logger.info("Crawl job created", job_id=str(job.id), source_id=source_id)
            return str(job.id)

    return asyncio.run(_create())


@celery_app.task(name="workers.crawl_tasks.cleanup_old_jobs")
def cleanup_old_jobs():
    """Clean up old completed/failed jobs."""
    from app.database import get_celery_session_context
    from app.models import CrawlJob, JobStatus
    from sqlalchemy import delete
    import asyncio

    async def _cleanup():
        async with get_celery_session_context() as session:
            # Delete jobs older than 30 days
            cutoff = datetime.utcnow() - timedelta(days=30)

            result = await session.execute(
                delete(CrawlJob).where(
                    CrawlJob.status.in_([JobStatus.COMPLETED, JobStatus.FAILED]),
                    CrawlJob.completed_at < cutoff,
                )
            )
            deleted = result.rowcount
            await session.commit()

            logger.info("Old jobs cleaned up", deleted=deleted)

    asyncio.run(_cleanup())


@celery_app.task(name="workers.crawl_tasks.detect_changes")
def detect_changes(source_id: str):
    """Detect changes on a data source without full crawl."""
    from app.database import get_celery_session_context
    from app.models import DataSource, ChangeLog, ChangeType
    import asyncio
    import httpx

    async def _detect():
        async with get_celery_session_context() as session:
            source = await session.get(DataSource, UUID(source_id))
            if not source:
                return

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.head(
                        source.base_url,
                        follow_redirects=True,
                        timeout=30,
                    )

                    # Calculate hash of headers that indicate changes
                    change_indicators = [
                        response.headers.get("last-modified", ""),
                        response.headers.get("etag", ""),
                        response.headers.get("content-length", ""),
                    ]
                    new_hash = hashlib.sha256(
                        "".join(change_indicators).encode()
                    ).hexdigest()

                    if source.content_hash and source.content_hash != new_hash:
                        # Change detected
                        change = ChangeLog(
                            source_id=source.id,
                            change_type=ChangeType.CONTENT_CHANGED,
                            affected_url=source.base_url,
                            old_hash=source.content_hash,
                            new_hash=new_hash,
                        )
                        session.add(change)
                        source.last_change_detected = datetime.utcnow()

                        logger.info("Change detected", source_id=source_id)

                        # Emit notification event for change
                        from workers.notification_tasks import emit_event
                        emit_event.delay(
                            "DOCUMENT_CHANGED",
                            {
                                "entity_type": "data_source",
                                "entity_id": source_id,
                                "source_name": source.name,
                                "category_id": str(source.category_id) if source.category_id else None,
                                "url": source.base_url,
                            }
                        )

                    source.content_hash = new_hash
                    await session.commit()

            except Exception as e:
                logger.error("Change detection failed", source_id=source_id, error=str(e))

    asyncio.run(_detect())
