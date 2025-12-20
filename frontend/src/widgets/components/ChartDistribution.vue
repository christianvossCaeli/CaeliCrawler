<script setup lang="ts">
/**
 * ChartDistribution Widget - Shows entity distribution by type
 */

import { ref, onMounted, computed, watch } from 'vue'
import { dashboardApi } from '@/services/api'
import BaseWidget from '../BaseWidget.vue'
import type { WidgetDefinition, WidgetConfig, ChartDataResponse } from '../types'

const props = defineProps<{
  definition: WidgetDefinition
  config?: WidgetConfig
  isEditing?: boolean
}>()

const loading = ref(true)
const chartData = ref<ChartDataResponse | null>(null)

const refresh = async () => {
  loading.value = true
  try {
    const response = await dashboardApi.getChartData('entity-distribution')
    chartData.value = response.data
  } catch (e) {
    console.error('Failed to load chart data:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  refresh()
})

// Compute chart data for display
const pieData = computed(() => {
  if (!chartData.value?.data) return []
  return chartData.value.data.slice(0, 6).map((item, index) => ({
    ...item,
    percentage: chartData.value!.total
      ? Math.round((item.value / chartData.value!.total) * 100)
      : 0,
  }))
})

const total = computed(() => chartData.value?.total || 0)

// Default colors if not provided
const defaultColors = [
  '#1976D2', '#388E3C', '#FBC02D', '#D32F2F',
  '#7B1FA2', '#0097A7', '#F57C00', '#455A64',
]
</script>

<template>
  <BaseWidget
    :definition="definition"
    :config="config"
    :is-editing="isEditing"
    @refresh="refresh"
  >
    <div v-if="loading" class="d-flex justify-center py-8">
      <v-progress-circular indeterminate size="48" />
    </div>

    <template v-else-if="pieData.length > 0">
      <div class="chart-container">
        <!-- Simple Bar Chart Visualization -->
        <div class="bar-chart mb-4">
          <div
            v-for="(item, index) in pieData"
            :key="item.label"
            class="bar-item mb-2"
          >
            <div class="d-flex justify-space-between align-center mb-1">
              <span class="text-caption text-truncate" style="max-width: 60%">
                {{ item.label }}
              </span>
              <span class="text-caption font-weight-medium">
                {{ item.value.toLocaleString() }}
              </span>
            </div>
            <v-progress-linear
              :model-value="item.percentage"
              :color="item.color || defaultColors[index % defaultColors.length]"
              height="8"
              rounded
            />
          </div>
        </div>

        <!-- Total -->
        <div class="text-center text-caption text-medium-emphasis">
          {{ $t('common.total') }}: {{ total.toLocaleString() }}
        </div>
      </div>
    </template>

    <div v-else class="text-center py-8 text-medium-emphasis">
      <v-icon size="48" class="mb-2">mdi-chart-pie</v-icon>
      <div>{{ $t('common.noData') }}</div>
    </div>
  </BaseWidget>
</template>

<style scoped>
.chart-container {
  min-height: 150px;
}

.bar-chart {
  max-height: 200px;
  overflow-y: auto;
}

.bar-item {
  padding: 4px 0;
}
</style>
