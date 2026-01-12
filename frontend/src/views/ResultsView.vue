<template>
  <div>
    <!-- Skeleton/Content Transition -->
    <transition name="fade" mode="out-in">
      <!-- Skeleton Loader for initial load -->
      <ResultsSkeleton v-if="state.loading.value && state.initialLoad.value" key="skeleton" />

      <!-- Main Content -->
      <div v-else key="content">
        <!-- Page Header -->
        <PageHeader
          :title="$t('results.title')"
          :subtitle="$t('results.subtitle')"
          icon="mdi-chart-box"
        >
          <template #actions>
            <!-- CSV Export Button -->
            <v-btn
              color="info"
              variant="outlined"
              prepend-icon="mdi-download"
              :loading="state.exporting.value"
              @click="actions.exportCsv"
            >
              {{ state.selectedResults.value.length > 0
                ? $t('results.actions.csvExportSelected', { count: state.selectedResults.value.length })
                : $t('results.actions.csvExport') }}
            </v-btn>

            <!-- Refresh Button -->
            <v-btn
              color="primary"
              variant="outlined"
              prepend-icon="mdi-refresh"
              :loading="state.loading.value"
              @click="filters.loadData"
            >
              {{ $t('results.actions.refresh') }}
            </v-btn>
          </template>
        </PageHeader>

        <!-- Info Box -->
        <PageInfoBox :storage-key="INFO_BOX_STORAGE_KEYS.RESULTS" :title="$t('results.info.title')">
          {{ $t('results.info.description') }}
        </PageInfoBox>

        <!-- Statistics Bar -->
        <ResultsStatsBar
          :stats="state.stats.value"
          :verified-filter="state.verifiedFilter.value"
          @toggle-verified="filters.toggleVerifiedFilter"
        />

        <!-- Filters -->
        <ResultsFilters
          :search-query="state.searchQuery.value"
          :location-filter="state.locationFilter.value"
          :extraction-type-filter="state.extractionTypeFilter.value"
          :category-filter="state.categoryFilter.value"
          :confidence-range="state.confidenceRange.value"
          :date-from="state.dateFrom.value"
          :date-to="state.dateTo.value"
          :show-rejected="state.showRejected.value"
          :locations="state.locations.value"
          :categories="state.categories.value"
          :extraction-types="state.extractionTypes.value"
          :show-location-filter="state.showLocationFilter.value"
          :has-active-filters="state.hasActiveFilters.value"
          @update:search-query="handleFilterUpdate('searchQuery', $event)"
          @update:location-filter="handleFilterUpdate('locationFilter', $event)"
          @update:extraction-type-filter="handleFilterUpdate('extractionTypeFilter', $event)"
          @update:category-filter="handleFilterUpdate('categoryFilter', $event)"
          @update:confidence-range="handleFilterUpdate('confidenceRange', $event)"
          @update:date-from="handleFilterUpdate('dateFrom', $event)"
          @update:date-to="handleFilterUpdate('dateTo', $event)"
          @update:show-rejected="handleFilterUpdate('showRejected', $event)"
          @search="filters.loadData"
          @clear-filters="filters.clearFilters"
        />

        <!-- Bulk Actions Toolbar -->
        <ResultsBulkActions
          :selected-results="state.selectedResults.value"
          :can-verify="state.canVerify.value"
          :bulk-verifying="state.bulkVerifying.value"
          :bulk-rejecting="state.bulkRejecting.value"
          @bulk-verify="actions.bulkVerify"
          @bulk-reject="initiateBulkReject"
          @clear="clearSelection"
        />

        <!-- Results Table -->
        <ResultsTable
          :results="state.results.value"
          :total-results="state.totalResults.value"
          :loading="state.loading.value"
          :can-verify="state.canVerify.value"
          :headers="state.headers.value"
          :selected-results="state.selectedResults.value"
          :page="state.page.value"
          :per-page="state.perPage.value"
          :sort-by="state.sortBy.value"
          @update:selected-results="state.selectedResults.value = $event"
          @update:page="state.page.value = $event"
          @update:per-page="state.perPage.value = $event"
          @update:sort-by="state.sortBy.value = $event"
          @options-update="filters.onTableOptionsUpdate"
          @show-details="actions.showDetails"
          @verify="actions.verifyResult"
          @reject="initiateReject"
          @unreject="actions.unrejectResult"
          @export-json="actions.exportJson"
        />

        <!-- Details Dialog -->
        <ResultDetailDialog
          v-model="state.detailsDialog.value"
          :result="state.selectedResult.value"
          :can-verify="state.canVerify.value"
          :facet-types="state.facetTypes.value"
          @verify="handleVerifyFromDialog"
          @export-json="actions.exportJson"
        />

        <!-- Reject Confirmation Dialog -->
        <v-dialog v-model="confirmRejectDialog" max-width="500" persistent>
          <v-card>
            <v-card-title class="d-flex align-center">
              <v-icon color="error" class="mr-2">mdi-alert-circle</v-icon>
              {{ $t('results.dialogs.rejectTitle') }}
            </v-card-title>
            <v-card-text>
              <p class="mb-3">{{ $t('results.dialogs.rejectMessage') }}</p>
              <v-alert type="info" variant="tonal" density="compact" class="mb-3">
                <v-icon start size="small">mdi-shield-check</v-icon>
                {{ $t('results.dialogs.rejectWarning') }}
              </v-alert>
              <v-alert type="warning" variant="tonal" density="compact">
                <v-icon start size="small">mdi-information</v-icon>
                {{ $t('results.dialogs.unrejectNote') }}
              </v-alert>
            </v-card-text>
            <v-card-actions>
              <v-spacer />
              <v-btn variant="text" @click="cancelReject">
                {{ $t('common.cancel') }}
              </v-btn>
              <v-btn color="error" variant="flat" @click="confirmReject">
                <v-icon start>mdi-close-circle</v-icon>
                {{ $t('results.dialogs.confirmReject') }}
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-dialog>

        <!-- Bulk Reject Confirmation Dialog -->
        <v-dialog v-model="confirmBulkRejectDialog" max-width="500" persistent>
          <v-card>
            <v-card-title class="d-flex align-center">
              <v-icon color="error" class="mr-2">mdi-alert-circle</v-icon>
              {{ $t('results.dialogs.bulkRejectTitle') }}
            </v-card-title>
            <v-card-text>
              <p class="mb-3">
                {{ $t('results.dialogs.bulkRejectMessage', { count: state.selectedResults.value.length }) }}
              </p>
              <v-alert type="info" variant="tonal" density="compact" class="mb-3">
                <v-icon start size="small">mdi-shield-check</v-icon>
                {{ $t('results.dialogs.rejectWarning') }}
              </v-alert>
              <v-alert type="warning" variant="tonal" density="compact">
                <v-icon start size="small">mdi-information</v-icon>
                {{ $t('results.dialogs.unrejectNote') }}
              </v-alert>
            </v-card-text>
            <v-card-actions>
              <v-spacer />
              <v-btn variant="text" @click="cancelBulkReject">
                {{ $t('common.cancel') }}
              </v-btn>
              <v-btn color="error" variant="flat" @click="confirmBulkReject">
                <v-icon start>mdi-close-circle-multiple</v-icon>
                {{ $t('results.dialogs.confirmBulkReject') }}
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-dialog>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
/**
 * ResultsView - Extracted Data Results
 *
 * Displays extracted data from documents with filtering, sorting, and export capabilities.
 * Refactored to use modular sub-components and composables.
 */
