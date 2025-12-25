import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useEntityStore } from '@/stores/entity'
import { adminApi, userApi, entityApi } from '@/services/api'
import { useSnackbar } from '@/composables/useSnackbar'
import { useFeatureFlags } from '@/composables/useFeatureFlags'
import { useDebounce, DEBOUNCE_DELAYS } from '@/composables/useDebounce'
import { useLogger } from '@/composables/useLogger'

export interface EntityFilters {
  category_id: string | null
  parent_id: string | null
  has_facets: boolean | null
  facet_type_slugs: string[]
}

export interface EntityForm {
  name: string
  external_id: string
  parent_id: string | null
  core_attributes: Record<string, any>
  latitude: number | null
  longitude: number | null
  owner_id: string | null
}

export interface EntityStats {
  total_facet_values: number
  verified_count: number
  relation_count: number
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

/**
 * Composable for shared state and logic in EntitiesView
 */
export function useEntitiesView() {
  const logger = useLogger('useEntitiesView')
  const { t } = useI18n()
  const { flags } = useFeatureFlags()
  const { showSuccess, showError } = useSnackbar()
  const route = useRoute()
  const store = useEntityStore()

  // Route params
  const typeSlug = computed(() => route.params.typeSlug as string | undefined)
  const selectedTypeTab = ref<string>('')

  // State
  const loading = ref(false)
  const searchQuery = ref('')
  const currentPage = ref(1)
  const itemsPerPage = ref(25)
  const viewMode = ref<'table' | 'cards' | 'map'>('table')
  const hasGeoData = ref(false)

  // Data
  const categories = ref<any[]>([])
  const parentOptions = ref<any[]>([])
  const loadingParents = ref(false)
  const userOptions = ref<any[]>([])
  const loadingUsers = ref(false)

  // Dialogs
  const createDialog = ref(false)
  const templateDialog = ref(false)
  const deleteDialog = ref(false)
  const extendedFilterDialog = ref(false)
  const entityTab = ref('general')
  const editingEntity = ref<any>(null)
  const entityToDelete = ref<any>(null)
  const saving = ref(false)
  const deleting = ref(false)

  // Form
  const entityForm = ref<EntityForm>({
    name: '',
    external_id: '',
    parent_id: null,
    core_attributes: {},
    latitude: null,
    longitude: null,
    owner_id: null,
  })

  // Filters
  const filters = ref<EntityFilters>({
    category_id: null,
    parent_id: null,
    has_facets: null,
    facet_type_slugs: [],
  })

  // Active filter from dashboard widget
  const isActiveFilter = ref<boolean | null>(null)

  // Initialize from route query params
  if (route.query.is_active !== undefined) {
    isActiveFilter.value = route.query.is_active === 'true'
  }

  // Handle type query param from ChartDistribution widget (fallback when no slug)
  if (route.query.type) {
    const typeName = route.query.type as string
    // Find entity type by name and set the tab
    const matchingType = store.entityTypes.find(
      et => et.name.toLowerCase() === typeName.toLowerCase() ||
            et.slug.toLowerCase() === typeName.toLowerCase()
    )
    if (matchingType) {
      selectedTypeTab.value = matchingType.slug
    }
  }

  // Extended Filters
  const extendedFilters = ref<Record<string, string | null>>({})
  const tempExtendedFilters = ref<Record<string, string | null>>({})
  const locationOptions = ref<LocationOptions>({
    countries: [],
    admin_level_1: [],
    admin_level_2: [],
  })

  // Schema-based attributes
  const schemaAttributes = ref<SchemaAttribute[]>([])
  const attributeValueOptions = ref<Record<string, string[]>>({})
  const locationFieldKeys = ['country', 'admin_level_1', 'admin_level_2']

  // Stats
  const stats = ref<EntityStats>({
    total_facet_values: 0,
    verified_count: 0,
    relation_count: 0,
  })

  // Computed
  const currentEntityType = computed(() => {
    const slug = typeSlug.value || selectedTypeTab.value
    return store.entityTypes.find(et => et.slug === slug) || store.activeEntityTypes[0]
  })

  const totalEntities = computed(() => store.entitiesTotal)
  const totalPages = computed(() => Math.ceil(totalEntities.value / itemsPerPage.value))

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

  const hasAnyFilters = computed(() =>
    Boolean(
      searchQuery.value ||
      filters.value.category_id !== null ||
      filters.value.parent_id !== null ||
      filters.value.has_facets !== null ||
      isActiveFilter.value !== null ||
      filters.value.facet_type_slugs.length > 0 ||
      hasExtendedFilters.value
    )
  )

  const locationAttributes = computed(() =>
    schemaAttributes.value.filter(attr => locationFieldKeys.includes(attr.key))
  )

  const nonLocationAttributes = computed(() =>
    schemaAttributes.value.filter(attr => !locationFieldKeys.includes(attr.key))
  )

  const facetFilterOptions = computed(() => [
    { label: t('entities.allFacets'), value: null },
    { label: t('entities.withFacets'), value: true },
    { label: t('entities.withoutFacets'), value: false },
  ])

  // Methods - Data Loading
  async function loadEntities(page = currentPage.value) {
    if (!currentEntityType.value) return

    loading.value = true
    try {
      const params: any = {
        entity_type_slug: currentEntityType.value.slug,
        page,
        per_page: itemsPerPage.value,
      }

      if (searchQuery.value) params.search = searchQuery.value
      if (filters.value.category_id) params.category_id = filters.value.category_id
      if (filters.value.parent_id) params.parent_id = filters.value.parent_id
      if (filters.value.has_facets !== null) params.has_facets = filters.value.has_facets
      if (isActiveFilter.value !== null) params.is_active = isActiveFilter.value
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

        if (locationParams.country) params.country = locationParams.country
        if (locationParams.admin_level_1) params.admin_level_1 = locationParams.admin_level_1
        if (locationParams.admin_level_2) params.admin_level_2 = locationParams.admin_level_2

        if (Object.keys(attrParams).length > 0) {
          params.core_attr_filters = JSON.stringify(attrParams)
        }
      }

      await store.fetchEntities(params)
      currentPage.value = page
      await loadStats()
    } catch (e) {
      logger.error('Failed to load entities', e)
      showError(t('entities.loadError'))
    } finally {
      loading.value = false
    }
  }

