<script setup lang="ts">
/**
 * ChartDistribution Widget - Shows entity distribution by type
 */

import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { dashboardApi } from '@/services/api'
import { handleKeyboardClick } from '../composables'
import BaseWidget from '../BaseWidget.vue'
import type { WidgetDefinition, WidgetConfig, ChartDataResponse, ChartItemWithPercentage } from '../types'

const props = defineProps<{
  definition: WidgetDefinition
  config?: WidgetConfig
  isEditing?: boolean
}>()

const router = useRouter()
const loading = ref(true)
const error = ref<string | null>(null)
const chartData = ref<ChartDataResponse | null>(null)

const refresh = async () => {
  loading.value = true
  error.value = null
  try {
    const response = await dashboardApi.getChartData('entity-distribution')
    chartData.value = response.data
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  refresh()
})

// Compute chart data for display
const pieData = computed<ChartItemWithPercentage[]>(() => {
  if (!chartData.value?.data) return []
  return chartData.value.data.slice(0, 6).map((item): ChartItemWithPercentage => ({
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

const navigateToEntityType = (item: ChartItemWithPercentage) => {
  if (props.isEditing) return
  // Navigate to entities filtered by type (using slug if available)
  if (item.slug) {
    router.push({ path: `/entities/${item.slug}` })
  } else {
    router.push({ path: '/entities', query: { type: item.label } })
  }
}

const handleKeydown = (event: KeyboardEvent, item: ChartItemWithPercentage) => {
  handleKeyboardClick(event, () => navigateToEntityType(item))
}
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
        <div class="bar-chart mb-4" role="list" aria-label="Entity distribution">
          <div
            v-for="(item, index) in pieData"
            :key="item.label"
            class="bar-item mb-2 clickable-bar"
            :class="{ 'non-interactive': isEditing }"
            role="button"
            :tabindex="isEditing ? -1 : 0"
            :aria-label="item.label + ': ' + item.value + ' (' + item.percentage + '%)'"
            @click="navigateToEntityType(item)"
            @keydown="handleKeydown($event, item)"
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

.clickable-bar {
  cursor: pointer;
  padding: 8px;
  margin: -4px -8px;
  border-radius: 8px;
  transition: background-color 0.2s ease;
}

.clickable-bar:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.08);
}

.clickable-bar:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.non-interactive {
  cursor: default;
  pointer-events: none;
}
</style>
