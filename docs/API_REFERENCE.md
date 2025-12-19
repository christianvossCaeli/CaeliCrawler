# CaeliCrawler API Reference

Vollständige technische Dokumentation aller API-Endpunkte.

**Base URL:** `http://localhost:8000/api`

**Interaktive Dokumentation:** `http://localhost:8000/docs` (Swagger UI)

---

## Inhaltsverzeichnis

1. [Kategorien](#kategorien)
2. [Datenquellen](#datenquellen)
3. [Crawler & Jobs](#crawler--jobs)
4. [KI-Tasks & Dokumentenverarbeitung](#ki-tasks--dokumentenverarbeitung)
5. [Locations (Standorte)](#locations-standorte)
6. [Public API (v1/data)](#public-api-v1data)
7. [Gemeinden & Reports](#gemeinden--reports)
8. [Export](#export)
9. [Entity-Facet System](#entity-facet-system) **NEU**
10. [PySis Integration](#pysis-integration)
11. [System & Health](#system--health)

---

## Kategorien

### GET /admin/categories
Liste aller Kategorien.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `is_active` | boolean | Nur aktive Kategorien |
| `skip` | int | Offset für Pagination |
| `limit` | int | Max. Ergebnisse (default: 100) |

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Windenergie-Beschlüsse",
    "description": "Beschreibung...",
    "purpose": "Windkraft-Restriktionen analysieren",
    "is_active": true,
    "search_terms": ["windkraft", "windenergie", "windpark"],
    "document_types": ["Beschluss", "Protokoll"],
    "extraction_prompt": "Analysiere das Dokument...",
    "url_include_patterns": ["/dokumente/", "/beschluesse/"],
    "url_exclude_patterns": ["/archiv/"],
    "schedule_cron": "0 2 * * *",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z"
  }
]
```

### POST /admin/categories
Neue Kategorie erstellen.

**Request Body:**
```json
{
  "name": "Windenergie-Beschlüsse",
  "description": "Sammelt alle Ratsbeschlüsse",
  "purpose": "Windkraft-Restriktionen analysieren",
  "search_terms": ["windkraft", "windenergie"],
  "extraction_prompt": "Analysiere das Dokument..."
}
```

**Response:** `201 Created` mit Kategorie-Objekt

### GET /admin/categories/{category_id}
Einzelne Kategorie abrufen.

**Response:** Kategorie-Objekt (siehe oben)

### PUT /admin/categories/{category_id}
Kategorie aktualisieren.

**Request Body:** Kategorie-Objekt (partielle Updates möglich)

**Response:** Aktualisiertes Kategorie-Objekt

### DELETE /admin/categories/{category_id}
Kategorie löschen.

**Response:** `204 No Content`

### GET /admin/categories/{category_id}/stats
Statistiken einer Kategorie.

**Response:**
```json
{
  "source_count": 50,
  "document_count": 1234,
  "extraction_count": 987,
  "avg_confidence": 0.78,
  "last_crawl": "2025-01-15T14:30:00Z"
}
```

---

## Datenquellen

### GET /admin/sources
Liste aller Datenquellen.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `category_id` | uuid | Filter nach Kategorie |
| `country` | string | Filter nach Land (DE, AT, CH) |
| `location_name` | string | Filter nach Ort |
| `status` | string | PENDING, ACTIVE, ERROR, CRAWLING |
| `source_type` | string | WEBSITE, OPARL_API, RSS, CUSTOM_API |
| `search` | string | Suche in Name/URL |
| `skip` | int | Offset |
| `limit` | int | Max. Ergebnisse |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Stadt Musterstadt",
      "base_url": "https://musterstadt.de",
      "source_type": "WEBSITE",
      "status": "ACTIVE",
      "category_id": "uuid",
      "category_name": "Windenergie",
      "country": "DE",
      "location_name": "Musterstadt",
      "location_id": "uuid",
      "crawl_config": {
        "max_depth": 3,
        "max_pages": 200,
        "render_javascript": false,
        "url_include_patterns": [],
        "url_exclude_patterns": []
      },
      "last_crawl": "2025-01-15T10:00:00Z",
      "document_count": 45,
      "error_message": null,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 150,
  "skip": 0,
  "limit": 20
}
```

### POST /admin/sources
Neue Datenquelle erstellen.

**Request Body:**
```json
{
  "name": "Stadt Musterstadt",
  "base_url": "https://musterstadt.de",
  "source_type": "WEBSITE",
  "category_id": "uuid",
  "country": "DE",
  "location_name": "Musterstadt",
  "crawl_config": {
    "max_depth": 3,
    "max_pages": 200
  }
}
```

**Response:** `201 Created` mit Source-Objekt

### POST /admin/sources/bulk-import
Mehrere Quellen auf einmal importieren.

**Request Body:**
```json
{
  "category_id": "uuid",
  "sources": [
    {"name": "Stadt A", "base_url": "https://a.de", "location_name": "A"},
    {"name": "Stadt B", "base_url": "https://b.de", "location_name": "B"}
  ]
}
```

**Response:**
```json
{
  "created": 2,
  "skipped": 0,
  "errors": []
}
```

### GET /admin/sources/meta/countries
Verfügbare Länder mit Anzahl.

**Response:**
```json
[
  {"value": "DE", "label": "DE", "count": 120},
  {"value": "AT", "label": "AT", "count": 15}
]
```

### GET /admin/sources/meta/locations
Verfügbare Orte mit Autocomplete.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `country` | string | Filter nach Land |
| `search` | string | Suchbegriff |
| `limit` | int | Max. Ergebnisse |

**Response:**
```json
[
  {"value": "Musterstadt", "label": "Musterstadt", "count": 3}
]
```

### GET /admin/sources/{source_id}
Einzelne Quelle abrufen.

### PUT /admin/sources/{source_id}
Quelle aktualisieren.

### DELETE /admin/sources/{source_id}
Quelle löschen (inkl. aller Dokumente).

### POST /admin/sources/{source_id}/reset
Quelle zurücksetzen (nur bei ERROR-Status).

**Response:**
```json
{
  "message": "Source reset successfully",
  "new_status": "PENDING"
}
```

---

## Crawler & Jobs

### POST /admin/crawler/start
Crawl starten.

**Request Body:**
```json
{
  "category_id": "uuid",
  "source_ids": ["uuid1", "uuid2"],
  "country": "DE",
  "status": "ACTIVE",
  "source_type": "WEBSITE",
  "search": "muster",
  "limit": 100
}
```

Alle Parameter sind optional. Ohne Parameter werden alle aktiven Quellen gecrawlt.

**Response:**
```json
{
  "jobs_started": 50,
  "skipped": 5,
  "message": "Crawl jobs queued"
}
```

### GET /admin/crawler/status
Aktueller Crawler-Status.

**Response:**
```json
{
  "worker_count": 4,
  "running_jobs": 3,
  "pending_jobs": 12,
  "total_documents": 5678
}
```

### GET /admin/crawler/stats
Crawler-Statistiken.

**Response:**
```json
{
  "total_jobs": 234,
  "completed_jobs": 220,
  "failed_jobs": 14,
  "total_documents": 12345,
  "avg_documents_per_job": 56,
  "avg_job_duration_seconds": 180
}
```

### GET /admin/crawler/running
Laufende Jobs mit Live-Details.

**Response:**
```json
[
  {
    "id": "uuid",
    "source_id": "uuid",
    "source_name": "Stadt Musterstadt",
    "base_url": "https://musterstadt.de",
    "current_url": "https://musterstadt.de/aktuelles",
    "status": "RUNNING",
    "started_at": "2025-01-15T14:30:00Z",
    "pages_crawled": 45,
    "documents_found": 12,
    "documents_new": 5,
    "error_count": 0
  }
]
```

### GET /admin/crawler/jobs
Job-Historie.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `status` | string | RUNNING, COMPLETED, FAILED, CANCELLED |
| `source_id` | uuid | Filter nach Quelle |
| `skip` | int | Offset |
| `limit` | int | Max. Ergebnisse |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "source_id": "uuid",
      "source_name": "Stadt Musterstadt",
      "category_name": "Windenergie",
      "status": "COMPLETED",
      "started_at": "2025-01-15T10:00:00Z",
      "completed_at": "2025-01-15T10:05:00Z",
      "duration_seconds": 300,
      "pages_crawled": 150,
      "documents_found": 45,
      "documents_new": 10,
      "documents_processed": 45,
      "error_count": 0,
      "error_log": []
    }
  ],
  "total": 500
}
```

### GET /admin/crawler/jobs/{job_id}
Job-Details.

### GET /admin/crawler/jobs/{job_id}/log
Job-Log mit Aktivitäten.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `limit` | int | Letzte N Einträge (default: 100) |

**Response:**
```json
{
  "current_url": "https://musterstadt.de/aktuelles",
  "log_entries": [
    {
      "timestamp": "2025-01-15T14:30:15Z",
      "url": "https://musterstadt.de/dokument.pdf",
      "status": "document"
    },
    {
      "timestamp": "2025-01-15T14:30:10Z",
      "url": "https://musterstadt.de/aktuelles",
      "status": "crawled"
    }
  ]
}
```

### POST /admin/crawler/jobs/{job_id}/cancel
Job abbrechen.

**Response:**
```json
{
  "message": "Job cancelled",
  "job_id": "uuid"
}
```

### POST /admin/crawler/reanalyze
Dokumente erneut analysieren.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `category_id` | uuid | Filter nach Kategorie |
| `source_id` | uuid | Filter nach Quelle |
| `limit` | int | Max. Dokumente |

**Response:**
```json
{
  "queued": 100,
  "message": "Reanalysis queued"
}
```

---

## KI-Tasks & Dokumentenverarbeitung

### GET /admin/crawler/ai-tasks
Liste aller KI-Tasks.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `status` | string | PENDING, RUNNING, COMPLETED, FAILED |
| `skip` | int | Offset |
| `limit` | int | Max. Ergebnisse |

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "analyze_document",
    "status": "RUNNING",
    "progress_current": 45,
    "progress_total": 100,
    "progress_percent": 45.0,
    "current_item": "Beschluss_2025_01.pdf",
    "started_at": "2025-01-15T14:30:00Z"
  }
]
```

### GET /admin/crawler/ai-tasks/running
Nur laufende KI-Tasks.

### POST /admin/crawler/ai-tasks/{task_id}/cancel
KI-Task abbrechen.

### POST /admin/crawler/documents/{document_id}/process
Einzelnes Dokument verarbeiten (Download + Text-Extraktion).

**Response:**
```json
{
  "message": "Processing started",
  "document_id": "uuid"
}
```

### POST /admin/crawler/documents/{document_id}/analyze
Einzelnes Dokument mit KI analysieren.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `skip_relevance_check` | boolean | Relevanz-Check überspringen |

### POST /admin/crawler/documents/process-pending
Alle wartenden Dokumente verarbeiten.

**Response:**
```json
{
  "queued": 150,
  "message": "Processing queued"
}
```

### POST /admin/crawler/documents/stop-all
Alle laufende Verarbeitungen stoppen.

**Response:**
```json
{
  "message": "All processing stopped",
  "tasks_cancelled": 5,
  "documents_reset": 12
}
```

### POST /admin/crawler/documents/reanalyze-filtered
Gefilterte Dokumente erneut analysieren.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `limit` | int | Max. Dokumente (default: 100) |

---

## Locations (Standorte)

### GET /admin/locations
Liste aller Locations.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `country` | string | Filter nach Land |
| `admin_level_1` | string | Filter nach Bundesland |
| `search` | string | Suchbegriff |
| `page` | int | Seite |
| `per_page` | int | Ergebnisse pro Seite |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Musterstadt",
      "country": "DE",
      "admin_level_1": "Nordrhein-Westfalen",
      "admin_level_2": "Kreis Muster",
      "source_count": 3,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 500,
  "page": 1,
  "per_page": 20
}
```

### GET /admin/locations/search
Location-Suche für Autocomplete.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `q` | string | Suchbegriff (min. 2 Zeichen) |
| `country` | string | Filter nach Land |
| `limit` | int | Max. Ergebnisse |

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Musterstadt",
    "admin_level_1": "NRW",
    "admin_level_2": "Kreis Muster"
  }
]
```

### GET /admin/locations/with-sources
Locations die Quellen haben.

### GET /admin/locations/countries
Verfügbare Länder.

**Response:**
```json
[
  {"code": "DE", "name": "Deutschland", "count": 450},
  {"code": "AT", "name": "Österreich", "count": 50}
]
```

### GET /admin/locations/states
Bundesländer/States.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `country` | string | Filter nach Land |

**Response:**
```json
["Baden-Württemberg", "Bayern", "Berlin", ...]
```

### GET /admin/locations/admin-levels
Admin-Levels (Bundesländer/Landkreise).

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `country` | string | Land |
| `level` | int | 1 = Bundesland, 2 = Landkreis |
| `parent` | string | Parent für Level 2 |

### POST /admin/locations
Location erstellen.

**Request Body:**
```json
{
  "name": "Musterstadt",
  "country": "DE",
  "admin_level_1": "Nordrhein-Westfalen"
}
```

### GET /admin/locations/{location_id}
Location abrufen.

### PUT /admin/locations/{location_id}
Location aktualisieren.

### DELETE /admin/locations/{location_id}
Location löschen.

### POST /admin/locations/link-sources
Quellen automatisch zu Locations verknüpfen.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `country` | string | Nur für dieses Land |

**Response:**
```json
{
  "linked": 45,
  "already_linked": 100,
  "no_match": 5
}
```

### POST /admin/locations/enrich-admin-levels
Admin-Levels via Geocoding ermitteln.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `country` | string | Nur für dieses Land |
| `limit` | int | Max. Locations |

**Response:**
```json
{
  "enriched": 20,
  "failed": 2
}
```

---

## Public API (v1/data)

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
| `skip` | int | Offset |
| `limit` | int | Max. Ergebnisse |

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
        "pain_points": ["Abstandsregelungen", "Lärmschutz"],
        "positive_signals": ["Grundsätzliche Zustimmung"],
        "decision_makers": [
          {"name": "Max Mustermann", "role": "Bürgermeister"}
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

**Response:**
```json
["Musterstadt", "Beispieldorf", "Testheim"]
```

### GET /v1/data/countries
Länder mit extrahierten Daten.

**Response:**
```json
[
  {"code": "DE", "name": "Deutschland", "count": 1000},
  {"code": "AT", "name": "Österreich", "count": 200}
]
```

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
| `skip` | int | Offset |
| `limit` | int | Max. Ergebnisse |

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
  "is_verified": true,
  "notes": "Manuell geprüft"
}
```

**Response:**
```json
{
  "id": "uuid",
  "is_verified": true,
  "verified_at": "2025-01-15T15:00:00Z"
}
```

---

## Gemeinden & Reports

### GET /v1/data/municipalities
Gemeinden-Übersicht.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `country` | string | Filter nach Land |
| `admin_level_1` | string | Filter nach Bundesland |
| `admin_level_2` | string | Filter nach Landkreis |
| `category_id` | uuid | Filter nach Kategorie |
| `min_confidence` | float | Min. Konfidenz |
| `search` | string | Suche im Namen |
| `page` | int | Seite |
| `per_page` | int | Ergebnisse pro Seite |

**Response:**
```json
{
  "items": [
    {
      "name": "Musterstadt",
      "country": "DE",
      "admin_level_1": "NRW",
      "admin_level_2": "Kreis Muster",
      "source_count": 3,
      "document_count": 45,
      "relevant_count": 30,
      "high_priority_count": 5,
      "avg_confidence": 0.82,
      "opportunity_score": 7.5,
      "decision_maker_count": 3
    }
  ],
  "total": 500
}
```

### GET /v1/data/municipalities/{municipality_name}/report
Detaillierter Gemeinde-Report.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `category_id` | uuid | Filter nach Kategorie |

**Response:**
```json
{
  "municipality": "Musterstadt",
  "category": "Windenergie",
  "category_purpose": "Windkraft-Restriktionen analysieren",
  "overview": {
    "total_documents": 45,
    "relevant_documents": 30,
    "avg_confidence": 0.82,
    "overall_priority": "high"
  },
  "decision_makers": [
    {
      "name": "Max Mustermann",
      "role": "Bürgermeister",
      "contact": "buergermeister@musterstadt.de",
      "document_ids": ["uuid1", "uuid2"]
    }
  ],
  "pain_points": [
    {
      "text": "Strenge Abstandsregelungen von 1000m",
      "type": "regulation",
      "severity": "high",
      "document_id": "uuid"
    }
  ],
  "positive_signals": [
    {
      "text": "Grundsätzliche Zustimmung zu erneuerbaren Energien",
      "type": "political_support",
      "priority": "medium",
      "document_id": "uuid"
    }
  ],
  "summaries": [
    {
      "document_id": "uuid",
      "document_title": "Ratsbeschluss 2025/01",
      "summary": "Der Rat hat beschlossen..."
    }
  ]
}
```

### GET /v1/data/municipalities/{municipality_name}/documents
Dokumente einer Gemeinde.

### GET /v1/data/report/overview
Übersichts-Report.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `category_id` | uuid | Filter |
| `min_confidence` | float | Min. Konfidenz |

**Response:**
```json
{
  "total_municipalities": 500,
  "total_documents": 12000,
  "total_extractions": 9500,
  "high_priority_municipalities": 45,
  "avg_confidence": 0.78,
  "top_pain_points": [...],
  "top_opportunities": [...]
}
```

### GET /v1/data/history/municipalities
Änderungshistorie für Gemeinden.

### GET /v1/data/history/crawls
Crawl-Historie.

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
Änderungs-Feed.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `since` | datetime | Änderungen seit |
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

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `url` | string | Webhook-URL |

**Response:**
```json
{
  "success": true,
  "status_code": 200,
  "response_time_ms": 150
}
```

---

## Entity-Facet System

> **NEU:** Das Entity-Facet System ermöglicht flexible, generische Datenstrukturen für verschiedene Analyse-Szenarien.

### Konzept

Das System besteht aus:
- **Entity Types**: Typdefinitionen (municipality, person, organization, event)
- **Entities**: Konkrete Instanzen eines Typs
- **Facet Types**: Eigenschaftsdefinitionen (pain_point, positive_signal, contact)
- **Facet Values**: Konkrete Werte einer Eigenschaft für eine Entity
- **Relation Types**: Beziehungsdefinitionen zwischen Entity Types
- **Entity Relations**: Konkrete Beziehungen zwischen Entities
- **Analysis Templates**: Konfiguration für Analyse-Ansichten

### Entity Types

#### GET /v1/entity-types
Liste aller Entity-Typen.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `is_active` | boolean | Nur aktive Typen |
| `is_system` | boolean | Nur System-Typen |
| `is_primary` | boolean | Nur primäre Aggregationstypen |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "slug": "municipality",
      "name": "Gemeinde",
      "name_plural": "Gemeinden",
      "description": "Kommunale Gebietskörperschaft",
      "icon": "mdi-city",
      "color": "primary",
      "is_primary": true,
      "supports_hierarchy": true,
      "hierarchy_config": {
        "levels": ["country", "state", "district", "municipality"]
      },
      "attribute_schema": {
        "type": "object",
        "properties": {
          "population": {"type": "integer"},
          "area_km2": {"type": "number"}
        }
      },
      "is_system": true,
      "is_active": true,
      "entity_count": 500
    }
  ],
  "total": 4
}
```

#### GET /v1/entity-types/{id}
Entity-Typ abrufen.

#### GET /v1/entity-types/by-slug/{slug}
Entity-Typ per Slug abrufen.

#### POST /v1/entity-types
Entity-Typ erstellen.

**Request Body:**
```json
{
  "slug": "custom_type",
  "name": "Mein Typ",
  "name_plural": "Meine Typen",
  "icon": "mdi-star",
  "color": "info",
  "is_primary": false,
  "supports_hierarchy": false,
  "attribute_schema": {}
}
```

#### PUT /v1/entity-types/{id}
Entity-Typ aktualisieren.

#### DELETE /v1/entity-types/{id}
Entity-Typ löschen. Nur möglich wenn keine Entities existieren.

---

### Entities

#### GET /v1/entities
Entities auflisten.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `entity_type_slug` | string | Filter nach Entity-Typ |
| `entity_type_id` | uuid | Filter nach Entity-Typ ID |
| `parent_id` | uuid | Filter nach Parent-Entity |
| `hierarchy_level` | int | Filter nach Hierarchie-Ebene (0=root) |
| `search` | string | Suche in Name |
| `has_facets` | boolean | Nur Entities mit/ohne Facets |
| `facet_type_slugs` | string | Komma-separierte Facet-Typ Slugs |
| `category_id` | uuid | Filter nach verknüpfter Kategorie |
| `is_active` | boolean | Nur aktive Entities |
| `page` | int | Seitennummer |
| `per_page` | int | Einträge pro Seite |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "entity_type_id": "uuid",
      "entity_type_slug": "municipality",
      "name": "Musterstadt",
      "name_normalized": "musterstadt",
      "slug": "musterstadt",
      "external_id": "12345678",
      "parent_id": null,
      "hierarchy_path": "/DE/Bayern/Musterstadt",
      "hierarchy_level": 2,
      "core_attributes": {
        "population": 50000,
        "area_km2": 75.5
      },
      "latitude": 48.1234,
      "longitude": 11.5678,
      "is_active": true,
      "facet_count": 15,
      "relation_count": 3,
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-15T10:00:00Z"
    }
  ],
  "total": 500,
  "page": 1,
  "per_page": 25
}
```

#### GET /v1/entities/{id}
Entity-Details abrufen.

#### GET /v1/entities/by-slug/{type_slug}/{entity_slug}
Entity per Slugs abrufen.

#### GET /v1/entities/{id}/brief
Kurze Entity-Info (für Autocomplete).

**Response:**
```json
{
  "id": "uuid",
  "name": "Musterstadt",
  "entity_type_name": "Gemeinde",
  "hierarchy_path": "/DE/Bayern/Musterstadt"
}
```

#### GET /v1/entities/{id}/children
Kind-Entities abrufen (für hierarchische Typen).

#### GET /v1/entities/hierarchy/{entity_type_slug}
Hierarchie-Baum abrufen.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `max_depth` | int | Maximale Tiefe |
| `root_id` | uuid | Nur Unterknoten von |

#### POST /v1/entities
Entity erstellen.

**Request Body:**
```json
{
  "entity_type_id": "uuid",
  "name": "Neue Stadt",
  "external_id": "12345679",
  "parent_id": "uuid (optional)",
  "core_attributes": {
    "population": 10000
  },
  "latitude": 48.0,
  "longitude": 11.0
}
```

#### PUT /v1/entities/{id}
Entity aktualisieren.

#### DELETE /v1/entities/{id}
Entity löschen.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `force` | boolean | Auch Kinder und Facets löschen |

---

### Facet Types

#### GET /v1/facets/types
Facet-Typen auflisten.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `applicable_entity_types` | string | Komma-separierte Entity-Type-Slugs |
| `is_active` | boolean | Nur aktive Typen |
| `is_time_based` | boolean | Nur zeitbasierte Typen |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "slug": "pain_point",
      "name": "Pain Point",
      "description": "Probleme und Herausforderungen",
      "value_schema": {
        "type": "object",
        "properties": {
          "text": {"type": "string"},
          "severity": {"type": "string", "enum": ["low", "medium", "high"]}
        }
      },
      "icon": "mdi-alert-circle",
      "color": "error",
      "applicable_entity_types": ["municipality", "organization"],
      "is_time_based": false,
      "default_time_filter": "all",
      "aggregation_method": "count",
      "ai_extraction_prompt": "Extrahiere Pain Points aus dem Dokument...",
      "is_system": true,
      "is_active": true,
      "display_order": 1
    }
  ],
  "total": 4
}
```

#### GET /v1/facets/types/{id}
Facet-Typ abrufen.

#### GET /v1/facets/types/by-slug/{slug}
Facet-Typ per Slug.

#### POST /v1/facets/types
Facet-Typ erstellen.

#### PUT /v1/facets/types/{id}
Facet-Typ aktualisieren.

#### DELETE /v1/facets/types/{id}
Facet-Typ löschen.

---

### Facet Values

#### GET /v1/facets/values
Facet-Werte auflisten.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `entity_id` | uuid | Filter nach Entity |
| `facet_type_id` | uuid | Filter nach Facet-Typ |
| `facet_type_slug` | string | Filter nach Facet-Typ Slug |
| `human_verified` | boolean | Nur verifizierte/unverifizierte |
| `min_confidence` | float | Mindest-Konfidenz (0-1) |
| `time_filter` | string | `future_only`, `past_only`, `all` |
| `page` | int | Seitennummer |
| `per_page` | int | Einträge pro Seite |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "entity_id": "uuid",
      "entity_name": "Musterstadt",
      "facet_type_id": "uuid",
      "facet_type_slug": "pain_point",
      "facet_type_name": "Pain Point",
      "value": {
        "text": "Bürger beschweren sich über...",
        "severity": "high"
      },
      "text_representation": "Bürger beschweren sich über...",
      "confidence_score": 0.85,
      "human_verified": false,
      "verified_by_id": null,
      "verified_at": null,
      "source_document_id": "uuid",
      "source_url": "https://...",
      "event_date": null,
      "valid_from": null,
      "valid_until": null,
      "created_at": "2025-01-15T10:00:00Z"
    }
  ],
  "total": 100
}
```

#### GET /v1/facets/values/{id}
Facet-Wert abrufen.

#### POST /v1/facets/values
Facet-Wert erstellen.

**Request Body:**
```json
{
  "entity_id": "uuid",
  "facet_type_id": "uuid",
  "value": {"text": "Neuer Pain Point"},
  "text_representation": "Neuer Pain Point",
  "confidence_score": 1.0,
  "source_url": "https://...",
  "event_date": "2025-06-15T14:00:00Z"
}
```

#### PUT /v1/facets/values/{id}
Facet-Wert aktualisieren.

#### PUT /v1/facets/values/{id}/verify
Facet-Wert verifizieren.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `verified` | boolean | Verifiziert ja/nein |

**Response:** Aktualisierter Facet-Wert

#### DELETE /v1/facets/values/{id}
Facet-Wert löschen.

#### GET /v1/facets/entity/{entity_id}/summary
Facet-Zusammenfassung einer Entity.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `include_samples` | boolean | Sample-Werte einschließen |
| `time_filter` | string | Zeitfilter für zeitbasierte Facets |

**Response:**
```json
{
  "entity_id": "uuid",
  "entity_name": "Musterstadt",
  "total_facet_values": 25,
  "verified_count": 10,
  "facets_by_type": [
    {
      "facet_type_id": "uuid",
      "facet_type_slug": "pain_point",
      "facet_type_name": "Pain Point",
      "facet_type_icon": "mdi-alert-circle",
      "facet_type_color": "error",
      "value_count": 15,
      "verified_count": 5,
      "avg_confidence": 0.82,
      "sample_values": [
        {
          "id": "uuid",
          "text_representation": "...",
          "confidence_score": 0.9,
          "human_verified": true
        }
      ]
    }
  ]
}
```

---

### Relation Types

#### GET /v1/relations/types
Beziehungstypen auflisten.

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "slug": "works_for",
      "name": "arbeitet für",
      "name_inverse": "beschäftigt",
      "description": "Person arbeitet für Organisation/Gemeinde",
      "source_entity_type_id": "uuid",
      "source_entity_type_slug": "person",
      "target_entity_type_id": "uuid",
      "target_entity_type_slug": "municipality",
      "cardinality": "n:1",
      "attributes_schema": {
        "type": "object",
        "properties": {
          "role": {"type": "string"},
          "since": {"type": "string", "format": "date"}
        }
      },
      "is_system": true,
      "is_active": true
    }
  ],
  "total": 4
}
```

