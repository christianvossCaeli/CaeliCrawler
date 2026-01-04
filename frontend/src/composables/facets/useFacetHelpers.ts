/**
 * Facet Helpers Composable
 *
 * Common helper functions for facet operations.
 * Uses centralized mappings from @/config/facetMappings for consistency.
 */

import { useDateFormatter } from '@/composables/useDateFormatter'
import { formatDistanceToNow } from 'date-fns'
import {
  getConfidenceColor as _getConfidenceColor,
  getSourceTypeColor,
  getSourceTypeIcon,
} from '@/config/facetMappings'

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

  /**
   * Get confidence score color
   * @see {@link @/config/facetMappings} for centralized configuration
   */
  function getConfidenceColor(score: number | null): string {
    return _getConfidenceColor(score)
  }

  /**
   * Get facet source color
   * @see {@link @/config/facetMappings} for centralized configuration
   */
  function getFacetSourceColor(sourceType: string | null | undefined): string {
    return getSourceTypeColor(sourceType)
  }

  /**
   * Get facet source icon
   * @see {@link @/config/facetMappings} for centralized configuration
   */
  function getFacetSourceIcon(sourceType: string | null | undefined): string {
    return getSourceTypeIcon(sourceType)
  }

  return {
    formatDate,
    formatEnrichmentDate,
    getConfidenceColor,
    getFacetSourceColor,
    getFacetSourceIcon,
  }
}
