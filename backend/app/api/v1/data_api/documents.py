"""Document endpoints."""

from datetime import datetime, time
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.database import get_session
from app.models import Category, DataSource, Document, ExtractedData, ProcessingStatus
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentProcessingStatsResponse,
    DocumentResponse,
)

from .loaders import bulk_load_categories, bulk_load_sources

router = APIRouter()


def apply_document_filters(
    query,
    category_id: UUID | None,
    source_id: UUID | None,
    document_type: str | None,
    processing_status: ProcessingStatus | None,
    search: str | None,
    discovered_from: str | None,
    discovered_to: str | None,
):
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
        safe_search = search.replace("%", "\\%").replace("_", "\\_")
        search_pattern = f"%{safe_search}%"
        query = query.where(
            (Document.title.ilike(search_pattern, escape="\\"))
            | (Document.original_url.ilike(search_pattern, escape="\\"))
        )
    if discovered_from:
        # Parse date string to datetime for proper comparison
        from_date = datetime.strptime(discovered_from, "%Y-%m-%d")
        query = query.where(Document.discovered_at >= from_date)
    if discovered_to:
        # Parse date string and set to end of day (23:59:59)
        to_date = datetime.combine(datetime.strptime(discovered_to, "%Y-%m-%d").date(), time(23, 59, 59))
        query = query.where(Document.discovered_at <= to_date)
    return query


@router.get("/locations", response_model=list[str])
async def list_extraction_locations(
    session: AsyncSession = Depends(get_session),
):
    """
    Legacy endpoint - location_name no longer exists on DataSource.

    DataSources are now decoupled from location data.
    Use Entity-based location queries instead.
    """
    return []


@router.get("/countries", response_model=list[dict])
async def list_extraction_countries(
    session: AsyncSession = Depends(get_session),
):
    """
    Legacy endpoint - country no longer exists on DataSource.

    DataSources are now decoupled from location data.
    Use Entity-based location queries instead.
    """
    return []


@router.get("/documents/locations", response_model=list[str])
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
    category_id: UUID | None = Query(default=None),
    source_id: UUID | None = Query(default=None),
    document_type: str | None = Query(default=None),
    processing_status: ProcessingStatus | None = Query(default=None),
    search: str | None = Query(default=None, description="Search in title and URL"),
    discovered_from: str | None = Query(default=None, description="Filter by discovered date from (YYYY-MM-DD)"),
    discovered_to: str | None = Query(default=None, description="Filter by discovered date to (YYYY-MM-DD)"),
    sort_by: str | None = Query(
        default=None,
        description="Sort by field (title, document_type, processing_status, source_name, discovered_at, file_size)",
    ),
    sort_order: str | None = Query(default="desc", description="Sort order (asc, desc)"),
    session: AsyncSession = Depends(get_session),
):
    """List documents with filters and sorting."""
    query = select(Document)

    query = apply_document_filters(
        query,
        category_id,
        source_id,
        document_type,
        processing_status,
        search,
        discovered_from,
        discovered_to,
    )

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


