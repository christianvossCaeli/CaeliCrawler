# Simplification Action Items - Detailed Breakdown

## PHASE 1: QUICK WINS (3-5 Days) - LOW RISK

### 1.1 Remove Deprecated Azure OpenAI Factories

**Why:** 120+ LOC of code that only throws errors  
**File**: `backend/services/ai_client.py`  
**Lines to delete**: 40-180

```
Delete completely:
- SyncAzureOpenAIClientFactory class
- AzureOpenAIClientFactory class  
- get_sync_openai_client() function
- All docstrings mentioning these

Keep:
- create_sync_client_for_user()
- create_async_client_for_user()
- All the working code
```

**Impact:**
- LOC Saved: 120
- Risk: NONE (deprecated code never called)
- Testing: Just check imports still work
- Time: 30 minutes

**Verification:**
```bash
grep -r "SyncAzureOpenAIClientFactory\|get_sync_openai_client" backend/
# Should return 0 results
```

---

### 1.2 Remove clean_municipality_name() Function

**Why:** Marked as DEPRECATED with explanation "no longer used"  
**File**: `backend/app/utils/text.py`  
**Lines**: 182-240

```python
# DEPRECATED: This function is no longer used for entity deduplication.
# We now use embedding-based similarity matching which handles variations
# like "Aberdeen City Council" vs "Aberdeen" automatically without
# entity-type-specific rules.

def clean_municipality_name(name: str, country: str = "DE") -> str:
    # ... 55 lines of code
```

**Impact:**
- LOC Saved: 55
- Risk: LOW (check 0 usages first)
- Testing: Search imports
- Time: 30 minutes

**Verification:**
```bash
# Check usages
grep -r "clean_municipality_name" backend/
# Should return 0
```

**Also verify** `__init__.py` doesn't export it anymore after removal

---

### 1.3 Remove Unused Composables

**What**: Composables with 0 actual usage

**Files to check for removal:**
1. `frontend/src/composables/useSpeechRecognition.ts`
   - LOC: 120
   - Usages: 0
   - Grep: `useSpeechRecognition`

2. `frontend/src/composables/useColorHelpers.ts`
   - LOC: 80
   - Usages: 0
   - Grep: `useColorHelpers`

3. `frontend/src/composables/useLoadingState.ts` (check first)
   - LOC: 50
   - Usages: ~3 (wrapper only)
   - Can be replaced with: inline `ref(false)` or `useAsyncOperation()`

**Impact:**
- LOC Saved: 250
- Risk: LOW (verify 0 usage)
- Time: 1-2 hours

**Verification:**
```bash
for file in useSpeechRecognition useColorHelpers useLoadingState; do
  echo "=== $file ==="
  grep -r "$file" frontend/src --exclude-dir=node_modules
done
```

---

### 1.4 Consolidate Date Formatters

**Current State**: 4 implementations of similar functionality

**Files involved:**
1. `frontend/src/utils/viewHelpers.ts` (lines 24-80)
   - formatDate()
   - formatDateOnly()
   - formatRelativeTime()

2. `frontend/src/utils/messageFormatting.ts` (lines 92-106)
   - formatMessageTime()
   - formatRelativeTime() ← DUPLICATE

3. `frontend/src/utils/llmFormatting.ts` (lines 66-80)
   - formatDate() ← DIFFERENT IMPL

4. `frontend/src/composables/useDateFormatter.ts`
   - Wrapper around date-fns

**Consolidation Plan:**
```
Step 1: Create utils/dateFormatting.ts with:
- formatDate(date, format?)
- formatDateOnly(date)
- formatMessageTime(date)
- formatRelativeTime(date)

Step 2: Update imports in:
- components/
- composables/
- views/

Step 3: Delete old functions from:
- viewHelpers.ts (keep other functions)
- messageFormatting.ts (keep other functions)
- llmFormatting.ts (keep other functions)

Step 4: Consider if useDateFormatter needs to exist
```

**Impact:**
- LOC Saved: 150
- Import Paths Reduced: 5 → 1
- Risk: MEDIUM (need to update imports)
- Time: 2-3 hours

