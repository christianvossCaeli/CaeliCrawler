# External APIs - API Reference

Dokumentation der externen API-Konfiguration und Synchronisation.

## Uebersicht

Das External APIs Modul ermoeglicht die automatische Synchronisation von Daten aus externen APIs (z.B. Wikidata, OParl, Custom APIs) mit dem Entity-System.

**Base URL:** `/api/admin/external-apis`

**Authentifizierung:** Alle Endpoints erfordern Admin-Berechtigung.

---

## Endpoints

### API-Konfigurationen auflisten

```http
GET /admin/external-apis
```

**Query Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| is_active | boolean | Nach Aktivstatus filtern |
| api_type | string | Nach API-Typ filtern |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Wikidata NRW Gemeinden",
      "description": "...",
      "api_type": "wikidata",
      "api_base_url": "https://query.wikidata.org/sparql",
      "is_active": true,
      "sync_enabled": true,
      "sync_interval_hours": 24,
      "last_sync_at": "2025-12-21T10:00:00Z",
      "last_sync_status": "success"
    }
  ],
  "total": 1
}
```

---

### Konfiguration erstellen

```http
POST /admin/external-apis
```

**Request Body:**
```json
{
  "name": "Wikidata NRW Gemeinden",
  "description": "Synchronisiert alle Gemeinden in NRW von Wikidata",
  "api_type": "wikidata",
  "api_base_url": "https://query.wikidata.org/sparql",
  "api_endpoint": null,
  "auth_type": null,
  "auth_config": {},
  "sync_interval_hours": 24,
  "sync_enabled": true,
  "entity_type_slug": "municipality",
  "id_field": "wikidata_id",
  "name_field": "label",
  "field_mappings": {
    "population": "population",
    "website": "website"
  },
  "location_fields": {
    "latitude": "lat",
    "longitude": "lon"
  },
  "request_config": {
    "sparql_query": "SELECT ?item ?label WHERE {...}"
  },
  "mark_missing_inactive": false,
  "inactive_after_days": 30,
  "ai_linking_enabled": true,
  "link_to_entity_types": ["person", "organization"],
  "data_source_id": null
}
```

**Response:** `201 Created` mit erstellter Konfiguration

---

### Konfiguration abrufen

```http
GET /admin/external-apis/{config_id}
```

**Response:** Konfiguration mit erweiterten Statistiken:
```json
{
  "id": "uuid",
  "name": "...",
  "...": "...",
  "total_sync_records": 1234,
  "active_records": 1200,
  "missing_records": 30,
  "archived_records": 4,
  "total_entities": 1150
}
```

---

### Konfiguration aktualisieren

```http
PATCH /admin/external-apis/{config_id}
```

**Request Body:** Nur zu aendernde Felder
```json
{
  "sync_enabled": false,
  "sync_interval_hours": 48
}
```

---

### Konfiguration loeschen

```http
DELETE /admin/external-apis/{config_id}
```

**Response:** `204 No Content`

**Hinweis:** Loescht auch alle Sync-Records. Entities bleiben erhalten, aber ihr `api_configuration_id` wird auf NULL gesetzt.

---

## Sync-Operationen

### Sync starten

```http
POST /admin/external-apis/{config_id}/sync
```

**Request Body (optional):**
```json
{
  "full_sync": true
}
```

**Response:**
```json
{
  "message": "Sync triggered successfully",
  "config_id": "uuid",
  "task_id": "celery-task-id"
}
```

---

### Verbindung testen

```http
POST /admin/external-apis/{config_id}/test
```

**Response:**
```json
{
  "success": true,
  "message": "Connection successful",
  "response_time_ms": 245,
  "sample_data": [...]
}
```

---

### Sync-Statistiken abrufen

```http
GET /admin/external-apis/{config_id}/stats
```

**Response:**
```json
{
  "config_id": "uuid",
  "config_name": "Wikidata NRW Gemeinden",
  "last_sync_at": "2025-12-21T10:00:00Z",
  "last_sync_status": "success",
  "total_records": 1234,
  "active_records": 1200,
  "missing_records": 30,
  "archived_records": 4,
  "total_entities": 1150,
  "linked_entities": 980
}
```

---

## Sync-Records

### Records auflisten

```http
GET /admin/external-apis/{config_id}/records
```

**Query Parameter:**
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| status | string | - | Filter: active, missing, archived |
| page | int | 1 | Seite |
| page_size | int | 50 | Eintraege pro Seite (max 200) |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "external_id": "Q123456",
      "display_name": "Gummersbach",
      "sync_status": "active",
      "last_seen_at": "2025-12-21T10:00:00Z",
      "entity_id": "uuid",
      "linked_entity_ids": ["uuid1", "uuid2"]
    }
  ],
  "total": 1234,
  "page": 1,
  "page_size": 50
}
```

