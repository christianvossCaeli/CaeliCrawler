"""Geographic utilities for Smart Query - German state aliases and geographic resolution."""

from typing import Optional, Tuple, List


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate the Levenshtein distance between two strings.

    The Levenshtein distance is the minimum number of single-character edits
    (insertions, deletions, substitutions) required to transform one string into another.

    Args:
        s1: First string
        s2: Second string

    Returns:
        The edit distance between the two strings
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # j+1 instead of j since previous_row and current_row are one character longer
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


# Geographic alias mapping for German Bundesländer
GERMAN_STATE_ALIASES = {
    # Nordrhein-Westfalen
    "nrw": "Nordrhein-Westfalen",
    "nordrhein westfalen": "Nordrhein-Westfalen",
    "nordrhein-westfalen": "Nordrhein-Westfalen",
    # Bayern
    "by": "Bayern",
    "bayern": "Bayern",
    "freistaat bayern": "Bayern",
    # Baden-Württemberg
    "bw": "Baden-Württemberg",
    "baden württemberg": "Baden-Württemberg",
    "baden-württemberg": "Baden-Württemberg",
    # Niedersachsen
    "nds": "Niedersachsen",
    "niedersachsen": "Niedersachsen",
    # Hessen
    "he": "Hessen",
    "hessen": "Hessen",
    # Rheinland-Pfalz
    "rp": "Rheinland-Pfalz",
    "rheinland pfalz": "Rheinland-Pfalz",
    "rheinland-pfalz": "Rheinland-Pfalz",
    # Schleswig-Holstein
    "sh": "Schleswig-Holstein",
    "schleswig holstein": "Schleswig-Holstein",
    "schleswig-holstein": "Schleswig-Holstein",
    # Saarland
    "sl": "Saarland",
    "saarland": "Saarland",
    # Berlin
    "be": "Berlin",
    "berlin": "Berlin",
    # Brandenburg
    "bb": "Brandenburg",
    "brandenburg": "Brandenburg",
    # Mecklenburg-Vorpommern
    "mv": "Mecklenburg-Vorpommern",
    "meck pomm": "Mecklenburg-Vorpommern",
    "mecklenburg vorpommern": "Mecklenburg-Vorpommern",
    "mecklenburg-vorpommern": "Mecklenburg-Vorpommern",
    # Sachsen
    "sn": "Sachsen",
    "sachsen": "Sachsen",
    # Sachsen-Anhalt
    "st": "Sachsen-Anhalt",
    "sachsen anhalt": "Sachsen-Anhalt",
    "sachsen-anhalt": "Sachsen-Anhalt",
    # Thüringen
    "th": "Thüringen",
    "thüringen": "Thüringen",
    # Hamburg
    "hh": "Hamburg",
    "hamburg": "Hamburg",
    # Bremen
    "hb": "Bremen",
    "bremen": "Bremen",
}


def resolve_geographic_alias(alias: str) -> str:
    """Resolve a geographic alias to its canonical name (e.g., NRW -> Nordrhein-Westfalen)."""
    if not alias:
        return alias
    normalized = alias.lower().strip()
    return GERMAN_STATE_ALIASES.get(normalized, alias)


# Default threshold for fuzzy matching (max Levenshtein distance)
DEFAULT_FUZZY_THRESHOLD = 2


def suggest_geo_correction(
    input_text: str,
    threshold: int = DEFAULT_FUZZY_THRESHOLD
) -> Optional[Tuple[str, str, int]]:
    """
    Suggest a correction for a potentially misspelled geographic term.

    Uses fuzzy matching (Levenshtein distance) to find the closest matching
    German state alias.

    Args:
        input_text: The user input to check for corrections
        threshold: Maximum edit distance to consider a match (default: 2)

    Returns:
        Tuple of (suggested_alias, canonical_name, distance) if a close match is found,
        None otherwise.

    Example:
        >>> suggest_geo_correction("NWR")
        ("nrw", "Nordrhein-Westfalen", 1)
        >>> suggest_geo_correction("Bayren")
        ("bayern", "Bayern", 1)
        >>> suggest_geo_correction("xyz")
        None
    """
    if not input_text:
        return None

    normalized = input_text.lower().strip()

    # First check for exact match
    if normalized in GERMAN_STATE_ALIASES:
        return None  # No correction needed

    best_match: Optional[Tuple[str, str, int]] = None
    min_distance = threshold + 1

    for alias, canonical in GERMAN_STATE_ALIASES.items():
        distance = levenshtein_distance(normalized, alias)
        if distance <= threshold and distance < min_distance:
            min_distance = distance
            best_match = (alias, canonical, distance)

    return best_match


