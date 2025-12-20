# Admin API

[Zurueck zur Uebersicht](./README.md)

Admin-Endpunkte fuer Kategorien, Datenquellen, Crawler, Locations, Audit-Logging und Versionierung.

---

## Kategorien

### GET /admin/categories
Liste aller Kategorien.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `is_active` | boolean | Nur aktive Kategorien |
| `page` | int | Seite (default: 1) |
| `per_page` | int | Eintraege pro Seite (default: 100) |

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Windenergie-Beschluesse",
    "description": "Beschreibung...",
    "purpose": "Windkraft-Restriktionen analysieren",
    "is_active": true,
    "search_terms": ["windkraft", "windenergie", "windpark"],
    "document_types": ["Beschluss", "Protokoll"],
    "ai_extraction_prompt": "Analysiere das Dokument...",
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
  "name": "Windenergie-Beschluesse",
  "description": "Sammelt alle Ratsbeschluesse",
  "purpose": "Windkraft-Restriktionen analysieren",
  "search_terms": ["windkraft", "windenergie"],
  "ai_extraction_prompt": "Analysiere das Dokument..."
}
```

**Response:** `201 Created` mit Kategorie-Objekt

### GET /admin/categories/{category_id}
Einzelne Kategorie abrufen.

### PUT /admin/categories/{category_id}
Kategorie aktualisieren.

**Request Body:** Kategorie-Objekt (partielle Updates moeglich)

### DELETE /admin/categories/{category_id}
Kategorie loeschen.

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
| `category_id` | uuid | Filter nach Kategorie (einzelne) |
| `category_ids` | uuid[] | Filter nach mehreren Kategorien |
| `country` | string | Filter nach Land (DE, AT, CH) |
| `location_name` | string | Filter nach Ort |
| `status` | string | PENDING, ACTIVE, ERROR, CRAWLING |
| `source_type` | string | WEBSITE, OPARL_API, RSS, CUSTOM_API |
| `search` | string | Suche in Name/URL |
| `page` | int | Seite (default: 1) |
| `per_page` | int | Eintraege pro Seite (default: 20) |

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
      "category_ids": ["uuid1", "uuid2"],
      "categories": [
        {"id": "uuid1", "name": "Windenergie"},
        {"id": "uuid2", "name": "Ratsbeschluesse"}
      ],
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
  "page": 1,
  "per_page": 20,
  "pages": 8
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
  "category_ids": ["uuid1", "uuid2"],
  "country": "DE",
  "location_name": "Musterstadt",
  "crawl_config": {
    "max_depth": 3,
    "max_pages": 200
  }
}
```

> **Hinweis:** `category_ids` ist ein Array - eine Quelle kann mehreren Kategorien zugeordnet werden (N:M-Beziehung).

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
Verfuegbare Laender mit Anzahl.

### GET /admin/sources/meta/locations
Verfuegbare Orte mit Autocomplete.

### GET /admin/sources/meta/counts
Aggregierte Counts fuer Sidebar-Navigation.

### GET /admin/sources/{source_id}
Einzelne Quelle abrufen.

### PUT /admin/sources/{source_id}
Quelle aktualisieren.

### DELETE /admin/sources/{source_id}
Quelle loeschen (inkl. aller Dokumente).

### POST /admin/sources/{source_id}/reset
Quelle zuruecksetzen (nur bei ERROR-Status).

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
  "jobs_created": 50,
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

### GET /admin/crawler/running
Laufende Jobs mit Live-Details.

### GET /admin/crawler/jobs
Job-Historie.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `status` | string | RUNNING, COMPLETED, FAILED, CANCELLED |
| `source_id` | uuid | Filter nach Quelle |
| `page` | int | Seite (default: 1) |
| `per_page` | int | Eintraege pro Seite (default: 20) |

### GET /admin/crawler/jobs/{job_id}
Job-Details.

### GET /admin/crawler/jobs/{job_id}/log
Job-Log mit Aktivitaeten.

### POST /admin/crawler/jobs/{job_id}/cancel
Job abbrechen.

### POST /admin/crawler/reanalyze
Dokumente erneut analysieren.

---

## KI-Tasks & Dokumentenverarbeitung

### GET /admin/crawler/ai-tasks
Liste aller KI-Tasks.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `status` | string | PENDING, RUNNING, COMPLETED, FAILED |
| `page` | int | Seite (default: 1) |
| `per_page` | int | Eintraege pro Seite (default: 20) |

### GET /admin/crawler/ai-tasks/running
Nur laufende KI-Tasks.

### POST /admin/crawler/ai-tasks/{task_id}/cancel
KI-Task abbrechen.

### POST /admin/crawler/documents/{document_id}/process
Einzelnes Dokument verarbeiten (Download + Text-Extraktion).

