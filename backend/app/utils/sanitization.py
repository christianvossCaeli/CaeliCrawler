"""
Input Sanitization Utilities for CaeliCrawler.

Provides functions for sanitizing and validating user inputs to prevent:
- SQL injection (defense in depth, SQLAlchemy already parameterizes)
- XSS attacks in stored data
- Path traversal attacks
- Excessive input lengths
- Invalid characters
"""

import html
import re

# Maximum lengths for common input types
MAX_SEARCH_LENGTH = 200
MAX_NAME_LENGTH = 500
MAX_DESCRIPTION_LENGTH = 10000
MAX_URL_LENGTH = 2048
MAX_EMAIL_LENGTH = 254


def sanitize_search_input(value: str | None, max_length: int = MAX_SEARCH_LENGTH) -> str | None:
    """
    Sanitize search input for database queries.

    - Strips whitespace
    - Limits length
    - Removes potentially dangerous characters for LIKE queries
    - Escapes SQL LIKE wildcards if they shouldn't be user-controlled

    Args:
        value: The search string to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string or None if input was None/empty
    """
    if value is None:
        return None

    # Strip whitespace
    value = value.strip()

    if not value:
        return None

    # Limit length to prevent DoS
    if len(value) > max_length:
        value = value[:max_length]

    # Remove null bytes (can cause issues with C-based libraries)
    value = value.replace("\x00", "")

    # Note: We do NOT escape % and _ for LIKE queries here because
    # SQLAlchemy properly parameterizes queries. If you need to allow
    # literal % or _ search, escape them with: value.replace('%', '\\%').replace('_', '\\_')

    return value


def sanitize_name(value: str | None, max_length: int = MAX_NAME_LENGTH) -> str | None:
    """
    Sanitize a name field (entity names, user names, etc.).

    - Strips whitespace
    - Limits length
    - Removes control characters

    Args:
        value: The name to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string or None if input was None/empty
    """
    if value is None:
        return None

    # Strip whitespace
    value = value.strip()

    if not value:
        return None

    # Limit length
    if len(value) > max_length:
        value = value[:max_length]

    # Remove control characters (except newlines and tabs in some cases)
    value = "".join(char for char in value if char == "\n" or char == "\t" or not (0 <= ord(char) < 32))

    # Remove null bytes
    value = value.replace("\x00", "")

    return value


def sanitize_html_content(value: str | None, max_length: int = MAX_DESCRIPTION_LENGTH) -> str | None:
    """
    Sanitize content that might be displayed as HTML.

    - Escapes HTML special characters
    - Limits length
    - Removes control characters

    Use this for user-provided content that will be displayed in web pages.

    Args:
        value: The content to sanitize
        max_length: Maximum allowed length

    Returns:
        HTML-escaped string or None if input was None/empty
    """
    if value is None:
        return None

    # Strip whitespace
    value = value.strip()

    if not value:
        return None

    # Limit length first (before escaping, as escaping increases length)
    if len(value) > max_length:
        value = value[:max_length]

    # Escape HTML special characters
    value = html.escape(value, quote=True)

    return value


def sanitize_url(value: str | None, max_length: int = MAX_URL_LENGTH) -> str | None:
    """
    Sanitize a URL input.

    - Strips whitespace
    - Limits length
    - Basic URL validation

    Args:
        value: The URL to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized URL or None if input was None/empty/invalid
    """
    if value is None:
        return None

    # Strip whitespace
    value = value.strip()

    if not value:
        return None

    # Limit length
    if len(value) > max_length:
        return None  # URLs that are too long are likely invalid/malicious

    # Basic URL pattern check
    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
        r"localhost|"  # localhost
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # or IP
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )

    if not url_pattern.match(value):
        return None

    return value


def sanitize_path(value: str | None, max_length: int = 1000) -> str | None:
    """
    Sanitize a file path to prevent path traversal attacks.

    - Removes .. sequences
    - Removes absolute path indicators
    - Limits length

    Args:
        value: The path to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized path or None if input was None/empty
    """
    if value is None:
        return None

    # Strip whitespace
    value = value.strip()

    if not value:
        return None

    # Limit length
    if len(value) > max_length:
        value = value[:max_length]

    # Remove path traversal sequences
    # Replace multiple consecutive .. with empty string
    while ".." in value:
        value = value.replace("..", "")

    # Remove leading slashes (prevent absolute paths)
    value = value.lstrip("/")
    value = value.lstrip("\\")

    # Remove null bytes
    value = value.replace("\x00", "")

    return value if value else None


def sanitize_json_key(value: str | None, max_length: int = 100) -> str | None:
    """
    Sanitize a JSON key name.

    - Only allows alphanumeric characters, underscores, and hyphens
    - Limits length

    Args:
        value: The key name to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized key or None if input was None/empty/invalid
    """
    if value is None:
        return None

    # Strip whitespace
    value = value.strip()

    if not value:
        return None

    # Limit length
    if len(value) > max_length:
        value = value[:max_length]

    # Only allow alphanumeric, underscore, hyphen
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_-]*$", value):
        return None

    return value


def validate_uuid_string(value: str | None) -> bool:
    """
    Validate that a string is a valid UUID format.

    Args:
        value: The string to validate

    Returns:
        True if valid UUID format, False otherwise
    """
    if value is None:
        return False

    uuid_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE
    )

    return bool(uuid_pattern.match(value))


def sanitize_integer(value: str | None, min_val: int = 0, max_val: int = 1000000) -> int | None:
    """
    Safely parse and validate an integer from string input.

    Args:
        value: The string to parse
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        Parsed integer or None if invalid
    """
    if value is None:
        return None

    try:
        parsed = int(value)
        if min_val <= parsed <= max_val:
            return parsed
        return None
    except (ValueError, TypeError):
        return None
