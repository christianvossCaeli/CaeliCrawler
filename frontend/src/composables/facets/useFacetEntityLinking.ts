/**
 * Facet Entity Linking Composable
 *
 * Handles linking facets to other entities (e.g., contacts).
 */

import { ref, onUnmounted, type Ref, type ComputedRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useSnackbar } from '@/composables/useSnackbar'
import { facetApi, entityApi } from '@/services/api'
import { useLogger } from '@/composables/useLogger'
import type { Entity } from '@/stores/entity'
import type { FacetValue, EntitySearchResult } from './types'

const logger = useLogger('useFacetEntityLinking')

export function useFacetEntityLinking(
  entity: Ref<Entity | null> | ComputedRef<Entity | null> | Entity | null,
  onFacetsSummaryUpdate: () => Promise<void>,
) {
  const { t } = useI18n()
  const router = useRouter()
  const { showSuccess, showError } = useSnackbar()

  // Helper to get entity value
  const getEntity = (): Entity | null => {
    if (entity === null) return null
    if ('value' in entity) return entity.value
    return entity
  }

  // State
  const facetToLink = ref<FacetValue | null>(null)
  const selectedTargetEntityId = ref<string | null>(null)
  const entitySearchQuery = ref('')
  const entitySearchResults = ref<EntitySearchResult[]>([])
  const searchingEntities = ref(false)
  const savingEntityLink = ref(false)
  let entitySearchTimeout: ReturnType<typeof setTimeout> | null = null

  // Functions
  function navigateToTargetEntity(facet: FacetValue) {
    if (!facet.target_entity_id || !facet.target_entity_slug) return

    const entityTypeSlug = facet.target_entity_type_slug || 'entity'
    router.push({
      name: 'entity-detail',
      params: {
        typeSlug: entityTypeSlug,
        entitySlug: facet.target_entity_slug,
      },
    })
  }

  function openEntityLinkDialog(facet: FacetValue) {
    facetToLink.value = facet
    selectedTargetEntityId.value = facet.target_entity_id || null
    entitySearchQuery.value = ''
    entitySearchResults.value = []
  }

  function closeEntityLinkDialog() {
    facetToLink.value = null
    selectedTargetEntityId.value = null
    entitySearchQuery.value = ''
    entitySearchResults.value = []
  }

  async function searchEntities(query: string) {
    // Clear any existing timeout
    if (entitySearchTimeout) {
      clearTimeout(entitySearchTimeout)
      entitySearchTimeout = null
    }

    if (!query || query.length < 2) {
      entitySearchResults.value = []
      return
    }

    entitySearchTimeout = setTimeout(async () => {
      searchingEntities.value = true
      try {
        const response = await entityApi.searchEntities({ q: query, per_page: 20 })
        const items = response.data.items || []
        const e = getEntity()

        entitySearchResults.value = items
          .filter((item: { id: string }) => item.id !== e?.id)
          .map(
            (item: {
              id: string
              name: string
              entity_type_name?: string
              entity_type?: { name?: string; icon?: string; color?: string }
            }) => ({
              id: item.id,
              name: item.name,
              entity_type_name: item.entity_type_name || item.entity_type?.name || 'Entity',
              entity_type_icon: item.entity_type?.icon || 'mdi-folder',
              entity_type_color: item.entity_type?.color || 'primary',
            }),
          )
      } catch (err) {
        logger.error('Failed to search entities', err)
        showError(t('entityDetail.messages.entitySearchError', 'Fehler bei der Entity-Suche'))
      } finally {
        searchingEntities.value = false
      }
    }, 300)
  }

  async function saveEntityLink() {
    if (!facetToLink.value || !selectedTargetEntityId.value) return

    savingEntityLink.value = true
    try {
      await facetApi.updateFacetValue(facetToLink.value.id, {
        target_entity_id: selectedTargetEntityId.value,
      })
      showSuccess(t('entityDetail.facets.entityLinked', 'Entity erfolgreich verknüpft'))
      closeEntityLinkDialog()
      await onFacetsSummaryUpdate()
    } catch (err) {
      logger.error('Failed to link entity', err)
      showError(t('entityDetail.messages.linkError', 'Fehler beim Verknüpfen'))
    } finally {
      savingEntityLink.value = false
    }
  }

  async function unlinkEntity(facet: FacetValue) {
    try {
      await facetApi.updateFacetValue(facet.id, {
        target_entity_id: null,
      })
      showSuccess(t('entityDetail.facets.entityUnlinked', 'Verknüpfung entfernt'))
      await onFacetsSummaryUpdate()
    } catch (err) {
      logger.error('Failed to unlink entity', err)
      showError(t('entityDetail.messages.unlinkError', 'Fehler beim Entfernen der Verknüpfung'))
    }
  }

  // Cleanup
  onUnmounted(() => {
    if (entitySearchTimeout) {
      clearTimeout(entitySearchTimeout)
      entitySearchTimeout = null
    }
  })

  return {
    // State
    facetToLink,
    selectedTargetEntityId,
    entitySearchQuery,
    entitySearchResults,
    searchingEntities,
    savingEntityLink,

    // Functions
    navigateToTargetEntity,
    openEntityLinkDialog,
    closeEntityLinkDialog,
    searchEntities,
    saveEntityLink,
    unlinkEntity,
  }
}
