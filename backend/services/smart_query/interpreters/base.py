"""Base utilities for Smart Query interpreters.

This module contains shared utilities, caching, constants, and sanitization
functions used by all interpreter modules.
"""

import re
import time
from typing import Any, Dict, List, Optional, Tuple

import structlog
from openai import AzureOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = structlog.get_logger()


# =============================================================================
# Constants
# =============================================================================

# AI Model Parameters
AI_TEMPERATURE_LOW = 0.1  # For precise, deterministic responses
AI_TEMPERATURE_MEDIUM = 0.2  # For creative but still consistent responses

# Token limits for different operations
MAX_TOKENS_QUERY = 1000
MAX_TOKENS_WRITE = 2000
MAX_TOKENS_COMPOUND = 1500
MAX_TOKENS_PLAN_MODE = 2000

# Query validation limits
MAX_QUERY_LENGTH = 2000  # Maximum characters in a query
MIN_QUERY_LENGTH = 3  # Minimum characters in a query

# Streaming Timeout Configuration
STREAMING_CONNECT_TIMEOUT = 10.0  # 10 seconds to establish connection
STREAMING_READ_TIMEOUT = 30.0  # 30 seconds between chunks
STREAMING_TOTAL_TIMEOUT = 120.0  # 120 seconds total for streaming

# SSE Event Types
SSE_EVENT_START = "start"
SSE_EVENT_CHUNK = "chunk"
SSE_EVENT_DONE = "done"
SSE_EVENT_ERROR = "error"


# =============================================================================
# TTL Cache for Database Types
# =============================================================================

TYPES_CACHE_TTL_SECONDS = 300  # 5 minutes


class TypesCache:
    """Simple TTL cache for entity types, facet types, etc.

    This cache reduces database queries when building prompts for
    AI interpretation, especially useful for Plan Mode which may
    make multiple queries in quick succession.
    """

    def __init__(self, ttl_seconds: int = TYPES_CACHE_TTL_SECONDS):
        self.ttl_seconds = ttl_seconds
        self._facet_entity_cache: Optional[Tuple[List[Dict], List[Dict]]] = None
        self._facet_entity_timestamp: float = 0
        self._all_types_cache: Optional[Tuple[List[Dict], List[Dict], List[Dict], List[Dict]]] = None
        self._all_types_timestamp: float = 0

    def get_facet_entity_types(self) -> Optional[Tuple[List[Dict], List[Dict]]]:
        """Get cached facet and entity types if not expired."""
        if self._facet_entity_cache is None:
            return None
        if time.time() - self._facet_entity_timestamp > self.ttl_seconds:
            self._facet_entity_cache = None
            return None
        return self._facet_entity_cache

    def set_facet_entity_types(self, data: Tuple[List[Dict], List[Dict]]) -> None:
        """Cache facet and entity types."""
        self._facet_entity_cache = data
        self._facet_entity_timestamp = time.time()

    def get_all_types(self) -> Optional[Tuple[List[Dict], List[Dict], List[Dict], List[Dict]]]:
        """Get cached all types (entity, facet, relation, category) if not expired."""
        if self._all_types_cache is None:
            return None
        if time.time() - self._all_types_timestamp > self.ttl_seconds:
            self._all_types_cache = None
            return None
        return self._all_types_cache

    def set_all_types(self, data: Tuple[List[Dict], List[Dict], List[Dict], List[Dict]]) -> None:
        """Cache all types."""
        self._all_types_cache = data
        self._all_types_timestamp = time.time()

    def invalidate(self) -> None:
        """Invalidate all caches."""
        self._facet_entity_cache = None
        self._all_types_cache = None
        logger.debug("Types cache invalidated")


# Global cache instance
_types_cache = TypesCache()


def invalidate_types_cache() -> None:
    """Invalidate the types cache.

    Call this when entity types, facet types, relation types,
    or categories are created, updated, or deleted.
    """
    _types_cache.invalidate()


# =============================================================================
# Azure OpenAI Client
# =============================================================================

# Azure OpenAI client - initialized lazily
_client = None


def get_openai_client() -> AzureOpenAI:
    """Get or create the Azure OpenAI client.

    Raises:
        ValueError: If Azure OpenAI is not configured
    """
    global _client
    if _client is None:
        if not settings.azure_openai_api_key:
            raise ValueError("KI-Service nicht erreichbar: Azure OpenAI ist nicht konfiguriert")
        _client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint,
        )
    return _client


# =============================================================================
# Prompt Injection Sanitization
# =============================================================================

