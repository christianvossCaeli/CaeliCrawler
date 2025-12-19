"""Service for Entity-Facet System integration with AI extraction."""

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Entity,
    EntityType,
    FacetType,
    FacetValue,
    ExtractedData,
    DataSource,
)

logger = structlog.get_logger()


def normalize_name(name: str) -> str:
    """Normalize entity name for matching."""
    # Lowercase
    result = name.lower()
    # German umlaut replacements
    replacements = {"ae": "ae", "oe": "oe", "ue": "ue", "ss": "ss"}
    for old, new in replacements.items():
        result = result.replace(old, new)
    # Remove diacritics
    result = unicodedata.normalize("NFD", result)
    result = "".join(c for c in result if not unicodedata.combining(c))
    # Remove non-alphanumeric
    result = re.sub(r"[^a-z0-9]", "", result)
    return result


def create_slug(name: str) -> str:
    """Create URL-safe slug from name."""
    result = name.lower()
    # German umlaut replacements
    replacements = {"ae": "ae", "oe": "oe", "ue": "ue", "ss": "ss", " ": "-"}
    for old, new in replacements.items():
        result = result.replace(old, new)
    # Remove special chars except hyphens
    result = re.sub(r"[^a-z0-9-]", "", result)
    # Remove multiple hyphens
    result = re.sub(r"-+", "-", result)
    return result.strip("-")


