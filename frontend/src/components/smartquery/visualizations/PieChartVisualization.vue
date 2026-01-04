<template>
  <div class="pie-chart-visualization">
    <div class="pie-chart-wrapper">
      <Pie :data="chartData" :options="chartOptions" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Pie } from 'vue-chartjs'
import {
  Chart as ChartJS,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { useDateFormatter } from '@/composables'
import type { VisualizationConfig } from './types'
import { getNestedValue } from './types'

const props = defineProps<{
  data: Record<string, unknown>[]
  config?: VisualizationConfig
}>()

const { formatNumber } = useDateFormatter()

// Register Chart.js components
ChartJS.register(ArcElement, Title, Tooltip, Legend)

const chartData = computed(() => {
  if (!props.data || props.data.length === 0) {
    return { labels: [], datasets: [] }
  }

  // Get labels from x-axis key or entity_name
  const xKey = props.config?.x_axis?.key || 'entity_name'
  const labels = props.data.map(item =>
    getNestedValue(item, xKey) || item.entity_name || 'Unbekannt'
  )

  // Get values from y-axis key or first numeric facet
  let valueKey = props.config?.y_axis?.key || ''

  if (!valueKey) {
    // Auto-detect
    const sample = props.data[0]
    if (sample.facets) {
      for (const [facetKey, facetValue] of Object.entries(sample.facets)) {
        if (typeof (facetValue as { value?: unknown })?.value === 'number') {
          valueKey = `facets.${facetKey}.value`
          break
        }
      }
    }
    if (!valueKey) valueKey = 'value'
  }

  const values = props.data.map(item => {
    const val = getNestedValue(item, valueKey)
    return typeof val === 'number' ? val : 0
  })

  // Generate colors
  const backgroundColors = props.data.map((_, idx) => getDefaultColor(idx))
  const borderColors = backgroundColors.map(c => c)

  return {
    labels,
    datasets: [{
      data: values,
      backgroundColor: backgroundColors,
      borderColor: borderColors,
      borderWidth: 2,
    }],
  }
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: true,
  aspectRatio: 1.5,
  plugins: {
    legend: {
      display: true,
      position: 'right' as const,
      labels: {
        usePointStyle: true,
        padding: 16,
      },
    },
    tooltip: {
      callbacks: {
        label: (context: { parsed: number; label?: string; dataset: { data: number[] } }) => {
          const value = context.parsed
          const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0)
          const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0
          return `${context.label}: ${formatNumber(value)} (${percentage}%)`
        },
      },
    },
  },
}))

function getDefaultColor(index: number): string {
  const colors = [
    '#1976D2', '#388E3C', '#F57C00', '#7B1FA2',
    '#C2185B', '#0097A7', '#FBC02D', '#455A64',
    '#D32F2F', '#512DA8', '#00796B', '#AFB42B',
  ]
  return colors[index % colors.length]
}
</script>

<style scoped>
.pie-chart-visualization {
  padding: 16px;
  background: rgba(var(--v-theme-surface-variant), 0.1);
  border-radius: 8px;
}

.pie-chart-wrapper {
  max-width: 500px;
  margin: 0 auto;
}
</style>
