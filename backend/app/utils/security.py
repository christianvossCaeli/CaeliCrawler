"""Security utilities for input sanitization and prompt injection protection.

This module provides comprehensive protection against prompt injection attacks
and other security concerns when working with LLM-based services.

Key features:
- Input sanitization and length validation
- Prompt injection detection
- Safe string escaping for AI prompts
- Unicode normalization
"""

import html
import json
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class SecurityRiskLevel(str, Enum):
    """Risk level classification for detected threats."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SanitizationResult:
    """Result of input sanitization."""
    sanitized_text: str
    original_length: int
    sanitized_length: int
    was_truncated: bool
    detected_risks: list[str]
    risk_level: SecurityRiskLevel


class SecurityConstants:
    """Security-related constants."""

    # Input length limits
    MAX_MESSAGE_LENGTH = 5000  # Max characters for chat messages
    MAX_PROMPT_LENGTH = 10000  # Max characters for custom prompts
    MAX_QUERY_LENGTH = 2000   # Max characters for search queries
    MAX_FIELD_LENGTH = 500    # Max characters for form fields

    # Truncation limits for AI context
    MAX_CONTEXT_LENGTH = 100000  # Max chars for AI context

    # Rate limiting (requests per minute)
    DEFAULT_RATE_LIMIT = 60
    AI_RATE_LIMIT = 30


# Prompt injection detection patterns
# These patterns detect common prompt injection techniques
INJECTION_PATTERNS: list[tuple[str, str, SecurityRiskLevel]] = [
    # Direct instruction override attempts
    (r"(?i)\bignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)",
     "instruction_override", SecurityRiskLevel.HIGH),
    (r"(?i)\bdisregard\s+(all\s+)?(previous|above|prior)",
     "instruction_override", SecurityRiskLevel.HIGH),
    (r"(?i)\bforget\s+(everything|all|what)\s+(you|i)?\s*(know|told|said)",
     "instruction_override", SecurityRiskLevel.HIGH),

    # Role manipulation attempts
    (r"(?i)\byou\s+are\s+(now|actually)\s+a\s+",
     "role_manipulation", SecurityRiskLevel.HIGH),
    (r"(?i)\bact\s+as\s+(if\s+you\s+are|a)\s+",
     "role_manipulation", SecurityRiskLevel.MEDIUM),
    (r"(?i)\bpretend\s+(to\s+be|you're|you\s+are)\s+",
     "role_manipulation", SecurityRiskLevel.MEDIUM),
    (r"(?i)\bsystem\s*:\s*",
     "system_prompt_injection", SecurityRiskLevel.CRITICAL),
    (r"(?i)\bassistant\s*:\s*",
     "assistant_injection", SecurityRiskLevel.HIGH),

    # Data exfiltration attempts
    (r"(?i)\brepeat\s+(back|your|the)\s+(system\s+)?(prompt|instructions?)",
     "data_exfiltration", SecurityRiskLevel.HIGH),
    (r"(?i)\btell\s+me\s+(your|the)\s+(system\s+)?(prompt|instructions?)",
     "data_exfiltration", SecurityRiskLevel.HIGH),
    (r"(?i)\bwhat\s+(is|are)\s+your\s+(system\s+)?(prompt|instructions?)",
     "data_exfiltration", SecurityRiskLevel.MEDIUM),
    (r"(?i)\bshow\s+(me\s+)?(your|the)\s+(hidden|secret|system)",
     "data_exfiltration", SecurityRiskLevel.MEDIUM),

    # Code injection attempts
    (r"(?i)\bexecute\s+(this\s+)?(code|script|command)",
     "code_injection", SecurityRiskLevel.CRITICAL),
    (r"(?i)\brun\s+(this\s+)?(python|javascript|bash|sql|code)",
     "code_injection", SecurityRiskLevel.CRITICAL),
    (r"(?i)\b(import|require|exec|eval)\s*\(",
     "code_injection", SecurityRiskLevel.HIGH),

    # Jailbreak attempts
    (r"(?i)\bjailbreak",
     "jailbreak_attempt", SecurityRiskLevel.HIGH),
    (r"(?i)\bdan\s+(mode|prompt)",
     "jailbreak_attempt", SecurityRiskLevel.HIGH),
    (r"(?i)\bdeveloper\s+mode\s+(enabled|on|activated)",
     "jailbreak_attempt", SecurityRiskLevel.HIGH),

    # Delimiter manipulation
    (r"```\s*(system|prompt|instruction)",
     "delimiter_manipulation", SecurityRiskLevel.MEDIUM),
    (r"<\|.*?\|>",
     "special_tokens", SecurityRiskLevel.MEDIUM),
    (r"\[\[.*?(system|prompt|instruction).*?\]\]",
     "bracket_injection", SecurityRiskLevel.MEDIUM),

    # Unicode obfuscation (homoglyphs)
    (r"[\u200b-\u200f\u2028-\u202f\ufeff]",
     "unicode_obfuscation", SecurityRiskLevel.LOW),
]


def normalize_unicode(text: str) -> str:
    """Normalize Unicode text to prevent homoglyph attacks.

    Uses NFKC normalization which:
    - Converts compatibility characters to their canonical form
    - Combines combining characters with their base characters
    - Normalizes visually similar characters

    Args:
        text: Input text to normalize

    Returns:
        Normalized text
    """
    if not text:
        return ""

    # NFKC normalization
    normalized = unicodedata.normalize("NFKC", text)

    # Remove zero-width characters and other invisible Unicode
    invisible_chars = re.compile(r"[\u200b-\u200f\u2028-\u202f\ufeff\u00ad]")
    normalized = invisible_chars.sub("", normalized)

    return normalized


def detect_injection_patterns(text: str) -> list[tuple[str, SecurityRiskLevel]]:
    """Detect potential prompt injection patterns in text.

    Args:
        text: Text to analyze

    Returns:
        List of (pattern_name, risk_level) tuples for detected patterns
    """
    detected = []
    normalized_text = normalize_unicode(text.lower())

    for pattern, name, risk_level in INJECTION_PATTERNS:
        if re.search(pattern, normalized_text):
            detected.append((name, risk_level))
            logger.warning(
                "prompt_injection_pattern_detected",
                pattern=name,
                risk_level=risk_level.value,
                text_preview=text[:100],
            )

    return detected


def get_max_risk_level(risks: list[tuple[str, SecurityRiskLevel]]) -> SecurityRiskLevel:
    """Get the maximum risk level from a list of detected risks.

    Args:
        risks: List of (pattern_name, risk_level) tuples

    Returns:
        Highest risk level found, or NONE if no risks
    """
    if not risks:
        return SecurityRiskLevel.NONE

    risk_order = [
        SecurityRiskLevel.NONE,
        SecurityRiskLevel.LOW,
        SecurityRiskLevel.MEDIUM,
        SecurityRiskLevel.HIGH,
        SecurityRiskLevel.CRITICAL,
    ]

    max_level = SecurityRiskLevel.NONE
    for _, risk_level in risks:
        if risk_order.index(risk_level) > risk_order.index(max_level):
            max_level = risk_level

    return max_level


def sanitize_for_prompt(text: str, max_length: int = SecurityConstants.MAX_MESSAGE_LENGTH) -> SanitizationResult:
    """Sanitize user input for safe inclusion in AI prompts.

    This function:
    1. Normalizes Unicode
    2. Truncates to max length
    3. Detects injection patterns
    4. Escapes special characters

    Args:
        text: User input text
        max_length: Maximum allowed length

    Returns:
        SanitizationResult with sanitized text and risk assessment
    """
    if not text:
        return SanitizationResult(
            sanitized_text="",
            original_length=0,
            sanitized_length=0,
            was_truncated=False,
            detected_risks=[],
            risk_level=SecurityRiskLevel.NONE,
        )

    original_length = len(text)

    # Step 1: Unicode normalization
    sanitized = normalize_unicode(text)

    # Step 2: Detect injection patterns BEFORE sanitization
    detected = detect_injection_patterns(sanitized)
    risk_level = get_max_risk_level(detected)

    # Step 3: Truncate if needed
    was_truncated = len(sanitized) > max_length
    if was_truncated:
        sanitized = sanitized[:max_length]
        logger.warning(
            "input_truncated",
            original_length=original_length,
            max_length=max_length,
        )

    # Step 4: Escape potential delimiter characters
    # This prevents manipulation of the prompt structure
    sanitized = sanitized.replace("```", "` ` `")
    sanitized = sanitized.replace("###", "# # #")
    sanitized = sanitized.replace("---", "- - -")

    return SanitizationResult(
        sanitized_text=sanitized,
        original_length=original_length,
        sanitized_length=len(sanitized),
        was_truncated=was_truncated,
        detected_risks=[r[0] for r in detected],
        risk_level=risk_level,
    )


def escape_for_json_prompt(value: Any) -> str:
    """Escape a value for safe inclusion in JSON within a prompt.

    This ensures user-controlled data cannot break JSON structure
    or inject additional prompt content.

    Args:
        value: Value to escape (will be converted to string)

    Returns:
        JSON-safe escaped string
    """
    if value is None:
        return "null"

    # Convert to string and normalize
    str_value = str(value)
    str_value = normalize_unicode(str_value)

    # Use json.dumps to properly escape
    escaped = json.dumps(str_value, ensure_ascii=False)

    # Remove the surrounding quotes (json.dumps adds them)
    return escaped[1:-1]


def escape_for_html(text: str) -> str:
    """Escape text for safe HTML display.

    Args:
        text: Text to escape

    Returns:
        HTML-escaped text
    """
    return html.escape(text, quote=True)


def validate_message_length(
    message: str,
    max_length: int = SecurityConstants.MAX_MESSAGE_LENGTH
) -> tuple[bool, str | None]:
    """Validate message length.

    Args:
        message: Message to validate
        max_length: Maximum allowed length

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not message:
        return True, None

    if len(message) > max_length:
        return False, f"Nachricht zu lang ({len(message)} Zeichen). Maximum: {max_length} Zeichen."

    return True, None


