<template>
  <div>
    <!-- Loading Overlay -->
    <v-overlay :model-value="loading && initialLoad" class="align-center justify-center" persistent >
      <v-card class="pa-8 text-center" min-width="320" elevation="24">
        <v-progress-circular indeterminate size="80" width="6" color="primary" class="mb-4"></v-progress-circular>
        <div class="text-h6 mb-2">{{ $t('documents.messages.loadingDocuments') }}</div>
        <div class="text-body-2 text-medium-emphasis">{{ $t('documents.messages.loadingDocuments') }}</div>
      </v-card>
    </v-overlay>

    <div class="d-flex align-center mb-6">
      <h1 class="text-h4">{{ $t('documents.title') }}</h1>
      <v-spacer></v-spacer>
      <!-- Bulk Actions -->
      <v-btn
        v-if="selectedDocuments.length > 0"
        color="primary"
        variant="outlined"
        prepend-icon="mdi-play"
        class="mr-2"
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
        class="mr-2"
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
        class="mr-2"
        :loading="stoppingAll"
        @click="stopAllProcessing"
      >
        {{ $t('documents.actions.stop') }}
      </v-btn>
      <v-btn
        v-if="stats.pending > 0 && selectedDocuments.length === 0"
        color="primary"
        prepend-icon="mdi-play"
        class="mr-2"
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
    </div>

    <!-- Statistics Bar -->
    <v-row class="mb-4">
      <v-col cols="6" sm="4" md="2">
        <v-card
          :color="statusFilter === 'PENDING' ? 'warning' : undefined"
          :variant="statusFilter === 'PENDING' ? 'elevated' : 'outlined'"
          @click="toggleStatusFilter('PENDING')"
          class="cursor-pointer"
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
          @click="toggleStatusFilter('PROCESSING')"
          class="cursor-pointer"
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
          @click="toggleStatusFilter('ANALYZING')"
          class="cursor-pointer"
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
          @click="toggleStatusFilter('COMPLETED')"
          class="cursor-pointer"
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
          @click="toggleStatusFilter('FILTERED')"
          class="cursor-pointer"
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
          @click="toggleStatusFilter('FAILED')"
          class="cursor-pointer"
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
        <v-row>
          <v-col cols="12" md="3">
            <v-text-field
              v-model="searchQuery"
              prepend-inner-icon="mdi-magnify"
              :label="$t('documents.filters.search')"
              variant="outlined"
              density="compact"
              clearable
              hide-details
              @update:model-value="debouncedLoadData"
            />
          </v-col>
          <v-col cols="12" md="2">
            <v-autocomplete
              v-model="locationFilter"
              :items="locations"
              :label="$t('documents.filters.location')"
              variant="outlined"
              density="compact"
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
              variant="outlined"
              density="compact"
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
              variant="outlined"
              density="compact"
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
              variant="outlined"
              density="compact"
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
              variant="outlined"
              density="compact"
              clearable
              hide-details
              @update:model-value="loadData"
            />
          </v-col>
        </v-row>
        <v-row v-if="hasActiveFilters" class="mt-0">
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
        <template v-slot:item.title="{ item }">
          <div class="py-2">
            <div class="font-weight-medium truncate-md" :title="item.title || item.original_url">
              {{ item.title || $t('documents.detail.noTitle') }}
            </div>
            <div class="text-caption text-medium-emphasis truncate-md">
              <a :href="item.original_url" target="_blank" class="text-decoration-none">{{ item.original_url }}</a>
            </div>
          </div>
        </template>

        <template v-slot:item.document_type="{ item }">
          <v-chip size="small" :color="getTypeColor(item.document_type)">
            <v-icon size="x-small" class="mr-1">{{ getTypeIcon(item.document_type) }}</v-icon>
            {{ item.document_type }}
          </v-chip>
        </template>

        <template v-slot:item.processing_status="{ item }">
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

        <template v-slot:item.source_name="{ item }">
          <div class="truncate-xs" :title="item.source_name">{{ item.source_name }}</div>
        </template>

        <template v-slot:item.discovered_at="{ item }">
          <div class="text-caption">{{ formatDate(item.discovered_at) }}</div>
        </template>

        <template v-slot:item.file_size="{ item }">
          <span v-if="item.file_size">{{ formatFileSize(item.file_size) }}</span>
          <span v-else class="text-medium-emphasis">-</span>
        </template>

        <template v-slot:item.actions="{ item }">
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { dataApi, adminApi } from '@/services/api'
import { format } from 'date-fns'
import { de } from 'date-fns/locale'
import { useSnackbar } from '@/composables/useSnackbar'

const { t } = useI18n()
const { showSuccess, showError } = useSnackbar()

// Loading states
const loading = ref(true)
const initialLoad = ref(true)
const processingAll = ref(false)
const stoppingAll = ref(false)
const bulkProcessing = ref(false)
const bulkAnalyzing = ref(false)
const processingIds = ref(new Set<string>())
const analyzingIds = ref(new Set<string>())

