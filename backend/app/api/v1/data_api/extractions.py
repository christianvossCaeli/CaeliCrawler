"""Extracted data endpoints."""

from datetime import UTC, date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_editor
from app.core.exceptions import NotFoundError
from app.database import get_session
from app.models import Category, Document, ExtractedData
from app.models.audit_log import AuditAction
from app.models.user import User
from app.services.audit_service import create_audit_log
from app.schemas.extracted_data import (
    DisplayColumn,
    DisplayFieldsConfig,
    ExtractedDataBulkReject,
    ExtractedDataBulkRejectResponse,
    ExtractedDataBulkVerify,
    ExtractedDataBulkVerifyResponse,
    ExtractedDataListResponse,
    ExtractedDataReject,
    ExtractedDataRejectResponse,
    ExtractedDataResponse,
    ExtractedDataVerify,
    ExtractionStats,
)
from app.schemas.facet_value import FacetValueResponse

from .loaders import bulk_load_documents_with_sources

router = APIRouter()


def apply_extraction_filters(
    query,
    *,
    document_id: UUID | None = None,
    category_id: UUID | None = None,
    source_id: UUID | None = None,
    extraction_type: str | None = None,
    min_confidence: float | None = None,
    human_verified: bool | None = None,
    include_rejected: bool = False,
    created_from: date | None = None,
    created_to: date | None = None,
    search: str | None = None,
):
    """Apply shared filters for extracted data queries."""
    if source_id is not None or search:
        query = query.join(Document, ExtractedData.document_id == Document.id)

    if document_id:
        query = query.where(ExtractedData.document_id == document_id)
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
    # Filter out rejected extractions unless explicitly included
    if not include_rejected:
        query = query.where(ExtractedData.is_rejected.is_(False))
    if created_from:
        query = query.where(func.date(ExtractedData.created_at) >= created_from)
    if created_to:
        query = query.where(func.date(ExtractedData.created_at) <= created_to)
    if search:
        safe_search = search.replace("%", "\\%").replace("_", "\\_")
        search_pattern = f"%{safe_search}%"
        search_query = func.plainto_tsquery("german", search)
        query = query.where(
            or_(
                Document.title.ilike(search_pattern, escape="\\"),
                Document.original_url.ilike(search_pattern, escape="\\"),
                ExtractedData.search_vector.op("@@")(search_query),
                ExtractedData.extracted_content.cast(String).ilike(search_pattern, escape="\\"),
                ExtractedData.human_corrections.cast(String).ilike(search_pattern, escape="\\"),
                ExtractedData.entity_references.cast(String).ilike(search_pattern, escape="\\"),
            )
        )

    return query


