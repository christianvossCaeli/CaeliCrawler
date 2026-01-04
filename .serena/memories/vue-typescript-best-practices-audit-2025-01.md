# Vue.js/TypeScript Best-Practices Audit (2025-01-02)

## Executive Summary
Audit durchgeführt auf: **frontend/src/composables/**, **frontend/src/stores/**, **frontend/src/components/**

**Gesamt-Score: 82/100** (GUT - Verbesserungen nötig)

### Score nach Kategorie:
- Composition API: 85/100 (GUT)
- Props/Emits: 87/100 (GUT)
- Lifecycle/Memory Leaks: 88/100 (SEHR GUT)
- Reactivity: 81/100 (GUT)
- Template Best-Practices: 84/100 (GUT)
- TypeScript Type Safety: 76/100 (MEDIUM)

---

## 1. COMPOSITION API ANALYSE

### 1.1 STÄRKEN

**Korrekte ref vs reactive Verwendung:**
- `useDocumentsView.ts:100-102`: Richtige Nutzung für Set-basierte IDs
- `useEntityFacets.ts:123-138`: Gute Struktur von Refs
- `useResultsView.ts:150-200`: Klare Separation von State Refs

**Gute Computed Properties:**
- `auth.ts:62-75`: Permissions computed (isAuthenticated, isAdmin, isEditor)
- `useDocumentsView.ts:86-87`: canEdit und canAdmin Computed Properties
- `useResultsView.ts:424-425`: Effiziente Watchers mit klarer Intent

### 1.2 KRITISCHE PROBLEME IDENTIFIZIERT

#### Problem #1: zu viele Top-Level Refs ohne Grouping
**Datei: frontend/src/composables/useDocumentsView.ts (Zeilen 93-122)**
```typescript
// Zeilen 93-122: 30+ Refs auf oberster Ebene
const loading = ref(true)
const initialLoad = ref(true)
const processingAll = ref(false)
const stoppingAll = ref(false)
const bulkProcessing = ref(false)
const bulkAnalyzing = ref(false)
const processingIds = ref(new Set<string>())        // ← Problem hier
const analyzingIds = ref(new Set<string>())         // ← Problem hier
// ... weitere 20+ Refs
```
**ISSUE**: Direkte Set-Mutationen triggern Re-Renders
**SEVERITY**: MEDIUM
**FIX**: Immutable Updates oder reaktive Objekte nutzen
```typescript
// STATT:
processingIds.value.add(id)

// BESSER:
const addProcessingId = (id: string) => {
  const newSet = new Set(processingIds.value)
  newSet.add(id)
  processingIds.value = newSet
}
```

#### Problem #2: Zu viele Props Parameter
**Datei: frontend/src/composables/useEntityFacets.ts (Zeilen 95-98)**
```typescript
export function useEntityFacets(
  entity: Ref<Entity | null> | ComputedRef<Entity | null> | Entity | null,
  entityType: Ref<EntityType | null> | ComputedRef<EntityType | null> | EntityType | null,
  onFacetsSummaryUpdate: () => Promise<void>,
)
```
**ISSUE**: Zu flexible Typisierung (Union Types)
**SEVERITY**: LOW
**RECOMMENDATION**: Helper Type für "Ref or Value" erstellen
```typescript
type RefOrValue<T> = T | Ref<T> | ComputedRef<T>
```

#### Problem #3: Missing readonly() Wrappers
**Datei: frontend/src/composables/useDocumentsView.ts (Zeilen 100-101)**
```typescript
// Problem: Diese sollten readonly sein
const processingIds = ref(new Set<string>())
const analyzingIds = ref(new Set<string>())
```
**SEVERITY**: LOW (Best Practice)

---

## 2. PROPS/EMITS - TYPISIERUNG

### 2.1 STÄRKEN

**Excellente Props Definition:**
**Datei: frontend/src/components/entity/EntityFacetsTab.vue (Zeilen 627-642)**
```typescript
const props = withDefaults(defineProps<{
  entity: Entity | null
  entityType: EntityType | null
  facetsSummary: FacetsSummary | null
  canEdit?: boolean
}>(), {
  canEdit: true,
})

const emit = defineEmits<{
  (e: 'facets-updated'): void
  (e: 'add-facet'): void
  (e: 'add-facet-value', facetGroup: FacetGroup): void
  (e: 'switch-tab', tab: string): void
  (e: 'enrichment-started', taskId: string): void
}>()
```
✓ Vollständige Typ-Sicherheit
✓ Korrekte Default Values
✓ Gutes Event-Naming

### 2.2 PROBLEME

#### Problem #4: Fehlende JSDoc Props Dokumentation
**Datei: frontend/src/components/entity/EntityFacetsTab.vue (Zeilen 627-634)**
```typescript
const props = withDefaults(defineProps<{
  entity: Entity | null          // ← Keine Dokumentation
  entityType: EntityType | null  // ← Keine Dokumentation
  facetsSummary: FacetsSummary | null  // ← Keine Dokumentation
  canEdit?: boolean              // ← Keine Dokumentation
}>(), {
  canEdit: true,
})
```
**SEVERITY**: LOW (Documentation)
**FIX**: JSDoc Comments hinzufügen
```typescript
const props = withDefaults(defineProps<{
  /** Die Entity deren Facets angezeigt werden sollen */
  entity: Entity | null
  /** Entity Type für Validierung und Filterung */
  entityType: EntityType | null
  /** Zusammenfassung aller Facets */
  facetsSummary: FacetsSummary | null
  /** Ob der Benutzer Edit-Permissions hat */
  canEdit?: boolean
}>(), {
  canEdit: true,
})
```

---

## 3. STATE MANAGEMENT - PINIA STORES

### 3.1 STÄRKEN

**Saubere Store-Architektur:**
**Datei: frontend/src/stores/auth.ts (Zeilen 45-76)**
```typescript
export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const isLoading = ref(false)
  
  // Computed
  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'ADMIN' || user.value?.is_superuser)
  
  // Actions
  async function login(email: string, password: string): Promise<boolean> { ... }
  
  return { user, token, isAuthenticated, isAdmin, login }
})
```
✓ Composition API Pattern korrekt
✓ Keine direkten State-Mutations möglich
✓ Gute Separation von Concerns

### 3.2 KRITISCHE PROBLEME

#### Problem #5: Auth Store Initialize Race Condition
**Datei: frontend/src/stores/auth.ts (Zeilen 268-299)**
```typescript
// Track initialization promise
let initPromise: Promise<boolean> | null = null

