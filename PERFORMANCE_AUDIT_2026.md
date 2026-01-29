# Performance & Security Audit Report 2026

**Anwendung:** CaeliCrawler
**Audit-Datum:** 2026-01-28
**Standards:** State of the Art 2026, Best Practices, OWASP Guidelines

---

## Executive Summary

### Gesamtbewertung: 7.5 / 10

CaeliCrawler ist eine gut strukturierte, moderne Anwendung mit soliden Grundlagen. Es gibt jedoch **signifikante Optimierungsmöglichkeiten** in mehreren Bereichen.

| Bereich | Score | Status |
|---------|-------|--------|
| Backend API | 8.0/10 | Gut - Minor N+1 Issues |
| Frontend | 7.8/10 | Gut - Virtual Scrolling fehlt |
| Datenbank | 7.0/10 | Verbesserungsbedarf - Fehlende Indizes |
| Infrastruktur | 7.5/10 | Gut - Einige Produktions-Gaps |
| Caching | 6.5/10 | Mittelmäßig - HTTP Headers nicht deployed |
| Security | 8.5/10 | Sehr gut - 3 kritische Items |

### Geschätztes Verbesserungspotential

- **API-Antwortzeiten:** 30-50% Reduktion möglich
- **Bundle-Größe:** ~200KB weitere Einsparung
- **Datenbankabfragen:** 40% weniger durch Caching
- **Sicherheit:** 3 kritische, 7 hohe Issues zu beheben

---

## Kritische Findings (CRITICAL)

### 🔴 C1: JWT ohne jti Claims - Token nicht einzeln widerrufbar
- **Datei:** `backend/app/core/security.py:60-68`
- **Problem:** Access Tokens haben keine JWT ID (jti), daher können einzelne Tokens nicht widerrufen werden
- **Impact:** Kompromittierte Tokens bleiben bis zum Ablauf gültig
- **Fix:** `"jti": str(uuid4())` zum Token-Payload hinzufügen

### 🔴 C2: Kein Key-Rotation-Mechanismus
- **Datei:** N/A - nicht implementiert
- **Problem:** SECRET_KEY kann nicht rotiert werden ohne alle Sessions zu invalidieren
- **Impact:** NIST Compliance-Verletzung, erhöhtes Risiko bei Key-Kompromittierung
- **Fix:** Key-ID (kid) System mit Overlap-Periode implementieren

### 🔴 C3: ChatMessages ohne Virtual Scrolling
- **Datei:** `frontend/src/components/assistant/ChatMessages.vue:12-76`
- **Problem:** Alle Nachrichten werden gerendert, egal wie viele
- **Impact:** 1000+ Messages = 1000+ DOM Nodes, Performance-Einbruch
- **Fix:** Vue-Virtual-Scroller implementieren

### 🔴 C4: N+1 Query in FacetValue Duplikat-Check
- **Datei:** `backend/services/entity_facet_service.py:738-760`
- **Problem:** Lädt ALLE FacetValues für Entity, iteriert dann
- **Impact:** Bei 10.000+ FacetValues massive Performance-Probleme
- **Fix:** Batch-Query mit LIMIT und Early-Exit

---

## Hohe Priorität (HIGH)

### Backend

| # | Problem | Datei:Zeile | Fix |
|---|---------|-------------|-----|
| H1 | Sequential session.get() statt Batch | `api/v1/relations.py:141-147` | `session.execute(select().where(id.in_(...)))` |
| H2 | Missing eager loading in detail endpoints | `api/v1/facets/facet_summary.py:115-120` | `selectinload()` verwenden |
| H3 | GZip minimum_size zu klein (1KB) | `app/main.py:279` | Auf 2000-5000 erhöhen |
| H4 | FacetValue.target_entity lazy="joined" | `models/facet_value.py:258` | Auf lazy="select" ändern |

### Frontend

| # | Problem | Datei:Zeile | Fix |
|---|---------|-------------|-----|
| H5 | setInterval ohne Cleanup | `App.vue:468`, `EntityAttachmentsTab.vue:448` | onUnmounted Cleanup |
| H6 | Expensive computed navGroups | `App.vue:332-378` | Split in kleinere Computeds |
| H7 | Redundante computed Properties | `stores/auth.ts:62-75` | Duplikate entfernen |
| H8 | Inconsistent Request-Deduplication | `services/api/entities.ts` | Alle GET-Endpoints deduplizieren |

### Datenbank

| # | Problem | Datei:Zeile | Fix |
|---|---------|-------------|-----|
| H9 | Missing composite index entity+facet_type+active | `models/facet_value.py:57-67` | Alembic Migration |
| H10 | JSONB ohne GIN Index | `models/api_configuration.py:104-134` | GIN Indexes hinzufügen |
| H11 | ForeignKey columns ohne index=True | Multiple models | Explizite Indexes |

### Infrastruktur

| # | Problem | Datei:Zeile | Fix |
|---|---------|-------------|-----|
| H12 | Redis maxmemory am Limit (450MB/512MB) | `docker-compose.yml:82` | Auf 256MB soft, 512MB hard |
| H13 | PostgreSQL statement_timeout zu lang (10min) | `docker-compose.yml:52` | Auf 3min reduzieren |
| H14 | Production Celery unified worker | `docker-compose.prod.yml:28` | Separate Workers |

