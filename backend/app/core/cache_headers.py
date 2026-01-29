"""
HTTP Cache Headers utilities for FastAPI.

Provides functions to add Cache-Control and ETag headers to responses
for improved client-side caching and reduced bandwidth.

Cache Strategy:
- Static config endpoints: 5 minute cache (public)
- Entity lists: 60 second cache with must-revalidate
- Single entity details: 60 second cache
- Dashboard stats: 30 second cache

Usage:
    from app.core.cache_headers import add_cache_headers, generate_etag

    @router.get("/entities")
    async def list_entities(response: Response):
        data = await get_entities()
        add_cache_headers(response, max_age=60, etag=generate_etag(data))
        return data
"""

import hashlib
import json
from typing import Any

from fastapi import Response


def generate_etag(data: Any) -> str:
    """
    Generate an ETag from response data.

    Uses MD5 hash of JSON-serialized data (truncated to 16 chars).
    MD5 is fine here since we only need a change detection hash,
    not cryptographic security.

    Args:
        data: The response data to hash

    Returns:
        ETag string (quoted as per HTTP spec)
    """
    try:
        serialized = json.dumps(data, sort_keys=True, default=str)
        # MD5 is fine for ETags - only used for change detection, not security
        hash_digest = hashlib.md5(serialized.encode(), usedforsecurity=False).hexdigest()[:16]
        return f'"{hash_digest}"'
    except (TypeError, ValueError):
        # Fallback for non-serializable data
        return f'"{hash(str(data)) & 0xFFFFFFFF:08x}"'


def add_cache_headers(
    response: Response,
    max_age: int = 60,
    *,
    private: bool = False,
    must_revalidate: bool = True,
    etag: str | None = None,
    vary: list[str] | None = None,
) -> None:
    """
    Add HTTP cache headers to a FastAPI response.

    Args:
        response: FastAPI Response object
        max_age: Cache max-age in seconds (default: 60)
        private: If True, cache is private (user-specific data)
        must_revalidate: If True, client must revalidate after max-age
        etag: Optional ETag value for the response
        vary: Optional list of headers that affect response content
    """
    # Build Cache-Control directive
    directives = []

    if private:
        directives.append("private")
    else:
        directives.append("public")

    directives.append(f"max-age={max_age}")

    if must_revalidate:
        directives.append("must-revalidate")

    response.headers["Cache-Control"] = ", ".join(directives)

    # Add ETag if provided
    if etag:
        response.headers["ETag"] = etag

    # Add Vary header for content negotiation
    vary_headers = vary or ["Accept-Language", "Accept-Encoding"]
    response.headers["Vary"] = ", ".join(vary_headers)


def add_no_cache_headers(response: Response) -> None:
    """
    Add headers to prevent caching.

    Use for sensitive or highly dynamic endpoints.
    """
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"


# Convenience functions for common cache profiles


def cache_for_config(response: Response, data: Any) -> None:
    """
    Cache configuration endpoints (5 minutes, public).

    Use for: /config/features, /api/config, etc.
    """
    add_cache_headers(response, max_age=300, private=False, etag=generate_etag(data))


def cache_for_list(response: Response, data: Any) -> None:
    """
    Cache list endpoints (60 seconds, revalidate).

    Use for: /entities, /facet-types, etc.
    """
    add_cache_headers(
        response,
        max_age=60,
        must_revalidate=True,
        etag=generate_etag(data),
    )


def cache_for_detail(response: Response, data: Any) -> None:
    """
    Cache detail endpoints (60 seconds, private).

    Use for: /entities/{id}, /facets/{id}, etc.
    """
    add_cache_headers(
        response,
        max_age=60,
        private=True,
        must_revalidate=True,
        etag=generate_etag(data),
    )


def cache_for_dashboard(response: Response, data: Any) -> None:
    """
    Cache dashboard/stats endpoints (30 seconds).

    Use for: /dashboard/stats, /dashboard/charts, etc.
    """
    add_cache_headers(
        response,
        max_age=30,
        must_revalidate=True,
        etag=generate_etag(data),
    )
