"""
Rate Limiting Module for CaeliCrawler

Provides configurable rate limiting for API endpoints using Redis as a backend
for distributed rate limiting across multiple instances.

Features:
- Sliding window rate limiting
- IP-based and user-based limiting
- Configurable limits per endpoint/group
- Redis-backed for scalability
- Graceful fallback when Redis unavailable
"""

import time
from collections.abc import Callable
from functools import wraps

import structlog
from fastapi import HTTPException, Request, status

logger = structlog.get_logger(__name__)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        retry_after: int = 60,
    ):
        self.detail = detail
        self.retry_after = retry_after
        super().__init__(detail)


class RateLimiter:
    """
    Sliding window rate limiter using Redis.

    Usage:
        rate_limiter = RateLimiter(redis_url="redis://localhost:6379/0")

        @app.get("/api/resource")
        @rate_limiter.limit(requests=100, window=60)
        async def get_resource():
            return {"data": "resource"}
    """

    def __init__(
        self,
        redis_url: str | None = None,
        default_requests: int = 100,
        default_window: int = 60,
        enabled: bool = True,
    ):
        """
        Initialize the rate limiter.

        Args:
            redis_url: Redis connection URL
            default_requests: Default max requests per window
            default_window: Default window size in seconds
            enabled: Whether rate limiting is enabled
        """
        self.redis_url = redis_url
        self.default_requests = default_requests
        self.default_window = default_window
        self.enabled = enabled
        self._redis = None
        self._fallback_storage: dict = {}  # In-memory fallback

    async def _get_redis(self):
        """Get Redis client with lazy initialization."""
        if not self.redis_url:
            return None

        if self._redis is None:
            try:
                import redis.asyncio as redis

                self._redis = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                # Test connection
                await self._redis.ping()
            except Exception as e:
                logger.warning("Redis unavailable for rate limiting", error=str(e))
                self._redis = None

        return self._redis

    def _get_client_identifier(self, request: Request, user_id: str | None = None) -> str:
        """
        Get unique identifier for the client.

        Uses user ID if available, otherwise falls back to IP address.
        """
        if user_id:
            return f"user:{user_id}"

        # Get real IP (consider X-Forwarded-For for proxied requests)
        forwarded = request.headers.get("X-Forwarded-For")
        ip = forwarded.split(",")[0].strip() if forwarded else request.client.host if request.client else "unknown"

        return f"ip:{ip}"

    async def _check_rate_limit_redis(
        self,
        key: str,
        max_requests: int,
        window: int,
    ) -> tuple[bool, int, int]:
        """
        Check rate limit using Redis sliding window.

        Returns:
            Tuple of (allowed, remaining, reset_time)
        """
        redis_client = await self._get_redis()
        if not redis_client:
            return True, max_requests, 0

        now = time.time()
        window_start = now - window

        try:
            pipeline = redis_client.pipeline()

            # Remove old entries
            pipeline.zremrangebyscore(key, "-inf", window_start)
            # Count current entries
            pipeline.zcard(key)
            # Add current request
            pipeline.zadd(key, {str(now): now})
            # Set expiry
            pipeline.expire(key, window)

            results = await pipeline.execute()
            current_count = results[1]

            remaining = max(0, max_requests - current_count - 1)
            reset_time = int(now + window)

            if current_count >= max_requests:
                return False, 0, reset_time

            return True, remaining, reset_time

        except Exception as e:
            logger.warning("Rate limit check failed", error=str(e), key=key)
            return True, max_requests, 0

    def _check_rate_limit_memory(
        self,
        key: str,
        max_requests: int,
        window: int,
    ) -> tuple[bool, int, int]:
        """
        Fallback in-memory rate limiting (single instance only).

        Returns:
            Tuple of (allowed, remaining, reset_time)
        """
        now = time.time()
        window_start = now - window

        if key not in self._fallback_storage:
            self._fallback_storage[key] = []

        # Remove old entries
        self._fallback_storage[key] = [ts for ts in self._fallback_storage[key] if ts > window_start]

        current_count = len(self._fallback_storage[key])
        remaining = max(0, max_requests - current_count - 1)
        reset_time = int(now + window)

        if current_count >= max_requests:
            return False, 0, reset_time

        self._fallback_storage[key].append(now)
        return True, remaining, reset_time

    async def check_rate_limit(
        self,
        request: Request,
        endpoint: str,
        max_requests: int,
        window: int,
        user_id: str | None = None,
    ) -> tuple[bool, int, int]:
        """
        Check if request is within rate limit.

        Args:
            request: FastAPI Request object
            endpoint: Endpoint identifier for the limit
            max_requests: Maximum requests allowed in window
            window: Time window in seconds
            user_id: Optional user identifier

        Returns:
            Tuple of (allowed, remaining, reset_time)
        """
        if not self.enabled:
            return True, max_requests, 0

        client_id = self._get_client_identifier(request, user_id)
        key = f"ratelimit:{endpoint}:{client_id}"

        redis_client = await self._get_redis()
        if redis_client:
            return await self._check_rate_limit_redis(key, max_requests, window)
        else:
            return self._check_rate_limit_memory(key, max_requests, window)

    def limit(
        self,
        requests: int | None = None,
        window: int | None = None,
        key_func: Callable[[Request], str] | None = None,
    ):
        """
        Decorator for rate limiting endpoints.

        Args:
            requests: Max requests per window (default: default_requests)
            window: Window size in seconds (default: default_window)
            key_func: Optional custom function to generate rate limit key

        Usage:
            @rate_limiter.limit(requests=10, window=60)
            async def limited_endpoint():
                return {"data": "limited"}
        """
        max_requests = requests or self.default_requests
        window_seconds = window or self.default_window

        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Find Request object in args/kwargs
                request = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

                if not request:
                    request = kwargs.get("request")

                if not request:
                    # Can't rate limit without request, allow through
                    logger.warning("Rate limit decorator couldn't find Request")
                    return await func(*args, **kwargs)

                # Generate key
                endpoint_key = key_func(request) if key_func else f"{request.method}:{request.url.path}"

                # Check rate limit
                allowed, remaining, reset_time = await self.check_rate_limit(
                    request=request,
                    endpoint=endpoint_key,
                    max_requests=max_requests,
                    window=window_seconds,
                )

                if not allowed:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail={
                            "error": "Rate limit exceeded",
                            "retry_after": window_seconds,
                            "limit": max_requests,
                            "window": window_seconds,
                        },
                        headers={
                            "Retry-After": str(window_seconds),
                            "X-RateLimit-Limit": str(max_requests),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(reset_time),
                        },
                    )

                # Execute the function
                response = await func(*args, **kwargs)

                # Add rate limit headers to response if it's a Response object
                if hasattr(response, "headers"):
                    response.headers["X-RateLimit-Limit"] = str(max_requests)
                    response.headers["X-RateLimit-Remaining"] = str(remaining)
                    response.headers["X-RateLimit-Reset"] = str(reset_time)

                return response

            return wrapper

        return decorator


