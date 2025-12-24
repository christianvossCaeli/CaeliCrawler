<template>
  <div class="sources-page d-flex">
    <!-- Loading Skeleton for initial load -->
    <template v-if="store.sourcesLoading && sources.length === 0">
      <SourcesSkeleton />
    </template>

    <template v-else>
      <!-- Sidebar Navigation -->
      <SourcesSidebar
        v-model="sidebarOpen"
        :counts="store.sidebarCounts"
        :selected-category="store.filters.category_id"
        :selected-type="store.filters.source_type"
        :selected-status="store.filters.status"
        :selected-tags="store.filters.tags"
        :available-tags="store.availableTags"
        @update:selected-category="onCategorySelect"
        @update:selected-type="onTypeSelect"
        @update:selected-status="onStatusSelect"
        @update:selected-tags="onTagsSelect"
      />

      <!-- Main Content -->
      <div class="sources-main flex-grow-1">
        <PageHeader
          :title="$t('sources.title')"
          :subtitle="$t('sources.subtitle')"
          icon="mdi-database"
          :count="store.sourcesTotal"
        >
          <template #actions>
            <v-btn
              icon="mdi-menu"
              variant="text"
              class="d-md-none"
              :aria-label="$t('common.toggleMenu')"
              @click="sidebarOpen = !sidebarOpen"
            />
            <!-- Import Dropdown Menu -->
            <v-menu>
              <template v-slot:activator="{ props }">
                <v-btn v-bind="props" variant="tonal" color="secondary">
                  <v-icon start>mdi-import</v-icon>
                  {{ $t('sources.import.title') }}
                  <v-icon end>mdi-chevron-down</v-icon>
                </v-btn>
              </template>
              <v-list density="compact">
                <v-list-item @click="bulkDialog = true">
                  <template v-slot:prepend>
                    <v-icon color="secondary">mdi-file-upload</v-icon>
                  </template>
                  <v-list-item-title>{{ $t('sources.import.bulkImport') }}</v-list-item-title>
                  <v-list-item-subtitle>{{ $t('sources.import.bulkImportDesc') }}</v-list-item-subtitle>
                </v-list-item>
                <v-list-item @click="apiImportDialog = true">
                  <template v-slot:prepend>
                    <v-icon color="info">mdi-api</v-icon>
                  </template>
                  <v-list-item-title>{{ $t('sources.import.apiImport') }}</v-list-item-title>
                  <v-list-item-subtitle>{{ $t('sources.import.apiImportDesc') }}</v-list-item-subtitle>
                </v-list-item>
                <v-divider />
                <v-list-item @click="aiDiscoveryDialog = true">
                  <template v-slot:prepend>
                    <v-icon color="primary">mdi-robot</v-icon>
                  </template>
                  <v-list-item-title class="text-primary font-weight-bold">{{ $t('sources.import.aiDiscovery') }}</v-list-item-title>
                  <v-list-item-subtitle>{{ $t('sources.import.aiDiscoveryDesc') }}</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-menu>

            <v-btn variant="tonal" color="primary" @click="openCreateDialog">
              <v-icon start>mdi-plus</v-icon>{{ $t('sources.actions.create') }}
            </v-btn>
          </template>
        </PageHeader>

        <!-- Active Filters Display -->
        <SourcesActiveFilters
          :category-id="store.filters.category_id"
          :category-name="store.getCategoryName(store.filters.category_id || '')"
          :source-type="store.filters.source_type"
          :status="store.filters.status"
          :tags="store.filters.tags"
          @clear:category="onCategorySelect(null)"
          @clear:type="onTypeSelect(null)"
          @clear:status="onStatusSelect(null)"
          @clear:tag="(tag: string) => onTagsSelect(store.filters.tags.filter(t => t !== tag))"
          @clear:all="clearAllFilters"
        />

        <!-- Search Filter -->
        <v-card class="mb-4">
          <v-card-text class="py-3">
            <v-row align="center">
              <v-col cols="12" md="6">
                <v-text-field
                  v-model="store.filters.search"
                  :label="$t('sources.filters.search')"
                  prepend-inner-icon="mdi-magnify"
                  clearable
                  hide-details
                  @update:model-value="debouncedSearch"
                ></v-text-field>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>

        <!-- Sources Table -->
        <v-card>
          <v-data-table-server
            :headers="headers"
            :items="sources"
            :items-length="store.sourcesTotal"
            :loading="store.sourcesLoading"
            :items-per-page="store.itemsPerPage"
            :page="store.currentPage"
            @update:options="onTableOptionsUpdate"
          >
            <template v-slot:item.categories="{ item }">
              <div class="d-flex flex-wrap gap-1">
                <v-chip
                  v-for="cat in (item.categories || [])"
                  :key="cat.id"
                  :color="cat.is_primary ? 'primary' : 'default'"
                  size="x-small"
                  variant="tonal"
                >
                  {{ cat.name }}
                  <v-icon v-if="cat.is_primary" end size="x-small">mdi-star</v-icon>
                </v-chip>
                <v-chip v-if="!item.categories?.length && item.category_name" size="x-small" variant="tonal">
                  {{ item.category_name }}
                </v-chip>
              </div>
            </template>

            <template v-slot:item.source_type="{ item }">
              <v-chip :color="getTypeColor(item.source_type)" size="small">
                {{ getTypeLabel(item.source_type) }}
              </v-chip>
            </template>

            <template v-slot:item.status="{ item }">
              <v-chip :color="getStatusColor(item.status)" size="small">
                {{ getStatusLabel(item.status) }}
              </v-chip>
            </template>

            <template v-slot:item.last_crawl="{ item }">
              {{ item.last_crawl ? formatDate(item.last_crawl) : $t('sources.never') }}
            </template>

            <template v-slot:item.actions="{ item }">
              <SourcesTableActions
                :source="item"
                :is-starting="isStartingCrawl(item.id)"
                :is-resetting="isResetting(item.id)"
                @edit="openEditDialog"
                @start-crawl="handleStartCrawl"
                @reset="handleResetSource"
                @delete="confirmDelete"
              />
            </template>

            <!-- Empty State -->
            <template v-slot:no-data>
              <div class="text-center py-8">
                <v-icon size="64" color="grey-lighten-1" class="mb-4">
                  {{ store.hasActiveFilters ? 'mdi-filter-off' : 'mdi-database-off' }}
                </v-icon>
                <h3 class="text-h6 text-medium-emphasis mb-2">
                  {{ store.hasActiveFilters ? $t('sources.empty.noFilterResults') : $t('sources.empty.noSources') }}
                </h3>
                <p class="text-body-2 text-disabled mb-4">
                  {{ store.hasActiveFilters ? $t('sources.empty.adjustFilters') : $t('sources.empty.createFirst') }}
                </p>
                <v-btn
                  v-if="store.hasActiveFilters"
                  variant="tonal"
                  color="primary"
                  @click="clearAllFilters"
                >
                  <v-icon start>mdi-filter-off</v-icon>
                  {{ $t('sources.filters.clearAll') }}
                </v-btn>
                <v-btn
                  v-else
                  variant="tonal"
                  color="primary"
                  @click="openCreateDialog"
                >
                  <v-icon start>mdi-plus</v-icon>
                  {{ $t('sources.actions.create') }}
                </v-btn>
              </div>
            </template>
          </v-data-table-server>
        </v-card>

        <!-- Create/Edit Dialog with Error Boundary (lazy-loaded) -->
        <ErrorBoundary v-if="formDialog" @error="onDialogError" @reset="formDialog = false">
          <Suspense>
            <SourceFormDialog
              v-model="formDialog"
              :edit-mode="store.editMode"
              :form-data="store.formData"
              :categories="store.categories"
              :tag-suggestions="store.tagSuggestions"
              :selected-entities="store.selectedEntities"
              :saving="store.saving"
              @update:form-data="store.formData = $event"
              @update:selected-entities="store.selectedEntities = $event"
              @save="saveSource"
              @show-category-info="showCategoryInfo"
            />
            <template #fallback>
              <v-dialog :model-value="true" max-width="600" persistent>
                <v-card class="d-flex align-center justify-center pa-8">
                  <v-progress-circular indeterminate color="primary" size="48" />
                </v-card>
              </v-dialog>
            </template>
          </Suspense>
        </ErrorBoundary>

        <!-- Bulk Import Dialog with Error Boundary (lazy-loaded) -->
        <ErrorBoundary v-if="bulkDialog" @error="onDialogError" @reset="bulkDialog = false">
          <Suspense>
            <SourcesBulkImportDialog
              v-model="bulkDialog"
              :categories="store.categories"
              :tag-suggestions="store.tagSuggestions"
              :existing-urls="existingUrls"
              @import="handleBulkImport"
            />
            <template #fallback>
              <v-dialog :model-value="true" max-width="800" persistent>
                <v-card class="d-flex align-center justify-center pa-8">
                  <v-progress-circular indeterminate color="primary" size="48" />
                </v-card>
              </v-dialog>
            </template>
          </Suspense>
        </ErrorBoundary>

        <!-- Delete Dialog -->
        <SourcesDeleteDialog
          v-model="deleteDialog"
          :source="store.selectedSource"
          :deleting="deleting"
          @confirm="handleDeleteSource"
        />

        <!-- API Import Dialog with Error Boundary (lazy-loaded) -->
        <ErrorBoundary v-if="apiImportDialog" @error="onDialogError" @reset="apiImportDialog = false">
          <Suspense>
            <ApiImportDialog
              v-model="apiImportDialog"
              :categories="store.categories"
              :available-tags="store.tagSuggestions"
              @imported="onApiImported"
            />
            <template #fallback>
              <v-dialog :model-value="true" max-width="900" persistent>
                <v-card class="d-flex align-center justify-center pa-8">
                  <v-progress-circular indeterminate color="primary" size="48" />
                </v-card>
              </v-dialog>
            </template>
          </Suspense>
        </ErrorBoundary>

        <!-- AI Discovery Dialog with Error Boundary (lazy-loaded) -->
        <ErrorBoundary v-if="aiDiscoveryDialog" @error="onDialogError" @reset="aiDiscoveryDialog = false">
          <Suspense>
            <AiDiscoveryDialog
              v-model="aiDiscoveryDialog"
              :categories="store.categories"
              @imported="onAiDiscoveryImported"
            />
            <template #fallback>
              <v-dialog :model-value="true" max-width="1200" persistent>
                <v-card class="d-flex align-center justify-center pa-8">
                  <v-progress-circular indeterminate color="primary" size="48" />
                </v-card>
              </v-dialog>
            </template>
          </Suspense>
        </ErrorBoundary>

        <!-- Category Info Dialog -->
        <CategoryInfoDialog
          v-model="categoryInfoDialog"
          :category="store.selectedCategoryInfo"
        />

        <!-- Snackbar for feedback -->
        <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3000">
          {{ snackbar.text }}
        </v-snackbar>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * SourcesView - Main view for managing data sources
 *
 * Uses Pinia store for centralized state management.
 * Handles CRUD operations, filtering, bulk import, and AI discovery.
 */
