"""Common utilities and helper functions for AI tasks.

This module contains shared constants, helper functions, and utilities
used across all AI task modules.
"""

from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

import structlog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

# =============================================================================
# Constants for PySis facet extraction
# =============================================================================

PYSIS_MAX_CONTEXT_LENGTH = 50000
PYSIS_TEXT_REPR_MAX_LENGTH = 2000
PYSIS_SUMMARY_MAX_LENGTH = 500
PYSIS_MIN_TEXT_LENGTH = 10
PYSIS_MIN_DEDUP_TEXT_LENGTH = 5
PYSIS_BASE_CONFIDENCE = 0.7
PYSIS_CONFIDENCE_BOOST = 0.05
PYSIS_MAX_CONFIDENCE = 0.95
PYSIS_DUPLICATE_SIMILARITY_THRESHOLD = 0.85

# =============================================================================
# Constants for AI API calls
# =============================================================================

AI_EXTRACTION_TEMPERATURE = 0.2
AI_EXTRACTION_MAX_TOKENS = 4000

# =============================================================================
# Default Entity Reference Field Mappings
# =============================================================================
# These mappings define how AI-extracted fields are mapped to entity types.
# Used by document_analyzer and migration tasks. Can be overridden per category.

DEFAULT_FIELD_MAPPINGS = {
    # Direct field mappings (top-level fields)
    "municipality": "territorial_entity",
    "kommune": "territorial_entity",
    "gemeinde": "territorial_entity",
    "stadt": "territorial_entity",
    "region": "territorial_entity",
    "landkreis": "territorial_entity",
    "organization": "organization",
    "organisation": "organization",
    "company": "organization",
    "unternehmen": "organization",
    "firma": "organization",
}

# Nested field mappings - dot notation for nested paths
DEFAULT_NESTED_FIELD_MAPPINGS = {
    "planungsstand.planungsregion": "territorial_entity",
    "planungsstand.behoerde": "organization",
    "offenlage.ansprechpartner": "person",
}

DEFAULT_ARRAY_FIELD_MAPPINGS = {
    # Note: All array mappings use intelligent multi-type matching by default.
    # The entity_type is used as a fallback/hint, but the actual type is determined
    # by similarity to existing entities or intelligent classification.
    "decision_makers": {
        "entity_type": "person",  # Fallback type if no match found
        "name_fields": ["name", "person", "kontakt"],
        "role_field": "role",
        "default_role": "decision_maker",
    },
    "entscheidungstraeger": {
        "entity_type": "person",
        "name_fields": ["name", "person"],
        "role_field": "rolle",
        "default_role": "decision_maker",
    },
    "contacts": {
        "entity_type": "person",
        "name_fields": ["name", "person", "ansprechpartner"],
        "role_field": "role",
        "default_role": "contact",
    },
    "ansprechpartner": {
        "entity_type": "person",
        "name_fields": ["name", "person"],
        "role_field": "rolle",
        "default_role": "contact",
    },
}


# =============================================================================
# Helper Functions
# =============================================================================


async def _get_active_entity_type_slugs(session: "AsyncSession") -> list[str]:
    """
    Get list of active EntityType slugs from database.

    This dynamically loads available entity types instead of using hardcoded values.
    Falls back to common defaults if database query fails.
    """
    from sqlalchemy import select

    from app.models import EntityType

    try:
        result = await session.execute(select(EntityType.slug).where(EntityType.is_active.is_(True)))
        slugs = [row[0] for row in result.fetchall()]
        return slugs if slugs else ["territorial_entity", "person", "organization"]
    except Exception:
        # Fallback if DB not available
        return ["territorial_entity", "person", "organization"]


