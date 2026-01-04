/**
 * Results Actions Composable
 *
 * Handles user actions: verify, bulk verify, export, clipboard operations.
 */

import { format } from 'date-fns'
import { useI18n } from 'vue-i18n'
import { dataApi } from '@/services/api'
import { useSnackbar } from '@/composables/useSnackbar'
import { useLogger } from '@/composables/useLogger'
import { getErrorMessage } from '@/utils/errorMessage'
import { EXPORT_CONFIG } from './constants'
import type { ResultsState } from './useResultsState'
import type { SearchResult } from './types'

// =============================================================================
// Composable
// =============================================================================

export function useResultsActions(state: ResultsState) {
  const logger = useLogger('useResultsActions')
  const { t } = useI18n()
  const { showSuccess, showError } = useSnackbar()

  // ===========================================================================
  // Dialog Actions
  // ===========================================================================

  /**
   * Show details dialog for a result item.
   */
  function showDetails(item: SearchResult): void {
    state.selectedResult.value = item
    state.detailsDialog.value = true
  }

  /**
   * Close details dialog.
   */
  function closeDetails(): void {
    state.detailsDialog.value = false
    state.selectedResult.value = null
  }

  // ===========================================================================
  // Verify Actions
  // ===========================================================================

  /**
   * Verify a single result with optimistic update.
   */
  async function verifyResult(item: SearchResult): Promise<void> {
    if (!state.canVerify.value) return
    if (item.human_verified) return

    const itemId = item.id
    const originalResults = [...state.results.value]
    const originalStats = { ...state.stats.value }

    // Optimistic update
    const index = state.results.value.findIndex((r) => r.id === itemId)
    if (index !== -1) {
      state.results.value[index] = { ...state.results.value[index], human_verified: true }
      state.stats.value = {
        ...state.stats.value,
        verified: (state.stats.value.verified || 0) + 1,
        unverified: Math.max(0, (state.stats.value.unverified || 0) - 1),
      }
    }

    try {
      await dataApi.verifyExtraction(itemId, { verified: true })
      showSuccess(t('results.messages.verified'))
    } catch (error) {
      // Rollback on error
      state.results.value = originalResults
      state.stats.value = originalStats
      logger.error('Failed to verify result:', error)
      showError(getErrorMessage(error) || t('results.messages.errorVerifying'))
    }
  }

  /**
   * Bulk verify selected results using the batch API.
   */
  async function bulkVerify(): Promise<void> {
    if (!state.canVerify.value) return
    if (state.selectedResults.value.length === 0) return

    state.bulkVerifying.value = true

    try {
      const idsToVerify = [...state.selectedResults.value]
      const toVerify = idsToVerify.filter((id) => {
        const item = state.results.value.find((r) => r.id === id)
        return item && !item.human_verified
      })

      if (toVerify.length === 0) {
        state.selectedResults.value = []
        return
      }

      // Use batch API for efficient verification
      const response = await dataApi.bulkVerifyExtractions({ ids: toVerify })
      const { verified_ids, failed_count } = response.data

      // Update local state for verified items
      let verifiedCount = 0
      for (const id of verified_ids) {
        const index = state.results.value.findIndex((r) => r.id === id)
        if (index !== -1 && !state.results.value[index].human_verified) {
          state.results.value[index] = { ...state.results.value[index], human_verified: true }
          verifiedCount++
        }
      }

      // Update stats
      if (verifiedCount > 0) {
        showSuccess(`${verifiedCount} ${t('results.messages.bulkVerified')}`)
        state.stats.value = {
          ...state.stats.value,
          verified: (state.stats.value.verified || 0) + verifiedCount,
          unverified: Math.max(0, (state.stats.value.unverified || 0) - verifiedCount),
        }
      }

      if (failed_count > 0) {
        showError(t('results.messages.errorBulkVerifying'))
      }

      state.selectedResults.value = []
    } catch (error) {
      logger.error('Failed to bulk verify:', error)
      showError(getErrorMessage(error) || t('results.messages.errorBulkVerifying'))
    } finally {
      state.bulkVerifying.value = false
    }
  }

  // ===========================================================================
  // Export Actions
  // ===========================================================================

  /**
   * Export a single result as JSON.
   */
  function exportJson(item: SearchResult): void {
    const data = {
      id: item.id,
      document_title: item.document_title,
      document_url: item.document_url,
      source_name: item.source_name,
      extraction_type: item.extraction_type,
      confidence_score: item.confidence_score,
      human_verified: item.human_verified,
      entity_references: item.entity_references,
      created_at: item.created_at,
      content: item.final_content || item.extracted_content,
    }

    const blob = new Blob(
      [JSON.stringify(data, null, EXPORT_CONFIG.JSON_INDENT)],
      { type: 'application/json' }
    )
    downloadBlob(blob, `extraction-${item.id}.json`)
    showSuccess(t('results.messages.jsonExported'))
  }

  /**
   * Export current results as CSV.
   */
  function exportCsv(): void {
    const csvHeaders = [
      t('results.columns.document'),
      t('results.detail.url'),
      t('results.columns.type'),
      t('results.columns.municipality'),
      t('results.columns.confidence'),
      t('results.columns.verified'),
      t('results.columns.created'),
      t('results.detail.summary'),
    ]

    const csvRows = state.results.value.map((r) => {
      const content = r.final_content || r.extracted_content || {}
      return [
        escapeCSV(r.document_title || ''),
        escapeCSV(r.document_url || ''),
        r.extraction_type || '',
        escapeCSV(String(content.municipality || '')),
        r.confidence_score ? `${(r.confidence_score * 100).toFixed(0)}%` : '',
        r.human_verified ? t('common.yes') : t('common.no'),
        r.created_at || '',
        escapeCSV((String(content.summary || '')).substring(0, EXPORT_CONFIG.CSV_MAX_SUMMARY_LENGTH)),
      ]
    })

    const csv = [csvHeaders.join(','), ...csvRows.map((r) => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    downloadBlob(blob, `ergebnisse-${format(new Date(), EXPORT_CONFIG.CSV_DATE_FORMAT)}.csv`)
    showSuccess(t('results.messages.csvExported'))
  }

  // ===========================================================================
  // Clipboard Actions
  // ===========================================================================

  /**
   * Copy text to clipboard.
   */
  function copyToClipboard(text?: string): void {
    if (!text) return
    navigator.clipboard.writeText(text)
    showSuccess(t('results.messages.copiedToClipboard'))
  }

  // ===========================================================================
  // Helper Functions
  // ===========================================================================

  /**
   * Escape a value for CSV output.
   */
  function escapeCSV(value: string): string {
    if (value.includes(',') || value.includes('"') || value.includes('\n')) {
      return `"${value.replace(/"/g, '""')}"`
    }
    return value
  }

  /**
   * Trigger download of a blob.
   */
  function downloadBlob(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // ===========================================================================
  // Return
  // ===========================================================================

  return {
    // Dialog Actions
    showDetails,
    closeDetails,

    // Verify Actions
    verifyResult,
    bulkVerify,

    // Export Actions
    exportJson,
    exportCsv,

    // Clipboard
    copyToClipboard,
  }
}
