"""Historical data and crawl history endpoints."""

from collections import defaultdict
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, case as sa_case, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import ExtractedData, Document, DataSource
from app.models.crawl_job import CrawlJob, JobStatus

router = APIRouter()


@router.get("/history/municipalities")
async def get_municipality_history(
    municipality_name: Optional[str] = Query(default=None),
    category_id: Optional[UUID] = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
):
    """Get historical development of results per municipality over time."""
    from datetime import datetime, timedelta

    start_date = datetime.utcnow() - timedelta(days=days)
    municipality_expr = ExtractedData.extracted_content["municipality"].astext

    if municipality_name:
        # History for specific municipality
        query = (
            select(
                cast(ExtractedData.created_at, Date).label("date"),
                func.count(ExtractedData.id).label("document_count"),
                func.avg(ExtractedData.confidence_score).label("avg_confidence"),
                func.sum(
                    sa_case(
                        (ExtractedData.extracted_content["is_relevant"].astext == "true", 1),
                        else_=0
                    )
                ).label("relevant_count"),
            )
            .where(municipality_expr.ilike(f"%{municipality_name}%"))
            .where(ExtractedData.created_at >= start_date)
            .group_by(cast(ExtractedData.created_at, Date))
            .order_by(cast(ExtractedData.created_at, Date))
        )

        if category_id:
            query = query.where(ExtractedData.category_id == category_id)

        result = await session.execute(query)
        rows = result.fetchall()

        history = [
            {
                "date": row.date.isoformat(),
                "document_count": row.document_count,
                "relevant_count": row.relevant_count or 0,
                "avg_confidence": round(float(row.avg_confidence), 2) if row.avg_confidence else None,
            }
            for row in rows
        ]

        # Calculate trends
        if len(history) >= 2:
            recent = history[-7:] if len(history) >= 7 else history[-len(history)//2:]
            older = history[:-7] if len(history) >= 7 else history[:len(history)//2]

            recent_avg = sum(h["document_count"] for h in recent) / len(recent) if recent else 0
            older_avg = sum(h["document_count"] for h in older) / len(older) if older else 0

            trend = "steigend" if recent_avg > older_avg * 1.1 else ("fallend" if recent_avg < older_avg * 0.9 else "stabil")
        else:
            trend = "unbekannt"

        return {
            "municipality": municipality_name,
            "period_days": days,
            "total_documents": sum(h["document_count"] for h in history),
            "total_relevant": sum(h["relevant_count"] for h in history),
            "trend": trend,
            "history": history,
        }

    else:
        # Overview: history for all municipalities
        query = (
            select(
                cast(ExtractedData.created_at, Date).label("date"),
                municipality_expr.label("municipality"),
                func.count(ExtractedData.id).label("document_count"),
            )
            .where(municipality_expr.isnot(None))
            .where(municipality_expr != "")
            .where(ExtractedData.created_at >= start_date)
            .group_by(cast(ExtractedData.created_at, Date), municipality_expr)
            .order_by(cast(ExtractedData.created_at, Date).desc())
        )

        if category_id:
            query = query.where(ExtractedData.category_id == category_id)

        result = await session.execute(query)
        rows = result.fetchall()

        by_municipality = defaultdict(list)
        for row in rows:
            if row.municipality and row.municipality.strip():
                by_municipality[row.municipality].append({
                    "date": row.date.isoformat(),
                    "count": row.document_count,
                })

        municipalities = []
        for name, history in by_municipality.items():
            total = sum(h["count"] for h in history)
            recent = history[:7] if len(history) >= 7 else history[:max(1, len(history)//2)]
            older = history[7:] if len(history) >= 7 else history[max(1, len(history)//2):]

            recent_avg = sum(h["count"] for h in recent) / len(recent) if recent else 0
            older_avg = sum(h["count"] for h in older) / len(older) if older else 0

            if older_avg > 0:
                trend_pct = ((recent_avg - older_avg) / older_avg) * 100
            else:
                trend_pct = 100 if recent_avg > 0 else 0

            municipalities.append({
                "name": name,
                "total_documents": total,
                "recent_documents": sum(h["count"] for h in recent),
                "trend_percent": round(trend_pct, 1),
                "trend": "steigend" if trend_pct > 10 else ("fallend" if trend_pct < -10 else "stabil"),
                "first_seen": history[-1]["date"] if history else None,
                "last_seen": history[0]["date"] if history else None,
            })

        municipalities.sort(key=lambda x: x["recent_documents"], reverse=True)

        return {
            "period_days": days,
            "total_municipalities": len(municipalities),
            "municipalities": municipalities,
        }


@router.get("/history/crawls")
async def get_crawl_history(
    source_id: Optional[UUID] = Query(default=None),
    category_id: Optional[UUID] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Get history of crawl jobs with results summary."""
    query = (
        select(CrawlJob)
        .where(CrawlJob.status.in_([JobStatus.COMPLETED, JobStatus.FAILED]))
        .order_by(CrawlJob.started_at.desc())
        .limit(limit)
    )

    if source_id:
        query = query.where(CrawlJob.source_id == source_id)

    result = await session.execute(query)
    jobs = result.scalars().all()

    crawls = []
    for job in jobs:
        source = await session.get(DataSource, job.source_id)

        doc_count = (await session.execute(
            select(func.count()).where(Document.crawl_job_id == job.id)
        )).scalar()

        extraction_query = (
            select(func.count())
            .select_from(ExtractedData)
            .join(Document)
            .where(Document.crawl_job_id == job.id)
        )
        extraction_count = (await session.execute(extraction_query)).scalar()

        crawls.append({
            "job_id": str(job.id),
            "source_name": source.name if source else None,
            "source_municipality": source.location_name if source else None,
            "status": job.status.value,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "documents_found": job.documents_found or 0,
            "documents_new": job.documents_new or 0,
            "documents_stored": doc_count or 0,
            "extractions_created": extraction_count or 0,
            "error_count": job.error_count or 0,
            "errors": job.error_log[:3] if job.error_log else [],
        })

    return {
        "total_crawls": len(crawls),
        "crawls": crawls,
    }