@router.get("/", response_model=ExtractedDataListResponse)
async def list_extracted_data(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    document_id: UUID | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    source_id: UUID | None = Query(default=None),
    extraction_type: str | None = Query(default=None),
    min_confidence: float | None = Query(default=None, ge=0, le=1, description="Minimum confidence score filter"),
    human_verified: bool | None = Query(default=None),
    include_rejected: bool = Query(default=False, description="Include rejected extractions in the list"),
    created_from: date | None = Query(default=None, description="Filter by created date from (YYYY-MM-DD)"),
    created_to: date | None = Query(default=None, description="Filter by created date to (YYYY-MM-DD)"),
    search: str | None = Query(
        default=None,
        description="Search in document title, URL, extracted content, corrections, and entity references",
    ),
    sort_by: str | None = Query(default="created_at", description="Field to sort by"),
    sort_order: str | None = Query(default="desc", description="Sort order: asc or desc"),
    session: AsyncSession = Depends(get_session),
):
    """List extracted data with filters."""
    query = apply_extraction_filters(
        select(ExtractedData),
        document_id=document_id,
        category_id=category_id,
        source_id=source_id,
        extraction_type=extraction_type,
        min_confidence=min_confidence,
        human_verified=human_verified,
        include_rejected=include_rejected,
        created_from=created_from,
        created_to=created_to,
        search=search,
    )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Dynamic sorting
    # entity_count uses JSONB array length for sorting
    entity_count_expr = func.coalesce(func.jsonb_array_length(ExtractedData.entity_references), 0)
    sortable_fields = {
        "created_at": ExtractedData.created_at,
        "confidence_score": ExtractedData.confidence_score,
        "relevance_score": ExtractedData.relevance_score,
        "extraction_type": ExtractedData.extraction_type,
        "human_verified": ExtractedData.human_verified,
        "entity_count": entity_count_expr,
    }
    sort_column = sortable_fields.get(sort_by, ExtractedData.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc().nulls_last())
    else:
        query = query.order_by(sort_column.desc().nulls_last())

    # Paginate
    query = query.offset((page - 1) * per_page).limit(per_page)
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

        # Build dict with all fields including computed ones
        ext_dict = {
            "id": ext.id,
            "document_id": ext.document_id,
            "category_id": ext.category_id,
            "extraction_type": ext.extraction_type,
            "extracted_content": ext.extracted_content,
            "confidence_score": ext.confidence_score,
            "ai_model_used": ext.ai_model_used,
            "ai_prompt_version": ext.ai_prompt_version,
            "tokens_used": ext.tokens_used,
            "human_verified": ext.human_verified,
            "human_corrections": ext.human_corrections,
            "verified_by": ext.verified_by,
            "verified_at": ext.verified_at,
            # Rejection fields
            "is_rejected": ext.is_rejected,
            "rejected_by": ext.rejected_by,
            "rejected_at": ext.rejected_at,
            "rejection_reason": ext.rejection_reason,
            "relevance_score": ext.relevance_score,
            "created_at": ext.created_at,
            "updated_at": ext.updated_at,
            "entity_references": ext.entity_references,
            "primary_entity_id": ext.primary_entity_id,
            # Computed fields
            "final_content": ext.final_content,
            "document_title": doc.title if doc else None,
            "document_url": doc.original_url if doc else None,
            "source_name": source.name if source else None,
        }
        items.append(ExtractedDataResponse.model_validate(ext_dict))

    return ExtractedDataListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.get("/stats", response_model=ExtractionStats)
