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
    search: Optional[str] = Query(default=None, description="Search in title and URL"),
    discovered_from: Optional[str] = Query(default=None, description="Filter by discovered date from (YYYY-MM-DD)"),
    discovered_to: Optional[str] = Query(default=None, description="Filter by discovered date to (YYYY-MM-DD)"),
    sort_by: Optional[str] = Query(default=None, description="Sort by field (title, document_type, processing_status, source_name, discovered_at, file_size)"),
    sort_order: Optional[str] = Query(default="desc", description="Sort order (asc, desc)"),
    session: AsyncSession = Depends(get_session),
):
    """List documents with filters and sorting."""
    query = select(Document)

    if category_id:
        query = query.where(Document.category_id == category_id)
    if source_id:
        query = query.where(Document.source_id == source_id)
    if document_type:
        query = query.where(Document.document_type == document_type)
    if processing_status:
        query = query.where(Document.processing_status == processing_status)
    if search:
        # Escape SQL wildcards to prevent injection
        safe_search = search.replace('%', '\\%').replace('_', '\\_')
        search_pattern = f"%{safe_search}%"
        query = query.where(
            (Document.title.ilike(search_pattern, escape='\\')) |
            (Document.original_url.ilike(search_pattern, escape='\\'))
        )
    if discovered_from:
        query = query.where(Document.discovered_at >= discovered_from)
    if discovered_to:
        query = query.where(Document.discovered_at <= discovered_to + " 23:59:59")

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Handle sorting
    sort_desc = sort_order == "desc"
    sort_column_map = {
        "title": Document.title,
        "document_type": Document.document_type,
        "processing_status": Document.processing_status,
        "discovered_at": Document.discovered_at,
        "file_size": Document.file_size,
    }

    if sort_by and sort_by in sort_column_map:
        order_col = sort_column_map[sort_by]
        if sort_desc:
            query = query.order_by(order_col.desc().nulls_last(), Document.discovered_at.desc())
        else:
            query = query.order_by(order_col.asc().nulls_last(), Document.discovered_at.desc())
    elif sort_by == "source_name":
        # Join with DataSource for source_name sorting
        query = query.outerjoin(DataSource, Document.source_id == DataSource.id)
        if sort_desc:
            query = query.order_by(DataSource.name.desc().nulls_last(), Document.discovered_at.desc())
        else:
            query = query.order_by(DataSource.name.asc().nulls_last(), Document.discovered_at.desc())
    elif sort_by == "category_name":
        # Join with Category for category_name sorting
        query = query.outerjoin(Category, Document.category_id == Category.id)
        if sort_desc:
            query = query.order_by(Category.name.desc().nulls_last(), Document.discovered_at.desc())
        else:
            query = query.order_by(Category.name.asc().nulls_last(), Document.discovered_at.desc())
    else:
        # Default sorting
        query = query.order_by(Document.discovered_at.desc())

    # Paginate
    query = query.offset((page - 1) * per_page).limit(per_page)
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
