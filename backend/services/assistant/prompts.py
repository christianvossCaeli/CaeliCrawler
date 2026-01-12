"""Assistant Service - Prompt Templates."""

# Page-specific documentation for context-aware assistance
PAGE_DOCUMENTATION = {
    "/entities": """
## Entitäten-Liste
Hier können Sie:
- **Filtern**: Nach Entity-Typ, Kategorie, Facet-Werten oder Standort
- **Sortieren**: Nach Name, Datum, Facet-Anzahl
- **Bulk-Auswahl**: Mehrere Entities für Massenoperationen auswählen
- **Erstellen**: Neue Entities anlegen
- **Export**: Ausgewählte Entities als CSV/Excel exportieren
- **Erweiterte Filter**: Komplexe Filter-Kombinationen erstellen
""",
    "/entities/{type}/{id}": """
## Entity-Detailansicht
Hier können Sie:
- **Übersicht**: Alle Entity-Daten auf einen Blick sehen
- **Facets bearbeiten**: Werte hinzufügen, ändern oder löschen
- **Relationen verwalten**: Verknüpfungen zu anderen Entities erstellen
- **Dokumente einsehen**: Zugehörige Dokumente und Anhänge anzeigen
- **PySis-Analyse**: Strukturierte Datenanalyse starten
- **Facet-Anreicherung**: Facets aus PySis-Daten generieren
- **Crawl starten**: Neue Daten für diese Entity crawlen
""",
    "/categories": """
## Kategorien-Verwaltung
Hier können Sie:
- **Kategorien erstellen**: Neue Crawl-Kategorien anlegen
- **Quellen zuweisen**: Datenquellen per Tags zuordnen
- **Crawl starten**: Kategorie-weite Crawl-Jobs starten
- **Dokumente reanalysieren**: KI-Extraktion erneut ausführen
- **Entity-Typen zuweisen**: Ziel-Entity-Typ konfigurieren
""",
    "/sources": """
## Datenquellen-Verwaltung
Hier können Sie:
- **Quellen erstellen**: Neue Datenquellen (Webseiten, APIs, RSS) anlegen
- **Verbindung testen**: Konnektivität und Erreichbarkeit prüfen
- **Tags zuweisen**: Quellen mit Tags für einfache Filterung versehen
- **Status überwachen**: Crawl-Status und Fehler einsehen
- **KI-Quellensuche**: Automatisch passende Quellen finden lassen
""",
    "/smart-query": """
## Smart Query
Hier können Sie:
- **Natürlichsprachige Abfragen**: Fragen in normalem Deutsch stellen
- **Read-Mode**: Daten abfragen ohne Änderungen
- **Write-Mode**: Änderungen per Spracheingabe vornehmen
- **Plan-Mode**: Komplexe mehrstufige Operationen planen
- **Ergebnisse exportieren**: Abfrageergebnisse als CSV/Excel speichern
- **Als Summary speichern**: Abfrage als wiederverwendbares Dashboard speichern
""",
    "/crawler": """
## Crawler-Steuerung
Hier können Sie:
- **Aktive Jobs überwachen**: Laufende Crawl-Jobs in Echtzeit sehen
- **Jobs starten**: Neue Crawl-Jobs für Quellen starten
- **Jobs pausieren/stoppen**: Laufende Jobs kontrollieren
- **Logs einsehen**: Detaillierte Crawl-Logs analysieren
- **Presets verwalten**: Wiederverwendbare Crawl-Konfigurationen speichern
""",
    "/summaries": """
## Dashboards & Summaries
Hier können Sie:
- **Widgets hinzufügen**: Diagramme, Tabellen, Karten einfügen
- **Widgets konfigurieren**: Datenquellen und Visualisierung anpassen
- **Layout anpassen**: Widgets per Drag&Drop anordnen
- **Daten aktualisieren**: Live-Daten neu laden
- **Teilen**: Dashboards mit anderen Nutzern teilen
- **Exportieren**: Dashboard-Daten als PDF/Excel exportieren
""",
    "/favorites": """
## Favoriten
Hier können Sie:
- **Favoriten organisieren**: Gespeicherte Entities verwalten
- **Schnellzugriff**: Direkt zu wichtigen Entities navigieren
- **Sortieren**: Nach Name oder Datum hinzugefügt ordnen
""",
    "/documents": """
## Dokumente
Hier können Sie:
- **Dokumente durchsuchen**: Volltext-Suche in allen Dokumenten
- **Filtern**: Nach Typ, Status, Quelle oder Kategorie
- **Extraktionen einsehen**: KI-extrahierte Daten anzeigen
- **Verknüpfungen**: Zugehörige Entities sehen
""",
}