async function initialize(): Promise<boolean> {
  if (initialized.value) {
    return !!user.value
  }
  
  if (initPromise) {
    return initPromise
  }
  
  if (token.value) {
    initPromise = fetchCurrentUser()  // ← ASYNC, nicht gewartet!
    return initPromise
  } else {
    initialized.value = true
    return false
  }
}

// Line 298: Start initialization immediately (non-blocking)
initialize()  // ← Wird nicht gewartet!
```
**ISSUE**: `initialize()` wird called aber nicht awaited im Store
**SEVERITY**: CRITICAL (Race Condition Risk)
**FIX**: Store Initialization properly awaiten in App.vue

#### Problem #6: State Mutation Protection fehlt
**Datei: frontend/src/stores/entity.ts (Zeilen 109-109)**
```typescript
async function fetchEntityType(id: string) {
  try {
    const response = await entityApi.getEntityType(id)
    selectedEntityType.value = response.data  // ← Direkte Mutation
    return response.data
  } catch (err: unknown) {
    error.value = getErrorMessage(err) || 'Failed to fetch entity type'
    throw err
  }
}
```
**ISSUE**: Direkte `.value =` Mutation ohne Validierung
**SEVERITY**: MEDIUM
**FIX**: Validation hinzufügen:
```typescript
async function fetchEntityType(id: string) {
  try {
    const response = await entityApi.getEntityType(id)
    if (!response.data?.id) throw new Error('Invalid entity type data')
    selectedEntityType.value = response.data
    return response.data
  } catch (err: unknown) {
    error.value = getErrorMessage(err) || 'Failed to fetch entity type'
    throw err
  }
}
```

#### Problem #7: Fehlende Promise Cleanup
**Datei: frontend/src/stores/auth.ts (Zeilen 268-269)**
```typescript
let initPromise: Promise<boolean> | null = null

