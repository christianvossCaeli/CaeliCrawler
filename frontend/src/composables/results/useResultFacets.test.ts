/**
 * Tests for useResultFacets composable
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ref, type Ref } from 'vue'
import { useResultFacets } from './useResultFacets'
import { mockAxiosResponse } from '@/test/setup'
import type { FacetValue } from '@/types/entity'

// Mock the API modules
vi.mock('@/services/api', () => ({
  dataApi: {
    getExtractionFacets: vi.fn(),
  },
  facetApi: {
    verifyFacetValue: vi.fn(),
    updateFacetValue: vi.fn(),
  },
}))

// Mock vue-i18n
vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string) => key,
  }),
}))

// Mock useSnackbar
vi.mock('@/composables/useSnackbar', () => ({
  useSnackbar: () => ({
    showSuccess: vi.fn(),
    showError: vi.fn(),
  }),
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

// Mock error message utility
vi.mock('@/utils/errorMessage', () => ({
  getErrorMessage: (error: Error) => error.message,
}))

// Import mocked modules
import { dataApi, facetApi } from '@/services/api'

// Mock facet data
const mockFacets: FacetValue[] = [
  {
    id: 'facet-1',
    entity_id: 'entity-1',
    entity_name: 'Test Entity',
    facet_type_id: 'type-1',
    facet_type_slug: 'contact',
    facet_type_name: 'Contact',
    text_representation: 'john@example.com',
    confidence_score: 0.95,
    human_verified: false,
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'facet-2',
    entity_id: 'entity-1',
    entity_name: 'Test Entity',
    facet_type_id: 'type-1',
    facet_type_slug: 'contact',
    facet_type_name: 'Contact',
    text_representation: 'jane@example.com',
    confidence_score: 0.85,
    human_verified: true,
    is_active: true,
    created_at: '2024-01-02T00:00:00Z',
  },
  {
    id: 'facet-3',
    entity_id: 'entity-2',
    entity_name: 'Another Entity',
    facet_type_id: 'type-2',
    facet_type_slug: 'date',
    facet_type_name: 'Date',
    text_representation: '2024-06-15',
    confidence_score: 0.90,
    human_verified: false,
    is_active: false,
    created_at: '2024-01-03T00:00:00Z',
  },
]

describe('useResultFacets', () => {
  let extractionIdRef: Ref<string | null>

  beforeEach(() => {
    vi.clearAllMocks()
    extractionIdRef = ref<string | null>('extraction-123')
  })

  // ==========================================================================
  // Initial State
  // ==========================================================================

  describe('Initial State', () => {
    it('should have loading as false', () => {
      const { loading } = useResultFacets(extractionIdRef)
      expect(loading.value).toBe(false)
    })

    it('should have empty facets array', () => {
      const { facets } = useResultFacets(extractionIdRef)
      expect(facets.value).toEqual([])
    })

    it('should have includeInactive as false', () => {
      const { includeInactive } = useResultFacets(extractionIdRef)
      expect(includeInactive.value).toBe(false)
    })

    it('should have no error', () => {
      const { error } = useResultFacets(extractionIdRef)
      expect(error.value).toBeNull()
    })

    it('should have facetCount as 0', () => {
      const { facetCount } = useResultFacets(extractionIdRef)
      expect(facetCount.value).toBe(0)
    })

    it('should have verifiedCount as 0', () => {
      const { verifiedCount } = useResultFacets(extractionIdRef)
      expect(verifiedCount.value).toBe(0)
    })

    it('should have empty groupedFacets', () => {
      const { groupedFacets } = useResultFacets(extractionIdRef)
      expect(groupedFacets.value).toEqual([])
    })
  })

  // ==========================================================================
  // Load Facets
  // ==========================================================================

  describe('loadFacets', () => {
    it('should set loading to true during fetch', async () => {
      vi.mocked(dataApi.getExtractionFacets).mockImplementation(async () => {
        return mockAxiosResponse(mockFacets)
      })

      const { loading, loadFacets } = useResultFacets(extractionIdRef)

      const loadPromise = loadFacets()
      expect(loading.value).toBe(true)

      await loadPromise
      expect(loading.value).toBe(false)
    })

    it('should load facets successfully', async () => {
      vi.mocked(dataApi.getExtractionFacets).mockResolvedValue(
        mockAxiosResponse(mockFacets)
      )

      const { facets, loadFacets } = useResultFacets(extractionIdRef)

      await loadFacets()

      expect(facets.value).toEqual(mockFacets)
      expect(dataApi.getExtractionFacets).toHaveBeenCalledWith('extraction-123', {
        include_inactive: false,
      })
    })

    it('should pass include_inactive parameter', async () => {
      vi.mocked(dataApi.getExtractionFacets).mockResolvedValue(
        mockAxiosResponse(mockFacets)
      )

      const { includeInactive, loadFacets } = useResultFacets(extractionIdRef)
      includeInactive.value = true

      await loadFacets()

      expect(dataApi.getExtractionFacets).toHaveBeenCalledWith('extraction-123', {
        include_inactive: true,
      })
    })

    it('should clear facets when extractionId is null', async () => {
      const nullRef = ref<string | null>(null)
      const { facets, loadFacets } = useResultFacets(nullRef)

      await loadFacets()

      expect(facets.value).toEqual([])
      expect(dataApi.getExtractionFacets).not.toHaveBeenCalled()
    })

    it('should set error on failure', async () => {
      vi.mocked(dataApi.getExtractionFacets).mockRejectedValue(
        new Error('API Error')
      )

      const { error, loadFacets } = useResultFacets(extractionIdRef)

      await loadFacets()

      expect(error.value).toBe('API Error')
    })

    it('should clear error on successful load', async () => {
      vi.mocked(dataApi.getExtractionFacets).mockResolvedValue(
        mockAxiosResponse(mockFacets)
      )

      const { error, loadFacets } = useResultFacets(extractionIdRef)
      error.value = 'Previous error'

      await loadFacets()

      expect(error.value).toBeNull()
    })
  })

  // ==========================================================================
  // Computed Properties
  // ==========================================================================

  describe('Computed Properties', () => {
    beforeEach(async () => {
      vi.mocked(dataApi.getExtractionFacets).mockResolvedValue(
        mockAxiosResponse(mockFacets)
      )
    })

    it('should calculate facetCount correctly', async () => {
      const { facetCount, loadFacets } = useResultFacets(extractionIdRef)

      await loadFacets()

      expect(facetCount.value).toBe(3)
    })

    it('should calculate activeCount correctly', async () => {
      const { activeCount, loadFacets } = useResultFacets(extractionIdRef)

      await loadFacets()

      expect(activeCount.value).toBe(2) // facet-1 and facet-2 are active
    })

    it('should calculate verifiedCount correctly', async () => {
      const { verifiedCount, loadFacets } = useResultFacets(extractionIdRef)

      await loadFacets()

      expect(verifiedCount.value).toBe(1) // Only facet-2 is verified
    })

    it('should group facets by type', async () => {
      const { groupedFacets, loadFacets } = useResultFacets(extractionIdRef)

      await loadFacets()

      expect(groupedFacets.value).toHaveLength(2) // type-1 (Contact) and type-2 (Date)

      const contactGroup = groupedFacets.value.find(g => g.facet_type_slug === 'contact')
      expect(contactGroup).toBeDefined()
      expect(contactGroup?.values).toHaveLength(2)

      const dateGroup = groupedFacets.value.find(g => g.facet_type_slug === 'date')
      expect(dateGroup).toBeDefined()
      expect(dateGroup?.values).toHaveLength(1)
    })
  })

  // ==========================================================================
  // Verify Facet
  // ==========================================================================

  describe('verifyFacet', () => {
    beforeEach(async () => {
      vi.mocked(dataApi.getExtractionFacets).mockResolvedValue(
        mockAxiosResponse(mockFacets)
      )
    })

    it('should verify a facet with optimistic update', async () => {
      vi.mocked(facetApi.verifyFacetValue).mockResolvedValue(mockAxiosResponse({}))

      const { facets, loadFacets, verifyFacet } = useResultFacets(extractionIdRef)

      await loadFacets()
      const result = await verifyFacet('facet-1')

      expect(result).toBe(true)
      expect(facets.value[0].human_verified).toBe(true)
      expect(facetApi.verifyFacetValue).toHaveBeenCalledWith('facet-1', { verified: true })
    })

    it('should return false for non-existent facet', async () => {
      const { loadFacets, verifyFacet } = useResultFacets(extractionIdRef)

      await loadFacets()
      const result = await verifyFacet('non-existent')

      expect(result).toBe(false)
      expect(facetApi.verifyFacetValue).not.toHaveBeenCalled()
    })

    it('should rollback on error', async () => {
      vi.mocked(facetApi.verifyFacetValue).mockRejectedValue(new Error('API Error'))

      const { facets, loadFacets, verifyFacet } = useResultFacets(extractionIdRef)

      await loadFacets()
      const originalVerified = facets.value[0].human_verified
      const result = await verifyFacet('facet-1')

      expect(result).toBe(false)
      expect(facets.value[0].human_verified).toBe(originalVerified)
    })
  })

  // ==========================================================================
  // Reject Facet
  // ==========================================================================

  describe('rejectFacet', () => {
    beforeEach(async () => {
      vi.mocked(dataApi.getExtractionFacets).mockResolvedValue(
        mockAxiosResponse(mockFacets)
      )
    })

    it('should deactivate a facet', async () => {
      vi.mocked(facetApi.updateFacetValue).mockResolvedValue(mockAxiosResponse({}))

      const { loadFacets, rejectFacet } = useResultFacets(extractionIdRef)

      await loadFacets()
      const result = await rejectFacet('facet-1')

      expect(result).toBe(true)
      expect(facetApi.updateFacetValue).toHaveBeenCalledWith('facet-1', { is_active: false })
    })

    it('should remove facet from list when not showing inactive', async () => {
      vi.mocked(facetApi.updateFacetValue).mockResolvedValue(mockAxiosResponse({}))

      const { facets, includeInactive, loadFacets, rejectFacet } = useResultFacets(extractionIdRef)
      includeInactive.value = false

      await loadFacets()
      const initialCount = facets.value.length
      await rejectFacet('facet-1')

      expect(facets.value.length).toBe(initialCount - 1)
      expect(facets.value.find(f => f.id === 'facet-1')).toBeUndefined()
    })

    it('should keep facet in list when showing inactive', async () => {
      vi.mocked(facetApi.updateFacetValue).mockResolvedValue(mockAxiosResponse({}))

      const { facets, facetCount, includeInactive, loadFacets, rejectFacet } = useResultFacets(extractionIdRef)
      includeInactive.value = true

      await loadFacets()
      const initialCount = facetCount.value
      await rejectFacet('facet-1')

      expect(facets.value.length).toBe(initialCount)
      expect(facets.value.find(f => f.id === 'facet-1')?.is_active).toBe(false)
    })

    it('should rollback on error', async () => {
      vi.mocked(facetApi.updateFacetValue).mockRejectedValue(new Error('API Error'))

      const { facets, loadFacets, rejectFacet } = useResultFacets(extractionIdRef)

      await loadFacets()
      const originalActive = facets.value[0].is_active
      const result = await rejectFacet('facet-1')

      expect(result).toBe(false)
      expect(facets.value[0].is_active).toBe(originalActive)
    })
  })

  // ==========================================================================
  // Reactivate Facet
  // ==========================================================================

  describe('reactivateFacet', () => {
    beforeEach(async () => {
      vi.mocked(dataApi.getExtractionFacets).mockResolvedValue(
        mockAxiosResponse(mockFacets)
      )
    })

    it('should reactivate a facet with optimistic update', async () => {
      vi.mocked(facetApi.updateFacetValue).mockResolvedValue(mockAxiosResponse({}))

      const { facets, loadFacets, reactivateFacet } = useResultFacets(extractionIdRef)

      await loadFacets()
      // facet-3 is inactive
      const result = await reactivateFacet('facet-3')

      expect(result).toBe(true)
      expect(facets.value[2].is_active).toBe(true)
      expect(facetApi.updateFacetValue).toHaveBeenCalledWith('facet-3', { is_active: true })
    })

    it('should rollback on error', async () => {
      vi.mocked(facetApi.updateFacetValue).mockRejectedValue(new Error('API Error'))

      const { facets, loadFacets, reactivateFacet } = useResultFacets(extractionIdRef)

      await loadFacets()
      const originalActive = facets.value[2].is_active
      const result = await reactivateFacet('facet-3')

      expect(result).toBe(false)
      expect(facets.value[2].is_active).toBe(originalActive)
    })
  })

  // ==========================================================================
  // Refresh
  // ==========================================================================

  describe('refresh', () => {
    it('should reload facets', async () => {
      vi.mocked(dataApi.getExtractionFacets).mockResolvedValue(
        mockAxiosResponse(mockFacets)
      )

      const { refresh } = useResultFacets(extractionIdRef)

      await refresh()

      expect(dataApi.getExtractionFacets).toHaveBeenCalled()
    })
  })
})
