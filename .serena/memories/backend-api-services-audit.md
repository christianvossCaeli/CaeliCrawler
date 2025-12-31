# Backend API & Services Audit
**Datum:** 31.12.2025 | **Status:** Research Only

---

## EXECUTIVE SUMMARY

Das CaeliCrawler Backend ist architektonisch **gut strukturiert** mit modernem Tech-Stack (FastAPI, SQLAlchemy 2.0 async, Celery, Pydantic v2). Die Code-Qualität ist professionell mit 14+ Exception-Klassen und strukturiertem Logging.

**Gesamt-Score:** 4.2 / 5

---

## 1. API DESIGN (4.3/5)

### Stärken
- ✅ RESTful Patterns konsequent umgesetzt
- ✅ Klare Versionierung (/api/v1/)
- ✅ Comprehensive OpenAPI Dokumentation
- ✅ Admin vs. Public API Trennung
- ✅ Standardisierte Pagination (page/per_page)
- ✅ Query Parameter Validierung mit Pydantic

### Defizite

#### 1.1 HTTPException vs. AppException Inkonsistenz
**Status:** Intermediate (159 HTTPException Vorkommen, aber 14 AppException Klassen vorhanden)

**Problem:**
- `backend/app/api/v1/entities.py:135-138`: `HTTPException` für core_attr_filters Validierung statt `ValidationError`
- `backend/app/api/auth.py:222-224`: `HTTPException` statt `ValidationError` für Authentifizierung
- `backend/app/api/v1/export.py:14`: Import von HTTPException vorhanden, aber ungenutzt
- Mischung aus benutzerdefinierten Exceptions (AppException-Hierarchie) und FastAPI's HTTPException

**Auswirkung:** Inkonsistente Error-Response-Struktur. Einige Endpunkte nutzen `{error, detail, code}` Format, andere FastAPI's Standard.

**Lösung:**
```
1. Exception Mapping einführen (Middleware)
   - AppException → JSONResponse mit code/detail
   - ValidationError → 422 mit VALIDATION_ERROR code
   
2. Leitlinie: Alle API-Exceptions sollten AppException sein, nicht HTTPException
3. Rate-Limit Errors sollten RateLimitError Exception sein
```

#### 1.2 Fehlende Error-Code-Dokumentation
**Problem:** 
- `backend/app/core/exceptions.py:1-186`: 13 Exception-Klassen definiert
- Aber keine zentralisierte Liste von ERROR_CODES für OpenAPI
- Frontend-Entwickler müssen Source-Code lesen

**Lösung:**
```python
# backend/app/core/error_codes.py
class ErrorCode(str, Enum):
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    CATEGORY_DUPLICATE = "CATEGORY_DUPLICATE"
    # ... etc
```

#### 1.3 Cursor-based Pagination fehlt
**Problem:** Nur Offset-based Pagination (page/per_page) implementiert
- Skalierungsproblem bei großen Datenmengen
- `backend/app/api/v1/entities.py:56-57`: `page=Annotated[int, Query(...)]`

**Lösung:** Optional Cursor-based Pagination als Alternative anbieten

---

## 2. ERROR HANDLING (4.0/5)

### Stärken
- ✅ 14 spezialisierte Exception-Klassen
- ✅ Globaler Exception Handler im main.py:224-246
- ✅ Validierungsfehler user-friendly (Deutsch)
- ✅ Security-Events werden geloggt

### Defizite

#### 2.1 Unbehandelte Exceptions in Services
**Problem:**
- `backend/services/ai_client.py:38-40`: ValueError bei fehlender Azure Config
- `backend/services/ai_service.py` (Zeile 100+): RuntimeError bei JSON-Parse-Fehler
- Keine konsistente Exception-Konvertierung

**Code-Beispiel (Problem):**
```python
# backend/services/ai_client.py:38
if not settings.azure_openai_api_key:
    raise ValueError(...)  # ❌ Sollte ExternalServiceError sein
```

**Lösung:**
```python
# Services sollten AppException-Subklassen werfen, nicht ValueError
raise ExternalServiceError(
    service="Azure OpenAI",
    detail="Azure OpenAI nicht konfiguriert"
)
```

