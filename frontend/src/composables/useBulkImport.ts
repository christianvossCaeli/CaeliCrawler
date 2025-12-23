/**
 * Bulk Import Composable
 *
 * Centralized CSV bulk import logic for data sources.
 * Extracted from stores/sources.ts for better modularity.
 *
 * @module composables/useBulkImport
 *
 * ## Features
 * - CSV text and file parsing
 * - Preview with validation
 * - Duplicate detection
 * - Configurable import options
 *
 * ## Usage
 * ```typescript
 * const {
 *   state,
 *   canPreview,
 *   canExecute,
 *   parsePreview,
 *   onFileSelected,
 *   execute,
 *   reset
 * } = useBulkImport({ existingUrls: [...] })
 * ```
 */

import { ref, computed } from 'vue'
import { adminApi } from '@/services/api'
import { parseCsv } from '@/utils/csvParser'
import { isSourceType } from '@/types/sources'
import { BULK_IMPORT } from '@/config/sources'
import { withApiErrorHandling } from '@/utils/apiErrorHandler'
import { useLogger } from './useLogger'
import type {
  BulkImportState,
  DataSourceBulkImport,
  DataSourceBulkImportResult,
  SourceType,
} from '@/types/sources'

/**
 * Options for useBulkImport composable
 */
export interface UseBulkImportOptions {
  /** Callback to get existing URLs for duplicate detection */
  getExistingUrls?: () => string[]
  /** Callback on successful import */
  onSuccess?: (result: DataSourceBulkImportResult) => void
  /** Callback on import error */
  onError?: (error: Error) => void
}

/**
 * Composable for CSV bulk import functionality
 */
