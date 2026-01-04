/**
 * Composable for managing Category dialog states
 *
 * Centralizes all dialog states and provides handlers for
 * opening, closing, and managing dialog interactions.
 */
import { ref, computed } from 'vue'
import type { CategoryResponse } from '@/types/category'

/**
 * Dialog identifiers
 */
export type CategoryDialogType =
  | 'edit'
  | 'delete'
  | 'reanalyze'
  | 'sources'
  | 'crawler'
  | 'aiPreview'
  | 'summaryCreate'

/**
 * Dialog state for all category dialogs
 */
export interface CategoryDialogState {
  /** Create/Edit form dialog */
  edit: boolean
  /** Delete confirmation dialog */
  delete: boolean
  /** Reanalyze confirmation dialog */
  reanalyze: boolean
  /** Sources overview dialog */
  sources: boolean
  /** Crawler start dialog */
  crawler: boolean
  /** AI setup preview dialog */
  aiPreview: boolean
  /** Summary create dialog */
  summaryCreate: boolean
}

/**
 * Default dialog state - all closed
 */
const DEFAULT_DIALOG_STATE: CategoryDialogState = {
  edit: false,
  delete: false,
  reanalyze: false,
  sources: false,
  crawler: false,
  aiPreview: false,
  summaryCreate: false,
}

/**
 * Composable for managing category dialog states
 */
export function useCategoryDialogs() {
  // Dialog visibility states
  const dialogs = ref<CategoryDialogState>({ ...DEFAULT_DIALOG_STATE })

  // Edit mode flag
  const isEditMode = ref(false)

  // Reanalyze all flag
  const reanalyzeAll = ref(false)

  // Selected categories for different contexts
  const selectedCategory = ref<CategoryResponse | null>(null)
  const categoryForSources = ref<CategoryResponse | null>(null)
  const categoryForCrawler = ref<CategoryResponse | null>(null)
  const categoryForSummary = ref<CategoryResponse | null>(null)

  // Computed for checking if any dialog is open
  const isAnyDialogOpen = computed(() =>
    Object.values(dialogs.value).some((v) => v)
  )

  /**
   * Open a specific dialog
   */
  function openDialog(dialog: CategoryDialogType) {
    dialogs.value[dialog] = true
  }

  /**
   * Close a specific dialog
   */
  function closeDialog(dialog: CategoryDialogType) {
    dialogs.value[dialog] = false
  }

  /**
   * Close all dialogs
   */
  function closeAllDialogs() {
    dialogs.value = { ...DEFAULT_DIALOG_STATE }
  }

  /**
   * Open create dialog
   */
  function openCreateDialog() {
    selectedCategory.value = null
    isEditMode.value = false
    dialogs.value.edit = true
  }

  /**
   * Open edit dialog for a category
   */
  function openEditDialog(category: CategoryResponse) {
    selectedCategory.value = category
    isEditMode.value = true
    dialogs.value.edit = true
  }

  /**
   * Open delete confirmation dialog
   */
  function openDeleteDialog(category: CategoryResponse) {
    selectedCategory.value = category
    dialogs.value.delete = true
  }

  /**
   * Open reanalyze confirmation dialog
   */
  function openReanalyzeDialog(category: CategoryResponse, analyzeAll = false) {
    selectedCategory.value = category
    reanalyzeAll.value = analyzeAll
    dialogs.value.reanalyze = true
  }

  /**
   * Open sources overview dialog
   */
  function openSourcesDialog(category: CategoryResponse) {
    categoryForSources.value = category
    dialogs.value.sources = true
  }

  /**
   * Open crawler dialog
   */
  function openCrawlerDialog(category: CategoryResponse) {
    categoryForCrawler.value = category
    dialogs.value.crawler = true
  }

  /**
   * Open AI preview dialog
   */
  function openAiPreviewDialog() {
    dialogs.value.aiPreview = true
  }

  /**
   * Open summary create dialog
   */
  function openSummaryDialog(category: CategoryResponse) {
    categoryForSummary.value = category
    dialogs.value.summaryCreate = true
  }

  /**
   * Close edit dialog and reset state
   */
  function closeEditDialog() {
    dialogs.value.edit = false
    // Don't reset selectedCategory immediately to allow animations
  }

  /**
   * Close AI preview and open edit dialog (for fallback)
   */
  function fallbackToEditDialog() {
    dialogs.value.aiPreview = false
    dialogs.value.edit = true
  }

  return {
    // State
    dialogs,
    isEditMode,
    reanalyzeAll,
    selectedCategory,
    categoryForSources,
    categoryForCrawler,
    categoryForSummary,

    // Computed
    isAnyDialogOpen,

    // Generic handlers
    openDialog,
    closeDialog,
    closeAllDialogs,

    // Specific handlers
    openCreateDialog,
    openEditDialog,
    openDeleteDialog,
    openReanalyzeDialog,
    openSourcesDialog,
    openCrawlerDialog,
    openAiPreviewDialog,
    openSummaryDialog,
    closeEditDialog,
    fallbackToEditDialog,
  }
}

export default useCategoryDialogs