import { ref, computed, onMounted, defineAsyncComponent } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'
import { useDebounceFn } from '@vueuse/core'
import { useSourcesStore } from '@/stores/sources'
// Always-visible components loaded synchronously
import {
  SourcesSidebar,
  SourcesDeleteDialog,
  SourcesSkeleton,
  CategoryInfoDialog,
  SourcesActiveFilters,
  SourcesTableActions,
} from '@/components/sources'
import { useSourceHelpers } from '@/composables/useSourceHelpers'
import { PageHeader, ErrorBoundary } from '@/components/common'
import { SEARCH, TABLE_HEADERS, ACTION_CLEANUP_DELAY } from '@/config/sources'
import type { BulkImportState, DataSourceResponse, SourceType, SourceStatus } from '@/types/sources'

// =============================================================================
// Lazy-loaded Dialog Components (heavy, only loaded when needed)
// =============================================================================

const SourceFormDialog = defineAsyncComponent({
  loader: () => import('@/components/sources/SourceFormDialog.vue'),
  delay: 200,
})

const SourcesBulkImportDialog = defineAsyncComponent({
  loader: () => import('@/components/sources/SourcesBulkImportDialog.vue'),
  delay: 200,
})

const ApiImportDialog = defineAsyncComponent({
  loader: () => import('@/components/sources/ApiImportDialog.vue'),
  delay: 200,
})

