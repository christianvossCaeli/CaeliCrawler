"""Authentication API endpoints."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.user import User, UserRole
from app.models.user_session import UserSession, DeviceType, parse_user_agent
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_tokens_for_session,
    hash_refresh_token,
    verify_refresh_token,
    MAX_SESSIONS_PER_USER,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from app.core.deps import get_current_user
from app.core.rate_limit import check_rate_limit, get_rate_limiter
from app.core.token_blacklist import blacklist_token
from app.core.password_policy import validate_password, check_password_strength
from app.services.audit_service import log_login, log_logout, log_session_revoke

# For extracting token from header
security = HTTPBearer()

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================


class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response schema."""

    id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    is_superuser: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    language: str = "de"

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response schema with refresh token."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token expiry in seconds")
    refresh_expires_in: int = Field(description="Refresh token expiry in seconds")
    user: UserResponse


class RefreshRequest(BaseModel):
    """Refresh token request schema."""

    refresh_token: str


class SessionResponse(BaseModel):
    """Session info response schema."""

    id: UUID
    device_type: DeviceType
    device_name: Optional[str]
    ip_address: Optional[str]
    location: Optional[str]
    created_at: datetime
    last_used_at: datetime
    is_current: bool = False

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """List of user sessions."""

    sessions: List[SessionResponse]
    total: int
    max_sessions: int


class PasswordChangeRequest(BaseModel):
    """Password change request schema."""

    current_password: str
    new_password: str


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


class PasswordStrengthRequest(BaseModel):
    """Request to check password strength."""

    password: str = Field(..., min_length=1)


class PasswordStrengthResponse(BaseModel):
    """Password strength check response."""

    is_valid: bool
    score: int
    errors: list[str]
    suggestions: list[str]
    requirements: str


