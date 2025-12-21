"""AI Prompts for Smart Query Service.

Note: Query interpretation prompts are now generated dynamically in
query_interpreter.py:build_dynamic_query_prompt() to include current
facet and entity types from the database.
"""

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
- discover_sources: KI-gesteuerte Suche nach Datenquellen im Internet (z.B. "Finde alle Bundesliga-Vereine", "Suche nach Gemeinden in NRW")
- analyze_pysis_for_facets: PySis-Felder analysieren und Facets erstellen
- enrich_facets_from_pysis: Bestehende Facets mit PySis-Daten anreichern
- update_entity: Entity aktualisieren
- create_facet_type: Neuen Facet-Typ erstellen (z.B. "Erstelle einen Facet-Typ für Kontaktdaten")
- assign_facet_type: Facet-Typ einem Entity-Typ zuweisen
- batch_operation: Massenoperation auf mehreren Entities (z.B. "Füge allen Gemeinden in NRW einen Pain Point hinzu")
- delete_entity: Entity löschen (Soft-Delete, kann rückgängig gemacht werden)
- delete_facet: Einzelnes Facet von Entity löschen
- batch_delete: Massen-Löschung von Entities oder Facets
- export_query_result: Query-Ergebnis exportieren als CSV, JSON oder Excel
- undo_change: Letzte Änderung rückgängig machen
- get_change_history: Änderungshistorie anzeigen
- combined: Mehrere Operationen in einem Befehl

## Befehle erkennen:
- "Erstelle", "Anlegen", "Neue/r/s", "Füge hinzu" → CREATE
- "Aktualisiere", "Ändere", "Setze" → UPDATE
- "Verknüpfe", "Verbinde" → CREATE_RELATION
- "Neuen Entity-Typ", "Neuen Typ" → CREATE_ENTITY_TYPE (nur für reine Typ-Definition ohne Crawling)
- "Erstelle eine Kategorie für...", "Neue Kategorie für...", "Kategorie für...", "Finde alle...", "Suche nach...", "Überwache...", "Crawle..." → CREATE_CATEGORY_SETUP (mit oder ohne geografische Einschränkung, für Themen die gecrawlt werden sollen wie PlayStation News, Kryptokurse, IT-Jobs, Wetter, etc.)
- "Starte Crawl", "Crawle", "Führe Crawl aus" → START_CRAWL
- "Finde Datenquellen", "Suche Datenquellen", "Entdecke Quellen", "Importiere alle X", "Finde alle X im Internet", "Suche im Web nach X" → DISCOVER_SOURCES
- "Analysiere PySis", "PySis zu Facets", "Extrahiere aus PySis" → ANALYZE_PYSIS_FOR_FACETS
- "Reichere Facets an", "Befülle Facets", "Ergänze Facets mit PySis" → ENRICH_FACETS_FROM_PYSIS
- "Neuen Facet-Typ", "Erstelle Facet-Typ", "Neuer Facet für" → CREATE_FACET_TYPE
- "Weise Facet-Typ zu", "Facet-Typ zuweisen", "Facet aktivieren für" → ASSIGN_FACET_TYPE
- "Füge ALLEN...", "Bei allen...", "Für alle..." + Massenangabe → BATCH_OPERATION
- "Lösche", "Entferne", "Delete", "Remove" (einzelne Entity) → DELETE_ENTITY
- "Lösche den Facet", "Entferne das Facet", "Facet löschen" → DELETE_FACET
- "Lösche alle", "Entferne alle", "Lösche bei allen" + Massenangabe → BATCH_DELETE
- "Exportiere", "Export", "Als CSV", "Als Excel", "Herunterladen" → EXPORT_QUERY_RESULT
- "Rückgängig", "UNDO", "Zurücksetzen", "Wiederherstellen" → UNDO_CHANGE
- "Änderungshistorie", "Änderungen anzeigen", "Was wurde geändert" → GET_CHANGE_HISTORY
- Kombinierte Befehle mit "und dann", "danach", "anschließend" → COMBINED

## UNDO-OPERATIONEN erkennen:
Trigger-Phrasen für Rückgängig-Machen:
- "Mach die letzte Änderung rückgängig"
- "UNDO die Änderung an Gemeinde X"
- "Setze die Entity Y zurück"
- "Stelle den vorherigen Zustand wieder her"
- "Zeige mir die Änderungshistorie von Entity X"

