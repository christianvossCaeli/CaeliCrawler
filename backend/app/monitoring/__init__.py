"""Prometheus metrics for the application."""

from .metrics import (
    ai_analysis_duration_seconds,
    ai_analysis_errors_total,
    # AI analysis metrics
    ai_analysis_total,
    crawler_documents_found,
    crawler_errors_total,
    crawler_job_duration_seconds,
    crawler_jobs_running,
    # Crawler metrics
    crawler_jobs_total,
    crawler_pages_crawled,
    documents_pending_count,
    # Document processing metrics
    documents_processed_total,
    documents_processing_duration_seconds,
    setup_metrics_endpoint,
    track_ai_analysis,
    # Helper functions
    track_crawler_job,
    track_document_processing,
)

__all__ = [
    # Metrics
    "crawler_jobs_total",
    "crawler_jobs_running",
    "crawler_pages_crawled",
    "crawler_documents_found",
    "crawler_errors_total",
    "crawler_job_duration_seconds",
    "documents_processed_total",
    "documents_processing_duration_seconds",
    "documents_pending_count",
    "ai_analysis_total",
    "ai_analysis_duration_seconds",
    "ai_analysis_errors_total",
    # Functions
    "track_crawler_job",
    "track_document_processing",
    "track_ai_analysis",
    "setup_metrics_endpoint",
]
