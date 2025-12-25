"""Authentication API endpoints."""

import structlog
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

logger = structlog.get_logger(__name__)
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
    create_sse_ticket,
    MAX_SESSIONS_PER_USER,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SSE_TICKET_EXPIRE_SECONDS,
)
from app.core.deps import get_current_user, get_current_session_id
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
    email_verified: bool = False
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


class EmailVerificationRequest(BaseModel):
    """Request to send verification email."""

    pass  # Uses authenticated user's email


class EmailVerificationConfirmRequest(BaseModel):
    """Confirm email with verification token."""

    token: str = Field(..., min_length=32, max_length=64)


class EmailVerificationStatusResponse(BaseModel):
    """Email verification status response."""

    email: str
    email_verified: bool
    verification_pending: bool = False
    message: str


class SSETicketResponse(BaseModel):
    """SSE ticket response for secure EventSource connections."""

    ticket: str
    expires_in: int = Field(description="Ticket expiry in seconds")


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
            UserSession.is_active.is_(True),
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


@router.post("/sse-ticket", response_model=SSETicketResponse)
async def get_sse_ticket(
    current_user: User = Depends(get_current_user),
):
    """
    Get a short-lived SSE ticket for secure EventSource connections.

    This endpoint should be called immediately before establishing an
    EventSource connection. The ticket is valid for only 30 seconds and
    can only be used for SSE authentication.

    **Security Benefits**:
    - The main access token is never exposed in URLs or server logs
    - Tickets are single-use and expire quickly
    - Tickets cannot be used for regular API calls

    **Usage**:
    1. Call this endpoint with your access token in the Authorization header
    2. Use the returned ticket in the SSE URL: `/api/.../events?ticket={ticket}`
    3. Establish the EventSource connection within 30 seconds

    ```javascript
    // Example usage
    const response = await fetch('/api/auth/sse-ticket', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${accessToken}` }
    });
    const { ticket } = await response.json();
    const eventSource = new EventSource(`/api/admin/crawler/events?ticket=${ticket}`);
    ```
    """
    ticket = create_sse_ticket(current_user.id, current_user.role.value)
    return SSETicketResponse(
        ticket=ticket,
        expires_in=SSE_TICKET_EXPIRE_SECONDS,
    )


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

    # Create new access token with session reference
    access_token = create_access_token(user.id, user.role.value, user_session.id)

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
    current_session_id: Optional[UUID] = Depends(get_current_session_id),
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
            UserSession.is_active.is_(True),
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
                is_current=(current_session_id is not None and s.id == current_session_id),
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
            UserSession.is_active.is_(True),
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


# =============================================================================
# Email Verification Endpoints
# =============================================================================