import { onMounted, ref } from 'vue'
import { useResults, type SearchResult } from '@/composables/results'
import PageHeader from '@/components/common/PageHeader.vue'
import PageInfoBox from '@/components/common/PageInfoBox.vue'
import { INFO_BOX_STORAGE_KEYS } from '@/config/infoBox'
import {
  ResultsSkeleton,
  ResultsStatsBar,
  ResultsFilters,
  ResultsTable,
  ResultDetailDialog,
  ResultsBulkActions,
} from '@/components/results'
import { usePageContextProvider, PAGE_ACTIONS } from '@/composables/usePageContext'
import type { PageContextData } from '@/composables/assistant/types'

// Initialize composable
const { state, filters, actions } = useResults()

// =============================================================================
// Reject Confirmation Dialog State
// =============================================================================

const confirmRejectDialog = ref(false)
const pendingRejectItem = ref<SearchResult | null>(null)
const confirmBulkRejectDialog = ref(false)

/**
 * Initiate reject by showing confirmation dialog.
 */
function initiateReject(item: SearchResult): void {
  pendingRejectItem.value = item
  confirmRejectDialog.value = true
}

/**
 * Confirm and execute the reject action.
 */
function confirmReject(): void {
  if (pendingRejectItem.value) {
    actions.rejectResult(pendingRejectItem.value)
  }
  confirmRejectDialog.value = false
  pendingRejectItem.value = null
}

