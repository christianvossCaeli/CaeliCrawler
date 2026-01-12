"""
Similarity search functions for entities, types, and duplicates.

This module contains database-level similarity operations using pgvector.
Core functionality is organized as:
- similarity/embedding.py: Embedding generation and caching
- similarity/concept_matching.py: Cross-lingual concept normalization
- This file: Entity/Type search, deduplication, hierarchy mapping

Functions are re-exported via similarity/__init__.py for convenience.
"""

import hashlib
import json
import time
import uuid
from typing import TYPE_CHECKING, Any, Optional, TypeVar

import structlog
from sqlalchemy import func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.models import Category, Entity
    from app.models.entity_type import EntityType
    from app.models.facet_type import FacetType
    from app.models.relation_type import RelationType

from app.core.cache import TTLCache
from app.database import Base
from app.models.llm_usage import LLMProvider, LLMTaskType
from app.utils.similarity.concept_matching import (
    _canonical_concept_cache,
    _concept_equivalence_cache,
    are_concepts_equivalent,
)

# =============================================================================
# Import from new modular structure (avoid circular imports by importing
# directly from the modules, not from the package __init__)
# =============================================================================
from app.utils.similarity.embedding import (
    SIMILARITY_THRESHOLDS,
    _cosine_similarity,
    _increment_stat,
    clear_embedding_cache,
    generate_embedding,
    generate_embeddings_batch,
)
from services.llm_usage_tracker import record_llm_usage

logger = structlog.get_logger(__name__)


# =============================================================================
# Cache Invalidation (uses imported caches from new modules)
# =============================================================================


def invalidate_hierarchy_cache() -> None:
    """Invalidate hierarchy mapping cache."""
    _hierarchy_mapping_cache.clear()
    logger.info("Hierarchy mapping cache invalidated")


def invalidate_all_similarity_caches() -> None:
    """Invalidate all similarity-related caches. Call after schema changes."""
    clear_embedding_cache()
    _canonical_concept_cache.clear()
    _concept_equivalence_cache.clear()
    _hierarchy_mapping_cache.clear()
    logger.info("All similarity caches invalidated")


# =============================================================================
# Entity Similarity (uses pgvector for DB-level search)
# =============================================================================


async def find_similar_entities(
    session: AsyncSession,
    entity_type_id: uuid.UUID,
    name: str,
    threshold: float = None,
    limit: int = 5,
    embedding: list[float] | None = None,
) -> list[tuple["Entity", float]]:
    """
    Find entities with similar names using embedding-based similarity.

    Uses pgvector's native cosine distance operator for efficient database-level
    filtering and sorting. This scales to millions of entities.

    Args:
        session: Database session
        entity_type_id: UUID of the entity type to search
        name: Name to find similar entities for
        threshold: Minimum similarity score (default: SIMILARITY_THRESHOLDS["entity"])
        limit: Maximum number of matches to return
        embedding: Pre-computed embedding (if available, saves API call)

    Returns:
        List of (Entity, similarity_score) tuples, sorted by score descending
    """
    from app.models import Entity

    if threshold is None:
        threshold = SIMILARITY_THRESHOLDS["entity"]

    _increment_stat("searches")

    if not name or len(name) < 2:
        return []

    # If no embedding provided, generate one using DB credentials
    if embedding is None:
        embedding = await generate_embedding(name, session=session)

    if embedding is None:
        logger.warning("Could not generate embedding for similarity search", name=name)
        return []

    # Use pgvector's native cosine distance for efficient DB-level filtering
    max_distance = 1.0 - threshold
    distance_expr = Entity.name_embedding.cosine_distance(embedding)

    result = await session.execute(
        select(Entity, (literal(1.0) - distance_expr).label("similarity"))
        .where(
            Entity.entity_type_id == entity_type_id,
            Entity.is_active.is_(True),
            Entity.name_embedding.isnot(None),
            distance_expr <= max_distance,
        )
        .order_by(distance_expr)
        .limit(limit)
    )

    matches: list[tuple[Entity, float]] = []
    for row in result:
        entity = row[0]
        similarity = float(row[1])
        matches.append((entity, similarity))
        _increment_stat("matches_found")

    if matches:
        logger.info(
            "Found similar entities",
            search_name=name,
            matches=len(matches),
            top_match=matches[0][0].name if matches else None,
            top_score=round(matches[0][1], 3) if matches else None,
        )

    return matches


# =============================================================================
# Generic Type Similarity (EntityType, FacetType, Category, RelationType)
# =============================================================================

# Type variable for generic functions
T = TypeVar("T", bound=Base)


