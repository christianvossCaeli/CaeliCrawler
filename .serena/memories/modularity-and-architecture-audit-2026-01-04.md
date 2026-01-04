# Frontend Modularity & Architecture Audit - 2026-01-04

## Executive Summary
The CaeliCrawler frontend has a reasonably well-organized structure with clear separation between services (API layer), stores (state management), and composables (reusable logic). However, there are several areas where modularity could be improved, particularly around component size, composable organization, and store responsibilities.

---

## 1. COMPONENT SIZE ANALYSIS

### Oversized Components (>500 lines)
**Critical Issues:**
- **MapVisualization.vue** (896 lines): Contains map initialization, feature rendering, popup management, and styling logic. Should split into:
  - MapContainer component
  - MapPopup component
  - MapLayers component
  
- **ChatWindow.vue** (830 lines): Combines chat UI, file upload, context management, and message handling. Suggests:
  - Extract ChatMessageList
  - Extract ChatInputArea
  - Extract FileUploadZone

- **EntityMapView.vue** (786 lines): Entity map display with filtering. Should extract:
  - EntityMapFilters
  - EntityMapMarkers
  - EntityMapControls

- **EntityAttachmentsTab.vue** (735 lines): Attachment management with upload and preview. Extract:
  - AttachmentList
  - AttachmentUploader
  - AttachmentPreview

- **ScheduleBuilder.vue** (680 lines): Cron schedule configuration. Complex domain logic should go to composable.

- **SmartQueryResults.vue** (642 lines): Results display with filtering. Extract:
  - ResultsTable
  - ResultsVisualization
  - ResultsFilters

**Medium Issues (600-650 lines):**
- NotificationRules.vue (611)
- CrawlPresetEditor.vue (600)
- SourceFormDialog.vue (585)
- Multiple admin views (FacetTypesView, AuditLogView, EntityTypesView)

### Recommendation
**Adopt Component Size Guidelines:**
- <300 lines: Single responsibility, reusable
- 300-500 lines: Acceptable for container components
- >500 lines: MUST split into smaller components

---

## 2. COMPOSABLES ORGANIZATION

### Strengths
✓ Good modular structure with domain-focused composables:
  - **Facets module**: Well-organized with separate files (useFacetCrud, useFacetSearch, useFacetBulkOps, useFacetEnrichment, useFacetEntityLinking, useFacetSourceDetails)
  - **Assistant module**: Modular design with sub-composables (useAssistantHistory, useAssistantBatch, useAssistantWizard, etc.)
  - **SmartQuery module**: Separated into core and SSE composables
  - **PlanMode module**: Properly split into core and SSE
  - **Results module**: Recently refactored into modular structure
  - **Categories module**: Separate composables for dialogs and AI setup

✓ Abstract utilities available (useAsyncOperation, useDebounce, etc.)

### Issues

**Problem 1: Large Monolithic Composables**
- **useCrawlerAdmin.ts** (792 lines): Handles too many responsibilities:
  - Job state management
  - AI task monitoring
  - SSE connection management
  - Bulk selection logic
  - Polling/refresh logic
  - File operations
  
  **Should split into:**
  - useCrawlerJobs (job state + operations)
  - useCrawlerSSE (real-time updates)
  - useCrawlerBulkActions (bulk selection)
  - useCrawlerAiTasks (AI task monitoring)

- **usePySisProcess.ts** (793 lines): Multiple concerns:
  - Template management
  - Field operations
  - Process synchronization
  - History management
  - UI state (dialogs, modals)
  
  **Should extract:**
  - usePySisFields (field-specific operations)
  - usePySisSync (sync logic)
  - usePySisHistory (history queries)

- **useEntitiesView.ts** (707 lines): View logic with:
  - Table state
  - Filtering
  - Pagination
  - Bulk operations
  - Dialog management

- **useDocumentsView.ts** (671 lines): Similar pattern to EntitiesView

- **useFacetTypesAdmin.ts** (632 lines): Should split into:
  - useFacetTypeList (CRUD)
  - useFacetTypeForm (form state)
  - useFacetTypeBulkOps (bulk operations)