# Patterns that could be used for prompt injection attacks
PROMPT_INJECTION_PATTERNS = [
    # OpenAI/ChatGPT control tokens
    "<|im_start|>",
    "<|im_end|>",
    "<|endoftext|>",
    "<|system|>",
    "<|user|>",
    "<|assistant|>",

    # Anthropic/Claude control tokens
    "\n\nHuman:",
    "\n\nAssistant:",
    "[INST]",
    "[/INST]",
    "<<SYS>>",
    "<</SYS>>",

    # Common role injection attempts
    "system:",
    "System:",
    "SYSTEM:",
    "Human:",
    "HUMAN:",
    "Assistant:",
    "ASSISTANT:",
    "user:",
    "User:",
    "USER:",

    # Instruction override attempts (case variations handled separately)
    "ignore previous instructions",
    "ignore all previous",
    "forget your instructions",
    "disregard previous",
    "override system",
    "new instructions:",
    "actual instructions:",
    "real instructions:",
    "true instructions:",

    # Role-play injection
    "you are now",
    "pretend you are",
    "act as if",
    "from now on you",
    "simulate being",
    "roleplay as",
    "behave like",

    # Delimiter injection
    "---BEGIN SYSTEM---",
    "---END SYSTEM---",
    "###SYSTEM###",
    "===SYSTEM===",
    "[SYSTEM]",
    "[/SYSTEM]",
    "```system",
    "```instruction",
]

# Regex patterns for more complex injection attempts
PROMPT_INJECTION_REGEX_PATTERNS = [
    # XML-style tags that could confuse the model
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"<\s*/\s*system\s*>", re.IGNORECASE),
    re.compile(r"<\s*instruction\s*>", re.IGNORECASE),
    re.compile(r"<\s*/\s*instruction\s*>", re.IGNORECASE),
    re.compile(r"<\s*prompt\s*>", re.IGNORECASE),
    re.compile(r"<\s*/\s*prompt\s*>", re.IGNORECASE),

    # Unicode escape sequences that could bypass filters
    re.compile(r"\\u[0-9a-fA-F]{4}"),  # \u0048 etc.
    re.compile(r"&#x?[0-9a-fA-F]+;"),  # HTML entities

    # Base64 encoded content (potential hidden instructions)
    re.compile(r"[A-Za-z0-9+/]{50,}={0,2}"),  # Long base64 strings

    # Excessive whitespace manipulation
    re.compile(r"\n{5,}"),  # More than 4 consecutive newlines
    re.compile(r" {10,}"),  # More than 9 consecutive spaces
]


def sanitize_user_input(content: str, max_length: int = MAX_QUERY_LENGTH) -> str:
    """Sanitize user input to prevent prompt injection attacks.

    This function removes or neutralizes patterns that could be used to:
    - Override system instructions
    - Inject new roles or personas
    - Bypass safety guidelines
    - Manipulate the AI's behavior

    Args:
        content: The user input to sanitize
        max_length: Maximum allowed length (truncated if exceeded)

    Returns:
        Sanitized content string
    """
    if not content:
        return ""

    # Step 1: Truncate to max length
    if len(content) > max_length:
        content = content[:max_length]
        logger.warning("User input truncated", original_length=len(content), max_length=max_length)

    # Step 2: Remove exact pattern matches (case-sensitive first)
    for pattern in PROMPT_INJECTION_PATTERNS:
        content = content.replace(pattern, "")

    # Step 3: Case-insensitive removal of dangerous patterns
    dangerous_phrases = [
        "ignore previous",
        "ignore all",
        "forget your",
        "disregard",
        "override",
        "new instruction",
        "actual instruction",
        "real instruction",
        "true instruction",
    ]
    content_lower = content.lower()
    for phrase in dangerous_phrases:
        # Find and remove case-insensitively while preserving surrounding text
        idx = content_lower.find(phrase)
        while idx != -1:
            content = content[:idx] + content[idx + len(phrase):]
            content_lower = content.lower()
            idx = content_lower.find(phrase)

    # Step 4: Apply regex patterns
    for regex in PROMPT_INJECTION_REGEX_PATTERNS:
        content = regex.sub("", content)

    # Step 5: Normalize whitespace (but preserve intentional formatting)
    content = re.sub(r"\n{3,}", "\n\n", content)  # Max 2 consecutive newlines
    content = re.sub(r" {3,}", "  ", content)  # Max 2 consecutive spaces

    # Step 6: Strip and clean
    content = content.strip()

    return content


def sanitize_conversation_messages(
    messages: List[Dict[str, str]],
    max_messages: int = 20,
) -> List[Dict[str, str]]:
    """Sanitize a list of conversation messages.

    Args:
        messages: List of {"role": "user"|"assistant", "content": "..."} dicts
        max_messages: Maximum number of messages to keep

    Returns:
        Sanitized list of messages
    """
    if not messages:
        return []

    # Limit number of messages (keep first and last n-1)
    if len(messages) > max_messages:
        messages = [messages[0]] + messages[-(max_messages - 1):]
        logger.info("Conversation history truncated", kept=max_messages)

    sanitized = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        # Validate role
        if role not in ("user", "assistant"):
            role = "user"

        # Sanitize content
        sanitized_content = sanitize_user_input(content)

        if sanitized_content:  # Only keep non-empty messages
            sanitized.append({
                "role": role,
                "content": sanitized_content,
            })

    return sanitized


