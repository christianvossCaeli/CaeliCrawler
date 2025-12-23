<template>
  <div class="comparison-visualization">
    <div class="comparison-grid" :style="gridStyle">
      <v-card
        v-for="(entity, idx) in entitiesToCompare"
        :key="entity.entity_id || idx"
        class="comparison-card"
        variant="outlined"
      >
        <v-card-title class="comparison-card__header">
          <v-avatar :color="getEntityColor(idx)" size="40" class="mr-3">
            <v-icon color="white">mdi-account-circle</v-icon>
          </v-avatar>
          <div class="comparison-card__title">
            <router-link
              v-if="entity.entity_id"
              :to="`/entities/${entity.entity_id}`"
              class="text-h6 text-primary text-decoration-none"
            >
              {{ entity.entity_name }}
            </router-link>
            <span v-else class="text-h6">{{ entity.entity_name }}</span>
            <div v-if="entity.entity_type" class="text-caption text-medium-emphasis">
              {{ entity.entity_type }}
            </div>
          </div>
        </v-card-title>

        <v-divider />

        <v-card-text class="comparison-card__body">
          <!-- Facets Comparison -->
          <div class="comparison-facets">
            <div
              v-for="facetKey in comparisonFacets"
              :key="facetKey"
              class="comparison-facet"
            >
              <div class="comparison-facet__label text-caption text-medium-emphasis">
                {{ formatFacetKey(facetKey) }}
              </div>
              <div class="comparison-facet__value text-body-1 font-weight-bold">
                {{ getFacetValue(entity, facetKey) }}
              </div>
            </div>
          </div>

          <!-- Core Attributes -->
          <div v-if="entity.core_attributes && Object.keys(entity.core_attributes).length > 0" class="comparison-attrs mt-4">
            <div class="text-caption text-medium-emphasis mb-2">
              {{ t('smartQuery.comparison.attributes') }}
            </div>
            <div class="comparison-attrs__grid">
              <div
                v-for="(value, key) in entity.core_attributes"
                :key="key"
                class="comparison-attr"
              >
                <span class="text-caption text-medium-emphasis">{{ formatAttrKey(String(key)) }}:</span>
                <span class="ml-1">{{ formatAttrValue(value) }}</span>
              </div>
            </div>
          </div>

          <!-- Tags -->
          <div v-if="entity.tags?.length > 0" class="comparison-tags mt-4">
            <v-chip
              v-for="tag in entity.tags.slice(0, 5)"
              :key="tag"
              size="small"
              variant="tonal"
              color="primary"
              class="mr-1 mb-1"
            >
              {{ tag }}
            </v-chip>
          </div>
        </v-card-text>
      </v-card>
    </div>

    <!-- Comparison Summary -->
    <v-card v-if="showSummary" variant="tonal" color="info" class="mt-4">
      <v-card-text class="d-flex align-center">
        <v-icon class="mr-2">mdi-information-outline</v-icon>
        <span>{{ comparisonSummary }}</span>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { VisualizationConfig } from './types'

const { t } = useI18n()

const props = defineProps<{
  data: Record<string, any>[]
  config?: VisualizationConfig
}>()

const entitiesToCompare = computed(() => {
  // Use configured entities or data
  if (props.config?.entities_to_compare && props.config.entities_to_compare.length > 0) {
    return props.config.entities_to_compare
  }
  return props.data.slice(0, 3)
})

const comparisonFacets = computed(() => {
  // Use configured facets or auto-detect from data
  if (props.config?.comparison_facets && props.config.comparison_facets.length > 0) {
    return props.config.comparison_facets
  }

  // Auto-detect from first entity
  const sample = entitiesToCompare.value[0]
  if (sample?.facets) {
    return Object.keys(sample.facets)
  }
  return []
})

const gridStyle = computed(() => ({
  gridTemplateColumns: `repeat(${Math.min(entitiesToCompare.value.length, 3)}, 1fr)`,
}))

const showSummary = computed(() => entitiesToCompare.value.length >= 2 && comparisonFacets.value.length > 0)

const comparisonSummary = computed(() => {
  if (entitiesToCompare.value.length < 2 || comparisonFacets.value.length === 0) return ''

  const entities = entitiesToCompare.value
  const facetKey = comparisonFacets.value[0]

  // Find entity with highest value for first facet
  let maxEntity = entities[0]
  let maxValue = getNumericFacetValue(entities[0], facetKey)

  for (const entity of entities.slice(1)) {
    const val = getNumericFacetValue(entity, facetKey)
    if (val > maxValue) {
      maxValue = val
      maxEntity = entity
    }
  }

  const facetLabel = formatFacetKey(facetKey)
  return t('smartQuery.comparison.summary', {
    entity: maxEntity.entity_name,
    facet: facetLabel,
    value: maxValue.toLocaleString('de-DE'),
  })
})

function getEntityColor(index: number): string {
  const colors = ['primary', 'success', 'warning', 'info']
  return colors[index % colors.length]
}

function getFacetValue(entity: Record<string, any>, facetKey: string): string {
  const facets = entity.facets || {}
  const facetValue = facets[facetKey]

  if (facetValue === undefined || facetValue === null) return '-'

  if (typeof facetValue === 'object' && 'value' in facetValue) {
    const val = facetValue.value
    if (typeof val === 'number') {
      return val.toLocaleString('de-DE')
    }
    return String(val)
  }

  if (typeof facetValue === 'number') {
    return facetValue.toLocaleString('de-DE')
  }

  return String(facetValue)
}

function getNumericFacetValue(entity: Record<string, any>, facetKey: string): number {
  const facets = entity.facets || {}
  const facetValue = facets[facetKey]

  if (typeof facetValue === 'object' && 'value' in facetValue) {
    return typeof facetValue.value === 'number' ? facetValue.value : 0
  }
  return typeof facetValue === 'number' ? facetValue : 0
}

function formatFacetKey(key: string): string {
  return key
    .replace(/-/g, ' ')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

function formatAttrKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

function formatAttrValue(value: any): string {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'number') return value.toLocaleString('de-DE')
  if (typeof value === 'boolean') return value ? 'Ja' : 'Nein'
  return String(value)
}
</script>

<style scoped>
.comparison-grid {
  display: grid;
  gap: 16px;
}

.comparison-card {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.comparison-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.comparison-card__header {
  display: flex;
  align-items: center;
  padding: 16px;
}

.comparison-card__title {
  min-width: 0;
  flex: 1;
}

.comparison-card__body {
  padding: 16px;
}

.comparison-facets {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.comparison-facet {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 8px 12px;
  background: rgba(var(--v-theme-surface-variant), 0.3);
  border-radius: 6px;
}

.comparison-facet__value {
  color: rgb(var(--v-theme-primary));
}

.comparison-attrs__grid {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.comparison-attr {
  font-size: 0.875rem;
}

@media (max-width: 768px) {
  .comparison-grid {
    grid-template-columns: 1fr !important;
  }
}
</style>
