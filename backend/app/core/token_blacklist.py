"""
Token Blacklist Service.

Uses Redis to store invalidated JWT tokens until they expire.
This enables proper logout functionality with stateless JWTs.
"""

from datetime import UTC, datetime

from redis.asyncio import Redis

from app.core.security import ACCESS_TOKEN_EXPIRE_MINUTES, decode_access_token


class TokenBlacklist:
    """
    Redis-based token blacklist.

    When a user logs out, their token is added to the blacklist.
    Tokens are automatically removed when they would have expired anyway.
    """

    KEY_PREFIX = "token_blacklist:"

    def __init__(self, redis: Redis):
        self.redis = redis

    async def add(self, token: str) -> bool:
        """
        Add a token to the blacklist.

        The token will be stored until its natural expiration time.

        Args:
            token: The JWT token to blacklist

        Returns:
            True if added successfully
        """
        # Decode token to get expiration time
        payload = decode_access_token(token)

        if payload is None:
            # Invalid token, nothing to blacklist
            return False

        # Get expiration from token
        exp = payload.get("exp")
        if exp is None:
            # No expiration, use default
            ttl = ACCESS_TOKEN_EXPIRE_MINUTES * 60
        else:
            # Calculate remaining TTL
            exp_time = datetime.fromtimestamp(exp, tz=UTC)
            now = datetime.now(UTC)
            ttl = int((exp_time - now).total_seconds())

            if ttl <= 0:
                # Token already expired, no need to blacklist
                return False

        # Store token in blacklist
        # We use the token's "jti" (JWT ID) if available, otherwise hash the token
        token_id = payload.get("jti") or self._hash_token(token)
        key = f"{self.KEY_PREFIX}{token_id}"

        await self.redis.setex(key, ttl, "1")
        return True

    async def is_blacklisted(self, token: str) -> bool:
        """
        Check if a token is blacklisted.

        Args:
            token: The JWT token to check

        Returns:
            True if token is blacklisted
        """
        payload = decode_access_token(token)

        if payload is None:
            # Invalid token
            return False

        token_id = payload.get("jti") or self._hash_token(token)
        key = f"{self.KEY_PREFIX}{token_id}"

        result = await self.redis.exists(key)
        return result > 0

    async def remove(self, token: str) -> bool:
        """
        Remove a token from the blacklist (e.g., for testing).

        Args:
            token: The JWT token to remove

        Returns:
            True if removed
        """
        payload = decode_access_token(token)

        if payload is None:
            return False

        token_id = payload.get("jti") or self._hash_token(token)
        key = f"{self.KEY_PREFIX}{token_id}"

        result = await self.redis.delete(key)
        return result > 0

    def _hash_token(self, token: str) -> str:
        """Create a short hash of the token for storage."""
        import hashlib

        return hashlib.sha256(token.encode()).hexdigest()[:32]


# Global blacklist instance
_token_blacklist: TokenBlacklist | None = None


def get_token_blacklist() -> TokenBlacklist | None:
    """Get the global token blacklist instance."""
    return _token_blacklist


def set_token_blacklist(blacklist: TokenBlacklist) -> None:
    """Set the global token blacklist instance."""
    global _token_blacklist
    _token_blacklist = blacklist


async def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token is blacklisted.

    Returns False if blacklist is not configured (allows graceful degradation).
    """
    blacklist = get_token_blacklist()

    if blacklist is None:
        return False

    return await blacklist.is_blacklisted(token)


async def blacklist_token(token: str) -> bool:
    """
    Add a token to the blacklist.

    Returns False if blacklist is not configured.
    """
    blacklist = get_token_blacklist()

    if blacklist is None:
        return False

    return await blacklist.add(token)