## DISCOVER_SOURCES erkennen (KI-gesteuerte Datenquellen-Suche):
Trigger-Phrasen für Datenquellen-Suche im Internet:
- "Finde alle deutschen Bundesliga-Vereine"
- "Suche nach Gemeinden in NRW"
- "Entdecke alle Universitäten in Deutschland"
- "Importiere alle DAX-Unternehmen"
- "Finde Datenquellen für Windparks"
- "Suche im Web nach Gemeinden in Bayern"
- "Durchsuche das Internet nach..."

WICHTIG: Diese Operation unterscheidet sich von CREATE_CATEGORY_SETUP:
- DISCOVER_SOURCES: Sucht im Internet nach neuen Datenquellen die noch nicht im System sind
- CREATE_CATEGORY_SETUP: Erstellt eine Kategorie um BESTEHENDE DataSources zu crawlen

## EXPORT-OPERATIONEN erkennen:
Trigger-Phrasen für Exports:
- "Exportiere alle Gemeinden in NRW als CSV"
- "Download Bürgermeister als Excel"
- "Exportiere die Ergebnisse als JSON"
- "Erstelle einen CSV-Export von Personen mit Pain Points"
- "Gib mir die Daten als Excel-Datei"

## DELETE-OPERATIONEN erkennen:
Trigger-Phrasen für Löschungen (VORSICHT - requires_confirmation=true!):
### Einzelne Entity:
- "Lösche die Gemeinde X"
- "Entferne die Person Y"
- "Delete Entity Z"
### Einzelnes Facet:
- "Lösche den Pain Point von Gemeinde X"
- "Entferne das Facet Y von Person Z"
- "Lösche die Event-Teilnahme von..."
### Massen-Löschung:
- "Lösche alle Pain Points von Gemeinden in NRW"
- "Entferne alle Event-Teilnahmen älter als 2023"
- "Lösche alle inaktiven Entities"

## BATCH_OPERATION erkennen:
Trigger-Phrasen für Massenoperationen:
- "Füge allen Gemeinden in NRW einen Pain Point hinzu"
- "Setze bei allen Personen die Position auf 'Kontakt'"
- "Lösche alle Facets vom Typ X bei Gemeinden in Bayern"
- "Verknüpfe alle Personen mit Event Y"
Wichtig: Muss mehrere Entities betreffen (nicht nur eine!)

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

## DataSource Tags:
DataSources werden über Tags kategorisiert und gefiltert:
### Geografische Tags (Bundesländer):
- nrw, bayern, baden-wuerttemberg, hessen, niedersachsen, schleswig-holstein
- rheinland-pfalz, saarland, berlin, brandenburg, mecklenburg-vorpommern
- sachsen, sachsen-anhalt, thueringen, hamburg, bremen
### Länder-Tags:
- de (Deutschland), at (Österreich), ch (Schweiz), uk (Großbritannien)
### Typ-Tags:
- kommunal (Gemeinden/Städte), landkreis, landesebene, bundesebene
- oparl (OParl-API), ratsinformation
### Themen-Tags:
- windkraft, solar, bauen, verkehr, umwelt

Bei CREATE_CATEGORY_SETUP: suggested_tags werden aus geographic_filter und Kontext abgeleitet.
Beispiel: "Gemeinden in NRW" → suggested_tags: ["nrw", "kommunal"]

