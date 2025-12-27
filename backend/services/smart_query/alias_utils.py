"""Generic utilities for Smart Query - AI-based alias resolution and term expansion.

This module provides generic, AI-based functions for:
- Resolving aliases/abbreviations to canonical forms (any domain, not just geographic)
- Expanding abstract search terms into concrete terms
- Fuzzy matching suggestions
"""

import structlog
from typing import Optional, Tuple, List, Dict

from app.core.cache import TTLCache

logger = structlog.get_logger(__name__)

# Caches for AI-based lookups with TTL and max size
# Alias cache: 30 min TTL, max 500 entries
_alias_cache: TTLCache[Optional[str]] = TTLCache(default_ttl=1800, max_size=500)
# Term expansion cache: 1 hour TTL, max 300 entries (expansions are more stable)
_term_expansion_cache: TTLCache[List[str]] = TTLCache(default_ttl=3600, max_size=300)


def invalidate_alias_cache(domain: Optional[str] = None) -> int:
    """
    Invalidate alias cache entries.

    Args:
        domain: Optional domain to invalidate. If None, clears all.

    Returns:
        Number of entries invalidated.
    """
    if domain:
        return _alias_cache.invalidate_pattern(f"{domain}:")
    else:
        _alias_cache.clear()
        return -1  # -1 indicates full clear


def invalidate_term_expansion_cache(context: Optional[str] = None) -> int:
    """
    Invalidate term expansion cache entries.

    Args:
        context: Optional context to invalidate. If None, clears all.

    Returns:
        Number of entries invalidated.
    """
    if context:
        return _term_expansion_cache.invalidate_pattern(f"{context}:")
    else:
        _term_expansion_cache.clear()
        return -1


def invalidate_all_alias_caches() -> None:
    """Invalidate all alias-related caches. Call after schema changes."""
    _alias_cache.clear()
    _term_expansion_cache.clear()
    logger.info("All alias caches invalidated")


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate the Levenshtein distance between two strings.

    The Levenshtein distance is the minimum number of single-character edits
    (insertions, deletions, substitutions) required to transform one string into another.
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


async def resolve_alias_async(
    alias: str,
    domain: Optional[str] = None
) -> str:
    """
    Resolve an alias/abbreviation to its canonical form using AI.

    This is a GENERIC function that works for any domain:
    - Geographic aliases (region abbreviations, colloquial names)
    - Organization abbreviations
    - Technical acronyms
    - Any other type of alias

    Args:
        alias: The alias/abbreviation to resolve
        domain: Optional domain hint to help AI (e.g., "geographic", "organization", "technical")

    Returns:
        The canonical form if recognized, otherwise the original input.
    """
    if not alias:
        return alias

    normalized = alias.lower().strip()
    cache_key = f"{domain or 'generic'}:{normalized}"

    # Check cache first
    cached = _alias_cache.get(cache_key)
    if cached is not None:
        return cached if cached != "__NONE__" else alias

    try:
        from services.ai_client import AzureOpenAIClientFactory
        from app.config import settings

        client = AzureOpenAIClientFactory.create_client()

        domain_hint = f"\nContext/Domain: {domain}" if domain else ""

        response = await client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": f"""You resolve abbreviations and aliases to their official canonical forms.
{domain_hint}
If the input is a recognized abbreviation or alias, return the official full form.
If NOT a recognized alias, return "NONE".

IMPORTANT:
- Return names in their native language when applicable
- Handle abbreviations, acronyms, colloquial names, and common variations

Return ONLY the canonical form or "NONE", nothing else."""
                },
                {
                    "role": "user",
                    "content": alias
                }
            ],
            temperature=0,
            max_tokens=100,
        )

        result = response.choices[0].message.content.strip()

        if result.upper() == "NONE" or result.lower() == alias.lower():
            _alias_cache.set(cache_key, "__NONE__")  # Sentinel for "no alias found"
            return alias
        else:
            _alias_cache.set(cache_key, result)
            logger.debug("alias_resolved", alias=alias, canonical=result, domain=domain)
            return result

    except Exception as e:
        logger.warning("alias_resolution_failed", alias=alias, domain=domain, error=str(e))
        # Don't cache errors - allow retry on next call
        return alias


def resolve_alias(alias: str, domain: Optional[str] = None) -> str:
    """Synchronous wrapper for resolve_alias_async.

    Note: If called from an async context, returns the original alias unchanged.
    In async code, use resolve_alias_async() directly for proper resolution.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            logger.debug(
                "resolve_alias_sync_in_async_context",
                alias=alias,
                domain=domain,
                hint="Use resolve_alias_async() in async code"
            )
            return alias
        return loop.run_until_complete(resolve_alias_async(alias, domain))
    except RuntimeError:
        return asyncio.run(resolve_alias_async(alias, domain))


# Backward compatibility aliases
async def resolve_geographic_alias_async(alias: str) -> str:
    """Backward compatible wrapper - resolves geographic aliases."""
    return await resolve_alias_async(alias, domain="geographic")


