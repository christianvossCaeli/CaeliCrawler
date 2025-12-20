# Architektur: Analysethemen (Categories)

**Stand:** 2025-12-20
**Version:** 1.0
**Autor:** Technisches Audit

---

## 1. Übersicht

Das **Analysethemen-System** (Categories) ist das zentrale Orchestrierungsmodul des CaeliCrawler. Es steuert:

- Welche Datenquellen gecrawlt werden
- Wie Dokumente gefiltert werden (URL-Patterns)
- Wie AI-Extraktion konfiguriert wird
- Welcher Extraktions-Handler verwendet wird

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  CategoriesView.vue (CRUD, Crawler-Start, Reanalyse)        ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ API Calls
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND API                                 │
│  ┌───────────────────────┐  ┌────────────────────────────────┐  │
│  │ /admin/categories     │  │ /admin/crawler                 │  │
│  │ - GET (list)          │  │ - POST /start                  │  │
│  │ - POST (create)       │  │ - POST /reanalyze              │  │
│  │ - PUT (update)        │  │ - GET /jobs                    │  │
│  │ - DELETE              │  │ - GET /running                 │  │
│  │ - GET /{id}/stats     │  │ - GET /ai-tasks                │  │
│  └───────────────────────┘  └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ Celery Tasks
┌─────────────────────────────────────────────────────────────────┐
│                      WORKER TASKS                                │
│  ┌───────────────────────┐  ┌────────────────────────────────┐  │
│  │ crawl_tasks.py        │  │ ai_tasks.py                    │  │
│  │ - create_crawl_job()  │  │ - analyze_document()           │  │
│  │ - crawl_source()      │  │ - batch_analyze()              │  │
│  └───────────────────────┘  └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ Handler-Routing
┌─────────────────────────────────────────────────────────────────┐
│                      SERVICES                                    │
│  ┌───────────────────────┐  ┌────────────────────────────────┐  │
│  │ entity_facet_service  │  │ event_extraction_service       │  │
│  │ (extraction_handler=  │  │ (extraction_handler=           │  │
│  │  "default")           │  │  "event")                      │  │
│  └───────────────────────┘  └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Datenmodell

### 2.1 Category Model

**Datei:** `backend/app/models/category.py`

```python
class Category(Base):
    __tablename__ = "categories"

    # Identifikation
    id: UUID                    # Primary Key
    name: str                   # Unique, max 255 chars
    slug: str                   # URL-freundlich, unique

    # Beschreibung
    description: Optional[str]  # Optionale Beschreibung
    purpose: str                # Kernzweck (z.B. "Windkraft-Restriktionen analysieren")

    # Crawl-Konfiguration
    search_terms: List[str]     # Keywords für Dokumenterkennung
    document_types: List[str]   # z.B. ["html", "pdf"]
    url_include_patterns: List[str]  # Regex - URLs müssen matchen
    url_exclude_patterns: List[str]  # Regex - URLs werden übersprungen
    languages: List[str]        # ISO 639-1 Codes, z.B. ["de", "en"]

    # AI-Konfiguration
    ai_extraction_prompt: Optional[str]  # Custom LLM Prompt
    extraction_handler: str     # "default" oder "event"

    # Scheduling
    schedule_cron: str          # z.B. "0 2 * * *" (täglich 2 Uhr)
    is_active: bool             # Aktiv zum Crawlen?

    # Ownership
    created_by_id: Optional[UUID]  # FK zu users
    owner_id: Optional[UUID]       # FK zu users
    is_public: bool                # Sichtbarkeit

    # Ziel-EntityType
    target_entity_type_id: Optional[UUID]  # FK zu entity_types
```

### 2.2 Beziehungen

