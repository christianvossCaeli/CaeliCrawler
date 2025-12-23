<template>
  <v-alert
    v-if="result"
    :type="hasResults ? 'success' : 'warning'"
    variant="tonal"
    class="mb-4"
  >
    <template v-slot:prepend>
      <v-icon>{{ hasResults ? 'mdi-check-circle' : 'mdi-alert' }}</v-icon>
    </template>
    <div class="d-flex align-center flex-wrap ga-2">
      <span>{{ summaryText }}</span>
      <v-chip v-if="result.from_template" size="small" color="info" variant="outlined">
        <v-icon start size="small">mdi-bookmark</v-icon>
        {{ $t('sources.aiDiscovery.fromTemplate') }}
      </v-chip>
      <v-chip v-if="result.used_fallback" size="small" color="warning" variant="outlined">
        <v-icon start size="small">mdi-web</v-icon>
        {{ $t('sources.aiDiscovery.serpFallback') }}
      </v-chip>
    </div>
  </v-alert>
</template>

<script setup lang="ts">
/**
 * AiDiscoveryResultsSummary - Summary alert for discovery results
 *
 * Shows result counts and status indicators (template match, fallback used).
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DiscoveryResultV2 } from './types'

interface Props {
  result: DiscoveryResultV2 | null
}

const props = defineProps<Props>()
const { t } = useI18n()

const hasResults = computed(() => {
  if (!props.result) return false
  return props.result.api_sources.length > 0 || props.result.web_sources.length > 0
})

const summaryText = computed(() => {
  if (!props.result) return ''
  const apiCount = props.result.api_sources.length
  const webCount = props.result.web_sources.length
  if (apiCount > 0 && webCount > 0) {
    return t('sources.aiDiscovery.foundBoth', { api: apiCount, web: webCount })
  }
  if (apiCount > 0) {
    return t('sources.aiDiscovery.foundApis', { count: apiCount })
  }
  if (webCount > 0) {
    return t('sources.aiDiscovery.foundWeb', { count: webCount })
  }
  return t('sources.aiDiscovery.noResults')
})
</script>
