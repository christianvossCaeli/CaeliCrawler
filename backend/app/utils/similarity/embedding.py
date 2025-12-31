"""
Core embedding generation and caching infrastructure.

This module provides:
- Embedding generation using Azure OpenAI
- LRU cache for embeddings (reduces API calls)
- Cosine similarity computation
- Statistics tracking for monitoring
"""

import hashlib
import os
from collections import OrderedDict
from threading import Lock

import structlog

logger = structlog.get_logger(__name__)

# =============================================================================
# Configuration - Consolidated Thresholds
# =============================================================================

# Single source of truth for all similarity thresholds
SIMILARITY_THRESHOLDS = {
    # Entity similarity (for deduplication within a type)
    "entity": float(os.getenv("ENTITY_SIMILARITY_THRESHOLD", "0.85")),
    # Type similarity (EntityType, FacetType, Category, RelationType)
    "type": float(os.getenv("TYPE_SIMILARITY_THRESHOLD", "0.80")),
    # Location similarity (stricter for geographic entities)
    "location": float(os.getenv("LOCATION_SIMILARITY_THRESHOLD", "0.90")),
}

# Default threshold for backward compatibility
DEFAULT_SIMILARITY_THRESHOLD = SIMILARITY_THRESHOLDS["entity"]

# Embedding dimensions (text-embedding-3-large with dimension reduction)
EMBEDDING_DIMENSIONS = 1536

# Cache configuration
EMBEDDING_CACHE_SIZE = int(os.getenv("EMBEDDING_CACHE_SIZE", "1000"))


# =============================================================================
# Statistics Tracking
# =============================================================================

_stats_lock = Lock()
_similarity_stats = {
    "searches": 0,
    "matches_found": 0,
    "embeddings_generated": 0,
    "cache_hits": 0,
}


def get_similarity_stats() -> dict:
    """Get current similarity matching statistics (thread-safe)."""
    with _stats_lock:
        return _similarity_stats.copy()


def reset_similarity_stats() -> None:
    """Reset similarity matching statistics (thread-safe)."""
    global _similarity_stats
    with _stats_lock:
        _similarity_stats = {
            "searches": 0,
            "matches_found": 0,
            "embeddings_generated": 0,
            "cache_hits": 0,
        }


def _increment_stat(key: str, amount: int = 1) -> None:
    """Thread-safe stat increment."""
    with _stats_lock:
        _similarity_stats[key] += amount


# =============================================================================
# Embedding Cache (True LRU using OrderedDict)
# =============================================================================

# In-memory LRU cache for embeddings (reduces API calls significantly)
_embedding_cache: OrderedDict[str, list[float]] = OrderedDict()
_cache_lock = Lock()


def _get_cache_key(text: str) -> str:
    """Generate a cache key for text."""
    return hashlib.md5(text.lower().strip().encode()).hexdigest()  # noqa: S324


def _get_cached_embedding(text: str) -> list[float] | None:
    """Get embedding from cache if available (moves to end for LRU)."""
    key = _get_cache_key(text)
    with _cache_lock:
        if key in _embedding_cache:
            # Move to end (most recently used)
            _embedding_cache.move_to_end(key)
            _increment_stat("cache_hits")
            return _embedding_cache[key]
    return None


def _set_cached_embedding(text: str, embedding: list[float]) -> None:
    """Store embedding in cache with LRU eviction."""
    key = _get_cache_key(text)
    with _cache_lock:
        # If key exists, update and move to end
        if key in _embedding_cache:
            _embedding_cache.move_to_end(key)
            _embedding_cache[key] = embedding
            return
        # Evict oldest (first) if cache is full
        while len(_embedding_cache) >= EMBEDDING_CACHE_SIZE:
            _embedding_cache.popitem(last=False)
        _embedding_cache[key] = embedding


def clear_embedding_cache() -> None:
    """Clear the embedding cache."""
    global _embedding_cache
    with _cache_lock:
        _embedding_cache = OrderedDict()


# =============================================================================
# Core Embedding Functions
# =============================================================================


async def generate_embedding(text: str, use_cache: bool = True) -> list[float] | None:
    """
    Generate embedding for text with caching.

    Args:
        text: Text to embed
        use_cache: Whether to use the LRU cache

    Returns:
        Embedding vector or None if generation failed
    """
    if not text or len(text) < 2:
        return None

    # Check cache first
    if use_cache:
        cached = _get_cached_embedding(text)
        if cached is not None:
            return cached

    # Generate new embedding
    from services.ai_service import AIService

    try:
        ai_service = AIService()
        embedding = await ai_service.generate_embedding(text)

        if embedding and use_cache:
            _set_cached_embedding(text, embedding)

        _increment_stat("embeddings_generated")
        return embedding
    except Exception as e:
        logger.error("Failed to generate embedding", text=text[:50], error=str(e))
        return None


# Alias for backwards compatibility
generate_entity_embedding = generate_embedding


async def generate_embeddings_batch(texts: list[str]) -> list[list[float] | None]:
    """
    Generate embeddings for multiple texts efficiently.

    Uses batch API call when available, falls back to individual calls.

    Args:
        texts: List of texts to embed

    Returns:
        List of embeddings (same order as input), None for failed items
    """
    if not texts:
        return []

    from services.ai_service import AIService

    try:
        ai_service = AIService()
        embeddings = await ai_service.generate_embeddings_batch(texts)
        _increment_stat("embeddings_generated", len([e for e in embeddings if e]))
        return embeddings
    except Exception as e:
        logger.error("Batch embedding failed, falling back to individual", error=str(e))
        # Fallback to individual
        return [await generate_embedding(t) for t in texts]


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    Returns value between -1 and 1 (usually 0-1 for embeddings).
    Returns 0.0 for invalid inputs.
    """
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    try:
        dot_product = sum(a * b for a, b in zip(vec1, vec2))  # noqa: B905
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)
    except (TypeError, ValueError):
        return 0.0


# Alias for internal use
_cosine_similarity = cosine_similarity


__all__ = [
    # Constants
    "SIMILARITY_THRESHOLDS",
    "DEFAULT_SIMILARITY_THRESHOLD",
    "EMBEDDING_DIMENSIONS",
    "EMBEDDING_CACHE_SIZE",
    # Stats
    "get_similarity_stats",
    "reset_similarity_stats",
    # Cache
    "clear_embedding_cache",
    # Core functions
    "generate_embedding",
    "generate_entity_embedding",
    "generate_embeddings_batch",
    "cosine_similarity",
    "_cosine_similarity",
    # Internal (for other modules in package)
    "_increment_stat",
    "_get_cached_embedding",
    "_set_cached_embedding",
]