def _get_default_prompt(category) -> str:
    """Get default extraction prompt based on category."""
    search_terms = ", ".join(category.search_terms) if category.search_terms else "relevante Informationen"
    doc_types = ", ".join(category.document_types) if category.document_types else "Dokumente"

    return f"""
Du bist ein Experte für die Analyse kommunaler Dokumente.

**Zweck dieser Analyse:** {category.purpose}

**Gesuchte Begriffe:** {search_terms}
**Dokumenttypen:** {doc_types}

Analysiere das folgende Dokument und extrahiere AUSFÜHRLICH und DETAILLIERT:

1. **Dokumenttyp**: Welche Art von Dokument ist das? (z.B. Beschluss, Protokoll, Satzung, Bericht)
2. **Datum**: Wann wurde das Dokument erstellt/beschlossen? Gib das genaue Datum an falls vorhanden.
3. **Zusammenfassung**: AUSFÜHRLICHE Zusammenfassung (mindestens 150 Wörter). Beschreibe:
   - Worum geht es im Kern?
   - Welche konkreten Maßnahmen/Entscheidungen werden beschrieben?
   - Wer ist beteiligt (Personen, Organisationen, Behörden)?
   - Welche Zeiträume/Fristen werden genannt?
   - Welche Zahlen/Fakten sind wichtig?
4. **Relevanz**: Wie relevant ist das Dokument für den angegebenen Zweck? (hoch/mittel/gering/keine)
5. **Kernaussagen**: Liste der wichtigsten Aussagen - JEDE mit Seitenreferenz [Seite X]
6. **Erwähnte Regelungen**: Spezifische Regelungen, Beschlüsse, Vorgaben mit Details und Seitenangabe
7. **Betroffene Bereiche**: Geografische oder thematische Bereiche (konkrete Orte, Straßen, Gebiete nennen)
8. **Referenzen**: Erwähnte Gesetze, Verordnungen, andere Dokumente (mit vollständiger Bezeichnung)
9. **Beteiligte Personen**: Namen und Funktionen von genannten Personen
10. **Beteiligte Organisationen**: Behörden, Unternehmen, Vereine etc. mit vollständigem Namen

**Wichtige Hinweise:**
- Sei KONKRET und DETAILLIERT - allgemeine Aussagen wie "verschiedene Maßnahmen" sind nicht hilfreich
- Nenne konkrete Zahlen, Daten, Namen, Orte wenn vorhanden
- Gib bei wichtigen Fakten immer die Seitenzahl an: [Seite X]
- Bei Unsicherheit über fehlenden Kontext: nutze "suggested_additional_pages" Array

Antworte im JSON-Format.
"""


def _calculate_confidence(content: dict[str, Any]) -> float:
    """
    Calculate confidence score based on multiple factors from AI response.

    The score determines how confident we are that the document is valuable.
    Relevant documents with good data quality should score >= 0.7.
    Non-relevant documents should score < 0.5.

    Factors:
    1. is_relevant: Primary relevance indicator (determines base score)
    2. relevanz: Secondary relevance rating with granularity
    3. outreach_priority: Business value indicator
    4. Data quality: pain_points, positive_signals, decision_makers, summary
    """
    # Base score depends on is_relevant flag
    is_relevant = content.get("is_relevant")
    if is_relevant is True:
        score = 0.72  # Start at threshold for relevant docs
    elif is_relevant is False:
        score = 0.25  # Non-relevant docs start low
    else:
        score = 0.45  # Unknown relevance

    # Factor 1: Explicit relevance rating (fine-tune the base)
    relevance = content.get("relevanz", content.get("relevance", ""))
    if isinstance(relevance, str):
        relevance_lower = relevance.lower()
        if relevance_lower == "hoch":
            score += 0.15
        elif relevance_lower == "mittel":
            score += 0.05
        elif relevance_lower == "gering":
            score -= 0.10
        elif relevance_lower == "keine":
            score -= 0.20

    # Factor 2: Outreach priority (business value)
    outreach = content.get("outreach_recommendation", {})
    if isinstance(outreach, dict):
        priority = outreach.get("priority", "")
        if isinstance(priority, str):
            priority_lower = priority.lower()
            if priority_lower == "hoch":
                score += 0.08
            elif priority_lower == "mittel":
                score += 0.03

    # Factor 3: Data quality indicators (reward rich extractions)
    # Supports multiple schema variants (ratsinformationen-nrw, kommunale-news, etc.)
    quality_bonus = 0.0

    # Summary quality (has meaningful summary)
    summary = content.get("summary", "")
    if isinstance(summary, str) and len(summary) > 50:
        quality_bonus += 0.02

    # Pain points / concerns (supports both schema variants)
    pain_points = content.get("pain_points", []) or content.get("concerns_raised", [])
    if isinstance(pain_points, list) and len(pain_points) > 0:
        quality_bonus += min(0.05, len(pain_points) * 0.015)

    # Positive signals / opportunities (supports both schema variants)
    positive_signals = content.get("positive_signals", []) or content.get("opportunities", [])
    if isinstance(positive_signals, list) and len(positive_signals) > 0:
        quality_bonus += min(0.05, len(positive_signals) * 0.015)

    # Decision makers / key_statements with person (supports both schema variants)
    decision_makers = content.get("decision_makers", [])
    if not decision_makers:
        # Fallback: Use key_statements that have a person identified
        key_statements = content.get("key_statements", [])
        if isinstance(key_statements, list):
            decision_makers = [s for s in key_statements if isinstance(s, dict) and s.get("person")]
    if isinstance(decision_makers, list) and len(decision_makers) > 0:
        quality_bonus += min(0.05, len(decision_makers) * 0.02)

    # Municipality identified
    municipality = content.get("municipality", "")
    if isinstance(municipality, str) and municipality and municipality.lower() not in ("", "unbekannt", "null"):
        quality_bonus += 0.02

    # Contact opportunity (kommunale-news schema)
    contact_opp = content.get("contact_opportunity", {})
    if isinstance(contact_opp, dict) and contact_opp.get("exists"):
        quality_bonus += 0.03

    score += quality_bonus

    # Clamp to valid range [0.1, 0.98]
    return max(0.1, min(0.98, round(score, 2)))


