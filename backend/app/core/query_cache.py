"""
Redis-based query cache for Smart Query results.

Provides a simple caching mechanism to avoid repeated expensive AI
interpretations and database queries for identical natural language queries.

Cache Strategy:
- Only cache read-only queries (not writes)
- TTL of 5 minutes (smart query results can change)
- Hash includes query text only (session-independent)
- Cache invalidation on write operations

Usage:
    from app.core.query_cache import get_cached_query, set_cached_query

    # Check cache first
    cached = await get_cached_query(question)
    if cached:
        return cached

    # Execute query and cache result
    result = await smart_query(session, question)
    await set_cached_query(question, result)
"""

import hashlib
import json
from typing import Any

import structlog
from redis.asyncio import Redis

logger = structlog.get_logger(__name__)

# Cache TTL in seconds (5 minutes)
QUERY_CACHE_TTL = 300

# Cache key prefix
CACHE_PREFIX = "sq:"

# Global Redis client (set during app startup)
_redis_client: Redis | None = None


def set_query_cache_client(client: Redis | None) -> None:
    """Set the Redis client for query caching."""
    global _redis_client
    _redis_client = client


def get_query_cache_client() -> Redis | None:
    """Get the Redis client for query caching."""
    return _redis_client


def _generate_cache_key(question: str) -> str:
    """
    Generate a deterministic cache key for a query.

    Uses SHA-256 hash of the lowercase, stripped question.
    """
    normalized = question.lower().strip()
    hash_digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"{CACHE_PREFIX}{hash_digest}"


async def get_cached_query(question: str) -> dict[str, Any] | None:
    """
    Get cached query result if available.

    Args:
        question: The natural language query

    Returns:
        Cached result dict or None if not cached
    """
    if not _redis_client:
        return None

    cache_key = _generate_cache_key(question)

    try:
        cached_data = await _redis_client.get(cache_key)
        if cached_data:
            logger.debug("Query cache hit", cache_key=cache_key)
            result = json.loads(cached_data)
            result["_cached"] = True
            return result
    except Exception as e:
        logger.warning("Query cache get failed", error=str(e), cache_key=cache_key)

    return None


async def set_cached_query(
    question: str,
    result: dict[str, Any],
    ttl: int = QUERY_CACHE_TTL,
) -> bool:
    """
    Cache a query result.

    Only caches successful read-only results. Skips caching for:
    - Write operations
    - Error results
    - Empty results

    Args:
        question: The natural language query
        result: The query result dict
        ttl: Time-to-live in seconds (default: 5 minutes)

    Returns:
        True if cached successfully, False otherwise
    """
    if not _redis_client:
        return False

    # Don't cache write operations or errors
    if result.get("mode") == "write":
        return False
    if result.get("error"):
        return False
    if result.get("items") is None and result.get("visualizations") is None:
        return False

    cache_key = _generate_cache_key(question)

    try:
        # Remove session-specific data before caching
        cache_data = result.copy()
        cache_data.pop("_cached", None)

        serialized = json.dumps(cache_data, default=str)
        await _redis_client.setex(cache_key, ttl, serialized)
        logger.debug("Query cached", cache_key=cache_key, ttl=ttl)
        return True
    except Exception as e:
        logger.warning("Query cache set failed", error=str(e), cache_key=cache_key)
        return False


async def invalidate_query_cache(pattern: str = "*") -> int:
    """
    Invalidate cached queries matching a pattern.

    Args:
        pattern: Key pattern to match (default: all smart query keys)

    Returns:
        Number of keys deleted
    """
    if not _redis_client:
        return 0

    try:
        # Find all matching keys
        full_pattern = f"{CACHE_PREFIX}{pattern}"
        keys = []
        async for key in _redis_client.scan_iter(match=full_pattern):
            keys.append(key)

        if keys:
            deleted = await _redis_client.delete(*keys)
            logger.info("Query cache invalidated", pattern=pattern, deleted=deleted)
            return deleted
        return 0
    except Exception as e:
        logger.warning("Query cache invalidation failed", error=str(e), pattern=pattern)
        return 0