// Data
const documents = ref<any[]>([])
const totalDocuments = ref(0)
const locations = ref<string[]>([])
const categories = ref<any[]>([])
const selectedDocuments = ref<string[]>([])

// Filters
const searchQuery = ref('')
const locationFilter = ref<string | null>(null)
const typeFilter = ref<string | null>(null)
const categoryFilter = ref<string | null>(null)
const statusFilter = ref<string | null>(null)
const dateFrom = ref<string | null>(null)
const dateTo = ref<string | null>(null)
const page = ref(1)
const perPage = ref(20)
const sortBy = ref<any[]>([{ key: 'discovered_at', order: 'desc' }])

// Dialog
const detailsDialog = ref(false)
const selectedDocument = ref<any>(null)

// Auto-refresh
let refreshInterval: number | null = null

// Statistics
const stats = ref({
  pending: 0,
  processing: 0,
  analyzing: 0,
  completed: 0,
  filtered: 0,
  failed: 0,
})

const documentTypes = ['PDF', 'HTML', 'DOCX', 'DOC']

const headers = [
  { title: t('documents.columns.title'), key: 'title', sortable: true },
  { title: t('common.type'), key: 'document_type', width: '90px', sortable: true },
  { title: t('common.status'), key: 'processing_status', width: '140px', sortable: true },
  { title: t('documents.columns.source'), key: 'source_name', width: '140px', sortable: true },
  { title: t('documents.columns.category'), key: 'category_name', width: '150px', sortable: true },
  { title: t('documents.columns.discovered'), key: 'discovered_at', width: '110px', sortable: true },
  { title: t('documents.columns.size'), key: 'file_size', width: '80px', sortable: true },
  { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' as const },
]

const hasActiveFilters = computed(() =>
  searchQuery.value || locationFilter.value || typeFilter.value ||
  categoryFilter.value || statusFilter.value || dateFrom.value || dateTo.value
)

// Helpers
const getStatusColor = (status: string) => {
  const colors: Record<string, string> = { PENDING: 'warning', PROCESSING: 'info', ANALYZING: 'purple', COMPLETED: 'success', FILTERED: 'grey', FAILED: 'error' }
  return colors[status] || 'grey'
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = { PENDING: 'Wartend', PROCESSING: 'Verarbeitung', ANALYZING: 'KI-Analyse', COMPLETED: 'Fertig', FILTERED: 'Gefiltert', FAILED: 'Fehler' }
  return labels[status] || status
}

const getTypeColor = (type: string) => {
  const colors: Record<string, string> = { PDF: 'red', HTML: 'blue', DOCX: 'indigo', DOC: 'indigo' }
  return colors[type] || 'grey'
}

const getTypeIcon = (type: string) => {
  const icons: Record<string, string> = { PDF: 'mdi-file-pdf-box', HTML: 'mdi-language-html5', DOCX: 'mdi-file-word', DOC: 'mdi-file-word' }
  return icons[type] || 'mdi-file-document'
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return format(new Date(dateStr), 'dd.MM.yy HH:mm', { locale: de })
}

const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// Data loading
const loadData = async () => {
  loading.value = true
  try {
    const params: any = { page: page.value, per_page: perPage.value }
    if (searchQuery.value) params.search = searchQuery.value
    if (locationFilter.value) params.location_name = locationFilter.value
    if (typeFilter.value) params.document_type = typeFilter.value
    if (categoryFilter.value) params.category_id = categoryFilter.value
    if (statusFilter.value) params.processing_status = statusFilter.value
    if (dateFrom.value) params.discovered_from = dateFrom.value
    if (dateTo.value) params.discovered_to = dateTo.value
    if (sortBy.value.length > 0) {
      params.sort_by = sortBy.value[0].key
      params.sort_order = sortBy.value[0].order
    }

    const documentsRes = await dataApi.getDocuments(params)
    documents.value = documentsRes.data.items
    totalDocuments.value = documentsRes.data.total
    await loadStats()
  } finally {
    loading.value = false
    initialLoad.value = false
  }
}

const loadStats = async () => {
  try {
    const statuses = ['PENDING', 'PROCESSING', 'ANALYZING', 'COMPLETED', 'FILTERED', 'FAILED']
    const results = await Promise.all(statuses.map(status => dataApi.getDocuments({ processing_status: status, per_page: 1 })))
    stats.value = {
      pending: results[0].data.total,
      processing: results[1].data.total,
      analyzing: results[2].data.total,
      completed: results[3].data.total,
      filtered: results[4].data.total,
      failed: results[5].data.total,
    }
  } catch (error) {
    console.error('Failed to load stats:', error)
  }
}

const loadLocations = async () => {
  try {
    const response = await dataApi.getDocumentLocations()
    locations.value = response.data
  } catch (error) {
    console.error('Failed to load locations:', error)
  }
}

const loadCategories = async () => {
  try {
    const response = await adminApi.getCategories()
    categories.value = response.data.items || response.data
  } catch (error) {
    console.error('Failed to load categories:', error)
  }
}

let debounceTimer: ReturnType<typeof setTimeout> | null = null
const debouncedLoadData = () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => loadData(), 300)
}

