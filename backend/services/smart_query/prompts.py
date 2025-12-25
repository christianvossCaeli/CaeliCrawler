"""AI Prompts for Smart Query Service.

All prompts are generated dynamically using data from the database.
This ensures the AI always has current information about available
entity types, facet types, relations, and categories.

Security Note:
All user-provided data embedded in prompts is sanitized to prevent
prompt injection attacks. Use escape_for_json_prompt() for any
user-controlled values.
"""

from typing import Any, Dict, List

from app.utils.security import escape_for_json_prompt, sanitize_for_prompt


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

    Security: The query is sanitized to prevent prompt injection attacks.
    """
    # Sanitize user query to prevent prompt injection
    sanitization_result = sanitize_for_prompt(query, max_length=2000)
    safe_query = escape_for_json_prompt(sanitization_result.sanitized_text)

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

### Schreib-Operationen:
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
- analyze_pysis: PySis-Daten analysieren und Facets daraus erstellen
- enrich_facets_from_pysis: Bestehende Facets mit PySis-Daten anreichern
- push_to_pysis: Facet-Werte zu PySis synchronisieren
- setup_api_facet_sync: Automatische API-zu-Facet Synchronisation einrichten
- trigger_api_sync: API-Sync manuell auslösen
- combined: Mehrere Operationen kombinieren

### Abfrage-Operationen:
- query_data: Interne Entity/Facet-Daten abfragen (mit Visualisierung)
- query_external: Externe API live abfragen (ohne Speicherung)
- query_facet_history: Zeitreihen-Daten eines Facet-Typs abfragen

## Daten-Abfrage Operationen:

### query_data - Interne Daten abfragen:
Wenn der Benutzer nach existierenden Daten fragt (z.B. "zeige mir...", "wie viele...", "liste..."):
{{
  "operation": "query_data",
  "query_config": {{
    "entity_type": "fussballverein",       // Erforderlich
    "facet_types": ["tabellen-punkte"],    // Optional: Welche Facets
    "filters": {{
      "tags": ["bundesliga-1"],            // Optional: Tags
      "admin_level_1": "Bayern"            // Optional: Region
    }},
    "time_range": {{                       // Optional: Für History-Facets
      "latest_only": true                  // Nur neuester Wert
    }},
    "sort_by": "tabellen-punkte",          // Optional: Sortierung
    "sort_order": "desc",
    "limit": 20
  }},
  "visualization_hint": "table",           // Optional: table|bar_chart|line_chart|pie_chart|stat_card
  "user_query": "Zeige die Bundesliga-Tabelle"
}}

### query_external - Live API-Abfrage:
Für Live-Daten von externen APIs (ohne Speicherung):
{{
  "operation": "query_external",
  "query_config": {{
    "prompt": "Aktuelle Bundesliga Tabelle"  // KI findet passende API
    // ODER: "api_url": "https://api.example.com/data"
    // ODER: "api_template_id": "uuid-hier"
  }},
  "user_query": "Zeige mir live die aktuelle Tabelle"
}}

### query_facet_history - Zeitreihen abfragen:
Für Verlaufsdaten über Zeit:
{{
  "operation": "query_facet_history",
  "query_config": {{
    "entity_type": "fussballverein",
    "facet_type": "tabellen-punkte",
    "entity_names": ["FC Bayern München"],  // Optional: Spezifische Entities
    "from_date": "2024-01-01",
    "to_date": "2024-12-31"
  }},
  "visualization_hint": "line_chart"
}}

### Wann welche Operation verwenden:
- "Zeige mir die Tabelle" → query_data (interne Daten)
- "Zeige mir LIVE die Tabelle" → query_external (externe API)
- "Zeige den Punkteverlauf von Bayern" → query_facet_history (Zeitreihe)
- "Sammle wöchentlich die Tabelle" → setup_api_facet_sync (Automatisierung)

## PySis-Operationen:
Für Entities mit PySis-Prozessen können folgende Operationen ausgeführt werden:

### analyze_pysis - PySis-Daten analysieren:
{{
  "operation": "analyze_pysis",
  "pysis_data": {{
    "entity_name": "Gummersbach",  // Name der Entity
    "overwrite_existing": false    // Bestehende Facets überschreiben?
  }}
}}

### enrich_facets_from_pysis - Facets anreichern:
{{
  "operation": "enrich_facets_from_pysis",
  "pysis_data": {{
    "entity_name": "Gummersbach",
    "overwrite_existing": false
  }}
}}

### push_to_pysis - Zu PySis synchronisieren:
{{
  "operation": "push_to_pysis",
  "pysis_data": {{
    "entity_name": "Gummersbach",
    "process_id": "optional-process-uuid"  // Optional: Spezifischer Prozess
  }}
}}

Beispiele für PySis-Befehle:
- "Analysiere PySis-Daten für Gummersbach" → analyze_pysis
- "Reichere Facets von Köln mit PySis an" → enrich_facets_from_pysis
- "Synchronisiere Gummersbach zu PySis" → push_to_pysis
- "Aktualisiere PySis-Daten für alle Gemeinden in NRW" → combined mit mehreren analyze_pysis

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

Benutzeranfrage: {safe_query}

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


# =============================================================================
# Visualization Selection Prompt
# =============================================================================

VISUALIZATION_SELECTOR_PROMPT = """Analysiere die folgenden Daten und wähle das beste Visualisierungsformat.

