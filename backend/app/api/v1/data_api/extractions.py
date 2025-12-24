"""Extracted data endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import ExtractedData, Document, Category
from app.schemas.extracted_data import (
    ExtractedDataResponse,
    ExtractedDataListResponse,
    ExtractedDataVerify,
    ExtractionStats,
    DisplayFieldsConfig,
    DisplayColumn,
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
    sort_by: Optional[str] = Query(default="created_at", description="Field to sort by"),
    sort_order: Optional[str] = Query(default="desc", description="Sort order: asc or desc"),
    session: AsyncSession = Depends(get_session),
):
    """List extracted data with filters."""
    query = select(ExtractedData)

    # Join with Document if filtering by source_id
    if source_id is not None:
        query = query.join(Document, ExtractedData.document_id == Document.id)

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

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Dynamic sorting
    sortable_fields = {
        "created_at": ExtractedData.created_at,
        "confidence_score": ExtractedData.confidence_score,
        "relevance_score": ExtractedData.relevance_score,
        "extraction_type": ExtractedData.extraction_type,
        "human_verified": ExtractedData.human_verified,
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
            ExtractedData.human_verified.is_(True),
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
    from datetime import datetime, timezone

    extraction = await session.get(ExtractedData, extraction_id)
    if not extraction:
        raise NotFoundError("Extracted Data", str(extraction_id))

    extraction.human_verified = data.verified
    extraction.verified_by = data.verified_by
    extraction.verified_at = datetime.now(timezone.utc)

    if data.corrections:
        extraction.human_corrections = data.corrections

    await session.commit()
    await session.refresh(extraction)

    return ExtractedDataResponse.model_validate(extraction)


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
        columns = [
            DisplayColumn(**col)
            for col in category.display_fields.get("columns", [])
        ]
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
            columns.append(DisplayColumn(
                key=f"entity_references.{entity_type}",
                label=label,
                type="entity_link",
                width="150px",
            ))
            entity_ref_cols.append(entity_type)

    # Add standard columns
    columns.extend([
        DisplayColumn(key="confidence_score", label="Konfidenz", type="confidence", width="110px"),
        DisplayColumn(key="relevance_score", label="Relevanz", type="confidence", width="110px"),
        DisplayColumn(key="human_verified", label="Geprüft", type="boolean", width="80px"),
        DisplayColumn(key="created_at", label="Erfasst", type="date", width="100px"),
    ])

    return DisplayFieldsConfig(
        columns=columns,
        entity_reference_columns=entity_ref_cols,
    )
