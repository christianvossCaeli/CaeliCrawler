/**
 * Tests for useCategoryDialogs composable
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { useCategoryDialogs } from './useCategoryDialogs'
import type { CategoryResponse } from '@/types/category'

// Mock category for testing
const mockCategory: CategoryResponse = {
  id: 'cat-123',
  name: 'Test Category',
  slug: 'test-category',
  purpose: 'Testing purposes',
  description: 'A test category',
  is_public: false,
  languages: ['de', 'en'],
  search_terms: ['test'],
  document_types: ['html', 'pdf'],
  url_include_patterns: [],
  url_exclude_patterns: [],
  schedule_cron: '',
  schedule_enabled: false,
  extraction_handler: 'default',
  ai_extraction_prompt: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  source_count: 0,
  document_count: 0,
  target_entity_type_id: null,
  target_entity_type: null,
}

describe('useCategoryDialogs', () => {
  let dialogs: ReturnType<typeof useCategoryDialogs>

  beforeEach(() => {
    dialogs = useCategoryDialogs()
  })

  // ==========================================================================
  // Initial State
  // ==========================================================================

  describe('Initial State', () => {
    it('should have all dialogs closed initially', () => {
      expect(dialogs.dialogs.value.edit).toBe(false)
      expect(dialogs.dialogs.value.delete).toBe(false)
      expect(dialogs.dialogs.value.reanalyze).toBe(false)
      expect(dialogs.dialogs.value.sources).toBe(false)
      expect(dialogs.dialogs.value.crawler).toBe(false)
      expect(dialogs.dialogs.value.aiPreview).toBe(false)
      expect(dialogs.dialogs.value.summaryCreate).toBe(false)
    })

    it('should have isEditMode as false', () => {
      expect(dialogs.isEditMode.value).toBe(false)
    })

    it('should have reanalyzeAll as false', () => {
      expect(dialogs.reanalyzeAll.value).toBe(false)
    })

    it('should have no selected categories', () => {
      expect(dialogs.selectedCategory.value).toBeNull()
      expect(dialogs.categoryForSources.value).toBeNull()
      expect(dialogs.categoryForCrawler.value).toBeNull()
      expect(dialogs.categoryForSummary.value).toBeNull()
    })

    it('should have isAnyDialogOpen as false', () => {
      expect(dialogs.isAnyDialogOpen.value).toBe(false)
    })
  })

  // ==========================================================================
  // Generic Dialog Actions
  // ==========================================================================

  describe('Generic Dialog Actions', () => {
    describe('openDialog', () => {
      it('should open the specified dialog', () => {
        dialogs.openDialog('edit')
        expect(dialogs.dialogs.value.edit).toBe(true)
      })

      it('should set isAnyDialogOpen to true', () => {
        dialogs.openDialog('delete')
        expect(dialogs.isAnyDialogOpen.value).toBe(true)
      })
    })

    describe('closeDialog', () => {
      it('should close the specified dialog', () => {
        dialogs.openDialog('edit')
        dialogs.closeDialog('edit')
        expect(dialogs.dialogs.value.edit).toBe(false)
      })

      it('should set isAnyDialogOpen to false when all closed', () => {
        dialogs.openDialog('edit')
        dialogs.closeDialog('edit')
        expect(dialogs.isAnyDialogOpen.value).toBe(false)
      })
    })

    describe('closeAllDialogs', () => {
      it('should close all open dialogs', () => {
        dialogs.openDialog('edit')
        dialogs.openDialog('delete')
        dialogs.openDialog('sources')

        dialogs.closeAllDialogs()

        expect(dialogs.dialogs.value.edit).toBe(false)
        expect(dialogs.dialogs.value.delete).toBe(false)
        expect(dialogs.dialogs.value.sources).toBe(false)
        expect(dialogs.isAnyDialogOpen.value).toBe(false)
      })
    })
  })

  // ==========================================================================
  // Create Dialog
  // ==========================================================================

  describe('Create Dialog', () => {
    it('should open edit dialog in create mode', () => {
      dialogs.openCreateDialog()

      expect(dialogs.dialogs.value.edit).toBe(true)
      expect(dialogs.isEditMode.value).toBe(false)
      expect(dialogs.selectedCategory.value).toBeNull()
    })

    it('should clear previous selection when opening create', () => {
      dialogs.selectedCategory.value = mockCategory
      dialogs.isEditMode.value = true

      dialogs.openCreateDialog()

      expect(dialogs.selectedCategory.value).toBeNull()
      expect(dialogs.isEditMode.value).toBe(false)
    })
  })

  // ==========================================================================
  // Edit Dialog
  // ==========================================================================

  describe('Edit Dialog', () => {
    it('should open edit dialog in edit mode with category', () => {
      dialogs.openEditDialog(mockCategory)

      expect(dialogs.dialogs.value.edit).toBe(true)
      expect(dialogs.isEditMode.value).toBe(true)
      expect(dialogs.selectedCategory.value).toEqual(mockCategory)
    })

    it('should close edit dialog', () => {
      dialogs.openEditDialog(mockCategory)
      dialogs.closeEditDialog()

      expect(dialogs.dialogs.value.edit).toBe(false)
    })
  })

  // ==========================================================================
  // Delete Dialog
  // ==========================================================================

  describe('Delete Dialog', () => {
    it('should open delete dialog with category', () => {
      dialogs.openDeleteDialog(mockCategory)

      expect(dialogs.dialogs.value.delete).toBe(true)
      expect(dialogs.selectedCategory.value).toEqual(mockCategory)
    })
  })

  // ==========================================================================
  // Reanalyze Dialog
  // ==========================================================================

  describe('Reanalyze Dialog', () => {
    it('should open reanalyze dialog with category', () => {
      dialogs.openReanalyzeDialog(mockCategory)

      expect(dialogs.dialogs.value.reanalyze).toBe(true)
      expect(dialogs.selectedCategory.value).toEqual(mockCategory)
      expect(dialogs.reanalyzeAll.value).toBe(false)
    })

    it('should open reanalyze dialog with analyzeAll flag', () => {
      dialogs.openReanalyzeDialog(mockCategory, true)

      expect(dialogs.dialogs.value.reanalyze).toBe(true)
      expect(dialogs.reanalyzeAll.value).toBe(true)
    })
  })

  // ==========================================================================
  // Sources Dialog
  // ==========================================================================

  describe('Sources Dialog', () => {
    it('should open sources dialog with category', () => {
      dialogs.openSourcesDialog(mockCategory)

      expect(dialogs.dialogs.value.sources).toBe(true)
      expect(dialogs.categoryForSources.value).toEqual(mockCategory)
    })
  })

  // ==========================================================================
  // Crawler Dialog
  // ==========================================================================

  describe('Crawler Dialog', () => {
    it('should open crawler dialog with category', () => {
      dialogs.openCrawlerDialog(mockCategory)

      expect(dialogs.dialogs.value.crawler).toBe(true)
      expect(dialogs.categoryForCrawler.value).toEqual(mockCategory)
    })
  })

  // ==========================================================================
  // AI Preview Dialog
  // ==========================================================================

  describe('AI Preview Dialog', () => {
    it('should open AI preview dialog', () => {
      dialogs.openAiPreviewDialog()

      expect(dialogs.dialogs.value.aiPreview).toBe(true)
    })
  })

  // ==========================================================================
  // Summary Dialog
  // ==========================================================================

  describe('Summary Dialog', () => {
    it('should open summary dialog with category', () => {
      dialogs.openSummaryDialog(mockCategory)

      expect(dialogs.dialogs.value.summaryCreate).toBe(true)
      expect(dialogs.categoryForSummary.value).toEqual(mockCategory)
    })
  })

  // ==========================================================================
  // Fallback to Edit Dialog
  // ==========================================================================

  describe('Fallback to Edit Dialog', () => {
    it('should close AI preview and open edit dialog', () => {
      dialogs.openAiPreviewDialog()

      dialogs.fallbackToEditDialog()

      expect(dialogs.dialogs.value.aiPreview).toBe(false)
      expect(dialogs.dialogs.value.edit).toBe(true)
    })
  })

  // ==========================================================================
  // isAnyDialogOpen Computed
  // ==========================================================================

  describe('isAnyDialogOpen Computed', () => {
    it('should return true when edit dialog is open', () => {
      dialogs.openDialog('edit')
      expect(dialogs.isAnyDialogOpen.value).toBe(true)
    })

    it('should return true when multiple dialogs are open', () => {
      dialogs.openDialog('edit')
      dialogs.openDialog('sources')
      expect(dialogs.isAnyDialogOpen.value).toBe(true)
    })

    it('should return false when all dialogs are closed', () => {
      dialogs.openDialog('edit')
      dialogs.closeAllDialogs()
      expect(dialogs.isAnyDialogOpen.value).toBe(false)
    })
  })
})
