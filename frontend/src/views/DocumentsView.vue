<template>
  <div>
    <!-- Skeleton Loader for initial load -->
    <DocumentsSkeleton v-if="loading && initialLoad" />

    <!-- Main Content -->
    <template v-else>
    <PageHeader
      :title="$t('documents.title')"
      :subtitle="$t('documents.subtitle')"
      icon="mdi-file-document-multiple"
    >
      <template #actions>
        <!-- Bulk Actions -->
        <v-btn
          v-if="selectedDocuments.length > 0"
          color="primary"
          variant="outlined"
          prepend-icon="mdi-play"
          :loading="bulkProcessing"
          @click="bulkProcess"
        >
          {{ selectedDocuments.length }} {{ $t('documents.bulkActions.processSelected') }}
        </v-btn>
        <v-btn
          v-if="selectedDocuments.length > 0"
          color="info"
          variant="outlined"
          prepend-icon="mdi-brain"
          :loading="bulkAnalyzing"
          @click="bulkAnalyze"
        >
          {{ selectedDocuments.length }} {{ $t('documents.bulkActions.analyzeSelected') }}
        </v-btn>
        <v-btn
          v-if="stats.processing > 0"
          color="error"
          variant="outlined"
          prepend-icon="mdi-stop"
          :loading="stoppingAll"
          @click="stopAllProcessing"
        >
          {{ $t('documents.actions.stop') }}
        </v-btn>
        <v-btn
          v-if="stats.pending > 0 && selectedDocuments.length === 0"
          color="primary"
          prepend-icon="mdi-play"
          :loading="processingAll"
          @click="processAllPending"
        >
          {{ $t('documents.actions.processAll') }} ({{ stats.pending }})
        </v-btn>
        <v-btn
          color="success"
          variant="outlined"
          prepend-icon="mdi-download"
          @click="exportCsv"
        >
          {{ $t('documents.actions.exportCsv') }}
        </v-btn>
      </template>
    </PageHeader>

    <!-- Statistics Bar -->
    <v-row class="mb-4">
      <v-col cols="6" sm="4" md="2">
        <v-card
          :color="statusFilter === 'PENDING' ? 'warning' : undefined"
          :variant="statusFilter === 'PENDING' ? 'elevated' : 'outlined'"
          class="cursor-pointer"
          @click="toggleStatusFilter('PENDING')"
        >
          <v-card-text class="text-center py-3">
            <div class="text-h5">{{ stats.pending }}</div>
            <div class="text-caption">{{ $t('documents.stats.pending') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="4" md="2">
        <v-card
          :color="statusFilter === 'PROCESSING' ? 'info' : undefined"
          :variant="statusFilter === 'PROCESSING' ? 'elevated' : 'outlined'"
          class="cursor-pointer"
          @click="toggleStatusFilter('PROCESSING')"
        >
          <v-card-text class="text-center py-3">
            <div class="text-h5">
              <v-icon v-if="stats.processing > 0" class="mdi-spin mr-1" size="small">mdi-loading</v-icon>
              {{ stats.processing }}
            </div>
            <div class="text-caption">{{ $t('documents.stats.processing') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="4" md="2">
        <v-card
          :color="statusFilter === 'ANALYZING' ? 'purple' : undefined"
          :variant="statusFilter === 'ANALYZING' ? 'elevated' : 'outlined'"
          class="cursor-pointer"
          @click="toggleStatusFilter('ANALYZING')"
        >
          <v-card-text class="text-center py-3">
            <div class="text-h5">
              <v-icon v-if="stats.analyzing > 0" class="mdi-spin mr-1" size="small">mdi-brain</v-icon>
              {{ stats.analyzing }}
            </div>
            <div class="text-caption">{{ $t('documents.stats.analyzing') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="4" md="2">
        <v-card
          :color="statusFilter === 'COMPLETED' ? 'success' : undefined"
          :variant="statusFilter === 'COMPLETED' ? 'elevated' : 'outlined'"
          class="cursor-pointer"
          @click="toggleStatusFilter('COMPLETED')"
        >
          <v-card-text class="text-center py-3">
            <div class="text-h5">{{ stats.completed }}</div>
            <div class="text-caption">{{ $t('documents.stats.completed') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="4" md="2">
        <v-card
          :color="statusFilter === 'FILTERED' ? 'grey' : undefined"
          :variant="statusFilter === 'FILTERED' ? 'elevated' : 'outlined'"
          class="cursor-pointer"
          @click="toggleStatusFilter('FILTERED')"
        >
          <v-card-text class="text-center py-3">
            <div class="text-h5">{{ stats.filtered }}</div>
            <div class="text-caption">{{ $t('documents.stats.filtered') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="4" md="2">
        <v-card
          :color="statusFilter === 'FAILED' ? 'error' : undefined"
          :variant="statusFilter === 'FAILED' ? 'elevated' : 'outlined'"
          class="cursor-pointer"
          @click="toggleStatusFilter('FAILED')"
        >
          <v-card-text class="text-center py-3">
            <div class="text-h5">{{ stats.failed }}</div>
            <div class="text-caption">{{ $t('documents.stats.failed') }}</div>
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
              :label="$t('documents.filters.search')"
              clearable
              hide-details
              @update:model-value="debouncedLoadData"
              @keyup.enter="loadData"
            />
          </v-col>
          <v-col cols="12" md="2">
            <v-autocomplete
              v-model="locationFilter"
              :items="locations"
              :label="$t('documents.filters.location')"
              clearable
              hide-details
              @update:model-value="loadData"
            />
          </v-col>
          <v-col cols="6" md="1">
            <v-select
              v-model="typeFilter"
              :items="documentTypes"
              :label="$t('documents.filters.type')"
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
              :label="$t('documents.filters.category')"
              clearable
              hide-details
              @update:model-value="loadData"
            />
          </v-col>
          <v-col cols="6" md="2">
            <v-text-field
              v-model="dateFrom"
              type="date"
              :label="$t('documents.filters.dateFrom')"
              clearable
              hide-details
              @update:model-value="loadData"
            />
          </v-col>
          <v-col cols="6" md="2">
            <v-text-field
              v-model="dateTo"
              type="date"
              :label="$t('documents.filters.dateTo')"
              clearable
              hide-details
              @update:model-value="loadData"
            />
          </v-col>
        </v-row>
        <v-row v-if="hasActiveFilters" class="mt-2">
          <v-col cols="12">
            <v-btn variant="tonal" color="primary" size="small" @click="clearFilters">
              <v-icon size="small" class="mr-1">mdi-filter-off</v-icon>
              {{ $t('documents.filters.resetFilters') }}
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Documents Table -->
    <v-card>
      <v-data-table-server
        v-model="selectedDocuments"
        v-model:items-per-page="perPage"
        v-model:page="page"
        v-model:sort-by="sortBy"
        :headers="headers"
        :items="documents"
        :items-length="totalDocuments"
        :loading="loading"
        show-select
        item-value="id"
        @update:options="onTableOptionsUpdate"
      >
        <template #item.title="{ item }">
          <div class="py-2">
            <div class="font-weight-medium truncate-md" :title="item.title || item.original_url">
              {{ item.title || $t('documents.detail.noTitle') }}
            </div>
            <div class="text-caption text-medium-emphasis truncate-md">
              <a :href="item.original_url" target="_blank" class="text-decoration-none">{{ item.original_url }}</a>
            </div>
          </div>
        </template>

        <template #item.document_type="{ item }">
          <v-chip size="small" :color="getTypeColor(item.document_type)">
            <v-icon size="x-small" class="mr-1">{{ getTypeIcon(item.document_type) }}</v-icon>
            {{ item.document_type }}
          </v-chip>
        </template>

        <template #item.processing_status="{ item }">
          <v-chip :color="getStatusColor(item.processing_status)" size="small">
            <v-icon v-if="item.processing_status === 'PROCESSING' || item.processing_status === 'ANALYZING'" class="mr-1 mdi-spin" size="small">
              {{ item.processing_status === 'ANALYZING' ? 'mdi-brain' : 'mdi-loading' }}
            </v-icon>
            {{ getStatusLabel(item.processing_status) }}
          </v-chip>
          <div v-if="(item.processing_status === 'FILTERED' || item.processing_status === 'FAILED') && item.processing_error" class="text-caption text-medium-emphasis mt-1 truncate-xs" :title="item.processing_error">
            {{ item.processing_error }}
          </div>
        </template>

        <template #item.source_name="{ item }">
          <div class="truncate-xs" :title="item.source_name">{{ item.source_name }}</div>
        </template>

        <template #item.discovered_at="{ item }">
          <div class="text-caption">{{ formatDate(item.discovered_at) }}</div>
        </template>

        <template #item.file_size="{ item }">
          <span v-if="item.file_size">{{ formatFileSize(item.file_size) }}</span>
          <span v-else class="text-medium-emphasis">-</span>
        </template>

        <template #item.actions="{ item }">
          <div class="table-actions d-flex justify-end ga-1">
            <v-btn v-if="item.processing_status === 'PENDING'" icon="mdi-play" size="small" variant="tonal" color="primary" :title="$t('documents.actions.process')" :aria-label="$t('documents.actions.process')" :loading="processingIds.has(item.id)" @click="processDocument(item)"></v-btn>
            <v-btn v-if="item.processing_status === 'COMPLETED' || item.processing_status === 'FILTERED'" icon="mdi-brain" size="small" variant="tonal" color="info" :title="$t('documents.actions.analyze')" :aria-label="$t('documents.actions.analyze')" :loading="analyzingIds.has(item.id)" @click="analyzeDocument(item)"></v-btn>
            <v-btn v-if="item.file_path" icon="mdi-download" size="small" variant="tonal" color="success" :title="$t('common.download')" :aria-label="$t('common.download')" @click="downloadDocument(item)"></v-btn>
            <v-btn icon="mdi-open-in-new" size="small" variant="tonal" :title="$t('common.open')" :aria-label="$t('common.open')" :href="item.original_url" target="_blank"></v-btn>
            <v-btn icon="mdi-information" size="small" variant="tonal" :title="$t('common.details')" :aria-label="$t('common.details')" @click="showDetails(item)"></v-btn>
          </div>
        </template>
      </v-data-table-server>
    </v-card>

    <!-- Details Dialog -->
    <v-dialog v-model="detailsDialog" max-width="900" scrollable>
      <v-card v-if="selectedDocument">
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">{{ getTypeIcon(selectedDocument.document_type) }}</v-icon>
          Dokument Details
          <v-spacer />
          <v-chip :color="getStatusColor(selectedDocument.processing_status)" size="small">
            {{ getStatusLabel(selectedDocument.processing_status) }}
          </v-chip>
        </v-card-title>
        <v-divider />
        <v-card-text style="max-height: 70vh;">
          <v-row>
            <v-col cols="12">
              <strong>Titel:</strong>
              <div>{{ selectedDocument.title || '(Kein Titel)' }}</div>
            </v-col>
            <v-col cols="12">
              <strong>URL:</strong>
              <div><a :href="selectedDocument.original_url" target="_blank">{{ selectedDocument.original_url }}</a></div>
            </v-col>
            <v-col cols="6" md="3">
              <strong>Typ:</strong>
              <v-chip size="small" :color="getTypeColor(selectedDocument.document_type)" class="ml-2">{{ selectedDocument.document_type }}</v-chip>
            </v-col>
            <v-col cols="6" md="3">
              <strong>Größe:</strong> {{ selectedDocument.file_size ? formatFileSize(selectedDocument.file_size) : '-' }}
            </v-col>
            <v-col cols="6" md="3">
              <strong>Seiten:</strong> {{ selectedDocument.page_count || '-' }}
            </v-col>
            <v-col cols="6" md="3">
              <strong>Quelle:</strong> {{ selectedDocument.source_name }}
            </v-col>
            <v-col cols="6" md="3">
              <strong>Entdeckt:</strong> {{ formatDate(selectedDocument.discovered_at) }}
            </v-col>
            <v-col cols="6" md="3">
              <strong>Verarbeitet:</strong> {{ selectedDocument.processed_at ? formatDate(selectedDocument.processed_at) : '-' }}
            </v-col>
          </v-row>

          <v-divider class="my-4" />

          <div v-if="selectedDocument.processing_error">
            <strong>Verarbeitungsfehler / Filter-Grund:</strong>
            <v-alert type="warning" variant="tonal" class="mt-2">{{ selectedDocument.processing_error }}</v-alert>
          </div>

          <div v-if="selectedDocument.raw_text" class="mt-4">
            <strong>Extrahierter Text (Vorschau):</strong>
            <v-textarea
              :model-value="selectedDocument.raw_text.substring(0, 3000) + (selectedDocument.raw_text.length > 3000 ? '...' : '')"
              readonly
              rows="10"
              variant="outlined"
              class="mt-2"
              style="font-family: monospace; font-size: 11px;"
            />
          </div>

          <div v-if="selectedDocument.extracted_data && selectedDocument.extracted_data.length > 0" class="mt-4">
            <div class="d-flex align-center mb-2">
              <strong>Extrahierte Daten ({{ selectedDocument.extracted_data.length }})</strong>
              <v-spacer />
              <v-btn size="small" variant="tonal" color="primary" :to="`/results?document_id=${selectedDocument.id}`">
                <v-icon size="small" class="mr-1">mdi-open-in-new</v-icon>
                In Ergebnissen anzeigen
              </v-btn>
            </div>
            <v-expansion-panels>
              <v-expansion-panel v-for="ed in selectedDocument.extracted_data" :key="ed.id">
                <v-expansion-panel-title>
                  <v-chip size="x-small" color="primary" class="mr-2">{{ ed.type }}</v-chip>
                  <span class="text-caption">Confidence: {{ (ed.confidence * 100).toFixed(0) }}%</span>
                  <v-icon v-if="ed.verified" color="success" size="small" class="ml-2">mdi-check-circle</v-icon>
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <pre class="json-viewer pa-2 rounded text-caption">{{ JSON.stringify(ed.content, null, 2) }}</pre>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </div>
        </v-card-text>
        <v-divider />
        <v-card-actions>
          <v-btn v-if="selectedDocument.file_path" color="success" variant="outlined" prepend-icon="mdi-download" @click="downloadDocument(selectedDocument)">Herunterladen</v-btn>
          <v-spacer />
          <v-btn v-if="selectedDocument.processing_status === 'PENDING'" variant="tonal" color="primary" prepend-icon="mdi-play" @click="processDocument(selectedDocument); detailsDialog = false">Verarbeiten</v-btn>
          <v-btn v-if="selectedDocument.processing_status === 'COMPLETED' || selectedDocument.processing_status === 'FILTERED'" variant="tonal" color="info" prepend-icon="mdi-brain" @click="analyzeDocument(selectedDocument); detailsDialog = false">KI-Analyse</v-btn>
          <v-btn variant="tonal" @click="detailsDialog = false">Schließen</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * DocumentsView - Document management and processing
 *
 * Uses useDocumentsView composable for all state and logic.
 * Supports bulk processing, AI analysis, and auto-refresh.
 */
import { onMounted } from 'vue'
import { useDocumentsView } from '@/composables/useDocumentsView'
import PageHeader from '@/components/common/PageHeader.vue'
import DocumentsSkeleton from '@/components/documents/DocumentsSkeleton.vue'

// Initialize composable with all state and methods
const {
  // Loading State
  loading,
  initialLoad,
  processingAll,
  stoppingAll,
  bulkProcessing,
  bulkAnalyzing,
  processingIds,
  analyzingIds,

  // Data
  documents,
  totalDocuments,
  locations,
  categories,
  selectedDocuments,
  stats,

  // Filters
  searchQuery,
  locationFilter,
  typeFilter,
  categoryFilter,
  statusFilter,
  dateFrom,
  dateTo,
  page,
  perPage,
  sortBy,

  // Dialog
  detailsDialog,
  selectedDocument,

  // Static
  documentTypes,
  headers,

  // Computed
  hasActiveFilters,

  // Helper Functions
  getStatusColor,
  getStatusLabel,
  getTypeColor,
  getTypeIcon,
  formatDate,
  formatFileSize,

  // Data Loading
  loadData,
  debouncedLoadData,

  // Filter Actions
  toggleStatusFilter,
  clearFilters,
  onTableOptionsUpdate,

  // Document Actions
  processDocument,
  analyzeDocument,
  processAllPending,
  stopAllProcessing,

  // Bulk Actions
  bulkProcess,
  bulkAnalyze,

  // Details
  showDetails,
  downloadDocument,

  // Export
  exportCsv,

  // Initialization
  initialize,
} = useDocumentsView()

// Explicitly mark unused but template-required variables
void documents
void categories

// Initialize on mount
onMounted(() => initialize())
</script>
