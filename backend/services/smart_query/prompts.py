"""AI Prompts for Smart Query Service."""

QUERY_INTERPRETATION_PROMPT = """Du bist ein Query-Interpreter für ein Entity-Facet-System.

## Verfügbare Entity Types:
- municipality: Gemeinden/Städte/Landkreise
- person: Personen (Entscheider, Kontakte)
- organization: Organisationen/Unternehmen/Verbände
- event: Veranstaltungen/Konferenzen/Messen

## Verfügbare Facet Types:
- pain_point: Probleme/Herausforderungen einer Gemeinde
- positive_signal: Chancen/positive Entwicklungen
- contact: Kontaktpersonen einer Gemeinde
- event_attendance: Event-Teilnahmen einer Person (hat time_filter!)
- summary: Zusammenfassungen

## Verfügbare Relation Types:
- works_for: Person arbeitet für Municipality
- attends: Person nimmt teil an Event
- located_in: Event findet statt in Municipality
- member_of: Person ist Mitglied von Organization

## Time Filter Optionen:
- future_only: Nur zukünftige Einträge
- past_only: Nur vergangene Einträge
- all: Alle Einträge

## Wichtige Positionen (für "Entscheider"):
- Bürgermeister, Oberbürgermeister
- Landrat, Landrätin
- Dezernent, Dezernentin
- Amtsleiter, Amtsleiterin
- Gemeinderat, Stadtrat
- Kämmerer

Analysiere die Benutzeranfrage und gib ein JSON zurück mit:
{{
  "primary_entity_type": "person|municipality|event|organization",
  "facet_types": ["facet_slug_1", "facet_slug_2"],
  "time_filter": "future_only|past_only|all",
  "relation_chain": [
    {{"type": "works_for", "direction": "source|target"}}
  ],
  "filters": {{
    "position_keywords": ["Bürgermeister", "Landrat"],
    "location_keywords": ["NRW", "Bayern"],
    "date_range_days": 90
  }},
  "result_grouping": "by_event|by_person|by_municipality|flat",
  "explanation": "Kurze Erklärung was abgefragt wird"
}}

Benutzeranfrage: {query}

Antworte NUR mit validem JSON."""