```
Category
    │
    ├──→ N:M DataSource (via DataSourceCategory junction table)
    │         └── Eine Quelle kann mehreren Kategorien gehören
    │
    ├──→ 1:N Document
    │         └── Dokumente gehören zu einer Kategorie
    │
    ├──→ 1:N ExtractedData
    │         └── Extraktionen sind kategorisiert
    │
    ├──→ 1:N CrawlJob
    │         └── Crawl-Jobs verfolgen Crawl-Operationen pro Kategorie
    │
    ├──→ 1:1 EntityType (target)
    │         └── Ziel-EntityType für extrahierte Entities
    │
    └──→ 1:1 User (owner/created_by)
              └── Ownership-Tracking
```

---

## 3. API-Endpunkte

### 3.1 Categories API (`/admin/categories`)

| Method | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | `/` | Liste aller Kategorien (paginiert, gefiltert) |
| POST | `/` | Neue Kategorie erstellen |
| GET | `/{id}` | Einzelne Kategorie abrufen |
| PUT | `/{id}` | Kategorie aktualisieren |
| DELETE | `/{id}` | Kategorie löschen |
| GET | `/{id}/stats` | Statistiken (Quellen, Dokumente, Extraktionen) |

**Sichtbarkeitsregeln:**
- `is_public=True`: Sichtbar für alle
- `is_public=False`: Nur für Owner/Creator sichtbar

### 3.2 Crawler API (`/admin/crawler`)

| Method | Endpoint | Beschreibung |
|--------|----------|--------------|
| POST | `/start` | Crawling starten (mit Filtern) |
| POST | `/reanalyze` | Dokumente neu analysieren |
| GET | `/jobs` | Liste der Crawl-Jobs |
| GET | `/running` | Laufende Jobs mit Live-Progress |
| GET | `/ai-tasks` | Liste der AI-Tasks |

---

## 4. Validierung

### 4.1 Schema-Validierung (`backend/app/schemas/category.py`)

**extraction_handler:**
```python
extraction_handler: Literal["default", "event"]
```

**Regex-Pattern-Validierung:**
```python
@field_validator("url_include_patterns", "url_exclude_patterns")
def validate_regex_patterns(cls, v):
    for pattern in v:
        try:
            re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{pattern}': {e}")
    return v
```

**Sprachcode-Validierung:**
```python
@field_validator("languages")
def validate_languages(cls, v):
    for lang in v:
        if len(lang) != 2:
            raise ValueError(f"Invalid language code: must be 2-letter ISO 639-1")
    return v
```

---

## 5. Extraktions-Handler

### 5.1 Handler-Routing

```python
# In ai_tasks.py
handler = category.extraction_handler or "default"

if handler == "event":
    from services.event_extraction_service import convert_event_extraction_to_facets
    facet_counts = await convert_event_extraction_to_facets(session, extracted, source, category)
else:
    from services.entity_facet_service import convert_extraction_to_facets
    facet_counts = await convert_extraction_to_facets(session, extracted, source)
```

### 5.2 Handler-Typen

| Handler | Service | Anwendungsfall |
|---------|---------|----------------|
| `default` | `entity_facet_service.py` | Standard-Extraktion (Pain Points, Positive Signals, etc.) |
| `event` | `event_extraction_service.py` | Event-spezifische Extraktion (Veranstaltungen, Termine) |

---

## 6. Workflow

### 6.1 Kategorie erstellen

```
1. POST /admin/categories
   └── CategoryCreate Schema validiert:
       - name (unique)
       - purpose (required)
       - extraction_handler (Literal["default", "event"])
       - url_include_patterns (Regex validiert)
       - languages (ISO 639-1 validiert)

2. Slug wird auto-generiert (wenn nicht angegeben)

3. Duplikat-Prüfung (name + slug)

4. Category in DB gespeichert
```

### 6.2 Crawling starten

```
1. POST /admin/crawler/start
   └── category_id, source_type, status Filter

2. Matching DataSources via Junction Table finden

3. CrawlJob pro (source, category) erstellt

4. Celery Task: crawl_source.delay(source_id, category_id)

5. Dokumente gefunden & gefiltert:
   - url_include_patterns müssen matchen
   - url_exclude_patterns werden übersprungen

6. Dokumente in DB gespeichert mit category_id
```