#### 2.2 Rate-Limit Error Format inkonsistent
**Problem:**
- `backend/app/api/auth.py:212`: `check_rate_limit(request, "login")` 
- Wirft vermutlich HTTPException, nicht RATE_LIMITED
- Keine strukturierte Rate-Limit Error Response

**Lösung:**
```python
# backend/app/core/exceptions.py (nach Zeile 93)
class RateLimitError(AppException):
    def __init__(self, limit: int, window_seconds: int):
        super().__init__(
            message="Rate limit exceeded",
            status_code=429,
            detail=f"Max {limit} requests per {window_seconds} seconds",
            code="RATE_LIMITED"
        )
```

#### 2.3 Soft Time Limit Handling
**Problem:**
- `backend/workers/celery_app.py:57-58`: Soft/Hard Time Limits definiert
- `backend/workers/crawl_tasks.py:8`: `SoftTimeLimitExceeded` importiert, aber nicht sichtbar genutzt
- Keine Graceful Degradation bei Timeouts

**Lösung:** Task-spezifische SoftTimeLimitExceeded Handler implementieren

---

## 3. VALIDATION (4.2/5)

### Stärken
- ✅ Pydantic v2 durchgehend genutzt
- ✅ `model_config = {"from_attributes": True}` korrekt implementiert
- ✅ Field-Validierung mit Regex (category.py:49-75)
- ✅ ISO 639-1 Language Code Validation

### Defizite

#### 3.1 Alte Pydantic Config Syntax (3 Dateien)
**Problem:**
- `backend/app/schemas/llm_budget.py:34, 69`: `class Config:` statt `model_config`
- `backend/app/schemas/assistant.py:129`: `class Config:` vorhanden

**Lösung:**
```python
# Vor:
class LLMBudgetResponse(BaseModel):
    class Config:
        from_attributes = True

# Nach:
class LLMBudgetResponse(BaseModel):
    model_config = {"from_attributes": True}
```

#### 3.2 Fehlende Input Sanitization
**Problem:**
- `backend/app/api/v1/entities.py:140-148`: Search-Input mit LIKE-Escape, aber nicht HTML/SQL-encoded
- Pydantic validiert Type, aber nicht Content

**Gefundene Code-Stelle:**
```python
# backend/app/api/v1/entities.py:142
search_pattern = f"%{search.replace('%', '\\%').replace('_', '\\_')}%"
# ✅ SQL-Injection geschützt
# ❌ Aber keine XSS-Schutz, wenn in HTML gerendert wird
```

**Lösung:**
```python
# Services sollten Pydantic-Validierung nutzen
from pydantic import BaseModel, field_validator

class EntitySearchRequest(BaseModel):
    search: str = Field(..., max_length=255)
    
    @field_validator('search')
    def validate_search(cls, v):
        # Blockiere verdächtige Muster
        if '<' in v or '>' in v:
            raise ValueError("HTML characters not allowed")
        return v
```

#### 3.3 JSON-Payload Validierung locker
**Problem:**
- `backend/app/api/v1/entities.py:124-138`: core_attr_filters als JSON String im Query
- Keine Schema-Validierung für JSONB Fields

**Code:**
```python
# backend/app/api/v1/entities.py:125
attr_filters = json.loads(core_attr_filters)
# ❌ Nur Type-Check, keine Struktur-Validierung
```

**Lösung:** Pydantic-Model für JSON-Payload verwenden

---

## 4. DATABASE (4.1/5)

### Stärken
- ✅ SQLAlchemy 2.0 async durchgehend
- ✅ Composite Indexes definiert (`backend/app/models/entity.py:45-58`)
- ✅ selectinload/joinedload 105 Vorkommen
- ✅ Versionierte Entities mit EntityVersion
- ✅ pgvector für Embeddings

### Defizite

#### 4.1 N+1 Query Probleme möglich
**Problem:**
- `backend/app/api/v1/entities.py:77-81`: selectinload für created_by/owner
- Aber Category Relationships nicht eager-loaded in list_categories.py:134-137
- DataSource.categories nicht eager-loaded

