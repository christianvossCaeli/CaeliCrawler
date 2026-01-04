<template>
  <v-chip
    size="small"
    :color="chipColor"
    variant="tonal"
    class="source-info-chip"
  >
    <v-icon start size="14">{{ chipIcon }}</v-icon>
    <span class="source-info-chip__label">{{ chipLabel }}</span>
    <v-tooltip activator="parent" location="bottom">
      <div class="source-tooltip">
        <div><strong>{{ t('smartQuery.sourceInfo.type') }}:</strong> {{ sourceTypeLabel }}</div>
        <div v-if="sourceInfo.last_updated">
          <strong>{{ t('smartQuery.sourceInfo.lastUpdated') }}:</strong> {{ formattedDate }}
        </div>
        <div v-if="sourceInfo.data_freshness">
          <strong>{{ t('smartQuery.sourceInfo.freshness') }}:</strong> {{ sourceInfo.data_freshness }}
        </div>
        <div v-if="sourceInfo.api_name">
          <strong>{{ t('smartQuery.sourceInfo.apiName') }}:</strong> {{ sourceInfo.api_name }}
        </div>
      </div>
    </v-tooltip>
  </v-chip>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDateFormatter } from '@/composables'
import type { SourceInfo } from '../types'

const props = defineProps<{
  sourceInfo: SourceInfo
}>()

const { t } = useI18n()
const { formatDateTime } = useDateFormatter()

const chipColor = computed(() => {
  switch (props.sourceInfo.type) {
    case 'live_api':
      return 'success'
    case 'facet_history':
      return 'info'
    default:
      return 'secondary'
  }
})

const chipIcon = computed(() => {
  switch (props.sourceInfo.type) {
    case 'live_api':
      return 'mdi-cloud-sync'
    case 'facet_history':
      return 'mdi-history'
    default:
      return 'mdi-database'
  }
})

const chipLabel = computed(() => {
  if (props.sourceInfo.data_freshness) {
    return props.sourceInfo.data_freshness
  }
  if (props.sourceInfo.api_name) {
    return props.sourceInfo.api_name
  }
  return sourceTypeLabel.value
})

const sourceTypeLabel = computed(() => {
  switch (props.sourceInfo.type) {
    case 'live_api':
      return t('smartQuery.sourceInfo.liveApi')
    case 'facet_history':
      return t('smartQuery.sourceInfo.facetHistory')
    default:
      return t('smartQuery.sourceInfo.internal')
  }
})

const formattedDate = computed(() => {
  if (!props.sourceInfo.last_updated) return ''
  try {
    const date = new Date(props.sourceInfo.last_updated)
    return formatDateTime(date)
  } catch {
    return props.sourceInfo.last_updated
  }
})
</script>

<style scoped>
.source-info-chip__label {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-tooltip {
  font-size: 0.75rem;
  line-height: 1.4;
}
</style>
