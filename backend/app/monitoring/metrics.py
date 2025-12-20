"""Prometheus metrics definitions for crawler monitoring.

This module provides comprehensive metrics for monitoring the crawler system:
- Job execution metrics (count, duration, status)
- Document processing metrics
- AI analysis metrics
- Error tracking

Usage:
    from app.monitoring import crawler_jobs_total, track_crawler_job

    # Increment counter
    crawler_jobs_total.labels(source_type="WEBSITE", status="completed").inc()

    # Use context manager for timing
    with track_crawler_job(source_type="WEBSITE") as tracker:
        # ... do crawl work ...
        tracker.set_pages(10)
        tracker.set_documents(5)
"""

import time
from contextlib import contextmanager
from typing import Generator, Optional

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    REGISTRY,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from fastapi import APIRouter, Response

# === Crawler Job Metrics ===

crawler_jobs_total = Counter(
    "crawler_jobs_total",
    "Total number of crawler jobs executed",
    ["source_type", "status"],
)

crawler_jobs_running = Gauge(
    "crawler_jobs_running",
    "Number of currently running crawler jobs",
    ["source_type"],
)

crawler_pages_crawled = Counter(
    "crawler_pages_crawled_total",
    "Total number of pages crawled",
    ["source_type"],
)

crawler_documents_found = Counter(
    "crawler_documents_found_total",
    "Total number of documents found by crawlers",
    ["source_type", "document_type"],
)

crawler_errors_total = Counter(
    "crawler_errors_total",
    "Total number of crawler errors",
    ["source_type", "error_type"],
)

crawler_job_duration_seconds = Histogram(
    "crawler_job_duration_seconds",
    "Duration of crawler jobs in seconds",
    ["source_type"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600),
)


# === Document Processing Metrics ===

documents_processed_total = Counter(
    "documents_processed_total",
    "Total number of documents processed",
    ["document_type", "status"],
)

documents_processing_duration_seconds = Histogram(
    "documents_processing_duration_seconds",
    "Duration of document processing in seconds",
    ["document_type"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60, 120),
)

documents_pending_count = Gauge(
    "documents_pending_count",
    "Number of documents pending processing",
    ["status"],
)


# === AI Analysis Metrics ===

ai_analysis_total = Counter(
    "ai_analysis_total",
    "Total number of AI analysis tasks",
    ["status"],
)

ai_analysis_duration_seconds = Histogram(
    "ai_analysis_duration_seconds",
    "Duration of AI analysis in seconds",
    buckets=(0.5, 1, 2, 5, 10, 30, 60, 120, 300),
)

ai_analysis_errors_total = Counter(
    "ai_analysis_errors_total",
    "Total number of AI analysis errors",
    ["error_type"],
)

ai_tokens_used = Counter(
    "ai_tokens_used_total",
    "Total number of AI tokens used",
    ["model", "token_type"],
)


# === Data Source Metrics ===

data_sources_total = Gauge(
    "data_sources_total",
    "Total number of data sources",
    ["source_type", "status"],
)

data_sources_last_crawl_timestamp = Gauge(
    "data_sources_last_crawl_timestamp",
    "Timestamp of last successful crawl per source",
    ["source_id", "source_name"],
)


# === System Health Metrics ===

celery_workers_active = Gauge(
    "celery_workers_active",
    "Number of active Celery workers",
    ["queue"],
)

redis_connection_status = Gauge(
    "redis_connection_status",
    "Redis connection status (1=connected, 0=disconnected)",
)


# === Application Info ===

app_info = Info(
    "caeli_crawler",
    "Application information",
)


# === Helper Classes and Functions ===

