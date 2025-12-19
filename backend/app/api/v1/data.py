"""Public API endpoints for accessing extracted data."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, and_, or_, case as sa_case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import (
    ExtractedData,
    Document,
    DataSource,
    Category,
    ProcessingStatus,
    Location,
)
from app.schemas.extracted_data import (
    ExtractedDataResponse,
    ExtractedDataListResponse,
    ExtractedDataUpdate,
    ExtractedDataVerify,
    ExtractedDataSearchParams,
    ExtractionStats,
)
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentDetailResponse,
    DocumentSearchParams,
    DocumentStats,
)
from app.core.exceptions import NotFoundError

router = APIRouter()


@router.get("", response_model=ExtractedDataListResponse)
async def list_extracted_data(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    category_id: Optional[UUID] = Query(default=None),
    source_id: Optional[UUID] = Query(default=None),
    extraction_type: Optional[str] = Query(default=None),
    min_confidence: float = Query(default=0.7, ge=0, le=1, description="Minimum confidence score (default 0.7 for quality results)"),
    human_verified: Optional[bool] = Query(default=None),
    location_name: Optional[str] = Query(default=None, description="Filter by source location name"),
    country: Optional[str] = Query(default=None, description="Filter by source country code"),
    session: AsyncSession = Depends(get_session),
):
    """List extracted data with filters."""
    query = select(ExtractedData)

    # Track if we need to join with Document and DataSource
    needs_document_join = source_id is not None or location_name is not None or country is not None
    needs_source_join = location_name is not None or country is not None

    if needs_document_join:
        query = query.join(Document, ExtractedData.document_id == Document.id)
        if needs_source_join:
            query = query.join(DataSource, Document.source_id == DataSource.id)

    if category_id:
        query = query.where(ExtractedData.category_id == category_id)
    if source_id:
        query = query.where(Document.source_id == source_id)
    if extraction_type:
        query = query.where(ExtractedData.extraction_type == extraction_type)
    if min_confidence is not None:
        query = query.where(ExtractedData.confidence_score >= min_confidence)
    if human_verified is not None:
        query = query.where(ExtractedData.human_verified == human_verified)
    if location_name:
        query = query.where(func.lower(DataSource.location_name) == location_name.lower())
    if country:
        query = query.where(func.upper(DataSource.country) == country.upper())

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(ExtractedData.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    extractions = result.scalars().all()

    # Enrich with document and source info
    items = []
    for ext in extractions:
        doc = await session.get(Document, ext.document_id)
        source = await session.get(DataSource, doc.source_id) if doc else None

        item = ExtractedDataResponse.model_validate(ext)
        item.final_content = ext.final_content
        item.document_title = doc.title if doc else None
        item.document_url = doc.original_url if doc else None
        item.source_name = source.name if source else None
        items.append(item)

    return ExtractedDataListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.get("/stats", response_model=ExtractionStats)
async def get_extraction_stats(
    category_id: Optional[UUID] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Get extraction statistics."""
    base_query = select(ExtractedData)
    if category_id:
        base_query = base_query.where(ExtractedData.category_id == category_id)

    total = (await session.execute(
        select(func.count()).select_from(base_query.subquery())
    )).scalar()

    verified = (await session.execute(
        select(func.count()).where(
            ExtractedData.human_verified == True,
            *([ExtractedData.category_id == category_id] if category_id else [])
        )
    )).scalar()

    avg_confidence = (await session.execute(
        select(func.avg(ExtractedData.confidence_score)).where(
            *([ExtractedData.category_id == category_id] if category_id else [])
        )
    )).scalar()

    high_confidence = (await session.execute(
        select(func.count()).where(
            ExtractedData.confidence_score >= 0.8,
            *([ExtractedData.category_id == category_id] if category_id else [])
        )
    )).scalar()

    low_confidence = (await session.execute(
        select(func.count()).where(
            ExtractedData.confidence_score < 0.5,
            *([ExtractedData.category_id == category_id] if category_id else [])
        )
    )).scalar()

    # By type
    type_result = await session.execute(
        select(ExtractedData.extraction_type, func.count())
        .where(*([ExtractedData.category_id == category_id] if category_id else []))
        .group_by(ExtractedData.extraction_type)
    )
    by_type = dict(type_result.fetchall())

    # By category
    cat_result = await session.execute(
        select(Category.name, func.count())
        .join(ExtractedData, Category.id == ExtractedData.category_id)
        .group_by(Category.name)
    )
    by_category = dict(cat_result.fetchall())

    return ExtractionStats(
        total=total,
        verified=verified,
        unverified=total - verified,
        avg_confidence=float(avg_confidence) if avg_confidence else None,
        by_type=by_type,
        by_category=by_category,
        high_confidence_count=high_confidence,
        low_confidence_count=low_confidence,
    )


