/**
 * EntityTypes Admin Composable
 *
 * Manages state and logic for the EntityTypes admin view.
 * Handles CRUD operations and facet assignment management.
 */
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { entityApi, facetApi } from '@/services/api'
import { useSnackbar } from '@/composables/useSnackbar'
import { useLogger } from '@/composables/useLogger'
import { getErrorMessage } from '@/utils/errorMessage'
import { useAuthStore } from '@/stores/auth'

// ============================================================================
// Types
// ============================================================================

export interface EntityType {
  id: string
  slug: string
  name: string
  name_plural?: string
  description?: string
  icon?: string
  color?: string
  is_primary?: boolean
  supports_hierarchy?: boolean
  supports_pysis?: boolean
  is_active?: boolean
  is_system?: boolean
  display_order?: number
  entity_count?: number
}

export interface FacetType {
  id: string
  slug?: string
  name: string
  description?: string
  applicable_entity_type_slugs?: string[]
  icon?: string
  color?: string
  value_type?: string
  is_system?: boolean
}

export interface VFormRef {
  validate: () => boolean | Promise<{ valid: boolean }>
  reset: () => void
  resetValidation: () => void
}

export interface EntityTypeForm {
  name: string
  name_plural: string
  description: string
  icon: string
  color: string
  is_primary: boolean
  supports_hierarchy: boolean
  supports_pysis: boolean
  is_active: boolean
  display_order: number
}

// ============================================================================
// Composable
// ============================================================================

