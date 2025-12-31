"""
Internationalization (i18n) module for CaeliCrawler Backend.

Provides thread-safe/async-safe locale management using ContextVar.
Supports JSON-based translation files for German (de) and English (en).

Usage:
    from app.i18n import t, set_locale, get_locale

    # Set locale for current request context
    set_locale('en')

    # Get translated string
    message = t('errors.not_found', resource='Document')

    # Get current locale
    current = get_locale()
"""

import json
from contextvars import ContextVar
from pathlib import Path
from typing import Any

# Current locale context variable (thread/async safe)
_current_locale: ContextVar[str] = ContextVar("current_locale", default="de")

# Loaded translations cache
_translations: dict[str, dict[str, Any]] = {}

# Supported locales
SUPPORTED_LOCALES = frozenset({"de", "en"})
DEFAULT_LOCALE = "de"


def load_translations() -> None:
    """
    Load all translation files from the locales directory.

    Should be called once at application startup.
    """
    global _translations
    locales_dir = Path(__file__).parent / "locales"

    for locale in SUPPORTED_LOCALES:
        locale_file = locales_dir / f"{locale}.json"
        if locale_file.exists():
            with open(locale_file, encoding="utf-8") as f:
                _translations[locale] = json.load(f)
        else:
            _translations[locale] = {}


def get_translation(
    key: str,
    locale: str | None = None,
    default: str | None = None,
    **kwargs: Any,
) -> str:
    """
    Get translated string by key.

    Args:
        key: Dot-notation key (e.g., "errors.not_found")
        locale: Target locale (default: current context locale)
        default: Default value if key not found (default: returns key)
        **kwargs: Interpolation values for string formatting

    Returns:
        Translated string with interpolated values, or key/default if not found

    Example:
        >>> t("errors.not_found", resource="Document")
        "Document nicht gefunden"

        >>> t("errors.not_found_detail", resource="Document", identifier="123")
        "Document mit Kennung '123' existiert nicht"
    """
    # Ensure translations are loaded
    if not _translations:
        load_translations()

    # Determine locale
    loc = locale or _current_locale.get()
    if loc not in SUPPORTED_LOCALES:
        loc = DEFAULT_LOCALE

    # Navigate nested keys
    result = _get_nested_value(_translations.get(loc, {}), key)

    # Fallback to default locale if not found
    if result is None and loc != DEFAULT_LOCALE:
        result = _get_nested_value(_translations.get(DEFAULT_LOCALE, {}), key)

    # Use default or key if still not found
    if result is None:
        return default if default is not None else key

    # Interpolate kwargs if result is a string
    if kwargs and isinstance(result, str):
        try:  # noqa: SIM105
            result = result.format(**kwargs)
        except (KeyError, ValueError):
            # Return unformatted string if interpolation fails
            pass

    return result


def _get_nested_value(data: dict[str, Any], key: str) -> str | None:
    """
    Navigate nested dictionary using dot-notation key.

    Args:
        data: Dictionary to navigate
        key: Dot-notation key (e.g., "errors.not_found")

    Returns:
        Value at key path, or None if not found
    """
    result = data
    for part in key.split("."):
        if isinstance(result, dict):
            result = result.get(part)
        else:
            return None
    return result if isinstance(result, str) else None


# Shorthand alias
t = get_translation


def set_locale(locale: str) -> None:
    """
    Set the current locale for this context (request/coroutine).

    Args:
        locale: Locale code ('de' or 'en')
    """
    if locale in SUPPORTED_LOCALES:
        _current_locale.set(locale)
    else:
        _current_locale.set(DEFAULT_LOCALE)


def get_locale() -> str:
    """
    Get the current locale for this context.

    Returns:
        Current locale code
    """
    return _current_locale.get()


def is_supported_locale(locale: str) -> bool:
    """
    Check if a locale is supported.

    Args:
        locale: Locale code to check

    Returns:
        True if locale is supported
    """
    return locale in SUPPORTED_LOCALES


def get_supported_locales() -> frozenset:
    """
    Get set of supported locale codes.

    Returns:
        Frozenset of supported locale codes
    """
    return SUPPORTED_LOCALES
