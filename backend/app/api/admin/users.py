"""Admin API endpoints for user management."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.user import User, UserRole
from app.core.deps import require_admin
from app.core.security import get_password_hash
from app.core.exceptions import NotFoundError, ConflictError
from app.core.password_policy import validate_password, default_policy
from app.core.rate_limit import check_rate_limit

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.VIEWER
    is_active: bool = True
    is_superuser: bool = False


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


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
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Paginated list of users."""

    items: List[UserResponse]
    total: int
    page: int
    per_page: int
    pages: int


class PasswordResetRequest(BaseModel):
    """Admin password reset request."""

    new_password: str


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """
    List all users with pagination and filtering.

    Admin only.
    """
    # Build query
    query = select(User)

    # Apply filters
    if role:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (User.email.ilike(search_filter)) | (User.full_name.ilike(search_filter))
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    # Apply pagination
    query = query.order_by(User.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    # Execute query
    result = await session.execute(query)
    users = list(result.scalars().all())

    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    data: UserCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """
    Create a new user.

    Admin only.

    **Password Requirements**:
    - Minimum 8 characters
    - At least one uppercase letter (A-Z)
    - At least one lowercase letter (a-z)
    - At least one digit (0-9)
    """
    # Rate limit: 10 user creations per minute
    await check_rate_limit(request, "user_create", identifier=str(current_user.id))

    # Check for duplicate email
    existing = await session.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise ConflictError(
            "User already exists",
            f"A user with email {data.email} already exists",
        )

    # Validate password against full policy
    validation = validate_password(data.password)
    if not validation.is_valid:
        raise ConflictError(
            "Invalid password",
            "; ".join(validation.errors) if validation.errors else default_policy.get_requirements_text(),
        )

    # Create user
    user = User(
        email=data.email,
        password_hash=get_password_hash(data.password),
        full_name=data.full_name,
        role=data.role,
        is_active=data.is_active,
        is_superuser=data.is_superuser,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """
    Get a specific user by ID.

    Admin only.
    """
    user = await session.get(User, user_id)
    if not user:
        raise NotFoundError("User", str(user_id))

    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """
    Update a user.

    Admin only.
    """
    # Rate limit: 20 user updates per minute
    await check_rate_limit(request, "user_update", identifier=str(current_user.id))

    user = await session.get(User, user_id)
    if not user:
        raise NotFoundError("User", str(user_id))

    # Check for email conflict if updating email
    if data.email and data.email != user.email:
        existing = await session.execute(select(User).where(User.email == data.email))
        if existing.scalar_one_or_none():
            raise ConflictError(
                "Email already in use",
                f"A user with email {data.email} already exists",
            )

    # Prevent self-demotion from admin
    if user.id == current_user.id:
        if data.role and data.role != UserRole.ADMIN:
            raise ConflictError(
                "Cannot demote self",
                "You cannot remove your own admin privileges",
            )
        if data.is_active is False:
            raise ConflictError(
                "Cannot deactivate self",
                "You cannot deactivate your own account",
            )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await session.commit()
    await session.refresh(user)

    return UserResponse.model_validate(user)


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """
    Delete a user.

    Admin only. Cannot delete yourself.
    """
    # Rate limit: 5 user deletions per minute
    await check_rate_limit(request, "user_delete", identifier=str(current_user.id))

    user = await session.get(User, user_id)
    if not user:
        raise NotFoundError("User", str(user_id))

    # Prevent self-deletion
    if user.id == current_user.id:
        raise ConflictError(
            "Cannot delete self",
            "You cannot delete your own account",
        )

    await session.delete(user)
    await session.commit()

    return MessageResponse(message=f"User {user.email} deleted successfully")


@router.post("/{user_id}/reset-password", response_model=MessageResponse)
async def reset_user_password(
    user_id: UUID,
    data: PasswordResetRequest,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """
    Reset a user's password.

    Admin only.

    **Password Requirements**:
    - Minimum 8 characters
    - At least one uppercase letter (A-Z)
    - At least one lowercase letter (a-z)
    - At least one digit (0-9)
    """
    user = await session.get(User, user_id)
    if not user:
        raise NotFoundError("User", str(user_id))

    # Validate password against full policy
    validation = validate_password(data.new_password)
    if not validation.is_valid:
        raise ConflictError(
            "Invalid password",
            "; ".join(validation.errors) if validation.errors else default_policy.get_requirements_text(),
        )

    user.password_hash = get_password_hash(data.new_password)
    await session.commit()

    return MessageResponse(message=f"Password for {user.email} reset successfully")
