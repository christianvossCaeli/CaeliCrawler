"""API endpoints for Analysis and Reporting."""

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import (
    Entity, EntityType, FacetType, FacetValue, EntityRelation, RelationType,
    AnalysisTemplate, Category, Document, DataSource,
)
from app.models.user import User
from app.schemas.analysis_template import (
    AnalysisTemplateCreate,
    AnalysisTemplateUpdate,
    AnalysisTemplateResponse,
    AnalysisTemplateListResponse,
    generate_slug,
)
from app.schemas.common import MessageResponse
from app.core.exceptions import NotFoundError, ConflictError
from app.core.deps import get_current_user_optional

router = APIRouter()


# ============================================================================
# Smart Query - KI-gestützte natürliche Sprache Abfragen
# ============================================================================


class SmartQueryRequest(BaseModel):
    """Request for smart query endpoint."""
    question: str = Field(..., min_length=3, max_length=500, description="Natural language question or command")
    allow_write: bool = Field(default=False, description="Allow write operations (create entities, facets, relations)")


@router.post("/smart-query")
async def smart_query_endpoint(
    request: SmartQueryRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Execute a natural language query or command against the Entity-Facet system.

    ## Read Examples:
    - "Zeige mir auf welche künftige Events wichtige Entscheider-Personen von Gemeinden gehen"
    - "Welche Bürgermeister sprechen auf Windenergie-Konferenzen in den nächsten 3 Monaten?"
    - "Zeige mir alle Pain Points von Gemeinden in NRW"

    ## Write Examples (requires allow_write=True):
    - "Erstelle eine neue Person Max Müller, Bürgermeister"
    - "Füge einen Pain Point für Gummersbach hinzu: Bürgerbeschwerden wegen Lärmbelästigung"
    - "Verknüpfe Max Müller mit Gummersbach als Arbeitgeber"

    The AI interprets the question/command and executes the appropriate action.
    """
    from services.smart_query_service import smart_query

    result = await smart_query(session, request.question, allow_write=request.allow_write)
    return result


class SmartWriteRequest(BaseModel):
    """Request for smart write endpoint with preview support."""
    question: str = Field(..., min_length=3, max_length=500, description="Natural language command")
    preview_only: bool = Field(default=True, description="If true, only return preview without executing")
    confirmed: bool = Field(default=False, description="If true and preview_only=false, execute the command")


@router.post("/smart-write")
async def smart_write_endpoint(
    request: SmartWriteRequest,
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Execute a write command in natural language with preview support.

    **Workflow:**
    1. Send command with preview_only=True (default) → Get preview of what will be created
    2. Review the preview
    3. Send same command with preview_only=False, confirmed=True → Execute the command

    This endpoint is for:
    - Creating new entities (persons, municipalities, organizations, events)
    - Adding facets (pain points, positive signals, contacts)
    - Creating relations between entities
    - Creating category setups with automatic data source linking
    - Starting crawls for specific data sources

    Examples:
    - "Erstelle eine Person Hans Schmidt, Landrat von Oberberg"
    - "Füge einen Pain Point für Münster hinzu: Personalmangel in der IT-Abteilung"
    - "Neue Organisation: Caeli Wind GmbH, Windenergie-Entwickler"
    - "Verknüpfe Hans Schmidt mit Oberbergischer Kreis"
    - "Finde alle Events auf denen Entscheider aus NRW teilnehmen"
    - "Starte Crawls für alle Gummersbach Datenquellen"
    """
    from services.smart_query_service import interpret_write_command, execute_write_command

    # First, interpret the command
    command = await interpret_write_command(request.question)

    if not command or command.get("operation", "none") == "none":
        return {
            "success": False,
            "mode": "preview" if request.preview_only else "write",
            "message": "Keine Schreib-Operation erkannt. Bitte formulieren Sie das Kommando anders.",
            "interpretation": command,
            "original_question": request.question,
        }

    # Preview mode - just return the interpretation
    if request.preview_only:
        return {
            "success": True,
            "mode": "preview",
            "message": "Vorschau der geplanten Aktion",
            "interpretation": command,
            "preview": _build_preview(command),
            "original_question": request.question,
        }

    # Execute mode - require confirmation
    if not request.confirmed:
        return {
            "success": False,
            "mode": "write",
            "message": "Bestätigung erforderlich. Setzen Sie confirmed=true um fortzufahren.",
            "interpretation": command,
            "preview": _build_preview(command),
            "original_question": request.question,
        }

    # Execute the command with current user context
    current_user_id = current_user.id if current_user else None
    result = await execute_write_command(session, command, current_user_id)
    result["original_question"] = request.question
    result["mode"] = "write"
    result["interpretation"] = command

    return result


def _build_preview(command: dict) -> dict:
    """Build a human-readable preview of what will be created."""
    operation = command.get("operation", "none")
    preview = {
        "operation_de": _operation_to_german(operation),
        "description": command.get("explanation", ""),
        "details": [],
    }

    if operation == "create_entity":
        entity_data = command.get("entity_data", {})
        entity_type = command.get("entity_type", "unknown")
        preview["details"] = [
            f"Typ: {_entity_type_to_german(entity_type)}",
            f"Name: {entity_data.get('name', 'N/A')}",
        ]
        attrs = entity_data.get("core_attributes", {})
        for key, value in attrs.items():
            if value:
                preview["details"].append(f"{key.title()}: {value}")

    elif operation == "create_facet":
        facet_data = command.get("facet_data", {})
        preview["details"] = [
            f"Facet-Typ: {_facet_type_to_german(facet_data.get('facet_type', 'unknown'))}",
            f"Für Entity: {facet_data.get('target_entity_name', 'N/A')}",
            f"Inhalt: {facet_data.get('text_representation', 'N/A')}",
        ]

    elif operation == "create_relation":
        rel_data = command.get("relation_data", {})
        preview["details"] = [
            f"Verknüpfung: {_relation_to_german(rel_data.get('relation_type', 'unknown'))}",
            f"Von: {rel_data.get('source_entity_name', 'N/A')} ({rel_data.get('source_entity_type', '')})",
            f"Nach: {rel_data.get('target_entity_name', 'N/A')} ({rel_data.get('target_entity_type', '')})",
        ]

    elif operation == "create_entity_type":
        type_data = command.get("entity_type_data", {})
        preview["details"] = [
            f"Name: {type_data.get('name', 'N/A')}",
            f"Plural: {type_data.get('name_plural', 'N/A')}",
            f"Icon: {type_data.get('icon', 'mdi-folder')}",
            f"Farbe: {type_data.get('color', '#4CAF50')}",
        ]
        if type_data.get("description"):
            preview["details"].append(f"Beschreibung: {type_data.get('description')}")

    elif operation == "create_category_setup":
        setup_data = command.get("category_setup_data", {})
        preview["details"] = [
            f"Name: {setup_data.get('name', 'N/A')}",
            f"Zweck: {setup_data.get('purpose', 'N/A')}",
        ]
        geo_filter = setup_data.get("geographic_filter", {})
        if geo_filter.get("admin_level_1"):
            preview["details"].append(f"Region: {geo_filter.get('admin_level_1')}")
        if geo_filter.get("admin_level_2"):
            preview["details"].append(f"Kreis/Stadt: {geo_filter.get('admin_level_2')}")
        search_terms = setup_data.get("search_terms", [])
        if search_terms:
            preview["details"].append(f"Suchbegriffe: {', '.join(search_terms[:5])}")
        search_focus = setup_data.get("search_focus", "general")
        focus_de = {
            "event_attendance": "Events & Teilnahmen",
            "pain_points": "Probleme & Herausforderungen",
            "contacts": "Kontakte & Ansprechpartner",
            "general": "Allgemein",
        }.get(search_focus, search_focus)
        preview["details"].append(f"Fokus: {focus_de}")
        preview["details"].append("→ Erstellt EntityType + Category + verknüpft Datenquellen")

    elif operation == "start_crawl":
        crawl_data = command.get("crawl_command_data", {})
        filter_type = crawl_data.get("filter_type", "unknown")
        preview["details"] = [f"Filter-Typ: {filter_type}"]
        if crawl_data.get("location_name"):
            preview["details"].append(f"Ort: {crawl_data.get('location_name')}")
        if crawl_data.get("admin_level_1"):
            preview["details"].append(f"Region: {crawl_data.get('admin_level_1')}")
        if crawl_data.get("category_slug"):
            preview["details"].append(f"Category: {crawl_data.get('category_slug')}")
        if crawl_data.get("entity_name"):
            preview["details"].append(f"Entity: {crawl_data.get('entity_name')}")
        preview["details"].append("→ Startet Crawl-Jobs für passende Datenquellen")

    elif operation == "combined":
        # Support both "operations" and "combined_operations" keys
        operations_list = command.get("operations", []) or command.get("combined_operations", [])
        preview["details"] = [f"Anzahl Operationen: {len(operations_list)}"]
        for i, sub_op in enumerate(operations_list, 1):
            op_name = sub_op.get("operation", "unknown")
            op_de = _operation_to_german(op_name)
            preview["details"].append(f"  {i}. {op_de}")
        preview["details"].append("→ Führt alle Operationen nacheinander aus")

    return preview


def _operation_to_german(op: str) -> str:
    """Convert operation to German."""
    return {
        "create_entity": "Entity erstellen",
        "create_entity_type": "Entity-Typ erstellen",
        "create_facet": "Facet hinzufügen",
        "create_relation": "Verknüpfung erstellen",
        "update_entity": "Entity aktualisieren",
        "create_category_setup": "Category-Setup erstellen",
        "start_crawl": "Crawl starten",
        "combined": "Kombinierte Operationen",
    }.get(op, op)


def _entity_type_to_german(et: str) -> str:
    """Convert entity type to German."""
    return {
        "municipality": "Gemeinde",
        "person": "Person",
        "organization": "Organisation",
        "event": "Veranstaltung",
    }.get(et, et)


def _facet_type_to_german(ft: str) -> str:
    """Convert facet type to German."""
    return {
        "pain_point": "Pain Point / Problem",
        "positive_signal": "Positive Signal / Chance",
        "contact": "Kontakt",
        "event_attendance": "Event-Teilnahme",
        "summary": "Zusammenfassung",
    }.get(ft, ft)


def _relation_to_german(rt: str) -> str:
    """Convert relation type to German."""
    return {
        "works_for": "arbeitet für",
        "attends": "nimmt teil an",
        "located_in": "befindet sich in",
        "member_of": "ist Mitglied von",
    }.get(rt, rt)


@router.get("/smart-query/examples")
async def get_smart_query_examples():
    """Get example queries for the smart query endpoint."""
    return {
        "read_examples": [
            {
                "question": "Zeige mir auf welche künftige Events wichtige Entscheider-Personen von Gemeinden gehen",
                "description": "Findet alle Personen mit Positionen wie Bürgermeister, Landrat etc. und deren zukünftige Event-Teilnahmen",
            },
            {
                "question": "Welche Bürgermeister sprechen auf Windenergie-Konferenzen?",
                "description": "Filtert nach Position 'Bürgermeister' und Event-Attendance Facets",
            },
            {
                "question": "Wo kann ich Entscheider aus Bayern in den nächsten 90 Tagen treffen?",
                "description": "Kombiniert Regions-Filter mit zukünftigen Events",
            },
            {
                "question": "Zeige mir alle Pain Points von Gemeinden",
                "description": "Listet alle Pain Point Facets gruppiert nach Gemeinde",
            },
        ],
        "write_examples": [
            {
                "question": "Erstelle eine neue Person Max Müller, Bürgermeister von Gummersbach",
                "description": "Erstellt eine Person-Entity mit Position 'Bürgermeister'",
            },
            {
                "question": "Füge einen Pain Point für Münster hinzu: Personalmangel in der IT",
                "description": "Erstellt einen Pain Point Facet für die Gemeinde Münster",
            },
            {
                "question": "Neue Organisation: Caeli Wind GmbH, Windenergie-Entwickler",
                "description": "Erstellt eine neue Organisation-Entity",
            },
            {
                "question": "Verknüpfe Max Müller mit Gummersbach als Arbeitgeber",
                "description": "Erstellt eine 'works_for' Relation zwischen Person und Gemeinde",
            },
        ],
        "supported_filters": {
            "time": ["künftig", "vergangen", "zukünftig", "in den nächsten X Tagen/Monaten"],
            "positions": ["Bürgermeister", "Landrat", "Dezernent", "Entscheider", "Amtsleiter"],
            "entity_types": ["Person", "Gemeinde", "Event", "Organisation"],
            "facet_types": ["Pain Points", "Positive Signale", "Event-Teilnahmen", "Kontakte"],
        },
        "write_operations": {
            "create_entity": ["Erstelle", "Neue/r/s", "Anlegen"],
            "create_facet": ["Füge hinzu", "Neuer Pain Point", "Neues Positive Signal"],
            "create_relation": ["Verknüpfe", "Verbinde", "arbeitet für", "ist Mitglied von"],
        },
    }


# ============================================================================
# AnalysisTemplate CRUD
# ============================================================================


@router.get("/templates", response_model=AnalysisTemplateListResponse)
async def list_analysis_templates(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    category_id: Optional[UUID] = Query(default=None),
    entity_type_id: Optional[UUID] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """List all analysis templates with pagination."""
    query = select(AnalysisTemplate)

    if category_id:
        query = query.where(AnalysisTemplate.category_id == category_id)
    if entity_type_id:
        query = query.where(AnalysisTemplate.primary_entity_type_id == entity_type_id)
    if is_active is not None:
        query = query.where(AnalysisTemplate.is_active == is_active)
    if search:
        query = query.where(
            AnalysisTemplate.name.ilike(f"%{search}%") |
            AnalysisTemplate.slug.ilike(f"%{search}%")
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(AnalysisTemplate.display_order, AnalysisTemplate.name).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    templates = result.scalars().all()

    # Enrich with related info
    items = []
    for t in templates:
        category = await session.get(Category, t.category_id) if t.category_id else None
        entity_type = await session.get(EntityType, t.primary_entity_type_id)

        item = AnalysisTemplateResponse.model_validate(t)
        item.category_name = category.name if category else None
        item.primary_entity_type_name = entity_type.name if entity_type else None
        item.primary_entity_type_slug = entity_type.slug if entity_type else None
        items.append(item)

    return AnalysisTemplateListResponse(items=items, total=total)


@router.post("/templates", response_model=AnalysisTemplateResponse, status_code=201)
async def create_analysis_template(
    data: AnalysisTemplateCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new analysis template."""
    # Verify entity type exists
    entity_type = await session.get(EntityType, data.primary_entity_type_id)
    if not entity_type:
        raise NotFoundError("EntityType", str(data.primary_entity_type_id))

    # Generate slug if not provided
    slug = data.slug or generate_slug(data.name)

    # Check for duplicate
    existing = await session.execute(
        select(AnalysisTemplate).where(
            (AnalysisTemplate.name == data.name) | (AnalysisTemplate.slug == slug)
        )
    )
    if existing.scalar():
        raise ConflictError(
            "Analysis Template already exists",
            detail=f"A template with name '{data.name}' or slug '{slug}' already exists",
        )

    template = AnalysisTemplate(
        name=data.name,
        slug=slug,
        description=data.description,
        category_id=data.category_id,
        primary_entity_type_id=data.primary_entity_type_id,
        facet_config=[fc.model_dump() for fc in data.facet_config],
        aggregation_config=data.aggregation_config.model_dump() if data.aggregation_config else {},
        display_config=data.display_config.model_dump() if data.display_config else {},
        extraction_prompt_template=data.extraction_prompt_template,
        is_default=data.is_default,
        is_active=data.is_active,
        display_order=data.display_order,
        is_system=False,
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)

    item = AnalysisTemplateResponse.model_validate(template)
    item.primary_entity_type_name = entity_type.name
    item.primary_entity_type_slug = entity_type.slug

    return item


@router.get("/templates/{template_id}", response_model=AnalysisTemplateResponse)
async def get_analysis_template(
    template_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a single analysis template by ID."""
    template = await session.get(AnalysisTemplate, template_id)
    if not template:
        raise NotFoundError("AnalysisTemplate", str(template_id))

    category = await session.get(Category, template.category_id) if template.category_id else None
    entity_type = await session.get(EntityType, template.primary_entity_type_id)

    response = AnalysisTemplateResponse.model_validate(template)
    response.category_name = category.name if category else None
    response.primary_entity_type_name = entity_type.name if entity_type else None
    response.primary_entity_type_slug = entity_type.slug if entity_type else None

    return response


@router.get("/templates/by-slug/{slug}", response_model=AnalysisTemplateResponse)
async def get_analysis_template_by_slug(
    slug: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a single analysis template by slug."""
    result = await session.execute(
        select(AnalysisTemplate).where(AnalysisTemplate.slug == slug)
    )
    template = result.scalar()
    if not template:
        raise NotFoundError("AnalysisTemplate", slug)

    category = await session.get(Category, template.category_id) if template.category_id else None
    entity_type = await session.get(EntityType, template.primary_entity_type_id)

    response = AnalysisTemplateResponse.model_validate(template)
    response.category_name = category.name if category else None
    response.primary_entity_type_name = entity_type.name if entity_type else None
    response.primary_entity_type_slug = entity_type.slug if entity_type else None

    return response


@router.put("/templates/{template_id}", response_model=AnalysisTemplateResponse)
async def update_analysis_template(
    template_id: UUID,
    data: AnalysisTemplateUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update an analysis template."""
    template = await session.get(AnalysisTemplate, template_id)
    if not template:
        raise NotFoundError("AnalysisTemplate", str(template_id))

    # Update fields
    update_data = data.model_dump(exclude_unset=True)

    # Handle nested configs
    if "facet_config" in update_data and update_data["facet_config"]:
        update_data["facet_config"] = [fc.model_dump() if hasattr(fc, 'model_dump') else fc for fc in update_data["facet_config"]]
    if "aggregation_config" in update_data and update_data["aggregation_config"]:
        update_data["aggregation_config"] = update_data["aggregation_config"].model_dump() if hasattr(update_data["aggregation_config"], 'model_dump') else update_data["aggregation_config"]
    if "display_config" in update_data and update_data["display_config"]:
        update_data["display_config"] = update_data["display_config"].model_dump() if hasattr(update_data["display_config"], 'model_dump') else update_data["display_config"]

    for field, value in update_data.items():
        setattr(template, field, value)

    await session.commit()
    await session.refresh(template)

    return AnalysisTemplateResponse.model_validate(template)


@router.delete("/templates/{template_id}", response_model=MessageResponse)
async def delete_analysis_template(
    template_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Delete an analysis template."""
    template = await session.get(AnalysisTemplate, template_id)
    if not template:
        raise NotFoundError("AnalysisTemplate", str(template_id))

    if template.is_system:
        raise ConflictError(
            "Cannot delete system template",
            detail=f"Template '{template.name}' is a system template and cannot be deleted",
        )

    await session.delete(template)
    await session.commit()

    return MessageResponse(message=f"Analysis template '{template.name}' deleted successfully")


# ============================================================================
# Analysis Overview Endpoints
# ============================================================================


@router.get("/overview")
async def get_analysis_overview(
    template_id: Optional[UUID] = Query(default=None),
    template_slug: Optional[str] = Query(default=None),
    entity_type_slug: Optional[str] = Query(default=None),
    category_id: Optional[UUID] = Query(default=None),
    facet_types: Optional[List[str]] = Query(default=None, description="Facet type slugs to include"),
    time_filter: Optional[str] = Query(default=None, description="future_only, past_only, all"),
    min_confidence: float = Query(default=0.7, ge=0, le=1),
    min_facet_values: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    """
    Get analysis overview for entities.

    Returns a list of entities with aggregated facet counts and key metrics
    based on the selected template or parameters.
    """
    # Determine entity type
    entity_type = None
    template = None

    if template_id:
        template = await session.get(AnalysisTemplate, template_id)
        if not template:
            raise NotFoundError("AnalysisTemplate", str(template_id))
        entity_type = await session.get(EntityType, template.primary_entity_type_id)
    elif template_slug:
        t_result = await session.execute(
            select(AnalysisTemplate).where(AnalysisTemplate.slug == template_slug)
        )
        template = t_result.scalar()
        if template:
            entity_type = await session.get(EntityType, template.primary_entity_type_id)
    elif entity_type_slug:
        et_result = await session.execute(
            select(EntityType).where(EntityType.slug == entity_type_slug)
        )
        entity_type = et_result.scalar()

    if not entity_type:
        raise ConflictError(
            "No entity type specified",
            detail="Provide template_id, template_slug, or entity_type_slug",
        )

    # Determine which facet types to include
    facet_type_ids = []
    if facet_types:
        ft_result = await session.execute(
            select(FacetType).where(FacetType.slug.in_(facet_types))
        )
        facet_type_ids = [ft.id for ft in ft_result.scalars().all()]
    elif template and template.facet_config:
        enabled_slugs = [
            fc.get("facet_type_slug") or fc.get("facet_type")
            for fc in template.facet_config
            if fc.get("enabled", True)
        ]
        if enabled_slugs:
            ft_result = await session.execute(
                select(FacetType).where(FacetType.slug.in_(enabled_slugs))
            )
            facet_type_ids = [ft.id for ft in ft_result.scalars().all()]

    # Get all entities of this type
    entities_query = select(Entity).where(
        Entity.entity_type_id == entity_type.id,
        Entity.is_active == True,
    )
    entities_result = await session.execute(entities_query)
    entities = entities_result.scalars().all()

    # Build overview data
    now = datetime.utcnow()
    overview_items = []

    for entity in entities:
        # Base query for facet values
        fv_query = select(FacetValue).where(
            FacetValue.entity_id == entity.id,
            FacetValue.is_active == True,
            FacetValue.confidence_score >= min_confidence,
        )

        if facet_type_ids:
            fv_query = fv_query.where(FacetValue.facet_type_id.in_(facet_type_ids))
        if category_id:
            fv_query = fv_query.where(FacetValue.category_id == category_id)

        # Apply time filter
        if time_filter == "future_only":
            fv_query = fv_query.where(
                or_(
                    FacetValue.event_date >= now,
                    FacetValue.valid_until >= now,
                    and_(FacetValue.event_date.is_(None), FacetValue.valid_until.is_(None))
                )
            )
        elif time_filter == "past_only":
            fv_query = fv_query.where(
                or_(
                    FacetValue.event_date < now,
                    FacetValue.valid_until < now
                )
            )

        fv_result = await session.execute(fv_query)
        facet_values = fv_result.scalars().all()

        if len(facet_values) < min_facet_values:
            continue

        # Group by facet type
        by_type: Dict[UUID, List[FacetValue]] = {}
        for fv in facet_values:
            if fv.facet_type_id not in by_type:
                by_type[fv.facet_type_id] = []
            by_type[fv.facet_type_id].append(fv)

        facet_counts = {}
        total_verified = 0
        avg_confidence = sum(fv.confidence_score or 0 for fv in facet_values) / len(facet_values) if facet_values else 0

        for ft_id, fvs in by_type.items():
            ft = await session.get(FacetType, ft_id)
            if ft:
                facet_counts[ft.slug] = len(fvs)
                total_verified += sum(1 for fv in fvs if fv.human_verified)

        # Count relations
        relation_count = (await session.execute(
            select(func.count()).where(
                or_(
                    EntityRelation.source_entity_id == entity.id,
                    EntityRelation.target_entity_id == entity.id
                )
            )
        )).scalar()

        # Count data sources
        source_count = (await session.execute(
            select(func.count()).where(DataSource.entity_id == entity.id)
        )).scalar()

        latest_facet = max((fv.created_at for fv in facet_values), default=None)

        overview_items.append({
            "entity_id": str(entity.id),
            "entity_name": entity.name,
            "entity_slug": entity.slug,
            "external_id": entity.external_id,
            "hierarchy_path": entity.hierarchy_path,
            "latitude": entity.latitude,
            "longitude": entity.longitude,
            "total_facet_values": len(facet_values),
            "verified_count": total_verified,
            "avg_confidence": round(avg_confidence, 2),
            "facet_counts": facet_counts,
            "relation_count": relation_count,
            "source_count": source_count,
            "latest_facet_date": latest_facet.isoformat() if latest_facet else None,
        })

    # Sort by total facet values
    overview_items.sort(key=lambda x: x["total_facet_values"], reverse=True)
    overview_items = overview_items[:limit]

    return {
        "entity_type": {
            "id": str(entity_type.id),
            "slug": entity_type.slug,
            "name": entity_type.name,
            "name_plural": entity_type.name_plural,
        },
        "template": {
            "id": str(template.id),
            "slug": template.slug,
            "name": template.name,
        } if template else None,
        "filters": {
            "category_id": str(category_id) if category_id else None,
            "facet_types": facet_types,
            "time_filter": time_filter,
            "min_confidence": min_confidence,
        },
        "total_entities": len(overview_items),
        "entities": overview_items,
    }


@router.get("/report/{entity_id}")
async def get_entity_report(
    entity_id: UUID,
    template_id: Optional[UUID] = Query(default=None),
    template_slug: Optional[str] = Query(default=None),
    category_id: Optional[UUID] = Query(default=None),
    time_filter: Optional[str] = Query(default=None),
    min_confidence: float = Query(default=0.7, ge=0, le=1),
    session: AsyncSession = Depends(get_session),
):
    """
    Get detailed analysis report for a specific entity.

    Aggregates all facet values and relations, with deduplication and ranking.
    """
    entity = await session.get(Entity, entity_id)
    if not entity:
        raise NotFoundError("Entity", str(entity_id))

    entity_type = await session.get(EntityType, entity.entity_type_id)

    # Get template if specified
    template = None
    if template_id:
        template = await session.get(AnalysisTemplate, template_id)
    elif template_slug:
        t_result = await session.execute(
            select(AnalysisTemplate).where(AnalysisTemplate.slug == template_slug)
        )
        template = t_result.scalar()

    # Determine facet type configuration
    facet_config = {}
    if template and template.facet_config:
        for fc in template.facet_config:
            slug = fc.get("facet_type_slug") or fc.get("facet_type")
            if fc.get("enabled", True):
                facet_config[slug] = {
                    "label": fc.get("label"),
                    "display_order": fc.get("display_order", 0),
                    "time_filter": fc.get("time_filter"),
                }

    # Base query for facet values
    now = datetime.utcnow()
    fv_query = select(FacetValue).where(
        FacetValue.entity_id == entity_id,
        FacetValue.is_active == True,
        FacetValue.confidence_score >= min_confidence,
    )

    if category_id:
        fv_query = fv_query.where(FacetValue.category_id == category_id)

    # Apply time filter
    if time_filter == "future_only":
        fv_query = fv_query.where(
            or_(
                FacetValue.event_date >= now,
                FacetValue.valid_until >= now,
                and_(FacetValue.event_date.is_(None), FacetValue.valid_until.is_(None))
            )
        )
    elif time_filter == "past_only":
        fv_query = fv_query.where(
            or_(
                FacetValue.event_date < now,
                FacetValue.valid_until < now
            )
        )

    fv_result = await session.execute(fv_query)
    facet_values = fv_result.scalars().all()

    # Group facet values by type and aggregate
    facets_by_type: Dict[str, Dict[str, Any]] = {}

    for fv in facet_values:
        ft = await session.get(FacetType, fv.facet_type_id)
        if not ft:
            continue

        # Apply per-facet time filter from template
        if ft.slug in facet_config:
            ft_time_filter = facet_config[ft.slug].get("time_filter")
            if ft_time_filter == "future_only" and fv.event_date and fv.event_date < now:
                continue
            elif ft_time_filter == "past_only" and fv.event_date and fv.event_date >= now:
                continue

        if ft.slug not in facets_by_type:
            facets_by_type[ft.slug] = {
                "facet_type_id": str(ft.id),
                "facet_type_slug": ft.slug,
                "facet_type_name": facet_config.get(ft.slug, {}).get("label") or ft.name,
                "icon": ft.icon,
                "color": ft.color,
                "values": [],
                "aggregated": {},
            }

        # Get document info if available
        document = await session.get(Document, fv.source_document_id) if fv.source_document_id else None

        facets_by_type[ft.slug]["values"].append({
            "id": str(fv.id),
            "value": fv.value,
            "text": fv.text_representation,
            "event_date": fv.event_date.isoformat() if fv.event_date else None,
            "confidence": fv.confidence_score,
            "verified": fv.human_verified,
            "source_url": fv.source_url,
            "document": {
                "id": str(document.id),
                "title": document.title,
                "url": document.original_url,
            } if document else None,
            "occurrence_count": fv.occurrence_count,
            "first_seen": fv.first_seen.isoformat() if fv.first_seen else None,
            "last_seen": fv.last_seen.isoformat() if fv.last_seen else None,
        })

    # Aggregate and deduplicate per facet type
    for slug, data in facets_by_type.items():
        ft_result = await session.execute(
            select(FacetType).where(FacetType.slug == slug)
        )
        ft = ft_result.scalar()

        if ft and ft.deduplication_fields:
            # Deduplicate based on configured fields
            deduped = _deduplicate_values(data["values"], ft.deduplication_fields)
            data["aggregated"] = {
                "total": len(data["values"]),
                "unique": len(deduped),
                "verified": sum(1 for v in data["values"] if v.get("verified")),
                "avg_confidence": round(
                    sum(v.get("confidence", 0) for v in data["values"]) / len(data["values"]),
                    2
                ) if data["values"] else 0,
            }
            data["values"] = deduped
        else:
            # No deduplication, just sort by confidence
            data["values"].sort(key=lambda x: x.get("confidence", 0), reverse=True)
            data["aggregated"] = {
                "total": len(data["values"]),
                "verified": sum(1 for v in data["values"] if v.get("verified")),
                "avg_confidence": round(
                    sum(v.get("confidence", 0) for v in data["values"]) / len(data["values"]),
                    2
                ) if data["values"] else 0,
            }

    # Get relations
    relations = []
    rel_query = select(EntityRelation).where(
        or_(
            EntityRelation.source_entity_id == entity_id,
            EntityRelation.target_entity_id == entity_id
        ),
        EntityRelation.is_active == True,
    )
    rel_result = await session.execute(rel_query)

    for rel in rel_result.scalars().all():
        rt = await session.get(RelationType, rel.relation_type_id)
        other_entity_id = rel.target_entity_id if rel.source_entity_id == entity_id else rel.source_entity_id
        other_entity = await session.get(Entity, other_entity_id)
        other_et = await session.get(EntityType, other_entity.entity_type_id) if other_entity else None

        is_outgoing = rel.source_entity_id == entity_id

        relations.append({
            "id": str(rel.id),
            "relation_type": rt.slug if rt else None,
            "relation_name": rt.name if is_outgoing else (rt.name_inverse if rt else None),
            "direction": "outgoing" if is_outgoing else "incoming",
            "related_entity": {
                "id": str(other_entity.id),
                "name": other_entity.name,
                "slug": other_entity.slug,
                "type": other_et.slug if other_et else None,
                "type_name": other_et.name if other_et else None,
            } if other_entity else None,
            "attributes": rel.attributes,
            "confidence": rel.confidence_score,
            "verified": rel.human_verified,
        })

    # Get data sources for this entity
    sources = []
    source_query = select(DataSource).where(DataSource.entity_id == entity_id)
    source_result = await session.execute(source_query)
    for src in source_result.scalars().all():
        sources.append({
            "id": str(src.id),
            "name": src.name,
            "url": src.url,
            "is_active": src.is_active,
        })

    # Calculate overview stats
    total_values = sum(len(d["values"]) for d in facets_by_type.values())
    verified_values = sum(d["aggregated"].get("verified", 0) for d in facets_by_type.values())

    return {
        "entity": {
            "id": str(entity.id),
            "name": entity.name,
            "slug": entity.slug,
            "external_id": entity.external_id,
            "hierarchy_path": entity.hierarchy_path,
            "core_attributes": entity.core_attributes,
            "latitude": entity.latitude,
            "longitude": entity.longitude,
        },
        "entity_type": {
            "id": str(entity_type.id),
            "slug": entity_type.slug,
            "name": entity_type.name,
        } if entity_type else None,
        "template": {
            "id": str(template.id),
            "slug": template.slug,
            "name": template.name,
        } if template else None,
        "overview": {
            "total_facet_values": total_values,
            "verified_values": verified_values,
            "facet_type_count": len(facets_by_type),
            "relation_count": len(relations),
            "source_count": len(sources),
        },
        "facets": facets_by_type,
        "relations": relations,
        "sources": sources,
    }


def _deduplicate_values(values: List[Dict], dedup_fields: List[str]) -> List[Dict]:
    """Deduplicate values based on specified fields."""
    seen = {}

    for v in values:
        # Build key from dedup fields
        key_parts = []
        for field in dedup_fields:
            val = v.get("value", {})
            if isinstance(val, dict):
                key_parts.append(str(val.get(field, "")).lower().strip())
            else:
                key_parts.append(str(val).lower().strip())

        key = "|".join(key_parts)

        if key not in seen:
            seen[key] = {
                **v,
                "occurrences": 1,
                "sources": [v.get("document")] if v.get("document") else [],
            }
        else:
            seen[key]["occurrences"] += 1
            seen[key]["confidence"] = max(seen[key]["confidence"], v.get("confidence", 0))
            if v.get("verified"):
                seen[key]["verified"] = True
            if v.get("document") and v["document"] not in seen[key]["sources"]:
                seen[key]["sources"].append(v["document"])

    # Sort by occurrences then confidence
    result = list(seen.values())
    result.sort(key=lambda x: (x["occurrences"], x["confidence"]), reverse=True)

    return result


@router.get("/stats")
async def get_analysis_stats(
    entity_type_slug: Optional[str] = Query(default=None),
    category_id: Optional[UUID] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Get overall analysis statistics."""
    # Entity counts by type
    et_query = select(
        EntityType.slug,
        EntityType.name,
        func.count(Entity.id).label("count")
    ).outerjoin(Entity, Entity.entity_type_id == EntityType.id).group_by(EntityType.id)

    et_result = await session.execute(et_query)
    entity_counts = {row.slug: {"name": row.name, "count": row.count} for row in et_result.fetchall()}

    # Facet value counts by type
    ft_query = select(
        FacetType.slug,
        FacetType.name,
        func.count(FacetValue.id).label("count")
    ).outerjoin(FacetValue, FacetValue.facet_type_id == FacetType.id)

    if category_id:
        ft_query = ft_query.where(FacetValue.category_id == category_id)

    ft_query = ft_query.group_by(FacetType.id)
    ft_result = await session.execute(ft_query)
    facet_counts = {row.slug: {"name": row.name, "count": row.count} for row in ft_result.fetchall()}

    # Relation counts by type
    rt_query = select(
        RelationType.slug,
        RelationType.name,
        func.count(EntityRelation.id).label("count")
    ).outerjoin(EntityRelation, EntityRelation.relation_type_id == RelationType.id).group_by(RelationType.id)

    rt_result = await session.execute(rt_query)
    relation_counts = {row.slug: {"name": row.name, "count": row.count} for row in rt_result.fetchall()}

    # Overall stats
    total_entities = (await session.execute(select(func.count(Entity.id)))).scalar()
    total_facets = (await session.execute(select(func.count(FacetValue.id)))).scalar()
    total_relations = (await session.execute(select(func.count(EntityRelation.id)))).scalar()
    verified_facets = (await session.execute(
        select(func.count(FacetValue.id)).where(FacetValue.human_verified == True)
    )).scalar()

    return {
        "overview": {
            "total_entities": total_entities,
            "total_facet_values": total_facets,
            "total_relations": total_relations,
            "verified_facet_values": verified_facets,
            "verification_rate": round(verified_facets / total_facets, 2) if total_facets > 0 else 0,
        },
        "by_entity_type": entity_counts,
        "by_facet_type": facet_counts,
        "by_relation_type": relation_counts,
    }


