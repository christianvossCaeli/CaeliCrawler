"""Public API endpoints for data export."""

import csv
import io
import ipaddress
import json
import socket
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import ExtractedData, Document, DataSource, DataSourceCategory, Category
from app.models.user import User
from app.core.deps import get_current_user

router = APIRouter()


# =============================================================================
# SSRF Protection
# =============================================================================

# Blocked IP ranges for SSRF protection
BLOCKED_IP_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),      # Localhost
    ipaddress.ip_network("10.0.0.0/8"),       # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),    # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),   # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),   # Link-local (AWS/Azure/GCP metadata)
    ipaddress.ip_network("0.0.0.0/8"),        # Current network
    ipaddress.ip_network("100.64.0.0/10"),    # Carrier-grade NAT
    ipaddress.ip_network("192.0.0.0/24"),     # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),     # TEST-NET-1
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),   # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),      # Multicast
    ipaddress.ip_network("240.0.0.0/4"),      # Reserved
]


def validate_webhook_url(url: str) -> Tuple[bool, str]:
    """
    Validate URL for SSRF protection.

    Returns (is_safe, error_message).
    """
    try:
        parsed = urlparse(url)

        # Only allow https for webhooks (security best practice)
        if parsed.scheme != "https":
            return False, "Only HTTPS URLs are allowed for webhooks"

        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid URL: no hostname"

        # Block localhost variations
        blocked_hostnames = {"localhost", "127.0.0.1", "::1", "0.0.0.0", "[::1]"}
        if hostname.lower() in blocked_hostnames:
            return False, "Localhost URLs are not allowed"

        # Block internal hostnames
        if hostname.endswith(".local") or hostname.endswith(".internal"):
            return False, "Internal hostnames are not allowed"

        # Try to resolve and check IP
        try:
            ip = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip)

            for blocked_range in BLOCKED_IP_RANGES:
                if ip_obj in blocked_range:
                    return False, "URL resolves to blocked IP range (internal network)"
        except socket.gaierror:
            # Can't resolve - allow but log warning
            pass

        return True, ""

    except Exception as e:
        return False, f"Invalid URL: {str(e)}"


async def _bulk_load_related_data(
    session: AsyncSession,
    extractions: List[ExtractedData]
) -> tuple[Dict[UUID, Document], Dict[UUID, DataSource], Dict[UUID, Category]]:
    """Bulk-load all related documents, sources, and categories for extractions.

    Returns dictionaries mapping IDs to their respective objects.
    This eliminates N+1 query problems by loading all data in 3 queries instead of 3N.
    """
    if not extractions:
        return {}, {}, {}

    # Collect all unique IDs
    doc_ids = {ext.document_id for ext in extractions if ext.document_id}
    cat_ids = {ext.category_id for ext in extractions if ext.category_id}

    # Bulk-load documents with their sources (single query with join)
    docs_result = await session.execute(
        select(Document)
        .options(selectinload(Document.source))
        .where(Document.id.in_(doc_ids))
    )
    docs_by_id: Dict[UUID, Document] = {doc.id: doc for doc in docs_result.scalars().all()}

    # Extract sources from loaded documents
    sources_by_id: Dict[UUID, DataSource] = {
        doc.source.id: doc.source
        for doc in docs_by_id.values()
        if doc.source
    }

    # Bulk-load categories
    cats_result = await session.execute(
        select(Category).where(Category.id.in_(cat_ids))
    )
    cats_by_id: Dict[UUID, Category] = {cat.id: cat for cat in cats_result.scalars().all()}

    return docs_by_id, sources_by_id, cats_by_id


@router.get("/json")
async def export_json(
    category_id: Optional[UUID] = Query(default=None),
    source_id: Optional[UUID] = Query(default=None),
    min_confidence: Optional[float] = Query(default=None, ge=0, le=1),
    human_verified_only: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
):
    """Export extracted data as JSON."""
    query = select(ExtractedData)

    if category_id:
        query = query.where(ExtractedData.category_id == category_id)
    if source_id:
        query = query.join(Document).where(Document.source_id == source_id)
    if min_confidence is not None:
        query = query.where(ExtractedData.confidence_score >= min_confidence)
    if human_verified_only:
        query = query.where(ExtractedData.human_verified == True)

    result = await session.execute(query)
    extractions = result.scalars().all()

    # Bulk-load all related data in 2-3 queries instead of 3N queries
    docs_by_id, sources_by_id, cats_by_id = await _bulk_load_related_data(
        session, extractions
    )

    export_data = []
    for ext in extractions:
        doc = docs_by_id.get(ext.document_id)
        source = sources_by_id.get(doc.source_id) if doc and doc.source_id else None
        category = cats_by_id.get(ext.category_id)

        export_data.append({
            "id": str(ext.id),
            "document_id": str(ext.document_id),
            "document_url": doc.original_url if doc else None,
            "document_title": doc.title if doc else None,
            "source_name": source.name if source else None,
            "category_name": category.name if category else None,
            "extraction_type": ext.extraction_type,
            "extracted_content": ext.final_content,
            "confidence_score": ext.confidence_score,
            "human_verified": ext.human_verified,
            "created_at": ext.created_at.isoformat(),
        })

    return StreamingResponse(
        iter([json.dumps(export_data, indent=2, ensure_ascii=False)]),
        media_type="application/json",
        headers={
            "Content-Disposition": "attachment; filename=caelichrawler_export.json"
        },
    )