// Filter actions
const toggleStatusFilter = (status: string) => {
  statusFilter.value = statusFilter.value === status ? null : status
  page.value = 1
  loadData()
}

const clearFilters = () => {
  searchQuery.value = ''
  locationFilter.value = null
  typeFilter.value = null
  categoryFilter.value = null
  statusFilter.value = null
  dateFrom.value = null
  dateTo.value = null
  page.value = 1
  loadData()
}

const onTableOptionsUpdate = (options: any) => {
  page.value = options.page
  perPage.value = options.itemsPerPage
  if (options.sortBy && options.sortBy.length > 0) {
    sortBy.value = options.sortBy
  }
  loadData()
}

// Document actions
const processDocument = async (doc: any) => {
  processingIds.value.add(doc.id)
  try {
    await adminApi.processDocument(doc.id)
    showSuccess(t('documents.processStarted'))
    loadData()
  } catch (error: any) {
    showError(error.response?.data?.detail || t('documents.processError'))
  } finally {
    processingIds.value.delete(doc.id)
  }
}

const analyzeDocument = async (doc: any) => {
  analyzingIds.value.add(doc.id)
  try {
    await adminApi.analyzeDocument(doc.id, true)
    showSuccess(t('documents.analysisStarted'))
    loadData()
  } catch (error: any) {
    showError(error.response?.data?.detail || t('documents.analysisError'))
  } finally {
    analyzingIds.value.delete(doc.id)
  }
}

const processAllPending = async () => {
  processingAll.value = true
  try {
    await adminApi.processAllPending()
    showSuccess(t('documents.allProcessStarted'))
    loadData()
  } catch (error: any) {
    showError(error.response?.data?.detail || t('documents.processError'))
  } finally {
    processingAll.value = false
  }
}

const stopAllProcessing = async () => {
  stoppingAll.value = true
  try {
    await adminApi.stopAllProcessing()
    showSuccess(t('documents.processingStopping'))
    loadData()
  } catch (error: any) {
    showError(error.response?.data?.detail || t('documents.stopError'))
  } finally {
    stoppingAll.value = false
  }
}

// Bulk actions
const bulkProcess = async () => {
  bulkProcessing.value = true
  try {
    for (const id of selectedDocuments.value) {
      await adminApi.processDocument(id)
    }
    showSuccess(`${selectedDocuments.value.length} Dokumente werden verarbeitet`)
    selectedDocuments.value = []
    loadData()
  } catch (error: any) {
    showError(error.response?.data?.detail || 'Fehler bei Bulk-Verarbeitung')
  } finally {
    bulkProcessing.value = false
  }
}

const bulkAnalyze = async () => {
  bulkAnalyzing.value = true
  try {
    for (const id of selectedDocuments.value) {
      await adminApi.analyzeDocument(id, true)
    }
    showSuccess(`${selectedDocuments.value.length} Dokumente werden analysiert`)
    selectedDocuments.value = []
    loadData()
  } catch (error: any) {
    showError(error.response?.data?.detail || 'Fehler bei Bulk-Analyse')
  } finally {
    bulkAnalyzing.value = false
  }
}

const showDetails = async (doc: any) => {
  try {
    const response = await dataApi.getDocument(doc.id)
    selectedDocument.value = response.data
    detailsDialog.value = true
  } catch (error: any) {
    showError(t('documents.loadDetailsError'))
  }
}

const downloadDocument = (doc: any) => {
  if (doc.file_path) {
    // Construct download URL - assuming backend serves files
    const downloadUrl = `/api/admin/documents/${doc.id}/download`
    window.open(downloadUrl, '_blank')
  }
}

const exportCsv = () => {
  const csvHeaders = ['Titel', 'URL', 'Typ', 'Status', 'Quelle', 'Entdeckt', 'Größe']
  const csvRows = documents.value.map(d => [
    `"${(d.title || '').replace(/"/g, '""')}"`,
    `"${d.original_url}"`,
    d.document_type,
    d.processing_status,
    `"${(d.source_name || '').replace(/"/g, '""')}"`,
    d.discovered_at,
    d.file_size || ''
  ])

  const csv = [csvHeaders.join(','), ...csvRows.map(r => r.join(','))].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `dokumente-${format(new Date(), 'yyyy-MM-dd')}.csv`
  a.click()
  URL.revokeObjectURL(url)
  showSuccess('CSV exportiert')
}

// Auto-refresh when processing is active
watch(() => stats.value.processing + stats.value.analyzing, (activeCount) => {
  if (activeCount > 0 && !refreshInterval) {
    refreshInterval = window.setInterval(loadData, 5000)
  } else if (activeCount === 0 && refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
})

onMounted(async () => {
  await Promise.all([loadData(), loadLocations(), loadCategories()])
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})
</script>
