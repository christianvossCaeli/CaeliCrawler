/**
 * Results View Composable
 *
 * Manages state, filters, data loading, and actions for the Results (Extracted Data) view.
 * Extracted from ResultsView.vue for better modularity and testability.
 */

import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { format } from 'date-fns'
import { dataApi, adminApi, facetApi } from '@/services/api'
import type { ExtractedDataParams, ExtractionStatsParams } from '@/services/api/sources'
import type { FacetType } from '@/types/entity'
import { useFacetTypeRenderer } from '@/composables/useFacetTypeRenderer'
import { useSnackbar } from '@/composables/useSnackbar'
import { useDebounce, DEBOUNCE_DELAYS } from '@/composables/useDebounce'
import { useLogger } from '@/composables/useLogger'
import { getErrorMessage } from '@/composables/useApiErrorHandler'
import { useAuthStore } from '@/stores/auth'
import { useDateFormatter } from '@/composables/useDateFormatter'

// ============================================================================
// Types
// ============================================================================

export interface EntityReference {
  entity_id: string
  entity_name: string
  entity_type: string
  relevance_score?: number
  role?: string
  confidence?: number
}

export interface SignalItem {
  description?: string
  text?: string
  concern?: string
  type?: string
  severity?: string
  quote?: string
  source?: string
  source_url?: string
  opportunity?: string
}

export interface DecisionMaker {
  name?: string
  person?: string
  role?: string
  position?: string
  department?: string
  contact?: string
  email?: string
  phone?: string
  telefon?: string
  sentiment?: string
  statement?: string
  quote?: string
  source?: string
  source_url?: string
  influence_level?: string
}

export interface OutreachRecommendation {
  priority?: string
  reason?: string
}

export interface ExtractedContent {
  is_relevant?: boolean
  relevanz?: string
  summary?: string
  municipality?: string
  pain_points?: (string | SignalItem)[]
  positive_signals?: (string | SignalItem)[]
  decision_makers?: DecisionMaker[]
  outreach_recommendation?: OutreachRecommendation
  [key: string]: unknown
}

export interface SearchResult {
  id: string
  document_id?: string
  document_title?: string
  document_url?: string
  content?: string
  extraction_type?: string
  entity_references?: EntityReference[]
  confidence_score?: number
  human_verified?: boolean
  verified_by?: string
  verified_at?: string
  created_at: string
  updated_at?: string
  source_name?: string
  final_content?: ExtractedContent
  extracted_content?: ExtractedContent
  raw?: SearchResult
  ai_model_used?: string
  tokens_used?: number
}

export interface TableHeader {
  title: string
  key: string
  sortable?: boolean
  align?: 'start' | 'center' | 'end'
  width?: string
}

export interface TableOptions {
  page: number
  itemsPerPage: number
  sortBy?: Array<{ key: string; order: 'asc' | 'desc' }>
}

export interface ResultsStats {
  total: number
  verified: number
  unverified: number
  avg_confidence: number | null
  high_confidence_count: number
  low_confidence_count: number
  by_type?: Record<string, number>
}

// ============================================================================
// Composable
// ============================================================================

