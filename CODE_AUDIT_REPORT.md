# Code-Audit-Bericht: CaeliCrawler

**Datum:** 2025-12-21
**Auditor:** Claude Code
**Umfang:** Backend AI Source Discovery, Multi-Entity Extraction, Smart Query Operations, Frontend Components

---

## Executive Summary

### Gesamtbewertung: **GUT** (7.5/10)

Das CaeliCrawler-Projekt zeigt eine solide Code-Qualität mit professioneller Architektur und durchdachten Sicherheitsmaßnahmen. Es gibt jedoch Verbesserungspotenzial in den Bereichen Error Handling, TypeScript-Nutzung und Accessibility.

### Highlights
- Exzellenter SSRF-Schutz in der AI Source Discovery
- Erfolgreiche N+1 Query-Optimierung im Multi-Entity Service
- Sauberes Command Pattern in Smart Query Operations
- Gute TypeScript-Interfaces im Frontend

### Kritische Punkte
- Frontend: Fehlende TypeScript-Typen für API-Responses
- Unzureichende Error-Boundary-Implementierung
- Mangelhafte ARIA-Labels und Accessibility-Features
- Inkonsistente Validierung über verschiedene Module

---

## 1. Backend AI Source Discovery

**Bewertung: EXCELLENT** (9/10)

### 1.1 discovery_service.py

#### Stärken
- **SSRF-Schutz (Zeile 35-90)**: Exzellente Implementierung
  - Blockierung privater IP-Ranges (10.x, 172.16-31.x, 192.168.x)
  - DNS-Auflösung und IP-Validierung
  - Post-Redirect-Validierung (Zeile 295-303)
  - Pattern-basierte Hostname-Filterung (internal, intranet, etc.)

- **Parallele Requests (Zeile 268-346)**: Sehr gut implementiert
  - Asyncio Semaphore für Concurrency-Limiting (max_concurrent=5)
  - Graceful Error Handling mit `return_exceptions=True`
  - Timeout-Schutz (30s per Request)

- **Code-Qualität**:
  - Strukturiertes Logging mit structlog
  - Klare Phasentrennung (Search Strategy → Web Search → Extraction → Deduplication → Tagging)
  - Gute Docstrings und Type Hints

#### Schwachstellen

**MITTEL: Fehlende Rate Limiting innerhalb des Service**
- **Zeile 152-155**: `search_provider.search()` hat kein internes Rate Limiting
- **Empfehlung**: Token-Bucket oder Sliding-Window-Algorithmus implementieren
```python
# Vorschlag:
from aiolimiter import AsyncLimiter
rate_limiter = AsyncLimiter(max_rate=10, time_period=60)  # 10 requests/minute

async def search_with_rate_limit(self, queries):
    async with self.rate_limiter:
        return await self.search_provider.search(queries)
```

**NIEDRIG: Hardcodierte Timeout-Werte**
- **Zeile 285**: `timeout=30.0` sollte konfigurierbar sein
```python
# Vorschlag:
timeout = settings.discovery_request_timeout or 30.0
```

**NIEDRIG: Keine Retry-Logik für transiente Fehler**
- **Zeile 326-329**: HTTPError wird nur geloggt, kein Retry
- **Empfehlung**: Tenacity für exponential backoff
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def fetch_with_retry(url):
    ...
```

---

### 1.2 ai_discovery.py (Admin API)

#### Stärken
- **Rate Limiting (Zeile 91)**: Gut implementiert mit User-spezifischem Identifier
- **SSRF-Schutz (Zeile 145-152)**: Doppelte Validierung bei Import
- **Input Validation**: Pydantic-Modelle für Request-Validierung

#### Schwachstellen

**MITTEL: Fehlende Request-Size-Limits**
- **Zeile 111-203**: `import_discovered_sources` hat keine Begrenzung für Array-Größe
```python
# Vorschlag:
class DiscoveryImportRequest(BaseModel):
    sources: List[SourceWithTags] = Field(..., min_length=1, max_length=100)  # Max 100
