"""FastAPI dependencies for authentication and authorization."""

from uuid import UUID

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token, decode_sse_ticket
from app.core.token_blacklist import is_token_blacklisted
from app.database import get_session
from app.models.user import User, UserRole


class HTTPBearer401(HTTPBearer):
    """
    Custom HTTPBearer that returns 401 instead of 403 when credentials are missing.

    This follows REST API best practices:
    - 401 Unauthorized: No credentials or invalid credentials
    - 403 Forbidden: Valid credentials but insufficient permissions
    """

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        try:
            return await super().__call__(request)
        except HTTPException as exc:
            if exc.status_code == 403:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                ) from None
            raise


# HTTP Bearer token security scheme
security = HTTPBearer401()
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
        ) from None

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
    credentials: HTTPAuthorizationCredentials | None = Depends(security_optional),
    session: AsyncSession = Depends(get_session),
) -> User | None:
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


async def get_current_user_from_token(
    token: str,
    session: AsyncSession,
) -> User:
    """
    Validate a token string and return the user.

    Used internally for SSE authentication where tokens come from query params.
    """
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    if await is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    try:
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        ) from None

    user = await session.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


async def get_current_user_from_sse_ticket(
    ticket: str,
    session: AsyncSession,
) -> User:
    """
    Validate an SSE ticket and return the user.

    SSE tickets are short-lived tokens specifically for SSE connections.
    They expire quickly and can only be used for SSE, not regular API calls.

    Args:
        ticket: The SSE ticket string
        session: Database session

    Returns:
        User object

    Raises:
        HTTPException: 401 if ticket is invalid or expired
    """
    payload = decode_sse_ticket(ticket)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired SSE ticket",
        )

    try:
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid ticket payload",
        ) from None

    user = await session.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


async def get_current_user_sse(
    ticket: str | None = Query(default=None, alias="ticket", description="SSE ticket for secure SSE auth"),
    token: str | None = Query(default=None, description="JWT token for SSE auth (deprecated, use ticket)"),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_optional),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Get current user from Bearer header, SSE ticket, or query parameter token.

    SSE (EventSource) cannot send custom headers, so this dependency
    accepts authentication via multiple methods:

    1. Bearer header (preferred for non-SSE)
    2. SSE ticket query param (preferred for SSE - short-lived, secure)
    3. Token query param (deprecated - exposes main token in URLs)

    Security Note:
    The 'ticket' parameter is the recommended approach for SSE. It uses
    short-lived tokens that expire in 30 seconds, minimizing exposure risk.
    """
    # Try Bearer header first (for testing/non-browser clients)
    if credentials:
        return await get_current_user(credentials, session)

    # Try SSE ticket (preferred for browser SSE connections)
    if ticket:
        return await get_current_user_from_sse_ticket(ticket, session)

    # Fallback to query parameter token (deprecated but supported)
    if token:
        return await get_current_user_from_token(token, session)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Use 'ticket' parameter with SSE ticket.",
    )


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


async def require_editor_sse(
    user: User = Depends(get_current_user_sse),
) -> User:
    """
    SSE-compatible editor role check.

    Accepts both Bearer header and query parameter token.
    """
    if user.is_superuser:
        return user
    if user.role not in [UserRole.ADMIN, UserRole.EDITOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return user


async def get_current_session_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UUID | None:
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


async def require_llm_budget(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Dependency that checks if user has available LLM budget.

    Blocks the request with HTTP 429 if the user has exceeded their
    monthly LLM budget limit.

    Returns:
        User object if budget is available

    Raises:
        HTTPException: 429 if user's LLM budget is exhausted
    """
    # Import here to avoid circular imports
    from services.llm_budget_service import LLMBudgetService

    service = LLMBudgetService(session)
    can_use, reason = await service.check_user_can_use_llm(current_user.id)

    if not can_use:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=reason,
            headers={"X-Error-Code": "LLM_BUDGET_EXCEEDED"},
        )

    return current_user