@router.get("/locations", response_model=List[str])
async def list_extraction_locations(
    session: AsyncSession = Depends(get_session),
):
    """Get distinct location names from sources that have extracted data."""
    result = await session.execute(
        select(DataSource.location_name)
        .distinct()
        .where(DataSource.location_name.isnot(None))
        .where(
            DataSource.id.in_(
                select(Document.source_id)
                .distinct()
                .where(
                    Document.id.in_(
                        select(ExtractedData.document_id).distinct()
                    )
                )
            )
        )
        .order_by(DataSource.location_name)
    )
    locations = [row[0] for row in result.fetchall()]
    return locations


@router.get("/countries", response_model=List[dict])
async def list_extraction_countries(
    session: AsyncSession = Depends(get_session),
):
    """Get distinct countries from sources that have extracted data."""
    from app.countries import COUNTRY_CONFIGS

    result = await session.execute(
        select(DataSource.country)
        .distinct()
        .where(DataSource.country.isnot(None))
        .where(
            DataSource.id.in_(
                select(Document.source_id)
                .distinct()
                .where(
                    Document.id.in_(
                        select(ExtractedData.document_id).distinct()
                    )
                )
            )
        )
        .order_by(DataSource.country)
    )
    countries = []
    for row in result.fetchall():
        code = row[0]
        config = COUNTRY_CONFIGS.get(code)
        countries.append({
            "code": code,
            "name": config.name_de if config else code,
        })
    return countries


