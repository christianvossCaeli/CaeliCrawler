"""
Data API Package - Modularized endpoints for extracted data and documents.

This package provides endpoints for:
- Extracted data listing and verification
- Document management and search
- Historical data and crawl history

Note: Municipality aggregation has been replaced by the Entity-Facet system.
Municipalities are now Entity records with EntityType.slug="municipality".

Modules:
- loaders: Bulk-loading utilities to avoid N+1 queries
- extractions: Extracted data endpoints
- documents: Document management endpoints
- history: Historical data endpoints (crawl history)
"""

from fastapi import APIRouter

from .documents import router as documents_router
from .extractions import router as extractions_router
from .history import router as history_router

# Create main router that combines all sub-routers
router = APIRouter()

# Include all routes (for backwards compatibility with flat structure)
# Note: extractions_router has a "/" root path that serves as the main /data endpoint
router.include_router(extractions_router, tags=["extractions"])
router.include_router(documents_router, tags=["documents"])
router.include_router(history_router, tags=["history"])

# Re-export loaders for use by other modules
from .loaders import (  # noqa: E402
    bulk_load_categories,
    bulk_load_documents_with_sources,
    bulk_load_sources,
)

__all__ = [
    "router",
    "bulk_load_documents_with_sources",
    "bulk_load_categories",
    "bulk_load_sources",
]
