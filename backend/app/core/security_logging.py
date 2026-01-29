"""
Centralized Security Logging Module.

This module provides structured logging for security-relevant events
such as SSRF attempts, rate limiting, authentication failures, and
authorization denials.

All security events are logged with consistent structure for easy
monitoring, alerting, and audit trails. Events are also persisted
to the database for compliance and incident response.

Usage:
    from app.core.security_logging import security_logger

    security_logger.log_ssrf_blocked(user_id, url, reason)
    security_logger.log_rate_limit_exceeded(user_id, endpoint, limit)
    security_logger.log_auth_failure(email, reason, ip_address)
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

import structlog

logger = structlog.get_logger()

# Late imports to avoid circular dependencies
# These are imported inside methods that need them


class SecurityEventType(str, Enum):
    """Types of security events for categorization."""

    # SSRF Protection
    SSRF_BLOCKED = "security.ssrf.blocked"
    SSRF_REDIRECT_BLOCKED = "security.ssrf.redirect_blocked"

    # Rate Limiting
    RATE_LIMIT_EXCEEDED = "security.rate_limit.exceeded"
    RATE_LIMIT_WARNING = "security.rate_limit.warning"

    # Authentication
    AUTH_FAILURE = "security.auth.failure"
    AUTH_SUCCESS = "security.auth.success"
    AUTH_LOGOUT = "security.auth.logout"
    AUTH_TOKEN_INVALID = "security.auth.token_invalid"  # noqa: S105
    AUTH_TOKEN_EXPIRED = "security.auth.token_expired"  # noqa: S105

    # Authorization
    AUTHZ_DENIED = "security.authz.denied"
    AUTHZ_ESCALATION_ATTEMPT = "security.authz.escalation_attempt"

    # Input Validation
    INPUT_VALIDATION_FAILED = "security.input.validation_failed"
    INPUT_SIZE_EXCEEDED = "security.input.size_exceeded"

    # Suspicious Activity
    SUSPICIOUS_PATTERN = "security.suspicious.pattern"
    BRUTE_FORCE_DETECTED = "security.suspicious.brute_force"


class SecurityLogger:
    """
    Centralized security event logger.

    Provides structured logging methods for all security-relevant events
    with consistent format and context. Events are both logged to structlog
    and persisted to the database for compliance purposes.
    """

    def __init__(self):
        self._logger = structlog.get_logger("security")

    def _log_event(
        self,
        event_type: SecurityEventType,
        severity: str,
        message: str,
        user_id: UUID | None = None,
        ip_address: str | None = None,
        **extra_context: Any,
    ) -> None:
        """
        Log a security event with structured context.

        Events are logged to structlog and persisted to the database.

        Args:
            event_type: Type of security event
            severity: Log level (info, warning, error, critical)
            message: Human-readable message
            user_id: Optional user ID associated with event
            ip_address: Optional IP address of requester
            **extra_context: Additional context fields
        """
        log_method = getattr(self._logger, severity, self._logger.warning)

        # Log to structlog (sync, immediate)
        log_method(
            message,
            event_type=event_type.value,
            user_id=str(user_id) if user_id else None,
            ip_address=ip_address,
            timestamp=datetime.now(UTC).isoformat(),
            **extra_context,
        )

        # Extract known fields from extra_context for database persistence
        email = extra_context.pop("email", None)
        endpoint = extra_context.get("endpoint")  # Keep in context for details

        # Persist to database (async, background)
        self._persist_event(
            event_type=event_type,
            severity=severity,
            message=message,
            user_id=user_id,
            ip_address=ip_address,
            email=email,
            endpoint=endpoint,
            details=extra_context if extra_context else None,
        )

    def _persist_event(
        self,
        event_type: SecurityEventType,
        severity: str,
        message: str,
        user_id: UUID | None = None,
        ip_address: str | None = None,
        email: str | None = None,
        endpoint: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Persist security event to database asynchronously."""
        try:
            # Late imports to avoid circular dependencies
            from app.models.security_event import SecurityEventSeverity
            from app.models.security_event import SecurityEventType as DBSecurityEventType
            from services.security_event_service import security_event_service

            # Mapping from local event types to database event types
            event_type_mapping = {
                SecurityEventType.AUTH_FAILURE: DBSecurityEventType.LOGIN_FAILURE,
                SecurityEventType.AUTH_SUCCESS: DBSecurityEventType.LOGIN_SUCCESS,
                SecurityEventType.AUTH_LOGOUT: DBSecurityEventType.LOGOUT,
                SecurityEventType.AUTH_TOKEN_INVALID: DBSecurityEventType.ACCESS_DENIED,
                SecurityEventType.AUTH_TOKEN_EXPIRED: DBSecurityEventType.ACCESS_DENIED,
                SecurityEventType.AUTHZ_DENIED: DBSecurityEventType.ACCESS_DENIED,
                SecurityEventType.AUTHZ_ESCALATION_ATTEMPT: DBSecurityEventType.PERMISSION_ESCALATION_ATTEMPT,
                SecurityEventType.RATE_LIMIT_EXCEEDED: DBSecurityEventType.RATE_LIMIT_EXCEEDED,
                SecurityEventType.RATE_LIMIT_WARNING: DBSecurityEventType.RATE_LIMIT_WARNING,
                SecurityEventType.SSRF_BLOCKED: DBSecurityEventType.SSRF_ATTEMPT,
                SecurityEventType.SSRF_REDIRECT_BLOCKED: DBSecurityEventType.SSRF_ATTEMPT,
                SecurityEventType.SUSPICIOUS_PATTERN: DBSecurityEventType.SUSPICIOUS_REQUEST,
                SecurityEventType.BRUTE_FORCE_DETECTED: DBSecurityEventType.SUSPICIOUS_REQUEST,
                SecurityEventType.INPUT_VALIDATION_FAILED: DBSecurityEventType.INVALID_INPUT,
                SecurityEventType.INPUT_SIZE_EXCEEDED: DBSecurityEventType.INVALID_INPUT,
            }

            # Mapping from string severity to enum
            severity_mapping = {
                "info": SecurityEventSeverity.INFO,
                "warning": SecurityEventSeverity.WARNING,
                "error": SecurityEventSeverity.ERROR,
                "critical": SecurityEventSeverity.CRITICAL,
            }

            db_event_type = event_type_mapping.get(event_type)
            if not db_event_type:
                return  # Event type not mapped, skip persistence

            db_severity = severity_mapping.get(severity, SecurityEventSeverity.INFO)

            # Determine success based on event type
            success = event_type in {
                SecurityEventType.AUTH_SUCCESS,
                SecurityEventType.AUTH_LOGOUT,
            }

            security_event_service.log_event_background(
                event_type=db_event_type,
                message=message,
                severity=db_severity,
                user_id=str(user_id) if user_id else None,
                user_email=email,
                ip_address=ip_address,
                endpoint=endpoint,
                details=details,
                success=success,
            )
        except Exception:
            # Never let persistence failure break the application
            pass

    # =========================================================================
    # SSRF Protection Events
    # =========================================================================

    def log_ssrf_blocked(
        self,
        user_id: UUID | None,
        url: str,
        reason: str,
        ip_address: str | None = None,
    ) -> None:
        """Log a blocked SSRF attempt."""
        self._log_event(
            event_type=SecurityEventType.SSRF_BLOCKED,
            severity="warning",
            message="SSRF attempt blocked",
            user_id=user_id,
            ip_address=ip_address,
            blocked_url=url,
            block_reason=reason,
        )

    def log_ssrf_redirect_blocked(
        self,
        user_id: UUID | None,
        original_url: str,
        redirect_url: str,
        reason: str,
        ip_address: str | None = None,
    ) -> None:
        """Log a blocked SSRF redirect attempt."""
        self._log_event(
            event_type=SecurityEventType.SSRF_REDIRECT_BLOCKED,
            severity="warning",
            message="SSRF redirect blocked",
            user_id=user_id,
            ip_address=ip_address,
            original_url=original_url,
            redirect_url=redirect_url,
            block_reason=reason,
        )

    # =========================================================================
    # Rate Limiting Events
    # =========================================================================

    def log_rate_limit_exceeded(
        self,
        user_id: UUID | None,
        endpoint: str,
        limit: int,
        window_seconds: int,
        ip_address: str | None = None,
    ) -> None:
        """Log when rate limit is exceeded."""
        self._log_event(
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            severity="warning",
            message="Rate limit exceeded",
            user_id=user_id,
            ip_address=ip_address,
            endpoint=endpoint,
            limit=limit,
            window_seconds=window_seconds,
        )

    def log_rate_limit_warning(
        self,
        user_id: UUID | None,
        endpoint: str,
        current_count: int,
        limit: int,
        ip_address: str | None = None,
    ) -> None:
        """Log when approaching rate limit (80% threshold)."""
        self._log_event(
            event_type=SecurityEventType.RATE_LIMIT_WARNING,
            severity="info",
            message="Approaching rate limit",
            user_id=user_id,
            ip_address=ip_address,
            endpoint=endpoint,
            current_count=current_count,
            limit=limit,
            percentage=round(current_count / limit * 100, 1),
        )

    # =========================================================================
    # Authentication Events
    # =========================================================================

    def log_auth_failure(
        self,
        email: str,
        reason: str,
        ip_address: str | None = None,
        attempt_count: int | None = None,
    ) -> None:
        """Log authentication failure."""
        self._log_event(
            event_type=SecurityEventType.AUTH_FAILURE,
            severity="warning",
            message="Authentication failed",
            ip_address=ip_address,
            email=email,
            failure_reason=reason,
            attempt_count=attempt_count,
        )

    def log_auth_success(
        self,
        user_id: UUID,
        email: str,
        ip_address: str | None = None,
    ) -> None:
        """Log successful authentication."""
        self._log_event(
            event_type=SecurityEventType.AUTH_SUCCESS,
            severity="info",
            message="Authentication successful",
            user_id=user_id,
            ip_address=ip_address,
            email=email,
        )

    def log_auth_logout(
        self,
        user_id: UUID,
        ip_address: str | None = None,
    ) -> None:
        """Log user logout."""
        self._log_event(
            event_type=SecurityEventType.AUTH_LOGOUT,
            severity="info",
            message="User logged out",
            user_id=user_id,
            ip_address=ip_address,
        )

    def log_token_invalid(
        self,
        token_hint: str,
        reason: str,
        ip_address: str | None = None,
    ) -> None:
        """Log invalid token usage attempt."""
        self._log_event(
            event_type=SecurityEventType.AUTH_TOKEN_INVALID,
            severity="warning",
            message="Invalid token used",
            ip_address=ip_address,
            token_hint=token_hint[:20] + "..." if len(token_hint) > 20 else token_hint,
            invalid_reason=reason,
        )

    # =========================================================================
    # Authorization Events
    # =========================================================================

    def log_authorization_denied(
        self,
        user_id: UUID,
        resource: str,
        action: str,
        required_role: str | None = None,
        ip_address: str | None = None,
    ) -> None:
        """Log authorization denial."""
        self._log_event(
            event_type=SecurityEventType.AUTHZ_DENIED,
            severity="warning",
            message="Authorization denied",
            user_id=user_id,
            ip_address=ip_address,
            resource=resource,
            action=action,
            required_role=required_role,
        )

    def log_privilege_escalation_attempt(
        self,
        user_id: UUID,
        attempted_action: str,
        ip_address: str | None = None,
    ) -> None:
        """Log potential privilege escalation attempt."""
        self._log_event(
            event_type=SecurityEventType.AUTHZ_ESCALATION_ATTEMPT,
            severity="error",
            message="Privilege escalation attempt detected",
            user_id=user_id,
            ip_address=ip_address,
            attempted_action=attempted_action,
        )

    # =========================================================================
    # Input Validation Events
    # =========================================================================

    def log_validation_failed(
        self,
        user_id: UUID | None,
        endpoint: str,
        field: str,
        value_hint: str,
        reason: str,
        ip_address: str | None = None,
    ) -> None:
        """Log input validation failure."""
        self._log_event(
            event_type=SecurityEventType.INPUT_VALIDATION_FAILED,
            severity="info",
            message="Input validation failed",
            user_id=user_id,
            ip_address=ip_address,
            endpoint=endpoint,
            field=field,
            value_hint=value_hint[:50] if value_hint else None,
            validation_reason=reason,
        )

    def log_input_size_exceeded(
        self,
        user_id: UUID | None,
        endpoint: str,
        field: str,
        size: int,
        max_size: int,
        ip_address: str | None = None,
    ) -> None:
        """Log when input size exceeds limits."""
        self._log_event(
            event_type=SecurityEventType.INPUT_SIZE_EXCEEDED,
            severity="warning",
            message="Input size limit exceeded",
            user_id=user_id,
            ip_address=ip_address,
            endpoint=endpoint,
            field=field,
            actual_size=size,
            max_size=max_size,
        )

    # =========================================================================
    # Suspicious Activity Events
    # =========================================================================

    def log_suspicious_pattern(
        self,
        user_id: UUID | None,
        pattern_type: str,
        details: str,
        ip_address: str | None = None,
    ) -> None:
        """Log suspicious activity pattern."""
        self._log_event(
            event_type=SecurityEventType.SUSPICIOUS_PATTERN,
            severity="warning",
            message="Suspicious pattern detected",
            user_id=user_id,
            ip_address=ip_address,
            pattern_type=pattern_type,
            details=details,
        )

    def log_brute_force_detected(
        self,
        target: str,
        attempt_count: int,
        window_seconds: int,
        ip_address: str | None = None,
    ) -> None:
        """Log potential brute force attack."""
        self._log_event(
            event_type=SecurityEventType.BRUTE_FORCE_DETECTED,
            severity="error",
            message="Brute force attack detected",
            ip_address=ip_address,
            target=target,
            attempt_count=attempt_count,
            window_seconds=window_seconds,
        )


# Global singleton instance
security_logger = SecurityLogger()
