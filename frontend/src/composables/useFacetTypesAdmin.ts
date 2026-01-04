/**
 * FacetTypes Admin Composable
 *
 * Manages state and logic for the FacetTypes admin view.
 * Handles CRUD operations, filtering, and AI schema generation.
 */
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { facetApi, entityApi } from '@/services/api'
import { useSnackbar } from '@/composables/useSnackbar'
import { useDebounce, DEBOUNCE_DELAYS } from '@/composables/useDebounce'
import { useLogger } from '@/composables/useLogger'
import { getErrorMessage } from '@/utils/errorMessage'
import { useAuthStore } from '@/stores/auth'

// ============================================================================
// Types
// ============================================================================

export interface FacetType {
  id: string
  slug?: string
  name: string
  name_plural?: string
  description?: string
  icon?: string
  color?: string
  value_type?: string
  value_schema?: Record<string, unknown> | null
  applicable_entity_type_slugs?: string[]
  aggregation_method?: string
  deduplication_fields?: string[]
  is_time_based?: boolean
  time_field_path?: string
  default_time_filter?: string
  ai_extraction_enabled?: boolean
  ai_extraction_prompt?: string
  is_active?: boolean
  is_system?: boolean
  needs_review?: boolean
  display_order?: number
  value_count?: number
  allows_entity_reference?: boolean
  target_entity_type_slugs?: string[]
  auto_create_entity?: boolean
}

export interface EntityType {
  id: string
  slug: string
  name: string
}

export interface VFormRef {
  validate: () => boolean | Promise<{ valid: boolean }>
  reset: () => void
  resetValidation: () => void
}

export interface FacetTypeForm {
  name: string
  name_plural: string
  description: string
  icon: string
  color: string
  value_type: string
  value_schema: Record<string, unknown> | null
  applicable_entity_type_slugs: string[]
  aggregation_method: string
  deduplication_fields: string[]
  is_time_based: boolean
  time_field_path: string
  default_time_filter: string
  ai_extraction_enabled: boolean
  ai_extraction_prompt: string
  is_active: boolean
  display_order: number
  allows_entity_reference: boolean
  target_entity_type_slugs: string[]
  auto_create_entity: boolean
}

// ============================================================================
// Composable
// ============================================================================

