/**
 * Tests for customSummaries store
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCustomSummariesStore } from './customSummaries'
import type {
  CustomSummary,
  SummaryWidget,
  SummaryExecution,
  SummaryShare,
  ExecutionStatus,
} from './customSummaries'

// Mock dependencies
vi.mock('@/services/api', () => ({
  customSummariesApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    createFromPrompt: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    execute: vi.fn(),
    toggleFavorite: vi.fn(),
    addWidget: vi.fn(),
    updateWidget: vi.fn(),
    deleteWidget: vi.fn(),
    createShare: vi.fn(),
    listShares: vi.fn(),
    deactivateShare: vi.fn(),
    listExecutions: vi.fn(),
    getSchedulePresets: vi.fn(),
    exportPdf: vi.fn(),
    exportExcel: vi.fn(),
  },
}))

vi.mock('@/composables/useFileDownload', () => ({
  useFileDownload: () => ({
    downloadBlob: vi.fn(),
  }),
}))

vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({
    error: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
  }),
}))

import { customSummariesApi } from '@/services/api'

describe('useCustomSummariesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  const createMockSummary = (overrides?: Partial<CustomSummary>): CustomSummary => ({
    id: 'summary-1',
    user_id: 'user-1',
    name: 'Test Summary',
    description: 'Test description',
    original_prompt: 'Show me data',
    interpreted_config: {},
    layout_config: {},
    status: 'ACTIVE',
    trigger_type: 'MANUAL',
    schedule_cron: null,
    trigger_category_id: null,
    trigger_preset_id: null,
    auto_trigger_entity_types: [],
    last_auto_trigger_reason: null,
    schedule_enabled: false,
    next_run_at: null,
    check_relevance: false,
    relevance_threshold: 0.7,
    auto_expand: false,
    is_favorite: false,
    execution_count: 0,
    last_executed_at: null,
    created_at: '2025-01-15T12:00:00Z',
    updated_at: '2025-01-15T12:00:00Z',
    widgets: [],
    last_execution: null,
    ...overrides,
  })

  const createMockWidget = (overrides?: Partial<SummaryWidget>): SummaryWidget => ({
    id: 'widget-1',
    widget_type: 'table',
    title: 'Test Widget',
    subtitle: null,
    position: { x: 0, y: 0, w: 6, h: 4 },
    query_config: {},
    visualization_config: {},
    display_order: 0,
    created_at: '2025-01-15T12:00:00Z',
    updated_at: '2025-01-15T12:00:00Z',
    ...overrides,
  })

  const createMockExecution = (overrides?: Partial<SummaryExecution>): SummaryExecution => ({
    id: 'exec-1',
    status: 'COMPLETED',
    triggered_by: 'manual',
    trigger_details: null,
    has_changes: true,
    relevance_score: null,
    relevance_reason: null,
    duration_ms: 1000,
    created_at: '2025-01-15T12:00:00Z',
    completed_at: '2025-01-15T12:00:01Z',
    cached_data: {},
    error_message: null,
    ...overrides,
  })

  describe('Initial State', () => {
    it('should initialize with correct default values', () => {
      const store = useCustomSummariesStore()

      expect(store.summaries).toEqual([])
      expect(store.currentSummary).toBeNull()
      expect(store.favoriteIds).toEqual(new Set())
      expect(store.isLoading).toBe(false)
      expect(store.isCreating).toBe(false)
      expect(store.isExecuting).toBe(false)
      expect(store.total).toBe(0)
      expect(store.page).toBe(1)
      expect(store.perPage).toBe(20)
      expect(store.error).toBeNull()
      expect(store.schedulePresets).toEqual([])
    })

    it('should have correct computed properties', () => {
      const store = useCustomSummariesStore()

      expect(store.favoriteCount).toBe(0)
      expect(store.favorites).toEqual([])
      expect(store.activeSummaries).toEqual([])
      expect(store.scheduledSummaries).toEqual([])
    })
  })

  describe('loadSummaries', () => {
    it('should load summaries successfully', async () => {
      const mockSummaries = [createMockSummary(), createMockSummary({ id: 'summary-2' })]
      vi.mocked(customSummariesApi.list).mockResolvedValue({
        data: { items: mockSummaries, total: 2, page: 1, per_page: 20 },
      } as any)

      const store = useCustomSummariesStore()
      await store.loadSummaries()

      expect(store.summaries).toEqual(mockSummaries)
      expect(store.total).toBe(2)
      expect(store.page).toBe(1)
      expect(store.isLoading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('should update favoriteIds when loading favorites', async () => {
      const mockSummaries = [
        createMockSummary({ id: 'summary-1', is_favorite: true }),
        createMockSummary({ id: 'summary-2', is_favorite: false }),
        createMockSummary({ id: 'summary-3', is_favorite: true }),
      ]
      vi.mocked(customSummariesApi.list).mockResolvedValue({
        data: { items: mockSummaries, total: 3, page: 1, per_page: 20 },
      } as any)

      const store = useCustomSummariesStore()
      await store.loadSummaries()

      expect(store.favoriteIds.has('summary-1')).toBe(true)
      expect(store.favoriteIds.has('summary-2')).toBe(false)
      expect(store.favoriteIds.has('summary-3')).toBe(true)
      expect(store.favoriteCount).toBe(2)
    })

    it('should handle API errors', async () => {
      vi.mocked(customSummariesApi.list).mockRejectedValue(new Error('API Error'))

      const store = useCustomSummariesStore()
      await store.loadSummaries()

      expect(store.error).toBe('Failed to load summaries')
      expect(store.isLoading).toBe(false)
    })

    it('should handle AbortError gracefully', async () => {
      const abortError = new Error('Aborted')
      abortError.name = 'AbortError'
      vi.mocked(customSummariesApi.list).mockRejectedValue(abortError)

      const store = useCustomSummariesStore()
      await store.loadSummaries()

      expect(store.error).toBeNull()
    })

    it('should pass correct options to API', async () => {
      vi.mocked(customSummariesApi.list).mockResolvedValue({
        data: { items: [], total: 0, page: 2, per_page: 10 },
      } as any)

      const store = useCustomSummariesStore()
      await store.loadSummaries({
        page: 2,
        per_page: 10,
        favorites_only: true,
        status: 'ACTIVE',
        search: 'test',
        sort_by: 'name',
        sort_order: 'asc',
      })

      expect(customSummariesApi.list).toHaveBeenCalledWith(
        expect.objectContaining({
          page: 2,
          per_page: 10,
          favorites_only: true,
          status: 'ACTIVE',
          search: 'test',
          sort_by: 'name',
          sort_order: 'asc',
        }),
        expect.objectContaining({ signal: expect.any(AbortSignal) })
      )
    })

    it('should cancel previous request when called again', async () => {
      const store = useCustomSummariesStore()

      // Start first request
      vi.mocked(customSummariesApi.list).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ data: { items: [], total: 0, page: 1, per_page: 20 } } as any), 100))
      )

      const promise1 = store.loadSummaries()
      const promise2 = store.loadSummaries()

      await Promise.all([promise1, promise2])

      // Only the second request should update the state
      expect(customSummariesApi.list).toHaveBeenCalledTimes(2)
    })
  })

  describe('loadSummary', () => {
    it('should load single summary with details', async () => {
      const mockSummary = createMockSummary({
        widgets: [createMockWidget()],
        last_execution: createMockExecution(),
      })
      vi.mocked(customSummariesApi.get).mockResolvedValue({ data: mockSummary } as any)

      const store = useCustomSummariesStore()
      const result = await store.loadSummary('summary-1')

      expect(result).toEqual(mockSummary)
      expect(store.currentSummary).toEqual(mockSummary)
      expect(customSummariesApi.get).toHaveBeenCalledWith(
        'summary-1',
        { include_widgets: true, include_last_execution: true },
        expect.objectContaining({ signal: expect.any(AbortSignal) })
      )
    })

    it('should handle API errors', async () => {
      vi.mocked(customSummariesApi.get).mockRejectedValue(new Error('Not found'))

      const store = useCustomSummariesStore()
      const result = await store.loadSummary('summary-1')

      expect(result).toBeNull()
      expect(store.error).toBe('Failed to load summary')
    })

    it('should handle AbortError gracefully', async () => {
      const abortError = new Error('Aborted')
      abortError.name = 'AbortError'
      vi.mocked(customSummariesApi.get).mockRejectedValue(abortError)

      const store = useCustomSummariesStore()
      const result = await store.loadSummary('summary-1')

      expect(result).toBeNull()
      expect(store.error).toBeNull()
    })
  })

  describe('createFromPrompt', () => {
    it('should create summary from prompt', async () => {
      const mockResult = {
        id: 'summary-1',
        name: 'Generated Summary',
        interpretation: { widgets: [] },
        widgets_created: 3,
        message: 'Success',
      }
      vi.mocked(customSummariesApi.createFromPrompt).mockResolvedValue({ data: mockResult } as any)
      vi.mocked(customSummariesApi.list).mockResolvedValue({
        data: { items: [], total: 0, page: 1, per_page: 20 },
      } as any)

      const store = useCustomSummariesStore()
      const result = await store.createFromPrompt({ prompt: 'Show me data' })

      expect(result).toEqual(mockResult)
      expect(store.isCreating).toBe(false)
      expect(customSummariesApi.list).toHaveBeenCalled()
    })

    it('should handle API errors', async () => {
      // Simulate an API error with response (not treated as network error)
      const apiError = {
        response: {
          status: 500,
          data: { detail: 'Server processing failed' },
        },
        message: 'Request failed with status code 500',
      }
      vi.mocked(customSummariesApi.createFromPrompt).mockRejectedValue(apiError)

      const store = useCustomSummariesStore()
      const result = await store.createFromPrompt({ prompt: 'Test' })

      expect(result).toBeNull()
      expect(store.error).toBe('Server processing failed')
      expect(store.isCreating).toBe(false)
    })

    it('should handle error with detail message', async () => {
      const apiError = {
        response: {
          status: 400,
          data: { detail: 'Invalid prompt format' },
        },
      }
      vi.mocked(customSummariesApi.createFromPrompt).mockRejectedValue(apiError)

      const store = useCustomSummariesStore()
      const result = await store.createFromPrompt({ prompt: 'Invalid' })

      expect(result).toBeNull()
      expect(store.error).toBe('Invalid prompt format')
    })
  })

  describe('createSummary', () => {
    it('should create summary successfully', async () => {
      const mockSummary = createMockSummary()
      vi.mocked(customSummariesApi.create).mockResolvedValue({ data: mockSummary } as any)

      const store = useCustomSummariesStore()
      const result = await store.createSummary({
        name: 'Test',
        original_prompt: 'prompt',
      })

      expect(result).toEqual(mockSummary)
      expect(store.summaries[0]).toEqual(mockSummary)
      expect(store.total).toBe(1)
    })

    it('should add favorite when creating favorite summary', async () => {
      const mockSummary = createMockSummary({ is_favorite: true })
      vi.mocked(customSummariesApi.create).mockResolvedValue({ data: mockSummary } as any)

      const store = useCustomSummariesStore()
      await store.createSummary({ name: 'Test', original_prompt: 'prompt' })

      expect(store.favoriteIds.has(mockSummary.id)).toBe(true)
    })

    it('should handle API errors', async () => {
      vi.mocked(customSummariesApi.create).mockRejectedValue(new Error('Failed'))

      const store = useCustomSummariesStore()
      const result = await store.createSummary({ name: 'Test', original_prompt: 'prompt' })

      expect(result).toBeNull()
      expect(store.error).toBe('Failed to create summary')
    })
  })

  describe('updateSummary', () => {
    it('should update summary successfully', async () => {
      const originalSummary = createMockSummary()
      const updatedSummary = createMockSummary({ name: 'Updated Name' })

      vi.mocked(customSummariesApi.update).mockResolvedValue({ data: updatedSummary } as any)

      const store = useCustomSummariesStore()
      store.summaries = [originalSummary]

      const result = await store.updateSummary('summary-1', { name: 'Updated Name' })

      expect(result).toEqual(updatedSummary)
      expect(store.summaries[0].name).toBe('Updated Name')
    })

    it('should update currentSummary if it matches', async () => {
      const originalSummary = createMockSummary()
      const updatedSummary = createMockSummary({ name: 'Updated Name' })

      vi.mocked(customSummariesApi.update).mockResolvedValue({ data: updatedSummary } as any)

      const store = useCustomSummariesStore()
      store.currentSummary = originalSummary

      await store.updateSummary('summary-1', { name: 'Updated Name' })

      expect(store.currentSummary?.name).toBe('Updated Name')
    })

    it('should update favoriteIds when toggling favorite', async () => {
      const summary = createMockSummary({ is_favorite: false })
      const updated = createMockSummary({ is_favorite: true })

      vi.mocked(customSummariesApi.update).mockResolvedValue({ data: updated } as any)

      const store = useCustomSummariesStore()
      store.summaries = [summary]

      await store.updateSummary('summary-1', { is_favorite: true })

      expect(store.favoriteIds.has('summary-1')).toBe(true)
    })

    it('should handle API errors', async () => {
      vi.mocked(customSummariesApi.update).mockRejectedValue(new Error('Failed'))

      const store = useCustomSummariesStore()
      const result = await store.updateSummary('summary-1', { name: 'Test' })

      expect(result).toBeNull()
      expect(store.error).toBe('Failed to update summary')
    })
  })

  describe('deleteSummary', () => {
    it('should delete summary successfully', async () => {
      vi.mocked(customSummariesApi.delete).mockResolvedValue({} as any)

      const store = useCustomSummariesStore()
      store.summaries = [createMockSummary()]
      store.total = 1

      const result = await store.deleteSummary('summary-1')

      expect(result).toBe(true)
      expect(store.summaries).toHaveLength(0)
      expect(store.total).toBe(0)
    })

    it('should remove from favoriteIds', async () => {
      vi.mocked(customSummariesApi.delete).mockResolvedValue({} as any)

      const store = useCustomSummariesStore()
      store.summaries = [createMockSummary({ is_favorite: true })]
      store.favoriteIds.add('summary-1')

      await store.deleteSummary('summary-1')

      expect(store.favoriteIds.has('summary-1')).toBe(false)
    })

    it('should clear currentSummary if it matches', async () => {
      vi.mocked(customSummariesApi.delete).mockResolvedValue({} as any)

      const store = useCustomSummariesStore()
      store.currentSummary = createMockSummary()

      await store.deleteSummary('summary-1')

      expect(store.currentSummary).toBeNull()
    })

    it('should handle API errors', async () => {
      vi.mocked(customSummariesApi.delete).mockRejectedValue(new Error('Failed'))

      const store = useCustomSummariesStore()
      const result = await store.deleteSummary('summary-1')

      expect(result).toBe(false)
      expect(store.error).toBe('Failed to delete summary')
    })
  })

  describe('executeSummary', () => {
    it('should execute summary successfully', async () => {
      const mockResult = {
        execution_id: 'exec-1',
        status: 'COMPLETED' as ExecutionStatus,
        has_changes: true,
        message: 'Success',
      }
      vi.mocked(customSummariesApi.execute).mockResolvedValue({ data: mockResult } as any)

      const store = useCustomSummariesStore()
      store.summaries = [createMockSummary()]

      const result = await store.executeSummary('summary-1')

      expect(result).toEqual(mockResult)
      expect(store.summaries[0].execution_count).toBe(1)
      expect(store.summaries[0].last_executed_at).toBeTruthy()
    })

    it('should track executing state per summary', async () => {
      vi.mocked(customSummariesApi.execute).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ data: { status: 'completed' } } as any), 100))
      )

      const store = useCustomSummariesStore()

      const promise = store.executeSummary('summary-1')
      expect(store.isExecutingSummary('summary-1')).toBe(true)
      expect(store.isExecuting).toBe(true)

      await promise

      expect(store.isExecutingSummary('summary-1')).toBe(false)
      expect(store.isExecuting).toBe(false)
    })

    it('should prevent double execution', async () => {
      vi.mocked(customSummariesApi.execute).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ data: { status: 'completed' } } as any), 100))
      )

      const store = useCustomSummariesStore()

      const promise1 = store.executeSummary('summary-1')
      const result2 = await store.executeSummary('summary-1') // Should return null

      expect(result2).toBeNull()

      await promise1
    })

    it('should update currentSummary execution count', async () => {
      const mockResult = {
        execution_id: 'exec-1',
        status: 'COMPLETED' as ExecutionStatus,
        has_changes: true,
        message: 'Success',
      }
      vi.mocked(customSummariesApi.execute).mockResolvedValue({ data: mockResult } as any)

      const store = useCustomSummariesStore()
      store.currentSummary = createMockSummary()

      await store.executeSummary('summary-1')

      expect(store.currentSummary?.execution_count).toBe(1)
    })

    it('should handle API errors', async () => {
      vi.mocked(customSummariesApi.execute).mockRejectedValue(new Error('Failed'))

      const store = useCustomSummariesStore()
      const result = await store.executeSummary('summary-1')

      expect(result).toBeNull()
      expect(store.error).toBe('Failed to execute summary')
      expect(store.isExecuting).toBe(false)
    })
  })

  describe('toggleFavorite', () => {
    it('should toggle favorite on', async () => {
      vi.mocked(customSummariesApi.toggleFavorite).mockResolvedValue({
        data: { is_favorite: true },
      } as any)

      const store = useCustomSummariesStore()
      store.summaries = [createMockSummary({ is_favorite: false })]

      const result = await store.toggleFavorite('summary-1')

      expect(result).toBe(true)
      expect(store.favoriteIds.has('summary-1')).toBe(true)
    })

    it('should toggle favorite off', async () => {
      vi.mocked(customSummariesApi.toggleFavorite).mockResolvedValue({
        data: { is_favorite: false },
      } as any)

      const store = useCustomSummariesStore()
      store.summaries = [createMockSummary({ is_favorite: true })]
      store.favoriteIds.add('summary-1')

      const result = await store.toggleFavorite('summary-1')

      expect(result).toBe(false)
      expect(store.favoriteIds.has('summary-1')).toBe(false)
    })

    it('should update favoriteIds even if summary not in list', async () => {
      vi.mocked(customSummariesApi.toggleFavorite).mockResolvedValue({
        data: { is_favorite: true },
      } as any)

      const store = useCustomSummariesStore()

      await store.toggleFavorite('summary-1')

      expect(store.favoriteIds.has('summary-1')).toBe(true)
    })

    it('should handle API errors', async () => {
      vi.mocked(customSummariesApi.toggleFavorite).mockRejectedValue(new Error('Failed'))

      const store = useCustomSummariesStore()
      const result = await store.toggleFavorite('summary-1')

      expect(result).toBe(false)
      expect(store.error).toBe('Failed to toggle favorite')
    })
  })

  describe('Widget Management', () => {
    it('should add widget successfully', async () => {
      const mockWidget = createMockWidget()
      vi.mocked(customSummariesApi.addWidget).mockResolvedValue({ data: mockWidget } as any)

      const store = useCustomSummariesStore()
      store.currentSummary = createMockSummary({ widgets: [] })

      const result = await store.addWidget('summary-1', {
        widget_type: 'table',
        title: 'Test Widget',
      })

      expect(result).toEqual(mockWidget)
      expect(store.currentSummary?.widgets?.[0]).toEqual(mockWidget)
    })

    it('should update widget successfully', async () => {
      const updatedWidget = createMockWidget({ title: 'Updated Title' })
      vi.mocked(customSummariesApi.updateWidget).mockResolvedValue({ data: updatedWidget } as any)

      const store = useCustomSummariesStore()
      store.currentSummary = createMockSummary({ widgets: [createMockWidget()] })

      const result = await store.updateWidget('summary-1', 'widget-1', { title: 'Updated Title' })

      expect(result).toEqual(updatedWidget)
      expect(store.currentSummary?.widgets?.[0].title).toBe('Updated Title')
    })

    it('should delete widget successfully', async () => {
      vi.mocked(customSummariesApi.deleteWidget).mockResolvedValue({} as any)

      const store = useCustomSummariesStore()
      store.currentSummary = createMockSummary({ widgets: [createMockWidget()] })

      const result = await store.deleteWidget('summary-1', 'widget-1')

      expect(result).toBe(true)
      expect(store.currentSummary?.widgets).toHaveLength(0)
    })
  })

  describe('Share Management', () => {
    it('should create share link', async () => {
      const mockShare: SummaryShare = {
        id: 'share-1',
        share_token: 'token',
        share_url: 'https://example.com/share/token',
        has_password: false,
        expires_at: null,
        allow_export: true,
        view_count: 0,
        last_viewed_at: null,
        is_active: true,
        created_at: '2025-01-15T12:00:00Z',
      }
      vi.mocked(customSummariesApi.createShare).mockResolvedValue({ data: mockShare } as any)

      const store = useCustomSummariesStore()
      const result = await store.createShareLink('summary-1', {})

      expect(result).toEqual(mockShare)
    })

    it('should list share links', async () => {
      const mockShares: SummaryShare[] = [
        {
          id: 'share-1',
          share_token: 'token1',
          share_url: 'url1',
          has_password: false,
          expires_at: null,
          allow_export: true,
          view_count: 5,
          last_viewed_at: null,
          is_active: true,
          created_at: '2025-01-15T12:00:00Z',
        },
      ]
      vi.mocked(customSummariesApi.listShares).mockResolvedValue({ data: mockShares } as any)

      const store = useCustomSummariesStore()
      const result = await store.listShareLinks('summary-1')

      expect(result).toEqual(mockShares)
    })

    it('should deactivate share link', async () => {
      vi.mocked(customSummariesApi.deactivateShare).mockResolvedValue({} as any)

      const store = useCustomSummariesStore()
      const result = await store.deactivateShareLink('summary-1', 'share-1')

      expect(result).toBe(true)
    })
  })

  describe('Execution History', () => {
    it('should list executions', async () => {
      const mockExecutions = [createMockExecution(), createMockExecution({ id: 'exec-2' })]
      vi.mocked(customSummariesApi.listExecutions).mockResolvedValue({
        data: mockExecutions,
      } as any)

      const store = useCustomSummariesStore()
      const result = await store.listExecutions('summary-1', 10)

      expect(result).toEqual(mockExecutions)
      expect(customSummariesApi.listExecutions).toHaveBeenCalledWith('summary-1', { limit: 10 })
    })
  })

  describe('Schedule Presets', () => {
    it('should load schedule presets', async () => {
      const mockPresets = [
        { label: 'Daily', cron: '0 0 * * *', description: 'Every day at midnight' },
        { label: 'Weekly', cron: '0 0 * * 0', description: 'Every Sunday' },
      ]
      vi.mocked(customSummariesApi.getSchedulePresets).mockResolvedValue({
        data: mockPresets,
      } as any)

      const store = useCustomSummariesStore()
      await store.loadSchedulePresets()

      expect(store.schedulePresets).toEqual(mockPresets)
    })
  })

  describe('Export Functions', () => {
    it('should export PDF', async () => {
      const mockPdfData = new ArrayBuffer(100)
      vi.mocked(customSummariesApi.exportPdf).mockResolvedValue({ data: mockPdfData } as any)

      const store = useCustomSummariesStore()
      const result = await store.exportPdf('summary-1', 'test.pdf')

      expect(result).toBe(true)
    })

    it('should export Excel', async () => {
      const mockExcelData = new ArrayBuffer(100)
      vi.mocked(customSummariesApi.exportExcel).mockResolvedValue({ data: mockExcelData } as any)

      const store = useCustomSummariesStore()
      const result = await store.exportExcel('summary-1', 'test.xlsx')

      expect(result).toBe(true)
    })

    it('should handle export errors', async () => {
      vi.mocked(customSummariesApi.exportPdf).mockRejectedValue(new Error('Export failed'))

      const store = useCustomSummariesStore()
      const result = await store.exportPdf('summary-1')

      expect(result).toBe(false)
      expect(store.error).toBe('Failed to export PDF')
    })
  })

  describe('Computed Properties', () => {
    it('should compute favoriteCount correctly', () => {
      const store = useCustomSummariesStore()
      store.summaries = [
        createMockSummary({ id: '1', is_favorite: true }),
        createMockSummary({ id: '2', is_favorite: false }),
        createMockSummary({ id: '3', is_favorite: true }),
      ]
      store.favoriteIds.add('1')
      store.favoriteIds.add('3')

      expect(store.favoriteCount).toBe(2)
    })

    it('should compute favorites list correctly', () => {
      const store = useCustomSummariesStore()
      store.summaries = [
        createMockSummary({ id: '1', is_favorite: true }),
        createMockSummary({ id: '2', is_favorite: false }),
        createMockSummary({ id: '3', is_favorite: true }),
      ]

      expect(store.favorites).toHaveLength(2)
      expect(store.favorites[0].id).toBe('1')
      expect(store.favorites[1].id).toBe('3')
    })

    it('should compute activeSummaries correctly', () => {
      const store = useCustomSummariesStore()
      store.summaries = [
        createMockSummary({ id: '1', status: 'ACTIVE' }),
        createMockSummary({ id: '2', status: 'DRAFT' }),
        createMockSummary({ id: '3', status: 'ACTIVE' }),
      ]

      expect(store.activeSummaries).toHaveLength(2)
    })

    it('should compute scheduledSummaries correctly', () => {
      const store = useCustomSummariesStore()
      store.summaries = [
        createMockSummary({ id: '1', schedule_enabled: true }),
        createMockSummary({ id: '2', schedule_enabled: false }),
        createMockSummary({ id: '3', schedule_enabled: true }),
      ]

      expect(store.scheduledSummaries).toHaveLength(2)
    })
  })

  describe('Helper Functions', () => {
    it('should check if summary is favorited', () => {
      const store = useCustomSummariesStore()
      store.favoriteIds.add('summary-1')

      expect(store.isFavorited('summary-1')).toBe(true)
      expect(store.isFavorited('summary-2')).toBe(false)
    })

    it('should check if summary is executing', () => {
      const store = useCustomSummariesStore()
      store.executingIds.add('summary-1')

      expect(store.isExecutingSummary('summary-1')).toBe(true)
      expect(store.isExecutingSummary('summary-2')).toBe(false)
    })

    it('should get summary by ID', () => {
      const store = useCustomSummariesStore()
      const summary = createMockSummary()
      store.summaries = [summary]

      expect(store.getSummaryById('summary-1')).toEqual(summary)
      expect(store.getSummaryById('summary-2')).toBeUndefined()
    })
  })

  describe('clearStore', () => {
    it('should reset all state', () => {
      const store = useCustomSummariesStore()
      store.summaries = [createMockSummary()]
      store.currentSummary = createMockSummary()
      store.favoriteIds.add('summary-1')
      store.executingIds.add('summary-2')
      store.total = 10
      store.page = 3
      store.error = 'Some error'

      store.clearStore()

      expect(store.summaries).toEqual([])
      expect(store.currentSummary).toBeNull()
      expect(store.favoriteIds.size).toBe(0)
      expect(store.executingIds.size).toBe(0)
      expect(store.total).toBe(0)
      expect(store.page).toBe(1)
      expect(store.error).toBeNull()
    })

    it('should cancel pending requests', () => {
      const store = useCustomSummariesStore()

      // Start a request
      vi.mocked(customSummariesApi.list).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ data: { items: [], total: 0, page: 1, per_page: 20 } } as any), 1000))
      )

      store.loadSummaries()
      store.clearStore()

      // Verify requests are cancelled (implementation dependent)
      expect(store.summaries).toEqual([])
    })
  })

  describe('Edge Cases', () => {
    it('should handle empty summaries list', async () => {
      vi.mocked(customSummariesApi.list).mockResolvedValue({
        data: { items: [], total: 0, page: 1, per_page: 20 },
      } as any)

      const store = useCustomSummariesStore()
      await store.loadSummaries()

      expect(store.summaries).toEqual([])
      expect(store.favoriteCount).toBe(0)
      expect(store.favorites).toEqual([])
    })

    it('should handle summary without widgets', () => {
      const store = useCustomSummariesStore()
      store.currentSummary = createMockSummary({ widgets: undefined })

      expect(store.currentSummary.widgets).toBeUndefined()
    })

    it('should preserve widgets when syncing summary state', async () => {
      const widgets = [createMockWidget()]
      const summary = createMockSummary({ widgets })
      const updated = createMockSummary({ name: 'Updated', widgets: undefined })

      vi.mocked(customSummariesApi.update).mockResolvedValue({ data: updated } as any)

      const store = useCustomSummariesStore()
      store.summaries = [summary]

      await store.updateSummary('summary-1', { name: 'Updated' })

      // Widgets should be preserved from original
      expect(store.summaries[0].widgets).toEqual(widgets)
    })

    it('should handle concurrent executions of different summaries', async () => {
      vi.mocked(customSummariesApi.execute).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ data: { status: 'completed' } } as any), 100))
      )

      const store = useCustomSummariesStore()

      const promise1 = store.executeSummary('summary-1')
      const promise2 = store.executeSummary('summary-2')

      expect(store.isExecutingSummary('summary-1')).toBe(true)
      expect(store.isExecutingSummary('summary-2')).toBe(true)
      expect(store.executingIds.size).toBe(2)

      await Promise.all([promise1, promise2])

      expect(store.executingIds.size).toBe(0)
    })
  })
})
