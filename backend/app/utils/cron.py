"""Cron expression utilities shared across API and worker tasks."""

from datetime import datetime, timezone
from typing import Optional

from croniter import croniter


def _split_cron_expression(expression: str) -> list[str]:
    """Split and validate cron expression field count.

    Supports 5-field (minute hour day month weekday)
    and 6-field (second minute hour day month weekday) formats.
    """
    parts = expression.strip().split()
    if len(parts) not in (5, 6):
        raise ValueError(
            "Expected 5 or 6 fields (minute hour day month weekday, optional leading seconds), "
            f"got {len(parts)}"
        )
    return parts


def croniter_for_expression(
    expression: str,
    base_time: Optional[datetime] = None,
) -> croniter:
    """Create a croniter instance for a cron expression."""
    parts = _split_cron_expression(expression)
    base_time = base_time or datetime.now(timezone.utc)
    return croniter(expression, base_time, second_at_beginning=len(parts) == 6)


def is_valid_cron_expression(expression: str) -> bool:
    """Return True if cron expression is parseable by croniter."""
    try:
        croniter_for_expression(expression)
        return True
    except (ValueError, KeyError):
        return False


def normalize_cron_expression(expression: Optional[str]) -> Optional[str]:
    """Normalize and validate cron expression input.

    Returns the trimmed expression or None for empty input.
    Raises ValueError for invalid expressions.
    """
    if expression is None:
        return None

    cleaned = expression.strip()
    if not cleaned:
        return None

    try:
        croniter_for_expression(cleaned)
    except (ValueError, KeyError) as exc:
        raise ValueError(f"Invalid cron expression: {exc}") from exc

    return cleaned