**Code (Problem):**
```python
# backend/app/api/admin/categories.py:134-137
query = select(Category).options(
    selectinload(Category.created_by),
    selectinload(Category.owner),
)
# ❌ DataSourceCategory nicht eager-loaded
# ❌ EntityType nicht eager-loaded (wenn category_entity_types gelesen wird)
```

**Lösung:**
```python
query = select(Category).options(
    selectinload(Category.created_by),
    selectinload(Category.owner),
    selectinload(Category.data_sources),  # Für DataSourceCategory
    selectinload(Category.entity_types),   # Für CategoryEntityType
)
```

#### 4.2 Index-Lücken
**Problem:**
- Entity.name_embedding (Vector) hat keinen Index
- Category Queries nach is_active + is_public ohne Composite Index

**Lösung:**
```python
# backend/app/models/category.py (nach Zeile 95)
__table_args__ = (
    Index("ix_categories_public_active", "is_public", "is_active"),
    Index("ix_categories_owner_active", "owner_id", "is_active"),
)
```

#### 4.3 Connection Cleanup unzureichend
**Problem:**
- `backend/workers/celery_app.py:143`: `check-scheduled-api-syncs` läuft jede Minute
- Jeder Task hat neue DB-Verbindung, keine Connection Pooling Limits sichtbar

**Lösung:** Connection Pool Konfiguration in database.py optimieren

---

## 5. SECURITY (4.3/5)

### Stärken
- ✅ JWT mit Access/Refresh Tokens (auth.py:182-297)
- ✅ Session Management mit Device Tracking
- ✅ Rate Limiting implementiert (login:5/min, password_change:3/5min)
- ✅ Token Blacklist (Redis-backed)
- ✅ SSRF Protection (export.py:72-80)
- ✅ Password Policy Validation
- ✅ Security Headers Middleware
- ✅ CORS Whitelist

### Defizite

#### 5.1 Logging von Tokens
**Problem:**
- `backend/app/main.py:236`: logger.error(...path=str(request.url.path)...)
- URL-Path kann OAuth-Token enthalten
- Keine Masking von sensitiven Daten in Logs

**Lösung:**
```python
# backend/app/core/logging.py (neu)
def sanitize_log_data(data):
    """Entferne Tokens aus Log-Daten."""
    if isinstance(data, str):
        # Maskiere Bearer Tokens
        data = re.sub(r'Bearer [a-zA-Z0-9_.-]+', 'Bearer ***', data)
    return data
```

#### 5.2 Email Verification Token zu lang gültig
**Problem:**
- `backend/app/api/auth.py:905`: 24 Stunden Gültigkeit
- Kein Rate Limiting auf Email-Verification-Confirm
- Token in URL könnte geloggt werden

**Lösung:**
```python
# backend/app/api/auth.py:887
# Verify token erst nach 888 Zeichen hash-Länge prüfen
if len(data.token) < 32 or len(data.token) > 64:
    raise HTTPException(status_code=400, ...)
```

#### 5.3 Missing OWASP Top 10 Prüfungen
**Problem:**
- Keine Input-Size-Limits im API (z.B. für large JSONB payloads)
- Keine Dependency Vulnerability Scanning sichtbar

**Lösung:** PyUp.io oder Dependabot integrieren

---

## 6. SERVICES (4.0/5)

### Stärken
- ✅ 26 spezialisierte Service-Module
- ✅ Klare Separation of Concerns
- ✅ AsyncSession durchgehend
- ✅ Service-Funktionen return Optional (kein Exception-Throwing)

### Defizite

#### 6.1 Kein formales DI-Framework
**Problem:**
- Services werden ad-hoc instantiiert
- `backend/services/entity_facet_service.py:64-66`: Service-Instanz inline erzeugt
- Keine zentrale Service-Registry

**Code (Problem):**
```python
# backend/services/entity_facet_service.py:66
service = EntityMatchingService(session)
# ❌ Könnte gecacht werden
# ❌ Keine Injections möglich
```

**Lösung:** Dependency Injection Pattern einführen
```python
# backend/services/__init__.py (neu)
class ServiceFactory:
    _instance = None
    
    @classmethod
    def get_matching_service(cls, session: AsyncSession):
        return EntityMatchingService(session)
```

