<script setup lang="ts">
/**
 * WidgetRenderer - Dynamically renders a widget based on its config
 *
 * Looks up the widget type in the registry and renders the appropriate component.
 */

import { computed, Suspense } from 'vue'
import type { WidgetConfig } from './types'
import { getWidget } from './registry'

const props = defineProps<{
  config: WidgetConfig
  isEditing?: boolean
}>()

// Get the widget definition from the registry
const definition = computed(() => getWidget(props.config.type))

// Check if widget exists
const hasWidget = computed(() => !!definition.value)
</script>

<template>
  <div v-if="hasWidget && definition" class="widget-renderer">
    <Suspense>
      <component
        :is="definition.component"
        :definition="definition"
        :config="config"
        :is-editing="isEditing"
      />

      <template #fallback>
        <v-card class="widget-loading" rounded="lg">
          <v-card-text class="d-flex align-center justify-center py-8">
            <v-progress-circular indeterminate color="primary" />
          </v-card-text>
        </v-card>
      </template>
    </Suspense>
  </div>

  <!-- Unknown Widget Type -->
  <v-card v-else class="widget-unknown" rounded="lg">
    <v-card-text class="text-center py-4">
      <v-icon size="32" class="text-disabled">mdi-help-circle-outline</v-icon>
      <div class="text-caption text-disabled mt-2">
        {{ $t('dashboard.unknownWidget', { type: config.type }) }}
      </div>
    </v-card-text>
  </v-card>
</template>

<style scoped>
.widget-renderer {
  height: 100%;
}

.widget-loading,
.widget-unknown {
  height: 100%;
  min-height: 120px;
}
</style>
