<template>
  <div class="usage-trend-chart">
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
import type { LLMUsageTrend } from '@/types/llm-usage'
import { useDateFormatter } from '@/composables'

const props = defineProps<{
  data: LLMUsageTrend[]
}>()

const { formatNumber, formatDateShort } = useDateFormatter()

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
  const sortedData = [...props.data].sort(
    (a, b) => new Date(a.day).getTime() - new Date(b.day).getTime()
  )

  return {
    datasets: [
      {
        label: 'Tokens',
        data: sortedData.map((d) => ({
          x: new Date(d.day).getTime(),
          y: d.total_tokens,
        })),
        borderColor: '#1976D2',
        backgroundColor: '#1976D220',
        tension: 0.3,
        fill: true,
        yAxisID: 'y',
        pointRadius: 3,
        pointHoverRadius: 5,
      },
      {
        label: 'Kosten ($)',
        data: sortedData.map((d) => ({
          x: new Date(d.day).getTime(),
          y: d.cost_cents / 100,
        })),
        borderColor: '#4CAF50',
        backgroundColor: '#4CAF5020',
        tension: 0.3,
        fill: false,
        yAxisID: 'y1',
        pointRadius: 3,
        pointHoverRadius: 5,
      },
      {
        label: 'Fehler',
        data: sortedData.map((d) => ({
          x: new Date(d.day).getTime(),
          y: d.error_count,
        })),
        borderColor: '#F44336',
        backgroundColor: '#F4433620',
        tension: 0.3,
        fill: false,
        yAxisID: 'y2',
        pointRadius: 3,
        pointHoverRadius: 5,
        hidden: true,
      },
    ],
  }
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: true,
  aspectRatio: 2.5,
  interaction: {
    mode: 'index' as const,
    intersect: false,
  },
  plugins: {
    legend: {
      display: true,
      position: 'top' as const,
    },
    tooltip: {
      callbacks: {
        title: (context: Array<{ label?: string }>) => {
          const label = context[0]?.label
          if (label) {
            try {
              const date = new Date(label)
              return formatDateShort(date)
            } catch {
              return label
            }
          }
          return label
        },
        label: (context: { parsed: { y: number | null }; dataset: { label?: string } }) => {
          const value = context.parsed.y ?? 0
          const label = context.dataset.label
          if (label === 'Tokens') {
            return `${label}: ${formatNumber(value)}`
          }
          if (label === 'Kosten ($)') {
            return `${label}: $${value.toFixed(2)}`
          }
          return `${label}: ${value}`
        },
      },
    },
  },
  scales: {
    x: {
      type: 'time' as const,
      time: {
        unit: 'day' as const,
        displayFormats: {
          day: 'dd.MM',
          week: 'dd.MM',
          month: 'MMM yyyy',
        },
      },
      adapters: {
        date: {
          locale: de,
        },
      },
      title: {
        display: false,
      },
    },
    y: {
      type: 'linear' as const,
      display: true,
      position: 'left' as const,
      title: {
        display: true,
        text: 'Tokens',
      },
      ticks: {
        callback: function (tickValue: string | number) {
          const value = Number(tickValue)
          if (value >= 1000000) {
            return `${(value / 1000000).toFixed(1)}M`
          }
          if (value >= 1000) {
            return `${(value / 1000).toFixed(0)}K`
          }
          return value
        },
      },
    },
    y1: {
      type: 'linear' as const,
      display: true,
      position: 'right' as const,
      title: {
        display: true,
        text: 'Kosten ($)',
      },
      grid: {
        drawOnChartArea: false,
      },
      ticks: {
        callback: function (tickValue: string | number) {
          return `$${Number(tickValue).toFixed(2)}`
        },
      },
    },
    y2: {
      type: 'linear' as const,
      display: false,
      position: 'right' as const,
    },
  },
}))
</script>

<style scoped>
.usage-trend-chart {
  padding: 8px;
}
</style>
