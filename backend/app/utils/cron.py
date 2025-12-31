"""Cron expression utilities shared across API and worker tasks."""

from datetime import UTC, datetime, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import croniter

from app.config import settings


def get_schedule_timezone() -> tzinfo:
    """Resolve the configured schedule timezone."""
    try:
        return ZoneInfo(settings.schedule_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return UTC


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
    base_time: datetime | None = None,
) -> croniter:
    """Create a croniter instance for a cron expression."""
    parts = _split_cron_expression(expression)
    schedule_tz = get_schedule_timezone()
    if base_time is None:
        base_time = datetime.now(schedule_tz)
    elif base_time.tzinfo is None:
        base_time = base_time.replace(tzinfo=schedule_tz)
    else:
        base_time = base_time.astimezone(schedule_tz)
    return croniter(expression, base_time, second_at_beginning=len(parts) == 6)


def is_valid_cron_expression(expression: str) -> bool:
    """Return True if cron expression is parseable by croniter."""
    try:
        croniter_for_expression(expression)
        return True
    except (ValueError, KeyError):
        return False


def normalize_cron_expression(expression: str | None) -> str | None:
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
