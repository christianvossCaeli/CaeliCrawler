# Modularity & Architecture Audit (31.12.2024)

## Executive Summary

The codebase demonstrates **good architectural separation** overall, but shows signs of growth-related complexity in several areas. No critical circular dependencies detected. Key issues involve component size, service layer consolidation opportunities, and missing abstractions in reusable UI patterns.

---

## BACKEND ANALYSIS (Python/FastAPI)

### 1. Service Layer Separation

**Current State: GOOD with CONSOLIDATION OPPORTUNITIES**

Large service files by responsibility:

| File | Lines | Responsibilities | Status |
|------|-------|-----------------|--------|
| `app/utils/similarity.py` | 1930 | Embedding generation, caching, similarity search, hierarchy mapping | OVERSIZED |
| `services/smart_query/entity_operations.py` | 1731 | Entity/Type creation, API fetching, hierarchy handling | LARGE |
| `services/ai_service.py` | 843 | LLM interactions, embeddings, multiple analysis types | GOOD |
| `services/entity_facet_service.py` | 1120 | Facet management, versioning, aggregation | LARGE |
| `services/smart_query/category_setup.py` | 1371 | Category initialization, template handling | LARGE |

**Observations:**
- `similarity.py` mixes 4+ distinct concerns: embeddings, caching, similarity matching, hierarchy logic
- `entity_operations.py` has good responsibility scope but 1730 lines is borderline
- Services are well-separated from API layer (0 API imports in services)
- Good use of helper modules (prompts.py, visualization_selector.py, etc.)

**Recommendations:**
1. **Split `similarity.py`** into:
   - `embedding_service.py` - generate_embedding, batch generation
   - `similarity_matcher.py` - find_similar_*, cosine similarity
   - `hierarchy_mapper.py` - hierarchy lookup, caching
   - `embedding_cache.py` - TTL cache management

2. **Extract from `entity_operations.py`**:
   - Move API fetching → `api_fetcher.py` (already exists, consolidate)
   - Move location logic → `location_operations.py`

3. **Extract from `entity_facet_service.py`**:
   - Move aggregation logic → `facet_aggregation_service.py`
   - Move versioning → `facet_version_service.py` (separate concern)

---

### 2. API Router Organization

**Current State: GOOD**

Well-organized router structure in `app/main.py`:
- 30+ routers mounted with clear prefixes
- Admin API isolated under `/admin` prefix
- V1 API grouped by feature (entities, facets, relations, etc.)
- Clear tag organization for API documentation

**Files > 500 lines requiring attention:**

| File | Lines | Route Count | Issues |
|------|-------|------------|--------|
| `app/api/v1/facets.py` | 1617 | 21 endpoints | OVER-LOADED |
| `app/api/v1/entities.py` | 1477 | 18+ endpoints | LARGE |
| `app/api/admin/custom_summaries.py` | 1407 | 14+ endpoints | LARGE |
| `app/api/v1/assistant.py` | 1226 | 8+ endpoints | OK |
| `app/api/admin/categories.py` | 1140 | 14+ endpoints | LARGE |

**Recommendations:**
1. **Split `facets.py`** (1617 lines, 21 endpoints):
   - `facets_types.py` - FacetType CRUD (lines 65-570)
   - `facets_values.py` - FacetValue management (lines 572-968)
   - `facets_history.py` - History tracking endpoints (lines 1377-1586)
   - Keep main router as dispatcher

2. **Split `entities.py`** (1477 lines):
   - Extract relation endpoints → `relations.py` (partially done)
   - Extract attachment endpoints → `attachments.py` (partially done)
   - Consolidate entity core operations

3. **Split `admin/custom_summaries.py`** (1407 lines):
   - `summary_execution.py` - execution and runs
   - `summary_widgets.py` - widget configuration
   - `summary_management.py` - CRUD and configuration

---

### 3. Dependency Injection Patterns

**Current State: EXCELLENT**