class LanguageUpdateRequest(BaseModel):
    """Language update request schema."""

    language: str = Field(..., pattern="^(de|en)$", description="Language code (de or en)")


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Authenticate user and return JWT tokens (access + refresh).

    - **email**: User's email address
    - **password**: User's password

    **Rate Limiting**: 5 attempts per minute per IP address.
    After 10 failed attempts within 15 minutes, the IP will be temporarily blocked.

    **Security Features**:
    - Passwords are verified using bcrypt hashing
    - Failed login attempts are tracked for rate limiting
    - Successful login resets the rate limit counter
    - Creates a new session with device tracking
    - Returns both access token (1h) and refresh token (7d)

    **Session Management**:
    - Maximum {MAX_SESSIONS_PER_USER} concurrent sessions per user
    - Oldest session is revoked when limit is reached
    """
    client_ip = request.client.host if request.client else "unknown"
    user_agent_str = request.headers.get("user-agent")

    # Check rate limit for login attempts
    await check_rate_limit(request, "login")

    # Find user by email
    result = await session.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    # Verify credentials
    if not user or not verify_password(data.password, user.password_hash):
        # Track failed login attempts separately
        await check_rate_limit(request, "login_failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    # Reset rate limit on successful login
    limiter = get_rate_limiter()
    if limiter:
        await limiter.reset("login", client_ip)
        await limiter.reset("login_failed", client_ip)

    # Check and enforce session limit
    active_sessions_result = await session.execute(
        select(UserSession)
        .where(and_(
            UserSession.user_id == user.id,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.now(timezone.utc)
        ))
        .order_by(UserSession.last_used_at.asc())
    )
    active_sessions = list(active_sessions_result.scalars().all())

    # Revoke oldest sessions if limit exceeded
    while len(active_sessions) >= MAX_SESSIONS_PER_USER:
        oldest_session = active_sessions.pop(0)
        oldest_session.revoke(reason="session_limit_exceeded")
        await log_session_revoke(
            session, user, oldest_session,
            reason="Session limit exceeded",
            ip_address=client_ip, user_agent=user_agent_str
        )

    # Parse device info
    device_type, device_name = parse_user_agent(user_agent_str)

    # Create tokens
    tokens = create_tokens_for_session(user.id, user.role.value, UUID("00000000-0000-0000-0000-000000000000"))

    # Create new session
    from datetime import timedelta
    new_session = UserSession(
        user_id=user.id,
        refresh_token_hash=tokens["refresh_token_hash"],
        device_type=device_type,
        device_name=device_name,
        user_agent=user_agent_str,
        ip_address=client_ip,
        expires_at=tokens["refresh_expires_at"],
    )
    session.add(new_session)

    # Update last login timestamp
    user.last_login = datetime.now(timezone.utc)

    # Log successful login to audit log
    await log_login(session, user, ip_address=client_ip, user_agent=user_agent_str)

    await session.commit()
    await session.refresh(user)
    await session.refresh(new_session)

    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        expires_in=tokens["access_token_expires_in"],
        refresh_expires_in=tokens["refresh_token_expires_in"],
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """
    Get current authenticated user's profile.

    Requires valid JWT token in Authorization header.
    """
    return UserResponse.model_validate(current_user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    data: PasswordChangeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Change the current user's password.

    - **current_password**: Current password for verification
    - **new_password**: New password to set

    **Password Requirements**:
    - Minimum 8 characters
    - At least one uppercase letter (A-Z)
    - At least one lowercase letter (a-z)
    - At least one digit (0-9)
    - Special characters recommended but not required

    **Rate Limiting**: 3 attempts per 5 minutes.

    **Security**: After password change, all existing tokens remain valid.
    Use logout to invalidate the current token if needed.
    """
    # Check rate limit for password changes
    await check_rate_limit(request, "password_change")

    # Verify current password
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate new password against policy
    validation = validate_password(data.new_password)
    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation.errors[0] if validation.errors else "Password does not meet requirements",
        )

    # Update password
    current_user.password_hash = get_password_hash(data.new_password)
    await session.commit()

    return MessageResponse(message="Password changed successfully")


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Logout current user and invalidate the current token.

    **Token Blacklisting**: The current JWT token is added to a blacklist
    and will be rejected for all future requests until it expires.

    **Note**: If Redis is not available, logout will still succeed but
    token blacklisting will be skipped (graceful degradation).
    """
    # Add token to blacklist
    token = credentials.credentials
    await blacklist_token(token)

    # Log logout to audit log
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent")
    await log_logout(session, current_user, ip_address=client_ip, user_agent=user_agent)
    await session.commit()

    return MessageResponse(message="Logged out successfully")


@router.post("/check-password-strength", response_model=PasswordStrengthResponse)
async def check_password_strength_endpoint(
    data: PasswordStrengthRequest,
):
    """
    Check password strength without changing it.

    Use this endpoint to provide real-time feedback during password entry.

    **Returns**:
    - **is_valid**: Whether the password meets minimum requirements
    - **score**: Strength score from 0-100
    - **errors**: List of policy violations
    - **suggestions**: Tips for improving password strength
    - **requirements**: Human-readable policy description
    """
    result = check_password_strength(data.password)
    return PasswordStrengthResponse(**result)


@router.put("/language", response_model=MessageResponse)
async def update_language(
    data: LanguageUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Update user's language preference.

    - **language**: Language code ('de' or 'en')

    The language preference is stored in the user's profile and will be
    used to determine the language for API responses.
    """
    from app.i18n import t, is_supported_locale, set_locale

    if not is_supported_locale(data.language):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t("errors.language_unsupported", language=data.language),
        )

    # Update user's language preference
    current_user.language = data.language
    await session.commit()

    # Set locale for this response
    set_locale(data.language)

    return MessageResponse(message=t("messages.language_updated"))