  async function loadStats() {
    try {
      const result = await store.fetchAnalysisStats({
        entity_type_slug: currentEntityType.value?.slug,
      })
      const overview = result.overview || result
      stats.value = {
        total_facet_values: overview.total_facet_values || 0,
        verified_count: overview.verified_facet_values || 0,
        relation_count: overview.total_connections || overview.total_relations || 0,
      }
    } catch (e) {
      logger.error('Failed to load stats', e)
    }
  }

  async function loadCategories() {
    try {
      const response = await adminApi.getCategories({ per_page: 100 })
      categories.value = response.data.items || []
    } catch (e) {
      logger.error('Failed to load categories', e)
    }
  }

  async function loadUsers() {
    loadingUsers.value = true
    try {
      const response = await userApi.getUsers({ per_page: 100, is_active: true })
      userOptions.value = (response.data.items || []).map((u: any) => ({
        id: u.id,
        full_name: u.full_name,
        email: u.email,
        display: `${u.full_name} (${u.email})`,
      }))
    } catch (e) {
      logger.error('Failed to load users', e)
    } finally {
      loadingUsers.value = false
    }
  }

  async function loadParentOptions() {
    if (!currentEntityType.value?.supports_hierarchy) {
      parentOptions.value = []
      return
    }

    try {
      await searchParents('')
    } catch (e) {
      logger.error('Failed to load parent options', e)
    }
  }

  let parentSearchTimeout: ReturnType<typeof setTimeout> | null = null
  async function searchParents(query: string) {
    if (!currentEntityType.value?.supports_hierarchy) return

    if (parentSearchTimeout) clearTimeout(parentSearchTimeout)

    parentSearchTimeout = setTimeout(async () => {
      loadingParents.value = true
      try {
        const response = await store.fetchEntities({
          entity_type_slug: currentEntityType.value!.slug,
          search: query || undefined,
          per_page: 50,
        })
        parentOptions.value = response.items || []
      } catch (e) {
        logger.error('Failed to search parents', e)
      } finally {
        loadingParents.value = false
      }
    }, 300)
  }

