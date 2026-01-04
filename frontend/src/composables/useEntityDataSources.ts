import { ref, toValue, type MaybeRefOrGetter } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSnackbar } from './useSnackbar'
import { adminApi, entityApi } from '@/services/api'
import { entityDetailCache } from '@/utils/cache'
import { useLogger } from '@/composables/useLogger'
import { emitCrawlerEvent } from '@/composables/useCrawlerEvents'
import { getErrorMessage as getErrorDetail } from '@/utils/errorMessage'

const logger = useLogger('useEntityDataSources')

export interface DataSource {
  id: string
  name: string
  base_url: string
  status: string
  source_type?: string
  is_direct_link?: boolean
  document_count?: number
  last_crawl?: string | null
  hasRunningJob?: boolean
  extra_data?: Record<string, unknown>
}

export function useEntityDataSources(entityIdRef: MaybeRefOrGetter<string | undefined>) {
  const { t } = useI18n()
  const { showSuccess, showError } = useSnackbar()

  const dataSources = ref<DataSource[]>([])
  const availableSourcesForLink = ref<DataSource[]>([])
  const selectedSourceToLink = ref<DataSource | null>(null)
  const sourceSearchQuery = ref('')

  const loadingDataSources = ref(false)
  const searchingSourcesForLink = ref(false)
  const linkingSource = ref(false)
  const startingCrawl = ref<string | null>(null)

  let sourceSearchTimeout: ReturnType<typeof setTimeout> | null = null

  async function loadDataSources() {
    const entityId = toValue(entityIdRef)
    if (!entityId) return

    // Check cache first
    const cacheKey = `datasources_${entityId}`
    const cached = entityDetailCache.get(cacheKey) as DataSource[] | undefined
    if (cached) {
      dataSources.value = cached
      return
    }

    loadingDataSources.value = true
    try {
      // Get sources via the new traceability endpoint:
      // Entity -> FacetValues -> Documents -> DataSources
      const response = await entityApi.getEntitySources(entityId)
      dataSources.value = response.data.sources || []

      // Cache the result
      entityDetailCache.set(cacheKey, dataSources.value)
    } catch (e) {
      logger.error('Failed to load data sources', e)
      dataSources.value = []
      showError(t('entityDetail.messages.dataSourcesLoadError'))
    } finally {
      loadingDataSources.value = false
    }
  }

  async function searchSourcesForLink(query: string) {
    sourceSearchQuery.value = query
    if (!query || query.length < 2) {
      availableSourcesForLink.value = []
      return
    }

    if (sourceSearchTimeout) clearTimeout(sourceSearchTimeout)
    sourceSearchTimeout = setTimeout(async () => {
      searchingSourcesForLink.value = true
      try {
        const response = await adminApi.getSources({ search: query, per_page: 20 })
        // Filter out already linked sources
        const linkedIds = new Set(dataSources.value.map((s) => s.id))
        availableSourcesForLink.value = (response.data.items || []).filter(
          (s: DataSource) => !linkedIds.has(s.id)
        )
      } catch (e) {
        logger.error('Failed to search sources:', e)
        availableSourcesForLink.value = []
        showError(t('entityDetail.messages.sourceSearchError'))
      } finally {
        searchingSourcesForLink.value = false
      }
    }, 300)
  }

  async function linkSourceToEntity() {
    const entityId = toValue(entityIdRef)
    if (!selectedSourceToLink.value || !entityId) return

    linkingSource.value = true
    try {
      // Update the source's extra_data to add this entity to entity_ids (N:M)
      const sourceId = selectedSourceToLink.value.id
      const currentExtraData = selectedSourceToLink.value.extra_data || {}

      // Support legacy entity_id and new entity_ids array - with type guards
      const rawEntityIds = currentExtraData.entity_ids
      const legacyEntityId = currentExtraData.entity_id
      const existingEntityIds: string[] = Array.isArray(rawEntityIds)
        ? rawEntityIds
        : (typeof legacyEntityId === 'string' ? [legacyEntityId] : [])

      // Add new entity if not already linked
      const newEntityIds = existingEntityIds.includes(entityId)
        ? existingEntityIds
        : [...existingEntityIds, entityId]

      await adminApi.updateSource(sourceId, {
        extra_data: {
          ...currentExtraData,
          entity_ids: newEntityIds,
          // Remove legacy field
          entity_id: undefined,
        },
      })

      showSuccess(t('entityDetail.messages.sourceLinkSuccess'))
      selectedSourceToLink.value = null

      // Invalidate cache and reload
      entityDetailCache.invalidate(`datasources_${entityId}`)
      await loadDataSources()
      return true
    } catch (e) {
      logger.error('Failed to link source:', e)
      showError(t('entityDetail.messages.sourceLinkError'))
      return false
    } finally {
      linkingSource.value = false
    }
  }

  async function startCrawl(source: DataSource) {
    startingCrawl.value = source.id
    try {
      await adminApi.startCrawl({ source_ids: [source.id] })
      showSuccess(t('entityDetail.messages.crawlStarted', { name: source.name }))
      source.hasRunningJob = true
      // Notify CrawlerView to refresh immediately
      emitCrawlerEvent('crawl-started', { sourceIds: [source.id] })
    } catch (e: unknown) {
      showError(getErrorDetail(e) || t('entityDetail.messages.crawlStartError'))
    } finally {
      startingCrawl.value = null
    }
  }

  async function reloadDataSources() {
    const entityId = toValue(entityIdRef)
    if (entityId) {
      entityDetailCache.invalidate(`datasources_${entityId}`)
      await loadDataSources()
    }
  }

  function cleanup() {
    if (sourceSearchTimeout) {
      clearTimeout(sourceSearchTimeout)
      sourceSearchTimeout = null
    }
  }

  return {
    dataSources,
    availableSourcesForLink,
    selectedSourceToLink,
    sourceSearchQuery,
    loadingDataSources,
    searchingSourcesForLink,
    linkingSource,
    startingCrawl,
    loadDataSources,
    searchSourcesForLink,
    linkSourceToEntity,
    startCrawl,
    reloadDataSources,
    cleanup,
  }
}
