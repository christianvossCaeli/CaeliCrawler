"""Utility modules for the application."""

from .text import normalize_entity_name, normalize_name, create_slug, normalize_for_search
from .validation import AssistantConstants, validate_uuid, validate_uuid_strict
from .security import (
    SecurityConstants,
    SecurityRiskLevel,
    SanitizationResult,
    sanitize_for_prompt,
    escape_for_json_prompt,
    escape_for_html,
    validate_message_length,
    should_block_request,
    create_safe_prompt_context,
    detect_injection_patterns,
    normalize_unicode,
    log_security_event,
)

__all__ = [
    # Text utilities
    "normalize_entity_name",
    "normalize_name",
    "create_slug",
    "normalize_for_search",
    # Validation utilities
    "AssistantConstants",
    "validate_uuid",
    "validate_uuid_strict",
    # Security utilities
    "SecurityConstants",
    "SecurityRiskLevel",
    "SanitizationResult",
    "sanitize_for_prompt",
    "escape_for_json_prompt",
    "escape_for_html",
    "validate_message_length",
    "should_block_request",
    "create_safe_prompt_context",
    "detect_injection_patterns",
    "normalize_unicode",
    "log_security_event",
]