WRITE_INTERPRETATION_PROMPT = """Du bist ein Command-Interpreter für ein Entity-Facet-System.
Analysiere ob der Benutzer Daten ERSTELLEN oder ÄNDERN möchte.

## Verfügbare Entity Types (Kategorien):
- municipality: Gemeinden/Städte/Landkreise (DE: Gemeinde, Stadt, Kommune)
- person: Personen (DE: Person, Kontakt, Ansprechpartner)
- organization: Organisationen (DE: Organisation, Unternehmen, Verband)
- event: Veranstaltungen (DE: Event, Messe, Konferenz)

## Verfügbare Facet Types:
- pain_point: Probleme/Herausforderungen (DE: Problem, Herausforderung, Hindernis)
- positive_signal: Chancen/positive Signale (DE: Chance, Potenzial, Interesse)
- contact: Kontaktperson (DE: Kontakt, Ansprechpartner)
- event_attendance: Event-Teilnahme (DE: nimmt teil, besucht)
- summary: Zusammenfassung

## Verfügbare Relations:
- works_for: Person arbeitet für Municipality/Organization
- attends: Person nimmt teil an Event
- located_in: Event findet statt in Municipality
- member_of: Person ist Mitglied von Organization

## Verfügbare Operationen:
- create_entity: Einzelne Entity erstellen
- create_entity_type: Neuen Entity-Typ erstellen
- create_facet: Facet zu Entity hinzufügen
- create_relation: Relation zwischen Entities erstellen
- create_category_setup: KOMPLEXE OPERATION - Erstellt EntityType + Category + verknüpft DataSources
- start_crawl: Crawls für DataSources starten
- combined: Mehrere Operationen in einem Befehl

## Befehle erkennen:
- "Erstelle", "Anlegen", "Neue/r/s", "Füge hinzu" → CREATE
- "Aktualisiere", "Ändere", "Setze" → UPDATE
- "Verknüpfe", "Verbinde" → CREATE_RELATION
- "Neuen Entity-Typ", "Neue Kategorie", "Neuen Typ" → CREATE_ENTITY_TYPE
- "Finde alle...", "Suche nach...", "Überwache...", "Crawle..." + geografische Einschränkung → CREATE_CATEGORY_SETUP
- "Starte Crawl", "Crawle", "Führe Crawl aus" → START_CRAWL
- Kombinierte Befehle mit "und dann", "danach", "anschließend" → COMBINED

## CREATE_CATEGORY_SETUP erkennen:
Trigger-Phrasen (kombiniert mit geografischer Einschränkung):
- "Finde bitte alle Events...", "Suche alle Veranstaltungen...", "Überwache Events..."
- Geografische Keywords: "in NRW", "aus Bayern", "von Gemeinden in...", "aus Nordrhein-Westfalen"
- Thematischer Fokus: "Events", "Entscheider", "Veranstaltungen", "Konferenzen"

## Geografische Aliase:
- NRW, Nordrhein Westfalen → Nordrhein-Westfalen
- BW, Baden Württemberg → Baden-Württemberg
- BY, Freistaat Bayern → Bayern
- SH → Schleswig-Holstein
- NDS → Niedersachsen
- HE → Hessen
- RP → Rheinland-Pfalz
- SL → Saarland
- BE → Berlin
- BB → Brandenburg
- MV → Mecklenburg-Vorpommern
- SN → Sachsen
- ST → Sachsen-Anhalt
- TH → Thüringen
- HH → Hamburg
- HB → Bremen

Analysiere die Anfrage und gib JSON zurück:
{{
  "operation": "create_entity|create_entity_type|create_facet|create_relation|create_category_setup|start_crawl|combined|none",
  "entity_type": "municipality|person|organization|event",
  "entity_data": {{
    "name": "Name der Entity",
    "core_attributes": {{"position": "...", "email": "..."}},
    "external_id": "optional"
  }},
  "entity_type_data": {{
    "name": "Name des Entity-Typs (z.B. 'Windpark')",
    "name_plural": "Plural-Form (z.B. 'Windparks')",
    "description": "Beschreibung",
    "icon": "mdi-wind-turbine",
    "color": "#4CAF50",
    "is_primary": true,
    "supports_hierarchy": false
  }},
  "facet_data": {{
    "facet_type": "pain_point|positive_signal|contact|summary",
    "target_entity_name": "Name der Ziel-Entity (z.B. Gemeinde)",
    "value": {{"description": "...", "severity": "high|medium|low"}},
    "text_representation": "Kurze Textdarstellung"
  }},
  "relation_data": {{
    "relation_type": "works_for|attends|located_in|member_of",
    "source_entity_name": "Name der Quell-Entity",
    "source_entity_type": "person|event",
    "target_entity_name": "Name der Ziel-Entity",
    "target_entity_type": "municipality|organization|event"
  }},
  "category_setup_data": {{
    "name": "Vorgeschlagener Name (z.B. 'Event-Besuche NRW')",
    "purpose": "Zweck/Beschreibung",
    "user_intent": "Original-Intent des Users",
    "search_focus": "event_attendance|pain_points|contacts|general",
    "search_terms": ["Begriff1", "Begriff2"],
    "geographic_filter": {{
      "admin_level_1": "Nordrhein-Westfalen",
      "admin_level_1_alias": "NRW",
      "country": "DE"
    }},
    "time_focus": "future_only|past_only|all",
    "target_entity_types": ["person", "event"],
    "extraction_handler": "event|default",
    "suggested_facets": ["event_attendance", "contact"]
  }},
  "crawl_command_data": {{
    "filter_type": "location|category|source_ids|entity_name",
    "location_name": "Ortsname (z.B. Gummersbach)",
    "admin_level_1": "Bundesland (z.B. Nordrhein-Westfalen)",
    "category_slug": "kategorie-slug",
    "source_ids": [],
    "include_all_categories": true
  }},
  "combined_operations": [
    {{"operation": "create_category_setup", "category_setup_data": {{...}}}},
    {{"operation": "start_crawl", "crawl_command_data": {{...}}}}
  ],
  "explanation": "Was wird erstellt/geändert"
}}

Wenn es KEINE Schreib-Operation ist, setze "operation": "none".

## Icons (Material Design Icons - mdi-*):
- Windenergie: mdi-wind-turbine
- Solar: mdi-solar-power
- Gebäude: mdi-office-building
- Projekt: mdi-clipboard-list
- Dokument: mdi-file-document
- Firma: mdi-domain
- Land: mdi-earth
- Technologie: mdi-cog
- Event: mdi-calendar
- Person: mdi-account

## Farben (Hex):
- Grün: #4CAF50
- Blau: #2196F3
- Orange: #FF9800
- Rot: #F44336
- Lila: #9C27B0

Benutzeranfrage: {query}

Antworte NUR mit validem JSON."""


