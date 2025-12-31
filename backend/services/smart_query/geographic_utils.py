"""Geographic utilities for Smart Query - Wrapper around generic alias_utils.

This module provides backward-compatible wrappers for geographic-specific
alias resolution and term expansion. All actual logic is in alias_utils.py.
"""

# Re-export everything from alias_utils for backward compatibility
from .alias_utils import (
    DEFAULT_FUZZY_THRESHOLD,
    expand_search_terms,
    # Term expansion backward compatibility
    expand_search_terms_async,
    expand_terms,
    expand_terms_async,
    find_all_geo_suggestions,
    find_all_geo_suggestions_async,
    find_all_suggestions_async,
    get_known_regions_from_db,
    get_known_values_from_db,
    # Core generic functions
    levenshtein_distance,
    resolve_alias,
    resolve_alias_async,
    resolve_geographic_alias,
    # Geographic-specific backward compatibility aliases
    resolve_geographic_alias_async,
    resolve_with_suggestion,
    resolve_with_suggestion_async,
    suggest_correction,
    suggest_correction_async,
    suggest_geo_correction,
    suggest_geo_correction_async,
)

__all__ = [
    # Core generic functions
    "levenshtein_distance",
    "resolve_alias_async",
    "resolve_alias",
    "suggest_correction_async",
    "suggest_correction",
    "find_all_suggestions_async",
    "resolve_with_suggestion_async",
    "resolve_with_suggestion",
    "expand_terms_async",
    "expand_terms",
    "get_known_values_from_db",
    "DEFAULT_FUZZY_THRESHOLD",
    # Geographic-specific backward compatibility
    "resolve_geographic_alias_async",
    "resolve_geographic_alias",
    "get_known_regions_from_db",
    "suggest_geo_correction_async",
    "suggest_geo_correction",
    "find_all_geo_suggestions_async",
    "find_all_geo_suggestions",
    # Term expansion
    "expand_search_terms_async",
    "expand_search_terms",
]
