# CaeliCrawler API Reference

Vollständige technische Dokumentation aller API-Endpunkte.

**Base URL:** `http://localhost:8000/api`

**Interaktive Dokumentation:** `http://localhost:8000/docs` (Swagger UI)

---

## Inhaltsverzeichnis

### Authentifizierung & Benutzer
1. [Authentifizierung](#authentifizierung) **NEU**
2. [Benutzerverwaltung (Admin)](#benutzerverwaltung-admin) **NEU**

### Admin API
3. [Kategorien](#kategorien)
4. [Datenquellen](#datenquellen)
5. [Crawler & Jobs](#crawler--jobs)
6. [KI-Tasks & Dokumentenverarbeitung](#ki-tasks--dokumentenverarbeitung)
7. [Locations (Standorte)](#locations-standorte)
8. [Audit Logging](#audit-logging) **NEU**
9. [Versionierung](#versionierung) **NEU**
10. [Benachrichtigungen](#benachrichtigungen) **NEU**
11. [PySis Integration](#pysis-integration)

### Public API v1
12. [Public API (v1/data)](#public-api-v1data)
13. [Gemeinden & Reports](#gemeinden--reports)
14. [Export](#export)
15. [Entity-Facet System](#entity-facet-system)
16. [KI-Assistant](#ki-assistant) **NEU**
17. [Smart Query & Analyse](#smart-query--analyse) **NEU**

### System
18. [System & Health](#system--health)
19. [Authentifizierung & Sicherheit](#authentifizierung--sicherheit)
20. [Rate Limiting](#rate-limiting)

---

## Authentifizierung

Die API verwendet JWT-basierte Authentifizierung. Alle geschützten Endpoints erfordern einen gültigen Bearer-Token im Authorization-Header.

### POST /api/auth/login
Benutzer authentifizieren und JWT-Token erhalten.

**Rate Limiting:** 5 Versuche pro Minute pro IP-Adresse. Nach 10 fehlgeschlagenen Versuchen innerhalb von 15 Minuten wird die IP temporär blockiert.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "Max Mustermann",
    "role": "ADMIN",
    "is_active": true,
    "is_superuser": false,
    "last_login": "2025-01-15T14:30:00Z",
    "created_at": "2025-01-01T00:00:00Z"
  }
}
```

**Fehler:**
- `401 Unauthorized` - Ungültige E-Mail oder Passwort
- `403 Forbidden` - Benutzerkonto deaktiviert
- `429 Too Many Requests` - Rate Limit erreicht

### GET /api/auth/me
Profil des aktuell angemeldeten Benutzers abrufen.

**Header:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "Max Mustermann",
  "role": "ADMIN",
  "is_active": true,
  "is_superuser": false,
  "last_login": "2025-01-15T14:30:00Z",
  "created_at": "2025-01-01T00:00:00Z"
}
```

### POST /api/auth/change-password
Passwort des aktuellen Benutzers ändern.

**Rate Limiting:** 3 Versuche pro 5 Minuten.

**Request Body:**
```json
{
  "current_password": "oldPassword123",
  "new_password": "newSecurePassword456"
}
```

**Passwort-Anforderungen:**
- Minimum 8 Zeichen
- Mindestens ein Großbuchstabe (A-Z)
- Mindestens ein Kleinbuchstabe (a-z)
- Mindestens eine Ziffer (0-9)

**Response:**
```json
{
  "message": "Password changed successfully"
}
```

**Fehler:**
- `400 Bad Request` - Aktuelles Passwort falsch oder neues Passwort erfüllt Anforderungen nicht

### POST /api/auth/logout
Aktuellen Benutzer abmelden und Token invalidieren.

**Header:** `Authorization: Bearer <token>`

**Token-Blacklisting:** Der aktuelle JWT-Token wird auf eine Blacklist gesetzt und für alle zukünftigen Anfragen abgelehnt.

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

### POST /api/auth/check-password-strength
Passwort-Stärke prüfen ohne es zu ändern (für Echtzeit-Feedback im UI).

**Request Body:**
```json
{
  "password": "testPassword123"
}
```

**Response:**
```json
{
  "is_valid": true,
  "score": 75,
  "errors": [],
  "suggestions": ["Sonderzeichen verwenden für mehr Sicherheit"],
  "requirements": "Minimum 8 Zeichen, Groß-/Kleinschreibung, Ziffern"
}
```

---

## Benutzerverwaltung (Admin)

Admin-Endpoints für Benutzerverwaltung. Erfordert Admin-Rolle.

### GET /api/admin/users
Alle Benutzer auflisten mit Pagination und Filterung.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `page` | int | Seite (default: 1) |
| `per_page` | int | Einträge pro Seite (1-100, default: 20) |
| `role` | string | Filter nach Rolle (ADMIN, EDITOR, VIEWER) |
| `is_active` | boolean | Nur aktive/inaktive Benutzer |
| `search` | string | Suche in E-Mail oder Name |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "full_name": "Max Mustermann",
      "role": "ADMIN",
      "is_active": true,
      "is_superuser": false,
      "last_login": "2025-01-15T14:30:00Z",
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-15T14:30:00Z"
    }
  ],
  "total": 50,
  "page": 1,
  "per_page": 20,
  "pages": 3
}
```

### POST /api/admin/users
Neuen Benutzer erstellen.

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "password": "securePassword123",
  "full_name": "Neuer Benutzer",
  "role": "EDITOR",
  "is_active": true,
  "is_superuser": false
}
```

**Response:** `201 Created` mit Benutzer-Objekt

**Fehler:**
- `409 Conflict` - E-Mail bereits vergeben
- `409 Conflict` - Passwort erfüllt Anforderungen nicht

### GET /api/admin/users/{user_id}
Einzelnen Benutzer abrufen.

### PUT /api/admin/users/{user_id}
Benutzer aktualisieren.

**Request Body:**
```json
{
  "email": "updated@example.com",
  "full_name": "Aktualisierter Name",
  "role": "ADMIN",
  "is_active": true
}
```

**Einschränkungen:**
- Eigene Admin-Rolle kann nicht entfernt werden
- Eigenes Konto kann nicht deaktiviert werden

### DELETE /api/admin/users/{user_id}
Benutzer löschen.

**Einschränkungen:**
- Eigenes Konto kann nicht gelöscht werden

**Response:**
```json
{
  "message": "User user@example.com deleted successfully"
}
```

### POST /api/admin/users/{user_id}/reset-password
Passwort eines Benutzers zurücksetzen (Admin-Funktion).

**Request Body:**
```json
{
  "new_password": "newSecurePassword456"
}
```

**Response:**
```json
{
  "message": "Password for user@example.com reset successfully"
}
```

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

## Audit Logging

Admin-Endpoints für Audit-Log-Verwaltung. Erfordert Admin-Rolle.

### GET /api/admin/audit
Audit-Log-Einträge auflisten mit Filterung und Pagination.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `page` | int | Seite (default: 1) |
| `per_page` | int | Einträge pro Seite (1-100, default: 50) |
| `action` | string | Filter nach Aktion (CREATE, UPDATE, DELETE, LOGIN, LOGOUT) |
| `entity_type` | string | Filter nach Entity-Typ |
| `entity_id` | uuid | Filter nach Entity-ID |
| `user_id` | uuid | Filter nach Benutzer |
| `start_date` | datetime | Änderungen seit |
| `end_date` | datetime | Änderungen bis |

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

### GET /api/admin/audit/entity/{entity_type}/{entity_id}
Änderungshistorie für eine spezifische Entity.

**Response:** Wie `GET /api/admin/audit`

### GET /api/admin/audit/user/{user_id}
Änderungshistorie eines Benutzers.

**Response:** Wie `GET /api/admin/audit`

### GET /api/admin/audit/stats
Audit-Log-Statistiken.

**Response:**
```json
{
  "total_entries": 12345,
  "entries_today": 156,
  "entries_this_week": 890,
  "actions_breakdown": {
    "CREATE": 4500,
    "UPDATE": 6800,
    "DELETE": 500,
    "LOGIN": 400,
    "LOGOUT": 145
  },
  "top_users": [
    {"email": "admin@example.com", "count": 1500}
  ],
  "top_entity_types": [
    {"entity_type": "DataSource", "count": 5000}
  ]
}
```

---

## Versionierung

Endpoints für Versionshistorie von Entities. Erfordert mindestens Viewer-Rolle.

### GET /api/admin/versions/{entity_type}/{entity_id}
Versionshistorie einer Entity abrufen.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `limit` | int | Max. Einträge (1-100, default: 50) |
| `offset` | int | Offset (default: 0) |

**Unterstützte Entity-Typen:**
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
      "change_reason": "Aktiviert nach Prüfung",
      "created_at": "2025-01-15T14:30:00Z"
    }
  ],
  "total": 5,
  "entity_type": "DataSource",
  "entity_id": "uuid"
}
```

### GET /api/admin/versions/{entity_type}/{entity_id}/{version_number}
Details einer spezifischen Version abrufen.

**Response:** Einzelnes Version-Objekt

### GET /api/admin/versions/{entity_type}/{entity_id}/{version_number}/state
Entity-Zustand zu einer bestimmten Version rekonstruieren.

**Response:**
```json
{
  "entity_type": "DataSource",
  "entity_id": "uuid",
  "version_number": 3,
  "state": {
    "name": "Stadt Musterstadt",
    "base_url": "https://musterstadt.de",
    "status": "PENDING",
    "last_crawl": null
  }
}
```

---

## Benachrichtigungen

Endpoints für Benachrichtigungsverwaltung.

### E-Mail-Adressen

#### GET /api/admin/notifications/email-addresses
E-Mail-Adressen des aktuellen Benutzers auflisten.

**Response:**
```json
[
  {
    "id": "uuid",
    "email": "notification@example.com",
    "label": "Arbeit",
    "is_verified": true,
    "is_primary": false,
    "created_at": "2025-01-01T00:00:00Z"
  }
]
```

#### POST /api/admin/notifications/email-addresses
Neue E-Mail-Adresse hinzufügen.

**Request Body:**
```json
{
  "email": "new@example.com",
  "label": "Privat"
}
```

#### DELETE /api/admin/notifications/email-addresses/{email_id}
E-Mail-Adresse löschen.

#### POST /api/admin/notifications/email-addresses/{email_id}/verify
E-Mail-Adresse verifizieren.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `token` | string | Verifizierungs-Token aus E-Mail |

#### POST /api/admin/notifications/email-addresses/{email_id}/resend-verification
Verifizierungs-E-Mail erneut senden.

### Benachrichtigungsregeln

#### GET /api/admin/notifications/rules
Benachrichtigungsregeln des Benutzers auflisten.

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Neue Dokumente",
    "description": "Benachrichtigung bei neuen Dokumenten",
    "event_type": "NEW_DOCUMENT",
    "channel": "EMAIL",
    "conditions": {"category_id": "uuid"},
    "channel_config": {"email_id": "uuid"},
    "digest_enabled": true,
    "digest_frequency": "daily",
    "is_active": true,
    "trigger_count": 45,
    "last_triggered": "2025-01-15T10:00:00Z",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-15T10:00:00Z"
  }
]
```

#### POST /api/admin/notifications/rules
Neue Benachrichtigungsregel erstellen.

**Request Body:**
```json
{
  "name": "Crawl-Fehler",
  "description": "Benachrichtigung bei Crawl-Fehlern",
  "event_type": "CRAWL_FAILED",
  "channel": "WEBHOOK",
  "conditions": {},
  "channel_config": {"url": "https://webhook.example.com"},
  "digest_enabled": false,
  "is_active": true
}
```

**Event-Typen:**
- `NEW_DOCUMENT` - Neue Dokumente gefunden
- `DOCUMENT_CHANGED` - Dokument geändert
- `DOCUMENT_REMOVED` - Dokument entfernt
- `CRAWL_STARTED` - Crawl gestartet
- `CRAWL_COMPLETED` - Crawl abgeschlossen
- `CRAWL_FAILED` - Crawl fehlgeschlagen
- `AI_ANALYSIS_COMPLETED` - KI-Analyse abgeschlossen
- `HIGH_CONFIDENCE_RESULT` - Relevantes Ergebnis gefunden
- `SOURCE_STATUS_CHANGED` - Quellenstatus geändert
- `SOURCE_ERROR` - Fehler bei Quelle

**Kanäle:**
- `EMAIL` - E-Mail-Benachrichtigung
- `WEBHOOK` - HTTP-Webhook
- `IN_APP` - In-App-Benachrichtigung
- `MS_TEAMS` - Microsoft Teams (demnächst)

#### GET /api/admin/notifications/rules/{rule_id}
Regel abrufen.

#### PUT /api/admin/notifications/rules/{rule_id}
Regel aktualisieren.

#### DELETE /api/admin/notifications/rules/{rule_id}
Regel löschen.

### Benachrichtigungen

#### GET /api/admin/notifications/notifications
Benachrichtigungen des Benutzers auflisten.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `status` | string | PENDING, SENT, DELIVERED, READ, FAILED |
| `channel` | string | EMAIL, WEBHOOK, IN_APP, MS_TEAMS |
| `event_type` | string | Event-Typ |
| `page` | int | Seite |
| `per_page` | int | Einträge pro Seite |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "event_type": "NEW_DOCUMENT",
      "channel": "IN_APP",
      "title": "Neues Dokument gefunden",
      "body": "In Stadt Musterstadt wurde ein neues Dokument gefunden.",
      "status": "READ",
      "related_entity_type": "Document",
      "related_entity_id": "uuid",
      "sent_at": "2025-01-15T10:00:00Z",
      "read_at": "2025-01-15T10:05:00Z",
      "created_at": "2025-01-15T10:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "per_page": 20,
  "pages": 5
}
```

#### GET /api/admin/notifications/notifications/unread-count
Anzahl ungelesener In-App-Benachrichtigungen.

**Response:**
```json
{
  "count": 5
}
```

#### GET /api/admin/notifications/notifications/{notification_id}
Einzelne Benachrichtigung abrufen.

#### POST /api/admin/notifications/notifications/{notification_id}/read
Benachrichtigung als gelesen markieren.

#### POST /api/admin/notifications/notifications/read-all
Alle Benachrichtigungen als gelesen markieren.

### Webhook-Test

#### POST /api/admin/notifications/test-webhook
Webhook-URL testen.

**Request Body:**
```json
{
  "url": "https://webhook.example.com/notify",
  "auth": {
    "type": "bearer",
    "token": "abc123"
  }
}
```

**Response:**
```json
{
  "success": true,
  "status_code": 200,
  "response": "OK"
}
```

### Benutzer-Einstellungen

#### GET /api/admin/notifications/preferences
Benachrichtigungs-Einstellungen abrufen.

#### PUT /api/admin/notifications/preferences
Benachrichtigungs-Einstellungen aktualisieren.

**Request Body:**
```json
{
  "notifications_enabled": true,
  "notification_digest_time": "09:00"
}
```

### Metadaten

#### GET /api/admin/notifications/event-types
Verfügbare Event-Typen abrufen.

#### GET /api/admin/notifications/channels
Verfügbare Kanäle abrufen.

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

#### GET /v1/entities/filter-options/location
Verfügbare Filter-Optionen für Standort-Felder abrufen.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `country` | string | Filter admin_level_1 Optionen nach Land |
| `admin_level_1` | string | Filter admin_level_2 Optionen nach Bundesland |

**Response:**
```json
{
  "countries": ["DE", "AT", "CH"],
  "admin_level_1": ["Baden-Württemberg", "Bayern", "Berlin", "..."],
  "admin_level_2": ["Oberbergischer Kreis", "Rheinisch-Bergischer Kreis", "..."]
}
```

**Hinweis:** Die admin_level Optionen werden entsprechend der gewählten übergeordneten Ebene gefiltert.

#### GET /v1/entities/filter-options/attributes
Verfügbare Filter-Optionen für core_attributes basierend auf Entity-Typ Schema.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `entity_type_slug` | string | **Erforderlich.** Entity-Typ Slug |
| `attribute_key` | string | Spezifisches Attribut für Wertabfrage |

**Response (ohne attribute_key):**
```json
{
  "entity_type_slug": "municipality",
  "entity_type_name": "Gemeinde",
  "attributes": [
    {
      "key": "locality_type",
      "title": "Gemeindetyp",
      "description": "Art der Gemeinde",
      "type": "string",
      "format": null
    },
    {
      "key": "population",
      "title": "Einwohnerzahl",
      "description": null,
      "type": "integer",
      "format": null
    }
  ]
}
```

**Response (mit attribute_key):**
```json
{
  "entity_type_slug": "municipality",
  "entity_type_name": "Gemeinde",
  "attributes": [...],
  "attribute_values": {
    "locality_type": ["Stadt", "Gemeinde", "Kreisfreie Stadt", "Große Kreisstadt"]
  }
}
```

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

## KI-Assistant

Interaktiver KI-Assistant für natürlichsprachliche Interaktionen mit dem System.

### POST /api/v1/assistant/chat
Nachricht an den KI-Assistant senden.

**Request Body:**
```json
{
  "message": "Zeige mir alle Bürgermeister in NRW",
  "context": {
    "current_route": "/entities/municipality",
    "current_entity_id": null,
    "current_entity_type": "municipality",
    "view_mode": "list",
    "available_actions": ["filter", "search", "navigate"]
  },
  "conversation_history": [
    {
      "role": "user",
      "content": "Vorherige Nachricht",
      "timestamp": "2025-01-15T14:25:00Z"
    },
    {
      "role": "assistant",
      "content": "Vorherige Antwort",
      "timestamp": "2025-01-15T14:25:05Z"
    }
  ],
  "mode": "read"
}
```

**Modi:**
- `read` - Nur Abfragen und Navigation (Standard)
- `write` - Erlaubt Inline-Bearbeitungen mit Preview/Bestätigung

**Slash-Kommandos:**
- `/help [topic]` - Hilfe anzeigen
- `/search <query>` - Entities suchen
- `/create <details>` - Neuen Datensatz erstellen (Weiterleitung zu Smart Query)
- `/summary` - Aktuelle Entity zusammenfassen
- `/navigate <entity>` - Zu einer Entity navigieren

**Response-Typen:**

1. **Query Result:**
```json
{
  "success": true,
  "response_type": "query_result",
  "response": {
    "results": [...],
    "summary": "Gefunden: 15 Bürgermeister in NRW",
    "follow_up_suggestions": ["Nach Alter filtern", "Nur aktive zeigen"]
  },
  "suggested_actions": ["Ergebnisse filtern", "Details anzeigen"]
}
```

2. **Action Preview (im Write-Modus):**
```json
{
  "success": true,
  "response_type": "action_preview",
  "response": {
    "action_type": "update_entity",
    "entity_id": "uuid",
    "changes": {"position": {"old": "Bürgermeister", "new": "Oberbürgermeister"}},
    "confirmation_required": true,
    "confirmation_message": "Position von Max Müller ändern?"
  }
}
```

3. **Navigation:**
```json
{
  "success": true,
  "response_type": "navigation",
  "response": {
    "target_route": "/entities/person/max-mueller",
    "target_entity_id": "uuid",
    "message": "Navigiere zu Max Müller"
  }
}
```

4. **Help:**
```json
{
  "success": true,
  "response_type": "help",
  "response": {
    "topics": ["Suche", "Navigation", "Bearbeitung"],
    "suggested_commands": ["/search", "/summary"]
  }
}
```

### POST /api/v1/assistant/execute-action
Bestätigte Aktion ausführen.

**Request Body:**
```json
{
  "action": {
    "action_type": "update_entity",
    "entity_id": "uuid",
    "changes": {"position": "Oberbürgermeister"}
  },
  "context": {
    "current_route": "/entities/person/max-mueller"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Position von Max Müller wurde aktualisiert",
  "affected_entity_id": "uuid",
  "affected_entity_name": "Max Müller",
  "refresh_required": true
}
```

### GET /api/v1/assistant/commands
Liste verfügbarer Slash-Kommandos abrufen.

**Response:**
```json
[
  {
    "command": "/help",
    "description": "Hilfe anzeigen",
    "usage": "/help [topic]",
    "examples": ["/help", "/help suche"]
  },
  {
    "command": "/search",
    "description": "Entities suchen",
    "usage": "/search <suchbegriff>",
    "examples": ["/search Gummersbach", "/search Bürgermeister"]
  }
]
```

### GET /api/v1/assistant/suggestions
Kontextbezogene Vorschläge basierend auf aktuellem Standort.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `route` | string | Aktuelle Route |
| `entity_type` | string | Aktueller Entity-Typ |
| `entity_id` | string | Aktuelle Entity-ID |

**Response:**
```json
{
  "suggestions": [
    {"label": "Zusammenfassung", "query": "/summary"},
    {"label": "Pain Points", "query": "Zeige Pain Points"},
    {"label": "Relationen", "query": "Zeige alle Relationen"}
  ]
}
```

---

## Smart Query & Analyse

KI-gestützte Abfragen und Schreiboperationen in natürlicher Sprache.

### POST /api/v1/analysis/smart-query
KI-gestützte natürliche Sprache Abfragen ausführen.

**Request Body:**
```json
{
  "question": "Zeige mir auf welche künftige Events wichtige Entscheider-Personen von Gemeinden gehen",
  "allow_write": false
}
```

**Beispiel-Abfragen:**
- "Welche Bürgermeister sprechen auf Windenergie-Konferenzen?"
- "Zeige mir alle Pain Points von Gemeinden in NRW"
- "Wo kann ich Entscheider aus Bayern in den nächsten 90 Tagen treffen?"

**Response:**
```json
{
  "success": true,
  "query_type": "search",
  "interpretation": {
    "intent": "find_event_attendance",
    "filters": {
      "entity_types": ["person"],
      "positions": ["Bürgermeister", "Landrat"],
      "time_filter": "future"
    }
  },
  "results": [
    {
      "person_name": "Max Müller",
      "position": "Bürgermeister",
      "municipality": "Gummersbach",
      "event": "Windenergie-Konferenz 2025",
      "event_date": "2025-03-15",
      "confidence": 0.95
    }
  ],
  "summary": "15 Entscheider besuchen in den nächsten 90 Tagen relevante Events"
}
```

### POST /api/v1/analysis/smart-write
Schreib-Kommandos in natürlicher Sprache mit Preview-Unterstützung.

**Workflow:**
1. Sende Kommando mit `preview_only=true` → Erhalte Vorschau
2. Überprüfe die Vorschau
3. Sende gleiches Kommando mit `preview_only=false, confirmed=true` → Ausführung

**Request Body:**
```json
{
  "question": "Erstelle eine neue Person Max Müller, Bürgermeister von Gummersbach",
  "preview_only": true,
  "confirmed": false
}
```

**Beispiel-Kommandos:**
- "Erstelle eine Person Hans Schmidt, Landrat von Oberberg"
- "Füge einen Pain Point für Münster hinzu: Personalmangel in der IT"
- "Verknüpfe Max Müller mit Gummersbach als Arbeitgeber"
- "Starte Crawls für alle Gummersbach Datenquellen"

**Unterstützte Operationen:**
| Operation | Beschreibung |
|-----------|--------------|
| `create_entity` | Entity erstellen (Person, Gemeinde, Organisation, Event) |
| `create_entity_type` | Neuen Entity-Typ erstellen |
| `create_facet` | Facet hinzufügen (Pain Point, Positive Signal, Kontakt) |
| `create_relation` | Verknüpfung zwischen Entities erstellen |
| `create_category_setup` | Category mit Datenquellen-Verknüpfung erstellen |
| `start_crawl` | Crawl für gefilterte Datenquellen starten |
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
      "name": "Max Müller",
      "core_attributes": {"position": "Bürgermeister"}
    },
    "explanation": "Erstellt eine neue Person mit Position Bürgermeister"
  },
  "preview": {
    "operation_de": "Entity erstellen",
    "description": "Erstellt eine neue Person mit Position Bürgermeister",
    "details": [
      "Typ: Person",
      "Name: Max Müller",
      "Position: Bürgermeister"
    ]
  },
  "original_question": "Erstelle eine neue Person Max Müller, Bürgermeister von Gummersbach"
}
```

**Response (Execute):**
```json
{
  "success": true,
  "mode": "write",
  "message": "Person 'Max Müller' wurde erfolgreich erstellt",
  "created_entity": {
    "id": "uuid",
    "name": "Max Müller",
    "slug": "max-mueller"
  }
}
```

### GET /api/v1/analysis/smart-query/examples
Beispiele für Smart Query abrufen.

**Response:**
```json
{
  "read_examples": [
    {
      "question": "Zeige mir auf welche künftige Events wichtige Entscheider-Personen von Gemeinden gehen",
      "description": "Findet alle Personen mit Positionen wie Bürgermeister, Landrat etc. und deren zukünftige Event-Teilnahmen"
    },
    {
      "question": "Welche Bürgermeister sprechen auf Windenergie-Konferenzen?",
      "description": "Filtert nach Position 'Bürgermeister' und Event-Attendance Facets"
    }
  ],
  "write_examples": [
    {
      "question": "Erstelle eine neue Person Max Müller, Bürgermeister von Gummersbach",
      "description": "Erstellt eine Person-Entity mit Position 'Bürgermeister'"
    },
    {
      "question": "Füge einen Pain Point für Münster hinzu: Personalmangel in der IT",
      "description": "Erstellt einen Pain Point Facet für die Gemeinde Münster"
    }
  ],
  "supported_filters": {
    "time": ["künftig", "vergangen", "zukünftig", "in den nächsten X Tagen/Monaten"],
    "positions": ["Bürgermeister", "Landrat", "Dezernent", "Entscheider", "Amtsleiter"],
    "entity_types": ["Person", "Gemeinde", "Event", "Organisation"],
    "facet_types": ["Pain Points", "Positive Signale", "Event-Teilnahmen", "Kontakte"]
  },
  "write_operations": {
    "create_entity": ["Erstelle", "Neue/r/s", "Anlegen"],
    "create_facet": ["Füge hinzu", "Neuer Pain Point", "Neues Positive Signal"],
    "create_relation": ["Verknüpfe", "Verbinde", "arbeitet für", "ist Mitglied von"]
  }
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

Die API implementiert Rate Limiting über Redis:

| Endpoint | Limit | Beschreibung |
|----------|-------|--------------|
| `POST /api/auth/login` | 5/Minute | Login-Versuche pro IP |
| `POST /api/auth/login` | 10/15Min | Nach 10 Fehlversuchen temporäre Sperre |
| `POST /api/auth/change-password` | 3/5Min | Passwortänderungen |
| `/api/admin/*` | 100/Minute | Admin-Endpoints |
| `/api/v1/*` | 1000/Minute | Public API Endpoints |

**Response bei Überschreitung:**
```json
{
  "detail": "Rate limit exceeded. Retry in 45 seconds.",
  "retry_after": 45
}
```

**HTTP Status:** `429 Too Many Requests`

**Header:**
- `X-RateLimit-Limit`: Maximale Anzahl Requests
- `X-RateLimit-Remaining`: Verbleibende Requests
- `X-RateLimit-Reset`: Unix-Timestamp des Reset-Zeitpunkts

---

## Authentifizierung & Sicherheit

Die API verwendet JWT-basierte Authentifizierung mit folgenden Sicherheitsfunktionen:

### JWT Token
- **Token-Typ:** Bearer Token
- **Header:** `Authorization: Bearer <token>`
- **Lebensdauer:** 24 Stunden (konfigurierbar)
- **Signatur:** HS256

### Token Blacklist
Bei Logout wird der Token auf eine Redis-basierte Blacklist gesetzt und sofort invalidiert.

### Passwort-Policy
- Minimum 8 Zeichen
- Mindestens ein Großbuchstabe (A-Z)
- Mindestens ein Kleinbuchstabe (a-z)
- Mindestens eine Ziffer (0-9)

### Rollen
| Rolle | Beschreibung |
|-------|--------------|
| `ADMIN` | Vollzugriff auf alle Funktionen |
| `EDITOR` | Lese- und Schreibzugriff auf Daten |
| `VIEWER` | Nur Lesezugriff |

### Security Headers (Production)
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'
```

### Audit Logging
Alle Änderungen werden im Audit-Log protokolliert:
- Benutzer-ID
- Aktion (CREATE, UPDATE, DELETE)
- Entity-Typ und ID
- Änderungen (Diff)
- IP-Adresse
- Zeitstempel