async def find_similar_types[T: Base](
    session: AsyncSession,
    model_class: type[T],
    name: str,
    threshold: float = None,
    exclude_id: uuid.UUID | None = None,
    name_fields: list[str] = None,
) -> list[tuple[T, float, str]]:
    """
    Generic function to find semantically similar types using stored embeddings.

    This replaces the separate find_similar_entity_types, find_similar_facet_types,
    find_similar_categories functions with a single generic implementation.

    IMPORTANT: This function uses a two-step approach for cross-lingual matching:
    1. First, try embedding-based similarity (fast, works well for same language)
    2. If no high-confidence match, use AI to directly check concept equivalence
       (catches cross-lingual synonyms across any language pair)

    Args:
        session: Database session
        model_class: SQLAlchemy model class (EntityType, FacetType, Category, RelationType)
        name: Name to check for duplicates
        threshold: Minimum similarity score (default: SIMILARITY_THRESHOLDS["type"])
        exclude_id: Optional ID to exclude from results (for updates)
        name_fields: Fields to check for similarity (default: ["name", "name_plural", "description"])

    Returns:
        List of (Model, similarity_score, reason) tuples, sorted by score descending
    """
    if threshold is None:
        threshold = SIMILARITY_THRESHOLDS["type"]

    if name_fields is None:
        name_fields = ["name"]
        # Add optional fields if they exist on the model
        if hasattr(model_class, "name_plural"):
            name_fields.append("name_plural")
        if hasattr(model_class, "description"):
            name_fields.append("description")

    if not name or len(name) < 2:
        return []

    _increment_stat("searches")

    # Check if model has name_embedding column
    has_stored_embedding = hasattr(model_class, "name_embedding")

    # Generate embedding for the search name
    new_embedding = await generate_embedding(name)
    if new_embedding is None:
        logger.warning(f"Could not generate embedding for {model_class.__name__} similarity", name=name)
        return []

    # Query for active items
    query = select(model_class).where(model_class.is_active.is_(True))
    if exclude_id:
        query = query.where(model_class.id != exclude_id)

    matches: list[tuple[T, float, str]] = []

    # ==========================================================================
    # STEP 1: Embedding-based similarity (fast)
    # ==========================================================================
    if has_stored_embedding:
        max_distance = 1.0 - threshold
        distance_expr = model_class.name_embedding.cosine_distance(new_embedding)

        emb_query = (
            select(model_class, (literal(1.0) - distance_expr).label("similarity"))
            .where(
                model_class.is_active.is_(True),
                model_class.name_embedding.isnot(None),
                distance_expr <= max_distance,
            )
            .order_by(distance_expr)
            .limit(10)
        )

        if exclude_id:
            emb_query = emb_query.where(model_class.id != exclude_id)

        result = await session.execute(emb_query)

        for row in result:
            item = row[0]
            similarity = float(row[1])
            matches.append((item, similarity, f"Semantisch ähnlich zu '{item.name}' ({int(similarity * 100)}%)"))
            _increment_stat("matches_found")

        if matches:
            logger.info(
                f"{model_class.__name__} similarity check - matches found",
                search_name=name,
                matches_found=len(matches),
                top_match=matches[0][0].name,
                top_score=round(matches[0][1], 3),
            )
            return matches

    # ==========================================================================
    # STEP 2: Cross-lingual check via direct AI concept equivalence
    # ==========================================================================
    # Only do this if we didn't find any embedding matches - this catches
    # cross-lingual synonyms by directly asking the AI if the concepts
    # are equivalent (works across any language pair).

    # Get all active items
    result = await session.execute(query)
    items = result.scalars().all()

    if not items:
        return []

    # Check concept equivalence with each existing item
    for item in items:
        is_equivalent = await are_concepts_equivalent(name, item.name)

        if is_equivalent:
            matches.append(
                (
                    item,
                    0.95,  # High score for concept equivalence
                    f"Konzept-Match: '{name}' ≡ '{item.name}'",
                )
            )
            _increment_stat("matches_found")
            logger.info(
                f"{model_class.__name__} cross-lingual match found",
                search_name=name,
                matched_name=item.name,
            )

    if matches:
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    # ==========================================================================
    # STEP 3: Fallback - compute similarity in Python (for items without embeddings)
    # ==========================================================================
    for item in items:
        best_similarity = 0.0
        best_match_name = item.name

        for field in name_fields:
            field_value = getattr(item, field, None)
            if not field_value:
                continue

            # Truncate long fields
            check_text = field_value[:100] if len(field_value) > 100 else field_value

            # Get or generate embedding for existing item
            existing_embedding = await generate_embedding(check_text)
            if existing_embedding is None:
                continue

            similarity = _cosine_similarity(new_embedding, existing_embedding)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match_name = check_text

        if best_similarity >= threshold:
            matches.append(
                (item, best_similarity, f"Semantisch ähnlich zu '{best_match_name}' ({int(best_similarity * 100)}%)")
            )
            _increment_stat("matches_found")

    # Sort by similarity descending
    matches.sort(key=lambda x: x[1], reverse=True)

    if matches:
        logger.info(
            f"{model_class.__name__} similarity check - matches found",
            search_name=name,
            matches_found=len(matches),
            top_match=matches[0][0].name,
            top_score=round(matches[0][1], 3),
        )

    return matches


# =============================================================================
# Convenience Wrappers (for backwards compatibility and cleaner API)
# =============================================================================


async def find_similar_entity_types(
    session: AsyncSession,
    name: str,
    threshold: float = None,
    exclude_id: uuid.UUID | None = None,
) -> list[tuple["EntityType", float, str]]:
    """Find EntityTypes with semantically similar names."""
    from app.models import EntityType

    return await find_similar_types(session, EntityType, name, threshold, exclude_id)


async def find_entity_type_by_alias(
    session: AsyncSession,
    name: str,
) -> Optional["EntityType"]:
    """
    Find an EntityType by checking if the name matches any of its aliases.

    This is an O(1) lookup using the aliases array column with a GIN index.
    No LLM costs involved.

    Args:
        session: Database session
        name: The name to search for in aliases (case-insensitive)

    Returns:
        The matching EntityType if found, None otherwise
    """
    from app.models import EntityType

    name_lower = name.lower().strip()

    # Use PostgreSQL's array containment operator with lowercase comparison
    # The @> operator checks if the array contains the element
    result = await session.execute(
        select(EntityType).where(
            EntityType.is_active.is_(True),
            func.lower(EntityType.name) == name_lower,  # Exact name match
        )
    )
    exact_match = result.scalar_one_or_none()
    if exact_match:
        return exact_match

    # Check aliases - PostgreSQL array contains check
    result = await session.execute(
        select(EntityType).where(
            EntityType.is_active.is_(True),
            EntityType.aliases.any(name_lower),  # Check if any alias matches
        )
    )
    return result.scalar_one_or_none()


async def find_similar_facet_types(
    session: AsyncSession,
    name: str,
    threshold: float = None,
    exclude_id: uuid.UUID | None = None,
) -> list[tuple["FacetType", float, str]]:
    """Find FacetTypes with semantically similar names."""
    from app.models import FacetType

    return await find_similar_types(session, FacetType, name, threshold, exclude_id)


async def find_similar_categories(
    session: AsyncSession,
    name: str,
    threshold: float = None,
    exclude_id: uuid.UUID | None = None,
) -> list[tuple["Category", float, str]]:
    """Find Categories with semantically similar names."""
    from app.models import Category

    return await find_similar_types(
        session, Category, name, threshold, exclude_id, name_fields=["name", "description", "purpose"]
    )


async def find_similar_relation_types(
    session: AsyncSession,
    name: str,
    name_inverse: str | None = None,
    source_entity_type_id: uuid.UUID | None = None,
    target_entity_type_id: uuid.UUID | None = None,
    threshold: float = None,
    exclude_id: uuid.UUID | None = None,
) -> list[tuple["RelationType", float, str]]:
    """
    Find RelationTypes with semantically similar names.

    Uses stored name_embedding and name_inverse_embedding for efficient pgvector search.
    Performs 4 similarity checks using stored embeddings:
    1. new_name vs stored name_embedding
    2. new_name vs stored name_inverse_embedding
    3. new_inverse vs stored name_embedding
    4. new_inverse vs stored name_inverse_embedding
    """
    from app.models import RelationType

    if threshold is None:
        threshold = SIMILARITY_THRESHOLDS["type"]

    if not name or len(name) < 2:
        return []

    _increment_stat("searches")

    # Generate embeddings for search terms
    new_name_embedding = await generate_embedding(name)
    if new_name_embedding is None:
        return []

    new_inverse_embedding = await generate_embedding(name_inverse) if name_inverse else None
    max_distance = 1.0 - threshold

    # Build base conditions
    base_conditions = [RelationType.is_active.is_(True)]
    if exclude_id:
        base_conditions.append(RelationType.id != exclude_id)
    if source_entity_type_id:
        base_conditions.append(RelationType.source_entity_type_id == source_entity_type_id)
    if target_entity_type_id:
        base_conditions.append(RelationType.target_entity_type_id == target_entity_type_id)

    matches: list[tuple[RelationType, float, str]] = []
    seen_ids: dict[uuid.UUID, tuple[float, str]] = {}  # id -> (best_similarity, reason)

    # Query 1: new_name vs stored name_embedding
    distance_expr_1 = RelationType.name_embedding.cosine_distance(new_name_embedding)
    query_1 = (
        select(RelationType, (literal(1.0) - distance_expr_1).label("similarity"))
        .where(
            *base_conditions,
            RelationType.name_embedding.isnot(None),
            distance_expr_1 <= max_distance,
        )
        .order_by(distance_expr_1)
        .limit(20)
    )
    result_1 = await session.execute(query_1)
    for row in result_1:
        rt, similarity = row[0], float(row[1])
        reason = f"Name '{name}' ähnlich zu '{rt.name}'"
        if rt.id not in seen_ids or similarity > seen_ids[rt.id][0]:
            seen_ids[rt.id] = (similarity, reason)

    # Query 2: new_name vs stored name_inverse_embedding
    distance_expr_2 = RelationType.name_inverse_embedding.cosine_distance(new_name_embedding)
    query_2 = (
        select(RelationType, (literal(1.0) - distance_expr_2).label("similarity"))
        .where(
            *base_conditions,
            RelationType.name_inverse_embedding.isnot(None),
            distance_expr_2 <= max_distance,
        )
        .order_by(distance_expr_2)
        .limit(20)
    )
    result_2 = await session.execute(query_2)
    for row in result_2:
        rt, similarity = row[0], float(row[1])
        reason = f"Name '{name}' ähnlich zu inversem '{rt.name_inverse}'"
        if rt.id not in seen_ids or similarity > seen_ids[rt.id][0]:
            seen_ids[rt.id] = (similarity, reason)

    # Query 3 & 4: Only if new_inverse_embedding is available
    if new_inverse_embedding:
        # Query 3: new_inverse vs stored name_embedding
        distance_expr_3 = RelationType.name_embedding.cosine_distance(new_inverse_embedding)
        query_3 = (
            select(RelationType, (literal(1.0) - distance_expr_3).label("similarity"))
            .where(
                *base_conditions,
                RelationType.name_embedding.isnot(None),
                distance_expr_3 <= max_distance,
            )
            .order_by(distance_expr_3)
            .limit(20)
        )
        result_3 = await session.execute(query_3)
        for row in result_3:
            rt, similarity = row[0], float(row[1])
            reason = f"Inverse '{name_inverse}' ähnlich zu '{rt.name}'"
            if rt.id not in seen_ids or similarity > seen_ids[rt.id][0]:
                seen_ids[rt.id] = (similarity, reason)

        # Query 4: new_inverse vs stored name_inverse_embedding
        distance_expr_4 = RelationType.name_inverse_embedding.cosine_distance(new_inverse_embedding)
        query_4 = (
            select(RelationType, (literal(1.0) - distance_expr_4).label("similarity"))
            .where(
                *base_conditions,
                RelationType.name_inverse_embedding.isnot(None),
                distance_expr_4 <= max_distance,
            )
            .order_by(distance_expr_4)
            .limit(20)
        )
        result_4 = await session.execute(query_4)
        for row in result_4:
            rt, similarity = row[0], float(row[1])
            reason = f"Inverse '{name_inverse}' ähnlich zu '{rt.name_inverse}'"
            if rt.id not in seen_ids or similarity > seen_ids[rt.id][0]:
                seen_ids[rt.id] = (similarity, reason)

    # Fetch all matched RelationTypes and build result
    if seen_ids:
        rt_query = select(RelationType).where(RelationType.id.in_(seen_ids.keys()))
        rt_result = await session.execute(rt_query)
        for rt in rt_result.scalars():
            similarity, reason = seen_ids[rt.id]
            matches.append((rt, similarity, f"{reason} ({int(similarity * 100)}%)"))
            _increment_stat("matches_found")

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
# Embedding Update Functions
# =============================================================================


async def update_entity_embedding(
    session: AsyncSession,
    entity_id: uuid.UUID,
    embedding: list[float] | None = None,
    name: str | None = None,
) -> bool:
    """Update an entity's name embedding using DB-stored credentials."""
    from app.models import Entity

    try:
        entity = await session.get(Entity, entity_id)
        if not entity:
            return False

        if embedding is None:
            name_to_embed = name or entity.name
            # Pass session to use DB credentials instead of environment variables
            embedding = await generate_embedding(name_to_embed, session=session)

        if embedding is None:
            return False

        entity.name_embedding = embedding
        await session.flush()
        return True

    except Exception as e:
        logger.error("Failed to update entity embedding", entity_id=str(entity_id), error=str(e))
        return False


async def update_type_embedding[T: Base](
    session: AsyncSession,
    model_class: type[T],
    item_id: uuid.UUID,
    embedding: list[float] | None = None,
    name: str | None = None,
) -> bool:
    """Update a type's name embedding (generic for any type model)."""
    try:
        item = await session.get(model_class, item_id)
        if not item:
            return False

        if embedding is None:
            name_to_embed = name or item.name
            embedding = await generate_embedding(name_to_embed)

        if embedding is None:
            return False

        if hasattr(item, "name_embedding"):
            item.name_embedding = embedding
            await session.flush()
            return True

        return False

    except Exception as e:
        logger.error(f"Failed to update {model_class.__name__} embedding", item_id=str(item_id), error=str(e))
        return False


async def update_relation_type_embeddings(
    session: AsyncSession,
    relation_type_id: uuid.UUID,
) -> bool:
    """Update both name_embedding and name_inverse_embedding for a RelationType."""
    from app.models import RelationType

    try:
        rt = await session.get(RelationType, relation_type_id)
        if not rt:
            return False

        # Generate and store name_embedding
        name_embedding = await generate_embedding(rt.name)
        if name_embedding:
            rt.name_embedding = name_embedding

        # Generate and store name_inverse_embedding
        if rt.name_inverse:
            inverse_embedding = await generate_embedding(rt.name_inverse)
            if inverse_embedding:
                rt.name_inverse_embedding = inverse_embedding

        await session.flush()
        return True

    except Exception as e:
        logger.error("Failed to update RelationType embeddings", relation_type_id=str(relation_type_id), error=str(e))
        return False


async def update_facet_value_embedding(
    session: AsyncSession,
    facet_value_id: uuid.UUID,
) -> bool:
    """Update text_embedding for a FacetValue."""
    from app.models import FacetValue

    try:
        fv = await session.get(FacetValue, facet_value_id)
        if not fv or not fv.text_representation:
            return False

        embedding = await generate_embedding(fv.text_representation)
        if embedding:
            fv.text_embedding = embedding
            await session.flush()
            return True

        return False

    except Exception as e:
        logger.error("Failed to update FacetValue embedding", facet_value_id=str(facet_value_id), error=str(e))
        return False


async def batch_update_embeddings(
    session: AsyncSession,
    entity_type_id: uuid.UUID | None = None,
    batch_size: int = 100,
    only_missing: bool = True,
) -> int:
    """Batch update embeddings for multiple entities."""
    from app.models import Entity

    query = select(Entity).where(Entity.is_active.is_(True))

    if entity_type_id:
        query = query.where(Entity.entity_type_id == entity_type_id)

    if only_missing:
        query = query.where(Entity.name_embedding.is_(None))

    result = await session.execute(query)
    entities = result.scalars().all()

    if not entities:
        return 0

    logger.info(f"Updating embeddings for {len(entities)} entities")

    updated_count = 0

    # Process in batches
    for i in range(0, len(entities), batch_size):
        batch = entities[i : i + batch_size]
        names = [e.name for e in batch]

        try:
            embeddings = await generate_embeddings_batch(names)

            for entity, embedding in zip(batch, embeddings, strict=False):
                if embedding:
                    entity.name_embedding = embedding
                    updated_count += 1

            await session.commit()
            logger.info(f"Updated batch {i // batch_size + 1}, total: {updated_count}")

        except Exception as e:
            logger.error(f"Failed to update batch {i // batch_size + 1}", error=str(e))
            await session.rollback()

    return updated_count


async def batch_update_type_embeddings[T: Base](
    session: AsyncSession,
    model_class: type[T],
    only_missing: bool = True,
) -> int:
    """Batch update embeddings for all items of a type model."""
    query = select(model_class).where(model_class.is_active.is_(True))

    if only_missing and hasattr(model_class, "name_embedding"):
        query = query.where(model_class.name_embedding.is_(None))

    result = await session.execute(query)
    items = result.scalars().all()

    if not items:
        return 0

    logger.info(f"Updating embeddings for {len(items)} {model_class.__name__} items")

    names = [item.name for item in items]
    embeddings = await generate_embeddings_batch(names)

    updated_count = 0
    for item, embedding in zip(items, embeddings, strict=False):
        if embedding and hasattr(item, "name_embedding"):
            item.name_embedding = embedding
            updated_count += 1

    await session.flush()

    logger.info(f"Updated {updated_count} {model_class.__name__} embeddings")
    return updated_count


async def batch_update_facet_value_embeddings(
    session: AsyncSession,
    entity_id: uuid.UUID | None = None,
    facet_type_id: uuid.UUID | None = None,
    batch_size: int = 100,
    only_missing: bool = True,
) -> int:
    """
    Batch update text_embedding for FacetValues.

    Args:
        session: Database session
        entity_id: Optional filter by entity
        facet_type_id: Optional filter by facet type
        batch_size: Number of items to process at once
        only_missing: Only update items without embedding
    """
    from app.models import FacetValue

    query = select(FacetValue).where(FacetValue.text_representation.isnot(None))

    if entity_id:
        query = query.where(FacetValue.entity_id == entity_id)
    if facet_type_id:
        query = query.where(FacetValue.facet_type_id == facet_type_id)
    if only_missing:
        query = query.where(FacetValue.text_embedding.is_(None))

    result = await session.execute(query)
    facet_values = result.scalars().all()

    if not facet_values:
        return 0

    logger.info(f"Updating text_embedding for {len(facet_values)} FacetValues")

    updated_count = 0

    for i in range(0, len(facet_values), batch_size):
        batch = facet_values[i : i + batch_size]
        texts = [fv.text_representation for fv in batch]

        try:
            embeddings = await generate_embeddings_batch(texts)

            for fv, embedding in zip(batch, embeddings, strict=False):
                if embedding:
                    fv.text_embedding = embedding
                    updated_count += 1

            await session.commit()
            logger.info(f"Updated FacetValue batch {i // batch_size + 1}, total: {updated_count}")

        except Exception as e:
            logger.error(f"Failed to update FacetValue batch {i // batch_size + 1}", error=str(e))
            await session.rollback()

    return updated_count


async def batch_update_relation_type_embeddings(
    session: AsyncSession,
    only_missing: bool = True,
) -> int:
    """
    Batch update both name_embedding and name_inverse_embedding for RelationTypes.

    Args:
        session: Database session
        only_missing: Only update items without embedding
    """
    from app.models import RelationType

    # Get all active relation types
    query = select(RelationType).where(RelationType.is_active.is_(True))
    result = await session.execute(query)
    relation_types = result.scalars().all()

    if not relation_types:
        return 0

    logger.info(f"Updating embeddings for {len(relation_types)} RelationTypes")

    # Collect all texts to embed
    name_texts = []
    inverse_texts = []
    rt_list = []

    for rt in relation_types:
        needs_name = only_missing and rt.name_embedding is None
        needs_inverse = only_missing and rt.name_inverse_embedding is None

        if not only_missing or needs_name or needs_inverse:
            rt_list.append((rt, needs_name or not only_missing, needs_inverse or not only_missing))
            name_texts.append(rt.name if (needs_name or not only_missing) else None)
            inverse_texts.append(rt.name_inverse if (needs_inverse or not only_missing) else None)

    if not rt_list:
        return 0

    # Generate embeddings for names
    valid_name_texts = [t for t in name_texts if t]
    valid_inverse_texts = [t for t in inverse_texts if t]

    name_embeddings = await generate_embeddings_batch(valid_name_texts) if valid_name_texts else []
    inverse_embeddings = await generate_embeddings_batch(valid_inverse_texts) if valid_inverse_texts else []

    # Map back to relation types
    name_idx = 0
    inverse_idx = 0
    updated_count = 0

    for rt, needs_name, needs_inverse in rt_list:
        if needs_name and name_texts[rt_list.index((rt, needs_name, needs_inverse))]:
            if name_idx < len(name_embeddings) and name_embeddings[name_idx]:
                rt.name_embedding = name_embeddings[name_idx]
                updated_count += 1
            name_idx += 1

        if needs_inverse and inverse_texts[rt_list.index((rt, needs_name, needs_inverse))]:
            if inverse_idx < len(inverse_embeddings) and inverse_embeddings[inverse_idx]:
                rt.name_inverse_embedding = inverse_embeddings[inverse_idx]
                updated_count += 1
            inverse_idx += 1

    await session.flush()
    logger.info(f"Updated {updated_count} RelationType embeddings")
    return updated_count


async def populate_all_embeddings(
    session: AsyncSession,
    only_missing: bool = True,
) -> dict[str, int]:
    """
    Populate all embedding columns across the entire system.

    This is the main function to call for initial embedding population
    or to fill in missing embeddings after migration.

    Returns:
        Dict with counts for each type updated
    """
    from app.models import Category, EntityType, FacetType

    results = {}

    logger.info("Starting full embedding population...")

    # 1. EntityType embeddings
    logger.info("Updating EntityType embeddings...")
    results["entity_types"] = await batch_update_type_embeddings(session, EntityType, only_missing)

    # 2. FacetType embeddings
    logger.info("Updating FacetType embeddings...")
    results["facet_types"] = await batch_update_type_embeddings(session, FacetType, only_missing)

    # 3. Category embeddings
    logger.info("Updating Category embeddings...")
    results["categories"] = await batch_update_type_embeddings(session, Category, only_missing)

    # 4. RelationType embeddings (both name and name_inverse)
    logger.info("Updating RelationType embeddings...")
    results["relation_types"] = await batch_update_relation_type_embeddings(session, only_missing)

    # 5. Entity embeddings
    logger.info("Updating Entity embeddings...")
    results["entities"] = await batch_update_embeddings(session, only_missing=only_missing)

    # 6. FacetValue embeddings
    logger.info("Updating FacetValue embeddings...")
    results["facet_values"] = await batch_update_facet_value_embeddings(session, only_missing=only_missing)

    await session.commit()

    logger.info(f"Embedding population complete: {results}")
    return results


# =============================================================================
# Hierarchy Level Detection (AI-based, no hardcoded values)
# =============================================================================
# The hierarchy mapping is now detected dynamically via AI using
# get_hierarchy_mapping_async() - see above.


def _normalize_type_name(name: str) -> str:
    """Normalize a type name for comparison."""
    if not name:
        return ""

    result = name.lower().strip()

    # Replace German umlauts
    umlaut_map = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}
    for umlaut, replacement in umlaut_map.items():
        result = result.replace(umlaut, replacement)

    # Replace common separators with space
    result = result.replace("-", " ").replace("_", " ")

    return result.strip()


# Cache for hierarchy mappings
# TTL: 30 min, max 200 entries (hierarchy info is relatively stable)
_hierarchy_mapping_cache: TTLCache[dict | None] = TTLCache(default_ttl=1800, max_size=200)


async def get_hierarchy_mapping_async(
    name: str,
    session: "AsyncSession | None" = None,
) -> dict | None:
    """
    Check if a name represents a territorial/geographic hierarchy level using AI.

    Returns a dict with parent_type_slug, hierarchy_level, and level_name
    if the term represents a territorial concept, otherwise None.

    Args:
        name: The term to classify
        session: Database session for loading LLM credentials
    """
    from app.models.user_api_credentials import LLMPurpose
    from services.llm_client_service import LLMClientService

    if not name or len(name) < 2:
        return None

    normalized = _normalize_type_name(name)

    # Check cache first (use sentinel for "checked but not territorial")
    cached = _hierarchy_mapping_cache.get(normalized)
    if cached is not None:
        return cached if cached != "__NOT_TERRITORIAL__" else None

    # Session is required for LLM access
    if not session:
        logger.debug("get_hierarchy_mapping_async: No session provided, skipping AI classification")
        return None

    start_time = time.time()

    try:
        llm_service = LLMClientService(session)
        client, config = await llm_service.get_system_client(LLMPurpose.DOCUMENT_ANALYSIS)

        if not client or not config:
            logger.warning("No LLM credentials configured for hierarchy mapping")
            return None

        model_name = llm_service.get_model_name(config)

        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": """You classify terms as territorial/geographic administrative divisions.

If the term represents a territorial/administrative division (in any language), respond with JSON:
{"is_territorial": true, "level": <1-4>, "level_name": "<English name for this level>"}