**Problem 2: Inconsistent Composable Patterns**
- Some composables use ref() for all state, some mix ref() + reactive()
- No consistent error handling pattern
- Some have extensive local helper functions that could be extracted
- 472 state declarations (ref/computed) across composables - high state density

**Problem 3: Missing Abstractions**
- useAsyncOperation exists but not universally adopted
- Many composables manually handle loading/error states
- No consistent patterns for:
  - Polling/refresh logic (some use setInterval, some use setTimeout)
  - Dialog management (refs scattered across composables)
  - Filter state management
  - List pagination

### Code Statistics
- 82 relative imports between composables (potential circular dependency risk)
- Composables directory contains 68 files (many should be grouped into modules)
- Root-level composables: 40+ individual files should be categorized

---

## 3. STORE ORGANIZATION & PINIA

### Current Structure
**Store Breakdown:**
- auth.ts (332 lines) ✓ Focused
- entity.ts (400 lines) - Core store, reasonable size
- facet.ts (418 lines) ✓ Focused on facet state
- categories.ts (421 lines) ✓ Focused
- customSummaries.ts (964 lines) ✗ OVERSIZED
- sources.ts (792 lines) ✗ OVERSIZED
- notifications.ts (645 lines) ⚠ Large
- crawlPresets.ts (396 lines) ✓ Reasonable
- llmUsage.ts (370 lines) ✓ Reasonable
- facetTypes.ts (211 lines) ✓ Focused
- smartQueryHistory.ts (251 lines) ✓ Focused
- dashboard.ts (234 lines) ✓ Focused
- favorites.ts (214 lines) ✓ Focused
- relation.ts (implied) ✓ Focused
- analysis.ts (implied) ✓ Focused

### Issues

**Problem 1: Oversized Stores**
- **customSummaries.ts** (964 lines - WORST OFFENDER):
  - Summary CRUD operations
  - Widget management
  - Execution tracking
  - Sharing state
  - Export functionality
  - History management
  
  **Should split into:**
  - summaries.ts (create/read/update/delete)
  - summaryWidgets.ts (widget management)
  - summaryExecutions.ts (execution tracking)
  - summarySharing.ts (share state)

- **sources.ts** (792 lines):
  - Source CRUD
  - Category assignment
  - Tags management
  - AI discovery state
  - API import state
  - Bulk operations
  
  **Could split into:**
  - sourcesCore.ts (CRUD)
  - sourcesCategories.ts (category linking)
  - sourcesDiscovery.ts (AI discovery)
  - sourcesImport.ts (API import)

- **notifications.ts** (645 lines):
  - Notification list/detail
  - Rules management
  - Preferences
  - Device tokens
  - Email addresses
  
  **Could split into:**
  - notificationsInbox.ts (list/detail)
  - notificationRules.ts (rule management)
  - notificationSettings.ts (preferences)

**Problem 2: Tight Coupling to Composables**
Stores import composables for:
- useLogger (all stores) ✓ Acceptable utility
- useFileDownload (customSummaries) ✓ Acceptable
- useSnackbar (should not be in stores - UI concern)
- emitCrawlerEvent (stores emitting events) - Acceptable pattern

**Problem 3: No Clear Responsibility Boundaries**
- Entity store has 400 lines but handles core entity state only
- No clear distinction between state shape and computed selectors
- Some stores mix data fetching with state management

**Problem 4: Missing Store Decomposition**
- No feature-flag store despite useFeatureFlags composable
- No settings store for global preferences
- Notification logic scattered between store and composables

---

## 4. API LAYER SEPARATION

### Current Structure
**Strengths:**
✓ Clean separation in `/services/api/`:
- client.ts (HTTP client setup)
- admin.ts (crawler, users, audit, notifications)
- ai.ts (assistant, analysis, smart query)
- entities.ts (entity types, CRUD, enrichment)
- facets.ts (facet types, values, history)
- relations.ts (relation types, CRUD)
- sources.ts (sources, categories, AI discovery, documents)
- categories.ts (dedicated categories module)
- llm.ts (LLM config and usage)
- auth.ts (authentication)
- index.ts (unified export with namespaced APIs)

