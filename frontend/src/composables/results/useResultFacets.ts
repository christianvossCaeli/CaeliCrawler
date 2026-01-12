/**
 * Result Facets Composable
 *
 * Handles loading and managing facet values for an extraction result.
 * Supports verify, reject (deactivate), and edit operations.
 */

import { ref, computed, type Ref, type ComputedRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { dataApi, facetApi } from '@/services/api'
import { useSnackbar } from '@/composables/useSnackbar'
import { useLogger } from '@/composables/useLogger'
import { getErrorMessage } from '@/utils/errorMessage'
import type { FacetValue, FacetValueUpdate } from '@/types/entity'

// =============================================================================
// Types
// =============================================================================

export interface FacetGroup {
  facet_type_id: string
  facet_type_slug: string
  facet_type_name: string
  values: FacetValue[]
}

export interface ResultFacetsState {
  loading: Ref<boolean>
  facets: Ref<FacetValue[]>
  includeInactive: Ref<boolean>
  error: Ref<string | null>
  // Computed
  facetCount: ComputedRef<number>
  activeCount: ComputedRef<number>
  verifiedCount: ComputedRef<number>
  groupedFacets: ComputedRef<FacetGroup[]>
}

// =============================================================================
// Composable
// =============================================================================

export function useResultFacets(extractionId: Ref<string | null>) {
  const logger = useLogger('useResultFacets')
  const { t } = useI18n()
  const { showSuccess, showError } = useSnackbar()

  // ===========================================================================
  // State
  // ===========================================================================

  const loading = ref(false)
  const facets = ref<FacetValue[]>([])
  const includeInactive = ref(false)
  const error = ref<string | null>(null)

  // ===========================================================================
  // Computed
  // ===========================================================================

  const facetCount = computed(() => facets.value.length)

  const activeCount = computed(() =>
    facets.value.filter((f) => f.is_active !== false).length
  )

  const verifiedCount = computed(() =>
    facets.value.filter((f) => f.human_verified).length
  )

  /**
   * Group facets by facet_type for display.
   */
  const groupedFacets = computed<FacetGroup[]>(() => {
    const groups = new Map<string, FacetGroup>()

    for (const facet of facets.value) {
      const typeId = facet.facet_type_id || 'unknown'
      const existing = groups.get(typeId)

      if (existing) {
        existing.values.push(facet)
      } else {
        groups.set(typeId, {
          facet_type_id: typeId,
          facet_type_slug: facet.facet_type_slug || '',
          facet_type_name: facet.facet_type_name || t('results.facets.unknownType'),
          values: [facet],
        })
      }
    }

    return Array.from(groups.values())
  })

  // ===========================================================================
  // Data Loading
  // ===========================================================================

  /**
   * Load facets for the current extraction.
   */
  async function loadFacets(): Promise<void> {
    if (!extractionId.value) {
      facets.value = []
      return
    }

    loading.value = true
    error.value = null

    try {
      const response = await dataApi.getExtractionFacets(extractionId.value, {
        include_inactive: includeInactive.value,
      })
      facets.value = response.data
      logger.debug(`Loaded ${facets.value.length} facets for extraction`)
    } catch (err) {
      logger.error('Failed to load facets:', err)
      error.value = getErrorMessage(err) || t('results.facets.errorLoading')
      facets.value = []
    } finally {
      loading.value = false
    }
  }

  /**
   * Reload facets (e.g., after an action).
   */
  async function refresh(): Promise<void> {
    await loadFacets()
  }

  // ===========================================================================
  // Actions
  // ===========================================================================

  /**
   * Verify a facet value.
   */
  async function verifyFacet(facetId: string): Promise<boolean> {
    const facet = facets.value.find((f) => f.id === facetId)
    if (!facet) return false

    // Optimistic update
    const originalVerified = facet.human_verified
    facet.human_verified = true

    try {
      await facetApi.verifyFacetValue(facetId, { verified: true })
      showSuccess(t('results.facets.verified'))
      return true
    } catch (err) {
      // Rollback
      facet.human_verified = originalVerified
      logger.error('Failed to verify facet:', err)
      showError(getErrorMessage(err) || t('results.facets.errorVerifying'))
      return false
    }
  }

  /**
   * Reject (deactivate) a facet value.
   */
  async function rejectFacet(facetId: string): Promise<boolean> {
    const facet = facets.value.find((f) => f.id === facetId)
    if (!facet) return false

    // Optimistic update
    const originalActive = facet.is_active

    try {
      await facetApi.updateFacetValue(facetId, { is_active: false } as FacetValueUpdate)

      // Remove from list if not showing inactive
      if (!includeInactive.value) {
        facets.value = facets.value.filter((f) => f.id !== facetId)
      } else {
        facet.is_active = false
      }

      showSuccess(t('results.facets.rejected'))
      return true
    } catch (err) {
      // Rollback
      facet.is_active = originalActive
      logger.error('Failed to reject facet:', err)
      showError(getErrorMessage(err) || t('results.facets.errorRejecting'))
      return false
    }
  }

  /**
   * Reactivate a previously rejected facet.
   */
  async function reactivateFacet(facetId: string): Promise<boolean> {
    const facet = facets.value.find((f) => f.id === facetId)
    if (!facet) return false

    // Optimistic update
    const originalActive = facet.is_active
    facet.is_active = true

    try {
      await facetApi.updateFacetValue(facetId, { is_active: true } as FacetValueUpdate)
      showSuccess(t('results.facets.reactivated'))
      return true
    } catch (err) {
      // Rollback
      facet.is_active = originalActive
      logger.error('Failed to reactivate facet:', err)
      showError(getErrorMessage(err) || t('results.facets.errorReactivating'))
      return false
    }
  }

  /**
   * Update a facet value.
   */
  async function updateFacet(facetId: string, data: FacetValueUpdate): Promise<boolean> {
    try {
      await facetApi.updateFacetValue(facetId, data)
      // Reload to get fresh data
      await refresh()
      showSuccess(t('results.facets.updated'))
      return true
    } catch (err) {
      logger.error('Failed to update facet:', err)
      showError(getErrorMessage(err) || t('results.facets.errorUpdating'))
      return false
    }
  }

  // ===========================================================================
  // Return
  // ===========================================================================

  return {
    // State
    loading,
    facets,
    includeInactive,
    error,

    // Computed
    facetCount,
    activeCount,
    verifiedCount,
    groupedFacets,

    // Actions
    loadFacets,
    refresh,
    verifyFacet,
    rejectFacet,
    reactivateFacet,
    updateFacet,
  }
}
