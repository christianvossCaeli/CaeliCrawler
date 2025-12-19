"""Geographic utilities for Smart Query - German state aliases and geographic resolution."""

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
