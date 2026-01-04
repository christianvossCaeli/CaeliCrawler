"""Duplicate detection service for Custom Summaries.

This module provides functionality to detect similar or duplicate summaries
before creating new ones, helping users avoid redundancy and discover
existing relevant summaries.
"""

import re
from difflib import SequenceMatcher
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CustomSummary
from app.models.custom_summary import SummaryStatus

logger = structlog.get_logger(__name__)


class DuplicateCandidate:
    """Represents a potential duplicate summary."""

    def __init__(
        self,
        summary: CustomSummary,
        similarity_score: float,
        match_reasons: list[str],
    ):
        self.summary = summary
        self.similarity_score = similarity_score
        self.match_reasons = match_reasons

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "summary_id": str(self.summary.id),
            "name": self.summary.name,
            "description": self.summary.description,
            "status": self.summary.status.value,
            "similarity_score": round(self.similarity_score, 2),
            "match_reasons": self.match_reasons,
            "original_prompt": self.summary.original_prompt[:200] + "..."
            if len(self.summary.original_prompt) > 200
            else self.summary.original_prompt,
        }


async def find_duplicate_summaries(
    session: AsyncSession,
    user_id: UUID,
    prompt: str,
    entity_types: list[str] | None = None,
    threshold: float = 0.5,
    limit: int = 5,
) -> list[DuplicateCandidate]:
    """
    Find potentially duplicate summaries for a user.

    Uses multiple similarity metrics:
    1. Prompt text similarity (Levenshtein-based)
    2. Entity type overlap
    3. Theme/intent matching
    4. Facet type overlap

    Args:
        session: Database session
        user_id: User's ID
        prompt: The new prompt to check against
        entity_types: Optional list of entity types in the new query
        threshold: Minimum similarity score (0-1) to be considered a duplicate
        limit: Maximum number of candidates to return

    Returns:
        List of DuplicateCandidate objects, sorted by similarity score descending
    """
    # Get user's existing summaries (active and draft, not archived)
    result = await session.execute(
        select(CustomSummary)
        .where(
            CustomSummary.user_id == user_id,
            CustomSummary.status.in_([SummaryStatus.ACTIVE, SummaryStatus.DRAFT, SummaryStatus.PAUSED]),
        )
        .order_by(CustomSummary.updated_at.desc())
        .limit(100)  # Check last 100 summaries
    )
    summaries = result.scalars().all()

    if not summaries:
        return []

    # Normalize the new prompt
    normalized_prompt = _normalize_text(prompt)
    prompt_keywords = _extract_keywords(prompt)

    candidates: list[DuplicateCandidate] = []

    for summary in summaries:
        score, reasons = _calculate_similarity(
            new_prompt=normalized_prompt,
            new_keywords=prompt_keywords,
            new_entity_types=entity_types or [],
            existing_summary=summary,
        )

        if score >= threshold:
            candidates.append(
                DuplicateCandidate(
                    summary=summary,
                    similarity_score=score,
                    match_reasons=reasons,
                )
            )

    # Sort by score descending
    candidates.sort(key=lambda c: c.similarity_score, reverse=True)

    return candidates[:limit]


def _normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    # Lowercase
    text = text.lower()

    # Remove common filler words (German and English)
    filler_words = {
        "zeige",
        "mir",
        "alle",
        "die",
        "den",
        "das",
        "bitte",
        "gib",
        "show",
        "me",
        "all",
        "the",
        "please",
        "give",
        "eine",
        "einen",
        "einer",
        "a",
        "an",
        "mit",
        "und",
        "oder",
        "von",
        "zu",
        "für",
        "with",
        "and",
        "or",
        "from",
        "to",
        "for",
    }

    words = text.split()
    words = [w for w in words if w not in filler_words]

    return " ".join(words)


def _extract_keywords(text: str) -> set:
    """Extract meaningful keywords from text."""
    # Normalize
    text = text.lower()

    # Remove punctuation
    text = re.sub(r"[^\w\s]", " ", text)

    # Split and filter
    words = text.split()

    # Remove short words and common words
    stop_words = {
        "der",
        "die",
        "das",
        "den",
        "dem",
        "des",
        "ein",
        "eine",
        "einer",
        "einen",
        "einem",
        "eines",
        "und",
        "oder",
        "aber",
        "wenn",
        "weil",
        "dass",
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "if",
        "because",
        "that",
        "ist",
        "sind",
        "war",
        "waren",
        "wird",
        "werden",
        "is",
        "are",
        "was",
        "were",
        "will",
        "be",
        "ich",
        "du",
        "er",
        "sie",
        "es",
        "wir",
        "ihr",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "mir",
        "mich",
        "dir",
        "dich",
        "me",
        "my",
        "your",
        "zeige",
        "show",
        "gib",
        "give",
        "bitte",
        "please",
        "alle",
        "all",
        "jede",
        "jeder",
        "every",
        "each",
    }

    keywords = {w for w in words if len(w) > 2 and w not in stop_words}

    return keywords


