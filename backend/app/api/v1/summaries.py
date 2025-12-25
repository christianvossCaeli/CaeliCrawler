"""Public API endpoints for shared summaries.

These endpoints allow unauthenticated access to shared summaries
via share tokens, with optional password protection.
"""

import asyncio
import io
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from passlib.hash import bcrypt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import CustomSummary, SummaryExecution, SummaryShare, SummaryWidget
from app.models.summary_execution import ExecutionStatus
from app.core.rate_limit import check_rate_limit
from services.summaries import SummaryExportService
from services.summaries.export_service import sanitize_filename

# Minimum response time to prevent timing attacks (500-1000ms random delay)
# Increased from 100-200ms to better protect against brute-force attacks
MIN_RESPONSE_TIME_MS = 500
MAX_RESPONSE_TIME_MS = 1000

logger = structlog.get_logger(__name__)

router = APIRouter()


# --- Helpers ---

def validate_share_token(token: str) -> bool:
    """
    Validate share token format.

    Valid tokens are URL-safe base64 strings of expected length (43 chars for 32 bytes).
    This helps reject clearly invalid tokens early without database lookup.
    """
    import re

    # Token must be 40-50 chars (secrets.token_urlsafe(32) produces ~43 chars)
    if not token or len(token) < 40 or len(token) > 50:
        return False

    # Must only contain URL-safe base64 characters
    if not re.match(r'^[A-Za-z0-9_-]+$', token):
        return False

    return True


# --- Schemas ---

class SharedSummaryRequest(BaseModel):
    """Request body for accessing a shared summary."""
    password: Optional[str] = None


class SharedWidgetResponse(BaseModel):
    """Widget data in shared summary response."""
    id: str
    widget_type: str
    title: str
    subtitle: Optional[str] = None
    position: Dict[str, int]
    visualization_config: Optional[Dict[str, Any]] = None


class SharedSummaryResponse(BaseModel):
    """Response for shared summary access."""
    summary: Dict[str, Any]
    widgets: List[SharedWidgetResponse]
    widget_data: Dict[str, Any]
    last_updated: Optional[str] = None
    allow_export: bool


# --- Endpoints ---

async def _add_timing_noise():
    """Add random delay to prevent timing attacks."""
    delay_ms = secrets.randbelow(MAX_RESPONSE_TIME_MS - MIN_RESPONSE_TIME_MS) + MIN_RESPONSE_TIME_MS
    await asyncio.sleep(delay_ms / 1000)


