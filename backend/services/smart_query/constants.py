"""Constants for Smart Query Service.

Centralizes configuration values and lookup tables used across
the smart query module for better maintainability.
"""


# Tag aliases for common geographic regions and source types
# Maps user-friendly terms to all accepted variations
TAG_ALIASES: dict[str, list[str]] = {
    # German Bundeslaender (States)
    "nordrhein-westfalen": ["nrw", "nordrhein-westfalen"],
    "nrw": ["nrw", "nordrhein-westfalen"],
    "bayern": ["bayern", "by"],
    "baden-wuerttemberg": ["baden-wuerttemberg", "bw"],
    "niedersachsen": ["niedersachsen", "ni"],
    "hessen": ["hessen", "he"],
    "sachsen": ["sachsen", "sn"],
    "rheinland-pfalz": ["rheinland-pfalz", "rlp"],
    "berlin": ["berlin", "be"],
    "schleswig-holstein": ["schleswig-holstein", "sh"],
    "brandenburg": ["brandenburg", "bb"],
    "sachsen-anhalt": ["sachsen-anhalt", "st"],
    "thueringen": ["thueringen", "th"],
    "hamburg": ["hamburg", "hh"],
    "mecklenburg-vorpommern": ["mecklenburg-vorpommern", "mv"],
    "saarland": ["saarland", "sl"],
    "bremen": ["bremen", "hb"],

    # Countries
    "deutschland": ["deutschland", "de", "germany"],
    "oesterreich": ["oesterreich", "at", "austria"],
    "schweiz": ["schweiz", "ch", "switzerland"],

    # Source types
    "kommunal": ["kommunal", "gemeinde", "stadt", "kommune"],
    "landkreis": ["landkreis", "kreis"],
}

# Default limits for queries
DEFAULT_SOURCE_LIMIT = 1000
MAX_SOURCE_LIMIT = 10000
DEFAULT_PREVIEW_LIMIT = 10

# Crawl configuration defaults
DEFAULT_MAX_DEPTH = 3
DEFAULT_MAX_PAGES = 100
DEFAULT_DOWNLOAD_EXTENSIONS = ["pdf", "doc", "docx", "xls", "xlsx"]
