"""Audit context manager and utilities."""

from typing import Any, Dict, List, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction
from app.models.user import User
from app.services.audit_service import create_audit_log, compute_diff


def get_request_context(request: Optional[Request]) -> Dict[str, Optional[str]]:
    """
    Extract audit context from FastAPI request.

    Args:
        request: FastAPI Request object

    Returns:
        Dict with ip_address and user_agent
    """
    if not request:
        return {"ip_address": None, "user_agent": None}

    # Get client IP (handle proxies)
    ip_address = None
    if request.client:
        ip_address = request.client.host

    # Check for forwarded header (behind proxy/load balancer)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()

    return {
        "ip_address": ip_address,
        "user_agent": request.headers.get("user-agent"),
    }


class AuditContext:
    """
    Context manager for tracking changes and creating audit logs.

    Usage:
        async with AuditContext(session, user, request) as audit:
            old_data = entity.to_dict()
            entity.name = "new name"
            new_data = entity.to_dict()
            audit.track_update(entity, old_data, new_data)

    The audit logs are only saved if no exception occurs.
    """

    def __init__(
        self,
        session: AsyncSession,
        user: Optional[User] = None,
        request: Optional[Request] = None,
    ):
        """
        Initialize audit context.

        Args:
            session: Database session
            user: Current user (optional for system actions)
            request: FastAPI request for IP/user-agent extraction
        """
        self.session = session
        self.user = user
        self.request = request
        self.entries: List[Dict[str, Any]] = []
        self._context = get_request_context(request)

    async def __aenter__(self) -> "AuditContext":
        """Enter context."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit context and save audit logs if no exception.

        Audit logs are only persisted if the operation succeeded.
        """
        if exc_type is None:
            # No exception, save all audit entries
            for entry in self.entries:
                await create_audit_log(self.session, **entry)

    def track_create(
        self,
        entity: Any,
        entity_name: Optional[str] = None,
    ) -> None:
        """
        Track entity creation.

        Args:
            entity: The created entity
            entity_name: Optional display name (auto-detected if not provided)
        """
        name = entity_name or self._get_entity_name(entity)
        self.entries.append({
            "action": AuditAction.CREATE,
            "entity_type": entity.__class__.__name__,
            "entity_id": entity.id,
            "entity_name": name,
            "changes": {"created": True},
            "user": self.user,
            **self._context,
        })

    def track_update(
        self,
        entity: Any,
        old_data: Dict[str, Any],
        new_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Track entity update with diff.

        Args:
            entity: The updated entity
            old_data: Entity state before update
            new_data: Entity state after update (uses entity.to_dict() if not provided)
        """
        if new_data is None:
            if hasattr(entity, "to_dict"):
                new_data = entity.to_dict()
            else:
                new_data = {}

        changes = compute_diff(old_data, new_data)

        if not changes:
            return  # No actual changes to track

        self.entries.append({
            "action": AuditAction.UPDATE,
            "entity_type": entity.__class__.__name__,
            "entity_id": entity.id,
            "entity_name": self._get_entity_name(entity),
            "changes": changes,
            "user": self.user,
            **self._context,
        })

    def track_delete(
        self,
        entity: Any,
        entity_name: Optional[str] = None,
    ) -> None:
        """
        Track entity deletion.

        Args:
            entity: The deleted entity
            entity_name: Optional display name
        """
        name = entity_name or self._get_entity_name(entity)
        self.entries.append({
            "action": AuditAction.DELETE,
            "entity_type": entity.__class__.__name__,
            "entity_id": entity.id,
            "entity_name": name,
            "changes": {"deleted": True},
            "user": self.user,
            **self._context,
        })

    def track_action(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: Optional[Any] = None,
        entity_name: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Track a custom action.

        Args:
            action: The action type
            entity_type: Type of entity
            entity_id: Entity ID (optional)
            entity_name: Entity name (optional)
            changes: Additional change data (optional)
        """
        self.entries.append({
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "entity_name": entity_name,
            "changes": changes or {},
            "user": self.user,
            **self._context,
        })

    def _get_entity_name(self, entity: Any) -> Optional[str]:
        """Get a human-readable name for an entity."""
        for attr in ["name", "title", "email", "slug"]:
            value = getattr(entity, attr, None)
            if value:
                return str(value)
        return str(entity.id) if hasattr(entity, "id") else None
