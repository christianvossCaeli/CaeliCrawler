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
            <!-- Bulk Verify Button -->
            <v-btn
              v-if="state.canVerify.value && state.selectedResults.value.length > 0"
              color="success"
              variant="outlined"
              prepend-icon="mdi-check-all"
              :loading="state.bulkVerifying.value"
              @click="actions.bulkVerify"
            >
              {{ state.selectedResults.value.length }} {{ $t('results.actions.bulkVerify') }}
            </v-btn>

            <!-- CSV Export Button -->
            <v-btn
              color="info"
              variant="outlined"
              prepend-icon="mdi-download"
              @click="actions.exportCsv"
            >
              {{ $t('results.actions.csvExport') }}
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
          :min-confidence="state.minConfidence.value"
          :date-from="state.dateFrom.value"
          :date-to="state.dateTo.value"
          :locations="state.locations.value"
          :categories="state.categories.value"
          :extraction-types="state.extractionTypes.value"
          :show-location-filter="state.showLocationFilter.value"
          :has-active-filters="state.hasActiveFilters.value"
          @update:search-query="handleFilterUpdate('searchQuery', $event)"
          @update:location-filter="handleFilterUpdate('locationFilter', $event)"
          @update:extraction-type-filter="handleFilterUpdate('extractionTypeFilter', $event)"
          @update:category-filter="handleFilterUpdate('categoryFilter', $event)"
          @update:min-confidence="handleFilterUpdate('minConfidence', $event)"
          @update:date-from="handleFilterUpdate('dateFrom', $event)"
          @update:date-to="handleFilterUpdate('dateTo', $event)"
          @search="filters.loadData"
          @clear-filters="filters.clearFilters"
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
import { onMounted } from 'vue'
import { useResults, type SearchResult } from '@/composables/results'
import PageHeader from '@/components/common/PageHeader.vue'
import {
  ResultsSkeleton,
  ResultsStatsBar,
  ResultsFilters,
  ResultsTable,
  ResultDetailDialog,
} from '@/components/results'
import { usePageContextProvider, PAGE_ACTIONS } from '@/composables/usePageContext'
import type { PageContextData } from '@/composables/assistant/types'

// Initialize composable
const { state, filters, actions } = useResults()

// =============================================================================
// Filter Update Handlers
// =============================================================================

type FilterKey = 'searchQuery' | 'locationFilter' | 'extractionTypeFilter' |
                 'categoryFilter' | 'minConfidence' | 'dateFrom' | 'dateTo'

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
    case 'minConfidence':
      state.minConfidence.value = value as number
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
      min_confidence: state.minConfidence.value || undefined,
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
