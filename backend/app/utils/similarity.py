"""
Embedding-based similarity matching for entity deduplication.

Uses OpenAI text-embedding-3-large vectors with pgvector for efficient
semantic similarity search. This approach is:
- Language-agnostic (works for any language)
- Entity-type-agnostic (works for persons, organizations, places, etc.)
- Handles synonyms and variations automatically

Examples of variations that would match:
- "Dr. Hans Müller" vs "Hans Müller" (title variations)
- "Deutsche Bank AG" vs "Deutsche Bank" (legal suffixes)
- "Microsoft Corporation" vs "Microsoft Corp." (abbreviations)
- "Regionalverband Ruhr" vs "Metropole Ruhr" (synonyms)
"""

import os
import uuid
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

import structlog
from sqlalchemy import select, literal
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.models import Entity

logger = structlog.get_logger(__name__)

# Configuration via environment variables
DEFAULT_SIMILARITY_THRESHOLD = float(os.getenv("ENTITY_SIMILARITY_THRESHOLD", "0.85"))
EMBEDDING_DIMENSIONS = 1536  # text-embedding-3-large with dimension reduction

# Monitoring counters (can be exposed via metrics endpoint)
_similarity_stats = {
    "searches": 0,
    "matches_found": 0,
    "embeddings_generated": 0,
    "cache_hits": 0,
}


async def find_similar_entities(
    session: AsyncSession,
    entity_type_id: uuid.UUID,
    name: str,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    limit: int = 5,
    embedding: Optional[List[float]] = None,
) -> List[Tuple["Entity", float]]:
    """
    Find entities with similar names using embedding-based similarity.

    Uses pgvector's native cosine distance operator for efficient database-level
    filtering and sorting. This scales to millions of entities.

    Args:
        session: Database session
        entity_type_id: UUID of the entity type to search
        name: Name to find similar entities for
        threshold: Minimum similarity score (0.0 - 1.0)
        limit: Maximum number of matches to return
        embedding: Pre-computed embedding (if available, saves API call)

    Returns:
        List of (Entity, similarity_score) tuples, sorted by score descending
    """
    from app.models import Entity

    _similarity_stats["searches"] += 1

    if not name or len(name) < 2:
        return []

    # If no embedding provided, generate one
    if embedding is None:
        embedding = await generate_entity_embedding(name)
        _similarity_stats["embeddings_generated"] += 1

    if embedding is None:
        logger.warning("Could not generate embedding for similarity search", name=name)
        return []

    # Use pgvector's native cosine distance for efficient DB-level filtering
    # cosine_distance returns 0 for identical vectors, 2 for opposite vectors
    # We convert: similarity = 1 - distance
    # Filter: distance <= (1 - threshold)
    max_distance = 1.0 - threshold

    # Build query using pgvector's cosine_distance method
    # This uses the HNSW index for fast approximate nearest neighbor search
    distance_expr = Entity.name_embedding.cosine_distance(embedding)

    result = await session.execute(
        select(Entity, (literal(1.0) - distance_expr).label("similarity"))
        .where(
            Entity.entity_type_id == entity_type_id,
            Entity.is_active.is_(True),
            Entity.name_embedding.isnot(None),
            distance_expr <= max_distance,  # Filter by threshold in DB
        )
        .order_by(distance_expr)  # Sort by similarity in DB
        .limit(limit)
    )

    matches: List[Tuple[Entity, float]] = []
    for row in result:
        entity = row[0]
        similarity = float(row[1])
        matches.append((entity, similarity))
        _similarity_stats["matches_found"] += 1

        logger.info(
            "Found similar entity",
            search_name=name,
            matched_name=entity.name,
            matched_id=str(entity.id),
            similarity=round(similarity, 3),
            threshold=threshold,
        )

    if not matches:
        logger.debug(
            "No similar entities found",
            search_name=name,
            entity_type_id=str(entity_type_id),
            threshold=threshold,
        )

    return matches


def get_similarity_stats() -> dict:
    """
    Get current similarity matching statistics.

    Returns:
        Dictionary with search/match/embedding counts
    """
    return _similarity_stats.copy()


