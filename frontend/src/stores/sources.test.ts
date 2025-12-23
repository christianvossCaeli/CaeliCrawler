import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSourcesStore } from './sources'

// Mock the API module
vi.mock('@/services/api', () => ({
  adminApi: {
    getSources: vi.fn(),
    createSource: vi.fn(),
    updateSource: vi.fn(),
    deleteSource: vi.fn(),
    startCrawl: vi.fn(),
    resetSource: vi.fn(),
    getCategories: vi.fn(),
    getSourceCounts: vi.fn(),
    getAvailableTags: vi.fn(),
    testSharePointConnection: vi.fn(),
    bulkImportSources: vi.fn(),
  },
  entityApi: {
    getEntity: vi.fn(),
    searchEntities: vi.fn(),
  },
}))

describe('Sources Store', () => {
  let store: ReturnType<typeof useSourcesStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useSourcesStore()
  })

  // ==========================================================================
  // Initial State
  // ==========================================================================

  describe('Initial State', () => {
    it('has correct default state', () => {
      expect(store.sources).toEqual([])
      expect(store.sourcesLoading).toBe(false)
      expect(store.sourcesTotal).toBe(0)
      expect(store.currentPage).toBe(1)
      expect(store.itemsPerPage).toBe(50)
    })

    it('has correct default filters', () => {
      expect(store.filters).toEqual({
        category_id: null,
        source_type: null,
        status: null,
        search: '',
        tags: [],
      })
    })

    it('has empty sidebar counts', () => {
      expect(store.sidebarCounts).toEqual({
        total: 0,
        categories: [],
        types: [],
        statuses: [],
      })
    })
  })

  // ==========================================================================
  // Filter Actions
  // ==========================================================================

  describe('Filter Actions', () => {
    describe('setFilter', () => {
      it('sets category_id filter', () => {
        store.setFilter('category_id', 'cat-123')
        expect(store.filters.category_id).toBe('cat-123')
        expect(store.currentPage).toBe(1) // Resets to page 1
      })

      it('sets source_type filter', () => {
        store.setFilter('source_type', 'WEBSITE')
        expect(store.filters.source_type).toBe('WEBSITE')
      })

      it('sets status filter', () => {
        store.setFilter('status', 'ACTIVE')
        expect(store.filters.status).toBe('ACTIVE')
      })

      it('sets search filter', () => {
        store.setFilter('search', 'test query')
        expect(store.filters.search).toBe('test query')
      })

      it('sets tags filter', () => {
        store.setFilter('tags', ['tag1', 'tag2'])
        expect(store.filters.tags).toEqual(['tag1', 'tag2'])
      })
    })

    describe('clearAllFilters', () => {
      it('resets all filters to defaults', () => {
        // Set some filters first
        store.setFilter('category_id', 'cat-123')
        store.setFilter('source_type', 'WEBSITE')
        store.setFilter('status', 'ACTIVE')
        store.setFilter('search', 'test')
        store.setFilter('tags', ['tag1'])

        // Clear all
        store.clearAllFilters()

        expect(store.filters).toEqual({
          category_id: null,
          source_type: null,
          status: null,
          search: '',
          tags: [],
        })
        expect(store.currentPage).toBe(1)
      })
    })
  })

  // ==========================================================================
  // Computed Properties
  // ==========================================================================

  describe('Computed Properties', () => {
    describe('hasActiveFilters', () => {
      it('returns false when no filters active', () => {
        expect(store.hasActiveFilters).toBe(false)
      })

      it('returns true when category_id is set', () => {
        store.setFilter('category_id', 'cat-123')
        expect(store.hasActiveFilters).toBe(true)
      })

      it('returns true when source_type is set', () => {
        store.setFilter('source_type', 'WEBSITE')
        expect(store.hasActiveFilters).toBe(true)
      })

      it('returns true when status is set', () => {
        store.setFilter('status', 'ACTIVE')
        expect(store.hasActiveFilters).toBe(true)
      })

      it('returns true when tags are set', () => {
        store.setFilter('tags', ['tag1'])
        expect(store.hasActiveFilters).toBe(true)
      })

      it('returns false when only search is set (search is not a sidebar filter)', () => {
        store.setFilter('search', 'test')
        expect(store.hasActiveFilters).toBe(false)
      })
    })

    describe('tagSuggestions', () => {
      it('extracts tag names from availableTags', () => {
        store.availableTags = [
          { tag: 'nrw', count: 10 },
          { tag: 'bayern', count: 5 },
        ]
        expect(store.tagSuggestions).toEqual(['nrw', 'bayern'])
      })

      it('returns empty array when no tags', () => {
        store.availableTags = []
        expect(store.tagSuggestions).toEqual([])
      })
    })

    describe('canPreviewBulkImport', () => {
      it('returns false when csvText is empty in text mode', () => {
        store.bulkImport.inputMode = 'text'
        store.bulkImport.csvText = ''
        expect(store.canPreviewBulkImport).toBe(false)
      })

      it('returns true when csvText has content in text mode', () => {
        store.bulkImport.inputMode = 'text'
        store.bulkImport.csvText = 'some content'
        expect(store.canPreviewBulkImport).toBe(true)
      })

      it('returns false when csvFile is null in file mode', () => {
        store.bulkImport.inputMode = 'file'
        store.bulkImport.csvFile = null
        expect(store.canPreviewBulkImport).toBe(false)
      })

      it('returns true when csvFile exists in file mode', () => {
        store.bulkImport.inputMode = 'file'
        store.bulkImport.csvFile = new File([''], 'test.csv')
        expect(store.canPreviewBulkImport).toBe(true)
      })
    })

    describe('canExecuteBulkImport', () => {
      it('returns false when no categories selected', () => {
        store.bulkImport.category_ids = []
        store.bulkImport.validCount = 5
        expect(store.canExecuteBulkImport).toBe(false)
      })

      it('returns false when no valid items', () => {
        store.bulkImport.category_ids = ['cat-1']
        store.bulkImport.validCount = 0
        expect(store.canExecuteBulkImport).toBe(false)
      })

      it('returns true when categories and valid items exist', () => {
        store.bulkImport.category_ids = ['cat-1']
        store.bulkImport.validCount = 5
        expect(store.canExecuteBulkImport).toBe(true)
      })
    })
  })

  // ==========================================================================
  // Bulk Import Parsing
  // ==========================================================================

  describe('Bulk Import Parsing', () => {
    beforeEach(() => {
      // Initialize with empty sources for duplicate detection
      store.sources = []
    })

    describe('parseBulkImportPreview', () => {
      it('parses simple URL format', () => {
        store.bulkImport.csvText = 'https://example.com'
        store.parseBulkImportPreview()

        expect(store.bulkImport.preview).toHaveLength(1)
        expect(store.bulkImport.preview[0].base_url).toBe('https://example.com')
        expect(store.bulkImport.preview[0].name).toBe('example.com')
        expect(store.bulkImport.validCount).toBe(1)
      })

      it('parses pipe-separated format (Name | URL)', () => {
        store.bulkImport.csvText = 'My Site | https://example.com'
        store.parseBulkImportPreview()

        expect(store.bulkImport.preview).toHaveLength(1)
        expect(store.bulkImport.preview[0].name).toBe('My Site')
        expect(store.bulkImport.preview[0].base_url).toBe('https://example.com')
      })

      it('parses CSV format (Name;URL;Type;Tags)', () => {
        store.bulkImport.csvText = 'Test Site;https://test.com;WEBSITE;tag1,tag2'
        store.parseBulkImportPreview()

        expect(store.bulkImport.preview).toHaveLength(1)
        expect(store.bulkImport.preview[0].name).toBe('Test Site')
        expect(store.bulkImport.preview[0].base_url).toBe('https://test.com')
        expect(store.bulkImport.preview[0].source_type).toBe('WEBSITE')
        expect(store.bulkImport.preview[0].tags).toEqual(['tag1', 'tag2'])
      })

      it('marks invalid URLs as errors', () => {
        store.bulkImport.csvText = 'invalid-url'
        store.parseBulkImportPreview()

        expect(store.bulkImport.preview[0].error).toBeDefined()
        expect(store.bulkImport.errorCount).toBe(1)
        expect(store.bulkImport.validCount).toBe(0)
      })

      it('detects duplicate URLs', () => {
        store.sources = [
          { id: '1', name: 'Existing', base_url: 'https://existing.com' } as any,
        ]
        store.bulkImport.csvText = 'https://existing.com'
        store.parseBulkImportPreview()

        expect(store.bulkImport.preview[0].duplicate).toBe(true)
        expect(store.bulkImport.duplicateCount).toBe(1)
      })

      it('detects duplicates within same import', () => {
        store.bulkImport.csvText = 'https://example.com\nhttps://example.com'
        store.parseBulkImportPreview()

        expect(store.bulkImport.preview).toHaveLength(2)
        expect(store.bulkImport.preview[0].duplicate).toBeFalsy()
        expect(store.bulkImport.preview[1].duplicate).toBe(true)
      })

      it('skips header line', () => {
        store.bulkImport.csvText = 'Name;URL;Type;Tags\nTest;https://test.com;WEBSITE;'
        store.parseBulkImportPreview()

        expect(store.bulkImport.preview).toHaveLength(1)
        expect(store.bulkImport.preview[0].name).toBe('Test')
      })

      it('applies default tags to all items', () => {
        store.bulkImport.default_tags = ['default-tag']
        store.bulkImport.csvText = 'https://example.com'
        store.parseBulkImportPreview()

        expect(store.bulkImport.preview[0].allTags).toContain('default-tag')
      })

      it('handles empty input', () => {
        store.bulkImport.csvText = ''
        store.parseBulkImportPreview()

        expect(store.bulkImport.preview).toHaveLength(0)
      })

      it('handles multiple lines', () => {
        store.bulkImport.csvText = 'https://site1.com\nhttps://site2.com\nhttps://site3.com'
        store.parseBulkImportPreview()

        expect(store.bulkImport.preview).toHaveLength(3)
        expect(store.bulkImport.validCount).toBe(3)
      })
    })
  })

  // ==========================================================================
  // Form Actions
  // ==========================================================================

  describe('Form Actions', () => {
    describe('prepareCreateForm', () => {
      it('sets editMode to false', () => {
        store.editMode = true // Set to true first
        store.prepareCreateForm()
        expect(store.editMode).toBe(false)
      })

      it('clears selectedSource', () => {
        store.selectedSource = { id: '1', name: 'Test' } as any
        store.prepareCreateForm()
        expect(store.selectedSource).toBeNull()
      })

      it('resets form data', () => {
        store.formData.name = 'Old Name'
        store.prepareCreateForm()
        expect(store.formData.name).toBe('')
      })
    })

    describe('resetFormData', () => {
      it('clears selected entities', () => {
        store.selectedEntities = [{ id: '1', name: 'Entity' } as any]
        store.resetFormData()
        expect(store.selectedEntities).toEqual([])
      })

      it('clears SharePoint test result', () => {
        store.sharepointTestResult = { success: true, message: 'OK' }
        store.resetFormData()
        expect(store.sharepointTestResult).toBeNull()
      })
    })
  })

  // ==========================================================================
  // Utility Functions
  // ==========================================================================

  describe('Utility Functions', () => {
    describe('getCategoryName', () => {
      it('returns category name when found', () => {
        store.sidebarCounts.categories = [
          { id: 'cat-1', name: 'Category One', slug: 'category-one', count: 5 },
        ]
        expect(store.getCategoryName('cat-1')).toBe('Category One')
      })

      it('returns categoryId as fallback when not found', () => {
        store.sidebarCounts.categories = []
        expect(store.getCategoryName('unknown-id')).toBe('unknown-id')
      })
    })

    describe('clearError', () => {
      it('clears error message', () => {
        store.error = 'Some error'
        store.clearError()
        expect(store.error).toBeNull()
      })
    })

    describe('resetState', () => {
      it('resets all state to defaults', () => {
        // Set some state
        store.sources = [{ id: '1' } as any]
        store.sourcesTotal = 10
        store.error = 'Error'
        store.setFilter('category_id', 'cat-1')

        store.resetState()

        expect(store.sources).toEqual([])
        expect(store.sourcesTotal).toBe(0)
        expect(store.error).toBeNull()
        expect(store.filters.category_id).toBeNull()
      })
    })
  })

  // ==========================================================================
  // Entity Management
  // ==========================================================================

  describe('Entity Management', () => {
    describe('selectEntity', () => {
      it('adds entity to selectedEntities', () => {
        const entity = { id: 'e1', name: 'Entity 1' } as any
        store.selectEntity(entity)
        expect(store.selectedEntities).toContainEqual(entity)
      })

      it('does not add duplicate entity', () => {
        const entity = { id: 'e1', name: 'Entity 1' } as any
        store.selectEntity(entity)
        store.selectEntity(entity)
        expect(store.selectedEntities).toHaveLength(1)
      })

      it('updates formData.extra_data.entity_ids', () => {
        const entity = { id: 'e1', name: 'Entity 1' } as any
        store.selectEntity(entity)
        expect(store.formData.extra_data.entity_ids).toContain('e1')
      })

      it('clears search results', () => {
        store.entitySearchResults = [{ id: 'e2' } as any]
        const entity = { id: 'e1', name: 'Entity 1' } as any
        store.selectEntity(entity)
        expect(store.entitySearchResults).toEqual([])
      })
    })

    describe('removeEntity', () => {
      it('removes entity from selectedEntities', () => {
        store.selectedEntities = [
          { id: 'e1', name: 'Entity 1' } as any,
          { id: 'e2', name: 'Entity 2' } as any,
        ]
        store.removeEntity('e1')
        expect(store.selectedEntities).toHaveLength(1)
        expect(store.selectedEntities[0].id).toBe('e2')
      })

      it('updates formData.extra_data.entity_ids', () => {
        store.selectedEntities = [{ id: 'e1' } as any]
        store.formData.extra_data.entity_ids = ['e1']
        store.removeEntity('e1')
        expect(store.formData.extra_data.entity_ids).toEqual([])
      })
    })

    describe('clearAllEntities', () => {
      it('clears all entities and search results', () => {
        store.selectedEntities = [{ id: 'e1' } as any]
        store.entitySearchResults = [{ id: 'e2' } as any]
        store.formData.extra_data.entity_ids = ['e1']

        store.clearAllEntities()

        expect(store.selectedEntities).toEqual([])
        expect(store.entitySearchResults).toEqual([])
        expect(store.formData.extra_data.entity_ids).toEqual([])
      })
    })
  })

  // ==========================================================================
  // Bulk Import State
  // ==========================================================================

  describe('Bulk Import State', () => {
    describe('resetBulkImport', () => {
      it('resets all bulk import state', () => {
        store.bulkImport.category_ids = ['cat-1']
        store.bulkImport.csvText = 'some content'
        store.bulkImport.validCount = 5

        store.resetBulkImport()

        expect(store.bulkImport.category_ids).toEqual([])
        expect(store.bulkImport.csvText).toBe('')
        expect(store.bulkImport.validCount).toBe(0)
        expect(store.bulkImport.importing).toBe(false)
      })
    })
  })
})
