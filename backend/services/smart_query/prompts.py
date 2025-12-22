"""AI Prompts for Smart Query Service.

All prompts are generated dynamically using data from the database.
This ensures the AI always has current information about available
entity types, facet types, relations, and categories.
"""

from typing import Any, Dict, List


def build_dynamic_write_prompt(
    entity_types: List[Dict[str, Any]],
    facet_types: List[Dict[str, Any]],
    relation_types: List[Dict[str, Any]],
    categories: List[Dict[str, Any]],
    query: str,
) -> str:
    """Build the write interpretation prompt dynamically with current database state.

    This replaces the old static WRITE_INTERPRETATION_PROMPT with a dynamic version
    that loads all available types from the database.
    """

    # Build entity types section
    entity_lines = []
    for et in entity_types:
        attrs = ""
        schema = et.get("attribute_schema") or {}
        if isinstance(schema, dict) and schema.get("properties"):
            attr_names = list(schema["properties"].keys())[:5]
            attrs = f" (Attribute: {', '.join(attr_names)})"
        hierarchy = " [hierarchisch]" if et.get("supports_hierarchy") else ""
        entity_lines.append(f"- {et['slug']}: {et.get('description') or et['name']}{hierarchy}{attrs}")
    entity_section = "\n".join(entity_lines) if entity_lines else "- (keine Entity-Typen definiert)"

    # Build facet types section
    facet_lines = []
    for ft in facet_types:
        applicable = ""
        if ft.get("applicable_entity_type_slugs"):
            applicable = f" [für: {', '.join(ft['applicable_entity_type_slugs'])}]"
        facet_lines.append(f"- {ft['slug']}: {ft.get('description') or ft['name']}{applicable}")
    facet_section = "\n".join(facet_lines) if facet_lines else "- (keine Facet-Typen definiert)"

    # Build relation types section
    relation_lines = []
    for rt in relation_types:
        relation_lines.append(f"- {rt['slug']}: {rt.get('description') or rt['name']}")
    relation_section = "\n".join(relation_lines) if relation_lines else "- (keine Relations definiert)"

    # Build categories section
    category_lines = []
    for cat in categories:
        category_lines.append(f"- {cat['slug']}: {cat.get('description') or cat['name']}")
    category_section = "\n".join(category_lines) if category_lines else "- (keine Kategorien definiert)"

    return f"""Du bist ein intelligenter Command-Interpreter für ein Entity-Facet-System.
Analysiere die Benutzeranfrage und entscheide selbstständig, welche Operationen ausgeführt werden sollen.

## Aktuell verfügbare Entity Types:
{entity_section}

## Aktuell verfügbare Facet Types:
{facet_section}

## Aktuell verfügbare Relations:
{relation_section}

## Bestehende Kategorien (Analysethemen):
{category_section}

## Verfügbare Operationen:
- create_entity_type: Neuen Entity-Typ erstellen
- create_entity: Einzelne Entity erstellen
- create_facet: Facet zu Entity hinzufügen
- create_relation: Relation zwischen Entities erstellen
- create_facet_type: Neuen Facet-Typ erstellen
- assign_facet_type: Facet-Typ einem Entity-Typ zuweisen
- add_history_point: Datenpunkt zu History-Facet hinzufügen (für Zeitreihen-Daten)
- fetch_and_create_from_api: Daten aus externen APIs importieren (Wikidata SPARQL, REST APIs)
- create_category_setup: Neue Kategorie mit DataSources erstellen
- start_crawl: Crawls starten (unterstützt Filter nach Entity-Type, Region, Tags)
- combined: Mehrere Operationen kombinieren

## Start Crawl Operation:
Starte Crawls für DataSources mit flexiblen Filtern:
{{
  "operation": "start_crawl",
  "crawl_command_data": {{
    "category_slug": "kommunale-news-windenergie",  // Optional: Kategorie-Filter
    "entity_type": "territorial-entity",            // Optional: Entity-Type
    "admin_level_1": "Bayern",                      // Optional: Region/Bundesland
    "tags": ["kommunal"],                           // Optional: Zusätzliche Tags (AND)
    "entity_filters": {{                            // Optional: Erweiterte Entity-Filter
      "hierarchy_level": 2,                         // 1=Root, 2=Children
      "parent_name": "Bayern",                      // Parent-Entity Name
      "core_attributes": {{                         // Filter auf Entity-Eigenschaften
        "population": {{"lt": 100000}},             // Einwohner < 100.000
        "area_km2": {{"gt": 50}}                    // Fläche > 50 km²
      }}
    }},
    "limit": 100                                    // Max. Anzahl Sources
  }}
}}

Filter-Operatoren für core_attributes: lt, lte, gt, gte, eq

Beispiele:
- "Crawle alle Gemeinden in Bayern" → admin_level_1="Bayern", tags=["kommunal"]
- "Crawle nur NRW Kommunen" → admin_level_1="NRW", tags=["kommunal"]
- "Starte Crawl für alle Windpark-Quellen" → entity_type="windpark"
- "Crawle Gemeinden unter 50.000 Einwohnern" → entity_filters.core_attributes.population={{"lt": 50000}}
- "Crawle große Gemeinden in Hessen" → admin_level_1="Hessen", entity_filters.core_attributes.population={{"gt": 100000}}

## History-Facets (Zeitreihen-Daten):
Für Verläufe wie Aktienkurse, Einwohnerzahlen, Haushaltsdaten:
- Erstelle Facet-Typ mit value_type="history"
- Nutze add_history_point zum Hinzufügen von Datenpunkten:
{{
  "operation": "add_history_point",
  "history_point_data": {{
    "entity_name": "Entity-Name",
    "facet_type": "facet-typ-slug",
    "value": 12345.67,
    "recorded_at": "2024-01-15T00:00:00",
    "track_key": "default",
    "note": "Optional: Notiz zum Datenpunkt"
  }}
}}

## Externe APIs (fetch_and_create_from_api):
- SPARQL: api_config.type="sparql" mit query und country
- REST: api_config.type="rest" mit template für vordefinierte APIs

## KRITISCH - Reihenfolge bei "combined" Operationen:
Bei combined MUSS diese Reihenfolge eingehalten werden:
1. **ERST create_entity_type** - Alle benötigten Entity-Types erstellen
2. **DANN fetch_and_create_from_api** - Daten importieren (erst Bundesländer mit level=1, dann Gemeinden mit level=2)
3. **ZULETZT assign_facet_type** - Facet-Types den Entity-Types zuweisen

## Entity Types:
- Prüfe ZUERST ob ein passender Entity-Type oben gelistet ist
- WENN KEINER EXISTIERT für Gebietskörperschaften → create_entity_type mit supports_hierarchy=true!
- Verschiedene Datenarten (z.B. Orte vs. Projekte vs. Unternehmen) brauchen EIGENE Entity-Types

## Hierarchische Entity-Types [hierarchisch]:
- Unterstützen ALLE Ebenen in EINEM Typ (Land → Bundesland → Gemeinde → Ortsteil)
- NIEMALS separate Entity-Types für verschiedene Hierarchie-Ebenen!
- Hierarchie über parent_id und hierarchy_level (1=oberste Ebene, 2=darunter, etc.)
- Bei Import: Erst Level 1, dann Level 2 mit parent_field

## Facet Types:
Nutze BESTEHENDE - weise sie mit "assign_facet_type" zu (NACH den Entity-Types!)

## Kategorien:
Verknüpfe mit BESTEHENDEN Kategorien über category_slugs in fetch_and_create_from_api

## Hierarchie-Import Beispiel:
Für "Importiere deutsche Gemeinden" bei LEEREM System (kein Entity-Type vorhanden):
1. ZUERST: create_entity_type für "territorial-entity" mit supports_hierarchy=true
2. DANN: fetch_and_create_from_api für Bundesländer mit hierarchy_level=1
3. DANN: fetch_and_create_from_api für Gemeinden mit hierarchy_level=2, parent_field="bundeslandLabel"

Bei BESTEHENDEM hierarchischem Entity-Type [hierarchisch]:
1. Erst Bundesländer importieren mit hierarchy_level=1
2. Dann Gemeinden importieren mit hierarchy_level=2 und parent_field="bundeslandLabel"

## Antwortformat (JSON):
{{
  "operation": "combined|create_entity_type|fetch_and_create_from_api|...",
  "combined_operations": [
    // Bei combined: Array von Operationen in der richtigen Reihenfolge
  ],
  "explanation": "Kurze Erklärung was gemacht wird"
}}

## Für fetch_and_create_from_api:
{{
  "operation": "fetch_and_create_from_api",
  "fetch_and_create_data": {{
    "api_config": {{
      "type": "sparql|rest",
      "query": "gemeinden|bundeslaender|councils (für SPARQL)",
      "template": "<template_name> (für REST - siehe verfügbare Templates)",
      "country": "DE|AT|GB"
    }},
    "entity_type": "slug des Entity-Types",
    "create_entity_type": true,  // true wenn Entity-Type noch nicht existiert
    "entity_type_config": {{     // NUR wenn create_entity_type=true
      "name": "Entity-Type Name",
      "name_plural": "Pluralform",
      "slug": "entity-type-slug",
      "supports_hierarchy": true|false,
      "is_public": true
    }},
    "hierarchy_level": 1|2|...,  // Hierarchie-Ebene (optional)
    "parent_field": "<api_field>",  // API-Feld für Parent-Lookup (optional)
    "match_to_gemeinde": true,  // Cross-Entity-Type Matching aktivieren (optional)
    "category_slugs": ["kategorie-slug"],
    "create_data_sources": true
  }}
}}

## Hierarchischer Import (territorial-entity):
- Oberste Ebene: hierarchy_level=1, kein parent_field (z.B. Bundesländer, Regionen)
- Untergeordnete Ebene: hierarchy_level=2, parent_field="<parentFieldName>" (z.B. Gemeinden → Bundesland)
- Die API-Felder für parent_field variieren je nach Datenquelle

## Cross-Entity-Type Matching:
- Für Entity-Types die zu anderen Typen gehören (z.B. Projekte → Orte)
- Nutze match_to_gemeinde=true oder match_to_parent mit passendem parent_entity_type
- Erstellt automatisch Relation "befindet_sich_in" zur passenden Parent-Entity
- Der Entity-Name wird analysiert um den zugehörigen Ort zu finden

Benutzeranfrage: {query}

Antworte NUR mit validem JSON. Sei kreativ und intelligent bei der Interpretation."""