# Icon hints for common entity type patterns
ENTITY_TYPE_ICON_HINTS = {
    "person": "mdi-account",
    "menschen": "mdi-account",
    "kontakt": "mdi-account",
    "organization": "mdi-domain",
    "organisation": "mdi-domain",
    "unternehmen": "mdi-domain",
    "firma": "mdi-domain",
    "kommune": "mdi-map-marker",
    "gemeinde": "mdi-map-marker",
    "stadt": "mdi-city",
    "landkreis": "mdi-map",
    "event": "mdi-calendar",
    "veranstaltung": "mdi-calendar",
    "projekt": "mdi-folder",
    "dokument": "mdi-file-document",
}

# Color palette for auto-created entity types
ENTITY_TYPE_COLORS = [
    "#2196F3",  # Blue
    "#4CAF50",  # Green
    "#9C27B0",  # Purple
    "#FF9800",  # Orange
    "#E91E63",  # Pink
    "#00BCD4",  # Cyan
    "#795548",  # Brown
    "#607D8B",  # Blue Grey
]


def _get_icon_for_entity_type(slug: str) -> str:
    """Get appropriate icon for entity type based on slug."""
    slug_lower = slug.lower()
    for pattern, icon in ENTITY_TYPE_ICON_HINTS.items():
        if pattern in slug_lower:
            return icon
    return "mdi-tag"


def _get_color_for_entity_type(slug: str) -> str:
    """Get consistent color for entity type based on slug hash."""
    import hashlib

    hash_val = int(hashlib.md5(slug.encode()).hexdigest(), 16)  # noqa: S324
    return ENTITY_TYPE_COLORS[hash_val % len(ENTITY_TYPE_COLORS)]


def _slug_to_display_name(slug: str) -> tuple[str, str]:
    """Convert slug to display name and plural form."""
    # Convert slug like 'territorial-entity' to 'Territorial Entity'
    name = slug.replace("-", " ").replace("_", " ").title()

    # Simple pluralization (German-aware)
    if name.endswith("e"):
        name_plural = name + "n"
    elif name.endswith("er") or name.endswith("el"):
        name_plural = name
    else:
        name_plural = name + "en"

    return name, name_plural


