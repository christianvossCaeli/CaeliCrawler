<template>
  <div>
    <!-- Skeleton Loader for initial load -->
    <ResultsSkeleton v-if="loading && initialLoad" />

    <!-- Main Content -->
    <template v-else>
    <PageHeader
      :title="$t('results.title')"
      :subtitle="$t('results.subtitle')"
      icon="mdi-chart-box"
    >
      <template #actions>
        <!-- Bulk Actions -->
        <v-btn
          v-if="canVerify && selectedResults.length > 0"
          color="success"
          variant="outlined"
          prepend-icon="mdi-check-all"
          :loading="bulkVerifying"
          @click="bulkVerify"
        >
          {{ selectedResults.length }} {{ $t('results.actions.bulkVerify') }}
        </v-btn>
        <v-btn
          color="success"
          variant="outlined"
          prepend-icon="mdi-download"
          @click="exportCsv"
        >
          {{ $t('results.actions.csvExport') }}
        </v-btn>
        <v-btn
          color="primary"
          variant="outlined"
          prepend-icon="mdi-refresh"
          :loading="loading"
          @click="loadData"
        >
          {{ $t('results.actions.refresh') }}
        </v-btn>
      </template>
    </PageHeader>

    <!-- Statistics Bar -->
    <v-row class="mb-4">
      <v-col cols="6" sm="3">
        <v-card variant="outlined">
          <v-card-text class="text-center py-3">
            <div class="text-h5 text-primary">{{ stats.total }}</div>
            <div class="text-caption">{{ $t('results.stats.total') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="3">
        <v-card
          :variant="verifiedFilter === true ? 'elevated' : 'outlined'"
          :color="verifiedFilter === true ? 'success' : undefined"
          class="cursor-pointer"
          @click="toggleVerifiedFilter(true)"
        >
          <v-card-text class="text-center py-3">
            <div class="text-h5 text-success">{{ stats.verified }}</div>
            <div class="text-caption">{{ $t('results.stats.verified') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="3">
        <v-card variant="outlined">
          <v-card-text class="text-center py-3">
            <div class="text-h5 text-info">{{ stats.high_confidence_count }}</div>
            <div class="text-caption">{{ $t('results.stats.highConfidence') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="3">
        <v-card variant="outlined">
          <v-card-text class="text-center py-3">
            <div class="text-h5">{{ stats.avg_confidence ? (stats.avg_confidence * 100).toFixed(0) + '%' : '-' }}</div>
            <div class="text-caption">{{ $t('results.stats.avgConfidence') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row align="center">
          <v-col cols="12" md="3">
            <v-text-field
              v-model="searchQuery"
              prepend-inner-icon="mdi-magnify"
              :label="$t('results.filters.fulltext')"
              clearable
              hide-details
              :placeholder="$t('results.filters.fulltextPlaceholder')"
              @update:model-value="debouncedLoadData"
              @keyup.enter="loadData"
            />
          </v-col>
          <v-col v-if="showLocationFilter" cols="6" md="2">
            <v-autocomplete
              v-model="locationFilter"
              :items="locations"
              :label="$t('results.filters.location')"
              clearable
              hide-details
              @update:model-value="loadData"
            />
          </v-col>
          <v-col cols="6" md="2">
            <v-select
              v-model="extractionTypeFilter"
              :items="extractionTypes"
              :label="$t('results.filters.analysisType')"
              clearable
              hide-details
              @update:model-value="loadData"
            />
          </v-col>
          <v-col cols="6" md="2">
            <v-select
              v-model="categoryFilter"
              :items="categories"
              item-title="name"
              item-value="id"
              :label="$t('results.filters.category')"
              clearable
              hide-details
              @update:model-value="loadData"
            />
          </v-col>
          <v-col cols="6" md="3">
            <v-slider
              v-model="minConfidence"
              :min="0"
              :max="100"
              :step="5"
              :label="$t('results.filters.minConfidence')"
              thumb-label="always"
              hide-details
              @update:model-value="debouncedLoadData"
            >
              <template #thumb-label="{ modelValue }">{{ modelValue }}%</template>
            </v-slider>
          </v-col>
        </v-row>
        <v-row align="center" class="mt-2">
          <v-col cols="6" md="2">
            <v-text-field
              v-model="dateFrom"
              type="date"
              :label="$t('results.filters.dateFrom')"
              clearable
              hide-details
              @update:model-value="loadData"
            />
          </v-col>
          <v-col cols="6" md="2">
            <v-text-field
              v-model="dateTo"
              type="date"
              :label="$t('results.filters.dateTo')"
              clearable
              hide-details
              @update:model-value="loadData"
            />
          </v-col>
          <v-col cols="12" md="8" class="d-flex align-center">
            <v-btn v-if="hasActiveFilters" variant="tonal" color="primary" size="small" @click="clearFilters">
              <v-icon size="small" class="mr-1">mdi-filter-off</v-icon>
              {{ $t('results.filters.resetFilters') }}
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Results Table -->
    <v-card>
      <v-data-table-server
        v-model="selectedResults"
        v-model:items-per-page="perPage"
        v-model:page="page"
        v-model:sort-by="sortBy"
        :headers="headers"
        :items="results"
        :items-length="totalResults"
        :loading="loading"
        :show-select="canVerify"
        item-value="id"
        @update:options="onTableOptionsUpdate"
      >
        <template #item.document="{ item }">
          <div class="py-2">
            <div class="font-weight-medium text-truncate" style="max-width: 220px;" :title="(item.raw?.document_title || item.document_title) || (item.raw?.document_url || item.document_url)">
              {{ (item.raw?.document_title || item.document_title) || t('results.detail.noTitle') }}
            </div>
            <div class="text-caption text-medium-emphasis">
              <router-link :to="`/documents?search=${encodeURIComponent((item.raw?.document_title || item.document_title) || '')}`" class="text-decoration-none">
                <v-icon size="x-small" class="mr-1">mdi-file-document</v-icon>{{ $t('results.columns.document') }}
              </router-link>
            </div>
          </div>
        </template>

        <template #item.extraction_type="{ item }">
          <v-chip size="small" color="primary" variant="tonal">{{ item.raw?.extraction_type || item.extraction_type }}</v-chip>
        </template>

        <template #item.entity_count="{ item }">
          <v-menu location="bottom" :close-on-content-click="false">
            <template #activator="{ props }">
              <v-chip
                v-bind="props"
                size="small"
                :color="(item.raw?.entity_references || item.entity_references)?.length ? 'primary' : 'grey'"
                :variant="(item.raw?.entity_references || item.entity_references)?.length ? 'flat' : 'outlined'"
                class="cursor-pointer"
              >
                <v-icon start size="small">mdi-domain</v-icon>
                {{ (item.raw?.entity_references || item.entity_references)?.length || 0 }}
              </v-chip>
            </template>
            <v-card min-width="280" max-width="400">
              <v-card-title class="text-subtitle-2 py-2 d-flex align-center">
                <v-icon size="small" class="mr-2">mdi-domain</v-icon>
                {{ $t('results.detail.relevantEntities') }}
              </v-card-title>
              <v-divider />
              <v-card-text class="pa-2">
                <template v-if="(item.raw?.entity_references || item.entity_references)?.length">
                  <v-chip
                    v-for="(entityRef, idx) in (item.raw?.entity_references || item.entity_references)"
                    :key="idx"
                    :color="entityRef.entity_id ? getEntityTypeColor(entityRef.entity_type) : 'grey'"
                    size="small"
                    :variant="entityRef.entity_id ? 'elevated' : 'outlined'"
                    :to="entityRef.entity_id ? `/entity/${entityRef.entity_id}` : undefined"
                    class="ma-1"
                  >
                    <v-icon start size="x-small">{{ getEntityTypeIcon(entityRef.entity_type) }}</v-icon>
                    {{ entityRef.entity_name }}
                    <v-icon v-if="entityRef.entity_id" end size="x-small">mdi-open-in-new</v-icon>
                  </v-chip>
                </template>
                <div v-else class="text-medium-emphasis text-caption pa-2">
                  {{ $t('results.detail.noEntityReferences') }}
                </div>
              </v-card-text>
            </v-card>
          </v-menu>
        </template>

        <template #item.confidence_score="{ item }">
          <v-chip :color="getConfidenceColor(item.raw?.confidence_score ?? item.confidence_score)" size="small">
            {{ (item.raw?.confidence_score ?? item.confidence_score) != null ? (((item.raw?.confidence_score ?? item.confidence_score) as number) * 100).toFixed(0) + '%' : '-' }}
          </v-chip>
        </template>

        <template #item.human_verified="{ item }">
          <v-icon v-if="item.raw?.human_verified ?? item.human_verified" color="success" size="small">mdi-check-circle</v-icon>
          <v-icon v-else color="grey" size="small">mdi-circle-outline</v-icon>
        </template>

        <template #item.created_at="{ item }">
          <div class="text-caption">{{ formatDate(item.raw?.created_at || item.created_at) }}</div>
        </template>

        <template #item.actions="{ item }">
          <div class="table-actions d-flex justify-end ga-1">
            <v-btn icon="mdi-eye" size="small" variant="tonal" :title="$t('common.details')" :aria-label="$t('common.details')" @click="showDetails(item.raw || item)"></v-btn>
            <v-btn
              v-if="canVerify"
              :icon="(item.raw?.human_verified ?? item.human_verified) ? 'mdi-check-circle' : 'mdi-check'"
              size="small"
              variant="tonal"
              :color="(item.raw?.human_verified ?? item.human_verified) ? 'success' : 'grey'"
              :title="(item.raw?.human_verified ?? item.human_verified) ? $t('results.actions.verified') : $t('results.actions.verify')"
              :aria-label="(item.raw?.human_verified ?? item.human_verified) ? $t('results.actions.verified') : $t('results.actions.verify')"
              @click="verifyResult(item.raw || item)"
            ></v-btn>
            <v-btn icon="mdi-file-document" size="small" variant="tonal" color="info" :title="$t('results.actions.goToDocument')" :aria-label="$t('results.actions.goToDocument')" :to="`/documents?search=${encodeURIComponent((item.raw?.document_title || item.document_title) || '')}`"></v-btn>
            <v-btn icon="mdi-code-json" size="small" variant="tonal" :title="$t('results.actions.exportJson')" :aria-label="$t('results.actions.exportJson')" @click="exportJson(item.raw || item)"></v-btn>
          </div>
        </template>
      </v-data-table-server>
    </v-card>

    <!-- Details Dialog -->
    <v-dialog v-model="detailsDialog" max-width="950" scrollable>
      <v-card v-if="selectedResult">
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">mdi-brain</v-icon>
          {{ $t('results.detail.title') }}
          <v-spacer />
          <v-chip :color="getConfidenceColor(selectedResult.confidence_score)" class="mr-2">
            {{ selectedResult.confidence_score ? (selectedResult.confidence_score * 100).toFixed(0) + '%' : '-' }}
          </v-chip>
          <v-chip v-if="selectedResult.human_verified" color="success">
            <v-icon size="small" class="mr-1">mdi-check</v-icon>{{ $t('results.columns.verified') }}
          </v-chip>
        </v-card-title>

        <v-divider />
        <v-card-text class="pa-4" style="max-height: 70vh; overflow-y: auto;">
          <!-- Document Info -->
          <v-card variant="outlined" class="mb-4">
            <v-card-title class="text-subtitle-1 d-flex align-center">
              <v-icon size="small" class="mr-2">mdi-file-document</v-icon>
              {{ $t('results.detail.sourceDocument') }}
              <v-spacer />
              <v-btn size="small" variant="tonal" color="primary" :to="`/documents?search=${encodeURIComponent(selectedResult.document_title || '')}`">
                <v-icon size="small" class="mr-1">mdi-open-in-new</v-icon>{{ $t('results.detail.goToDocument') }}
              </v-btn>
            </v-card-title>
            <v-card-text>
              <div><strong>{{ $t('results.detail.title') }}:</strong> {{ selectedResult.document_title || t('results.detail.noTitle') }}</div>
              <div v-if="selectedResult.document_url"><strong>{{ $t('results.detail.url') }}:</strong> <a :href="selectedResult.document_url" target="_blank">{{ selectedResult.document_url }}</a></div>
              <div><strong>{{ $t('results.detail.source') }}:</strong> {{ selectedResult.source_name || '-' }}</div>
            </v-card-text>
          </v-card>

          <!-- Entity References (Prominent Display) -->
          <v-card variant="tonal" class="mb-4 entity-references-card" :color="selectedResult.entity_references?.length ? 'primary' : 'grey'">
            <v-card-title class="text-subtitle-1 d-flex align-center">
              <v-icon size="small" class="mr-2">mdi-domain</v-icon>
              {{ $t('results.detail.relevantEntities') }}
              <v-chip v-if="selectedResult.entity_references?.length" size="x-small" class="ml-2" color="primary" variant="flat">
                {{ selectedResult.entity_references.length }}
              </v-chip>
            </v-card-title>
            <v-card-text>
              <template v-if="selectedResult.entity_references?.length">
                <div class="d-flex flex-wrap ga-2">
                  <v-chip
                    v-for="(entityRef, idx) in selectedResult.entity_references"
                    :key="idx"
                    :color="entityRef.entity_id ? getEntityTypeColor(entityRef.entity_type) : 'grey'"
                    size="large"
                    :variant="entityRef.entity_id ? 'elevated' : 'outlined'"
                    :to="entityRef.entity_id ? `/entity/${entityRef.entity_id}` : undefined"
                    :class="['entity-chip', { 'entity-chip--clickable': entityRef.entity_id, 'entity-chip--unlinked': !entityRef.entity_id }]"
                  >
                    <v-icon start size="small">{{ getEntityTypeIcon(entityRef.entity_type) }}</v-icon>
                    <span class="font-weight-medium">{{ entityRef.entity_name }}</span>
                    <v-chip v-if="entityRef.role === 'primary'" size="x-small" class="ml-1" color="warning" variant="flat">
                      {{ $t('results.detail.primary') }}
                    </v-chip>
                    <v-icon v-if="entityRef.entity_id" end size="x-small" class="ml-1">mdi-open-in-new</v-icon>
                    <v-icon v-else end size="x-small" class="ml-1" color="warning">mdi-link-off</v-icon>
                    <v-tooltip activator="parent" location="top">
                      <div><strong>{{ $t('results.detail.entityType') }}:</strong> {{ entityRef.entity_type }}</div>
                      <div><strong>{{ $t('results.detail.role') }}:</strong> {{ entityRef.role }}</div>
                      <div><strong>{{ $t('results.detail.confidence') }}:</strong> {{ Math.round((entityRef.confidence ?? 0) * 100) }}%</div>
                      <div v-if="entityRef.entity_id" class="text-info">{{ $t('results.detail.clickToView') }}</div>
                      <div v-else class="text-warning">{{ $t('results.detail.notLinked') }}</div>
                    </v-tooltip>
                  </v-chip>
                </div>
              </template>
              <template v-else>
                <div class="text-medium-emphasis d-flex align-center">
                  <v-icon size="small" class="mr-2">mdi-information-outline</v-icon>
                  {{ $t('results.detail.noEntityReferences') }}
                </div>
              </template>
            </v-card-text>
          </v-card>

          <!-- Extracted Content -->
          <template v-if="selectedResult.final_content || selectedResult.extracted_content">

            <v-row class="mb-4">
              <v-col cols="12">
                <v-card variant="outlined" height="100%">
                  <v-card-title class="text-subtitle-1"><v-icon size="small" class="mr-2">mdi-check-circle</v-icon>{{ $t('results.detail.relevance') }}</v-card-title>
                  <v-card-text>
                    <v-chip :color="getContent(selectedResult).is_relevant ? 'success' : 'grey'">
                      {{ getContent(selectedResult).is_relevant ? t('results.detail.relevant') : t('results.detail.notRelevant') }}
                    </v-chip>
                    <span v-if="getContent(selectedResult).relevanz" class="ml-2 text-caption">{{ $t('results.detail.level') }}: {{ getContent(selectedResult).relevanz }}</span>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>

            <!-- Summary -->
            <v-card v-if="getContent(selectedResult).summary" variant="outlined" class="mb-4">
              <v-card-title class="text-subtitle-1"><v-icon size="small" class="mr-2">mdi-text</v-icon>{{ $t('results.detail.summary') }}</v-card-title>
              <v-card-text>{{ getContent(selectedResult).summary }}</v-card-text>
            </v-card>

            <!-- Generic FacetType Display -->
            <!-- If a category is selected, use FacetTypes from that category -->
            <template v-if="facetTypes.length > 0">
              <GenericFacetCard
                v-for="facetType in facetTypes"
                :key="facetType.slug"
                :facet-type="facetType"
                :values="getValuesForFacetType(getContent(selectedResult), facetType)"
              />
            </template>

            <!-- Fallback: Show all dynamic fields if no category-specific FacetTypes are loaded -->
            <template v-else>
              <!-- Dynamic Content Fields -->
              <v-card
                v-for="field in getDynamicContentFields(getContent(selectedResult))"
                :key="field.key"
                variant="flat"
                class="mb-4"
              >
                <v-card-title class="text-subtitle-1 d-flex align-center pa-4 pb-2">
                  <v-icon size="small" :color="field.color" class="mr-2">{{ field.icon }}</v-icon>
                  <span class="text-medium-emphasis">{{ field.label }}</span>
                  <v-chip size="x-small" variant="tonal" :color="field.color" class="ml-2">
                    {{ field.values.length }}
                  </v-chip>
                </v-card-title>
                <v-card-text class="pt-0">
                  <!-- Chip-based display (for entity references, contacts) -->
                  <template v-if="field.displayType === 'chips'">
                    <div class="d-flex flex-wrap ga-2">
                      <v-chip
                        v-for="(val, idx) in field.values"
                        :key="idx"
                        variant="tonal"
                        :color="field.color"
                        size="small"
                      >
                        <v-avatar start :color="field.color" size="20">
                          <v-icon size="x-small">mdi-account</v-icon>
                        </v-avatar>
                        {{ getValueText(val) }}
                      </v-chip>
                    </div>
                  </template>
                  <!-- List-based display (default for other fields) -->
                  <template v-else>
                    <div class="d-flex flex-column">
                      <div
                        v-for="(val, idx) in field.values"
                        :key="idx"
                        class="field-item d-flex align-start px-3 py-3"
                      >
                        <div
                          class="field-indicator mr-3"
                          :style="{ backgroundColor: `rgb(var(--v-theme-${field.color}))` }"
                        ></div>
                        <div class="flex-grow-1">
                          <div class="text-body-2">{{ getValueText(val) }}</div>
                          <!-- Show additional chips for structured data -->
                          <div v-if="typeof val === 'object'" class="d-flex flex-wrap ga-1 mt-2">
                            <template v-for="(propVal, propKey) in (val as Record<string, unknown>)" :key="propKey">
                              <v-chip
                                v-if="propVal && propKey !== 'description' && propKey !== 'text' && propKey !== 'aenderungen' && typeof propVal !== 'object'"
                                size="x-small"
                                variant="tonal"
                                color="grey"
                              >
                                {{ propKey }}: {{ propVal }}
                              </v-chip>
                            </template>
                          </div>
                        </div>
                      </div>
                    </div>
                  </template>
                </v-card-text>
              </v-card>
            </template>

            <!-- Outreach Recommendation -->
            <v-card v-if="getContent(selectedResult).outreach_recommendation" variant="outlined" class="mb-4" color="info">
              <v-card-title class="text-subtitle-1"><v-icon size="small" class="mr-2">mdi-bullhorn</v-icon>{{ $t('results.detail.outreachRecommendation') }}</v-card-title>
              <v-card-text>
                <div v-if="getContent(selectedResult).outreach_recommendation?.priority">
                  <strong>{{ $t('results.detail.priority') }}:</strong>
                  <v-chip :color="getPriorityColor(getContent(selectedResult).outreach_recommendation?.priority ?? '')" size="small" class="ml-2">
                    {{ getContent(selectedResult).outreach_recommendation?.priority }}
                  </v-chip>
                </div>
                <div v-if="getContent(selectedResult).outreach_recommendation?.reason" class="mt-2">
                  <strong>{{ $t('results.detail.reason') }}:</strong> {{ getContent(selectedResult).outreach_recommendation?.reason }}
                </div>
              </v-card-text>
            </v-card>
          </template>

          <!-- Raw JSON -->
          <v-expansion-panels class="mb-4">
            <v-expansion-panel>
              <v-expansion-panel-title><v-icon size="small" class="mr-2">mdi-code-json</v-icon>{{ $t('results.detail.rawData') }}</v-expansion-panel-title>
              <v-expansion-panel-text>
                <pre class="json-viewer pa-3 rounded">{{ JSON.stringify(getContent(selectedResult), null, 2) }}</pre>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>

          <!-- AI Metadata -->
          <v-card variant="outlined">
            <v-card-title class="text-subtitle-1"><v-icon size="small" class="mr-2">mdi-robot</v-icon>{{ $t('results.detail.aiMetadata') }}</v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="6"><div><strong>{{ $t('results.columns.type') }}:</strong> {{ selectedResult.extraction_type }}</div></v-col>
                <v-col cols="6"><div><strong>{{ $t('results.detail.model') }}:</strong> {{ selectedResult.ai_model_used || '-' }}</div></v-col>
                <v-col cols="6"><div><strong>{{ $t('results.columns.created') }}:</strong> {{ formatDate(selectedResult.created_at) }}</div></v-col>
                <v-col cols="6"><div><strong>{{ $t('results.detail.tokens') }}:</strong> {{ selectedResult.tokens_used || '-' }}</div></v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-card-text>
        <v-divider />
        <v-card-actions>
          <v-btn color="primary" variant="outlined" prepend-icon="mdi-code-json" @click="exportJson(selectedResult)">{{ $t('results.actions.exportJson') }}</v-btn>
          <v-spacer />
          <v-btn v-if="canVerify && !selectedResult.human_verified" variant="tonal" color="success" prepend-icon="mdi-check" @click="verifyResult(selectedResult); detailsDialog = false">{{ $t('results.actions.verify') }}</v-btn>
          <v-btn variant="tonal" @click="detailsDialog = false">{{ $t('common.close') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * ResultsView - Extracted Data Results
 *
 * Displays extracted data from documents with filtering, sorting, and export capabilities.
 * Uses useResultsView composable for all state and logic.
 */
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useResultsView } from '@/composables/useResultsView'
import PageHeader from '@/components/common/PageHeader.vue'
import ResultsSkeleton from '@/components/results/ResultsSkeleton.vue'
import { GenericFacetCard } from '@/components/facets'

const { t } = useI18n()

// Initialize composable with all state and methods
const {
  // State
  loading,
  initialLoad,
  bulkVerifying,
  results,
  totalResults,
  locations,
  categories,
  extractionTypes,
  selectedResults,
  stats,
  facetTypes,

  // Filters
  searchQuery,
  locationFilter,
  extractionTypeFilter,
  categoryFilter,
  minConfidence,
  verifiedFilter,
  dateFrom,
  dateTo,

  // Pagination
  page,
  perPage,
  sortBy,

  // Dialog
  detailsDialog,
  selectedResult,

  // Headers
  headers,

  // Computed
  showLocationFilter,
  hasActiveFilters,
  canVerify,

  // Helper Functions
  getConfidenceColor,
  getPriorityColor,
  getEntityTypeColor,
  getEntityTypeIcon,
  getContent,
  formatDate,

  // Data Loading
  loadData,
  debouncedLoadData,

  // FacetType Helpers
  getValuesForFacetType,

  // Dynamic Content Helpers
  getDynamicContentFields,
  getValueText,

  // Filter Actions
  toggleVerifiedFilter,
  clearFilters,
  onTableOptionsUpdate,

  // Result Actions
  showDetails,
  verifyResult,
  bulkVerify,

  // Export Actions
  exportJson,
  exportCsv,

  // Initialization
  initialize,
} = useResultsView()

// Initialize on mount
onMounted(() => initialize())
</script>

<style scoped>
/* Generic entity reference cell styling */
.entity-ref-text {
  font-size: 0.8125rem;
  line-height: 1.3;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  word-break: break-word;
}

.entity-ref-text:hover {
  text-decoration: underline;
  color: rgb(var(--v-theme-info-darken-1));
}

.entity-references {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

/* JSON Viewer - Dark Mode optimized */
.json-viewer {
  overflow-x: auto;
  font-size: 0.75rem;
  max-height: 400px;
  white-space: pre-wrap;
  font-family: 'Fira Code', 'Consolas', 'Monaco', monospace;
  background-color: #1a2f2e;
  color: #b8d4ce;
  border: 1px solid #2a4544;
  border-radius: 8px;
}

/* Light mode override */
:deep(.v-theme--caeliLight) .json-viewer {
  background-color: #f5f5f5;
  color: #333;
  border-color: #e0e0e0;
}

/* Pain Points Card */
.pain-points-card {
  background: rgba(var(--v-theme-warning), 0.04);
  border: 1px solid rgba(var(--v-theme-warning), 0.15);
  border-left: 3px solid rgb(var(--v-theme-warning));
}

.pain-point-item {
  background: rgba(var(--v-theme-warning), 0.08);
  border: 1px solid rgba(var(--v-theme-warning), 0.2);
  border-radius: 8px;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.pain-point-item:hover {
  background: rgba(var(--v-theme-warning), 0.12);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.pain-point-item:not(:last-child) {
  margin-bottom: 8px;
}

.pain-point-indicator {
  width: 4px;
  height: 100%;
  min-height: 24px;
  background: rgb(var(--v-theme-warning));
  border-radius: 2px;
  flex-shrink: 0;
}

/* Positive Signals Card */
.positive-signals-card {
  background: rgba(var(--v-theme-success), 0.04);
  border: 1px solid rgba(var(--v-theme-success), 0.15);
  border-left: 3px solid rgb(var(--v-theme-success));
}

.positive-signal-item {
  background: rgba(var(--v-theme-success), 0.08);
  border: 1px solid rgba(var(--v-theme-success), 0.2);
  border-radius: 8px;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.positive-signal-item:hover {
  background: rgba(var(--v-theme-success), 0.12);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.positive-signal-item:not(:last-child) {
  margin-bottom: 8px;
}

.positive-signal-indicator {
  width: 4px;
  height: 100%;
  min-height: 24px;
  background: rgb(var(--v-theme-success));
  border-radius: 2px;
  flex-shrink: 0;
}

/* Decision Makers Card */
.decision-makers-card {
  background: rgba(var(--v-theme-info), 0.04);
  border: 1px solid rgba(var(--v-theme-info), 0.15);
  border-left: 3px solid rgb(var(--v-theme-info));
}

/* Generic Field Item (for dynamic fields) */
.field-item {
  background: rgba(var(--v-theme-on-surface), 0.04);
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 8px;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.field-item:hover {
  background: rgba(var(--v-theme-on-surface), 0.08);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.field-item:not(:last-child) {
  margin-bottom: 8px;
}

.field-indicator {
  width: 4px;
  height: 100%;
  min-height: 24px;
  border-radius: 2px;
  flex-shrink: 0;
}

/* Entity References Card */
.entity-references-card {
  border-left: 4px solid rgb(var(--v-theme-primary));
}

/* Entity Chips */
.entity-chip {
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.entity-chip--clickable {
  cursor: pointer;
}

.entity-chip--clickable:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.entity-chip--unlinked {
  opacity: 0.75;
  border-style: dashed;
}
</style>