# Pre-configured rate limiters for different use cases
class RateLimitPresets:
    """Pre-configured rate limit settings."""

    # Standard API endpoints
    STANDARD = {"requests": 100, "window": 60}

    # Admin endpoints (more restrictive)
    ADMIN = {"requests": 30, "window": 60}

    # Auth endpoints (very restrictive to prevent brute force)
    AUTH = {"requests": 5, "window": 60}

    # Login attempts
    LOGIN = {"requests": 5, "window": 300}  # 5 attempts per 5 minutes

    # Password reset
    PASSWORD_RESET = {"requests": 3, "window": 3600}  # 3 per hour

    # File upload
    UPLOAD = {"requests": 10, "window": 60}

    # AI/LLM endpoints (expensive operations)
    AI = {"requests": 10, "window": 60}

    # Search endpoints
    SEARCH = {"requests": 30, "window": 60}

    # Export endpoints
    EXPORT = {"requests": 5, "window": 60}

    # Webhook endpoints
    WEBHOOK = {"requests": 100, "window": 60}

    # Crawl operations
    CRAWL = {"requests": 5, "window": 60}


# Global rate limiter instance (configured in app startup)
rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global rate_limiter
    if rate_limiter is None:
        from app.config import settings

        rate_limiter = RateLimiter(
            redis_url=settings.REDIS_URL,
            default_requests=100,
            default_window=60,
            enabled=settings.APP_ENV != "development",
        )
    return rate_limiter


def configure_rate_limiter(
    redis_url: str | None = None,
    enabled: bool = True,
    default_requests: int = 100,
    default_window: int = 60,
):
    """Configure the global rate limiter."""
    global rate_limiter
    rate_limiter = RateLimiter(
        redis_url=redis_url,
        default_requests=default_requests,
        default_window=default_window,
        enabled=enabled,
    )