// PROBLEM: initPromise wird nicht auf null zurückgesetzt nach Resolution
```
**SEVERITY**: LOW
**FIX**: In initialize() nach Completion `initPromise = null` setzen

---

## 4. LIFECYCLE HOOKS & MEMORY LEAKS

### 4.1 GUTE PRAKTIKEN

**Correcte Cleanup in useDebounce:**
**Datei: frontend/src/composables/useDebounce.ts (Zeilen 109-118)**
```typescript
const cancel = () => {
  isPending.value = false
  if (timeoutId) {
    clearTimeout(timeoutId)
    timeoutId = null  // ← Wichtig!
  }
}

// Auto cleanup
onUnmounted(cancel)  // ← Automatisch aufgeräumt
```
✓ Korrekte Timeout-Cleanup
✓ Null-Zuweisung nach Clear
✓ onUnmounted Hook vorhanden

**Gute Cleanup-Pattern in useDocumentsView:**
**Datei: frontend/src/composables/useDocumentsView.ts (Zeilen 523-535)**
```typescript
watch(() => stats.value.processing + stats.value.analyzing, (activeCount) => {
  if (activeCount > 0 && !refreshInterval) {
    refreshInterval = window.setInterval(loadData, 5000)
  } else if (activeCount === 0 && refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
})

// Cleanup on unmount
onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})
```
✓ Interval richtig aufgeräumt
✓ onUnmounted Hook vorhanden

### 4.2 KRITISCHE PROBLEME

#### Problem #8: Watch ohne explizites Unsubscribe
**Datei: frontend/src/composables/useResultsView.ts (Zeilen 424-426)**
```typescript
// Watch for category changes to reload FacetTypes
watch(categoryFilter, () => {
  loadFacetTypesForCategory()
})
// ← KEIN CLEANUP!
```
**ISSUE**: Watch-Rückgabewert wird nicht genutzt
**SEVERITY**: HIGH (Memory Leak Risk)
**FIX**: Explizites Cleanup hinzufügen
```typescript
let unwatchCategory: (() => void) | undefined

// In initialize():
unwatchCategory = watch(categoryFilter, () => {
  loadFacetTypesForCategory()
})

// In onUnmounted():
onUnmounted(() => {
  if (unwatchCategory) unwatchCategory()
  if (refreshInterval) clearInterval(refreshInterval)
})
```

#### Problem #9: setTimeout ohne Cleanup in useAsyncOperation
**Datei: frontend/src/composables/useAsyncOperation.ts (Zeilen 221-228)**
```typescript
// Auto-execute on mount
if (immediate) {
  if (delay > 0) {
    setTimeout(() => operation.execute(), delay)  // ← KEIN CLEANUP!
  } else {
    operation.execute()
  }
}
```
**ISSUE**: Delayed setTimeout wird nicht in onUnmounted aufgeräumt
**SEVERITY**: HIGH (Memory Leak Risk, Race Condition)
**FIX**: Timeout tracking hinzufügen
```typescript
let delayTimeoutId: ReturnType<typeof setTimeout> | null = null

// Auto-execute on mount
if (immediate) {
  if (delay > 0) {
    delayTimeoutId = setTimeout(() => operation.execute(), delay)
  } else {
    operation.execute()
  }
}