Analysiere die Anfrage und gib JSON zurück:
{{
  "operation": "create_entity|create_entity_type|create_facet|create_relation|create_category_setup|start_crawl|discover_sources|analyze_pysis_for_facets|enrich_facets_from_pysis|update_entity|create_facet_type|assign_facet_type|batch_operation|delete_entity|delete_facet|batch_delete|export_query_result|undo_change|get_change_history|combined|none",
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
    "suggested_facets": ["event_attendance", "contact"],
    "suggested_tags": ["nrw", "kommunal"]
  }},
  "crawl_command_data": {{
    "filter_type": "location|category|source_ids|entity_name",
    "location_name": "Ortsname (z.B. Gummersbach)",
    "admin_level_1": "Bundesland (z.B. Nordrhein-Westfalen)",
    "category_slug": "kategorie-slug",
    "source_ids": [],
    "include_all_categories": true
  }},
  "discover_sources_data": {{
    "prompt": "Natürlichsprachiger Suchauftrag (z.B. 'Alle deutschen Bundesliga-Vereine', 'Gemeinden in NRW')",
    "max_results": 50,
    "search_depth": "quick|standard|deep",
    "auto_import": false,
    "category_ids": []
  }},
  "pysis_data": {{
    "entity_name": "Name der Entity (z.B. 'Gummersbach')",
    "entity_id": "optional - Entity-UUID falls bekannt",
    "facet_type_id": "optional - nur diesen FacetType anreichern",
    "overwrite": false,
    "include_empty": false
  }},
  "update_data": {{
    "entity_name": "Name der zu aktualisierenden Entity",
    "entity_id": "optional - Entity-UUID falls bekannt",
    "updates": {{
      "name": "Neuer Name",
      "core_attributes": {{"key": "value"}}
    }}
  }},
  "facet_type_data": {{
    "name": "Name des Facet-Typs (z.B. 'Kontaktdaten')",
    "name_plural": "Plural (z.B. 'Kontaktdaten')",
    "description": "Beschreibung was dieser Facet-Typ erfasst",
    "icon": "mdi-account-card-details",
    "color": "#2196F3",
    "value_type": "structured|text|number|boolean|date",
    "applicable_entity_type_slugs": ["municipality", "person"],
    "ai_extraction_enabled": true,
    "ai_extraction_prompt": "Extrahiere Kontaktdaten aus dem Dokument..."
  }},
  "assign_facet_type_data": {{
    "facet_type_slug": "pain_point",
    "target_entity_type_slugs": ["municipality", "organization"]
  }},
  "batch_operation_data": {{
    "action_type": "add_facet|update_field|add_relation|remove_facet",
    "target_filter": {{
      "entity_type": "municipality|person|organization|event",
      "location_filter": "NRW|Bayern|...",
      "additional_filters": {{"position": "Bürgermeister"}}
    }},
    "action_data": {{
      "facet_type": "pain_point (für add_facet/remove_facet)",
      "facet_value": {{"description": "...", "severity": "high"}},
      "field_name": "position (für update_field)",
      "field_value": "neuer Wert",
      "relation_type": "works_for (für add_relation)",
      "relation_target": "Ziel-Entity Name"
    }},
    "dry_run": true
  }},
  "delete_entity_data": {{
    "entity_name": "Name der zu löschenden Entity",
    "entity_id": "optional - Entity-UUID falls bekannt",
    "entity_type": "municipality|person|organization|event",
    "reason": "Begründung für die Löschung (optional)",
    "requires_confirmation": true
  }},
  "delete_facet_data": {{
    "entity_name": "Name der Entity, deren Facet gelöscht werden soll",
    "entity_id": "optional - Entity-UUID falls bekannt",
    "facet_type": "pain_point|positive_signal|contact|event_attendance|summary",
    "facet_id": "optional - Facet-UUID für spezifisches Facet",
    "facet_description": "Beschreibung des zu löschenden Facets (für Identifikation)",
    "delete_all_of_type": false,
    "requires_confirmation": true
  }},
  "batch_delete_data": {{
    "delete_type": "entities|facets",
    "target_filter": {{
      "entity_type": "municipality|person|organization|event",
      "location_filter": "NRW|Bayern|...",
      "facet_type": "pain_point (nur für facets)",
      "date_before": "2023-01-01 (optional - für alte Facets)",
      "additional_filters": {{"is_active": false}}
    }},
    "reason": "Begründung für die Massen-Löschung",
    "dry_run": true,
    "requires_confirmation": true
  }},
  "export_data": {{
    "format": "csv|json|excel",
    "query_filter": {{
      "entity_type": "municipality|person|organization|event",
      "location_filter": "NRW|Bayern|...",
      "facet_types": ["pain_point", "contact"],
      "position_keywords": ["Bürgermeister"],
      "country": "DE"
    }},
    "include_facets": true,
    "include_relations": true,
    "fields": ["name", "position", "email", "facets"],
    "filename": "export_gemeinden_nrw"
  }},
  "undo_data": {{
    "entity_name": "Name der Entity deren Änderung rückgängig gemacht werden soll",
    "entity_id": "optional - Entity-UUID falls bekannt",
    "entity_type": "Entity|FacetValue",
    "undo_type": "last (standard, letzte Änderung)"
  }},
  "history_data": {{
    "entity_name": "Name der Entity deren Historie angezeigt werden soll",
    "entity_id": "optional - Entity-UUID falls bekannt",
    "entity_type": "Entity|FacetValue",
    "limit": 10
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

## Geografischer Kontext:
{geographic_context}

## Aufgabe:
Erstelle eine Category-Konfiguration mit einem detaillierten KI-Extraktions-Prompt.

## Ausgabe (JSON):
{{
  "purpose": "Kurze Zweckbeschreibung für die Category",
  "search_terms": ["Begriff1", "Begriff2", "Begriff3", "..."],
  "extraction_handler": "event|default",
  "ai_extraction_prompt": "Detaillierter mehrzeiliger Prompt für die KI-Extraktion...\\n\\nMit Anweisungen...\\n\\nUnd Beispielen...",
  "suggested_tags": ["tag1", "tag2"]
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

## Wichtig für suggested_tags:
Tags werden verwendet um passende DataSources der Category zuzuordnen.
Verfügbare Tag-Kategorien:
- Bundesländer: nrw, bayern, baden-wuerttemberg, hessen, niedersachsen, etc.
- Länder: de, at, ch, uk
- Typ: kommunal, landkreis, landesebene, oparl, ratsinformation
- Themen: windkraft, solar, bauen, verkehr, umwelt

Leite Tags aus dem geografischen Kontext und Thema ab:
- "Gemeinden in NRW" → ["nrw", "kommunal"]
- "OParl-Daten aus Bayern" → ["bayern", "oparl"]
- "Windkraft-Projekte in Deutschland" → ["de", "kommunal", "windkraft"]

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


AI_FACET_TYPES_PROMPT = """Du generierst FacetType-Vorschläge für ein Entity-Daten-System.

## Benutzeranfrage:
{user_intent}

## EntityType:
Name: {entity_type_name}
Beschreibung: {entity_type_description}

## Was sind FacetTypes?
FacetTypes definieren strukturierte Informationen, die über Zeit zu Entities gesammelt werden:
- Beobachtungen aus verschiedenen Quellen (Dokumente, Web-Crawler)
- Zeit-basierte Daten mit event_date
- Mehrere Werte pro Entity möglich
- Mit Quellenangabe und Confidence Score

## Unterschied zu core_attributes:
- core_attributes: Statische Grunddaten (Name, Adresse, Gründungsjahr)
- FacetTypes: Dynamische Beobachtungen (News-Erwähnungen, Pain Points, Kontakte, Events)

## Aufgabe:
Generiere 2-4 passende FacetTypes für diese Kategorie.
Wähle aus Standard-FacetTypes oder erstelle neue, themenspezifische.

## Standard-FacetTypes (wenn passend verwenden):
- pain_point: Probleme, Herausforderungen, negative Entwicklungen
- positive_signal: Chancen, positive Entwicklungen, Erfolge
- contact: Ansprechpartner, Kontaktpersonen
- news_mention: Erwähnungen in Nachrichten/Medien
- event_attendance: Event-Teilnahmen, Veranstaltungen

## Ausgabe (JSON):
{{
  "facet_types": [
    {{
      "name": "Name des FacetTypes",
      "slug": "slug_lowercase_underscore",
      "name_plural": "Plural-Name",
      "description": "Kurze Beschreibung wofür dieser FacetType verwendet wird",
      "value_type": "object",
      "value_schema": {{
        "type": "object",
        "properties": {{
          "description": {{"type": "string", "description": "Textbeschreibung"}},
          "category": {{"type": "string", "description": "Kategorie/Typ"}}
        }}
      }},
      "icon": "mdi-icon-name",
      "color": "#HexColor",
      "is_time_based": true,
      "ai_extraction_prompt": "Extrahiere X aus dem Dokument. Achte auf Y und Z."
    }}
  ],
  "reasoning": "Begründung für die Auswahl der FacetTypes"
}}

## Icon-Auswahl (Material Design Icons):
- Pain Points: mdi-alert-circle (rot)
- Positive Signale: mdi-thumb-up (grün)
- Kontakte: mdi-account (blau)
- News: mdi-newspaper (orange)
- Events: mdi-calendar (lila)
- Finanzen: mdi-currency-eur (grün)
- Technologie: mdi-chip (blau)
- Sport: mdi-soccer (grün)

Antworte NUR mit validem JSON."""


AI_SEED_ENTITIES_PROMPT = """Du generierst eine Liste von bekannten Entities für ein Datenerfassungssystem.

## Benutzeranfrage:
{user_intent}

## EntityType:
Name: {entity_type_name}
Beschreibung: {entity_type_description}

## Attribute Schema:
{attribute_schema}

## Geografischer Kontext:
{geographic_context}

## Aufgabe:
Generiere eine Liste von BEKANNTEN, REALEN Entities basierend auf deinem Wissen.
Diese dienen als Seed-Daten, die später durch Crawling angereichert werden.

## WICHTIG:
- NUR bekannte, verifizierbare Entities nennen
- Lieber weniger aber korrekte Daten als Vermutungen
- Bei großen Listen (z.B. alle Gemeinden in NRW): Beschränke auf die wichtigsten ~50
- Attribute nur ausfüllen wenn SICHER bekannt

## Beispiele:
- "Bundesliga-Vereine" → Alle 18 aktuellen Erstliga-Vereine
- "DAX Unternehmen" → Alle 40 DAX-Unternehmen
- "Gemeinden in NRW" → Die 50 größten Städte/Gemeinden

## Ausgabe (JSON):
{{
  "entities": [
    {{
      "name": "Name der Entity",
      "external_id": "Optional: Offizielle ID (z.B. AGS für Gemeinden)",
      "core_attributes": {{
        "attribute1": "Wert (nur wenn sicher bekannt)",
        "attribute2": "Wert"
      }},
      "latitude": null,
      "longitude": null,
      "admin_level_1": "Bundesland/Region (wenn relevant)",
      "country": "DE",
      "relations": [
        {{
          "relation_type": "located_in",
          "target_name": "Name der Ziel-Entity (z.B. Stadt/Gemeinde)",
          "target_type": "municipality"
        }}
      ]
    }}
  ],
  "total_known": 18,
  "is_complete_list": true,
  "reasoning": "Begründung warum diese Entities gewählt wurden",
  "data_quality_note": "Hinweis zur Datenqualität",
  "hierarchy": {{
    "use_hierarchy": false,
    "parent_entity_type": null,
    "parent_name": null,
    "hierarchy_reasoning": "Begründung ob Hierarchie sinnvoll ist"
  }}
}}

## Relations (Beziehungen):
Füge sinnvolle Relationen hinzu wenn die Ziel-Entity bekannt ist:
- located_in: Für geografische Zuordnung (Verein → Stadt, Unternehmen → Stadt)
- member_of: Für Mitgliedschaften (Person → Organisation)
- works_for: Für Arbeitsverhältnisse

## Hierarchie:
Prüfe ob eine hierarchische Struktur sinnvoll ist:
- "Gemeinden in NRW" → use_hierarchy: true, parent_name: "Nordrhein-Westfalen", parent_entity_type: "municipality"
- "Städte in Hessen" → use_hierarchy: true, parent_name: "Hessen", parent_entity_type: "municipality"
- "Kreisfreie Städte in Hessen" → use_hierarchy: true, parent_name: "Hessen", parent_entity_type: "municipality"
- "Bundesliga-Vereine" → use_hierarchy: false (keine natürliche Hierarchie)
- "DAX Unternehmen" → use_hierarchy: false

WICHTIG: Bei geografisch eingeschränkten Anfragen (z.B. "in Hessen", "in Bayern", "in NRW")
MUSS use_hierarchy: true gesetzt werden und parent_name MUSS das Bundesland sein!

## Datenqualität:
- is_complete_list: true wenn ALLE bekannten Entities enthalten sind (z.B. 18 Bundesliga-Vereine)
- is_complete_list: false wenn nur eine Auswahl (z.B. 50 von 396 NRW-Gemeinden)
- total_known: Geschätzte Gesamtzahl bekannter Entities

Antworte NUR mit validem JSON."""
