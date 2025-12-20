<script setup lang="ts">
/**
 * StatsEntities Widget - Shows entity statistics
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
const error = ref<string | null>(null)

const refresh = async () => {
  loading.value = true
  error.value = null
  try {
    await store.loadStats()
  } catch (e) {
    error.value = 'Failed to load'
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

      <template v-else-if="store.stats?.entities">
        <div class="text-h3 font-weight-bold text-primary">
          {{ store.stats.entities.total.toLocaleString() }}
        </div>
        <div class="text-caption text-medium-emphasis mt-1">
          {{ $t('dashboard.widgets.statsEntities.total') }}
        </div>

        <v-divider class="my-3" />

        <div class="d-flex justify-space-around text-body-2">
          <div>
            <div class="font-weight-medium text-success">
              {{ store.stats.entities.active.toLocaleString() }}
            </div>
            <div class="text-caption text-medium-emphasis">
              {{ $t('common.active') }}
            </div>
          </div>
          <div>
            <div class="font-weight-medium text-medium-emphasis">
              {{ store.stats.entities.inactive.toLocaleString() }}
            </div>
            <div class="text-caption text-medium-emphasis">
              {{ $t('common.inactive') }}
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