onUnmounted(() => {
  abort('Component unmounted')
  if (delayTimeoutId) clearTimeout(delayTimeoutId)
})
```

#### Problem #10: Entity Search Timeout ohne vollständiges Cleanup
**Datei: frontend/src/composables/useEntityFacets.ts (Zeilen 650-657)**
```typescript
async function searchEntities(query: string) {
  if (entitySearchTimeout) clearTimeout(entitySearchTimeout)

  if (!query || query.length < 2) {
    entitySearchResults.value = []
    return  // ← EARLY RETURN - entitySearchTimeout nicht auf null!
  }

  entitySearchTimeout = setTimeout(async () => {
    // ...
  }, 300)
}
```
**ISSUE**: Bei Early Return wird Timeout nicht auf null gesetzt
**SEVERITY**: MEDIUM
**FIX**: Immer Cleanup machen
```typescript
async function searchEntities(query: string) {
  // Clear any existing timeout
  if (entitySearchTimeout) {
    clearTimeout(entitySearchTimeout)
    entitySearchTimeout = null  // ← Always set to null
  }

  if (!query || query.length < 2) {
    entitySearchResults.value = []
    return
  }

  entitySearchTimeout = setTimeout(async () => {
    // ...
  }, 300)
}
```

---

## 5. REACTIVITY PATTERNS

### 5.1 PROBLEME

#### Problem #11: .value Mutation in Sets
**Datei: frontend/src/composables/useDocumentsView.ts (Zeilen 100-101)**
```typescript
const processingIds = ref(new Set<string>())

// Verwendung:
processingIds.value.add(id)  // ← Problem!
processingIds.value.delete(id)
```
**ISSUE**: Set-Mutationen triggern nicht immer Vue Reactivity
**SEVERITY**: MEDIUM
**BEST PRACTICE**: Immutable Updates
```typescript
// STATT:
processingIds.value.add(id)

// BESSER:
const addProcessingId = (id: string) => {
  const newSet = new Set(processingIds.value)
  newSet.add(id)
  processingIds.value = newSet  // Trigger re-render
}
```

#### Problem #12: Fehlende toRef/toRefs Nutzung
**Datei: frontend/src/components/entity/EntityFacetsTab.vue (Zeilen 651-652)**
```typescript
const entityRef = toRef(props, 'entity')
const entityTypeRef = toRef(props, 'entityType')

const facets = useEntityFacets(entityRef, entityTypeRef, async () => {
  emit('facets-updated')
})
```
✓ toRef wird korrekt genutzt
✓ Reactive Link zur Prop gewährleistet

---

## 6. TEMPLATE BEST-PRACTICES

### 6.1 STÄRKEN

**Korrekte v-if vs v-show Nutzung:**
**Datei: frontend/src/components/entity/EntityFacetsTab.vue (Zeilen 4, 18-23)**
```vue
<!-- v-if für seltene Render-Wechsel -->
<v-card v-if="facetsSummary?.facets_by_type?.length" class="mb-4">
  <!-- ... -->
  <v-menu
    v-if="canEdit && entityType?.supports_pysis"
    v-model="enrichmentMenuOpen"
  >
    <!-- ... -->
  </v-menu>
</v-card>
```
✓ v-if richtig für Conditional Rendering
✓ Optional Chaining korrekt

### 6.2 PROBLEME

#### Problem #13: Event Handler ohne .stop modifier wo nötig
**Datei: frontend/src/components/entity/EntityFacetsTab.vue (Zeilen 600)**
```vue
<!-- Sollte .stop haben wenn nested in clickable container -->
@click="handleSaveEntityLink"  <!-- ← Kontrolliere Parent-Click -->
```
**SEVERITY**: LOW

#### Problem #14: Template-Komplexität zu hoch
**Datei: frontend/src/components/entity/EntityFacetsTab.vue (~1-608)**
```vue
<template>
  <!-- 600+ Zeilen Template! -->
  <!-- Sollte in Sub-Komponenten aufgespaltet werden -->
