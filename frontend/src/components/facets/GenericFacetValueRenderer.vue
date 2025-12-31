<template>
  <div class="generic-facet-value d-flex align-start ga-2">
    <!-- Icon from FacetType -->
    <v-icon
      v-if="showIcon !== false"
      :icon="icon"
      :color="color"
      size="small"
      class="mt-1 flex-shrink-0"
    />

    <div class="flex-grow-1 min-width-0">
      <!-- Primary Text -->
      <div class="text-body-2">{{ primaryValue }}</div>

      <!-- Chip Fields (Type, Severity, etc.) -->
      <div v-if="chips.length" class="d-flex flex-wrap ga-1 mt-2">
        <v-chip
          v-for="chip in chips"
          :key="chip.field"
          size="x-small"
          :color="chip.color"
          variant="tonal"
        >
          {{ chip.value }}
        </v-chip>
      </div>

      <!-- Quote (if present) -->
      <div
        v-if="quote"
        class="quote-block mt-2 pa-2 rounded text-body-2"
      >
        <v-icon size="x-small" class="mr-1 opacity-60">mdi-format-quote-open</v-icon>
        <span class="font-italic">{{ quote }}</span>
      </div>

      <!-- Source URL (if present) -->
      <div v-if="sourceUrl" class="mt-1">
        <a
          :href="sourceUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="text-caption text-decoration-none text-primary"
        >
          <v-icon size="x-small" class="mr-1">mdi-link</v-icon>
          {{ $t('common.source') }}
        </a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { FacetType } from '@/types/entity'
import { useFacetTypeRenderer } from '@/composables/useFacetTypeRenderer'

const props = defineProps<{
  /** The facet value data object */
  value: Record<string, unknown>
  /** The FacetType definition */
  facetType: FacetType
  /** Whether to show the icon (default: true) */
  showIcon?: boolean
}>()

const {
  getDisplayConfig,
  getPrimaryValue,
  getChips,
  getQuote,
  getIcon,
  getColor,
} = useFacetTypeRenderer()

const config = computed(() => getDisplayConfig(props.facetType))
const icon = computed(() => (props.showIcon !== false ? getIcon(props.facetType) : ''))
const color = computed(() => getColor(props.facetType))

const primaryValue = computed(() => getPrimaryValue(props.value, config.value))
const chips = computed(() => getChips(props.value, config.value))
const quote = computed(() => getQuote(props.value, config.value))

const sourceUrl = computed(() => {
  const url = props.value.source_url
  return url && typeof url === 'string' ? url : null
})
</script>

<style scoped>
.generic-facet-value {
  min-width: 0;
}

.min-width-0 {
  min-width: 0;
}

/* Theme-aware quote block */
.quote-block {
  background-color: rgba(var(--v-theme-on-surface), 0.05);
  border-left: 3px solid rgba(var(--v-theme-on-surface), 0.2);
}

.v-theme--dark .quote-block {
  background-color: rgba(var(--v-theme-on-surface), 0.08);
}
</style>
