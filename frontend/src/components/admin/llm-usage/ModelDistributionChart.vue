<template>
  <div class="model-distribution-chart">
    <Doughnut :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import type { LLMUsageByModel } from '@/types/llm-usage'

const props = defineProps<{
  data: LLMUsageByModel[]
}>()

ChartJS.register(ArcElement, Title, Tooltip, Legend)

const colors = [
  '#1976D2',
  '#4CAF50',
  '#FF9800',
  '#9C27B0',
  '#00BCD4',
  '#F44336',
  '#3F51B5',
  '#009688',
]

const chartData = computed(() => {
  const sortedData = [...props.data].sort((a, b) => b.cost_cents - a.cost_cents)

  return {
    labels: sortedData.map((d) => d.model),
    datasets: [
      {
        data: sortedData.map((d) => d.cost_cents / 100),
        backgroundColor: sortedData.map((_, i) => colors[i % colors.length]),
        borderWidth: 2,
        borderColor: '#fff',
      },
    ],
  }
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: true,
  aspectRatio: 1.2,
  plugins: {
    legend: {
      display: true,
      position: 'bottom' as const,
      labels: {
        usePointStyle: true,
        padding: 12,
        font: {
          size: 11,
        },
      },
    },
    tooltip: {
      callbacks: {
        label: (context: { label?: string; parsed: number; dataset: { data: number[] } }) => {
          const value = context.parsed
          const total = context.dataset.data.reduce((a, b) => a + b, 0)
          const percentage = ((value / total) * 100).toFixed(1)
          return `${context.label}: $${value.toFixed(2)} (${percentage}%)`
        },
      },
    },
  },
  cutout: '50%',
}))
</script>

<style scoped>
.model-distribution-chart {
  padding: 8px;
  max-height: 300px;
}
</style>
