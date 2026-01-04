/**
 * Tests for useDocumentsView composable
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useDocumentsView } from '../useDocumentsView'

// Mock dependencies
vi.mock('@/services/api', () => ({
  dataApi: {
    getDocuments: vi.fn().mockResolvedValue({
      data: { items: [], total: 0 },
    }),
    getDocumentLocations: vi.fn().mockResolvedValue({ data: [] }),
    getDocument: vi.fn().mockResolvedValue({ data: {} }),
  },
  adminApi: {
    getCategories: vi.fn().mockResolvedValue({ data: { items: [] } }),
    processDocument: vi.fn().mockResolvedValue({ data: {} }),
    analyzeDocument: vi.fn().mockResolvedValue({ data: {} }),
    processAllPending: vi.fn().mockResolvedValue({ data: {} }),
    stopAllProcessing: vi.fn().mockResolvedValue({ data: {} }),
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
  }),
}))

vi.mock('@/composables/useDateFormatter', () => ({
  useDateFormatter: () => ({
    formatDate: (date: string) => date,
  }),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({
    query: {},
  }),
}))

describe('useDocumentsView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('initialization', () => {
    it('should return all expected properties', () => {
      const result = useDocumentsView()

      // Loading states
      expect(result.loading).toBeDefined()
      expect(result.initialLoad).toBeDefined()
      expect(result.processingAll).toBeDefined()
      expect(result.bulkProcessing).toBeDefined()
      expect(result.bulkAnalyzing).toBeDefined()

      // Data
      expect(result.documents).toBeDefined()
      expect(result.totalDocuments).toBeDefined()
      expect(result.stats).toBeDefined()

      // Filters
      expect(result.searchQuery).toBeDefined()
      expect(result.statusFilter).toBeDefined()
      expect(result.typeFilter).toBeDefined()

      // Methods
      expect(result.loadData).toBeDefined()
      expect(result.clearFilters).toBeDefined()
      expect(result.processDocument).toBeDefined()
      expect(result.exportCsv).toBeDefined()
    })

    it('should have correct default values', () => {
      const result = useDocumentsView()

      expect(result.loading.value).toBe(true)
      expect(result.documents.value).toEqual([])
      expect(result.totalDocuments.value).toBe(0)
      expect(result.selectedDocuments.value).toEqual([])
      expect(result.stats.value).toEqual({
        pending: 0,
        processing: 0,
        analyzing: 0,
        completed: 0,
        filtered: 0,
        failed: 0,
      })
    })
  })

  describe('helper functions', () => {
    it('getStatusColor should return correct colors', () => {
      const { getStatusColor } = useDocumentsView()

      expect(getStatusColor('PENDING')).toBe('warning')
      expect(getStatusColor('PROCESSING')).toBe('info')
      expect(getStatusColor('ANALYZING')).toBe('info') // ANALYZING is an info state (activity indicator)
      expect(getStatusColor('COMPLETED')).toBe('success')
      expect(getStatusColor('FAILED')).toBe('error')
      expect(getStatusColor(undefined)).toBe('grey')
    })

    it('getTypeColor should return correct colors', () => {
      const { getTypeColor } = useDocumentsView()

      expect(getTypeColor('PDF')).toBe('red')
      expect(getTypeColor('HTML')).toBe('blue')
      expect(getTypeColor('DOCX')).toBe('indigo')
      expect(getTypeColor(undefined)).toBe('grey')
    })

    it('getTypeIcon should return correct icons', () => {
      const { getTypeIcon } = useDocumentsView()

      expect(getTypeIcon('PDF')).toBe('mdi-file-pdf-box')
      expect(getTypeIcon('HTML')).toBe('mdi-language-html5')
      expect(getTypeIcon('DOCX')).toBe('mdi-file-word')
      expect(getTypeIcon(undefined)).toBe('mdi-file-document')
    })

    it('formatFileSize should format bytes correctly', () => {
      const { formatFileSize } = useDocumentsView()

      expect(formatFileSize(500)).toBe('500 B')
      expect(formatFileSize(1024)).toBe('1.0 KB')
      expect(formatFileSize(1536)).toBe('1.5 KB')
      expect(formatFileSize(1048576)).toBe('1.0 MB')
      expect(formatFileSize(undefined)).toBe('-')
    })
  })

  describe('filter actions', () => {
    it('clearFilters should reset all filters', () => {
      const result = useDocumentsView()

      // Set some filter values
      result.searchQuery.value = 'test'
      result.statusFilter.value = 'PENDING'
      result.typeFilter.value = 'PDF'

      // Clear filters
      result.clearFilters()

      // Verify reset
      expect(result.searchQuery.value).toBe('')
      expect(result.statusFilter.value).toBeNull()
      expect(result.typeFilter.value).toBeNull()
      expect(result.page.value).toBe(1)
    })

    it('toggleStatusFilter should toggle filter correctly', () => {
      const result = useDocumentsView()

      expect(result.statusFilter.value).toBeNull()

      result.toggleStatusFilter('PENDING')
      expect(result.statusFilter.value).toBe('PENDING')

      result.toggleStatusFilter('PENDING')
      expect(result.statusFilter.value).toBeNull()

      result.toggleStatusFilter('COMPLETED')
      expect(result.statusFilter.value).toBe('COMPLETED')
    })
  })

  describe('computed properties', () => {
    it('hasActiveFilters should detect active filters', () => {
      const result = useDocumentsView()

      // Initially no filters should be active
      expect(result.hasActiveFilters.value).toBeFalsy()

      result.searchQuery.value = 'test'
      expect(result.hasActiveFilters.value).toBeTruthy()

      result.searchQuery.value = ''
      result.statusFilter.value = 'PENDING'
      expect(result.hasActiveFilters.value).toBeTruthy()
    })
  })

  describe('static data', () => {
    it('documentTypes should contain expected types', () => {
      const { documentTypes } = useDocumentsView()

      expect(documentTypes).toContain('PDF')
      expect(documentTypes).toContain('HTML')
      expect(documentTypes).toContain('DOCX')
      expect(documentTypes).toContain('DOC')
    })
  })
})
