"""
In-memory cache with TTL support for frequently accessed data.

This module provides a simple caching mechanism for data that doesn't change
frequently, such as FacetTypes, EntityTypes, and other configuration data.

Features:
- TTL-based expiration
- Thread-safe operations
- Async-compatible
- Automatic cleanup of expired entries
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar
from uuid import UUID

import structlog

logger = structlog.get_logger()

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """A single cache entry with value and expiration time."""
    value: T
    expires_at: float
    created_at: float = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        return time.time() > self.expires_at


class TTLCache(Generic[T]):
    """
    A simple in-memory cache with TTL (Time To Live) support.

    Thread-safe and async-compatible for use in FastAPI applications.

    Usage:
        cache = TTLCache[FacetType](default_ttl=300)  # 5 minutes
        cache.set("key", value)
        cached = cache.get("key")

    For database-backed caching:
        facet_type = await facet_type_cache.get_or_fetch(
            "pain_point",
            fetch_fn=lambda: session.execute(select(FacetType).where(...))
        )
    """

    def __init__(
        self,
        default_ttl: int = 300,
        max_size: int = 1000,
        cleanup_interval: int = 60,
    ):
        """
        Initialize the cache.

        Args:
            default_ttl: Default time-to-live in seconds (default: 5 minutes)
            max_size: Maximum number of entries (default: 1000)
            cleanup_interval: Seconds between cleanup runs (default: 60)
        """
        self._cache: Dict[str, CacheEntry[T]] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[T]:
        """
        Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        self._maybe_cleanup()

        entry = self._cache.get(key)
        if entry is None:
            self._misses += 1
            return None

        if entry.is_expired:
            del self._cache[key]
            self._misses += 1
            return None

        self._hits += 1
        return entry.value

    def set(self, key: str, value: T, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override in seconds
        """
        self._maybe_cleanup()

        # Enforce max size by removing oldest entries
        if len(self._cache) >= self._max_size:
            self._evict_oldest()

        expires_at = time.time() + (ttl if ttl is not None else self._default_ttl)
        self._cache[key] = CacheEntry(value=value, expires_at=expires_at)

    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.

        Args:
            key: Cache key

        Returns:
            True if the key existed, False otherwise
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all entries from the cache."""
        self._cache.clear()
        logger.info("Cache cleared")

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching a pattern.

        Args:
            pattern: String pattern to match (simple contains check)

        Returns:
            Number of keys invalidated
        """
        keys_to_delete = [k for k in self._cache if pattern in k]
        for key in keys_to_delete:
            del self._cache[key]
        return len(keys_to_delete)

    async def get_or_fetch(
        self,
        key: str,
        fetch_fn: Callable[[], Any],
        ttl: Optional[int] = None,
    ) -> T:
        """
        Get from cache or fetch using provided function.

        This is the primary method for database-backed caching.

        Args:
            key: Cache key
            fetch_fn: Async function to fetch the value if not cached
            ttl: Optional TTL override

        Returns:
            Cached or fetched value
        """
        cached = self.get(key)
        if cached is not None:
            return cached

        # Fetch and cache
        if asyncio.iscoroutinefunction(fetch_fn):
            value = await fetch_fn()
        else:
            value = fetch_fn()

        if value is not None:
            self.set(key, value, ttl)

        return value

    def _maybe_cleanup(self) -> None:
        """Run cleanup if enough time has passed."""
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup()
            self._last_cleanup = now

    def _cleanup(self) -> None:
        """Remove all expired entries."""
        expired_keys = [k for k, v in self._cache.items() if v.is_expired]
        for key in expired_keys:
            del self._cache[key]
        if expired_keys:
            logger.debug("Cache cleanup", removed=len(expired_keys))

    def _evict_oldest(self) -> None:
        """Evict oldest entries when max size is reached."""
        # Sort by creation time and remove oldest 10%
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].created_at
        )
        evict_count = max(1, len(sorted_entries) // 10)
        for key, _ in sorted_entries[:evict_count]:
            del self._cache[key]
        logger.debug("Cache eviction", evicted=evict_count)

    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "ttl": self._default_ttl,
        }


# Global cache instances for commonly accessed data

# FacetType cache - 5 minute TTL
facet_type_cache: TTLCache[Any] = TTLCache(default_ttl=300, max_size=100)

# EntityType cache - 5 minute TTL
entity_type_cache: TTLCache[Any] = TTLCache(default_ttl=300, max_size=50)

# Category cache - 5 minute TTL
category_cache: TTLCache[Any] = TTLCache(default_ttl=300, max_size=100)

# AI Discovery cache - 30 minute TTL for expensive LLM operations
ai_discovery_cache: TTLCache[Any] = TTLCache(default_ttl=1800, max_size=200)

# Search strategy cache - 1 hour TTL
search_strategy_cache: TTLCache[Any] = TTLCache(default_ttl=3600, max_size=100)


def get_cache_stats() -> Dict[str, Dict[str, Any]]:
    """Get statistics for all caches."""
    return {
        "facet_types": facet_type_cache.stats,
        "entity_types": entity_type_cache.stats,
        "categories": category_cache.stats,
        "ai_discovery": ai_discovery_cache.stats,
        "search_strategy": search_strategy_cache.stats,
    }


def clear_all_caches() -> None:
    """Clear all application caches."""
    facet_type_cache.clear()
    entity_type_cache.clear()
    category_cache.clear()
    ai_discovery_cache.clear()
    search_strategy_cache.clear()
    logger.info("All caches cleared")


import hashlib
import json


def make_cache_key(*args: Any, **kwargs: Any) -> str:
    """
    Create a deterministic cache key from arguments.

    Args:
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key

    Returns:
        SHA256 hash of the serialized arguments (first 16 chars)
    """
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.sha256(key_data.encode()).hexdigest()[:16]


def cached_async(
    cache: TTLCache,
    key_prefix: str = "",
    ttl: Optional[int] = None,
):
    """
    Decorator for caching async function results.

    Args:
        cache: TTLCache instance to use
        key_prefix: Prefix for cache keys
        ttl: Optional TTL override

    Usage:
        @cached_async(ai_discovery_cache, key_prefix="strategy")
        async def generate_search_strategy(prompt: str) -> dict:
            ...
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Build cache key
            cache_key = f"{key_prefix}:{make_cache_key(*args, **kwargs)}" if key_prefix else make_cache_key(*args, **kwargs)

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug("Cache hit for function", func=func.__name__, key=cache_key)
                return cached_result

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            if result is not None:
                # Handle Pydantic models
                if hasattr(result, "model_dump"):
                    cache_data = result.model_dump()
                else:
                    cache_data = result

                cache.set(cache_key, cache_data, ttl=ttl)
                logger.debug("Cached function result", func=func.__name__, key=cache_key)

            return result

        return wrapper
    return decorator