export function useBulkImport(options: UseBulkImportOptions = {}) {
  const { getExistingUrls = () => [], onSuccess, onError } = options

  const logger = useLogger('BulkImport')

  // ==========================================================================
  // State
  // ==========================================================================

  const state = ref<BulkImportState>({
    category_ids: [],
    default_tags: [],
    inputMode: 'text',
    csvText: '',
    csvFile: null,
    preview: [],
    validCount: 0,
    duplicateCount: 0,
    errorCount: 0,
    importing: false,
    skip_duplicates: true,
  })

  /** CSV validation error message */
  const validationError = ref<string | null>(null)

  /** General error from API */
  const error = ref<string | null>(null)

  // ==========================================================================
  // Computed
  // ==========================================================================

  /** Whether preview can be generated */
  const canPreview = computed(() => {
    if (state.value.inputMode === 'text') {
      return state.value.csvText.trim().length > 0
    }
    return state.value.csvFile !== null
  })

  /** Whether import can be executed */
  const canExecute = computed(() => {
    return state.value.category_ids.length > 0 && state.value.validCount > 0
  })

  /** Whether currently importing */
  const isImporting = computed(() => state.value.importing)

  // ==========================================================================
  // Functions
  // ==========================================================================

  /**
   * Reset bulk import state to defaults
   */
  function reset(): void {
    state.value = {
      category_ids: [],
      default_tags: [],
      inputMode: 'text',
      csvText: '',
      csvFile: null,
      preview: [],
      validCount: 0,
      duplicateCount: 0,
      errorCount: 0,
      importing: false,
      skip_duplicates: true,
    }
    validationError.value = null
    error.value = null
  }

  /**
   * Parse CSV text and update preview state
   */
  function parsePreview(): void {
    const text = state.value.csvText
    validationError.value = null

    if (!text.trim()) {
      state.value.preview = []
      state.value.validCount = 0
      state.value.duplicateCount = 0
      state.value.errorCount = 0
      return
    }

    // Check file size limit
    if (text.length > BULK_IMPORT.MAX_FILE_SIZE) {
      validationError.value = `CSV exceeds maximum size of ${BULK_IMPORT.MAX_FILE_SIZE / 1024 / 1024}MB`
      state.value.preview = []
      state.value.validCount = 0
      state.value.errorCount = 1
      return
    }

    // Use centralized CSV parser
    const existingUrls = getExistingUrls()
    const result = parseCsv(text, {
      defaultTags: state.value.default_tags,
      existingUrls,
      skipDuplicates: state.value.skip_duplicates,
    })

    // Handle validation errors from parser
    if (result.error) {
      validationError.value = result.error
      state.value.preview = []
      state.value.validCount = 0
      state.value.duplicateCount = 0
      state.value.errorCount = 1
      return
    }

    // Check line count
    if (result.items.length > BULK_IMPORT.MAX_LINES) {
      validationError.value = `CSV exceeds maximum of ${BULK_IMPORT.MAX_LINES} lines`
      state.value.preview = []
      state.value.validCount = 0
      state.value.errorCount = 1
      return
    }

    // Update state with parse results
    state.value.preview = result.items
    state.value.validCount = result.validCount
    state.value.duplicateCount = result.duplicateCount
    state.value.errorCount = result.errorCount
  }

  /**
   * Handle CSV file selection
   */
  async function onFileSelected(files: File | File[] | null): Promise<void> {
    if (!files) return
    const file = Array.isArray(files) ? files[0] : files
    if (!file) return

    // Check file size
    if (file.size > BULK_IMPORT.MAX_FILE_SIZE) {
      validationError.value = `File exceeds maximum size of ${BULK_IMPORT.MAX_FILE_SIZE / 1024 / 1024}MB`
      return
    }

    try {
      const text = await file.text()
      state.value.csvText = text
      state.value.csvFile = file
      parsePreview()
    } catch (err) {
      logger.error('Failed to read CSV file', err)
      validationError.value = 'Failed to read file'
    }
  }

  /**
   * Execute the bulk import
   */
  async function execute(): Promise<DataSourceBulkImportResult | null> {
    if (!canExecute.value) {
      throw new Error('Cannot execute bulk import: missing requirements')
    }

    state.value.importing = true
    error.value = null

    try {
      const result = await withApiErrorHandling(
        async () => {
          // Filter valid items with type validation
          const validItems = state.value.preview.filter((item) => {
            if (item.error) return false
            if (item.duplicate && state.value.skip_duplicates) return false
            if (!isSourceType(item.source_type)) return false
            return true
          })

          // Build sources array for API
          const sourcesToImport = validItems.map((item) => ({
            name: item.name,
            base_url: item.base_url,
            source_type: item.source_type as SourceType,
            tags: item.tags,
          }))

          const importData: DataSourceBulkImport = {
            category_ids: state.value.category_ids,
            default_tags: state.value.default_tags,
            sources: sourcesToImport,
            skip_duplicates: state.value.skip_duplicates,
          }

          const response = await adminApi.bulkImportSources(importData)
          return response.data
        },
        { errorRef: error, fallbackMessage: 'Bulk import failed' }
      )

      if (result) {
        logger.info('Bulk import completed', {
          imported: result.imported,
          skipped: result.skipped,
        })
        onSuccess?.(result as DataSourceBulkImportResult)
      }

      return result as DataSourceBulkImportResult | null
    } catch (err) {
      const importError = err instanceof Error ? err : new Error('Bulk import failed')
      logger.error('Bulk import failed', err)
      onError?.(importError)
      return null
    } finally {
      state.value.importing = false
    }
  }

  /**
   * Update a state property
   */
  function updateState<K extends keyof BulkImportState>(
    key: K,
    value: BulkImportState[K]
  ): void {
    state.value[key] = value
  }

  // ==========================================================================
  // Return
  // ==========================================================================

  return {
    // State
    state,
    validationError,
    error,

    // Computed
    canPreview,
    canExecute,
    isImporting,

    // Functions
    reset,
    parsePreview,
    onFileSelected,
    execute,
    updateState,
  }
}
