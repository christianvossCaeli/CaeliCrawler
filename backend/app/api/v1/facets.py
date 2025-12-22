"""API endpoints for Facet Type and Facet Value management."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import (
    FacetType, FacetValue, FacetValueHistory, Entity, EntityType, Category, Document,
    TimeFilter, AnalysisTemplate,
)
from app.models.facet_value import FacetValueSourceType
from app.schemas.facet_value_history import (
    HistoryDataPointCreate,
    HistoryDataPointUpdate,
    HistoryDataPointResponse,
    HistoryBulkImport,
    HistoryBulkImportResponse,
    EntityHistoryResponse,
    AggregatedHistoryResponse,
)
from services.facet_history_service import FacetHistoryService
from app.models.user import User
from app.core.deps import get_current_user, require_editor
from app.core.audit import AuditContext
from app.models.audit_log import AuditAction
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
    FacetValueSearchResult,
    FacetValueSearchResponse,
)
from app.schemas.common import MessageResponse
from app.core.exceptions import NotFoundError, ConflictError
from app.core.validators import validate_entity_type_slugs
from app.core.cache import facet_type_cache
from app.utils.text import build_text_representation

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
        query = query.where(FacetType.is_active.is_(is_active))
    if ai_extraction_enabled is not None:
        query = query.where(FacetType.ai_extraction_enabled.is_(ai_extraction_enabled))
    if is_time_based is not None:
        query = query.where(FacetType.is_time_based.is_(is_time_based))
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
    facet_types = list(result.scalars().all())

    # Get all value counts in a single query to avoid N+1
    facet_type_ids = [ft.id for ft in facet_types]
    value_counts_map: Dict[UUID, int] = {}

    if facet_type_ids:
        value_counts_query = (
            select(FacetValue.facet_type_id, func.count(FacetValue.id))
            .where(FacetValue.facet_type_id.in_(facet_type_ids))
            .group_by(FacetValue.facet_type_id)
        )
        value_counts_result = await session.execute(value_counts_query)
        for facet_type_id, count in value_counts_result.all():
            value_counts_map[facet_type_id] = count

    # Build response items
    items = []
    for ft in facet_types:
        item = FacetTypeResponse.model_validate(ft)
        item.value_count = value_counts_map.get(ft.id, 0)
        items.append(item)

    pages = (total + per_page - 1) // per_page if total > 0 else 1
    return FacetTypeListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.post("/types", response_model=FacetTypeResponse, status_code=201)
async def create_facet_type(
    data: FacetTypeCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Create a new facet type using the unified write executor."""
    from services.smart_query.write_executor import execute_facet_type_create

    # Prepare data for unified executor
    facet_type_data = {
        "name": data.name,
        "name_plural": data.name_plural,
        "slug": data.slug or generate_slug(data.name),
        "description": data.description,
        "value_type": data.value_type,
        "value_schema": data.value_schema,
        "applicable_entity_type_slugs": data.applicable_entity_type_slugs,
        "icon": data.icon,
        "color": data.color,
        "display_order": data.display_order,
        "aggregation_method": data.aggregation_method,
        "deduplication_fields": data.deduplication_fields,
        "is_time_based": data.is_time_based,
        "time_field_path": data.time_field_path,
        "default_time_filter": data.default_time_filter,
        "ai_extraction_enabled": data.ai_extraction_enabled,
        "ai_extraction_prompt": data.ai_extraction_prompt,
        "is_active": data.is_active,
    }

    # Use unified executor
    result = await execute_facet_type_create(session, facet_type_data)

    if not result.get("success"):
        raise ConflictError(
            "Facet Type creation failed",
            detail=result.get("message", "Unknown error"),
        )

    # Audit log
    async with AuditContext(session, current_user, request) as audit:
        audit.track_action(
            action=AuditAction.CREATE,
            entity_type="FacetType",
            entity_id=result["facet_type_id"],
            entity_name=data.name,
            changes={
                "name": data.name,
                "slug": data.slug or facet_type_data["slug"],
                "value_type": data.value_type,
                "is_time_based": data.is_time_based,
                "ai_extraction_enabled": data.ai_extraction_enabled,
                "applicable_entity_type_slugs": data.applicable_entity_type_slugs,
            },
        )
        await session.commit()

    # Fetch the created facet type
    facet_type = await session.get(FacetType, result["facet_type_id"])
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
    """Get a single facet type by slug (cached)."""
    cache_key = f"facet_type:slug:{slug}"

    # Try cache first
    cached = facet_type_cache.get(cache_key)
    if cached:
        # Still need to get fresh value_count
        value_count = (await session.execute(
            select(func.count()).where(FacetValue.facet_type_id == cached["id"])
        )).scalar()
        response = FacetTypeResponse(**cached)
        response.value_count = value_count
        return response

    # Fetch from database
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

    # Cache the facet type data (without value_count as it changes)
    facet_type_cache.set(cache_key, response.model_dump(exclude={"value_count"}))

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
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """Update a facet type."""
    facet_type = await session.get(FacetType, facet_type_id)
    if not facet_type:
        raise NotFoundError("FacetType", str(facet_type_id))

    # Validate applicable_entity_type_slugs if being updated
    if data.applicable_entity_type_slugs is not None and data.applicable_entity_type_slugs:
        _, invalid_slugs = await validate_entity_type_slugs(session, data.applicable_entity_type_slugs)
        if invalid_slugs:
            raise ConflictError(
                "Invalid entity type slugs",
                detail=f"The following entity type slugs do not exist: {', '.join(sorted(invalid_slugs))}",
            )

    old_slug = facet_type.slug

    # Capture old state
    old_data = {
        "name": facet_type.name,
        "slug": facet_type.slug,
        "is_active": facet_type.is_active,
        "ai_extraction_enabled": facet_type.ai_extraction_enabled,
    }

    async with AuditContext(session, current_user, request) as audit:
        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(facet_type, field, value)

        new_data = {
            "name": facet_type.name,
            "slug": facet_type.slug,
            "is_active": facet_type.is_active,
            "ai_extraction_enabled": facet_type.ai_extraction_enabled,
        }

        audit.track_update(facet_type, old_data, new_data)

        await session.commit()
        await session.refresh(facet_type)

    # Invalidate cache for old and new slugs
    facet_type_cache.delete(f"facet_type:slug:{old_slug}")
    facet_type_cache.delete(f"facet_type:slug:{facet_type.slug}")
    facet_type_cache.delete(f"facet_type:id:{facet_type_id}")

    return FacetTypeResponse.model_validate(facet_type)


