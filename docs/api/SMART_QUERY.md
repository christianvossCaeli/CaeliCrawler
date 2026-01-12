# Smart Query & Analyse

[Zurueck zur Uebersicht](./README.md)

KI-gestuetzte Abfragen und Schreiboperationen in natuerlicher Sprache.

---

## Architektur

Die Smart Query und der KI-Assistent nutzen eine **einheitliche Executor-Architektur**:

- **Zentrale Ausfuehrung**: Alle Schreiboperationen werden ueber `write_executor.py` ausgefuehrt
- **Konsistenz**: Gleiche Operationen funktionieren identisch in Smart Query und Assistant
- **Ein Service**: FacetType-Erstellung, Batch-Operationen und PySis-Operationen nutzen denselben Code

```
┌──────────────────┐     ┌──────────────────┐
│  Smart Query UI  │     │   KI-Assistant   │
└────────┬─────────┘     └────────┬─────────┘
         │                        │
         ▼                        ▼
┌─────────────────────────────────────────────┐
│         write_executor.py                    │
│   (Unified Command Execution)               │
└─────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│           Database / Services               │
└─────────────────────────────────────────────┘
```

### Handler-Patterns

Es gibt zwei Arten von Operationen, die unterschiedlich implementiert werden:

**1. Registrierte Operationen (Operations Registry)**

Diese nutzen den `@register_operation`-Dekorator und befinden sich in separaten Modul-Dateien unter `operations/`:

| Operation | Modul |
|-----------|-------|
| `analyze_pysis` | `operations/entity_operations.py` |
| `batch_operation` | `operations/entity_operations.py` |
| `batch_delete` | `operations/entity_operations.py` |
| `push_to_pysis` | `operations/entity_operations.py` |
| `start_crawl` | `operations/crawl_operations.py` |
| `create_category_setup` | `operations/category_ops.py` |
| `discover_sources` | `operations/discovery.py` |
| `update_crawl_schedule` | `operations/schedule_ops.py` |
| `create_custom_summary` | `operations/summary_ops.py` |
| ... und weitere |

**2. Direkte Handler (write_executor.py)**

Diese Basis-Operationen sind direkt in `write_executor.py` implementiert:

| Operation | Beschreibung |
|-----------|--------------|
| `create_entity` | Entity erstellen |
| `create_facet` | Facet-Wert hinzufuegen |
| `create_relation` | Beziehung erstellen |
| `update_entity` | Entity aktualisieren |
| `delete_entity` | Entity loeschen (soft-delete) |
| `delete_facet` | Facet-Wert loeschen |
| `combined` | Mehrere Operationen kombiniert |

> **Hinweis fuer Entwickler:** Neue Operationen sollten als registrierte Operationen implementiert werden, um eine klare Trennung und Wiederverwendbarkeit zu gewaehrleisten.

---

## Smart Query Endpoint

### POST /v1/analysis/smart-query
KI-gestuetzte natuerliche Sprache Abfragen ausfuehren.

**Request Body:**
```json
{
  "question": "Zeige mir auf welche kuenftige Events wichtige Entscheider-Personen von Gemeinden gehen",
  "allow_write": false
}
```

**Beispiel-Abfragen:**
- "Welche Buergermeister sprechen auf Windenergie-Konferenzen?"
- "Zeige mir alle Pain Points von Gemeinden in NRW"
- "Wo kann ich Entscheider aus Bayern in den naechsten 90 Tagen treffen?"

**Response:**
```json
{
  "success": true,
  "query_type": "search",
  "interpretation": {
    "intent": "find_event_attendance",
    "filters": {
      "entity_types": ["person"],
      "positions": ["Buergermeister", "Landrat"],
      "time_filter": "future"
    }
  },
  "results": [
    {
      "person_name": "Max Mueller",
      "position": "Buergermeister",
      "municipality": "Gummersbach",
      "event": "Windenergie-Konferenz 2025",
      "event_date": "2025-03-15",
      "confidence": 0.95
    }
  ],
  "summary": "15 Entscheider besuchen in den naechsten 90 Tagen relevante Events"
}
```

---

## Smart Write Endpoint

### POST /v1/analysis/smart-write
Schreib-Kommandos in natuerlicher Sprache mit Preview-Unterstuetzung.

**Workflow:**
1. Sende Kommando mit `preview_only=true` → Erhalte Vorschau
2. Ueberpruefe die Vorschau
3. Sende gleiches Kommando mit `preview_only=false, confirmed=true` → Ausfuehrung

**Request Body:**
```json
{
  "question": "Erstelle eine neue Person Max Mueller, Buergermeister von Gummersbach",
  "preview_only": true,
  "confirmed": false
}
```

**Beispiel-Kommandos:**
- "Erstelle eine Person Hans Schmidt, Landrat von Oberberg"
- "Fuege einen Pain Point fuer Muenster hinzu: Personalmangel in der IT"
- "Verknuepfe Max Mueller mit Gummersbach als Arbeitgeber"
- "Starte Crawls fuer alle Gummersbach Datenquellen"