Well-implemented DI using FastAPI's Depends:
- `app/core/deps.py` - centralized dependency definitions
- Proper use of HTTPBearer401 custom class
- Clear separation: `get_current_user`, `require_editor`, `require_admin`
- Session injection: `Depends(get_session)`
- AuditContext injection for audit logging

**Best Practices Observed:**
- HTTPBearer with proper 401/403 distinction
- Custom exception handling for token validation
- Optional authentication support via `HTTPBearer(auto_error=False)`

**No Issues Found** - Pattern is industry-standard and clean.

---

### 4. Model/Schema Separation

**Current State: VERY GOOD**

**File Organization:**
- 44 model files in `app/models/` (well-distributed)
- 26 schema files in `app/schemas/` (good 1:2 ratio)
- Clear separation between database models and API schemas
- Schema files match model domains (entity.py ↔ entity_type.py)

**Observations:**
- Models use proper mixins (VersionedMixin, TimestampMixin)
- Models import cleanly (no circular dependencies detected)
- Schemas properly import from models for type hints
- Good use of TYPE_CHECKING for forward references

**Minimal Issues:**
- Some large schema files could benefit from sub-modules:
  - `schemas/entity_type.py` - Entity type related schemas
  - `schemas/facet_type.py` - Facet type related schemas

---

### 5. Worker Task Organization

**Current State: GOOD with STRUCTURE CONCERNS**

| File | Lines | Tasks | Status |
|------|-------|-------|--------|
| `workers/ai_tasks/pysis_processor.py` | 1447 | 4 tasks | OVERSIZED |
| `workers/maintenance_tasks.py` | 1273 | 4 major tasks | LARGE |
| `workers/ai_tasks/common.py` | 955 | 15+ helper functions | UTILITY |
| `workers/ai_tasks/document_analyzer.py` | 888 | 3 tasks | OK |
| `workers/summary_tasks.py` | 872 | 4 tasks | OK |
| `workers/ai_tasks/entity_operations.py` | 682 | 3 tasks | OK |

**Issues:**
1. **`pysis_processor.py` (1447 lines)**:
   - Mixes PySis field processing with facet enrichment
   - Consider splitting: `pysis_field_tasks.py` + `pysis_facet_enrichment_tasks.py`

2. **`maintenance_tasks.py` (1273 lines)**:
   - Contains 4 distinct long-running migrations
   - `migrate_entity_references` (200 lines) - separate into `entity_reference_migration_tasks.py`
   - `migrate_facet_value_entity_links` - separate file
   - `reclassify_entities` - separate file
   - Keep `aggregate_llm_usage` and `check_llm_budgets` together

3. **`ai_tasks/common.py` (955 lines)**:
   - Good utility module, but should be split:
    - `ai_tasks/resolution.py` - Entity resolution functions
    - `ai_tasks/llm_utils.py` - LLM interaction helpers
    - `ai_tasks/validation.py` - Data validation functions

---

## FRONTEND ANALYSIS (Vue 3/TypeScript)

### 1. Component Composition

**Current State: NEEDS REFACTORING**

Components > 700 lines (should be ≤ 500 for maintainability):

| Component | Lines | Responsibilities | Priority |
|-----------|-------|-----------------|----------|
| `PySisTab.vue` | 1474 | Field management, process sync, template handling | HIGH |
| `EntityFacetsTab.vue` | 1302 | Facet display, enrichment, source selection | HIGH |
| `ChatAssistant.vue` | 1047 | Chat UI, file upload, message rendering | MEDIUM |
| `PlanModeChat.vue` | 918 | Plan execution, result display | MEDIUM |
| `MapVisualization.vue` | 862 | Map rendering, clustering, data binding | MEDIUM |
| `ChatWindow.vue` | 830 | Message display, formatting, interaction | MEDIUM |
| `EntityMapView.vue` | 765 | Entity map visualization, filters | MEDIUM |
| `EntityAttachmentsTab.vue` | 741 | Attachment management, analysis | MEDIUM |
| `ScheduleBuilder.vue` | 680 | CRON expression builder | MEDIUM |