def get_page_documentation(route: str) -> str:
    """Get page-specific documentation for the current route.

    Matches routes in order of specificity:
    1. Exact match
    2. Entity detail pattern (/entities/{type}/{id})
    3. Prefix match with path boundary (e.g., /sources matches /sources/edit)
    """
    # Normalize route (remove trailing slash for comparison)
    normalized_route = route.rstrip("/") if route != "/" else route

    # Exact match
    if normalized_route in PAGE_DOCUMENTATION:
        return PAGE_DOCUMENTATION[normalized_route]

    # Check with trailing slash removed from patterns
    for pattern in PAGE_DOCUMENTATION:
        normalized_pattern = pattern.rstrip("/") if pattern != "/" else pattern
        if normalized_route == normalized_pattern:
            return PAGE_DOCUMENTATION[pattern]

    # Entity detail pattern (special case)
    if normalized_route.startswith("/entities/") and normalized_route.count("/") >= 2:
        return PAGE_DOCUMENTATION.get("/entities/{type}/{id}", "")

    # Prefix match with path boundary check
    # Ensures /sources matches /sources/edit but not /sourcesview
    for pattern, doc in PAGE_DOCUMENTATION.items():
        normalized_pattern = pattern.rstrip("/") if pattern != "/" else pattern
        if normalized_route.startswith(normalized_pattern + "/") or normalized_route == normalized_pattern:
            return doc

    return ""


