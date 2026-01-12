# Admin API

[Zurueck zur Uebersicht](./README.md)

Admin-Endpunkte fuer Kategorien, Datenquellen, Crawler, Locations, Audit-Logging und Versionierung.

---

## Kategorien

> **BREAKING CHANGE (v2.2.0):** Der Parameter `is_active` wurde entfernt und durch `scheduled_only` ersetzt. Das Feld `is_active` existiert nicht mehr in der Response. Siehe [Migration Guide](./MIGRATION_v2.2.md) fuer Details.

### GET /admin/categories
Liste aller Kategorien.

**Query-Parameter:**
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `page` | int | 1 | Seite (1-basiert) |
| `per_page` | int | 20 | Eintraege pro Seite (max 100) |
| `scheduled_only` | boolean | `false` | Nur Kategorien mit aktivem Crawl-Schedule |
| `is_public` | boolean | - | Sichtbarkeitsfilter (true=nur öffentliche, false=nur private, null=basierend auf include_private) |
| `include_private` | boolean | `true` | Private Kategorien des Benutzers einschliessen |
| `search` | string | - | Suche in Name und Beschreibung (case-insensitive) |
| `has_documents` | boolean | - | Filter nach Dokumenten (true=mit Dokumenten, false=ohne) |
| `language` | string | - | Filter nach Sprachcode (ISO 639-1, z.B. "de", "en") |
| `sort_by` | string | `"name"` | Sortierung: `name`, `purpose`, `schedule_enabled`, `source_count`, `document_count` |
| `sort_order` | string | `"asc"` | Sortierreihenfolge: `asc`, `desc` |

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Windenergie-Beschluesse",
    "description": "Beschreibung...",
    "purpose": "Windkraft-Restriktionen analysieren",
    "schedule_enabled": true,
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

### POST /admin/categories/preview-ai-setup
KI-gestuetzte Konfigurationsvorschlaege fuer eine neue Kategorie generieren.

> **NEU in v2.2.0**

Generiert basierend auf Name und Zweck einer Kategorie:
- **EntityType**: Vorgeschlagener Entity-Typ mit Schema
- **FacetTypes**: Vorgeschlagene Facet-Typen
- **Extraction Prompt**: KI-Prompt fuer Dokumentenanalyse
- **Search Terms**: Suchbegriffe fuer Crawling
- **URL Patterns**: Include/Exclude-Patterns

**Berechtigung:** Editor

**Request Body:**
```json
{
  "name": "Windkraft-Restriktionen",
  "purpose": "Identifiziere Hindernisse fuer Windkraftprojekte in kommunalen Dokumenten",
  "description": "Optional: Zusaetzliche Beschreibung"
}
```

| Parameter | Typ | Required | Beschreibung |
|-----------|-----|----------|--------------|
| `name` | string | ja | Kategoriename (1-255 Zeichen) |
| `purpose` | string | ja | Zweck/Intent der Kategorie |
| `description` | string | nein | Zusaetzliche Beschreibung |

**Response:**
```json
{
  "suggested_entity_type": {
    "id": null,
    "name": "Windkraft-Projekt",
    "slug": "windkraft-projekt",
    "name_plural": "Windkraft-Projekte",
    "description": "Projekte im Bereich Windenergie",
    "icon": "mdi-wind-turbine",
    "color": "#4CAF50",
    "attribute_schema": {
      "type": "object",
      "properties": {
        "power_mw": {"type": "number"},
        "status": {"type": "string"}
      }
    },
    "is_new": true
  },
  "existing_entity_types": [
    {"id": "uuid", "name": "Gemeinde", "slug": "municipality", "is_new": false}
  ],
  "suggested_facet_types": [
    {
      "id": null,
      "name": "Pain Point",
      "slug": "pain_point",
      "name_plural": "Pain Points",
      "description": "Probleme, Bedenken und Hindernisse",
      "value_type": "object",
      "value_schema": {...},
      "icon": "mdi-alert-circle",
      "color": "#F44336",
      "is_new": true,
      "selected": true
    }
  ],
  "existing_facet_types": [...],
  "suggested_extraction_prompt": "Analysiere das Dokument auf Hindernisse...",
  "suggested_search_terms": ["windkraft", "windenergie", "genehmigung"],
  "suggested_url_include_patterns": ["/dokumente/", "/beschluesse/"],
  "suggested_url_exclude_patterns": ["/archiv/", "/alt/"],
  "reasoning": "Basierend auf dem Fokus auf Windkraft-Restriktionen..."
}
```

