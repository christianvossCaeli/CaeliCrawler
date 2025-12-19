"""
Rate Limiting for API endpoints.

Uses Redis to track request counts per IP/user.
Includes in-memory fallback when Redis is unavailable.
"""

import time
from collections import defaultdict
from threading import Lock
from typing import Dict, Optional, Tuple

from fastapi import HTTPException, Request, status
from redis.asyncio import Redis

from app.config import settings


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter as fallback when Redis is unavailable.

    Note: This is per-process only and won't work correctly with multiple workers.
    It's a security fallback, not a replacement for Redis.
    """

    def __init__(self):
        self._data: Dict[str, Tuple[int, float]] = {}  # key -> (count, window_start)
        self._lock = Lock()

    def check(
        self,
        key_prefix: str,
        identifier: str,
        max_requests: int,
        window_seconds: int,
    ) -> bool:
        """Check if request is allowed under rate limit."""
        key = f"{key_prefix}:{identifier}"
        current_time = time.time()

        with self._lock:
            if key in self._data:
                count, window_start = self._data[key]

                # Check if window has expired
                if current_time - window_start >= window_seconds:
                    # Reset window
                    self._data[key] = (1, current_time)
                    return True

                if count >= max_requests:
                    ttl = int(window_seconds - (current_time - window_start))
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Too many requests. Try again in {ttl} seconds.",
                        headers={"Retry-After": str(ttl)},
                    )

                # Increment counter
                self._data[key] = (count + 1, window_start)
            else:
                # First request
                self._data[key] = (1, current_time)

            return True

    def reset(self, key_prefix: str, identifier: str) -> None:
        """Reset rate limit counter."""
        key = f"{key_prefix}:{identifier}"
        with self._lock:
            self._data.pop(key, None)

    def cleanup_expired(self, max_age_seconds: int = 3600) -> None:
        """Remove expired entries to prevent memory growth."""
        current_time = time.time()
        with self._lock:
            expired_keys = [
                k for k, (_, window_start) in self._data.items()
                if current_time - window_start > max_age_seconds
            ]
            for key in expired_keys:
                del self._data[key]


class RateLimiter:
    """
    Redis-based rate limiter.

    Usage:
        limiter = RateLimiter(redis)
        await limiter.check("login", request.client.host, max_requests=5, window_seconds=60)
    """

    def __init__(self, redis: Redis):
        self.redis = redis

    async def check(
        self,
        key_prefix: str,
        identifier: str,
        max_requests: int,
        window_seconds: int,
    ) -> bool:
        """
        Check if request is allowed under rate limit.

        Args:
            key_prefix: Type of action (e.g., "login", "api")
            identifier: User identifier (IP, user_id, etc.)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            True if allowed, raises HTTPException if rate limited
        """
        key = f"rate_limit:{key_prefix}:{identifier}"

        # Get current count
        current = await self.redis.get(key)

        if current is None:
            # First request, set counter with expiry
            await self.redis.setex(key, window_seconds, 1)
            return True

        current_count = int(current)

        if current_count >= max_requests:
            # Get remaining TTL for error message
            ttl = await self.redis.ttl(key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests. Try again in {ttl} seconds.",
                headers={"Retry-After": str(ttl)},
            )

        # Increment counter
        await self.redis.incr(key)
        return True

    async def reset(self, key_prefix: str, identifier: str) -> None:
        """Reset rate limit counter (e.g., after successful login)."""
        key = f"rate_limit:{key_prefix}:{identifier}"
        await self.redis.delete(key)

    async def get_remaining(
        self,
        key_prefix: str,
        identifier: str,
        max_requests: int,
    ) -> int:
        """Get remaining requests in current window."""
        key = f"rate_limit:{key_prefix}:{identifier}"
        current = await self.redis.get(key)

        if current is None:
            return max_requests

        return max(0, max_requests - int(current))


# Rate limit configurations by action type
RATE_LIMITS = {
    # Authentication
    "login": {"max_requests": 5, "window_seconds": 60},  # 5 attempts per minute
    "login_failed": {"max_requests": 10, "window_seconds": 900},  # 10 failed attempts per 15 min
    "password_change": {"max_requests": 3, "window_seconds": 300},  # 3 per 5 min
    "token_refresh": {"max_requests": 30, "window_seconds": 60},  # 30 per minute (allow fast refresh)

    # Session Management
    "session_revoke": {"max_requests": 10, "window_seconds": 60},  # 10 per minute
    "session_list": {"max_requests": 30, "window_seconds": 60},  # 30 per minute

    # Data Export (expensive operations)
    "export_json": {"max_requests": 10, "window_seconds": 60},  # 10 per minute
    "export_csv": {"max_requests": 10, "window_seconds": 60},  # 10 per minute
    "export_bulk": {"max_requests": 3, "window_seconds": 300},  # 3 per 5 min

    # Crawler Operations (resource intensive)
    "crawler_start": {"max_requests": 5, "window_seconds": 60},  # 5 per minute
    "crawler_stop": {"max_requests": 10, "window_seconds": 60},  # 10 per minute

    # Admin Operations
    "user_create": {"max_requests": 10, "window_seconds": 60},  # 10 per minute
    "user_update": {"max_requests": 20, "window_seconds": 60},  # 20 per minute
    "user_delete": {"max_requests": 5, "window_seconds": 60},  # 5 per minute

    # API General (fallback)
    "api_general": {"max_requests": 100, "window_seconds": 60},  # 100 per minute
    "api_read": {"max_requests": 200, "window_seconds": 60},  # 200 per minute (reads are cheaper)
    "api_write": {"max_requests": 50, "window_seconds": 60},  # 50 per minute

    # Webhook Testing
    "webhook_test": {"max_requests": 5, "window_seconds": 60},  # 5 per minute (SSRF concern)
}


# Global rate limiter instances
_rate_limiter: Optional[RateLimiter] = None
_fallback_limiter: Optional[InMemoryRateLimiter] = None


def get_rate_limiter() -> Optional[RateLimiter]:
    """Get the global rate limiter instance."""
    return _rate_limiter


def get_fallback_limiter() -> InMemoryRateLimiter:
    """Get or create the fallback in-memory rate limiter."""
    global _fallback_limiter
    if _fallback_limiter is None:
        _fallback_limiter = InMemoryRateLimiter()
    return _fallback_limiter


def set_rate_limiter(limiter: RateLimiter) -> None:
    """Set the global rate limiter instance."""
    global _rate_limiter
    _rate_limiter = limiter


async def check_rate_limit(
    request: Request,
    action: str,
    identifier: Optional[str] = None,
) -> bool:
    """
    Convenience function to check rate limit.

    Uses Redis-based limiter when available, falls back to in-memory limiter.

    Args:
        request: FastAPI request object
        action: Action type (must be in RATE_LIMITS)
        identifier: Optional custom identifier (defaults to client IP)
    """
    if action not in RATE_LIMITS:
        return True

    config = RATE_LIMITS[action]
    client_id = identifier or (request.client.host if request.client else "unknown")

    limiter = get_rate_limiter()

    if limiter is not None:
        # Use Redis-based rate limiter
        return await limiter.check(
            key_prefix=action,
            identifier=client_id,
            max_requests=config["max_requests"],
            window_seconds=config["window_seconds"],
        )
    else:
        # Fallback to in-memory rate limiter (security: don't allow unlimited requests)
        fallback = get_fallback_limiter()
        return fallback.check(
            key_prefix=action,
            identifier=client_id,
            max_requests=config["max_requests"],
            window_seconds=config["window_seconds"],
        )
