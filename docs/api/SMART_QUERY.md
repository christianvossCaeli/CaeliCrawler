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
| `analyze_pysis_for_facets` | PySis-Felder analysieren und Facets erstellen |
| `enrich_facets_from_pysis` | Facets mit PySis-Daten anreichern |
| `update_entity` | Bestehende Entity aktualisieren |
| `delete_entity` | Entity soft-delete |
| `delete_facet` | Facet-Wert loeschen |
| `export_query_result` | Suchergebnisse exportieren |
| `undo_change` | Letzte Aenderung rueckgaengig machen |
| `combined` | Mehrere Operationen kombiniert |

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
