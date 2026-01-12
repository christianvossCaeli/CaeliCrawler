# API Documentation Reference

## Datum: December 2024

## Übersicht

CaeliCrawler Backend nutzt FastAPI mit automatischer OpenAPI-Dokumentation.

## Version 2.2.0 Updates (Januar 2026)

**Letztes Audit:** 2026-01-05

### Breaking Changes
- **Category API:** Parameter `is_active` durch `scheduled_only` ersetzt
- **CrawlPreset API:** Feld `status` entfernt, `category_id` jetzt required

### Neue Endpoints
- `GET /api/v1/attachments/search` - Volltext-Suche ueber Anhaenge
- `PUT /api/v1/data/extracted/{id}/reject` - Extraktion ablehnen
- `GET /api/v1/data/stats/unverified-count` - Zaehler fuer unverifizierte Extraktionen
- `GET /api/v1/entities/{id}/sources` - DataSources einer Entity abrufen
- `GET /api/v1/facets/types/for-category/{category_id}` - FacetTypes fuer Kategorie
- `GET /api/v1/facets/entity/{entity_id}/referenced-by` - Referenzierende FacetValues
- `POST /admin/crawler/ai-discovery/import-api-data` - API-Daten als DataSources importieren

### Neue Smart Query Operations
- `update_crawl_schedule` - Crawl-Schedule einer Kategorie aendern
- `create_custom_summary` - Benutzerdefinierte Zusammenfassung erstellen
- `push_to_pysis` - Facet-Daten nach PySis exportieren
- `get_history` - Aenderungshistorie abrufen
- `link_existing_category` - Bestehende Kategorie verknuepfen
- `fetch_and_create_from_api` - Daten von API importieren und Entities erstellen

### Korrigierte Operation-Namen (SMART_QUERY.md)
- `analyze_pysis_for_facets` → `analyze_pysis`
- `export_query_result` → `export`
- `undo_change` → `undo`

### Neue Felder
- ExtractedData: `is_rejected`, `rejected_by`, `rejected_at`, `rejection_reason`
- Facet Values: `target_entity_type_icon`, `target_entity_type_color`
- Entities: `core_attr_filters` unterstuetzt jetzt Range-Filter (min/max)

### Migration Guide
Siehe `docs/api/MIGRATION_v2.2.md` fuer detaillierte Migrations-Anweisungen.

---

## Endpoints

### Docs-Zugriff (nur Development)
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## API-Struktur

### Authentifizierung (`/api/auth`)
| Endpoint | Method | Beschreibung |
|----------|--------|--------------|
| `/login` | POST | Login mit Email/Passwort, gibt JWT zurück |
| `/logout` | POST | Logout, invalidiert Token |
| `/me` | GET | Aktueller User |
| `/change-password` | POST | Passwort ändern |

### Admin API (`/admin`)
Prefix: `/admin`

| Modul | Prefix | Tags |
|-------|--------|------|
| Users | `/users` | Admin - Users |
| Audit | `/audit` | Admin - Audit Log |
| Categories | `/categories` | Admin - Categories |
| Sources | `/sources` | Admin - Sources |
| Crawler | `/crawler` | Admin - Crawler |
| Notifications | `/notifications` | Admin - Notifications |
| External APIs | `/external-apis` | Admin - External APIs |

### Public API v1 (`/api/v1`)

| Modul | Prefix | Beschreibung |
|-------|--------|--------------|
| Entities | `/entities` | Entity CRUD & Suche |
| Entity Types | `/entity-types` | Entity-Type Management |
| Facets | `/facets` | Facet Values Management |
| Relations | `/relations` | Entity-Relationen |
| Dashboard | `/dashboard` | Dashboard Statistiken |
| Export | `/export` | Datenexport (CSV, JSON, etc.) |
| Assistant | `/assistant` | AI-Chat Funktionen |
| Smart Query | `/smart-query` | Natürliche Sprachabfragen |

### Data API (`/api/v1/data`)
Spezielle Endpunkte für Daten-Operationen:
- Bulk-Operationen
- Aggregationen
- Suche mit komplexen Filtern

### Analysis API (`/api/v1/analysis`)
AI-gestützte Analyse-Funktionen.

## Authentifizierung

### JWT Token Flow
```
1. POST /api/auth/login
   Body: { "email": "...", "password": "..." }
   Response: { "access_token": "...", "token_type": "bearer" }

2. Alle weiteren Requests:
   Header: Authorization: Bearer <access_token>

3. POST /api/auth/logout
   Invalidiert Token sofort (Redis Blacklist)
```

