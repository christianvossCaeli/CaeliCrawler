/**
 * Entities filtering composable - extracted from EntitiesView.vue.
 *
 * Provides filter state and logic for entity list filtering:
 * - Basic filters (category, parent, has_facets)
 * - Extended filters (location, schema attributes)
 * - Filter application and clearing
 */
import { ref, computed, type Ref, type ComputedRef } from 'vue'

export interface BasicFilters {
  category_id: string | null
  parent_id: string | null
  has_facets: boolean | null
  facet_type_slugs: string[]
}

export interface LocationOptions {
  countries: string[]
  admin_level_1: string[]
  admin_level_2: string[]
}

export interface SchemaAttribute {
  key: string
  title: string
  description?: string
  type: string
}

// Location field keys (these map to Entity columns, not core_attributes)
export const locationFieldKeys = ['country', 'admin_level_1', 'admin_level_2']

export const facetFilterOptions = [
  { label: 'Alle', value: null },
  { label: 'Mit Facets', value: true },
  { label: 'Ohne Facets', value: false },
]

export function useEntitiesFilters() {
  // Basic filters
  const filters = ref<BasicFilters>({
    category_id: null,
    parent_id: null,
    has_facets: null,
    facet_type_slugs: [],
  })

  // Extended filters (Location + Schema Attributes)
  const extendedFilters = ref<Record<string, string | null>>({})
  const tempExtendedFilters = ref<Record<string, string | null>>({})

  // Location options (for dropdowns)
  const locationOptions = ref<LocationOptions>({
    countries: [],
    admin_level_1: [],
    admin_level_2: [],
  })

  // Schema-based attributes
  const schemaAttributes = ref<SchemaAttribute[]>([])
  const attributeValueOptions = ref<Record<string, string[]>>({})

  // Computed properties
  const hasExtendedFilters = computed(() =>
    Object.values(extendedFilters.value).some(v => v !== null && v !== undefined && v !== '')
  )

  const activeExtendedFilterCount = computed(() =>
    Object.values(extendedFilters.value).filter(v => v !== null && v !== undefined && v !== '').length
  )

  const allExtendedFilters = computed(() => {
    const result: Record<string, string> = {}
    for (const [key, value] of Object.entries(extendedFilters.value)) {
      if (value !== null && value !== undefined && value !== '') {
        result[key] = value
      }
    }
    return result
  })

  const hasAnyFilters = computed(
    (searchQuery: Ref<string>) =>
      searchQuery.value ||
      filters.value.category_id !== null ||
      filters.value.parent_id !== null ||
      filters.value.has_facets !== null ||
      filters.value.facet_type_slugs.length > 0 ||
      hasExtendedFilters.value
  )

  // Split schema attributes into location and non-location
  const locationAttributes = computed(() =>
    schemaAttributes.value.filter(attr => locationFieldKeys.includes(attr.key))
  )

  const nonLocationAttributes = computed(() =>
    schemaAttributes.value.filter(attr => !locationFieldKeys.includes(attr.key))
  )

  // Methods
  function hasAttribute(key: string): boolean {
    return schemaAttributes.value.some(attr => attr.key === key)
  }

  function clearBasicFilters() {
    filters.value = {
      category_id: null,
      parent_id: null,
      has_facets: null,
      facet_type_slugs: [],
    }
  }

  function clearExtendedFilters() {
    extendedFilters.value = {}
    tempExtendedFilters.value = {}
  }

  function clearAllFilters() {
    clearBasicFilters()
    clearExtendedFilters()
  }

  function removeExtendedFilter(key: string) {
    extendedFilters.value[key] = null
    delete extendedFilters.value[key]
  }

  function applyExtendedFilters() {
    extendedFilters.value = { ...tempExtendedFilters.value }
  }

  function openExtendedFilterDialog() {
    // Copy current filters to temp
    tempExtendedFilters.value = { ...extendedFilters.value }
  }

  function onCountryChange() {
    // Reset dependent filters
    tempExtendedFilters.value.admin_level_1 = null
    tempExtendedFilters.value.admin_level_2 = null
    locationOptions.value.admin_level_1 = []
    locationOptions.value.admin_level_2 = []
  }

  function onAdminLevel1Change() {
    // Reset dependent filter
    tempExtendedFilters.value.admin_level_2 = null
    locationOptions.value.admin_level_2 = []
  }

  function getExtendedFilterTitle(key: string): string {
    const attr = schemaAttributes.value.find(a => a.key === key)
    if (attr) return attr.title

    // Fallback for location fields
    const locationTitles: Record<string, string> = {
      country: 'Land',
      admin_level_1: 'Region',
      admin_level_2: 'Bezirk',
    }
    return locationTitles[key] || key
  }

  /**
   * Build query params from filters for API calls
   */
  function buildFilterParams(searchQuery: string): Record<string, any> {
    const params: Record<string, any> = {}

    if (searchQuery) params.search = searchQuery
    if (filters.value.category_id) params.category_id = filters.value.category_id
    if (filters.value.parent_id) params.parent_id = filters.value.parent_id
    if (filters.value.has_facets !== null) params.has_facets = filters.value.has_facets
    if (filters.value.facet_type_slugs.length > 0) {
      params.facet_type_slugs = filters.value.facet_type_slugs.join(',')
    }

    // Extended filters (location + schema attributes)
    if (hasExtendedFilters.value) {
      const locationParams: Record<string, string> = {}
      const attrParams: Record<string, string> = {}

      for (const [key, value] of Object.entries(extendedFilters.value)) {
        if (value !== null && value !== undefined && value !== '') {
          if (locationFieldKeys.includes(key)) {
            locationParams[key] = value
          } else {
            attrParams[key] = value
          }
        }
      }

      // Apply location filters directly
      if (locationParams.country) params.country = locationParams.country
      if (locationParams.admin_level_1) params.admin_level_1 = locationParams.admin_level_1
      if (locationParams.admin_level_2) params.admin_level_2 = locationParams.admin_level_2

      // Apply attribute filters as JSON
      if (Object.keys(attrParams).length > 0) {
        params.core_attr_filters = JSON.stringify(attrParams)
      }
    }

    return params
  }

  return {
    // State
    filters,
    extendedFilters,
    tempExtendedFilters,
    locationOptions,
    schemaAttributes,
    attributeValueOptions,

    // Computed
    hasExtendedFilters,
    activeExtendedFilterCount,
    allExtendedFilters,
    locationAttributes,
    nonLocationAttributes,

    // Constants
    facetFilterOptions,
    locationFieldKeys,

    // Methods
    hasAttribute,
    clearBasicFilters,
    clearExtendedFilters,
    clearAllFilters,
    removeExtendedFilter,
    applyExtendedFilters,
    openExtendedFilterDialog,
    onCountryChange,
    onAdminLevel1Change,
    getExtendedFilterTitle,
    buildFilterParams,
  }
}
