"""
Text normalization utilities for consistent matching across the application.

This module provides centralized text normalization functions to ensure
consistent behavior when matching entity names, creating slugs, etc.

IMPORTANT: All entity name normalization should use these functions to avoid
duplicate entries caused by inconsistent normalization (e.g., "Köln" vs "Koln").
"""

import re
import unicodedata
from typing import Any, Optional

# German-speaking countries that use the same umlaut replacements
GERMAN_SPEAKING_COUNTRIES = ("DE", "AT", "CH")

# Umlaut replacements for German-speaking countries
GERMAN_UMLAUT_REPLACEMENTS = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}


def normalize_entity_name(name: str, country: str = "DE") -> str:
    """
    Normalize entity name for database matching.

    This function ensures consistent normalization across all imports and services.
    It converts names to a canonical form that can be used for duplicate detection.

    Process:
    1. Convert to lowercase
    2. Replace country-specific characters (e.g., German umlauts)
    3. Remove diacritical marks (accents)
    4. Remove non-alphanumeric characters

    Args:
        name: The entity name to normalize
        country: ISO 3166-1 alpha-2 country code (default: "DE")

    Returns:
        Normalized name suitable for matching

    Examples:
        >>> normalize_entity_name("Köln")
        'koln'
        >>> normalize_entity_name("München")
        'munchen'
        >>> normalize_entity_name("Sankt Augustin")
        'sanktaugustin'
        >>> normalize_entity_name("London", "GB")
        'london'
    """
    result = name.lower()

    # Country-specific character replacements
    if country in GERMAN_SPEAKING_COUNTRIES:
        # German, Austrian, Swiss - same umlaut replacements
        for old, new in GERMAN_UMLAUT_REPLACEMENTS.items():
            result = result.replace(old, new)
    elif country == "GB":
        # UK-specific normalizations
        result = result.replace("saint ", "st ")
        result = result.replace("-upon-", " upon ")

    # Remove diacritical marks (e.g., é → e, ñ → n)
    result = unicodedata.normalize("NFD", result)
    result = "".join(c for c in result if not unicodedata.combining(c))

    # Remove non-alphanumeric characters
    result = re.sub(r"[^a-z0-9]", "", result)

    return result


def create_slug(name: str, country: str = "DE") -> str:
    """
    Create URL-safe slug from name.

    Args:
        name: The name to convert to slug
        country: ISO 3166-1 alpha-2 country code (default: "DE")

    Returns:
        URL-safe slug

    Examples:
        >>> create_slug("Köln")
        'koeln'
        >>> create_slug("Sankt Augustin")
        'sankt-augustin'
    """
    result = name.lower()

    # Country-specific replacements
    if country in ("DE", "AT", "CH"):
        replacements = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}
        for old, new in replacements.items():
            result = result.replace(old, new)

    # Replace spaces with hyphens
    result = result.replace(" ", "-")

    # Remove diacritical marks
    result = unicodedata.normalize("NFD", result)
    result = "".join(c for c in result if not unicodedata.combining(c))

    # Remove special chars except hyphens
    result = re.sub(r"[^a-z0-9-]", "", result)

    # Remove multiple consecutive hyphens
    result = re.sub(r"-+", "-", result)

    return result.strip("-")


def normalize_for_search(text: str) -> str:
    """
    Normalize text for full-text search.

    Less aggressive than normalize_entity_name, preserves more structure.

    Args:
        text: Text to normalize

    Returns:
        Normalized text for search
    """
    result = text.lower()

    # Remove diacritical marks
    result = unicodedata.normalize("NFD", result)
    result = "".join(c for c in result if not unicodedata.combining(c))

    return result


def build_text_representation(value: Any) -> str:
    """
    Build searchable text representation from a facet value.

    Converts various value types (dict, list, string) into a flat text
    representation suitable for full-text search and display.

    Args:
        value: The facet value (can be str, dict, list, or other)

    Returns:
        Searchable text representation

    Examples:
        >>> build_text_representation("Simple text")
        'Simple text'
        >>> build_text_representation({"name": "John", "role": "Manager"})
        'John Manager'
        >>> build_text_representation(["Tag1", "Tag2"])
        'Tag1 Tag2'
    """
    if isinstance(value, str):
        return value
    elif isinstance(value, dict):
        parts = []
        for v in value.values():
            if isinstance(v, str):
                parts.append(v)
            elif isinstance(v, list):
                parts.extend(str(item) for item in v if item)
            elif v is not None:
                parts.append(str(v))
        return " ".join(parts)
    elif isinstance(value, list):
        return " ".join(str(item) for item in value if item)
    elif value is not None:
        return str(value)
    return ""


# Backwards compatibility aliases
def normalize_name(name: str, country: str = "DE") -> str:
    """Alias for normalize_entity_name for backwards compatibility."""
    return normalize_entity_name(name, country)