**Unterstuetzte Operationen:**
| Operation | Beschreibung |
|-----------|--------------|
| `create_entity` | Entity erstellen (Person, Gemeinde, Organisation, Event) |
| `create_entity_type` | Neuen Entity-Typ erstellen |
| `create_facet` | Facet hinzufuegen (Pain Point, Positive Signal, Kontakt) |
| `create_facet_type` | Neuen Facet-Typ erstellen |
| `assign_facet_type` | Facet-Typ einem Entity-Typ zuweisen |
| `create_relation` | Verknuepfung zwischen Entities erstellen |
| `create_category_setup` | Category mit Datenquellen-Verknuepfung erstellen |
| `start_crawl` | Crawl fuer gefilterte Datenquellen starten |
| `batch_operation` | Massenoperation auf mehreren Entities |
| `analyze_pysis` | PySis-Felder analysieren und Facets erstellen |
| `enrich_facets_from_pysis` | Facets mit PySis-Daten anreichern |
| `push_to_pysis` | Facet-Daten nach PySis exportieren |
| `update_entity` | Bestehende Entity aktualisieren |
| `delete_entity` | Entity soft-delete |
| `delete_facet` | Facet-Wert loeschen |
| `export` | Suchergebnisse exportieren |
| `undo` | Letzte Aenderung rueckgaengig machen |
| `get_history` | Aenderungshistorie abrufen |
| `combined` | Mehrere Operationen kombiniert |
| `update_crawl_schedule` | Crawl-Schedule einer Kategorie aktualisieren |
| `create_custom_summary` | Benutzerdefinierte Zusammenfassung erstellen |
| `discover_sources` | KI-gestuetzte automatische Datenquellen-Suche |
| `fetch_and_create_from_api` | Daten von API abrufen und Entities erstellen |
| `batch_delete` | Mehrere Entities oder Facets loeschen |
| `assign_facet_types` | Mehrere Facet-Types Entity-Types zuweisen |
| `link_category_entity_types` | Entity-Typen mit Kategorien verknuepfen |
| `link_existing_category` | Bestehende Kategorie mit Entity-Typen verknuepfen |
| `create_relation_type` | Relation-Typ zwischen Entity-Typen erstellen/verifizieren |
| `add_history_point` | Datenpunkt zu History-Facet hinzufuegen |

**Response (Preview):**
```json
{
  "success": true,
  "mode": "preview",
  "message": "Vorschau der geplanten Aktion",
  "interpretation": {
    "operation": "create_entity",
    "entity_type": "person",
    "entity_data": {
      "name": "Max Mueller",
      "core_attributes": {"position": "Buergermeister"}
    },
    "explanation": "Erstellt eine neue Person mit Position Buergermeister"
  },
  "preview": {
    "operation_de": "Entity erstellen",
    "description": "Erstellt eine neue Person mit Position Buergermeister",
    "details": [
      "Typ: Person",
      "Name: Max Mueller",
      "Position: Buergermeister"
    ]
  },
  "original_question": "Erstelle eine neue Person Max Mueller, Buergermeister von Gummersbach"
}
```

**Response (Execute):**
```json
{
  "success": true,
  "mode": "write",
  "message": "Person 'Max Mueller' wurde erfolgreich erstellt",
  "created_entity": {
    "id": "uuid",
    "name": "Max Mueller",
    "slug": "max-mueller"
  }
}
```

---

## Create Category Setup (Vollautomatisches Daten-Setup)

Die `create_category_setup` Operation erstellt automatisch einen kompletten Daten-Pipeline:

1. **EntityType** - Neuer Entity-Typ mit Felddefinitionen
2. **Category** - Kategorie mit AI-Extraktions-Prompt
3. **AI Source Discovery** - Automatische Suche nach relevanten Datenquellen
4. **Source Linking** - Verknuepfung gefundener Quellen mit der Kategorie

### Request

```json
{
  "question": "Erstelle ein Setup um wöchentlich alle Bundesliga-Ergebnisse der 1. und 2. Bundesliga zu erfassen",
  "preview_only": true
}
```

### Response (Preview)

```json
{
  "success": true,
  "mode": "preview",
  "interpretation": {
    "operation": "create_category_setup",
    "category_setup_data": {
      "name": "Bundesliga Ergebnisse wöchentlich",
      "purpose": "Erfassung der wöchentlichen Ergebnisse der 1. und 2. Bundesliga",
      "search_terms": ["Bundesliga", "1. Bundesliga", "2. Bundesliga", "Ergebnisse"],
      "geographic_filter": {"country": "DE"},
      "time_focus": "future_only",
      "target_entity_types": ["organization", "event"]
    }
  },
  "preview": {
    "operation_de": "Category-Setup erstellen",
    "details": [
      "Name: Bundesliga Ergebnisse wöchentlich",
      "Suchbegriffe: Bundesliga, 1. Bundesliga, 2. Bundesliga, Ergebnisse",
      "→ Erstellt EntityType + Category + verknüpft Datenquellen"
    ]
  }
}
```

### Response (Execute)

