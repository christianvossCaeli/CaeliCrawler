/**
 * Facet Helpers Composable
 *
 * Common helper functions for facet operations.
 */

import { useDateFormatter } from '@/composables/useDateFormatter'
import { formatDistanceToNow } from 'date-fns'

export function useFacetHelpers() {
  const { dateLocale, formatDate: formatLocaleDate } = useDateFormatter()

  function formatDate(dateStr: string): string {
    return formatLocaleDate(dateStr, 'dd.MM.yyyy HH:mm')
  }

  function formatEnrichmentDate(dateStr: string | null): string {
    if (!dateStr) return '-'
    try {
      return formatDistanceToNow(new Date(dateStr), { addSuffix: true, locale: dateLocale.value })
    } catch {
      return dateStr
    }
  }

  function getConfidenceColor(score: number | null): string {
    if (!score) return 'grey'
    if (score >= 0.8) return 'success'
    if (score >= 0.5) return 'warning'
    return 'error'
  }

  function normalizeSourceType(sourceType: string | null | undefined): string {
    return (sourceType || 'DOCUMENT').toLowerCase().replace('_', '_')
  }

  function getFacetSourceColor(sourceType: string | null | undefined): string {
    const colors: Record<string, string> = {
      document: 'blue',
      manual: 'purple',
      pysis: 'deep-purple',
      smart_query: 'green',
      ai_assistant: 'indigo',
      import: 'teal',
    }
    return colors[normalizeSourceType(sourceType)] || 'grey'
  }

  function getFacetSourceIcon(sourceType: string | null | undefined): string {
    const icons: Record<string, string> = {
      document: 'mdi-file-document',
      manual: 'mdi-hand-pointing-right',
      pysis: 'mdi-database-cog',
      smart_query: 'mdi-code-tags',
      ai_assistant: 'mdi-robot',
      import: 'mdi-import',
    }
    return icons[normalizeSourceType(sourceType)] || 'mdi-file-document'
  }

  return {
    formatDate,
    formatEnrichmentDate,
    getConfidenceColor,
    normalizeSourceType,
    getFacetSourceColor,
    getFacetSourceIcon,
  }
}
