<script setup lang="ts">
/**
 * StatsFacets Widget - Shows facet value statistics
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

      <template v-else-if="store.stats?.facets">
        <div class="text-h3 font-weight-bold text-info">
          {{ store.stats.facets.total.toLocaleString() }}
        </div>
        <div class="text-caption text-medium-emphasis mt-1">
          {{ $t('dashboard.widgets.statsFacets.total') }}
        </div>

        <v-divider class="my-3" />

        <div class="d-flex align-center justify-center">
          <v-progress-circular
            :model-value="store.stats.facets.verification_rate"
            :size="50"
            :width="4"
            color="success"
          >
            <span class="text-caption">
              {{ Math.round(store.stats.facets.verification_rate) }}%
            </span>
          </v-progress-circular>
          <div class="ml-3 text-left">
            <div class="text-body-2 font-weight-medium">
              {{ store.stats.facets.verified.toLocaleString() }}
            </div>
            <div class="text-caption text-medium-emphasis">
              {{ $t('dashboard.widgets.statsFacets.verified') }}
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
