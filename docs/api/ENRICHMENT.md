# Entity Data Enrichment

[Zurueck zur Uebersicht](./README.md)

KI-basierte Anreicherung von Facets aus verschiedenen Datenquellen (PySIS, Relationen, Dokumente, Extraktionen).

---

## Uebersicht

Das Entity Data Enrichment System ermoeglicht eine Preview-basierte Facet-Anreicherung. Die KI analysiert verknuepfte Daten und schlaegt neue Facets vor, die vor dem Speichern geprueft und bestaetigt werden koennen.

---

## Endpoints

### GET /v1/entity-data/enrichment-sources
Verfuegbare Datenquellen fuer eine Entity abrufen.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `entity_id` | uuid | Entity-ID (required) |

**Response:**
```json
{
  "pysis": {
    "available": true,
    "count": 15,
    "last_updated": "2025-01-15T14:30:00Z"
  },
  "relations": {
    "count": 8,
    "last_updated": "2025-01-14T10:00:00Z"
  },
  "documents": {
    "count": 23,
    "last_updated": "2025-01-15T09:00:00Z"
  },
  "extractions": {
    "count": 45,
    "last_updated": "2025-01-15T12:00:00Z"
  },
  "existing_facets": 12
}
```

**Felder:**
- `pysis.available`: `true` wenn PySIS-Prozesse verknuepft sind
- `*.count`: Anzahl der verfuegbaren Eintraege pro Quelle
- `*.last_updated`: Zeitstempel der letzten Aktualisierung
- `existing_facets`: Anzahl bereits vorhandener Facet-Werte

---

### POST /v1/entity-data/analyze-for-facets
KI-Analyse fuer neue Facets starten.

**Request Body:**
```json
{
  "entity_id": "uuid",
  "source_types": ["pysis", "relations", "documents", "extractions"]
}
```

**Response:**
```json
{
  "task_id": "uuid",
  "message": "Analyse gestartet",
  "status": "pending"
}
```

**Hinweis:** Die Analyse laeuft als Hintergrund-Task. Status und Ergebnisse koennen ueber `/v1/entity-data/analysis-preview` abgerufen werden.

---

### GET /v1/entity-data/analysis-preview
Preview-Daten nach abgeschlossener Analyse abrufen.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `task_id` | uuid | Task-ID aus `/analyze-for-facets` (required) |

**Response (waehrend Analyse):**
```json
{
  "status": "processing",
  "progress": {
    "current": 3,
    "total": 5,
    "message": "Analysiere Relationen..."
  }
}
```

**Response (nach Abschluss):**
```json
{
  "status": "completed",
  "preview": {
    "new_facets": [
      {
        "facet_type_slug": "pain_point",
        "facet_type_name": "Pain Point",
        "value": {
          "description": "Widerstand gegen geplanten Windpark",
          "severity": "high",
          "type": "citizen_opposition"
        },
        "text": "Buergerinitiative gegen Windpark formiert sich...",
        "confidence": 0.85,
        "source": "relations"
      }
    ],
    "updates": [
      {
        "facet_value_id": "uuid",
        "facet_type_slug": "contact",
        "facet_type_name": "Kontakt",
        "current_value": {
          "name": "Max Mustermann",
          "email": null,
          "phone": null
        },
        "proposed_value": {
          "name": "Max Mustermann",
          "email": "m.mustermann@stadt.de",
          "phone": "+49 123 456789"
        },
        "changes": ["email", "phone"],
        "confidence": 0.92,
        "source": "pysis"
      }
    ]
  },
  "summary": {
    "sources_analyzed": 4,
    "new_facets_count": 5,
    "updates_count": 2
  }
}
```

**Response (bei Fehler):**
```json
{
  "status": "failed",
  "error": "Keine Daten fuer Analyse verfuegbar"
}
```

---

### POST /v1/entity-data/apply-changes
Ausgewaehlte Aenderungen aus der Preview anwenden.

**Request Body:**
```json
{
  "task_id": "uuid",
  "accepted_new_facets": [0, 2, 3],
  "accepted_updates": ["uuid-1", "uuid-3"]
}
```

**Felder:**
- `task_id`: Task-ID der Analyse
- `accepted_new_facets`: Indizes der akzeptierten neuen Facets (aus `preview.new_facets`)
- `accepted_updates`: UUIDs der akzeptierten Updates (aus `preview.updates[].facet_value_id`)

**Response:**
```json
{
  "success": true,
  "created": 3,
  "updated": 2,
  "message": "3 neue Facets erstellt, 2 Facets aktualisiert"
}
```

**Hinweise:**
- Nicht ausgewaehlte Vorschlaege werden verworfen
- Erstellte Facets erhalten `source_type: "AI_ASSISTANT"`
- Updates ueberschreiben nur die geaenderten Felder

---

## AI Task Status

Der Status von Enrichment-Tasks kann auch ueber die allgemeine AI-Tasks API abgerufen werden.

### GET /v1/ai-tasks/status
Status eines KI-Tasks abrufen.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `task_id` | string | Task-ID oder Celery-Task-ID |

**Response:**
```json
{
  "task_id": "uuid",
  "task_type": "ENTITY_DATA_ANALYSIS",
  "status": "processing",
  "progress_current": 3,
  "progress_total": 5,
  "entity_id": "uuid",
  "created_at": "2025-01-15T14:30:00Z",
  "updated_at": "2025-01-15T14:30:05Z",
  "error_message": null
}
```

**Task-Status-Werte:**
| Status | Beschreibung |
|--------|--------------|
| `pending` | Task wartet auf Ausfuehrung |
| `processing` | Task wird gerade ausgefuehrt |
| `completed` | Task erfolgreich abgeschlossen |
| `failed` | Task fehlgeschlagen |