export function useEntityTypesAdmin() {
  const logger = useLogger('EntityTypesAdmin')
  const { t } = useI18n()
  const { showSuccess, showError } = useSnackbar()
  const auth = useAuthStore()

  // ============================================================================
  // State
  // ============================================================================

  const entityTypes = ref<EntityType[]>([])
  const facetTypes = ref<FacetType[]>([])
  const loading = ref(false)
  const dialog = ref(false)
  const deleteDialog = ref(false)
  const editingItem = ref<EntityType | null>(null)
  const itemToDelete = ref<EntityType | null>(null)
  const saving = ref(false)
  const deleting = ref(false)
  const formRef = ref<VFormRef | null>(null)

  // Dialog state
  const activeTab = ref('basic')
  const selectedFacetIds = ref<string[]>([])
  const facetSearch = ref('')
  const originalFacetIds = ref<string[]>([])
  const originalGlobalFacetIds = ref<string[]>([])

  // Form state
  const form = ref<EntityTypeForm>(getDefaultForm())

  // ============================================================================
  // Computed
  // ============================================================================

  const canEdit = computed(() => auth.isEditor)
  const canDelete = computed(() => auth.isAdmin)

  const headers = computed(() => [
    { title: '', key: 'icon', width: '50px', sortable: false },
    { title: t('admin.entityTypes.columns.name'), key: 'name', sortable: true },
    { title: t('admin.entityTypes.columns.slug'), key: 'slug', sortable: true },
    { title: t('admin.entityTypes.facets'), key: 'facets', sortable: false },
    { title: t('admin.entityTypes.columns.color'), key: 'color', width: '120px', sortable: true },
    { title: t('admin.entityTypes.columns.entities'), key: 'entity_count', width: '100px', align: 'center' as const, sortable: true },
    { title: t('admin.entityTypes.columns.system'), key: 'is_system', width: '80px', align: 'center' as const, sortable: true },
    { title: t('admin.entityTypes.columns.active'), key: 'is_active', width: '80px', align: 'center' as const, sortable: true },
    { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' as const },
  ])

  // Filtered facets for search
  const filteredFacets = computed(() => {
    if (!facetSearch.value) return facetTypes.value
    const search = facetSearch.value.toLowerCase()
    return facetTypes.value.filter(f =>
      f.name.toLowerCase().includes(search) ||
      f.slug?.toLowerCase().includes(search) ||
      f.description?.toLowerCase().includes(search)
    )
  })

  // ============================================================================
  // Static Options
  // ============================================================================

  const suggestedIcons = [
    'mdi-office-building',
    'mdi-domain',
    'mdi-account-group',
    'mdi-account',
    'mdi-map-marker',
    'mdi-city',
    'mdi-home',
    'mdi-factory',
    'mdi-school',
    'mdi-hospital-building',
    'mdi-store',
    'mdi-bank',
    'mdi-church',
    'mdi-stadium',
    'mdi-folder',
    'mdi-file-document',
    'mdi-calendar-clock',
    'mdi-tag',
    'mdi-shape',
    'mdi-cube',
  ]

  const tabOrder = ['basic', 'appearance', 'facets', 'settings']

  // ============================================================================
  // Helper Functions
  // ============================================================================

  function getDefaultForm(): EntityTypeForm {
    return {
      name: '',
      name_plural: '',
      description: '',
      icon: 'mdi-folder',
      color: 'success',
      is_primary: true,
      supports_hierarchy: false,
      supports_pysis: false,
      is_active: true,
      display_order: 10,
    }
  }

  function getNextTab(): string {
    const currentIndex = tabOrder.indexOf(activeTab.value)
    return tabOrder[Math.min(currentIndex + 1, tabOrder.length - 1)]
  }

  function getPrevTab(): string {
    const currentIndex = tabOrder.indexOf(activeTab.value)
    return tabOrder[Math.max(currentIndex - 1, 0)]
  }

  function getFacetsForEntityType(entityTypeSlug: string): FacetType[] {
    return facetTypes.value.filter(ft =>
      ft.applicable_entity_type_slugs?.length === 0 ||
      ft.applicable_entity_type_slugs?.includes(entityTypeSlug)
    )
  }

  function toggleFacet(facetId: string) {
    const index = selectedFacetIds.value.indexOf(facetId)
    if (index === -1) {
      selectedFacetIds.value.push(facetId)
    } else {
      selectedFacetIds.value.splice(index, 1)
    }
  }

  function selectAllFacets() {
    selectedFacetIds.value = facetTypes.value.map(f => f.id)
  }

  // ============================================================================
  // Data Loading
  // ============================================================================

  async function loadEntityTypes() {
    loading.value = true
    try {
      const response = await entityApi.getEntityTypes({ per_page: 100 })
      entityTypes.value = response.data.items || []
    } catch (e) {
      logger.error('Failed to load entity types', e)
      showError(t('admin.entityTypes.messages.loadError'))
    } finally {
      loading.value = false
    }
  }

  async function loadFacetTypes() {
    try {
      const response = await facetApi.getFacetTypes({ per_page: 100, is_active: true })
      facetTypes.value = response.data.items || []
    } catch (e) {
      logger.error('Failed to load facet types', e)
    }
  }

  // ============================================================================
  // Dialog Actions
  // ============================================================================

  function openCreateDialog() {
    if (!canEdit.value) return
    editingItem.value = null
    activeTab.value = 'basic'
    facetSearch.value = ''
    selectedFacetIds.value = []
    originalFacetIds.value = []
    originalGlobalFacetIds.value = []
    form.value = getDefaultForm()
    dialog.value = true
  }

  function openEditDialog(item: EntityType) {
    if (!canEdit.value) return
    editingItem.value = item
    activeTab.value = 'basic'
    facetSearch.value = ''

    // Get facets that have empty array (applies to all entity types)
    const globalFacetIds = facetTypes.value
      .filter(ft => !ft.applicable_entity_type_slugs?.length)
      .map(ft => ft.id)

    // Get facets that are explicitly assigned to this entity type
    const explicitlyAssignedFacetIds = facetTypes.value
      .filter(ft => {
        if (!ft.applicable_entity_type_slugs?.length) return false
        return ft.applicable_entity_type_slugs.includes(item.slug)
      })
      .map(ft => ft.id)

    // Both global and explicitly assigned facets should appear as selected
    const allAssignedFacetIds = [...new Set([...globalFacetIds, ...explicitlyAssignedFacetIds])]

    selectedFacetIds.value = [...allAssignedFacetIds]
    originalFacetIds.value = [...allAssignedFacetIds]
    originalGlobalFacetIds.value = [...globalFacetIds]

    form.value = {
      name: item.name,
      name_plural: item.name_plural || '',
      description: item.description || '',
      icon: item.icon || 'mdi-folder',
      color: item.color || 'success',
      is_primary: item.is_primary ?? true,
      supports_hierarchy: item.supports_hierarchy ?? false,
      supports_pysis: item.supports_pysis ?? false,
      is_active: item.is_active ?? true,
      display_order: item.display_order ?? 10,
    }
    dialog.value = true
  }

  function closeDialog() {
    dialog.value = false
    editingItem.value = null
    activeTab.value = 'basic'
  }

  function confirmDelete(item: EntityType) {
    if (!canDelete.value) return
    itemToDelete.value = item
    deleteDialog.value = true
  }

  // ============================================================================
  // CRUD Operations
  // ============================================================================

  async function save() {
    if (!formRef.value?.validate()) return

    saving.value = true
    try {
      const data = {
        ...form.value,
        name_plural: form.value.name_plural || `${form.value.name}s`,
      }

      let entityTypeSlug: string

      if (editingItem.value) {
        await entityApi.updateEntityType(editingItem.value.id, data)
        entityTypeSlug = editingItem.value.slug
        showSuccess(t('admin.entityTypes.messages.updated'))
      } else {
        const response = await entityApi.createEntityType(data)
        entityTypeSlug = response.data.slug
        showSuccess(t('admin.entityTypes.messages.created'))
      }

      await updateFacetAssignments(entityTypeSlug)

      closeDialog()
      await Promise.all([loadEntityTypes(), loadFacetTypes()])
    } catch (e) {
      const detail = getErrorMessage(e) || t('admin.entityTypes.messages.saveError')
      showError(detail)
    } finally {
      saving.value = false
    }
  }

  async function updateFacetAssignments(entityTypeSlug: string) {
    const addedFacetIds = selectedFacetIds.value.filter(id =>
      !originalFacetIds.value.includes(id)
    )
    const removedFacetIds = originalFacetIds.value.filter(id =>
      !selectedFacetIds.value.includes(id)
    )

    // Add entity type to newly selected facets
    for (const facetId of addedFacetIds) {
      const facet = facetTypes.value.find(f => f.id === facetId)
      if (facet) {
        const newSlugs = [...(facet.applicable_entity_type_slugs || []), entityTypeSlug]
        await facetApi.updateFacetType(facetId, {
          ...facet,
          applicable_entity_type_slugs: newSlugs,
        })
      }
    }

    // Remove entity type from deselected facets
    for (const facetId of removedFacetIds) {
      const facet = facetTypes.value.find(f => f.id === facetId)
      if (!facet) continue

      const wasGlobal = originalGlobalFacetIds.value.includes(facetId)

      if (wasGlobal) {
        const allOtherSlugs = entityTypes.value
          .map(et => et.slug)
          .filter(slug => slug !== entityTypeSlug)

        await facetApi.updateFacetType(facetId, {
          ...facet,
          applicable_entity_type_slugs: allOtherSlugs,
        })
      } else if (facet.applicable_entity_type_slugs?.length) {
        const newSlugs = facet.applicable_entity_type_slugs.filter((s: string) => s !== entityTypeSlug)
        await facetApi.updateFacetType(facetId, {
          ...facet,
          applicable_entity_type_slugs: newSlugs,
        })
      }
    }
  }

  async function deleteItem() {
    if (!canDelete.value) return
    if (!itemToDelete.value) return

    deleting.value = true
    try {
      await entityApi.deleteEntityType(itemToDelete.value.id)
      showSuccess(t('admin.entityTypes.messages.deleted', { name: itemToDelete.value.name }))
      deleteDialog.value = false
      itemToDelete.value = null
      await loadEntityTypes()
    } catch (e) {
      const detail = getErrorMessage(e) || t('admin.entityTypes.messages.deleteError')
      showError(detail)
    } finally {
      deleting.value = false
    }
  }

  // ============================================================================
  // Initialization
  // ============================================================================

  async function initialize() {
    await Promise.all([loadEntityTypes(), loadFacetTypes()])
  }

  // ============================================================================
  // Return
  // ============================================================================

  return {
    // State
    entityTypes,
    facetTypes,
    loading,
    dialog,
    deleteDialog,
    editingItem,
    itemToDelete,
    saving,
    deleting,
    formRef,
    activeTab,
    selectedFacetIds,
    facetSearch,
    form,

    // Computed
    canEdit,
    canDelete,
    headers,
    filteredFacets,

    // Static Options
    suggestedIcons,

    // Helper Functions
    getNextTab,
    getPrevTab,
    getFacetsForEntityType,
    toggleFacet,
    selectAllFacets,

    // Dialog Actions
    openCreateDialog,
    openEditDialog,
    closeDialog,
    confirmDelete,

    // CRUD Operations
    save,
    deleteItem,

    // Initialization
    initialize,
  }
}
