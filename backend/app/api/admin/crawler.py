"""Admin API endpoints for crawler control.

This module aggregates all crawler-related endpoints from submodules:
- crawler_jobs: Job listing, details, logs, running jobs
- crawler_control: Start/stop crawls, statistics, status, reanalyze
- crawler_ai: AI task management
- crawler_documents: Document processing operations
- crawler_sse: Server-Sent Events for real-time updates

The endpoints are organized for better maintainability while keeping
the same API structure for backwards compatibility.
"""

from fastapi import APIRouter

from app.api.admin.crawler_jobs import router as jobs_router
from app.api.admin.crawler_control import router as control_router
from app.api.admin.crawler_ai import router as ai_router
from app.api.admin.crawler_documents import router as documents_router
from app.api.admin.crawler_sse import router as sse_router

router = APIRouter()

# Include all sub-routers
# Jobs: GET /jobs, GET /jobs/{id}, GET /jobs/{id}/log, GET /running
router.include_router(jobs_router)

# Control: POST /start, POST /jobs/{id}/cancel, GET /stats, GET /status, POST /reanalyze
router.include_router(control_router)

# AI Tasks: GET /ai-tasks, GET /ai-tasks/running, POST /ai-tasks/{id}/cancel
router.include_router(ai_router)

# Documents: POST /documents/{id}/process, POST /documents/{id}/analyze,
#            POST /documents/process-pending, POST /documents/stop-all,
#            POST /documents/reanalyze-filtered
router.include_router(documents_router)

# SSE: GET /events, GET /events/job/{id} - Real-time updates
router.include_router(sse_router)
