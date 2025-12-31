"""Assistant Service Module - AI-powered chat assistant for the app.

This module provides the AssistantService class which handles:
- Intent classification for user messages
- Query handling and context-aware responses
- Action execution (single and batch)
- Facet management suggestions
- Streaming responses
- Image analysis
- Discussion/document analysis

The module is split into:
- common.py: Shared utilities and client initialization
- prompts.py: All LLM prompt templates
- utils.py: Utility functions
- context_actions.py: Context action handlers (PySis, crawl, facets)
- context_builder.py: Context building and entity data collection
- query_handler.py: Query and search handlers
- action_executor.py: Action execution handlers
- response_formatter.py: Response formatting and presentation
"""

# Prompts
# Action Executor
from services.assistant.action_executor import (
    execute_action,
    execute_batch_action,
    handle_batch_action_intent,
    parse_action_data,
    parse_batch_filter,
    preview_inline_edit,
)

# Common
from services.assistant.common import (
    AIServiceNotAvailableException,
    EntityNotFoundException,
    build_suggestions_list,
    format_count_message,
    get_entity_with_context,
    get_openai_client,
    validate_entity_context,
)

# Context Actions
from services.assistant.context_actions import handle_context_action

# Context Builder
from services.assistant.context_builder import (
    build_app_summary_context,
    build_entity_context,
    build_entity_summary_for_prompt,
    build_facet_summary,
    build_pysis_context,
    count_entity_relations,
    get_facet_counts_by_type,
    prepare_entity_data_for_ai,
)

# Facet Management
from services.assistant.facet_management import handle_facet_management_request
from services.assistant.prompts import (
    CONTEXT_RESPONSE_PROMPT,
    DISCUSSION_ANALYSIS_PROMPT,
    FACET_TYPE_SUGGESTION_PROMPT,
    IMAGE_ANALYSIS_PROMPT,
    INTENT_CLASSIFICATION_PROMPT,
    RESPONSE_GENERATION_PROMPT,
    SUMMARIZE_PROMPT,
)

# Query Handler
from services.assistant.query_handler import (
    build_context_query_suggestions,
    build_query_suggestions,
    format_query_result_message,
    generate_context_response_with_ai,
    handle_context_query,
    handle_query,
    suggest_corrections,
)

# Response Formatter
from services.assistant.response_formatter import (
    generate_help_response,
    handle_discussion,
    handle_image_analysis,
    handle_navigation,
    handle_summarize,
    suggest_smart_query_redirect,
)

# Utils
from services.assistant.utils import (
    extract_json_from_response,
    format_entity_link,
    format_entity_summary,
    safe_json_loads,
    truncate_for_prompt,
)

__all__ = [
    # Prompts
    "INTENT_CLASSIFICATION_PROMPT",
    "RESPONSE_GENERATION_PROMPT",
    "DISCUSSION_ANALYSIS_PROMPT",
    "FACET_TYPE_SUGGESTION_PROMPT",
    "IMAGE_ANALYSIS_PROMPT",
    "CONTEXT_RESPONSE_PROMPT",
    "SUMMARIZE_PROMPT",
    # Utils
    "format_entity_link",
    "extract_json_from_response",
    "truncate_for_prompt",
    "safe_json_loads",
    "format_entity_summary",
    # Common
    "get_openai_client",
    "validate_entity_context",
    "build_suggestions_list",
    "format_count_message",
    "get_entity_with_context",
    "EntityNotFoundException",
    "AIServiceNotAvailableException",
    # Context Builder
    "build_entity_context",
    "build_facet_summary",
    "build_pysis_context",
    "count_entity_relations",
    "get_facet_counts_by_type",
    "build_app_summary_context",
    "build_entity_summary_for_prompt",
    "prepare_entity_data_for_ai",
    # Query Handler
    "handle_query",
    "handle_context_query",
    "generate_context_response_with_ai",
    "suggest_corrections",
    "format_query_result_message",
    "build_query_suggestions",
    "build_context_query_suggestions",
    # Action Executor
    "execute_action",
    "execute_batch_action",
    "preview_inline_edit",
    "handle_batch_action_intent",
    "parse_batch_filter",
    "parse_action_data",
    # Response Formatter
    "generate_help_response",
    "handle_navigation",
    "handle_summarize",
    "handle_image_analysis",
    "handle_discussion",
    "suggest_smart_query_redirect",
    # Context Actions
    "handle_context_action",
    # Facet Management
    "handle_facet_management_request",
]