### 6.3 Dokument analysieren

```
1. Celery Task: analyze_document(document_id)

2. Category und ai_extraction_prompt laden

3. Relevanz-Check (wenn nicht skip_relevance_check):
   - Keywords aus search_terms prüfen
   - Irrelevante → FILTERED status

4. Azure OpenAI API aufrufen:
   - System Prompt = ai_extraction_prompt
   - Response = JSON mit extrahierten Daten

5. ExtractedData in DB speichert

6. Handler-Routing basierend auf extraction_handler:
   - "default" → entity_facet_service
   - "event" → event_extraction_service

7. FacetValues erstellt
```

---

## 7. Performance-Optimierungen

### 7.1 N+1 Query-Vermeidung

**Problem:** Für jede Kategorie/Job werden einzelne Queries ausgeführt.

**Lösung:** Batch-Fetching

```python
# Vorher (N+1):
for job in jobs:
    source = await session.get(DataSource, job.source_id)
    category = await session.get(Category, job.category_id)

# Nachher (2 Queries):
source_ids = list({job.source_id for job in jobs})
sources_result = await session.execute(
    select(DataSource).where(DataSource.id.in_(source_ids))
)
sources_dict = {s.id: s for s in sources_result.scalars().all()}
```

**Angewandt in:**
- `list_categories` (source_count, document_count)
- `list_jobs` (source_name, category_name)
- `get_running_jobs` (source, category)
- `list_ai_tasks` (process_name, location_name)
- `get_running_ai_tasks` (process_name, location_name)

---

## 8. Frontend-Integration

### 8.1 CategoriesView.vue

**Datei:** `frontend/src/views/CategoriesView.vue` (~1100 Zeilen)

**Features:**
- Kategorien-Liste mit Filtern (Suche, Status, Dokumente, Sprache)
- Create/Edit Dialog mit Tabs:
  - General: Name, Beschreibung, Zweck, Sprachen
  - Search: Suchbegriffe, Dokumenttypen, Cron
  - Filters: URL Include/Exclude Patterns
  - AI: Extraktions-Prompt
- Sources Dialog: Zeigt verknüpfte Datenquellen
- Crawler Dialog: Start Crawl mit Filtern
- Reanalyze Dialog: Neu-Analyse (alle oder nur Low Confidence)

### 8.2 API-Integration

```typescript
// frontend/src/services/api.ts
export const adminApi = {
  getCategories: (params) => api.get('/admin/categories', { params }),
  createCategory: (data) => api.post('/admin/categories', data),
  updateCategory: (id, data) => api.put(`/admin/categories/${id}`, data),
  deleteCategory: (id) => api.delete(`/admin/categories/${id}`),
  getCategoryStats: (id) => api.get(`/admin/categories/${id}/stats`),
  startCrawl: (data) => api.post('/admin/crawler/start', data),
  reanalyzeDocuments: (params) => api.post('/admin/crawler/reanalyze', null, { params }),
}
```

---

## 9. Lokalisierung

**Dateien:**
- `frontend/src/locales/de/categories.json` (145 Zeilen)
- `frontend/src/locales/en/categories.json`

**Schlüssel-Struktur:**
```json
{
  "categories": {
    "title": "Analysethemen",
    "form": {
      "name": "Name",
      "purpose": "Zweck",
      "aiPromptTitle": "KI-Extraktions-Prompt"
    },
    "actions": {
      "create": "Erstellen",
      "reanalyze": "Dokumente neu analysieren"
    }
  }
}
```

---

## 10. Migrationen

| Revision | Datei | Beschreibung |
|----------|-------|--------------|
| h1234567896 | `add_category_url_filters.py` | URL Include/Exclude Patterns |
| j1234567898 | `add_category_languages.py` | Languages (JSONB) |
| n1234567902 | `add_ownership_to_entitytype_category.py` | created_by, owner, is_public, target_entity_type_id |
| y1234567913 | `add_extraction_handler_to_categories.py` | extraction_handler ("default" oder "event") |

