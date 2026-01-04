/**
 * Facet Search Composable
 *
 * Handles facet search, filtering, and expansion.
 */

import { ref, computed, watch, type Ref, type ComputedRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSnackbar } from '@/composables/useSnackbar'
import { useDebounce, DEBOUNCE_DELAYS } from '@/composables/useDebounce'
import { facetApi } from '@/services/api'
import { useLogger } from '@/composables/useLogger'
import type { Entity } from '@/stores/entity'
import type { FacetGroup, FacetValue } from './types'

const logger = useLogger('useFacetSearch')

export function useFacetSearch(
  entity: Ref<Entity | null> | ComputedRef<Entity | null> | Entity | null,
) {
  const { t } = useI18n()
  const { showError } = useSnackbar()

  // Helper to get entity value
  const getEntity = (): Entity | null => {
    if (entity === null) return null
    if ('value' in entity) return entity.value
    return entity
  }

  // State
  const facetSearchQuery = ref('')
  const debouncedSearchQuery = ref('')
  const expandedFacets = ref<string[]>([])
  const expandedFacetValues = ref<Record<string, FacetValue[]>>({})
  const loadingMoreFacets = ref<Record<string, boolean>>({})

  // Debounce the search query to avoid excessive filtering on every keystroke
  const { debouncedFn: updateDebouncedQuery } = useDebounce(
    (query: string) => {
      debouncedSearchQuery.value = query
    },
    { delay: DEBOUNCE_DELAYS.FAST }
  )

  // Watch for changes and debounce
  watch(facetSearchQuery, (newQuery) => {
    updateDebouncedQuery(newQuery)
  })

  // Functions
  function matchesFacetSearch(facet: FacetValue, query: string): boolean {
    const textRepr = facet.text_representation || ''
    if (textRepr.toLowerCase().includes(query)) return true

    const val = facet.value
    if (typeof val === 'string' && val.toLowerCase().includes(query)) return true
    if (typeof val === 'object' && val) {
      const v = val as Record<string, unknown>
      if ((v.description as string)?.toLowerCase().includes(query)) return true
      if ((v.text as string)?.toLowerCase().includes(query)) return true
      if ((v.name as string)?.toLowerCase().includes(query)) return true
      if ((v.type as string)?.toLowerCase().includes(query)) return true
      if ((v.quote as string)?.toLowerCase().includes(query)) return true
    }
    return false
  }

  function getDisplayedFacets(facetGroup: FacetGroup): FacetValue[] {
    const slug = facetGroup.facet_type_slug
    const allFacets = expandedFacetValues.value[slug] || facetGroup.sample_values || []

    // Use debounced query for filtering to avoid excessive re-renders
    if (debouncedSearchQuery.value) {
      const query = debouncedSearchQuery.value.toLowerCase()
      return allFacets.filter((f: FacetValue) => matchesFacetSearch(f, query))
    }

    return allFacets
  }

  function canLoadMore(facetGroup: FacetGroup): boolean {
    const slug = facetGroup.facet_type_slug
    const loaded = expandedFacetValues.value[slug]?.length || facetGroup.sample_values?.length || 0
    return loaded < (facetGroup.value_count ?? 0)
  }

  function getRemainingCount(facetGroup: FacetGroup): number {
    const slug = facetGroup.facet_type_slug
    const loaded = expandedFacetValues.value[slug]?.length || facetGroup.sample_values?.length || 0
    return Math.min(10, (facetGroup.value_count ?? 0) - loaded)
  }

  function isExpanded(facetGroup: FacetGroup): boolean {
    const slug = facetGroup.facet_type_slug
    return !!expandedFacetValues.value[slug]
  }

  async function loadMoreFacets(facetGroup: FacetGroup) {
    const e = getEntity()
    if (!e) return

    const slug = facetGroup.facet_type_slug
    loadingMoreFacets.value[slug] = true

    try {
      const currentCount =
        expandedFacetValues.value[slug]?.length || facetGroup.sample_values?.length || 0
      const response = await facetApi.getFacetValues({
        entity_id: e.id,
        facet_type_slug: slug,
        page: 1,
        per_page: currentCount + 10,
      })

      expandedFacetValues.value[slug] = response.data.items || []
    } catch (err) {
      logger.error('Failed to load more facets', err)
      showError(t('entityDetail.messages.loadMoreError'))
    } finally {
      loadingMoreFacets.value[slug] = false
    }
  }

  function collapseFacets(facetGroup: FacetGroup) {
    const slug = facetGroup.facet_type_slug
    delete expandedFacetValues.value[slug]
  }

  function toggleFacetExpand(slug: string) {
    const idx = expandedFacets.value.indexOf(slug)
    if (idx >= 0) {
      expandedFacets.value.splice(idx, 1)
    } else {
      expandedFacets.value.push(slug)
    }
  }

  function resetSearch() {
    facetSearchQuery.value = ''
    debouncedSearchQuery.value = ''
    expandedFacets.value = []
    expandedFacetValues.value = {}
  }

  // Computed: whether search is active
  const isSearchActive = computed(() => debouncedSearchQuery.value.length > 0)

  return {
    // State
    facetSearchQuery,
    debouncedSearchQuery,
    isSearchActive,
    expandedFacets,
    expandedFacetValues,
    loadingMoreFacets,

    // Functions
    matchesFacetSearch,
    getDisplayedFacets,
    canLoadMore,
    getRemainingCount,
    isExpanded,
    loadMoreFacets,
    collapseFacets,
    toggleFacetExpand,
    resetSearch,
  }
}