AI_ENTITY_TYPE_PROMPT = """Du generierst eine EntityType-Konfiguration basierend auf einer Benutzeranfrage.

## Benutzeranfrage:
{user_intent}

## Geografischer Fokus:
{geographic_context}

## Aufgabe:
Analysiere die Anfrage und erstelle eine passende EntityType-Konfiguration.

## Ausgabe (JSON):
{{
  "name": "Kurzer, prägnanter Name (z.B. 'Event-Besuche NRW')",
  "name_plural": "Pluralform",
  "description": "Ausführliche Beschreibung was dieser Typ repräsentiert",
  "icon": "Material Design Icon (mdi-calendar, mdi-account, mdi-office-building, mdi-lightbulb, mdi-alert, mdi-handshake)",
  "color": "Hex-Farbe (#2196F3=blau, #4CAF50=grün, #FF9800=orange, #9C27B0=lila)",
  "attribute_schema": {{
    "type": "object",
    "properties": {{
      "field_name": {{"type": "string", "description": "Beschreibung"}}
    }},
    "required": ["wichtigstes_feld"]
  }},
  "search_focus": "event_attendance|pain_points|contacts|opportunities|general"
}}

Antworte NUR mit validem JSON."""


AI_CATEGORY_PROMPT = """Du generierst eine Category-Konfiguration für Web-Crawling und KI-Extraktion.

## Benutzeranfrage:
{user_intent}

## EntityType:
Name: {entity_type_name}
Beschreibung: {entity_type_description}

## Aufgabe:
Erstelle eine Category-Konfiguration mit einem detaillierten KI-Extraktions-Prompt.

## Ausgabe (JSON):
{{
  "purpose": "Kurze Zweckbeschreibung für die Category",
  "search_terms": ["Begriff1", "Begriff2", "Begriff3", "..."],
  "extraction_handler": "event|default",
  "ai_extraction_prompt": "Detaillierter mehrzeiliger Prompt für die KI-Extraktion...\\n\\nMit Anweisungen...\\n\\nUnd Beispielen..."
}}

## Wichtig für search_terms:
- Erweitere abstrakte Begriffe: "Entscheider" → "Bürgermeister", "Landrat", "Dezernent", etc.
- Füge relevante Synonyme hinzu
- Mindestens 10-15 konkrete Suchbegriffe
- In der Sprache der Zieldokumente (meist Deutsch)

## Wichtig für ai_extraction_prompt:
- Sehr detailliert (200-500 Wörter)
- Klare Struktur mit ## Überschriften
- Konkrete Beispiele was extrahiert werden soll
- Bezug zum EntityType "{entity_type_name}"
- Output-Format spezifizieren (JSON-Struktur)

Antworte NUR mit validem JSON."""


AI_CRAWL_CONFIG_PROMPT = """Du generierst URL-Filter-Konfiguration für einen Web-Crawler.

## Benutzeranfrage:
{user_intent}

## Suchfokus:
{search_focus}

## Search Terms:
{search_terms}

## Aufgabe:
Erstelle AUSSCHLIESSLICH Exclude-Patterns (Blacklist) um irrelevante Seiten auszufiltern.
WICHTIG: Keine Include-Patterns (Whitelist) verwenden! Die KI-gestützte Inhaltsanalyse
filtert relevante Dokumente - der Crawler soll ALLE Seiten besuchen (außer den ausgeschlossenen).

## Ausgabe (JSON):
{{
  "url_include_patterns": [],
  "url_exclude_patterns": [
    "/impressum",
    "/datenschutz",
    "/privacy",
    "/pattern_to_exclude"
  ],
  "reasoning": "Kurze Begründung für die gewählten Exclude-Patterns"
}}

## Exclude-Patterns (Blacklist):
Standard-Ausschlüsse (immer inkludieren):
- /impressum, /datenschutz, /privacy, /kontakt, /contact
- /login, /logout, /register, /admin/, /api/, /wp-admin
- /sitemap, /feed/, /rss, /print/, /suche, /search
- /archiv.*, /warenkorb, /cart, /checkout
- \\?page=, \\?sort=, \\?filter= (Pagination/Sortierung)
- /cdn/, /static/, /assets/, /media/

Zusätzliche kontextspezifische Ausschlüsse basierend auf dem Suchfokus hinzufügen.

WICHTIG: url_include_patterns MUSS ein leeres Array [] sein!

Antworte NUR mit validem JSON."""