def should_block_request(risk_level: SecurityRiskLevel) -> bool:
    """Determine if a request should be blocked based on risk level.

    Args:
        risk_level: Detected risk level

    Returns:
        True if request should be blocked
    """
    return risk_level in (SecurityRiskLevel.HIGH, SecurityRiskLevel.CRITICAL)


def create_safe_prompt_context(
    user_input: str,
    context_data: dict[str, Any],
    max_input_length: int = SecurityConstants.MAX_MESSAGE_LENGTH,
    max_context_length: int = SecurityConstants.MAX_CONTEXT_LENGTH,
) -> tuple[str, dict[str, str], SanitizationResult]:
    """Create a safe prompt context with sanitized user input and data.

    This is the main function to use when constructing AI prompts
    that include user-provided data.

    Args:
        user_input: The user's raw input text
        context_data: Dictionary of context data to include
        max_input_length: Max length for user input
        max_context_length: Max total context length

    Returns:
        Tuple of (sanitized_input, sanitized_context, sanitization_result)
    """
    # Sanitize user input
    result = sanitize_for_prompt(user_input, max_input_length)

    # Sanitize context data
    safe_context = {}
    for key, value in context_data.items():
        if value is None:
            safe_context[key] = ""
        elif isinstance(value, (list, dict)):
            # JSON-encode complex types
            json_str = json.dumps(value, ensure_ascii=False, default=str)
            if len(json_str) > max_context_length // len(context_data):
                json_str = json_str[:max_context_length // len(context_data)] + "..."
            safe_context[key] = json_str
        else:
            str_value = str(value)
            safe_context[key] = escape_for_json_prompt(str_value)

    return result.sanitized_text, safe_context, result


def log_security_event(
    event_type: str,
    risk_level: SecurityRiskLevel,
    details: dict[str, Any],
    user_id: str | None = None,
) -> None:
    """Log a security-relevant event.

    Args:
        event_type: Type of security event
        risk_level: Risk level of the event
        details: Additional event details
        user_id: Optional user identifier
    """
    logger.warning(
        "security_event",
        event_type=event_type,
        risk_level=risk_level.value,
        user_id=user_id,
        **details,
    )
