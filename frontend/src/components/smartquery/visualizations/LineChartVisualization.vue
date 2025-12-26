<template>
  <div class="line-chart-visualization">
    <Line :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  TimeScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import 'chartjs-adapter-date-fns'
import { de } from 'date-fns/locale'
import type { VisualizationConfig } from './types'
import { getNestedValue } from './types'

// History data point
interface HistoryPoint {
  recorded_at: string
  value: number
}

// Local interface for line chart data items
interface LineChartDataItem {
  entity_id?: string
  entity_name?: string
  entity_type?: string
  history?: HistoryPoint[]
  facets?: Record<string, { value?: unknown } | unknown>
  [key: string]: unknown
}

const props = defineProps<{
  data: LineChartDataItem[]
  config?: VisualizationConfig
}>()

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  TimeScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const chartData = computed(() => {
  if (!props.data || props.data.length === 0) {
    return { labels: [], datasets: [] }
  }

  const isTimeSeries = props.config?.x_axis?.type === 'time'
  const xKey = props.config?.x_axis?.key || 'recorded_at'
  const series = props.config?.series || []

  // Check if data is grouped by entity (for multi-line charts)
  const hasEntityGrouping = props.data.some(d => d.history && Array.isArray(d.history))

  if (hasEntityGrouping) {
    // Multi-entity time series
    const datasets = props.data.map((entity, idx) => {
      const history = entity.history || []
      const sortedHistory = [...history].sort((a, b) =>
        new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime()
      )

      return {
        label: entity.entity_name || `Serie ${idx + 1}`,
        data: sortedHistory.map((point) => ({
          x: new Date(point.recorded_at).getTime(), // Use timestamp for Chart.js time scale
          y: point.value,
        })),
        borderColor: getDefaultColor(idx),
        backgroundColor: getDefaultColor(idx) + '20',
        tension: 0.3,
        fill: false,
        pointRadius: 3,
        pointHoverRadius: 5,
      }
    })

    return { datasets }
  }

  // Single series or flat data
  if (series.length > 0) {
    const labels = props.data.map(item => {
      const val = getNestedValue(item, xKey)
      if (isTimeSeries && (typeof val === 'string' || typeof val === 'number' || val instanceof Date)) {
        return new Date(val).getTime()
      }
      return val
    })

    const datasets = series.map((s, idx) => ({
      label: s.label,
      data: props.data.map(item => {
        const val = getNestedValue(item, s.key)
        return typeof val === 'number' ? val : 0
      }),
      borderColor: s.color || getDefaultColor(idx),
      backgroundColor: (s.color || getDefaultColor(idx)) + '20',
      tension: 0.3,
      fill: s.type === 'area',
      pointRadius: 3,
      pointHoverRadius: 5,
    }))

    return { labels, datasets }
  }

  // Auto-detect: find first numeric field
  const sample = props.data[0]
  let valueKey = 'value'
  let valueLabel = 'Wert'

  if (sample.facets) {
    for (const [facetKey, facetValue] of Object.entries(sample.facets)) {
      if (typeof (facetValue as { value?: unknown })?.value === 'number') {
        valueKey = `facets.${facetKey}.value`
        valueLabel = formatFacetLabel(facetKey)
        break
      }
    }
  }

  const labels = props.data.map(item => {
    const val = getNestedValue(item, xKey) || item.entity_name
    if (isTimeSeries && val && (typeof val === 'string' || typeof val === 'number' || val instanceof Date)) {
      return new Date(val).getTime()
    }
    return val
  })

  const data = props.data.map(item => {
    const val = getNestedValue(item, valueKey)
    return typeof val === 'number' ? val : 0
  })

  return {
    labels,
    datasets: [{
      label: props.config?.y_axis?.label || valueLabel,
      data,
      borderColor: '#1976D2',
      backgroundColor: '#1976D220',
      tension: 0.3,
      fill: true,
      pointRadius: 3,
      pointHoverRadius: 5,
    }],
  }
})

const chartOptions = computed(() => {
  const isTimeSeries = props.config?.x_axis?.type === 'time'
  const hasEntityGrouping = props.data.some(d => d.history && Array.isArray(d.history))

  return {
    responsive: true,
    maintainAspectRatio: true,
    aspectRatio: 2,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        display: (props.config?.series?.length || 0) > 1 || hasEntityGrouping,
        position: 'top' as const,
      },
      tooltip: {
        callbacks: {
          title: (context: Array<{ label?: string }>) => {
            const label = context[0]?.label
            if (label && isTimeSeries) {
              try {
                const date = new Date(label)
                return date.toLocaleDateString(undefined, {
                  day: '2-digit',
                  month: '2-digit',
                  year: 'numeric',
                })
              } catch {
                return label
              }
            }
            return label
          },
          label: (context: { parsed: { y: unknown }; dataset: { label?: string } }) => {
            const value = context.parsed.y
            if (typeof value === 'number') {
              return `${context.dataset.label}: ${value.toLocaleString()}`
            }
            return `${context.dataset.label}: ${value}`
          },
        },
      },
    },
    scales: {
      x: isTimeSeries || hasEntityGrouping ? {
        type: 'time' as const,
        time: {
          unit: 'day' as const,
          displayFormats: {
            day: 'dd.MM.yy',
            week: 'dd.MM.yy',
            month: 'MMM yyyy',
          },
        },
        adapters: {
          date: {
            locale: de,
          },
        },
        title: {
          display: !!props.config?.x_axis?.label,
          text: props.config?.x_axis?.label || 'Zeit',
        },
      } : {
        title: {
          display: !!props.config?.x_axis?.label,
          text: props.config?.x_axis?.label || '',
        },
      },
      y: {
        type: 'linear' as const,
        title: {
          display: !!props.config?.y_axis?.label,
          text: props.config?.y_axis?.label || '',
        },
        ticks: {
          callback: function(tickValue: string | number) {
            return Number(tickValue).toLocaleString()
          },
        },
      },
    },
  }
})

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
    '#D32F2F', '#512DA8', '#00796B', '#AFB42B',
  ]
  return colors[index % colors.length]
}
</script>

<style scoped>
.line-chart-visualization {
  padding: 16px;
  background: rgba(var(--v-theme-surface-variant), 0.1);
  border-radius: 8px;
}
</style>