def _calculate_similarity(
    new_prompt: str,
    new_keywords: set,
    new_entity_types: list[str],
    existing_summary: CustomSummary,
) -> tuple[float, list[str]]:
    """
    Calculate similarity between new prompt and existing summary.

    Returns:
        Tuple of (similarity_score, list_of_reasons)
    """
    scores: list[float] = []
    reasons: list[str] = []

    # 1. Text similarity (40% weight)
    existing_prompt = _normalize_text(existing_summary.original_prompt)
    text_sim = SequenceMatcher(None, new_prompt, existing_prompt).ratio()
    scores.append(text_sim * 0.4)

    if text_sim > 0.7:
        reasons.append(f"Ähnlicher Prompt-Text ({int(text_sim * 100)}%)")

    # 2. Keyword overlap (30% weight)
    existing_keywords = _extract_keywords(existing_summary.original_prompt)
    if new_keywords and existing_keywords:
        overlap = len(new_keywords & existing_keywords)
        total = len(new_keywords | existing_keywords)
        keyword_sim = overlap / total if total > 0 else 0
        scores.append(keyword_sim * 0.3)

        if keyword_sim > 0.5:
            common = new_keywords & existing_keywords
            reasons.append(f"Gemeinsame Begriffe: {', '.join(list(common)[:5])}")
    else:
        scores.append(0)

    # 3. Entity type overlap (20% weight)
    if new_entity_types:
        config = existing_summary.interpreted_config or {}
        existing_entity_type = config.get("primary_entity_type")

        if existing_entity_type:
            # Normalize for comparison
            new_types_normalized = {t.lower() for t in new_entity_types}
            existing_normalized = existing_entity_type.lower()

            if existing_normalized in new_types_normalized:
                scores.append(0.2)
                reasons.append(f"Gleicher Datentyp: {existing_entity_type}")
            else:
                scores.append(0)
        else:
            scores.append(0)
    else:
        scores.append(0)

    # 4. Theme/intent matching (10% weight)
    config = existing_summary.interpreted_config or {}
    existing_theme = config.get("theme", "")

    # Check if theme keywords appear in new prompt
    if existing_theme and existing_theme.lower() in new_prompt.lower():
        scores.append(0.1)
        reasons.append(f"Ähnliches Thema: {existing_theme}")
    else:
        scores.append(0)

    total_score = sum(scores)

    # Bonus for exact name match
    if existing_summary.name.lower() in new_prompt.lower():
        total_score = min(1.0, total_score + 0.1)
        reasons.append(f"Name erwähnt: {existing_summary.name}")

    return total_score, reasons


async def check_summary_exists_for_category(
    session: AsyncSession,
    user_id: UUID,
    category_id: UUID,
) -> CustomSummary | None:
    """
    Check if a summary already exists for a specific category.

    Useful when creating summaries from Analysis Themes/Categories
    to detect if one was already created.

    Args:
        session: Database session
        user_id: User's ID
        category_id: Category/Analysis Theme ID

    Returns:
        Existing CustomSummary if found, None otherwise
    """
    result = await session.execute(
        select(CustomSummary)
        .where(
            CustomSummary.user_id == user_id,
            CustomSummary.trigger_category_id == category_id,
            CustomSummary.status.in_([SummaryStatus.ACTIVE, SummaryStatus.DRAFT, SummaryStatus.PAUSED]),
        )
        .order_by(CustomSummary.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def find_summaries_for_entity_type(
    session: AsyncSession,
    user_id: UUID,
    entity_type_slug: str,
    limit: int = 5,
) -> list[CustomSummary]:
    """
    Find summaries that use a specific entity type.

    Useful for suggesting existing summaries when viewing entities.

    Args:
        session: Database session
        user_id: User's ID
        entity_type_slug: Entity type slug to search for
        limit: Maximum results

    Returns:
        List of matching CustomSummary objects
    """

    # Search in interpreted_config.primary_entity_type
    result = await session.execute(
        select(CustomSummary)
        .where(
            CustomSummary.user_id == user_id,
            CustomSummary.status.in_([SummaryStatus.ACTIVE, SummaryStatus.DRAFT]),
            CustomSummary.interpreted_config["primary_entity_type"].astext == entity_type_slug,
        )
        .order_by(CustomSummary.updated_at.desc())
        .limit(limit)
    )

    return list(result.scalars().all())
