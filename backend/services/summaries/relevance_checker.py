"""Relevance Checker for Custom Summaries.

Checks if data changes are meaningful enough to warrant updating
a summary, using semantic analysis to determine relevance.
"""

import hashlib
import json
import time
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.llm_usage import LLMProvider, LLMTaskType
from services.llm_usage_tracker import record_llm_usage
from services.smart_query.query_interpreter import (
    AI_TEMPERATURE_LOW,
    get_openai_client,
)
from services.smart_query.utils import clean_json_response

logger = structlog.get_logger(__name__)

# Token limits
MAX_TOKENS_RELEVANCE_CHECK = 800


class RelevanceCheckResult:
    """Result of a relevance check."""

    def __init__(
        self,
        should_update: bool,
        score: float,
        reason: str,
        changes_summary: str | None = None,
        significant_changes: list[dict[str, Any]] | None = None,
    ):
        self.should_update = should_update
        self.score = score
        self.reason = reason
        self.changes_summary = changes_summary
        self.significant_changes = significant_changes or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "should_update": self.should_update,
            "score": self.score,
            "reason": self.reason,
            "changes_summary": self.changes_summary,
            "significant_changes": self.significant_changes,
        }


def calculate_data_hash(data: dict[str, Any]) -> str:
    """Calculate SHA256 hash of data for change detection.

    Args:
        data: Data dictionary to hash

    Returns:
        Hex digest of SHA256 hash
    """
    # Sort keys for deterministic hashing
    json_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(json_str.encode()).hexdigest()


def quick_change_detection(
    old_data: dict[str, Any],
    new_data: dict[str, Any],
) -> tuple[bool, str]:
    """Quick check if data has changed using hash comparison.

    This is a fast preliminary check before doing semantic analysis.

    Args:
        old_data: Previous cached data
        new_data: New data to compare

    Returns:
        Tuple of (has_changed, reason)
    """
    if not old_data and not new_data:
        return False, "Keine Daten vorhanden"

    if not old_data:
        return True, "Erste Datenerfassung"

    if not new_data:
        return True, "Keine neuen Daten verfügbar"

    old_hash = calculate_data_hash(old_data)
    new_hash = calculate_data_hash(new_data)

    if old_hash == new_hash:
        return False, "Daten unverändert (identischer Hash)"

    return True, "Datenänderungen erkannt"


def count_record_changes(
    old_data: dict[str, Any],
    new_data: dict[str, Any],
) -> dict[str, int]:
    """Count the number of records added, removed, and changed.

    Args:
        old_data: Previous cached data
        new_data: New data to compare

    Returns:
        Dict with counts: added, removed, changed, total_old, total_new
    """
    changes = {
        "added": 0,
        "removed": 0,
        "changed": 0,
        "total_old": 0,
        "total_new": 0,
    }

    # Extract data arrays from each widget
    for widget_key in set(list(old_data.keys()) + list(new_data.keys())):
        old_widget = old_data.get(widget_key, {})
        new_widget = new_data.get(widget_key, {})

        old_records = old_widget.get("data", [])
        new_records = new_widget.get("data", [])

        changes["total_old"] += len(old_records)
        changes["total_new"] += len(new_records)

        # Create lookup by entity_id if available
        old_by_id = {r.get("entity_id", str(i)): r for i, r in enumerate(old_records)}
        new_by_id = {r.get("entity_id", str(i)): r for i, r in enumerate(new_records)}

        # Count changes
        for eid in new_by_id:
            if eid not in old_by_id:
                changes["added"] += 1
            elif json.dumps(new_by_id[eid], sort_keys=True) != json.dumps(old_by_id[eid], sort_keys=True):
                changes["changed"] += 1

        for eid in old_by_id:
            if eid not in new_by_id:
                changes["removed"] += 1

    return changes


