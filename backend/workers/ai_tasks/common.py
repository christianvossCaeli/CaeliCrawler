"""Common utilities and helper functions for AI tasks.

This module contains shared constants, helper functions, and utilities
used across all AI task modules.
"""

from typing import Any, Dict, Optional, TYPE_CHECKING
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
# Helper Functions
# =============================================================================


def _get_default_prompt(category) -> str:
    """Get default extraction prompt based on category."""
    search_terms = ", ".join(category.search_terms) if category.search_terms else "relevante Informationen"
    doc_types = ", ".join(category.document_types) if category.document_types else "Dokumente"

    return f"""
Du bist ein Experte für die Analyse kommunaler Dokumente.

**Zweck dieser Analyse:** {category.purpose}

**Gesuchte Begriffe:** {search_terms}
**Dokumenttypen:** {doc_types}

Analysiere das folgende Dokument und extrahiere strukturiert:

1. **Dokumenttyp**: Welche Art von Dokument ist das?
2. **Datum**: Wann wurde das Dokument erstellt/beschlossen?
3. **Zusammenfassung**: Kurze Zusammenfassung (max 200 Wörter)
4. **Relevanz**: Wie relevant ist das Dokument für den angegebenen Zweck? (hoch/mittel/gering/keine)
5. **Kernaussagen**: Liste der wichtigsten Aussagen
6. **Erwähnte Regelungen**: Spezifische Regelungen, Beschlüsse, Vorgaben
7. **Betroffene Bereiche**: Geografische oder thematische Bereiche
8. **Referenzen**: Erwähnte Gesetze, Verordnungen, andere Dokumente

Antworte im JSON-Format.
"""


def _calculate_confidence(content: Dict[str, Any]) -> float:
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


async def _resolve_entity(
    session: "AsyncSession",
    entity_type_slug: str,
    entity_name: str,
    similarity_threshold: float = 0.85,
) -> Optional[UUID]:
    """
    Resolve an entity name to its UUID using exact and similarity matching.

    Uses a two-phase approach:
    1. Exact match on normalized name
    2. Similarity matching if no exact match found

    Args:
        session: Database session
        entity_type_slug: Entity type slug
        entity_name: Entity name to resolve
        similarity_threshold: Minimum similarity score for fuzzy matching (default: 0.85)

    Returns:
        Entity UUID if found, None otherwise
    """
    from app.models import Entity, EntityType
    from app.utils.text import normalize_entity_name
    from app.utils.similarity import find_similar_entities
    from sqlalchemy import select

    try:
        # Get entity type
        et_result = await session.execute(
            select(EntityType).where(EntityType.slug == entity_type_slug)
        )
        entity_type = et_result.scalar_one_or_none()

        if not entity_type:
            return None

        # Phase 1: Exact match on normalized name
        name_normalized = normalize_entity_name(entity_name, country="DE")

        entity_result = await session.execute(
            select(Entity).where(
                Entity.entity_type_id == entity_type.id,
                Entity.name_normalized == name_normalized,
                Entity.is_active.is_(True),
            )
        )
        entity = entity_result.scalar_one_or_none()

        if entity:
            return entity.id

        # Phase 2: Similarity matching
        similar_entities = await find_similar_entities(
            session,
            entity_type.id,
            entity_name,
            threshold=similarity_threshold,
            limit=1,
        )

        if similar_entities:
            matched_entity, score = similar_entities[0]
            logger.info(
                "Resolved entity via similarity matching",
                search_name=entity_name,
                matched_name=matched_entity.name,
                similarity_score=score,
            )
            return matched_entity.id

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