**Hinweis:** Dieser Endpoint speichert keine Daten. Die Vorschlaege koennen vom Benutzer angepasst werden, bevor die Kategorie erstellt wird.

**Fehler:**
- `503 Service Unavailable` - KI-Service nicht verfuegbar (z.B. fehlender API-Key)

### POST /admin/categories/{category_id}/assign-sources-by-tags
Datenquellen anhand von Tags einer Kategorie zuweisen.

> **NEU in v2.2.0**

Bulk-Operation zum Zuweisen von DataSources zu einer Kategorie basierend auf Tag-Filtern.

**Berechtigung:** Editor

**Request Body:**
```json
{
  "tags": ["nrw", "kommunal"],
  "match_mode": "all",
  "mode": "add"
}
```

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `tags` | string[] | required | Tags zum Filtern der Quellen |
| `match_mode` | string | `all` | `all` (AND-Logik) oder `any` (OR-Logik) |
| `mode` | string | `add` | `add` (behalte bestehende) oder `replace` (entferne bestehende) |

**Match-Modi:**
- `all`: Quelle muss ALLE angegebenen Tags haben (AND)
- `any`: Quelle muss mindestens EINEN Tag haben (OR)

**Assignment-Modi:**
- `add`: Neue Quellen hinzufuegen, bestehende Zuweisungen behalten
- `replace`: Alle bestehenden Zuweisungen entfernen, neue hinzufuegen

**Response:**
```json
{
  "assigned": 45,
  "already_assigned": 12,
  "removed": 0,
  "total_in_category": 57
}
```

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `assigned` | int | Anzahl neu zugewiesener Quellen |
| `already_assigned` | int | Anzahl bereits zugewiesener Quellen |
| `removed` | int | Anzahl entfernter Zuweisungen (bei `mode=replace`) |
| `total_in_category` | int | Gesamtzahl Quellen in der Kategorie nach der Operation |

---

## Datenquellen

### GET /admin/sources
Liste aller Datenquellen.

**Berechtigung:** Editor

**Query-Parameter:**
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `page` | int | 1 | Seite (1-basiert) |
| `per_page` | int | 20 | Eintraege pro Seite (max 10000) |
| `category_id` | uuid | - | Filter nach Kategorie (N:M-Verknuepfung) |
| `status` | string | - | PENDING, ACTIVE, ERROR, CRAWLING |
| `source_type` | string | - | WEBSITE, OPARL_API, RSS, CUSTOM_API |
| `search` | string | - | Suche in Name/URL (max 200 Zeichen) |
| `tags` | string[] | - | Filter nach Tags (OR-Logik) |
| `sort_by` | string | - | Sortierung: `name`, `status`, `source_type`, `last_crawl`, `document_count`, `created_at`, `updated_at` |
| `sort_order` | string | `"asc"` | Sortierreihenfolge: `asc`, `desc` |

> **Hinweis:** Die Parameter `country`, `location_name` und `category_ids` existieren nicht mehr. Verwenden Sie `tags` fuer erweiterte Filterung.

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

**Response:**
```json
{
  "total": 500,
  "by_status": {
    "ACTIVE": 450,
    "PENDING": 30,
    "ERROR": 20
  },
  "by_country": {
    "DE": 400,
    "AT": 50,
    "CH": 50
  }
}
```

### GET /admin/sources/meta/tags
Alle verfuegbaren Tags fuer Datenquellen.

**Response:**
```json
{
  "tags": [
    {"name": "windenergie", "count": 150},
    {"name": "solar", "count": 80},
    {"name": "kommunal", "count": 200}
  ]
}
```