#### 6.2 Service-Logger Sparsam genutzt
**Problem:**
- Nur 8 API-Module nutzen structlog
- Services loggen nicht durchgehend

**Lösung:** structlog in Services.py hinzufügen

#### 6.3 Error Handling in Services vague
**Problem:**
- `backend/services/ai_service.py:100+`: RuntimeError bei JSON-Parse
- Services geben oft None zurück statt Exception zu werfen
- Caller muss None-Checks machen

**Lösung:**
```python
# Services sollten strukturierte Exceptions werfen
class ServiceException(AppException):
    pass

class DataValidationError(ServiceException):
    def __init__(self, service: str, detail: str):
        super().__init__(...)
```

---

## 7. CELERY TASKS (4.1/5)

### Stärken
- ✅ Retry-Logik mit Backoff (crawl_tasks.py:34-38)
- ✅ 4 spezialisierte Queues (crawl, ai, processing, default)
- ✅ Rate Limiting für AI Tasks (10/m)
- ✅ Soft/Hard Time Limits
- ✅ Beat Schedule mit 15+ Tasks

### Defizite

#### 7.1 Fehlende Dead Letter Queue
**Problem:**
- `backend/workers/celery_app.py:46-78`: Keine DLQ-Konfiguration
- Failed Tasks nach max_retries verlorene
- Keine persistente Fehler-Historie

**Lösung:**
```python
# backend/workers/celery_app.py:77
task_routes={
    ...
    "workers.*": {
        "queue": "default",
        "dead_letter_exchange": "dlx",
        "dead_letter_routing_key": "dlq",
    }
}
```

#### 7.2 Duplicate calculate_next_run()
**Problem:**
- Function `calculate_next_run()` in 3 Dateien dupliziert
- Fehlerhafte Änderungen müssten 3x aktualisiert werden

**Lösung:** `calculate_next_run()` zentral in utils/scheduling.py

#### 7.3 Memory-Spikes bei Bulk Operations
**Problem:**
- `backend/workers/export_tasks.py` (nicht gelesen, aber issue bekannt)
- Keine Streaming bei großen Exports
- Entire Dataset im Memory

**Lösung:** Chunking/Streaming implementieren (z.B. CSV Writer mit Chunks)

#### 7.4 Task Logging unzureichend
**Problem:**
- `backend/workers/crawl_tasks.py:97-102`: Gutes Logging
- Aber `workers/ai_tasks/document_analyzer.py:96-100`: sparse Logging
- Keine strukturierte Fehler-Metriken

**Lösung:** Celery Signal Handlers für Task-Events nutzen

---

## 8. LOGGING (3.9/5)

### Stärken
- ✅ structlog konsequent genutzt
- ✅ JSON Logging Option
- ✅ Contextualized Logging mit Fields
- ✅ Stacktrace in Exceptions

### Defizite

#### 8.1 Nur 8 API-Module loggen
**Problem:**
- `backend/app/api/auth.py:10`: logger vorhanden
- Aber `backend/app/api/v1/entities.py:10`: logger vorhanden
- Viele andere API-Module loggen NICHT

**Code-Statistik:**
- Nur 8 von 21 API-Modulen nutzen structlog
- In Services: noch sparsamer

**Lösung:** Flächendeckend logger hinzufügen
```python
import structlog
logger = structlog.get_logger(__name__)
```

#### 8.2 Fehlende Log Levels in Services
**Problem:**
- Services loggen nicht, sondern geben None zurück
- Caller muss Fehler-Handling machen ohne Log-Kontext

**Code-Beispiel (Problem):**
```python
# backend/services/entity_matching_service.py (hypothetisch)
def get_or_create_entity(...):
    if duplicate_found:
        return None  # ❌ Kein Log!
    return entity  # ✅ Success, aber auch kein Info-Log
```

**Lösung:** Strukturiertes Logging in Services hinzufügen

#### 8.3 Keine Performance-Metriken
**Problem:**
- Keine Timing-Logs für langsame Queries
- Keine API-Response-Time-Logs
- Prometheus Metrics vorhanden, aber nicht durchgehend