def calculate_change_significance(
    changes: dict[str, int],
    threshold: float = 0.1,
) -> tuple[float, str]:
    """Calculate the significance of changes.

    Args:
        changes: Dict from count_record_changes
        threshold: Minimum change ratio to consider significant (default 10%)

    Returns:
        Tuple of (significance_score, explanation)
    """
    total = max(changes["total_old"], changes["total_new"], 1)
    change_count = changes["added"] + changes["removed"] + changes["changed"]
    change_ratio = change_count / total

    if change_ratio == 0:
        return 0.0, "Keine Änderungen"

    # Score based on change ratio
    score = min(1.0, change_ratio * 2)  # Scale so 50% change = 1.0 score

    # Build explanation
    parts = []
    if changes["added"] > 0:
        parts.append(f"{changes['added']} neu")
    if changes["removed"] > 0:
        parts.append(f"{changes['removed']} entfernt")
    if changes["changed"] > 0:
        parts.append(f"{changes['changed']} geändert")

    explanation = ", ".join(parts) if parts else "Keine Änderungen"

    return score, explanation


async def check_relevance(
    summary_context: dict[str, Any],
    old_data: dict[str, Any],
    new_data: dict[str, Any],
    threshold: float = 0.3,
    use_ai: bool = True,
    session: AsyncSession | None = None,
) -> RelevanceCheckResult:
    """Check if data changes are relevant for the summary.

    Performs a multi-level check:
    1. Quick hash comparison (fast)
    2. Record-level change counting (medium)
    3. AI-based semantic analysis (slow, optional)

    Args:
        summary_context: Summary metadata (name, prompt, theme)
        old_data: Previous cached data
        new_data: New data to compare
        threshold: Minimum relevance score to trigger update (0-1)
        use_ai: Whether to use AI for semantic analysis
        session: Database session (optional, for AI calls)

    Returns:
        RelevanceCheckResult with should_update, score, and reason
    """
    # Step 1: Quick hash check
    has_changed, quick_reason = quick_change_detection(old_data, new_data)

    if not has_changed:
        return RelevanceCheckResult(
            should_update=False,
            score=0.0,
            reason=quick_reason,
        )

    # Step 2: Count changes
    changes = count_record_changes(old_data, new_data)
    significance_score, change_explanation = calculate_change_significance(changes, threshold)

    logger.debug(
        "change_significance_calculated",
        score=significance_score,
        changes=changes,
        explanation=change_explanation,
    )

    # If changes are minimal, skip update
    if significance_score < threshold * 0.5:
        return RelevanceCheckResult(
            should_update=False,
            score=significance_score,
            reason=f"Änderungen zu gering ({change_explanation})",
            changes_summary=change_explanation,
        )

    # Step 3: AI semantic analysis (if enabled and significant changes)
    if use_ai and significance_score >= threshold * 0.5:
        try:
            ai_result = await _check_relevance_with_ai(
                summary_context=summary_context,
                old_data=old_data,
                new_data=new_data,
                changes=changes,
            )

            # Combine scores (weighted average)
            combined_score = significance_score * 0.4 + ai_result["score"] * 0.6

            return RelevanceCheckResult(
                should_update=combined_score >= threshold,
                score=combined_score,
                reason=ai_result.get("reason", change_explanation),
                changes_summary=ai_result.get("summary", change_explanation),
                significant_changes=ai_result.get("highlights", []),
            )
        except Exception as e:
            logger.warning("AI relevance check failed, using fallback", error=str(e))
            # Fall through to non-AI result

    # Non-AI result based on change significance
    return RelevanceCheckResult(
        should_update=significance_score >= threshold,
        score=significance_score,
        reason=f"Änderungen erkannt: {change_explanation}",
        changes_summary=change_explanation,
    )


