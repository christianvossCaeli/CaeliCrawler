"""Document endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Document, DataSource, Category, ExtractedData, ProcessingStatus
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentDetailResponse,
)
from app.core.exceptions import NotFoundError
from .loaders import bulk_load_sources, bulk_load_categories

router = APIRouter()


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

    # Bulk-load related data to avoid N+1 queries
    source_ids = {doc.source_id for doc in documents if doc.source_id}
    cat_ids = {doc.category_id for doc in documents if doc.category_id}
    doc_ids = {doc.id for doc in documents}

    sources_by_id = await bulk_load_sources(session, source_ids)
    cats_by_id = await bulk_load_categories(session, cat_ids)

    # Bulk-load extraction counts in a single query
    ext_counts_result = await session.execute(
        select(ExtractedData.document_id, func.count(ExtractedData.id))
        .where(ExtractedData.document_id.in_(doc_ids))
        .group_by(ExtractedData.document_id)
    )
    ext_counts = dict(ext_counts_result.all())

    # Enrich
    items = []
    for doc in documents:
        source = sources_by_id.get(doc.source_id)
        category = cats_by_id.get(doc.category_id)
        ext_count = ext_counts.get(doc.id, 0)

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