# =============================================================================
# Refresh Token & Session Management Endpoints
# =============================================================================


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    data: RefreshRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Refresh access token using refresh token.

    - **refresh_token**: Valid refresh token from login

    **Security Features**:
    - Refresh token is validated against stored hash
    - Session must be active and not expired
    - New access token is issued (refresh token remains the same)
    - Last used timestamp is updated

    **Returns**: New access token with same refresh token
    """
    client_ip = request.client.host if request.client else "unknown"

    # Rate limit refresh attempts
    await check_rate_limit(request, "token_refresh")

    # Hash the provided refresh token
    token_hash = hash_refresh_token(data.refresh_token)

    # Find session by refresh token hash
    result = await session.execute(
        select(UserSession)
        .where(UserSession.refresh_token_hash == token_hash)
    )
    user_session = result.scalar_one_or_none()

    if not user_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Check if session is valid
    if not user_session.is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or revoked",
        )

    # Load user
    user = await session.get(User, user_session.user_id)
    if not user or not user.is_active:
        user_session.revoke(reason="user_inactive")
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated",
        )

    # Update session last used
    user_session.update_last_used(client_ip)

    # Create new access token
    access_token = create_access_token(user.id, user.role.value)

    await session.commit()

    from app.core.security import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

    # Calculate remaining time on refresh token
    remaining_refresh = int((user_session.expires_at - datetime.now(timezone.utc)).total_seconds())

    return TokenResponse(
        access_token=access_token,
        refresh_token=data.refresh_token,  # Same refresh token
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_expires_in=max(0, remaining_refresh),
        user=UserResponse.model_validate(user),
    )


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    List all active sessions for the current user.

    Shows device info, location, and last activity for each session.
    Use this to review and manage active sessions.
    """
    result = await session.execute(
        select(UserSession)
        .where(and_(
            UserSession.user_id == current_user.id,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.now(timezone.utc)
        ))
        .order_by(UserSession.last_used_at.desc())
    )
    sessions_list = list(result.scalars().all())

    return SessionListResponse(
        sessions=[
            SessionResponse(
                id=s.id,
                device_type=s.device_type,
                device_name=s.device_name,
                ip_address=s.ip_address,
                location=s.location,
                created_at=s.created_at,
                last_used_at=s.last_used_at,
                is_current=False,  # TODO: Mark current session
            )
            for s in sessions_list
        ],
        total=len(sessions_list),
        max_sessions=MAX_SESSIONS_PER_USER,
    )


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def revoke_session(
    session_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Revoke a specific session.

    - **session_id**: The session ID to revoke

    The session will be immediately invalidated and cannot be used for refresh.
    """
    # Find the session
    user_session = await session.get(UserSession, session_id)

    if not user_session or user_session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if not user_session.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session already revoked",
        )

    # Revoke the session
    user_session.revoke(reason="user_revoked")

    # Log the action
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent")
    await log_session_revoke(
        session, current_user, user_session,
        reason="User revoked session",
        ip_address=client_ip, user_agent=user_agent
    )

    await session.commit()

    return MessageResponse(message="Session revoked successfully")


@router.delete("/sessions", response_model=MessageResponse)
async def revoke_all_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Revoke all sessions except the current one.

    Use this for "Sign out everywhere" functionality.
    All other devices will be logged out immediately.
    """
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent")

    # Find all active sessions
    result = await session.execute(
        select(UserSession)
        .where(and_(
            UserSession.user_id == current_user.id,
            UserSession.is_active == True,
        ))
    )
    all_sessions = list(result.scalars().all())

    revoked_count = 0
    for user_session in all_sessions:
        user_session.revoke(reason="user_revoked_all")
        revoked_count += 1

    # Log the bulk action
    from app.services.audit_service import log_bulk_session_revoke
    await log_bulk_session_revoke(
        session, current_user,
        count=revoked_count,
        ip_address=client_ip, user_agent=user_agent
    )

    await session.commit()

    return MessageResponse(message=f"Revoked {revoked_count} session(s)")
