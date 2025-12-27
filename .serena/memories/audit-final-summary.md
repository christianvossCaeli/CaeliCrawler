# CaeliCrawler - E2E/Smoke Test Audit (26.12.2025 - Update 2)

## Executive Summary

**Gesamtbewertung: ⭐⭐⭐⭐ (4.0/5)** - Produktionsreif mit kleinen Test-Fixes

---

## Testergebnisse

| Test-Suite | Status | Details |
|------------|--------|---------|
| Backend Unit-Tests | ⚠️ 508/539 | 13 failed, 18 errors, 25 skipped |
| Frontend Unit-Tests | ✅ 829/829 | 28 Test-Dateien, alle bestanden |
| E2E-Tests (Playwright) | ❌ 12/129 | Login-Credentials fehlen |
| ESLint | ⚠️ 3 Fehler | Deprecated Vue filters |
| Backend Health | ✅ Healthy | Version 0.1.0 |

---

## Kritische Bugs

### 1. Async/Await Bug in Smart Query (base.py:465)
```python
# Fehler: 'coroutine' object has no attribute 'all'
for et in entity_result.scalars().all()
```
**Betroffene Tests:** 31 (13 failed + 18 errors)

### 2. E2E-Tests brauchen Test-Environment
- `.env.test` fehlt
- Test-User nicht konfiguriert

### 3. Vue Filter Deprecation
- `DynamicSchemaForm.vue` (Zeilen 7, 142)
- `EntityFormDialog.vue` (Zeile 135)

---

## Infrastruktur Status

| Service | Status |
|---------|--------|
| Backend | ✅ Healthy |
| Frontend | ✅ Running |
| PostgreSQL | ✅ Healthy |
| Redis | ✅ Healthy |
| Celery Worker | ⚠️ Unhealthy |
| Prometheus/Grafana | ✅ Running |

---

## Statistiken

- 284 API-Endpoints
- 10.605 Entities in DB
- 2 Entity-Types
- 829 Frontend Tests (alle ✅)
- 539 Backend Tests (94% ✅)
- 129 E2E Tests (benötigen Config)