### POST /admin/crawler/documents/{document_id}/analyze
Einzelnes Dokument mit KI analysieren.

### POST /admin/crawler/documents/process-pending
Alle wartenden Dokumente verarbeiten.

### POST /admin/crawler/documents/stop-all
Alle laufende Verarbeitungen stoppen.

### POST /admin/crawler/documents/reanalyze-filtered
Gefilterte Dokumente erneut analysieren.

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

### GET /admin/locations/search
Location-Suche fuer Autocomplete.

### GET /admin/locations/with-sources
Locations die Quellen haben.

### GET /admin/locations/countries
Verfuegbare Laender.

### GET /admin/locations/states
Bundeslaender/States.

### GET /admin/locations/admin-levels
Admin-Levels (Bundeslaender/Landkreise).

### POST /admin/locations
Location erstellen.

### GET /admin/locations/{location_id}
Location abrufen.

### PUT /admin/locations/{location_id}
Location aktualisieren.

### DELETE /admin/locations/{location_id}
Location loeschen.

### POST /admin/locations/link-sources
Quellen automatisch zu Locations verknuepfen.

### POST /admin/locations/enrich-admin-levels
Admin-Levels via Geocoding ermitteln.

---

## Audit Logging

Admin-Endpoints fuer Audit-Log-Verwaltung. **Erfordert Admin-Rolle.**

### GET /admin/audit
Audit-Log-Eintraege auflisten mit Filterung und Pagination.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `page` | int | Seite (default: 1) |
| `per_page` | int | Eintraege pro Seite (1-100, default: 50) |
| `action` | string | Filter nach Aktion (CREATE, UPDATE, DELETE, LOGIN, LOGOUT) |
| `entity_type` | string | Filter nach Entity-Typ |
| `entity_id` | uuid | Filter nach Entity-ID |
| `user_id` | uuid | Filter nach Benutzer |
| `start_date` | datetime | Aenderungen seit |
| `end_date` | datetime | Aenderungen bis |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "user_email": "user@example.com",
      "action": "UPDATE",
      "entity_type": "DataSource",
      "entity_id": "uuid",
      "entity_name": "Stadt Musterstadt",
      "changes": {
        "status": {"old": "PENDING", "new": "ACTIVE"}
      },
      "ip_address": "192.168.1.1",
      "created_at": "2025-01-15T14:30:00Z"
    }
  ],
  "total": 1234,
  "page": 1,
  "per_page": 50,
  "pages": 25
}
```

### GET /admin/audit/entity/{entity_type}/{entity_id}
Aenderungshistorie fuer eine spezifische Entity.

### GET /admin/audit/user/{user_id}
Aenderungshistorie eines Benutzers.

### GET /admin/audit/stats
Audit-Log-Statistiken.

---

## Versionierung

Endpoints fuer Versionshistorie von Entities. **Erfordert mindestens Viewer-Rolle.**

### GET /admin/versions/{entity_type}/{entity_id}
Versionshistorie einer Entity abrufen.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `limit` | int | Max. Eintraege (1-100, default: 50) |
| `offset` | int | Offset (default: 0) |

**Unterstuetzte Entity-Typen:**
- Category
- DataSource
- Entity
- FacetValue
- Und alle anderen versionierten Models...

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "entity_type": "DataSource",
      "entity_id": "uuid",
      "version_number": 5,
      "diff": {
        "status": {"old": "PENDING", "new": "ACTIVE"},
        "last_crawl": {"old": null, "new": "2025-01-15T14:30:00Z"}
      },
      "has_snapshot": true,
      "user_id": "uuid",
      "user_email": "admin@example.com",
      "change_reason": "Aktiviert nach Pruefung",
      "created_at": "2025-01-15T14:30:00Z"
    }
  ],
  "total": 5,
  "entity_type": "DataSource",
  "entity_id": "uuid"
}
```

### GET /admin/versions/{entity_type}/{entity_id}/{version_number}
Details einer spezifischen Version abrufen.

### GET /admin/versions/{entity_type}/{entity_id}/{version_number}/state
Entity-Zustand zu einer bestimmten Version rekonstruieren.

---

## Externe APIs

### GET /admin/external-apis
Liste aller konfigurierten externen APIs.

### POST /admin/external-apis
Neue externe API konfigurieren.

### GET /admin/external-apis/{api_id}
API-Details abrufen.

### PUT /admin/external-apis/{api_id}
API aktualisieren.

### DELETE /admin/external-apis/{api_id}
API loeschen.

### POST /admin/external-apis/{api_id}/sync
Synchronisation starten.

### GET /admin/external-apis/{api_id}/status
Sync-Status abrufen.