async def get_or_create_entity(
    session: AsyncSession,
    entity_type_slug: str,
    name: str,
    external_id: Optional[str] = None,
    parent_id: Optional[UUID] = None,
    core_attributes: Optional[Dict[str, Any]] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> Optional[Entity]:
    """
    Get or create an entity by name and type.

    Returns None if entity_type not found.
    """
    # Get entity type
    result = await session.execute(
        select(EntityType).where(EntityType.slug == entity_type_slug)
    )
    entity_type = result.scalar_one_or_none()
    if not entity_type:
        logger.warning("Entity type not found", slug=entity_type_slug)
        return None

    # Try to find existing entity
    name_normalized = normalize_name(name)
    slug = create_slug(name)

    result = await session.execute(
        select(Entity).where(
            Entity.entity_type_id == entity_type.id,
            Entity.name_normalized == name_normalized,
        )
    )
    entity = result.scalar_one_or_none()

    if entity:
        logger.debug("Found existing entity", entity_id=str(entity.id), name=name)
        return entity

    # Create new entity
    entity = Entity(
        entity_type_id=entity_type.id,
        name=name,
        name_normalized=name_normalized,
        slug=slug,
        external_id=external_id,
        parent_id=parent_id,
        core_attributes=core_attributes or {},
        latitude=latitude,
        longitude=longitude,
    )
    session.add(entity)
    await session.flush()

    logger.info("Created new entity", entity_id=str(entity.id), name=name, type=entity_type_slug)
    return entity


async def get_facet_type_by_slug(session: AsyncSession, slug: str) -> Optional[FacetType]:
    """Get facet type by slug."""
    result = await session.execute(
        select(FacetType).where(FacetType.slug == slug, FacetType.is_active == True)
    )
    return result.scalar_one_or_none()


async def create_facet_value(
    session: AsyncSession,
    entity_id: UUID,
    facet_type_id: UUID,
    value: Dict[str, Any],
    text_representation: str,
    confidence_score: float = 0.5,
    source_document_id: Optional[UUID] = None,
    source_url: Optional[str] = None,
    event_date: Optional[datetime] = None,
) -> FacetValue:
    """Create a new facet value."""
    facet_value = FacetValue(
        entity_id=entity_id,
        facet_type_id=facet_type_id,
        value=value,
        text_representation=text_representation[:2000] if text_representation else "",
        confidence_score=confidence_score,
        source_document_id=source_document_id,
        source_url=source_url,
        event_date=event_date,
    )
    session.add(facet_value)
    return facet_value


async def check_duplicate_facet(
    session: AsyncSession,
    entity_id: UUID,
    facet_type_id: UUID,
    text_representation: str,
    similarity_threshold: float = 0.9,
) -> bool:
    """
    Check if a similar facet value already exists.

    Uses simple string matching for now. Could be enhanced with embeddings.
    """
    # Normalize for comparison
    normalized = normalize_name(text_representation)

    # Get existing facet values for this entity and type
    result = await session.execute(
        select(FacetValue).where(
            FacetValue.entity_id == entity_id,
            FacetValue.facet_type_id == facet_type_id,
        )
    )
    existing = result.scalars().all()

    for fv in existing:
        existing_normalized = normalize_name(fv.text_representation or "")
        # Simple substring check
        if normalized in existing_normalized or existing_normalized in normalized:
            return True
        # Check for high similarity (Jaccard-like)
        if len(normalized) > 10 and len(existing_normalized) > 10:
            set1 = set(normalized.split())
            set2 = set(existing_normalized.split())
            if set1 and set2:
                intersection = len(set1 & set2)
                union = len(set1 | set2)
                if union > 0 and intersection / union >= similarity_threshold:
                    return True

    return False


async def convert_extraction_to_facets(
    session: AsyncSession,
    extracted_data: ExtractedData,
    source: Optional[DataSource] = None,
) -> Dict[str, int]:
    """
    Convert ExtractedData to FacetValues in the Entity-Facet system.

    Returns dict with counts of created facet values per type.
    """
    content = extracted_data.final_content
    if not content:
        return {}

    # Determine municipality name
    municipality_name = (
        content.get("municipality")
        or content.get("source_location")
        or (source.location_name if source else None)
    )

    if not municipality_name or municipality_name.lower() in ("", "unbekannt", "null"):
        logger.debug("No municipality name found, skipping facet creation")
        return {}

    # Get or create municipality entity
    entity = await get_or_create_entity(
        session,
        entity_type_slug="municipality",
        name=municipality_name,
    )
    if not entity:
        return {}

    # Get facet types
    pain_point_type = await get_facet_type_by_slug(session, "pain_point")
    positive_signal_type = await get_facet_type_by_slug(session, "positive_signal")
    contact_type = await get_facet_type_by_slug(session, "contact")
    summary_type = await get_facet_type_by_slug(session, "summary")

    counts = {"pain_point": 0, "positive_signal": 0, "contact": 0, "summary": 0}
    base_confidence = extracted_data.confidence_score or 0.5

    # Process Pain Points
    if pain_point_type:
        pain_points = content.get("pain_points", []) or content.get("concerns_raised", [])
        for pp in pain_points if isinstance(pain_points, list) else []:
            if isinstance(pp, dict):
                text = pp.get("description") or pp.get("text") or pp.get("concern", "")
                severity = pp.get("severity", "mittel")
                pp_type = pp.get("type", "Sonstiges")
            elif isinstance(pp, str):
                text = pp
                severity = "mittel"
                pp_type = "Sonstiges"
            else:
                continue

            if not text or len(text) < 10:
                continue

            # Check for duplicates
            is_dupe = await check_duplicate_facet(
                session, entity.id, pain_point_type.id, text
            )
            if is_dupe:
                continue

            await create_facet_value(
                session,
                entity_id=entity.id,
                facet_type_id=pain_point_type.id,
                value={"description": text, "type": pp_type, "severity": severity},
                text_representation=text,
                confidence_score=min(0.95, base_confidence + 0.05),
                source_document_id=extracted_data.document_id,
            )
            counts["pain_point"] += 1

    # Process Positive Signals
    if positive_signal_type:
        positive_signals = content.get("positive_signals", []) or content.get("opportunities", [])
        for ps in positive_signals if isinstance(positive_signals, list) else []:
            if isinstance(ps, dict):
                text = ps.get("description") or ps.get("text") or ps.get("opportunity", "")
                ps_type = ps.get("type", "Sonstiges")
            elif isinstance(ps, str):
                text = ps
                ps_type = "Sonstiges"
            else:
                continue

            if not text or len(text) < 10:
                continue

            is_dupe = await check_duplicate_facet(
                session, entity.id, positive_signal_type.id, text
            )
            if is_dupe:
                continue

            await create_facet_value(
                session,
                entity_id=entity.id,
                facet_type_id=positive_signal_type.id,
                value={"description": text, "type": ps_type},
                text_representation=text,
                confidence_score=min(0.95, base_confidence + 0.05),
                source_document_id=extracted_data.document_id,
            )
            counts["positive_signal"] += 1

    # Process Decision Makers / Contacts
    if contact_type:
        decision_makers = content.get("decision_makers", [])
        if not decision_makers:
            # Fallback to key_statements with person
            key_statements = content.get("key_statements", [])
            if isinstance(key_statements, list):
                decision_makers = [
                    {"name": s.get("person"), "role": s.get("role"), "statement": s.get("statement")}
                    for s in key_statements
                    if isinstance(s, dict) and s.get("person")
                ]

        for dm in decision_makers if isinstance(decision_makers, list) else []:
            if not isinstance(dm, dict):
                continue

            name = dm.get("name", "")
            if not name or len(name) < 3:
                continue

            role = dm.get("role", dm.get("position", ""))
            email = dm.get("email", "")
            phone = dm.get("phone", "")
            statement = dm.get("statement", "")
            sentiment = dm.get("sentiment", "neutral")

            text_repr = f"{name}"
            if role:
                text_repr += f" ({role})"

            is_dupe = await check_duplicate_facet(
                session, entity.id, contact_type.id, name
            )
            if is_dupe:
                continue

            await create_facet_value(
                session,
                entity_id=entity.id,
                facet_type_id=contact_type.id,
                value={
                    "name": name,
                    "role": role,
                    "email": email,
                    "phone": phone,
                    "statement": statement,
                    "sentiment": sentiment,
                },
                text_representation=text_repr,
                confidence_score=min(0.9, base_confidence),
                source_document_id=extracted_data.document_id,
            )
            counts["contact"] += 1

    # Process Summary
    if summary_type:
        summary = content.get("summary", "")
        if isinstance(summary, str) and len(summary) > 20:
            # Summaries are per-document, so we allow "duplicates"
            await create_facet_value(
                session,
                entity_id=entity.id,
                facet_type_id=summary_type.id,
                value={"text": summary},
                text_representation=summary[:500],
                confidence_score=base_confidence,
                source_document_id=extracted_data.document_id,
            )
            counts["summary"] += 1

    logger.info(
        "Created facet values from extraction",
        entity_id=str(entity.id),
        entity_name=municipality_name,
        counts=counts,
    )

    return counts


async def link_source_to_entity(
    session: AsyncSession,
    source: DataSource,
) -> Optional[Entity]:
    """
    Link a DataSource to an Entity based on location_name.

    Returns the linked entity or None if not found/created.
    """
    if not source.location_name:
        return None

    if source.entity_id:
        # Already linked
        entity = await session.get(Entity, source.entity_id)
        if entity:
            return entity

    # Get or create municipality entity
    entity = await get_or_create_entity(
        session,
        entity_type_slug="municipality",
        name=source.location_name,
        core_attributes={
            "country": source.country,
            "admin_level_1": source.admin_level_1,
            "region": source.region,
        },
    )

    if entity:
        source.entity_id = entity.id
        logger.info(
            "Linked source to entity",
            source_id=str(source.id),
            entity_id=str(entity.id),
            entity_name=entity.name,
        )

    return entity
