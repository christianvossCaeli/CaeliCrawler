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
   * Reject a single result with optimistic update.
   * Also deactivates related facet values (unless protected).
   */
  async function rejectResult(item: SearchResult): Promise<void> {
    if (!state.canVerify.value) return
    if (item.is_rejected) return

    const itemId = item.id
    const originalResults = [...state.results.value]
    const originalStats = { ...state.stats.value }

    // Optimistic update
    const index = state.results.value.findIndex((r) => r.id === itemId)
    if (index !== -1) {
      const wasVerified = state.results.value[index].human_verified
      state.results.value[index] = {
        ...state.results.value[index],
        is_rejected: true,
        human_verified: false,
      }
      // Update stats if it was previously verified
      if (wasVerified) {
        state.stats.value = {
          ...state.stats.value,
          verified: Math.max(0, (state.stats.value.verified || 0) - 1),
          unverified: (state.stats.value.unverified || 0) + 1,
        }
      }
    }

    try {
      const response = await dataApi.rejectExtraction(itemId, {
        rejected: true,
        cascade_to_facets: true,
      })

      const { deactivated_facets_count, protected_facets_count } = response.data
      let message = t('results.messages.rejected')
      if (deactivated_facets_count > 0) {
        message += ` (${deactivated_facets_count} ${t('results.messages.facetsDeactivated')})`
      }
      if (protected_facets_count > 0) {
        message += ` (${protected_facets_count} ${t('results.messages.facetsProtected')})`
      }
      showSuccess(message)

      // If not showing rejected, remove from list
      if (!state.showRejected.value) {
        state.results.value = state.results.value.filter((r) => r.id !== itemId)
        state.totalResults.value = Math.max(0, state.totalResults.value - 1)
      }
    } catch (error) {
      // Rollback on error
      state.results.value = originalResults
      state.stats.value = originalStats
      logger.error('Failed to reject result:', error)
      showError(getErrorMessage(error) || t('results.messages.errorRejecting'))
    }
  }

  /**
   * Unreject a previously rejected result.
   */
  async function unrejectResult(item: SearchResult): Promise<void> {
    if (!state.canVerify.value) return
    if (!item.is_rejected) return

    const itemId = item.id
    const originalResults = [...state.results.value]

    // Optimistic update
    const index = state.results.value.findIndex((r) => r.id === itemId)
    if (index !== -1) {
      state.results.value[index] = {
        ...state.results.value[index],
        is_rejected: false,
      }
    }

    try {
      await dataApi.rejectExtraction(itemId, { rejected: false })
      showSuccess(t('results.messages.unrejected'))
    } catch (error) {
      // Rollback on error
      state.results.value = originalResults
      logger.error('Failed to unreject result:', error)
      showError(getErrorMessage(error) || t('results.messages.errorUnrejecting'))
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

  /**
   * Bulk reject selected results using the batch API.
   */
  async function bulkReject(): Promise<void> {
    if (!state.canVerify.value) return
    if (state.selectedResults.value.length === 0) return

    state.bulkRejecting.value = true

    try {
      const idsToReject = [...state.selectedResults.value]
      const toReject = idsToReject.filter((id) => {
        const item = state.results.value.find((r) => r.id === id)
        return item && !item.is_rejected
      })

      if (toReject.length === 0) {
        state.selectedResults.value = []
        return
      }

      // Use batch API for efficient rejection
      const response = await dataApi.bulkRejectExtractions({
        ids: toReject,
        cascade_to_facets: true,
      })
      const {
        rejected_ids,
        failed_count,
        total_deactivated_facets,
        total_protected_facets,
      } = response.data

      // Update local state for rejected items
      let rejectedCount = 0
      for (const id of rejected_ids) {
        const index = state.results.value.findIndex((r) => r.id === id)
        if (index !== -1 && !state.results.value[index].is_rejected) {
          const wasVerified = state.results.value[index].human_verified
          state.results.value[index] = {
            ...state.results.value[index],
            is_rejected: true,
            human_verified: false,
          }
          rejectedCount++

          // Update stats if it was previously verified
          if (wasVerified) {
            state.stats.value = {
              ...state.stats.value,
              verified: Math.max(0, (state.stats.value.verified || 0) - 1),
              unverified: (state.stats.value.unverified || 0) + 1,
            }
          }
        }
      }

      // Build success message
      if (rejectedCount > 0) {
        let message = `${rejectedCount} ${t('results.messages.bulkRejected')}`
        if (total_deactivated_facets > 0) {
          message += ` (${total_deactivated_facets} ${t('results.messages.facetsDeactivated')})`
        }
        if (total_protected_facets > 0) {
          message += ` (${total_protected_facets} ${t('results.messages.facetsProtected')})`
        }
        showSuccess(message)

        // If not showing rejected, remove from list
        if (!state.showRejected.value) {
          state.results.value = state.results.value.filter(
            (r) => !rejected_ids.includes(r.id)
          )
          state.totalResults.value = Math.max(0, state.totalResults.value - rejectedCount)
        }
      }

      if (failed_count > 0) {
        showError(t('results.messages.errorBulkRejecting'))
      }

      state.selectedResults.value = []
    } catch (error) {
      logger.error('Failed to bulk reject:', error)
      showError(getErrorMessage(error) || t('results.messages.errorBulkRejecting'))
    } finally {
      state.bulkRejecting.value = false
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

  // Reserved content fields that are handled separately
  const RESERVED_CONTENT_FIELDS = new Set([
    'is_relevant', 'relevanz', 'summary', 'municipality', 'zusammenfassung',
  ])

  /**
   * Export results as CSV.
   * - If results are selected: export only selected results
   * - If no selection: export all results matching current filters via API
   * - Dynamic content fields are automatically detected and included
   */
  async function exportCsv(): Promise<void> {
    state.exporting.value = true

    try {
      let resultsToExport: SearchResult[]

      if (state.selectedResults.value.length > 0) {
        // Export only selected results
        const selectedIds = new Set(state.selectedResults.value)
        resultsToExport = state.results.value.filter((r) => selectedIds.has(r.id))
        logger.debug(`Exporting ${resultsToExport.length} selected results`)
      } else {
        // Export all results matching current filters via API
        const params = {
          per_page: 10000, // Get all results
          search: state.searchQuery.value || undefined,
          extraction_type: state.extractionTypeFilter.value || undefined,
          category_id: state.categoryFilter.value || undefined,
          min_confidence: state.confidenceRange.value[0] > 0 ? state.confidenceRange.value[0] / 100 : undefined,
          max_confidence: state.confidenceRange.value[1] < 100 ? state.confidenceRange.value[1] / 100 : undefined,
          human_verified: state.verifiedFilter.value ?? undefined,
          include_rejected: state.showRejected.value || undefined,
          created_from: state.dateFrom.value || undefined,
          created_to: state.dateTo.value || undefined,
        }

        const response = await dataApi.getExtractedData(params)
        resultsToExport = response.data.items || []
        logger.debug(`Exporting ${resultsToExport.length} results (all matching filters)`)
      }

      if (resultsToExport.length === 0) {
        showError(t('results.messages.noResultsToExport'))
        return
      }

      // Collect all unique dynamic content field keys across all results
      const dynamicFieldKeys = new Set<string>()
      for (const r of resultsToExport) {
        const content = r.final_content || r.extracted_content || {}
        for (const key of Object.keys(content)) {
          if (!RESERVED_CONTENT_FIELDS.has(key) && content[key] != null) {
            dynamicFieldKeys.add(key)
          }
        }
      }
      const sortedDynamicKeys = Array.from(dynamicFieldKeys).sort()

      // Build headers: fixed fields + dynamic content fields
      const csvHeaders = [
        'ID',
        t('results.columns.document'),
        t('results.detail.url'),
        t('results.export.source'),
        t('results.columns.type'),
        t('results.columns.municipality'),
        t('results.columns.confidence'),
        t('results.columns.verified'),
        t('results.export.verifiedBy'),
        t('results.export.verifiedAt'),
        t('results.export.rejected'),
        t('results.export.rejectionReason'),
        t('results.columns.created'),
        t('results.export.entities'),
        t('results.detail.summary'),
        // Dynamic content field headers
        ...sortedDynamicKeys.map(formatFieldLabel),
        // Meta fields at the end
        t('results.export.aiModel'),
        t('results.export.tokensUsed'),
      ]

      const csvRows = resultsToExport.map((r) => {
        const content = r.final_content || r.extracted_content || {}
        return [
          r.id,
          escapeCSV(r.document_title || ''),
          escapeCSV(r.document_url || ''),
          escapeCSV(r.source_name || ''),
          r.extraction_type || '',
          escapeCSV(String(content.municipality || '')),
          r.confidence_score ? `${(r.confidence_score * 100).toFixed(0)}%` : '',
          r.human_verified ? t('common.yes') : t('common.no'),
          escapeCSV(r.verified_by || ''),
          r.verified_at || '',
          r.is_rejected ? t('common.yes') : t('common.no'),
          escapeCSV(r.rejection_reason || ''),
          r.created_at || '',
          escapeCSV(formatEntityReferences(r.entity_references)),
          escapeCSV((String(content.summary || content.zusammenfassung || '')).substring(0, EXPORT_CONFIG.CSV_MAX_SUMMARY_LENGTH)),
          // Dynamic content field values
          ...sortedDynamicKeys.map((key) => escapeCSV(formatDynamicValue(content[key]))),
          // Meta fields
          escapeCSV(r.ai_model_used || ''),
          r.tokens_used?.toString() || '',
        ]
      })

      const csv = [csvHeaders.join(','), ...csvRows.map((r) => r.join(','))].join('\n')
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
      downloadBlob(blob, `ergebnisse-${format(new Date(), EXPORT_CONFIG.CSV_DATE_FORMAT)}.csv`)
      showSuccess(t('results.messages.csvExported', { count: resultsToExport.length }))
    } catch (error) {
      logger.error('Failed to export results:', error)
      showError(t('results.messages.errorExporting'))
    } finally {
      state.exporting.value = false
    }
  }

  /**
   * Format a field label from snake_case to Title Case.
   */
  function formatFieldLabel(key: string): string {
    return key
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  /**
   * Format any dynamic content value for CSV export.
   */
  function formatDynamicValue(value: unknown): string {
    if (value === null || value === undefined) return ''

    // Handle arrays
    if (Array.isArray(value)) {
      return value
        .map((item) => {
          if (typeof item === 'string') return item
          if (typeof item === 'object' && item !== null) {
            // Try common text fields
            const textValue = (item as Record<string, unknown>).description
              || (item as Record<string, unknown>).text
              || (item as Record<string, unknown>).concern
              || (item as Record<string, unknown>).name
              || (item as Record<string, unknown>).person
              || (item as Record<string, unknown>).value
            if (textValue) {
              // Add role/position if available
              const role = (item as Record<string, unknown>).role || (item as Record<string, unknown>).position
              const email = (item as Record<string, unknown>).email
              let result = String(textValue)
              if (role) result += ` (${role})`
              if (email) result += ` <${email}>`
              return result
            }
            // Fallback: stringify object
            return JSON.stringify(item)
          }
          return String(item)
        })
        .filter(Boolean)
        .join('; ')
    }

    // Handle objects (like outreach_recommendation)
    if (typeof value === 'object') {
      const obj = value as Record<string, unknown>
      // Try to extract meaningful text
      const parts: string[] = []
      if (obj.priority) parts.push(`${t('results.export.priority')}: ${obj.priority}`)
      if (obj.reason) parts.push(`${t('results.export.reason')}: ${obj.reason}`)
      if (parts.length > 0) return parts.join(' | ')
      // Fallback: stringify
      return JSON.stringify(value)
    }

    // Handle primitives
    return String(value)
  }

  /**
   * Format entity references for CSV export.
   */
  function formatEntityReferences(refs?: SearchResult['entity_references']): string {
    if (!refs || refs.length === 0) return ''
    return refs
      .map((ref) => {
        const parts = [ref.entity_name]
        if (ref.entity_type) parts.push(`(${ref.entity_type})`)
        if (ref.role) parts.push(`[${ref.role}]`)
        return parts.join(' ')
      })
      .join('; ')
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

    // Reject Actions
    rejectResult,
    unrejectResult,
    bulkReject,

    // Export Actions
    exportJson,
    exportCsv,

    // Clipboard
    copyToClipboard,
  }
}