const AiDiscoveryDialog = defineAsyncComponent({
  loader: () => import('@/components/sources/AiDiscoveryDialog.vue'),
  delay: 200,
})

// =============================================================================
// Store & Composables
// =============================================================================

const store = useSourcesStore()
const { sources } = storeToRefs(store)
const { t } = useI18n()
const route = useRoute()

const {
  getTypeColor,
  getTypeLabel,
  getStatusColor,
  getStatusLabel,
  formatDate,
} = useSourceHelpers()

// =============================================================================
// Local UI State (dialogs, sidebar, etc.)
// =============================================================================

const sidebarOpen = ref(true)
const formDialog = ref(false)
const bulkDialog = ref(false)
const deleteDialog = ref(false)
const categoryInfoDialog = ref(false)
const apiImportDialog = ref(false)
const aiDiscoveryDialog = ref(false)
const deleting = ref(false)

/** Snackbar state */
const snackbar = ref({
  show: false,
  text: '',
  color: 'success',
})

/** Per-source loading states for individual actions */
const actionLoading = ref<{
  starting: Record<string, boolean>
  resetting: Record<string, boolean>
}>({
  starting: {},
  resetting: {},
})

// =============================================================================
// Computed Properties
// =============================================================================

/** Check if a specific source is starting a crawl */
const isStartingCrawl = (sourceId: string) => actionLoading.value.starting[sourceId] ?? false