#### GET /v1/relations/types/{id}
Beziehungstyp abrufen.

#### GET /v1/relations/types/by-slug/{slug}
Beziehungstyp per Slug.

#### POST /v1/relations/types
Beziehungstyp erstellen.

#### PUT /v1/relations/types/{id}
Beziehungstyp aktualisieren.

#### DELETE /v1/relations/types/{id}
Beziehungstyp löschen.

---

### Entity Relations

#### GET /v1/relations
Beziehungen auflisten.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `entity_id` | uuid | Entity als Source ODER Target |
| `source_entity_id` | uuid | Entity als Source |
| `target_entity_id` | uuid | Entity als Target |
| `relation_type_id` | uuid | Filter nach Beziehungstyp |
| `relation_type_slug` | string | Filter nach Beziehungstyp Slug |
| `human_verified` | boolean | Nur verifizierte |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "relation_type_id": "uuid",
      "relation_type_slug": "works_for",
      "relation_type_name": "arbeitet für",
      "relation_type_name_inverse": "beschäftigt",
      "source_entity_id": "uuid",
      "source_entity_name": "Max Mustermann",
      "source_entity_type_slug": "person",
      "target_entity_id": "uuid",
      "target_entity_name": "Musterstadt",
      "target_entity_type_slug": "municipality",
      "attributes": {
        "role": "Bürgermeister",
        "since": "2020-01-01"
      },
      "confidence_score": 0.95,
      "human_verified": true,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 50
}
```

#### GET /v1/relations/{id}
Beziehung abrufen.

#### POST /v1/relations
Beziehung erstellen.

**Request Body:**
```json
{
  "relation_type_id": "uuid",
  "source_entity_id": "uuid",
  "target_entity_id": "uuid",
  "attributes": {
    "role": "Stadtrat"
  },
  "confidence_score": 1.0
}
```

#### PUT /v1/relations/{id}
Beziehung aktualisieren.

#### PUT /v1/relations/{id}/verify
Beziehung verifizieren.

#### DELETE /v1/relations/{id}
Beziehung löschen.

#### GET /v1/relations/graph/{entity_id}
Beziehungsgraph einer Entity.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `depth` | int | Traversierungstiefe (default: 1) |
| `relation_type_slugs` | string | Komma-separierte Typen |

**Response:**
```json
{
  "center_entity": {
    "id": "uuid",
    "name": "Musterstadt",
    "entity_type_slug": "municipality"
  },
  "nodes": [
    {
      "id": "uuid",
      "name": "Max Mustermann",
      "entity_type_slug": "person"
    }
  ],
  "edges": [
    {
      "source_id": "uuid",
      "target_id": "uuid",
      "relation_type_slug": "works_for",
      "attributes": {"role": "Bürgermeister"}
    }
  ]
}
```

---

### Analysis Templates

#### GET /v1/analysis/templates
Analyse-Templates auflisten.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `is_active` | boolean | Nur aktive Templates |
| `primary_entity_type_slug` | string | Filter nach primärem Entity-Typ |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "slug": "pain_point_analysis",
      "name": "Pain-Point-Analyse",
      "description": "Aggregiert Pain Points pro Gemeinde",
      "primary_entity_type_id": "uuid",
      "primary_entity_type_slug": "municipality",
      "facet_config": [
        {
          "facet_type_slug": "pain_point",
          "display_order": 1,
          "show_in_summary": true,
          "default_expanded": true
        },
        {
          "facet_type_slug": "positive_signal",
          "display_order": 2,
          "show_in_summary": true
        }
      ],
      "aggregation_config": {
        "group_by": "entity",
        "sort_by": "opportunity_score",
        "sort_order": "desc"
      },
      "display_config": {
        "chart_type": "bar",
        "show_map": true
      },
      "is_default": true,
      "is_active": true
    }
  ],
  "total": 3
}
```

