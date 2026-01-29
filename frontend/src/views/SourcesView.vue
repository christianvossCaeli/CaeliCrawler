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
            <v-menu v-if="canEdit">
              <template #activator="{ props }">
                <v-btn v-bind="props" variant="tonal" color="secondary">
                  <v-icon start>mdi-import</v-icon>
                  {{ $t('sources.import.title') }}
                  <v-icon end>mdi-chevron-down</v-icon>
                </v-btn>
              </template>
              <v-list density="compact">
                <v-list-item v-if="canAdmin" @click="bulkDialog = true">
                  <template #prepend>
                    <v-icon color="secondary">mdi-file-upload</v-icon>
                  </template>
                  <v-list-item-title>{{ $t('sources.import.bulkImport') }}</v-list-item-title>
                  <v-list-item-subtitle>{{ $t('sources.import.bulkImportDesc') }}</v-list-item-subtitle>
                </v-list-item>
                <v-list-item v-if="canEdit" @click="apiImportDialog = true">
                  <template #prepend>
                    <v-icon color="info">mdi-api</v-icon>
                  </template>
                  <v-list-item-title>{{ $t('sources.import.apiImport') }}</v-list-item-title>
                  <v-list-item-subtitle>{{ $t('sources.import.apiImportDesc') }}</v-list-item-subtitle>
                </v-list-item>
                <template v-if="canEdit">
                  <v-divider />
                  <v-list-item @click="aiDiscoveryDialog = true">
                    <template #prepend>
                      <v-icon color="primary">mdi-robot</v-icon>
                    </template>
                    <v-list-item-title class="text-primary font-weight-bold">{{ $t('sources.import.aiDiscovery') }}</v-list-item-title>
                    <v-list-item-subtitle>{{ $t('sources.import.aiDiscoveryDesc') }}</v-list-item-subtitle>
                  </v-list-item>
                </template>
              </v-list>
            </v-menu>

            <v-btn v-if="canEdit" variant="tonal" color="primary" @click="openCreateDialog">
              <v-icon start>mdi-plus</v-icon>{{ $t('sources.actions.create') }}
            </v-btn>
          </template>
        </PageHeader>

        <!-- Info Box -->
        <PageInfoBox :storage-key="INFO_BOX_STORAGE_KEYS.SOURCES" :title="$t('sources.info.title')">
          {{ $t('sources.info.description') }}
        </PageInfoBox>

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

        <!-- Running Jobs Banner -->
        <v-alert
          v-if="runningJobsCount > 0"
          type="info"
          variant="tonal"
          density="compact"
          class="mb-4 cursor-pointer"
          closable
          @click="goToCrawler"
        >
          <template #prepend>
            <v-progress-circular
              indeterminate
              size="20"
              width="2"
              color="info"
              class="mr-2"
            />
          </template>
          <div class="d-flex align-center justify-space-between flex-wrap">
            <span>
              <strong>{{ runningJobsCount }}</strong> {{ $t('sources.runningJobs.active', runningJobsCount) }}
              <span v-if="runningJobs.length > 0" class="text-medium-emphasis ml-2">
                ({{ runningJobs.slice(0, 3).map(j => j.source_name).join(', ') }}{{ runningJobs.length > 3 ? '...' : '' }})
              </span>
            </span>
            <v-btn
              variant="text"
              color="info"
              size="small"
              append-icon="mdi-arrow-right"
              @click.stop="goToCrawler"
            >
              {{ $t('sources.runningJobs.viewAll') }}
            </v-btn>
          </div>
        </v-alert>

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
                  @keyup.enter="store.fetchSources(1)"
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
            :sort-by="store.sortBy"
            @update:options="onTableOptionsUpdate"
          >
            <template #item.categories="{ item }">
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

            <template #item.source_type="{ item }">
              <v-chip :color="getTypeColor(item.source_type)" size="small">
                {{ getTypeLabel(item.source_type) }}
              </v-chip>
            </template>

            <template #item.status="{ item }">
              <v-chip :color="getStatusColor(item.status)" size="small">
                {{ getStatusLabel(item.status) }}
              </v-chip>
            </template>

            <template #item.last_crawl="{ item }">
              {{ item.last_crawl ? formatDate(item.last_crawl) : $t('sources.never') }}
            </template>

            <template #item.actions="{ item }">
              <SourcesTableActions
                :source="item"
                :is-starting="isStartingCrawl(item.id)"
                :is-resetting="isResetting(item.id)"
                :can-edit="canEdit"
                :can-admin="canAdmin"
                @edit="openEditDialog"
                @start-crawl="handleStartCrawl"
                @reset="handleResetSource"
                @delete="confirmDelete"
              />
            </template>

            <!-- Empty State -->
            <template #no-data>
              <TableErrorState
                v-if="store.error"
                :title="$t('common.loadError')"
                :message="store.error || $t('errors.generic')"
                :retrying="store.sourcesLoading"
                @retry="store.fetchSources(1)"
              />
              <EmptyState
                v-else-if="store.hasActiveFilters"
                icon="mdi-filter-off"
                :title="$t('sources.empty.noFilterResults')"
                :description="$t('sources.empty.adjustFilters')"
              >
                <v-btn variant="tonal" color="primary" @click="clearAllFilters">
                  <v-icon start>mdi-filter-off</v-icon>
                  {{ $t('sources.filters.clearAll') }}
                </v-btn>
              </EmptyState>
              <EmptyState
                v-else
                icon="mdi-database-off"
                :title="$t('sources.empty.noSources')"
                :description="$t('sources.empty.createFirst')"
              >
                <v-btn v-if="canEdit" variant="tonal" color="primary" @click="openCreateDialog">
                  <v-icon start>mdi-plus</v-icon>
                  {{ $t('sources.actions.create') }}
                </v-btn>
              </EmptyState>
            </template>
          </v-data-table-server>
        </v-card>

        <!-- Create/Edit Dialog with Error Boundary (lazy-loaded) -->
        <ErrorBoundary v-if="formDialog && canEdit" @error="onDialogError" @reset="formDialog = false">
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
              <v-dialog :model-value="true" :max-width="DIALOG_SIZES.MD" persistent>
                <v-card class="d-flex align-center justify-center pa-8">
                  <v-progress-circular indeterminate color="primary" size="48" />
                </v-card>
              </v-dialog>
            </template>
          </Suspense>
        </ErrorBoundary>

        <!-- Bulk Import Dialog with Error Boundary (lazy-loaded) -->
        <ErrorBoundary v-if="bulkDialog && canAdmin" @error="onDialogError" @reset="bulkDialog = false">
          <Suspense>
            <SourcesBulkImportDialog
              v-model="bulkDialog"
              :categories="store.categories"
              :tag-suggestions="store.tagSuggestions"
              :existing-urls="existingUrls"
              @import="handleBulkImport"
            />
            <template #fallback>
              <v-dialog :model-value="true" :max-width="DIALOG_SIZES.LG" persistent>
                <v-card class="d-flex align-center justify-center pa-8">
                  <v-progress-circular indeterminate color="primary" size="48" />
                </v-card>
              </v-dialog>
            </template>
          </Suspense>
        </ErrorBoundary>

        <!-- Delete Dialog -->
        <SourcesDeleteDialog
          v-if="canAdmin"
          v-model="deleteDialog"
          :source="store.selectedSource"
          :deleting="deleting"
          @confirm="handleDeleteSource"
        />

        <!-- API Import Dialog with Error Boundary (lazy-loaded) -->
        <ErrorBoundary v-if="apiImportDialog && canEdit" @error="onDialogError" @reset="apiImportDialog = false">
          <Suspense>
            <ApiImportDialog
              v-model="apiImportDialog"
              :categories="store.categories"
              :available-tags="store.tagSuggestions"
              @imported="onApiImported"
            />
            <template #fallback>
              <v-dialog :model-value="true" :max-width="DIALOG_SIZES.XL" persistent>
                <v-card class="d-flex align-center justify-center pa-8">
                  <v-progress-circular indeterminate color="primary" size="48" />
                </v-card>
              </v-dialog>
            </template>
          </Suspense>
        </ErrorBoundary>

        <!-- AI Discovery Dialog with Error Boundary (lazy-loaded) -->
        <ErrorBoundary v-if="aiDiscoveryDialog && canEdit" @error="onDialogError" @reset="aiDiscoveryDialog = false">
          <Suspense>
            <AiDiscoveryDialog
              v-model="aiDiscoveryDialog"
              :categories="store.categories"
              @imported="onAiDiscoveryImported"
            />
            <template #fallback>
              <v-dialog :model-value="true" :max-width="DIALOG_SIZES.XXL" persistent>
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
import { ref, computed, onMounted, onUnmounted, defineAsyncComponent } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'
import { storeToRefs } from 'pinia'
import { useDebounceFn } from '@vueuse/core'
import { useSourcesStore } from '@/stores/sources'
import { useAuthStore } from '@/stores/auth'
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
import { PageHeader, ErrorBoundary, TableErrorState, EmptyState, PageInfoBox } from '@/components/common'
import { INFO_BOX_STORAGE_KEYS } from '@/config/infoBox'
import { extractErrorMessage } from '@/utils/errorMessage'
import { SEARCH, TABLE_HEADERS, ACTION_CLEANUP_DELAY } from '@/config/sources'
import type { BulkImportState, DataSourceResponse, SourceType, SourceStatus } from '@/types/sources'
import { useLogger } from '@/composables/useLogger'
import { usePageContextProvider, PAGE_FEATURES, PAGE_ACTIONS } from '@/composables/usePageContext'
import { onCrawlerEvent } from '@/composables/useCrawlerEvents'
import * as adminApi from '@/services/api/admin'
import type { PageContextData } from '@/composables/assistant/types'

