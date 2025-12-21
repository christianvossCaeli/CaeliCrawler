# Public Data API

[Zurueck zur Uebersicht](./README.md)

Public API (v1/data) fuer extrahierte Daten, Dokumente, Gemeinden-Reports und Export.

---

## Extrahierte Daten

### GET /v1/data
Extrahierte Daten abrufen.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `category_id` | uuid | Filter nach Kategorie |
| `source_id` | uuid | Filter nach Quelle |
| `country` | string | Filter nach Land |
| `location_name` | string | Filter nach Ort |
| `min_confidence` | float | Min. Konfidenz (0.0-1.0) |
| `verified_only` | boolean | Nur verifizierte |
| `extraction_type` | string | Filter nach Extraktionstyp |
| `human_verified` | boolean | Nur manuell verifizierte |
| `page` | int | Seite (default: 1) |
| `per_page` | int | Eintraege pro Seite (default: 20) |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "document_id": "uuid",
      "document_url": "https://...",
      "document_title": "Beschluss 2025/01",
      "source_id": "uuid",
      "source_name": "Stadt Musterstadt",
      "category_name": "Windenergie",
      "confidence": 0.85,
      "is_verified": false,
      "final_content": {
        "topic": "Windkraftanlage Genehmigung",
        "summary": "Der Rat hat beschlossen...",
        "is_relevant": true,
        "municipality": "Musterstadt",
        "pain_points": ["Abstandsregelungen", "Laermschutz"],
        "positive_signals": ["Grundsaetzliche Zustimmung"],
        "decision_makers": [
          {"name": "Max Mustermann", "role": "Buergermeister"}
        ],
        "sentiment": "neutral",
        "relevanz": "hoch",
        "outreach_recommendation": {
          "priority": "high",
          "reason": "Aktive Entscheidungsphase"
        }
      },
      "extracted_at": "2025-01-15T14:30:00Z"
    }
  ],
  "total": 1234
}
```

### GET /v1/data/stats
Extraktions-Statistiken.

**Response:**
```json
{
  "total_extractions": 1234,
  "verified_count": 456,
  "high_confidence_count": 890,
  "avg_confidence": 0.78,
  "by_category": [
    {"category": "Windenergie", "count": 800},
    {"category": "Solarenergie", "count": 434}
  ]
}
```

### GET /v1/data/locations
Orte mit extrahierten Daten.

### GET /v1/data/countries
Laender mit extrahierten Daten.

---

## Dokumente

### GET /v1/data/documents
Dokumente auflisten.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `source_id` | uuid | Filter nach Quelle |
| `category_id` | uuid | Filter nach Kategorie |
| `processing_status` | string | PENDING, PROCESSING, COMPLETED, FILTERED, FAILED |
| `location_name` | string | Filter nach Ort |
| `search` | string | Volltextsuche |
| `page` | int | Seite (default: 1) |
| `per_page` | int | Eintraege pro Seite (default: 20) |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "url": "https://...",
      "title": "Beschluss_2025_01.pdf",
      "file_type": "application/pdf",
      "file_size": 245000,
      "processing_status": "COMPLETED",
      "processing_error": null,
      "discovered_at": "2025-01-15T10:00:00Z",
      "downloaded_at": "2025-01-15T10:01:00Z",
      "processed_at": "2025-01-15T10:02:00Z",
      "extraction_count": 1
    }
  ],
  "total": 5000
}
```

### GET /v1/data/documents/{document_id}
Dokument-Details.

**Response:**
```json
{
  "id": "uuid",
  "url": "https://...",
  "title": "Beschluss_2025_01.pdf",
  "file_type": "application/pdf",
  "file_size": 245000,
  "page_count": 5,
  "raw_text": "Volltext des Dokuments...",
  "processing_status": "COMPLETED",
  "source_name": "Stadt Musterstadt",
  "category_name": "Windenergie",
  "extractions": [
    {
      "id": "uuid",
      "confidence": 0.85,
      "final_content": {...}
    }
  ]
}
```

### GET /v1/data/documents/locations
Orte mit Dokumenten.

### GET /v1/data/search
Volltextsuche.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `q` | string | Suchbegriff |
| `category_id` | uuid | Filter |
| `limit` | int | Max. Ergebnisse |

**Response:**
```json
{
  "results": [
    {
      "document_id": "uuid",
      "title": "...",
      "snippet": "...Suchbegriff im Kontext...",
      "score": 0.95
    }
  ],
  "total": 50
}
```

### PUT /v1/data/extracted/{extraction_id}/verify
Extraktion verifizieren.

