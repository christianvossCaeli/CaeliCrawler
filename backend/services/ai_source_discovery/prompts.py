"""LLM Prompts for AI Source Discovery Service."""

AI_SEARCH_STRATEGY_PROMPT = """Du bist ein Experte für Datenquellen-Recherche. Analysiere die folgende Anfrage
und erstelle eine Suchstrategie.

ANFRAGE: {prompt}

Erstelle eine JSON-Antwort mit:
1. search_queries: 3-5 Suchbegriffe für Web-Suche (verschiedene Formulierungen, auf Deutsch und Englisch)
2. expected_data_type: Art der Daten (z.B. "sports_teams", "municipalities", "companies", "organizations", "institutions")
3. preferred_sources: Priorisierte Quelltypen ["official_api", "wikipedia", "open_data", "government", "industry"]
4. entity_schema: Erwartete Felder pro Entität {{"name": "string", "website": "url", ...}}
5. base_tags: Basis-Tags die auf alle gefundenen Quellen angewendet werden sollten (lowercase, ohne Leerzeichen)
6. expected_entity_count: WICHTIG! Schätze die Anzahl der erwarteten Entitäten basierend auf deinem Wissen:
   - "Bundesliga-Vereine" → 18 (1. Liga) oder 36 (1. + 2. Liga)
   - "DAX Unternehmen" → 40
   - "Gemeinden in NRW" → ca. 400
   - "Ministerien in Deutschland" → ca. 15
   - "Playstation Neuerscheinungen" → ca. 50 pro Jahr
   - Bei unbekannter Größe: schätze realistisch basierend auf dem Thema
7. recommended_max_sources: Empfohlene maximale Quellenanzahl
   - Für geschlossene Listen (Bundesliga, DAX): ca. 1.5x expected_entity_count
   - Für offene Themen (News, Stellenangebote): 15-30 qualitative Quellen
   - KEINE 100+ Quellen wenn nur 20 Entitäten erwartet werden!
8. reasoning: Kurze Begründung für die Quellenanzahl

Antwort NUR als valides JSON ohne Erklärung:

{{
  "search_queries": ["...", "...", "..."],
  "expected_data_type": "...",
  "preferred_sources": ["...", "..."],
  "entity_schema": {{"name": "string", "website": "url"}},
  "base_tags": ["...", "..."],
  "expected_entity_count": 18,
  "recommended_max_sources": 25,
  "reasoning": "18 Bundesliga-Vereine, je ~1.5 Quellen pro Verein für offizielle Websites und Backup-Quellen"
}}"""


AI_EXTRACTION_PROMPT = """Extrahiere strukturierte Daten aus dem folgenden Webseiten-Inhalt.

ERWARTETE DATENSTRUKTUR:
{entity_schema}

WEBSEITEN-INHALT:
{content}

Extrahiere alle gefundenen Entitäten als JSON-Array. Jede Entität muss mindestens "name" und "website" haben.

Antwort NUR als valides JSON-Array ohne Erklärung:
[
  {{"name": "...", "website": "https://..."}},
  ...
]

Regeln:
- Nur Einträge mit gültiger Website-URL zurückgeben
- Name muss aussagekräftig sein
- URLs müssen vollständig sein (mit https://)
- Bei Unsicherheit: Eintrag weglassen
- Maximal 100 Einträge"""


AI_TAG_GENERATION_PROMPT = """Generiere passende Tags für die folgenden Datenquellen.

URSPRÜNGLICHE ANFRAGE: {prompt}
BASIS-TAGS (bereits gesetzt): {base_tags}

DATENQUELLEN:
{sources}

Für jede Quelle, generiere 2-4 ZUSÄTZLICHE spezifische Tags:
- Geografisch: Land, Region, Stadt (z.B. de, bayern, münchen)
- Thematisch: Branche, Kategorie (z.B. sport, energie, bildung)
- Organisationstyp: verein, firma, behörde, gemeinde

Antwort NUR als valides JSON ohne Erklärung:
{{
  "source_tags": {{
    "Name der Quelle 1": ["tag1", "tag2"],
    "Name der Quelle 2": ["tag1", "tag2"],
    ...
  }}
}}

WICHTIG: Nur kurze, lowercase Tags ohne Leerzeichen! Keine Duplikate mit basis_tags."""


