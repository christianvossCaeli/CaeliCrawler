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
]
