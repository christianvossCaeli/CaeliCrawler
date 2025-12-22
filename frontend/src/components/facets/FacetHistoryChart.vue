<template>
  <v-card :loading="loading" class="facet-history-chart">
    <v-card-title class="d-flex align-center flex-wrap ga-2">
      <v-icon :icon="facetType?.facet_type_icon || 'mdi-chart-line'" :color="facetType?.facet_type_color" class="mr-2" />
      <span>{{ facetType?.facet_type_name || $t('entities.history.title') }}</span>
      <v-chip v-if="historyData?.statistics?.trend" :color="trendColor" size="small" class="ml-2">
        <v-icon :icon="trendIcon" size="small" start />
        {{ formatPercent(historyData?.statistics?.change_percent) }}
      </v-chip>
      <v-spacer />
      <!-- Time range filter -->
      <v-btn-toggle v-model="selectedRange" density="compact" mandatory color="primary" variant="outlined">
        <v-btn value="7d" size="small">7T</v-btn>
        <v-btn value="30d" size="small">30T</v-btn>
        <v-btn value="90d" size="small">90T</v-btn>
        <v-btn value="1y" size="small">1J</v-btn>
        <v-btn value="all" size="small">{{ $t('common.all') }}</v-btn>
      </v-btn-toggle>
    </v-card-title>

    <v-card-text>
      <!-- Chart -->
      <div v-if="!loading && chartData" class="chart-container" style="height: 300px;">
        <Line :data="chartData" :options="chartOptions" />
      </div>

      <!-- Empty state -->
      <v-alert v-else-if="!loading && !chartData" type="info" variant="tonal" class="my-4">
        {{ $t('entities.history.noData') }}
      </v-alert>

      <!-- Statistics cards -->
      <v-row v-if="historyData?.statistics" class="mt-4" dense>
        <v-col cols="6" md="3">
          <div class="text-center pa-2 rounded bg-surface-variant">
            <div class="text-h6 font-weight-bold">{{ formatValue(historyData.statistics.latest_value) }}</div>
            <div class="text-caption text-medium-emphasis">{{ $t('entities.history.current') }}</div>
          </div>
        </v-col>
        <v-col cols="6" md="3">
          <div class="text-center pa-2 rounded bg-surface-variant">
            <div class="text-h6 font-weight-bold" :class="trendTextColor">
              <v-icon :icon="trendIcon" size="small" />
              {{ formatPercent(historyData.statistics.change_percent) }}
            </div>
            <div class="text-caption text-medium-emphasis">{{ $t('entities.history.change') }}</div>
          </div>
        </v-col>
        <v-col cols="6" md="3">
          <div class="text-center pa-2 rounded bg-surface-variant">
            <div class="text-h6 font-weight-bold">{{ formatValue(historyData.statistics.min_value) }}</div>
            <div class="text-caption text-medium-emphasis">{{ $t('entities.history.minimum') }}</div>
          </div>
        </v-col>
        <v-col cols="6" md="3">
          <div class="text-center pa-2 rounded bg-surface-variant">
            <div class="text-h6 font-weight-bold">{{ formatValue(historyData.statistics.max_value) }}</div>
            <div class="text-caption text-medium-emphasis">{{ $t('entities.history.maximum') }}</div>
          </div>
        </v-col>
      </v-row>
    </v-card-text>

    <v-card-actions>
      <v-btn variant="tonal" size="small" @click="showAddDialog = true">
        <v-icon start>mdi-plus</v-icon>
        {{ $t('entities.history.addDataPoint') }}
      </v-btn>
      <v-spacer />
      <v-btn variant="text" size="small" @click="exportData">
        <v-icon start>mdi-download</v-icon>
        {{ $t('common.export') }}
      </v-btn>
      <v-btn variant="text" size="small" @click="loadHistory">
        <v-icon start>mdi-refresh</v-icon>
        {{ $t('common.refresh') }}
      </v-btn>
    </v-card-actions>

    <!-- Add Data Point Dialog -->
    <v-dialog v-model="showAddDialog" max-width="500">
      <v-card>
        <v-card-title>{{ $t('entities.history.addDataPoint') }}</v-card-title>
        <v-card-text>
          <v-form ref="addForm" @submit.prevent="addDataPoint">
            <v-text-field
              v-model.number="newDataPoint.value"
              :label="$t('entities.history.value') + (historyData?.unit_label ? ` (${historyData.unit_label})` : '')"
              type="number"
              :step="Math.pow(10, -(historyData?.precision || 2))"
              :rules="[v => v !== null && v !== undefined || $t('validation.required')]"
              required
            />
            <v-text-field
              v-model="newDataPoint.recorded_at"
              :label="$t('entities.history.recordedAt')"
              type="datetime-local"
              :rules="[v => !!v || $t('validation.required')]"
              required
            />
            <v-select
              v-model="newDataPoint.track_key"
              :items="availableTracks"
              item-title="label"
              item-value="key"
              :label="$t('entities.history.track')"
            />
            <v-textarea
              v-model="newDataPoint.note"
              :label="$t('entities.history.note')"
              rows="2"
              hint="Optional"
              persistent-hint
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showAddDialog = false">{{ $t('common.cancel') }}</v-btn>
          <v-btn color="primary" :loading="saving" @click="addDataPoint">{{ $t('common.add') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTheme } from 'vuetify'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
  Filler,
} from 'chart.js'
import 'chartjs-adapter-date-fns'
import { de } from 'date-fns/locale'
import { facetApi } from '@/services/api'
import type { EntityHistoryResponse, HistoryTrack } from '@/types/facets'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
  Filler
)

