/**
 * Tests for useFeatureFlags composable
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// We need to reset the module state between tests
let useFeatureFlags: typeof import('./useFeatureFlags').useFeatureFlags

// Mock API
const mockApiGet = vi.fn()
vi.mock('@/services/api', () => ({
  api: {
    get: (...args: unknown[]) => mockApiGet(...args),
  },
}))

describe('useFeatureFlags', () => {
  beforeEach(async () => {
    vi.clearAllMocks()

    // Reset module state by re-importing
    vi.resetModules()
    const module = await import('./useFeatureFlags')
    useFeatureFlags = module.useFeatureFlags
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('initial state', () => {
    it('should return flags, loaded, and loadFeatureFlags', () => {
      const result = useFeatureFlags()

      expect(result.flags).toBeDefined()
      expect(result.loaded).toBeDefined()
      expect(result.loadFeatureFlags).toBeInstanceOf(Function)
    })

    it('should have default flag values', () => {
      const { flags } = useFeatureFlags()

      expect(flags.value.entityLevelFacets).toBe(false)
      expect(flags.value.pysisFieldTemplates).toBe(false)
      expect(flags.value.entityHierarchyEnabled).toBe(false)
    })

    it('should not be loaded initially', () => {
      const { loaded } = useFeatureFlags()

      expect(loaded.value).toBe(false)
    })
  })

  describe('loadFeatureFlags', () => {
    it('should load feature flags from API', async () => {
      mockApiGet.mockResolvedValue({
        data: {
          entityLevelFacets: true,
          pysisFieldTemplates: true,
          entityHierarchyEnabled: true,
        },
      })

      const { flags, loaded, loadFeatureFlags } = useFeatureFlags()

      await loadFeatureFlags()

      expect(mockApiGet).toHaveBeenCalledWith('/config/features')
      expect(flags.value.entityLevelFacets).toBe(true)
      expect(flags.value.pysisFieldTemplates).toBe(true)
      expect(flags.value.entityHierarchyEnabled).toBe(true)
      expect(loaded.value).toBe(true)
    })

    it('should only load once', async () => {
      mockApiGet.mockResolvedValue({
        data: {
          entityLevelFacets: true,
          pysisFieldTemplates: false,
          entityHierarchyEnabled: false,
        },
      })

      const { loadFeatureFlags } = useFeatureFlags()

      await loadFeatureFlags()
      await loadFeatureFlags()
      await loadFeatureFlags()

      expect(mockApiGet).toHaveBeenCalledTimes(1)
    })

    it('should handle API errors gracefully', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      mockApiGet.mockRejectedValue(new Error('Network error'))

      const { flags, loaded, loadFeatureFlags } = useFeatureFlags()

      await loadFeatureFlags()

      // Should not throw, flags should remain default
      expect(flags.value.entityLevelFacets).toBe(false)
      expect(loaded.value).toBe(false)
      expect(consoleSpy).toHaveBeenCalledWith(
        'Failed to load feature flags',
        expect.any(Error)
      )

      consoleSpy.mockRestore()
    })

    it('should share state between composable instances', async () => {
      mockApiGet.mockResolvedValue({
        data: {
          entityLevelFacets: true,
          pysisFieldTemplates: false,
          entityHierarchyEnabled: false,
        },
      })

      const instance1 = useFeatureFlags()
      const instance2 = useFeatureFlags()

      await instance1.loadFeatureFlags()

      // instance2 should see the loaded flags
      expect(instance2.flags.value.entityLevelFacets).toBe(true)
      expect(instance2.loaded.value).toBe(true)
    })
  })

  describe('flags readonly', () => {
    it('should expose flags as readonly ref', () => {
      const { flags } = useFeatureFlags()

      // The flags should be a readonly ref - verify the structure
      expect(flags).toHaveProperty('value')
      expect(flags.value).toHaveProperty('entityLevelFacets')
    })

    it('should expose loaded as readonly ref', () => {
      const { loaded } = useFeatureFlags()

      // The loaded should be a readonly ref - verify the structure
      expect(loaded).toHaveProperty('value')
      expect(typeof loaded.value).toBe('boolean')
    })
  })
})
