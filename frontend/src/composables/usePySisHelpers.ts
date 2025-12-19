/**
 * PySis helpers composable - extracted from PySisTab.vue.
 *
 * Provides formatting and display utilities for PySis integration:
 * - Sync status colors and icons
 * - Field value source colors
 * - Confidence score colors
 * - History action formatting
 * - Value truncation
 */
import { format } from 'date-fns'
import { de } from 'date-fns/locale'

export function usePySisHelpers() {
  /**
   * Get sync status color
   */
  function getSyncStatusColor(status: string): string {
    const colors: Record<string, string> = {
      synced: 'success',
      pending: 'warning',
      error: 'error',
      out_of_sync: 'orange',
    }
    return colors[status] || 'grey'
  }

  /**
   * Get sync status icon
   */
  function getSyncStatusIcon(status: string): string {
    const icons: Record<string, string> = {
      synced: 'mdi-check-circle',
      pending: 'mdi-clock-outline',
      error: 'mdi-alert-circle',
      out_of_sync: 'mdi-sync-alert',
    }
    return icons[status] || 'mdi-help-circle'
  }

  /**
   * Get field value source color
   */
  function getSourceColor(source: string): string {
    const colors: Record<string, string> = {
      MANUAL: 'primary',
      AI: 'info',
      PYSIS: 'secondary',
      TEMPLATE: 'purple',
    }
    return colors[source] || 'grey'
  }

  /**
   * Get confidence score color
   */
  function getConfidenceColor(score: number | null | undefined): string {
    if (!score) return 'grey'
    if (score >= 0.8) return 'success'
    if (score >= 0.6) return 'info'
    if (score >= 0.4) return 'warning'
    return 'error'
  }

  /**
   * Format date for display
   */
  function formatDate(dateStr: string | null | undefined): string {
    if (!dateStr) return '-'
    try {
      return format(new Date(dateStr), 'dd.MM.yyyy HH:mm', { locale: de })
    } catch {
      return dateStr
    }
  }

  /**
   * Truncate long values for display
   */
  function truncateValue(value: string | null | undefined, maxLength = 100): string {
    if (!value) return ''
    if (value.length <= maxLength) return value
    return value.substring(0, maxLength) + '...'
  }

  // History helpers
  /**
   * Format history action for display
   */
  function formatHistoryAction(action: string): string {
    const actions: Record<string, string> = {
      created: 'Erstellt',
      updated: 'Aktualisiert',
      ai_generated: 'KI-generiert',
      accepted: 'Akzeptiert',
      rejected: 'Abgelehnt',
      synced_from_pysis: 'Von PySis',
      synced_to_pysis: 'Zu PySis',
    }
    return actions[action] || action
  }

  /**
   * Get history action color
   */
  function getHistoryActionColor(action: string): string {
    const colors: Record<string, string> = {
      created: 'success',
      updated: 'primary',
      ai_generated: 'info',
      accepted: 'success',
      rejected: 'error',
      synced_from_pysis: 'secondary',
      synced_to_pysis: 'secondary',
    }
    return colors[action] || 'grey'
  }

  /**
   * Get history action icon
   */
  function getHistoryActionIcon(action: string): string {
    const icons: Record<string, string> = {
      created: 'mdi-plus-circle',
      updated: 'mdi-pencil',
      ai_generated: 'mdi-auto-fix',
      accepted: 'mdi-check',
      rejected: 'mdi-close',
      synced_from_pysis: 'mdi-download',
      synced_to_pysis: 'mdi-upload',
    }
    return icons[action] || 'mdi-circle'
  }

  /**
   * Get history item CSS class
   */
  function getHistoryItemClass(action: string): string {
    if (action === 'rejected') return 'bg-error-lighten-5'
    if (action === 'accepted') return 'bg-success-lighten-5'
    return ''
  }

  // Field type options
  const fieldTypes = [
    { title: 'Text', value: 'text' },
    { title: 'Zahl', value: 'number' },
    { title: 'Datum', value: 'date' },
    { title: 'Boolean', value: 'boolean' },
    { title: 'JSON', value: 'json' },
  ]

  return {
    // Sync status
    getSyncStatusColor,
    getSyncStatusIcon,

    // Field source
    getSourceColor,

    // Confidence
    getConfidenceColor,

    // Formatting
    formatDate,
    truncateValue,

    // History
    formatHistoryAction,
    getHistoryActionColor,
    getHistoryActionIcon,
    getHistoryItemClass,

    // Constants
    fieldTypes,
  }
}