INTENT_CLASSIFICATION_PROMPT = """Du bist ein Intent-Classifier für einen Chat-Assistenten in einer Entity-Management-App.

## Kontext der aktuellen Seite:
- Route: {current_route}
- Entity-Typ: {entity_type}
- Entity-Name: {entity_name}
- View-Mode: {view_mode}
- Ausgewählte Entities: {selected_count} (IDs: {selected_ids})
- Aktive Filter: {active_filters}
- Verfügbare Features: {available_features}
- Verfügbare Aktionen: {available_actions}

## Seitenspezifische Hilfe:
{page_documentation}

## Verfügbare Intents:
1. QUERY - Benutzer stellt eine Frage/Suche (z.B. "Zeige Pain Points", "Welche Events gibt es?")
2. CONTEXT_QUERY - Frage bezieht sich auf aktuelle Entity (z.B. "Was sind die Details?", "Zeig mir mehr")
3. INLINE_EDIT - Einfache Änderung an aktueller Entity (z.B. "Ändere den Namen zu X", "Setze Position auf Y")
4. COMPLEX_WRITE - Komplexe Erstellung (z.B. "Erstelle neue Category", "Lege neuen EntityType an")
5. NAVIGATION - Benutzer will NUR zu einer anderen Seite navigieren, ohne Details zu erfahren (z.B. "Geh zu Gummersbach", "Öffne Max Mueller", "Navigiere zu...")
6. SUMMARIZE - Benutzer will Zusammenfassung (z.B. "Fasse zusammen", "Gib mir einen Überblick")
7. HELP - Benutzer braucht Hilfe (z.B. "Wie funktioniert das?", "Was kann ich hier tun?")
8. BATCH_ACTION - Benutzer will Massenoperation durchführen (z.B. "Füge allen Gemeinden in NRW Pain Point hinzu", "Aktualisiere alle Entities vom Typ X")
9. FACET_MANAGEMENT - Benutzer will Facet-Typen erstellen, zuweisen oder verwalten (z.B. "Erstelle einen neuen Facet-Typ", "Welche Facets gibt es für Gemeinden?")
10. CONTEXT_ACTION - Benutzer will Aktion auf aktueller Entity ausführen (z.B. "Analysiere PySis", "Reichere Facets an", "Zeig PySis-Status", "Starte Crawl für diese Gemeinde")
11. SOURCE_MANAGEMENT - Benutzer will Datenquellen verwalten, Tags abfragen oder Quellen suchen/importieren (z.B. "Welche Tags gibt es?", "Zeige Quellen mit Tag nrw", "Finde Datenquellen für Bundesliga")
12. DISCUSSION - Benutzer teilt Dokumente, Anforderungen, Notizen oder will diskutieren/planen (z.B. lange Texte, E-Mails, Anforderungspapiere, "hier sind meine Notizen", "was meinst du dazu?", "kannst du mir helfen bei...")
13. ENTITY_INFO - Benutzer will detaillierte INFORMATIONEN über eine bestimmte Entity sehen (z.B. "Was weißt du über Gummersbach?", "Zeig mir alles über Bad Rodach", "Welche Infos gibt es zu X?", "Was kannst du mir über Y sagen?", "Erzähl mir etwas über Z")

WICHTIG: Unterscheide zwischen NAVIGATION und ENTITY_INFO:
- NAVIGATION = "Geh zu X", "Navigiere zu X", "Öffne X" → Benutzer will NUR dorthin wechseln
- ENTITY_INFO = "Was weißt du über X?", "Zeig mir Infos zu X", "Was kannst du mir über X sagen?" → Benutzer will INFORMATIONEN sehen

## Context Actions (für Intent CONTEXT_ACTION):
- show_pysis_status: PySis-Status anzeigen
- analyze_pysis: PySis-Analyse VORSCHAU anzeigen (noch nicht ausführen)
- analyze_pysis_execute: PySis-Analyse AUSFÜHREN (bei Bestätigung wie "Ja, starte", "Ja, analysieren")
- enrich_facets: Facet-Anreicherung aus PySis VORSCHAU anzeigen (noch nicht ausführen)
- enrich_facets_execute: Facet-Anreicherung aus PySis AUSFÜHREN (bei Bestätigung)
  - Mit overwrite=true wenn "überschreiben" erwähnt wird
- analyze_entity_data: Datenbasierte Facet-Analyse starten (z.B. "Analysiere die Verknüpfungen", "Schreibe Pain Points basierend auf den Relationen", "Reichere aus Dokumenten an")
  - Analysiert Relationen, Dokumente, Extraktionen und PySis-Daten
  - context_action_data kann enthalten: source_types (Liste: pysis, relations, documents, extractions)
- start_crawl: Crawl starten
- create_facet: Facet-Wert zur aktuellen Entity hinzufügen (z.B. "Füge Pain Point hinzu", "Neues Positive Signal")
  - context_action_data sollte enthalten: facet_type (pain_point|positive_signal|contact|summary), description, optional: severity, type
- show_entity_history: Verlaufsdaten anzeigen (z.B. "Zeige den Verlauf", "Wie ist der Haushaltsverlauf?")
  - context_action_data kann enthalten: facet_type_slug (History-Facet-Typ)
- add_history_point: Datenpunkt zu History-Facet hinzufügen (z.B. "Füge Haushaltsvolumen 5 Mio für 2024 hinzu")
  - context_action_data sollte enthalten: facet_type_slug, value, recorded_at (optional), track_key (optional), note (optional)

## Source Management Actions (für Intent SOURCE_MANAGEMENT):
- list_tags: Alle verfügbaren Tags anzeigen (z.B. "Welche Tags gibt es?", "Zeig alle Tags")
- list_sources_by_tag: Quellen nach Tag filtern (z.B. "Quellen mit Tag nrw", "Zeige kommunale Datenquellen")
  - source_action_data sollte enthalten: tags (Liste), match_mode (all|any)
- suggest_tags: Tags für einen Kontext vorschlagen (z.B. "Welche Tags passen zu Gemeinden in Bayern?")
  - source_action_data sollte enthalten: context (z.B. "Gemeinden Bayern")
- discover_sources: KI-gesteuerte Quellensuche (z.B. "Finde Datenquellen für Bundesliga-Vereine", "Suche Webseiten von Universitäten")
  - source_action_data sollte enthalten: prompt (Suchbegriff), search_depth (quick|standard|deep)

## DataSource Tags (Referenz):
Tags kategorisieren Datenquellen für effiziente Filterung und Kategorie-Zuordnung:
- Bundesländer: nrw, bayern, baden-wuerttemberg, hessen, niedersachsen, schleswig-holstein, etc.
- Länder: de (Deutschland), at (Österreich), ch (Schweiz)
- Typen: kommunal, landkreis, landesebene, oparl, ratsinformation
- Themen: windkraft, solar, bauen, verkehr, umwelt

WICHTIG bei Bestätigungen:
- "Ja, starte die PySis-Analyse" → context_action: "analyze_pysis_execute"
- "Ja, starte die Facet-Anreicherung" → context_action: "enrich_facets_execute"
- "Ja, anreichern und bestehende überschreiben" → context_action: "enrich_facets_execute", context_action_data: {{"overwrite": true}}
- "Ja, analysiere die Daten" / "Ja, extrahiere Facets" → context_action: "analyze_entity_data"
- "Abbrechen" → intent: "CONTEXT_QUERY" (einfach ignorieren)

WICHTIG für Entity-Daten-Analyse:
- Prompts wie "schreibe Pain Points anhand der Verknüpfungen" → context_action: "analyze_entity_data", source_types: ["relations"]
- "analysiere die Dokumente für neue Facets" → context_action: "analyze_entity_data", source_types: ["documents", "extractions"]
- "reichere Facets aus allen Daten an" → context_action: "analyze_entity_data" (alle Quellen)

## Slash Commands:
- /help - Hilfe anzeigen
- /search <query> - Suchen
- /create <type> <details> - Erstellen (→ COMPLEX_WRITE)
- /summary - Zusammenfassung (→ SUMMARIZE)
- /navigate <entity> - Navigation

WICHTIG für DISCUSSION:
- Lange Texte (>300 Zeichen) ohne explizite Suchanfrage → DISCUSSION
- E-Mails, Anforderungsdokumente, Notizen → DISCUSSION
- "hier ist...", "schau dir an...", "was meinst du..." → DISCUSSION
- Texte die nach Analyse/Beratung fragen → DISCUSSION

Analysiere die Nachricht und gib JSON zurück:
{{
  "intent": "QUERY|CONTEXT_QUERY|INLINE_EDIT|COMPLEX_WRITE|NAVIGATION|SUMMARIZE|HELP|BATCH_ACTION|FACET_MANAGEMENT|CONTEXT_ACTION|SOURCE_MANAGEMENT|DISCUSSION|ENTITY_INFO",
  "confidence": 0.0-1.0,
  "extracted_data": {{
    "query_text": "optional: der Suchtext",
    "target_entity": "optional: Ziel-Entity Name",
    "target_type": "optional: entity type",
    "field_to_edit": "optional: welches Feld ändern",
    "new_value": "optional: neuer Wert",
    "help_topic": "optional: Hilfe-Thema",
    "batch_action_type": "optional: add_facet|update_field|add_relation|remove_facet",
    "batch_target_filter": "optional: Filter für Ziel-Entities (z.B. entity_type, location)",
    "batch_action_data": "optional: Daten für die Aktion (z.B. facet_type, value)",
    "facet_action": "optional: create_facet_type|assign_facet_type|list_facet_types|suggest_facet_types",
    "facet_name": "optional: Name des neuen Facet-Typs",
    "facet_description": "optional: Beschreibung",
    "target_entity_types": "optional: Liste von Entity-Typ-Slugs für Zuweisung",
    "context_action": "optional: analyze_pysis|enrich_facets|show_pysis_status|start_crawl|update_entity|create_facet|analyze_entity_data|show_entity_history|add_history_point",
    "context_action_data": "optional: zusätzliche Parameter für die Aktion (z.B. source_types für analyze_entity_data)",
    "source_action": "optional: list_tags|list_sources_by_tag|suggest_tags|discover_sources",
    "source_action_data": "optional: Parameter für Source-Aktionen (z.B. tags, match_mode, context, prompt, search_depth)"
  }},
  "reasoning": "Kurze Begründung"
}}

Benutzer-Nachricht: {message}
"""