### GET /admin/sources/by-tags
Datenquellen nach Tags filtern.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `tags` | string | Komma-getrennte Tag-Namen |
| `match_all` | boolean | Alle Tags muessen vorhanden sein (default: false) |

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Stadt Musterstadt",
    "base_url": "https://musterstadt.de",
    "tags": ["windenergie", "kommunal"]
  }
]
```

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
  "status": "running",
  "running_jobs": 3,
  "pending_jobs": 12,
  "completed_today": 45,
  "failed_today": 2,
  "last_completed_at": "2025-01-15T14:30:00Z",
  "celery_connected": true,
  "worker_count": 4
}
```

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `status` | string | Aktueller Status (`idle`, `running`, `busy`) |
| `running_jobs` | int | Anzahl laufender Jobs |
| `pending_jobs` | int | Anzahl wartender Jobs |
| `completed_today` | int | Heute abgeschlossene Jobs |
| `failed_today` | int | Heute fehlgeschlagene Jobs |
| `last_completed_at` | datetime | Zeitpunkt des letzten abgeschlossenen Jobs |
| `celery_connected` | boolean | Celery-Verbindungsstatus |
| `worker_count` | int | Anzahl aktiver Celery-Worker |

### GET /admin/crawler/stats
Crawler-Statistiken (aggregierte Uebersicht).

> **NEU in v2.2.0**

**Response:**
```json
{
  "total_jobs": 1500,
  "running_jobs": 3,
  "completed_jobs": 1200,
  "failed_jobs": 150,
  "cancelled_jobs": 50,
  "total_documents": 45000,
  "total_pages_crawled": 125000,
  "avg_duration_seconds": 45.7
}
```

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `total_jobs` | int | Gesamtzahl aller Jobs |
| `running_jobs` | int | Aktuell laufende Jobs |
| `completed_jobs` | int | Erfolgreich abgeschlossene Jobs |
| `failed_jobs` | int | Fehlgeschlagene Jobs |
| `cancelled_jobs` | int | Abgebrochene Jobs |
| `total_documents` | int | Gesamtzahl Dokumente |
| `total_pages_crawled` | int | Gesamtzahl gecrawlter Seiten |
| `avg_duration_seconds` | float | Durchschnittliche Job-Dauer in Sekunden |

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

### POST /admin/crawler/jobs/{job_id}/retry
Fehlgeschlagenen oder abgebrochenen Job erneut starten.

> **NEU in v2.2.0**

Erstellt einen neuen Crawl-Job mit denselben Parametern wie der urspruengliche Job.

**Erlaubte Status:** `FAILED`, `CANCELLED`

**Response:**
```json
{
  "message": "Job retry started"
}
```

**Fehler:**
- `404 Not Found` - Job existiert nicht
- `400 Bad Request` - Job hat nicht den Status `FAILED` oder `CANCELLED`

### DELETE /admin/crawler/jobs/{job_id}
Einzelnen abgeschlossenen, fehlgeschlagenen oder abgebrochenen Job loeschen.

> **NEU in v2.2.0**

**Erlaubte Status:** `COMPLETED`, `FAILED`, `CANCELLED`

**Response:**
```json
{
  "message": "Job deleted"
}
```

**Fehler:**
- `404 Not Found` - Job existiert nicht
- `400 Bad Request` - Job ist noch im Status `RUNNING` oder `PENDING`

### DELETE /admin/crawler/jobs/failed
Alle fehlgeschlagenen Jobs auf einmal loeschen (Bulk-Delete).

> **NEU in v2.2.0**

**Berechtigung:** Editor

**Response:**
```json
{
  "message": "Deleted 42 failed jobs",
  "data": {
    "deleted_count": 42
  }
}
```

### DELETE /admin/crawler/jobs/cancelled
Alle abgebrochenen Jobs auf einmal loeschen (Bulk-Delete).

> **NEU in v2.2.0**

**Berechtigung:** Editor

**Response:**
```json
{
  "message": "Deleted 15 cancelled jobs",
  "data": {
    "deleted_count": 15
  }
}
```

### POST /admin/crawler/reanalyze
Dokumente erneut analysieren mit aktualisierten KI-Prompts.

> **Erweitert in v2.2.0:** Zusaetzliche Query-Parameter fuer feinere Steuerung.

**Berechtigung:** Admin

**Query-Parameter:**
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `category_id` | uuid | - | Nur Dokumente dieser Kategorie reanalysieren |
| `reanalyze_all` | boolean | `false` | Alle Dokumente (`true`) oder nur Low-Confidence (`false`) |

