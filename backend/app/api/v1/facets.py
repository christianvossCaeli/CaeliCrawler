"""API endpoints for Facet Type and Facet Value management."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import (
    FacetType, FacetValue, Entity, EntityType, Category, Document,
    TimeFilter,
)
from app.schemas.facet_type import (
    FacetTypeCreate,
    FacetTypeUpdate,
    FacetTypeResponse,
    FacetTypeListResponse,
    FacetTypeSchemaGenerateRequest,
    FacetTypeSchemaGenerateResponse,
    generate_slug,
)
from app.schemas.facet_value import (
    FacetValueCreate,
    FacetValueUpdate,
    FacetValueResponse,
    FacetValueListResponse,
    FacetValueAggregated,
    EntityFacetsSummary,
)
from app.schemas.common import MessageResponse
from app.core.exceptions import NotFoundError, ConflictError

router = APIRouter()


# ============================================================================
# FacetType Endpoints
# ============================================================================


@router.get("/types", response_model=FacetTypeListResponse)
async def list_facet_types(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    is_active: Optional[bool] = Query(default=None),
    ai_extraction_enabled: Optional[bool] = Query(default=None),
    is_time_based: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """List all facet types with pagination."""
    query = select(FacetType)

    if is_active is not None:
        query = query.where(FacetType.is_active == is_active)
    if ai_extraction_enabled is not None:
        query = query.where(FacetType.ai_extraction_enabled == ai_extraction_enabled)
    if is_time_based is not None:
        query = query.where(FacetType.is_time_based == is_time_based)
    if search:
        query = query.where(
            FacetType.name.ilike(f"%{search}%") |
            FacetType.slug.ilike(f"%{search}%")
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(FacetType.display_order, FacetType.name).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    facet_types = result.scalars().all()

    # Get value counts
    items = []
    for ft in facet_types:
        value_count = (await session.execute(
            select(func.count()).where(FacetValue.facet_type_id == ft.id)
        )).scalar()

        item = FacetTypeResponse.model_validate(ft)
        item.value_count = value_count
        items.append(item)

    return FacetTypeListResponse(items=items, total=total)


@router.post("/types", response_model=FacetTypeResponse, status_code=201)
async def create_facet_type(
    data: FacetTypeCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new facet type."""
    # Generate slug if not provided
    slug = data.slug or generate_slug(data.name)

    # Check for duplicate
    existing = await session.execute(
        select(FacetType).where(
            (FacetType.name == data.name) | (FacetType.slug == slug)
        )
    )
    if existing.scalar():
        raise ConflictError(
            "Facet Type already exists",
            detail=f"A facet type with name '{data.name}' or slug '{slug}' already exists",
        )

    facet_type = FacetType(
        name=data.name,
        name_plural=data.name_plural,
        slug=slug,
        description=data.description,
        value_type=data.value_type,
        value_schema=data.value_schema,
        applicable_entity_type_slugs=data.applicable_entity_type_slugs,
        icon=data.icon,
        color=data.color,
        display_order=data.display_order,
        aggregation_method=data.aggregation_method,
        deduplication_fields=data.deduplication_fields,
        is_time_based=data.is_time_based,
        time_field_path=data.time_field_path,
        default_time_filter=data.default_time_filter,
        ai_extraction_enabled=data.ai_extraction_enabled,
        ai_extraction_prompt=data.ai_extraction_prompt,
        is_active=data.is_active,
        is_system=False,
    )
    session.add(facet_type)
    await session.commit()
    await session.refresh(facet_type)

    return FacetTypeResponse.model_validate(facet_type)