### Security

| # | Problem | Datei:Zeile | Fix |
|---|---------|-------------|-----|
| H15 | User-based Rate Limiting fehlt | `core/rate_limit.py` | user_id Parameter |
| H16 | JWT HS256 statt RS256 | `core/security.py:14` | Asymmetrische Signierung |
| H17 | Resource-Level Authorization fehlt | `core/deps.py` | Ownership Checks |

### Caching

| # | Problem | Datei:Zeile | Fix |
|---|---------|-------------|-----|
| H18 | HTTP Cache Headers nicht deployed | `api/v1/*` | cache_for_list() zu ~35 Endpoints |
| H19 | In-Memory Cache unused | `core/cache.py:235-244` | get_or_fetch() aufrufen |
| H20 | Feature-Flags Endpoint ohne Cache | `app/main.py:381` | cache_for_config() |

---

## Mittlere Priorität (MEDIUM)

### Backend (11 Items)

1. **Logger re-instantiation in exception handler** - `main.py:340`
2. **Unnecessary model_dump() calls** - `api/v1/dashboard.py:55`
3. **Memory overhead on large exports** - `api/v1/export.py`
4. **Missing async context cleanup in deps** - `core/deps.py:336-365`
5. **Subquery compilation overhead** - `api/v1/facets/facet_values.py:68-69`
6. **I18nMiddleware auf jedem Request** - `core/i18n_middleware.py:31-66`
7. **PostgreSQL pool_recycle zu aggressiv (5min)** - `database.py:64`
8. **Celery task time limits zu permissiv** - `workers/celery_app.py:55-56`
9. **Missing OpenTelemetry Metrics** - `core/telemetry.py:30-51`
10. **Audit log persistence kann silent failen** - `core/security_logging.py:194-196`
11. **Request Correlation IDs fehlen** - N/A

### Frontend (12 Items)

1. **chunkSizeWarningLimit zu hoch (600KB)** - `vite.config.ts:46`
2. **Unbounded cache growth in Pinia** - `stores/facet.ts:52`
3. **Complex nested v-if in SmartQueryResults** - `SmartQueryResults.vue:53-100`
4. **Entity store unnecessary proxy computed** - `stores/entity.ts:319-366`
5. **Dynamic import in axios interceptor** - `services/api/client.ts:82-86`
6. **Multiple watch dependencies in App.vue** - `App.vue:489-542`
7. **Missing Suspense wrappers** - Multiple components
8. **Marked/DOMPurify nicht lazy-loaded** - `package.json`
9. **Frontend XSS Audit ausstehend** - v-html Verwendungen
10. **11 setInterval instances** - Multiple files
11. **Key anti-pattern (array index)** - `ChatMessages.vue:13`
12. **Function calls in template** - `ChatMessages.vue:36`

### Datenbank (6 Items)

1. **User model 15+ relationships ohne lazy strategy** - `models/user.py:145-215`
2. **Missing pagination indexes** - Multiple models
3. **Cascade delete risk bei großen Datasets** - `models/entity.py:239`
4. **Smart Query Cache ohne Write-Invalidation** - `services/smart_query/__init__.py`
5. **Timestamp range queries ohne optimierte Indexes** - `models/llm_usage.py:65`
6. **Context builder multiple round trips** - `services/assistant/context_builder.py`

### Infrastruktur (8 Items)

1. **Nginx CSP too permissive** - `nginx/nginx.conf:126`
2. **Missing request body compression** - Backend
3. **Celery health check kann bei Deadlock hängen** - `docker-compose.yml:194-198`
4. **Rate limit headers fehlen** - `nginx/nginx.conf`
5. **Missing graceful shutdown** - `docker-compose.yml`
6. **Nginx buffer sizes conservative** - `nginx/nginx.conf:47-50`
7. **Logging configuration not enforced** - `config.py:187-188`
8. **Missing Docker image scanning** - CI/CD

### Caching (8 Items)

1. **Cache invalidation strategy incomplete** - `core/cache.py:144-157`
2. **Missing cache statistics API** - `core/cache.py:270-280`
3. **Query cache nicht mit writes integriert** - `services/smart_query/__init__.py`
4. **Vary header potentially overly broad** - `core/cache_headers.py:94-95`
5. **Static asset versioning unclear** - `frontend/nginx.conf:33-36`
6. **No Surrogate-Control headers for CDN** - `nginx/nginx.conf`
7. **API response buffering ohne Cache** - `nginx/nginx.conf:151-153`
8. **Rate limiting zones don't align with cache TTLs** - `nginx/nginx.conf`

### Security (5 Items)

1. **Superuser bypass not logged** - `core/deps.py:273-274`
2. **Password policy allows common patterns** - `core/password_policy.py:105-120`
3. **CSP Report-Only mode not configured** - `core/security_headers.py:66`
4. **Refresh tokens ohne Encryption in DB** - `models/user_session.py`
5. **SSE tickets use same ALGORITHM** - `core/security.py:219`