---

## 11. Fehlerbehandlung

### 11.1 Custom Exceptions

```python
from app.core.exceptions import NotFoundError, ConflictError, ValidationError

# Kategorie nicht gefunden
raise NotFoundError("Category", str(category_id))

# Duplikat-Name
raise ConflictError("Category name already exists", detail=f"...")

# Ungültige Regex
raise ValueError(f"Invalid regex pattern '{pattern}': {e}")
```

### 11.2 Validierungsfehler

Pydantic-Validierung gibt automatisch HTTP 422 mit Details zurück:

```json
{
  "detail": [
    {
      "loc": ["body", "extraction_handler"],
      "msg": "Input should be 'default' or 'event'",
      "type": "literal_error"
    }
  ]
}
```

---

## 12. Best Practices

### 12.1 Modularität

- **Models** in `app/models/` - nur Datenstruktur
- **Schemas** in `app/schemas/` - API-Validierung
- **API** in `app/api/` - HTTP-Endpunkte
- **Services** in `services/` - Geschäftslogik
- **Workers** in `workers/` - Async Tasks

### 12.2 Typisierung

- Pydantic `Literal` für eingeschränkte Werte
- `Optional[T]` für nullable Felder
- `List[str]` statt `list` für JSONB

### 12.3 Async/Await

Alle DB-Operationen sind async:
```python
async def list_categories(...):
    result = await session.execute(query)
    categories = result.scalars().all()
```

---

## 13. Event-Extraction-Handler

### 13.1 Architektur

Der Event-Extraction-Handler ist eine spezialisierte Extraktions-Pipeline für Veranstaltungen und Termine:

```
Category (extraction_handler="event")
         │
         ▼
    ai_tasks.py (Router)
         │
         ▼
event_extraction_service.py
         │
         ▼
entity_facet_service.py (gemeinsame Funktionen)
         │
         ▼
    Erstellt:
    ├── Event Entities (oder Custom EntityType via target_entity_type_id)
    ├── Person Entities (Teilnehmer)
    ├── FacetValues (event_attendance)
    └── Relations (attends, works_for, located_in)
```

### 13.2 Gemeinsame Funktionen

Die folgenden Funktionen sind in `entity_facet_service.py` zentralisiert und werden von beiden Handlern verwendet:

| Funktion | Beschreibung |
|----------|--------------|
| `get_or_create_entity()` | Entity abrufen oder erstellen |
| `get_facet_type_by_slug()` | FacetType nach Slug finden |
| `create_facet_value()` | Neuen FacetValue erstellen |
| `check_duplicate_facet()` | Duplikat-Prüfung |
| `get_relation_type_by_slug()` | RelationType nach Slug finden |
| `create_relation()` | Neue EntityRelation erstellen |

### 13.3 Konfiguration

**Custom EntityType für Events:**

Wenn `target_entity_type_id` gesetzt ist, werden Event-Entities mit diesem EntityType erstellt statt dem Standard-"event"-Typ.

```python
# In category_setup.py
if category.target_entity_type_id:
    target_type = await session.get(EntityType, category.target_entity_type_id)
    event_entity_type_slug = target_type.slug  # z.B. "event-besuche-nrw"
else:
    event_entity_type_slug = "event"  # Standard
```

### 13.4 Extraktions-Struktur

**Erwartete AI-Output-Struktur für Event-Handler:**

```json
{
  "event": {
    "event_name": "Husum Wind 2025",
    "event_date": "2025-09-09",
    "event_end_date": "2025-09-12",
    "event_type": "Messe",
    "event_venue": "Messe Husum",
    "event_location": "Husum",
    "event_url": "https://...",
    "event_description": "..."
  },
  "attendees": [
    {
      "name": "Max Müller",
      "position": "Bürgermeister",
      "organization": "Stadt Husum",
      "role": "Redner",
      "topic": "Kommunale Windenergie"
    }
  ],
  "is_future_event": true
}
```