```json
{
  "success": true,
  "message": "Erfolgreich erstellt: EntityType 'Bundesliga Ergebnisse', Category 'Bundesliga Ergebnisse', 98 neue Quellen entdeckt, 98 Datenquellen verknüpft",
  "entity_type": "Bundesliga Ergebnisse",
  "category": "Bundesliga Ergebnisse",
  "search_terms": [
    "Bundesliga Ergebnisse",
    "1. Bundesliga Spieltag",
    "2. Bundesliga Ergebnisse",
    "Fußball Bundesliga Tabelle"
  ],
  "discovered_sources": 98,
  "linked_sources": 98,
  "steps": [
    {"step": 1, "message": "Generiere EntityType-Konfiguration...", "success": true},
    {"step": 2, "message": "Generiere Category & AI-Extraktions-Prompt...", "success": true},
    {"step": 3, "message": "Generiere URL-Filter & Crawl-Konfiguration...", "success": true},
    {"step": 4, "message": "Suche automatisch nach relevanten Datenquellen...", "success": true}
  ]
}
```

### Wichtige Hinweise

**Trigger-Phrasen:**
- "Erstelle ein Setup um..."
- "Erstelle ein Setup für..."
- "Richte ein Setup ein für..."

**AI Source Discovery:**
- Wird automatisch ausgefuehrt wenn < 3 passende Quellen existieren
- Nutzt AI zur Websuche nach relevanten Datenquellen
- Gefundene Quellen werden als PENDING erstellt

**Suchbegriff-Generierung:**
- AI generiert automatisch 10-20 relevante Suchbegriffe
- Basiert auf dem angegebenen Thema/Zweck
- Werden fuer AI Source Discovery verwendet

---

## Update Crawl Schedule

> **NEU in v2.2.0:** Die `update_crawl_schedule` Operation ermoeglicht die Aktualisierung von Crawl-Schedules per natuerlicher Sprache.

### Request

```json
{
  "question": "Setze den Crawl-Schedule fuer Windkraft-Monitoring auf alle 15 Minuten",
  "preview_only": false,
  "confirmed": true
}
```

### Identifikation der Kategorie

Die Kategorie kann identifiziert werden durch:
- **ID:** `"...fuer Kategorie 550e8400-e29b-..."`
- **Name:** `"...fuer Windkraft-Monitoring"`
- **Slug:** `"...fuer windkraft-monitoring"`

### Parameter

| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `schedule_cron` | string | Cron-Ausdruck (5 oder 6 Felder) |
| `schedule_enabled` | boolean | Schedule aktivieren/deaktivieren (default: `true`) |

### Beispiel Cron-Ausdruecke

| Ausdruck | Trigger-Phrasen | Bedeutung |
|----------|-----------------|-----------|
| `*/15 * * * *` | "alle 15 Minuten" | Alle 15 Minuten |
| `0 * * * *` | "stuendlich" | Jede volle Stunde |
| `0 */2 * * *` | "alle 2 Stunden" | Alle 2 Stunden |
| `0 8 * * *` | "taeglich um 8 Uhr" | Taeglich um 8:00 |
| `0 9 * * 1` | "woechentlich Montags" | Montags um 9:00 |
| `0 0 1 * *` | "monatlich" | Am 1. jeden Monats |

### Response (Preview)

```json
{
  "success": true,
  "mode": "preview",
  "interpretation": {
    "operation": "update_crawl_schedule",
    "category_id": "uuid",
    "category_name": "Windkraft-Monitoring",
    "schedule_cron": "*/15 * * * *",
    "schedule_enabled": true
  },
  "preview": {
    "operation_de": "Schedule aktualisieren",
    "details": [
      "Kategorie: Windkraft-Monitoring",
      "Neuer Schedule: */15 * * * * (alle 15 Minuten)",
      "Status: aktiviert"
    ],
    "changes": [
      "schedule_cron: '0 8 * * *' → '*/15 * * * *'"
    ]
  }
}
```

### Response (Execute)

```json
{
  "success": true,
  "message": "Schedule fuer 'Windkraft-Monitoring' aktualisiert: */15 * * * *",
  "data": {
    "category_id": "uuid",
    "category_name": "Windkraft-Monitoring",
    "schedule_cron": "*/15 * * * *",
    "schedule_enabled": true,
    "updates": ["schedule_cron: '0 8 * * *' → '*/15 * * * *'"]
  }
}
```

---

## Create Custom Summary

> **NEU in v2.2.0:** Die `create_custom_summary` Operation erstellt benutzerdefinierte KI-Zusammenfassungen basierend auf natuerlichsprachlichen Beschreibungen.

### Request

```json
{
  "question": "Erstelle eine Zusammenfassung aller Windkraft-Pain-Points in NRW",
  "preview_only": false,
  "confirmed": true
}
```

### Trigger-Phrasen

- "Erstelle eine Zusammenfassung..."
- "Erstelle ein Dashboard fuer..."
- "Fasse zusammen..."
- "Erstelle einen Bericht ueber..."

### Parameter

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `prompt` | string | - | Beschreibung (10-2000 Zeichen, KI-interpretiert) |
| `name` | string | KI-generiert | Optionaler Name fuer die Zusammenfassung |
| `schedule` | string | `"auto"` | Aktualisierungs-Schedule |

### Schedule-Optionen

| Option | Beschreibung | Cron |
|--------|--------------|------|
| `auto` | Automatisch bei relevanten Crawls (Standard) | - |
| `hourly` | Stuendlich | `0 * * * *` |
| `daily` | Taeglich um 8 Uhr | `0 8 * * *` |
| `weekly` | Woechentlich Montags | `0 9 * * 1` |
| `monthly` | Monatlich am 1. | `0 0 1 * *` |
| `none` | Nur manuell | - |

