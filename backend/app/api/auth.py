"""Authentication API endpoints."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.user import User, UserRole
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.deps import get_current_user
from app.core.rate_limit import check_rate_limit, get_rate_limiter
from app.core.token_blacklist import blacklist_token
from app.core.password_policy import validate_password, check_password_strength
from app.services.audit_service import log_login, log_logout

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

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


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
    Authenticate user and return JWT token.

    - **email**: User's email address
    - **password**: User's password

    **Rate Limiting**: 5 attempts per minute per IP address.
    After 10 failed attempts within 15 minutes, the IP will be temporarily blocked.

    **Security Features**:
    - Passwords are verified using bcrypt hashing
    - Failed login attempts are tracked for rate limiting
    - Successful login resets the rate limit counter
    """
    client_ip = request.client.host if request.client else "unknown"

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

    # Update last login timestamp
    user.last_login = datetime.now(timezone.utc)

    # Log successful login to audit log
    user_agent = request.headers.get("user-agent")
    await log_login(session, user, ip_address=client_ip, user_agent=user_agent)

    await session.commit()
    await session.refresh(user)

    # Create access token
    token = create_access_token(user.id, user.role.value)

    return TokenResponse(
        access_token=token,
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