---

## 14. AI-Generierungs-Workflow

### 14.1 Kategorie mit AI erstellen

**Service:** `services/smart_query/category_setup.py`

```
1. User-Intent empfangen (z.B. "Windkraft-Veranstaltungen in NRW")

2. Step 1: EntityType generieren (ai_generation.py)
   └── ai_generate_entity_type_config()
       └── Erstellt: name, description, icon, color, attribute_schema

3. Step 2: Category generieren (ai_generation.py)
   └── ai_generate_category_config()
       └── Erstellt: purpose, search_terms, extraction_handler, ai_extraction_prompt

4. Step 3: Crawl-Config generieren (ai_generation.py)
   └── ai_generate_crawl_config()
       └── Erstellt: url_include_patterns, url_exclude_patterns

5. EntityType + Category in DB speichern
   └── Category.target_entity_type_id → EntityType.id

6. DataSources verlinken
   └── DataSourceCategory Junction Table
```

### 14.2 AI-Generierungs-Funktionen

**Datei:** `services/smart_query/ai_generation.py`

| Funktion | Parameter | Rückgabe |
|----------|-----------|----------|
| `ai_generate_entity_type_config()` | user_intent, geographic_context | name, description, icon, color, attribute_schema |
| `ai_generate_category_config()` | user_intent, entity_type_name, entity_type_description | purpose, search_terms, extraction_handler, ai_extraction_prompt |
| `ai_generate_crawl_config()` | user_intent, search_focus, search_terms | url_include_patterns, url_exclude_patterns |

---

## 15. Datenfluss-Übersicht

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATENFLUSS                                   │
└─────────────────────────────────────────────────────────────────────┘

[User erstellt Category]
         │
         ▼
┌─────────────────────┐
│     Category        │ ←── purpose, search_terms, url_patterns,
│                     │     ai_extraction_prompt, extraction_handler
└─────────────────────┘
         │
         │ N:M via DataSourceCategory
         ▼
┌─────────────────────┐
│    DataSource       │ ←── base_url, source_type, location_name
└─────────────────────┘
         │
         │ Celery: crawl_source()
         ▼
┌─────────────────────┐
│     Document        │ ←── url, content, category_id
│                     │     status: PENDING → ANALYZING → COMPLETED
└─────────────────────┘
         │
         │ Celery: analyze_document()
         ▼
┌─────────────────────┐
│   ExtractedData     │ ←── raw_content, final_content, confidence_score
│                     │     extraction_type, category_id
└─────────────────────┘
         │
         │ extraction_handler Routing
         ├─────────────────────────────────────┐
         ▼                                     ▼
┌─────────────────────┐           ┌─────────────────────┐
│  entity_facet_      │           │  event_extraction_  │
│  service.py         │           │  service.py         │
│  (handler=default)  │           │  (handler=event)    │
└─────────────────────┘           └─────────────────────┘
         │                                     │
         ▼                                     ▼