### Auto-Trigger Funktion

Wenn `schedule: "auto"` (Standard), wird die Zusammenfassung automatisch aktualisiert, wenn:
- Ein Crawl abgeschlossen wird, der relevante Entity-Typen betrifft
- Die erfassten Daten zu den Widget-Queries der Zusammenfassung passen
- Mindestens eine neue relevante Information gefunden wurde

Dies ermoeglicht "Near-Realtime" Dashboards ohne manuelle Konfiguration.

### Response (Preview)

```json
{
  "success": true,
  "mode": "preview",
  "interpretation": {
    "operation": "create_custom_summary",
    "name": "Windkraft Pain Points NRW",
    "prompt": "Zusammenfassung aller Windkraft-Pain-Points in NRW",
    "schedule": "auto",
    "widgets": [
      {"type": "list", "query": "Pain Points zu Windkraft in NRW"},
      {"type": "chart", "query": "Verteilung nach Gemeinde"},
      {"type": "count", "query": "Anzahl gesamt"}
    ]
  },
  "preview": {
    "operation_de": "Zusammenfassung erstellen",
    "details": [
      "Name: Windkraft Pain Points NRW",
      "3 Widgets werden erstellt",
      "Auto-Update bei relevanten Crawls"
    ]
  }
}
```

### Response (Execute)

```json
{
  "success": true,
  "message": "Zusammenfassung 'Windkraft Pain Points NRW' mit 3 Widgets erstellt (automatische Aktualisierung bei relevanten Crawls)",
  "data": {
    "summary_id": "uuid",
    "name": "Windkraft Pain Points NRW",
    "widgets_created": 3,
    "trigger_type": "auto",
    "auto_trigger_entity_types": ["municipality", "organization"],
    "schedule_cron": null,
    "link": "/custom-summaries/uuid"
  }
}
```

### Beispiele

**Taeglich aktualisierte Zusammenfassung:**
```
"Erstelle eine taegliche Zusammenfassung aller neuen Entscheider-Kontakte"
→ schedule: "daily"
```

**Woechentlicher Report:**
```
"Erstelle einen woechentlichen Bericht ueber Crawl-Aktivitaeten"
→ schedule: "weekly"
```

**Nur manuell:**
```
"Erstelle eine einmalige Zusammenfassung ohne automatische Updates"
→ schedule: "none"
```

---

## Discover Sources (KI-Quellensuche)

> **NEU in v2.2.0:** Die `discover_sources` Operation ermoeglicht die automatische Suche nach relevanten Datenquellen mittels KI.

### Request

```json
{
  "question": "Finde Datenquellen fuer Bundesliga-Ergebnisse",
  "preview_only": false,
  "confirmed": true
}
```

### Trigger-Phrasen

- "Finde Quellen fuer..."
- "Suche Datenquellen zu..."
- "Entdecke automatisch Quellen fuer..."
- "Welche Quellen gibt es zu..."

### Parameter

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `prompt` | string | - | Natuerlichsprachige Beschreibung der gesuchten Quellen (required) |
| `max_results` | integer | 50 | Maximale Anzahl Ergebnisse (1-200) |
| `search_depth` | string | `"standard"` | Suchtiefe: `quick`, `standard`, `deep` |

### Search Depth Optionen

| Option | Beschreibung | Performance |
|--------|--------------|-------------|
| `quick` | Schnelle Suche, weniger Ergebnisse | ~5 Sekunden |
| `standard` | Ausgewogene Suche (empfohlen) | ~15 Sekunden |
| `deep` | Gruendliche Suche, mehr Ergebnisse | ~45 Sekunden |

### Response

```json
{
  "success": true,
  "message": "42 Datenquellen gefunden",
  "data": {
    "sources": [
      {
        "name": "DFL Bundesliga",
        "base_url": "https://www.bundesliga.de/",
        "source_type": "website",
        "tags": ["sport", "fussball", "bundesliga"],
        "confidence": 0.95,
        "metadata": {
          "description": "Offizielle Bundesliga-Website"
        }
      }
    ],
    "search_strategy": {
      "queries_executed": 5,
      "sources_analyzed": 120
    },
    "stats": {
      "total_found": 42,
      "duplicates_removed": 15,
      "execution_time_ms": 14523
    },
    "warnings": []
  }
}
```

---

## Batch Operations (Massenoperationen)

> **NEU in v2.2.0:** Batch-Operationen ermoeglichen Aenderungen an mehreren Entities gleichzeitig.

### Batch Operation (Massenbearbeitung)

Bearbeitet mehrere Entities gleichzeitig mit derselben Operation.

```json
{
  "question": "Fuege allen Gemeinden in NRW den Tag 'Kernmarkt' hinzu",
  "preview_only": true
}
```

**Unterstuetzte Action-Types:**

| Action | Beschreibung |
|--------|--------------|
| `add_facet` | Facet zu allen gefilterten Entities hinzufuegen |
| `update_field` | Feld in core_attributes aktualisieren |
| `remove_facet` | Facets von gefilterten Entities entfernen |

**Command-Struktur:**

