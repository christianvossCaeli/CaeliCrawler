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
from typing import Any, List, Optional, Tuple, TYPE_CHECKING

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.models import Entity

# Constants for similarity matching
MIN_SUBSTRING_LENGTH = 3
SUBSTRING_SIMILARITY_BOOST = 0.85
DEFAULT_SIMILARITY_THRESHOLD = 0.85
MAX_CANDIDATES_FOR_COMPARISON = 500  # Limit memory usage

# Common German location prefixes to remove for comparison
GERMAN_PREFIXES = (
    "stadt ",
    "gemeinde ",
    "markt ",
    "marktgemeinde ",
    "landkreis ",
    "kreis ",
    "samtgemeinde ",
    "verbandsgemeinde ",
    "ortsgemeinde ",
)

# Common suffixes to remove
GERMAN_SUFFIXES = (" stadt", " gemeinde", " (stadt)", " (gemeinde)")

# Character replacements for normalization
CHARACTER_REPLACEMENTS = {
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
    # Handle empty strings
    if not name1 or not name2:
        return 0.0

    if len(name1) < 2 or len(name2) < 2:
        return 0.0

    # Normalize for comparison
    n1 = _normalize_for_comparison(name1)
    n2 = _normalize_for_comparison(name2)

    # Handle empty after normalization
    if not n1 or not n2:
        return 0.0

    # Exact match after normalization
    if n1 == n2:
        return 1.0

    # Calculate base similarity using SequenceMatcher
    ratio = SequenceMatcher(None, n1, n2).ratio()

    # Boost if one is substring of other (after normalization)
    if len(n1) > MIN_SUBSTRING_LENGTH and len(n2) > MIN_SUBSTRING_LENGTH:
        if n1 in n2 or n2 in n1:
            ratio = max(ratio, SUBSTRING_SIMILARITY_BOOST)

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
    if not name:
        return ""

    result = name.strip().lower()

    # Remove common German location prefixes
    for prefix in GERMAN_PREFIXES:
        if result.startswith(prefix):
            result = result[len(prefix):]
            break  # Only remove one prefix

    # Remove common suffixes
    for suffix in GERMAN_SUFFIXES:
        if result.endswith(suffix):
            result = result[: -len(suffix)]
            break  # Only remove one suffix

    # Replace German umlauts with ASCII equivalents
    for old, new in CHARACTER_REPLACEMENTS.items():
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
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    limit: int = 5,
) -> List[Tuple["Entity", float]]:
    """
    Find entities with similar names using optimized database queries.

    This function uses a two-phase approach:
    1. Pre-filter candidates using database LIKE queries on normalized name
    2. Calculate exact similarity only for candidates

    This avoids loading ALL entities into memory.

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
    from app.utils.text import normalize_entity_name

    if not name or len(name) < 2:
        return []

    # Normalize the search name
    normalized_search = normalize_entity_name(name, country="DE")
    comparison_normalized = _normalize_for_comparison(name)

    # Phase 1: Get candidates using database pre-filtering
    # Use multiple strategies to find potential matches
    candidates: List[Entity] = []

    # Strategy 1: Exact normalized name match
    exact_result = await session.execute(
        select(Entity).where(
            Entity.entity_type_id == entity_type_id,
            Entity.is_active.is_(True),
            Entity.name_normalized == normalized_search,
        )
    )
    exact_match = exact_result.scalar_one_or_none()
    if exact_match:
        return [(exact_match, 1.0)]

    # Strategy 2: Prefix-based search (first 3+ chars of normalized name)
    if len(normalized_search) >= 3:
        prefix = normalized_search[:3]
        prefix_result = await session.execute(
            select(Entity)
            .where(
                Entity.entity_type_id == entity_type_id,
                Entity.is_active.is_(True),
                Entity.name_normalized.startswith(prefix),
            )
            .limit(MAX_CANDIDATES_FOR_COMPARISON)
        )
        candidates.extend(prefix_result.scalars().all())

    # Strategy 3: Contains search for longer names
    if len(normalized_search) >= 5:
        # Escape LIKE special characters
        escaped_search = (
            normalized_search.replace("%", r"\%").replace("_", r"\_")
        )
        contains_result = await session.execute(
            select(Entity)
            .where(
                Entity.entity_type_id == entity_type_id,
                Entity.is_active.is_(True),
                Entity.name_normalized.contains(escaped_search[2:5]),
            )
            .limit(MAX_CANDIDATES_FOR_COMPARISON)
        )
        for entity in contains_result.scalars().all():
            if entity not in candidates:
                candidates.append(entity)

    # Strategy 4: If still no candidates, get entities with similar length
    if not candidates and len(normalized_search) >= 3:
        length_result = await session.execute(
            select(Entity)
            .where(
                Entity.entity_type_id == entity_type_id,
                Entity.is_active.is_(True),
                func.length(Entity.name_normalized).between(
                    len(normalized_search) - 3,
                    len(normalized_search) + 3,
                ),
            )
            .limit(MAX_CANDIDATES_FOR_COMPARISON)
        )
        candidates.extend(length_result.scalars().all())

    # Phase 2: Calculate exact similarity for candidates
    matches: List[Tuple[Entity, float]] = []

    seen_ids = set()
    for entity in candidates:
        if entity.id in seen_ids:
            continue
        seen_ids.add(entity.id)

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


def get_normalized_variants(name: str) -> List[str]:
    """
    Generate normalized variants of a name for searching.

    Useful for building search queries that might match the name.

    Args:
        name: Original name

    Returns:
        List of normalized variant strings
    """
    from app.utils.text import normalize_entity_name

    variants = set()

    # Standard normalization
    variants.add(normalize_entity_name(name, country="DE"))

    # Comparison normalization (with prefix/suffix removal)
    variants.add(_normalize_for_comparison(name))

    # Without spaces
    no_spaces = normalize_entity_name(name, country="DE").replace(" ", "")
    variants.add(no_spaces)

    return list(variants)
