"""Utility modules for the application."""

from .datetime_utils import (
    DATE_FORMAT_DE,
    DATE_ISO_FORMAT,
    DATETIME_FORMAT_DE,
    DATETIME_FORMAT_DE_FULL,
    ISO_FORMAT,
    days_between,
    ensure_utc,
    format_date,
    format_datetime,
    format_iso,
    format_relative_time,
    is_this_week,
    is_today,
    now_utc,
    parse_date,
    parse_datetime,
)
from .security import (
    SanitizationResult,
    SecurityConstants,
    SecurityRiskLevel,
    create_safe_prompt_context,
    detect_injection_patterns,
    escape_for_html,
    escape_for_json_prompt,
    log_security_event,
    normalize_unicode,
    sanitize_for_prompt,
    should_block_request,
    validate_message_length,
)
from .text import create_slug, normalize_entity_name, normalize_for_search, normalize_name
from .validation import AssistantConstants, validate_uuid, validate_uuid_strict

__all__ = [
    # Datetime utilities
    "DATE_FORMAT_DE",
    "DATETIME_FORMAT_DE",
    "DATETIME_FORMAT_DE_FULL",
    "ISO_FORMAT",
    "DATE_ISO_FORMAT",
    "now_utc",
    "ensure_utc",
    "format_datetime",
    "format_date",
    "format_iso",
    "format_relative_time",
    "parse_datetime",
    "parse_date",
    "is_today",
    "is_this_week",
    "days_between",
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