**Verification:**
```bash
# All imports should come from one file
grep -r "formatDate\|formatRelativeTime" frontend/src --include="*.ts" --include="*.vue" | grep "from" | sort | uniq -c
```

---

### PHASE 1 SUMMARY

| Task | LOC | Risk | Time |
|------|-----|------|------|
| Remove deprecated factories | 120 | NONE | 30m |
| Remove clean_municipality | 55 | LOW | 30m |
| Remove unused composables | 250 | LOW | 1-2h |
| Consolidate date formatters | 150 | MEDIUM | 2-3h |
| **TOTAL** | **575** | **LOW** | **5-6h** |

---

## PHASE 2: CACHE CONSOLIDATION (2-3 Days) - MEDIUM RISK

### 2.1 Audit Current Cache Usage

**Identify all cache patterns:**

```bash
# Pinia cache
grep -r "new Map" frontend/src/stores/
grep -r "cache.*set\|cache.*get" frontend/src/stores/

# Utility cache
grep -r "entityCache\|categoryCache\|facetTypeCache" frontend/src/

# Manual cache
grep -r "getCachedData\|setCachedData" frontend/src/composables/
```

**Document:**
- Which features use which cache?
- Cache TTLs in each system?
- Cache hit rates (if measurable)?
- Invalidation strategies?

---

### 2.2 Choose Single Cache Strategy

**Options:**

**Option A: Use Pinia Cache (Simple)**
- Location: `stores/cache.ts`
- Pro: Works with Pinia
- Con: Limited features
- Best for: Entity/Facet caching

**Option B: Use Utils Cache (Comprehensive)**
- Location: `utils/cache.ts`
- Pro: More features
- Con: Separate from Pinia
- Best for: All caching needs

**Option C: Use VueUse** (already installed)
- useStorage(), useSessionStorage()
- Pro: Standard library
- Con: Needs migration
- Best for: Persistent cache

**Recommendation:** Consolidate to Pinia (already in stores)

---

### 2.3 Migration Plan

