"""Security utilities for password hashing and JWT tokens."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from app.config import settings

# JWT settings
ALGORITHM = "HS256"
# Security: Reduced from 24 hours to 1 hour for access tokens
# This limits the window of opportunity if a token is compromised
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour (was 24 hours)
REFRESH_TOKEN_EXPIRE_DAYS = 7  # 7 days for refresh tokens

# Session settings
MAX_SESSIONS_PER_USER = 5  # Maximum concurrent sessions per user


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash using bcrypt."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """Generate password hash using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(
    user_id: UUID,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create JWT access token.

    Args:
        user_id: The user's UUID
        role: The user's role
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate JWT token.

    Args:
        token: The JWT token string

    Returns:
        Decoded payload dict or None if invalid
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# =============================================================================
# Refresh Token Functions
# =============================================================================


def generate_refresh_token() -> str:
    """
    Generate a secure random refresh token.

    Returns:
        A 64-character URL-safe random string
    """
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """
    Hash a refresh token for secure storage.

    Uses SHA-256 for fast verification while maintaining security.

    Args:
        token: The raw refresh token

    Returns:
        Hexadecimal hash of the token
    """
    return hashlib.sha256(token.encode()).hexdigest()


def verify_refresh_token(token: str, token_hash: str) -> bool:
    """
    Verify a refresh token against its stored hash.

    Args:
        token: The raw refresh token from the client
        token_hash: The stored hash to compare against

    Returns:
        True if token matches the hash
    """
    return hash_refresh_token(token) == token_hash


def create_refresh_token_response(
    user_id: UUID,
    role: str,
    session_id: UUID,
) -> Tuple[str, str, datetime]:
    """
    Create a refresh token with associated metadata.

    Args:
        user_id: The user's UUID
        role: The user's role
        session_id: The session UUID for tracking

    Returns:
        Tuple of (raw_token, token_hash, expires_at)
    """
    raw_token = generate_refresh_token()
    token_hash = hash_refresh_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    return raw_token, token_hash, expires_at


def create_tokens_for_session(
    user_id: UUID,
    role: str,
    session_id: UUID,
) -> dict:
    """
    Create both access and refresh tokens for a new session.

    Args:
        user_id: The user's UUID
        role: The user's role
        session_id: The session UUID

    Returns:
        Dict with access_token, refresh_token, and expiry info
    """
    # Create access token with session reference
    access_token = create_access_token(user_id, role)

    # Create refresh token
    refresh_token, token_hash, refresh_expires_at = create_refresh_token_response(
        user_id, role, session_id
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "refresh_token_hash": token_hash,
        "refresh_expires_at": refresh_expires_at,
        "access_token_expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
        "refresh_token_expires_in": REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # seconds
    }