### Rollen & Berechtigungen
| Rolle | Beschreibung | Zugriff |
|-------|--------------|---------|
| ADMIN | Vollzugriff | Alles |
| EDITOR | Daten bearbeiten | CRUD auf Entities, Facets, Relations |
| VIEWER | Nur lesen | GET-Endpunkte |

### Dependencies
```python
from app.core.deps import (
    get_current_user,    # Aktueller User (Required)
    get_optional_user,   # Optional (für public endpoints)
    require_admin,       # Admin-Rolle erforderlich
    require_editor,      # Editor-Rolle erforderlich
)
```

## Rate Limiting

| Endpunkt-Typ | Limit |
|--------------|-------|
| Login | 5 Versuche/Minute |
| Failed Login | 10 Fehlversuche/15 Min |
| Passwort-Änderung | 3 Versuche/5 Min |
| API allgemein | 100 Requests/Minute |

## Schema-Dokumentation

### Pydantic Models mit OpenAPI
```python
from pydantic import BaseModel, Field

class EntityCreate(BaseModel):
    """Schema for creating a new entity."""

    name: str = Field(
        ...,  # Required
        min_length=1,
        max_length=500,
        description="Primary name of the entity"
    )
    external_id: str | None = Field(
        None,
        max_length=255,
        description="External reference (AGS, UUID, etc.)"
    )
```

### Query Parameter Dokumentation
```python
from fastapi import Query
from typing import Annotated

@router.get("")
async def list_entities(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=500, description="Items per page")] = 50,
    search: Annotated[str | None, Query(description="Search in name")] = None,
):
    ...
```

### Response Models
```python
class EntityListResponse(BaseModel):
    """Paginated entity list response."""
    items: list[EntityResponse]
    total: int
    page: int
    per_page: int
    pages: int
```

## Error Responses

### Standard Format
```json
{
  "error": "Kurze Fehlermeldung",
  "detail": "Detaillierte Beschreibung",
  "code": "ERROR_CODE"
}
```

### Error Codes
| Code | HTTP Status | Bedeutung |
|------|-------------|-----------|
| `VALIDATION_ERROR` | 422 | Eingabevalidierung fehlgeschlagen |
| `NOT_FOUND` | 404 | Resource nicht gefunden |
| `CONFLICT` | 409 | Ressourcenkonflikt (z.B. doppelter Name) |
| `UNAUTHORIZED` | 401 | Nicht authentifiziert |
| `FORBIDDEN` | 403 | Keine Berechtigung |
| `RATE_LIMITED` | 429 | Rate Limit erreicht |
| `INTERNAL_SERVER_ERROR` | 500 | Serverfehler |

## Feature Flags

Endpoint: `GET /api/config/features`

```json
{
  "entityLevelFacets": true,
  "pysisFieldTemplates": true,
  "entityHierarchyEnabled": true
}
```

## Health & Metrics

| Endpoint | Beschreibung |
|----------|--------------|
| `GET /health` | Health Check Status |
| `GET /metrics` | Prometheus Metriken |

## Best Practices

### 1. Router Tags verwenden
```python
router = APIRouter()

@router.get("", tags=["Entities"])
async def list_entities():
    ...
```

### 2. Response Models definieren
```python
@router.get("/{id}", response_model=EntityResponse)
async def get_entity(id: UUID):
    ...
```

### 3. Dependencies für Auth nutzen
```python
@router.post("", dependencies=[Depends(require_editor)])
async def create_entity():
    ...
```

### 4. Docstrings für OpenAPI
```python
@router.get("/{id}")
async def get_entity(id: UUID):
    """
    Get entity by ID.

    Returns complete entity data including facets summary.
    """
    ...
```

### 5. Audit-Logging
```python
from app.core.audit import AuditContext

async with AuditContext(
    db=session,
    user_id=current_user.id,
    action=AuditAction.UPDATE,
    resource_type="entity",
    resource_id=entity.id,
):
    # Änderungen werden automatisch geloggt
    entity.name = new_name
    ...
```

## Frontend API Client

Der Frontend API-Client (`src/services/api.ts`) spiegelt diese Struktur:

```typescript
export const entityApi = {
  list: (params) => api.get('/entities', { params }),
  get: (id) => api.get(`/entities/${id}`),
  create: (data) => api.post('/entities', data),
  update: (id, data) => api.patch(`/entities/${id}`, data),
  delete: (id) => api.delete(`/entities/${id}`),
}
```
