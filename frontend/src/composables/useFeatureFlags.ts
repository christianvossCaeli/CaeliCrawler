import { ref, readonly } from 'vue'
import { api } from '@/services/api'

interface FeatureFlags {
  entityLevelFacets: boolean
  pysisFieldTemplates: boolean
}

const flags = ref<FeatureFlags>({
  entityLevelFacets: false,
  pysisFieldTemplates: false,
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
      console.error('Failed to load feature flags', e)
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