**Specific Issues:**

1. **PySisTab.vue (1474 lines)** - Multiple concerns:
   - Process list management
   - Field editor/renderer
   - Template dialog
   - Facet enrichment dialogs
   - Sync operations (pull/push)
   - **Action:** Split into:
     - `PySisProcessList.vue` (300 lines)
     - `PySisFieldEditor.vue` (400 lines)
     - `PySisTemplateDialog.vue` (200 lines)
     - `PySisFacetEnrichmentPanel.vue` (300 lines)
     - `PySisTab.vue` (orchestrator, 200 lines)

2. **EntityFacetsTab.vue (1302 lines)** - Too many concerns:
   - Facet search and filtering
   - Enrichment source selection
   - Entity enrichment operations
   - Facet value listing and editing
   - History tracking
   - **Action:** Split into:
     - `FacetSearchPanel.vue` (150 lines)
     - `EnrichmentSourceSelector.vue` (200 lines)
     - `FacetValuesList.vue` (300 lines)
     - `EntityFacetsTab.vue` (orchestrator, 250 lines)

3. **ChatAssistant.vue (1047 lines)**:
   - Chat message loop
   - File upload
   - Quick actions
   - Input hints
   - **Action:** Extract:
     - `ChatMessageList.vue` (250 lines) - message display
     - `ChatFileUpload.vue` (150 lines)
     - `ChatQuickActions.vue` (150 lines)

---

### 2. Composable Reusability

**Current State: GOOD with SOME DUPLICATION**

Large composables (>600 lines, should be <400):

| Composable | Lines | Purpose | Issue |
|-----------|-------|---------|-------|
| `useResultsView.ts` | 875 | Data filtering, loading, actions | OVERSIZED |
| `assistant/index.ts` | 775 | Assistant logic aggregator | OVER-AGGREGATED |
| `useEntitiesView.ts` | 699 | Entity list management | LARGE |
| `useDocumentsView.ts` | 653 | Document list management | LARGE |

**Recommendations:**
1. **useResultsView.ts (875 lines)** - Extract:
   - `useExtractedDataFilters.ts` - filter logic (200 lines)
   - `useExtractedDataTable.ts` - table state (200 lines)
   - `useExtractedDataActions.ts` - bulk operations (150 lines)
   - Keep orchestrator at 325 lines

2. **assistant/index.ts (775 lines)** - Currently aggregates:
   - Query execution
   - Message handling
   - File processing
   - **Action:** Already decomposed into sub-files, consolidate exports only

3. **useEntitiesView.ts, useDocumentsView.ts** - Similar pattern:
   - These are view orchestrators, OK at 650-700 lines
   - Extract shared filter logic → `useListViewFilters.ts` (reusable)

**Positive Findings:**
- Good use of composable composition
- `useFacetTypeRenderer.ts` (309 lines) - well-focused
- `useNotifications.ts` (378 lines) - good separation
- Test files properly separated (.test.ts pattern)

---

### 3. Store Organization (Pinia)

**Current State: EXCELLENT**

Store files by size:

| Store | Lines | Status |
|-------|-------|--------|
| `customSummaries.ts` | 986 | EXCELLENT |
| `sources.ts` | 787 | GOOD |
| `crawlPresets.ts` | 389 | GOOD |
| `entity.ts` | 387 | GOOD |
| `llmUsage.ts` | 370 | GOOD |
| `facet.ts` | 309 | GOOD |
| `auth.ts` | 306 | GOOD |
| `dashboard.ts` | 234 | GOOD |

**Observations:**
- Well-organized with clear state/actions/getters
- Good test coverage (customSummaries.test.ts, sources.test.ts, auth.test.ts)
- No oversized stores (all <1000 lines)
- Clear separation of concerns

**No Major Issues** - Store organization follows best practices.

---

### 4. API Client Structure

**Current State: GOOD**

