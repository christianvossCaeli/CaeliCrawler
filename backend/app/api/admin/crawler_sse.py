"""Server-Sent Events (SSE) endpoint for real-time crawler updates.

SSE provides push-based updates from server to client, eliminating the need
for polling and reducing server load while improving user experience.
"""

import asyncio
import json
from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_editor_sse
from app.database import get_session
from app.models import CrawlJob, JobStatus, User
from app.services.crawler_progress import crawler_progress

router = APIRouter()

# Update interval in seconds
SSE_UPDATE_INTERVAL = 2.0


async def _generate_crawler_events(
    session: AsyncSession,
    include_logs: bool = False,
    job_id: UUID | None = None,
) -> AsyncGenerator[str]:
    """Generate SSE events for crawler status updates.

    Yields events in SSE format:
    - event: status - Overall crawler status
    - event: jobs - Running jobs with live stats
    - event: log - Log entries (if include_logs=True and job_id specified)
    """
    last_log_count = 0

    while True:
        try:
            # Get running/pending job counts
            running_count = (
                await session.execute(select(func.count()).where(CrawlJob.status == JobStatus.RUNNING))
            ).scalar() or 0

            pending_count = (
                await session.execute(select(func.count()).where(CrawlJob.status == JobStatus.PENDING))
            ).scalar() or 0

            # Get running jobs with live stats
            result = await session.execute(select(CrawlJob).where(CrawlJob.status == JobStatus.RUNNING))
            running_jobs = result.scalars().all()

            jobs_data = []
            for job in running_jobs:
                live_stats = await crawler_progress.get_stats(job.id)
                jobs_data.append(
                    {
                        "id": str(job.id),
                        "source_id": str(job.source_id) if job.source_id else None,
                        "category_id": str(job.category_id) if job.category_id else None,
                        "status": job.status.value,
                        "started_at": job.started_at.isoformat() if job.started_at else None,
                        "pages_crawled": live_stats.get("pages_crawled", job.pages_crawled),
                        "documents_found": live_stats.get("documents_found", job.documents_found),
                    }
                )

            # Emit status event
            status_data = {
                "running_jobs": running_count,
                "pending_jobs": pending_count,
                "status": "crawling" if running_count > 0 else ("pending" if pending_count > 0 else "idle"),
            }
            yield f"event: status\ndata: {json.dumps(status_data)}\n\n"

            # Emit jobs event
            yield f"event: jobs\ndata: {json.dumps(jobs_data)}\n\n"

            # Emit log events if requested
            if include_logs and job_id:
                log_entries = await crawler_progress.get_log(job_id, limit=50)
                if len(log_entries) > last_log_count:
                    # Only send new entries
                    new_entries = log_entries[last_log_count:]
                    last_log_count = len(log_entries)
                    yield f"event: log\ndata: {json.dumps(new_entries)}\n\n"

            # Heartbeat to keep connection alive
            yield ": heartbeat\n\n"

            await asyncio.sleep(SSE_UPDATE_INTERVAL)

        except asyncio.CancelledError:
            # Client disconnected
            break
        except Exception as e:
            # Send error event and continue
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            await asyncio.sleep(SSE_UPDATE_INTERVAL)


@router.get("/events")
async def crawler_events(
    include_logs: bool = Query(default=False, description="Include log entries in stream"),
    job_id: UUID | None = Query(default=None, description="Specific job to get logs for"),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor_sse),
):
    """
    Server-Sent Events stream for real-time crawler updates.

    Events:
    - `status`: Overall crawler status (running_jobs, pending_jobs, status)
    - `jobs`: List of running jobs with live stats
    - `log`: Log entries (if include_logs=True and job_id specified)
    - `error`: Error messages

    Usage:
    ```javascript
    const eventSource = new EventSource('/api/admin/crawler/events');
    eventSource.addEventListener('status', (e) => {
        const data = JSON.parse(e.data);
        console.log('Status:', data);
    });
    eventSource.addEventListener('jobs', (e) => {
        const data = JSON.parse(e.data);
        console.log('Jobs:', data);
    });
    ```
    """
    return StreamingResponse(
        _generate_crawler_events(session, include_logs, job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/events/job/{job_id}")
async def job_events(
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor_sse),
):
    """
    SSE stream for a specific job's progress and logs.

    More focused than /events - only streams updates for one job.
    """

    async def generate():
        last_log_count = 0

        while True:
            try:
                job = await session.get(CrawlJob, job_id)
                if not job:
                    yield f"event: error\ndata: {json.dumps({'error': 'Job not found'})}\n\n"
                    break

                # Stop streaming if job is no longer running
                if job.status not in (JobStatus.RUNNING, JobStatus.PENDING):
                    yield f"event: completed\ndata: {json.dumps({'status': job.status.value})}\n\n"
                    break

                # Get live stats
                live_stats = await crawler_progress.get_stats(job_id)

                job_data = {
                    "id": str(job.id),
                    "status": job.status.value,
                    "pages_crawled": live_stats.get("pages_crawled", job.pages_crawled),
                    "documents_found": live_stats.get("documents_found", job.documents_found),
                }
                yield f"event: progress\ndata: {json.dumps(job_data)}\n\n"

                # Get log entries
                log_entries = await crawler_progress.get_log(job_id, limit=100)
                if len(log_entries) > last_log_count:
                    new_entries = log_entries[last_log_count:]
                    last_log_count = len(log_entries)
                    for entry in new_entries:
                        yield f"event: log\ndata: {json.dumps(entry)}\n\n"

                yield ": heartbeat\n\n"
                await asyncio.sleep(1.0)  # Faster updates for single job

            except asyncio.CancelledError:
                break
            except Exception as e:
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                await asyncio.sleep(SSE_UPDATE_INTERVAL)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