async def _ensure_entity_type_exists(
    session: "AsyncSession",
    entity_type_slug: str,
    auto_create: bool = True,
) -> Optional["EntityType"]:  # noqa: F821
    """
    Ensure an entity type exists, creating it automatically if needed.

    Args:
        session: Database session
        entity_type_slug: Entity type slug to ensure exists
        auto_create: If True, create the entity type if it doesn't exist

    Returns:
        EntityType if found or created, None if auto_create is False and type doesn't exist
    """
    from sqlalchemy import select

    from app.models import EntityType

    # Check if it already exists
    result = await session.execute(select(EntityType).where(EntityType.slug == entity_type_slug))
    entity_type = result.scalar_one_or_none()

    if entity_type:
        return entity_type

    if not auto_create:
        return None

    # Auto-create the entity type with sensible defaults
    name, name_plural = _slug_to_display_name(entity_type_slug)
    new_type = EntityType(
        slug=entity_type_slug,
        name=name,
        name_plural=name_plural,
        icon=_get_icon_for_entity_type(entity_type_slug),
        color=_get_color_for_entity_type(entity_type_slug),
        description=f"Automatisch erstellter Entity-Typ: {name}",
        is_active=True,
        is_public=True,
    )
    session.add(new_type)
    await session.flush()

    logger.info(
        "Auto-created entity type from AI extraction",
        entity_type_slug=entity_type_slug,
        entity_type_name=name,
    )
    return new_type


# =============================================================================
# Intelligent Entity Type Classification
# =============================================================================


async def classify_by_existing_entities(
    session: "AsyncSession",
    name: str,
    allowed_types: list[str] | None = None,
    similarity_threshold: float = 0.6,
) -> str | None:
    """
    Classify entity type based on similarity to existing entities.

    This is a generic, data-driven approach that works for any entity types:
    - "Niedersächsisches Ministerium..." → similar to other Organizations → "organization"
    - "Max Müller" → similar to other Persons → "person"
    - "Titanic" → similar to other Ships → "ship"

    Args:
        session: Database session
        name: The entity name to classify
        allowed_types: Optional list of entity type slugs to consider
        similarity_threshold: Minimum similarity score (lower than matching threshold)

    Returns:
        Entity type slug of the best matching type, or None if no match found
    """
    from sqlalchemy import select

    from app.models import EntityType
    from app.utils.similarity import find_similar_entities, generate_embedding

    embedding = await generate_embedding(name)
    if not embedding:
        return None

    # Load all (or allowed) entity types
    query = select(EntityType).where(EntityType.is_active.is_(True))
    if allowed_types:
        query = query.where(EntityType.slug.in_(allowed_types))

    result = await session.execute(query)
    entity_types = result.scalars().all()

    best_match: tuple[str | None, float] = (None, 0.0)

    for et in entity_types:
        matches = await find_similar_entities(
            session,
            entity_type_id=et.id,
            name=name,
            threshold=similarity_threshold,
            limit=1,
            embedding=embedding,
        )
        if matches and matches[0][1] > best_match[1]:
            best_match = (et.slug, matches[0][1])

    if best_match[0]:
        logger.debug(
            "Classified entity type by similarity",
            name=name,
            classified_type=best_match[0],
            similarity=round(best_match[1], 3),
        )

    return best_match[0]


async def classify_entity_type(
    session: "AsyncSession",
    name: str,
    allowed_types: list[str] | None = None,
    default_type: str | None = None,
) -> str:
    """
    Generic entity type classification with fallback chain.

    Classification strategy:
    1. Similarity to existing entities (fast, free, data-driven)
    2. Fallback to default type or first allowed type

    This approach is generic and works for any entity types without
    hardcoded patterns. The classification improves as more entities
    are added to the database.

    Args:
        session: Database session
        name: The entity name to classify
        allowed_types: Optional list of entity type slugs to consider
        default_type: Fallback type if no classification possible

    Returns:
        Entity type slug (never None - always returns a valid type)
    """
    # Strategy 1: Classify by similarity to existing entities
    result = await classify_by_existing_entities(session, name, allowed_types)
    if result:
        return result

    # Fallback: Use default or first allowed type
    if default_type:
        return default_type
    if allowed_types:
        return allowed_types[0]
    return "person"  # Ultimate fallback


