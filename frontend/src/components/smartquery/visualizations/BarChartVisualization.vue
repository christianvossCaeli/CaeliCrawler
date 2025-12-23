<template>
  <div class="bar-chart-visualization">
    <Bar :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import type { VisualizationConfig } from './types'
import { getNestedValue } from './types'

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const props = defineProps<{
  data: Record<string, any>[]
  config?: VisualizationConfig
}>()

const chartData = computed(() => {
  if (!props.data || props.data.length === 0) {
    return { labels: [], datasets: [] }
  }

  // Get category labels (x-axis)
  const xKey = props.config?.x_axis?.key || 'entity_name'
  const labels = props.data.map(item => getNestedValue(item, xKey) || item.entity_name || 'Unbekannt')

  // Get series data (y-axis)
  const series = props.config?.series || []

  if (series.length > 0) {
    // Use configured series
    const datasets = series.map((s, idx) => ({
      label: s.label,
      data: props.data.map(item => {
        const val = getNestedValue(item, s.key)
        return typeof val === 'number' ? val : 0
      }),
      backgroundColor: s.color || getDefaultColor(idx),
      borderRadius: 4,
    }))

    return { labels, datasets }
  }

  // Auto-detect: find first numeric facet
  const sample = props.data[0]
  let valueKey = 'value'
  let valueLabel = 'Wert'

  if (sample.facets) {
    for (const [facetKey, facetValue] of Object.entries(sample.facets)) {
      if (typeof (facetValue as any)?.value === 'number') {
        valueKey = `facets.${facetKey}.value`
        valueLabel = formatFacetLabel(facetKey)
        break
      }
    }
  }

  const data = props.data.map(item => {
    const val = getNestedValue(item, valueKey)
    return typeof val === 'number' ? val : 0
  })

  return {
    labels,
    datasets: [{
      label: props.config?.y_axis?.label || valueLabel,
      data,
      backgroundColor: '#1976D2',
      borderRadius: 4,
    }],
  }
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: true,
  aspectRatio: 2,
  plugins: {
    legend: {
      display: (props.config?.series?.length || 0) > 1,
      position: 'top' as const,
    },
    tooltip: {
      callbacks: {
        label: (context: any) => {
          const value = context.parsed.y
          if (typeof value === 'number') {
            return `${context.dataset.label}: ${value.toLocaleString('de-DE')}`
          }
          return `${context.dataset.label}: ${value}`
        },
      },
    },
  },
  scales: {
    x: {
      title: {
        display: !!props.config?.x_axis?.label,
        text: props.config?.x_axis?.label || '',
      },
      ticks: {
        maxRotation: 45,
        minRotation: 0,
      },
    },
    y: {
      title: {
        display: !!props.config?.y_axis?.label,
        text: props.config?.y_axis?.label || '',
      },
      beginAtZero: true,
      ticks: {
        callback: (value: number) => value.toLocaleString('de-DE'),
      },
    },
  },
}))

function formatFacetLabel(slug: string): string {
  return slug
    .replace(/-/g, ' ')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

function getDefaultColor(index: number): string {
  const colors = [
    '#1976D2', '#388E3C', '#F57C00', '#7B1FA2',
    '#C2185B', '#0097A7', '#FBC02D', '#455A64',
  ]
  return colors[index % colors.length]
}
</script>

<style scoped>
.bar-chart-visualization {
  padding: 16px;
  background: rgba(var(--v-theme-surface-variant), 0.1);
  border-radius: 8px;
}
</style>