class CrawlerJobTracker:
    """Context manager for tracking crawler job metrics."""

    def __init__(self, source_type: str):
        self.source_type = source_type
        self.start_time: Optional[float] = None
        self.pages = 0
        self.documents = 0
        self.status = "completed"

    def set_pages(self, count: int) -> None:
        """Set the number of pages crawled."""
        self.pages = count

    def set_documents(self, count: int) -> None:
        """Set the number of documents found."""
        self.documents = count

    def set_error(self, error_type: str = "unknown") -> None:
        """Mark the job as failed."""
        self.status = "failed"
        crawler_errors_total.labels(
            source_type=self.source_type,
            error_type=error_type
        ).inc()


@contextmanager
def track_crawler_job(source_type: str) -> Generator[CrawlerJobTracker, None, None]:
    """Context manager for tracking crawler job execution.

    Example:
        with track_crawler_job("WEBSITE") as tracker:
            # ... perform crawl ...
            tracker.set_pages(10)
            tracker.set_documents(5)
    """
    tracker = CrawlerJobTracker(source_type)
    tracker.start_time = time.time()

    # Increment running jobs
    crawler_jobs_running.labels(source_type=source_type).inc()

    try:
        yield tracker
    except Exception:
        tracker.set_error("exception")
        raise
    finally:
        # Record duration
        duration = time.time() - tracker.start_time
        crawler_job_duration_seconds.labels(source_type=source_type).observe(duration)

        # Record counts
        crawler_pages_crawled.labels(source_type=source_type).inc(tracker.pages)

        # Record job completion
        crawler_jobs_total.labels(
            source_type=source_type,
            status=tracker.status
        ).inc()

        # Decrement running jobs
        crawler_jobs_running.labels(source_type=source_type).dec()


@contextmanager
def track_document_processing(document_type: str) -> Generator[None, None, None]:
    """Context manager for tracking document processing.

    Example:
        with track_document_processing("PDF"):
            # ... process document ...
    """
    start_time = time.time()
    status = "completed"

    try:
        yield
    except Exception:
        status = "failed"
        raise
    finally:
        duration = time.time() - start_time
        documents_processing_duration_seconds.labels(document_type=document_type).observe(duration)
        documents_processed_total.labels(document_type=document_type, status=status).inc()


@contextmanager
def track_ai_analysis() -> Generator[None, None, None]:
    """Context manager for tracking AI analysis.

    Example:
        with track_ai_analysis():
            # ... perform AI analysis ...
    """
    start_time = time.time()
    status = "completed"

    try:
        yield
    except Exception:
        status = "failed"
        ai_analysis_errors_total.labels(error_type="exception").inc()
        raise
    finally:
        duration = time.time() - start_time
        ai_analysis_duration_seconds.observe(duration)
        ai_analysis_total.labels(status=status).inc()


def update_pending_documents_gauge(pending: int, processing: int, analyzed: int) -> None:
    """Update the pending documents gauge."""
    documents_pending_count.labels(status="pending").set(pending)
    documents_pending_count.labels(status="processing").set(processing)
    documents_pending_count.labels(status="awaiting_analysis").set(analyzed)


def update_data_sources_gauge(sources_by_type_status: dict) -> None:
    """Update the data sources gauge.

    Args:
        sources_by_type_status: Dict with (source_type, status) -> count
    """
    for (source_type, status), count in sources_by_type_status.items():
        data_sources_total.labels(source_type=source_type, status=status).set(count)


def set_app_info(version: str, environment: str) -> None:
    """Set application info metrics."""
    app_info.info({
        "version": version,
        "environment": environment,
    })


# === FastAPI Metrics Endpoint ===

def setup_metrics_endpoint(app) -> None:
    """Setup the /metrics endpoint for Prometheus scraping.

    Args:
        app: FastAPI application instance
    """
    router = APIRouter()

    @router.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST,
        )

    app.include_router(router)


def get_metrics_router() -> APIRouter:
    """Get a router with the metrics endpoint.

    Returns:
        APIRouter with /metrics endpoint
    """
    router = APIRouter(tags=["Monitoring"])

    @router.get("/metrics", include_in_schema=False)
    async def metrics():
        """Prometheus metrics endpoint."""
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST,
        )

    return router