def resolve_geographic_alias(alias: str) -> str:
    """Backward compatible wrapper - resolves geographic aliases."""
    return resolve_alias(alias, domain="geographic")


# Default threshold for fuzzy matching
DEFAULT_FUZZY_THRESHOLD = 2


async def get_known_values_from_db(
    entity_type_slug: str,
    hierarchy_level: Optional[int] = None
) -> List[str]:
    """
    Get list of known values from the database for fuzzy matching.

    This is a generic function that can retrieve any type of entity names.
    """
    try:
        from app.database import get_session_context
        from sqlalchemy import select
        from app.models import Entity, EntityType

        async with get_session_context() as session:
            et_result = await session.execute(
                select(EntityType).where(EntityType.slug == entity_type_slug)
            )
            entity_type = et_result.scalar_one_or_none()

            if not entity_type:
                return []

            query = select(Entity.name).where(
                Entity.entity_type_id == entity_type.id,
                Entity.is_active.is_(True),
            )

            if hierarchy_level is not None:
                query = query.where(Entity.hierarchy_level == hierarchy_level)

            result = await session.execute(query)
            return [row[0] for row in result.all()]
    except Exception as e:
        logger.warning("failed_to_get_values_from_db", entity_type=entity_type_slug, error=str(e))
        return []


async def suggest_correction_async(
    input_text: str,
    known_values: List[str],
    threshold: int = DEFAULT_FUZZY_THRESHOLD
) -> Optional[Tuple[str, str, int]]:
    """
    Suggest a correction for a potentially misspelled term.

    Uses fuzzy matching (Levenshtein distance) against known values.

    Args:
        input_text: The user input to check for corrections
        known_values: List of known valid values to match against
        threshold: Maximum edit distance to consider a match

    Returns:
        Tuple of (matched_value_lower, matched_value, distance) if found, None otherwise.
    """
    if not input_text or not known_values:
        return None

    normalized = input_text.lower().strip()

    best_match: Optional[Tuple[str, str, int]] = None
    min_distance = threshold + 1

    for value in known_values:
        distance = levenshtein_distance(normalized, value.lower())
        if distance <= threshold and distance < min_distance:
            min_distance = distance
            best_match = (value.lower(), value, distance)

    return best_match


def suggest_correction(
    input_text: str,
    known_values: List[str],
    threshold: int = DEFAULT_FUZZY_THRESHOLD
) -> Optional[Tuple[str, str, int]]:
    """Synchronous wrapper for suggest_correction_async."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return None
        return loop.run_until_complete(suggest_correction_async(input_text, known_values, threshold))
    except RuntimeError:
        return asyncio.run(suggest_correction_async(input_text, known_values, threshold))


# Backward compatibility: geo-specific wrappers
async def get_known_regions_from_db() -> List[str]:
    """Backward compatible - gets known regions."""
    return await get_known_values_from_db("territorial_entity", hierarchy_level=1)


async def suggest_geo_correction_async(
    input_text: str,
    threshold: int = DEFAULT_FUZZY_THRESHOLD
) -> Optional[Tuple[str, str, int]]:
    """Backward compatible wrapper for geographic corrections."""
    # First try AI-based resolution
    resolved = await resolve_alias_async(input_text, domain="geographic")
    if resolved != input_text:
        return None

    known_regions = await get_known_regions_from_db()
    return await suggest_correction_async(input_text, known_regions, threshold)


def suggest_geo_correction(
    input_text: str,
    threshold: int = DEFAULT_FUZZY_THRESHOLD
) -> Optional[Tuple[str, str, int]]:
    """Backward compatible synchronous wrapper."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return None
        return loop.run_until_complete(suggest_geo_correction_async(input_text, threshold))
    except RuntimeError:
        return asyncio.run(suggest_geo_correction_async(input_text, threshold))


async def find_all_suggestions_async(
    input_text: str,
    known_values: List[str],
    threshold: int = DEFAULT_FUZZY_THRESHOLD,
    max_suggestions: int = 3
) -> List[Tuple[str, str, int]]:
    """
    Find all suggestions within the threshold distance.

    Args:
        input_text: The user input to check
        known_values: List of known valid values
        threshold: Maximum edit distance to consider
        max_suggestions: Maximum number of suggestions to return

    Returns:
        List of tuples (value_lower, value, distance), sorted by distance
    """
    if not input_text or not known_values:
        return []

    normalized = input_text.lower().strip()

    suggestions = []
    for value in known_values:
        distance = levenshtein_distance(normalized, value.lower())
        if distance <= threshold:
            suggestions.append((value.lower(), value, distance))

    suggestions.sort(key=lambda x: (x[2], len(x[0])))
    return suggestions[:max_suggestions]


# Backward compatibility
async def find_all_geo_suggestions_async(
    input_text: str,
    threshold: int = DEFAULT_FUZZY_THRESHOLD,
    max_suggestions: int = 3
) -> List[Tuple[str, str, int]]:
    """Backward compatible wrapper for geographic suggestions."""
    resolved = await resolve_alias_async(input_text, domain="geographic")
    if resolved != input_text:
        return []

    known_regions = await get_known_regions_from_db()
    return await find_all_suggestions_async(input_text, known_regions, threshold, max_suggestions)