```

**NIEDRIG: Keine Logging von Security-Events**
- **Zeile 148-152**: SSRF-Blockierung wird nicht zentral geloggt
```python
# Vorschlag:
logger.warning(
    "SSRF attempt blocked",
    user_id=user.id,
    url=source.base_url,
    reason=error_msg,
)
```

---

### 1.3 Extractors (base.py, html_table_extractor.py, wikipedia_extractor.py, ai_extractor.py)

#### Stärken
- **Modulares Design**: Sauberes Strategy Pattern mit `BaseExtractor`
- **Wikipedia-Extractor**: Robuste Extraktion aus verschiedenen Strukturen (Infoboxes, Wikitables, Listen)
- **HTML-Table-Extractor**: Gute Heuristiken für Spalten-Erkennung

#### Schwachstellen

**MITTEL: Fehlende Input-Sanitization in Extractors**
- **html_table_extractor.py Zeile 47-49**: `_clean_text()` verwendet regex, aber keine HTML-Escape-Validierung
- **wikipedia_extractor.py Zeile 113-122**: Keine URL-Validierung vor der Erstellung von ExtractedSource
```python
# Vorschlag in base.py:
def _sanitize_url(self, url: str) -> Optional[str]:
    """Sanitize and validate URL before use."""
    import html
    url = html.unescape(url)
    if not self._is_valid_url(url):
        return None
    return url
```

**NIEDRIG: AI-Extractor nutzt unsicheren JSON-Parse**
- **ai_extractor.py Zeile 66**: `json.loads()` ohne Schema-Validierung
```python
# Vorschlag:
from pydantic import ValidationError
try:
    extracted_items = ExtractedSourceList.parse_raw(content)
except ValidationError as e:
    logger.error("Invalid AI response schema", error=str(e))
    return []
```

**NIEDRIG: BeautifulSoup Import-Fehler nicht gehandhabt**
- **wikipedia_extractor.py Zeile 36-39**: Gibt leere Liste zurück, sollte Exception werfen
```python
# Vorschlag:
try:
    from bs4 import BeautifulSoup
except ImportError:
    raise RuntimeError("BeautifulSoup4 is required for WikipediaExtractor")
```

---

## 2. Backend Multi-Entity Extraction

**Bewertung: GUT** (8/10)

### 2.1 multi_entity_extraction_service.py

#### Stärken
- **N+1 Query Fix (Zeile 276-302)**: Exzellente Batch-Optimierung
  - Single Query für alle Entity-Namen
  - Dict-Mapping für O(1) Lookups
  - Gut dokumentiert

- **Transaction Management**: Konsistente Verwendung von `flush()` und `commit()`

- **Error Handling**: Try-Except in `process_extraction_result` mit detailliertem Logging

#### Schwachstellen

**MITTEL: Fehlende Batch-Size-Limits**
- **Zeile 180-189**: `_batch_find_entities` hat keine Größenbeschränkung für `names`-Liste
- **Problem**: Bei 10.000+ Entities könnte SQL IN-Clause zu groß werden
```python
# Vorschlag:
async def _batch_find_entities(
    self, entity_type_id: UUID, names: List[str]
) -> Dict[str, Entity]:
    """Batch find with chunking for large lists."""
    if not names:
        return {}

    result_map = {}
    # Chunk into batches of 500
    for i in range(0, len(names), 500):
        chunk = names[i:i+500]
        result = await self.session.execute(
            select(Entity).where(
                Entity.entity_type_id == entity_type_id,
                Entity.name.in_(chunk),
                Entity.deleted_at.is_(None),
            )
        )
        result_map.update({entity.name: entity for entity in result.scalars().all()})

    return result_map
```

**NIEDRIG: Redundante Query in add_entity_type_to_category**
- **Zeile 405-413**: Query wird ausgeführt, auch wenn `is_primary=False`
```python
# Vorschlag:
if is_primary:
    result = await self.session.execute(...)
    for existing in result.scalars().all():
        existing.is_primary = False
```

**NIEDRIG: Fehlende Validierung der Relation-Konfiguration**
- **Zeile 90-101**: `relation_config` wird nicht validiert
```python
# Vorschlag:
from pydantic import BaseModel, validator

class RelationConfigItem(BaseModel):
    from_type: str
    to_type: str
    relation: str

    @validator('relation')
    def validate_relation(cls, v):
        allowed = ['related_to', 'located_in', 'member_of', 'attends']
        if v not in allowed:
            raise ValueError(f"Invalid relation: {v}")
        return v
```

---

### 2.2 category_entity_type.py (Model)

#### Stärken
- **Sauberes Schema**: Gut strukturierte N:M-Relation
- **Constraints**: UniqueConstraint verhindert Duplikate
- **Type Hints**: Vollständige Mapped-Annotations

#### Schwachstellen

**NIEDRIG: Fehlende Validierung auf Model-Ebene**
- **Zeile 85-90**: `relation_config` als JSONB ohne Schema
```python
# Vorschlag: Pydantic-Validator hinzufügen
from sqlalchemy.ext.hybrid import hybrid_property

