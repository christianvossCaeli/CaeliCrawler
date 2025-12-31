<template>
  <v-card
    v-if="normalizedValues.length > 0"
    variant="outlined"
    class="mb-4 facet-card"
    :style="cardStyle"
  >
    <v-card-title class="text-subtitle-1 d-flex align-center ga-2 py-2">
      <v-icon :icon="icon" :color="color" size="small" />
      <span>{{ displayName }}</span>
      <v-chip size="x-small" variant="tonal" :color="color" class="ml-auto">
        {{ normalizedValues.length }}
      </v-chip>
    </v-card-title>

    <v-card-text>
      <div class="d-flex flex-column ga-3">
        <GenericFacetValueRenderer
          v-for="(value, idx) in displayedValues"
          :key="idx"
          :value="value"
          :facet-type="facetType"
          :show-icon="false"
        />

        <!-- Show more button if there are more values -->
        <v-btn
          v-if="hasMore"
          variant="text"
          size="small"
          color="primary"
          @click="showAll = !showAll"
        >
          <v-icon start size="small">
            {{ showAll ? 'mdi-chevron-up' : 'mdi-chevron-down' }}
          </v-icon>
          {{ showAll ? $t('common.showLess') : $t('common.showMore', { count: remainingCount }) }}
        </v-btn>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { FacetType } from '@/types/entity'
import { useFacetTypeRenderer } from '@/composables/useFacetTypeRenderer'
import GenericFacetValueRenderer from './GenericFacetValueRenderer.vue'

const props = withDefaults(
  defineProps<{
    /** The FacetType definition */
    facetType: FacetType
    /** Array of facet values (can be objects or strings) */
    values: unknown[]
    /** Maximum number of values to show initially */
    maxInitial?: number
  }>(),
  {
    maxInitial: 3,
  }
)

const { normalizeValue, getIcon, getColor } = useFacetTypeRenderer()

const showAll = ref(false)

const icon = computed(() => getIcon(props.facetType))
const color = computed(() => getColor(props.facetType))

// Use CSS custom property for theme-aware border
const cardStyle = computed(() => ({
  '--facet-color': color.value,
  borderColor: 'var(--facet-border-color)',
}))

const displayName = computed(() => {
  return props.facetType.name_plural || props.facetType.name
})

const normalizedValues = computed(() => {
  return props.values.map((v) => normalizeValue(v))
})

const displayedValues = computed(() => {
  if (showAll.value) {
    return normalizedValues.value
  }
  return normalizedValues.value.slice(0, props.maxInitial)
})

const hasMore = computed(() => {
  return normalizedValues.value.length > props.maxInitial
})

const remainingCount = computed(() => {
  return normalizedValues.value.length - props.maxInitial
})
</script>

<style scoped>
.facet-card {
  --facet-border-color: color-mix(in srgb, var(--facet-color) 50%, transparent);
}

/* Slightly stronger border in light mode */
:root .facet-card {
  --facet-border-color: color-mix(in srgb, var(--facet-color) 40%, transparent);
}

/* Softer border in dark mode for better contrast */
.v-theme--dark .facet-card {
  --facet-border-color: color-mix(in srgb, var(--facet-color) 60%, transparent);
}
</style>
