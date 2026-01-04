"""Service for creating audit log entries."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction, AuditLog
from app.models.user import User


def compute_diff(old_data: dict[str, Any], new_data: dict[str, Any]) -> dict[str, Any]:
    """
    Compute the difference between old and new data.

    Args:
        old_data: Entity state before changes
        new_data: Entity state after changes

    Returns:
        Dict with changed fields: {field: {old: value, new: value}}
    """
    changes = {}
    all_keys = set(old_data.keys()) | set(new_data.keys())

    # Fields to exclude from diff
    excluded_fields = {"updated_at", "created_at", "password_hash"}

    for key in all_keys:
        if key in excluded_fields:
            continue

        old_val = old_data.get(key)
        new_val = new_data.get(key)

        # Normalize datetime objects for comparison
        if isinstance(old_val, datetime):
            old_val = old_val.isoformat()
        if isinstance(new_val, datetime):
            new_val = new_val.isoformat()

        # Normalize UUID objects
        if isinstance(old_val, UUID):
            old_val = str(old_val)
        if isinstance(new_val, UUID):
            new_val = str(new_val)

        if old_val != new_val:
            changes[key] = {
                "old": _serialize_value(old_val),
                "new": _serialize_value(new_val),
            }

    return changes


def _serialize_value(value: Any) -> Any:
    """Serialize a value for JSON storage."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if hasattr(value, "value"):  # Enum
        return value.value
    if isinstance(value, (list, dict)):
        return value
    return str(value)


async def create_audit_log(
    session: AsyncSession,
    action: AuditAction,
    entity_type: str,
    entity_id: UUID | None = None,
    entity_name: str | None = None,
    changes: dict[str, Any] | None = None,
    user: User | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """
    Create an audit log entry.

    Args:
        session: Database session
        action: The action being performed
        entity_type: Type of entity (model name)
        entity_id: ID of the affected entity
        entity_name: Human-readable name of the entity
        changes: Dict of changes for UPDATE actions
        user: User performing the action
        ip_address: Client IP address
        user_agent: Client user agent

    Returns:
        Created AuditLog instance
    """
    log = AuditLog(
        user_id=user.id if user else None,
        user_email=user.email if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        changes=changes or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(log)
    return log


async def log_create(
    session: AsyncSession,
    entity: Any,
    user: User | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """
    Log entity creation.

    Args:
        session: Database session
        entity: The created entity
        user: User who created it
        ip_address: Client IP
        user_agent: Client user agent

    Returns:
        Created AuditLog
    """
    entity_name = getattr(entity, "name", None) or getattr(entity, "email", None)
    return await create_audit_log(
        session=session,
        action=AuditAction.CREATE,
        entity_type=entity.__class__.__name__,
        entity_id=entity.id,
        entity_name=str(entity_name) if entity_name else None,
        changes={"created": True},
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def log_update(
    session: AsyncSession,
    entity: Any,
    old_data: dict[str, Any],
    new_data: dict[str, Any],
    user: User | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog | None:
    """
    Log entity update with computed diff.

    Args:
        session: Database session
        entity: The updated entity
        old_data: Entity state before update
        new_data: Entity state after update
        user: User who made the update
        ip_address: Client IP
        user_agent: Client user agent

    Returns:
        Created AuditLog or None if no changes
    """
    changes = compute_diff(old_data, new_data)

    if not changes:
        return None  # No actual changes to log

    entity_name = getattr(entity, "name", None) or getattr(entity, "email", None)
    return await create_audit_log(
        session=session,
        action=AuditAction.UPDATE,
        entity_type=entity.__class__.__name__,
        entity_id=entity.id,
        entity_name=str(entity_name) if entity_name else None,
        changes=changes,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def log_delete(
    session: AsyncSession,
    entity: Any,
    user: User | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """
    Log entity deletion.

    Args:
        session: Database session
        entity: The deleted entity
        user: User who deleted it
        ip_address: Client IP
        user_agent: Client user agent

    Returns:
        Created AuditLog
    """
    entity_name = getattr(entity, "name", None) or getattr(entity, "email", None)
    return await create_audit_log(
        session=session,
        action=AuditAction.DELETE,
        entity_type=entity.__class__.__name__,
        entity_id=entity.id,
        entity_name=str(entity_name) if entity_name else None,
        changes={"deleted": True},
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def log_login(
    session: AsyncSession,
    user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Log user login."""
    return await create_audit_log(
        session=session,
        action=AuditAction.LOGIN,
        entity_type="User",
        entity_id=user.id,
        entity_name=user.email,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def log_logout(
    session: AsyncSession,
    user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Log user logout."""
    return await create_audit_log(
        session=session,
        action=AuditAction.LOGOUT,
        entity_type="User",
        entity_id=user.id,
        entity_name=user.email,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def log_password_change(
    session: AsyncSession,
    user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Log password change."""
    return await create_audit_log(
        session=session,
        action=AuditAction.PASSWORD_CHANGE,
        entity_type="User",
        entity_id=user.id,
        entity_name=user.email,
        changes={"password_changed": True},
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def log_session_revoke(
    session: AsyncSession,
    user: User,
    user_session: Any,
    reason: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Log session revocation."""
    return await create_audit_log(
        session=session,
        action=AuditAction.SESSION_REVOKE,
        entity_type="UserSession",
        entity_id=user_session.id,
        entity_name=user_session.device_name,
        changes={
            "reason": reason,
            "device_type": user_session.device_type.value
            if hasattr(user_session.device_type, "value")
            else str(user_session.device_type),
            "session_ip": user_session.ip_address,
        },
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def log_bulk_session_revoke(
    session: AsyncSession,
    user: User,
    count: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Log bulk session revocation (sign out everywhere)."""
    return await create_audit_log(
        session=session,
        action=AuditAction.SESSION_REVOKE_ALL,
        entity_type="User",
        entity_id=user.id,
        entity_name=user.email,
        changes={"sessions_revoked": count},
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def log_crawler_start(
    session: AsyncSession,
    user: User,
    source: Any,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Log crawler start."""
    return await create_audit_log(
        session=session,
        action=AuditAction.CRAWLER_START,
        entity_type="DataSource",
        entity_id=source.id,
        entity_name=source.name,
        changes={"url": source.url if hasattr(source, "url") else None},
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def log_export(
    session: AsyncSession,
    user: User,
    export_type: str,
    record_count: int,
    filters: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Log data export."""
    return await create_audit_log(
        session=session,
        action=AuditAction.EXPORT,
        entity_type="Export",
        entity_name=export_type,
        changes={
            "export_type": export_type,
            "record_count": record_count,
            "filters": filters or {},
        },
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def log_security_event(
    session: AsyncSession,
    event_type: str,
    details: dict[str, Any],
    user: User | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Log security events (rate limiting, suspicious activity, etc.)."""
    return await create_audit_log(
        session=session,
        action=AuditAction.SECURITY_ALERT,
        entity_type="Security",
        entity_name=event_type,
        changes=details,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )
