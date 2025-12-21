"""
Similarity matching utilities for entity deduplication.

Provides fuzzy name matching to detect similar entities that might be
duplicates despite slight spelling variations.

Example variations that would match:
- "München" vs "Muenchen" (umlaut variations)
- "Stadt München" vs "München" (prefix variations)
- "Cologne" vs "Köln" (same city, different names - would NOT match by default)
"""

import re
import uuid
from difflib import SequenceMatcher
from typing import List, Optional, Tuple, TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.models import Entity


def calculate_name_similarity(name1: str, name2: str) -> float:
    """
    Calculate similarity between two entity names.

    Uses a combination of:
    1. Substring matching (boost if one contains the other)
    2. SequenceMatcher ratio (for general string similarity)
    3. Normalized comparison (handles umlauts, prefixes)

    Args:
        name1: First name to compare
        name2: Second name to compare

    Returns:
        Similarity score between 0.0 (no match) and 1.0 (exact match)

    Examples:
        >>> calculate_name_similarity("München", "München")
        1.0
        >>> calculate_name_similarity("München", "Muenchen")
        0.9  # High similarity due to umlaut normalization
        >>> calculate_name_similarity("Stadt München", "München")
        0.85  # High similarity due to prefix removal
        >>> calculate_name_similarity("Berlin", "Hamburg")
        0.3  # Low similarity - different cities
    """
    # Normalize for comparison
    n1 = _normalize_for_comparison(name1)
    n2 = _normalize_for_comparison(name2)

    # Exact match after normalization
    if n1 == n2:
        return 1.0

    # Calculate base similarity using SequenceMatcher
    ratio = SequenceMatcher(None, n1, n2).ratio()

    # Boost if one is substring of other (after normalization)
    if len(n1) > 3 and len(n2) > 3:
        if n1 in n2 or n2 in n1:
            ratio = max(ratio, 0.85)

    # Word-based Jaccard similarity for multi-word names
    words1 = set(n1.split())
    words2 = set(n2.split())

    if words1 and words2:
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        if union > 0:
            jaccard = intersection / union
            # Use max of SequenceMatcher and Jaccard
            ratio = max(ratio, jaccard)

    return round(ratio, 3)


def _normalize_for_comparison(name: str) -> str:
    """
    Normalize name for similarity comparison.

    More aggressive than the standard normalize_entity_name to catch
    more variations when doing fuzzy matching.

    Args:
        name: Name to normalize

    Returns:
        Normalized name for comparison
    """
    result = name.lower()

    # Remove common German location prefixes
    prefixes = [
        "stadt ",
        "gemeinde ",
        "markt ",
        "marktgemeinde ",
        "landkreis ",
        "kreis ",
        "samtgemeinde ",
        "verbandsgemeinde ",
        "ortsgemeinde ",
    ]
    for prefix in prefixes:
        if result.startswith(prefix):
            result = result[len(prefix) :]

    # Remove common suffixes
    suffixes = [" stadt", " gemeinde", " (stadt)", " (gemeinde)"]
    for suffix in suffixes:
        if result.endswith(suffix):
            result = result[: -len(suffix)]

    # Replace German umlauts with ASCII equivalents
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "à": "a",
        "á": "a",
        "â": "a",
        "ç": "c",
        "ñ": "n",
    }
    for old, new in replacements.items():
        result = result.replace(old, new)

    # Remove special characters but keep spaces
    result = re.sub(r"[^a-z0-9\s]", "", result)

    # Normalize whitespace
    result = " ".join(result.split())

    return result.strip()


async def find_similar_entities(
    session: AsyncSession,
    entity_type_id: uuid.UUID,
    name: str,
    threshold: float = 0.85,
    limit: int = 5,
) -> List[Tuple["Entity", float]]:
    """
    Find entities with similar names.

    WARNING: This function loads ALL active entities of the given type
    into memory for comparison. For large datasets, consider using
    PostgreSQL's pg_trgm extension instead.

    Args:
        session: Database session
        entity_type_id: UUID of the entity type to search
        name: Name to find similar entities for
        threshold: Minimum similarity score (0.0 - 1.0)
        limit: Maximum number of matches to return

    Returns:
        List of (Entity, similarity_score) tuples, sorted by score descending
    """
    from app.models import Entity

    # Load all active entities of this type
    # NOTE: For production with large datasets, this should use pg_trgm
    result = await session.execute(
        select(Entity).where(
            Entity.entity_type_id == entity_type_id,
            Entity.is_active.is_(True),
        )
    )
    all_entities = result.scalars().all()

    # Calculate similarity for each
    matches: List[Tuple[Entity, float]] = []

    for entity in all_entities:
        similarity = calculate_name_similarity(name, entity.name)
        if similarity >= threshold:
            matches.append((entity, similarity))

    # Sort by similarity descending
    matches.sort(key=lambda x: x[1], reverse=True)

    return matches[:limit]


def is_likely_duplicate(
    name1: str, name2: str, strict_threshold: float = 0.9
) -> bool:
    """
    Quick check if two names are likely duplicates.

    Args:
        name1: First name
        name2: Second name
        strict_threshold: Minimum similarity to consider as duplicate

    Returns:
        True if names are likely duplicates
    """
    return calculate_name_similarity(name1, name2) >= strict_threshold