# =============================================================================
# AI Generation Prompts (used by ai_generation.py for specific tasks)
# These are minimal and task-focused, not prescriptive
# =============================================================================

AI_ENTITY_TYPE_PROMPT = """Generiere eine EntityType-Konfiguration.

Benutzeranfrage: {user_intent}
Geografischer Fokus: {geographic_context}

Erstelle eine passende EntityType-Konfiguration als JSON:
{{
  "name": "Kurzer Name",
  "name_plural": "Pluralform",
  "description": "Beschreibung",
  "icon": "mdi-icon-name",
  "color": "#HexColor",
  "attribute_schema": {{ "type": "object", "properties": {{ ... }} }},
  "search_focus": "event_attendance|pain_points|contacts|general"
}}

Antworte NUR mit validem JSON."""


AI_CATEGORY_PROMPT = """Generiere eine Category-Konfiguration für Web-Crawling.

Benutzeranfrage: {user_intent}
EntityType: {entity_type_name} - {entity_type_description}
Geografischer Kontext: {geographic_context}

Erstelle eine Category-Konfiguration als JSON:
{{
  "purpose": "Kurze Zweckbeschreibung",
  "search_terms": ["Begriff1", "Begriff2", ...],
  "extraction_handler": "event|default",
  "ai_extraction_prompt": "Detaillierter Prompt für KI-Extraktion...",
  "suggested_tags": ["tag1", "tag2"]
}}

Antworte NUR mit validem JSON."""


