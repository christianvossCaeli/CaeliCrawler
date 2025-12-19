"""Municipality endpoints - aggregation and reports."""

from collections import defaultdict
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import ExtractedData, Document, DataSource, Category, Location

router = APIRouter()


@router.get("/municipalities")
async def get_municipalities(
    category_id: Optional[UUID] = Query(default=None),
    min_documents: int = Query(default=1, ge=1),
    min_confidence: float = Query(default=0.7, ge=0, le=1),
    only_relevant: bool = Query(default=True, description="Only include documents marked as relevant"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get list of municipalities with document counts.

    Only includes extractions with confidence >= min_confidence for quality results.
    By default, only shows documents marked as relevant by AI analysis.
    """
    municipality_expr = ExtractedData.extracted_content["municipality"].astext
    is_relevant_expr = ExtractedData.extracted_content["is_relevant"].astext

    query = (
        select(
            municipality_expr.label("municipality"),
            func.count(ExtractedData.id).label("document_count"),
            func.avg(ExtractedData.confidence_score).label("avg_confidence"),
            func.max(ExtractedData.created_at).label("latest_document"),
        )
        .where(municipality_expr.isnot(None))
        .where(municipality_expr != "")
        .where(municipality_expr != "null")
        .where(ExtractedData.confidence_score >= min_confidence)
    )

    if only_relevant:
        query = query.where(is_relevant_expr == "true")

    query = (
        query.group_by(municipality_expr)
        .having(func.count(ExtractedData.id) >= min_documents)
        .order_by(func.count(ExtractedData.id).desc())
    )

    if category_id:
        query = query.where(ExtractedData.category_id == category_id)

    result = await session.execute(query)
    rows = result.fetchall()

    municipalities = [
        {
            "name": row.municipality,
            "document_count": row.document_count,
            "avg_confidence": round(float(row.avg_confidence), 2) if row.avg_confidence else None,
            "latest_document": row.latest_document.isoformat() if row.latest_document else None,
        }
        for row in rows
        if row.municipality and row.municipality.strip()
    ]

    return {
        "municipalities": municipalities,
        "total_municipalities": len(municipalities),
        "total_documents": sum(m["document_count"] for m in municipalities),
    }


@router.get("/municipalities/{municipality_name}/documents")
async def get_municipality_documents(
    municipality_name: str,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    category_id: Optional[UUID] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Get all documents for a specific municipality."""
    query = (
        select(ExtractedData)
        .where(ExtractedData.extracted_content["municipality"].astext.ilike(f"%{municipality_name}%"))
    )

    if category_id:
        query = query.where(ExtractedData.category_id == category_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    query = query.order_by(ExtractedData.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    extractions = result.scalars().all()

    items = []
    for ext in extractions:
        doc = await session.get(Document, ext.document_id)
        source = await session.get(DataSource, doc.source_id) if doc else None
        category = await session.get(Category, ext.category_id)

        items.append({
            "extraction_id": str(ext.id),
            "document_id": str(ext.document_id),
            "document_title": doc.title if doc else None,
            "document_url": doc.original_url if doc else None,
            "document_type": doc.document_type if doc else None,
            "document_date": doc.document_date.isoformat() if doc and doc.document_date else None,
            "source_name": source.name if source else None,
            "category_name": category.name if category else None,
            "confidence": ext.confidence_score,
            "extracted_content": ext.final_content,
            "created_at": ext.created_at.isoformat(),
        })

    return {
        "municipality": municipality_name,
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page if per_page > 0 else 0,
    }


@router.get("/municipalities/{municipality_name}/report")
async def get_municipality_report(
    municipality_name: str,
    category_id: Optional[UUID] = Query(default=None),
    min_confidence: float = Query(default=0.7, ge=0, le=1),
    only_relevant: bool = Query(default=True),
    session: AsyncSession = Depends(get_session),
):
    """Get aggregated intelligence report for a municipality."""
    is_relevant_expr = ExtractedData.extracted_content["is_relevant"].astext

    query = (
        select(ExtractedData)
        .where(ExtractedData.extracted_content["municipality"].astext.ilike(f"%{municipality_name}%"))
        .where(ExtractedData.confidence_score >= min_confidence)
    )

    if only_relevant:
        query = query.where(is_relevant_expr == "true")
    if category_id:
        query = query.where(ExtractedData.category_id == category_id)

    result = await session.execute(query)
    extractions = result.scalars().all()

    if not extractions:
        return {
            "municipality": municipality_name,
            "total_documents": 0,
            "message": "Keine Dokumente für diese Gemeinde gefunden",
        }

    category = None
    if category_id:
        category = await session.get(Category, category_id)
    elif extractions:
        category = await session.get(Category, extractions[0].category_id)

    # Aggregate data
    all_pain_points = []
    all_positive_signals = []
    all_decision_makers = []
    all_summaries = []
    relevance_counts = {"hoch": 0, "mittel": 0, "gering": 0, "keine": 0}
    outreach_priorities = {"hoch": 0, "mittel": 0, "niedrig": 0}
    topics = defaultdict(int)
    document_types = defaultdict(int)
    sources = set()
    total_confidence = 0
    relevant_count = 0

    for ext in extractions:
        content = ext.final_content
        total_confidence += ext.confidence_score or 0

        # Collect pain points
        pain_points = content.get("pain_points", [])
        if isinstance(pain_points, list):
            for pp in pain_points:
                text = pp.get("description") or pp.get("text") or pp.get("quote", "") if isinstance(pp, dict) else pp
                if text and str(text).strip():
                    all_pain_points.append({
                        "text": str(text).strip(),
                        "type": pp.get("type") if isinstance(pp, dict) else None,
                        "severity": pp.get("severity") if isinstance(pp, dict) else None,
                        "document_id": str(ext.document_id),
                        "confidence": ext.confidence_score,
                    })

        # Collect positive signals
        positive_signals = content.get("positive_signals", [])
        if isinstance(positive_signals, list):
            for ps in positive_signals:
                text = ps.get("description") or ps.get("text") or ps.get("quote", "") if isinstance(ps, dict) else ps
                if text and str(text).strip():
                    all_positive_signals.append({
                        "text": str(text).strip(),
                        "type": ps.get("type") if isinstance(ps, dict) else None,
                        "document_id": str(ext.document_id),
                        "confidence": ext.confidence_score,
                    })

        # Collect decision makers
        decision_makers = content.get("decision_makers", [])
        if isinstance(decision_makers, list):
            for dm in decision_makers:
                if isinstance(dm, dict):
                    all_decision_makers.append({**dm, "document_id": str(ext.document_id)})
                elif isinstance(dm, str) and dm.strip():
                    all_decision_makers.append({"name": dm, "document_id": str(ext.document_id)})

        # Collect summaries
        summary = content.get("summary", "")
        if summary:
            all_summaries.append({
                "text": summary,
                "document_id": str(ext.document_id),
                "confidence": ext.confidence_score,
            })

        # Count relevance levels
        relevance = content.get("relevanz", content.get("relevance", ""))
        if isinstance(relevance, str) and relevance.lower() in relevance_counts:
            relevance_counts[relevance.lower()] += 1

        # Count outreach priorities
        outreach = content.get("outreach_recommendation", {})
        if isinstance(outreach, dict):
            priority = outreach.get("priority", "")
            if isinstance(priority, str) and priority.lower() in outreach_priorities:
                outreach_priorities[priority.lower()] += 1

        if content.get("is_relevant") is True:
            relevant_count += 1

        for key in ["document_type", "type", "kategorie"]:
            if key in content and content[key]:
                topics[content[key]] += 1

        doc = await session.get(Document, ext.document_id)
        if doc:
            document_types[doc.document_type or "Unbekannt"] += 1
            source = await session.get(DataSource, doc.source_id)
            if source:
                sources.add(source.name)

    # Calculate metrics
    avg_confidence = total_confidence / len(extractions) if extractions else 0
    relevance_ratio = relevant_count / len(extractions) if extractions else 0

    if outreach_priorities["hoch"] > 0 or relevance_counts["hoch"] >= 2:
        overall_priority = "hoch"
    elif outreach_priorities["mittel"] > 0 or relevance_counts["mittel"] >= 2:
        overall_priority = "mittel"
    else:
        overall_priority = "niedrig"

    # Deduplicate pain points
    pain_point_freq = defaultdict(list)
    for pp in all_pain_points:
        pain_point_freq[pp["text"].lower().strip()].append(pp)

    ranked_pain_points = []
    for normalized, items in sorted(pain_point_freq.items(), key=lambda x: -len(x[1])):
        ranked_pain_points.append({
            "text": items[0]["text"],
            "type": next((i.get("type") for i in items if i.get("type")), None),
            "severity": next((i.get("severity") for i in items if i.get("severity")), None),
            "frequency": len(items),
            "avg_confidence": sum(i["confidence"] or 0 for i in items) / len(items),
        })

    # Deduplicate positive signals
    signal_freq = defaultdict(list)
    for ps in all_positive_signals:
        signal_freq[ps["text"].lower().strip()].append(ps)

    ranked_positive_signals = []
    for normalized, items in sorted(signal_freq.items(), key=lambda x: -len(x[1])):
        ranked_positive_signals.append({
            "text": items[0]["text"],
            "type": next((i.get("type") for i in items if i.get("type")), None),
            "frequency": len(items),
            "avg_confidence": sum(i["confidence"] or 0 for i in items) / len(items),
        })

    # Deduplicate decision makers
    dm_by_name = {}
    for dm in all_decision_makers:
        name = (dm.get("name") or dm.get("person") or "").strip()
        if name and name not in dm_by_name:
            dm_by_name[name] = {
                "name": name,
                "role": dm.get("role", dm.get("position", "")),
                "contact": dm.get("contact", dm.get("email", "")),
            }

    return {
        "municipality": municipality_name,
        "category": category.name if category else None,
        "category_purpose": category.purpose if category else None,
        "overview": {
            "total_documents": len(extractions),
            "relevant_documents": relevant_count,
            "relevance_ratio": round(relevance_ratio, 2),
            "avg_confidence": round(avg_confidence, 2),
            "overall_priority": overall_priority,
            "sources": list(sources),
            "document_types": dict(document_types),
        },
        "relevance_breakdown": relevance_counts,
        "outreach_priorities": outreach_priorities,
        "pain_points": ranked_pain_points[:20],
        "positive_signals": ranked_positive_signals[:20],
        "decision_makers": list(dm_by_name.values())[:20],
        "top_summaries": sorted(all_summaries, key=lambda x: x["confidence"] or 0, reverse=True)[:5],
        "topics": dict(topics),
    }


@router.get("/report/overview")
async def get_overview_report(
    category_id: Optional[UUID] = Query(default=None),
    min_confidence: float = Query(default=0.7, ge=0, le=1),
    only_relevant: bool = Query(default=True),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    """Get overview report of all municipalities with key metrics."""
    municipality_expr = ExtractedData.extracted_content["municipality"].astext
    is_relevant_expr = ExtractedData.extracted_content["is_relevant"].astext

    query = (
        select(
            municipality_expr.label("municipality"),
            func.count(ExtractedData.id).label("document_count"),
            func.avg(ExtractedData.confidence_score).label("avg_confidence"),
            func.max(ExtractedData.created_at).label("latest_document"),
        )
        .where(municipality_expr.isnot(None))
        .where(municipality_expr != "")
        .where(municipality_expr != "null")
        .where(ExtractedData.confidence_score >= min_confidence)
    )

    if only_relevant:
        query = query.where(is_relevant_expr == "true")

    query = query.group_by(municipality_expr).order_by(func.count(ExtractedData.id).desc()).limit(limit)

    if category_id:
        query = query.where(ExtractedData.category_id == category_id)

    result = await session.execute(query)
    rows = result.fetchall()

    municipalities = []
    for row in rows:
        if not row.municipality or not row.municipality.strip():
            continue

        municipalities.append({
            "name": row.municipality,
            "document_count": row.document_count,
            "avg_confidence": round(float(row.avg_confidence), 2) if row.avg_confidence else None,
            "latest_document": row.latest_document.isoformat() if row.latest_document else None,
        })

    category = await session.get(Category, category_id) if category_id else None

    return {
        "category": category.name if category else "Alle Kategorien",
        "category_purpose": category.purpose if category else None,
        "total_municipalities": len(municipalities),
        "municipalities": municipalities,
        "top_opportunities": municipalities[:10],
    }
