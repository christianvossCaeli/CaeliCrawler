/**
 * Dashboard Store
 *
 * Manages dashboard widget preferences, statistics, and state.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { dashboardApi } from '@/services/api'
import type {
  WidgetConfig,
  DashboardStats,
  ActivityFeedResponse,
  InsightsResponse,
} from '@/widgets/types'
import { getDefaultWidgets } from '@/widgets/registry'

export const useDashboardStore = defineStore('dashboard', () => {
  // State
  const widgets = ref<WidgetConfig[]>([])
  const stats = ref<DashboardStats | null>(null)
  const activityFeed = ref<ActivityFeedResponse | null>(null)
  const insights = ref<InsightsResponse | null>(null)

  const isLoading = ref(false)
  const isEditing = ref(false)
  const hasChanges = ref(false)
  const error = ref<string | null>(null)
  const lastUpdated = ref<Date | null>(null)

  // Computed
  const enabledWidgets = computed(() =>
    widgets.value.filter((w) => w.enabled)
  )

  const disabledWidgets = computed(() =>
    widgets.value.filter((w) => !w.enabled)
  )

  // Actions

  /**
   * Load dashboard preferences from the API
   */
  async function loadPreferences(): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      const response = await dashboardApi.getPreferences()
      widgets.value = response.data.widgets || getDefaultWidgets()
      lastUpdated.value = response.data.updated_at
        ? new Date(response.data.updated_at)
        : new Date()
      hasChanges.value = false
    } catch (e) {
      console.error('Failed to load dashboard preferences:', e)
      // Use default widgets on error
      widgets.value = getDefaultWidgets()
      error.value = 'Failed to load preferences'
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Save dashboard preferences to the API
   */
  async function savePreferences(): Promise<boolean> {
    isLoading.value = true
    error.value = null

    try {
      await dashboardApi.updatePreferences({ widgets: widgets.value })
      hasChanges.value = false
      lastUpdated.value = new Date()
      return true
    } catch (e) {
      console.error('Failed to save dashboard preferences:', e)
      error.value = 'Failed to save preferences'
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Reset widgets to defaults
   */
  async function resetToDefaults(): Promise<void> {
    widgets.value = getDefaultWidgets()
    hasChanges.value = true
    await savePreferences()
  }

  /**
   * Toggle widget enabled state
   */
  function toggleWidget(widgetId: string, enabled: boolean): void {
    const widget = widgets.value.find((w) => w.id === widgetId)
    if (widget) {
      widget.enabled = enabled
      hasChanges.value = true
    }
  }

  /**
   * Update widget position
   */
  function updateWidgetPosition(
    widgetId: string,
    position: { x: number; y: number; w: number; h: number }
  ): void {
    const widget = widgets.value.find((w) => w.id === widgetId)
    if (widget) {
      widget.position = position
      hasChanges.value = true
    }
  }

  /**
   * Update widget size
   */
  function updateWidgetSize(widgetId: string, w: number): void {
    const widget = widgets.value.find((w) => w.id === widgetId)
    if (widget) {
      widget.position.w = w
      hasChanges.value = true
    }
  }

  /**
   * Reorder widgets (for drag & drop)
   */
  function reorderWidgets(fromIndex: number, toIndex: number): void {
    const widget = widgets.value.splice(fromIndex, 1)[0]
    widgets.value.splice(toIndex, 0, widget)

    // Update positions
    widgets.value.forEach((w, i) => {
      w.position.y = Math.floor(i / 4)
      w.position.x = i % 4
    })

    hasChanges.value = true
  }

  /**
   * Toggle edit mode
   */
  function setEditMode(editing: boolean): void {
    isEditing.value = editing
  }

  /**
   * Load dashboard statistics
   */
  async function loadStats(): Promise<void> {
    try {
      const response = await dashboardApi.getStats()
      stats.value = response.data
    } catch (e) {
      console.error('Failed to load dashboard stats:', e)
    }
  }

  /**
   * Load activity feed
   */
  async function loadActivityFeed(
    limit: number = 20,
    offset: number = 0
  ): Promise<void> {
    try {
      const response = await dashboardApi.getActivityFeed({ limit, offset })
      activityFeed.value = response.data
    } catch (e) {
      console.error('Failed to load activity feed:', e)
    }
  }

  /**
   * Load user insights
   */
  async function loadInsights(periodDays: number = 7): Promise<void> {
    try {
      const response = await dashboardApi.getInsights({ period_days: periodDays })
      insights.value = response.data
    } catch (e) {
      console.error('Failed to load insights:', e)
    }
  }

  /**
   * Initialize dashboard (load preferences and stats)
   */
  async function initialize(): Promise<void> {
    await Promise.all([loadPreferences(), loadStats()])
  }

  return {
    // State
    widgets,
    stats,
    activityFeed,
    insights,
    isLoading,
    isEditing,
    hasChanges,
    error,
    lastUpdated,

    // Computed
    enabledWidgets,
    disabledWidgets,

    // Actions
    loadPreferences,
    savePreferences,
    resetToDefaults,
    toggleWidget,
    updateWidgetPosition,
    updateWidgetSize,
    reorderWidgets,
    setEditMode,
    loadStats,
    loadActivityFeed,
    loadInsights,
    initialize,
  }
})
