# PySis Integration

[Zurueck zur Uebersicht](./README.md)

PySis ist eine optionale Integration fuer externes Prozess-Management. Erfordert Azure AD Konfiguration.

---

## Admin Endpoints

### GET /admin/pysis/test-connection
Verbindung testen.

**Response:**
```json
{
  "connected": true,
  "api_version": "1.0",
  "user": "service-account"
}
```

---

## Templates

### GET /admin/pysis/templates
Feld-Templates auflisten.

### POST /admin/pysis/templates
Template erstellen.

### GET /admin/pysis/templates/{template_id}
Template abrufen.

### PUT /admin/pysis/templates/{template_id}
Template aktualisieren.

### DELETE /admin/pysis/templates/{template_id}
Template loeschen.

---

## Prozesse

### GET /admin/pysis/available-processes
Verfuegbare Prozesse von PySis.

### GET /admin/pysis/locations/{location_name}/processes
Prozesse einer Location.

### POST /admin/pysis/locations/{location_name}/processes
Prozess fuer Location erstellen.

### GET /admin/pysis/processes/{process_id}
Prozess-Details.

### PUT /admin/pysis/processes/{process_id}
Prozess aktualisieren.

### DELETE /admin/pysis/processes/{process_id}
Prozess loeschen.

### POST /admin/pysis/processes/{process_id}/apply-template
Template auf Prozess anwenden.

### POST /admin/pysis/processes/{process_id}/generate
Felder KI-generieren.

### POST /admin/pysis/processes/{process_id}/sync/pull
Daten von PySis laden.

### POST /admin/pysis/processes/{process_id}/sync/push
Daten zu PySis senden.

**Request Body (optional):**
```json
{
  "field_ids": ["uuid1", "uuid2"]
}
```

| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `field_ids` | array[uuid] | Optional: Nur bestimmte Felder synchronisieren. Wenn nicht angegeben, werden alle Felder mit `needs_push=true` synchronisiert. |

**Response:**
```json
{
  "success": true,
  "fields_synced": 5,
  "synced_at": "2024-01-15T10:30:00Z",
  "errors": []
}
```

---

## Felder

### GET /admin/pysis/processes/{process_id}/fields
Felder eines Prozesses.

### POST /admin/pysis/processes/{process_id}/fields
Feld hinzufuegen.

### PUT /admin/pysis/fields/{field_id}
Feld aktualisieren.

### PUT /admin/pysis/fields/{field_id}/value
Feld-Wert setzen.

### DELETE /admin/pysis/fields/{field_id}
Feld loeschen.

### POST /admin/pysis/fields/{field_id}/generate
KI-Vorschlag fuer Feld generieren.

### POST /admin/pysis/fields/{field_id}/accept-ai
KI-Vorschlag akzeptieren.

### POST /admin/pysis/fields/{field_id}/reject-ai
KI-Vorschlag ablehnen.

### POST /admin/pysis/fields/{field_id}/sync/push
Feld zu PySis senden.

### GET /admin/pysis/fields/{field_id}/history
Feld-Aenderungshistorie.

### POST /admin/pysis/fields/{field_id}/restore/{history_id}
Version wiederherstellen.

---

## PySis-Facets API (Public v1)

Diese Endpunkte ermoeglichen die Integration von PySis-Daten mit dem Facet-System. Sie koennen sowohl ueber die UI als auch ueber den KI-Assistenten genutzt werden.

### POST /v1/pysis-facets/analyze
PySis-Felder analysieren und neue Facets erstellen.

Startet einen Hintergrund-Task der:
1. PySis-Felder der Entity laedt
2. Aktive FacetTypes mit AI-Extraktion identifiziert
3. Mit KI relevante Informationen extrahiert
4. Neue FacetValues erstellt

**Request Body:**
```json
{
  "entity_id": "uuid",
  "process_id": "uuid",
  "include_empty": false,
  "min_confidence": 0.0
}
```

| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `entity_id` | UUID | Entity-ID (required) |
| `process_id` | UUID | Spezifischer PySis-Prozess (optional) |
| `include_empty` | boolean | Auch leere Felder analysieren (default: false) |
| `min_confidence` | float | Minimale Konfidenz 0.0-1.0 (default: 0.0) |

**Response:**
```json
{
  "success": true,
  "task_id": "uuid",
  "message": "PySis-Facet-Analyse gestartet"
}
```

**Fehler:**
- `400 Bad Request` - Entity nicht gefunden oder keine PySis-Daten vorhanden

### POST /v1/pysis-facets/enrich
Bestehende Facets mit PySis-Daten anreichern.

Startet einen Hintergrund-Task der:
1. Bestehende FacetValues der Entity laedt
2. PySis-Felder sammelt
3. Mit KI fehlende Felder in FacetValues ergaenzt
4. FacetValues aktualisiert

**Request Body:**
```json
{
  "entity_id": "uuid",
  "facet_type_id": "uuid",
  "overwrite": false
}
```

| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `entity_id` | UUID | Entity-ID (required) |
| `facet_type_id` | UUID | Nur diesen FacetType anreichern (optional) |
| `overwrite` | boolean | Bestehende Werte ueberschreiben (default: false) |

**Response:**
```json
{
  "success": true,
  "task_id": "uuid",
  "message": "Facet-Anreicherung gestartet"
}
```

### GET /v1/pysis-facets/preview
Vorschau einer Operation anzeigen.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `entity_id` | UUID | Entity-ID (required) |
| `operation` | string | `analyze` oder `enrich` (required) |

**Response:**
```json
{
  "can_execute": true,
  "message": "Operation kann ausgefuehrt werden",
  "operation": "analyze",
  "entity_name": "Gemeinde Gummersbach",
  "pysis_processes": 2,
  "pysis_fields": 45,
  "fields_with_values": 38,
  "facet_types_count": 5,
  "facet_values_count": 12,
  "facet_types": [
    {"slug": "pain_point", "name": "Pain Point", "count": 5},
    {"slug": "contact", "name": "Kontakt", "count": 3}
  ]
}
```

### GET /v1/pysis-facets/status
PySis-Status einer Entity abrufen.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `entity_id` | UUID | Entity-ID (required) |

**Response:**
```json
{
  "has_pysis": true,
  "entity_name": "Gemeinde Gummersbach",
  "total_processes": 2,
  "total_fields": 45,
  "processes": [
    {
      "id": "uuid",
      "name": "Windenergie-Projekt A",
      "fields_count": 25,
      "fields_with_values": 20
    }
  ],
  "recent_tasks": [
    {
      "task_id": "uuid",
      "operation": "analyze",
      "status": "completed",
      "created_at": "2025-01-15T14:30:00Z"
    }
  ]
}
```

### GET /v1/pysis-facets/summary
Kurzuebersicht fuer UI.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `entity_id` | UUID | Entity-ID (required) |

**Response:**
```json
{
  "has_pysis": true,
  "process_count": 2,
  "field_count": 45,
  "last_sync": "2025-01-15T14:30:00Z"
}
```

**Quellen-Markierung:**
Erstellte FacetValues erhalten `source_url: "pysis://process/{process_id}"` zur Nachverfolgung.

---

## KI-Assistent Integration

Die PySis-Facets Operationen koennen auch ueber den KI-Assistenten ausgefuehrt werden:

**Natuerliche Sprache (auf Entity-Detailseite):**
- "Analysiere PySis fuer Facets" → POST /v1/pysis-facets/analyze
- "Reichere Facets an" → POST /v1/pysis-facets/enrich
- "Zeig PySis-Status" → GET /v1/pysis-facets/status

**Smart Query (mit expliziter Entity):**
- "Analysiere PySis fuer Gummersbach" → POST /v1/pysis-facets/analyze
- "Ergaenze Facets fuer Muenchen mit PySis-Daten" → POST /v1/pysis-facets/enrich
