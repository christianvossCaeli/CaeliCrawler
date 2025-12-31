"""
Analysis API Package - Modularized endpoints for analysis and reporting.

This package provides endpoints for:
- Smart Query: AI-powered natural language queries and commands
- Templates: AnalysisTemplate CRUD operations
- Reports: Overview and entity reports with facet aggregation
- Stats: Analysis statistics

Modules:
- smart_query: Natural language query endpoints
- templates: AnalysisTemplate management
- reports: Overview and entity report endpoints
- stats: Statistics endpoint
- helpers: Shared helper functions (translations, preview building)
"""

from fastapi import APIRouter

from .reports import router as reports_router
from .smart_query import router as smart_query_router
from .stats import router as stats_router
from .templates import router as templates_router

# Create main router that combines all sub-routers
router = APIRouter()

# Include all routes (for backwards compatibility with flat structure)
router.include_router(smart_query_router, tags=["smart-query"])
router.include_router(templates_router, tags=["templates"])
router.include_router(reports_router, tags=["reports"])
router.include_router(stats_router, tags=["stats"])

# Re-export helpers for use by other modules
from .helpers import (  # noqa: E402
    build_preview,
    entity_type_to_german,
    facet_type_to_german,
    operation_to_german,
    relation_to_german,
)

__all__ = [
    "router",
    "build_preview",
    "operation_to_german",
    "entity_type_to_german",
    "facet_type_to_german",
    "relation_to_german",
]
