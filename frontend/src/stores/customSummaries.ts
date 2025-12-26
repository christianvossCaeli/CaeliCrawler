/**
 * Custom Summaries Store
 *
 * Manages user-defined dashboard summaries with:
 * - Prompt-based creation (KI-interpreted)
 * - Widget management
 * - Execution and caching
 * - Sharing functionality
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { customSummariesApi } from '@/services/api'
import { useFileDownload } from '@/composables/useFileDownload'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('CustomSummariesStore')

// --- Types ---

export type SummaryStatus = 'draft' | 'active' | 'paused' | 'archived'
export type SummaryTriggerType = 'manual' | 'cron' | 'crawl_category' | 'crawl_preset'
export type SummaryWidgetType = 'table' | 'bar_chart' | 'line_chart' | 'pie_chart' | 'stat_card' | 'text' | 'comparison' | 'timeline' | 'map'
export type ExecutionStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
export type CheckUpdatesStatus = 'pending' | 'crawling' | 'updating' | 'completed' | 'failed'

export interface CheckUpdatesProgress {
  status: CheckUpdatesStatus
  total_sources: number
  completed_sources: number
  current_source?: string
  message: string
  error?: string
}

export interface WidgetPosition {
  x: number
  y: number
  w: number
  h: number
}

export interface WidgetQueryConfig {
  entity_type?: string
  facet_types?: string[]
  filters?: Record<string, unknown>
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  limit?: number
  aggregate?: string
  group_by?: string
  [key: string]: unknown
}

export interface WidgetVisualizationConfig {
  // Table
  columns?: Array<{ field: string; label: string; sortable?: boolean; width?: string }>
  show_pagination?: boolean
  rows_per_page?: number
  // Charts
  x_axis?: { field: string; label: string }
  y_axis?: { field: string; label: string }
  color?: string
  colors?: string[]
  horizontal?: boolean
  stacked?: boolean
  show_legend?: boolean
  show_labels?: boolean
  // Stat card
  trend?: 'up' | 'down' | 'neutral'
  trend_value?: string
  format?: string
  // Text
  content?: string
  [key: string]: unknown
}

export interface SummaryWidget {
  id: string
  widget_type: SummaryWidgetType
  title: string
  subtitle?: string | null
  position: WidgetPosition
  query_config: WidgetQueryConfig
  visualization_config: WidgetVisualizationConfig
  display_order: number
  created_at: string
  updated_at: string
}

export interface SummaryExecution {
  id: string
  status: ExecutionStatus
  triggered_by: string
  trigger_details?: Record<string, unknown> | null
  has_changes: boolean
  relevance_score?: number | null
  relevance_reason?: string | null
  duration_ms?: number | null
  created_at: string
  completed_at?: string | null
  cached_data?: Record<string, unknown>
  error_message?: string | null
}

export interface CustomSummary {
  id: string
  user_id: string
  name: string
  description?: string | null
  original_prompt: string
  interpreted_config: Record<string, unknown>
  layout_config: Record<string, unknown>
  status: SummaryStatus
  trigger_type: SummaryTriggerType
  schedule_cron?: string | null
  trigger_category_id?: string | null
  trigger_preset_id?: string | null
  schedule_enabled: boolean
  next_run_at?: string | null
  check_relevance: boolean
  relevance_threshold: number
  auto_expand: boolean
  is_favorite: boolean
  execution_count: number
  last_executed_at?: string | null
  created_at: string
  updated_at: string
  widgets?: SummaryWidget[]
  last_execution?: SummaryExecution | null
}

export interface SummaryShare {
  id: string
  share_token: string
  share_url: string
  has_password: boolean
  expires_at?: string | null
  allow_export: boolean
  view_count: number
  last_viewed_at?: string | null
  is_active: boolean
  created_at: string
}

export interface SummaryCreateFromPrompt {
  prompt: string
  name?: string
}

export interface SummaryCreate {
  name: string
  description?: string
  original_prompt: string
  interpreted_config?: Record<string, unknown>
  layout_config?: Record<string, unknown>
  trigger_type?: SummaryTriggerType
  schedule_cron?: string
  trigger_category_id?: string
  trigger_preset_id?: string
}

export interface SummaryUpdate {
  name?: string
  description?: string
  layout_config?: Record<string, unknown>
  trigger_type?: SummaryTriggerType
  schedule_cron?: string
  trigger_category_id?: string
  trigger_preset_id?: string
  schedule_enabled?: boolean
  check_relevance?: boolean
  relevance_threshold?: number
  auto_expand?: boolean
  is_favorite?: boolean
  status?: SummaryStatus
}

export interface WidgetCreate {
  widget_type: SummaryWidgetType
  title: string
  subtitle?: string
  position_x?: number
  position_y?: number
  width?: number
  height?: number
  query_config?: WidgetQueryConfig
  visualization_config?: WidgetVisualizationConfig
}

export interface WidgetUpdate {
  title?: string
  subtitle?: string
  position_x?: number
  position_y?: number
  width?: number
  height?: number
  query_config?: WidgetQueryConfig
  visualization_config?: WidgetVisualizationConfig
}

export interface ShareCreate {
  password?: string
  expires_days?: number
  allow_export?: boolean
}

export interface SchedulePreset {
  label: string
  cron: string
  description: string
}

// --- Type Guards ---

interface ApiError {
  response?: {
    status?: number
    data?: {
      detail?: string
    }
  }
  message?: string
}

function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === 'object' &&
    error !== null &&
    ('response' in error || 'message' in error)
  )
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (isApiError(error)) {
    return error.response?.data?.detail || error.message || fallback
  }
  return fallback
}

// --- Store ---

export const useCustomSummariesStore = defineStore('customSummaries', () => {
  // State
  const summaries = ref<CustomSummary[]>([])
  const currentSummary = ref<CustomSummary | null>(null)
  const favoriteIds = ref<Set<string>>(new Set())
  const isLoading = ref(false)
  const isCreating = ref(false)
  // Track execution state per summary to prevent race conditions
  const executingIds = ref<Set<string>>(new Set())
  // Keep isExecuting as computed for backward compatibility
  const isExecuting = computed(() => executingIds.value.size > 0)
  // Track check-updates state
  const checkingUpdatesIds = ref<Set<string>>(new Set())
  const checkUpdatesProgress = ref<CheckUpdatesProgress | null>(null)
  const checkUpdatesTaskId = ref<string | null>(null)
  const isCheckingUpdates = computed(() => checkingUpdatesIds.value.size > 0)
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(20)
  const error = ref<string | null>(null)
  const schedulePresets = ref<SchedulePreset[]>([])

  // File download helper with proper cleanup
  const { downloadBlob } = useFileDownload()

  // Request tracking to prevent race conditions
  let loadSummariesRequestId = 0
  // AbortController for cancelling in-flight requests
  let loadSummariesAbortController: AbortController | null = null
  let loadSummaryAbortController: AbortController | null = null

  // Computed
  const favoriteCount = computed(() => favoriteIds.value.size)
  const favorites = computed(() => summaries.value.filter(s => s.is_favorite))
  const activeSummaries = computed(() => summaries.value.filter(s => s.status === 'active'))
  const scheduledSummaries = computed(() => summaries.value.filter(s => s.schedule_enabled))

  /**
   * Check if summary is favorited
   */
  function isFavorited(summaryId: string): boolean {
    return favoriteIds.value.has(summaryId)
  }

  /**
   * Check if a specific summary is currently executing
   */
  function isExecutingSummary(summaryId: string): boolean {
    return executingIds.value.has(summaryId)
  }

  /**
   * Get summary by ID from local state
   */
  function getSummaryById(summaryId: string): CustomSummary | undefined {
    return summaries.value.find(s => s.id === summaryId)
  }

  /**
   * Load summaries from API
   * Uses request ID tracking and AbortController to prevent race conditions
   * when rapidly changing pages/filters
   */
  async function loadSummaries(options?: {
    page?: number
    per_page?: number
    favorites_only?: boolean
    status?: string
    search?: string
    sort_by?: string
    sort_order?: 'asc' | 'desc'
  }): Promise<void> {
    // Cancel any pending request
    if (loadSummariesAbortController) {
      loadSummariesAbortController.abort()
    }

    // Create new AbortController for this request
    loadSummariesAbortController = new AbortController()
    const signal = loadSummariesAbortController.signal

    // Increment request ID to track this specific request
    const currentRequestId = ++loadSummariesRequestId

    isLoading.value = true
    error.value = null

    if (options?.per_page) {
      perPage.value = options.per_page
    }

    try {
      const response = await customSummariesApi.list({
        page: options?.page || page.value,
        per_page: perPage.value,
        favorites_only: options?.favorites_only,
        status: options?.status,
        search: options?.search,
        sort_by: options?.sort_by,
        sort_order: options?.sort_order,
      }, { signal })

      // Only update state if this is still the latest request
      // This prevents stale responses from overwriting newer data
      if (currentRequestId !== loadSummariesRequestId) {
        return
      }

      summaries.value = response.data.items
      total.value = response.data.total
      page.value = response.data.page

      // Update favoriteIds set
      favoriteIds.value = new Set(
        summaries.value.filter(s => s.is_favorite).map(s => s.id)
      )
    } catch (e) {
      // Ignore aborted requests
      if (e instanceof Error && e.name === 'AbortError') {
        return
      }
      // Only handle error if this is still the latest request
      if (currentRequestId !== loadSummariesRequestId) {
        return
      }
      logger.error('Failed to load summaries:', e)
      error.value = 'Failed to load summaries'
    } finally {
      // Only update loading state if this is still the latest request
      if (currentRequestId === loadSummariesRequestId) {
        isLoading.value = false
        loadSummariesAbortController = null
      }
    }
  }

  /**
   * Load a single summary with widgets and last execution
   * Uses AbortController to cancel previous requests when navigating quickly
   */
  async function loadSummary(summaryId: string): Promise<CustomSummary | null> {
    // Cancel any pending request
    if (loadSummaryAbortController) {
      loadSummaryAbortController.abort()
    }

    // Create new AbortController for this request
    loadSummaryAbortController = new AbortController()
    const signal = loadSummaryAbortController.signal

    isLoading.value = true
    error.value = null

    try {
      const response = await customSummariesApi.get(summaryId, {
        include_widgets: true,
        include_last_execution: true,
      }, { signal })
      currentSummary.value = response.data
      return response.data
    } catch (e) {
      // Ignore aborted requests
      if (e instanceof Error && e.name === 'AbortError') {
        return null
      }
      logger.error('Failed to load summary:', e)
      error.value = 'Failed to load summary'
      return null
    } finally {
      isLoading.value = false
      loadSummaryAbortController = null
    }
  }

  /**
   * Cancel all pending requests
   * Call this when unmounting components or clearing the store
   */
  function cancelPendingRequests(): void {
    if (loadSummariesAbortController) {
      loadSummariesAbortController.abort()
      loadSummariesAbortController = null
    }
    if (loadSummaryAbortController) {
      loadSummaryAbortController.abort()
      loadSummaryAbortController = null
    }
  }

  /**
   * Create a summary from natural language prompt
   */
  async function createFromPrompt(data: SummaryCreateFromPrompt): Promise<{
    id: string
    name: string
    interpretation: Record<string, unknown>
    widgets_created: number
    message: string
  } | null> {
    isCreating.value = true
    error.value = null

    try {
      const response = await customSummariesApi.createFromPrompt(data)
      const result = response.data

      // Reload summaries to include the new one
      await loadSummaries()

      return result
    } catch (e: unknown) {
      logger.error('Failed to create summary from prompt:', e)
      error.value = getErrorMessage(e, 'Failed to create summary')
      return null
    } finally {
      isCreating.value = false
    }
  }

  /**
   * Create a summary with manual configuration
   */
  async function createSummary(data: SummaryCreate): Promise<CustomSummary | null> {
    try {
      const response = await customSummariesApi.create(data)
      const newSummary = response.data

      summaries.value.unshift(newSummary)
      total.value++

      if (newSummary.is_favorite) {
        favoriteIds.value.add(newSummary.id)
      }

      return newSummary
    } catch (e) {
      logger.error('Failed to create summary:', e)
      error.value = 'Failed to create summary'
      return null
    }
  }

  /**
   * Synchronize state between summaries list and currentSummary
   * Ensures consistent state when either is updated
   */
  function syncSummaryState(summary: CustomSummary): void {
    // Update in summaries array
    const index = summaries.value.findIndex(s => s.id === summary.id)
    if (index > -1) {
      // Preserve widgets and last_execution if not provided
      summaries.value[index] = {
        ...summaries.value[index],
        ...summary,
        widgets: summary.widgets ?? summaries.value[index].widgets,
        last_execution: summary.last_execution ?? summaries.value[index].last_execution,
      }
    }

    // Update currentSummary if it matches
    if (currentSummary.value?.id === summary.id) {
      currentSummary.value = {
        ...currentSummary.value,
        ...summary,
        widgets: summary.widgets ?? currentSummary.value.widgets,
        last_execution: summary.last_execution ?? currentSummary.value.last_execution,
      }
    }

    // Update favorites set
    if (summary.is_favorite) {
      favoriteIds.value.add(summary.id)
    } else {
      favoriteIds.value.delete(summary.id)
    }
  }

  /**
   * Update a summary
   */
  async function updateSummary(summaryId: string, data: SummaryUpdate): Promise<CustomSummary | null> {
    try {
      const response = await customSummariesApi.update(summaryId, data)
      const updated = response.data

      // Use unified sync function to update all state
      syncSummaryState(updated)

      return updated
    } catch (e) {
      logger.error('Failed to update summary:', e)
      error.value = 'Failed to update summary'
      return null
    }
  }

  /**
   * Delete a summary
   */
  async function deleteSummary(summaryId: string): Promise<boolean> {
    try {
      await customSummariesApi.delete(summaryId)

      const index = summaries.value.findIndex(s => s.id === summaryId)
      if (index > -1) {
        summaries.value.splice(index, 1)
      }
      favoriteIds.value.delete(summaryId)
      total.value = Math.max(0, total.value - 1)

      if (currentSummary.value?.id === summaryId) {
        currentSummary.value = null
      }

      return true
    } catch (e) {
      logger.error('Failed to delete summary:', e)
      error.value = 'Failed to delete summary'
      return false
    }
  }

  /**
   * Execute a summary
   * Uses per-summary execution tracking to prevent race conditions
   */
  async function executeSummary(summaryId: string, force: boolean = false): Promise<{
    execution_id: string
    status: ExecutionStatus
    has_changes: boolean
    cached_data?: Record<string, unknown>
    message: string
  } | null> {
    // Prevent double execution
    if (executingIds.value.has(summaryId)) {
      logger.warn('Summary already executing:', summaryId)
      return null
    }

    // Track this specific summary as executing
    executingIds.value.add(summaryId)
    error.value = null

    try {
      const response = await customSummariesApi.execute(summaryId, { force })
      const result = {
        ...response.data,
        status: response.data.status as ExecutionStatus,
      }

      // Update local state
      const summary = summaries.value.find(s => s.id === summaryId)
      if (summary) {
        summary.execution_count++
        summary.last_executed_at = new Date().toISOString()
      }

      if (currentSummary.value?.id === summaryId) {
        currentSummary.value.execution_count++
        currentSummary.value.last_executed_at = new Date().toISOString()
      }

      return result
    } catch (e) {
      logger.error('Failed to execute summary:', e)
      error.value = 'Failed to execute summary'
      return null
    } finally {
      // Remove from executing set
      executingIds.value.delete(summaryId)
    }
  }

  /**
   * Check for updates by crawling relevant data sources
   * Returns the task ID for progress polling
   */
  async function checkForUpdates(summaryId: string): Promise<{
    task_id: string
    source_count: number
    message: string
  } | null> {
    // Prevent double execution
    if (checkingUpdatesIds.value.has(summaryId)) {
      logger.warn('Already checking updates for summary:', summaryId)
      return null
    }

    // Track this specific summary as checking
    checkingUpdatesIds.value.add(summaryId)
    checkUpdatesProgress.value = null
    checkUpdatesTaskId.value = null
    error.value = null

    try {
      const response = await customSummariesApi.checkUpdates(summaryId)
      const result = response.data

      checkUpdatesTaskId.value = result.task_id

      // Initialize progress
      checkUpdatesProgress.value = {
        status: 'pending',
        total_sources: result.source_count,
        completed_sources: 0,
        message: result.message,
      }

      return result
    } catch (e: unknown) {
      logger.error('Failed to start check updates:', e)
      error.value = getErrorMessage(e, 'Fehler beim Starten der Aktualisierungsprüfung')
      checkingUpdatesIds.value.delete(summaryId)
      return null
    }
  }

  /**
   * Poll for check-updates progress
   * Call this periodically after starting checkForUpdates
   */
  async function pollCheckUpdatesProgress(summaryId: string, taskId: string): Promise<CheckUpdatesProgress | null> {
    try {
      const response = await customSummariesApi.getCheckUpdatesStatus(summaryId, taskId)
      const progress = response.data

      checkUpdatesProgress.value = progress

      // If completed or failed, cleanup the tracking
      if (progress.status === 'completed' || progress.status === 'failed') {
        checkingUpdatesIds.value.delete(summaryId)
        checkUpdatesTaskId.value = null
      }

      return progress
    } catch (e) {
      logger.error('Failed to poll check updates progress:', e)
      return null
    }
  }

  /**
   * Stop tracking check-updates (e.g., when dialog is closed)
   */
  function cancelCheckUpdates(summaryId: string): void {
    checkingUpdatesIds.value.delete(summaryId)
    checkUpdatesProgress.value = null
    checkUpdatesTaskId.value = null
  }

  /**
   * Check if a specific summary is currently checking for updates
   */
  function isCheckingUpdatesSummary(summaryId: string): boolean {
    return checkingUpdatesIds.value.has(summaryId)
  }

  /**
   * Toggle favorite status
   */
  async function toggleFavorite(summaryId: string): Promise<boolean> {
    try {
      const response = await customSummariesApi.toggleFavorite(summaryId)
      const newState = response.data.is_favorite

      // Find existing summary to create update object
      const existing = summaries.value.find(s => s.id === summaryId) ?? currentSummary.value
      if (existing?.id === summaryId) {
        syncSummaryState({ ...existing, is_favorite: newState })
      } else {
        // Fallback: just update favorites set
        if (newState) {
          favoriteIds.value.add(summaryId)
        } else {
          favoriteIds.value.delete(summaryId)
        }
      }

      return newState
    } catch (e) {
      logger.error('Failed to toggle favorite:', e)
      error.value = 'Failed to toggle favorite'
      return false
    }
  }

  // --- Widget Management ---

  /**
   * Add a widget to a summary
   */
  async function addWidget(summaryId: string, data: WidgetCreate): Promise<SummaryWidget | null> {
    try {
      const response = await customSummariesApi.addWidget(summaryId, data)
      const widget = response.data

      // Update current summary if loaded
      if (currentSummary.value?.id === summaryId) {
        if (!currentSummary.value.widgets) {
          currentSummary.value.widgets = []
        }
        currentSummary.value.widgets.push(widget)
      }

      return widget
    } catch (e) {
      logger.error('Failed to add widget:', e)
      error.value = 'Failed to add widget'
      return null
    }
  }

  /**
   * Update a widget
   */
  async function updateWidget(
    summaryId: string,
    widgetId: string,
    data: WidgetUpdate
  ): Promise<SummaryWidget | null> {
    try {
      const response = await customSummariesApi.updateWidget(summaryId, widgetId, data)
      const updated = response.data

      // Update current summary if loaded
      if (currentSummary.value?.id === summaryId && currentSummary.value.widgets) {
        const index = currentSummary.value.widgets.findIndex(w => w.id === widgetId)
        if (index > -1) {
          currentSummary.value.widgets[index] = updated
        }
      }

      return updated
    } catch (e) {
      logger.error('Failed to update widget:', e)
      error.value = 'Failed to update widget'
      return null
    }
  }

  /**
   * Delete a widget
   */
  async function deleteWidget(summaryId: string, widgetId: string): Promise<boolean> {
    try {
      await customSummariesApi.deleteWidget(summaryId, widgetId)

      // Update current summary if loaded
      if (currentSummary.value?.id === summaryId && currentSummary.value.widgets) {
        const index = currentSummary.value.widgets.findIndex(w => w.id === widgetId)
        if (index > -1) {
          currentSummary.value.widgets.splice(index, 1)
        }
      }

      return true
    } catch (e) {
      logger.error('Failed to delete widget:', e)
      error.value = 'Failed to delete widget'
      return false
    }
  }

  // --- Share Management ---

  /**
   * Create a share link
   */
  async function createShareLink(summaryId: string, data: ShareCreate): Promise<SummaryShare | null> {
    try {
      const response = await customSummariesApi.createShare(summaryId, data)
      return response.data
    } catch (e) {
      logger.error('Failed to create share link:', e)
      error.value = 'Failed to create share link'
      return null
    }
  }

  /**
   * List share links
   */
  async function listShareLinks(summaryId: string): Promise<SummaryShare[]> {
    try {
      const response = await customSummariesApi.listShares(summaryId)
      return response.data
    } catch (e) {
      logger.error('Failed to list share links:', e)
      error.value = 'Failed to list shares'
      return []
    }
  }

  /**
   * Deactivate a share link
   */
  async function deactivateShareLink(summaryId: string, shareId: string): Promise<boolean> {
    try {
      await customSummariesApi.deactivateShare(summaryId, shareId)
      return true
    } catch (e) {
      logger.error('Failed to deactivate share link:', e)
      error.value = 'Failed to deactivate share'
      return false
    }
  }

  // --- Executions ---

  /**
   * List execution history
   */
  async function listExecutions(summaryId: string, limit: number = 10): Promise<SummaryExecution[]> {
    try {
      const response = await customSummariesApi.listExecutions(summaryId, { limit })
      return response.data
    } catch (e) {
      logger.error('Failed to list executions:', e)
      error.value = 'Failed to list executions'
      return []
    }
  }

  // --- Schedule Presets ---

  /**
   * Load schedule presets
   */
  async function loadSchedulePresets(): Promise<void> {
    try {
      const response = await customSummariesApi.getSchedulePresets()
      schedulePresets.value = response.data
    } catch (e) {
      logger.error('Failed to load schedule presets:', e)
    }
  }

  // --- Export Functions ---

  /**
   * Export summary to PDF and trigger download
   */
  async function exportPdf(summaryId: string, filename?: string): Promise<boolean> {
    try {
      const response = await customSummariesApi.exportPdf(summaryId)
      const blob = new Blob([response.data], { type: 'application/pdf' })
      downloadBlob(blob, filename || `summary-${summaryId}.pdf`)
      return true
    } catch (e) {
      logger.error('Failed to export PDF:', e)
      error.value = 'Failed to export PDF'
      return false
    }
  }

  /**
   * Export summary to Excel and trigger download
   */
  async function exportExcel(summaryId: string, filename?: string): Promise<boolean> {
    try {
      const response = await customSummariesApi.exportExcel(summaryId)
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      })
      downloadBlob(blob, filename || `summary-${summaryId}.xlsx`)
      return true
    } catch (e) {
      logger.error('Failed to export Excel:', e)
      error.value = 'Failed to export Excel'
      return false
    }
  }

  /**
   * Clear store on logout
   */
  function clearStore(): void {
    // Cancel any pending requests first
    cancelPendingRequests()

    summaries.value = []
    currentSummary.value = null
    favoriteIds.value.clear()
    executingIds.value.clear()
    total.value = 0
    page.value = 1
    error.value = null
  }

  return {
    // State
    summaries,
    currentSummary,
    favoriteIds,
    executingIds,
    checkingUpdatesIds,
    checkUpdatesProgress,
    checkUpdatesTaskId,
    isLoading,
    isCreating,
    isExecuting,
    isCheckingUpdates,
    total,
    page,
    perPage,
    error,
    schedulePresets,

    // Computed
    favoriteCount,
    favorites,
    activeSummaries,
    scheduledSummaries,

    // Actions
    isFavorited,
    isExecutingSummary,
    isCheckingUpdatesSummary,
    getSummaryById,
    loadSummaries,
    loadSummary,
    createFromPrompt,
    createSummary,
    updateSummary,
    deleteSummary,
    executeSummary,
    checkForUpdates,
    pollCheckUpdatesProgress,
    cancelCheckUpdates,
    toggleFavorite,
    addWidget,
    updateWidget,
    deleteWidget,
    createShareLink,
    listShareLinks,
    deactivateShareLink,
    listExecutions,
    loadSchedulePresets,
    exportPdf,
    exportExcel,
    clearStore,
    cancelPendingRequests,
  }
})
