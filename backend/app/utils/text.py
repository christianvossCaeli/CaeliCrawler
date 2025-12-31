"""
Text normalization utilities for consistent matching across the application.

This module provides centralized text normalization functions to ensure
consistent behavior when matching entity names, creating slugs, etc.

For entity deduplication, we use embedding-based similarity matching
(see app.utils.similarity) which is entity-type-agnostic and handles
variations like titles, abbreviations, and synonyms automatically.

The functions here are used for:
- Exact name matching (normalize_entity_name)
- URL slug generation (create_slug)
- Full-text search preparation (normalize_for_search)
"""

import re
import unicodedata
from typing import Any

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


def clean_municipality_name(name: str, country: str = "DE") -> str:
    """
    Clean municipality names with minimal, generic rules.

    DEPRECATED: This function is no longer used for entity deduplication.
    We now use embedding-based similarity matching which handles variations
    like "Aberdeen City Council" vs "Aberdeen" automatically without
    entity-type-specific rules.

    Only removes clearly redundant suffixes like parenthetical abbreviations
    and trailing country/state names.

    Args:
        name: The municipality name
        country: ISO 3166-1 alpha-2 country code

    Returns:
        Cleaned name with minimal normalization

    Examples:
        >>> clean_municipality_name("Regionalverband Ruhr (RVR)", "DE")
        'Regionalverband Ruhr'
        >>> clean_municipality_name("Aberdeen City Council", "GB")
        'Aberdeen'
    """
    original = name

    # Universal: Remove parenthetical suffixes like "(RVR)", "(NRW)"
    name = re.sub(r'\s*\([^)]*\)$', '', name)

    if country in GERMAN_SPEAKING_COUNTRIES:
        # Remove trailing country/state names after comma
        name = re.sub(r',\s*(?:Deutschland|Germany)$', '', name, flags=re.IGNORECASE)

    elif country == "GB":
        # Remove common UK institutional suffixes
        uk_suffix_patterns = [
            r'\s+City\s+Council$',
            r'\s+Borough\s+Council$',
            r'\s+District\s+Council$',
            r'\s+County\s+Council$',
            r'\s+Council$',
        ]
        for pattern in uk_suffix_patterns:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)

        # Remove UK prefixes
        uk_prefix_patterns = [
            r'^City\s+of\s+',
            r'^Borough\s+of\s+',
            r'^County\s+of\s+',
            r'^Royal\s+Borough\s+of\s+',
        ]
        for pattern in uk_prefix_patterns:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)

    name = name.strip()
    return name if name else original


# =============================================================================
# Core Name Extraction for Duplicate Detection
# =============================================================================

# Truly generic patterns for extracting core names from ANY entity type.
# Works for: cities, movies, games, magazines, football teams, spaceships, etc.
#
# Philosophy:
# - Only remove STRUCTURAL elements (parentheses, trailing qualifiers)
# - No language or domain-specific assumptions
# - Let embedding-based AI handle semantic similarity
#
# The patterns focus on common naming conventions that appear across domains:
# - "Entity Name (Qualifier)" -> "Entity Name"
# - "Entity Name, Location" -> "Entity Name"
# - "Entity Name: Subtitle" -> "Entity Name"


def extract_core_entity_name(name: str, country: str = "DE") -> str:
    """
    Extract the core name from any entity name by removing structural qualifiers.

    This is a GENERIC function that works for ANY entity type:
    - Cities: "München, Bayern" -> "München"
    - Movies: "Star Wars: Episode IV (1977)" -> "Star Wars: Episode IV"
    - Games: "The Legend of Zelda (Nintendo)" -> "The Legend of Zelda"
    - Teams: "FC Bayern München (Fußball)" -> "FC Bayern München"
    - Companies: "Apple Inc. (NASDAQ: AAPL)" -> "Apple Inc."
    - Regions: "Oberfranken-West (Region 4), Bayern" -> "Oberfranken-West"

    The function removes:
    1. Parenthetical content at the end: "X (Y)" -> "X"
    2. Trailing comma-separated qualifiers: "X, Y" -> "X"
    3. Content after trailing colon with short text: "X: Y" -> "X" (only if Y is short)

    It does NOT remove:
    - Important prefixes that are part of the name (FC, The, etc.)
    - Domain-specific patterns (handled by AI similarity)
    - Anything that might fundamentally change the entity's identity

    Args:
        name: The entity name (any type - city, movie, game, team, etc.)
        country: Ignored - kept for API compatibility

    Returns:
        The core name with structural qualifiers removed

    Examples:
        >>> extract_core_entity_name("Oberfranken-West (Region 4), Bayern")
        'Oberfranken-West'
        >>> extract_core_entity_name("Star Wars: A New Hope (1977)")
        'Star Wars: A New Hope'
        >>> extract_core_entity_name("FC Bayern München (Bundesliga)")
        'FC Bayern München'
        >>> extract_core_entity_name("Apple Inc. (NASDAQ: AAPL)")
        'Apple Inc.'
        >>> extract_core_entity_name("The Witcher 3, Game of the Year Edition")
        'The Witcher 3'
    """
    result = name.strip()
    original = result

    # 1. Remove parenthetical content at the end (most common pattern)
    # Handles: "X (Y)" and "X (Y), Z" patterns
    # E.g., "München (Bayern)" -> "München"
    # E.g., "Region 4 (Oberfranken), Bayern" -> "Region 4"
    result = re.sub(r"\s*\([^)]*\)(?:\s*,\s*[^,]+)?$", "", result)
    result = result.strip()

    # 2. Remove trailing comma-separated qualifier (if what remains is substantial)
    # Handles: "X, Y" where Y looks like a qualifier (capitalized word(s))
    # E.g., "München, Bayern" -> "München"
    # E.g., "The Witcher 3, Game of the Year Edition" -> "The Witcher 3"
    # But preserve: "Hall & Oates" (no comma)
    comma_match = re.match(r"^(.+?),\s*(.+)$", result)
    if comma_match:
        before_comma = comma_match.group(1).strip()
        after_comma = comma_match.group(2).strip()
        # Only strip if:
        # - The part before comma is substantial (>= 3 chars)
        # - The part after comma looks like a qualifier (starts with capital or is short)
        if len(before_comma) >= 3 and (
            after_comma[0].isupper() or len(after_comma) <= 20
        ):
            result = before_comma

    # 3. If we stripped too much (result too short), restore original
    if len(result) < 2:
        result = original

    return result.strip() if result.strip() else name


def normalize_core_entity_name(name: str, country: str = "DE") -> str:
    """
    Extract core name and normalize it for matching.

    Combines extract_core_entity_name with normalize_entity_name to produce
    a canonical form suitable for duplicate detection.

    Args:
        name: The entity name
        country: ISO 3166-1 alpha-2 country code (default: "DE")

    Returns:
        Normalized core name

    Examples:
        >>> normalize_core_entity_name("Markt Erlbach")
        'erlbach'
        >>> normalize_core_entity_name("Region Oberfranken-West")
        'oberfrankenwest'
        >>> normalize_core_entity_name("Oberfranken-West (Region 4), Bayern")
        'oberfrankenwest'
    """
    core = extract_core_entity_name(name, country)
    return normalize_entity_name(core, country)


# Backwards compatibility aliases
def normalize_name(name: str, country: str = "DE") -> str:
    """Alias for normalize_entity_name for backwards compatibility."""
    return normalize_entity_name(name, country)