✓ No business logic in API layer
✓ Proper type imports from @/types
✓ Consistent error handling pattern

### Issues

**Problem 1: Fat API Index**
- index.ts is 527 lines
- Re-exports 40+ namespaced APIs (adminApi, entityApi, facetApi, etc.)
- Manually groups related functions
- Could benefit from organizing by feature

**Problem 2: Manual API Grouping**
- Entity-related APIs spread across entityApi, entityDataApi, favoritesApi, attachmentApi
- No automatic grouping based on module structure
- Hard to navigate which API calls go where

**Problem 3: Missing API Abstractions**
- No caching layer for read operations
- No automatic request deduplication
- No offline support
- No conflict resolution for concurrent writes

### Recommendation
Keep current structure but consider:
- Dynamic API namespace generation
- Optional request caching decorator
- Automatic retry logic for failed requests

---

## 5. CIRCULAR DEPENDENCIES & COUPLING

### Current Analysis

**Safe Patterns Found:**
✓ Stores → Composables ✓ Correct direction
✓ Stores → Services/API ✓ Correct direction
✓ Composables → Stores ✓ Correct direction
✓ Components → Stores/Composables ✓ Correct direction
✓ Services/API → No dependencies ✓ Correct isolation

**Potential Issues:**

**Issue 1: Store Cross-Dependencies**
- entity.ts imports facet state
- Some cross-store state mutations could cause issues
- Solution: Clear parent-child relationships or use shared composition

**Issue 2: Composable Depth**
- 82 relative imports in composables
- Some composables chain dependencies (A → B → C → D)
- Risk of hard-to-trace circular imports

**Issue 3: Type Exports**
- types/entity.ts (302 lines) is a large type hub
- Many stores/composables depend on it
- Could split into entity.ts, facet-types.ts, etc.

### Recommendation
- Map dependency graph to identify deep chains
- Implement max-depth limit (suggest 3 levels)
- Use index files to prevent circular imports

---

## 6. DUPLICATED LOGIC PATTERNS

### Identified Duplications

**Pattern 1: Loading State Management**
Found in 30+ places:
```ts
const loading = ref(false)
const error = ref(null)
const execute = async () => { loading.value = true; try { ... } finally { loading.value = false } }
```
**Solution:** useAsyncOperation exists but underutilized. Audit calls to replace manual patterns.

**Pattern 2: Dialog/Modal Management**
Repeated in 15+ components:
```ts
const dialogOpen = ref(false)
const selectedItem = ref(null)
const open = (item) => { selectedItem.value = item; dialogOpen.value = true }
const close = () => { dialogOpen.value = false; selectedItem.value = null }
```
**Solution:** Create useDialog composable.

**Pattern 3: Table State Management**
Found in 8+ places (EntityTable, SourcesTable, CrawlJobs, etc.):
```ts
const page = ref(1)
const perPage = ref(20)
const total = ref(0)
const sortBy = ref('name')
const filters = ref({})
```
**Solution:** Create useDataTable composable.

**Pattern 4: Snackbar Toast Notifications**
Repeated pattern across views:
```ts
const { showSuccess, showError } = useSnackbar()
try { await api.action(); showSuccess(...) }
catch (e) { showError(getErrorMessage(e)) }
```
**Solution:** Create wrapper composable or helper function.

### Missing Abstractions

**1. Form State Management**
- DynamicSchemaForm.vue (417 lines) handles complex form logic
- Repeated in SourceFormDialog, EntityFormDialog, etc.
- **Solution:** useFormState composable

**2. List Operations**
- Search, filter, pagination repeated across views
- **Solution:** useListView composable

**3. Export/Download**
- Implemented in 3+ places differently
- **Solution:** Already has useTableExport, useEntityExport - unify

**4. Chart Visualization**
- Similar chart setup in multiple places
- **Solution:** Extract chart configuration logic

---

## 7. MISSING MODULARITY OPPORTUNITIES