#### GET /v1/analysis/templates/{id}
Template abrufen.

#### GET /v1/analysis/templates/by-slug/{slug}
Template per Slug.

#### POST /v1/analysis/templates
Template erstellen.

#### PUT /v1/analysis/templates/{id}
Template aktualisieren.

#### DELETE /v1/analysis/templates/{id}
Template löschen.

---

### Analysis Endpoints

#### GET /v1/analysis/overview
Analyse-Übersicht.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `template_slug` | string | Analyse-Template |
| `entity_type_slug` | string | Entity-Typ |
| `category_id` | uuid | Filter nach Kategorie |
| `parent_entity_id` | uuid | Filter nach Parent-Entity |
| `time_filter` | string | Zeitfilter |

**Response:**
```json
{
  "template": {
    "id": "uuid",
    "name": "Pain-Point-Analyse"
  },
  "entities": [
    {
      "entity_id": "uuid",
      "entity_name": "Musterstadt",
      "facet_counts": {
        "pain_point": 15,
        "positive_signal": 5
      },
      "opportunity_score": 0.75,
      "avg_confidence": 0.82
    }
  ],
  "total": 500
}
```

#### GET /v1/analysis/report/{entity_id}
Detaillierter Analyse-Report.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `template_slug` | string | Analyse-Template |
| `include_facets` | boolean | Facet-Details einschließen |
| `include_relations` | boolean | Relations einschließen |