**Logik:**
- Ohne `category_id`: Alle Dokumente werden beruecksichtigt
- Mit `reanalyze_all=false` (Default): Nur Dokumente mit Confidence < 0.7
- Mit `reanalyze_all=true`: Alle Dokumente unabhaengig von Confidence

**Ablauf:**
1. Bestehende Extraktionen werden geloescht
2. Dokumente werden zur erneuten KI-Analyse in die Queue gestellt

**Response:**
```json
{
  "message": "Queued 156 documents for re-analysis"
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

---

## KI-gestuetzte Quellenentdeckung

Endpoints fuer die automatische Entdeckung neuer Datenquellen mittels KI.

### POST /admin/crawler/ai-discovery/discover
Standard-Quellenentdeckung (SERP-basiert).

Sucht nach Datenquellen basierend auf Suchbegriffen.

**Request Body:**
```json
{
  "prompt": "Kommunale Ratsinformationssysteme in NRW",
  "max_results": 50
}
```

**Response:**
```json
{
  "sources": [
    {
      "name": "Stadt Gummersbach",
      "url": "https://gummersbach.de/politik",
      "relevance_score": 0.85,
      "suggested_type": "WEBSITE"
    }
  ],
  "stats": {...}
}
```

### POST /admin/crawler/ai-discovery/discover-v2
KI-First Quellenentdeckung (V2) mit API-Erkennung.

> **NEU in v2.2.0**

Neuer Discovery-Flow:
1. KI generiert API-Vorschlaege basierend auf Prompt
2. API-Vorschlaege werden validiert (HTTP-Test)
3. Bei Erfolg: Daten direkt von API abrufen
4. Bei Misserfolg: Fallback zu SERP-basierter Suche

**Rate Limit:** 10 Requests pro Minute

**Request Body:**
```json
{
  "prompt": "Alle Bundesliga-Vereine mit Kontaktdaten",
  "max_results": 50,
  "search_depth": "standard",
  "skip_api_discovery": false
}
```

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `prompt` | string | required | Natuerlicher Suchprompt (3-1000 Zeichen) |
| `max_results` | int | 50 | Maximale Anzahl Ergebnisse (1-200) |
| `search_depth` | string | `standard` | `quick`, `standard`, oder `deep` |
| `skip_api_discovery` | boolean | `false` | Direkt zu SERP-Suche (ueberspringt KI-API-Vorschlaege) |

**Response:**
```json
{
  "api_sources": [
    {
      "api_name": "OpenLigaDB",
      "api_url": "https://www.openligadb.de/api/getavailableteams/bl1/2024",
      "api_type": "REST_JSON",
      "item_count": 18,
      "sample_items": [
        {"name": "Bayern München", "short_name": "FCB"}
      ],
      "tags": ["bundesliga", "fussball"],
      "field_mapping": {"name": "Vereinsname"}
    }
  ],
  "web_sources": [
    {
      "name": "Bundesliga.de",
      "url": "https://www.bundesliga.de/de/clubs",
      "relevance_score": 0.9
    }
  ],
  "api_suggestions": [
    {
      "api_name": "OpenLigaDB",
      "base_url": "https://www.openligadb.de",
      "endpoint": "/api/getavailableteams/bl1/2024",
      "description": "Offene Fussball-Datenbank",
      "api_type": "REST_JSON",
      "auth_required": false,
      "confidence": 0.85,
      "documentation_url": "https://www.openligadb.de/Doku"
    }
  ],
  "api_validations": [
    {
      "api_name": "OpenLigaDB",
      "is_valid": true,
      "status_code": 200,
      "item_count": 18,
      "error_message": null,
      "field_mapping": {"name": "Vereinsname"}
    }
  ],
  "stats": {
    "apis_suggested": 3,
    "apis_validated": 2,
    "apis_successful": 1,
    "items_extracted": 18
  },
  "warnings": [],
  "used_fallback": false,
  "from_template": false
}
```

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `api_sources` | array | Validierte APIs mit extrahierten Daten |
| `web_sources` | array | SERP-basierte Quellen (Fallback) |
| `api_suggestions` | array | Alle KI-generierten API-Vorschlaege |
| `api_validations` | array | Validierungsergebnisse fuer jeden Vorschlag |
| `used_fallback` | boolean | `true` wenn SERP-Fallback verwendet wurde |
| `from_template` | boolean | `true` wenn aus Template generiert |

### POST /admin/crawler/ai-discovery/import
Entdeckte Quellen importieren.

**Request Body:**
```json
{
  "category_id": "uuid",
  "sources": [
    {
      "name": "Stadt Gummersbach",
      "url": "https://gummersbach.de",
      "source_type": "WEBSITE"
    }
  ]
}
```

### GET /admin/crawler/ai-discovery/examples
Beispiel-Prompts fuer die KI-Entdeckung abrufen.

### POST /admin/crawler/ai-discovery/import-api-data
API-Daten als DataSources importieren.

> **NEU in v2.2.0**

Nimmt die extrahierten Items von einer validierten API und erstellt DataSource-Eintraege.

**Rate Limit:** 20 Requests pro Minute

**Request Body:**
```json
{
  "api_name": "OpenLigaDB",
  "api_url": "https://www.openligadb.de/api/getavailableteams/bl1/2024",
  "field_mapping": {"teamName": "name", "teamIconUrl": "logo"},
  "items": [
    {"teamName": "Bayern München", "teamIconUrl": "https://..."}
  ],
  "category_ids": ["uuid1", "uuid2"],
  "tags": ["bundesliga", "fussball"],
  "skip_duplicates": true
}
```

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `api_name` | string | required | Name der API (fuer Logging) |
| `api_url` | string | required | URL der API (fuer Referenz) |
| `field_mapping` | object | required | Feld-Mapping (z.B. `{"teamName": "name"}`) |
| `items` | array | required | Die zu importierenden Items (1-1000) |
| `category_ids` | uuid[] | `[]` | Kategorien fuer Zuordnung (max 20) |
| `tags` | string[] | `[]` | Tags fuer alle erstellten Sources |
| `skip_duplicates` | boolean | `true` | Duplikate ueberspringen |

**Response:**
```json
{
  "created": 18,
  "skipped": 2,
  "errors": []
}
```

---

## Crawl-Presets

> **NEU in v2.2.0:** Crawl-Presets ermoeglichen das Speichern und Wiederverwenden von Crawl-Konfigurationen.

### GET /admin/crawl-presets
Liste aller Crawl-Presets.

**Query-Parameter:**
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `page` | int | 1 | Seite (1-basiert) |
| `per_page` | int | 20 | Eintraege pro Seite (max 100) |
| `favorites_only` | boolean | `false` | Nur Favoriten anzeigen |
| `scheduled_only` | boolean | `false` | Nur Presets mit aktivem Schedule |
| `search` | string | - | Suche nach Name |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "NRW Windkraft-Gemeinden",
      "description": "Alle Gemeinden mit Windkraft-Projekten in NRW",
      "filters": {
        "category_id": "uuid",
        "entity_type_slug": "territorial_entity",
        "location_filter": "Nordrhein-Westfalen"
      },
      "category_id": "uuid",
      "source_count": 156,
      "last_run": "2025-01-15T14:30:00Z",
      "created_by": "uuid",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 5,
  "page": 1,
  "per_page": 20
}
```