@hybrid_property
def validated_relation_config(self):
    """Validate relation config structure."""
    if not self.relation_config:
        return []
    # Validate structure
    for rel in self.relation_config:
        if not all(k in rel for k in ['from_type', 'to_type', 'relation']):
            raise ValueError("Invalid relation config structure")
    return self.relation_config
```

---

## 3. Backend Smart Query Operations

**Bewertung: EXCELLENT** (9/10)

### 3.1 operations/base.py (Command Pattern)

#### Stärken
- **Sauberes Command Pattern**: Exzellente Architektur
  - Abstract Base Class mit `@abstractmethod`
  - Registry-Pattern für Operation-Handler
  - Standardisierter `OperationResult`-Container

- **Modularität**: Operations sind isoliert und testbar

- **Fehlerbehandlung**: Graceful Fallback zu Legacy-Executor (Zeile 219-229)

#### Schwachstellen

**NIEDRIG: Fehlende Operation-Logging**
- **Zeile 201-217**: Keine strukturierte Audit-Log-Einträge
```python
# Vorschlag:
async def execute_operation(...):
    start_time = time.time()
    logger.info(
        "Operation started",
        operation=operation_name,
        user_id=str(user_id) if user_id else None,
    )
    try:
        result = await handler.execute(session, command, user_id)
        logger.info(
            "Operation completed",
            operation=operation_name,
            success=result.success,
            duration_ms=(time.time() - start_time) * 1000,
        )
        return result
    except Exception as e:
        logger.error(..., duration_ms=(time.time() - start_time) * 1000)
```

**NIEDRIG: Keine Operation-Timeouts**
- **Zeile 202**: `await handler.execute()` hat keinen Timeout
```python
# Vorschlag:
import asyncio
result = await asyncio.wait_for(
    handler.execute(session, command, user_id),
    timeout=300.0  # 5 minutes
)
```

---

### 3.2 operations/discovery.py

#### Stärken
- **Validierung (Zeile 50-64)**: Umfassende Input-Validierung
- **Dokumentation**: Exzellentes Docstring mit Beispiel
- **Fehlerbehandlung**: Try-Except mit detailliertem Logging

#### Schwachstellen

**NIEDRIG: Keine Caching-Strategie**
- Identische Prompts führen zu wiederholten teuren AI-Anfragen
```python
# Vorschlag:
import hashlib
from aiocache import Cache

cache = Cache(Cache.REDIS)

async def execute(...):
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
    cache_key = f"discovery:{prompt_hash}:{search_depth}"

    cached = await cache.get(cache_key)
    if cached:
        return OperationResult(**cached)

    result = await service.discover_sources(...)
    await cache.set(cache_key, result.dict(), ttl=3600)
    return result
```

---

### 3.3 write_executor.py (Legacy)

#### Stärken
- **Vollständigkeit**: Deckt viele Operations ab
- **Transaction-Handling**: Konsistent mit commit/rollback

#### Schwachstellen

**MITTEL: Monolithische Struktur**
- **Zeile 23-279**: 250+ Zeilen in einer Funktion
- **Empfehlung**: Schrittweise Migration zu Command Pattern (bereits begonnen)

**NIEDRIG: Duplikate Code**
- **Zeile 769-841, 972-1149**: `execute_delete_entity` und `execute_batch_delete` haben ähnliche Logik
```python
# Vorschlag: Extract common soft-delete logic
async def _soft_delete_entity(entity: Entity, reason: str):
    entity.is_active = False
    if entity.core_attributes is None:
        entity.core_attributes = {}
    entity.core_attributes["_deletion_reason"] = reason
    entity.core_attributes["_deleted_at"] = str(datetime.now(timezone.utc).isoformat())
```

---

## 4. Frontend Components

**Bewertung: GUT** (7/10)

### 4.1 AiDiscoveryDialog.vue

#### Stärken
- **TypeScript-Interfaces (Zeile 297-350)**: Exzellente Type-Definitionen
  - `DiscoverySource`, `SearchStrategy`, `DiscoveryStats`
  - Klare Strukturen für API-Responses

- **Accessibility**: Gute ARIA-Labels
  - `aria-labelledby` (Zeile 7)
  - `aria-label` für Buttons (Zeile 25, 192)
  - `role="dialog"` (Zeile 8)

- **User Experience**:
  - Multi-Phase-UI (input → searching → results)
  - Loading-States mit Progress-Indikatoren
  - Preview-Tabelle mit Confidence-Scores

#### Schwachstellen

**MITTEL: Fehlende TypeScript-Validierung für API-Responses**
- **Zeile 461**: `response.data as DiscoveryResult` - Unsicheres Type-Casting
```typescript
// Vorschlag: Runtime-Validierung mit Zod
import { z } from 'zod'