/** Check if a specific source is being reset */
const isResetting = (sourceId: string) => actionLoading.value.resetting[sourceId] ?? false

/** Existing URLs for duplicate detection in bulk import */
const existingUrls = computed(() => sources.value.map(s => s.base_url || ''))

/** Table headers with translations (using centralized config) */
const headers = computed(() =>
  TABLE_HEADERS.map((header) => ({
    title: t(header.i18nKey),
    key: header.key,
    ...(header.sortable !== undefined && { sortable: header.sortable }),
    ...(header.align && { align: header.align }),
  }))
)

// =============================================================================
// Debounced Search (VueUse handles cleanup automatically)
// =============================================================================

/**
 * Debounced search handler - waits before fetching (using config)
 * VueUse automatically cleans up on component unmount
 */
const debouncedSearch = useDebounceFn(() => {
  store.currentPage = 1
  store.fetchSources(1)
}, SEARCH.DEBOUNCE_MS)

// =============================================================================
// Filter Handlers
// =============================================================================

/**
 * Handle category filter change
 */
const onCategorySelect = (categoryId: string | null) => {
  store.setFilter('category_id', categoryId)
  store.fetchSources(1)
}

/**
 * Handle source type filter change
 */
const onTypeSelect = (type: SourceType | null) => {
  store.setFilter('source_type', type)
  store.fetchSources(1)
}

/**
 * Handle status filter change
 */
const onStatusSelect = (status: SourceStatus | null) => {
  store.setFilter('status', status)
  store.fetchSources(1)
}

/**
 * Handle tags filter change
 */
const onTagsSelect = (tags: string[]) => {
  store.setFilter('tags', tags)
  store.fetchSources(1)
}

/**
 * Clear all active filters
 */
const clearAllFilters = () => {
  store.clearAllFilters()
  store.fetchSources(1)
}

// =============================================================================
// Table Handlers
// =============================================================================

/**
 * Handle table pagination/sorting changes
 */
const onTableOptionsUpdate = (options: { page: number; itemsPerPage: number }) => {
  if (options.itemsPerPage !== store.itemsPerPage) {
    store.itemsPerPage = options.itemsPerPage
  }
  store.fetchSources(options.page, options.itemsPerPage)
}

// =============================================================================
// Dialog Handlers
// =============================================================================

/**
 * Open create source dialog
 */
const openCreateDialog = () => {
  store.prepareCreateForm()
  formDialog.value = true
}

/**
 * Open edit source dialog
 */
const openEditDialog = async (source: DataSourceResponse) => {
  await store.prepareEditForm(source)
  formDialog.value = true
}

/**
 * Save source (create or update)
 */
const saveSource = async () => {
  try {
    await store.saveForm()
    formDialog.value = false
    showSnackbar(t('sources.messages.saved'), 'success')
  } catch (error) {
    console.error('Failed to save source:', error)
    showSnackbar(store.error || t('sources.errors.saveFailed'), 'error')
  }
}

/**
 * Show category info dialog
 */
const showCategoryInfo = (categoryId: string) => {
  const category = store.categories.find(c => c.id === categoryId)
  if (category) {
    store.selectedCategoryInfo = category
    categoryInfoDialog.value = true
  }
}

/**
 * Handle errors from dialog error boundaries
 */
const onDialogError = (error: Error, info: string) => {
  console.error('[SourcesView] Dialog error:', error, info)
  showSnackbar(t('common.errorOccurred'), 'error')
}

/**
 * Confirm delete source
 */
const confirmDelete = (source: DataSourceResponse) => {
  store.selectedSource = source
  deleteDialog.value = true
}

/**
 * Handle delete source
 */