export function useFacetTypesAdmin() {
  const logger = useLogger('FacetTypesAdmin')
  const { t } = useI18n()
  const { showSuccess, showError } = useSnackbar()
  const auth = useAuthStore()

  // ============================================================================
  // State
  // ============================================================================

  const facetTypes = ref<FacetType[]>([])
  const entityTypes = ref<EntityType[]>([])
  const loading = ref(false)
  const dialog = ref(false)
  const deleteDialog = ref(false)
  const editingItem = ref<FacetType | null>(null)
  const itemToDelete = ref<FacetType | null>(null)
  const saving = ref(false)
  const deleting = ref(false)
  const formRef = ref<VFormRef | null>(null)
  const activeTab = ref('basic')
  const schemaJson = ref('')
  const schemaError = ref('')
  const generatingSchema = ref(false)

  // Filters
  const filters = ref({
    search: '',
    entityTypeSlug: null as string | null,
    isActive: null as boolean | null,
    needsReview: null as boolean | null,
  })

  // Review state
  const reviewDialog = ref(false)
  const reviewingItem = ref<FacetType | null>(null)
  const reviewing = ref(false)
  const needsReviewCount = ref(0)

  // Form state
  const form = ref<FacetTypeForm>(getDefaultForm())

  // ============================================================================
  // Computed
  // ============================================================================

  const canEdit = computed(() => auth.isEditor)

  const headers = computed(() => [
    { title: '', key: 'icon', width: '50px', sortable: false },
    { title: t('admin.facetTypes.columns.name'), key: 'name', sortable: true },
    { title: t('admin.facetTypes.columns.entityTypes'), key: 'applicable_entity_types', sortable: false },
    { title: t('admin.facetTypes.columns.valueType'), key: 'value_type', width: '120px', sortable: true },
    { title: t('admin.facetTypes.columns.values'), key: 'value_count', width: '100px', align: 'center' as const, sortable: true },
    { title: t('admin.facetTypes.columns.ai'), key: 'ai_extraction_enabled', width: '60px', align: 'center' as const, sortable: true },
    { title: t('admin.facetTypes.columns.review', 'Review'), key: 'needs_review', width: '80px', align: 'center' as const, sortable: true },
    { title: t('admin.facetTypes.columns.system'), key: 'is_system', width: '80px', align: 'center' as const, sortable: true },
    { title: t('admin.facetTypes.columns.active'), key: 'is_active', width: '80px', align: 'center' as const, sortable: true },
    { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' as const },
  ])

  const activeOptions = computed(() => [
    { title: t('common.active'), value: true },
    { title: t('common.inactive'), value: false },
  ])

  const entityTypeOptions = computed(() =>
    entityTypes.value.map(et => ({
      title: et.name,
      value: et.slug,
    }))
  )

  // ============================================================================
  // Static Options
  // ============================================================================

  const valueTypeOptions = [
    { title: 'Text', value: 'text' },
    { title: 'Structured', value: 'structured' },
    { title: 'List', value: 'list' },
    { title: 'Reference', value: 'reference' },
  ]

  const aggregationOptions = [
    { title: 'Count', value: 'count' },
    { title: 'Sum', value: 'sum' },
    { title: 'Average', value: 'avg' },
    { title: 'List', value: 'list' },
    { title: 'Deduplicate', value: 'dedupe' },
  ]

  const suggestedFacetIcons = [
    'mdi-tag',
    'mdi-label',
    'mdi-account',
    'mdi-calendar',
    'mdi-clock',
    'mdi-map-marker',
    'mdi-phone',
    'mdi-email',
    'mdi-link',
    'mdi-file-document',
    'mdi-currency-eur',
    'mdi-chart-line',
    'mdi-alert',
    'mdi-lightbulb',
    'mdi-check-circle',
    'mdi-information',
    'mdi-star',
    'mdi-heart',
    'mdi-flag',
    'mdi-bookmark',
  ]

  // ============================================================================
  // Helper Functions
  // ============================================================================

  function getDefaultForm(): FacetTypeForm {
    return {
      name: '',
      name_plural: '',
      description: '',
      icon: 'mdi-tag',
      color: '#9E9E9E',
      value_type: 'structured',
      value_schema: null,
      applicable_entity_type_slugs: [],
      aggregation_method: 'dedupe',
      deduplication_fields: [],
      is_time_based: false,
      time_field_path: '',
      default_time_filter: 'all',
      ai_extraction_enabled: true,
      ai_extraction_prompt: '',
      is_active: true,
      display_order: 0,
      allows_entity_reference: false,
      target_entity_type_slugs: [],
      auto_create_entity: false,
    }
  }

  function getEntityTypeName(slug: string): string {
    const et = entityTypes.value.find(e => e.slug === slug)
    return et?.name || slug
  }

  // ============================================================================
  // Data Loading
  // ============================================================================

  async function loadFacetTypes() {
    loading.value = true
    try {
      const params: Record<string, unknown> = { per_page: 100 }
      if (filters.value.search) params.search = filters.value.search
      if (filters.value.isActive !== null) params.is_active = filters.value.isActive

      const response = await facetApi.getFacetTypes(params)
      let items = response.data.items || []

      // Filter by entity type if selected
      const entityTypeSlugFilter = filters.value.entityTypeSlug
      if (entityTypeSlugFilter) {
        items = items.filter((ft: FacetType) =>
          !ft.applicable_entity_type_slugs?.length ||
          ft.applicable_entity_type_slugs.includes(entityTypeSlugFilter)
        )
      }

      facetTypes.value = items
    } catch (e) {
      logger.error('Failed to load facet types', e)
      showError(t('admin.facetTypes.messages.loadError'))
    } finally {
      loading.value = false
    }
  }

  async function loadEntityTypes() {
    try {
      const response = await entityApi.getEntityTypes({ per_page: 100, is_active: true })
      entityTypes.value = response.data.items || []
    } catch (e) {
      logger.error('Failed to load entity types', e)
    }
  }

  // Debounced search
  const { debouncedFn: debouncedSearch } = useDebounce(
    () => loadFacetTypes(),
    { delay: DEBOUNCE_DELAYS.SEARCH }
  )

  // ============================================================================
  // Dialog Actions
  // ============================================================================

  function openCreateDialog() {
    if (!canEdit.value) return
    editingItem.value = null
    activeTab.value = 'basic'
    schemaJson.value = ''
    schemaError.value = ''
    form.value = getDefaultForm()
    dialog.value = true
  }

  function openEditDialog(item: FacetType) {
    if (!canEdit.value) return
    editingItem.value = item
    activeTab.value = 'basic'
    schemaError.value = ''

    // Convert Vuetify color names to HEX for the color picker
    const colorValue = item.color || '#9E9E9E'
    const resolvedColor = colorValue.startsWith('#') ? colorValue : '#9E9E9E'

    form.value = {
      name: item.name,
      name_plural: item.name_plural || '',
      description: item.description || '',
      icon: item.icon || 'mdi-tag',
      color: resolvedColor,
      value_type: item.value_type || 'structured',
      value_schema: item.value_schema ?? null,
      applicable_entity_type_slugs: item.applicable_entity_type_slugs || [],
      aggregation_method: item.aggregation_method || 'dedupe',
      deduplication_fields: item.deduplication_fields || [],
      is_time_based: item.is_time_based ?? false,
      time_field_path: item.time_field_path || '',
      default_time_filter: item.default_time_filter || 'all',
      ai_extraction_enabled: item.ai_extraction_enabled ?? true,
      ai_extraction_prompt: item.ai_extraction_prompt || '',
      is_active: item.is_active ?? true,
      display_order: item.display_order ?? 0,
      allows_entity_reference: item.allows_entity_reference ?? false,
      target_entity_type_slugs: item.target_entity_type_slugs || [],
      auto_create_entity: item.auto_create_entity ?? false,
    }
    schemaJson.value = item.value_schema ? JSON.stringify(item.value_schema, null, 2) : ''
    dialog.value = true
  }

  function closeDialog() {
    dialog.value = false
    editingItem.value = null
  }

  function confirmDelete(item: FacetType) {
    if (!canEdit.value) return
    itemToDelete.value = item
    deleteDialog.value = true
  }

  // ============================================================================
  // CRUD Operations
  // ============================================================================

  async function save() {
    if (!formRef.value?.validate()) return
    if (schemaError.value) {
      showError(t('admin.facetTypes.form.invalidJson'))
      return
    }

    saving.value = true
    try {
      const data = {
        ...form.value,
        name_plural: form.value.name_plural || `${form.value.name}s`,
      }

      if (editingItem.value) {
        await facetApi.updateFacetType(editingItem.value.id, data)
        showSuccess(t('admin.facetTypes.messages.updated'))
      } else {
        await facetApi.createFacetType(data)
        showSuccess(t('admin.facetTypes.messages.created'))
      }

      closeDialog()
      await loadFacetTypes()
    } catch (e) {
      const detail = getErrorMessage(e) || t('admin.facetTypes.messages.saveError')
      showError(detail)
    } finally {
      saving.value = false
    }
  }

  async function deleteItem() {
    if (!canEdit.value) return
    if (!itemToDelete.value) return

    deleting.value = true
    try {
      await facetApi.deleteFacetType(itemToDelete.value.id)
      showSuccess(t('admin.facetTypes.messages.deleted', { name: itemToDelete.value.name }))
      deleteDialog.value = false
      itemToDelete.value = null
      await loadFacetTypes()
    } catch (e) {
      const detail = getErrorMessage(e) || t('admin.facetTypes.messages.deleteError')
      showError(detail)
    } finally {
      deleting.value = false
    }
  }

  // ============================================================================
  // Review Functions
  // ============================================================================

  async function loadNeedsReviewCount() {
    try {
      const response = await facetApi.getFacetTypes({ needs_review: true, per_page: 1 })
      needsReviewCount.value = response.data.total || 0
    } catch (e) {
      logger.error('Failed to load needs_review count', e)
    }
  }

  function openReviewDialog(item: FacetType) {
    reviewingItem.value = item
    reviewDialog.value = true
  }

  function closeReviewDialog() {
    reviewDialog.value = false
    reviewingItem.value = null
  }

  async function approveReview(item: FacetType) {
    if (!canEdit.value || !item) return

    reviewing.value = true
    try {
      await facetApi.reviewFacetType(item.id, { action: 'approve' })
      showSuccess(t('admin.facetTypes.messages.approved', { name: item.name }))
      closeReviewDialog()
      await Promise.all([loadFacetTypes(), loadNeedsReviewCount()])
    } catch (e) {
      const detail = getErrorMessage(e) || t('admin.facetTypes.messages.reviewError')
      showError(detail)
    } finally {
      reviewing.value = false
    }
  }

  async function rejectReview(item: FacetType) {
    if (!canEdit.value || !item) return

    reviewing.value = true
    try {
      await facetApi.reviewFacetType(item.id, { action: 'reject' })
      showSuccess(t('admin.facetTypes.messages.rejected', { name: item.name }))
      closeReviewDialog()
      await Promise.all([loadFacetTypes(), loadNeedsReviewCount()])
    } catch (e) {
      const detail = getErrorMessage(e) || t('admin.facetTypes.messages.reviewError')
      showError(detail)
    } finally {
      reviewing.value = false
    }
  }

  async function mergeReview(item: FacetType, targetId: string) {
    if (!canEdit.value || !item) return

    reviewing.value = true
    try {
      await facetApi.reviewFacetType(item.id, { action: 'merge', merge_target_id: targetId })
      showSuccess(t('admin.facetTypes.messages.merged', { name: item.name }))
      closeReviewDialog()
      await Promise.all([loadFacetTypes(), loadNeedsReviewCount()])
    } catch (e) {
      const detail = getErrorMessage(e) || t('admin.facetTypes.messages.reviewError')
      showError(detail)
    } finally {
      reviewing.value = false
    }
  }

  // ============================================================================
  // AI Schema Generation
  // ============================================================================

  async function generateSchemaWithAI() {
    if (!form.value.name) {
      showError(t('admin.facetTypes.form.nameRequired'))
      return
    }

    generatingSchema.value = true
    try {
      // Get entity type names for context
      const entityTypeNames = form.value.applicable_entity_type_slugs
        .map(slug => entityTypes.value.find(et => et.slug === slug)?.name || slug)

      const response = await facetApi.generateFacetTypeSchema({
        name: form.value.name,
        name_plural: form.value.name_plural,
        description: form.value.description,
        applicable_entity_types: entityTypeNames,
      })

      const generated = response.data

      // Apply generated values
      if (generated.value_schema) {
        form.value.value_schema = generated.value_schema
        schemaJson.value = JSON.stringify(generated.value_schema, null, 2)
      }
      if (generated.value_type) {
        form.value.value_type = generated.value_type
      }
      if (generated.deduplication_fields) {
        form.value.deduplication_fields = generated.deduplication_fields
      }
      if (generated.is_time_based !== undefined) {
        form.value.is_time_based = generated.is_time_based
      }
      if (generated.time_field_path) {
        form.value.time_field_path = generated.time_field_path
      }
      if (generated.ai_extraction_prompt) {
        form.value.ai_extraction_prompt = generated.ai_extraction_prompt
      }
      if (generated.icon) {
        form.value.icon = generated.icon
      }
      if (generated.color) {
        form.value.color = generated.color
      }

      showSuccess(t('admin.facetTypes.messages.schemaGenerated'))
    } catch (e) {
      const detail = getErrorMessage(e) || t('admin.facetTypes.messages.schemaGenerationError')
      showError(detail)
    } finally {
      generatingSchema.value = false
    }
  }

  // ============================================================================
  // Watchers
  // ============================================================================

  // Watch schema JSON for validation
  watch(schemaJson, (val) => {
    if (!val) {
      form.value.value_schema = null
      schemaError.value = ''
      return
    }
    try {
      form.value.value_schema = JSON.parse(val)
      schemaError.value = ''
    } catch {
      schemaError.value = t('admin.facetTypes.form.invalidJson')
    }
  })

  // ============================================================================
  // Initialization
  // ============================================================================

  async function initialize() {
    await Promise.all([loadEntityTypes(), loadFacetTypes(), loadNeedsReviewCount()])
  }

  // ============================================================================
  // Return
  // ============================================================================

  return {
    // State
    facetTypes,
    entityTypes,
    loading,
    dialog,
    deleteDialog,
    editingItem,
    itemToDelete,
    saving,
    deleting,
    formRef,
    activeTab,
    schemaJson,
    schemaError,
    generatingSchema,
    filters,
    form,

    // Review State
    reviewDialog,
    reviewingItem,
    reviewing,
    needsReviewCount,

    // Computed
    canEdit,
    headers,
    activeOptions,
    entityTypeOptions,

    // Static Options
    valueTypeOptions,
    aggregationOptions,
    suggestedFacetIcons,

    // Helper Functions
    getEntityTypeName,

    // Data Loading
    loadFacetTypes,
    loadNeedsReviewCount,
    debouncedSearch,

    // Dialog Actions
    openCreateDialog,
    openEditDialog,
    closeDialog,
    confirmDelete,

    // Review Actions
    openReviewDialog,
    closeReviewDialog,
    approveReview,
    rejectReview,
    mergeReview,

    // CRUD Operations
    save,
    deleteItem,

    // AI
    generateSchemaWithAI,

    // Initialization
    initialize,
  }
}