```json
{
  "operation": "batch_operation",
  "batch_data": {
    "action_type": "add_facet",
    "target_filter": {
      "entity_type": "territorial_entity",
      "location_filter": "Nordrhein-Westfalen",
      "additional_filters": {
        "category": "municipality"
      }
    },
    "action_data": {
      "facet_type": "tag",
      "facet_value": {
        "name": "Kernmarkt",
        "description": "Priorisierte Region"
      }
    }
  },
  "dry_run": true
}
```

**Response (Preview):**

```json
{
  "success": true,
  "message": "156 Entities wuerden bearbeitet werden (Vorschau)",
  "data": {
    "affected_count": 156,
    "preview": [
      {
        "entity_id": "uuid",
        "entity_name": "Gummersbach",
        "entity_type": "territorial_entity"
      }
    ],
    "dry_run": true
  }
}
```

### Batch Delete (Massenloeschung)

Loescht mehrere Entities oder Facets basierend auf Filtern.

```json
{
  "question": "Loesche alle Test-Entities vom Typ 'demo'",
  "preview_only": true
}
```

**Trigger-Phrasen:**

- "Loesche alle..."
- "Entferne alle Facets von..."
- "Bereinige alle..."

**Delete-Types:**

| Type | Beschreibung |
|------|--------------|
| `entities` | Soft-Delete von Entities (is_active = false) |
| `facets` | Hard-Delete von Facet-Values |

**Command-Struktur:**

```json
{
  "operation": "batch_delete",
  "delete_data": {
    "delete_type": "facets",
    "target_filter": {
      "entity_type": "territorial_entity",
      "location_filter": "Bayern",
      "facet_type": "pain_point",
      "date_before": "2024-01-01"
    },
    "reason": "Veraltete Daten bereinigen"
  },
  "dry_run": true
}
```

**Filter-Optionen:**

| Filter | Beschreibung |
|--------|--------------|
| `entity_type` | Entity-Typ Slug |
| `location_filter` | Admin-Level-1 (Bundesland) |
| `facet_type` | Facet-Typ Slug (nur bei `delete_type: facets`) |
| `date_before` | Nur Facets vor diesem Datum (YYYY-MM-DD) |
| `additional_filters` | Zusaetzliche core_attributes Filter |

**Response (Preview):**

```json
{
  "success": true,
  "message": "89 Facets wuerden geloescht werden (Vorschau)",
  "data": {
    "affected_count": 89,
    "preview": [
      {
        "type": "facet",
        "id": "uuid",
        "entity_id": "uuid",
        "facet_type": "pain_point",
        "text": "Personalmangel im Bauamt..."
      }
    ],
    "dry_run": true
  }
}
```

**Wichtige Hinweise:**

- `dry_run: true` (default) zeigt nur eine Vorschau
- Entities werden soft-deleted (is_active = false)
- Facets werden permanent geloescht
- Maximal 1000 Eintraege pro Operation

---

## Assign Facet Types (Facet-Typ-Zuweisung)

> **NEU in v2.2.0:** Weist Facet-Typen mehreren Entity-Typen zu oder umgekehrt.

### Request

```json
{
  "question": "Aktiviere Pain Points fuer Windpark und Solarpark Entity-Typen",
  "preview_only": false,
  "confirmed": true
}
```

### Trigger-Phrasen

- "Aktiviere [Facet] fuer [Entity-Typen]..."
- "Weise [Facet-Typen] dem Entity-Typ [X] zu..."
- "Erlaube [Facets] fuer..."

### Zwei Formate

**Format 1: Ein Facet zu mehreren Entity-Typen**

```json
{
  "operation": "assign_facet_types",
  "assign_data": {
    "facet_type_slug": "pain_point",
    "target_entity_type_slugs": ["windpark", "solarpark", "biogas_anlage"]
  }
}
```

**Format 2: Mehrere Facets zu einem Entity-Typ**

```json
{
  "operation": "assign_facet_types",
  "assign_data": {
    "entity_type_slug": "windpark",
    "facet_type_slugs": ["pain_point", "contact", "positive_signal"],
    "auto_detect": false
  }
}
```

### Parameter

| Parameter | Beschreibung |
|-----------|--------------|
| `facet_type_slug` | Einzelner Facet-Typ (Format 1) |
| `target_entity_type_slugs` | Liste von Ziel-Entity-Typen (Format 1) |
| `entity_type_slug` | Einzelner Entity-Typ (Format 2) |
| `facet_type_slugs` | Liste von Facet-Typen (Format 2) |
| `auto_detect` | Wenn true, werden alle aktiven Facet-Typen zugewiesen |

### Response

```json
{
  "success": true,
  "message": "Facet 'pain_point' fuer 3 Entity-Types aktiviert",
  "data": {
    "assigned_facets": ["pain_point"],
    "assigned_to_entity_types": ["windpark", "solarpark", "biogas_anlage"]
  }
}
```

---

## Beispiele abrufen

### GET /v1/analysis/smart-query/examples
Beispiele fuer Smart Query abrufen.