#### GET /v1/analysis/stats
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

---

## PySis Integration

> **Hinweis:** PySis ist eine optionale Integration für externes Prozess-Management. Erfordert Azure AD Konfiguration.

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

### GET /admin/pysis/templates
Feld-Templates auflisten.

### POST /admin/pysis/templates
Template erstellen.

### GET /admin/pysis/templates/{template_id}
Template abrufen.

### PUT /admin/pysis/templates/{template_id}
Template aktualisieren.

### DELETE /admin/pysis/templates/{template_id}
Template löschen.

### GET /admin/pysis/available-processes
Verfügbare Prozesse von PySis.

### GET /admin/pysis/locations/{location_name}/processes
Prozesse einer Location.

### POST /admin/pysis/locations/{location_name}/processes
Prozess für Location erstellen.

### GET /admin/pysis/processes/{process_id}
Prozess-Details.

### PUT /admin/pysis/processes/{process_id}
Prozess aktualisieren.

### DELETE /admin/pysis/processes/{process_id}
Prozess löschen.

### POST /admin/pysis/processes/{process_id}/apply-template
Template auf Prozess anwenden.

### POST /admin/pysis/processes/{process_id}/generate
Felder KI-generieren.

### POST /admin/pysis/processes/{process_id}/sync/pull
Daten von PySis laden.