async def _resolve_entity_any_type(
    session: "AsyncSession",
    name: str,
    allowed_types: list[str] | None = None,
    similarity_threshold: float = 0.85,
) -> tuple[UUID | None, str | None]:
    """
    Search for an entity across ALL active entity types.

    Unlike _resolve_entity which searches in one type, this searches
    across all types and returns the best match with its type.

    Uses a two-phase approach:
    1. Exact match on normalized name (fast, no API needed)
    2. Similarity matching using embeddings (if no exact match)

    Args:
        session: Database session
        name: Entity name to search for
        allowed_types: Optional list of entity type slugs to search in
        similarity_threshold: Minimum similarity score for matching

    Returns:
        Tuple of (entity_id, entity_type_slug) or (None, None) if not found
    """
    from sqlalchemy import select

    from app.models import Entity, EntityType
    from app.utils.similarity import find_similar_entities, generate_embedding
    from app.utils.text import normalize_entity_name

    if not name or len(name.strip()) < 2:
        return None, None

    # Normalize the search name
    name_normalized = normalize_entity_name(name.strip(), country="DE")

    # Load all (or allowed) entity types
    query = select(EntityType).where(EntityType.is_active.is_(True))
    if allowed_types:
        query = query.where(EntityType.slug.in_(allowed_types))

    result = await session.execute(query)
    entity_types = result.scalars().all()

    # Phase 1: Try exact match first (no API needed)
    for et in entity_types:
        entity_result = await session.execute(
            select(Entity).where(
                Entity.entity_type_id == et.id,
                Entity.name_normalized == name_normalized,
                Entity.is_active.is_(True),
            )
        )
        entity = entity_result.scalar_one_or_none()
        if entity:
            logger.debug(
                "Found entity via exact match (multi-type)",
                name=name,
                entity_id=str(entity.id),
                entity_type=et.slug,
            )
            return entity.id, et.slug

    # Phase 2: Similarity matching (requires embedding API)
    embedding = await generate_embedding(name)
    if not embedding:
        logger.warning(
            "Could not generate embedding for multi-type entity search",
            name=name,
        )
        return None, None

    best_match: tuple[Any | None, float, str | None] = (None, 0.0, None)

    for et in entity_types:
        matches = await find_similar_entities(
            session,
            entity_type_id=et.id,
            name=name,
            threshold=similarity_threshold,
            limit=1,
            embedding=embedding,
        )
        if matches and matches[0][1] > best_match[1]:
            entity, score = matches[0]
            best_match = (entity, score, et.slug)

    if best_match[0]:
        logger.debug(
            "Found entity via similarity (multi-type)",
            name=name,
            entity_id=str(best_match[0].id),
            entity_type=best_match[2],
            similarity=round(best_match[1], 3),
        )
        return best_match[0].id, best_match[2]

    return None, None


async def _resolve_entity_smart(
    session: "AsyncSession",
    name: str,
    allowed_types: list[str] | None = None,
    auto_create: bool = True,
    default_type: str | None = None,
) -> tuple[UUID | None, str]:
    """
    Intelligent entity resolution with automatic type classification.

    This is the main entry point for smart entity resolution:
    1. Multi-type search: Find existing entity across all types
    2. Classification: If not found, intelligently determine the type
    3. Creation: If auto_create, create entity with the classified type

    Args:
        session: Database session
        name: Entity name to resolve
        allowed_types: Optional list of entity type slugs to consider
        auto_create: If True, create entity if not found (default: True)
        default_type: Fallback type for classification/creation

    Returns:
        Tuple of (entity_id, entity_type_slug)
        - entity_id may be None if not found and auto_create=False
        - entity_type_slug is always returned (classified type)
    """
    # Phase 1: Multi-type search for existing entity
    entity_id, found_type = await _resolve_entity_any_type(session, name, allowed_types)
    if entity_id:
        return entity_id, found_type

    # Phase 2: Classify the entity type
    classified_type = await classify_entity_type(session, name, allowed_types, default_type)

    # Phase 3: Create entity if requested
    if auto_create:
        entity_id = await _resolve_entity(session, classified_type, name, auto_create=True)
        logger.info(
            "Created entity with classified type",
            name=name,
            entity_type=classified_type,
            entity_id=str(entity_id) if entity_id else None,
        )
        return entity_id, classified_type

    return None, classified_type