def find_all_geo_suggestions(
    input_text: str,
    threshold: int = DEFAULT_FUZZY_THRESHOLD,
    max_suggestions: int = 3
) -> List[Tuple[str, str, int]]:
    """
    Find all geographic suggestions within the threshold distance.

    Args:
        input_text: The user input to check
        threshold: Maximum edit distance to consider
        max_suggestions: Maximum number of suggestions to return

    Returns:
        List of tuples (alias, canonical_name, distance), sorted by distance
    """
    if not input_text:
        return []

    normalized = input_text.lower().strip()

    # Check for exact match
    if normalized in GERMAN_STATE_ALIASES:
        return []

    suggestions = []
    for alias, canonical in GERMAN_STATE_ALIASES.items():
        distance = levenshtein_distance(normalized, alias)
        if distance <= threshold:
            suggestions.append((alias, canonical, distance))

    # Sort by distance, then by alias length (prefer shorter)
    suggestions.sort(key=lambda x: (x[2], len(x[0])))

    return suggestions[:max_suggestions]


def resolve_with_suggestion(
    input_text: str,
    threshold: int = DEFAULT_FUZZY_THRESHOLD
) -> Tuple[str, Optional[str]]:
    """
    Resolve a geographic input with optional suggestion for typos.

    Args:
        input_text: User input to resolve
        threshold: Maximum edit distance for suggestions

    Returns:
        Tuple of (resolved_value, suggestion_message)
        - resolved_value: The canonical name if exact match, or original input
        - suggestion_message: "Meinten Sie 'X' (Y)?" if typo detected, None otherwise
    """
    if not input_text:
        return input_text, None

    normalized = input_text.lower().strip()

    # Check for exact match
    if normalized in GERMAN_STATE_ALIASES:
        return GERMAN_STATE_ALIASES[normalized], None

    # Try to find a suggestion
    suggestion = suggest_geo_correction(input_text, threshold)
    if suggestion:
        alias, canonical, _ = suggestion
        return input_text, f"Meinten Sie '{alias.upper()}' ({canonical})?"

    return input_text, None


# Term expansion mappings for search term expansion
TERM_EXPANSIONS = {
    "entscheider": [
        "Bürgermeister",
        "Oberbürgermeister",
        "Landrat",
        "Landrätin",
        "Dezernent",
        "Dezernentin",
        "Amtsleiter",
        "Amtsleiterin",
        "Kämmerer",
        "Kämmerin",
        "Gemeinderat",
        "Stadtrat",
        "Kreisrat",
        "Fraktionsvorsitzender",
        "Verwaltungsleiter",
    ],
    "politiker": [
        "Bürgermeister",
        "Oberbürgermeister",
        "Landrat",
        "Landrätin",
        "Abgeordneter",
        "Abgeordnete",
        "Minister",
        "Ministerin",
        "Staatssekretär",
        "Fraktionsvorsitzender",
    ],
    "veranstaltung": [
        "Event",
        "Konferenz",
        "Kongress",
        "Tagung",
        "Messe",
        "Seminar",
        "Workshop",
        "Symposium",
        "Forum",
        "Gipfel",
    ],
    "event": [
        "Veranstaltung",
        "Konferenz",
        "Kongress",
        "Tagung",
        "Messe",
        "Seminar",
        "Workshop",
    ],
    "gemeinde": [
        "Gemeinde",
        "Stadt",
        "Kommune",
        "Landkreis",
        "Kreis",
    ],
}


def expand_search_terms(search_focus: str, raw_terms: list[str]) -> list[str]:
    """
    Expand abstract search terms into concrete terms.

    E.g., "Entscheider" -> "Bürgermeister", "Landrat", "Oberbürgermeister", etc.
    """
    expanded = []
    for term in raw_terms:
        term_lower = term.lower()
        if term_lower in TERM_EXPANSIONS:
            # Add the expanded terms
            expanded.extend(TERM_EXPANSIONS[term_lower])
        else:
            # Keep the original term
            expanded.append(term)

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for t in expanded:
        if t.lower() not in seen:
            seen.add(t.lower())
            unique.append(t)

    return unique