### POST /admin/pysis/processes/{process_id}/sync/push
Daten zu PySis senden.

### GET /admin/pysis/processes/{process_id}/fields
Felder eines Prozesses.

### POST /admin/pysis/processes/{process_id}/fields
Feld hinzufügen.

### PUT /admin/pysis/fields/{field_id}
Feld aktualisieren.

### PUT /admin/pysis/fields/{field_id}/value
Feld-Wert setzen.

### DELETE /admin/pysis/fields/{field_id}
Feld löschen.

### POST /admin/pysis/fields/{field_id}/generate
KI-Vorschlag für Feld generieren.

### POST /admin/pysis/fields/{field_id}/accept-ai
KI-Vorschlag akzeptieren.

### POST /admin/pysis/fields/{field_id}/reject-ai
KI-Vorschlag ablehnen.

### POST /admin/pysis/fields/{field_id}/sync/push
Feld zu PySis senden.

### GET /admin/pysis/fields/{field_id}/history
Feld-Änderungshistorie.

### POST /admin/pysis/fields/{field_id}/restore/{history_id}
Version wiederherstellen.

---

## System & Health

### GET /
Root-Endpoint.

**Response:**
```json
{
  "name": "CaeliCrawler API",
  "version": "1.0.0",
  "docs": "/docs"
}
```

### GET /health
Health-Check.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "celery_workers": 4
}
```

---

## Fehler-Responses

Alle Endpunkte können folgende Fehler zurückgeben:

### 400 Bad Request
```json
{
  "detail": "Validation error message"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limiting

Aktuell kein Rate Limiting implementiert. Für Produktionsumgebungen wird empfohlen:
- Max. 100 Requests/Minute für `/admin/*`
- Max. 1000 Requests/Minute für `/v1/*`

---

## Authentifizierung

Aktuell keine Authentifizierung implementiert. Für Produktionsumgebungen wird empfohlen:
- API-Key Header: `X-API-Key: <key>`
- OAuth2/JWT für Admin-Endpunkte
