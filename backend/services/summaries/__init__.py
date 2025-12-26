"""Custom Summaries Services.

This module provides services for managing user-defined dashboard summaries:
- SummaryExecutor: Executes widget queries and caches results
- SummaryExportService: Exports summaries to PDF and Excel
- interpret_summary_prompt: Interprets prompts into widget configurations
- check_relevance: Checks if updates are meaningful
"""

from services.summaries.executor import SummaryExecutor
from services.summaries.export_service import SummaryExportService
from services.summaries.ai_interpreter import (
    interpret_summary_prompt,
    suggest_widgets_for_entity_type,
    get_schedule_suggestion,
)
from services.summaries.relevance_checker import (
    check_relevance,
    RelevanceCheckResult,
    calculate_data_hash,
    quick_change_detection,
    should_notify_user,
)
from services.summaries.source_resolver import (
    resolve_sources_for_summary,
    resolve_all_sources_for_summary,
    extract_entity_types_from_summary,
    get_sources_for_category,
    get_sources_for_preset,
    get_categories_for_entity_type,
    get_external_apis_for_entity_type,
    get_source_names,
    ResolvedSources,
)

__all__ = [
    "SummaryExecutor",
    "SummaryExportService",
    "interpret_summary_prompt",
    "suggest_widgets_for_entity_type",
    "get_schedule_suggestion",
    "check_relevance",
    "RelevanceCheckResult",
    "calculate_data_hash",
    "quick_change_detection",
    "should_notify_user",
    "resolve_sources_for_summary",
    "resolve_all_sources_for_summary",
    "extract_entity_types_from_summary",
    "get_sources_for_category",
    "get_sources_for_preset",
    "get_categories_for_entity_type",
    "get_external_apis_for_entity_type",
    "get_source_names",
    "ResolvedSources",
]