## Datenübersicht
- Anzahl Datenpunkte: {count}
- Datenfelder: {fields}
- Hat Zeitdimension: {has_time}
- Anzahl Kategorien/Entities: {category_count}
- Numerische Felder: {numeric_fields}
- User-Query: "{user_query}"

## Datensample (erste 3 Einträge):
```json
{data_sample}
```

## Verfügbare Visualisierungstypen:
- "table": Für Ranglisten, Vergleichstabellen (>3 Spalten, sortierbar)
- "bar_chart": Für Kategorievergleiche (2-15 Kategorien, ein Wert pro Kategorie)
- "line_chart": Für Zeitverläufe (hat Zeitdimension, zeigt Entwicklung)
- "pie_chart": Für Anteile/Prozente (2-8 Kategorien, summieren zu 100%)
- "stat_card": Für Einzelwerte oder KPIs (1-4 Werte)
- "text": Für Zusammenfassungen oder wenn Charts nicht sinnvoll
- "comparison": Für 2-3 Entities detailliert vergleichen

## Entscheidungskriterien:
1. Bei Ranglisten (Position, Punkte) → "table"
2. Bei Zeitreihen → "line_chart"
3. Bei Vergleichsfrage mit 2-3 Entities → "comparison"
4. Bei Einzelwert-Frage ("Wie viele...?") → "stat_card"
5. Bei Kategorien mit einem Wert → "bar_chart"
6. Bei Anteilen/Prozenten → "pie_chart"

## Antwortformat (JSON):
{{
  "visualization_type": "table|bar_chart|line_chart|pie_chart|stat_card|text|comparison",
  "reasoning": "Kurze Begründung",
  "title": "Vorgeschlagener Titel",
  "subtitle": "Optional: Untertitel",
  "columns": [  // NUR für table
    {{"key": "feldname", "label": "Anzeigename", "type": "text|number|date"}}
  ],
  "sort_column": "feldname",  // NUR für table
  "sort_order": "asc|desc",   // NUR für table
  "x_axis": {{"key": "...", "label": "...", "type": "category|number|time"}},  // NUR für Charts
  "y_axis": {{"key": "...", "label": "...", "type": "number"}},  // NUR für Charts
  "series": [{{"key": "...", "label": "...", "color": "#..."}}],  // NUR für Charts
  "cards": [{{"label": "...", "value_key": "...", "unit": "..."}}]  // NUR für stat_card
}}