export function useResultsView() {
  const logger = useLogger('useResultsView')
  const { t } = useI18n()
  const route = useRoute()
  const { showSuccess, showError } = useSnackbar()
  const auth = useAuthStore()
  const { formatDate: formatLocaleDate } = useDateFormatter()
  const { getValuesForFacetType, hasValues, normalizeValue, getPrimaryValue } = useFacetTypeRenderer()

  // ========================================
  // Permissions
  // ========================================
  const canVerify = computed(() => auth.isEditor)

  // ========================================
  // Loading State
  // ========================================
  const loading = ref(true)
  const initialLoad = ref(true)
  const bulkVerifying = ref(false)

  // ========================================
  // Data
  // ========================================
  const results = ref<SearchResult[]>([])
  const totalResults = ref(0)
  const locations = ref<string[]>([])
  const categories = ref<{ id: string; name: string }[]>([])
  const extractionTypes = ref<string[]>([])
  const selectedResults = ref<string[]>([])

  // FacetTypes for the active category (for generic display)
  const facetTypes = ref<FacetType[]>([])
  const facetTypesLoading = ref(false)

  // Statistics
  const stats = ref<ResultsStats>({
    total: 0,
    verified: 0,
    unverified: 0,
    avg_confidence: null,
    high_confidence_count: 0,
    low_confidence_count: 0,
  })

  // ========================================
  // Filters
  // ========================================
  const searchQuery = ref('')
  const locationFilter = ref<string | null>(null)
  const extractionTypeFilter = ref<string | null>(null)
  const categoryFilter = ref<string | null>(null)
  const minConfidence = ref(0)
  const verifiedFilter = ref<boolean | null>(null)
  const dateFrom = ref<string | null>(null)
  const dateTo = ref<string | null>(null)
  const page = ref(1)
  const perPage = ref(20)
  const sortBy = ref<Array<{ key: string; order: 'asc' | 'desc' }>>([{ key: 'created_at', order: 'desc' }])

  // ========================================
  // Dialog State
  // ========================================
  const detailsDialog = ref(false)
  const selectedResult = ref<SearchResult | null>(null)

  // ========================================
  // Dynamic Headers
  // ========================================
  const headers = ref<TableHeader[]>([])
  const entityReferenceColumns = ref<string[]>([])

  // ========================================
  // Computed
  // ========================================
  const showLocationFilter = computed(() => locations.value.length > 0)

  const hasActiveFilters = computed(() =>
    searchQuery.value || locationFilter.value || extractionTypeFilter.value ||
    categoryFilter.value || minConfidence.value > 0 || verifiedFilter.value !== null ||
    dateFrom.value || dateTo.value
  )

  // ========================================
  // Helper Functions
  // ========================================
  function getDefaultHeaders(): TableHeader[] {
    return [
      { title: t('results.columns.document'), key: 'document', sortable: false, width: '220px' },
      { title: t('results.columns.type'), key: 'extraction_type', width: '140px', sortable: true },
      { title: t('results.columns.entities'), key: 'entity_count', width: '100px', sortable: true, align: 'center' as const },
      { title: t('results.columns.confidence'), key: 'confidence_score', width: '110px', sortable: true },
      { title: t('results.columns.verified'), key: 'human_verified', width: '90px', sortable: true },
      { title: t('results.columns.created'), key: 'created_at', width: '100px', sortable: true },
      { title: t('results.columns.actions'), key: 'actions', sortable: false, align: 'end' as const },
    ]
  }

  function getConfidenceColor(score?: number | null): string {
    if (!score) return 'grey'
    if (score >= 0.8) return 'success'
    if (score >= 0.6) return 'warning'
    return 'error'
  }

  function getSeverityColor(severity?: string): string {
    if (!severity) return 'grey'
    const colors: Record<string, string> = {
      hoch: 'error', mittel: 'warning', niedrig: 'info',
      high: 'error', medium: 'warning', low: 'info'
    }
    return colors[severity.toLowerCase()] || 'grey'
  }

  function getSeverityIcon(severity: string): string {
    const s = severity.toLowerCase()
    if (s === 'hoch' || s === 'high') return 'mdi-alert'
    if (s === 'mittel' || s === 'medium') return 'mdi-alert-circle-outline'
    if (s === 'niedrig' || s === 'low') return 'mdi-information-outline'
    return 'mdi-minus'
  }

  function getSentimentColor(sentiment: string): string {
    if (!sentiment) return 'grey'
    const s = sentiment.toLowerCase()
    if (s === 'positiv' || s === 'positive') return 'success'
    if (s === 'negativ' || s === 'negative') return 'error'
    return 'grey'
  }

  function getPriorityColor(priority: string): string {
    const colors: Record<string, string> = {
      hoch: 'error', mittel: 'warning', niedrig: 'info',
      high: 'error', medium: 'warning', low: 'info'
    }
    return colors[priority.toLowerCase()] || 'grey'
  }

  function getEntityTypeColor(entityType: string): string {
    const colors: Record<string, string> = {
      'territorial-entity': 'primary',
      'person': 'info',
      'organization': 'secondary',
      'event': 'warning',
    }
    return colors[entityType] || 'grey'
  }

  function getEntityTypeIcon(entityType: string): string {
    const icons: Record<string, string> = {
      'territorial-entity': 'mdi-map-marker',
      'person': 'mdi-account',
      'organization': 'mdi-domain',
      'event': 'mdi-calendar',
    }
    return icons[entityType] || 'mdi-tag'
  }

  function getContent(item: SearchResult): ExtractedContent {
    return item.final_content || item.extracted_content || {}
  }

  function getEntityReferencesByType(item: SearchResult, entityType: string): EntityReference[] {
    if (!item.entity_references || !Array.isArray(item.entity_references)) {
      return []
    }
    return item.entity_references.filter((ref: EntityReference) => ref.entity_type === entityType)
  }

  /**
   * Get the primary entity reference from the result (role='primary')
   */
  function getPrimaryEntityRef(item: SearchResult): EntityReference | null {
    if (!item.entity_references || !Array.isArray(item.entity_references)) {
      return null
    }
    return item.entity_references.find((ref: EntityReference) => ref.role === 'primary') || null
  }

  function formatDate(dateStr: string): string {
    if (!dateStr) return '-'
    return formatLocaleDate(dateStr, 'dd.MM.yy HH:mm') || '-'
  }

  function copyToClipboard(text?: string): void {
    if (!text) return
    navigator.clipboard.writeText(text)
    showSuccess(t('results.messages.copiedToClipboard'))
  }

  // ========================================
  // Data Loading
  // ========================================
  let requestCounter = 0

  async function loadData() {
    const requestId = ++requestCounter
    loading.value = true
    try {
      // Use default headers (no dynamic entity columns in table)
      if (headers.value.length === 0) {
        headers.value = getDefaultHeaders()
      }

      const params: ExtractedDataParams = { page: page.value, per_page: perPage.value }
      if (searchQuery.value) params.search = searchQuery.value
      if (extractionTypeFilter.value) params.extraction_type = extractionTypeFilter.value
      if (categoryFilter.value) params.category_id = categoryFilter.value
      if (minConfidence.value > 0) params.min_confidence = minConfidence.value / 100
      if (verifiedFilter.value !== null) params.human_verified = verifiedFilter.value
      if (dateFrom.value) params.created_from = dateFrom.value
      if (dateTo.value) params.created_to = dateTo.value
      if (sortBy.value.length > 0) {
        params.sort_by = sortBy.value[0].key
        params.sort_order = sortBy.value[0].order
      }

      const statsParams: ExtractionStatsParams = {}
      if (searchQuery.value) statsParams.search = searchQuery.value
      if (extractionTypeFilter.value) statsParams.extraction_type = extractionTypeFilter.value
      if (categoryFilter.value) statsParams.category_id = categoryFilter.value
      if (minConfidence.value > 0) statsParams.min_confidence = minConfidence.value / 100
      if (verifiedFilter.value !== null) statsParams.human_verified = verifiedFilter.value
      if (dateFrom.value) statsParams.created_from = dateFrom.value
      if (dateTo.value) statsParams.created_to = dateTo.value

      const [dataRes, statsRes] = await Promise.all([
        dataApi.getExtractedData(params),
        dataApi.getExtractionStats(statsParams),
      ])
      if (requestId !== requestCounter) return

      results.value = dataRes.data.items
      totalResults.value = dataRes.data.total
      stats.value = statsRes.data

      if (statsRes.data.by_type) {
        extractionTypes.value = Object.keys(statsRes.data.by_type)
      }
    } catch (error) {
      if (requestId !== requestCounter) return
      logger.error('Failed to load data:', error)
      showError(t('results.messages.errorLoading'))
    } finally {
      if (requestId === requestCounter) {
        loading.value = false
        initialLoad.value = false
      }
    }
  }

  async function loadFilters() {
    try {
      const [locationsRes, categoriesRes] = await Promise.all([
        dataApi.getExtractionLocations(),
        adminApi.getCategories(),
      ])
      locations.value = locationsRes.data
      categories.value = categoriesRes.data.items || categoriesRes.data
    } catch (error) {
      logger.error('Failed to load filters:', error)
    }
  }

  /**
   * Load FacetTypes for the active category.
   * Uses the Category → EntityTypes → FacetTypes connection.
   */
  async function loadFacetTypesForCategory() {
    if (!categoryFilter.value) {
      facetTypes.value = []
      return
    }

    facetTypesLoading.value = true
    try {
      const response = await facetApi.getFacetTypesForCategory(categoryFilter.value, {
        ai_extraction_enabled: true,
        is_active: true,
      })
      facetTypes.value = response.data || []
      logger.debug(`Loaded ${facetTypes.value.length} FacetTypes for category`)
    } catch (error) {
      logger.error('Failed to load FacetTypes for category:', error)
      facetTypes.value = []
    } finally {
      facetTypesLoading.value = false
    }
  }

  // Watch for category changes to reload FacetTypes
  watch(categoryFilter, () => {
    loadFacetTypesForCategory()
  })

  // ========================================
  // Dynamic Content Fields
  // ========================================

  /**
   * Reserved fields that are handled separately in the UI
   * (displayed in their own sections, not in the generic dynamic list)
   */
  const RESERVED_FIELDS = new Set([
    'is_relevant',
    'relevanz',
    'summary',
    'outreach_recommendation',
    'municipality',
  ])

  /**
   * Format a field key to a human-readable label
   * e.g., "pain_points" → "Pain Points", "flaechenausweisung" → "Flächenausweisung"
   */
  function formatFieldLabel(key: string): string {
    return key
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  /**
   * Get icon for a dynamic field based on its name
   */
  function getFieldIcon(key: string): string {
    const iconMap: Record<string, string> = {
      pain_points: 'mdi-alert-circle',
      positive_signals: 'mdi-lightbulb-on',
      decision_makers: 'mdi-account-group',
      contacts: 'mdi-account',
      flaechenausweisung: 'mdi-map-marker-radius',
      windenergie: 'mdi-wind-turbine',
      solar: 'mdi-solar-panel',
      timeline: 'mdi-timeline-clock',
      events: 'mdi-calendar-star',
      documents: 'mdi-file-document-multiple',
    }
    return iconMap[key] || 'mdi-tag'
  }

  /**
   * Get color for a dynamic field based on its name
   */
  function getFieldColor(key: string): string {
    const colorMap: Record<string, string> = {
      pain_points: 'warning',
      positive_signals: 'success',
      decision_makers: 'info',
      contacts: 'primary',
    }
    return colorMap[key] || 'blue-grey'
  }

  /**
   * Fields that should be displayed as chips (entity references, contacts)
   */
  const CHIP_DISPLAY_FIELDS = new Set([
    'decision_makers',
    'contacts',
    'entscheider',
    'ansprechpartner',
  ])

  /**
   * Dynamic content field type for template rendering
   */
  interface DynamicContentField {
    key: string
    label: string
    values: unknown[]
    icon: string
    color: string
    displayType: 'chips' | 'list'
  }

  /**
   * Extract all dynamic array/object fields from extracted_content
   * that should be displayed in the detail view
   */
  function getDynamicContentFields(content: ExtractedContent): DynamicContentField[] {
    if (!content || typeof content !== 'object') return []

    const dynamicFields: DynamicContentField[] = []

    for (const [key, value] of Object.entries(content)) {
      // Skip reserved fields
      if (RESERVED_FIELDS.has(key)) continue

      // Skip null/undefined values
      if (value === null || value === undefined) continue

      // Determine display type based on field semantics
      const displayType = CHIP_DISPLAY_FIELDS.has(key) ? 'chips' : 'list'

      // Handle arrays
      if (Array.isArray(value) && value.length > 0) {
        dynamicFields.push({
          key,
          label: formatFieldLabel(key),
          values: value,
          icon: getFieldIcon(key),
          color: getFieldColor(key),
          displayType,
        })
      }
      // Handle single objects (wrap in array for consistent rendering)
      // Only include if the object has at least one non-null value
      else if (typeof value === 'object' && Object.keys(value).length > 0) {
        const hasContent = Object.values(value).some(v => v !== null && v !== undefined && v !== '')
        if (hasContent) {
          dynamicFields.push({
            key,
            label: formatFieldLabel(key),
            values: [value],
            icon: getFieldIcon(key),
            color: getFieldColor(key),
            displayType,
          })
        }
      }
      // Handle non-empty strings (wrap for display)
      else if (typeof value === 'string' && value.trim().length > 0 && key !== 'summary') {
        dynamicFields.push({
          key,
          label: formatFieldLabel(key),
          values: [{ text: value }],
          icon: getFieldIcon(key),
          color: getFieldColor(key),
          displayType: 'list',
        })
      }
    }

    return dynamicFields
  }

  /**
   * Get the primary display text from a dynamic field value.
   * Reuses getPrimaryValue from useFacetTypeRenderer for consistency.
   */
  function getValueText(value: unknown): string {
    if (typeof value === 'string') return value
    if (typeof value === 'boolean') return value ? t('common.yes') : t('common.no')
    if (typeof value === 'number') return String(value)
    if (value && typeof value === 'object') {
      const normalized = normalizeValue(value)
      // Use default display config for fallback rendering
      const defaultConfig = { primaryField: 'description', chipFields: [], severityColors: {}, layout: 'card' as const }
      return getPrimaryValue(normalized, defaultConfig)
    }
    return ''
  }

  // Debounced load
  const { debouncedFn: debouncedLoadData } = useDebounce(
    () => loadData(),
    { delay: DEBOUNCE_DELAYS.SEARCH }
  )

  // ========================================
  // Filter Actions
  // ========================================
  function toggleVerifiedFilter(value: boolean) {
    verifiedFilter.value = verifiedFilter.value === value ? null : value
    page.value = 1
    loadData()
  }

  function clearFilters() {
    searchQuery.value = ''
    locationFilter.value = null
    extractionTypeFilter.value = null
    categoryFilter.value = null
    minConfidence.value = 0
    verifiedFilter.value = null
    dateFrom.value = null
    dateTo.value = null
    page.value = 1
    loadData()
  }

  function filterByEntityReference(_entityType: string, entityName: string) {
    searchQuery.value = entityName
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

  // ========================================
  // Result Actions
  // ========================================
  function showDetails(item: SearchResult) {
    selectedResult.value = item
    detailsDialog.value = true
  }

  async function verifyResult(item: SearchResult) {
    if (!canVerify.value) return
    if (item.human_verified) return
    try {
      await dataApi.verifyExtraction(item.id, { verified: true })
      showSuccess(t('results.messages.verified'))

      const index = results.value.findIndex((r: SearchResult) => r.id === item.id)
      if (index !== -1) {
        results.value[index] = { ...results.value[index], human_verified: true }
      }

      stats.value.verified = (stats.value.verified || 0) + 1
      stats.value.unverified = Math.max(0, (stats.value.unverified || 0) - 1)
    } catch (error) {
      showError(getErrorMessage(error) || t('results.messages.errorVerifying'))
    }
  }

  async function bulkVerify() {
    if (!canVerify.value) return
    bulkVerifying.value = true
    try {
      const verifiedIds = [...selectedResults.value]
      const toVerify = verifiedIds.filter((id) => {
        const item = results.value.find((r: SearchResult) => r.id === id)
        return item && !item.human_verified
      })
      if (toVerify.length === 0) {
        selectedResults.value = []
        return
      }

      const settled = await Promise.allSettled(
        toVerify.map((id) => dataApi.verifyExtraction(id, { verified: true }))
      )

      const succeededIds = toVerify.filter((_, idx) => settled[idx].status === 'fulfilled')
      const failedCount = settled.length - succeededIds.length

      let verifiedCount = 0
      for (const id of succeededIds) {
        const index = results.value.findIndex((r: SearchResult) => r.id === id)
        if (index !== -1 && !results.value[index].human_verified) {
          results.value[index] = { ...results.value[index], human_verified: true }
          verifiedCount++
        }
      }

      if (verifiedCount > 0) {
        showSuccess(`${verifiedCount} ${t('results.messages.bulkVerified')}`)
        stats.value.verified = (stats.value.verified || 0) + verifiedCount
        stats.value.unverified = Math.max(0, (stats.value.unverified || 0) - verifiedCount)
      }
      if (failedCount > 0) {
        showError(t('results.messages.errorBulkVerifying'))
      }

      selectedResults.value = []
    } catch (error) {
      showError(getErrorMessage(error) || t('results.messages.errorBulkVerifying'))
    } finally {
      bulkVerifying.value = false
    }
  }

  // ========================================
  // Export Actions
  // ========================================
  function exportJson(item: SearchResult) {
    const data = {
      id: item.id,
      document_title: item.document_title,
      document_url: item.document_url,
      source_name: item.source_name,
      extraction_type: item.extraction_type,
      confidence_score: item.confidence_score,
      human_verified: item.human_verified,
      created_at: item.created_at,
      content: item.final_content || item.extracted_content,
    }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `extraction-${item.id}.json`
    a.click()
    URL.revokeObjectURL(url)
    showSuccess(t('results.messages.jsonExported'))
  }

  function exportCsv() {
    const csvHeaders = [
      t('results.columns.document'),
      t('results.detail.url'),
      t('results.columns.type'),
      t('results.columns.municipality'),
      t('results.columns.confidence'),
      t('results.columns.verified'),
      t('results.columns.created'),
      t('results.detail.summary')
    ]
    const csvRows = results.value.map(r => {
      const content = r.final_content || r.extracted_content || {}
      return [
        `"${(r.document_title || '').replace(/"/g, '""')}"`,
        `"${r.document_url || ''}"`,
        r.extraction_type,
        `"${content.municipality || ''}"`,
        r.confidence_score ? (r.confidence_score * 100).toFixed(0) + '%' : '',
        r.human_verified ? t('common.yes') : t('common.no'),
        r.created_at,
        `"${(content.summary || '').replace(/"/g, '""').substring(0, 200)}"`
      ]
    })

    const csv = [csvHeaders.join(','), ...csvRows.map(r => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ergebnisse-${format(new Date(), 'yyyy-MM-dd')}.csv`
    a.click()
    URL.revokeObjectURL(url)
    showSuccess(t('results.messages.csvExported'))
  }

  // ========================================
  // Initialization
  // ========================================
  async function initialize() {
    // Initialize headers
    headers.value = getDefaultHeaders()

    // Check for verified filter from URL
    if (route.query.verified !== undefined) {
      verifiedFilter.value = route.query.verified === 'true'
    }

    await Promise.all([loadData(), loadFilters()])
  }

  // ========================================
  // Return
  // ========================================
  return {
    // Permissions
    canVerify,

    // Loading State
    loading,
    initialLoad,
    bulkVerifying,

    // Data
    results,
    totalResults,
    locations,
    categories,
    extractionTypes,
    selectedResults,
    stats,
    facetTypes,
    facetTypesLoading,

    // Filters
    searchQuery,
    locationFilter,
    extractionTypeFilter,
    categoryFilter,
    minConfidence,
    verifiedFilter,
    dateFrom,
    dateTo,
    page,
    perPage,
    sortBy,

    // Dialog
    detailsDialog,
    selectedResult,

    // Headers
    headers,
    entityReferenceColumns,

    // Computed
    showLocationFilter,
    hasActiveFilters,

    // Helper Functions
    getConfidenceColor,
    getSeverityColor,
    getSeverityIcon,
    getSentimentColor,
    getPriorityColor,
    getEntityTypeColor,
    getEntityTypeIcon,
    getContent,
    getEntityReferencesByType,
    getPrimaryEntityRef,
    formatDate,
    copyToClipboard,

    // Data Loading
    loadData,
    loadFilters,
    loadFacetTypesForCategory,
    debouncedLoadData,

    // FacetType Helpers
    getValuesForFacetType,
    hasValues,

    // Dynamic Content Helpers
    getDynamicContentFields,
    getValueText,
    formatFieldLabel,

    // Filter Actions
    toggleVerifiedFilter,
    clearFilters,
    filterByEntityReference,
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
  }
}
