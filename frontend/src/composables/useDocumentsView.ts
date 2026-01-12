/**
 * Documents View Composable
 *
 * Manages state and logic for the Documents view.
 * Handles document listing, filtering, bulk operations, and auto-refresh.
 */
import { ref, computed, watch, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { dataApi, adminApi } from '@/services/api'
import { format } from 'date-fns'
import { useSnackbar } from '@/composables/useSnackbar'
import { useDebounce, DEBOUNCE_DELAYS } from '@/composables/useDebounce'
import { useLogger } from '@/composables/useLogger'
import { getErrorMessage } from '@/utils/errorMessage'
import { useDateFormatter } from '@/composables/useDateFormatter'
import { useAuthStore } from '@/stores/auth'
import { getStatusColor } from '@/composables/useStatusColors'

// ============================================================================
// Types
// ============================================================================

export interface ExtractedDataItem {
  id: string
  type: string
  confidence: number
  verified?: boolean
  content?: Record<string, unknown>
}

export interface Document {
  id: string
  title?: string
  file_path?: string
  status: string
  source_id?: string
  source_name?: string
  created_at: string
  updated_at?: string
  document_type?: string
  original_url?: string
  processing_status?: string
  processing_error?: string
  file_size?: number
  discovered_at?: string
  processed_at?: string
  page_count?: number
  raw_text?: string
  extracted_data?: ExtractedDataItem[]
  category_name?: string
  // Page-based analysis tracking
  page_analysis_status?: 'pending' | 'partial' | 'complete' | 'needs_review' | 'has_more'
  relevant_pages?: number[]
  analyzed_pages?: number[]
  total_relevant_pages?: number
  page_analysis_note?: string
}

export interface TableOptions {
  page: number
  itemsPerPage: number
  sortBy?: Array<{ key: string; order: 'asc' | 'desc' }>
}

export interface DocumentStats {
  pending: number
  processing: number
  analyzing: number
  completed: number
  filtered: number
  failed: number
}

// ============================================================================
// Composable
// ============================================================================

export function useDocumentsView() {
  const logger = useLogger('DocumentsView')
  const { t } = useI18n()
  const { formatDate: formatLocaleDate } = useDateFormatter()
  const route = useRoute()
  const { showSuccess, showError } = useSnackbar()
  const auth = useAuthStore()
  const canEdit = computed(() => auth.isEditor)
  const canAdmin = computed(() => auth.isAdmin)

  // ============================================================================
  // State
  // ============================================================================

  // Loading states
  const loading = ref(true)
  const initialLoad = ref(true)
  const processingAll = ref(false)
  const stoppingAll = ref(false)
  const bulkProcessing = ref(false)
  const bulkAnalyzing = ref(false)
  const processingIds = ref(new Set<string>())
  const analyzingIds = ref(new Set<string>())

  // Helper functions for immutable Set updates (ensures Vue reactivity)
  const addProcessingId = (id: string) => {
    processingIds.value = new Set([...processingIds.value, id])
  }
  const removeProcessingId = (id: string) => {
    const newSet = new Set(processingIds.value)
    newSet.delete(id)
    processingIds.value = newSet
  }
  const addAnalyzingId = (id: string) => {
    analyzingIds.value = new Set([...analyzingIds.value, id])
  }
  const removeAnalyzingId = (id: string) => {
    const newSet = new Set(analyzingIds.value)
    newSet.delete(id)
    analyzingIds.value = newSet
  }
  const triggeringFullAnalysis = ref(false)
  const analyzingMorePages = ref(false)

  // Data
  const documents = ref<Document[]>([])
  const totalDocuments = ref(0)
  const locations = ref<string[]>([])
  const categories = ref<{ id: string; name: string }[]>([])
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
  const sortBy = ref<Array<{ key: string; order: 'asc' | 'desc' }>>([{ key: 'discovered_at', order: 'desc' }])

  // Dialog
  const detailsDialog = ref(false)
  const selectedDocument = ref<Document | null>(null)

  // Auto-refresh
  let refreshInterval: number | null = null

  // Statistics
  const stats = ref<DocumentStats>({
    pending: 0,
    processing: 0,
    analyzing: 0,
    completed: 0,
    filtered: 0,
    failed: 0,
  })

  // ============================================================================
  // Static Data
  // ============================================================================

  const documentTypes = ['PDF', 'HTML', 'DOCX', 'DOC']

  const headers = computed(() => [
    { title: t('documents.columns.title'), key: 'title', sortable: true },
    { title: t('common.type'), key: 'document_type', width: '90px', sortable: true },
    { title: t('common.status'), key: 'processing_status', width: '140px', sortable: true },
    { title: t('documents.columns.source'), key: 'source_name', width: '140px', sortable: true },
    { title: t('documents.columns.category'), key: 'category_name', width: '150px', sortable: true },
    { title: t('documents.columns.discovered'), key: 'discovered_at', width: '110px', sortable: true },
    { title: t('documents.columns.size'), key: 'file_size', width: '80px', sortable: true },
    { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' as const },
  ])

  // ============================================================================
  // Computed
  // ============================================================================

  const hasActiveFilters = computed(() =>
    searchQuery.value || locationFilter.value || typeFilter.value ||
    categoryFilter.value || statusFilter.value || dateFrom.value || dateTo.value
  )

  // ============================================================================
  // Helper Functions
  // ============================================================================

  function getStatusLabel(status?: string): string {
    if (!status) return '-'
    const labels: Record<string, string> = {
      PENDING: 'Wartend',
      PROCESSING: 'Verarbeitung',
      ANALYZING: 'KI-Analyse',
      COMPLETED: 'Fertig',
      FILTERED: 'Gefiltert',
      FAILED: 'Fehler',
    }
    return labels[status] || status
  }

  function getTypeColor(type?: string): string {
    if (!type) return 'grey'
    const colors: Record<string, string> = { PDF: 'red', HTML: 'blue', DOCX: 'indigo', DOC: 'indigo' }
    return colors[type] || 'grey'
  }

  function getTypeIcon(type?: string): string {
    if (!type) return 'mdi-file-document'
    const icons: Record<string, string> = {
      PDF: 'mdi-file-pdf-box',
      HTML: 'mdi-language-html5',
      DOCX: 'mdi-file-word',
      DOC: 'mdi-file-word',
    }
    return icons[type] || 'mdi-file-document'
  }

  function formatDate(dateStr?: string): string {
    if (!dateStr) return '-'
    return formatLocaleDate(dateStr, 'dd.MM.yy HH:mm') || '-'
  }

  function formatFileSize(bytes?: number): string {
    if (!bytes) return '-'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  // ============================================================================
  // Data Loading
  // ============================================================================

  async function loadData() {
    loading.value = true
    try {
      const params: Record<string, unknown> = { page: page.value, per_page: perPage.value }
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

  async function loadStats() {
    try {
      const response = await dataApi.getDocumentStats()
      const counts = response.data.by_status || {}
      stats.value = {
        pending: counts.PENDING || 0,
        processing: counts.PROCESSING || 0,
        analyzing: counts.ANALYZING || 0,
        completed: counts.COMPLETED || 0,
        filtered: counts.FILTERED || 0,
        failed: counts.FAILED || 0,
      }
    } catch (error) {
      logger.error('Failed to load stats:', error)
    }
  }

  async function loadLocations() {
    try {
      const response = await dataApi.getDocumentLocations()
      locations.value = response.data
    } catch (error) {
      logger.error('Failed to load locations:', error)
    }
  }

  async function loadCategories() {
    if (!canEdit.value) return
    try {
      const response = await adminApi.getCategories()
      categories.value = response.data.items || response.data
    } catch (error) {
      logger.error('Failed to load categories:', error)
    }
  }

  // Debounced search
  const { debouncedFn: debouncedLoadData } = useDebounce(
    () => loadData(),
    { delay: DEBOUNCE_DELAYS.SEARCH }
  )

  // ============================================================================
  // Filter Actions
  // ============================================================================

  function toggleStatusFilter(status: string) {
    statusFilter.value = statusFilter.value === status ? null : status
    page.value = 1
    loadData()
  }

  function clearFilters() {
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

  function onTableOptionsUpdate(options: TableOptions) {
    page.value = options.page
    perPage.value = options.itemsPerPage
    if (options.sortBy && options.sortBy.length > 0) {
      sortBy.value = options.sortBy
    }
    loadData()
  }

  // ============================================================================
  // Document Actions
  // ============================================================================

  async function processDocument(doc: Document) {
    if (!canEdit.value) {
      showError(t('common.forbidden'))
      return
    }
    addProcessingId(doc.id)
    try {
      await adminApi.processDocument(doc.id)
      showSuccess(t('documents.processStarted'))
      loadData()
    } catch (error) {
      showError(getErrorMessage(error) || t('documents.processError'))
    } finally {
      removeProcessingId(doc.id)
    }
  }

  async function analyzeDocument(doc: Document) {
    if (!canEdit.value) {
      showError(t('common.forbidden'))
      return
    }
    addAnalyzingId(doc.id)
    try {
      await adminApi.analyzeDocument(doc.id, true)
      showSuccess(t('documents.analysisStarted'))
      loadData()
    } catch (error) {
      showError(getErrorMessage(error) || t('documents.analysisError'))
    } finally {
      removeAnalyzingId(doc.id)
    }
  }

  async function processAllPending() {
    if (!canAdmin.value) {
      showError(t('common.forbidden'))
      return
    }
    processingAll.value = true
    try {
      await adminApi.processAllPending()
      showSuccess(t('documents.allProcessStarted'))
      loadData()
    } catch (error) {
      showError(getErrorMessage(error) || t('documents.processError'))
    } finally {
      processingAll.value = false
    }
  }

  async function stopAllProcessing() {
    if (!canAdmin.value) {
      showError(t('common.forbidden'))
      return
    }
    stoppingAll.value = true
    try {
      await adminApi.stopAllProcessing()
      showSuccess(t('documents.processingStopping'))
      loadData()
    } catch (error) {
      showError(getErrorMessage(error) || t('documents.stopError'))
    } finally {
      stoppingAll.value = false
    }
  }

  // ============================================================================
  // Bulk Actions
  // ============================================================================

  async function bulkProcess() {
    if (!canEdit.value) {
      showError(t('common.forbidden'))
      return
    }
    bulkProcessing.value = true
    try {
      await adminApi.bulkProcessDocuments({ document_ids: selectedDocuments.value })
      showSuccess(`${selectedDocuments.value.length} Dokumente werden verarbeitet`)
      selectedDocuments.value = []
      loadData()
    } catch (error) {
      showError(getErrorMessage(error) || 'Fehler bei Bulk-Verarbeitung')
    } finally {
      bulkProcessing.value = false
    }
  }

  async function bulkAnalyze() {
    if (!canEdit.value) {
      showError(t('common.forbidden'))
      return
    }
    bulkAnalyzing.value = true
    try {
      await adminApi.bulkAnalyzeDocuments({ document_ids: selectedDocuments.value, skip_relevance_check: true })
      showSuccess(`${selectedDocuments.value.length} Dokumente werden analysiert`)
      selectedDocuments.value = []
      loadData()
    } catch (error) {
      showError(getErrorMessage(error) || 'Fehler bei Bulk-Analyse')
    } finally {
      bulkAnalyzing.value = false
    }
  }

  // ============================================================================
  // Details Dialog
  // ============================================================================

  async function showDetails(doc: Document) {
    try {
      const response = await dataApi.getDocument(doc.id)
      selectedDocument.value = response.data
      detailsDialog.value = true
    } catch {
      showError(t('documents.loadDetailsError'))
    }
  }

  function downloadDocument(doc: Document) {
    if (!canEdit.value) {
      showError(t('common.forbidden'))
      return
    }
    if (doc.file_path) {
      const downloadUrl = `/api/admin/documents/${doc.id}/download`
      window.open(downloadUrl, '_blank')
    }
  }

  // ============================================================================
  // Export
  // ============================================================================

  function exportCsv() {
    const csvHeaders = ['Titel', 'URL', 'Typ', 'Status', 'Quelle', 'Entdeckt', 'Größe']
    const csvRows = documents.value.map(d => [
      `"${(d.title || '').replace(/"/g, '""')}"`,
      `"${d.original_url}"`,
      d.document_type,
      d.processing_status,
      `"${(d.source_name || '').replace(/"/g, '""')}"`,
      d.discovered_at,
      d.file_size || '',
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

  // ============================================================================
  // Page-based Analysis Actions
  // ============================================================================

  async function triggerFullAnalysis(doc: Document) {
    if (!canEdit.value) {
      showError(t('common.forbidden'))
      return
    }
    triggeringFullAnalysis.value = true
    try {
      await dataApi.triggerFullAnalysis(doc.id)
      showSuccess('Vollanalyse gestartet')
      detailsDialog.value = false
      loadData()
    } catch (error) {
      showError(getErrorMessage(error) || 'Fehler beim Starten der Vollanalyse')
    } finally {
      triggeringFullAnalysis.value = false
    }
  }

  async function analyzeMorePages(doc: Document) {
    if (!canEdit.value) {
      showError(t('common.forbidden'))
      return
    }
    analyzingMorePages.value = true
    try {
      await dataApi.analyzeMorePages(doc.id)
      showSuccess('Analyse weiterer Seiten gestartet')
      loadData()
    } catch (error) {
      showError(getErrorMessage(error) || 'Fehler beim Starten der Seitenanalyse')
    } finally {
      analyzingMorePages.value = false
    }
  }

  // ============================================================================
  // Auto-Refresh
  // ============================================================================

  watch(() => stats.value.processing + stats.value.analyzing, (activeCount) => {
    if (activeCount > 0 && !refreshInterval) {
      refreshInterval = window.setInterval(loadData, 5000)
    } else if (activeCount === 0 && refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
  })

  // Cleanup on unmount
  onUnmounted(() => {
    if (refreshInterval) clearInterval(refreshInterval)
  })

  // ============================================================================
  // Initialization
  // ============================================================================

  async function initialize() {
    // Check for search query parameter from results links
    if (route.query.search) {
      const search = Array.isArray(route.query.search) ? route.query.search[0] : route.query.search
      if (search) {
        searchQuery.value = search
        page.value = 1
      }
    }

    // Check for processing_status query parameter from dashboard widget
    if (route.query.processing_status) {
      const status = route.query.processing_status as string
      const validStatuses = ['PENDING', 'PROCESSING', 'ANALYZING', 'COMPLETED', 'FILTERED', 'FAILED']
      if (validStatuses.includes(status)) {
        statusFilter.value = status
      }
    }

    await Promise.all([loadData(), loadLocations(), loadCategories()])

    // Check for document_id query parameter to auto-open document details
    if (route.query.document_id) {
      const docId = route.query.document_id as string
      const doc = documents.value.find((d: Document) => d.id === docId)
      if (doc) {
        selectedDocument.value = doc
        detailsDialog.value = true
      } else {
        try {
          const response = await dataApi.getDocument(docId)
          selectedDocument.value = response.data
          detailsDialog.value = true
        } catch (error) {
          logger.warn('Could not load document details:', error)
          showError(t('documents.loadDetailsError'))
        }
      }
    }
  }

  // ============================================================================
  // Return
  // ============================================================================

  return {
    // Loading State
    loading,
    initialLoad,
    processingAll,
    stoppingAll,
    bulkProcessing,
    bulkAnalyzing,
    processingIds,
    analyzingIds,
    triggeringFullAnalysis,
    analyzingMorePages,

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

    // Page-based Analysis
    triggerFullAnalysis,
    analyzeMorePages,

    // Initialization
    initialize,
  }
}