Antworte NUR mit validem JSON."""


def build_compound_query_prompt(
    entity_types: List[Dict[str, Any]],
    facet_types: List[Dict[str, Any]],
    query: str,
) -> str:
    """Build prompt to detect and decompose compound queries (UND-Abfragen).

    This prompt helps the AI identify when a user query contains multiple
    distinct data requests that should be visualized separately.

    Security: The query is sanitized to prevent prompt injection attacks.
    """
    # Sanitize user query to prevent prompt injection
    sanitization_result = sanitize_for_prompt(query, max_length=2000)
    safe_query = escape_for_json_prompt(sanitization_result.sanitized_text)

    # Build entity types section
    entity_lines = [f"- {et['slug']}: {et.get('description') or et['name']}" for et in entity_types]
    entity_section = "\n".join(entity_lines) if entity_lines else "- (keine)"

    # Build facet types section
    facet_lines = [f"- {ft['slug']}: {ft.get('description') or ft['name']}" for ft in facet_types]
    facet_section = "\n".join(facet_lines) if facet_lines else "- (keine)"

    return f"""Analysiere diese Benutzeranfrage und prüfe, ob sie mehrere separate Datenabfragen enthält.

## Benutzeranfrage:
"{safe_query}"

## Verfügbare Entity Types:
{entity_section}

## Verfügbare Facet Types:
{facet_section}

## Aufgabe:
Erkenne ob die Anfrage mehrere UNTERSCHIEDLICHE Datensätze oder Visualisierungen anfordert.

Signale für Compound Queries:
- "UND" / "und" / "sowie" / "zusätzlich" / "außerdem" / "dazu"
- "als auch" / "plus" / "and also"
- Zwei unterschiedliche Datentypen werden genannt (z.B. "Tabelle" und "Verlauf")
- Zwei verschiedene Entity-Typen oder Filterkriterien

NICHT Compound:
- Eine Abfrage mit mehreren Filterkriterien (z.B. "Personen aus NRW und Bayern")
- Eine Abfrage mit mehreren Facet-Typen für dieselben Entities

## Antwortformat (JSON):
{{{{
  "is_compound": true|false,
  "reasoning": "Kurze Begründung",
  "sub_queries": [
    {{{{
      "id": "unique-id-1",
      "description": "Was diese Teil-Abfrage zeigt",
      "query_config": {{{{
        "entity_type": "entity_slug",
        "facet_types": ["facet_slug"],
        "filters": {{{{}}}},
        "sort_by": "optional",
        "sort_order": "asc|desc",
        "limit": 10
      }}}},
      "visualization_hint": "table|bar_chart|line_chart|pie_chart|stat_card|map|comparison|null"
    }}}}
  ]
}}}}

Wenn is_compound=false, gib sub_queries als leeres Array zurück.
Wenn is_compound=true, zerlege die Anfrage in 2-4 separate sub_queries.

Antworte NUR mit validem JSON."""


def build_plan_mode_prompt(
    entity_types: List[Dict[str, Any]],
    facet_types: List[Dict[str, Any]],
    relation_types: List[Dict[str, Any]],
    categories: List[Dict[str, Any]],
) -> str:
    """Build the Plan Mode system prompt.

    The Plan Mode is an interactive assistant that helps users formulate
    the correct prompts for Smart Query. It knows:
    1. The code/implementation (static documentation)
    2. The database contents (dynamic from DB)

    Args:
        entity_types: List of entity types from database
        facet_types: List of facet types with applicable_entity_type_slugs
        relation_types: List of relation types
        categories: List of categories

    Returns:
        System prompt for Claude Opus
    """
    # Build entity types section
    entity_lines = []
    for et in entity_types:
        desc = et.get("description") or et["name"]
        hierarchy = " [hierarchisch]" if et.get("supports_hierarchy") else ""
        entity_lines.append(f"• {et['slug']}: {desc}{hierarchy}")
    entity_section = "\n".join(entity_lines) if entity_lines else "• (keine Entity-Typen definiert)"

    # Build facet types section with applicability info
    facet_lines = []
    for ft in facet_types:
        desc = ft.get("description") or ft["name"]
        applicable = ft.get("applicable_entity_type_slugs") or []
        applicable_info = f" [für: {', '.join(applicable)}]" if applicable else " [für alle Entity-Typen]"
        facet_lines.append(f"• {ft['slug']}: {desc}{applicable_info}")
    facet_section = "\n".join(facet_lines) if facet_lines else "• (keine Facet-Typen definiert)"

    # Build relation types section
    relation_lines = []
    for rt in relation_types:
        desc = rt.get("description") or rt["name"]
        relation_lines.append(f"• {rt['slug']}: {desc}")
    relation_section = "\n".join(relation_lines) if relation_lines else "• (keine Relations definiert)"

    # Build categories section
    category_lines = []
    for cat in categories:
        desc = cat.get("description") or cat["name"]
        category_lines.append(f"• {cat['slug']}: {desc}")
    category_section = "\n".join(category_lines) if category_lines else "• (keine Kategorien definiert)"

    return f"""Du bist ein freundlicher, interaktiver Assistent der Benutzern hilft, die richtigen Prompts
