"""AI Tasks Module.

This module provides Celery tasks for AI-powered analysis and processing.
It has been split into focused sub-modules for better maintainability:

- common.py: Shared utilities, constants, and helper functions
- document_analyzer.py: Document analysis tasks
- pysis_processor.py: PySis field extraction and processing
- entity_operations.py: Entity data analysis and attachment processing

All tasks are automatically registered with the Celery app when this module
is imported by celery_app.py.
"""

from workers.celery_app import celery_app

# Import and register tasks from each sub-module
from . import document_analyzer, entity_operations, pysis_processor

# Register all tasks with the Celery app
_doc_tasks = document_analyzer.register_tasks(celery_app)
_pysis_tasks = pysis_processor.register_tasks(celery_app)
_entity_tasks = entity_operations.register_tasks(celery_app)

# Unpack task references for easy access
(
    analyze_document,
    batch_analyze,
    reanalyze_low_confidence,
) = _doc_tasks

(
    extract_pysis_fields,
    convert_extractions_to_facets,
    analyze_pysis_fields_for_facets,
    enrich_facet_values_from_pysis,
) = _pysis_tasks

(
    analyze_entity_data_for_facets,
    analyze_attachment_task,
) = _entity_tasks

# Export all tasks for backward compatibility
__all__ = [
    # Document analyzer tasks
    "analyze_document",
    "batch_analyze",
    "reanalyze_low_confidence",
    # PySis processor tasks
    "extract_pysis_fields",
    "convert_extractions_to_facets",
    "analyze_pysis_fields_for_facets",
    "enrich_facet_values_from_pysis",
    # Entity operation tasks
    "analyze_entity_data_for_facets",
    "analyze_attachment_task",
]
