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
    """
    Legacy endpoint - location_name no longer exists on DataSource.

    DataSources are now decoupled from location data.
    Use Entity-based location queries instead.
    """
    return []


@router.get("/countries", response_model=List[dict])
async def list_extraction_countries(
    session: AsyncSession = Depends(get_session),
):
    """
    Legacy endpoint - country no longer exists on DataSource.

    DataSources are now decoupled from location data.
    Use Entity-based location queries instead.
    """
    return []


@router.get("/documents/locations", response_model=List[str])
async def list_document_locations(
    session: AsyncSession = Depends(get_session),
):
    """
    Legacy endpoint - location_name no longer exists on DataSource.

    DataSources are now decoupled from location data.
    Use Entity-based location queries instead.
    """
    return []


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=500),
    category_id: Optional[UUID] = Query(default=None),
    source_id: Optional[UUID] = Query(default=None),
    document_type: Optional[str] = Query(default=None),
    processing_status: Optional[ProcessingStatus] = Query(default=None),
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

    # Batch load sources to avoid N+1 query
    source_ids = list({doc.source_id for doc in documents if doc.source_id})
    sources_result = await session.execute(
        select(DataSource).where(DataSource.id.in_(source_ids))
    )
    sources_map = {s.id: s for s in sources_result.scalars().all()}

    items = []
    for doc in documents:
        item = DocumentResponse.model_validate(doc)
        source = sources_map.get(doc.source_id)
        item.source_name = source.name if source else None
        items.append(item)

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "query": q,
    }
