import { ref, readonly } from 'vue'
import { api } from '@/services/api'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('useFeatureFlags')

interface FeatureFlags {
  entityLevelFacets: boolean
  pysisFieldTemplates: boolean
  /** Enable entity hierarchy features (children tab, parent filter) */
  entityHierarchyEnabled: boolean
}

const flags = ref<FeatureFlags>({
  entityLevelFacets: false,
  pysisFieldTemplates: false,
  entityHierarchyEnabled: false,
})

const loaded = ref(false)
const loading = ref(false)

export function useFeatureFlags() {
  async function loadFeatureFlags() {
    if (loaded.value || loading.value) return

    loading.value = true
    try {
      const response = await api.get('/config/features')
      flags.value = response.data
      loaded.value = true
    } catch (e) {
      logger.error('Failed to load feature flags', e)
    } finally {
      loading.value = false
    }
  }

  return {
    flags: readonly(flags),
    loaded: readonly(loaded),
    loadFeatureFlags,
  }
}