const DiscoveryResultSchema = z.object({
  sources: z.array(DiscoverySourceSchema),
  search_strategy: SearchStrategySchema.nullable(),
  stats: DiscoveryStatsSchema,
  warnings: z.array(z.string()),
})

const response = await adminApi.discoverSources(...)
const validatedData = DiscoveryResultSchema.parse(response.data)
discoveryResult.value = validatedData
```

**MITTEL: Unzureichendes Error Handling**
- **Zeile 416-425**: `getErrorMessage()` ist zu generisch
```typescript
// Vorschlag: Spezifische Error-Types
interface ApiError {
  response?: {
    status: number
    data?: {
      detail?: string
      message?: string
      error_code?: string
    }
  }
  message?: string
}

const getErrorMessage = (error: unknown): string => {
  const apiError = error as ApiError
  const status = apiError.response?.status

  if (status === 429) {
    return t('errors.rateLimitExceeded')
  } else if (status === 403) {
    return t('errors.insufficientPermissions')
  } else if (status === 503) {
    return t('errors.serviceUnavailable')
  }

  return apiError.response?.data?.detail
    || apiError.response?.data?.message
    || apiError.message
    || t('common.unknownError')
}
```

**NIEDRIG: Fehlende ARIA-Live-Regions für dynamische Inhalte**
- **Zeile 115-140**: Searching-Phase hat keine Screenreader-Ankündigungen
```vue
<!-- Vorschlag -->
<v-card variant="outlined" class="pa-6 text-center" role="status" aria-live="polite">
  <v-progress-circular ... aria-label="Searching for sources"></v-progress-circular>
  <div class="text-h6 mb-2" aria-live="assertive">{{ $t('sources.aiDiscovery.searching') }}</div>
  ...
</v-card>
```

**NIEDRIG: Keine Keyboard-Navigation für Beispiele**
- **Zeile 67-77**: Chips sind nur mit Maus klickbar
```vue
<!-- Vorschlag -->
<v-chip
  ...
  @click="prompt = example.prompt"
  @keydown.enter="prompt = example.prompt"
  @keydown.space="prompt = example.prompt"
  tabindex="0"
  role="button"
>
```

---

### 4.2 SourcesView.vue

#### Stärken
- **Composable-Nutzung (Zeile 865-872)**: Gute Code-Organisation
- **URL-Validierung (Zeile 1058-1066)**: Robuste Client-Side-Validierung
- **Bulk-Import-Preview (Zeile 1306-1416)**: Exzellente UX mit Fehlerdarstellung

#### Schwachstellen

**MITTEL: Fehlende TypeScript-Types für State**
- **Zeile 878**: `sources = ref<any[]>([])` - Untypisiert
```typescript
// Vorschlag:
interface DataSource {
  id: string
  name: string
  base_url: string
  source_type: 'WEBSITE' | 'OPARL_API' | 'RSS' | 'CUSTOM_API'
  status: 'ACTIVE' | 'INACTIVE' | 'ERROR'
  categories?: Array<{
    id: string
    name: string
    is_primary: boolean
  }>
  last_crawl?: string
  document_count: number
  tags: string[]
  crawl_config: CrawlConfig
}

const sources = ref<DataSource[]>([])
```

**MITTEL: Unzureichende Form-Validierung**
- **Zeile 1239-1245**: Validierung erfolgt erst beim Submit
```typescript
// Vorschlag: Real-time validation
const formErrors = computed(() => {
  const errors: Record<string, string> = {}

  if (formData.value.name && formData.value.name.length < 2) {
    errors.name = t('sources.validation.nameTooShort')
  }

  if (formData.value.base_url && !isValidUrl(formData.value.base_url)) {
    errors.base_url = t('sources.validation.urlInvalid')
  }

  return errors
})
```

**NIEDRIG: CSV-Parser ist anfällig für Injection**
- **Zeile 1322-1399**: Keine Sanitization von CSV-Input
```typescript
// Vorschlag:
import DOMPurify from 'dompurify'

