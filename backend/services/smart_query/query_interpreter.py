"""Query interpretation for Smart Query Service - AI-powered NLP query parsing.

This module re-exports all interpreter functionality from the interpreters submodule
for backward compatibility. New code should import directly from:

    from backend.services.smart_query.interpreters import (
        interpret_query,
        interpret_write_command,
        interpret_plan_query,
        # etc.
    )

The interpreters submodule provides better organization:
- interpreters/base.py: Shared utilities, constants, caching, sanitization
- interpreters/read_interpreter.py: Read query interpretation
- interpreters/write_interpreter.py: Write command interpretation
- interpreters/plan_interpreter.py: Plan mode with streaming support
"""

# Re-export everything from the interpreters module for backward compatibility
from .interpreters import (
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
    # Read interpreter
    build_dynamic_query_prompt,
    call_claude_for_plan_mode,
    # Plan interpreter
    call_claude_for_plan_mode_stream,
    detect_compound_query,
    # Client
    get_openai_client,
    interpret_plan_query,
    interpret_plan_query_stream,
    interpret_query,
    # Write interpreter
    interpret_write_command,
    invalidate_types_cache,
    load_all_types_for_write,
    # Database loading
    load_facet_and_entity_types,
    sanitize_conversation_messages,
    sanitize_user_input,
    # Validation
    validate_and_sanitize_query,
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
