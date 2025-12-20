<script setup lang="ts">
/**
 * StatsCrawler Widget - Shows crawler statistics
 */

import { ref, onMounted } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'
import BaseWidget from '../BaseWidget.vue'
import type { WidgetDefinition, WidgetConfig } from '../types'

const props = defineProps<{
  definition: WidgetDefinition
  config?: WidgetConfig
  isEditing?: boolean
}>()

const store = useDashboardStore()
const loading = ref(true)

const refresh = async () => {
  loading.value = true
  try {
    await store.loadStats()
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (!store.stats) {
    refresh()
  } else {
    loading.value = false
  }
})
</script>

<template>
  <BaseWidget
    :definition="definition"
    :config="config"
    :is-editing="isEditing"
    @refresh="refresh"
  >
    <div class="stats-content text-center">
      <div v-if="loading" class="py-4">
        <v-progress-circular indeterminate size="32" />
      </div>

      <template v-else-if="store.stats?.crawler">
        <div class="text-h3 font-weight-bold" :class="store.stats.crawler.running_jobs > 0 ? 'text-success' : 'text-medium-emphasis'">
          {{ store.stats.crawler.running_jobs }}
        </div>
        <div class="text-caption text-medium-emphasis mt-1">
          {{ $t('dashboard.widgets.statsCrawler.running') }}
        </div>

        <v-divider class="my-3" />

        <div class="d-flex justify-space-around text-body-2">
          <div>
            <div class="font-weight-medium text-success">
              {{ store.stats.crawler.completed_jobs.toLocaleString() }}
            </div>
            <div class="text-caption text-medium-emphasis">
              {{ $t('common.completed') }}
            </div>
          </div>
          <div>
            <div class="font-weight-medium text-error">
              {{ store.stats.crawler.failed_jobs.toLocaleString() }}
            </div>
            <div class="text-caption text-medium-emphasis">
              {{ $t('common.failed') }}
            </div>
          </div>
        </div>
      </template>

      <div v-else class="text-medium-emphasis py-4">
        {{ $t('common.noData') }}
      </div>
    </div>
  </BaseWidget>
</template>

<style scoped>
.stats-content {
  min-height: 100px;
}
</style>