const parts = line.split(delimiter).map(p => DOMPurify.sanitize(p.trim()))
```

**NIEDRIG: Fehlende Accessibility für Tabellen-Actions**
- **Zeile 198-203**: Icon-Buttons haben nur `title`, kein `aria-label`
```vue
<!-- Vorschlag -->
<v-btn
  icon="mdi-pencil"
  size="small"
  variant="tonal"
  :aria-label="$t('common.edit') + ' ' + item.name"
  @click="openEditDialog(item)"
></v-btn>
```

---

## 5. Gesamtempfehlungen

### 5.1 Security

#### HOCH: Zentrale Security-Logging implementieren
```python
# backend/app/core/security_logging.py
import structlog
from typing import Optional
from uuid import UUID

logger = structlog.get_logger()

def log_ssrf_attempt(user_id: Optional[UUID], url: str, reason: str):
    logger.warning(
        "SSRF attempt blocked",
        event_type="security.ssrf_blocked",
        user_id=str(user_id) if user_id else None,
        url=url,
        reason=reason,
    )

def log_rate_limit_exceeded(user_id: UUID, endpoint: str):
    logger.warning(
        "Rate limit exceeded",
        event_type="security.rate_limit",
        user_id=str(user_id),
        endpoint=endpoint,
    )
```

#### MITTEL: API-Input-Size-Limits
```python
# backend/app/core/config.py
class Settings(BaseSettings):
    max_import_batch_size: int = Field(default=100)
    max_search_results: int = Field(default=200)
    max_extraction_entities: int = Field(default=1000)
```

---

### 5.2 Performance

#### HOCH: Caching-Layer für teure Operations
```python
# backend/app/core/cache.py
from functools import wraps
import hashlib
import json
from typing import Any, Callable

def cached(ttl: int = 3600, key_prefix: str = ""):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from args
            cache_key = f"{key_prefix}:{hashlib.sha256(
                json.dumps([args, kwargs], sort_keys=True).encode()
            ).hexdigest()}"

            # Check cache
            cached_value = await redis_client.get(cache_key)
            if cached_value:
                return json.loads(cached_value)

            # Execute and cache
            result = await func(*args, **kwargs)
            await redis_client.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator

# Usage:
@cached(ttl=1800, key_prefix="discovery")
async def discover_sources(prompt: str, max_results: int, search_depth: str):
    ...
```

---

### 5.3 Code Quality

#### MITTEL: Einheitliche Error-Response-Struktur
```typescript
// frontend/src/types/api.ts
export interface ApiErrorResponse {
  error_code: string
  message: string
  detail?: string
  field_errors?: Record<string, string[]>
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public response: ApiErrorResponse
  ) {
    super(response.message)
    this.name = 'ApiError'
  }

  get isRateLimitError(): boolean {
    return this.status === 429
  }

  get isAuthError(): boolean {
    return this.status === 401 || this.status === 403
  }
}

// Usage in components:
try {
  await api.call()
} catch (error) {
  if (error instanceof ApiError && error.isRateLimitError) {
    showError(t('errors.rateLimitExceeded'))
  }
}
```

---

### 5.4 Accessibility

#### MITTEL: Globale Accessibility-Helpers
```typescript
// frontend/src/composables/useAccessibility.ts
export function useAccessibility() {
  const announce = (message: string, priority: 'polite' | 'assertive' = 'polite') => {
    const liveRegion = document.getElementById('app-live-region')
    if (liveRegion) {
      liveRegion.setAttribute('aria-live', priority)
      liveRegion.textContent = message
      setTimeout(() => {
        liveRegion.textContent = ''
      }, 1000)
    }
  }

  const focusElement = (selector: string) => {
    const element = document.querySelector(selector) as HTMLElement
    if (element) {
      element.focus()
    }
  }

  return { announce, focusElement }
}

// Usage:
const { announce } = useAccessibility()
announce(t('sources.messages.crawlStarted'), 'polite')
```

```vue
<!-- App.vue -->
<template>
  <div id="app">
    <!-- Hidden live region for screen reader announcements -->
    <div
      id="app-live-region"
      class="sr-only"
      role="status"
      aria-live="polite"
    ></div>
    <router-view />
  </div>
</template>

