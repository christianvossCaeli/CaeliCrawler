"""Facets API module.

This module provides API endpoints for managing:
- FacetTypes: Schema definitions for facet data
- FacetValues: Actual facet data attached to entities
- Entity Facets Summary: Aggregated view of facets per entity
- Full-Text Search: Search across facet values
- History: Time-series data for facets
"""

from fastapi import APIRouter

from .facet_history import router as history_router
from .facet_search import router as search_router
from .facet_summary import router as summary_router
from .facet_types import router as types_router
from .facet_values import router as values_router

# Main router that aggregates all sub-routers
router = APIRouter()

# Include all sub-routers
router.include_router(types_router, tags=["Facet Types"])
router.include_router(values_router, tags=["Facet Values"])
router.include_router(summary_router, tags=["Facet Summary"])
router.include_router(search_router, tags=["Facet Search"])
router.include_router(history_router, tags=["Facet History"])

__all__ = ["router"]