  async function checkGeoDataAvailable() {
    if (!currentEntityType.value?.slug) {
      hasGeoData.value = false
      return
    }
    try {
      const response = await entityApi.getEntitiesGeoJSON({
        entity_type_slug: currentEntityType.value.slug,
        limit: 1,
      })
      hasGeoData.value = response.data.total_with_coords > 0
    } catch {
      hasGeoData.value = false
    }
  }

  async function loadSchemaAttributes() {
    if (!currentEntityType.value?.slug) {
      schemaAttributes.value = []
      return
    }

    try {
      const response = await entityApi.getAttributeFilterOptions({
        entity_type_slug: currentEntityType.value.slug,
      })
      schemaAttributes.value = response.data.attributes || []
    } catch (e) {
      logger.error('Failed to load schema attributes', e)
      schemaAttributes.value = []
    }
  }

  async function loadAttributeValues(attributeKey: string) {
    if (!currentEntityType.value?.slug) return
    if (attributeValueOptions.value[attributeKey]?.length > 0) return

    try {
      const response = await entityApi.getAttributeFilterOptions({
        entity_type_slug: currentEntityType.value.slug,
        attribute_key: attributeKey,
      })
      if (response.data.attribute_values?.[attributeKey]) {
        attributeValueOptions.value[attributeKey] = response.data.attribute_values[attributeKey]
      }
    } catch (e) {
      logger.error(`Failed to load values for attribute ${attributeKey}`, e)
    }
  }

  async function loadLocationOptions() {
    try {
      const params: any = {}
      if (tempExtendedFilters.value.country) {
        params.country = tempExtendedFilters.value.country
      }
      if (tempExtendedFilters.value.admin_level_1) {
        params.admin_level_1 = tempExtendedFilters.value.admin_level_1
      }

      const response = await entityApi.getLocationFilterOptions(params)
      const data = response.data

      locationOptions.value.countries = data.countries || []
      locationOptions.value.admin_level_1 = data.admin_level_1 || []
      locationOptions.value.admin_level_2 = data.admin_level_2 || []
    } catch (e) {
      logger.error('Failed to load location options', e)
    }
  }

  // Methods - Entity Actions
  async function saveEntity(formRef: any) {
    if (!formRef?.validate()) return
    if (!currentEntityType.value) return

    saving.value = true
    try {
      const data = {
        entity_type_id: currentEntityType.value.id,
        name: entityForm.value.name,
        external_id: entityForm.value.external_id || null,
        parent_id: entityForm.value.parent_id,
        core_attributes: entityForm.value.core_attributes,
        latitude: entityForm.value.latitude,
        longitude: entityForm.value.longitude,
        owner_id: entityForm.value.owner_id,
      }

      if (editingEntity.value) {
        await store.updateEntity(editingEntity.value.id, data)
        showSuccess(t('entities.entityUpdated'))
      } else {
        await store.createEntity(data)
        showSuccess(t('entities.entityCreated'))
      }

      closeDialog()
      await loadEntities()
    } catch (e: any) {
      showError(e.response?.data?.detail || t('entities.saveError'))
    } finally {
      saving.value = false
    }
  }

  async function deleteEntity() {
    if (!entityToDelete.value) return

    deleting.value = true
    try {
      await store.deleteEntity(entityToDelete.value.id)
      showSuccess(t('entities.entityDeleted', { name: entityToDelete.value.name }))
      deleteDialog.value = false
      entityToDelete.value = null
      await loadEntities()
    } catch (e: any) {
      const detail = e.response?.data?.detail || t('entities.deleteError')
      showError(detail)
    } finally {
      deleting.value = false
    }
  }

  // Methods - Dialog Management
  function openEditDialog(entity: any) {
    editingEntity.value = entity
    entityForm.value = {
      name: entity.name,
      external_id: entity.external_id || '',
      parent_id: entity.parent_id,
      core_attributes: { ...entity.core_attributes },
      latitude: entity.latitude,
      longitude: entity.longitude,
      owner_id: entity.owner_id || null,
    }
    createDialog.value = true
  }

  function closeDialog() {
    createDialog.value = false
    editingEntity.value = null
    entityForm.value = {
      name: '',
      external_id: '',
      parent_id: null,
      core_attributes: {},
      latitude: null,
      longitude: null,
      owner_id: null,
    }
  }