AI_CRAWL_CONFIG_PROMPT = """Generiere URL-Filter für einen Web-Crawler.

Benutzeranfrage: {user_intent}
Suchfokus: {search_focus}
Search Terms: {search_terms}

Erstelle AUSSCHLIESSLICH Exclude-Patterns (Blacklist) als JSON:
{{
  "url_include_patterns": [],
  "url_exclude_patterns": ["/impressum", "/datenschutz", ...],
  "reasoning": "Begründung"
}}

WICHTIG: url_include_patterns MUSS leer sein!

Antworte NUR mit validem JSON."""


AI_FACET_TYPES_PROMPT = """Generiere FacetType-Vorschläge.

Benutzeranfrage: {user_intent}
EntityType: {entity_type_name} - {entity_type_description}

FacetTypes sind dynamische Beobachtungen die über Zeit gesammelt werden (News, Pain Points, Kontakte, Events).

Generiere 2-4 passende FacetTypes als JSON:
{{
  "facet_types": [
    {{
      "name": "Name",
      "slug": "slug_lowercase",
      "name_plural": "Plural",
      "description": "Beschreibung",
      "value_type": "object",
      "icon": "mdi-icon",
      "color": "#HexColor",
      "is_time_based": true,
      "ai_extraction_prompt": "Prompt für Extraktion..."
    }}
  ],
  "reasoning": "Begründung"
}}

Antworte NUR mit validem JSON."""


AI_SEED_ENTITIES_PROMPT = """Generiere eine Liste bekannter Entities.

Benutzeranfrage: {user_intent}
EntityType: {entity_type_name} - {entity_type_description}
Attribute Schema: {attribute_schema}
Geografischer Kontext: {geographic_context}

Generiere BEKANNTE, REALE Entities als JSON:
{{
  "entities": [
    {{
      "name": "Name",
      "external_id": "Optional ID",
      "core_attributes": {{ ... }},
      "admin_level_1": "Bundesland/Region",
      "country": "DE"
    }}
  ],
  "total_known": 18,
  "is_complete_list": true,
  "reasoning": "Begründung"
}}

Antworte NUR mit validem JSON."""


AI_API_RESPONSE_ANALYSIS_PROMPT = """Analysiere diese API-Antwort und erstelle ein Mapping.

User-Intent: {user_intent}
API-Typ: {api_type}
Ziel Entity-Typ: {target_entity_type}

API-Sample ({sample_size} Einträge):
```json
{api_sample}
```

Erstelle ein JSON mit:
- field_mapping: API-Felder → Entity-Felder
- additional_mappings: Weitere Felder → core_attributes
- parent_config: Hierarchie wenn erkennbar
- entity_type_suggestion: Vorschlag für neuen EntityType

Antworte NUR mit validem JSON."""


# Legacy prompt - deprecated, use build_dynamic_write_prompt() instead
WRITE_INTERPRETATION_PROMPT = """DEPRECATED: Use build_dynamic_write_prompt() instead.
Benutzeranfrage: {query}"""
