/**
 * Unit tests for the dashboard store
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDashboardStore } from './dashboard'

// Mock the API module
vi.mock('@/services/api', () => ({
  dashboardApi: {
    getPreferences: vi.fn(),
    updatePreferences: vi.fn(),
    getStats: vi.fn(),
    getActivityFeed: vi.fn(),
    getInsights: vi.fn(),
  },
}))

// Mock the widget registry
vi.mock('@/widgets/registry', () => ({
  getDefaultWidgets: vi.fn(() => [
    {
      id: 'stats-entities',
      type: 'stats-entities',
      title: 'Entities',
      enabled: true,
      position: { x: 0, y: 0, w: 1, h: 1 },
    },
    {
      id: 'stats-documents',
      type: 'stats-documents',
      title: 'Documents',
      enabled: true,
      position: { x: 1, y: 0, w: 1, h: 1 },
    },
  ]),
}))

// Mock useLogger
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}))

// Import the mocked api after vi.mock
import { dashboardApi } from '@/services/api'
import { getDefaultWidgets } from '@/widgets/registry'

describe('Dashboard Store', () => {
  let store: ReturnType<typeof useDashboardStore>

  const mockWidgets = [
    {
      id: 'stats-entities',
      type: 'stats-entities',
      title: 'Entities',
      enabled: true,
      position: { x: 0, y: 0, w: 1, h: 1 },
    },
    {
      id: 'activity-feed',
      type: 'activity-feed',
      title: 'Activity',
      enabled: false,
      position: { x: 2, y: 0, w: 2, h: 2 },
    },
  ]

  const mockStats = {
    total_entities: 100,
    total_documents: 500,
    total_sources: 50,
    active_crawlers: 3,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    store = useDashboardStore()
  })

  // ==========================================================================
  // Initial State
  // ==========================================================================

  describe('Initial State', () => {
    it('has correct default state', () => {
      expect(store.widgets).toEqual([])
      expect(store.stats).toBeNull()
      expect(store.activityFeed).toBeNull()
      expect(store.insights).toBeNull()
      expect(store.isLoading).toBe(false)
      expect(store.isEditing).toBe(false)
      expect(store.hasChanges).toBe(false)
      expect(store.error).toBeNull()
    })

    it('has empty enabled widgets initially', () => {
      expect(store.enabledWidgets).toEqual([])
      expect(store.disabledWidgets).toEqual([])
    })
  })

  // ==========================================================================
  // Load Preferences
  // ==========================================================================

  describe('loadPreferences', () => {
    it('loads preferences from API', async () => {
      vi.mocked(dashboardApi.getPreferences).mockResolvedValueOnce({
        data: {
          widgets: mockWidgets,
          updated_at: '2024-01-01T00:00:00Z',
        },
      } as never)

      await store.loadPreferences()

      expect(store.widgets).toEqual(mockWidgets)
      expect(store.hasChanges).toBe(false)
      expect(store.lastUpdated).toBeInstanceOf(Date)
    })

    it('uses default widgets when API returns empty', async () => {
      vi.mocked(dashboardApi.getPreferences).mockResolvedValueOnce({
        data: { widgets: null },
      } as never)

      await store.loadPreferences()

      expect(store.widgets).toEqual(getDefaultWidgets())
    })

    it('uses default widgets on API error', async () => {
      vi.mocked(dashboardApi.getPreferences).mockRejectedValueOnce(
        new Error('API Error')
      )

      await store.loadPreferences()

      expect(store.widgets).toEqual(getDefaultWidgets())
      expect(store.error).toBe('Failed to load preferences')
    })

    it('sets isLoading during load', async () => {
      let resolvePromise: (value: unknown) => void
      const pendingPromise = new Promise((resolve) => {
        resolvePromise = resolve
      })
      vi.mocked(dashboardApi.getPreferences).mockReturnValueOnce(
        pendingPromise as never
      )

      const loadPromise = store.loadPreferences()

      expect(store.isLoading).toBe(true)

      resolvePromise!({ data: { widgets: mockWidgets } })
      await loadPromise

      expect(store.isLoading).toBe(false)
    })
  })

  // ==========================================================================
  // Save Preferences
  // ==========================================================================

  describe('savePreferences', () => {
    beforeEach(async () => {
      // Load some widgets first
      vi.mocked(dashboardApi.getPreferences).mockResolvedValueOnce({
        data: { widgets: mockWidgets },
      } as never)
      await store.loadPreferences()
    })

    it('saves preferences to API', async () => {
      vi.mocked(dashboardApi.updatePreferences).mockResolvedValueOnce(
        {} as never
      )

      const result = await store.savePreferences()

      expect(result).toBe(true)
      expect(dashboardApi.updatePreferences).toHaveBeenCalledWith({
        widgets: mockWidgets,
      })
      expect(store.hasChanges).toBe(false)
    })

    it('handles save error', async () => {
      vi.mocked(dashboardApi.updatePreferences).mockRejectedValueOnce(
        new Error('API Error')
      )

      const result = await store.savePreferences()

      expect(result).toBe(false)
      expect(store.error).toBe('Failed to save preferences')
    })
  })

  // ==========================================================================
  // Toggle Widget
  // ==========================================================================

  describe('toggleWidget', () => {
    beforeEach(async () => {
      vi.mocked(dashboardApi.getPreferences).mockResolvedValueOnce({
        data: { widgets: mockWidgets },
      } as never)
      await store.loadPreferences()
    })

    it('enables a disabled widget', () => {
      store.toggleWidget('activity-feed', true)

      const widget = store.widgets.find((w) => w.id === 'activity-feed')
      expect(widget?.enabled).toBe(true)
      expect(store.hasChanges).toBe(true)
    })

    it('disables an enabled widget', () => {
      store.toggleWidget('stats-entities', false)

      const widget = store.widgets.find((w) => w.id === 'stats-entities')
      expect(widget?.enabled).toBe(false)
      expect(store.hasChanges).toBe(true)
    })

    it('does nothing for non-existent widget', () => {
      store.toggleWidget('non-existent', true)

      expect(store.hasChanges).toBe(false)
    })
  })

  // ==========================================================================
  // Update Widget Position
  // ==========================================================================

  describe('updateWidgetPosition', () => {
    beforeEach(async () => {
      vi.mocked(dashboardApi.getPreferences).mockResolvedValueOnce({
        data: { widgets: mockWidgets },
      } as never)
      await store.loadPreferences()
    })

    it('updates widget position', () => {
      const newPosition = { x: 3, y: 1, w: 2, h: 2 }

      store.updateWidgetPosition('stats-entities', newPosition)

      const widget = store.widgets.find((w) => w.id === 'stats-entities')
      expect(widget?.position).toEqual(newPosition)
      expect(store.hasChanges).toBe(true)
    })

    it('does nothing for non-existent widget', () => {
      const newPosition = { x: 3, y: 1, w: 2, h: 2 }

      store.updateWidgetPosition('non-existent', newPosition)

      expect(store.hasChanges).toBe(false)
    })
  })

  // ==========================================================================
  // Update Widget Size
  // ==========================================================================

  describe('updateWidgetSize', () => {
    beforeEach(async () => {
      vi.mocked(dashboardApi.getPreferences).mockResolvedValueOnce({
        data: { widgets: mockWidgets },
      } as never)
      await store.loadPreferences()
    })

    it('updates widget width', () => {
      store.updateWidgetSize('stats-entities', 3)

      const widget = store.widgets.find((w) => w.id === 'stats-entities')
      expect(widget?.position.w).toBe(3)
      expect(store.hasChanges).toBe(true)
    })
  })

  // ==========================================================================
  // Reorder Widgets
  // ==========================================================================

  describe('reorderWidgets', () => {
    beforeEach(async () => {
      vi.mocked(dashboardApi.getPreferences).mockResolvedValueOnce({
        data: { widgets: mockWidgets },
      } as never)
      await store.loadPreferences()
    })

    it('reorders widgets', () => {
      const originalFirst = store.widgets[0].id

      store.reorderWidgets(0, 1)

      expect(store.widgets[1].id).toBe(originalFirst)
      expect(store.hasChanges).toBe(true)
    })

    it('updates positions after reorder', () => {
      store.reorderWidgets(0, 1)

      // Positions should be recalculated
      store.widgets.forEach((w, i) => {
        expect(w.position.y).toBe(Math.floor(i / 4))
        expect(w.position.x).toBe(i % 4)
      })
    })
  })

  // ==========================================================================
  // Edit Mode
  // ==========================================================================

  describe('setEditMode', () => {
    it('enables edit mode', () => {
      store.setEditMode(true)

      expect(store.isEditing).toBe(true)
    })

    it('disables edit mode', () => {
      store.setEditMode(true)
      store.setEditMode(false)

      expect(store.isEditing).toBe(false)
    })
  })

  // ==========================================================================
  // Load Stats
  // ==========================================================================

  describe('loadStats', () => {
    it('loads stats from API', async () => {
      vi.mocked(dashboardApi.getStats).mockResolvedValueOnce({
        data: mockStats,
      } as never)

      await store.loadStats()

      expect(store.stats).toEqual(mockStats)
    })

    it('handles stats error gracefully', async () => {
      vi.mocked(dashboardApi.getStats).mockRejectedValueOnce(
        new Error('API Error')
      )

      await store.loadStats()

      // Should not throw, just log error
      expect(store.stats).toBeNull()
    })
  })

  // ==========================================================================
  // Load Activity Feed
  // ==========================================================================

  describe('loadActivityFeed', () => {
    const mockActivityFeed = {
      items: [
        { id: 1, type: 'crawl', message: 'Crawl completed' },
        { id: 2, type: 'import', message: 'Documents imported' },
      ],
      total: 2,
    }

    it('loads activity feed from API', async () => {
      vi.mocked(dashboardApi.getActivityFeed).mockResolvedValueOnce({
        data: mockActivityFeed,
      } as never)

      await store.loadActivityFeed()

      expect(store.activityFeed).toEqual(mockActivityFeed)
      expect(dashboardApi.getActivityFeed).toHaveBeenCalledWith({
        limit: 20,
        offset: 0,
      })
    })

    it('accepts custom limit and offset', async () => {
      vi.mocked(dashboardApi.getActivityFeed).mockResolvedValueOnce({
        data: mockActivityFeed,
      } as never)

      await store.loadActivityFeed(10, 5)

      expect(dashboardApi.getActivityFeed).toHaveBeenCalledWith({
        limit: 10,
        offset: 5,
      })
    })
  })

  // ==========================================================================
  // Load Insights
  // ==========================================================================

  describe('loadInsights', () => {
    const mockInsights = {
      trending_topics: ['Topic A', 'Topic B'],
      summary: 'This week summary',
    }

    it('loads insights from API', async () => {
      vi.mocked(dashboardApi.getInsights).mockResolvedValueOnce({
        data: mockInsights,
      } as never)

      await store.loadInsights()

      expect(store.insights).toEqual(mockInsights)
      expect(dashboardApi.getInsights).toHaveBeenCalledWith({ period_days: 7 })
    })

    it('accepts custom period', async () => {
      vi.mocked(dashboardApi.getInsights).mockResolvedValueOnce({
        data: mockInsights,
      } as never)

      await store.loadInsights(30)

      expect(dashboardApi.getInsights).toHaveBeenCalledWith({ period_days: 30 })
    })
  })

  // ==========================================================================
  // Initialize
  // ==========================================================================

  describe('initialize', () => {
    it('loads preferences and stats in parallel', async () => {
      vi.mocked(dashboardApi.getPreferences).mockResolvedValueOnce({
        data: { widgets: mockWidgets },
      } as never)
      vi.mocked(dashboardApi.getStats).mockResolvedValueOnce({
        data: mockStats,
      } as never)

      await store.initialize()

      expect(dashboardApi.getPreferences).toHaveBeenCalled()
      expect(dashboardApi.getStats).toHaveBeenCalled()
      expect(store.widgets).toEqual(mockWidgets)
      expect(store.stats).toEqual(mockStats)
    })
  })

  // ==========================================================================
  // Reset to Defaults
  // ==========================================================================

  describe('resetToDefaults', () => {
    beforeEach(async () => {
      vi.mocked(dashboardApi.getPreferences).mockResolvedValueOnce({
        data: { widgets: mockWidgets },
      } as never)
      await store.loadPreferences()
    })

    it('resets widgets to defaults and saves', async () => {
      vi.mocked(dashboardApi.updatePreferences).mockResolvedValueOnce(
        {} as never
      )

      await store.resetToDefaults()

      expect(store.widgets).toEqual(getDefaultWidgets())
      expect(dashboardApi.updatePreferences).toHaveBeenCalled()
    })
  })

  // ==========================================================================
  // Computed Properties
  // ==========================================================================

  describe('computed properties', () => {
    beforeEach(async () => {
      vi.mocked(dashboardApi.getPreferences).mockResolvedValueOnce({
        data: { widgets: mockWidgets },
      } as never)
      await store.loadPreferences()
    })

    it('enabledWidgets returns only enabled widgets', () => {
      expect(store.enabledWidgets).toHaveLength(1)
      expect(store.enabledWidgets[0].enabled).toBe(true)
    })

    it('disabledWidgets returns only disabled widgets', () => {
      expect(store.disabledWidgets).toHaveLength(1)
      expect(store.disabledWidgets[0].enabled).toBe(false)
    })
  })
})