### POST /admin/crawl-presets
Neues Crawl-Preset erstellen.

**Request Body:**
```json
{
  "name": "NRW Windkraft-Gemeinden",
  "description": "Alle Gemeinden mit Windkraft-Projekten",
  "filters": {
    "category_id": "uuid",
    "entity_type_slug": "territorial_entity",
    "location_filter": "Nordrhein-Westfalen",
    "tags": ["windkraft", "prioritaet"]
  }
}
```

### GET /admin/crawl-presets/{preset_id}
Einzelnes Preset abrufen.

### PUT /admin/crawl-presets/{preset_id}
Preset aktualisieren.

### DELETE /admin/crawl-presets/{preset_id}
Preset loeschen.

### GET /admin/crawl-presets/schedule-presets
Vordefinierte Schedule-Optionen fuer die UI abrufen.

> **NEU in v2.2.0**

**Response:**
```json
[
  {"label": "daily", "cron": "0 6 * * *", "description": "Daily at 6:00 AM"},
  {"label": "weekly_monday", "cron": "0 8 * * 1", "description": "Weekly on Monday at 8:00 AM"},
  {"label": "weekly_friday", "cron": "0 18 * * 5", "description": "Weekly on Friday at 6:00 PM"},
  {"label": "monthly", "cron": "0 0 1 * *", "description": "Monthly on the 1st at midnight"},
  {"label": "every_6_hours", "cron": "0 */6 * * *", "description": "Every 6 hours"}
]
```