const props = defineProps<{
  entityId: string
  facetTypeId: string
  facetType?: {
    facet_type_id: string
    facet_type_slug: string
    facet_type_name: string
    facet_type_icon?: string
    facet_type_color?: string
    facet_type_value_type?: string
  }
}>()

const emit = defineEmits<{
  (e: 'updated'): void
}>()

const { t, locale } = useI18n()
const theme = useTheme()

// Computed for dark mode
const isDark = computed(() => theme.global.current.value.dark)

// Dark mode aware colors
const chartColors = computed(() => ({
  gridColor: isDark.value ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
  textColor: isDark.value ? 'rgba(255, 255, 255, 0.7)' : 'rgba(0, 0, 0, 0.7)',
  tooltipBg: isDark.value ? 'rgba(50, 50, 50, 0.95)' : 'rgba(255, 255, 255, 0.95)',
  tooltipBorder: isDark.value ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.2)',
  tooltipText: isDark.value ? '#ffffff' : '#000000',
}))

// State
const loading = ref(false)
const saving = ref(false)
const showAddDialog = ref(false)
const selectedRange = ref('all')
const historyData = ref<EntityHistoryResponse | null>(null)

const newDataPoint = ref({
  value: 0,
  recorded_at: new Date().toISOString().slice(0, 16),
  track_key: 'default',
  note: '',
})

// Computed
const trendColor = computed(() => {
  const trend = historyData.value?.statistics?.trend
  if (trend === 'up') return 'success'
  if (trend === 'down') return 'error'
  return 'grey'
})

const trendIcon = computed(() => {
  const trend = historyData.value?.statistics?.trend
  if (trend === 'up') return 'mdi-trending-up'
  if (trend === 'down') return 'mdi-trending-down'
  return 'mdi-trending-neutral'
})

const trendTextColor = computed(() => {
  const trend = historyData.value?.statistics?.trend
  if (trend === 'up') return 'text-success'
  if (trend === 'down') return 'text-error'
  return ''
})

const availableTracks = computed(() => {
  if (!historyData.value?.tracks) {
    return [{ key: 'default', label: 'Standard' }]
  }
  return historyData.value.tracks.map(t => ({
    key: t.track_key,
    label: t.label,
  }))
})

const dateRange = computed(() => {
  const now = new Date()
  switch (selectedRange.value) {
    case '7d':
      return { from: new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString() }
    case '30d':
      return { from: new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString() }
    case '90d':
      return { from: new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000).toISOString() }
    case '1y':
      return { from: new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000).toISOString() }
    default:
      return {}
  }
})

