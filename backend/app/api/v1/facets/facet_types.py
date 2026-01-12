"""API endpoints for FacetType management."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import AuditContext
from app.core.cache import facet_type_cache
from app.core.deps import require_editor
from app.core.exceptions import ConflictError, NotFoundError
from app.core.validators import validate_entity_type_slugs
from app.database import get_session
from app.models import (
    AnalysisTemplate,
    Category,
    FacetType,
    FacetValue,
)
from app.models.audit_log import AuditAction
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.facet_type import (
    FacetTypeCreate,
    FacetTypeListResponse,
    FacetTypeResponse,
    FacetTypeSchemaGenerateRequest,
    FacetTypeSchemaGenerateResponse,
    FacetTypeUpdate,
    generate_slug,
)

router = APIRouter()


@router.get("/types", response_model=FacetTypeListResponse)
async def list_facet_types(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    is_active: bool | None = Query(default=None),
    ai_extraction_enabled: bool | None = Query(default=None),
    is_time_based: bool | None = Query(default=None),
    applicable_entity_type_slugs: list[str] | None = Query(default=None),
    search: str | None = Query(default=None),
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
    if applicable_entity_type_slugs:
        # Filter FacetTypes that apply to any of the given entity type slugs
        query = query.where(FacetType.applicable_entity_type_slugs.overlap(applicable_entity_type_slugs))
    if search:
        # Escape SQL wildcards to prevent injection
        escaped_search = search.replace("%", r"\%").replace("_", r"\_")
        search_pattern = f"%{escaped_search}%"
        query = query.where(
            FacetType.name.ilike(search_pattern, escape="\\") | FacetType.slug.ilike(search_pattern, escape="\\")
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
    value_counts_map: dict[UUID, int] = {}

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


@router.get("/types/for-category/{category_id}", response_model=list[FacetTypeResponse])
async def get_facet_types_for_category(
    category_id: UUID,
    ai_extraction_enabled: bool | None = Query(default=True),
    is_active: bool | None = Query(default=True),
    session: AsyncSession = Depends(get_session),
):
    """
    Get all FacetTypes relevant for a specific Category.

    The connection is: Category -> EntityTypes -> FacetTypes
    (via applicable_entity_type_slugs).

    This is useful for ResultsView to load FacetTypes dynamically
    based on the active category filter.
    """
    # 1. Load Category with EntityType associations (including the EntityType itself)
    from app.models import CategoryEntityType

    category_query = (
        select(Category)
        .options(
            selectinload(Category.entity_type_associations).selectinload(CategoryEntityType.entity_type),
            selectinload(Category.target_entity_type),
        )
        .where(Category.id == category_id)
    )
    result = await session.execute(category_query)
    category = result.scalar_one_or_none()

    if not category:
        raise NotFoundError("Category", str(category_id))

    # 2. Collect EntityType slugs from associations
    entity_type_slugs = []
    for assoc in category.entity_type_associations:
        if assoc.entity_type:
            entity_type_slugs.append(assoc.entity_type.slug)

    # Also include target_entity_type for backwards compatibility
    if category.target_entity_type and category.target_entity_type.slug not in entity_type_slugs:
        entity_type_slugs.append(category.target_entity_type.slug)

    if not entity_type_slugs:
        return []

    # 3. Load FacetTypes that apply to these EntityTypes
    query = select(FacetType).where(FacetType.applicable_entity_type_slugs.overlap(entity_type_slugs))

    if is_active is not None:
        query = query.where(FacetType.is_active.is_(is_active))
    if ai_extraction_enabled is not None:
        query = query.where(FacetType.ai_extraction_enabled.is_(ai_extraction_enabled))

    query = query.order_by(FacetType.display_order, FacetType.name)

    result = await session.execute(query)
    facet_types = list(result.scalars().all())

    return [FacetTypeResponse.model_validate(ft) for ft in facet_types]


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

    value_count = (
        await session.execute(select(func.count()).where(FacetValue.facet_type_id == facet_type.id))
    ).scalar()

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
        value_count = (
            await session.execute(select(func.count()).where(FacetValue.facet_type_id == cached["id"]))
        ).scalar()
        response = FacetTypeResponse(**cached)
        response.value_count = value_count
        return response

    # Fetch from database
    result = await session.execute(select(FacetType).where(FacetType.slug == slug))
    facet_type = result.scalar()
    if not facet_type:
        raise NotFoundError("FacetType", slug)

    value_count = (
        await session.execute(select(func.count()).where(FacetValue.facet_type_id == facet_type.id))
    ).scalar()

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
        entity_context = (
            f"\nDieser Facet-Typ wird für folgende Entity-Typen verwendet: {', '.join(data.applicable_entity_types)}"
        )

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
Plural: {data.name_plural or data.name + "s"}
Beschreibung: {data.description or "Keine Beschreibung angegeben"}{entity_context}

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
        generated = result.extracted_data if hasattr(result, "extracted_data") else {}

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

        # If name changes, regenerate embedding
        if "name" in update_data:
            from app.utils.similarity import generate_embedding

            embedding = await generate_embedding(update_data["name"], session=session)
            if embedding:
                update_data["name_embedding"] = embedding

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
    value_count = (
        await session.execute(select(func.count()).where(FacetValue.facet_type_id == facet_type.id))
    ).scalar()

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
            cleaned_config = [fc for fc in original_config if fc.get("facet_type_slug") != slug]
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
