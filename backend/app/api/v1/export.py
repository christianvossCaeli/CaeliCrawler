"""Public API endpoints for data export."""

import csv
import io
import json
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import ExtractedData, Document, DataSource, Category

router = APIRouter()


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

    export_data = []
    for ext in extractions:
        doc = await session.get(Document, ext.document_id)
        source = await session.get(DataSource, doc.source_id) if doc else None
        category = await session.get(Category, ext.category_id)

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
        doc = await session.get(Document, ext.document_id)
        source = await session.get(DataSource, doc.source_id) if doc else None
        category = await session.get(Category, ext.category_id)

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
        query = query.join(DataSource).where(DataSource.category_id == category_id)

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
):
    """Test a webhook endpoint."""
    import httpx

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