const logger = useLogger('SourcesView')

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
const router = useRouter()
const auth = useAuthStore()

// =============================================================================
// Running Jobs State (for banner display)
// =============================================================================

interface RunningJobInfo {
  id: string
  source_name: string
  progress: number
}

const runningJobsCount = ref(0)
const runningJobs = ref<RunningJobInfo[]>([])
let runningJobsPollInterval: ReturnType<typeof setInterval> | null = null
const POLL_INTERVAL = 5000 // 5 seconds

const canEdit = computed(() => auth.isEditor)
const canAdmin = computed(() => auth.isAdmin)

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

// Page Context Provider for AI Assistant awareness
usePageContextProvider(
  '/sources',
  (): PageContextData => ({
    // Source context
    source_id: store.selectedSource?.id || undefined,
    source_type: store.selectedSource?.source_type || undefined,
    source_status: store.selectedSource?.status as 'active' | 'error' | 'disabled' | undefined,

    // List context
    total_count: store.sourcesTotal,
    filters: {
      search_query: store.filters.search || undefined
    },

    // Features and actions
    available_features: [...PAGE_FEATURES.source],
    available_actions: [
      ...PAGE_ACTIONS.base,
      'add_source', 'edit_source', 'test_connection'
    ]
  })
)

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
const onTableOptionsUpdate = (options: { page: number; itemsPerPage: number; sortBy: Array<{ key: string; order: 'asc' | 'desc' }> }) => {
  if (options.itemsPerPage !== store.itemsPerPage) {
    store.itemsPerPage = options.itemsPerPage
  }
  // Handle sorting changes
  if (JSON.stringify(options.sortBy) !== JSON.stringify(store.sortBy)) {
    store.sortBy = options.sortBy
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
  if (!canEdit.value) {
    showSnackbar(t('common.forbidden'), 'error')
    return
  }
  store.prepareCreateForm()
  formDialog.value = true
}

/**
 * Open edit source dialog
 */
const openEditDialog = async (source: DataSourceResponse) => {
  if (!canEdit.value) {
    showSnackbar(t('common.forbidden'), 'error')
    return
  }
  await store.prepareEditForm(source)
  formDialog.value = true
}

/**
 * Save source (create or update)
 */
const saveSource = async () => {
  if (!canEdit.value) {
    showSnackbar(t('common.forbidden'), 'error')
    return
  }
  try {
    await store.saveForm()
    formDialog.value = false
    showSnackbar(t('sources.messages.saved'), 'success')
  } catch (error) {
    logger.error('Failed to save source:', error)
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
  logger.error('[SourcesView] Dialog error', { error, info })
  showSnackbar(t('common.errorOccurred'), 'error')
}

/**
 * Confirm delete source
 */
const confirmDelete = (source: DataSourceResponse) => {
  if (!canAdmin.value) {
    showSnackbar(t('common.forbidden'), 'error')
    return
  }
  store.selectedSource = source
  deleteDialog.value = true
}

/**
 * Handle delete source
 */
const handleDeleteSource = async () => {
  if (!store.selectedSource) return
  if (!canAdmin.value) {
    showSnackbar(t('common.forbidden'), 'error')
    return
  }

  deleting.value = true
  try {
    await store.deleteSource(store.selectedSource.id)
    deleteDialog.value = false
    showSnackbar(t('sources.messages.deleted'), 'success')
  } catch (error) {
    logger.error('Failed to delete source:', error)
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
  if (!canEdit.value) {
    showSnackbar(t('common.forbidden'), 'error')
    return
  }
  actionLoading.value.starting[source.id] = true
  try {
    await store.startCrawl(source)
    showSnackbar(t('sources.messages.crawlStarted', { name: source.name }), 'success')
  } catch (error) {
    logger.error('Failed to start crawl:', error)
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
  if (!canEdit.value) {
    showSnackbar(t('common.forbidden'), 'error')
    return
  }
  actionLoading.value.resetting[source.id] = true
  try {
    await store.resetSource(source)
    showSnackbar(t('sources.messages.reset', { name: source.name }), 'success')
  } catch (error) {
    logger.error('Failed to reset source:', error)
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
  if (!canAdmin.value) {
    showSnackbar(t('common.forbidden'), 'error')
    return
  }
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
    logger.error('Bulk import failed:', error)
    showSnackbar(extractErrorMessage(error), 'error')
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
// Running Jobs Functions
// =============================================================================

/**
 * Fetch running jobs from API
 */
async function fetchRunningJobs(): Promise<void> {
  try {
    const [statusRes, runningRes] = await Promise.all([
      adminApi.getCrawlerStatus(),
      adminApi.getRunningJobs(),
    ])

    runningJobsCount.value = statusRes.data?.running_jobs ?? 0

    const jobs = runningRes.data?.jobs || []
    runningJobs.value = jobs.map((job: { id: string; source_name?: string; progress?: number }) => ({
      id: job.id,
      source_name: job.source_name || 'Unbekannt',
      progress: job.progress ?? 0,
    }))

    // Adjust polling based on activity
    updatePollingInterval()
  } catch (error) {
    logger.error('Failed to fetch running jobs:', error)
  }
}

/**
 * Update polling interval based on running jobs
 */
function updatePollingInterval(): void {
  if (runningJobsCount.value > 0 && !runningJobsPollInterval) {
    // Start polling when jobs are running
    runningJobsPollInterval = setInterval(fetchRunningJobs, POLL_INTERVAL)
  } else if (runningJobsCount.value === 0 && runningJobsPollInterval) {
    // Stop polling when no jobs running
    clearInterval(runningJobsPollInterval)
    runningJobsPollInterval = null
  }
}

/**
 * Navigate to crawler view
 */
function goToCrawler(): void {
  router.push('/crawler')
}

/**
 * Cleanup polling interval
 */
function cleanupPolling(): void {
  if (runningJobsPollInterval) {
    clearInterval(runningJobsPollInterval)
    runningJobsPollInterval = null
  }
}

// =============================================================================
// Lifecycle Hooks
// =============================================================================

// Subscribe to crawler events
const unsubscribeCrawlerEvents = onCrawlerEvent((event) => {
  if (event.type === 'crawl-started') {
    // Immediately fetch running jobs when a crawl is started
    fetchRunningJobs()
  }
})

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

  // Initialize store data and fetch running jobs in parallel for faster load
  await Promise.all([
    store.initialize(),
    fetchRunningJobs(),
  ])

  // Check for id query parameter to auto-select source (from DataFreshness widget)
  if (route.query.id) {
    const sourceId = route.query.id as string
    const source = store.sources.find((s: DataSourceResponse) => s.id === sourceId)
    if (source) {
      store.selectedSource = source
    }
  }
})

onUnmounted(() => {
  // Cleanup polling and event subscriptions
  cleanupPolling()
  unsubscribeCrawlerEvents()
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
