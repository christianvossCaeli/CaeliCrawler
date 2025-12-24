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
- prompts.py: All LLM prompt templates
- utils.py: Utility functions
- context_actions.py: Context action handlers (PySis, crawl, facets)
- query_handlers.py: Query and search handlers
- action_handlers.py: Action execution handlers
"""

from services.assistant.prompts import (
    INTENT_CLASSIFICATION_PROMPT,
    RESPONSE_GENERATION_PROMPT,
    DISCUSSION_ANALYSIS_PROMPT,
    FACET_TYPE_SUGGESTION_PROMPT,
    IMAGE_ANALYSIS_PROMPT,
    CONTEXT_RESPONSE_PROMPT,
    SUMMARIZE_PROMPT,
)

from services.assistant.utils import (
    format_entity_link,
    extract_json_from_response,
    truncate_for_prompt,
    safe_json_loads,
    format_entity_summary,
)

from services.assistant.context_actions import handle_context_action

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
    # Context Actions
    "handle_context_action",
]
