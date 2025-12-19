"""Extracted data endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import ExtractedData, Document, DataSource, Category
from app.schemas.extracted_data import (
    ExtractedDataResponse,
    ExtractedDataListResponse,
    ExtractedDataVerify,
    ExtractionStats,
)
from app.core.exceptions import NotFoundError
from .loaders import bulk_load_documents_with_sources

router = APIRouter()


@router.get("/", response_model=ExtractedDataListResponse)
async def list_extracted_data(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    category_id: Optional[UUID] = Query(default=None),
    source_id: Optional[UUID] = Query(default=None),
    extraction_type: Optional[str] = Query(default=None),
    min_confidence: float = Query(default=0, ge=0, le=1, description="Minimum confidence score filter"),
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

    # Bulk-load related data to avoid N+1 queries
    doc_ids = {ext.document_id for ext in extractions if ext.document_id}
    docs_by_id = await bulk_load_documents_with_sources(session, doc_ids)

    # Enrich with document and source info
    items = []
    for ext in extractions:
        doc = docs_by_id.get(ext.document_id)
        source = doc.source if doc else None

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
