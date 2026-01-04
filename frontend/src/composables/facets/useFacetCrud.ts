/**
 * Facet CRUD Composable
 *
 * Handles create, read, update, delete operations for facets.
 */

import { ref, computed, type Ref, type ComputedRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSnackbar } from '@/composables/useSnackbar'
import { useEntityStore } from '@/stores/entity'
import { facetApi } from '@/services/api'
import { buildTextRepresentation } from '@/composables/useEntityDetailHelpers'
import { useLogger } from '@/composables/useLogger'
import { getErrorMessage as getErrorDetail } from '@/utils/errorMessage'
import type { Entity, EntityType } from '@/stores/entity'
import type { FacetGroup, FacetValue, NewFacet, FacetSchema } from './types'

const logger = useLogger('useFacetCrud')

export function useFacetCrud(
  entity: Ref<Entity | null> | ComputedRef<Entity | null> | Entity | null,
  entityType: Ref<EntityType | null> | ComputedRef<EntityType | null> | EntityType | null,
  onFacetsSummaryUpdate: () => Promise<void>,
) {
  const { t } = useI18n()
  const { showSuccess, showError } = useSnackbar()
  const store = useEntityStore()

  // Helper to get entity value
  const getEntity = (): Entity | null => {
    if (entity === null) return null
    if ('value' in entity) return entity.value
    return entity
  }

  const getEntityType = (): EntityType | null => {
    if (entityType === null) return null
    if ('value' in entityType) return entityType.value
    return entityType
  }

  // State
  const selectedFacetGroup = ref<FacetGroup | null>(null)
  const facetDetails = ref<FacetValue[]>([])
  const facetToDelete = ref<FacetValue | null>(null)
  const editingFacet = ref<FacetValue | null>(null)
  const editingFacetValue = ref<Record<string, unknown>>({})
  const editingFacetTextValue = ref('')
  const editingFacetSchema = ref<FacetSchema | null>(null)
  const savingFacet = ref(false)
  const deletingFacet = ref(false)

  const newFacet = ref<NewFacet>({
    facet_type_id: '',
    text_representation: '',
    source_url: '',
    confidence_score: 0.8,
    value: {},
    target_entity_id: null,
  })

  // Computed
  const applicableFacetTypes = computed(() => {
    const et = getEntityType()
    const entityTypeSlug = et?.slug
    if (!entityTypeSlug) return store.activeFacetTypes

    return store.activeFacetTypes.filter((ft) => {
      if (!ft.applicable_entity_type_slugs || ft.applicable_entity_type_slugs.length === 0) {
        return true
      }
      return ft.applicable_entity_type_slugs.includes(entityTypeSlug)
    })
  })

  const selectedFacetTypeForForm = computed(() => {
    if (!newFacet.value.facet_type_id) return null
    return store.facetTypes.find((ft) => ft.id === newFacet.value.facet_type_id)
  })

  const editingFacetTypeName = computed(() => selectedFacetGroup.value?.facet_type_name || '')

  // Functions
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
    const e = getEntity()
    if (!newFacet.value.facet_type_id || !e) return false

    const facetType = selectedFacetTypeForForm.value
    if (!facetType) return false

    let valueToSave: Record<string, unknown>
    let textRepresentation: string

    if (facetType.value_schema?.properties) {
      valueToSave = { ...newFacet.value.value }
      textRepresentation = buildTextRepresentation(valueToSave, facetType.slug)
    } else if (facetType.allows_entity_reference && newFacet.value.target_entity_id) {
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
        entity_id: e.id,
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
    } catch (err: unknown) {
      showError(getErrorDetail(err) || t('entityDetail.messages.facetSaveError'))
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
    } catch {
      showError(t('entityDetail.messages.verifyError'))
    }
  }

  async function loadFacetDetails(facetGroup: FacetGroup) {
    const e = getEntity()
    if (!e) return

    selectedFacetGroup.value = facetGroup
    try {
      const response = await facetApi.getFacetValues({
        entity_id: e.id,
        facet_type_slug: facetGroup.facet_type_slug,
        per_page: 10000,
      })
      facetDetails.value = response.data.items || []
    } catch (err) {
      logger.error('Failed to load facet details', err)
      facetDetails.value = []
      showError(t('entityDetail.messages.facetDetailsLoadError'))
    }
  }

  function openEditFacetDialog(facet: FacetValue, facetGroup: FacetGroup) {
    editingFacet.value = facet
    selectedFacetGroup.value = facetGroup
    editingFacetValue.value = { ...(facet.value as Record<string, unknown>) }
    editingFacetTextValue.value = facet.text_representation || ''
    editingFacetSchema.value = (facetGroup.value_schema as FacetSchema) || null
  }

  async function saveEditedFacet() {
    if (!editingFacet.value) return false

    savingFacet.value = true
    try {
      const updateData = {
        value: editingFacetSchema.value
          ? editingFacetValue.value
          : { text: editingFacetTextValue.value },
        text_representation: editingFacetSchema.value
          ? Object.values(editingFacetValue.value)
              .filter((v) => v)
              .join(' - ')
              .substring(0, 500)
          : editingFacetTextValue.value,
      }
      await facetApi.updateFacetValue(editingFacet.value.id, updateData)
      showSuccess(t('entityDetail.messages.facetUpdated'))
      if (selectedFacetGroup.value) {
        await loadFacetDetails(selectedFacetGroup.value)
      }
      return true
    } catch (err: unknown) {
      showError(getErrorDetail(err) || t('entityDetail.messages.facetSaveError'))
      return false
    } finally {
      savingFacet.value = false
    }
  }

  function confirmDeleteFacet(facet: FacetValue) {
    facetToDelete.value = facet
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
    } catch (err: unknown) {
      showError(getErrorDetail(err) || t('entityDetail.messages.deleteError'))
      return false
    } finally {
      deletingFacet.value = false
    }
  }

  function closeDeleteDialog() {
    facetToDelete.value = null
  }

  function closeEditDialog() {
    editingFacet.value = null
    editingFacetValue.value = {}
    editingFacetTextValue.value = ''
    editingFacetSchema.value = null
  }

  function closeFacetDetails() {
    selectedFacetGroup.value = null
    facetDetails.value = []
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
    editingFacetTypeName,

    // Functions
    onFacetTypeChange,
    resetAddFacetForm,
    openAddFacetValueDialog,
    saveFacetValue,
    verifyFacet,
    loadFacetDetails,
    openEditFacetDialog,
    saveEditedFacet,
    confirmDeleteFacet,
    deleteSingleFacet,
    closeDeleteDialog,
    closeEditDialog,
    closeFacetDetails,
  }
}