**Response:**
```json
{
  "read_examples": [
    {
      "question": "Zeige mir auf welche kuenftige Events wichtige Entscheider-Personen von Gemeinden gehen",
      "description": "Findet alle Personen mit Positionen wie Buergermeister, Landrat etc. und deren zukuenftige Event-Teilnahmen"
    }
  ],
  "write_examples": [
    {
      "question": "Erstelle eine neue Person Max Mueller, Buergermeister von Gummersbach",
      "description": "Erstellt eine Person-Entity mit Position 'Buergermeister'"
    }
  ],
  "supported_filters": {
    "time": ["kuenftig", "vergangen", "zukuenftig", "in den naechsten X Tagen/Monaten"],
    "positions": ["Buergermeister", "Landrat", "Dezernent", "Entscheider", "Amtsleiter"],
    "entity_types": ["Person", "Gemeinde", "Event", "Organisation"],
    "facet_types": ["Pain Points", "Positive Signale", "Event-Teilnahmen", "Kontakte"]
  },
  "write_operations": {
    "create_entity": ["Erstelle", "Neue/r/s", "Anlegen"],
    "create_facet": ["Fuege hinzu", "Neuer Pain Point", "Neues Positive Signal"],
    "create_relation": ["Verknuepfe", "Verbinde", "arbeitet fuer", "ist Mitglied von"]
  }
}
```

---

## Erweiterte Query-Syntax

### Boolean-Operatoren (AND/OR)

Smart Query unterstuetzt logische Verknuepfungen fuer komplexe Filter.

**OR-Verknuepfung fuer Orte:**
```
"Zeige Buergermeister in NRW oder Bayern"
→ filters.admin_level_1: ["Nordrhein-Westfalen", "Bayern"]
→ filters.logical_operator: "OR"
```

**AND-Verknuepfung fuer Facets:**
```
"Gemeinden mit Pain Points UND Positive Signals"
→ facet_types: ["pain_point", "positive_signal"]
→ facet_logical_operator: "AND"
```

**Unterstuetzte Schluesselwoerter:**
| Deutsch | Englisch | Operator |
|---------|----------|----------|
| und, sowie | and | AND |
| oder | or | OR |

### Negation (NOT/OHNE)

Ausschluss-Filter mit Negation:

```
"Gemeinden OHNE Pain Points"
→ negative_facet_types: ["pain_point"]

"Personen NICHT in Bayern"
→ negative_location_filter: { admin_level_1: "Bayern" }
```

### Datumsbereich-Filter

Praezise Zeitfilter fuer Events und andere zeitbasierte Daten.

```
"Events zwischen 1. Januar und 31. Maerz 2025"
→ date_range: { start: "2025-01-01", end: "2025-03-31" }
```

### Aggregations-Queries

Statistische Abfragen fuer Zusammenfassungen und Analysen.

**Request:**
```json
{
  "question": "Durchschnittliche Anzahl Pain Points pro Gemeinde in NRW",
  "allow_write": false
}
```

**Response:**
```json
{
  "success": true,
  "query_type": "aggregate",
  "aggregate_function": "AVG",
  "results": [
    {
      "label": "Nordrhein-Westfalen",
      "value": 3.2,
      "count": 156
    }
  ],
  "summary": "Gemeinden in NRW haben durchschnittlich 3.2 Pain Points"
}
```

**Unterstuetzte Aggregations-Funktionen:**
| Funktion | Beschreibung | Beispiel-Trigger |
|----------|--------------|------------------|
| COUNT | Anzahl zaehlen | "Wie viele..." |
| AVG | Durchschnitt | "Durchschnittlich...", "Mittel..." |
| SUM | Summe | "Summe...", "Gesamt..." |
| MIN | Minimum | "Minimum...", "Mindestens..." |
| MAX | Maximum | "Maximum...", "Hoechstens..." |

### Multi-Hop Relationen

Komplexe Abfragen ueber mehrere Entity-Beziehungen hinweg.

```json
{
  "question": "Zeige Personen, deren Gemeinden Pain Points haben",
  "allow_write": false
}
```

**Maximale Tiefe:** 3 Relation-Hops (aus Performance-Gruenden)

---

## Intelligente Fehlerbehandlung

Bei fehlerhaften oder mehrdeutigen Queries liefert das System automatische Korrekturvorschlaege.

**Beispiel: Tippfehler in geografischem Filter**

Request:
```json
{
  "question": "Zeige Gemeinden in NWR"
}
```

Response (mit Suggestions):
```json
{
  "success": true,
  "query_type": "search",
  "results": [],
  "suggestions": [
    {
      "type": "geographic",
      "original": "NWR",
      "suggestion": "NRW (Nordrhein-Westfalen)",
      "corrected_query": "Zeige Gemeinden in NRW",
      "message": "Meinten Sie 'NRW'?"
    }
  ]
}
```

---

## Link Category Entity Types

> **NEU in v2.2.0:** Verknuepft Entity-Typen mit Kategorien fuer die Datenextraktion.

### Request

```json
{
  "question": "Verknuepfe Windpark und Solarpark Entity-Typen mit der Kategorie Energie",
  "preview_only": false,
  "confirmed": true
}
```

### Command-Struktur

```json
{
  "operation": "link_category_entity_types",
  "link_data": {
    "category_slug": "energie",
    "entity_type_slugs": ["windpark", "solarpark"],
    "auto_detect": false
  }
}
```

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `category_slug` | string | - | Slug der Ziel-Kategorie |
| `entity_type_slugs` | string[] | - | Liste der zu verknuepfenden Entity-Type Slugs |
| `auto_detect` | boolean | false | Wenn true, mit allen Kategorien verknuepfen |

### Response