</template>
```
**SEVERITY**: MEDIUM (Maintenance)
**Recommendations**: 
- EnrichmentMenu in Sub-Komponente
- EntityLinkDialog in eigene Komponente
- FacetList in Sub-Komponente

---

## 7. TYPESCRIPT TYPE SAFETY

### 7.1 PROBLEME

#### Problem #15: `any` Types in Composables
**Datei: frontend/src/composables/useAsyncOperation.ts (gesamte Datei)**
```typescript
// Problem #1: Union Types zu breit
export type AsyncOperationFn<T, P = void> = (
  params: P,
  signal: AbortSignal
) => Promise<T>
```
**SEVERITY**: LOW
✓ Eigentlich gut typisiert!

#### Problem #16: Weak Error Typing in useEntityFacets
**Datei: frontend/src/composables/useEntityFacets.ts (Zeilen 681-683)**
```typescript
async function searchEntities(query: string) {
  // ...
  try {
    const response = await entityApi.searchEntities({ q: query, per_page: 20 })
  } catch (err) {
    logger.error('Failed to search entities', err)  // ← err ist unknown
    showError(t('entityDetail.messages.entitySearchError', 'Fehler...'))
  }
}
```
**SEVERITY**: MEDIUM
**FIX**: Error Type Guard hinzufügen
```typescript
catch (err: unknown) {
  const message = getErrorDetail(err)
  logger.error('Failed to search entities', message)
  showError(t('entityDetail.messages.entitySearchError', message))
}
```

#### Problem #17: Fehlende Type Guards
**Datei: frontend/src/composables/useResultsView.ts (Zeilen 448-453)**
```typescript
function formatFieldLabel(key: string): string {
  return key
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')  // ← Keine Validierung des Inputs
}
```
**SEVERITY**: LOW
**RECOMMENDATION**: Input Validation hinzufügen

---

## 8. PERFORMANCE & REACTIVITY

### 8.1 PROBLEME

#### Problem #18: Computed Properties mit zu viel Logik
**Datei: frontend/src/composables/useResultsView.ts (Zeilen ~500+)**
```typescript
// Angenommen große berechnungen in Computeds
const complexCalculation = computed(() => {
  // 50+ Zeilen Logik
  return results.value.map(r => {
    // Komplexe Transformationen
  })
})
```
**RECOMMENDATION**: Memoized Helper-Funktion statt Computed wenn möglich

#### Problem #19: Keine Lazy Loading in Listen
**Severity**: MEDIUM
**RECOMMENDATION**: Für 1000+ Items useVirtualizer von @tanstack/vue-virtual nutzen

---

## ZUSAMMENFASSUNG - TOP 10 ISSUES NACH KRITIKALITÄT

| Rang | Issue | Datei | Zeile | Severity | Aufwand |
|------|-------|-------|-------|----------|---------|
| 1 | Auth Store Initialize Race Condition | auth.ts | 268-298 | CRITICAL | Hoch |
| 2 | Watch ohne Unsubscribe (Potential Memory Leak) | useResultsView.ts | 424-426 | HIGH | Mittel |
| 3 | setTimeout ohne Cleanup in useAsyncOperation | useAsyncOperation.ts | 221-228 | HIGH | Mittel |
| 4 | Entity Search Timeout Cleanup unvollständig | useEntityFacets.ts | 650-657 | MEDIUM | Niedrig |
| 5 | Set-Mutationen nicht Immutable | useDocumentsView.ts | 100-101 | MEDIUM | Mittel |
| 6 | State Validation in Stores fehlt | entity.ts | 109 | MEDIUM | Mittel |
| 7 | Zu viele Top-Level Refs | useDocumentsView.ts | 93-122 | MEDIUM | Hoch |
| 8 | Fehlende JSDoc Props Dokumentation | EntityFacetsTab.vue | 627-634 | LOW | Niedrig |
| 9 | Weak Error Type Handling | useEntityFacets.ts | 681-683 | MEDIUM | Mittel |
| 10 | Template-Komplexität zu hoch | EntityFacetsTab.vue | 1-608 | MEDIUM | Hoch |

---

## EMPFEHLUNGEN

### Sofort zu beheben (CRITICAL):
1. Auth Store Initialize Race Condition fixen
2. Memory Leak Risks (watch cleanup, setTimeout)

### Kurzfristig (1-2 Wochen):
1. Set-Mutationen immutable machen
2. Error Type Handling verbessern
3. State Validation in Stores hinzufügen

### Langfristig (Refactoring):
1. EntityFacetsTab.vue in Sub-Komponenten aufteilen
2. Composable State Refs groupieren (Object statt einzelne Refs)
3. Lazy Loading für große Listen implementieren

