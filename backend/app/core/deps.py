"""FastAPI dependencies for authentication and authorization."""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.user import User, UserRole
from app.core.security import decode_access_token
from app.core.token_blacklist import is_token_blacklisted

# HTTP Bearer token security scheme
security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Get current authenticated user from JWT token.

    Validates the token against:
    1. JWT signature and expiration
    2. Token blacklist (for logged out tokens)
    3. User existence and active status

    Raises:
        HTTPException: 401 if token is invalid, expired, or blacklisted
        HTTPException: 403 if user account is deactivated
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if token is blacklisted (logged out)
    if await is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await session.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    session: AsyncSession = Depends(get_session),
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.

    Use this for endpoints that work both with and without authentication.
    """
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, session)
    except HTTPException:
        return None


def require_role(required_roles: list[UserRole]):
    """
    Dependency factory for role-based access control.

    Args:
        required_roles: List of roles that are allowed access

    Returns:
        Dependency function that validates user role
    """

    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        # Superusers bypass role checks
        if current_user.is_superuser:
            return current_user

        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[r.value for r in required_roles]}",
            )
        return current_user

    return role_checker


# Convenience dependencies for common role checks
require_admin = require_role([UserRole.ADMIN])
require_editor = require_role([UserRole.ADMIN, UserRole.EDITOR])
require_viewer = require_role([UserRole.ADMIN, UserRole.EDITOR, UserRole.VIEWER])


async def get_current_session_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Optional[UUID]:
    """
    Get the current session ID from the JWT token.

    Returns:
        Session UUID if present in token, None otherwise
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        return None

    # Extract session ID from token payload
    sid = payload.get("sid")
    if sid:
        try:
            return UUID(sid)
        except ValueError:
            return None
    return None