async def get_extraction_stats(
    document_id: UUID | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    source_id: UUID | None = Query(default=None),
    extraction_type: str | None = Query(default=None),
    min_confidence: float | None = Query(default=None, ge=0, le=1, description="Minimum confidence score filter"),
    human_verified: bool | None = Query(default=None),
    include_rejected: bool = Query(default=False, description="Include rejected extractions in stats"),
    created_from: date | None = Query(default=None, description="Filter by created date from (YYYY-MM-DD)"),
    created_to: date | None = Query(default=None, description="Filter by created date to (YYYY-MM-DD)"),
    search: str | None = Query(
        default=None,
        description="Search in document title, URL, extracted content, corrections, and entity references",
    ),
    session: AsyncSession = Depends(get_session),
):
    """Get extraction statistics."""
    base_query = apply_extraction_filters(
        select(ExtractedData),
        document_id=document_id,
        category_id=category_id,
        source_id=source_id,
        extraction_type=extraction_type,
        min_confidence=min_confidence,
        human_verified=human_verified,
        include_rejected=include_rejected,
        created_from=created_from,
        created_to=created_to,
        search=search,
    )
    base_subquery = base_query.subquery()

    total = (await session.execute(select(func.count()).select_from(base_subquery))).scalar()

    verified = (
        await session.execute(
            select(func.count()).select_from(base_subquery).where(base_subquery.c.human_verified.is_(True))
        )
    ).scalar()

    avg_confidence = (
        await session.execute(select(func.avg(base_subquery.c.confidence_score)).select_from(base_subquery))
    ).scalar()

    high_confidence = (
        await session.execute(
            select(func.count()).select_from(base_subquery).where(base_subquery.c.confidence_score >= 0.8)
        )
    ).scalar()

    low_confidence = (
        await session.execute(
            select(func.count()).select_from(base_subquery).where(base_subquery.c.confidence_score < 0.5)
        )
    ).scalar()

    # By type
    type_result = await session.execute(
        select(base_subquery.c.extraction_type, func.count())
        .select_from(base_subquery)
        .group_by(base_subquery.c.extraction_type)
    )
    by_type = dict(type_result.fetchall())

    # By category
    cat_result = await session.execute(
        select(Category.name, func.count())
        .select_from(base_subquery)
        .join(Category, Category.id == base_subquery.c.category_id)
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


@router.get("/stats/unverified-count")
async def get_unverified_count(
    session: AsyncSession = Depends(get_session),
):
    """Get only the count of unverified extractions (optimized for badge display)."""
    count = (
        await session.execute(
            select(func.count()).select_from(ExtractedData).where(ExtractedData.human_verified.is_(False))
        )
    ).scalar() or 0

    return {"unverified": count}


@router.put("/extracted/{extraction_id}/verify", response_model=ExtractedDataResponse)
async def verify_extraction(
    extraction_id: UUID,
    data: ExtractedDataVerify,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    """Verify extracted data and optionally apply corrections."""
    from datetime import datetime

    extraction = await session.get(ExtractedData, extraction_id)
    if not extraction:
        raise NotFoundError("Extracted Data", str(extraction_id))

    extraction.human_verified = data.verified
    if data.verified:
        verifier = current_user.full_name or current_user.email or str(current_user.id)
        extraction.verified_by = verifier
        extraction.verified_at = datetime.now(UTC)
    else:
        extraction.verified_by = None
        extraction.verified_at = None

    if data.corrections:
        extraction.human_corrections = data.corrections

    await create_audit_log(
        session=session,
        action=AuditAction.VERIFY if data.verified else AuditAction.UPDATE,
        entity_type="ExtractedData",
        entity_id=extraction_id,
        entity_name=f"extraction {extraction_id}",
        user=current_user,
    )

    await session.commit()
    await session.refresh(extraction)

    return ExtractedDataResponse.model_validate(extraction)


@router.put("/extracted/{extraction_id}/reject", response_model=ExtractedDataRejectResponse)
async def reject_extraction(
    extraction_id: UUID,
    data: ExtractedDataReject,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    """
    Reject extracted data and optionally deactivate related facet values.

    When cascade_to_facets is True (default):
    - All FacetValues with source_document_id matching the extraction's document_id
      will have is_active set to False
    - Already human_verified or human_corrected FacetValues will NOT be deactivated (protected)

    Returns the updated extraction along with counts of deactivated and protected facets.
    """
    from datetime import datetime

    from sqlalchemy.orm import selectinload

    from app.models.facet_value import FacetValue

    extraction = await session.get(ExtractedData, extraction_id)
    if not extraction:
        raise NotFoundError("Extracted Data", str(extraction_id))

    deactivated_count = 0
    protected_count = 0

    if data.rejected:
        # Set rejection status
        rejector = current_user.full_name or current_user.email or str(current_user.id)
        extraction.is_rejected = True
        extraction.rejected_by = rejector
        extraction.rejected_at = datetime.now(UTC)
        extraction.rejection_reason = data.reason
        # Clear verification if rejecting
        extraction.human_verified = False
        extraction.verified_by = None
        extraction.verified_at = None

        # Cascade to facet values if requested
        if data.cascade_to_facets:
            # Find all FacetValues from this document that are still active
            facet_query = (
                select(FacetValue)
                .where(
                    FacetValue.source_document_id == extraction.document_id,
                    FacetValue.is_active.is_(True),
                )
                .options(selectinload(FacetValue.entity))
            )
            result = await session.execute(facet_query)
            facet_values = result.scalars().all()

            for fv in facet_values:
                # Protect human-verified or human-corrected facets
                if fv.human_verified or fv.human_corrections:
                    protected_count += 1
                else:
                    fv.is_active = False
                    deactivated_count += 1
    else:
        # Unreject - clear rejection status
        extraction.is_rejected = False
        extraction.rejected_by = None
        extraction.rejected_at = None
        extraction.rejection_reason = None

    await create_audit_log(
        session=session,
        action=AuditAction.DELETE if data.rejected else AuditAction.UPDATE,
        entity_type="ExtractedData",
        entity_id=extraction_id,
        entity_name=f"extraction {'rejected' if data.rejected else 'unrejected'}",
        user=current_user,
    )

    await session.commit()
    await session.refresh(extraction)

    # Build response with document info
    doc = extraction.document
    source = doc.source if doc else None

    ext_response = ExtractedDataResponse.model_validate(
        {
            "id": extraction.id,
            "document_id": extraction.document_id,
            "category_id": extraction.category_id,
            "extraction_type": extraction.extraction_type,
            "extracted_content": extraction.extracted_content,
            "confidence_score": extraction.confidence_score,
            "ai_model_used": extraction.ai_model_used,
            "ai_prompt_version": extraction.ai_prompt_version,
            "tokens_used": extraction.tokens_used,
            "human_verified": extraction.human_verified,
            "human_corrections": extraction.human_corrections,
            "verified_by": extraction.verified_by,
            "verified_at": extraction.verified_at,
            "is_rejected": extraction.is_rejected,
            "rejected_by": extraction.rejected_by,
            "rejected_at": extraction.rejected_at,
            "rejection_reason": extraction.rejection_reason,
            "relevance_score": extraction.relevance_score,
            "created_at": extraction.created_at,
            "updated_at": extraction.updated_at,
            "entity_references": extraction.entity_references,
            "primary_entity_id": extraction.primary_entity_id,
            "final_content": extraction.final_content,
            "document_title": doc.title if doc else None,
            "document_url": doc.original_url if doc else None,
            "source_name": source.name if source else None,
        }
    )

    return ExtractedDataRejectResponse(
        extraction=ext_response,
        deactivated_facets_count=deactivated_count,
        protected_facets_count=protected_count,
    )


@router.put("/extracted/bulk-verify", response_model=ExtractedDataBulkVerifyResponse)
async def bulk_verify_extractions(
    data: ExtractedDataBulkVerify,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    """
    Bulk verify multiple extracted data entries.

    Verifies up to 100 extractions in a single request.
    Returns the count of successfully verified and failed entries.
    """
    from datetime import datetime

    verified_ids: list[UUID] = []
    failed_ids: list[UUID] = []

    verifier = current_user.full_name or current_user.email or str(current_user.id)
    now = datetime.now(UTC)

    for extraction_id in data.ids:
        extraction = await session.get(ExtractedData, extraction_id)
        if not extraction:
            failed_ids.append(extraction_id)
            continue

        # Skip already verified
        if extraction.human_verified:
            verified_ids.append(extraction_id)
            continue

        try:
            extraction.human_verified = True
            extraction.verified_by = verifier
            extraction.verified_at = now
            verified_ids.append(extraction_id)
        except Exception:
            failed_ids.append(extraction_id)

    if verified_ids:
        await create_audit_log(
            session=session,
            action=AuditAction.VERIFY,
            entity_type="ExtractedData",
            entity_id=None,
            entity_name=f"bulk verify ({len(verified_ids)} extractions)",
            user=current_user,
        )

    await session.commit()

    return ExtractedDataBulkVerifyResponse(
        verified_ids=verified_ids,
        failed_ids=failed_ids,
        verified_count=len(verified_ids),
        failed_count=len(failed_ids),
    )


@router.put("/extracted/bulk-reject", response_model=ExtractedDataBulkRejectResponse)
async def bulk_reject_extractions(
    data: ExtractedDataBulkReject,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    """
    Bulk reject multiple extracted data entries.

    Rejects up to 100 extractions in a single request.
    Optionally cascades to deactivate related facet values.
    """
    from datetime import datetime

    from sqlalchemy.orm import selectinload

    from app.models.facet_value import FacetValue

    rejected_ids: list[UUID] = []
    failed_ids: list[UUID] = []
    total_deactivated = 0
    total_protected = 0

    rejector = current_user.full_name or current_user.email or str(current_user.id)
    now = datetime.now(UTC)

    for extraction_id in data.ids:
        extraction = await session.get(ExtractedData, extraction_id)
        if not extraction:
            failed_ids.append(extraction_id)
            continue

        # Skip already rejected
        if extraction.is_rejected:
            rejected_ids.append(extraction_id)
            continue

        try:
            extraction.is_rejected = True
            extraction.rejected_by = rejector
            extraction.rejected_at = now
            extraction.human_verified = False
            extraction.verified_by = None
            extraction.verified_at = None

            # Cascade to facet values if requested
            if data.cascade_to_facets:
                facet_query = (
                    select(FacetValue)
                    .where(
                        FacetValue.source_document_id == extraction.document_id,
                        FacetValue.is_active.is_(True),
                    )
                    .options(selectinload(FacetValue.entity))
                )
                result = await session.execute(facet_query)
                facet_values = result.scalars().all()

                for fv in facet_values:
                    if fv.human_verified or fv.human_corrections:
                        total_protected += 1
                    else:
                        fv.is_active = False
                        total_deactivated += 1

            rejected_ids.append(extraction_id)
        except Exception:
            failed_ids.append(extraction_id)

    if rejected_ids:
        await create_audit_log(
            session=session,
            action=AuditAction.DELETE,
            entity_type="ExtractedData",
            entity_id=None,
            entity_name=f"bulk reject ({len(rejected_ids)} extractions)",
            user=current_user,
        )

    await session.commit()

    return ExtractedDataBulkRejectResponse(
        rejected_ids=rejected_ids,
        failed_ids=failed_ids,
        rejected_count=len(rejected_ids),
        failed_count=len(failed_ids),
        total_deactivated_facets=total_deactivated,
        total_protected_facets=total_protected,
    )


@router.get("/by-entity/{entity_id}", response_model=ExtractedDataListResponse)
async def get_extractions_by_entity(
    entity_id: UUID,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """
    Get extracted data that references a specific entity.

    Searches in both primary_entity_id and entity_references JSONB field.
    """
    # Build query to find extractions referencing this entity
    # Either via primary_entity_id or in entity_references array
    entity_id_str = str(entity_id)

    query = (
        select(ExtractedData)
        .where(
            or_(
                ExtractedData.primary_entity_id == entity_id,
                # JSONB containment: check if entity_id is in any entity_references entry
                ExtractedData.entity_references.op("@>")([{"entity_id": entity_id_str}]),
            )
        )
        .order_by(ExtractedData.created_at.desc())
    )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    # Paginate
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    extractions = result.scalars().all()

    # Bulk-load related data
    doc_ids = {ext.document_id for ext in extractions if ext.document_id}
    docs_by_id = await bulk_load_documents_with_sources(session, doc_ids)

    # Enrich with document and source info
    items = []
    for ext in extractions:
        doc = docs_by_id.get(ext.document_id)
        source = doc.source if doc else None

        ext_dict = {
            "id": ext.id,
            "document_id": ext.document_id,
            "category_id": ext.category_id,
            "extraction_type": ext.extraction_type,
            "extracted_content": ext.extracted_content,
            "confidence_score": ext.confidence_score,
            "ai_model_used": ext.ai_model_used,
            "ai_prompt_version": ext.ai_prompt_version,
            "tokens_used": ext.tokens_used,
            "human_verified": ext.human_verified,
            "human_corrections": ext.human_corrections,
            "verified_by": ext.verified_by,
            "verified_at": ext.verified_at,
            # Rejection fields
            "is_rejected": ext.is_rejected,
            "rejected_by": ext.rejected_by,
            "rejected_at": ext.rejected_at,
            "rejection_reason": ext.rejection_reason,
            "relevance_score": ext.relevance_score,
            "created_at": ext.created_at,
            "updated_at": ext.updated_at,
            "entity_references": ext.entity_references,
            "primary_entity_id": ext.primary_entity_id,
            "final_content": ext.final_content,
            "document_title": doc.title if doc else None,
            "document_url": doc.original_url if doc else None,
            "source_name": source.name if source else None,
        }
        items.append(ExtractedDataResponse.model_validate(ext_dict))

    return ExtractedDataListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.get("/display-config", response_model=DisplayFieldsConfig)
async def get_global_display_config(
    session: AsyncSession = Depends(get_session),
):
    """
    Get global display configuration for the results view without category filter.

    Analyzes existing entity_references in extracted_data to determine
    which entity type columns to show.
    """
    # Query distinct entity types from entity_references JSONB
    # Uses PostgreSQL JSONB array element extraction
    entity_types_query = (
        select(func.jsonb_array_elements(ExtractedData.entity_references).op("->>")("entity_type").label("entity_type"))
        .where(
            ExtractedData.entity_references.isnot(None), func.jsonb_array_length(ExtractedData.entity_references) > 0
        )
        .distinct()
        .limit(10)
    )

    result = await session.execute(entity_types_query)
    entity_types = [row.entity_type for row in result if row.entity_type]

    # Build columns
    columns = [
        DisplayColumn(key="document", label="Dokument", type="document_link", width="220px"),
    ]

    entity_ref_cols = []
    label_map = {
        "territorial-entity": "Kommune",
        "person": "Person",
        "organization": "Organisation",
    }

    for entity_type in entity_types:
        label = label_map.get(entity_type, entity_type.replace("-", " ").title())
        columns.append(
            DisplayColumn(
                key=f"entity_references.{entity_type}",
                label=label,
                type="entity_link",
                width="150px",
            )
        )
        entity_ref_cols.append(entity_type)

    columns.extend(
        [
            DisplayColumn(key="confidence_score", label="Konfidenz", type="confidence", width="110px"),
            DisplayColumn(key="relevance_score", label="Relevanz", type="confidence", width="110px"),
            DisplayColumn(key="human_verified", label="Geprüft", type="boolean", width="80px"),
            DisplayColumn(key="created_at", label="Erfasst", type="date", width="100px"),
        ]
    )

    return DisplayFieldsConfig(
        columns=columns,
        entity_reference_columns=entity_ref_cols,
    )


@router.get("/display-config/{category_id}", response_model=DisplayFieldsConfig)
async def get_category_display_config(
    category_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """
    Get display configuration for a category's results view.

    Returns the configured columns for displaying extraction results.
    If no custom configuration exists, returns a default configuration.
    """
    category = await session.get(Category, category_id)
    if not category:
        raise NotFoundError("Category", str(category_id))

    # If category has custom display_fields config, use it
    if category.display_fields and category.display_fields.get("columns"):
        columns = [DisplayColumn(**col) for col in category.display_fields.get("columns", [])]
        entity_ref_cols = category.display_fields.get("entity_reference_columns", [])
        return DisplayFieldsConfig(
            columns=columns,
            entity_reference_columns=entity_ref_cols,
        )

    # Build default config based on category's entity_reference_config
    columns = [
        DisplayColumn(key="document", label="Dokument", type="document_link", width="220px"),
    ]

    # Add entity reference columns from config
    entity_ref_cols = []
    if category.entity_reference_config:
        entity_types = category.entity_reference_config.get("entity_types", [])
        for entity_type in entity_types:
            # Map entity type to human-readable label
            label_map = {
                "territorial-entity": "Kommune",
                "person": "Person",
                "organization": "Organisation",
            }
            label = label_map.get(entity_type, entity_type.replace("-", " ").title())
            columns.append(
                DisplayColumn(
                    key=f"entity_references.{entity_type}",
                    label=label,
                    type="entity_link",
                    width="150px",
                )
            )
            entity_ref_cols.append(entity_type)

    # Add standard columns
    columns.extend(
        [
            DisplayColumn(key="confidence_score", label="Konfidenz", type="confidence", width="110px"),
            DisplayColumn(key="relevance_score", label="Relevanz", type="confidence", width="110px"),
            DisplayColumn(key="human_verified", label="Geprüft", type="boolean", width="80px"),
            DisplayColumn(key="created_at", label="Erfasst", type="date", width="100px"),
        ]
    )

    return DisplayFieldsConfig(
        columns=columns,
        entity_reference_columns=entity_ref_cols,
    )


@router.get("/extracted/{extraction_id}/facets", response_model=list[FacetValueResponse])
async def get_extraction_facets(
    extraction_id: UUID,
    include_inactive: bool = Query(default=False, description="Include inactive facets"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get facet values that were extracted from this extraction's source document.

    This retrieves all FacetValues where source_document_id matches the extraction's
    document_id. Use include_inactive=true to also see deactivated facets.
    """
    from sqlalchemy.orm import selectinload

    from app.models.entity import Entity
    from app.models.facet_type import FacetType
    from app.models.facet_value import FacetValue

    # Get the extraction
    extraction = await session.get(ExtractedData, extraction_id)
    if not extraction:
        raise NotFoundError("Extracted Data", str(extraction_id))

    # Build query for facet values from this document
    query = (
        select(FacetValue)
        .where(FacetValue.source_document_id == extraction.document_id)
        .options(
            selectinload(FacetValue.entity),
            selectinload(FacetValue.facet_type),
            selectinload(FacetValue.category),
            selectinload(FacetValue.source_document),
            selectinload(FacetValue.target_entity).selectinload(Entity.entity_type),
        )
        .order_by(FacetValue.created_at.desc())
    )

    # Filter by active status unless including inactive
    if not include_inactive:
        query = query.where(FacetValue.is_active.is_(True))

    result = await session.execute(query)
    facet_values = result.scalars().all()

    # Build response items
    items = []
    for fv in facet_values:
        entity = fv.entity
        facet_type = fv.facet_type
        category = fv.category
        doc = fv.source_document
        target_entity = fv.target_entity

        items.append(
            FacetValueResponse(
                id=fv.id,
                entity_id=fv.entity_id,
                facet_type_id=fv.facet_type_id,
                category_id=fv.category_id,
                source_document_id=fv.source_document_id,
                value=fv.value,
                text_representation=fv.text_representation,
                event_date=fv.event_date,
                valid_from=fv.valid_from,
                valid_until=fv.valid_until,
                source_type=fv.source_type,
                source_url=fv.source_url,
                confidence_score=fv.confidence_score,
                ai_model_used=fv.ai_model_used,
                human_verified=fv.human_verified,
                verified_by=fv.verified_by,
                verified_at=fv.verified_at,
                human_corrections=fv.human_corrections,
                occurrence_count=fv.occurrence_count,
                first_seen=fv.first_seen,
                last_seen=fv.last_seen,
                is_active=fv.is_active,
                created_at=fv.created_at,
                updated_at=fv.updated_at,
                # Nested info
                entity_name=entity.name if entity else None,
                facet_type_slug=facet_type.slug if facet_type else None,
                facet_type_name=facet_type.name if facet_type else None,
                category_name=category.name if category else None,
                document_title=doc.title if doc else None,
                document_url=doc.original_url if doc else None,
                # Target entity info
                target_entity_name=target_entity.name if target_entity else None,
                target_entity_slug=target_entity.slug if target_entity else None,
                target_entity_type_slug=(
                    target_entity.entity_type.slug
                    if target_entity and target_entity.entity_type
                    else None
                ),
                target_entity_type_icon=(
                    target_entity.entity_type.icon
                    if target_entity and target_entity.entity_type
                    else None
                ),
                target_entity_type_color=(
                    target_entity.entity_type.color
                    if target_entity and target_entity.entity_type
                    else None
                ),
            )
        )

    return items
