<template>
  <v-card
    class="widget-card"
    :class="{ 'widget-card--editing': editMode }"
  >
    <!-- Widget Header -->
    <v-card-item density="compact">
      <template #prepend>
        <v-icon :icon="widgetIcon" :color="widgetColor" size="small" />
      </template>

      <v-card-title class="text-body-1 font-weight-medium">
        {{ widget.title }}
      </v-card-title>
      <v-card-subtitle v-if="widget.subtitle" class="text-caption">
        {{ widget.subtitle }}
      </v-card-subtitle>

      <template v-if="editMode" #append>
        <v-btn
          icon="mdi-pencil"
          size="x-small"
          variant="text"
          @click="$emit('edit')"
        />
        <v-btn
          icon="mdi-delete"
          size="x-small"
          variant="text"
          color="error"
          @click="$emit('delete')"
        />
      </template>
    </v-card-item>

    <v-divider />

    <!-- Widget Content -->
    <v-card-text class="widget-content">
      <!-- Loading State -->
      <div v-if="isLoading" class="d-flex justify-center align-center h-100">
        <v-progress-circular indeterminate size="32" color="primary" />
      </div>

      <!-- No Data State -->
      <div v-else-if="!data || data.length === 0" class="d-flex flex-column justify-center align-center h-100 text-medium-emphasis">
        <v-icon size="48" color="grey-lighten-1">mdi-database-off-outline</v-icon>
        <span class="text-body-2 mt-2">{{ t('summaries.noData') }}</span>
      </div>

      <!-- Visualization -->
      <component
        :is="visualizationComponent"
        v-else
        :data="data"
        :config="visualizationConfig"
      />
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, type Component } from 'vue'
import { useI18n } from 'vue-i18n'
import type { SummaryWidget } from '@/stores/customSummaries'

const props = defineProps<{
  widget: SummaryWidget
  data: Record<string, unknown>[]
  editMode?: boolean
  isLoading?: boolean
}>()
defineEmits<{
  edit: []
  delete: []
}>()
const { t } = useI18n()
import {
  VISUALIZATION_ICONS,
  VISUALIZATION_COLORS,
  type VisualizationType,
} from '@/components/smartquery/visualizations/types'

// Visualization Components - reuse from Smart Query
import TableVisualization from '@/components/smartquery/visualizations/TableVisualization.vue'
import StatCardVisualization from '@/components/smartquery/visualizations/StatCardVisualization.vue'
import TextVisualization from '@/components/smartquery/visualizations/TextVisualization.vue'

// Lazy-loaded components
const BarChartVisualization = defineAsyncComponent(
  () => import('@/components/smartquery/visualizations/BarChartVisualization.vue')
)
const LineChartVisualization = defineAsyncComponent(
  () => import('@/components/smartquery/visualizations/LineChartVisualization.vue')
)
const PieChartVisualization = defineAsyncComponent(
  () => import('@/components/smartquery/visualizations/PieChartVisualization.vue')
)
const ComparisonVisualization = defineAsyncComponent(
  () => import('@/components/smartquery/visualizations/ComparisonVisualization.vue')
)
const MapVisualization = defineAsyncComponent(
  () => import('@/components/smartquery/visualizations/MapVisualization.vue')
)
const CalendarVisualization = defineAsyncComponent(
  () => import('@/components/smartquery/visualizations/CalendarVisualization.vue')
)

const visualizationComponents: Record<string, Component> = {
  table: TableVisualization,
  bar_chart: BarChartVisualization,
  line_chart: LineChartVisualization,
  pie_chart: PieChartVisualization,
  stat_card: StatCardVisualization,
  text: TextVisualization,
  comparison: ComparisonVisualization,
  map: MapVisualization,
  calendar: CalendarVisualization,
  timeline: TableVisualization, // Fallback
}

const widgetIcon = computed(() => {
  const type = props.widget.widget_type as VisualizationType
  return VISUALIZATION_ICONS[type] || 'mdi-widgets'
})

const widgetColor = computed(() => {
  const type = props.widget.widget_type as VisualizationType
  return VISUALIZATION_COLORS[type] || 'grey'
})

const visualizationComponent = computed(() => {
  return visualizationComponents[props.widget.widget_type] || TableVisualization
})

const visualizationConfig = computed(() => {
  const vizConfig = props.widget.visualization_config || {}
  return {
    type: props.widget.widget_type,
    title: props.widget.title,
    subtitle: props.widget.subtitle,
    ...vizConfig,
  }
})
</script>

<style scoped>
.widget-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.widget-card--editing {
  border: 2px dashed rgb(var(--v-theme-primary));
  cursor: move;
}

.widget-content {
  flex: 1;
  overflow: auto;
  min-height: 100px;
}
</style>
