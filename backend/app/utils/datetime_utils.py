"""Centralized datetime utilities for consistent date/time formatting.

This module provides:
- Standard date/time formatters for display
- ISO 8601 formatters for API responses
- Relative time formatters (e.g., "2 hours ago")
- Timezone-aware datetime handling
- Date parsing from various formats

Usage:
    from app.utils.datetime_utils import (
        format_datetime,
        format_date,
        format_relative_time,
        parse_datetime,
        now_utc,
    )

    # Format for display
    formatted = format_datetime(my_datetime)  # "31.12.2024 14:30"

    # Format for API
    iso_str = format_iso(my_datetime)  # "2024-12-31T14:30:00Z"

    # Relative time
    relative = format_relative_time(my_datetime)  # "vor 2 Stunden"
"""

from datetime import UTC, datetime

# =============================================================================
# Constants
# =============================================================================

# Standard German date formats
DATE_FORMAT_DE = "%d.%m.%Y"
DATETIME_FORMAT_DE = "%d.%m.%Y %H:%M"
DATETIME_FORMAT_DE_FULL = "%d.%m.%Y %H:%M:%S"

# ISO 8601 formats
ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
ISO_FORMAT_WITH_MS = "%Y-%m-%dT%H:%M:%S.%fZ"
DATE_ISO_FORMAT = "%Y-%m-%d"

# Time thresholds for relative time (in seconds)
MINUTE = 60
HOUR = 60 * MINUTE
DAY = 24 * HOUR
WEEK = 7 * DAY
MONTH = 30 * DAY
YEAR = 365 * DAY


# =============================================================================
# Core Functions
# =============================================================================


def now_utc() -> datetime:
    """Get current UTC datetime (timezone-aware).

    Returns:
        Current datetime in UTC timezone
    """
    return datetime.now(UTC)


def ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime is UTC. Converts naive datetime to UTC.

    Args:
        dt: Datetime to convert

    Returns:
        UTC datetime (timezone-aware)
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


# =============================================================================
# Formatting Functions
# =============================================================================


def format_datetime(
    dt: datetime | None,
    format_str: str = DATETIME_FORMAT_DE,
    default: str = "-",
) -> str:
    """Format datetime for display.

    Args:
        dt: Datetime to format (can be None)
        format_str: strftime format string (default: German format)
        default: Value to return if dt is None

    Returns:
        Formatted datetime string
    """
    if dt is None:
        return default
    try:
        return dt.strftime(format_str)
    except (ValueError, AttributeError):
        return default


def format_date(
    dt: datetime | None,
    format_str: str = DATE_FORMAT_DE,
    default: str = "-",
) -> str:
    """Format date for display (no time).

    Args:
        dt: Datetime to format (can be None)
        format_str: strftime format string (default: German format)
        default: Value to return if dt is None

    Returns:
        Formatted date string
    """
    return format_datetime(dt, format_str, default)


def format_iso(dt: datetime | None, default: str = "") -> str:
    """Format datetime as ISO 8601 string for API responses.

    Args:
        dt: Datetime to format (can be None)
        default: Value to return if dt is None

    Returns:
        ISO 8601 formatted string (e.g., "2024-12-31T14:30:00Z")
    """
    if dt is None:
        return default
    try:
        # Ensure UTC and format
        utc_dt = ensure_utc(dt)
        return utc_dt.strftime(ISO_FORMAT)
    except (ValueError, AttributeError):
        return default


def format_relative_time(
    dt: datetime | None,
    now: datetime | None = None,
    locale: str = "de",
) -> str:
    """Format datetime as relative time string.

    Args:
        dt: Datetime to format (can be None)
        now: Reference time (default: current UTC time)
        locale: Language code ("de" or "en")

    Returns:
        Relative time string (e.g., "vor 2 Stunden" / "2 hours ago")
    """
    if dt is None:
        return "-"

    if now is None:
        now = now_utc()

    try:
        # Ensure both are UTC for comparison
        dt_utc = ensure_utc(dt)
        now_utc_time = ensure_utc(now)

        diff = now_utc_time - dt_utc
        seconds = diff.total_seconds()

        # Future times
        if seconds < 0:
            return _format_future_time(-seconds, locale)

        return _format_past_time(seconds, locale)
    except (ValueError, AttributeError, TypeError):
        return format_datetime(dt)


