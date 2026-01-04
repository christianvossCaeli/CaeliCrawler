/**
 * Tests for Results composables
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useResultsView, useResultsHelpers } from '../results'

// Mock dependencies
vi.mock('@/services/api', () => ({
  dataApi: {
    getExtractedData: vi.fn().mockResolvedValue({
      data: { items: [], total: 0 },
    }),
    getExtractionStats: vi.fn().mockResolvedValue({
      data: { total: 0, verified: 0, high_confidence_count: 0, avg_confidence: 0 },
    }),
    getExtractionLocations: vi.fn().mockResolvedValue({ data: [] }),
    bulkVerifyExtractions: vi.fn().mockResolvedValue({
      data: { verified_ids: [], failed_ids: [], verified_count: 0, failed_count: 0 },
    }),
  },
  adminApi: {
    getCategories: vi.fn().mockResolvedValue({ data: { items: [] } }),
  },
  facetApi: {
    getFacetTypesForCategory: vi.fn().mockResolvedValue({ data: [] }),
  },
}))

vi.mock('@/composables/useSnackbar', () => ({
  useSnackbar: () => ({
    showSuccess: vi.fn(),
    showError: vi.fn(),
  }),
}))

vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    debug: vi.fn(),
  }),
}))

vi.mock('@/composables/useDateFormatter', () => ({
  useDateFormatter: () => ({
    formatDate: vi.fn((date: string) => date),
  }),
}))

vi.mock('@/composables/useFacetTypeRenderer', () => ({
  useFacetTypeRenderer: () => ({
    getValuesForFacetType: vi.fn(() => []),
    hasValues: vi.fn(() => false),
    normalizeValue: vi.fn((v: unknown) => v),
    getPrimaryValue: vi.fn(() => ''),
  }),
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    isEditor: true,
    isAdmin: true,
  }),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({
    query: {},
  }),
}))

describe('useResultsView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('initialization', () => {
    it('should return all expected properties', () => {
      const result = useResultsView()

      // State
      expect(result.loading).toBeDefined()
      expect(result.initialLoad).toBeDefined()
      expect(result.results).toBeDefined()
      expect(result.totalResults).toBeDefined()
      expect(result.stats).toBeDefined()

      // Filters
      expect(result.searchQuery).toBeDefined()
      expect(result.minConfidence).toBeDefined()
      expect(result.verifiedFilter).toBeDefined()

      // Methods
      expect(result.loadData).toBeDefined()
      expect(result.clearFilters).toBeDefined()
      expect(result.initialize).toBeDefined()
    })

    it('should have correct default values', () => {
      const result = useResultsView()

      expect(result.loading.value).toBe(true)
      expect(result.initialLoad.value).toBe(true)
      expect(result.results.value).toEqual([])
      expect(result.totalResults.value).toBe(0)
      expect(result.minConfidence.value).toBe(0)
      expect(result.verifiedFilter.value).toBeNull()
    })
  })

  describe('filter actions', () => {
    it('clearFilters should reset all filters', () => {
      const result = useResultsView()

      // Set some filter values
      result.searchQuery.value = 'test'
      result.minConfidence.value = 50
      result.verifiedFilter.value = true

      // Clear filters
      result.clearFilters()

      // Verify reset
      expect(result.searchQuery.value).toBe('')
      expect(result.minConfidence.value).toBe(0)
      expect(result.verifiedFilter.value).toBeNull()
      expect(result.page.value).toBe(1)
    })

    it('toggleVerifiedFilter should toggle filter correctly', () => {
      const result = useResultsView()

      // Initially null
      expect(result.verifiedFilter.value).toBeNull()

      // Toggle to true
      result.toggleVerifiedFilter(true)
      expect(result.verifiedFilter.value).toBe(true)

      // Toggle same value should reset to null
      result.toggleVerifiedFilter(true)
      expect(result.verifiedFilter.value).toBeNull()
    })
  })

  describe('computed properties', () => {
    it('hasActiveFilters should detect active filters', () => {
      const result = useResultsView()

      // Initially no filters should be active
      expect(result.hasActiveFilters.value).toBeFalsy()

      result.searchQuery.value = 'test'
      expect(result.hasActiveFilters.value).toBeTruthy()

      result.searchQuery.value = ''
      result.minConfidence.value = 50
      expect(result.hasActiveFilters.value).toBeTruthy()
    })

    it('canVerify should reflect auth state', () => {
      const result = useResultsView()
      expect(result.canVerify.value).toBe(true)
    })
  })
})

describe('useResultsHelpers', () => {
  describe('getConfidenceColor', () => {
    it('should return correct colors based on thresholds', () => {
      const { getConfidenceColor } = useResultsHelpers()

      expect(getConfidenceColor(0.9)).toBe('success') // >= 0.8
      expect(getConfidenceColor(0.8)).toBe('success')
      expect(getConfidenceColor(0.7)).toBe('warning') // >= 0.6
      expect(getConfidenceColor(0.5)).toBe('error') // < 0.6
      expect(getConfidenceColor(0.3)).toBe('error')
      expect(getConfidenceColor(undefined)).toBe('grey')
      expect(getConfidenceColor(null)).toBe('grey')
    })
  })

  describe('getSeverityColor', () => {
    it('should return correct colors', () => {
      const { getSeverityColor } = useResultsHelpers()

      expect(getSeverityColor('high')).toBe('error')
      expect(getSeverityColor('hoch')).toBe('error')
      expect(getSeverityColor('medium')).toBe('warning')
      expect(getSeverityColor('mittel')).toBe('warning')
      expect(getSeverityColor('low')).toBe('info')
      expect(getSeverityColor('niedrig')).toBe('info')
      expect(getSeverityColor('unknown')).toBe('grey')
    })
  })

  describe('getPriorityColor', () => {
    it('should return correct colors', () => {
      const { getPriorityColor } = useResultsHelpers()

      expect(getPriorityColor('high')).toBe('error')
      expect(getPriorityColor('medium')).toBe('warning')
      expect(getPriorityColor('low')).toBe('info')
      expect(getPriorityColor('unknown')).toBe('grey')
    })
  })

  describe('getEntityTypeColor', () => {
    it('should return correct colors for known types', () => {
      const { getEntityTypeColor } = useResultsHelpers()

      expect(getEntityTypeColor('territorial-entity')).toBe('primary')
      expect(getEntityTypeColor('person')).toBe('info')
      expect(getEntityTypeColor('organization')).toBe('secondary')
      expect(getEntityTypeColor('event')).toBe('warning')
      expect(getEntityTypeColor('unknown')).toBe('grey')
    })
  })

  describe('getEntityTypeIcon', () => {
    it('should return correct icons for known types', () => {
      const { getEntityTypeIcon } = useResultsHelpers()

      expect(getEntityTypeIcon('territorial-entity')).toBe('mdi-map-marker')
      expect(getEntityTypeIcon('person')).toBe('mdi-account')
      expect(getEntityTypeIcon('organization')).toBe('mdi-domain')
      expect(getEntityTypeIcon('event')).toBe('mdi-calendar')
      expect(getEntityTypeIcon('unknown')).toBe('mdi-tag')
    })
  })

  describe('formatConfidence', () => {
    it('should format confidence score as percentage', () => {
      const { formatConfidence } = useResultsHelpers()

      expect(formatConfidence(0.85)).toBe('85%')
      expect(formatConfidence(1.0)).toBe('100%')
      expect(formatConfidence(0.0)).toBe('0%')
      expect(formatConfidence(null)).toBe('-')
      expect(formatConfidence(undefined)).toBe('-')
    })
  })

  describe('formatFieldLabel', () => {
    it('should convert snake_case to Title Case', () => {
      const { formatFieldLabel } = useResultsHelpers()

      expect(formatFieldLabel('pain_points')).toBe('Pain Points')
      expect(formatFieldLabel('decision_makers')).toBe('Decision Makers')
      expect(formatFieldLabel('simple')).toBe('Simple')
    })
  })
})
