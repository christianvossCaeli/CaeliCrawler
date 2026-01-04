"""Admin API endpoints for user management."""

from datetime import datetime
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query, Request

logger = structlog.get_logger(__name__)
from pydantic import BaseModel, EmailStr  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.audit import AuditContext  # noqa: E402
from app.core.deps import require_admin  # noqa: E402
from app.core.exceptions import ConflictError, NotFoundError  # noqa: E402
from app.core.password_policy import default_policy, validate_password  # noqa: E402
from app.core.query_helpers import PaginationParams, paginate_query  # noqa: E402
from app.core.rate_limit import check_rate_limit  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.database import get_session  # noqa: E402
from app.models.audit_log import AuditAction  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402

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

    email: EmailStr | None = None
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None


class UserResponse(BaseModel):
    """User response schema."""

    id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    is_superuser: bool
    last_login: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Paginated list of users."""

    items: list[UserResponse]
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
    role: UserRole | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    sort_by: str | None = Query(
        default=None, description="Sort by field (email, full_name, role, is_active, last_login, created_at)"
    ),
    sort_order: str | None = Query(default="desc", description="Sort order (asc, desc)"),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """
    List all users with pagination, filtering and sorting.

    Admin only.
    """
    # Build query with filters
    query = select(User)

    if role:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if search:
        # Escape SQL wildcards to prevent injection
        escaped_search = search.replace("%", r"\%").replace("_", r"\_")
        search_pattern = f"%{escaped_search}%"
        query = query.where(
            (User.email.ilike(search_pattern, escape="\\")) | (User.full_name.ilike(search_pattern, escape="\\"))
        )

    # Handle sorting
    sort_desc = sort_order == "desc"
    sort_column_map = {
        "email": User.email,
        "full_name": User.full_name,
        "role": User.role,
        "is_active": User.is_active,
        "last_login": User.last_login,
        "created_at": User.created_at,
    }

    if sort_by and sort_by in sort_column_map:
        order_col = sort_column_map[sort_by]
        if sort_desc:
            query = query.order_by(order_col.desc().nulls_last(), User.created_at.desc())
        else:
            query = query.order_by(order_col.asc().nulls_last(), User.created_at.desc())
    else:
        # Default ordering
        query = query.order_by(User.created_at.desc())

    # Use pagination helper
    pagination = PaginationParams(page=page, per_page=per_page)
    users, total = await paginate_query(session, query, pagination)

    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=pagination.total_pages(total),
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

    # Create user with audit
    async with AuditContext(session, current_user, request) as audit:
        user = User(
            email=data.email,
            password_hash=get_password_hash(data.password),
            full_name=data.full_name,
            role=data.role,
            is_active=data.is_active,
            is_superuser=data.is_superuser,
        )
        session.add(user)
        await session.flush()

        audit.track_action(
            action=AuditAction.USER_CREATE,
            entity_type="User",
            entity_id=user.id,
            entity_name=user.email,
            changes={
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
            },
        )

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

    # Capture old state for audit
    old_data = {
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value if user.role else None,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
    }

    async with AuditContext(session, current_user, request) as audit:
        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        # Capture new state
        new_data = {
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value if user.role else None,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
        }

        audit.track_update(user, old_data, new_data)

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

    user_email = user.email
    user_name = user.full_name

    async with AuditContext(session, current_user, request) as audit:
        audit.track_action(
            action=AuditAction.USER_DELETE,
            entity_type="User",
            entity_id=user.id,
            entity_name=user_email,
            changes={
                "deleted": True,
                "email": user_email,
                "full_name": user_name,
                "role": user.role.value if user.role else None,
            },
        )

        await session.delete(user)
        await session.commit()

    return MessageResponse(message=f"User {user_email} deleted successfully")


@router.post("/{user_id}/reset-password", response_model=MessageResponse)
async def reset_user_password(
    user_id: UUID,
    data: PasswordResetRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
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

    async with AuditContext(session, current_user, request) as audit:
        user.password_hash = get_password_hash(data.new_password)

        audit.track_action(
            action=AuditAction.PASSWORD_RESET,
            entity_type="User",
            entity_id=user.id,
            entity_name=user.email,
            changes={
                "password_reset": True,
                "admin_initiated": True,
            },
        )

        await session.commit()

    return MessageResponse(message=f"Password for {user.email} reset successfully")
