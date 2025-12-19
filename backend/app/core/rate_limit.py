"""
Rate Limiting for API endpoints.

Uses Redis to track request counts per IP/user.
"""

import time
from typing import Optional

from fastapi import HTTPException, Request, status
from redis.asyncio import Redis

from app.config import settings


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


# Rate limit configurations
RATE_LIMITS = {
    "login": {"max_requests": 5, "window_seconds": 60},  # 5 attempts per minute
    "login_failed": {"max_requests": 10, "window_seconds": 900},  # 10 failed attempts per 15 min
    "password_change": {"max_requests": 3, "window_seconds": 300},  # 3 per 5 min
    "api_general": {"max_requests": 100, "window_seconds": 60},  # 100 per minute
}


# Global rate limiter instance (initialized in main.py)
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> Optional[RateLimiter]:
    """Get the global rate limiter instance."""
    return _rate_limiter


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

    Args:
        request: FastAPI request object
        action: Action type (must be in RATE_LIMITS)
        identifier: Optional custom identifier (defaults to client IP)
    """
    limiter = get_rate_limiter()

    if limiter is None:
        # Rate limiting not configured, allow request
        return True

    if action not in RATE_LIMITS:
        return True

    config = RATE_LIMITS[action]
    client_id = identifier or (request.client.host if request.client else "unknown")

    return await limiter.check(
        key_prefix=action,
        identifier=client_id,
        max_requests=config["max_requests"],
        window_seconds=config["window_seconds"],
    )