<style>
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
```

---

## 6. Prioritätenliste

### Sofort (Kritisch)
1. ❗ **Zentrale Security-Logging implementieren** (discovery_service.py, ai_discovery.py)
2. ❗ **Input-Size-Limits hinzufügen** (ai_discovery.py, multi_entity_extraction_service.py)
3. ❗ **TypeScript-Types für API-Responses** (AiDiscoveryDialog.vue, SourcesView.vue)

### Kurzfristig (1-2 Wochen)
4. 🔶 **Batch-Size-Limits in multi_entity_extraction_service.py** (Zeile 276-302)
5. 🔶 **Runtime-Validierung mit Zod im Frontend** (AiDiscoveryDialog.vue)
6. 🔶 **Caching-Layer für AI-Discovery** (operations/discovery.py)
7. 🔶 **Error-Boundary-Komponente** (Frontend global)

### Mittelfristig (1 Monat)
8. 🔷 **Migration von write_executor.py zu Command Pattern**
9. 🔷 **Retry-Logik für transiente Fehler** (discovery_service.py)
10. 🔷 **Accessibility-Verbesserungen** (ARIA-Live, Keyboard-Navigation)

### Langfristig (3 Monate)
11. 🔹 **Comprehensive Testing-Suite**
12. 🔹 **Monitoring & Alerting für Security-Events**
13. 🔹 **Performance-Profiling und Optimierung**

---

## 7. Testabdeckung-Empfehlungen

### Backend
```python
# tests/test_security/test_ssrf_protection.py
@pytest.mark.parametrize("url,expected", [
    ("http://localhost/test", False),
    ("http://10.0.0.1/test", False),
    ("http://192.168.1.1/test", False),
    ("http://172.16.0.1/test", False),
    ("https://example.com", True),
])
async def test_is_safe_url(url, expected):
    from services.ai_source_discovery.discovery_service import is_safe_url
    assert is_safe_url(url) == expected
```

### Frontend
```typescript
// tests/unit/AiDiscoveryDialog.spec.ts
import { mount } from '@vue/test-utils'
import AiDiscoveryDialog from '@/components/sources/AiDiscoveryDialog.vue'

describe('AiDiscoveryDialog', () => {
  it('validates prompt is required', async () => {
    const wrapper = mount(AiDiscoveryDialog, {
      props: { modelValue: true, categories: [] }
    })

    const button = wrapper.find('[data-testid="start-search-btn"]')
    expect(button.attributes('disabled')).toBe('true')
  })

  it('handles API errors gracefully', async () => {
    // Mock API error
    vi.spyOn(adminApi, 'discoverSources').mockRejectedValue(
      new Error('Rate limit exceeded')
    )

    const wrapper = mount(AiDiscoveryDialog, ...)
    await wrapper.vm.startDiscovery()

    expect(wrapper.find('.v-alert--error').exists()).toBe(true)
  })
})
```

---

## 8. Metriken & Monitoring

### Empfohlene Metriken
```python
# backend/app/core/metrics.py
from prometheus_client import Counter, Histogram

# Discovery Service Metrics
discovery_requests = Counter(
    'discovery_requests_total',
    'Total AI discovery requests',
    ['status', 'search_depth']
)

discovery_duration = Histogram(
    'discovery_duration_seconds',
    'Discovery request duration',
    ['search_depth']
)

ssrf_blocks = Counter(
    'ssrf_blocks_total',
    'Total SSRF attempts blocked',
    ['user_id', 'url_pattern']
)

# Multi-Entity Extraction Metrics
entity_extractions = Counter(
    'entity_extractions_total',
    'Total entity extractions',
    ['category', 'entity_type']
)

batch_query_duration = Histogram(
    'batch_query_duration_seconds',
    'Batch entity lookup duration'
)
```

---

## Anhang: Checkliste für Code-Reviews

### Backend
- [ ] SSRF-Schutz bei allen URL-Inputs
- [ ] Rate Limiting auf teure Endpoints
- [ ] Input-Validierung mit Pydantic
- [ ] Batch-Size-Limits für Array-Parameter
- [ ] Strukturiertes Logging mit Context
- [ ] Transaction-Handling (commit/rollback)
- [ ] Type Hints für alle Funktionen
- [ ] Docstrings für Public APIs

### Frontend
- [ ] TypeScript-Interfaces für alle Props/Emits
- [ ] Runtime-Validierung für API-Responses
- [ ] Error-Handling mit spezifischen Messages
- [ ] Loading-States für Async-Operations
- [ ] ARIA-Labels für alle interaktiven Elemente
- [ ] Keyboard-Navigation (Tab, Enter, Space)
- [ ] Form-Validierung (Client-Side + Server-Side)
- [ ] Proper Input-Sanitization

---

**Ende des Audit-Berichts**