### POST /admin/crawl-presets/{preset_id}/toggle-favorite
Favoriten-Status eines Presets umschalten.

> **NEU in v2.2.0**

Nur der Ersteller des Presets kann den Favoriten-Status aendern.

**Response:**
```json
{
  "id": "uuid",
  "is_favorite": true,
  "message": "Added to favorites"
}
```

**Fehler:**
- `404 Not Found` - Preset existiert nicht oder gehoert einem anderen User

### POST /admin/crawl-presets/from-filters
Preset aus aktueller Filter-Auswahl erstellen (UI-Helper).

> **NEU in v2.2.0**

**Request Body:**
```json
{
  "name": "Meine Gemeinden",
  "description": "Ausgewaehlte Gemeinden fuer regelmaessiges Crawling",
  "filters": {
    "category_id": "uuid",
    "entity_type_slug": "territorial_entity",
    "location_filter": "Bayern",
    "tags": ["prioritaet"]
  },
  "schedule_cron": "0 6 * * *",
  "schedule_enabled": true
}
```

| Parameter | Typ | Required | Beschreibung |
|-----------|-----|----------|--------------|
| `name` | string | ja | Name des Presets (1-255 Zeichen) |
| `description` | string | nein | Beschreibung (max. 2000 Zeichen) |
| `filters` | object | ja | Filter-Konfiguration (category_id required) |
| `schedule_cron` | string | nein | Cron-Expression fuer geplante Ausfuehrung |
| `schedule_enabled` | boolean | nein | Schedule aktivieren (default: false) |

**Response:** CrawlPreset-Objekt mit `filter_summary`

### POST /admin/crawl-presets/{preset_id}/execute
Preset ausfuehren (Crawls starten).

**Request Body:**
```json
{
  "force": false
}
```

**Response:**
```json
{
  "jobs_created": 156,
  "skipped": 12,
  "message": "Crawl jobs created from preset"
}
```

### POST /admin/crawl-presets/preview-filters
Vorschau fuer Filter-basierte Auswahl.

**Request Body (CrawlPresetFilters):**
```json
{
  "category_id": "uuid",
  "entity_type_slug": "territorial_entity",
  "source_status": "ACTIVE",
  "tags": ["windkraft"]
}
```

**Response:**
```json
{
  "source_count": 156,
  "sources_preview": [
    {"id": "uuid", "name": "Stadt Gummersbach", "url": "https://gummersbach.de"}
  ],
  "has_more": true
}
```

### POST /admin/crawl-presets/preview-entities
Vorschau fuer Entity-basierte Auswahl.

> **NEU in v2.2.0**

**Request Body (EntityCrawlPreviewRequest):**
```json
{
  "entity_ids": ["uuid1", "uuid2", "uuid3"],
  "category_id": "uuid"
}
```

**Response (EntityCrawlPreviewResponse):**
```json
{
  "entity_count": 3,
  "sources_count": 45,
  "sources_preview": [
    {"id": "uuid", "name": "Stadt Gummersbach", "url": "https://gummersbach.de"}
  ],
  "entities_without_sources": 1,
  "has_more": true
}
```

### POST /admin/crawl-presets/entity-crawl
Crawl fuer ausgewaehlte Entities starten.

> **NEU in v2.2.0**

Startet Crawls fuer alle DataSources, die mit den angegebenen Entities verknuepft sind.

**Request Body (EntityCrawlRequest):**
```json
{
  "entity_ids": ["uuid1", "uuid2", "uuid3"],
  "category_id": "uuid",
  "save_as_preset": true,
  "preset_name": "Meine Gemeinden",
  "selection_mode": "fixed",
  "force": false
}
```

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `entity_ids` | uuid[] | required | Liste der Entity-IDs |
| `category_id` | uuid | required | Kategorie fuer den Crawl |
| `save_as_preset` | boolean | false | Als Preset speichern |
| `preset_name` | string | - | Name fuer das Preset (required wenn save_as_preset=true) |
| `selection_mode` | string | "fixed" | `fixed` (speichert IDs) oder `dynamic` (speichert Filter) |
| `force` | boolean | false | Crawl erzwingen auch wenn kuerzlich gecrawlt |

