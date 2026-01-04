/**
 * Facet Enrichment Composable
 *
 * Handles facet enrichment from various sources (PySIS, relations, documents, etc.).
 */

import { ref, computed, onUnmounted, type Ref, type ComputedRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSnackbar } from '@/composables/useSnackbar'
import { entityDataApi } from '@/services/api'
import { useLogger } from '@/composables/useLogger'
import { extractErrorMessage } from '@/utils/errorMessage'
import type { Entity } from '@/stores/entity'
import type { EnrichmentSources } from './types'

const logger = useLogger('useFacetEnrichment')

export function useFacetEnrichment(
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
  const enrichmentSources = ref<EnrichmentSources | null>(null)
  const loadingEnrichmentSources = ref(false)
  const startingEnrichment = ref(false)
  const selectedEnrichmentSources = ref<string[]>([])
  const enrichmentTaskPolling = ref<ReturnType<typeof setInterval> | null>(null)

  // Computed
  const hasAnyEnrichmentSource = computed(() => {
    if (!enrichmentSources.value) return false
    return (
      enrichmentSources.value.pysis?.available ||
      enrichmentSources.value.relations?.available ||
      enrichmentSources.value.documents?.available ||
      enrichmentSources.value.extractions?.available ||
      enrichmentSources.value.attachments?.available
    )
  })

  // Functions
  async function loadEnrichmentSources() {
    const e = getEntity()
    if (!e) return

    loadingEnrichmentSources.value = true
    try {
      const response = await entityDataApi.getEnrichmentSources(e.id)
      enrichmentSources.value = response.data

      // Pre-select available sources
      selectedEnrichmentSources.value = []
      if (response.data.pysis?.available) selectedEnrichmentSources.value.push('pysis')
      if (response.data.relations?.available) selectedEnrichmentSources.value.push('relations')
      if (response.data.documents?.available) selectedEnrichmentSources.value.push('documents')
      if (response.data.extractions?.available) selectedEnrichmentSources.value.push('extractions')
    } catch (err) {
      logger.error('Failed to load enrichment sources', err)
      showError(t('entityDetail.enrichment.noSourcesAvailable'))
    } finally {
      loadingEnrichmentSources.value = false
    }
  }

  async function onEnrichmentMenuOpen(isOpen: boolean) {
    if (isOpen && !enrichmentSources.value) {
      await loadEnrichmentSources()
    }
  }

  async function startEnrichmentAnalysis(): Promise<string | null> {
    const e = getEntity()
    if (!e || selectedEnrichmentSources.value.length === 0) return null

    startingEnrichment.value = true
    try {
      const response = await entityDataApi.analyzeForFacets({
        entity_id: e.id,
        source_types: selectedEnrichmentSources.value,
      })
      return response.data.task_id
    } catch (err: unknown) {
      showError(extractErrorMessage(err))
      return null
    } finally {
      startingEnrichment.value = false
    }
  }

  function stopEnrichmentTaskPolling() {
    if (enrichmentTaskPolling.value) {
      clearInterval(enrichmentTaskPolling.value)
      enrichmentTaskPolling.value = null
    }
  }

  function toggleEnrichmentSource(source: string) {
    const idx = selectedEnrichmentSources.value.indexOf(source)
    if (idx >= 0) {
      selectedEnrichmentSources.value.splice(idx, 1)
    } else {
      selectedEnrichmentSources.value.push(source)
    }
  }

  function isSourceSelected(source: string): boolean {
    return selectedEnrichmentSources.value.includes(source)
  }

  function resetEnrichment() {
    enrichmentSources.value = null
    selectedEnrichmentSources.value = []
    stopEnrichmentTaskPolling()
  }

  // Cleanup
  onUnmounted(() => {
    stopEnrichmentTaskPolling()
  })

  return {
    // State
    enrichmentSources,
    loadingEnrichmentSources,
    startingEnrichment,
    selectedEnrichmentSources,
    enrichmentTaskPolling,

    // Computed
    hasAnyEnrichmentSource,

    // Functions
    loadEnrichmentSources,
    onEnrichmentMenuOpen,
    startEnrichmentAnalysis,
    stopEnrichmentTaskPolling,
    toggleEnrichmentSource,
    isSourceSelected,
    resetEnrichment,
  }
}