async def _resolve_entity(
    session: "AsyncSession",
    entity_type_slug: str,
    entity_name: str,
    similarity_threshold: float = 0.85,
    auto_create: bool = True,
) -> UUID | None:
    """
    Resolve an entity name to its UUID using exact and similarity matching.
    Optionally creates a new entity if none found.
    Also auto-creates standard entity types if they don't exist.

    This function delegates to EntityMatchingService for consistent behavior
    across the codebase, while adding AI extraction-specific logic.

    Args:
        session: Database session
        entity_type_slug: Entity type slug
        entity_name: Entity name to resolve
        similarity_threshold: Minimum similarity score for fuzzy matching (default: 0.85)
        auto_create: If True, create a new entity when no match is found (default: True)

    Returns:
        Entity UUID if found or created, None otherwise
    """
    from services.entity_matching_service import EntityMatchingService

    # Skip invalid names
    if not entity_name or len(entity_name.strip()) < 2:
        return None

    entity_name = entity_name.strip()

    try:
        # Ensure entity type exists (auto-creates standard types like person, organization)
        entity_type = await _ensure_entity_type_exists(session, entity_type_slug)

        if not entity_type:
            logger.debug(
                "Entity type not found and not a standard type",
                entity_type_slug=entity_type_slug,
                entity_name=entity_name,
            )
            return None

        # Delegate to EntityMatchingService for consistent entity resolution
        # This uses the unified matching logic: external_id, normalized name,
        # core name, embedding similarity, and composite entity detection
        service = EntityMatchingService(session)

        # If auto_create is False, use find_entity method (search only, no create)
        if not auto_create:
            entity = await service.find_entity(
                entity_type_slug=entity_type_slug,
                name=entity_name,
                country="DE",
                similarity_threshold=similarity_threshold,
            )
            return entity.id if entity else None

        # With auto_create=True, use get_or_create with AI extraction marker
        entity = await service.get_or_create_entity(
            entity_type_slug=entity_type_slug,
            name=entity_name,
            country="DE",
            core_attributes={"auto_created": True, "source": "ai_extraction"},
            similarity_threshold=similarity_threshold,
            auto_deduplicate=True,
        )

        if entity:
            logger.debug(
                "Resolved entity via EntityMatchingService",
                entity_type=entity_type_slug,
                entity_name=entity_name,
                entity_id=str(entity.id),
            )
            return entity.id

        return None

    except Exception as e:
        logger.warning(
            "Failed to resolve entity",
            entity_type=entity_type_slug,
            entity_name=entity_name,
            error=str(e),
        )
        return None


def _texts_similar(text1: str, text2: str, threshold: float = 0.7) -> bool:
    """
    Check if two texts are similar using Jaccard similarity on word sets.

    Args:
        text1: First text to compare
        text2: Second text to compare
        threshold: Minimum similarity score (0.0-1.0)

    Returns:
        True if texts are similar above threshold
    """
    if not text1 or not text2:
        return False

    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    intersection = len(words1 & words2)
    union = len(words1 | words2)

    return (intersection / union) >= threshold if union > 0 else False


