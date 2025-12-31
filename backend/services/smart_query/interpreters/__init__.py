"""Smart Query Interpreters Module.

This module provides AI-powered interpretation of natural language queries
for the Smart Query feature. It is organized into three main interpreters:

- read_interpreter: For read-only queries (search, filter, aggregate)
- write_interpreter: For write commands (create, update, delete)
- plan_interpreter: For interactive Plan Mode (guidance, prompt generation)

All public symbols are re-exported here for backward compatibility.
"""

# Base utilities and constants
from .base import (
    # Constants
    AI_TEMPERATURE_LOW,
    AI_TEMPERATURE_MEDIUM,
    MAX_QUERY_LENGTH,
    MAX_TOKENS_COMPOUND,
    MAX_TOKENS_PLAN_MODE,
    MAX_TOKENS_QUERY,
    MAX_TOKENS_WRITE,
    MIN_QUERY_LENGTH,
    # Sanitization
    PROMPT_INJECTION_PATTERNS,
    PROMPT_INJECTION_REGEX_PATTERNS,
    SSE_EVENT_CHUNK,
    SSE_EVENT_DONE,
    SSE_EVENT_ERROR,
    SSE_EVENT_START,
    STREAMING_CONNECT_TIMEOUT,
    STREAMING_READ_TIMEOUT,
    STREAMING_TOTAL_TIMEOUT,
    TYPES_CACHE_TTL_SECONDS,
    # Cache
    TypesCache,
    _types_cache,
    _validate_query_input,
    # Client
    get_openai_client,
    invalidate_types_cache,
    load_all_types_for_write,
    # Database loading
    load_facet_and_entity_types,
    sanitize_conversation_messages,
    sanitize_user_input,
    # Validation
    validate_and_sanitize_query,
)

# Plan interpreter
from .plan_interpreter import (
    call_claude_for_plan_mode,
    call_claude_for_plan_mode_stream,
    interpret_plan_query,
    interpret_plan_query_stream,
)

# Read interpreter
from .read_interpreter import (
    build_dynamic_query_prompt,
    detect_compound_query,
    interpret_query,
)

# Write interpreter
from .write_interpreter import (
    interpret_write_command,
)

__all__ = [
    # Constants
    "AI_TEMPERATURE_LOW",
    "AI_TEMPERATURE_MEDIUM",
    "MAX_TOKENS_QUERY",
    "MAX_TOKENS_WRITE",
    "MAX_TOKENS_COMPOUND",
    "MAX_TOKENS_PLAN_MODE",
    "MAX_QUERY_LENGTH",
    "MIN_QUERY_LENGTH",
    "STREAMING_CONNECT_TIMEOUT",
    "STREAMING_READ_TIMEOUT",
    "STREAMING_TOTAL_TIMEOUT",
    "SSE_EVENT_START",
    "SSE_EVENT_CHUNK",
    "SSE_EVENT_DONE",
    "SSE_EVENT_ERROR",
    "TYPES_CACHE_TTL_SECONDS",
    # Cache
    "TypesCache",
    "_types_cache",
    "invalidate_types_cache",
    # Client
    "get_openai_client",
    # Sanitization
    "PROMPT_INJECTION_PATTERNS",
    "PROMPT_INJECTION_REGEX_PATTERNS",
    "sanitize_user_input",
    "sanitize_conversation_messages",
    # Validation
    "validate_and_sanitize_query",
    "_validate_query_input",
    # Database loading
    "load_facet_and_entity_types",
    "load_all_types_for_write",
    # Read interpreter
    "build_dynamic_query_prompt",
    "interpret_query",
    "detect_compound_query",
    # Write interpreter
    "interpret_write_command",
    # Plan interpreter
    "call_claude_for_plan_mode_stream",
    "call_claude_for_plan_mode",
    "interpret_plan_query",
    "interpret_plan_query_stream",
]
