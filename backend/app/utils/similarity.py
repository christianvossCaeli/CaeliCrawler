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
from typing import List, Optional, Tuple, TYPE_CHECKING

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


def calculate_name_similarity(name1: str, name2: str) -> float:
    """
    Calculate similarity between two entity names.

    DEPRECATED: This is a legacy function for backwards compatibility.
    Use embedding-based similarity via find_similar_entities() instead.

    This synchronous function uses simple string comparison as a fallback.

    Args:
        name1: First name to compare
        name2: Second name to compare

    Returns:
        Similarity score between 0.0 and 1.0
    """
    from difflib import SequenceMatcher

    if not name1 or not name2:
        return 0.0

    # Simple lowercase comparison
    n1 = name1.lower().strip()
    n2 = name2.lower().strip()

    if n1 == n2:
        return 1.0

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
