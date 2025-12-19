"""Country configuration for international location support."""

from dataclasses import dataclass
from typing import Dict, List, Optional
import re


@dataclass
class CountryConfig:
    """Configuration for a supported country."""

    # Basic info
    code: str  # ISO 3166-1 alpha-2
    name: str  # English name
    name_de: str  # German name (for UI)

    # Admin level labels
    admin_level_1_name: str  # English
    admin_level_1_name_de: str  # German
    admin_level_2_name: str  # English
    admin_level_2_name_de: str  # German

    # Official code info
    official_code_name: str  # e.g., "AGS", "GSS Code"
    official_code_pattern: Optional[str]  # Regex for validation

    # Locality types common in this country
    locality_types: List[str]

    # External data sources
    wikidata_type_qid: Optional[str]  # Wikidata QID for municipality type
    wikidata_code_property: Optional[str]  # Property for official code
    nominatim_country_code: str  # For Nominatim API

    def validate_official_code(self, code: str) -> bool:
        """Validate official code format for this country."""
        if not self.official_code_pattern:
            return True
        return bool(re.match(self.official_code_pattern, code))


# Supported countries configuration
COUNTRY_CONFIGS: Dict[str, CountryConfig] = {
    "DE": CountryConfig(
        code="DE",
        name="Germany",
        name_de="Deutschland",
        admin_level_1_name="State",
        admin_level_1_name_de="Bundesland",
        admin_level_2_name="District",
        admin_level_2_name_de="Landkreis",
        official_code_name="AGS",
        official_code_pattern=r"^\d{8}$",
        locality_types=["municipality", "city", "town", "gemeinde"],
        wikidata_type_qid="Q262166",
        wikidata_code_property="P439",
        nominatim_country_code="de",
    ),
    "GB": CountryConfig(
        code="GB",
        name="United Kingdom",
        name_de="Vereinigtes Königreich",
        admin_level_1_name="Country/Region",
        admin_level_1_name_de="Land/Region",
        admin_level_2_name="County/District",
        admin_level_2_name_de="Grafschaft/Bezirk",
        official_code_name="GSS Code",
        official_code_pattern=r"^[EWSN]\d{8}$",
        locality_types=["civil_parish", "town", "city", "district", "borough"],
        wikidata_type_qid="Q15060255",
        wikidata_code_property="P836",
        nominatim_country_code="gb",
    ),
    "AT": CountryConfig(
        code="AT",
        name="Austria",
        name_de="Österreich",
        admin_level_1_name="State",
        admin_level_1_name_de="Bundesland",
        admin_level_2_name="District",
        admin_level_2_name_de="Bezirk",
        official_code_name="Gemeindekennziffer",
        official_code_pattern=r"^\d{5}$",
        locality_types=["municipality", "city", "market_town", "gemeinde"],
        wikidata_type_qid="Q667509",
        wikidata_code_property="P964",
        nominatim_country_code="at",
    ),
    "CH": CountryConfig(
        code="CH",
        name="Switzerland",
        name_de="Schweiz",
        admin_level_1_name="Canton",
        admin_level_1_name_de="Kanton",
        admin_level_2_name="District",
        admin_level_2_name_de="Bezirk",
        official_code_name="BFS-Nr.",
        official_code_pattern=r"^\d{4}$",
        locality_types=["municipality", "city", "gemeinde"],
        wikidata_type_qid="Q70208",
        wikidata_code_property="P771",
        nominatim_country_code="ch",
    ),
    "FR": CountryConfig(
        code="FR",
        name="France",
        name_de="Frankreich",
        admin_level_1_name="Region",
        admin_level_1_name_de="Region",
        admin_level_2_name="Department",
        admin_level_2_name_de="Département",
        official_code_name="Code INSEE",
        official_code_pattern=r"^\d{5}$",
        locality_types=["commune", "city", "town"],
        wikidata_type_qid="Q484170",
        wikidata_code_property="P374",
        nominatim_country_code="fr",
    ),
    "NL": CountryConfig(
        code="NL",
        name="Netherlands",
        name_de="Niederlande",
        admin_level_1_name="Province",
        admin_level_1_name_de="Provinz",
        admin_level_2_name="Municipality",
        admin_level_2_name_de="Gemeinde",
        official_code_name="CBS Code",
        official_code_pattern=r"^\d{4}$",
        locality_types=["municipality", "city", "gemeente"],
        wikidata_type_qid="Q2039348",
        wikidata_code_property="P382",
        nominatim_country_code="nl",
    ),
    "BE": CountryConfig(
        code="BE",
        name="Belgium",
        name_de="Belgien",
        admin_level_1_name="Region",
        admin_level_1_name_de="Region",
        admin_level_2_name="Province",
        admin_level_2_name_de="Provinz",
        official_code_name="NIS Code",
        official_code_pattern=r"^\d{5}$",
        locality_types=["municipality", "city", "gemeente", "commune"],
        wikidata_type_qid="Q493522",
        wikidata_code_property="P1567",
        nominatim_country_code="be",
    ),
}


def get_country_config(code: str) -> CountryConfig:
    """
    Get configuration for a country.

    Args:
        code: ISO 3166-1 alpha-2 country code

    Returns:
        CountryConfig for the country

    Raises:
        ValueError: If country is not supported
    """
    config = COUNTRY_CONFIGS.get(code.upper())
    if not config:
        raise ValueError(f"Unsupported country: {code}")
    return config


def get_supported_countries() -> List[Dict[str, str]]:
    """
    Get list of supported countries.

    Returns:
        List of dicts with code, name, name_de
    """
    return [
        {
            "code": config.code,
            "name": config.name,
            "name_de": config.name_de,
        }
        for config in COUNTRY_CONFIGS.values()
    ]


def is_country_supported(code: str) -> bool:
    """Check if a country is supported."""
    return code.upper() in COUNTRY_CONFIGS