@router.get("/documents/stats", response_model=DocumentProcessingStatsResponse)
async def get_document_stats(
    category_id: UUID | None = Query(default=None),
    source_id: UUID | None = Query(default=None),
    document_type: str | None = Query(default=None),
    search: str | None = Query(default=None, description="Search in title and URL"),
    discovered_from: str | None = Query(default=None, description="Filter by discovered date from (YYYY-MM-DD)"),
    discovered_to: str | None = Query(default=None, description="Filter by discovered date to (YYYY-MM-DD)"),
    session: AsyncSession = Depends(get_session),
):
    """Return document counts grouped by processing status."""
    filtered_query = apply_document_filters(
        select(Document),
        category_id,
        source_id,
        document_type,
        None,
        search,
        discovered_from,
        discovered_to,
    ).subquery()

    total = (await session.execute(select(func.count()).select_from(filtered_query))).scalar() or 0

    status_result = await session.execute(
        select(filtered_query.c.processing_status, func.count()).group_by(filtered_query.c.processing_status)
    )
    raw_counts = {row[0].value if row[0] else "UNKNOWN": row[1] for row in status_result.fetchall()}

    by_status = {status.value: raw_counts.get(status.value, 0) for status in ProcessingStatus}

    return DocumentProcessingStatsResponse(
        total=total,
        by_status=by_status,
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
    ext_result = await session.execute(select(ExtractedData).where(ExtractedData.document_id == document_id))
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
    category_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Full-text search across documents."""
    # PostgreSQL full-text search
    query = select(Document).where(Document.search_vector.op("@@")(func.plainto_tsquery("german", q)))

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
    sources_result = await session.execute(select(DataSource).where(DataSource.id.in_(source_ids)))
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


@router.post("/documents/{document_id}/analyze-pages")
async def analyze_additional_pages(
    document_id: UUID,
    page_numbers: list[int] | None = Query(
        default=None, description="Specific page numbers to analyze. If empty, analyzes remaining relevant pages."
    ),
    max_pages: int = Query(default=10, ge=1, le=50, description="Maximum pages to analyze"),
    session: AsyncSession = Depends(get_session),
):
    """
    Analyze additional pages of a document.

    Use this endpoint to:
    - Analyze remaining relevant pages when page_analysis_status is "has_more"
    - Analyze specific pages manually

    Returns the triggered task ID.
    """
    document = await session.get(Document, document_id)
    if not document:
        raise NotFoundError("Document", str(document_id))

    # Determine which pages to analyze
    if page_numbers:
        # User specified specific pages
        pages_to_analyze = page_numbers[:max_pages]
    elif document.relevant_pages and document.analyzed_pages:
        # Analyze remaining relevant pages
        analyzed = set(document.analyzed_pages)
        remaining = [p for p in document.relevant_pages if p not in analyzed]
        pages_to_analyze = remaining[:max_pages]
    elif document.relevant_pages:
        # First analysis
        pages_to_analyze = document.relevant_pages[:max_pages]
    else:
        return {
            "status": "error",
            "message": "No relevant pages to analyze. Use /full-analysis for documents without keywords.",
        }

    if not pages_to_analyze:
        return {
            "status": "complete",
            "message": "All relevant pages have been analyzed.",
            "analyzed_pages": document.analyzed_pages,
        }

    # Trigger analysis task
    from workers.ai_tasks import analyze_document

    task = analyze_document.delay(str(document_id), skip_relevance_check=True)

    return {
        "status": "started",
        "task_id": str(task.id),
        "pages_to_analyze": pages_to_analyze,
        "message": f"Analysis started for {len(pages_to_analyze)} pages",
    }


@router.post("/documents/{document_id}/full-analysis")
async def trigger_full_analysis(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """
    Trigger full document analysis (ignoring page filtering).

    Use this endpoint for:
    - Documents with page_analysis_status = "needs_review" (no keywords found)
    - Manual override to analyze entire document

    This bypasses page-based filtering and analyzes the full document.
    """
    document = await session.get(Document, document_id)
    if not document:
        raise NotFoundError("Document", str(document_id))

    if not document.raw_text:
        return {
            "status": "error",
            "message": "Document has no text content to analyze.",
        }

    # Reset page analysis status to force full analysis
    document.page_analysis_status = "pending"
    document.relevant_pages = None
    document.analyzed_pages = None
    document.page_analysis_note = "Manuelle Vollanalyse gestartet"
    document.processing_status = ProcessingStatus.ANALYZING

    await session.commit()

    # Trigger analysis task
    from workers.ai_tasks import analyze_document

    task = analyze_document.delay(str(document_id), skip_relevance_check=True)

    return {
        "status": "started",
        "task_id": str(task.id),
        "message": "Full document analysis started",
    }


@router.get("/documents/{document_id}/page-analysis")
async def get_page_analysis_status(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """
    Get the page analysis status for a document.

    Returns information about:
    - Which pages are relevant (have keyword matches)
    - Which pages have been analyzed
    - Whether more pages need analysis
    """
    document = await session.get(Document, document_id)
    if not document:
        raise NotFoundError("Document", str(document_id))

    analyzed_count = len(document.analyzed_pages) if document.analyzed_pages else 0
    relevant_count = document.total_relevant_pages or 0

    return {
        "document_id": str(document_id),
        "page_count": document.page_count,
        "page_analysis_status": document.page_analysis_status,
        "relevant_pages": document.relevant_pages,
        "analyzed_pages": document.analyzed_pages,
        "total_relevant_pages": relevant_count,
        "pages_remaining": max(0, relevant_count - analyzed_count),
        "page_analysis_note": document.page_analysis_note,
        "can_analyze_more": (
            document.page_analysis_status in ("has_more", "partial") and analyzed_count < relevant_count
        ),
        "needs_manual_review": document.page_analysis_status == "needs_review",
    }
