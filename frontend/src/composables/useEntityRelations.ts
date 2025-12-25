import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSnackbar } from './useSnackbar'
import { relationApi, entityApi } from '@/services/api'
import { useEntityStore } from '@/stores/entity'
import { getCachedData, setCachedData } from './useEntityDetailHelpers'
import type { Entity } from '@/stores/entity'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('useEntityRelations')

export interface Relation {
  id: string
  relation_type_id: string
  source_entity_id: string
  source_entity_name: string
  source_entity_slug: string
  source_entity_type_slug: string
  target_entity_id: string
  target_entity_name: string
  target_entity_slug: string
  target_entity_type_slug: string
  relation_type_name: string
  relation_type_name_inverse: string | null
  relation_type_color: string | null
  attributes: Record<string, any>
  human_verified: boolean
}

export function useEntityRelations(entity: Entity | null) {
  const { t } = useI18n()
  const { showSuccess, showError } = useSnackbar()
  const store = useEntityStore()

  const relations = ref<Relation[]>([])
  const relationTypes = ref<any[]>([])
  const targetEntities = ref<any[]>([])
  const entitySearchQuery = ref('')

  const loadingRelations = ref(false)
  const loadingRelationTypes = ref(false)
  const searchingEntities = ref(false)
  const savingRelation = ref(false)
  const deletingRelation = ref(false)
  const relationsLoaded = ref(false)

  const editingRelation = ref<Relation | null>(null)
  const relationToDelete = ref<Relation | null>(null)

  const newRelation = ref({
    relation_type_id: '',
    target_entity_id: '',
    direction: 'outgoing' as 'outgoing' | 'incoming',
    attributes_json: '',
  })

  async function loadRelations() {
    if (!entity || relationsLoaded.value) return

    // Check cache first
    const cacheKey = `relations_${entity.id}`
    const cached = getCachedData(cacheKey)
    if (cached) {
      relations.value = cached
      relationsLoaded.value = true
      return
    }

    loadingRelations.value = true
    try {
      const result = await store.fetchEntityRelations({
        entity_id: entity.id,
      })
      relations.value = result.items || []
      relationsLoaded.value = true

      // Cache the result
      setCachedData(cacheKey, relations.value)
    } catch (e) {
      logger.error('Failed to load relations', e)
      showError(t('entityDetail.messages.relationsLoadError'))
    } finally {
      loadingRelations.value = false
    }
  }

  async function loadRelationTypes() {
    if (relationTypes.value.length > 0) return // Already loaded

    loadingRelationTypes.value = true
    try {
      const response = await relationApi.getRelationTypes()
      relationTypes.value = response.data.items || response.data || []
    } catch (e) {
      logger.error('Failed to load relation types', e)
      showError(t('entityDetail.messages.relationTypesLoadError'))
    } finally {
      loadingRelationTypes.value = false
    }
  }

  async function searchEntities(query: string) {
    if (!query || query.length < 2) {
      targetEntities.value = []
      return
    }

    searchingEntities.value = true
    try {
      const response = await entityApi.searchEntities({ q: query, per_page: 20 })
      // Filter out the current entity from results
      targetEntities.value = (response.data.items || []).filter(
        (e: any) => e.id !== entity?.id
      )
    } catch (e) {
      logger.error('Failed to search entities', e)
      targetEntities.value = []
      showError(t('entityDetail.messages.entitySearchError'))
    } finally {
      searchingEntities.value = false
    }
  }

  function openAddRelationDialog() {
    editingRelation.value = null
    newRelation.value = {
      relation_type_id: '',
      target_entity_id: '',
      direction: 'outgoing',
      attributes_json: '',
    }
    targetEntities.value = []
    entitySearchQuery.value = ''
    loadRelationTypes()
  }

  function editRelation(rel: Relation) {
    editingRelation.value = rel
    // Determine direction based on whether current entity is source or target
    const isSource = rel.source_entity_id === entity?.id
    newRelation.value = {
      relation_type_id: rel.relation_type_id || '',
      target_entity_id: isSource ? rel.target_entity_id : rel.source_entity_id,
      direction: isSource ? 'outgoing' : 'incoming',
      attributes_json: rel.attributes ? JSON.stringify(rel.attributes, null, 2) : '',
    }
    // Pre-populate the target entities list with the current target
    targetEntities.value = [{
      id: isSource ? rel.target_entity_id : rel.source_entity_id,
      name: isSource ? rel.target_entity_name : rel.source_entity_name,
      entity_type_name: isSource ? rel.target_entity_type_slug : rel.source_entity_type_slug,
    }]
    loadRelationTypes()
  }

  function closeRelationDialog() {
    editingRelation.value = null
    newRelation.value = {
      relation_type_id: '',
      target_entity_id: '',
      direction: 'outgoing',
      attributes_json: '',
    }
  }

  async function saveRelation() {
    if (!entity || !newRelation.value.relation_type_id || !newRelation.value.target_entity_id) {
      return
    }

    savingRelation.value = true
    try {
      // Parse attributes JSON if provided
      let attributes = {}
      if (newRelation.value.attributes_json.trim()) {
        try {
          attributes = JSON.parse(newRelation.value.attributes_json)
        } catch (e) {
          showError(t('entityDetail.messages.invalidJson'))
          savingRelation.value = false
          return
        }
      }

      // Determine source and target based on direction
      const sourceId = newRelation.value.direction === 'outgoing'
        ? entity.id
        : newRelation.value.target_entity_id
      const targetId = newRelation.value.direction === 'outgoing'
        ? newRelation.value.target_entity_id
        : entity.id

      const data = {
        relation_type_id: newRelation.value.relation_type_id,
        source_entity_id: sourceId,
        target_entity_id: targetId,
        attributes: Object.keys(attributes).length > 0 ? attributes : null,
      }

      if (editingRelation.value) {
        await relationApi.updateRelation(editingRelation.value.id, data)
        showSuccess(t('entityDetail.messages.relationUpdated'))
      } else {
        await relationApi.createRelation(data)
        showSuccess(t('entityDetail.messages.relationCreated'))
      }

      closeRelationDialog()
      // Reload relations
      relationsLoaded.value = false
      await loadRelations()
      return true
    } catch (e: any) {
      showError(e.response?.data?.detail || t('entityDetail.messages.relationSaveError'))
      return false
    } finally {
      savingRelation.value = false
    }
  }

  function confirmDeleteRelation(rel: Relation) {
    relationToDelete.value = rel
  }

  async function deleteRelation() {
    if (!relationToDelete.value) return

    deletingRelation.value = true
    try {
      await relationApi.deleteRelation(relationToDelete.value.id)
      showSuccess(t('entityDetail.messages.relationDeleted'))
      relationToDelete.value = null
      // Reload relations
      relationsLoaded.value = false
      await loadRelations()
      return true
    } catch (e: any) {
      showError(e.response?.data?.detail || t('entityDetail.messages.deleteError'))
      return false
    } finally {
      deletingRelation.value = false
    }
  }

  return {
    relations,
    relationTypes,
    targetEntities,
    entitySearchQuery,
    loadingRelations,
    loadingRelationTypes,
    searchingEntities,
    savingRelation,
    deletingRelation,
    relationsLoaded,
    editingRelation,
    relationToDelete,
    newRelation,
    loadRelations,
    loadRelationTypes,
    searchEntities,
    openAddRelationDialog,
    editRelation,
    closeRelationDialog,
    saveRelation,
    confirmDeleteRelation,
    deleteRelation,
  }
}
