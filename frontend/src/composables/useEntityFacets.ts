import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSnackbar } from './useSnackbar'
import { facetApi } from '@/services/api'
import { useEntityStore } from '@/stores/entity'
import { buildTextRepresentation } from './useEntityDetailHelpers'
import type { Entity, EntityType } from '@/stores/entity'
import type { FacetGroup, FacetValue } from '@/types/entity'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('useEntityFacets')

// Helper for type-safe error handling
function getErrorDetail(err: unknown): string | undefined {
  if (err && typeof err === 'object') {
    const e = err as { response?: { data?: { detail?: string } }; message?: string }
    return e.response?.data?.detail || e.message
  }
  return undefined
}

export interface NewFacet {
  facet_type_id: string
  text_representation: string
  source_url: string
  confidence_score: number
  value: Record<string, unknown>
  target_entity_id: string | null  // For entity references (e.g., contacts → person)
}

// Re-export for convenience
export type { FacetGroup, FacetValue }

// Alias for backward compatibility
export type FacetDetail = FacetValue

export interface FacetSchema {
  properties?: Record<string, { title?: string; type?: string; description?: string }>
  required?: string[]
}

export function useEntityFacets(
  entity: Entity | null,
  entityType: EntityType | null,
  onFacetsSummaryUpdate: () => Promise<void>
) {
  const { t } = useI18n()
  const { showSuccess, showError } = useSnackbar()
  const store = useEntityStore()

  const selectedFacetGroup = ref<FacetGroup | null>(null)
  const facetDetails = ref<FacetValue[]>([])
  const facetToDelete = ref<FacetValue | null>(null)
  const editingFacet = ref<FacetValue | null>(null)
  const editingFacetValue = ref<Record<string, unknown>>({})
  const editingFacetTextValue = ref('')
  const editingFacetSchema = ref<FacetSchema | null>(null)

  const newFacet = ref<NewFacet>({
    facet_type_id: '',
    text_representation: '',
    source_url: '',
    confidence_score: 0.8,
    value: {},
    target_entity_id: null,
  })

  const savingFacet = ref(false)
  const deletingFacet = ref(false)

  // Computed properties
  const applicableFacetTypes = computed(() => {
    const entityTypeSlug = entityType?.slug
    if (!entityTypeSlug) return store.activeFacetTypes

    return store.activeFacetTypes.filter(ft => {
      if (!ft.applicable_entity_type_slugs || ft.applicable_entity_type_slugs.length === 0) {
        return true
      }
      return ft.applicable_entity_type_slugs.includes(entityTypeSlug)
    })
  })

  const selectedFacetTypeForForm = computed(() => {
    if (!newFacet.value.facet_type_id) return null
    return store.facetTypes.find(ft => ft.id === newFacet.value.facet_type_id)
  })

  // Methods
  function onFacetTypeChange() {
    newFacet.value.value = {}
    newFacet.value.text_representation = ''
    newFacet.value.target_entity_id = null
  }

  function resetAddFacetForm() {
    newFacet.value = {
      facet_type_id: '',
      text_representation: '',
      source_url: '',
      confidence_score: 0.8,
      value: {},
      target_entity_id: null,
    }
  }

  function openAddFacetValueDialog(facetGroup: FacetGroup) {
    resetAddFacetForm()
    newFacet.value.facet_type_id = facetGroup.facet_type_id
  }

  async function saveFacetValue() {
    if (!newFacet.value.facet_type_id || !entity) return false

    const facetType = selectedFacetTypeForForm.value
    if (!facetType) return false

    let valueToSave: Record<string, unknown>
    let textRepresentation: string

    if (facetType.value_schema?.properties) {
      valueToSave = { ...newFacet.value.value }
      textRepresentation = buildTextRepresentation(valueToSave, facetType.slug)
    } else if (facetType.allows_entity_reference && newFacet.value.target_entity_id) {
      // Entity reference without schema - use text_representation (set by AddFacetDialog)
      textRepresentation = newFacet.value.text_representation || ''
      valueToSave = { entity_reference: newFacet.value.target_entity_id, name: textRepresentation }
    } else {
      if (!newFacet.value.text_representation) return false
      valueToSave = { text: newFacet.value.text_representation }
      textRepresentation = newFacet.value.text_representation
    }

    if (!textRepresentation) {
      showError(t('entityDetail.messages.facetValueRequired'))
      return false
    }

    savingFacet.value = true
    try {
      await facetApi.createFacetValue({
        entity_id: entity.id,
        facet_type_id: newFacet.value.facet_type_id,
        value: valueToSave,
        text_representation: textRepresentation,
        source_url: newFacet.value.source_url || null,
        confidence_score: newFacet.value.confidence_score,
        target_entity_id: newFacet.value.target_entity_id || undefined,
      })

      showSuccess(t('entityDetail.messages.facetAdded'))
      resetAddFacetForm()
      await onFacetsSummaryUpdate()
      return true
    } catch (e: unknown) {
      showError(getErrorDetail(e) || t('entityDetail.messages.facetSaveError'))
      return false
    } finally {
      savingFacet.value = false
    }
  }

  async function verifyFacet(facetValueId: string) {
    try {
      await store.verifyFacetValue(facetValueId, true)
      showSuccess(t('entityDetail.messages.facetVerified'))
      if (selectedFacetGroup.value) {
        await loadFacetDetails(selectedFacetGroup.value)
      }
      await onFacetsSummaryUpdate()
    } catch (e) {
      showError(t('entityDetail.messages.verifyError'))
    }
  }

  async function loadFacetDetails(facetGroup: FacetGroup) {
    if (!entity) return
    selectedFacetGroup.value = facetGroup
    try {
      const response = await facetApi.getFacetValues({
        entity_id: entity.id,
        facet_type_slug: facetGroup.facet_type_slug,
        per_page: 10000,
      })
      facetDetails.value = response.data.items || []
    } catch (e) {
      logger.error('Failed to load facet details', e)
      facetDetails.value = []
      showError(t('entityDetail.messages.facetDetailsLoadError'))
    }
  }

  async function saveEditedFacet() {
    if (!editingFacet.value) return false

    savingFacet.value = true
    try {
      const updateData = {
        value: editingFacetSchema.value ? editingFacetValue.value : { text: editingFacetTextValue.value },
        text_representation: editingFacetSchema.value
          ? Object.values(editingFacetValue.value).filter(v => v).join(' - ').substring(0, 500)
          : editingFacetTextValue.value,
      }
      await facetApi.updateFacetValue(editingFacet.value.id, updateData)
      showSuccess(t('entityDetail.messages.facetUpdated'))
      if (selectedFacetGroup.value) {
        await loadFacetDetails(selectedFacetGroup.value)
      }
      return true
    } catch (e: unknown) {
      showError(getErrorDetail(e) || t('entityDetail.messages.facetSaveError'))
      return false
    } finally {
      savingFacet.value = false
    }
  }

  async function deleteSingleFacet() {
    if (!facetToDelete.value) return false

    deletingFacet.value = true
    try {
      await facetApi.deleteFacetValue(facetToDelete.value.id)
      showSuccess(t('entityDetail.messages.facetDeleted'))
      facetToDelete.value = null
      if (selectedFacetGroup.value) {
        await loadFacetDetails(selectedFacetGroup.value)
      }
      await onFacetsSummaryUpdate()
      return true
    } catch (e: unknown) {
      showError(getErrorDetail(e) || t('entityDetail.messages.deleteError'))
      return false
    } finally {
      deletingFacet.value = false
    }
  }

  return {
    // State
    selectedFacetGroup,
    facetDetails,
    facetToDelete,
    editingFacet,
    editingFacetValue,
    editingFacetTextValue,
    editingFacetSchema,
    newFacet,
    savingFacet,
    deletingFacet,
    // Computed
    applicableFacetTypes,
    selectedFacetTypeForForm,
    // Methods
    onFacetTypeChange,
    resetAddFacetForm,
    openAddFacetValueDialog,
    saveFacetValue,
    verifyFacet,
    loadFacetDetails,
    saveEditedFacet,
    deleteSingleFacet,
  }
}
