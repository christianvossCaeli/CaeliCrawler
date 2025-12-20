"""Validation utilities and constants for the application."""

from typing import Optional
from uuid import UUID


class AssistantConstants:
    """Constants for the Assistant service."""

    # Display limits
    MAX_FACET_TYPES_IN_LIST = 10
    SUGGESTED_FACET_TYPES_COUNT = 2
    MAX_CHAT_ITEMS_DISPLAY = 20
    MAX_VALUE_PREVIEW_LENGTH = 200
    MAX_PYSIS_FIELDS_DISPLAY = 30
    MAX_ENTITY_RESULTS = 50
    MAX_FACET_VALUES_IN_CONTEXT = 30
    MAX_ENTITY_LINKS_IN_MESSAGE = 3
    MAX_FACET_SUGGESTIONS = 5
    MAX_BATCH_PREVIEW_ITEMS = 20
    BATCH_OPERATION_LIMIT = 1000

    # AI settings
    AI_MAX_TOKENS = 1000
    AI_MAX_TOKENS_CONTEXT = 1000
    AI_MAX_TOKENS_INTENT = 500
    AI_MAX_TOKENS_FACET_SUGGEST = 500
    AI_TEMPERATURE = 0.3
    AI_TEMPERATURE_INTENT = 0.1
    AI_TEMPERATURE_CREATIVE = 0.7

    # Pagination
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100

    # String limits
    MAX_TEXT_REPRESENTATION_LENGTH = 500
    MAX_FACET_VALUE_PREVIEW = 200
    MAX_PYSIS_FIELD_PREVIEW = 500
    MAX_AI_RESPONSE_WORDS = 400

    # Attachment settings
    ATTACHMENT_MAX_SIZE_MB = 10
    ATTACHMENT_EXPIRY_HOURS = 1

    # Batch operation settings
    BATCH_POLL_INTERVAL_MS = 2000


def validate_uuid(value: Optional[str]) -> Optional[UUID]:
    """
    Safely convert a string to UUID.

    Args:
        value: String representation of UUID or None

    Returns:
        UUID object if valid, None otherwise
    """
    if not value:
        return None
    try:
        return UUID(value) if isinstance(value, str) else value
    except (ValueError, TypeError, AttributeError):
        return None


def validate_uuid_strict(value: str) -> UUID:
    """
    Convert string to UUID, raising ValueError if invalid.

    Args:
        value: String representation of UUID

    Returns:
        UUID object

    Raises:
        ValueError: If value is not a valid UUID
    """
    try:
        return UUID(value) if isinstance(value, str) else value
    except (ValueError, TypeError, AttributeError) as e:
        raise ValueError(f"Invalid UUID: {value}") from e