async def _check_relevance_with_ai(
    summary_context: dict[str, Any],
    old_data: dict[str, Any],
    new_data: dict[str, Any],
    changes: dict[str, int],
) -> dict[str, Any]:
    """Use AI to analyze the semantic relevance of changes.

    Args:
        summary_context: Summary name, prompt, theme
        old_data: Previous data
        new_data: New data
        changes: Change counts

    Returns:
        Dict with score, reason, summary, highlights
    """
    # Build a summary of the changes for AI analysis
    # (Don't send all data - just samples and statistics)
    change_summary = _build_change_summary(old_data, new_data, max_samples=5)

    prompt = f"""Analysiere diese Datenänderungen für eine Zusammenfassung.

## Zusammenfassung-Kontext:
- Name: {summary_context.get("name", "Unbekannt")}
- Beschreibung: {summary_context.get("prompt", "Keine Beschreibung")[:200]}
- Thema: {summary_context.get("theme", {}).get("context", "Allgemein")}

## Änderungsstatistik:
- Neue Einträge: {changes["added"]}
- Entfernte Einträge: {changes["removed"]}
- Geänderte Einträge: {changes["changed"]}
- Gesamt vorher: {changes["total_old"]}
- Gesamt nachher: {changes["total_new"]}

## Änderungsbeispiele:
{change_summary}

## Aufgabe:
Bewerte ob diese Änderungen für den Benutzer relevant sind.
Berücksichtige:
1. Sind die Änderungen inhaltlich bedeutsam (z.B. neue wichtige Daten)?
2. Passen die Änderungen zum Thema der Zusammenfassung?
3. Würde ein Benutzer von diesen Änderungen erfahren wollen?

Antworte mit JSON:
{{
  "score": 0.0-1.0,
  "reason": "Kurze Begründung",
  "summary": "Zusammenfassung der wichtigsten Änderungen",
  "highlights": ["Wichtige Änderung 1", "Wichtige Änderung 2"]
}}

Antworte NUR mit validem JSON."""

    try:
        client = get_openai_client()

        start_time = time.time()
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": "Du bist ein Datenanalyst der Änderungen bewertet. Antworte nur mit JSON.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=AI_TEMPERATURE_LOW,
            max_tokens=MAX_TOKENS_RELEVANCE_CHECK,
        )

        if response.usage:
            await record_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=settings.azure_openai_deployment_name,
                task_type=LLMTaskType.RELEVANCE_CHECK,
                task_name="_check_relevance_with_ai",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                duration_ms=int((time.time() - start_time) * 1000),
                is_error=False,
            )

        content = response.choices[0].message.content.strip()
        content = clean_json_response(content)
        result = json.loads(content)

        # Validate and normalize score
        score = float(result.get("score", 0.5))
        score = max(0.0, min(1.0, score))
        result["score"] = score

        logger.debug(
            "ai_relevance_check_completed",
            score=score,
            reason=result.get("reason", "")[:100],
        )

        return result

    except Exception as e:
        logger.error("AI relevance check failed", error=str(e))
        # Return neutral result on failure
        return {
            "score": 0.5,
            "reason": f"KI-Analyse fehlgeschlagen: {str(e)}",
            "summary": "Automatische Analyse nicht verfügbar",
            "highlights": [],
        }


def _build_change_summary(
    old_data: dict[str, Any],
    new_data: dict[str, Any],
    max_samples: int = 5,
) -> str:
    """Build a human-readable summary of data changes.

    Args:
        old_data: Previous data
        new_data: New data
        max_samples: Maximum number of change examples to include

    Returns:
        Formatted string describing changes
    """
    parts = []
    samples_collected = 0

    for widget_key in new_data:
        if samples_collected >= max_samples:
            break

        old_widget = old_data.get(widget_key, {})
        new_widget = new_data.get(widget_key, {})

        old_records = old_widget.get("data", [])
        new_records = new_widget.get("data", [])

        # Sample new records
        old_ids = {r.get("entity_id") for r in old_records if r.get("entity_id")}
        for record in new_records[: max_samples - samples_collected]:
            entity_id = record.get("entity_id")
            if entity_id and entity_id not in old_ids:
                name = record.get("name", entity_id)
                parts.append(f"+ Neu: {name}")
                samples_collected += 1

        # Sample removed records
        new_ids = {r.get("entity_id") for r in new_records if r.get("entity_id")}
        for record in old_records[: max_samples - samples_collected]:
            entity_id = record.get("entity_id")
            if entity_id and entity_id not in new_ids:
                name = record.get("name", entity_id)
                parts.append(f"- Entfernt: {name}")
                samples_collected += 1

    if not parts:
        return "Keine detaillierten Änderungen verfügbar"

    return "\n".join(parts)


def should_notify_user(
    result: RelevanceCheckResult,
    notification_threshold: float = 0.5,
) -> bool:
    """Determine if user should be notified about changes.

    Args:
        result: Result from relevance check
        notification_threshold: Minimum score to notify (default 0.5)

    Returns:
        True if user should be notified
    """
    return result.should_update and result.score >= notification_threshold