@router.delete("/types/{facet_type_id}", response_model=MessageResponse)
async def delete_facet_type(
    facet_type_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
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

    # Store slug for cache invalidation before deletion
    slug = facet_type.slug

    # Clean up AnalysisTemplate facet_config references to this facet type
    analysis_templates = await session.execute(select(AnalysisTemplate))
    for template in analysis_templates.scalars():
        if template.facet_config:
            original_config = template.facet_config
            cleaned_config = [
                fc for fc in original_config
                if fc.get("facet_type_slug") != slug
            ]
            if len(cleaned_config) != len(original_config):
                template.facet_config = cleaned_config

    facet_type_name = facet_type.name

    async with AuditContext(session, current_user, request) as audit:
        audit.track_action(
            action=AuditAction.DELETE,
            entity_type="FacetType",
            entity_id=facet_type_id,
            entity_name=facet_type_name,
            changes={
                "deleted": True,
                "name": facet_type_name,
                "slug": slug,
            },
        )

        await session.delete(facet_type)
        await session.commit()

    # Invalidate cache
    facet_type_cache.delete(f"facet_type:slug:{slug}")
    facet_type_cache.delete(f"facet_type:id:{facet_type_id}")

    return MessageResponse(message=f"Facet type '{facet_type_name}' deleted successfully")


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
    search: Optional[str] = Query(
        default=None,
        description="Search in text_representation",
        min_length=2,
    ),
    time_filter: Optional[str] = Query(
        default=None,
        description="Time filter: 'future_only', 'past_only', or 'all'",
        pattern="^(future_only|past_only|all)$",
    ),
    is_active: Optional[bool] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """List facet values with filters and search."""
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
        query = query.where(FacetValue.human_verified.is_(human_verified))
    if is_active is not None:
        query = query.where(FacetValue.is_active.is_(is_active))
    if search:
        # Use PostgreSQL full-text search for better performance
        # Falls back to ILIKE if search_vector not populated
        search_query = func.plainto_tsquery("german", search)
        query = query.where(
            or_(
                FacetValue.search_vector.op("@@")(search_query),
                FacetValue.text_representation.ilike(f"%{search}%")
            )
        )

    # Time-based filtering
    now = datetime.now(timezone.utc)
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

    # Sort: verified first, then by confidence (desc), then by created_at (desc)
    # Use selectinload for eager loading of relationships
    query = query.options(
        selectinload(FacetValue.entity),
        selectinload(FacetValue.facet_type),
        selectinload(FacetValue.category),
        selectinload(FacetValue.source_document),
    ).order_by(
        FacetValue.human_verified.desc(),
        FacetValue.confidence_score.desc(),
        FacetValue.created_at.desc()
    ).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    values = result.scalars().all()

    # Build response items with enriched data from relationships
    items = []
    for fv in values:
        item = FacetValueResponse.model_validate(fv)
        item.entity_name = fv.entity.name if fv.entity else None
        item.facet_type_name = fv.facet_type.name if fv.facet_type else None
        item.facet_type_slug = fv.facet_type.slug if fv.facet_type else None
        item.category_name = fv.category.name if fv.category else None
        item.document_title = fv.source_document.title if fv.source_document else None
        item.document_url = fv.source_document.original_url if fv.source_document else None
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
    request: Request,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    """Create a new facet value. Requires Editor role."""
    # Verify entity exists
    entity = await session.get(Entity, data.entity_id)
    if not entity:
        raise NotFoundError("Entity", str(data.entity_id))

    # Verify facet type exists
    facet_type = await session.get(FacetType, data.facet_type_id)
    if not facet_type:
        raise NotFoundError("FacetType", str(data.facet_type_id))

    # Validate FacetType is applicable for this Entity's type
    if facet_type.applicable_entity_type_slugs:
        entity_type = await session.get(EntityType, entity.entity_type_id)
        entity_type_slug = entity_type.slug if entity_type else None
        if entity_type_slug and entity_type_slug not in facet_type.applicable_entity_type_slugs:
            raise ConflictError(
                "FacetType not applicable",
                detail=f"FacetType '{facet_type.name}' is not applicable for entity type '{entity_type_slug}'. "
                       f"Applicable types: {', '.join(facet_type.applicable_entity_type_slugs)}",
            )

    # Use provided text_representation or generate from value
    text_repr = data.text_representation or build_text_representation(data.value)

    async with AuditContext(session, current_user, request) as audit:
        facet_value = FacetValue(
            entity_id=data.entity_id,
            facet_type_id=data.facet_type_id,
            category_id=data.category_id,
            value=data.value,
            text_representation=text_repr,
            event_date=data.event_date,
            valid_from=data.valid_from,
            valid_until=data.valid_until,
            source_type=FacetValueSourceType(data.source_type.value) if data.source_type else FacetValueSourceType.MANUAL,
            source_document_id=data.source_document_id,
            source_url=data.source_url,
            confidence_score=data.confidence_score,
            ai_model_used=data.ai_model_used,
            is_active=data.is_active,
        )
        session.add(facet_value)
        await session.flush()

        audit.track_action(
            action=AuditAction.CREATE,
            entity_type="FacetValue",
            entity_id=facet_value.id,
            entity_name=f"{facet_type.name} for {entity.name}",
            changes={
                "entity_name": entity.name,
                "facet_type": facet_type.name,
                "text_representation": text_repr[:100] if text_repr else None,
                "source_type": data.source_type.value if data.source_type else "manual",
            },
        )

        await session.commit()
        await session.refresh(facet_value)

    item = FacetValueResponse.model_validate(facet_value)
    item.entity_name = entity.name
    item.facet_type_name = facet_type.name
    item.facet_type_slug = facet_type.slug

    return item


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
    request: Request,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    """Update a facet value."""
    fv = await session.get(FacetValue, facet_value_id)
    if not fv:
        raise NotFoundError("FacetValue", str(facet_value_id))

    async with AuditContext(session, current_user, request) as audit:
        # Update fields
        update_data = data.model_dump(exclude_unset=True)

        # Rebuild text representation if value changes
        if "value" in update_data:
            update_data["text_representation"] = build_text_representation(update_data["value"])

        for field, value in update_data.items():
            setattr(fv, field, value)

        audit.track_action(
            action=AuditAction.UPDATE,
            entity_type="FacetValue",
            entity_id=fv.id,
            entity_name=fv.text_representation[:50] if fv.text_representation else str(fv.id),
            changes={"updated_fields": list(update_data.keys())},
        )

        await session.commit()
        await session.refresh(fv)

    # Enrich response with related entity info
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


@router.put("/values/{facet_value_id}/verify", response_model=FacetValueResponse)
async def verify_facet_value(
    facet_value_id: UUID,
    verified: bool = Query(default=True),
    verified_by: Optional[str] = Query(default=None),
    corrections: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    """Verify a facet value and optionally apply corrections."""
    fv = await session.get(FacetValue, facet_value_id)
    if not fv:
        raise NotFoundError("FacetValue", str(facet_value_id))

    fv.human_verified = verified
    fv.verified_by = verified_by
    fv.verified_at = datetime.now(timezone.utc)

    if corrections:
        fv.human_corrections = corrections

    await session.commit()
    await session.refresh(fv)

    # Enrich response with related entity info
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


@router.delete("/values/{facet_value_id}", response_model=MessageResponse)
async def delete_facet_value(
    facet_value_id: UUID,
    request: Request,
    current_user: User = Depends(require_editor),
    session: AsyncSession = Depends(get_session),
):
    """Delete a facet value. Requires Editor role."""
    fv = await session.get(FacetValue, facet_value_id)
    if not fv:
        raise NotFoundError("FacetValue", str(facet_value_id))

    fv_name = fv.text_representation[:50] if fv.text_representation else str(facet_value_id)

    async with AuditContext(session, current_user, request) as audit:
        audit.track_action(
            action=AuditAction.DELETE,
            entity_type="FacetValue",
            entity_id=facet_value_id,
            entity_name=fv_name,
            changes={"deleted": True},
        )

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
    time_filter: Optional[str] = Query(
        default=None,
        description="Time filter: 'future_only', 'past_only', or 'all'",
        pattern="^(future_only|past_only|all)$",
    ),
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
        FacetValue.is_active.is_(True),
        FacetValue.confidence_score >= min_confidence,
        FacetValue.facet_type_id.in_(applicable_facet_types_subq),
    )

    if category_id:
        query = query.where(FacetValue.category_id == category_id)

    # Apply time filter
    now = datetime.now(timezone.utc)
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
            FacetType.is_active.is_(True),
            or_(
                FacetType.applicable_entity_type_slugs == [],  # Empty = applies to all
                FacetType.applicable_entity_type_slugs.any(entity_type_slug)  # Contains this type
            )
        ).order_by(FacetType.display_order, FacetType.name)
    else:
        applicable_types_query = select(FacetType).where(
            FacetType.is_active.is_(True),
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
            # Sort: verified first, then by confidence (desc), then by created_at (desc)
            sorted_values = sorted(
                type_values,
                key=lambda x: (
                    0 if x.human_verified else 1,  # Verified first
                    -(x.confidence_score or 0),  # Higher confidence first
                    -(x.created_at.timestamp() if x.created_at else 0)  # Newer first
                )
            )
            sample_values = [
                {
                    "id": str(v.id),
                    "value": v.value,
                    "text_representation": v.text_representation,
                    "confidence_score": v.confidence_score,
                    "human_verified": v.human_verified,
                    "source_type": v.source_type.value if v.source_type else "DOCUMENT",
                    "source_url": v.source_url,
                    "created_at": v.created_at.isoformat() if v.created_at else None,
                }
                for v in sorted_values[:5]  # Show up to 5 samples
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
            facet_type_value_type=facet_type.value_type.value if hasattr(facet_type.value_type, 'value') else facet_type.value_type,
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


# ============================================================================
# Full-Text Search Endpoint
# ============================================================================


@router.get("/search", response_model=FacetValueSearchResponse)
async def search_facet_values(
    q: str = Query(..., min_length=2, description="Search query"),
    entity_id: Optional[UUID] = Query(default=None, description="Filter by entity"),
    facet_type_slug: Optional[str] = Query(default=None, description="Filter by facet type"),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=20, ge=1, le=100, description="Results per page"),
    session: AsyncSession = Depends(get_session),
):
    """
    Full-text search across facet values with relevance ranking.

    Uses PostgreSQL full-text search (tsvector/tsquery) for efficient
    searching with German language support. Results are ranked by relevance.

    Features:
    - German language stemming and normalization
    - Relevance-based ranking
    - Highlighted search matches
    """
    import time
    start_time = time.time()

    # Build the search query with ts_rank for relevance scoring
    search_query = func.plainto_tsquery("german", q)

    # Build base query with ranking
    query = (
        select(
            FacetValue,
            func.ts_rank(FacetValue.search_vector, search_query).label("rank"),
            func.ts_headline(
                "german",
                FacetValue.text_representation,
                search_query,
                "StartSel=<mark>, StopSel=</mark>, MaxWords=50, MinWords=20"
            ).label("headline"),
        )
        .where(FacetValue.search_vector.op("@@")(search_query))
        .where(FacetValue.is_active.is_(True))
    )

    # Apply filters
    if entity_id:
        query = query.where(FacetValue.entity_id == entity_id)
    if facet_type_slug:
        subq = select(FacetType.id).where(FacetType.slug == facet_type_slug)
        query = query.where(FacetValue.facet_type_id.in_(subq))

    # Order by rank (highest first) with pagination
    query = query.order_by(func.ts_rank(FacetValue.search_vector, search_query).desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    # Execute with eager loading
    query = query.options(
        selectinload(FacetValue.entity),
        selectinload(FacetValue.facet_type),
    )

    result = await session.execute(query)
    rows = result.all()

    # Count total matches (without limit)
    count_query = (
        select(func.count())
        .select_from(FacetValue)
        .where(FacetValue.search_vector.op("@@")(search_query))
        .where(FacetValue.is_active.is_(True))
    )
    if entity_id:
        count_query = count_query.where(FacetValue.entity_id == entity_id)
    if facet_type_slug:
        subq = select(FacetType.id).where(FacetType.slug == facet_type_slug)
        count_query = count_query.where(FacetValue.facet_type_id.in_(subq))

    total = (await session.execute(count_query)).scalar() or 0

    # Build response
    items = []
    for row in rows:
        fv = row[0]
        rank = row[1] if row[1] else 0.0
        headline = row[2]

        items.append(FacetValueSearchResult(
            id=fv.id,
            entity_id=fv.entity_id,
            entity_name=fv.entity.name if fv.entity else "Unknown",
            facet_type_id=fv.facet_type_id,
            facet_type_slug=fv.facet_type.slug if fv.facet_type else "",
            facet_type_name=fv.facet_type.name if fv.facet_type else "",
            value=fv.value,
            text_representation=fv.text_representation,
            headline=headline,
            rank=round(rank, 4),
            confidence_score=fv.confidence_score,
            human_verified=fv.human_verified,
            source_type=fv.source_type.value if fv.source_type else "DOCUMENT",
            created_at=fv.created_at,
        ))

    search_time_ms = (time.time() - start_time) * 1000
    pages = (total + per_page - 1) // per_page if total > 0 else 1

    return FacetValueSearchResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        query=q,
        search_time_ms=round(search_time_ms, 2),
    )


# ============================================================================
# History Endpoints (Time-Series Data)
# ============================================================================


@router.get("/entity/{entity_id}/history/{facet_type_id}", response_model=EntityHistoryResponse)
async def get_entity_history(
    entity_id: UUID,
    facet_type_id: UUID,
    from_date: Optional[datetime] = Query(default=None, description="Start date filter"),
    to_date: Optional[datetime] = Query(default=None, description="End date filter"),
    tracks: Optional[List[str]] = Query(default=None, description="Filter by track keys"),
    limit: int = Query(default=1000, ge=1, le=10000, description="Max points to return"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get history data for an entity+facet combination.

    Returns time-series data with statistics and trend information.
    Supports filtering by date range and track keys.
    """
    service = FacetHistoryService(session)

    try:
        return await service.get_history(
            entity_id=entity_id,
            facet_type_id=facet_type_id,
            from_date=from_date,
            to_date=to_date,
            track_keys=tracks,
            limit=limit,
        )
    except ValueError as e:
        raise NotFoundError("Entity or FacetType", str(e))


@router.get("/entity/{entity_id}/history/{facet_type_id}/aggregated", response_model=AggregatedHistoryResponse)
async def get_entity_history_aggregated(
    entity_id: UUID,
    facet_type_id: UUID,
    interval: str = Query(default="month", pattern="^(day|week|month|quarter|year)$"),
    method: str = Query(default="avg", pattern="^(avg|sum|min|max)$"),
    from_date: Optional[datetime] = Query(default=None),
    to_date: Optional[datetime] = Query(default=None),
    tracks: Optional[List[str]] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """
    Get aggregated history data.

    Aggregates data points by time interval (day, week, month, quarter, year)
    using the specified method (avg, sum, min, max).
    """
    service = FacetHistoryService(session)

    try:
        return await service.aggregate_history(
            entity_id=entity_id,
            facet_type_id=facet_type_id,
            interval=interval,
            method=method,
            from_date=from_date,
            to_date=to_date,
            track_keys=tracks,
        )
    except ValueError as e:
        raise NotFoundError("Entity or FacetType", str(e))


@router.post("/entity/{entity_id}/history/{facet_type_id}", response_model=HistoryDataPointResponse, status_code=201)
async def add_history_data_point(
    entity_id: UUID,
    facet_type_id: UUID,
    data: HistoryDataPointCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Add a single data point to the history.

    Requires Editor role.
    """
    service = FacetHistoryService(session)

    try:
        async with AuditContext(session, current_user, request) as audit:
            data_point = await service.add_data_point(
                entity_id=entity_id,
                facet_type_id=facet_type_id,
                recorded_at=data.recorded_at,
                value=data.value,
                track_key=data.track_key,
                value_label=data.value_label,
                annotations=data.annotations,
                source_type=data.source_type,
                source_url=data.source_url,
                confidence_score=data.confidence_score,
            )

            audit.track_action(
                action=AuditAction.CREATE,
                entity_type="FacetValueHistory",
                entity_id=data_point.id,
                entity_name=f"History point at {data.recorded_at}",
                changes={
                    "entity_id": str(entity_id),
                    "facet_type_id": str(facet_type_id),
                    "track_key": data.track_key,
                    "value": data.value,
                    "recorded_at": data.recorded_at.isoformat(),
                },
            )

            await session.commit()
            await session.refresh(data_point)

        return HistoryDataPointResponse.model_validate(data_point)

    except ValueError as e:
        raise ConflictError("Invalid data", detail=str(e))


@router.post("/entity/{entity_id}/history/{facet_type_id}/bulk", response_model=HistoryBulkImportResponse)
async def add_history_data_points_bulk(
    entity_id: UUID,
    facet_type_id: UUID,
    data: HistoryBulkImport,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Bulk import multiple history data points.

    Requires Editor role. Optionally skips duplicates.
    """
    service = FacetHistoryService(session)

    try:
        async with AuditContext(session, current_user, request) as audit:
            result = await service.add_data_points_bulk(
                entity_id=entity_id,
                facet_type_id=facet_type_id,
                data_points=data.data_points,
                skip_duplicates=data.skip_duplicates,
            )

            audit.track_action(
                action=AuditAction.CREATE,
                entity_type="FacetValueHistory",
                entity_id=entity_id,  # Using entity_id as reference
                entity_name=f"Bulk import: {result.created} points",
                changes={
                    "entity_id": str(entity_id),
                    "facet_type_id": str(facet_type_id),
                    "created": result.created,
                    "skipped": result.skipped,
                },
            )

            await session.commit()

        return result

    except ValueError as e:
        raise ConflictError("Invalid data", detail=str(e))


@router.put("/entity/{entity_id}/history/{facet_type_id}/{point_id}", response_model=HistoryDataPointResponse)
async def update_history_data_point(
    entity_id: UUID,
    facet_type_id: UUID,
    point_id: UUID,
    data: HistoryDataPointUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Update a history data point.

    Requires Editor role.
    """
    service = FacetHistoryService(session)

    async with AuditContext(session, current_user, request) as audit:
        data_point = await service.update_data_point(
            data_point_id=point_id,
            value=data.value,
            value_label=data.value_label,
            annotations=data.annotations,
            human_verified=data.human_verified,
            verified_by=current_user.email if data.human_verified else None,
        )

        if not data_point:
            raise NotFoundError("HistoryDataPoint", str(point_id))

        audit.track_action(
            action=AuditAction.UPDATE,
            entity_type="FacetValueHistory",
            entity_id=point_id,
            entity_name=f"History point at {data_point.recorded_at}",
            changes=data.model_dump(exclude_unset=True),
        )

        await session.commit()
        await session.refresh(data_point)

    return HistoryDataPointResponse.model_validate(data_point)


@router.delete("/entity/{entity_id}/history/{facet_type_id}/{point_id}", response_model=MessageResponse)
async def delete_history_data_point(
    entity_id: UUID,
    facet_type_id: UUID,
    point_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    """
    Delete a single history data point.

    Requires Editor role.
    """
    service = FacetHistoryService(session)

    async with AuditContext(session, current_user, request) as audit:
        deleted = await service.delete_data_point(point_id)

        if not deleted:
            raise NotFoundError("HistoryDataPoint", str(point_id))

        audit.track_action(
            action=AuditAction.DELETE,
            entity_type="FacetValueHistory",
            entity_id=point_id,
            entity_name=f"History point {point_id}",
            changes={"deleted": True},
        )

        await session.commit()

    return MessageResponse(message="History data point deleted successfully")