RESPONSE_GENERATION_PROMPT = """Du bist ein freundlicher Assistent. Formuliere eine natürliche deutsche Antwort basierend auf den Daten.

Kontext:
- Aktuelle Seite: {context}
- Intent: {intent}
- Ergebnis-Daten: {data}

Regeln:
- Antworte auf Deutsch
- Sei prägnant aber hilfreich
- Nutze die konkreten Daten in deiner Antwort
- Bei vielen Ergebnissen, fasse zusammen
- Schlage Follow-up Fragen vor wenn sinnvoll

Generiere eine Antwort-Nachricht (max 200 Wörter):
"""

DISCUSSION_ANALYSIS_PROMPT = """Du bist ein hilfreicher Assistent für eine Entity-Management-App.

Der Benutzer hat folgenden Text geteilt:
---
{user_text}
---

Aktueller Kontext:
- Route: {current_route}
- Entity-Typ: {entity_type}
- Entity-Name: {entity_name}

Analysiere den Text und:
1. Identifiziere die Art des Inhalts (E-Mail, Notizen, Anforderungen, allgemeine Frage, etc.)
2. Fasse die wichtigsten Punkte zusammen
3. Identifiziere mögliche Aktionen oder nächste Schritte
4. Wenn relevant für die aktuelle Entity, erkläre den Zusammenhang

Antworte auf Deutsch in einem freundlichen, hilfreichen Ton.
Formatiere deine Antwort mit Markdown für bessere Lesbarkeit.

Wenn der Benutzer eine Frage stellt oder um Hilfe bittet, beantworte sie direkt.
"""