/**
 * Cancel the reject action.
 */
function cancelReject(): void {
  confirmRejectDialog.value = false
  pendingRejectItem.value = null
}

/**
 * Clear selected results.
 */
function clearSelection(): void {
  state.selectedResults.value = []
}

/**
 * Initiate bulk reject by showing confirmation dialog.
 */
function initiateBulkReject(): void {
  confirmBulkRejectDialog.value = true
}

/**
 * Confirm and execute the bulk reject action.
 */
function confirmBulkReject(): void {
  actions.bulkReject()
  confirmBulkRejectDialog.value = false
}

/**
 * Cancel the bulk reject action.
 */
function cancelBulkReject(): void {
  confirmBulkRejectDialog.value = false
}

// =============================================================================
// Filter Update Handlers
// =============================================================================

type FilterKey = 'searchQuery' | 'locationFilter' | 'extractionTypeFilter' |
                 'categoryFilter' | 'confidenceRange' | 'dateFrom' | 'dateTo' | 'showRejected'

function handleFilterUpdate(key: FilterKey, value: unknown): void {
  // Update the state value
  switch (key) {
    case 'searchQuery':
      state.searchQuery.value = value as string
      filters.debouncedLoadData()
      break
    case 'locationFilter':
      state.locationFilter.value = value as string | null
      filters.loadData()
      break
    case 'extractionTypeFilter':
      state.extractionTypeFilter.value = value as string | null
      filters.loadData()
      break
    case 'categoryFilter':
      state.categoryFilter.value = value as string | null
      filters.loadData()
      break
    case 'confidenceRange':
      state.confidenceRange.value = value as [number, number]
      filters.debouncedLoadData()
      break
    case 'dateFrom':
      state.dateFrom.value = value as string | null
      filters.loadData()
      break
    case 'dateTo':
      state.dateTo.value = value as string | null
      filters.loadData()
      break
    case 'showRejected':
      state.showRejected.value = value as boolean
      filters.loadData()
      break
  }
}

function handleVerifyFromDialog(item: SearchResult): void {
  actions.verifyResult(item)
  state.detailsDialog.value = false
}

// =============================================================================
// Page Context Provider (KI-Assistant awareness)
// =============================================================================

usePageContextProvider(
  '/results',
  (): PageContextData => ({
    current_route: '/results',
    view_mode: 'list',
    total_count: state.totalResults.value,
    selected_count: state.selectedResults.value.length,
    filters: {
      search_query: state.searchQuery.value || undefined,
      location_filter: state.locationFilter.value || undefined,
      extraction_type: state.extractionTypeFilter.value || undefined,
      category_id: state.categoryFilter.value || undefined,
      min_confidence: state.confidenceRange.value[0] || undefined,
      max_confidence: state.confidenceRange.value[1] < 100 ? state.confidenceRange.value[1] : undefined,
      verified_filter: state.verifiedFilter.value ?? undefined,
    },
    available_features: ['verify_result', 'bulk_verify', 'export', 'filter', 'search'],
    available_actions: [
      ...PAGE_ACTIONS.base,
      'verify',
      'bulk_verify',
      'export_json',
      'export_csv',
      'view_document',
    ],
  })
)

// =============================================================================
// Lifecycle
// =============================================================================

onMounted(() => filters.initialize())
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