**Request Body:**
```json
{
  "verified": true,
  "notes": "Manuell geprueft"
}
```

---

## History

### GET /v1/data/history/crawls
Crawl-Historie.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `source_id` | uuid | Filter nach Quelle |
| `category_id` | uuid | Filter nach Kategorie |
| `limit` | int | Max. Ergebnisse (default: 20) |

**Response:**
```json
{
  "crawls": [
    {
      "id": "uuid",
      "source_id": "uuid",
      "source_name": "Stadt Musterstadt",
      "status": "COMPLETED",
      "documents_found": 15,
      "documents_new": 3,
      "started_at": "2025-01-15T10:00:00Z",
      "finished_at": "2025-01-15T10:05:00Z"
    }
  ],
  "total": 100
}
```

> **Hinweis:** Die Gemeinden-Reports (`/municipalities/*`) wurden durch das Entity-Facet-System ersetzt.
> Fuer Entity-basierte Analysen siehe [ENTITIES.md](./ENTITIES.md) und [Analysis API](#analysis-api).

---

## Export

### GET /v1/export/json
JSON-Export.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `category_id` | uuid | Filter |
| `country` | string | Filter |
| `location_name` | string | Filter |
| `min_confidence` | float | Min. Konfidenz |
| `verified_only` | boolean | Nur verifizierte |

**Response:** JSON-Datei als Download

### GET /v1/export/csv
CSV-Export.

**Query-Parameter:** Wie JSON-Export

**Response:** CSV-Datei als Download

### GET /v1/export/changes
Aenderungs-Feed.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `since` | datetime | Aenderungen seit |
| `limit` | int | Max. Ergebnisse |

**Response:**
```json
[
  {
    "id": "uuid",
    "change_type": "NEW",
    "entity_type": "extraction",
    "entity_id": "uuid",
    "changed_at": "2025-01-15T14:30:00Z",
    "data": {...}
  }
]
```

### POST /v1/export/webhook/test
Webhook testen.

---

## Async Export

Fuer Exports mit >5000 Datensaetzen wird ein asynchroner Job gestartet.

### POST /v1/export/async
Startet einen asynchronen Export-Job.

**Request Body:**
```json
{
  "entity_type": "municipality",
  "format": "json",
  "location_filter": "Nordrhein-Westfalen",
  "facet_types": ["pain_point", "positive_signal"],
  "position_keywords": ["Buergermeister"],
  "country": "DE",
  "include_facets": true,
  "filename": "mein_export"
}
```

| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `entity_type` | string | Entity-Typ (municipality, person, etc.) |
| `format` | string | json, csv, excel |
| `location_filter` | string | Filter nach Bundesland/Region |
| `facet_types` | string[] | Nur bestimmte Facet-Typen |
| `position_keywords` | string[] | Position-Filter (fuer Personen) |
| `country` | string | Laenderfilter |
| `include_facets` | boolean | Facetten einschliessen (Standard: true) |
| `filename` | string | Dateiname ohne Extension |

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "export_format": "json",
  "total_records": null,
  "processed_records": 0,
  "progress_percent": 0,
  "progress_message": null,
  "created_at": "2025-12-20T18:00:00Z",
  "is_downloadable": false
}
```

### GET /v1/export/async/{job_id}
Status eines Export-Jobs abfragen.

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "export_format": "json",
  "total_records": 5432,
  "processed_records": 2500,
  "progress_percent": 46,
  "progress_message": "Verarbeitet: 2500/5432",
  "file_size": null,
  "created_at": "2025-12-20T18:00:00Z",
  "started_at": "2025-12-20T18:00:05Z",
  "is_downloadable": false
}
```

**Status-Werte:**
| Status | Beschreibung |
|--------|--------------|
| `pending` | Job wartet auf Verarbeitung |
| `processing` | Job wird verarbeitet |
| `completed` | Export fertig, Download verfuegbar |
| `failed` | Export fehlgeschlagen |
| `cancelled` | Job abgebrochen |

### GET /v1/export/async/{job_id}/download
Fertigen Export herunterladen.

**Response:** Datei als Download (JSON, CSV oder XLSX)

**Fehler:**
- `400 Bad Request` - Export noch nicht fertig
- `404 Not Found` - Job nicht gefunden oder Datei abgelaufen

### DELETE /v1/export/async/{job_id}
Export-Job abbrechen.

### GET /v1/export/async
Liste aller Export-Jobs des aktuellen Benutzers.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `status_filter` | string | Filter nach Status |
| `limit` | int | Max. Ergebnisse (Standard: 20) |