const chartData = computed(() => {
  if (!historyData.value?.tracks?.length) return null

  const datasets = historyData.value.tracks.map((track: HistoryTrack) => ({
    label: track.label,
    data: track.data_points.map(dp => ({
      x: new Date(dp.recorded_at),
      y: dp.value,
    })),
    borderColor: track.color,
    backgroundColor: track.color + '20',
    borderWidth: 2,
    borderDash: track.style === 'dashed' ? [5, 5] : track.style === 'dotted' ? [2, 2] : [],
    tension: 0.3,
    fill: true,
    pointRadius: 3,
    pointHoverRadius: 5,
  }))

  return { datasets }
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index' as const,
    intersect: false,
  },
  plugins: {
    legend: {
      display: (historyData.value?.tracks?.length ?? 0) > 1,
      position: 'top' as const,
      labels: {
        color: chartColors.value.textColor,
      },
    },
    tooltip: {
      backgroundColor: chartColors.value.tooltipBg,
      borderColor: chartColors.value.tooltipBorder,
      borderWidth: 1,
      titleColor: chartColors.value.tooltipText,
      bodyColor: chartColors.value.tooltipText,
      callbacks: {
        label: (context: any) => {
          const value = formatValue(context.parsed.y)
          return `${context.dataset.label}: ${value}`
        },
      },
    },
  },
  scales: {
    x: {
      type: 'time' as const,
      time: {
        unit: getTimeUnit(),
        displayFormats: {
          day: 'dd.MM',
          week: 'dd.MM',
          month: 'MMM yyyy',
          quarter: 'QQQ yyyy',
          year: 'yyyy',
        },
      },
      adapters: {
        date: {
          locale: locale.value === 'de' ? de : undefined,
        },
      },
      title: {
        display: false,
      },
      grid: {
        color: chartColors.value.gridColor,
      },
      ticks: {
        color: chartColors.value.textColor,
      },
    },
    y: {
      beginAtZero: false,
      title: {
        display: !!historyData.value?.unit_label,
        text: historyData.value?.unit_label || '',
        color: chartColors.value.textColor,
      },
      grid: {
        color: chartColors.value.gridColor,
      },
      ticks: {
        color: chartColors.value.textColor,
        callback: (value: number) => formatValue(value, true),
      },
    },
  },
}))

// Methods
function getTimeUnit(): 'day' | 'week' | 'month' | 'year' {
  switch (selectedRange.value) {
    case '7d':
      return 'day'
    case '30d':
      return 'day'
    case '90d':
      return 'week'
    case '1y':
      return 'month'
    default:
      return 'month'
  }
}

function formatValue(value: number | null | undefined, short = false): string {
  if (value === null || value === undefined) return '-'

  const precision = historyData.value?.precision ?? 2
  const unit = short ? '' : (historyData.value?.unit || '')

  // Format large numbers
  if (Math.abs(value) >= 1000000) {
    return (value / 1000000).toFixed(1) + ' Mio' + (unit ? ' ' + unit : '')
  }
  if (Math.abs(value) >= 1000 && short) {
    return (value / 1000).toFixed(1) + 'k' + (unit ? ' ' + unit : '')
  }

  const formatted = value.toLocaleString(locale.value, {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  })

  return unit ? `${formatted} ${unit}` : formatted
}

function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-'
  const sign = value > 0 ? '+' : ''
  return sign + value.toFixed(1) + '%'
}

async function loadHistory() {
  loading.value = true
  try {
    const params: Record<string, any> = {}
    if (dateRange.value.from) {
      params.from_date = dateRange.value.from
    }

    const response = await facetApi.getEntityHistory(props.entityId, props.facetTypeId, params)
    historyData.value = response.data
  } catch (error) {
    console.error('Failed to load history:', error)
  } finally {
    loading.value = false
  }
}

async function addDataPoint() {
  if (!newDataPoint.value.value && newDataPoint.value.value !== 0) return

  saving.value = true
  try {
    const data: any = {
      recorded_at: new Date(newDataPoint.value.recorded_at).toISOString(),
      value: newDataPoint.value.value,
      track_key: newDataPoint.value.track_key,
    }

    if (newDataPoint.value.note) {
      data.annotations = { note: newDataPoint.value.note }
    }

    await facetApi.addHistoryDataPoint(props.entityId, props.facetTypeId, data)

    showAddDialog.value = false
    newDataPoint.value = {
      value: 0,
      recorded_at: new Date().toISOString().slice(0, 16),
      track_key: 'default',
      note: '',
    }

    await loadHistory()
    emit('updated')
  } catch (error) {
    console.error('Failed to add data point:', error)
  } finally {
    saving.value = false
  }
}

function exportData() {
  if (!historyData.value?.tracks) return

  // Build CSV
  const headers = ['Datum', 'Track', 'Wert', historyData.value.unit_label || 'Einheit'].join(';')
  const rows: string[] = []

  for (const track of historyData.value.tracks) {
    for (const dp of track.data_points) {
      rows.push([
        new Date(dp.recorded_at).toLocaleDateString('de-DE'),
        track.label,
        dp.value.toString().replace('.', ','),
        historyData.value.unit || '',
      ].join(';'))
    }
  }

  const csv = [headers, ...rows].join('\n')
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)

  const a = document.createElement('a')
  a.href = url
  a.download = `${historyData.value.entity_name}_${historyData.value.facet_type_slug}_history.csv`
  a.click()

  URL.revokeObjectURL(url)
}

// Watch for range changes
watch(selectedRange, () => {
  loadHistory()
})

// Initial load
onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.facet-history-chart {
  overflow: visible;
}

.chart-container {
  position: relative;
  width: 100%;
}
</style>