**Response:**
```json
{
  "jobs_created": 45,
  "skipped": 3,
  "message": "Crawl jobs created",
  "preset_id": "uuid"
}
```

---

## SharePoint-Integration

Endpoints fuer Microsoft SharePoint Online-Integration via Microsoft Graph API.

> **Voraussetzung:** Azure AD App-Registrierung mit folgenden Berechtigungen:
> - `Sites.Read.All` (Anwendungsberechtigung)
> - `Files.Read.All` (Anwendungsberechtigung)
>
> **Environment Variables:**
> - `SHAREPOINT_TENANT_ID` - Azure AD Tenant ID
> - `SHAREPOINT_CLIENT_ID` - App-Client-ID
> - `SHAREPOINT_CLIENT_SECRET` - App-Client-Secret

### GET /admin/sharepoint/status
Verbindungsstatus und Konfiguration pruefen.

**Berechtigung:** Editor

**Response:**
```json
{
  "connected": true,
  "configured": true,
  "tenant_id": "a1b2c3d4...",
  "error": null
}
```

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `connected` | boolean | Verbindung erfolgreich |
| `configured` | boolean | Credentials sind gesetzt |
| `tenant_id` | string | Partieller Tenant-ID (zur Verifizierung) |
| `error` | string | Fehlermeldung bei Verbindungsproblemen |

### GET /admin/sharepoint/sites
Verfuegbare SharePoint-Sites auflisten.

**Berechtigung:** Editor

**Query-Parameter:**
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `query` | string | `*` | Suchbegriff fuer Sites |

**Response:**
```json
{
  "items": [
    {
      "id": "contoso.sharepoint.com,abc123,def456",
      "name": "Documents",
      "display_name": "Team Documents",
      "web_url": "https://contoso.sharepoint.com/sites/Documents"
    }
  ],
  "total": 5
}
```

### GET /admin/sharepoint/sites/{site_id}/drives
Dokumentbibliotheken (Drives) einer Site auflisten.

**Berechtigung:** Editor

**Response:**
```json
{
  "items": [
    {
      "id": "b!abc123",
      "name": "Shared Documents",
      "drive_type": "documentLibrary",
      "web_url": "https://contoso.sharepoint.com/sites/Documents/Shared%20Documents"
    }
  ],
  "total": 2,
  "site_id": "contoso.sharepoint.com,abc123,def456"
}
```

### GET /admin/sharepoint/sites/{site_id}/drives/{drive_id}/files
Dateien in einer Dokumentbibliothek auflisten.

**Berechtigung:** Editor

**Query-Parameter:**
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `folder_path` | string | `""` | Ordnerpfad innerhalb des Drive |
| `recursive` | boolean | `false` | Unterordner einschliessen |
| `limit` | int | `100` | Max. Dateien (1-500) |

**Response:**
```json
{
  "items": [
    {
      "id": "01ABC123",
      "name": "report.pdf",
      "size": 1048576,
      "mime_type": "application/pdf",
      "web_url": "https://contoso.sharepoint.com/sites/Documents/report.pdf",
      "parent_path": "/Windprojekte/2024",
      "created_at": "2024-01-15T10:30:00+00:00",
      "modified_at": "2024-03-20T14:45:00+00:00",
      "created_by": "Max Mustermann",
      "modified_by": "Erika Musterfrau"
    }
  ],
  "total": 25,
  "site_id": "...",
  "drive_id": "...",
  "folder_path": "/Windprojekte"
}
```

### GET /admin/sharepoint/config-example
Beispiel-Konfiguration fuer SharePoint-Datenquelle.

**Berechtigung:** Editor

**Response:**
```json
{
  "site_url": "contoso.sharepoint.com:/sites/Documents",
  "drive_name": "Shared Documents",
  "folder_path": "/Windprojekte",
  "file_extensions": [".pdf", ".docx", ".doc", ".xlsx", ".pptx"],
  "recursive": true,
  "exclude_patterns": ["~$*", "*.tmp", ".DS_Store"],
  "max_files": 1000,
  "file_paths_text": "/Documents/Report.pdf\n/Projects/Analysis.docx"
}
```