async def _create_entity_facet_value(
    session: "AsyncSession",
    primary_entity_id: UUID,
    target_entity_id: UUID,
    target_entity_type_slug: str,
    target_entity_name: str,
    role: str,
    document_id: UUID | None = None,
    category_id: UUID | None = None,
    confidence_score: float = 0.7,
    additional_data: dict[str, Any] | None = None,
) -> UUID | None:
    """
    Create a FacetValue linking a primary entity to a target entity.

    Automatically finds a matching FacetType based on:
    - allows_entity_reference = True
    - target_entity_type_slugs contains the target entity's type
    - applicable_entity_type_slugs contains the primary entity's type

    This creates a bidirectional relationship:
    - The primary entity gets a facet linking to the target entity
    - Via target_entity_id, the system can traverse from facet to target entity

    Args:
        session: Database session
        primary_entity_id: Entity to attach the facet to
        target_entity_id: Target entity to link
        target_entity_type_slug: Slug of the target entity's type (e.g., "person")
        target_entity_name: Name of the target entity
        role: Role/position of the target entity
        document_id: Source document ID (optional)
        category_id: Category context (optional)
        confidence_score: AI confidence score
        additional_data: Additional facet value data (email, phone, etc.)

    Returns:
        FacetValue ID if created, None otherwise
    """
    from sqlalchemy import func, select
    from sqlalchemy.orm import selectinload

    from app.models import Entity, FacetType, FacetValue
    from app.models.facet_value import FacetValueSourceType

    try:
        # Get primary entity to check its type
        primary_entity = await session.get(Entity, primary_entity_id, options=[selectinload(Entity.entity_type)])
        if not primary_entity or not primary_entity.entity_type:
            logger.debug(
                "Primary entity or type not found",
                primary_entity_id=str(primary_entity_id),
            )
            return None

        primary_type_slug = primary_entity.entity_type.slug

        # Find matching FacetType that:
        # 1. allows_entity_reference = True
        # 2. target_entity_type_slugs contains target_entity_type_slug
        # 3. applicable_entity_type_slugs contains primary_type_slug (or is empty = all types)
        result = await session.execute(
            select(FacetType).where(
                FacetType.is_active.is_(True),
                FacetType.allows_entity_reference.is_(True),
            )
        )
        facet_types = result.scalars().all()

        matching_facet_type = None
        for ft in facet_types:
            # Check if this FacetType can link to the target entity type
            target_types = ft.target_entity_type_slugs or []
            if target_entity_type_slug not in target_types:
                continue

            # Check if this FacetType is applicable to the primary entity type
            applicable_types = ft.applicable_entity_type_slugs or []
            if applicable_types and primary_type_slug not in applicable_types:
                continue

            matching_facet_type = ft
            break

        if not matching_facet_type:
            logger.debug(
                "No matching FacetType found for entity reference",
                target_entity_type=target_entity_type_slug,
                primary_entity_type=primary_type_slug,
            )
            return None

        # Build text representation first (needed for dedup check)
        text_parts = [target_entity_name]
        if role:
            text_parts.append(f"({role})")
        text_representation = " ".join(text_parts)

        # Check if facet already exists by dedup index (entity_id, facet_type_id, md5(text_representation))
        existing = await session.execute(
            select(FacetValue).where(
                FacetValue.entity_id == primary_entity_id,
                FacetValue.facet_type_id == matching_facet_type.id,
                func.md5(FacetValue.text_representation) == func.md5(text_representation),
            )
        )
        existing_facet = existing.scalar_one_or_none()

        if existing_facet:
            # Update target_entity_id if not set, and increment occurrence count
            updated = False
            if not existing_facet.target_entity_id:
                existing_facet.target_entity_id = target_entity_id
                updated = True
            existing_facet.occurrence_count += 1
            existing_facet.last_seen = existing_facet.updated_at
            logger.debug(
                "Entity facet already exists, updating",
                facet_id=str(existing_facet.id),
                facet_type=matching_facet_type.slug,
                target_entity_linked=updated,
            )
            return existing_facet.id

        # Build value dict
        value = {
            "name": target_entity_name,
            "role": role,
            "entity_type": target_entity_type_slug,
        }
        if additional_data:
            value.update(additional_data)

        # Create new FacetValue
        new_facet = FacetValue(
            entity_id=primary_entity_id,
            facet_type_id=matching_facet_type.id,
            category_id=category_id,
            value=value,
            text_representation=text_representation,
            source_type=FacetValueSourceType.DOCUMENT,
            source_document_id=document_id,
            target_entity_id=target_entity_id,
            confidence_score=confidence_score,
            is_active=True,
        )
        session.add(new_facet)
        await session.flush()

        logger.info(
            "Created entity facet value",
            entity_id=str(primary_entity_id),
            target_entity_id=str(target_entity_id),
            target_entity_name=target_entity_name,
            facet_type=matching_facet_type.slug,
            facet_id=str(new_facet.id),
        )
        return new_facet.id

    except Exception as e:
        logger.warning(
            "Failed to create entity facet value",
            primary_entity_id=str(primary_entity_id),
            target_entity_id=str(target_entity_id),
            error=str(e),
        )
        return None


# Alias for backwards compatibility
_create_contact_facet_value = _create_entity_facet_value