  function confirmDelete(entity: any) {
    entityToDelete.value = entity
    deleteDialog.value = true
  }

  function selectTemplate(template: any) {
    store.selectedTemplate = template
    templateDialog.value = false
    loadEntities()
  }

  // Methods - Filter Management
  function clearAllFilters() {
    searchQuery.value = ''
    filters.value.category_id = null
    filters.value.parent_id = null
    filters.value.has_facets = null
    filters.value.facet_type_slugs = []
    isActiveFilter.value = null
    clearExtendedFilters()
    loadEntities(1)
  }

  function clearExtendedFilters() {
    extendedFilters.value = {}
    tempExtendedFilters.value = {}
  }

  function removeExtendedFilter(key: string) {
    const newFilters = { ...extendedFilters.value }
    delete newFilters[key]
    extendedFilters.value = newFilters
    loadEntities()
  }

  function getExtendedFilterTitle(key: string): string {
    const attr = schemaAttributes.value.find(a => a.key === key)
    return attr?.title || key
  }

  function hasAttribute(key: string): boolean {
    return schemaAttributes.value.some(attr => attr.key === key)
  }

  async function onCountryChange() {
    tempExtendedFilters.value.admin_level_1 = null
    tempExtendedFilters.value.admin_level_2 = null
    await loadLocationOptions()
  }

  async function onAdminLevel1Change() {
    tempExtendedFilters.value.admin_level_2 = null
    await loadLocationOptions()
  }

  // Debounced search
  const { debouncedFn: debouncedLoadEntities } = useDebounce(
    () => loadEntities(),
    { delay: DEBOUNCE_DELAYS.SEARCH }
  )

  // Utility
  function isLightColor(color: string | undefined): boolean {
    if (!color) return false
    const hex = color.replace('#', '')
    if (hex.length !== 6) return false
    const r = parseInt(hex.substr(0, 2), 16)
    const g = parseInt(hex.substr(2, 2), 16)
    const b = parseInt(hex.substr(4, 2), 16)
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return luminance > 0.6
  }

  function getTopFacetCounts(_entity: any): Array<{ slug: string; name: string; icon: string; color: string; count: number }> {
    return []
  }

  // Watchers
  watch(selectedTypeTab, () => {
    if (selectedTypeTab.value) {
      clearExtendedFilters()
      attributeValueOptions.value = {}
      viewMode.value = 'table'
      loadEntities(1)
      loadParentOptions()
      loadSchemaAttributes()
      checkGeoDataAvailable()
    }
  })

  return {
    // Route & Store
    typeSlug,
    selectedTypeTab,
    store,
    flags,

    // State
    loading,
    searchQuery,
    currentPage,
    itemsPerPage,
    viewMode,
    hasGeoData,

    // Data
    categories,
    parentOptions,
    loadingParents,
    userOptions,
    loadingUsers,

    // Dialogs
    createDialog,
    templateDialog,
    deleteDialog,
    extendedFilterDialog,
    entityTab,
    editingEntity,
    entityToDelete,
    saving,
    deleting,

    // Form
    entityForm,

    // Filters
    filters,
    isActiveFilter,
    extendedFilters,
    tempExtendedFilters,
    locationOptions,
    schemaAttributes,
    attributeValueOptions,
    locationFieldKeys,

    // Stats
    stats,

    // Computed
    currentEntityType,
    totalEntities,
    totalPages,
    hasExtendedFilters,
    activeExtendedFilterCount,
    allExtendedFilters,
    hasAnyFilters,
    locationAttributes,
    nonLocationAttributes,
    facetFilterOptions,

    // Methods
    loadEntities,
    loadStats,
    loadCategories,
    loadUsers,
    loadParentOptions,
    searchParents,
    checkGeoDataAvailable,
    loadSchemaAttributes,
    loadAttributeValues,
    loadLocationOptions,
    saveEntity,
    deleteEntity,
    openEditDialog,
    closeDialog,
    confirmDelete,
    selectTemplate,
    clearAllFilters,
    clearExtendedFilters,
    removeExtendedFilter,
    getExtendedFilterTitle,
    hasAttribute,
    onCountryChange,
    onAdminLevel1Change,
    debouncedLoadEntities,
    isLightColor,
    getTopFacetCounts,
  }
}