def reset_similarity_stats() -> None:
    """Reset similarity matching statistics."""
    global _similarity_stats
    _similarity_stats = {
        "searches": 0,
        "matches_found": 0,
        "embeddings_generated": 0,
        "cache_hits": 0,
    }


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors (fallback/utility)."""
    if len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


async def generate_entity_embedding(name: str) -> Optional[List[float]]:
    """
    Generate embedding for an entity name.

    Uses the AI service to generate text embeddings.

    Args:
        name: Entity name to embed

    Returns:
        Embedding vector or None if generation failed
    """
    from services.ai_service import AIService

    if not name or len(name) < 2:
        return None

    try:
        ai_service = AIService()
        embedding = await ai_service.generate_embedding(name)
        return embedding
    except Exception as e:
        logger.error("Failed to generate embedding", name=name, error=str(e))
        return None


async def update_entity_embedding(
    session: AsyncSession,
    entity_id: uuid.UUID,
    embedding: Optional[List[float]] = None,
    name: Optional[str] = None,
) -> bool:
    """
    Update an entity's name embedding.

    Args:
        session: Database session
        entity_id: Entity ID to update
        embedding: Pre-computed embedding (if None, will generate from name)
        name: Entity name (required if embedding is None)

    Returns:
        True if update successful, False otherwise
    """
    from app.models import Entity

    try:
        entity = await session.get(Entity, entity_id)
        if not entity:
            logger.warning("Entity not found for embedding update", entity_id=str(entity_id))
            return False

        if embedding is None:
            name_to_embed = name or entity.name
            embedding = await generate_entity_embedding(name_to_embed)

        if embedding is None:
            logger.warning("Could not generate embedding", entity_id=str(entity_id))
            return False

        # Update via ORM - pgvector handles the conversion
        entity.name_embedding = embedding
        await session.flush()

        logger.debug("Updated entity embedding", entity_id=str(entity_id), name=entity.name)
        return True

    except Exception as e:
        logger.error("Failed to update entity embedding", entity_id=str(entity_id), error=str(e))
        return False


async def batch_update_embeddings(
    session: AsyncSession,
    entity_type_id: Optional[uuid.UUID] = None,
    batch_size: int = 100,
    only_missing: bool = True,
) -> int:
    """
    Batch update embeddings for multiple entities.

    Args:
        session: Database session
        entity_type_id: Optional filter by entity type
        batch_size: Number of embeddings to generate per API call
        only_missing: Only update entities without embeddings

    Returns:
        Number of entities updated
    """
    from app.models import Entity
    from services.ai_service import AIService

    query = select(Entity).where(Entity.is_active.is_(True))

    if entity_type_id:
        query = query.where(Entity.entity_type_id == entity_type_id)

    if only_missing:
        query = query.where(Entity.name_embedding.is_(None))

    result = await session.execute(query)
    entities = result.scalars().all()

    if not entities:
        logger.info("No entities need embedding updates")
        return 0

    logger.info(f"Updating embeddings for {len(entities)} entities")

    ai_service = AIService()
    updated_count = 0

    # Process in batches
    for i in range(0, len(entities), batch_size):
        batch = entities[i : i + batch_size]
        names = [e.name for e in batch]

        try:
            embeddings = await ai_service.generate_embeddings(names)

            for entity, embedding in zip(batch, embeddings):
                entity.name_embedding = embedding
                updated_count += 1

            await session.commit()
            logger.info(f"Updated batch {i // batch_size + 1}, total: {updated_count}")

        except Exception as e:
            logger.error(f"Failed to update batch {i // batch_size + 1}", error=str(e))
            await session.rollback()

    return updated_count


def _normalize_for_comparison(name: str) -> str:
    """
    Normalize a name for comparison purposes.

    - Converts to lowercase
    - Replaces German umlauts with ASCII equivalents
    - Removes common prefixes like 'Stadt', 'Gemeinde', 'Landkreis'
    - Strips whitespace

    Args:
        name: The name to normalize

    Returns:
        Normalized string for comparison
    """
    if not name:
        return ""

    # Lowercase and strip
    result = name.lower().strip()

    # Replace German umlauts
    umlaut_map = {
        'ä': 'ae', 'ö': 'oe', 'ü': 'ue',
        'Ä': 'ae', 'Ö': 'oe', 'Ü': 'ue',
        'ß': 'ss'
    }
    for umlaut, replacement in umlaut_map.items():
        result = result.replace(umlaut, replacement)

    # Remove common prefixes (both at start and end)
    prefixes_to_remove = ['stadt ', 'gemeinde ', 'landkreis ', 'kreis ']
    suffixes_to_remove = [' stadt', ' gemeinde', ' landkreis', ' kreis']

    for prefix in prefixes_to_remove:
        if result.startswith(prefix):
            result = result[len(prefix):]

    for suffix in suffixes_to_remove:
        if result.endswith(suffix):
            result = result[:-len(suffix)]

    return result.strip()


def calculate_name_similarity(name1: str, name2: str) -> float:
    """
    Calculate similarity between two entity names.

    DEPRECATED: This is a legacy function for backwards compatibility.
    Use embedding-based similarity via find_similar_entities() instead.

    This synchronous function uses simple string comparison as a fallback,
    with a boost for substring matches (e.g. "Bad Homburg" matching
    "Bad Homburg vor der Höhe").

    Args:
        name1: First name to compare
        name2: Second name to compare

    Returns:
        Similarity score between 0.0 and 1.0
    """
    from difflib import SequenceMatcher

    if not name1 or not name2:
        return 0.0

    # Normalize for comparison
    n1 = _normalize_for_comparison(name1)
    n2 = _normalize_for_comparison(name2)

    if n1 == n2:
        return 1.0

    # Substring boost: if one is a complete substring of the other at word boundary
    # e.g., "Bad Homburg" in "Bad Homburg vor der Höhe" -> high similarity
    shorter, longer = (n1, n2) if len(n1) <= len(n2) else (n2, n1)

    # Check if shorter is a prefix or exact word-boundary substring of longer
    if longer.startswith(shorter) or f" {shorter}" in longer or shorter in longer.split():
        # Calculate substring coverage ratio
        coverage = len(shorter) / len(longer)
        # Boost: 0.85 + (coverage * 0.15) gives 0.85-1.0 range
        return min(1.0, 0.85 + (coverage * 0.15))

    # Use SequenceMatcher as fallback
    return SequenceMatcher(None, n1, n2).ratio()


def is_likely_duplicate(name1: str, name2: str, strict_threshold: float = 0.9) -> bool:
    """
    Quick check if two names are likely duplicates.

    DEPRECATED: Use embedding-based similarity for accurate results.

    Args:
        name1: First name
        name2: Second name
        strict_threshold: Minimum similarity to consider as duplicate

    Returns:
        True if names are likely duplicates
    """
    return calculate_name_similarity(name1, name2) >= strict_threshold


# =============================================================================
# EntityType and FacetType Duplicate Detection
# =============================================================================

# Hierarchical entity type mappings
# Maps names that should be hierarchy levels within an existing EntityType
# Format: {"name_variant": {"parent_type_slug": "slug", "hierarchy_level": int, "level_name": "display_name"}}
HIERARCHY_LEVEL_MAPPINGS = {
    # German territorial hierarchy (territorial_entity)
    "bundesland": {"parent_type_slug": "territorial_entity", "hierarchy_level": 1, "level_name": "Bundesland"},
    "bundesländer": {"parent_type_slug": "territorial_entity", "hierarchy_level": 1, "level_name": "Bundesland"},
    "land": {"parent_type_slug": "territorial_entity", "hierarchy_level": 1, "level_name": "Bundesland"},
    "länder": {"parent_type_slug": "territorial_entity", "hierarchy_level": 1, "level_name": "Bundesland"},
    "state": {"parent_type_slug": "territorial_entity", "hierarchy_level": 1, "level_name": "Bundesland"},
    "states": {"parent_type_slug": "territorial_entity", "hierarchy_level": 1, "level_name": "Bundesland"},

    "landkreis": {"parent_type_slug": "territorial_entity", "hierarchy_level": 2, "level_name": "Landkreis"},
    "landkreise": {"parent_type_slug": "territorial_entity", "hierarchy_level": 2, "level_name": "Landkreis"},
    "kreis": {"parent_type_slug": "territorial_entity", "hierarchy_level": 2, "level_name": "Landkreis"},
    "kreise": {"parent_type_slug": "territorial_entity", "hierarchy_level": 2, "level_name": "Landkreis"},
    "county": {"parent_type_slug": "territorial_entity", "hierarchy_level": 2, "level_name": "Landkreis"},
    "counties": {"parent_type_slug": "territorial_entity", "hierarchy_level": 2, "level_name": "Landkreis"},
    "bezirk": {"parent_type_slug": "territorial_entity", "hierarchy_level": 2, "level_name": "Landkreis"},
    "bezirke": {"parent_type_slug": "territorial_entity", "hierarchy_level": 2, "level_name": "Landkreis"},

    "gemeinde": {"parent_type_slug": "territorial_entity", "hierarchy_level": 3, "level_name": "Gemeinde"},
    "gemeinden": {"parent_type_slug": "territorial_entity", "hierarchy_level": 3, "level_name": "Gemeinde"},
    "kommune": {"parent_type_slug": "territorial_entity", "hierarchy_level": 3, "level_name": "Gemeinde"},
    "kommunen": {"parent_type_slug": "territorial_entity", "hierarchy_level": 3, "level_name": "Gemeinde"},
    "municipality": {"parent_type_slug": "territorial_entity", "hierarchy_level": 3, "level_name": "Gemeinde"},
    "municipalities": {"parent_type_slug": "territorial_entity", "hierarchy_level": 3, "level_name": "Gemeinde"},

    "stadt": {"parent_type_slug": "territorial_entity", "hierarchy_level": 3, "level_name": "Stadt"},
    "städte": {"parent_type_slug": "territorial_entity", "hierarchy_level": 3, "level_name": "Stadt"},
    "stadte": {"parent_type_slug": "territorial_entity", "hierarchy_level": 3, "level_name": "Stadt"},
    "city": {"parent_type_slug": "territorial_entity", "hierarchy_level": 3, "level_name": "Stadt"},
    "cities": {"parent_type_slug": "territorial_entity", "hierarchy_level": 3, "level_name": "Stadt"},

    "ort": {"parent_type_slug": "territorial_entity", "hierarchy_level": 3, "level_name": "Ort"},
    "orte": {"parent_type_slug": "territorial_entity", "hierarchy_level": 3, "level_name": "Ort"},
    "standort": {"parent_type_slug": "territorial_entity", "hierarchy_level": 3, "level_name": "Standort"},
    "standorte": {"parent_type_slug": "territorial_entity", "hierarchy_level": 3, "level_name": "Standort"},
    "location": {"parent_type_slug": "territorial_entity", "hierarchy_level": 3, "level_name": "Ort"},
    "locations": {"parent_type_slug": "territorial_entity", "hierarchy_level": 3, "level_name": "Ort"},
    "place": {"parent_type_slug": "territorial_entity", "hierarchy_level": 3, "level_name": "Ort"},
    "places": {"parent_type_slug": "territorial_entity", "hierarchy_level": 3, "level_name": "Ort"},

    "ortsteil": {"parent_type_slug": "territorial_entity", "hierarchy_level": 4, "level_name": "Ortsteil"},
    "ortsteile": {"parent_type_slug": "territorial_entity", "hierarchy_level": 4, "level_name": "Ortsteil"},
    "stadtteil": {"parent_type_slug": "territorial_entity", "hierarchy_level": 4, "level_name": "Stadtteil"},
    "stadtteile": {"parent_type_slug": "territorial_entity", "hierarchy_level": 4, "level_name": "Stadtteil"},
    "district": {"parent_type_slug": "territorial_entity", "hierarchy_level": 4, "level_name": "Stadtteil"},
    "districts": {"parent_type_slug": "territorial_entity", "hierarchy_level": 4, "level_name": "Stadtteil"},

    # Organization hierarchy
    "abteilung": {"parent_type_slug": "organization", "hierarchy_level": 2, "level_name": "Abteilung"},
    "abteilungen": {"parent_type_slug": "organization", "hierarchy_level": 2, "level_name": "Abteilung"},
    "department": {"parent_type_slug": "organization", "hierarchy_level": 2, "level_name": "Abteilung"},
    "departments": {"parent_type_slug": "organization", "hierarchy_level": 2, "level_name": "Abteilung"},
    "team": {"parent_type_slug": "organization", "hierarchy_level": 3, "level_name": "Team"},
    "teams": {"parent_type_slug": "organization", "hierarchy_level": 3, "level_name": "Team"},
}


def _normalize_type_name(name: str) -> str:
    """Normalize a type name for comparison."""
    if not name:
        return ""

    result = name.lower().strip()

    # Replace German umlauts
    umlaut_map = {
        'ä': 'ae', 'ö': 'oe', 'ü': 'ue',
        'Ä': 'ae', 'Ö': 'oe', 'Ü': 'ue',
        'ß': 'ss'
    }
    for umlaut, replacement in umlaut_map.items():
        result = result.replace(umlaut, replacement)

    # Replace common separators with space
    result = result.replace("-", " ").replace("_", " ")

    return result.strip()


def get_hierarchy_mapping(name: str) -> Optional[Dict]:
    """Check if a name maps to a hierarchy level of an existing EntityType.

    Args:
        name: The name to check

    Returns:
        Dict with parent_type_slug, hierarchy_level, level_name if found, None otherwise
    """
    normalized = _normalize_type_name(name)
    return HIERARCHY_LEVEL_MAPPINGS.get(normalized)


# =============================================================================
# AI-based semantic similarity for types (language-agnostic)
# =============================================================================

# Similarity threshold for type matching (higher = stricter)
# 0.70 provides balance between catching semantic duplicates and avoiding false positives
# Cross-language matches (e.g., "News" vs "Nachrichten") typically score 0.65-0.75
TYPE_SIMILARITY_THRESHOLD = float(os.getenv("TYPE_SIMILARITY_THRESHOLD", "0.70"))


async def find_similar_entity_types(
    session: AsyncSession,
    name: str,
    threshold: float = TYPE_SIMILARITY_THRESHOLD,
    exclude_id: Optional[uuid.UUID] = None,
) -> List[Tuple["EntityType", float, str]]:
    """
    Find EntityTypes with semantically similar names using AI embeddings.

    This is language-agnostic and works for any domain without hardcoded mappings.

    Args:
        session: Database session
        name: Name to check for duplicates
        threshold: Minimum similarity score (0-1), default from TYPE_SIMILARITY_THRESHOLD
        exclude_id: Optional ID to exclude from results (for updates)

    Returns:
        List of (EntityType, similarity_score, reason) tuples
    """
    from app.models import EntityType

    if not name or len(name) < 2:
        return []

    # Get all active entity types
    query = select(EntityType).where(EntityType.is_active.is_(True))
    if exclude_id:
        query = query.where(EntityType.id != exclude_id)

    result = await session.execute(query)
    entity_types = result.scalars().all()

    if not entity_types:
        return []

    # Generate embedding for the new name
    new_embedding = await generate_entity_embedding(name)
    if new_embedding is None:
        logger.warning("Could not generate embedding for EntityType similarity", name=name)
        return []

    matches: List[Tuple[EntityType, float, str]] = []

    for et in entity_types:
        # Check all name variants
        names_to_check = [et.name]
        if et.name_plural:
            names_to_check.append(et.name_plural)
        if et.description:
            names_to_check.append(et.description[:100])  # First 100 chars of description

        best_similarity = 0.0
        best_match_name = et.name

        for check_name in names_to_check:
            # Generate embedding for existing name
            existing_embedding = await generate_entity_embedding(check_name)
            if existing_embedding is None:
                continue

            # Calculate cosine similarity
            similarity = _cosine_similarity(new_embedding, existing_embedding)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match_name = check_name

        if best_similarity >= threshold:
            matches.append((
                et,
                best_similarity,
                f"Semantisch ähnlich zu '{best_match_name}' ({int(best_similarity * 100)}%)"
            ))

    # Sort by similarity descending
    matches.sort(key=lambda x: x[1], reverse=True)

    if matches:
        logger.info(
            "EntityType similarity check - matches found",
            search_name=name,
            matches_found=len(matches),
            top_match=matches[0][0].name,
            top_score=round(matches[0][1], 3),
        )

    return matches


async def find_similar_facet_types(
    session: AsyncSession,
    name: str,
    threshold: float = TYPE_SIMILARITY_THRESHOLD,
    exclude_id: Optional[uuid.UUID] = None,
) -> List[Tuple["FacetType", float, str]]:
    """
    Find FacetTypes with semantically similar names using AI embeddings.

    This is language-agnostic and works for any domain without hardcoded mappings.

    Args:
        session: Database session
        name: Name to check for duplicates
        threshold: Minimum similarity score (0-1), default from TYPE_SIMILARITY_THRESHOLD
        exclude_id: Optional ID to exclude from results (for updates)

    Returns:
        List of (FacetType, similarity_score, reason) tuples
    """
    from app.models import FacetType

    if not name or len(name) < 2:
        return []

    # Get all active facet types
    query = select(FacetType).where(FacetType.is_active.is_(True))
    if exclude_id:
        query = query.where(FacetType.id != exclude_id)

    result = await session.execute(query)
    facet_types = result.scalars().all()

    if not facet_types:
        return []

    # Generate embedding for the new name
    new_embedding = await generate_entity_embedding(name)
    if new_embedding is None:
        logger.warning("Could not generate embedding for FacetType similarity", name=name)
        return []

    matches: List[Tuple[FacetType, float, str]] = []

    for ft in facet_types:
        # Check all name variants
        names_to_check = [ft.name]
        if ft.name_plural:
            names_to_check.append(ft.name_plural)
        if ft.description:
            names_to_check.append(ft.description[:100])  # First 100 chars of description

        best_similarity = 0.0
        best_match_name = ft.name

        for check_name in names_to_check:
            # Generate embedding for existing name
            existing_embedding = await generate_entity_embedding(check_name)
            if existing_embedding is None:
                continue

            # Calculate cosine similarity
            similarity = _cosine_similarity(new_embedding, existing_embedding)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match_name = check_name

        if best_similarity >= threshold:
            matches.append((
                ft,
                best_similarity,
                f"Semantisch ähnlich zu '{best_match_name}' ({int(best_similarity * 100)}%)"
            ))

    # Sort by similarity descending
    matches.sort(key=lambda x: x[1], reverse=True)

    if matches:
        logger.info(
            "FacetType similarity check - matches found",
            search_name=name,
            matches_found=len(matches),
            top_match=matches[0][0].name,
            top_score=round(matches[0][1], 3),
        )

    return matches


# =============================================================================
# RelationType Duplicate Detection (AI-Embedding based)
# =============================================================================

async def find_similar_relation_types(
    session: AsyncSession,
    name: str,
    name_inverse: Optional[str] = None,
    source_entity_type_id: Optional[uuid.UUID] = None,
    target_entity_type_id: Optional[uuid.UUID] = None,
    threshold: float = TYPE_SIMILARITY_THRESHOLD,
    exclude_id: Optional[uuid.UUID] = None,
) -> List[Tuple["RelationType", float, str]]:
    """
    Find RelationTypes with semantically similar names using AI embeddings.

    Checks both name and name_inverse for semantic similarity.

    Args:
        session: Database session
        name: Relation name (e.g., "works_for")
        name_inverse: Inverse name (e.g., "employs")
        source_entity_type_id: Optional source type filter
        target_entity_type_id: Optional target type filter
        threshold: Minimum similarity score (0-1)
        exclude_id: Optional ID to exclude from results

    Returns:
        List of (RelationType, similarity_score, reason) tuples
    """
    from app.models import RelationType

    if not name or len(name) < 2:
        return []

    # Get all active relation types
    query = select(RelationType).where(RelationType.is_active.is_(True))
    if exclude_id:
        query = query.where(RelationType.id != exclude_id)

    # Optional: Filter by entity types if provided
    if source_entity_type_id:
        query = query.where(RelationType.source_entity_type_id == source_entity_type_id)
    if target_entity_type_id:
        query = query.where(RelationType.target_entity_type_id == target_entity_type_id)

    result = await session.execute(query)
    relation_types = result.scalars().all()

    if not relation_types:
        return []

    # Generate embeddings for the new names
    new_name_embedding = await generate_entity_embedding(name)
    new_inverse_embedding = None
    if name_inverse:
        new_inverse_embedding = await generate_entity_embedding(name_inverse)

    if new_name_embedding is None:
        logger.warning("Could not generate embedding for RelationType similarity", name=name)
        return []

    matches: List[Tuple[RelationType, float, str]] = []

    for rt in relation_types:
        best_similarity = 0.0
        best_reason = ""

        # Check name against name
        existing_name_embedding = await generate_entity_embedding(rt.name)
        if existing_name_embedding:
            similarity = _cosine_similarity(new_name_embedding, existing_name_embedding)
            if similarity > best_similarity:
                best_similarity = similarity
                best_reason = f"Name '{name}' ähnlich zu '{rt.name}'"

        # Check name against inverse (might be semantically related)
        existing_inverse_embedding = await generate_entity_embedding(rt.name_inverse)
        if existing_inverse_embedding:
            similarity = _cosine_similarity(new_name_embedding, existing_inverse_embedding)
            if similarity > best_similarity:
                best_similarity = similarity
                best_reason = f"Name '{name}' ähnlich zu inversem '{rt.name_inverse}'"

        # Check inverse against inverse
        if new_inverse_embedding and existing_inverse_embedding:
            similarity = _cosine_similarity(new_inverse_embedding, existing_inverse_embedding)
            if similarity > best_similarity:
                best_similarity = similarity
                best_reason = f"Inverse '{name_inverse}' ähnlich zu '{rt.name_inverse}'"

        # Check inverse against name
        if new_inverse_embedding and existing_name_embedding:
            similarity = _cosine_similarity(new_inverse_embedding, existing_name_embedding)
            if similarity > best_similarity:
                best_similarity = similarity
                best_reason = f"Inverse '{name_inverse}' ähnlich zu '{rt.name}'"

        if best_similarity >= threshold:
            matches.append((
                rt,
                best_similarity,
                f"{best_reason} ({int(best_similarity * 100)}%)"
            ))

    # Sort by similarity descending
    matches.sort(key=lambda x: x[1], reverse=True)

    if matches:
        logger.info(
            "RelationType similarity check - matches found",
            search_name=name,
            matches_found=len(matches),
            top_match=matches[0][0].name,
            top_score=round(matches[0][1], 3),
        )

    return matches


# =============================================================================
# Location Duplicate Detection (Normalization + Geo-based)
# =============================================================================

def find_similar_locations_by_name(
    name: str,
    country: str,
    existing_locations: List["Location"],
    threshold: float = 0.90,
) -> List[Tuple["Location", float, str]]:
    """
    Find locations with similar names using normalization and fuzzy matching.

    Args:
        name: Location name to check
        country: Country code (for normalization rules)
        existing_locations: List of existing locations to check against
        threshold: Minimum similarity score (0-1)

    Returns:
        List of (Location, similarity_score, reason) tuples
    """
    from app.models import Location
    from difflib import SequenceMatcher

    if not name or len(name) < 2:
        return []

    # Normalize the new name
    new_normalized = Location.normalize_name(name, country)

    matches: List[Tuple[Location, float, str]] = []

    for loc in existing_locations:
        # Exact normalized match
        if loc.name_normalized == new_normalized:
            matches.append((loc, 1.0, f"Exakter Match (normalisiert): '{loc.name}'"))
            continue

        # Fuzzy match on normalized names
        similarity = SequenceMatcher(None, new_normalized, loc.name_normalized).ratio()

        if similarity >= threshold:
            matches.append((
                loc,
                similarity,
                f"Ähnlicher Name: '{loc.name}' ({int(similarity * 100)}%)"
            ))

    # Sort by similarity descending
    matches.sort(key=lambda x: x[1], reverse=True)

    return matches


def check_location_geo_proximity(
    lat1: Optional[float],
    lon1: Optional[float],
    lat2: Optional[float],
    lon2: Optional[float],
    max_distance_km: float = 5.0,
) -> Tuple[bool, float]:
    """
    Check if two locations are within a certain distance.

    Uses Haversine formula for distance calculation.

    Args:
        lat1, lon1: First location coordinates
        lat2, lon2: Second location coordinates
        max_distance_km: Maximum distance to consider as "nearby"

    Returns:
        Tuple of (is_nearby, distance_km)
    """
    import math

    if any(x is None for x in [lat1, lon1, lat2, lon2]):
        return False, float('inf')

    # Earth radius in km
    R = 6371.0

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c

    return distance <= max_distance_km, distance


async def find_duplicate_location(
    session: AsyncSession,
    name: str,
    country: str,
    admin_level_1: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    exclude_id: Optional[uuid.UUID] = None,
) -> Optional[Tuple["Location", str]]:
    """
    Find a duplicate location using multiple criteria.

    Checks in order:
    1. Exact normalized name match within same country + admin_level_1
    2. Fuzzy name match (>95%) within same country + admin_level_1
    3. Geo proximity check (<5km) for locations with coordinates

    Args:
        session: Database session
        name: Location name
        country: Country code
        admin_level_1: State/Region
        latitude, longitude: Coordinates (optional)
        exclude_id: ID to exclude

    Returns:
        Tuple of (Location, reason) if duplicate found, None otherwise
    """
    from app.models import Location

    if not name or not country:
        return None

    # Build query for same country and admin_level_1
    query = select(Location).where(
        Location.country == country,
        Location.is_active.is_(True),
    )

    if admin_level_1:
        query = query.where(Location.admin_level_1 == admin_level_1)

    if exclude_id:
        query = query.where(Location.id != exclude_id)

    result = await session.execute(query)
    existing_locations = result.scalars().all()

    if not existing_locations:
        return None

    # Check normalized name match
    new_normalized = Location.normalize_name(name, country)

    for loc in existing_locations:
        if loc.name_normalized == new_normalized:
            return loc, f"Exakter Match (normalisiert): '{loc.name}'"

    # Check fuzzy name match
    name_matches = find_similar_locations_by_name(name, country, existing_locations, threshold=0.95)
    if name_matches:
        return name_matches[0][0], name_matches[0][2]

    # Check geo proximity if coordinates provided
    if latitude is not None and longitude is not None:
        for loc in existing_locations:
            is_nearby, distance = check_location_geo_proximity(
                latitude, longitude,
                loc.latitude, loc.longitude,
                max_distance_km=5.0
            )
            if is_nearby:
                return loc, f"Geografisch nahe ({distance:.1f}km): '{loc.name}'"

    return None


# =============================================================================
# Config-Hash based Duplicate Detection
# =============================================================================

import hashlib
import json


def compute_config_hash(config: Dict) -> str:
    """
    Compute a deterministic hash for a configuration dictionary.

    Args:
        config: Configuration dictionary

    Returns:
        SHA256 hash string
    """
    # Sort keys for deterministic serialization
    config_str = json.dumps(config, sort_keys=True, default=str)
    return hashlib.sha256(config_str.encode()).hexdigest()[:16]


async def find_duplicate_analysis_template(
    session: AsyncSession,
    name: str,
    primary_entity_type_id: uuid.UUID,
    category_id: Optional[uuid.UUID],
    facet_config: List[Dict],
    exclude_id: Optional[uuid.UUID] = None,
) -> Optional[Tuple["AnalysisTemplate", str]]:
    """
    Find duplicate AnalysisTemplate by configuration.

    Checks:
    1. Same primary_entity_type + category + facet_config hash
    2. Semantic name similarity

    Args:
        session: Database session
        name: Template name
        primary_entity_type_id: Primary entity type
        category_id: Category (optional)
        facet_config: Facet configuration
        exclude_id: ID to exclude

    Returns:
        Tuple of (AnalysisTemplate, reason) if duplicate found
    """
    from app.models import AnalysisTemplate

    # Build query
    query = select(AnalysisTemplate).where(
        AnalysisTemplate.is_active.is_(True),
        AnalysisTemplate.primary_entity_type_id == primary_entity_type_id,
    )

    if category_id:
        query = query.where(AnalysisTemplate.category_id == category_id)

    if exclude_id:
        query = query.where(AnalysisTemplate.id != exclude_id)

    result = await session.execute(query)
    templates = result.scalars().all()

    if not templates:
        return None

    # Compute config hash for new template
    new_config_hash = compute_config_hash({"facet_config": facet_config})

    for template in templates:
        # Check config hash
        existing_hash = compute_config_hash({"facet_config": template.facet_config})
        if existing_hash == new_config_hash:
            return template, f"Identische Facet-Konfiguration: '{template.name}'"

        # Check name similarity
        new_normalized = _normalize_type_name(name)
        existing_normalized = _normalize_type_name(template.name)
        if new_normalized == existing_normalized:
            return template, f"Identischer Name: '{template.name}'"

    return None


async def find_duplicate_api_configuration(
    session: AsyncSession,
    base_url: str,
    endpoint: str,
    exclude_id: Optional[uuid.UUID] = None,
) -> Optional[Tuple["APIConfiguration", str]]:
    """
    Find duplicate APIConfiguration by URL.

    Args:
        session: Database session
        base_url: API base URL
        endpoint: API endpoint
        exclude_id: ID to exclude

    Returns:
        Tuple of (APIConfiguration, reason) if duplicate found
    """
    from sqlalchemy.orm import selectinload
    from app.models.api_configuration import APIConfiguration

    # Normalize URLs
    base_url_normalized = base_url.rstrip("/").lower()
    endpoint_normalized = endpoint.strip("/").lower()

    query = (
        select(APIConfiguration)
        .options(selectinload(APIConfiguration.data_source))
        .where(APIConfiguration.is_active == True)
    )

    if exclude_id:
        query = query.where(APIConfiguration.id != exclude_id)

    result = await session.execute(query)
    configs = result.scalars().all()

    for config in configs:
        if not config.data_source:
            continue

        existing_base = config.data_source.base_url.rstrip("/").lower()
        existing_endpoint = config.endpoint.strip("/").lower()
        config_name = config.data_source.name

        if existing_base == base_url_normalized and existing_endpoint == endpoint_normalized:
            return config, f"Identische API-URL: '{config_name}'"

    return None


async def find_duplicate_crawl_preset(
    session: AsyncSession,
    user_id: uuid.UUID,
    filters: Dict,
    exclude_id: Optional[uuid.UUID] = None,
) -> Optional[Tuple["CrawlPreset", str]]:
    """
    Find duplicate CrawlPreset by filter configuration.

    Args:
        session: Database session
        user_id: User ID (presets are user-specific)
        filters: Filter configuration
        exclude_id: ID to exclude

    Returns:
        Tuple of (CrawlPreset, reason) if duplicate found
    """
    from app.models import CrawlPreset

    query = select(CrawlPreset).where(
        CrawlPreset.user_id == user_id,
        CrawlPreset.status == "active",
    )

    if exclude_id:
        query = query.where(CrawlPreset.id != exclude_id)

    result = await session.execute(query)
    presets = result.scalars().all()

    if not presets:
        return None

    # Compute filter hash
    new_filter_hash = compute_config_hash(filters)

    for preset in presets:
        existing_hash = compute_config_hash(preset.filters)
        if existing_hash == new_filter_hash:
            return preset, f"Identische Filter-Konfiguration: '{preset.name}'"

    return None


async def find_duplicate_notification_rule(
    session: AsyncSession,
    user_id: uuid.UUID,
    event_type: str,
    channel: str,
    conditions: Dict,
    exclude_id: Optional[uuid.UUID] = None,
) -> Optional[Tuple["NotificationRule", str]]:
    """
    Find duplicate NotificationRule by conditions.

    Args:
        session: Database session
        user_id: User ID
        event_type: Event type
        channel: Notification channel
        conditions: Filter conditions
        exclude_id: ID to exclude

    Returns:
        Tuple of (NotificationRule, reason) if duplicate found
    """
    from app.models import NotificationRule

    query = select(NotificationRule).where(
        NotificationRule.user_id == user_id,
        NotificationRule.is_active.is_(True),
        NotificationRule.event_type == event_type,
        NotificationRule.channel == channel,
    )

    if exclude_id:
        query = query.where(NotificationRule.id != exclude_id)

    result = await session.execute(query)
    rules = result.scalars().all()

    if not rules:
        return None

    # Compute conditions hash
    new_conditions_hash = compute_config_hash(conditions)

    for rule in rules:
        existing_hash = compute_config_hash(rule.conditions)
        if existing_hash == new_conditions_hash:
            return rule, f"Identische Regel-Bedingungen: '{rule.name}'"

    return None


# =============================================================================
# FacetValue Semantic Duplicate Detection
# =============================================================================

async def find_similar_facet_values(
    session: AsyncSession,
    entity_id: uuid.UUID,
    facet_type_id: uuid.UUID,
    text_representation: str,
    threshold: float = 0.85,
    exclude_id: Optional[uuid.UUID] = None,
) -> List[Tuple["FacetValue", float, str]]:
    """
    Find FacetValues with semantically similar text_representation.

    Uses AI embeddings for semantic comparison.

    Args:
        session: Database session
        entity_id: Entity to check within
        facet_type_id: FacetType to check within
        text_representation: Text to compare
        threshold: Minimum similarity score (0-1)
        exclude_id: Optional ID to exclude

    Returns:
        List of (FacetValue, similarity_score, reason) tuples
    """
    from app.models import FacetValue

    if not text_representation or len(text_representation) < 5:
        return []

    # Get existing facet values for this entity and type
    query = select(FacetValue).where(
        FacetValue.entity_id == entity_id,
        FacetValue.facet_type_id == facet_type_id,
    )

    if exclude_id:
        query = query.where(FacetValue.id != exclude_id)

    result = await session.execute(query)
    existing_values = result.scalars().all()

    if not existing_values:
        return []

    # Generate embedding for new text
    new_embedding = await generate_entity_embedding(text_representation)
    if new_embedding is None:
        return []

    matches: List[Tuple[FacetValue, float, str]] = []

    for fv in existing_values:
        if not fv.text_representation:
            continue

        # Generate embedding for existing value
        existing_embedding = await generate_entity_embedding(fv.text_representation)
        if existing_embedding is None:
            continue

        similarity = _cosine_similarity(new_embedding, existing_embedding)

        if similarity >= threshold:
            matches.append((
                fv,
                similarity,
                f"Ähnlicher Wert: '{fv.text_representation[:50]}...' ({int(similarity * 100)}%)"
            ))

    # Sort by similarity descending
    matches.sort(key=lambda x: x[1], reverse=True)

    return matches


# =============================================================================
# EntityAttachment Duplicate Detection
# =============================================================================

async def find_duplicate_entity_attachment(
    session: AsyncSession,
    entity_id: uuid.UUID,
    file_hash: str,
    exclude_id: Optional[uuid.UUID] = None,
) -> Optional[Tuple["EntityAttachment", str]]:
    """
    Find duplicate EntityAttachment by file_hash.

    Args:
        session: Database session
        entity_id: Entity to check within
        file_hash: SHA256 hash of the file
        exclude_id: ID to exclude

    Returns:
        Tuple of (EntityAttachment, reason) if duplicate found
    """
    from app.models import EntityAttachment

    query = select(EntityAttachment).where(
        EntityAttachment.entity_id == entity_id,
        EntityAttachment.file_hash == file_hash,
    )

    if exclude_id:
        query = query.where(EntityAttachment.id != exclude_id)

    result = await session.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        return existing, f"Identische Datei bereits vorhanden: '{existing.filename}'"

    return None


# =============================================================================
# CustomSummary Duplicate Detection
# =============================================================================

async def find_duplicate_custom_summary(
    session: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    widget_config: Optional[List[Dict]] = None,
    exclude_id: Optional[uuid.UUID] = None,
) -> Optional[Tuple["CustomSummary", str]]:
    """
    Find duplicate CustomSummary by name or widget configuration.

    Args:
        session: Database session
        user_id: User ID
        name: Summary name
        widget_config: Widget configuration (optional)
        exclude_id: ID to exclude

    Returns:
        Tuple of (CustomSummary, reason) if duplicate found
    """
    from app.models import CustomSummary
    from sqlalchemy import func as sqla_func

    # Check for exact name match (case-insensitive)
    query = select(CustomSummary).where(
        CustomSummary.user_id == user_id,
        CustomSummary.is_active.is_(True),
        sqla_func.lower(CustomSummary.name) == sqla_func.lower(name),
    )

    if exclude_id:
        query = query.where(CustomSummary.id != exclude_id)

    result = await session.execute(query)
    name_match = result.scalar_one_or_none()

    if name_match:
        return name_match, f"Summary mit gleichem Namen existiert: '{name_match.name}'"

    # If widget config provided, check for config hash match
    if widget_config:
        query = select(CustomSummary).where(
            CustomSummary.user_id == user_id,
            CustomSummary.is_active.is_(True),
        )

        if exclude_id:
            query = query.where(CustomSummary.id != exclude_id)

        result = await session.execute(query)
        all_summaries = result.scalars().all()

        new_config_hash = compute_config_hash({"widgets": widget_config})

        for summary in all_summaries:
            if summary.widget_config:
                existing_hash = compute_config_hash({"widgets": summary.widget_config})
                if existing_hash == new_config_hash:
                    return summary, f"Summary mit identischer Widget-Konfiguration: '{summary.name}'"

    return None