def find_all_geo_suggestions(
    input_text: str,
    threshold: int = DEFAULT_FUZZY_THRESHOLD,
    max_suggestions: int = 3
) -> List[Tuple[str, str, int]]:
    """Backward compatible synchronous wrapper."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return []
        return loop.run_until_complete(find_all_geo_suggestions_async(input_text, threshold, max_suggestions))
    except RuntimeError:
        return asyncio.run(find_all_geo_suggestions_async(input_text, threshold, max_suggestions))


async def resolve_with_suggestion_async(
    input_text: str,
    domain: Optional[str] = None,
    known_values: Optional[List[str]] = None,
    threshold: int = DEFAULT_FUZZY_THRESHOLD
) -> Tuple[str, Optional[str]]:
    """
    Resolve an input with optional suggestion for typos.

    Args:
        input_text: User input to resolve
        domain: Optional domain hint for AI resolution
        known_values: Optional list of known values for fuzzy matching
        threshold: Maximum edit distance for suggestions

    Returns:
        Tuple of (resolved_value, suggestion_message)
    """
    if not input_text:
        return input_text, None

    # Try AI-based resolution first
    resolved = await resolve_alias_async(input_text, domain)
    if resolved != input_text:
        return resolved, None

    # Try fuzzy matching if known values provided
    if known_values:
        suggestion = await suggest_correction_async(input_text, known_values, threshold)
        if suggestion:
            _, canonical, _ = suggestion
            return input_text, f"Meinten Sie '{canonical}'?"

    return input_text, None


def resolve_with_suggestion(
    input_text: str,
    domain: Optional[str] = None,
    known_values: Optional[List[str]] = None,
    threshold: int = DEFAULT_FUZZY_THRESHOLD
) -> Tuple[str, Optional[str]]:
    """Synchronous wrapper."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return input_text, None
        return loop.run_until_complete(resolve_with_suggestion_async(input_text, domain, known_values, threshold))
    except RuntimeError:
        return asyncio.run(resolve_with_suggestion_async(input_text, domain, known_values, threshold))


async def expand_terms_async(
    context: str,
    raw_terms: list[str]
) -> list[str]:
    """
    Expand abstract terms into concrete terms using AI.

    This is a GENERIC function that works for any domain:
    - Role titles (e.g., "decision maker" → specific job titles)
    - Event types (e.g., "event" → conference, workshop, etc.)
    - Any abstract category → specific instances

    Args:
        context: The context for expansion (helps AI understand the domain)
        raw_terms: List of terms to potentially expand

    Returns:
        List of expanded terms with duplicates removed.
    """
    from services.ai_client import AzureOpenAIClientFactory
    from app.config import settings

    expanded = []

    for term in raw_terms:
        term_lower = term.lower()
        cache_key = f"{context}:{term_lower}"

        # Check cache
        cached_terms = _term_expansion_cache.get(cache_key)
        if cached_terms is not None:
            expanded.extend(cached_terms)
            continue

        try:
            client = AzureOpenAIClientFactory.create_client()

            response = await client.chat.completions.create(
                model=settings.azure_openai_deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": f"""You expand abstract/umbrella terms into concrete, specific terms.

Context: {context}

If the term is an abstract/umbrella term, return a JSON array of specific concrete terms.
If the term is already concrete/specific, return a JSON array containing just that term.

Return ONLY a valid JSON array of strings, nothing else.
Maximum 10 terms."""
                    },
                    {
                        "role": "user",
                        "content": term
                    }
                ],
                temperature=0,
                max_tokens=200,
            )

            import json
            result = response.choices[0].message.content.strip()
            terms = json.loads(result)

            if isinstance(terms, list) and terms:
                _term_expansion_cache.set(cache_key, terms)
                expanded.extend(terms)
                logger.debug("term_expanded", original=term, expanded=terms, context=context)
            else:
                _term_expansion_cache.set(cache_key, [term])
                expanded.append(term)

        except Exception as e:
            logger.warning("term_expansion_failed", term=term, context=context, error=str(e))
            # Don't cache errors - allow retry on next call
            expanded.append(term)

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for t in expanded:
        if t.lower() not in seen:
            seen.add(t.lower())
            unique.append(t)

    return unique


def expand_terms(context: str, raw_terms: list[str]) -> list[str]:
    """Synchronous wrapper for expand_terms_async."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return raw_terms
        return loop.run_until_complete(expand_terms_async(context, raw_terms))
    except RuntimeError:
        return asyncio.run(expand_terms_async(context, raw_terms))


# Backward compatibility aliases
async def expand_search_terms_async(search_focus: str, raw_terms: list[str]) -> list[str]:
    """Backward compatible wrapper."""
    return await expand_terms_async(search_focus, raw_terms)


def expand_search_terms(search_focus: str, raw_terms: list[str]) -> list[str]:
    """Backward compatible wrapper."""
    return expand_terms(search_focus, raw_terms)