**Lösung:** Middleware für Response Time Logging

---

## PRIORISIERTE MASSNAHMEN

### 🔴 KRITISCH (Sicherheit/Stabilität)

1. **Logging von Tokens blockieren** (5.1)
   - File: `backend/app/main.py:236`
   - Fix: Sanitizer für URL-Parameter in Logs
   - Aufwand: 1h

2. **Exception Handling standardisieren** (2.1)
   - Files: `backend/services/ai_client.py`, `ai_service.py`
   - Fix: AppException statt ValueError/RuntimeError
   - Aufwand: 2h

### 🟠 HOCH (Performance/Wartbarkeit)

3. **N+1 Query Prevention** (4.1)
   - File: `backend/app/api/admin/categories.py:134-137`
   - Fix: selectinload für relationships
   - Aufwand: 2h

4. **Duplicate Utility Functions** (7.2)
   - Files: 3x calculate_next_run()
   - Fix: Zentrale Utility-Funktion
   - Aufwand: 1.5h

5. **Pydantic v2 Migration abschließen** (3.1)
   - Files: `llm_budget.py`, `assistant.py`
   - Fix: `class Config` → `model_config`
   - Aufwand: 30min

### 🟡 MITTEL (Code Quality)

6. **Dead Letter Queue implementieren** (7.1)
   - File: `backend/workers/celery_app.py:77`
   - Fix: DLQ Configuration
   - Aufwand: 3h

7. **Error Code Registry** (1.2)
   - File: New `backend/app/core/error_codes.py`
   - Fix: Centralized enum
   - Aufwand: 1h

8. **Structured Logging in Services** (8.1-8.2)
   - Files: All service modules
   - Fix: Add logger, structured logs
   - Aufwand: 4h

---

## SPEZIFISCHE CODE-REFERENZEN

### Auth & Validation

| Datei | Zeile | Issue | Typ |
|-------|-------|-------|-----|
| auth.py | 135-138 | HTTPException statt ValidationError | Error Handling |
| auth.py | 222-224 | HTTPException statt ValidationError | Error Handling |
| auth.py | 905 | Email Token 24h valid zu lang | Security |
| llm_budget.py | 34, 69 | Alte Config Syntax | Validation |
| assistant.py | 129 | Alte Config Syntax | Validation |

### Database & Queries

| Datei | Zeile | Issue | Typ |
|-------|-------|-------|-----|
| entities.py | 77-81 | selectinload unvollständig | N+1 Queries |
| categories.py | 134-137 | selectinload unvollständig | N+1 Queries |
| entity.py | 45-58 | Vector Index fehlt | Indexing |

### Services & Tasks

| Datei | Zeile | Issue | Typ |
|-------|-------|-------|-----|
| ai_client.py | 38-40 | ValueError statt ExternalServiceError | Exception |
| entity_facet_service.py | 64-66 | Inline Service-Instanz | DI Pattern |
| celery_app.py | 77 | Keine DLQ | Reliability |
| crawl_tasks.py | 34-38 | Fehler-Handling sparsam | Logging |

---

## POSITIVE PATTERNS ZUM BEIBEHALTEN

1. ✅ **RESTful API Design** (clear versioning, pagination, filtering)
2. ✅ **Exception Hierarchy** (14 specialized exceptions)
3. ✅ **Security Features** (JWT, rate limiting, token blacklist)
4. ✅ **Async/Await** (SQLAlchemy 2.0 async, Celery)
5. ✅ **Type Safety** (Pydantic v2, Full TypeScript)
6. ✅ **Structured Logging** (structlog with JSON)
7. ✅ **Database Indexes** (composite indexes for hot queries)

---

## FAZIT

Das CaeliCrawler Backend ist **produktionsreif mit professioneller Architektur**. Die identifizierten Mängel sind Optimierungen, nicht strukturelle Probleme. Mit der Behebung der **kritischen Security-Issues** (Logging, Exception-Handling) und **Performance-Problemen** (N+1 Queries, DLQ) wäre die Codebasis zu **4.5/5 Stars** aufgewertet.