für Smart Query zu formulieren. Du kennst das System in- und auswendig und kannst erklären,
wie man es optimal nutzt.

## TEIL 1: System-Dokumentation (Was das System kann)

### Lese-Modus (Read Mode) - Daten abfragen

Im Lese-Modus kann man Daten suchen, filtern und anzeigen lassen. Hier sind die Möglichkeiten:

**Query-Types:**
• "list" - Eine Liste von Ergebnissen (Standard)
• "count" - Nur die Anzahl zählen ("Wie viele...")
• "aggregate" - Statistische Berechnungen (Durchschnitt, Summe, etc.)

**Filter-Möglichkeiten:**
• Nach Entity-Typ filtern (Personen, Gemeinden, Veranstaltungen, etc.)
• Nach Region filtern (Bundesland, Land)
• Nach Facet-Typ filtern (Problemfelder, Kontakte, etc.)
• Nach Zeit filtern (zukünftig, vergangen, Zeitraum)
• Nach Position filtern (Bürgermeister, Landrat, etc.)

**Verknüpfungen (Multi-Hop):**
Das System kann mehrere Beziehungen verfolgen, z.B.:
• "Personen deren Gemeinden Problemfelder haben" (Person → works_for → Gemeinde → hat pain_point)
• "Veranstaltungen an denen Bürgermeister teilnehmen" (Event ← attends ← Person mit Position)
• "Gemeinden deren Mitarbeiter Events besucht haben"

**Beispiel-Prompts für Lese-Modus:**
• "Zeige mir alle Gemeinden in NRW mit Problemfeldern"
• "Wie viele Personen haben wir in Bayern?"
• "Welche Veranstaltungen finden in den nächsten 30 Tagen statt?"
• "Zeige Bürgermeister deren Gemeinden Problemfelder zum Thema Windkraft haben"

### Schreib-Modus (Write Mode) - Daten anlegen

Im Schreib-Modus kann man neue Daten erstellen oder bestehende ändern:

**Verfügbare Operationen:**
• create_entity: Neue Entity erstellen (Person, Gemeinde, etc.)
• create_facet: Facet zu Entity hinzufügen (Problemfeld, Kontakt, etc.)
• create_relation: Verknüpfung zwischen Entities erstellen
• start_crawl: Datensammlung starten
• fetch_and_create_from_api: Daten aus externen APIs importieren
• combined: Mehrere Operationen nacheinander ausführen

**Beispiel-Prompts für Schreib-Modus:**
• "Erstelle eine Person Max Müller, Bürgermeister von Gummersbach"
• "Füge ein Problemfeld für Attendorn hinzu: Personalmangel in der IT"
• "Starte Datensammlung für alle Gemeinden in NRW"

### Visualisierungen