@router.post("/shared/{token}", response_model=SharedSummaryResponse)
async def access_shared_summary(
    token: str,
    data: SharedSummaryRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Access a shared summary by token.

    This endpoint is public (no authentication required).
    If the share is password-protected, the correct password must be provided.

    Rate limited to prevent brute-force attacks on share tokens.

    Args:
        token: The share token
        data: Request body with optional password

    Returns:
        Summary data with widget content

    Raises:
        401: Password required or incorrect
        404: Share not found
        410: Share expired or deactivated
        429: Too many requests
    """
    # Rate limiting based on client IP to prevent brute-force attacks
    client_ip = request.client.host if request.client else "unknown"
    await check_rate_limit(request, "shared_summary_access", identifier=client_ip)

    # Validate token format first (prevents unnecessary DB queries)
    if not validate_share_token(token):
        await _add_timing_noise()  # Prevent timing attacks
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share-Link nicht gefunden",
        )

    # Find share by token
    result = await session.execute(
        select(SummaryShare).where(SummaryShare.share_token == token)
    )
    share = result.scalar_one_or_none()

    if not share:
        await _add_timing_noise()  # Prevent timing attacks
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share-Link nicht gefunden",
        )

    # Check if active
    if not share.is_active:
        await _add_timing_noise()  # Prevent timing attacks
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Dieser Share-Link wurde deaktiviert",
        )

    # Check expiry
    if share.expires_at and share.expires_at < datetime.now(timezone.utc):
        await _add_timing_noise()  # Prevent timing attacks
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Dieser Share-Link ist abgelaufen",
        )

    # Check password
    if share.password_hash:
        if not data.password:
            await _add_timing_noise()  # Prevent timing attacks
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Passwort erforderlich",
            )
        if not bcrypt.verify(data.password, share.password_hash):
            await _add_timing_noise()  # Prevent timing attacks
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Falsches Passwort",
            )

    # Update view stats
    share.view_count += 1
    share.last_viewed_at = datetime.now(timezone.utc)

    # Load summary with widgets
    summary_result = await session.execute(
        select(CustomSummary)
        .options(selectinload(CustomSummary.widgets))
        .where(CustomSummary.id == share.summary_id)
    )
    summary = summary_result.scalar_one_or_none()

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zusammenfassung nicht gefunden",
        )

    # Get latest execution with cached data
    exec_result = await session.execute(
        select(SummaryExecution)
        .where(
            SummaryExecution.summary_id == summary.id,
            SummaryExecution.status == ExecutionStatus.COMPLETED,
        )
        .order_by(SummaryExecution.created_at.desc())
        .limit(1)
    )
    last_execution = exec_result.scalar_one_or_none()

    await session.commit()

    # Build response
    widgets = [
        SharedWidgetResponse(
            id=str(w.id),
            widget_type=w.widget_type.value,
            title=w.title,
            subtitle=w.subtitle,
            position={
                "x": w.position_x,
                "y": w.position_y,
                "w": w.width,
                "h": w.height,
            },
            visualization_config=w.visualization_config,
        )
        for w in sorted(summary.widgets, key=lambda x: (x.position_y, x.position_x))
    ]

    # Map widget data with string keys for frontend
    widget_data = {}
    if last_execution and last_execution.cached_data:
        for w in summary.widgets:
            old_key = f"widget_{w.id}"
            if old_key in last_execution.cached_data:
                widget_data[str(w.id)] = last_execution.cached_data[old_key]

    logger.info(
        "shared_summary_accessed",
        share_id=str(share.id),
        summary_id=str(summary.id),
        view_count=share.view_count,
    )

    return SharedSummaryResponse(
        summary={
            "id": str(summary.id),
            "name": summary.name,
            "description": summary.description,
        },
        widgets=widgets,
        widget_data=widget_data,
        last_updated=last_execution.completed_at.isoformat() if last_execution and last_execution.completed_at else None,
        allow_export=share.allow_export,
    )


@router.get("/shared/{token}/export")
async def export_shared_summary(
    token: str,
    request: Request,
    password: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """
    Export a shared summary as PDF.

    Only available if allow_export is enabled for the share.
    Rate limited to prevent DoS via expensive PDF generation.

    Args:
        token: The share token
        password: Optional password if protected

    Returns:
        PDF file stream

    Raises:
        429: Too many requests
    """
    # Rate limiting - PDF generation is expensive
    client_ip = request.client.host if request.client else "unknown"
    await check_rate_limit(request, "shared_summary_export", identifier=client_ip)

    # Validate token format first (prevents unnecessary DB queries)
    if not validate_share_token(token):
        await _add_timing_noise()  # Prevent timing attacks
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share-Link nicht gefunden",
        )

    # Find share by token
    result = await session.execute(
        select(SummaryShare).where(SummaryShare.share_token == token)
    )
    share = result.scalar_one_or_none()

    if not share:
        await _add_timing_noise()  # Prevent timing attacks
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share-Link nicht gefunden",
        )

    # Check if active
    if not share.is_active:
        await _add_timing_noise()  # Prevent timing attacks
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Dieser Share-Link wurde deaktiviert",
        )

    # Check expiry
    if share.expires_at and share.expires_at < datetime.now(timezone.utc):
        await _add_timing_noise()  # Prevent timing attacks
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Dieser Share-Link ist abgelaufen",
        )

    # Check password
    if share.password_hash:
        if not password:
            await _add_timing_noise()  # Prevent timing attacks
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Passwort erforderlich",
            )
        if not bcrypt.verify(password, share.password_hash):
            await _add_timing_noise()  # Prevent timing attacks
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Falsches Passwort",
            )

    # Check if export is allowed
    if not share.allow_export:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Export ist für diesen Share-Link nicht erlaubt",
        )

    # Get summary name for filename
    summary = await session.get(CustomSummary, share.summary_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zusammenfassung nicht gefunden",
        )

    # Export to PDF
    export_service = SummaryExportService(session)
    try:
        pdf_bytes = await export_service.export_to_pdf(share.summary_id)
        # Sanitize filename to prevent path traversal and header injection
        safe_filename = sanitize_filename(summary.name)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=\"{safe_filename}.pdf\""
            }
        )
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF-Export nicht verfügbar: {str(e)}",
        )