```json
{
  "success": true,
  "message": "2 Entity-Types mit 1 Kategorien verknuepft",
  "data": {
    "linked_entity_types": ["windpark", "solarpark"],
    "linked_categories": ["energie"]
  }
}
```

---

## Create Relation Type

> **NEU in v2.2.0:** Erstellt oder verifiziert Beziehungstypen zwischen Entity-Typen.

### Request

```json
{
  "question": "Erstelle eine 'arbeitet-fuer' Relation von Person zu Organisation",
  "preview_only": false,
  "confirmed": true
}
```

### Command-Struktur

```json
{
  "operation": "create_relation_type",
  "relation_type_data": {
    "relation_type": "works_for",
    "source_type": "person",
    "target_type": "organization"
  }
}
```

| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `relation_type` | string | Slug des Relation-Typs |
| `source_type` | string | Slug des Quell-Entity-Typs |
| `target_type` | string | Slug des Ziel-Entity-Typs |

### Response

```json
{
  "success": true,
  "message": "Relation 'Arbeitet fuer' (Person → Organisation) verifiziert",
  "data": {
    "relation_type_slug": "works_for",
    "source_type_slug": "person",
    "target_type_slug": "organization"
  }
}
```

---

## Add History Point (History-Facets)

> **NEU in v2.2.0:** Fuegt Datenpunkte zu zeitreihenbasierten History-Facets hinzu.

History-Facets speichern Zeitreihen-Daten wie Mitgliederzahlen, Leistungswerte oder andere metrische Entwicklungen.

### Request

```json
{
  "question": "Fuge Mitgliederzahl 1500 fuer Verein Gummersbach am 01.01.2025 hinzu",
  "preview_only": false,
  "confirmed": true
}
```

### Command-Struktur

```json
{
  "operation": "add_history_point",
  "history_point_data": {
    "entity_name": "Verein Gummersbach",
    "facet_type": "member_count",
    "value": 1500,
    "recorded_at": "2025-01-01T00:00:00Z",
    "track_key": "default",
    "note": "Jahresbeginn"
  }
}
```

| Parameter | Typ | Required | Beschreibung |
|-----------|-----|----------|--------------|
| `entity_id` | uuid | * | Entity-ID (alternativ zu entity_name) |
| `entity_name` | string | * | Entity-Name (alternativ zu entity_id) |
| `facet_type` | string | ja | Slug des History-Facet-Typs |
| `value` | number | ja | Numerischer Wert |
| `recorded_at` | datetime | nein | Zeitpunkt (default: jetzt) |
| `track_key` | string | nein | Track-Schluessel fuer Multi-Track Facets (default: "default") |
| `note` | string | nein | Optionale Notiz zum Datenpunkt |

\* Entweder `entity_id` oder `entity_name` erforderlich

### Response

```json
{
  "success": true,
  "message": "Datenpunkt fuer 'Verein Gummersbach' hinzugefuegt: 1500 am 01.01.2025",
  "created_items": [
    {
      "type": "history_point",
      "id": "uuid",
      "entity_id": "uuid",
      "facet_type": "member_count",
      "value": 1500
    }
  ]
}
```

### Wichtige Hinweise

- Der Facet-Typ muss `value_type: "history"` haben
- Werte werden als Float gespeichert
- Mehrere Tracks pro Entity moeglich (z.B. verschiedene Metriken)
- Zeitreihen koennen spaeter fuer Trend-Analysen verwendet werden

---

## Push to PySis (PySis Export)

> **NEU in v2.2.0:** Exportiert Facet-Daten zu PySis fuer CRM-Integration.

### Request

```json
{
  "question": "Exportiere alle Facets von Gummersbach nach PySis",
  "preview_only": false,
  "confirmed": true
}
```

### Command-Struktur

```json
{
  "operation": "push_to_pysis",
  "pysis_data": {
    "entity_name": "Gummersbach",
    "process_id": "optional-process-uuid"
  }
}
```

| Parameter | Typ | Required | Beschreibung |
|-----------|-----|----------|--------------|
| `entity_id` | uuid | * | Entity-ID (alternativ zu entity_name) |
| `entity_name` | string | * | Entity-Name (alternativ zu entity_id) |
| `process_id` | string | nein | Spezifischer PySis-Prozess (default: alle aktiven) |

\* Entweder `entity_id` oder `entity_name` erforderlich

### Response

```json
{
  "success": true,
  "message": "2 Facet-Werte nach PySis synchronisiert",
  "data": {
    "synced_count": 2
  }
}
```

---

## Get History (Aenderungshistorie)

> **NEU in v2.2.0:** Ruft die Aenderungshistorie einer Entity ab.

### Request

```json
{
  "question": "Zeige mir die letzten Aenderungen an Gummersbach",
  "preview_only": false
}
```

### Command-Struktur

```json
{
  "operation": "get_history",
  "history_data": {
    "entity_name": "Gummersbach",
    "entity_type": "Entity",
    "limit": 10
  }
}
```

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `entity_id` | uuid | - | Entity-ID (alternativ zu entity_name) |
| `entity_name` | string | - | Entity-Name (alternativ zu entity_id) |
| `entity_type` | string | `"Entity"` | Typ der Entity (`Entity`, `FacetValue`) |
| `limit` | int | 10 | Maximale Anzahl der Historie-Eintraege |

### Response

