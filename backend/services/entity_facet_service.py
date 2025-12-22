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
    RelationType,
    EntityRelation,
)
from app.models.facet_value import FacetValueSourceType
from app.utils.text import normalize_name, create_slug

logger = structlog.get_logger()


async def get_or_create_entity(
    session: AsyncSession,
    entity_type_slug: str,
    name: str,
    external_id: Optional[str] = None,
    parent_id: Optional[UUID] = None,
    core_attributes: Optional[Dict[str, Any]] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    country: str = "DE",
    similarity_threshold: float = 0.85,
) -> Optional[Entity]:
    """
    Get or create an entity by name and type.

    Delegates to EntityMatchingService for consistent:
    - Name normalization
    - Duplicate detection (with optional fuzzy matching)
    - Race-condition-safe creation

    Args:
        session: Database session
        entity_type_slug: The entity type slug
        name: Entity name
        external_id: Optional external ID
        parent_id: Optional parent entity ID
        core_attributes: Optional JSON attributes
        latitude: Optional latitude
        longitude: Optional longitude
        country: Country code for normalization (default: DE)
        similarity_threshold: Threshold for fuzzy matching (default: 0.85, set to 1.0 for exact only)

    Returns:
        Entity if found or created, None if entity_type not found.
    """
    from services.entity_matching_service import EntityMatchingService

    service = EntityMatchingService(session)
    return await service.get_or_create_entity(
        entity_type_slug=entity_type_slug,
        name=name,
        country=country,
        external_id=external_id,
        core_attributes=core_attributes,
        parent_id=parent_id,
        latitude=latitude,
        longitude=longitude,
        similarity_threshold=similarity_threshold,
    )


async def get_facet_type_by_slug(session: AsyncSession, slug: str) -> Optional[FacetType]:
    """Get facet type by slug."""
    result = await session.execute(
        select(FacetType).where(FacetType.slug == slug, FacetType.is_active.is_(True))
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
    source_type: FacetValueSourceType = FacetValueSourceType.DOCUMENT,
) -> Optional[FacetValue]:
    """Create a new facet value.

    Args:
        session: Database session
        entity_id: UUID of the entity
        facet_type_id: UUID of the facet type
        value: Structured value dict
        text_representation: Human-readable text representation
        confidence_score: Confidence score (0-1)
        source_document_id: Optional source document UUID
        source_url: Optional source URL
        event_date: Optional event date
        source_type: How this value was created (default: DOCUMENT for AI extraction)

    Returns:
        Created FacetValue, or None if duplicate was detected by database constraint
    """
    from sqlalchemy.exc import IntegrityError

    facet_value = FacetValue(
        entity_id=entity_id,
        facet_type_id=facet_type_id,
        value=value,
        text_representation=text_representation[:2000] if text_representation else "",
        confidence_score=confidence_score,
        source_document_id=source_document_id,
        source_url=source_url,
        event_date=event_date,
        source_type=source_type,
    )
    session.add(facet_value)

    try:
        await session.flush()
        return facet_value
    except IntegrityError as e:
        # Duplicate detected by database unique index - rollback and return None
        if "ix_facet_values_dedup" in str(e):
            await session.rollback()
            logger.debug(
                "Duplicate facet value prevented by database",
                entity_id=str(entity_id),
                facet_type_id=str(facet_type_id),
                text_preview=text_representation[:50] if text_representation else "",
            )
            return None
        raise  # Re-raise if it's a different IntegrityError


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

    # Determine municipality name from AI extraction
    municipality_name = (
        content.get("municipality")
        or content.get("source_location")
    )

    if not municipality_name or municipality_name.lower() in ("", "unbekannt", "null"):
        logger.debug("No municipality name found, skipping facet creation")
        return {}

    # Get or create territorial entity (municipality/city/town)
    entity = await get_or_create_entity(
        session,
        entity_type_slug="territorial_entity",
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


# =============================================================================
# Relation Functions (shared between services)
# =============================================================================


async def get_relation_type_by_slug(
    session: AsyncSession, slug: str
) -> Optional[RelationType]:
    """Get relation type by slug.

    Args:
        session: Database session
        slug: Relation type slug (e.g., 'attends', 'works_for', 'located_in')

    Returns:
        RelationType if found and active, None otherwise
    """
    result = await session.execute(
        select(RelationType).where(
            RelationType.slug == slug, RelationType.is_active.is_(True)
        )
    )
    return result.scalar_one_or_none()


async def create_relation(
    session: AsyncSession,
    source_entity_id: UUID,
    target_entity_id: UUID,
    relation_type_id: UUID,
    attributes: Optional[Dict[str, Any]] = None,
    source_document_id: Optional[UUID] = None,
    confidence_score: float = 0.5,
) -> Optional[EntityRelation]:
    """Create a relation between two entities if it doesn't exist.

    Args:
        session: Database session
        source_entity_id: UUID of the source entity
        target_entity_id: UUID of the target entity
        relation_type_id: UUID of the relation type
        attributes: Optional dict of additional attributes
        source_document_id: Optional source document UUID
        confidence_score: Confidence score (0-1)

    Returns:
        EntityRelation (existing or newly created)
    """
    # Check for existing relation
    result = await session.execute(
        select(EntityRelation).where(
            EntityRelation.source_entity_id == source_entity_id,
            EntityRelation.target_entity_id == target_entity_id,
            EntityRelation.relation_type_id == relation_type_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    relation = EntityRelation(
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        relation_type_id=relation_type_id,
        attributes=attributes or {},
        source_document_id=source_document_id,
        confidence_score=confidence_score,
    )
    session.add(relation)
    return relation