---

### Record-Details

```http
GET /admin/external-apis/{config_id}/records/{record_id}
```

**Response:** Record mit vollstaendigen Raw-Daten:
```json
{
  "id": "uuid",
  "external_id": "Q123456",
  "display_name": "Gummersbach",
  "sync_status": "active",
  "raw_data": {
    "wikidata_id": "Q123456",
    "label": "Gummersbach",
    "population": 50000,
    "...": "..."
  },
  "...": "..."
}
```

---

### Record loeschen

```http
DELETE /admin/external-apis/{config_id}/records/{record_id}
```

**Response:** `204 No Content`

**Hinweis:** Loescht nur den Sync-Record. Die verknuepfte Entity bleibt erhalten.

---

## Utility-Endpoints

### Verfuegbare API-Typen

```http
GET /admin/external-apis/types/available
```

**Response:**
```json
["wikidata", "oparl", "custom", "govdata", "rest", "auction"]
```

---

### Verfuegbare Import-Modi

```http
GET /admin/external-apis/import-modes/available
```

**Response:**
```json
["entities", "facets", "both"]
```

---

### Von AI-Discovery speichern

Speichert eine durch AI-Discovery gefundene API als neue APIConfiguration.

```http
POST /admin/external-apis/save-from-discovery
```

**Request Body:**
```json
{
  "name": "OpenLigaDB Bundesliga",
  "description": "Via AI-Discovery erstellt",
  "api_type": "rest",
  "base_url": "https://api.openligadb.de",
  "endpoint": "/getbltable/bl1/2024",
  "documentation_url": "https://api.openligadb.de",
  "auth_required": false,
  "field_mapping": {
    "teamName": "name",
    "points": "points"
  },
  "keywords": ["bundesliga", "fußball", "tabelle"],
  "default_tags": ["sport"],
  "confidence": 0.9
}
```

**Response:** `201 Created` mit erstellter APIConfiguration

**Hinweis:** Erstellt automatisch eine DataSource und verknuepfte APIConfiguration mit `is_template=true`.

---

## API-Typen

| Typ | Beschreibung |
|-----|--------------|
| `wikidata` | Wikidata SPARQL Queries |
| `oparl` | OParl-konforme Ratsinformationssysteme |
| `custom` | Benutzerdefinierte REST APIs |
| `govdata` | GovData-Portal APIs |

---

## Authentifizierungs-Typen

| Typ | Beschreibung | Config-Felder |
|-----|--------------|---------------|
| `none` | Keine Authentifizierung | - |
| `api_key` | API-Schluessel im Header | `header_name`, `api_key` |
| `bearer` | Bearer Token | `token` |
| `basic` | HTTP Basic Auth | `username`, `password` |
| `oauth2` | OAuth 2.0 | `client_id`, `client_secret`, `token_url` |

---

## Sync-Status

| Status | Beschreibung |
|--------|--------------|
| `active` | Record wurde beim letzten Sync gefunden |
| `missing` | Record wurde beim letzten Sync nicht gefunden |
| `archived` | Record wurde manuell archiviert |

---

**Letzte Aktualisierung:** 2025-12-25

---

## Architektur-Hinweis

Ab Version 2025-12 nutzt das System das vereinheitlichte `APIConfiguration`-Modell, das die frueheren `ExternalAPIConfig` und `APITemplate` Modelle zusammenfuehrt. Jede APIConfiguration ist zwingend mit einer `DataSource` verknuepft.

**Import-Modi:**
- `entities`: Erstellt/aktualisiert Entities aus API-Daten
- `facets`: Aktualisiert nur Facet-Werte auf bestehenden Entities
- `both`: Kombiniert beide Modi