### Features That Should Be Isolated

1. **Search & Autocomplete**
   - Scattered in entity search, facet search, location search
   - **Opportunity:** useSearch composable with debouncing

2. **Batch Operations**
   - useAssistantBatch exists (good!)
   - But similar pattern needed for other entities
   - **Opportunity:** Generic useBatchOperations composable

3. **Rich Text Editing**
   - Used in multiple places
   - **Opportunity:** useRichTextEditor composable

4. **Permission Checking**
   - Some scattered permission checks
   - **Opportunity:** usePermissions composable with hook

5. **Real-time Updates (SSE)**
   - Implemented in useCrawlerAdmin
   - Pattern should be extracted
   - **Opportunity:** useSSE generic composable

---

## 8. RECOMMENDATIONS SUMMARY

### HIGH PRIORITY

1. **Split oversized stores** (customSummaries, sources, notifications)
   - Impact: Better maintainability, easier testing
   - Effort: High
   - Timeline: 2-3 weeks

2. **Extract monolithic composables** (useCrawlerAdmin, usePySisProcess)
   - Impact: Reduced cognitive load, easier to test
   - Effort: Medium
   - Timeline: 1-2 weeks

3. **Break down large components** (MapVisualization, ChatWindow, EntityMapView)
   - Impact: Better reusability, easier to test
   - Effort: Medium
   - Timeline: 1-2 weeks per component

4. **Standardize async patterns**
   - Replace manual loading/error handling with useAsyncOperation
   - Impact: Consistency, fewer bugs
   - Effort: Low
   - Timeline: 3-5 days

### MEDIUM PRIORITY

5. **Create missing composables**
   - useDialog, useDataTable, useFormState
   - Impact: Eliminates code duplication
   - Effort: Medium
   - Timeline: 1-2 weeks

6. **Refactor store exports**
   - Better organize API index.ts
   - Impact: Easier navigation, reduced file size
   - Effort: Low
   - Timeline: 1-2 days

7. **Extract shared type definitions**
   - Split oversized type files
   - Impact: Better maintainability
   - Effort: Low
   - Timeline: 1-2 days

### LOW PRIORITY

8. **Add circular dependency detection**
   - Use eslint-plugin-import
   - Impact: Prevents future issues
   - Effort: Low
   - Timeline: 1 day

9. **Document composable patterns**
   - Create composable style guide
   - Impact: Better consistency
   - Effort: Low
   - Timeline: 1-2 days

---

## 10. METRICS SUMMARY

| Metric | Value | Assessment |
|--------|-------|------------|
| Files >500 lines | 12 components, 3 stores, 5 composables | HIGH - needs splitting |
| Average composable size | ~150 lines | GOOD |
| Average store size | ~380 lines | ACCEPTABLE |
| Average component size | ~300 lines | ACCEPTABLE |
| Relative imports in composables | 82 | MODERATE - watch for circles |
| State declarations (ref/computed) | 472 | HIGH - consider composition |
| Composable files | 68 | MODERATE - could group better |
| API namespaces | 12 | GOOD - clear separation |
| Oversized stores | 3 | CRITICAL - needs refactoring |
| Code duplication patterns identified | 4 major | MEDIUM - reduce duplication |

---

## Conclusion

The frontend codebase demonstrates **good overall architecture** with clear API/Store/Composable separation. However, **component and composable sizing** represents the biggest modularity challenge. The three oversized stores need splitting, and several composables exceed ideal complexity thresholds.

**Key Strengths:**
- Clean API layer isolation
- Good use of Pinia for state management
- Emerging modular composable patterns (Facets, Assistant, SmartQuery)
- No evidence of circular dependencies

**Key Weaknesses:**
- Component sizes (12 files >500 lines)
- Store sizes (3 files >600 lines)
- Duplicated async/loading patterns
- Missing composable abstractions
- Type file too large (302 lines in types/entity.ts)

**Expected Impact of Refactoring:**
- 30-40% reduction in largest files
- 50% reduction in code duplication
- Improved testability and reusability
- Better onboarding for new developers
