<template>
  <v-card>
    <v-data-table-server
      v-model="selectedResultsModel"
      v-model:items-per-page="perPageModel"
      v-model:page="pageModel"
      v-model:sort-by="sortByModel"
      :headers="headers"
      :items="results"
      :items-length="totalResults"
      :loading="loading"
      :show-select="canVerify"
      item-value="id"
      @update:options="handleOptionsUpdate"
    >
      <!-- Document Column -->
      <template #item.document="{ item }">
        <div class="py-2">
          <div class="font-weight-medium truncate-text" :title="getDocumentTitle(item)">
            {{ getDocumentTitle(item) || $t('results.detail.noTitle') }}
          </div>
          <div class="text-caption text-medium-emphasis">
            <router-link
              :to="`/documents?search=${encodeURIComponent(getDocumentTitle(item) || '')}`"
              class="text-decoration-none"
            >
              <v-icon size="x-small" class="mr-1">mdi-file-document</v-icon>
              {{ $t('results.columns.document') }}
            </router-link>
          </div>
        </div>
      </template>

      <!-- Extraction Type Column -->
      <template #item.extraction_type="{ item }">
        <v-chip size="small" color="primary" variant="tonal">
          {{ normalizeItem(item).extraction_type }}
        </v-chip>
      </template>

      <!-- Entity Count Column -->
      <template #item.entity_count="{ item }">
        <EntityReferencePopup :entity-references="normalizeItem(item).entity_references" />
      </template>

      <!-- Confidence Score Column -->
      <template #item.confidence_score="{ item }">
        <v-chip :color="getConfidenceColor(normalizeItem(item).confidence_score)" size="small">
          {{ formatConfidence(normalizeItem(item).confidence_score) }}
        </v-chip>
      </template>

      <!-- Human Verified Column -->
      <template #item.human_verified="{ item }">
        <v-icon
          v-if="normalizeItem(item).human_verified"
          color="success"
          size="small"
        >
          mdi-check-circle
        </v-icon>
        <v-icon v-else color="grey" size="small">mdi-circle-outline</v-icon>
      </template>

      <!-- Created At Column -->
      <template #item.created_at="{ item }">
        <div class="text-caption">{{ formatDate(normalizeItem(item).created_at) }}</div>
      </template>

      <!-- Actions Column -->
      <template #item.actions="{ item }">
        <div class="table-actions d-flex justify-end ga-1">
          <v-btn
            icon="mdi-eye"
            size="default"
            variant="tonal"
            :title="$t('common.details')"
            :aria-label="$t('common.details')"
            @click="$emit('show-details', normalizeItem(item))"
          />

          <v-btn
            v-if="canVerify"
            :icon="normalizeItem(item).human_verified ? 'mdi-check-circle' : 'mdi-check'"
            size="default"
            variant="tonal"
            :color="normalizeItem(item).human_verified ? 'success' : 'grey'"
            :title="normalizeItem(item).human_verified ? $t('results.actions.verified') : $t('results.actions.verify')"
            :aria-label="normalizeItem(item).human_verified ? $t('results.actions.verified') : $t('results.actions.verify')"
            @click="$emit('verify', normalizeItem(item))"
          />

          <v-btn
            icon="mdi-file-document"
            size="default"
            variant="tonal"
            color="info"
            :title="$t('results.actions.goToDocument')"
            :aria-label="$t('results.actions.goToDocument')"
            :to="`/documents?search=${encodeURIComponent(getDocumentTitle(item) || '')}`"
          />

          <v-btn
            icon="mdi-code-json"
            size="default"
            variant="tonal"
            :title="$t('results.actions.exportJson')"
            :aria-label="$t('results.actions.exportJson')"
            @click="$emit('export-json', normalizeItem(item))"
          />
        </div>
      </template>

      <!-- Empty / Error State -->
      <template #no-data>
        <TableErrorState
          v-if="props.error"
          :title="$t('common.loadError')"
          :message="props.errorMessage || $t('errors.generic')"
          :retrying="loading"
          @retry="emit('retry')"
        />
        <EmptyState
          v-else
          icon="mdi-chart-box-outline"
          :title="$t('results.emptyState.title', 'Keine Ergebnisse')"
          :description="$t('results.emptyState.description', 'Es wurden noch keine AI-Extraktionen gefunden.')"
        />
      </template>
    </v-data-table-server>
  </v-card>
</template>

<script setup lang="ts">
/**
 * ResultsTable - Data table for extracted results
 *
 * Server-side paginated table with selection, sorting, and actions.
 */
import { computed } from 'vue'
import EntityReferencePopup from './EntityReferencePopup.vue'
import { TableErrorState, EmptyState } from '@/components/common'
import {
  useResultsHelpers,
  normalizeResultItem,
  type SearchResult,
  type TableHeader,
  type TableOptions,
  type SortConfig,
} from '@/composables/results'

const props = defineProps<{
  results: SearchResult[]
  totalResults: number
  loading: boolean
  canVerify: boolean
  headers: TableHeader[]
  selectedResults: string[]
  page: number
  perPage: number
  sortBy: SortConfig[]
  /** Whether an error occurred during data loading */
  error?: boolean
  /** User-friendly error message */
  errorMessage?: string
}>()

const emit = defineEmits<{
  'update:selectedResults': [value: string[]]
  'update:page': [value: number]
  'update:perPage': [value: number]
  'update:sortBy': [value: SortConfig[]]
  'options-update': [options: TableOptions]
  'show-details': [item: SearchResult]
  'verify': [item: SearchResult]
  'export-json': [item: SearchResult]
  /** Emitted when user clicks retry after an error */
  'retry': []
}>()

const { getConfidenceColor, formatConfidence, formatDate } = useResultsHelpers()

// Two-way bindings for v-data-table-server
const selectedResultsModel = computed({
  get: () => props.selectedResults,
  set: (value) => emit('update:selectedResults', value),
})

const pageModel = computed({
  get: () => props.page,
  set: (value) => emit('update:page', value),
})

const perPageModel = computed({
  get: () => props.perPage,
  set: (value) => emit('update:perPage', value),
})

const sortByModel = computed({
  get: () => props.sortBy,
  set: (value) => emit('update:sortBy', value),
})

/**
 * Normalize item to handle raw wrapper from v-data-table.
 */
function normalizeItem(item: SearchResult | { raw?: SearchResult }): SearchResult {
  return normalizeResultItem(item)
}

/**
 * Get document title from normalized item.
 */
function getDocumentTitle(item: SearchResult | { raw?: SearchResult }): string {
  return normalizeItem(item).document_title || ''
}

/**
 * Handle table options update (pagination, sorting).
 */
function handleOptionsUpdate(options: TableOptions): void {
  emit('options-update', options)
}
</script>

<style scoped>
.truncate-text {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.table-actions {
  min-width: 160px;
}
</style>