AI_CATEGORY_SUGGESTION_PROMPT = """Analysiere die gefundenen Datenquellen und schlage passende Kategorien vor.

URSPRÜNGLICHE ANFRAGE: {prompt}
GEFUNDENE QUELLEN ({source_count} Stück):
{sources_summary}

BESTEHENDE KATEGORIEN:
{existing_categories}

Schlage vor:
1. Welche bestehenden Kategorien zu den Quellen passen
2. Ob eine neue Kategorie erstellt werden sollte

Antwort NUR als valides JSON:
{{
  "existing_matches": [
    {{"category_name": "...", "matching_count": 5, "confidence": 0.8}}
  ],
  "new_category": {{
    "name": "...",
    "slug": "...",
    "purpose": "...",
    "confidence": 0.9
  }}
}}

Falls keine neue Kategorie nötig: "new_category": null"""


AI_API_SUGGESTION_PROMPT = """Du bist ein Experte für öffentliche APIs und Open Data.
Analysiere die folgende Anfrage und schlage passende APIs vor, die diese Daten liefern könnten.

ANFRAGE: {prompt}

Deine Aufgabe:
1. Überlege, welche öffentlichen APIs (REST, GraphQL, SPARQL) die gewünschten Daten bereitstellen könnten
2. Berücksichtige besonders: Deutsche/EU APIs, Open Data Portale, Wikipedia/Wikidata, offizielle Institutionen
3. Gib konkrete Endpoints an, wenn du sie kennst

Antwort NUR als valides JSON-Array ohne Erklärung:
[
  {{
    "api_name": "Name der API (z.B. OpenLigaDB)",
    "base_url": "https://...",
    "endpoint": "/pfad/zum/endpoint",
    "description": "Kurze Beschreibung was die API liefert",
    "api_type": "REST|GRAPHQL|SPARQL|OPARL",
    "auth_required": false,
    "confidence": 0.9,
    "expected_fields": ["name", "website", "..."],
    "documentation_url": "https://... (falls bekannt, sonst null)"
  }},
  ...
]

WICHTIGE REGELN:
- Nur APIs vorschlagen, die du WIRKLICH kennst und die existieren
- Lieber weniger, aber korrekte Vorschläge
- confidence: 0.9+ nur wenn du den Endpoint sicher kennst
- Bei Unsicherheit über den genauen Endpoint: confidence < 0.7
- Maximal 5 Vorschläge
- Wenn keine passende API bekannt: leeres Array []

BEKANNTE DEUTSCHE APIs (als Referenz):
- OpenLigaDB: Fußball-Ligen (api.openligadb.de)
- Wikidata: Alle strukturierten Daten (query.wikidata.org/sparql)
- GovData: Behördendaten (govdata.de)
- OParl: Ratsinformationssysteme (oparl.org)
- Destatis: Statistisches Bundesamt
- Overpass: OpenStreetMap-Daten
- DWD: Wetterdaten"""


AI_FIELD_MAPPING_PROMPT = """Analysiere die API-Response und erstelle ein Field-Mapping.

API-RESPONSE (Beispiel):
{sample_response}

GEWÜNSCHTE FELDER:
- name: Der Hauptname/Titel der Entität
- base_url: Die Website/URL der Entität
- external_id: Eine eindeutige ID (falls vorhanden)

Finde die passenden Felder in der Response und erstelle ein Mapping.

Antwort NUR als valides JSON:
{{
  "field_mapping": {{
    "quellfeld_in_api": "zielfeld",
    "z.B. teamName": "name",
    "z.B. website": "base_url"
  }},
  "data_path": "pfad.zu.array (z.B. 'data.items' oder '' für Root-Array)",
  "total_items": 123
}}"""