@router.get("/documents/locations", response_model=List[str])
async def list_document_locations(
    session: AsyncSession = Depends(get_session),
):
    """Get distinct location names from sources that have documents."""
    result = await session.execute(
        select(DataSource.location_name)
        .distinct()
        .where(DataSource.location_name.isnot(None))
        .where(
            DataSource.id.in_(
                select(Document.source_id).distinct()
            )
        )
        .order_by(DataSource.location_name)
    )
    locations = [row[0] for row in result.fetchall()]
    return locations


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=500),
    category_id: Optional[UUID] = Query(default=None),
    source_id: Optional[UUID] = Query(default=None),
    document_type: Optional[str] = Query(default=None),
    processing_status: Optional[ProcessingStatus] = Query(default=None),
    location_name: Optional[str] = Query(default=None, description="Filter by source location name"),
    session: AsyncSession = Depends(get_session),
):
    """List documents with filters."""
    query = select(Document)

    if category_id:
        query = query.where(Document.category_id == category_id)
    if source_id:
        query = query.where(Document.source_id == source_id)
    if document_type:
        query = query.where(Document.document_type == document_type)
    if processing_status:
        query = query.where(Document.processing_status == processing_status)
    if location_name:
        # Join with DataSource to filter by location_name
        query = query.join(DataSource, Document.source_id == DataSource.id).where(
            func.lower(DataSource.location_name) == location_name.lower()
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(Document.discovered_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    documents = result.scalars().all()

    # Enrich
    items = []
    for doc in documents:
        source = await session.get(DataSource, doc.source_id)
        category = await session.get(Category, doc.category_id)

        # Count extractions
        ext_count = (await session.execute(
            select(func.count()).where(ExtractedData.document_id == doc.id)
        )).scalar()

        item = DocumentResponse.model_validate(doc)
        item.source_name = source.name if source else None
        item.category_name = category.name if category else None
        item.has_extracted_data = ext_count > 0
        item.extraction_count = ext_count
        items.append(item)

    return DocumentListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get detailed document info including extracted data."""
    document = await session.get(Document, document_id)
    if not document:
        raise NotFoundError("Document", str(document_id))

    source = await session.get(DataSource, document.source_id)
    category = await session.get(Category, document.category_id)

    # Get extractions
    ext_result = await session.execute(
        select(ExtractedData).where(ExtractedData.document_id == document_id)
    )
    extractions = ext_result.scalars().all()

    # Build response manually to avoid async relationship access issues
    response = DocumentDetailResponse(
        id=document.id,
        source_id=document.source_id,
        category_id=document.category_id,
        crawl_job_id=document.crawl_job_id,
        document_type=document.document_type,
        original_url=document.original_url,
        title=document.title,
        file_path=document.file_path,
        file_hash=document.file_hash,
        file_size=document.file_size or 0,
        page_count=document.page_count,
        processing_status=document.processing_status,
        processing_error=document.processing_error,
        discovered_at=document.discovered_at,
        downloaded_at=document.downloaded_at,
        processed_at=document.processed_at,
        document_date=document.document_date,
        raw_text=document.raw_text,
        source_name=source.name if source else None,
        category_name=category.name if category else None,
        has_extracted_data=len(extractions) > 0,
        extraction_count=len(extractions),
        extracted_data=[
            {
                "id": str(ext.id),
                "type": ext.extraction_type,
                "content": ext.final_content,
                "confidence": ext.confidence_score,
                "verified": ext.human_verified,
            }
            for ext in extractions
        ],
    )

    return response


@router.get("/search")
async def search_documents(
    q: str = Query(..., min_length=2, description="Search query"),
    category_id: Optional[UUID] = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Full-text search across documents."""
    from sqlalchemy import text

    # PostgreSQL full-text search
    query = select(Document).where(
        Document.search_vector.op("@@")(func.plainto_tsquery("german", q))
    )

    if category_id:
        query = query.where(Document.category_id == category_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(Document.discovered_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    documents = result.scalars().all()

    items = []
    for doc in documents:
        source = await session.get(DataSource, doc.source_id)
        item = DocumentResponse.model_validate(doc)
        item.source_name = source.name if source else None
        items.append(item)

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "query": q,
    }


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
    # Define the municipality expression once for consistency
    municipality_expr = ExtractedData.extracted_content["municipality"].astext
    is_relevant_expr = ExtractedData.extracted_content["is_relevant"].astext

    # Query extractions that have a municipality field and meet confidence threshold
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

    # Filter for relevant documents only
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
    """
    Get all documents for a specific municipality.

    Returns documents grouped by a municipality name extracted from AI analysis.
    """
    # Find extractions for this municipality
    query = (
        select(ExtractedData)
        .where(ExtractedData.extracted_content["municipality"].astext.ilike(f"%{municipality_name}%"))
    )

    if category_id:
        query = query.where(ExtractedData.category_id == category_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(ExtractedData.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    extractions = result.scalars().all()

    # Build response with document details
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
    only_relevant: bool = Query(default=True, description="Only include documents marked as relevant"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get aggregated intelligence report for a municipality.

    Aggregates all extracted insights by focus areas:
    - Pain points (challenges, restrictions, concerns)
    - Positive signals (opportunities, support, projects)
    - Decision makers (contacts, stakeholders)
    - Key topics and themes
    - Outreach recommendations

    By default, only includes documents marked as relevant for cleaner reports.
    """
    from collections import defaultdict

    is_relevant_expr = ExtractedData.extracted_content["is_relevant"].astext

    # Find all relevant extractions for this municipality
    query = (
        select(ExtractedData)
        .where(ExtractedData.extracted_content["municipality"].astext.ilike(f"%{municipality_name}%"))
        .where(ExtractedData.confidence_score >= min_confidence)
    )

    # Filter for relevant documents only
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

    # Get category info for context
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

        # Collect pain points (can be strings or objects with description/text)
        pain_points = content.get("pain_points", [])
        if isinstance(pain_points, list):
            for pp in pain_points:
                text = None
                pp_type = None
                severity = None
                if isinstance(pp, dict):
                    # AI returns objects with description, type, severity
                    text = pp.get("description") or pp.get("text") or pp.get("quote", "")
                    pp_type = pp.get("type")
                    severity = pp.get("severity")
                elif isinstance(pp, str):
                    text = pp

                if text and text.strip():
                    all_pain_points.append({
                        "text": text.strip(),
                        "type": pp_type,
                        "severity": severity,
                        "document_id": str(ext.document_id),
                        "confidence": ext.confidence_score,
                    })

        # Collect positive signals (can be strings or objects with description/text)
        positive_signals = content.get("positive_signals", [])
        if isinstance(positive_signals, list):
            for ps in positive_signals:
                text = None
                ps_type = None
                if isinstance(ps, dict):
                    # AI returns objects with description, type
                    text = ps.get("description") or ps.get("text") or ps.get("quote", "")
                    ps_type = ps.get("type")
                elif isinstance(ps, str):
                    text = ps

                if text and text.strip():
                    all_positive_signals.append({
                        "text": text.strip(),
                        "type": ps_type,
                        "document_id": str(ext.document_id),
                        "confidence": ext.confidence_score,
                    })

        # Collect decision makers
        decision_makers = content.get("decision_makers", [])
        if isinstance(decision_makers, list):
            for dm in decision_makers:
                if isinstance(dm, dict):
                    all_decision_makers.append({
                        **dm,
                        "document_id": str(ext.document_id),
                    })
                elif isinstance(dm, str) and dm.strip():
                    all_decision_makers.append({
                        "name": dm,
                        "document_id": str(ext.document_id),
                    })

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
        if isinstance(relevance, str):
            relevance_lower = relevance.lower()
            if relevance_lower in relevance_counts:
                relevance_counts[relevance_lower] += 1

        # Count outreach priorities
        outreach = content.get("outreach_recommendation", {})
        if isinstance(outreach, dict):
            priority = outreach.get("priority", "")
            if isinstance(priority, str) and priority.lower() in outreach_priorities:
                outreach_priorities[priority.lower()] += 1

        # Count is_relevant
        if content.get("is_relevant") is True:
            relevant_count += 1

        # Extract topics/keywords from content
        for key in ["document_type", "type", "kategorie"]:
            if key in content and content[key]:
                topics[content[key]] += 1

        # Get document info
        doc = await session.get(Document, ext.document_id)
        if doc:
            document_types[doc.document_type or "Unbekannt"] += 1
            source = await session.get(DataSource, doc.source_id)
            if source:
                sources.add(source.name)

    # Collect all document IDs for lookup
    all_doc_ids = set()
    for pp in all_pain_points:
        all_doc_ids.add(pp["document_id"])
    for ps in all_positive_signals:
        all_doc_ids.add(ps["document_id"])
    for dm in all_decision_makers:
        all_doc_ids.add(dm.get("document_id"))

    # Load all documents in one query
    doc_info = {}
    if all_doc_ids:
        from uuid import UUID as PyUUID
        doc_query = select(Document).where(Document.id.in_([PyUUID(d) for d in all_doc_ids if d]))
        doc_result = await session.execute(doc_query)
        for doc in doc_result.scalars().all():
            doc_info[str(doc.id)] = {
                "id": str(doc.id),
                "title": doc.title or "Ohne Titel",
                "url": doc.original_url,
                "type": doc.document_type,
            }

    # Deduplicate and rank pain points by frequency
    pain_point_freq = defaultdict(list)
    for pp in all_pain_points:
        # Normalize text for grouping
        normalized = pp["text"].lower().strip()
        pain_point_freq[normalized].append(pp)

    ranked_pain_points = []
    for normalized, items in sorted(pain_point_freq.items(), key=lambda x: -len(x[1])):
        # Get most common type and severity from items
        types = [i.get("type") for i in items if i.get("type")]
        severities = [i.get("severity") for i in items if i.get("severity")]
        doc_ids = list(set(i["document_id"] for i in items))
        ranked_pain_points.append({
            "text": items[0]["text"],  # Original text
            "type": types[0] if types else None,
            "severity": severities[0] if severities else None,
            "frequency": len(items),
            "avg_confidence": sum(i["confidence"] or 0 for i in items) / len(items),
            "document_ids": doc_ids,
            "sources": [doc_info.get(d) for d in doc_ids if doc_info.get(d)],
        })

    # Deduplicate positive signals
    signal_freq = defaultdict(list)
    for ps in all_positive_signals:
        normalized = ps["text"].lower().strip()
        signal_freq[normalized].append(ps)

    ranked_positive_signals = []
    for normalized, items in sorted(signal_freq.items(), key=lambda x: -len(x[1])):
        # Get most common type from items
        types = [i.get("type") for i in items if i.get("type")]
        doc_ids = list(set(i["document_id"] for i in items))
        ranked_positive_signals.append({
            "text": items[0]["text"],
            "type": types[0] if types else None,
            "frequency": len(items),
            "avg_confidence": sum(i["confidence"] or 0 for i in items) / len(items),
            "document_ids": doc_ids,
            "sources": [doc_info.get(d) for d in doc_ids if doc_info.get(d)],
        })

    # Deduplicate decision makers by name
    # Filter out invalid entries (titles/organizations instead of person names)
    invalid_person_patterns = [
        "bürgermeister", "stadtverordneter", "ausschuss", "rat der stadt",
        "rat der gemeinde", "kreistag", "stadtrat", "gemeinderat", "verwaltung",
        "mayor", "council", "committee", "board"
    ]

    dm_by_name = {}
    for dm in all_decision_makers:
        # Support both "name" and "person" field names
        name = (dm.get("name") or dm.get("person") or "").strip()
        if name:
            # Skip entries where "name" is actually a title or organization
            name_lower = name.lower()
            is_invalid = any(pattern in name_lower for pattern in invalid_person_patterns)
            # Also skip if name is too short or doesn't contain a space (likely not a full name)
            is_likely_title = len(name) < 5 or (len(name.split()) == 1 and not name[0].isupper())

            if is_invalid or (is_likely_title and name_lower in invalid_person_patterns):
                continue

            if name not in dm_by_name:
                dm_by_name[name] = {
                    "name": name,
                    "role": dm.get("role", dm.get("position", "")),
                    "contact": dm.get("contact", dm.get("email", "")),
                    "statement": dm.get("statement", ""),
                    "sentiment": dm.get("sentiment", ""),
                    "document_ids": [],
                    "sources": [],
                }
            doc_id = dm.get("document_id")
            if doc_id:
                dm_by_name[name]["document_ids"].append(doc_id)
                if doc_info.get(doc_id) and doc_info[doc_id] not in dm_by_name[name]["sources"]:
                    dm_by_name[name]["sources"].append(doc_info[doc_id])

    unique_decision_makers = list(dm_by_name.values())

    # Add sources to summaries
    for summary in all_summaries:
        doc_id = summary.get("document_id")
        summary["source"] = doc_info.get(doc_id) if doc_id else None

    # Calculate overall assessment
    avg_confidence = total_confidence / len(extractions) if extractions else 0
    relevance_ratio = relevant_count / len(extractions) if extractions else 0

    # Determine overall priority
    if outreach_priorities["hoch"] > 0 or relevance_counts["hoch"] >= 2:
        overall_priority = "hoch"
    elif outreach_priorities["mittel"] > 0 or relevance_counts["mittel"] >= 2:
        overall_priority = "mittel"
    else:
        overall_priority = "niedrig"

    return {
        "municipality": municipality_name,
        "category": category.name if category else None,
        "category_purpose": category.purpose if category else None,

        # Overview
        "overview": {
            "total_documents": len(extractions),
            "relevant_documents": relevant_count,
            "relevance_ratio": round(relevance_ratio, 2),
            "avg_confidence": round(avg_confidence, 2),
            "overall_priority": overall_priority,
            "sources": list(sources),
            "document_types": dict(document_types),
        },

        # Relevance breakdown
        "relevance_breakdown": relevance_counts,
        "outreach_priorities": outreach_priorities,

        # Aggregated insights (all items, frontend handles display/pagination)
        "pain_points": ranked_pain_points,
        "positive_signals": ranked_positive_signals,
        "decision_makers": unique_decision_makers,

        # Recent summaries (top 5 by confidence)
        "top_summaries": sorted(
            all_summaries,
            key=lambda x: x["confidence"] or 0,
            reverse=True
        )[:5],

        # Topics found
        "topics": dict(topics),
    }


@router.get("/report/overview")
async def get_overview_report(
    category_id: Optional[UUID] = Query(default=None),
    min_confidence: float = Query(default=0.7, ge=0, le=1),
    only_relevant: bool = Query(default=True, description="Only include documents marked as relevant"),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    """
    Get overview report of all municipalities with key metrics.

    Returns a ranked list of municipalities by relevance and opportunity.
    By default, only includes documents marked as relevant for cleaner reports.
    """
    municipality_expr = ExtractedData.extracted_content["municipality"].astext
    is_relevant_expr = ExtractedData.extracted_content["is_relevant"].astext

    # Base query for municipalities
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

    # Filter for relevant documents only
    if only_relevant:
        query = query.where(is_relevant_expr == "true")

    query = (
        query.group_by(municipality_expr)
        .order_by(func.count(ExtractedData.id).desc())
        .limit(limit)
    )

    if category_id:
        query = query.where(ExtractedData.category_id == category_id)

    result = await session.execute(query)
    rows = result.fetchall()

    municipalities = []
    for row in rows:
        if not row.municipality or not row.municipality.strip():
            continue

        # Get detailed stats for this municipality
        detail_query = (
            select(ExtractedData)
            .where(municipality_expr == row.municipality)
            .where(ExtractedData.confidence_score >= min_confidence)
        )
        if only_relevant:
            detail_query = detail_query.where(is_relevant_expr == "true")
        if category_id:
            detail_query = detail_query.where(ExtractedData.category_id == category_id)

        detail_result = await session.execute(detail_query)
        extractions = detail_result.scalars().all()

        # Count key metrics
        relevant_count = 0
        high_priority_count = 0
        pain_point_count = 0
        positive_signal_count = 0
        decision_maker_count = 0

        for ext in extractions:
            content = ext.final_content
            if content.get("is_relevant") is True:
                relevant_count += 1

            outreach = content.get("outreach_recommendation", {})
            if isinstance(outreach, dict) and outreach.get("priority", "").lower() == "hoch":
                high_priority_count += 1

            pp = content.get("pain_points", [])
            if isinstance(pp, list):
                pain_point_count += len(pp)

            ps = content.get("positive_signals", [])
            if isinstance(ps, list):
                positive_signal_count += len(ps)

            dm = content.get("decision_makers", [])
            if isinstance(dm, list):
                decision_maker_count += len(dm)

        # Calculate opportunity score
        opportunity_score = (
            (relevant_count * 3) +
            (high_priority_count * 5) +
            (positive_signal_count * 2) +
            (decision_maker_count * 1)
        ) / max(row.document_count, 1)

        # Count data sources for this municipality/location
        source_count_query = (
            select(func.count(func.distinct(DataSource.id)))
            .where(
                or_(
                    func.lower(DataSource.location_name) == row.municipality.lower(),
                    DataSource.location_id.in_(
                        select(Location.id)
                        .where(func.lower(Location.name) == row.municipality.lower())
                    )
                )
            )
        )
        source_count_result = await session.execute(source_count_query)
        source_count = source_count_result.scalar() or 0

        municipalities.append({
            "name": row.municipality,
            "document_count": row.document_count,
            "source_count": source_count,
            "relevant_count": relevant_count,
            "high_priority_count": high_priority_count,
            "pain_point_count": pain_point_count,
            "positive_signal_count": positive_signal_count,
            "decision_maker_count": decision_maker_count,
            "avg_confidence": round(float(row.avg_confidence), 2) if row.avg_confidence else None,
            "opportunity_score": round(opportunity_score, 2),
            "latest_document": row.latest_document.isoformat() if row.latest_document else None,
        })

    # Sort by opportunity score
    municipalities.sort(key=lambda x: x["opportunity_score"], reverse=True)

    # Get category info
    category = None
    if category_id:
        category = await session.get(Category, category_id)

    return {
        "category": category.name if category else "Alle Kategorien",
        "category_purpose": category.purpose if category else None,
        "total_municipalities": len(municipalities),
        "municipalities": municipalities,
        "top_opportunities": municipalities[:10],
    }


@router.put("/extracted/{extraction_id}/verify", response_model=ExtractedDataResponse)
async def verify_extraction(
    extraction_id: UUID,
    data: ExtractedDataVerify,
    session: AsyncSession = Depends(get_session),
):
    """Verify extracted data and optionally apply corrections."""
    from datetime import datetime

    extraction = await session.get(ExtractedData, extraction_id)
    if not extraction:
        raise NotFoundError("Extracted Data", str(extraction_id))

    extraction.human_verified = data.verified
    extraction.verified_by = data.verified_by
    extraction.verified_at = datetime.utcnow()

    if data.corrections:
        extraction.human_corrections = data.corrections

    await session.commit()
    await session.refresh(extraction)

    return ExtractedDataResponse.model_validate(extraction)


@router.get("/history/municipalities")
async def get_municipality_history(
    municipality_name: Optional[str] = Query(default=None),
    category_id: Optional[UUID] = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
):
    """
    Get historical development of results per municipality over time.

    Shows how document counts and key metrics evolved over crawl cycles.
    """
    from datetime import datetime, timedelta
    from sqlalchemy import cast, Date

    start_date = datetime.utcnow() - timedelta(days=days)

    # Base query
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

        # Group by municipality
        from collections import defaultdict
        by_municipality = defaultdict(list)

        for row in rows:
            if row.municipality and row.municipality.strip():
                by_municipality[row.municipality].append({
                    "date": row.date.isoformat(),
                    "count": row.document_count,
                })

        # Calculate totals and trends per municipality
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

        # Sort by recent activity
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
    """
    Get history of crawl jobs with results summary.

    Shows documents found, processed, and key metrics per crawl.
    """
    from app.models.crawl_job import CrawlJob, JobStatus

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

        # Count documents from this crawl
        doc_count = (await session.execute(
            select(func.count()).where(Document.crawl_job_id == job.id)
        )).scalar()

        # Count extractions from documents of this crawl
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
            "errors": job.error_log[:3] if job.error_log else [],  # Last 3 errors
        })

    return {
        "total_crawls": len(crawls),
        "crawls": crawls,
    }