# =============================================================================
# Query Validation
# =============================================================================

def validate_and_sanitize_query(question: str) -> str:
    """Validate and sanitize query input.

    Args:
        question: The query string to validate and sanitize

    Returns:
        Sanitized query string

    Raises:
        ValueError: If query is invalid (empty, too short, or too long after sanitization)
    """
    if not question or not question.strip():
        raise ValueError("Query cannot be empty")

    # Sanitize the input first
    sanitized = sanitize_user_input(question)

    if not sanitized:
        raise ValueError("Query cannot be empty after sanitization")

    query_length = len(sanitized)
    if query_length < MIN_QUERY_LENGTH:
        raise ValueError(f"Query too short (min {MIN_QUERY_LENGTH} characters)")
    if query_length > MAX_QUERY_LENGTH:
        raise ValueError(f"Query too long (max {MAX_QUERY_LENGTH} characters)")

    return sanitized


# Legacy function - use validate_and_sanitize_query instead
def _validate_query_input(question: str) -> None:
    """Validate query input for length and content (legacy).

    Args:
        question: The query string to validate

    Raises:
        ValueError: If query is invalid
    """
    validate_and_sanitize_query(question)


# =============================================================================
# Database Type Loading
# =============================================================================

async def load_facet_and_entity_types(session: AsyncSession) -> Tuple[List[Dict], List[Dict]]:
    """Load facet types and entity types from the database with TTL caching."""
    from app.models import FacetType, EntityType

    # Check cache first
    cached = _types_cache.get_facet_entity_types()
    if cached is not None:
        logger.debug("Using cached facet and entity types")
        return cached

    logger.debug("Loading facet and entity types from database")

    # Load facet types
    facet_result = await session.execute(
        select(FacetType).where(FacetType.is_active.is_(True)).order_by(FacetType.display_order)
    )
    facet_types = [
        {
            "slug": ft.slug,
            "name": ft.name,
            "description": ft.description,
            "is_time_based": ft.is_time_based,
        }
        for ft in facet_result.scalars().all()
    ]

    # Load entity types
    entity_result = await session.execute(
        select(EntityType).where(EntityType.is_active.is_(True)).order_by(EntityType.display_order)
    )
    entity_types = [
        {
            "slug": et.slug,
            "name": et.name,
            "description": et.description,
        }
        for et in entity_result.scalars().all()
    ]

    # Cache the result
    result = (facet_types, entity_types)
    _types_cache.set_facet_entity_types(result)

    return result


async def load_all_types_for_write(session: AsyncSession) -> Tuple[List[Dict], List[Dict], List[Dict], List[Dict]]:
    """Load all types needed for write command interpretation with TTL caching.

    Returns:
        Tuple of (entity_types, facet_types, relation_types, categories)
    """
    from app.models import FacetType, EntityType, RelationType, Category

    # Check cache first
    cached = _types_cache.get_all_types()
    if cached is not None:
        logger.debug("Using cached all types (entity, facet, relation, category)")
        return cached

    logger.debug("Loading all types from database")

    # Load entity types with full details
    entity_result = await session.execute(
        select(EntityType).where(EntityType.is_active.is_(True)).order_by(EntityType.display_order)
    )
    entity_types = [
        {
            "slug": et.slug,
            "name": et.name,
            "description": et.description,
            "supports_hierarchy": et.supports_hierarchy,
            "attribute_schema": et.attribute_schema,
        }
        for et in entity_result.scalars().all()
    ]

    # Load facet types with applicable entity types
    facet_result = await session.execute(
        select(FacetType).where(FacetType.is_active.is_(True)).order_by(FacetType.display_order)
    )
    facet_types = [
        {
            "slug": ft.slug,
            "name": ft.name,
            "description": ft.description,
            "applicable_entity_type_slugs": ft.applicable_entity_type_slugs or [],
        }
        for ft in facet_result.scalars().all()
    ]

    # Load relation types
    relation_result = await session.execute(
        select(RelationType).where(RelationType.is_active.is_(True))
    )
    relation_types = [
        {
            "slug": rt.slug,
            "name": rt.name,
            "description": rt.description,
        }
        for rt in relation_result.scalars().all()
    ]

    # Load categories
    category_result = await session.execute(
        select(Category).where(Category.is_active.is_(True))
    )
    categories = [
        {
            "slug": cat.slug,
            "name": cat.name,
            "description": cat.description,
        }
        for cat in category_result.scalars().all()
    ]

    # Cache the result
    result = (entity_types, facet_types, relation_types, categories)
    _types_cache.set_all_types(result)

    return result


# =============================================================================
# Exports
# =============================================================================

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
]