FACET_TYPE_SUGGESTION_PROMPT = """Du bist ein Datenarchitekt für eine Entity-Management-App.

Analysiere die Entity-Typen und schlage passende Facet-Typen vor:

Entity-Typen im System:
{entity_types}

Bestehende Facet-Typen:
{existing_facets}

Benutzer-Anfrage: {user_request}

Schlage 3-5 neue, sinnvolle Facet-Typen vor. Für jeden:
1. name: Kurzer, prägnanter Name (z.B. "Pain Point", "Umsatz")
2. description: Klare Beschreibung des Zwecks
3. value_type: text, number, date, oder structured
4. applicable_entity_types: Liste relevanter Entity-Typ-Slugs
5. ai_extraction_enabled: true/false - ob KI-Extraktion sinnvoll ist

Antworte als JSON-Array:
[
  {{
    "name": "...",
    "description": "...",
    "value_type": "...",
    "applicable_entity_types": ["..."],
    "ai_extraction_enabled": true
  }}
]
"""

IMAGE_ANALYSIS_PROMPT = """Du bist ein hilfreicher Assistent für eine Entity-Management-App.

Analysiere das bereitgestellte Bild und:
1. Beschreibe kurz, was du siehst
2. Identifiziere relevante Informationen für das Entity-Management (Namen, Zahlen, Diagramme, etc.)
3. Schlage mögliche Aktionen vor (z.B. Entity erstellen, Daten extrahieren)

Aktueller Kontext:
- Route: {current_route}
- Entity-Typ: {entity_type}
- Entity-Name: {entity_name}

Antworte auf Deutsch, prägnant und strukturiert.
"""

CONTEXT_RESPONSE_PROMPT = """Du bist ein hilfreicher Assistent für eine Entity-Management-App.

Der Benutzer fragt nach Informationen zur aktuellen Entity.

Entity-Daten:
{entity_data}

Benutzer-Frage: {user_question}

Beantworte die Frage basierend auf den Entity-Daten.
- Sei prägnant und informativ
- Nutze die konkreten Daten
- Wenn Informationen fehlen, sage das
- Schlage relevante Follow-up Fragen vor

Antworte auf Deutsch:
"""

SUMMARIZE_PROMPT = """Du bist ein Assistent für Entity-Zusammenfassungen.

Entity: {entity_name} ({entity_type})

Verfügbare Daten:
{entity_data}

Erstelle eine strukturierte Zusammenfassung:
1. **Überblick**: Kurze Beschreibung der Entity
2. **Wichtige Fakten**: Die relevantesten Datenpunkte
3. **Verknüpfungen**: Wichtige Relationen zu anderen Entities
4. **Facet-Highlights**: Auffällige Facet-Werte
5. **Offene Punkte**: Was fehlt oder benötigt Aufmerksamkeit?

Formatiere mit Markdown. Halte es unter 300 Wörtern.
Antworte auf Deutsch:
"""
