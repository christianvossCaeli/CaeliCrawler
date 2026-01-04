"""
Cross-lingual concept matching using AI.

This module provides semantic concept normalization and equivalence checking
to handle synonyms and translations across languages.
"""

import time

import structlog

from app.core.cache import TTLCache
from app.models.llm_usage import LLMProvider, LLMTaskType
from services.llm_usage_tracker import record_llm_usage

logger = structlog.get_logger(__name__)

# =============================================================================
# Caches for concept operations
# =============================================================================

# Cache for canonical concepts to avoid repeated API calls
# TTL: 1 hour, max 500 entries (concepts are stable)
_canonical_concept_cache: TTLCache[str] = TTLCache(default_ttl=3600, max_size=500)

# Cache for concept equivalence checks
# TTL: 1 hour, max 1000 entries (equivalence checks are stable)
_concept_equivalence_cache: TTLCache[bool] = TTLCache(default_ttl=3600, max_size=1000)


def invalidate_concept_caches() -> None:
    """Invalidate all concept-related caches (canonical concepts and equivalence)."""
    _canonical_concept_cache.clear()
    _concept_equivalence_cache.clear()
    logger.info("Concept caches invalidated")


# =============================================================================
# Concept Normalization
# =============================================================================


async def get_canonical_concept(term: str) -> str | None:
    """
    Get a canonical English concept/translation for a term using AI.

    This helps match cross-lingual synonyms by normalizing terms
    in any language to a common English concept.

    Returns: English canonical form or None if generation fails.
    """
    from app.config import settings
    from services.ai_client import AzureOpenAIClientFactory

    start_time = time.time()
    error_message = None

    try:
        client = AzureOpenAIClientFactory.create_client()

        response = await client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": """You are a concept normalizer for database schema deduplication.

Your task: Given a term in ANY language, return the single most common English noun that represents this concept.

RULES:
1. Return ONLY ONE English word (or two-word compound noun if necessary)
2. Use singular form, lowercase, no articles
3. Use the most generic/common English term for that concept domain
4. Translations of the same concept MUST return the same English term
5. Focus on the core semantic meaning, not literal translation
6. For business/software terms, prefer standard industry terminology

OUTPUT FORMAT: Just the English term, nothing else.""",
                },
                {"role": "user", "content": term},
            ],
            temperature=0,
            max_tokens=20,
        )

        # Track LLM usage
        if response.usage:
            await record_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=settings.azure_openai_deployment_name,
                task_type=LLMTaskType.CLASSIFY,
                task_name="get_canonical_concept",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                duration_ms=int((time.time() - start_time) * 1000),
                is_error=False,
            )

        canonical = response.choices[0].message.content.strip().lower()
        logger.debug(
            "canonical_concept_generated",
            original_term=term,
            canonical=canonical,
        )
        return canonical

    except Exception as e:
        error_message = str(e)
        logger.warning("canonical_concept_generation_failed", term=term, error=str(e))
        # Track error
        await record_llm_usage(
            provider=LLMProvider.AZURE_OPENAI,
            model=settings.azure_openai_deployment_name,
            task_type=LLMTaskType.CLASSIFY,
            task_name="get_canonical_concept",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            duration_ms=int((time.time() - start_time) * 1000),
            is_error=True,
            error_message=error_message,
        )
        return None


async def get_cached_canonical_concept(term: str) -> str | None:
    """Get canonical concept with caching."""
    term_lower = term.lower().strip()

    cached = _canonical_concept_cache.get(term_lower)
    if cached is not None:
        return cached

    canonical = await get_canonical_concept(term)
    if canonical:
        _canonical_concept_cache.set(term_lower, canonical)

    return canonical


# =============================================================================
# Concept Equivalence
# =============================================================================


async def are_concepts_equivalent(term1: str, term2: str) -> bool:
    """
    Check if two terms represent the same concept using AI.

    This is more reliable than comparing canonical translations because
    it directly evaluates semantic equivalence.

    Returns: True if the terms represent the same concept, False otherwise.
    """
    from app.config import settings
    from services.ai_client import AzureOpenAIClientFactory

    # Normalize and create cache key (sorted to make symmetric)
    t1, t2 = term1.lower().strip(), term2.lower().strip()
    if t1 == t2:
        return True

    cache_key = "|".join(sorted([t1, t2]))
    cached = _concept_equivalence_cache.get(cache_key)
    if cached is not None:
        return cached

    start_time = time.time()

    try:
        client = AzureOpenAIClientFactory.create_client()

        response = await client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": """You determine if two terms represent the SAME concept for database deduplication.

Answer ONLY "yes" or "no".

Consider terms equivalent if they:
- Are translations of each other across languages
- Are synonyms referring to the same category of data
- Are spelling or plural variations of the same concept

Consider terms NOT equivalent if they:
- Refer to different concepts even if related
- Have distinctly different meanings in context""",
                },
                {
                    "role": "user",
                    "content": f"Are these the same concept?\nTerm 1: {term1}\nTerm 2: {term2}",
                },
            ],
            temperature=0,
            max_tokens=5,
        )

        # Track LLM usage
        if response.usage:
            await record_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=settings.azure_openai_deployment_name,
                task_type=LLMTaskType.CLASSIFY,
                task_name="are_concepts_equivalent",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                duration_ms=int((time.time() - start_time) * 1000),
                is_error=False,
            )

        answer = response.choices[0].message.content.strip().lower()
        is_equivalent = answer.startswith("yes")

        _concept_equivalence_cache.set(cache_key, is_equivalent)

        logger.debug(
            "concept_equivalence_check",
            term1=term1,
            term2=term2,
            is_equivalent=is_equivalent,
        )
        return is_equivalent

    except Exception as e:
        logger.warning("concept_equivalence_check_failed", term1=term1, term2=term2, error=str(e))
        # Track error
        await record_llm_usage(
            provider=LLMProvider.AZURE_OPENAI,
            model=settings.azure_openai_deployment_name,
            task_type=LLMTaskType.CLASSIFY,
            task_name="are_concepts_equivalent",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            duration_ms=int((time.time() - start_time) * 1000),
            is_error=True,
            error_message=str(e),
        )
        # Don't cache errors - allow retry on next call
        return False


__all__ = [
    "get_canonical_concept",
    "get_cached_canonical_concept",
    "are_concepts_equivalent",
    "invalidate_concept_caches",
    # Internal caches (for cache invalidation)
    "_canonical_concept_cache",
    "_concept_equivalence_cache",
]
