"""Admin API endpoints for notification management."""

import secrets
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditContext
from app.core.deps import get_current_user
from app.core.exceptions import ConflictError, NotFoundError
from app.database import get_session
from app.models.audit_log import AuditAction
from app.models.device_token import DevicePlatform, DeviceToken
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationEventType,
    NotificationStatus,
)
from app.models.notification_rule import NotificationRule
from app.models.user import User
from app.models.user_email import UserEmailAddress
from services.notifications.notification_service import NotificationService

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================


class UserEmailAddressCreate(BaseModel):
    """Schema for adding an email address."""

    email: EmailStr
    label: str | None = None


class UserEmailAddressResponse(BaseModel):
    """Email address response schema."""

    id: UUID
    email: str
    label: str | None = None
    is_verified: bool
    is_primary: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationRuleCreate(BaseModel):
    """Schema for creating a notification rule."""

    name: str
    description: str | None = None
    event_type: NotificationEventType
    channel: NotificationChannel
    conditions: dict[str, Any] = {}
    channel_config: dict[str, Any] = {}
    digest_enabled: bool = False
    digest_frequency: str | None = None
    is_active: bool = True


class NotificationRuleUpdate(BaseModel):
    """Schema for updating a notification rule."""

    name: str | None = None
    description: str | None = None
    conditions: dict[str, Any] | None = None
    channel_config: dict[str, Any] | None = None
    digest_enabled: bool | None = None
    digest_frequency: str | None = None
    is_active: bool | None = None


class NotificationRuleResponse(BaseModel):
    """Notification rule response schema."""

    id: UUID
    name: str
    description: str | None = None
    event_type: NotificationEventType
    channel: NotificationChannel
    conditions: dict[str, Any]
    channel_config: dict[str, Any]
    digest_enabled: bool
    digest_frequency: str | None = None
    is_active: bool
    trigger_count: int
    last_triggered: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    """Notification response schema."""

    id: UUID
    event_type: NotificationEventType
    channel: NotificationChannel
    title: str
    body: str
    status: NotificationStatus
    related_entity_type: str | None = None
    related_entity_id: UUID | None = None
    sent_at: datetime | None = None
    read_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Paginated list of notifications."""

    items: list[NotificationResponse]
    total: int
    page: int
    per_page: int
    pages: int


class UnreadCountResponse(BaseModel):
    """Unread notification count."""

    count: int


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


class WebhookTestRequest(BaseModel):
    """Webhook test request."""

    url: str
    auth: dict[str, Any] | None = None


class WebhookTestResponse(BaseModel):
    """Webhook test response."""

    success: bool
    status_code: int | None = None
    response: str | None = None
    error: str | None = None


class NotificationPreferencesUpdate(BaseModel):
    """User notification preferences update."""

    notifications_enabled: bool | None = None
    notification_digest_time: str | None = None


class NotificationPreferencesResponse(BaseModel):
    """User notification preferences."""

    notifications_enabled: bool
    notification_digest_time: str | None = None


class DeviceTokenCreate(BaseModel):
    """Schema for registering a device token."""

    token: str
    platform: str  # "ios", "android", "web"
    device_name: str | None = None
    app_version: str | None = None
    os_version: str | None = None


class DeviceTokenResponse(BaseModel):
    """Device token response schema."""

    id: UUID
    token: str
    platform: DevicePlatform
    device_name: str | None = None
    app_version: str | None = None
    os_version: str | None = None
    is_active: bool
    last_used_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Email Addresses Endpoints
# =============================================================================


@router.get("/email-addresses", response_model=list[UserEmailAddressResponse])
async def list_email_addresses(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    List all email addresses for current user.
    """
    result = await session.execute(
        select(UserEmailAddress)
        .where(UserEmailAddress.user_id == current_user.id)
        .order_by(UserEmailAddress.created_at.desc())
    )
    return [UserEmailAddressResponse.model_validate(ea) for ea in result.scalars().all()]