```json
{
  "success": true,
  "message": "Änderungshistorie für 'Gummersbach': 5 Einträge",
  "data": {
    "history": [
      {
        "id": "uuid",
        "changed_at": "2025-01-15T14:30:00Z",
        "changed_by": "user@example.com",
        "change_type": "UPDATE",
        "old_values": {"name": "Alt"},
        "new_values": {"name": "Neu"}
      }
    ]
  }
}
```

---

## Link Existing Category

> **NEU in v2.2.0:** Verknuepft zu einer bestehenden Kategorie per Slug.

Diese Operation wird verwendet, wenn die KI auf eine existierende Kategorie verweist, anstatt eine neue zu erstellen.

### Command-Struktur

```json
{
  "operation": "link_existing_category",
  "link_data": {
    "category_slug": "windkraft-monitoring"
  }
}
```

| Parameter | Typ | Required | Beschreibung |
|-----------|-----|----------|--------------|
| `category_slug` | string | ja | Slug der bestehenden Kategorie |

### Response

```json
{
  "success": true,
  "message": "Kategorie 'Windkraft-Monitoring' verknüpft",
  "data": {
    "category_id": "uuid",
    "category_slug": "windkraft-monitoring",
    "category_name": "Windkraft-Monitoring"
  }
}
```

---

## Fetch and Create from API

> **NEU in v2.2.0:** Ruft Daten von externen APIs ab und erstellt Entities.

Unterstuetzt:
- **Wikidata SPARQL** Queries (DE/AT/GB Gemeinden, Bundeslaender, Raete)
- **REST APIs** mit vordefinierten Templates
- **Automatische Parent-Entity-Erstellung** fuer Hierarchien
- **Entity-Matching** zur Verknuepfung mit bestehenden Entities

### Request

```json
{
  "question": "Importiere alle deutschen Bundeslaender von Wikidata",
  "preview_only": false,
  "confirmed": true
}
```

### Command-Struktur

```json
{
  "operation": "fetch_and_create_from_api",
  "fetch_and_create_data": {
    "api_type": "wikidata",
    "template": "de_states",
    "entity_type": "territorial_entity",
    "parent_type": "country",
    "create_entity_type": true,
    "match_existing": true
  }
}
```

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `api_type` | string | - | API-Typ (`wikidata`, `rest`) |
| `template` | string | - | Template-Name (z.B. `de_states`, `de_municipalities`) |
| `entity_type` | string | - | Slug des Ziel-Entity-Typs |
| `parent_type` | string | - | Slug des Parent-Entity-Typs (fuer Hierarchien) |
| `create_entity_type` | boolean | `false` | Entity-Typ erstellen falls nicht vorhanden |
| `entity_type_config` | object | - | Konfiguration fuer neuen Entity-Typ |
| `match_existing` | boolean | `true` | Mit bestehenden Entities matchen |

### Verfuegbare Wikidata-Templates

| Template | Beschreibung |
|----------|--------------|
| `de_states` | Deutsche Bundeslaender |
| `de_municipalities` | Deutsche Gemeinden (mit Bundesland-Parent) |
| `at_states` | Oesterreichische Bundeslaender |
| `gb_councils` | Britische Councils |

### Response

```json
{
  "success": true,
  "message": "16 Bundesländer importiert, 0 existierten bereits",
  "data": {
    "created_count": 16,
    "existing_count": 0,
    "error_count": 0,
    "total_fetched": 16,
    "entity_type": "territorial_entity",
    "parent_type": "country",
    "matched_count": 0,
    "warnings": []
  }
}
```

---

## Analysis Templates

### GET /v1/analysis/templates
Analyse-Templates auflisten.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `is_active` | boolean | Nur aktive Templates |
| `primary_entity_type_slug` | string | Filter nach primaeren Entity-Typ |

### GET /v1/analysis/templates/{id}
Template abrufen.

### GET /v1/analysis/templates/by-slug/{slug}
Template per Slug.

### POST /v1/analysis/templates
Template erstellen.

### PUT /v1/analysis/templates/{id}
Template aktualisieren.

### DELETE /v1/analysis/templates/{id}
Template loeschen.

---

## Analysis Endpoints

### GET /v1/analysis/overview
Analyse-Uebersicht.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `template_slug` | string | Analyse-Template |
| `entity_type_slug` | string | Entity-Typ |
| `category_id` | uuid | Filter nach Kategorie |
| `parent_entity_id` | uuid | Filter nach Parent-Entity |
| `time_filter` | string | Zeitfilter |

### GET /v1/analysis/report/{entity_id}
Detaillierter Analyse-Report.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `template_slug` | string | Analyse-Template |
| `include_facets` | boolean | Facet-Details einschliessen |
| `include_relations` | boolean | Relations einschliessen |

### GET /v1/analysis/stats
Aggregierte Statistiken.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `entity_type_slug` | string | Filter nach Entity-Typ |
| `category_id` | uuid | Filter nach Kategorie |

**Response:**
```json
{
  "total_entities": 500,
  "total_facet_values": 5000,
  "verified_count": 2500,
  "total_relations": 1200,
  "by_facet_type": [
    {
      "facet_type_slug": "pain_point",
      "count": 3000,
      "verified": 1500,
      "avg_confidence": 0.78
    }
  ]
}
```