def _format_past_time(seconds: float, locale: str) -> str:
    """Format past time as relative string."""
    if seconds < MINUTE:
        return "gerade eben" if locale == "de" else "just now"

    if seconds < HOUR:
        minutes = int(seconds / MINUTE)
        if locale == "de":
            return f"vor {minutes} Min."
        return f"{minutes}m ago"

    if seconds < DAY:
        hours = int(seconds / HOUR)
        if locale == "de":
            return f"vor {hours} Std."
        return f"{hours}h ago"

    if seconds < WEEK:
        days = int(seconds / DAY)
        if locale == "de":
            return f"vor {days} {'Tag' if days == 1 else 'Tagen'}"
        return f"{days}d ago"

    if seconds < MONTH:
        weeks = int(seconds / WEEK)
        if locale == "de":
            return f"vor {weeks} {'Woche' if weeks == 1 else 'Wochen'}"
        return f"{weeks}w ago"

    if seconds < YEAR:
        months = int(seconds / MONTH)
        if locale == "de":
            return f"vor {months} {'Monat' if months == 1 else 'Monaten'}"
        return f"{months}mo ago"

    years = int(seconds / YEAR)
    if locale == "de":
        return f"vor {years} {'Jahr' if years == 1 else 'Jahren'}"
    return f"{years}y ago"


def _format_future_time(seconds: float, locale: str) -> str:
    """Format future time as relative string."""
    if seconds < MINUTE:
        return "gleich" if locale == "de" else "soon"

    if seconds < HOUR:
        minutes = int(seconds / MINUTE)
        if locale == "de":
            return f"in {minutes} Min."
        return f"in {minutes}m"

    if seconds < DAY:
        hours = int(seconds / HOUR)
        if locale == "de":
            return f"in {hours} Std."
        return f"in {hours}h"

    days = int(seconds / DAY)
    if locale == "de":
        return f"in {days} {'Tag' if days == 1 else 'Tagen'}"
    return f"in {days}d"


# =============================================================================
# Parsing Functions
# =============================================================================


def parse_datetime(
    value: str | None,
    formats: list[str] | None = None,
) -> datetime | None:
    """Parse datetime string from various formats.

    Args:
        value: String to parse (can be None)
        formats: List of formats to try (default: common formats)

    Returns:
        Parsed datetime or None if parsing fails
    """
    if not value:
        return None

    if formats is None:
        formats = [
            ISO_FORMAT,
            ISO_FORMAT_WITH_MS,
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
            DATETIME_FORMAT_DE,
            DATETIME_FORMAT_DE_FULL,
            DATE_FORMAT_DE,
            DATE_ISO_FORMAT,
        ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue

    # Try ISO format with fromisoformat (handles more variants)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError):
        pass

    return None


def parse_date(value: str | None) -> datetime | None:
    """Parse date string (without time).

    Args:
        value: Date string to parse (can be None)

    Returns:
        Parsed datetime (time set to 00:00:00) or None
    """
    return parse_datetime(value, formats=[DATE_FORMAT_DE, DATE_ISO_FORMAT])


# =============================================================================
# Utility Functions
# =============================================================================


def is_today(dt: datetime | None) -> bool:
    """Check if datetime is today (UTC).

    Args:
        dt: Datetime to check

    Returns:
        True if dt is today
    """
    if dt is None:
        return False
    today = now_utc().date()
    return ensure_utc(dt).date() == today


def is_this_week(dt: datetime | None) -> bool:
    """Check if datetime is in the current week (UTC).

    Args:
        dt: Datetime to check

    Returns:
        True if dt is in current week
    """
    if dt is None:
        return False
    now = now_utc()
    dt_utc = ensure_utc(dt)
    diff = (now - dt_utc).days
    return 0 <= diff < 7


def days_between(dt1: datetime, dt2: datetime) -> int:
    """Calculate days between two datetimes.

    Args:
        dt1: First datetime
        dt2: Second datetime

    Returns:
        Number of days between dt1 and dt2 (positive if dt2 > dt1)
    """
    return (ensure_utc(dt2).date() - ensure_utc(dt1).date()).days


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Constants
    "DATE_FORMAT_DE",
    "DATETIME_FORMAT_DE",
    "DATETIME_FORMAT_DE_FULL",
    "ISO_FORMAT",
    "DATE_ISO_FORMAT",
    # Core functions
    "now_utc",
    "ensure_utc",
    # Formatting
    "format_datetime",
    "format_date",
    "format_iso",
    "format_relative_time",
    # Parsing
    "parse_datetime",
    "parse_date",
    # Utilities
    "is_today",
    "is_this_week",
    "days_between",
]