@router.get("/types/{facet_type_id}", response_model=FacetTypeResponse)
async def get_facet_type(
    facet_type_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a single facet type by ID."""
    facet_type = await session.get(FacetType, facet_type_id)
    if not facet_type:
        raise NotFoundError("FacetType", str(facet_type_id))

    value_count = (await session.execute(
        select(func.count()).where(FacetValue.facet_type_id == facet_type.id)
    )).scalar()

    response = FacetTypeResponse.model_validate(facet_type)
    response.value_count = value_count

    return response


@router.get("/types/by-slug/{slug}", response_model=FacetTypeResponse)
async def get_facet_type_by_slug(
    slug: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a single facet type by slug."""
    result = await session.execute(
        select(FacetType).where(FacetType.slug == slug)
    )
    facet_type = result.scalar()
    if not facet_type:
        raise NotFoundError("FacetType", slug)

    value_count = (await session.execute(
        select(func.count()).where(FacetValue.facet_type_id == facet_type.id)
    )).scalar()

    response = FacetTypeResponse.model_validate(facet_type)
    response.value_count = value_count

    return response


@router.post("/types/generate-schema", response_model=FacetTypeSchemaGenerateResponse)
async def generate_facet_type_schema(
    data: FacetTypeSchemaGenerateRequest,
):
    """
    Generate facet type schema and configuration using AI.

    Takes the facet name, description, and applicable entity types as input
    and generates:
    - JSON Schema for the value structure
    - Recommended value type
    - Deduplication fields
    - Time-based settings if applicable
    - AI extraction prompt
    - Suggested icon and color
    """
    from services.ai_service import AIService

    ai_service = AIService()

    entity_context = ""
    if data.applicable_entity_types:
        entity_context = f"\nDieser Facet-Typ wird für folgende Entity-Typen verwendet: {', '.join(data.applicable_entity_types)}"

    system_prompt = """Du bist ein Experte für Datenmodellierung und JSON Schema Design.
Deine Aufgabe ist es, ein passendes Schema und Konfiguration für einen neuen Facet-Typ zu erstellen.

Ein Facet-Typ definiert eine Art von Information, die zu Entities (wie Gemeinden, Personen, Organisationen) erfasst werden kann.
Beispiele für Facet-Typen: "Pain Point" (Probleme/Herausforderungen), "Kontakt" (Kontaktpersonen), "Event" (Termine/Veranstaltungen).

Beachte folgende Richtlinien:
1. Das JSON Schema sollte alle relevanten Felder für diesen Informationstyp enthalten
2. Verwende deutsche Feldnamen und Beschreibungen
3. Wähle einen passenden Werttyp: "text" für einfache Texte, "structured" für komplexe Objekte, "list" für Listen
4. Bei zeitbezogenen Facets (Events, Termine) setze is_time_based=true und gib den Pfad zum Datumsfeld an
5. Definiere Deduplikationsfelder um Duplikate zu erkennen
6. Erstelle einen AI-Extraktions-Prompt der beschreibt, wie diese Information aus Dokumenten extrahiert werden soll
7. Wähle ein passendes Material Design Icon (mdi-*) und eine Farbe

Antworte im JSON-Format."""

    user_prompt = f"""Erstelle ein Schema und Konfiguration für folgenden Facet-Typ:

Name: {data.name}
Plural: {data.name_plural or data.name + 's'}
Beschreibung: {data.description or 'Keine Beschreibung angegeben'}{entity_context}

Generiere ein JSON mit folgender Struktur:
{{
  "value_type": "structured|text|list",
  "value_schema": {{ ... JSON Schema ... }},
  "deduplication_fields": ["feld1", "feld2"],
  "is_time_based": true|false,
  "time_field_path": "datum" oder null,
  "ai_extraction_prompt": "Prompt für KI-Extraktion...",
  "icon": "mdi-icon-name",
  "color": "#hexcolor"
}}"""

    try:
        result = await ai_service.analyze_custom(
            text="",  # No document text needed
            prompt=user_prompt,
            system_context=system_prompt,
        )

        # Parse the AI response
        generated = result.extracted_data if hasattr(result, 'extracted_data') else {}

        return FacetTypeSchemaGenerateResponse(
            value_type=generated.get("value_type", "structured"),
            value_schema=generated.get("value_schema"),
            deduplication_fields=generated.get("deduplication_fields", []),
            is_time_based=generated.get("is_time_based", False),
            time_field_path=generated.get("time_field_path"),
            ai_extraction_prompt=generated.get("ai_extraction_prompt"),
            icon=generated.get("icon", "mdi-tag"),
            color=generated.get("color", "#607D8B"),
        )
    except Exception as e:
        # Return sensible defaults on error
        import structlog
        logger = structlog.get_logger()
        logger.error("Schema generation failed", error=str(e))

        return FacetTypeSchemaGenerateResponse(
            value_type="structured",
            value_schema={
                "type": "object",
                "properties": {
                    "beschreibung": {"type": "string", "description": "Beschreibung"},
                },
                "required": ["beschreibung"],
            },
            deduplication_fields=["beschreibung"],
            is_time_based=False,
            ai_extraction_prompt=f"Extrahiere alle {data.name} Informationen aus dem Dokument.",
            icon="mdi-tag",
            color="#607D8B",
        )
    finally:
        await ai_service.close()


@router.put("/types/{facet_type_id}", response_model=FacetTypeResponse)
async def update_facet_type(
    facet_type_id: UUID,
    data: FacetTypeUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update a facet type."""
    facet_type = await session.get(FacetType, facet_type_id)
    if not facet_type:
        raise NotFoundError("FacetType", str(facet_type_id))

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(facet_type, field, value)

    await session.commit()
    await session.refresh(facet_type)

    return FacetTypeResponse.model_validate(facet_type)


@router.delete("/types/{facet_type_id}", response_model=MessageResponse)
async def delete_facet_type(
    facet_type_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Delete a facet type."""
    facet_type = await session.get(FacetType, facet_type_id)
    if not facet_type:
        raise NotFoundError("FacetType", str(facet_type_id))

    if facet_type.is_system:
        raise ConflictError(
            "Cannot delete system facet type",
            detail=f"Facet type '{facet_type.name}' is a system type and cannot be deleted",
        )

    # Check for existing values
    value_count = (await session.execute(
        select(func.count()).where(FacetValue.facet_type_id == facet_type.id)
    )).scalar()

    if value_count > 0:
        raise ConflictError(
            "Cannot delete facet type with existing values",
            detail=f"Facet type '{facet_type.name}' has {value_count} values. Delete them first.",
        )

    await session.delete(facet_type)
    await session.commit()

    return MessageResponse(message=f"Facet type '{facet_type.name}' deleted successfully")


# ============================================================================
# FacetValue Endpoints
# ============================================================================


@router.get("/values", response_model=FacetValueListResponse)
async def list_facet_values(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    entity_id: Optional[UUID] = Query(default=None),
    facet_type_id: Optional[UUID] = Query(default=None),
    facet_type_slug: Optional[str] = Query(default=None),
    category_id: Optional[UUID] = Query(default=None),
    min_confidence: float = Query(default=0.0, ge=0, le=1),
    human_verified: Optional[bool] = Query(default=None),
    time_filter: Optional[str] = Query(default=None, description="future_only, past_only, all"),
    is_active: Optional[bool] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """List facet values with filters."""
    query = select(FacetValue)

    if entity_id:
        query = query.where(FacetValue.entity_id == entity_id)
    if facet_type_id:
        query = query.where(FacetValue.facet_type_id == facet_type_id)
    elif facet_type_slug:
        subq = select(FacetType.id).where(FacetType.slug == facet_type_slug)
        query = query.where(FacetValue.facet_type_id.in_(subq))
    if category_id:
        query = query.where(FacetValue.category_id == category_id)
    if min_confidence > 0:
        query = query.where(FacetValue.confidence_score >= min_confidence)
    if human_verified is not None:
        query = query.where(FacetValue.human_verified == human_verified)
    if is_active is not None:
        query = query.where(FacetValue.is_active == is_active)

    # Time-based filtering
    now = datetime.utcnow()
    if time_filter == "future_only":
        query = query.where(
            or_(
                FacetValue.event_date >= now,
                FacetValue.valid_until >= now,
                and_(FacetValue.event_date.is_(None), FacetValue.valid_until.is_(None))
            )
        )
    elif time_filter == "past_only":
        query = query.where(
            or_(
                FacetValue.event_date < now,
                FacetValue.valid_until < now
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(FacetValue.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    values = result.scalars().all()

    # Enrich with related info
    items = []
    for fv in values:
        entity = await session.get(Entity, fv.entity_id)
        facet_type = await session.get(FacetType, fv.facet_type_id)
        category = await session.get(Category, fv.category_id) if fv.category_id else None
        document = await session.get(Document, fv.source_document_id) if fv.source_document_id else None

        item = FacetValueResponse.model_validate(fv)
        item.entity_name = entity.name if entity else None
        item.facet_type_name = facet_type.name if facet_type else None
        item.facet_type_slug = facet_type.slug if facet_type else None
        item.category_name = category.name if category else None
        item.document_title = document.title if document else None
        item.document_url = document.original_url if document else None
        items.append(item)

    return FacetValueListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.post("/values", response_model=FacetValueResponse, status_code=201)
async def create_facet_value(
    data: FacetValueCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new facet value."""
    # Verify entity exists
    entity = await session.get(Entity, data.entity_id)
    if not entity:
        raise NotFoundError("Entity", str(data.entity_id))

    # Verify facet type exists
    facet_type = await session.get(FacetType, data.facet_type_id)
    if not facet_type:
        raise NotFoundError("FacetType", str(data.facet_type_id))

    # Build text representation
    text_repr = _build_text_representation(data.value)

    facet_value = FacetValue(
        entity_id=data.entity_id,
        facet_type_id=data.facet_type_id,
        category_id=data.category_id,
        value=data.value,
        text_representation=text_repr,
        event_date=data.event_date,
        valid_from=data.valid_from,
        valid_until=data.valid_until,
        source_document_id=data.source_document_id,
        source_url=data.source_url,
        confidence_score=data.confidence_score,
        ai_model_used=data.ai_model_used,
        is_active=data.is_active,
    )
    session.add(facet_value)
    await session.commit()
    await session.refresh(facet_value)

    item = FacetValueResponse.model_validate(facet_value)
    item.entity_name = entity.name
    item.facet_type_name = facet_type.name
    item.facet_type_slug = facet_type.slug

    return item


def _build_text_representation(value: Any) -> str:
    """Build searchable text from value."""
    if isinstance(value, str):
        return value
    elif isinstance(value, dict):
        parts = []
        for k, v in value.items():
            if isinstance(v, str):
                parts.append(v)
            elif isinstance(v, list):
                parts.extend(str(item) for item in v)
        return " ".join(parts)
    elif isinstance(value, list):
        return " ".join(str(item) for item in value)
    else:
        return str(value)


@router.get("/values/{facet_value_id}", response_model=FacetValueResponse)
async def get_facet_value(
    facet_value_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a single facet value by ID."""
    fv = await session.get(FacetValue, facet_value_id)
    if not fv:
        raise NotFoundError("FacetValue", str(facet_value_id))

    entity = await session.get(Entity, fv.entity_id)
    facet_type = await session.get(FacetType, fv.facet_type_id)
    category = await session.get(Category, fv.category_id) if fv.category_id else None
    document = await session.get(Document, fv.source_document_id) if fv.source_document_id else None

    response = FacetValueResponse.model_validate(fv)
    response.entity_name = entity.name if entity else None
    response.facet_type_name = facet_type.name if facet_type else None
    response.facet_type_slug = facet_type.slug if facet_type else None
    response.category_name = category.name if category else None
    response.document_title = document.title if document else None
    response.document_url = document.original_url if document else None

    return response


@router.put("/values/{facet_value_id}", response_model=FacetValueResponse)
async def update_facet_value(
    facet_value_id: UUID,
    data: FacetValueUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update a facet value."""
    fv = await session.get(FacetValue, facet_value_id)
    if not fv:
        raise NotFoundError("FacetValue", str(facet_value_id))

    # Update fields
    update_data = data.model_dump(exclude_unset=True)

    # Rebuild text representation if value changes
    if "value" in update_data:
        update_data["text_representation"] = _build_text_representation(update_data["value"])

    for field, value in update_data.items():
        setattr(fv, field, value)

    await session.commit()
    await session.refresh(fv)

    facet_type = await session.get(FacetType, fv.facet_type_id)

    response = FacetValueResponse.model_validate(fv)
    response.facet_type_name = facet_type.name if facet_type else None
    response.facet_type_slug = facet_type.slug if facet_type else None

    return response


@router.put("/values/{facet_value_id}/verify", response_model=FacetValueResponse)
async def verify_facet_value(
    facet_value_id: UUID,
    verified: bool = Query(default=True),
    verified_by: Optional[str] = Query(default=None),
    corrections: Optional[Dict[str, Any]] = None,
    session: AsyncSession = Depends(get_session),
):
    """Verify a facet value and optionally apply corrections."""
    fv = await session.get(FacetValue, facet_value_id)
    if not fv:
        raise NotFoundError("FacetValue", str(facet_value_id))

    fv.human_verified = verified
    fv.verified_by = verified_by
    fv.verified_at = datetime.utcnow()

    if corrections:
        fv.human_corrections = corrections

    await session.commit()
    await session.refresh(fv)

    return FacetValueResponse.model_validate(fv)


@router.delete("/values/{facet_value_id}", response_model=MessageResponse)
async def delete_facet_value(
    facet_value_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Delete a facet value."""
    fv = await session.get(FacetValue, facet_value_id)
    if not fv:
        raise NotFoundError("FacetValue", str(facet_value_id))

    await session.delete(fv)
    await session.commit()

    return MessageResponse(message="Facet value deleted successfully")


# ============================================================================
# Entity Facets Summary
# ============================================================================


@router.get("/entity/{entity_id}/summary", response_model=EntityFacetsSummary)
async def get_entity_facets_summary(
    entity_id: UUID,
    category_id: Optional[UUID] = Query(default=None),
    time_filter: Optional[str] = Query(default=None),
    min_confidence: float = Query(default=0.0, ge=0, le=1),
    session: AsyncSession = Depends(get_session),
):
    """Get summary of all facets for an entity."""
    entity = await session.get(Entity, entity_id)
    if not entity:
        raise NotFoundError("Entity", str(entity_id))

    entity_type = await session.get(EntityType, entity.entity_type_id)
    entity_type_slug = entity_type.slug if entity_type else None

    # Build subquery for applicable facet types based on entity type
    # A FacetType is applicable if:
    # 1. applicable_entity_type_slugs is empty (applies to all entity types), OR
    # 2. applicable_entity_type_slugs contains the current entity's type slug
    if entity_type_slug:
        applicable_facet_types_subq = select(FacetType.id).where(
            or_(
                FacetType.applicable_entity_type_slugs == [],  # Empty = applies to all
                FacetType.applicable_entity_type_slugs.any(entity_type_slug)  # Contains this type
            )
        )
    else:
        # If entity has no type, only show facets that apply to all
        applicable_facet_types_subq = select(FacetType.id).where(
            FacetType.applicable_entity_type_slugs == []
        )

    # Base query for facet values - only include values from applicable facet types
    query = select(FacetValue).where(
        FacetValue.entity_id == entity_id,
        FacetValue.is_active == True,
        FacetValue.confidence_score >= min_confidence,
        FacetValue.facet_type_id.in_(applicable_facet_types_subq),
    )

    if category_id:
        query = query.where(FacetValue.category_id == category_id)

    # Apply time filter
    now = datetime.utcnow()
    if time_filter == "future_only":
        query = query.where(
            or_(
                FacetValue.event_date >= now,
                FacetValue.valid_until >= now,
                and_(FacetValue.event_date.is_(None), FacetValue.valid_until.is_(None))
            )
        )
    elif time_filter == "past_only":
        query = query.where(
            or_(
                FacetValue.event_date < now,
                FacetValue.valid_until < now
            )
        )

    result = await session.execute(query)
    values = result.scalars().all()

    # Group values by facet type
    by_facet_type: Dict[UUID, List[FacetValue]] = {}
    for fv in values:
        if fv.facet_type_id not in by_facet_type:
            by_facet_type[fv.facet_type_id] = []
        by_facet_type[fv.facet_type_id].append(fv)

    # Load ALL applicable facet types for this entity type (including those without values)
    if entity_type_slug:
        applicable_types_query = select(FacetType).where(
            FacetType.is_active == True,
            or_(
                FacetType.applicable_entity_type_slugs == [],  # Empty = applies to all
                FacetType.applicable_entity_type_slugs.any(entity_type_slug)  # Contains this type
            )
        ).order_by(FacetType.display_order, FacetType.name)
    else:
        applicable_types_query = select(FacetType).where(
            FacetType.is_active == True,
            FacetType.applicable_entity_type_slugs == []
        ).order_by(FacetType.display_order, FacetType.name)

    applicable_types_result = await session.execute(applicable_types_query)
    applicable_facet_types = applicable_types_result.scalars().all()

    # Build aggregated facets for ALL applicable types (even without values)
    facets_by_type = []
    total_values = 0
    verified_count = 0

    for facet_type in applicable_facet_types:
        type_values = by_facet_type.get(facet_type.id, [])

        if type_values:
            avg_confidence = sum(v.confidence_score or 0 for v in type_values) / len(type_values)
            type_verified_count = sum(1 for v in type_values if v.human_verified)
            latest_value = max((v.created_at for v in type_values), default=None)
            sample_values = [
                {
                    "id": str(v.id),
                    "value": v.value,
                    "text": v.text_representation,
                    "confidence": v.confidence_score,
                }
                for v in sorted(type_values, key=lambda x: x.confidence_score or 0, reverse=True)[:3]
            ]
        else:
            avg_confidence = 0.0
            type_verified_count = 0
            latest_value = None
            sample_values = []

        facets_by_type.append(FacetValueAggregated(
            facet_type_id=facet_type.id,
            facet_type_slug=facet_type.slug,
            facet_type_name=facet_type.name,
            facet_type_icon=facet_type.icon,
            facet_type_color=facet_type.color,
            display_order=facet_type.display_order or 0,
            value_count=len(type_values),
            verified_count=type_verified_count,
            avg_confidence=round(avg_confidence, 2),
            latest_value=latest_value,
            sample_values=sample_values,
        ))

        total_values += len(type_values)
        verified_count += type_verified_count

    # Sort by display order
    facets_by_type.sort(key=lambda x: x.display_order)

    return EntityFacetsSummary(
        entity_id=entity.id,
        entity_name=entity.name,
        entity_type_slug=entity_type.slug if entity_type else None,
        total_facet_values=total_values,
        verified_count=verified_count,
        facet_type_count=len(facets_by_type),
        facets_by_type=facets_by_type,
    )