Hierarchy levels (from largest to smallest):
- Level 1: State/Province level (first-level administrative division of a country)
- Level 2: County/District level (second-level administrative division)
- Level 3: Municipality/City level (third-level, local government unit)
- Level 4: Neighborhood/Borough level (subdivision of a city)

If the term is NOT a territorial/geographic term, respond: {"is_territorial": false}

Respond ONLY with valid JSON, nothing else.""",
                },
                {"role": "user", "content": name},
            ],
            temperature=0,
            max_tokens=100,
        )

        # Track LLM usage
        if response.usage:
            await record_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=model_name,
                task_type=LLMTaskType.CLASSIFY,
                task_name="get_hierarchy_mapping",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                duration_ms=int((time.time() - start_time) * 1000),
                is_error=False,
            )

        import json

        result_text = response.choices[0].message.content.strip()
        result = json.loads(result_text)

        if result.get("is_territorial"):
            mapping = {
                "parent_type_slug": "territorial_entity",
                "hierarchy_level": result.get("level", 3),
                "level_name": result.get("level_name", name),
            }
            _hierarchy_mapping_cache.set(normalized, mapping)
            logger.debug(
                "hierarchy_mapping_detected",
                term=name,
                level=mapping["hierarchy_level"],
                level_name=mapping["level_name"],
            )
            return mapping
        else:
            # Cache "not territorial" with sentinel
            _hierarchy_mapping_cache.set(normalized, "__NOT_TERRITORIAL__")
            return None

    except Exception as e:
        logger.warning("hierarchy_mapping_detection_failed", term=name, error=str(e))
        # Track error
        await record_llm_usage(
            provider=LLMProvider.AZURE_OPENAI,
            model="unknown",
            task_type=LLMTaskType.CLASSIFY,
            task_name="get_hierarchy_mapping",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            duration_ms=int((time.time() - start_time) * 1000),
            is_error=True,
            error_message=str(e),
        )
        # Don't cache errors - allow retry on next call
        return None


def get_hierarchy_mapping(name: str) -> dict | None:
    """
    Check if a name maps to a hierarchy level of an existing EntityType.

    DEPRECATED: This sync wrapper cannot access database credentials.
    Use get_hierarchy_mapping_async() with a session in async code.

    Returns None since LLM access requires a database session.
    """
    logger.debug(
        "get_hierarchy_mapping_sync_deprecated",
        name=name,
        hint="Use get_hierarchy_mapping_async(name, session) in async code",
    )
    return None


# =============================================================================
# Location Duplicate Detection
# =============================================================================


def find_similar_locations_by_name(
    name: str,
    country: str,
    existing_locations: list["Location"],  # noqa: F821
    threshold: float = None,
) -> list[tuple["Location", float, str]]:  # noqa: F821
    """Find locations with similar names using normalization and fuzzy matching."""
    from difflib import SequenceMatcher

    if threshold is None:
        threshold = SIMILARITY_THRESHOLDS["location"]

    if not name or len(name) < 2:
        return []

    from app.models import Location

    new_normalized = Location.normalize_name(name, country)

    matches: list[tuple[Location, float, str]] = []

    for loc in existing_locations:
        if loc.name_normalized == new_normalized:
            matches.append((loc, 1.0, f"Exakter Match (normalisiert): '{loc.name}'"))
            continue

        similarity = SequenceMatcher(None, new_normalized, loc.name_normalized).ratio()

        if similarity >= threshold:
            matches.append((loc, similarity, f"Ähnlicher Name: '{loc.name}' ({int(similarity * 100)}%)"))

    matches.sort(key=lambda x: x[1], reverse=True)
    return matches


def check_location_geo_proximity(
    lat1: float | None,
    lon1: float | None,
    lat2: float | None,
    lon2: float | None,
    max_distance_km: float = 5.0,
) -> tuple[bool, float]:
    """Check if two locations are within a certain distance using Haversine formula."""
    import math

    if any(x is None for x in [lat1, lon1, lat2, lon2]):
        return False, float("inf")

    R = 6371.0  # Earth radius in km

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
    admin_level_1: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    exclude_id: uuid.UUID | None = None,
) -> tuple["Location", str] | None:  # noqa: F821
    """Find a duplicate location using multiple criteria."""
    from app.models import Location

    if not name or not country:
        return None

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
    name_matches = find_similar_locations_by_name(name, country, existing_locations)
    if name_matches:
        return name_matches[0][0], name_matches[0][2]

    # Check geo proximity
    if latitude is not None and longitude is not None:
        for loc in existing_locations:
            is_nearby, distance = check_location_geo_proximity(
                latitude, longitude, loc.latitude, loc.longitude, max_distance_km=5.0
            )
            if is_nearby:
                return loc, f"Geografisch nahe ({distance:.1f}km): '{loc.name}'"

    return None


# =============================================================================
# Config-Hash based Duplicate Detection
# =============================================================================


def compute_config_hash(config: dict) -> str:
    """Compute a deterministic hash for a configuration dictionary."""
    config_str = json.dumps(config, sort_keys=True, default=str)
    return hashlib.sha256(config_str.encode()).hexdigest()[:16]


async def find_duplicate_by_config[T: Base](
    session: AsyncSession,
    model_class: type[T],
    config_field: str,
    config_value: Any,
    additional_filters: dict[str, Any] = None,
    exclude_id: uuid.UUID | None = None,
) -> tuple[T, str] | None:
    """
    Generic function to find duplicates by configuration hash.

    Args:
        session: Database session
        model_class: SQLAlchemy model class
        config_field: Name of the config field to compare
        config_value: Value to compare against
        additional_filters: Additional WHERE conditions
        exclude_id: ID to exclude from results

    Returns:
        Tuple of (item, reason) if duplicate found
    """
    query = select(model_class)

    # Apply is_active filter if exists
    if hasattr(model_class, "is_active"):
        query = query.where(model_class.is_active.is_(True))

    # Apply additional filters
    if additional_filters:
        for field, value in additional_filters.items():
            if hasattr(model_class, field):
                query = query.where(getattr(model_class, field) == value)

    if exclude_id:
        query = query.where(model_class.id != exclude_id)

    result = await session.execute(query)
    items = result.scalars().all()

    if not items:
        return None

    new_hash = compute_config_hash({config_field: config_value})

    for item in items:
        existing_value = getattr(item, config_field, None)
        if existing_value:
            existing_hash = compute_config_hash({config_field: existing_value})
            if existing_hash == new_hash:
                item_name = getattr(item, "name", str(item.id))
                return item, f"Identische Konfiguration: '{item_name}'"

    return None


# =============================================================================
# FacetValue Semantic Duplicate Detection
# =============================================================================


async def find_similar_facet_values(
    session: AsyncSession,
    entity_id: uuid.UUID,
    facet_type_id: uuid.UUID,
    text_representation: str,
    threshold: float = None,
    exclude_id: uuid.UUID | None = None,
    embedding: list[float] | None = None,
) -> list[tuple["FacetValue", float, str]]:  # noqa: F821
    """
    Find FacetValues with semantically similar text_representation.

    Uses stored text_embedding for efficient pgvector search when available.
    Falls back to on-demand embedding generation for items without stored embeddings.

    Args:
        session: Database session
        entity_id: Entity to search within
        facet_type_id: FacetType to search within
        text_representation: Text to find similar values for
        threshold: Minimum similarity score
        exclude_id: Optional ID to exclude from results
        embedding: Pre-computed embedding (saves API call if available)
    """
    from app.models import FacetValue

    if threshold is None:
        threshold = SIMILARITY_THRESHOLDS["entity"]

    if not text_representation or len(text_representation) < 5:
        return []

    _increment_stat("searches")

    # Generate embedding for search text
    if embedding is None:
        embedding = await generate_embedding(text_representation)
    if embedding is None:
        return []

    # Use pgvector for items with stored embeddings
    max_distance = 1.0 - threshold
    distance_expr = FacetValue.text_embedding.cosine_distance(embedding)

    query = (
        select(FacetValue, (literal(1.0) - distance_expr).label("similarity"))
        .where(
            FacetValue.entity_id == entity_id,
            FacetValue.facet_type_id == facet_type_id,
            FacetValue.text_embedding.isnot(None),
            distance_expr <= max_distance,
        )
        .order_by(distance_expr)
        .limit(20)
    )

    if exclude_id:
        query = query.where(FacetValue.id != exclude_id)

    result = await session.execute(query)
    matches: list[tuple[FacetValue, float, str]] = []
    seen_ids = set()

    for row in result:
        fv = row[0]
        similarity = float(row[1])
        seen_ids.add(fv.id)
        text_preview = fv.text_representation[:50] if fv.text_representation else "..."
        matches.append((fv, similarity, f"Ähnlicher Wert: '{text_preview}...' ({int(similarity * 100)}%)"))
        _increment_stat("matches_found")

    # Fallback: check items without stored embeddings (on-demand generation)
    fallback_query = select(FacetValue).where(
        FacetValue.entity_id == entity_id,
        FacetValue.facet_type_id == facet_type_id,
        FacetValue.text_embedding.is_(None),
        FacetValue.text_representation.isnot(None),
    )
    if exclude_id:
        fallback_query = fallback_query.where(FacetValue.id != exclude_id)

    fallback_result = await session.execute(fallback_query)
    fallback_values = fallback_result.scalars().all()

    for fv in fallback_values:
        if fv.id in seen_ids or not fv.text_representation:
            continue

        existing_embedding = await generate_embedding(fv.text_representation)
        if existing_embedding is None:
            continue

        similarity = _cosine_similarity(embedding, existing_embedding)

        if similarity >= threshold:
            text_preview = fv.text_representation[:50]
            matches.append((fv, similarity, f"Ähnlicher Wert: '{text_preview}...' ({int(similarity * 100)}%)"))
            _increment_stat("matches_found")

    matches.sort(key=lambda x: x[1], reverse=True)
    return matches


# =============================================================================
# Simple Duplicate Detection Functions
# =============================================================================


async def find_duplicate_entity_attachment(
    session: AsyncSession,
    entity_id: uuid.UUID,
    file_hash: str,
    exclude_id: uuid.UUID | None = None,
) -> tuple["EntityAttachment", str] | None:  # noqa: F821
    """Find duplicate EntityAttachment by file_hash."""
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