@router.post("/email-addresses", response_model=UserEmailAddressResponse, status_code=201)
async def add_email_address(
    data: UserEmailAddressCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Add a new email address for the current user.

    The email address will need to be verified before it can be used.
    """
    # Check for duplicate
    existing = await session.execute(
        select(UserEmailAddress).where(
            UserEmailAddress.user_id == current_user.id,
            UserEmailAddress.email == data.email,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(
            "Email already exists",
            f"The email address {data.email} is already registered",
        )

    # Check if it's the user's primary email
    if data.email == current_user.email:
        raise ConflictError(
            "Primary email",
            "This is your primary account email and doesn't need to be added separately",
        )

    email_address = UserEmailAddress(
        user_id=current_user.id,
        email=data.email,
        label=data.label,
        verification_token=secrets.token_urlsafe(32),
    )
    session.add(email_address)
    await session.commit()
    await session.refresh(email_address)

    # TODO: Send verification email via notification service

    return UserEmailAddressResponse.model_validate(email_address)


@router.delete("/email-addresses/{email_id}", response_model=MessageResponse)
async def delete_email_address(
    email_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Delete an email address.
    """
    email_address = await session.get(UserEmailAddress, email_id)

    if not email_address or email_address.user_id != current_user.id:
        raise NotFoundError("Email address", str(email_id))

    await session.delete(email_address)
    await session.commit()

    return MessageResponse(message="Email address deleted")


@router.post("/email-addresses/{email_id}/verify", response_model=MessageResponse)
async def verify_email_address(
    email_id: UUID,
    token: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """
    Verify an email address using the verification token.
    """
    email_address = await session.get(UserEmailAddress, email_id)

    if not email_address:
        raise NotFoundError("Email address", str(email_id))

    if email_address.is_verified:
        return MessageResponse(message="Email address already verified")

    if email_address.verification_token != token:
        raise HTTPException(
            status_code=400,
            detail="Invalid verification token",
        )

    email_address.is_verified = True
    email_address.verified_at = datetime.now(UTC)
    email_address.verification_token = None
    await session.commit()

    return MessageResponse(message="Email address verified successfully")


@router.post("/email-addresses/{email_id}/resend-verification", response_model=MessageResponse)
async def resend_verification(
    email_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Resend verification email.
    """
    email_address = await session.get(UserEmailAddress, email_id)

    if not email_address or email_address.user_id != current_user.id:
        raise NotFoundError("Email address", str(email_id))

    if email_address.is_verified:
        return MessageResponse(message="Email address already verified")

    # Generate new token
    email_address.verification_token = secrets.token_urlsafe(32)
    await session.commit()

    # TODO: Send verification email via notification service

    return MessageResponse(message="Verification email sent")


# =============================================================================
# Device Token Endpoints (Push Notifications)
# =============================================================================


@router.get("/device-tokens", response_model=list[DeviceTokenResponse])
async def list_device_tokens(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    List all registered device tokens for current user.
    """
    result = await session.execute(
        select(DeviceToken)
        .where(DeviceToken.user_id == current_user.id)
        .order_by(DeviceToken.created_at.desc())
    )
    return [DeviceTokenResponse.model_validate(dt) for dt in result.scalars().all()]


@router.post("/device-token", response_model=DeviceTokenResponse, status_code=201)
async def register_device_token(
    data: DeviceTokenCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Register a device token for push notifications.

    If the token already exists for this user, it will be updated.
    If the token exists for another user, it will be moved to this user.
    """
    # Validate platform
    try:
        platform = DevicePlatform(data.platform.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platform. Must be one of: {', '.join(p.value for p in DevicePlatform)}",
        ) from None

    # Check if token already exists (for any user)
    existing = await session.execute(
        select(DeviceToken).where(DeviceToken.token == data.token)
    )
    existing_token = existing.scalar_one_or_none()

    if existing_token:
        # Update existing token - transfer to current user if needed
        existing_token.user_id = current_user.id
        existing_token.platform = platform
        existing_token.device_name = data.device_name
        existing_token.app_version = data.app_version
        existing_token.os_version = data.os_version
        existing_token.is_active = True
        existing_token.last_used_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(existing_token)
        return DeviceTokenResponse.model_validate(existing_token)

    # Create new token
    device_token = DeviceToken(
        user_id=current_user.id,
        token=data.token,
        platform=platform,
        device_name=data.device_name,
        app_version=data.app_version,
        os_version=data.os_version,
        last_used_at=datetime.now(UTC),
    )
    session.add(device_token)
    await session.commit()
    await session.refresh(device_token)

    return DeviceTokenResponse.model_validate(device_token)


@router.delete("/device-token/{token}", response_model=MessageResponse)
async def unregister_device_token(
    token: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Unregister a device token.

    The token is identified by the raw token string (URL-encoded if necessary).
    """
    result = await session.execute(
        select(DeviceToken).where(
            DeviceToken.token == token,
            DeviceToken.user_id == current_user.id,
        )
    )
    device_token = result.scalar_one_or_none()

    if not device_token:
        raise NotFoundError("Device token", token[:20] + "...")

    await session.delete(device_token)
    await session.commit()

    return MessageResponse(message="Device token unregistered")


@router.post("/device-token/{token}/deactivate", response_model=MessageResponse)
async def deactivate_device_token(
    token: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Deactivate a device token without deleting it.

    Useful when the user logs out but may log back in.
    """
    result = await session.execute(
        select(DeviceToken).where(
            DeviceToken.token == token,
            DeviceToken.user_id == current_user.id,
        )
    )
    device_token = result.scalar_one_or_none()

    if not device_token:
        raise NotFoundError("Device token", token[:20] + "...")

    device_token.is_active = False
    await session.commit()

    return MessageResponse(message="Device token deactivated")


# =============================================================================
# Notification Rules Endpoints
# =============================================================================


@router.get("/rules", response_model=list[NotificationRuleResponse])
async def list_rules(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    List all notification rules for current user.
    """
    result = await session.execute(
        select(NotificationRule)
        .where(NotificationRule.user_id == current_user.id)
        .order_by(NotificationRule.created_at.desc())
    )
    return [NotificationRuleResponse.model_validate(r) for r in result.scalars().all()]


@router.post("/rules", response_model=NotificationRuleResponse, status_code=201)
async def create_rule(
    data: NotificationRuleCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new notification rule.
    """
    # Validate digest frequency if digest is enabled
    if data.digest_enabled and data.digest_frequency not in ("hourly", "daily", "weekly", None):
        raise HTTPException(
            status_code=400,
            detail="Invalid digest frequency. Must be 'hourly', 'daily', or 'weekly'",
        )

    # Check for duplicate by conditions
    from app.utils.similarity import find_duplicate_notification_rule
    duplicate = await find_duplicate_notification_rule(
        session,
        user_id=current_user.id,
        event_type=data.event_type.value,
        channel=data.channel.value,
        conditions=data.conditions,
    )
    if duplicate:
        existing_rule, reason = duplicate
        raise ConflictError(
            "Ähnliche Benachrichtigungsregel existiert bereits",
            detail=f"{reason}. Bearbeiten Sie die bestehende Regel statt eine neue zu erstellen.",
        )

    rule = NotificationRule(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        event_type=data.event_type,
        channel=data.channel,
        conditions=data.conditions,
        channel_config=data.channel_config,
        digest_enabled=data.digest_enabled,
        digest_frequency=data.digest_frequency,
        is_active=data.is_active,
    )

    async with AuditContext(session, current_user, request) as audit:
        session.add(rule)
        await session.flush()

        audit.track_action(
            action=AuditAction.CREATE,
            entity_type="NotificationRule",
            entity_id=rule.id,
            entity_name=rule.name,
            changes={
                "name": rule.name,
                "event_type": rule.event_type.value,
                "channel": rule.channel.value,
                "is_active": rule.is_active,
            },
        )

        await session.commit()
        await session.refresh(rule)

    return NotificationRuleResponse.model_validate(rule)


@router.get("/rules/{rule_id}", response_model=NotificationRuleResponse)
async def get_rule(
    rule_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific notification rule.
    """
    rule = await session.get(NotificationRule, rule_id)

    if not rule or rule.user_id != current_user.id:
        raise NotFoundError("Notification rule", str(rule_id))

    return NotificationRuleResponse.model_validate(rule)


@router.put("/rules/{rule_id}", response_model=NotificationRuleResponse)
async def update_rule(
    rule_id: UUID,
    data: NotificationRuleUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Update a notification rule.
    """
    rule = await session.get(NotificationRule, rule_id)

    if not rule or rule.user_id != current_user.id:
        raise NotFoundError("Notification rule", str(rule_id))

    # Validate digest frequency if provided
    if data.digest_frequency is not None and data.digest_frequency not in ("hourly", "daily", "weekly"):
        raise HTTPException(
            status_code=400,
            detail="Invalid digest frequency. Must be 'hourly', 'daily', or 'weekly'",
        )

    # Capture old state for audit
    old_data = {
        "name": rule.name,
        "is_active": rule.is_active,
    }

    update_data = data.model_dump(exclude_unset=True)

    async with AuditContext(session, current_user, request) as audit:
        for field, value in update_data.items():
            setattr(rule, field, value)

        new_data = {
            "name": rule.name,
            "is_active": rule.is_active,
        }

        audit.track_update(rule, old_data, new_data)

        await session.commit()
        await session.refresh(rule)

    return NotificationRuleResponse.model_validate(rule)


@router.delete("/rules/{rule_id}", response_model=MessageResponse)
async def delete_rule(
    rule_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a notification rule.
    """
    rule = await session.get(NotificationRule, rule_id)

    if not rule or rule.user_id != current_user.id:
        raise NotFoundError("Notification rule", str(rule_id))

    name = rule.name

    async with AuditContext(session, current_user, request) as audit:
        audit.track_action(
            action=AuditAction.DELETE,
            entity_type="NotificationRule",
            entity_id=rule_id,
            entity_name=name,
            changes={
                "deleted": True,
                "name": name,
                "event_type": rule.event_type.value,
                "channel": rule.channel.value,
            },
        )

        await session.delete(rule)
        await session.commit()

    return MessageResponse(message="Rule deleted")


# =============================================================================
# Notifications Endpoints
# =============================================================================


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    status: NotificationStatus | None = None,
    channel: NotificationChannel | None = None,
    event_type: NotificationEventType | None = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    List notifications for current user with optional filtering.
    """
    query = select(Notification).where(Notification.user_id == current_user.id)

    if status:
        query = query.where(Notification.status == status)
    if channel:
        query = query.where(Notification.channel == channel)
    if event_type:
        query = query.where(Notification.event_type == event_type)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    # Apply pagination
    query = query.order_by(Notification.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    notifications = list(result.scalars().all())

    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get count of unread in-app notifications.
    """
    service = NotificationService(session)
    count = await service.get_unread_count(current_user.id)
    return UnreadCountResponse(count=count)


@router.get("/notifications/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific notification.
    """
    notification = await session.get(Notification, notification_id)

    if not notification or notification.user_id != current_user.id:
        raise NotFoundError("Notification", str(notification_id))

    return NotificationResponse.model_validate(notification)


@router.post("/notifications/{notification_id}/read", response_model=MessageResponse)
async def mark_notification_read(
    notification_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Mark a notification as read.
    """
    service = NotificationService(session)
    success = await service.mark_as_read(str(notification_id), current_user.id)

    if not success:
        raise NotFoundError("Notification", str(notification_id))

    return MessageResponse(message="Notification marked as read")


@router.post("/notifications/read-all", response_model=MessageResponse)
async def mark_all_read(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Mark all notifications as read.
    """
    service = NotificationService(session)
    count = await service.mark_all_as_read(current_user.id)
    return MessageResponse(message=f"{count} notifications marked as read")


# =============================================================================
# Webhook Testing
# =============================================================================


@router.post("/test-webhook", response_model=WebhookTestResponse)
async def test_webhook(
    data: WebhookTestRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Test a webhook URL with a sample payload.
    """
    import httpx

    test_payload = {
        "event_type": "TEST",
        "notification_id": "test-notification-id",
        "title": "Webhook Test",
        "body": "Dies ist eine Test-Benachrichtigung von CaeliCrawler",
        "timestamp": datetime.now(UTC).isoformat(),
        "data": {"test": True},
    }

    headers = {"Content-Type": "application/json", "User-Agent": "CaeliCrawler-Webhook/1.0"}

    # Handle authentication
    if data.auth:
        auth_type = data.auth.get("type")
        if auth_type == "bearer":
            headers["Authorization"] = f"Bearer {data.auth.get('token', '')}"
        elif auth_type == "basic":
            import base64
            creds = base64.b64encode(
                f"{data.auth.get('username', '')}:{data.auth.get('password', '')}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {creds}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                data.url,
                json=test_payload,
                headers=headers,
                timeout=10,
            )

            return WebhookTestResponse(
                success=response.is_success,
                status_code=response.status_code,
                response=response.text[:500] if response.text else None,
            )

    except httpx.TimeoutException:
        return WebhookTestResponse(
            success=False,
            error="Connection timeout",
        )
    except httpx.RequestError as e:
        return WebhookTestResponse(
            success=False,
            error=str(e),
        )
    except Exception as e:
        return WebhookTestResponse(
            success=False,
            error=f"Unexpected error: {str(e)}",
        )


# =============================================================================
# User Preferences
# =============================================================================


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_preferences(
    current_user: User = Depends(get_current_user),
):
    """
    Get notification preferences for current user.
    """
    return NotificationPreferencesResponse(
        notifications_enabled=current_user.notifications_enabled,
        notification_digest_time=current_user.notification_digest_time,
    )


@router.put("/preferences", response_model=NotificationPreferencesResponse)
async def update_preferences(
    data: NotificationPreferencesUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Update notification preferences for current user.
    """
    update_data = data.model_dump(exclude_unset=True)

    # Validate digest time format if provided
    if "notification_digest_time" in update_data:
        time_str = update_data["notification_digest_time"]
        if time_str:
            try:
                parts = time_str.split(":")
                if len(parts) != 2:
                    raise ValueError()
                hour, minute = int(parts[0]), int(parts[1])
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError()
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid time format. Use HH:MM (24-hour format)",
                ) from None

    for field, value in update_data.items():
        setattr(current_user, field, value)

    await session.commit()

    return NotificationPreferencesResponse(
        notifications_enabled=current_user.notifications_enabled,
        notification_digest_time=current_user.notification_digest_time,
    )


# =============================================================================
# Available Event Types and Channels (for UI)
# =============================================================================


@router.get("/event-types")
async def get_event_types():
    """
    Get all available notification event types.
    """
    return [
        {
            "value": e.value,
            "label": _get_event_type_label(e),
            "description": _get_event_type_description(e),
        }
        for e in NotificationEventType
    ]


@router.get("/channels")
async def get_channels():
    """
    Get all available notification channels.
    """
    return [
        {
            "value": c.value,
            "label": _get_channel_label(c),
            "description": _get_channel_description(c),
            "available": c != NotificationChannel.MS_TEAMS,  # MS Teams not yet implemented
        }
        for c in NotificationChannel
    ]


def _get_event_type_label(event_type: NotificationEventType) -> str:
    """Get human-readable label for event type."""
    labels = {
        NotificationEventType.NEW_DOCUMENT: "Neue Dokumente",
        NotificationEventType.DOCUMENT_CHANGED: "Dokument geändert",
        NotificationEventType.DOCUMENT_REMOVED: "Dokument entfernt",
        NotificationEventType.CRAWL_STARTED: "Crawl gestartet",
        NotificationEventType.CRAWL_COMPLETED: "Crawl abgeschlossen",
        NotificationEventType.CRAWL_FAILED: "Crawl fehlgeschlagen",
        NotificationEventType.AI_ANALYSIS_COMPLETED: "Analyse abgeschlossen",
        NotificationEventType.HIGH_CONFIDENCE_RESULT: "Relevantes Ergebnis",
        NotificationEventType.SOURCE_STATUS_CHANGED: "Quellenstatus geändert",
        NotificationEventType.SOURCE_ERROR: "Fehler bei Quelle",
    }
    return labels.get(event_type, event_type.value)


def _get_event_type_description(event_type: NotificationEventType) -> str:
    """Get description for event type."""
    descriptions = {
        NotificationEventType.NEW_DOCUMENT: "Wenn neue Dokumente in einer Datenquelle gefunden werden",
        NotificationEventType.DOCUMENT_CHANGED: "Wenn sich ein Dokument geändert hat",
        NotificationEventType.DOCUMENT_REMOVED: "Wenn ein Dokument entfernt wurde",
        NotificationEventType.CRAWL_STARTED: "Wenn ein Crawl-Vorgang startet",
        NotificationEventType.CRAWL_COMPLETED: "Wenn ein Crawl-Vorgang erfolgreich abgeschlossen wurde",
        NotificationEventType.CRAWL_FAILED: "Wenn ein Crawl-Vorgang fehlschlägt",
        NotificationEventType.AI_ANALYSIS_COMPLETED: "Wenn die AI-Analyse eines Dokuments abgeschlossen ist",
        NotificationEventType.HIGH_CONFIDENCE_RESULT: "Wenn ein Ergebnis mit hoher Relevanz gefunden wird",
        NotificationEventType.SOURCE_STATUS_CHANGED: "Wenn sich der Status einer Datenquelle ändert",
        NotificationEventType.SOURCE_ERROR: "Wenn ein Fehler bei einer Datenquelle auftritt",
    }
    return descriptions.get(event_type, "")


def _get_channel_label(channel: NotificationChannel) -> str:
    """Get human-readable label for channel."""
    labels = {
        NotificationChannel.EMAIL: "E-Mail",
        NotificationChannel.WEBHOOK: "Webhook",
        NotificationChannel.IN_APP: "In-App",
        NotificationChannel.MS_TEAMS: "Microsoft Teams",
    }
    return labels.get(channel, channel.value)


def _get_channel_description(channel: NotificationChannel) -> str:
    """Get description for channel."""
    descriptions = {
        NotificationChannel.EMAIL: "Benachrichtigungen per E-Mail erhalten",
        NotificationChannel.WEBHOOK: "HTTP-Webhook an eine URL senden",
        NotificationChannel.IN_APP: "Benachrichtigungen in der Web-Oberfläche anzeigen",
        NotificationChannel.MS_TEAMS: "Benachrichtigungen an Microsoft Teams senden (demnächst)",
    }
    return descriptions.get(channel, "")