@router.get("/csv")
async def export_csv(
    category_id: Optional[UUID] = Query(default=None),
    source_id: Optional[UUID] = Query(default=None),
    min_confidence: Optional[float] = Query(default=None, ge=0, le=1),
    human_verified_only: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
):
    """Export extracted data as CSV."""
    query = select(ExtractedData)

    if category_id:
        query = query.where(ExtractedData.category_id == category_id)
    if source_id:
        query = query.join(Document).where(Document.source_id == source_id)
    if min_confidence is not None:
        query = query.where(ExtractedData.confidence_score >= min_confidence)
    if human_verified_only:
        query = query.where(ExtractedData.human_verified == True)

    result = await session.execute(query)
    extractions = result.scalars().all()

    # Bulk-load all related data in 2-3 queries instead of 3N queries
    docs_by_id, sources_by_id, cats_by_id = await _bulk_load_related_data(
        session, extractions
    )

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "id",
        "document_url",
        "document_title",
        "source_name",
        "category_name",
        "extraction_type",
        "confidence_score",
        "human_verified",
        "extracted_content",
        "created_at",
    ])

    for ext in extractions:
        doc = docs_by_id.get(ext.document_id)
        source = sources_by_id.get(doc.source_id) if doc and doc.source_id else None
        category = cats_by_id.get(ext.category_id)

        writer.writerow([
            str(ext.id),
            doc.original_url if doc else "",
            doc.title if doc else "",
            source.name if source else "",
            category.name if category else "",
            ext.extraction_type,
            ext.confidence_score or "",
            ext.human_verified,
            json.dumps(ext.final_content, ensure_ascii=False),
            ext.created_at.isoformat(),
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=caelichrawler_export.csv"
        },
    )


@router.get("/changes")
async def get_changes_feed(
    since: Optional[str] = Query(default=None, description="ISO datetime to get changes since"),
    category_id: Optional[UUID] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
):
    """Get a feed of recent changes (for polling)."""
    from datetime import datetime
    from app.models import ChangeLog

    query = select(ChangeLog)

    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            query = query.where(ChangeLog.detected_at > since_dt)
        except ValueError:
            pass

    if category_id:
        # Filter via junction table (N:M relationship)
        query = (
            query
            .join(DataSource, ChangeLog.source_id == DataSource.id)
            .join(DataSourceCategory, DataSource.id == DataSourceCategory.data_source_id)
            .where(DataSourceCategory.category_id == category_id)
        )

    query = query.order_by(ChangeLog.detected_at.desc()).limit(limit)

    result = await session.execute(query)
    changes = result.scalars().all()

    return {
        "changes": [
            {
                "id": str(c.id),
                "source_id": str(c.source_id),
                "change_type": c.change_type.value,
                "affected_url": c.affected_url,
                "detected_at": c.detected_at.isoformat(),
                "details": c.details,
            }
            for c in changes
        ],
        "count": len(changes),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/webhook/test")
async def test_webhook(
    url: str = Query(..., description="Webhook URL to test"),
    current_user: User = Depends(get_current_user),  # Require authentication
):
    """
    Test a webhook endpoint.

    **Security:**
    - Requires authentication
    - Only HTTPS URLs allowed
    - Internal/private IP ranges are blocked (SSRF protection)
    """
    import httpx

    # SSRF Protection: Validate URL before making request
    is_safe, error_msg = validate_webhook_url(url)
    if not is_safe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid webhook URL: {error_msg}",
        )

    test_payload = {
        "event": "test",
        "message": "This is a test webhook from CaeliCrawler",
        "timestamp": "2024-01-01T00:00:00Z",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=test_payload,
                timeout=10,
            )
            return {
                "success": response.is_success,
                "status_code": response.status_code,
                "response": response.text[:500] if response.text else None,
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