### POST /admin/sharepoint/test-connection
Verbindung mit optionaler Site-URL testen.

**Berechtigung:** Editor

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `site_url` | string | SharePoint Site URL (z.B. `contoso.sharepoint.com:/sites/Documents`) |

**Response:**
```json
{
  "authentication": true,
  "sites_accessible": true,
  "sites_found": 5,
  "target_site": "contoso.sharepoint.com:/sites/Documents",
  "target_site_accessible": true,
  "target_site_name": "Team Documents",
  "drives": [
    {"id": "b!abc123", "name": "Shared Documents", "type": "documentLibrary"}
  ],
  "errors": []
}
```

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `authentication` | boolean | OAuth2-Authentifizierung erfolgreich |
| `sites_accessible` | boolean | Sites koennen aufgelistet werden |
| `sites_found` | int | Anzahl gefundener Sites |
| `target_site` | string | Geprueftes Site-URL |
| `target_site_accessible` | boolean | Ziel-Site erreichbar |
| `target_site_name` | string | Name der Ziel-Site |
| `drives` | array | Gefundene Dokumentbibliotheken |
| `errors` | array | Fehlermeldungen |

---

## SharePoint als Datenquelle verwenden

### Schritt 1: Azure AD App registrieren

1. **Azure Portal** → App registrations → New registration
2. **Name**: `CaeliCrawler SharePoint` (beliebig)
3. **Supported account types**: Single tenant
4. **API Permissions** hinzufuegen:
   - Microsoft Graph → Application permissions:
     - `Sites.Read.All`
     - `Files.Read.All`
5. **Admin Consent** erteilen (erfordert Azure AD Admin)
6. **Client Secret** erstellen unter Certificates & secrets
7. **IDs notieren**:
   - Application (client) ID → `SHAREPOINT_CLIENT_ID`
   - Directory (tenant) ID → `SHAREPOINT_TENANT_ID`
   - Client Secret Value → `SHAREPOINT_CLIENT_SECRET`

### Schritt 2: Environment Variables setzen

```bash
export SHAREPOINT_TENANT_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
export SHAREPOINT_CLIENT_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
export SHAREPOINT_CLIENT_SECRET="your-client-secret-value"
```

### Schritt 3: Datenquelle anlegen

```json
POST /admin/sources
{
  "name": "SharePoint Kundenvertraege",
  "source_type": "SHAREPOINT",
  "base_url": "https://contoso.sharepoint.com/sites/Documents",
  "category_ids": ["uuid"],
  "crawl_config": {
    "site_url": "contoso.sharepoint.com:/sites/Documents",
    "drive_name": "Shared Documents",
    "folder_path": "/Vertraege/Kunden",
    "file_extensions": [".pdf", ".docx"],
    "recursive": true,
    "exclude_patterns": ["~$*", "*.tmp"],
    "max_files": 1000
  }
}
```

### Schritt 4: Kategorie mit Keywords konfigurieren

Fuer effiziente Analyse sollte die Kategorie `search_terms` enthalten:

```json
PUT /admin/categories/{category_id}
{
  "search_terms": ["Klausel", "Vertragsbedingung", "§12"],
  "ai_extraction_prompt": "Analysiere den Vertrag und extrahiere..."
}
```

Dokumente ohne diese Keywords werden automatisch gefiltert (ProcessingStatus: FILTERED) und nicht zur KI-Analyse geschickt.

### Unterstuetzte Dateitypen

| Extension | Typ | Unterstuetzt |
|-----------|-----|--------------|
| `.pdf` | PDF | ✅ |
| `.docx` | Word (2007+) | ✅ |
| `.doc` | Word (Legacy) | ✅ |
| `.xlsx` | Excel (2007+) | ✅ |
| `.xls` | Excel (Legacy) | ✅ |
| `.pptx` | PowerPoint (2007+) | ✅ |
| `.ppt` | PowerPoint (Legacy) | ✅ |
| `.txt` | Text | ✅ |
| `.rtf` | Rich Text | ✅ |
| `.html/.htm` | HTML | ✅ |