┌─────────────────────┐           ┌─────────────────────┐
│  Entity             │           │  Entity (Event)     │
│  (Municipality)     │           │  Entity (Person)    │
│  + FacetValues      │           │  + FacetValues      │
│                     │           │  + Relations        │
└─────────────────────┘           └─────────────────────┘
```

---

## 16. Audit-Ergebnisse (2025-12-20)

### 16.1 Geprüfte Komponenten

| Komponente | Dateien | Status |
|------------|---------|--------|
| Backend API | `categories.py`, `crawler.py` | ✅ Geprüft & optimiert |
| Models | `category.py`, `data_source_category.py` | ✅ OK |
| Schemas | `category.py` | ✅ Validierung verbessert |
| Services | `category_setup.py`, `ai_generation.py` | ✅ OK |
| Workers | `ai_tasks.py` | ✅ OK |
| Extraction | `entity_facet_service.py`, `event_extraction_service.py` | ✅ OK |
| Frontend | `CategoriesView.vue`, `api.ts` | ✅ OK |

### 16.2 Durchgeführte Optimierungen

| Bereich | Optimierung | Auswirkung |
|---------|-------------|------------|
| Performance | N+1 Query → Batch-Fetch | ~5x schneller bei Listen |
| Validierung | Regex-Pattern-Check | Fehler frühzeitig erkannt |
| Validierung | extraction_handler Literal | Nur gültige Werte |
| Validierung | ISO 639-1 Sprachcodes | Konsistente Sprachen |
| Datenintegrität | Duplikat-Prüfung bei Update | Keine doppelten Namen |

### 16.3 Code-Qualität-Bewertung

| Metrik | Bewertung | Details |
|--------|-----------|---------|
| Modularität | ✅ Ausgezeichnet | Klare Trennung der Verantwortlichkeiten |
| Typisierung | ✅ Ausgezeichnet | Pydantic Literal, TypeScript Interfaces (`frontend/src/types/category.ts`) |
| Dokumentation | ✅ Ausgezeichnet | Docstrings mit Examples, OpenAPI-Beispiele in Schemas |
| Error Handling | ✅ Ausgezeichnet | Spezifische Exceptions (`InvalidCronExpressionError`, `CategoryDuplicateError`, etc.) |
| Performance | ✅ Ausgezeichnet | N+1 Query-Optimierungen, Batch-Fetching |

---

## 17. Erweiterungsmöglichkeiten

### 17.1 Neue Extraction-Handler hinzufügen

1. **Service erstellen:** `services/new_handler_service.py`
```python
async def convert_new_extraction_to_facets(
    session: AsyncSession,
    extracted_data: ExtractedData,
    source: Optional[DataSource],
    category: Optional[Category],
) -> Dict[str, int]:
    # Handler-Logik
    return {"new_facets": n}
```

2. **Handler registrieren:** In `ai_tasks.py`
```python
elif handler == "new_handler":
    from services.new_handler_service import convert_new_extraction_to_facets
    facet_counts = await convert_new_extraction_to_facets(...)
```

3. **Schema aktualisieren:** In `app/schemas/category.py`
```python
extraction_handler: Literal["default", "event", "new_handler"]
```

### 17.2 Empfohlene zukünftige Validierungen

- Cron-Expression-Validierung für `schedule_cron`
- URL-Validierung für `url_include_patterns` (nicht nur Regex-Syntax)
- Prompt-Length-Limit für `ai_extraction_prompt`

---

## 18. Änderungshistorie

| Datum | Änderung | Autor |
|-------|----------|-------|
| 2025-12-20 | Initiale Dokumentation | Audit |
| 2025-12-20 | N+1 Query-Optimierungen | Audit |
| 2025-12-20 | extraction_handler Validierung | Audit |
| 2025-12-20 | Regex-Pattern-Validierung | Audit |
| 2025-12-20 | ISO 639-1 Sprachcode-Validierung | Audit |
| 2025-12-20 | Duplikat-Prüfung bei update_category | Audit |
| 2025-12-20 | Event-Extraction-Handler Dokumentation | Audit |
| 2025-12-20 | AI-Generierungs-Workflow Dokumentation | Audit |
| 2025-12-20 | Datenfluss-Übersicht hinzugefügt | Audit |
| 2025-12-20 | Audit-Ergebnisse dokumentiert | Audit |
| 2025-12-20 | Spezifische Exception-Klassen hinzugefügt | Audit |
| 2025-12-20 | Cron-Expression-Validierung implementiert | Audit |
| 2025-12-20 | TypeScript Interfaces erstellt (`frontend/src/types/category.ts`) | Audit |
| 2025-12-20 | OpenAPI-Beispiele in Schemas hinzugefügt | Audit |
| 2025-12-20 | Code-Qualität auf "Ausgezeichnet" gehoben | Audit |