Das System wählt automatisch die passende Darstellung:
• table: Für Listen und Ranglisten (Standard)
• bar_chart: Für Kategorievergleiche (2-15 Kategorien)
• line_chart: Für Zeitverläufe
• pie_chart: Für Anteile/Prozente
• stat_card: Für Einzelwerte ("Wie viele?")
• map: Für geografische Daten
• comparison: Für direkten Vergleich von 2-3 Entities

## TEIL 2: Verfügbare Daten in diesem System

### Entity-Typen (Was gibt es für Datentypen):
{entity_section}

### Facet-Typen (Welche Eigenschaften kann man erfassen):
{facet_section}

### Beziehungstypen (Wie hängen Dinge zusammen):
{relation_section}

### Kategorien/Analysethemen:
{category_section}

## TEIL 3: Deine Aufgabe

Du sollst dem Benutzer interaktiv helfen, den richtigen Prompt zu formulieren:

1. **Verstehe die Absicht**: Was möchte der Benutzer erreichen?

2. **Prüfe die Machbarkeit**: Existieren die gewünschten Types im System?
   - Wenn ja, bestätige das kurz
   - Wenn nein, erkläre was stattdessen möglich ist

3. **Stelle Rückfragen**: Wenn Details fehlen, frage gezielt nach:
   - Welche Region? (wenn nicht angegeben)
   - Welcher Zeitraum? (bei Events/zeitbasierten Daten)
   - Welche zusätzlichen Informationen? (Ansprechpartner, Details, etc.)

4. **Generiere den Prompt**: Wenn du genug Informationen hast:
   - Formuliere einen fertigen, natürlichsprachigen Prompt
   - Erkläre kurz warum dieser Prompt funktioniert
   - Gib an ob es ein Lese- oder Schreib-Prompt ist

## Antwortformat

Antworte IMMER in natürlicher Sprache, freundlich und hilfsbereit.
Verwende Aufzählungen mit • für Übersichtlichkeit.
Erkläre technische Details einfach und verständlich.

Wenn du einen fertigen Prompt hast, formatiere ihn so:

**Fertiger Prompt:**
> [Der Prompt hier]

**Modus:** Lese-Modus / Schreib-Modus

**So funktioniert's:**
• [Erklärung Punkt 1]
• [Erklärung Punkt 2]

Wenn du noch Rückfragen hast, stelle diese am Ende deiner Antwort
und biete Vorschläge als Optionen an.

## TEIL 4: Zusammenfassungen (Custom Summaries)

Wenn der Benutzer eine WIEDERKEHRENDE Analyse wünscht, schlage vor, diese als
automatisch aktualisierte Zusammenfassung zu speichern.

**Erkenne Signalwörter für wiederkehrende Analysen:**
• "regelmäßig", "täglich", "wöchentlich", "monatlich"
• "automatisch aktualisieren", "immer aktuell"
• "Dashboard", "Übersicht", "Zusammenfassung"
• "als Startseite", "immer sehen", "beobachten"
• "verfolgen", "tracken", "monitoring"

**Wenn erkannt, füge hinzu:**

[SUMMARY_SUGGESTION]
Möchten Sie diese Abfrage als automatisch aktualisierte Zusammenfassung speichern?
Das System kann:
• Die Daten täglich/wöchentlich automatisch aktualisieren
• Sie bei relevanten Änderungen benachrichtigen
• Die Ergebnisse als Dashboard mit mehreren Widgets anzeigen

Um fortzufahren, klicken Sie auf "Als Zusammenfassung speichern" oder formulieren Sie:
> "Speichere als Zusammenfassung: [Name]"
[/SUMMARY_SUGGESTION]

**Beispiele für Summary-Vorschläge:**
• "Zeige mir täglich die Bundesliga-Tabelle" → Vorschlag: Zusammenfassung
• "Ich möchte NRW Gemeinden mit Problemen beobachten" → Vorschlag: Zusammenfassung
• "Erstelle ein Dashboard mit Windpark-Statistiken" → Vorschlag: Zusammenfassung"""
