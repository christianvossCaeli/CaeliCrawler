/**
 * Tests for useCategoryAiSetup composable
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useCategoryAiSetup } from './useCategoryAiSetup'
import type { CategoryFormData, CategoryAiPreviewData } from '@/types/category'
import { mockAxiosResponse } from '@/test/setup'

// Mock the API module
vi.mock('@/services/api/categories', () => ({
  categoryApi: {
    previewAiSetup: vi.fn(),
  },
}))

// Mock vue-i18n
vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string) => key,
  }),
}))

// Mock logger
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

// Import mocked module
import { categoryApi } from '@/services/api/categories'

// Mock form data
const mockFormData: CategoryFormData = {
  name: 'Test Category',
  purpose: 'Testing purposes',
  description: 'A test category',
  languages: ['de'],
  search_terms: [],
  document_types: [],
  url_include_patterns: [],
  url_exclude_patterns: [],
  schedule_cron: '',
  schedule_enabled: false,
  extraction_handler: 'default',
  ai_extraction_prompt: '',
  is_active: true,
  is_public: false,
  target_entity_type_id: null,
}

// Mock AI preview response
const mockPreviewData: CategoryAiPreviewData = {
  suggested_extraction_prompt: 'Extract relevant information from the document.',
  suggested_facet_types: [
    { name: 'Date', slug: 'date', selected: true },
    { name: 'Title', slug: 'title', selected: true },
    { name: 'Description', slug: 'description', selected: false },
  ],
  suggested_entity_type: {
    name: 'Document',
    is_new: true,
  },
  suggested_search_terms: ['test', 'document'],
  suggested_url_include_patterns: ['.*\\.pdf$'],
  suggested_url_exclude_patterns: ['.*draft.*'],
  existing_entity_types: [],
}

describe('useCategoryAiSetup', () => {
  let aiSetup: ReturnType<typeof useCategoryAiSetup>

  beforeEach(() => {
    vi.clearAllMocks()
    aiSetup = useCategoryAiSetup()
  })

  // ==========================================================================
  // Initial State
  // ==========================================================================

  describe('Initial State', () => {
    it('should have loading as false', () => {
      expect(aiSetup.loading.value).toBe(false)
    })

    it('should have saving as false', () => {
      expect(aiSetup.saving.value).toBe(false)
    })

    it('should have no preview data', () => {
      expect(aiSetup.previewData.value).toBeNull()
    })

    it('should have selectedEntityType as "new"', () => {
      expect(aiSetup.selectedEntityType.value).toBe('new')
    })

    it('should have empty selectedFacetTypes', () => {
      expect(aiSetup.selectedFacetTypes.value).toEqual([])
    })

    it('should have empty extractionPrompt', () => {
      expect(aiSetup.extractionPrompt.value).toBe('')
    })

    it('should have hasPreviewData as false', () => {
      expect(aiSetup.hasPreviewData.value).toBe(false)
    })

    it('should have adaptedPreviewData as null', () => {
      expect(aiSetup.adaptedPreviewData.value).toBeNull()
    })
  })

  // ==========================================================================
  // Reset State
  // ==========================================================================

  describe('resetState', () => {
    it('should reset all state to defaults', () => {
      // Set some state first
      aiSetup.loading.value = true
      aiSetup.saving.value = true
      aiSetup.previewData.value = mockPreviewData
      aiSetup.selectedEntityType.value = 'entity-123'
      aiSetup.selectedFacetTypes.value = [true, false]
      aiSetup.extractionPrompt.value = 'Some prompt'

      aiSetup.resetState()

      expect(aiSetup.loading.value).toBe(false)
      expect(aiSetup.saving.value).toBe(false)
      expect(aiSetup.previewData.value).toBeNull()
      expect(aiSetup.selectedEntityType.value).toBe('new')
      expect(aiSetup.selectedFacetTypes.value).toEqual([])
      expect(aiSetup.extractionPrompt.value).toBe('')
    })
  })

  // ==========================================================================
  // Fetch Preview
  // ==========================================================================

  describe('fetchPreview', () => {
    it('should set loading to true during fetch', async () => {
      vi.mocked(categoryApi.previewAiSetup).mockImplementation(async () => {
        expect(aiSetup.loading.value).toBe(true)
        return mockAxiosResponse(mockPreviewData)
      })

      await aiSetup.fetchPreview(mockFormData)

      expect(aiSetup.loading.value).toBe(false)
    })

    it('should set preview data on success', async () => {
      vi.mocked(categoryApi.previewAiSetup).mockResolvedValue(
        mockAxiosResponse(mockPreviewData)
      )

      const result = await aiSetup.fetchPreview(mockFormData)

      expect(result.success).toBe(true)
      expect(aiSetup.previewData.value).toEqual(mockPreviewData)
    })

    it('should set extractionPrompt from response', async () => {
      vi.mocked(categoryApi.previewAiSetup).mockResolvedValue(
        mockAxiosResponse(mockPreviewData)
      )

      await aiSetup.fetchPreview(mockFormData)

      expect(aiSetup.extractionPrompt.value).toBe(mockPreviewData.suggested_extraction_prompt)
    })

    it('should set selectedFacetTypes based on suggested types', async () => {
      vi.mocked(categoryApi.previewAiSetup).mockResolvedValue(
        mockAxiosResponse(mockPreviewData)
      )

      await aiSetup.fetchPreview(mockFormData)

      expect(aiSetup.selectedFacetTypes.value).toEqual([true, true, false])
    })

    it('should set selectedEntityType to "new" for new entity types', async () => {
      vi.mocked(categoryApi.previewAiSetup).mockResolvedValue(
        mockAxiosResponse(mockPreviewData)
      )

      await aiSetup.fetchPreview(mockFormData)

      expect(aiSetup.selectedEntityType.value).toBe('new')
    })

    it('should set selectedEntityType to ID for existing entity types', async () => {
      const previewWithExisting = {
        ...mockPreviewData,
        suggested_entity_type: {
          name: 'Existing Type',
          id: 'existing-123',
          is_new: false,
        },
      }
      vi.mocked(categoryApi.previewAiSetup).mockResolvedValue(
        mockAxiosResponse(previewWithExisting)
      )

      await aiSetup.fetchPreview(mockFormData)

      expect(aiSetup.selectedEntityType.value).toBe('existing-123')
    })

    it('should return error on failure', async () => {
      vi.mocked(categoryApi.previewAiSetup).mockRejectedValue(new Error('API Error'))

      const result = await aiSetup.fetchPreview(mockFormData)

      expect(result.success).toBe(false)
      expect(result.error).toBe('API Error')
    })

    it('should return cancelled error for abort', async () => {
      const abortError = new Error('Aborted')
      abortError.name = 'AbortError'
      vi.mocked(categoryApi.previewAiSetup).mockRejectedValue(abortError)

      const result = await aiSetup.fetchPreview(mockFormData)

      expect(result.success).toBe(false)
      expect(result.error).toBe('cancelled')
    })

    it('should clear previous preview data on new fetch', async () => {
      aiSetup.previewData.value = mockPreviewData

      vi.mocked(categoryApi.previewAiSetup).mockImplementation(async () => {
        expect(aiSetup.previewData.value).toBeNull()
        return mockAxiosResponse(mockPreviewData)
      })

      await aiSetup.fetchPreview(mockFormData)
    })
  })

  // ==========================================================================
  // Update Facet Type Selection
  // ==========================================================================

  describe('updateFacetTypeSelection', () => {
    beforeEach(() => {
      aiSetup.selectedFacetTypes.value = [true, true, false]
    })

    it('should update selection at valid index', () => {
      aiSetup.updateFacetTypeSelection(0, false)
      expect(aiSetup.selectedFacetTypes.value[0]).toBe(false)
    })

    it('should not update at invalid negative index', () => {
      const original = [...aiSetup.selectedFacetTypes.value]
      aiSetup.updateFacetTypeSelection(-1, true)
      expect(aiSetup.selectedFacetTypes.value).toEqual(original)
    })

    it('should not update at index beyond array length', () => {
      const original = [...aiSetup.selectedFacetTypes.value]
      aiSetup.updateFacetTypeSelection(10, true)
      expect(aiSetup.selectedFacetTypes.value).toEqual(original)
    })
  })

  // ==========================================================================
  // Get Merged Category Data
  // ==========================================================================

  describe('getMergedCategoryData', () => {
    it('should return form data when no preview data', () => {
      const result = aiSetup.getMergedCategoryData(mockFormData)

      expect(result).toEqual({ ...mockFormData })
    })

    it('should merge preview data with form data', () => {
      aiSetup.previewData.value = mockPreviewData
      aiSetup.extractionPrompt.value = 'Custom prompt'

      const result = aiSetup.getMergedCategoryData(mockFormData)

      expect(result.ai_extraction_prompt).toBe('Custom prompt')
      expect(result.search_terms).toEqual(mockPreviewData.suggested_search_terms)
      expect(result.url_include_patterns).toEqual(mockPreviewData.suggested_url_include_patterns)
      expect(result.url_exclude_patterns).toEqual(mockPreviewData.suggested_url_exclude_patterns)
    })

    it('should use form data values when provided', () => {
      aiSetup.previewData.value = mockPreviewData

      const formWithValues = {
        ...mockFormData,
        search_terms: ['custom-term'],
        url_include_patterns: ['custom-pattern'],
      }

      const result = aiSetup.getMergedCategoryData(formWithValues)

      expect(result.search_terms).toEqual(['custom-term'])
      expect(result.url_include_patterns).toEqual(['custom-pattern'])
    })

    it('should set target_entity_type_id when existing entity selected', () => {
      aiSetup.previewData.value = mockPreviewData
      aiSetup.selectedEntityType.value = 'existing-123'

      const result = aiSetup.getMergedCategoryData(mockFormData)

      expect(result.target_entity_type_id).toBe('existing-123')
    })

    it('should not set target_entity_type_id when "new" selected', () => {
      aiSetup.previewData.value = mockPreviewData
      aiSetup.selectedEntityType.value = 'new'

      const result = aiSetup.getMergedCategoryData(mockFormData)

      // target_entity_type_id should be null (or undefined) when creating new entity type
      expect(result.target_entity_type_id).toBeFalsy()
    })
  })

  // ==========================================================================
  // Get Selected Facet Types
  // ==========================================================================

  describe('getSelectedFacetTypes', () => {
    it('should return empty array when no preview data', () => {
      const result = aiSetup.getSelectedFacetTypes()
      expect(result).toEqual([])
    })

    it('should return only selected facet types', () => {
      aiSetup.previewData.value = mockPreviewData
      aiSetup.selectedFacetTypes.value = [true, false, true]

      const result = aiSetup.getSelectedFacetTypes()

      expect(result).toHaveLength(2)
      expect(result[0].name).toBe('Date')
      expect(result[1].name).toBe('Description')
    })

    it('should return all facet types when all selected', () => {
      aiSetup.previewData.value = mockPreviewData
      aiSetup.selectedFacetTypes.value = [true, true, true]

      const result = aiSetup.getSelectedFacetTypes()

      expect(result).toHaveLength(3)
    })

    it('should return empty array when none selected', () => {
      aiSetup.previewData.value = mockPreviewData
      aiSetup.selectedFacetTypes.value = [false, false, false]

      const result = aiSetup.getSelectedFacetTypes()

      expect(result).toEqual([])
    })
  })

  // ==========================================================================
  // Computed Properties
  // ==========================================================================

  describe('Computed Properties', () => {
    describe('hasPreviewData', () => {
      it('should be false when previewData is null', () => {
        expect(aiSetup.hasPreviewData.value).toBe(false)
      })

      it('should be true when previewData exists', () => {
        aiSetup.previewData.value = mockPreviewData
        expect(aiSetup.hasPreviewData.value).toBe(true)
      })
    })
  })

  // ==========================================================================
  // Cancel Request
  // ==========================================================================

  describe('cancelRequest', () => {
    it('should not throw when called without active request', () => {
      expect(() => aiSetup.cancelRequest()).not.toThrow()
    })
  })
})