async def _send_verification_email(user: User, token: str) -> bool:
    """Send verification email to user.

    Args:
        user: The user to send verification to
        token: The verification token

    Returns:
        True if email was sent successfully
    """
    import aiosmtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from app.config import settings

    # Build verification URL
    frontend_url = getattr(settings, "frontend_url", "https://app.caeli-wind.de")
    verification_url = f"{frontend_url}/verify-email?token={token}"

    # Create message
    message = MIMEMultipart("alternative")
    message["Subject"] = "E-Mail-Adresse bestätigen - CaeliCrawler"
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = user.email

    # Plain text
    text_content = f"""Hallo {user.full_name},

bitte bestätigen Sie Ihre E-Mail-Adresse, indem Sie den folgenden Link aufrufen:

{verification_url}

Dieser Link ist 24 Stunden gültig.

Falls Sie diese E-Mail nicht angefordert haben, können Sie sie ignorieren.

Mit freundlichen Grüßen,
Das CaeliCrawler-Team
"""

    # HTML
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #113634; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #e0e0e0; border-top: none; }}
        .button {{ display: inline-block; background: #113634; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
        .footer {{ background: #f0f0f0; padding: 15px 20px; border-radius: 0 0 8px 8px; font-size: 12px; color: #666; border: 1px solid #e0e0e0; border-top: none; }}
    </style>
</head>
<body>
    <div class="header"><h1 style="margin: 0; font-size: 20px;">E-Mail bestätigen</h1></div>
    <div class="content">
        <p>Hallo {user.full_name},</p>
        <p>bitte bestätigen Sie Ihre E-Mail-Adresse, indem Sie auf den folgenden Button klicken:</p>
        <a href="{verification_url}" class="button">E-Mail bestätigen</a>
        <p style="font-size: 13px; color: #666; margin-top: 20px;">
            Oder kopieren Sie diesen Link in Ihren Browser:<br>
            <code>{verification_url}</code>
        </p>
        <p style="font-size: 13px; color: #666;">Dieser Link ist 24 Stunden gültig.</p>
    </div>
    <div class="footer">Falls Sie diese E-Mail nicht angefordert haben, können Sie sie ignorieren.</div>
</body>
</html>
"""

    message.attach(MIMEText(text_content, "plain", "utf-8"))
    message.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username or None,
            password=settings.smtp_password or None,
            use_tls=settings.smtp_use_tls,
            start_tls=settings.smtp_use_tls and not settings.smtp_use_ssl,
            timeout=settings.smtp_timeout,
        )
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to send verification email: {e}")
        return False


@router.get("/email-verification/status", response_model=EmailVerificationStatusResponse)
async def get_email_verification_status(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user's email verification status.

    Returns whether the user's email is verified and if a verification is pending.
    """
    verification_pending = (
        current_user.email_verification_token is not None
        and current_user.email_verification_sent_at is not None
    )

    return EmailVerificationStatusResponse(
        email=current_user.email,
        email_verified=current_user.email_verified,
        verification_pending=verification_pending,
        message=(
            "E-Mail ist bestätigt"
            if current_user.email_verified
            else "E-Mail noch nicht bestätigt"
        ),
    )


@router.post("/email-verification/request", response_model=MessageResponse)
async def request_email_verification(
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Request a verification email to be sent.

    Rate limited to 1 request per 5 minutes per user.
    """
    import secrets
    from datetime import timedelta

    # Check if already verified
    if current_user.email_verified:
        return MessageResponse(message="E-Mail ist bereits bestätigt")

    # Rate limiting: max 1 request per 5 minutes
    if current_user.email_verification_sent_at:
        time_since_last = datetime.now(timezone.utc) - current_user.email_verification_sent_at
        if time_since_last < timedelta(minutes=5):
            remaining = 5 - int(time_since_last.total_seconds() / 60)
            raise HTTPException(
                status_code=429,
                detail=f"Bitte warten Sie {remaining} Minute(n) bevor Sie eine neue E-Mail anfordern",
            )

    # Generate secure token
    token = secrets.token_urlsafe(32)

    # Update user
    current_user.email_verification_token = token
    current_user.email_verification_sent_at = datetime.now(timezone.utc)

    # Send email
    email_sent = await _send_verification_email(current_user, token)

    if not email_sent:
        # Reset token if email failed
        current_user.email_verification_token = None
        current_user.email_verification_sent_at = None
        await session.commit()
        raise HTTPException(
            status_code=500,
            detail="E-Mail konnte nicht gesendet werden. Bitte versuchen Sie es später erneut.",
        )

    await session.commit()

    return MessageResponse(
        message=f"Bestätigungs-E-Mail wurde an {current_user.email} gesendet"
    )


@router.post("/email-verification/confirm", response_model=MessageResponse)
async def confirm_email_verification(
    data: EmailVerificationConfirmRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Confirm email verification with token.

    Token is valid for 24 hours after being sent.
    """
    from datetime import timedelta

    # Apply rate limiting
    await check_rate_limit(request, "email_verification")

    # Find user by token
    result = await session.execute(
        select(User).where(User.email_verification_token == data.token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Ungültiger oder abgelaufener Bestätigungslink",
        )

    # Check token expiry (24 hours)
    if user.email_verification_sent_at:
        token_age = datetime.now(timezone.utc) - user.email_verification_sent_at
        if token_age > timedelta(hours=24):
            # Clear expired token
            user.email_verification_token = None
            user.email_verification_sent_at = None
            await session.commit()
            raise HTTPException(
                status_code=400,
                detail="Bestätigungslink ist abgelaufen. Bitte fordern Sie einen neuen an.",
            )

    # Mark as verified
    user.email_verified = True
    user.email_verification_token = None
    user.email_verification_sent_at = None

    await session.commit()

    return MessageResponse(message="E-Mail-Adresse erfolgreich bestätigt")
