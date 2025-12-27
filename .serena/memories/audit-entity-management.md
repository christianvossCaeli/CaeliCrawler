# Entity-Management Audit (27.12.2025)

## Executive Summary

**Gesamtbewertung: ⭐⭐⭐⭐ (4.2/5)** - Gut strukturiert, einige Verbesserungspotentiale

---

## Analysierte Dateien

| Bereich | Datei | LOC | Bewertung |
|---------|-------|-----|-----------|
| Frontend View | `EntitiesView.vue` | 447 | ⭐⭐⭐⭐ |
| Frontend View | `EntityDetailView.vue` | 803 | ⭐⭐⭐⭐⭐ |
| Frontend Composable | `useEntitiesView.ts` | 704 | ⭐⭐⭐½ |
| Frontend API | `services/api/entities.ts` | 156 | ⭐⭐⭐⭐ |
| Backend API | `api/v1/entities.py` | ~1500 | ⭐⭐⭐⭐ |
| Backend Service | `entity_matching_service.py` | ~1014 | ⭐⭐⭐⭐⭐ |

---

## Kritische Issues

### 🔴 SQL-Injection-Risiko (HOCH)

**Betroffen:** `backend/app/api/v1/entities.py`

```python
# Zeile 143-147 - list_entities
query = query.where(
    or_(
        Entity.name.ilike(f"%{search}%"),  # UNSICHER!
        Entity.name_normalized.ilike(f"%{search}%"),
        Entity.external_id.ilike(f"%{search}%")
    )
)

# Zeile 691 - get_entities_geojson
query = query.where(Entity.name.ilike(f"%{search}%"))  # UNSICHER!
```

**Empfehlung:** Parameterisierte Queries verwenden oder User-Input escapen.

---

## Positive Findings

### Frontend

✅ **Komponentenarchitektur** (EntitiesView)
- 8 spezialisierte Subkomponenten in `/components/entities/`
- Lazy-Loading für MapView (schwere Abhängigkeit ~1MB)
- Gute Trennung von UI und Logik via Composables

✅ **Accessibility** 
- ARIA-Labels durchgehend
- role-Attribute für Screenreader
- Keyboard-Navigation unterstützt

✅ **EntityDetailView** - Exzellente Modularität
- 23 spezialisierte Tab-Komponenten
- 6 Composables für verschiedene Concerns:
  - `useEntityExport`
  - `useEntityNotes`
  - `useEntityRelations`
  - `useEntityDataSources`
  - `useEntityEnrichment`
  - `useEntityFacets`
- Cleanup in `onUnmounted`

✅ **Internationalisierung**
- Alle Strings via `$t()` übersetzt
- DE/EN Locales vorhanden

### Backend

✅ **Batch-Queries** - Keine N+1 Probleme
- `selectinload` für eager loading
- Batch-Counts für facets, relations, children

✅ **Race-Condition-Safety** (EntityMatchingService)
```python
try:
    await self.session.flush()
except IntegrityError as e:
    if "uq_entity_type_name_normalized" in str(e):
        await self.session.rollback()
        return await self._find_by_normalized_name(...)
```

✅ **Effizientes Cascade-Delete** via CTE
```sql
WITH RECURSIVE entity_tree AS (
    SELECT id FROM entities WHERE id = :entity_id
    UNION ALL
    SELECT e.id FROM entities e
    INNER JOIN entity_tree et ON e.parent_id = et.id
)
```

✅ **Audit-Logging** integriert
- `AuditContext` für alle schreibenden Operationen
- Änderungen werden getrackt

✅ **Entity-Matching Service** - State of the Art
- Composite Entity Detection (Regex-Pattern)
- Embedding-basierte Similarity Search (pgvector)
- Multi-Step Matching: external_id → normalized_name → core_name → embedding

---

## Verbesserungspotentiale

### 🟡 Memory Leak (MITTEL)

**Datei:** `useEntitiesView.ts:344`
```typescript
let parentSearchTimeout: ReturnType<typeof setTimeout> | null = null
```
Timeout wird nicht in `onUnmounted` gecleaned.

**Fix:**
```typescript
onUnmounted(() => {
  if (parentSearchTimeout) clearTimeout(parentSearchTimeout)
})
```

### 🟡 Dead Code (NIEDRIG)

**Datei:** `useEntitiesView.ts:591-593`
```typescript
function getTopFacetCounts(_entity: Entity): Array<...> {
    return []  // Immer leer - nicht implementiert
}
```

### 🟡 Code-Duplikation (NIEDRIG)

**Datei:** `entities.py`
- `get_entity` (773-839) und `get_entity_by_slug` (841-920) haben ~80% identischen Code
- Empfehlung: Helper-Funktion `_build_entity_response(entity, session)` extrahieren

### 🟡 Composable-Größe (NIEDRIG)

**Datei:** `useEntitiesView.ts` - 704 Zeilen
- Könnte aufgeteilt werden in:
  - `useEntitiesFilters`
  - `useEntitiesDialogs`
  - `useEntitiesPagination`

### 🟡 Props-Explosion (NIEDRIG)

**Datei:** `EntityDialogsManager.vue`
- 50+ Props - schwer zu warten
- Empfehlung: Props-Objekte gruppieren oder Provide/Inject nutzen

### 🟡 Kommentar-Inkonsistenz (TRIVIAL)

**Datei:** `entity_matching_service.py`
- Zeile 287: `# 7. Check for composite...`
- Zeile 305: `# 7. Create new entity...`
- Nummerierung ist doppelt (Copy-Paste-Fehler)

---

## Best Practices Umgesetzt

| Practice | Status |
|----------|--------|
| TypeScript Strict Mode | ✅ |
| ESLint/Prettier | ✅ |
| Structured Logging (structlog) | ✅ |
| Feature Flags | ✅ |
| Debounced Search | ✅ |
| Pagination | ✅ |
| Error Boundaries | ⚠️ Teilweise |
| Unit Tests | ✅ Vorhanden |
| API Response Types | ⚠️ Teilweise |

---

## Durchgeführte Fixes (27.12.2025)

| # | Issue | Status | Datei |
|---|-------|--------|-------|
| 1 | SQL-Injection | ✅ Gefixt | `entities.py:142-148, 692-695` |
| 2 | SQL-Injection | ✅ Gefixt | `entity_matching_service.py:587-591` |
| 3 | Memory Leak | ✅ Gefixt | `useEntitiesView.ts:367-373` |
| 4 | Dead Code | ✅ Entfernt | `useEntitiesView.ts` (getTopFacetCounts) |
| 5 | Code-Duplikation | ✅ Refactored | `entities.py:777-842` (_build_entity_response) |
| 6 | Kommentar-Fehler | ✅ Gefixt | `entity_matching_service.py:305` |

### Details der Fixes

**SQL-Injection Prevention:**
```python
# Vorher (UNSICHER):
Entity.name.ilike(f"%{search}%")

# Nachher (SICHER):
search_pattern = f"%{search.replace('%', '\\%').replace('_', '\\_')}%"
Entity.name.ilike(search_pattern, escape='\\')
```

**Memory Leak Fix:**
```typescript
onUnmounted(() => {
  if (parentSearchTimeout) {
    clearTimeout(parentSearchTimeout)
    parentSearchTimeout = null
  }
})
```

**Code-Duplikation:**
- Neue Helper-Funktion `_build_entity_response()` 
- Reduziert ~70 Zeilen doppelten Code

---

## Verbleibende Empfehlungen (optional)

1. **🟢 Composable aufteilen** - `useEntitiesView.ts` könnte in kleinere Composables aufgeteilt werden
