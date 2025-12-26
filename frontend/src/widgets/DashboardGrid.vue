<template>
  <v-row class="dashboard-grid">
    <v-col
      v-for="widget in sortedWidgets"
      :key="widget.id"
      v-bind="getColProps(widget)"
      class="widget-col"
      :style="{ minHeight: getMinHeight(widget) }"
    >
      <WidgetRenderer :config="widget" :is-editing="isEditing" />
    </v-col>

    <!-- Empty State -->
    <v-col v-if="sortedWidgets.length === 0" cols="12">
      <v-card rounded="lg" class="pa-8 text-center">
        <v-icon size="64" class="mb-4 text-disabled">
          mdi-widgets-outline
        </v-icon>
        <div class="text-h6 text-medium-emphasis">
          {{ $t('dashboard.noWidgets') }}
        </div>
        <div class="text-body-2 text-disabled mt-2">
          {{ $t('dashboard.noWidgetsHint') }}
        </div>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
/**
 * DashboardGrid - Responsive grid layout for widgets
 *
 * Arranges widgets in a 4-column grid with responsive breakpoints.
 */

import { computed } from 'vue'
import type { WidgetConfig } from './types'
import { sortWidgetsByPosition, getColumnClasses } from './registry'
import WidgetRenderer from './WidgetRenderer.vue'

const props = defineProps<{
  widgets: WidgetConfig[]
  isEditing?: boolean
}>()

// Filter and sort widgets
const sortedWidgets = computed(() => {
  const enabled = props.widgets.filter((w) => w.enabled)
  return sortWidgetsByPosition(enabled)
})

// Get column props for a widget
const getColProps = (widget: WidgetConfig) => {
  const classes = getColumnClasses(widget.position.w)
  return {
    cols: classes.cols,
    sm: classes.sm,
    md: classes.md,
  }
}

// Calculate min-height based on widget height
const getMinHeight = (widget: WidgetConfig) => {
  // Base height of 150px per row unit
  const baseHeight = 150
  return `${widget.position.h * baseHeight}px`
}
</script>

<style scoped>
.dashboard-grid {
  margin: -8px;
}

.widget-col {
  padding: 8px;
}

/* Ensure widgets take full height of their cell */
.widget-col > * {
  height: 100%;
}
</style>