const handleDeleteSource = async () => {
  if (!store.selectedSource) return

  deleting.value = true
  try {
    await store.deleteSource(store.selectedSource.id)
    deleteDialog.value = false
    showSnackbar(t('sources.messages.deleted'), 'success')
  } catch (error) {
    console.error('Failed to delete source:', error)
    showSnackbar(t('sources.errors.deleteFailed'), 'error')
  } finally {
    deleting.value = false
  }
}

// =============================================================================
// Action Handlers
// =============================================================================

/**
 * Start crawl for a source
 * Uses timestamp tracking to prevent race conditions in cleanup
 */
const handleStartCrawl = async (source: DataSourceResponse) => {
  actionLoading.value.starting[source.id] = true
  try {
    await store.startCrawl(source)
    showSnackbar(t('sources.messages.crawlStarted', { name: source.name }), 'success')
  } catch (error) {
    console.error('Failed to start crawl:', error)
    showSnackbar(t('sources.messages.crawlError'), 'error')
  } finally {
    // Only cleanup if no newer action has started (prevents race condition)
    setTimeout(() => {
      // Check if this is still the same action (not a newer one)
      if (actionLoading.value.starting[source.id] !== undefined) {
        delete actionLoading.value.starting[source.id]
      }
    }, ACTION_CLEANUP_DELAY)
  }
}

/**
 * Reset a source
 * Uses timestamp tracking to prevent race conditions in cleanup
 */
const handleResetSource = async (source: DataSourceResponse) => {
  actionLoading.value.resetting[source.id] = true
  try {
    await store.resetSource(source)
    showSnackbar(t('sources.messages.reset', { name: source.name }), 'success')
  } catch (error) {
    console.error('Failed to reset source:', error)
    showSnackbar(t('sources.messages.resetError'), 'error')
  } finally {
    // Only cleanup after delay (no intermediate false state)
    setTimeout(() => {
      if (actionLoading.value.resetting[source.id] !== undefined) {
        delete actionLoading.value.resetting[source.id]
      }
    }, ACTION_CLEANUP_DELAY)
  }
}

/**
 * Handle bulk import
 */
const handleBulkImport = async (data: BulkImportState) => {
  try {
    // Update store's bulk import state
    store.bulkImport.category_ids = data.category_ids
    store.bulkImport.default_tags = data.default_tags
    store.bulkImport.preview = data.preview
    store.bulkImport.skip_duplicates = data.skip_duplicates

    const result = await store.executeBulkImport()
    bulkDialog.value = false
    showSnackbar(
      t('sources.messages.bulkImportSuccess', {
        imported: result.imported,
        skipped: result.skipped,
      }),
      'success'
    )
  } catch (error) {
    console.error('Bulk import failed:', error)
    // Extract detailed error message from API response
    const apiError = error as { response?: { data?: { detail?: string; message?: string } }; message?: string }
    const errorDetail = apiError.response?.data?.detail
      || apiError.response?.data?.message
      || apiError.message
      || t('sources.messages.bulkImportError')
    showSnackbar(errorDetail, 'error')
  }
}

/**
 * Handle API import success
 */
const onApiImported = (count: number) => {
  showSnackbar(t('sources.messages.apiImportSuccess', { count }), 'success')
  store.fetchSources()
  store.fetchSidebarCounts()
  store.fetchAvailableTags()
}

/**
 * Handle AI discovery import success
 */
const onAiDiscoveryImported = (count: number) => {
  showSnackbar(t('sources.aiDiscovery.importSuccess', { count }), 'success')
  store.fetchSources()
  store.fetchSidebarCounts()
  store.fetchAvailableTags()
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Show snackbar message
 */
const showSnackbar = (text: string, color: 'success' | 'error' | 'warning' | 'info' = 'success') => {
  snackbar.value = { show: true, text, color }
}

// =============================================================================
// Lifecycle Hooks
// =============================================================================

onMounted(async () => {
  // Check for query parameters to pre-filter
  if (route.query.category_id) {
    store.filters.category_id = route.query.category_id as string
  }
  if (route.query.source_type) {
    store.setFilter('source_type', route.query.source_type as SourceType)
  }
  if (route.query.status) {
    store.setFilter('status', route.query.status as SourceStatus)
  }

  // Initialize store data
  await store.initialize()
})

// Note: VueUse's useDebounceFn handles cleanup automatically on unmount
</script>

<style scoped>
.sources-page {
  min-height: 100%;
}

.sources-main {
  padding: 16px;
  overflow-x: hidden;
}

@media (max-width: 960px) {
  .sources-main {
    padding: 8px;
  }
}
</style>