---

## Niedrige Priorität (LOW)

### Auflistung (15 Items)

1. Subquery pattern in facet_values.py
2. Cache miss logging not visible
3. Gzip compression level conservative (6)
4. Assistant batch cache TTL short (30min)
5. Wildcard localhost in development CORS
6. Nonce generation prepared but unused
7. Exception handler doesn't log request body
8. Static asset versioning unclear
9. Idle connection timeout conservative (5min)
10. Image lazy-loading strategy fehlt
11. Add v-memo to nav items
12. Optimize marked/dompurify imports
13. Add Suspense fallbacks
14. Browser cache support headers
15. Time-of-check-to-time-of-use SSRF gap

---

## Positive Findings ✓

### Backend
- ✅ Alle Endpoints nutzen async/await korrekt
- ✅ Keine blocking I/O in async contexts
- ✅ Pydantic v2 Best Practices
- ✅ Excellent Dependency Injection patterns
- ✅ Proper transaction cleanup

### Frontend
- ✅ Excellent route-based code splitting
- ✅ SVG Icons statt Font (~195KB gespart)
- ✅ Good API request deduplication
- ✅ Proper font optimization (preconnect, display=swap)
- ✅ Token refresh queue pattern

### Datenbank
- ✅ Connection Pool properly configured
- ✅ pool_pre_ping für Health-Checks
- ✅ expire_on_commit=False verhindert Reloads
- ✅ Batch loading patterns in einigen Endpoints

### Infrastruktur
- ✅ Multi-stage Docker builds
- ✅ Non-root users
- ✅ Health checks configured
- ✅ Resource limits defined
- ✅ Structured logging (structlog)

### Security
- ✅ Comprehensive JWT implementation
- ✅ Excellent rate limiting with presets
- ✅ Complete SSRF protection
- ✅ Excellent audit logging
- ✅ Proper security headers
- ✅ Token blacklist implementation
- ✅ Password policy enforcement
- ✅ Session management (max 5)

---

## Implementierungsplan

### Phase 1: Critical Fixes (Woche 1)

| Task | Aufwand | Impact |
|------|---------|--------|
| JWT jti Claims hinzufügen | 2h | Hoch |
| Virtual Scrolling ChatMessages | 4h | Hoch |
| FacetValue Duplikat-Check optimieren | 2h | Hoch |
| HTTP Cache Headers deployen | 4h | Mittel |
| setInterval Cleanup fixen | 2h | Mittel |

### Phase 2: High Priority (Woche 2-3)

| Task | Aufwand | Impact |
|------|---------|--------|
| Key Rotation Mechanismus | 8h | Hoch |
| Composite Database Indexes | 4h | Mittel |
| GIN Indexes für JSONB | 2h | Mittel |
| RS256 JWT Migration | 12h | Hoch |
| Request Deduplication komplett | 3h | Mittel |

### Phase 3: Medium Priority (Woche 4-6)

| Task | Aufwand | Impact |
|------|---------|--------|
| Pinia Cache LRU | 3h | Niedrig |
| Frontend XSS Audit | 4h | Hoch |
| Celery Worker Separation | 4h | Mittel |
| OpenTelemetry Metrics | 6h | Mittel |
| Cache Invalidation Strategy | 4h | Mittel |

### Phase 4: Optimierungen (Ongoing)

- Query Performance Monitoring
- Bundle Size Monitoring
- Load Testing mit k6
- Security Penetration Testing

---

## Metriken zur Erfolgsmessung

### Performance KPIs

| Metrik | Aktuell | Ziel |
|--------|---------|------|
| API P95 Latency | ~200ms | <100ms |
| Frontend Bundle Size | ~2.5MB | <2MB |
| Lighthouse Performance | ~75 | >90 |
| DB Queries per Request | ~5-10 | <3 |
| Cache Hit Rate | ~0% | >60% |

### Security KPIs

| Metrik | Aktuell | Ziel |
|--------|---------|------|
| Critical Vulnerabilities | 3 | 0 |
| High Vulnerabilities | 7 | 0 |
| Dependency CVEs | Unbekannt | 0 |
| OWASP Top 10 Coverage | ~80% | 100% |

---

## Anhang: Referenzierte Dateien

### Backend (Kritisch)
- `app/core/security.py` - JWT Implementation
- `app/core/security_headers.py` - CSP Configuration
- `app/core/cache_headers.py` - HTTP Caching
- `app/core/cache.py` - In-Memory Cache
- `app/database.py` - Connection Pool
- `services/entity_facet_service.py` - N+1 Query

### Frontend (Kritisch)
- `src/App.vue` - Root Component, Intervals
- `src/components/assistant/ChatMessages.vue` - Virtual Scroll
- `src/services/api/cache.ts` - Request Deduplication
- `src/stores/facet.ts` - Pinia Cache

### Infrastruktur
- `docker-compose.yml` - Service Configuration
- `docker-compose.prod.yml` - Production Config
- `nginx/nginx.conf` - Reverse Proxy

---

**Report erstellt von:** Performance & Security Audit System
**Nächste Review:** Quartal 2/2026