| File | Lines | Coverage |
|------|-------|----------|
| `services/api/index.ts` | 519 | Main export hub |
| `services/api/client.ts` | ~200 | HTTP client config |
| `services/api/sources.ts` | ~250 | Source endpoints |
| `services/api/facets.ts` | ~200 | Facet endpoints |
| `services/api/admin.ts` | ~300 | Admin endpoints |

**Observations:**
- Good modular structure by domain
- Centralized HTTP client
- Type-safe endpoints
- Proper error handling integration

**Recommendations:**
- Consider creating `services/api/entities.ts` (currently inline)
- Consolidate data API client exports

---

### 5. Type Definitions Organization

**Current State: GOOD**

| File | Lines | Scope |
|------|-------|-------|
| `types/entity.ts` | 846 | Entity, Facet, Relation types |
| `types/sources.ts` | 729 | Source, Crawler types |
| `types/admin.ts` | 552 | Admin panel types |
| `types/assistant.ts` | 402 | Chat, assistant types |
| `types/category.ts` | 268 | Category types |

**Observations:**
- Well-distributed type definitions
- Good naming conventions
- Clear domain boundaries

**No Issues Found** - Structure is appropriate.

---

## CROSS-CUTTING CONCERNS

### Circular Dependencies

**Status: NO CRITICAL ISSUES**
- ✅ Services do NOT import from API layer
- ✅ Models have minimal cross-imports
- ✅ Schemas properly import models (one-way)
- ✅ Workers are isolated

### Tight Coupling Issues

**Identified:**

1. **API handlers tightly coupled to specific services**
   - Example: `facets.py` hard-depends on `FacetHistoryService`
   - **Mitigation:** Already via dependency injection, OK pattern

2. **Frontend components import directly from stores**
   - Example: EntityFacetsTab imports 5+ store modules
   - **Recommendation:** Create store aggregator composable
   - See: `src/composables/useStoreAggregator.ts` (proposed)

3. **Worker tasks importing multiple service layers**
   - Example: `ai_tasks/common.py` imports 8+ services
   - **Status:** Acceptable (tasks are orchestrators)

### Missing Abstractions

1. **Frontend**: No reusable form builder
   - Components like `SourceFormDialog`, `EntityFormDialog` have overlapping logic
   - **Recommendation:** Create `GenericFormBuilder.vue` + validation composable

2. **Backend**: No generic list endpoint abstraction
   - Filtering logic repeated across 15+ endpoints
   - **Recommendation:** Create `BaseCRUDRouter` mixin

3. **Frontend**: No unified data grid abstraction
   - Multiple tables using similar pagination/sorting
   - **Recommendation:** Extract `DataTableComposable.ts` (in progress)

---

## SUMMARY SCORES

| Category | Score | Status |
|----------|-------|--------|
| Service Separation | 7.5/10 | Good, needs consolidation |
| API Organization | 7/10 | Good, needs router splitting |
| Dependency Injection | 9.5/10 | Excellent |
| Model/Schema Separation | 9/10 | Excellent |
| Worker Organization | 6.5/10 | Good, needs restructuring |
| Component Composition | 5.5/10 | Needs refactoring |
| Composable Reusability | 7.5/10 | Good, extract large ones |
| Store Organization | 9/10 | Excellent |
| API Client Structure | 8/10 | Good |
| Type Organization | 9/10 | Excellent |
| **OVERALL** | **7.7/10** | **GOOD WITH IMPROVEMENTS** |

---

## PRIORITY RECOMMENDATIONS

### Immediate (High Impact)
1. Split `similarity.py` into 3-4 focused modules
2. Break down `PySisTab.vue` into 5 sub-components
3. Extract `EntityFacetsTab.vue` utilities into separate components

### Short-term (Medium Impact)
4. Refactor `facets.py` router into 3 sub-routers
5. Extract composable logic from large view composables
6. Create generic form builder abstraction

### Medium-term (Continuous Improvement)
7. Consolidate `ai_tasks/` structure
8. Extract reusable list/table patterns
9. Create store aggregator for frontend