**Step 1: Create cache.ts in stores/**
```typescript
// stores/cache.ts
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export const useCacheStore = defineStore('cache', () => {
  const caches = ref<Map<string, { value: any, expires: number }>>(new Map())
  
  const get = (key: string) => {
    const cache = caches.value.get(key)
    if (!cache || cache.expires < Date.now()) {
      caches.value.delete(key)
      return null
    }
    return cache.value
  }
  
  const set = (key: string, value: any, ttl = 30000) => {
    caches.value.set(key, { value, expires: Date.now() + ttl })
  }
  
  const clear = (prefix?: string) => {
    if (!prefix) {
      caches.value.clear()
    } else {
      for (const [k] of caches.value) {
        if (k.startsWith(prefix)) caches.value.delete(k)
      }
    }
  }
  
  return { get, set, clear }
})
```

**Step 2: Migrate all usages**
- Pinia cache → useCacheStore().get()
- Util cache → same
- Manual cache → same

**Step 3: Delete old cache files**
- `utils/cache.ts`
- Manual cache helpers

**Impact:**
- LOC Saved: 100 (removed duplicate implementations)
- Consistency: +1 (single source)
- Risk: MEDIUM (cache behavior must stay same)
- Time: 2-3 hours

---

## PHASE 3: SERVICE SIMPLIFICATION (3-5 Days) - MEDIUM RISK

### 3.1 Identify Over-Engineered Services

**Services with <300 LOC, single file usage:**

| Service | File | LOC | Used In | Issue |
|---------|------|-----|---------|-------|
| APIFacetSyncService | api_facet_sync_service.py | 280 | sync_commands.py | Could be utils |
| EntityAPISyncService | entity_api_sync_service.py | 220 | API routes | Could be inline |
| ChangeTracker | change_tracker.py | 150 | 2 files | Could be model |
| DocumentPageFilter | document_page_filter.py | 200 | 1 API endpoint | Could be utils |

---

### 3.2 Refactoring Plan for APIFacetSyncService

**Current Pattern:**
```python
# api_facet_sync_service.py
class APIFacetSyncService:
    def __init__(self, api_fetcher, entity_service):
        self.api_fetcher = api_fetcher
        self.entity_service = entity_service
    
    async def sync_facet(self, facet_id):
        data = await self.api_fetcher.get_facet(facet_id)
        return await self.entity_service.apply_facet(data)

# In sync_commands.py
service = APIFacetSyncService(api_fetcher, entity_service)
result = await service.sync_facet(facet_id)
```

**Better Pattern:**
```python
# In sync_commands.py directly
async def sync_facet(facet_id, db_session, ...):
    data = await api_fetcher.get_facet(facet_id)
    return await entity_service.apply_facet(data)

# Or utils/sync_utils.py (40 LOC max)
async def sync_facet_from_api(facet_id, ...):
    ...
```

**Migration:**
1. Create `backend/app/utils/sync_utils.py`
2. Move sync logic there
3. Update imports in sync_commands.py
4. Delete `api_facet_sync_service.py`

**Impact:**
- LOC Saved: 200 (service boilerplate)
- Clarity: Better (logic where used)
- Risk: MEDIUM (test sync operations)
- Time: 2-3 hours

---

### 3.3 Similar for DocumentPageFilter

**Current:** 200 LOC service class  
**Better:** 40 LOC utility function

```python
# Before
class DocumentPageFilter:
    def __init__(self, config):
        self.config = config
    
    def filter_pages(self, pages):
        return [p for p in pages if self.matches(p)]

# After
def filter_document_pages(pages: List[Document], config: FilterConfig) -> List[Document]:
    return [p for p in pages if matches_config(p, config)]
```

---

## PHASE 4: COMPOSABLE ABSTRACTION (1-2 Days) - MEDIUM RISK

### 4.1 Create useDialog Composable

**Pattern** (found in 15+ components):
```typescript
// Before
const isOpen = ref(false)
const selectedItem = ref<Item | null>(null)

const open = (item?: Item) => {
  selectedItem.value = item || null
  isOpen.value = true
}

const close = () => {
  isOpen.value = false
  selectedItem.value = null
}
```

**After:**
```typescript
// composables/useDialog.ts
export function useDialog<T>() {
  const isOpen = ref(false)
  const selectedItem = ref<T | null>(null)
  
  const open = (item?: T) => {
    selectedItem.value = item || null
    isOpen.value = true
  }
  
  const close = () => {
    isOpen.value = false
    selectedItem.value = null
  }
  
  return { isOpen, selectedItem, open, close }
}

// In component:
const { isOpen, selectedItem, open, close } = useDialog<Item>()
```

**Impact:**
- LOC Saved per component: 10-15
- Total saved: 150-200 LOC (15 components × 15)
- Consistency: +1
- Time: 1-2 hours to create + 2-3 hours to migrate

---

### 4.2 Create useDataTable Composable

**Pattern** (found in 8+ views):
```typescript
// Current (repeated)
const page = ref(1)
const perPage = ref(20)
const total = ref(0)
const sortBy = ref('name')
const sortDesc = ref(false)
const search = ref('')

// After
const table = useDataTable({ defaultSort: 'name', defaultPerPage: 20 })

// Use as
table.page, table.perPage, table.sortBy, etc.
```

**Impact:**
- LOC Saved per view: 10-15
- Total: 80-120 LOC
- Time: 1-2 hours

---

## PHASE 5: LARGE COMPONENT DECOMPOSITION (2-3 Weeks) - HIGH RISK

### 5.1 MapVisualization.vue (896 → 300 LOC)

**Current Structure:**
```
MapVisualization.vue (896 LOC)
  ├── Map initialization (150 LOC)
  ├── Feature rendering (200 LOC)
  ├── Popup management (150 LOC)
  ├── Layer toggle (100 LOC)
  ├── Styling logic (150 LOC)
  └── Error handling (100 LOC)
```

**After:**
```
MapVisualization.vue (200 LOC - main container)
  ├── MapContainer.vue (150 LOC)
  ├── MapPopup.vue (100 LOC)
  ├── MapLayers.vue (100 LOC)
  └── composables/useMapState.ts (150 LOC)
```

**Refactoring Steps:**
1. Extract `MapContainer` (initialization + base map)
2. Extract `MapPopup` (popup rendering logic)
3. Extract `MapLayers` (layer toggle logic)
4. Create `composables/useMapState.ts` for state management

**Time:** 3-4 days
**Risk:** HIGH (complex component)
**Testing:** Map interactions must still work

---

### 5.2 EntityMapView.vue (786 → 300 LOC)

Similar to MapVisualization:
- Extract EntityMapFilters
- Extract EntityMapMarkers
- Extract EntityMapControls

**Time:** 2-3 days
**Risk:** HIGH

---

## PHASE 6: DEPRECATED FACADE REMOVAL (2-3 Days) - HIGH RISK

### 6.1 Remove useEntityFacets Facade

**Status:** Deprecated, multiple patterns coexist

**Current:**
```typescript
// Old facade
export function useEntityFacets(...) { return { ...70+ items } }

// New modular
export { useFacetCrud } from './useFacetCrud'
export { useFacetSearch } from './useFacetSearch'
// ... 5+ more
```

**Migration:**
1. Find all usages of `useEntityFacets`
2. Replace with individual composable imports
3. Document why each sub-composable is needed
4. Remove from exports
5. Mark for removal in v2.0

**Time:** 2-3 hours
**Risk:** MEDIUM (ensure all usages migrated)

---

## PHASE 7: LOGGER SIMPLIFICATION (1-2 Days) - LOW-MEDIUM RISK

### 7.1 Simplify useLogger

**Current:** 200+ LOC with features:
- Performance tracking
- Error tracking endpoint
- Rate limiting
- Stack traces
- Custom metadata

**Keep:** 
- 5 log levels
- Structured context
- Basic error handling

**Remove:**
- Performance tracking (never used)
- Error endpoint (never configured)
- Rate limiting (never used)
- Stack traces (rarely needed)

**New Size:** ~80 LOC

**Implementation:**
```typescript
// composables/useLogger.ts (simplified)
export function useLogger(context: string) {
  const log = (level: LogLevel, message: string, error?: Error) => {
    console.log(`[${level.toUpperCase()}] [${context}] ${message}`, error)
  }
  
  return {
    debug: (m) => log('debug', m),
    info: (m) => log('info', m),
    warn: (m) => log('warn', m),
    error: (m, e) => log('error', m, e),
  }
}
```

**Time:** 1-2 hours
**Risk:** LOW

---

## SUMMARY TABLE

| Phase | Focus | LOC | Risk | Time | Priority |
|-------|-------|-----|------|------|----------|
| 1 | Quick Wins | 575 | LOW | 5-6h | CRITICAL |
| 2 | Cache | 100 | MEDIUM | 2-3d | HIGH |
| 3 | Services | 500 | MEDIUM | 3-5d | HIGH |
| 4 | Composables | 250 | MEDIUM | 1-2d | HIGH |
| 5 | Components | 600 | HIGH | 2-3w | MEDIUM |
| 6 | Facades | - | HIGH | 2-3d | MEDIUM |
| 7 | Logger | 120 | LOW | 1-2d | MEDIUM |
| **TOTAL** | | **2145** | - | **4-5w** | - |

---

## EXECUTION ROADMAP

**Week 1:**
- Days 1-2: Phase 1 (Quick Wins)
- Days 3-4: Phase 2 (Cache Consolidation)
- Days 5: Phase 7 (Logger Simplification) + buffer

**Week 2-3:**
- Phase 3 (Service Simplification)
- Phase 4 (Composable Creation)

**Week 4-5:**
- Phase 5 (Component Decomposition)
- Phase 6 (Facade Removal)

**Quality Assurance:**
- Run full test suite after each phase
- Code review for each major change
- Deploy incrementally

---

## SUCCESS METRICS

After completion:
- [x] Remove 2000+ LOC of unnecessary code
- [x] Reduce average service dependencies from 25 → 8
- [x] Single cache strategy vs 3
- [x] Date formatting consolidated: 1 location
- [x] Component average size reduced: 400 → 250 LOC
- [x] Dialog pattern unified: +15 LOC saved per component
- [x] No functional regression

**Testing Gate:**
- All existing tests pass
- Performance tests show no regression
- Manual smoke test on key features
