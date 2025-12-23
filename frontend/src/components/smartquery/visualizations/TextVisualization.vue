<template>
  <div class="text-visualization">
    <v-card variant="flat" class="text-visualization__card">
      <v-card-text class="text-visualization__content">
        <!-- Render markdown-like content -->
        <div v-if="textContent" class="text-visualization__text" v-html="renderedContent" />

        <!-- Fallback: Show data as formatted list -->
        <div v-else-if="data.length > 0" class="text-visualization__data">
          <div
            v-for="(item, idx) in data"
            :key="idx"
            class="text-visualization__item"
          >
            <div class="text-visualization__item-header">
              <v-icon size="20" color="primary" class="mr-2">mdi-circle-small</v-icon>
              <strong>{{ item.entity_name || `Eintrag ${idx + 1}` }}</strong>
            </div>
            <div class="text-visualization__item-facets" v-if="item.facets">
              <div
                v-for="(facetValue, facetKey) in item.facets"
                :key="facetKey"
                class="text-visualization__facet"
              >
                <span class="text-medium-emphasis">{{ formatFacetKey(facetKey) }}:</span>
                <span class="ml-1 font-weight-medium">{{ formatFacetValue(facetValue) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- No data -->
        <div v-else class="text-visualization__empty">
          <v-icon size="48" color="grey-lighten-1">mdi-text-box-outline</v-icon>
          <p class="text-body-2 text-medium-emphasis mt-2">
            {{ t('smartQuery.visualization.noData') }}
          </p>
        </div>
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

const textContent = computed(() => props.config?.text_content || '')

// Simple markdown-like rendering
const renderedContent = computed(() => {
  if (!textContent.value) return ''

  return textContent.value
    // Bold text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    // Line breaks
    .replace(/\n/g, '<br>')
    // Lists
    .replace(/^- (.*)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)+/g, '<ul>$&</ul>')
})

function formatFacetKey(key: string): string {
  return key
    .replace(/-/g, ' ')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

function formatFacetValue(value: any): string {
  if (value === null || value === undefined) return '-'

  if (typeof value === 'object') {
    if ('value' in value) {
      const v = value.value
      if (typeof v === 'number') {
        return v.toLocaleString('de-DE')
      }
      return String(v)
    }
    return JSON.stringify(value)
  }

  if (typeof value === 'number') {
    return value.toLocaleString('de-DE')
  }

  return String(value)
}
</script>

<style scoped>
.text-visualization__card {
  background: rgba(var(--v-theme-surface-variant), 0.2);
  border-radius: 12px;
}

.text-visualization__content {
  padding: 24px;
}

.text-visualization__text {
  font-size: 1rem;
  line-height: 1.6;
  color: rgb(var(--v-theme-on-surface));
}

.text-visualization__text :deep(strong) {
  color: rgb(var(--v-theme-primary));
}

.text-visualization__text :deep(ul) {
  margin: 12px 0;
  padding-left: 24px;
}

.text-visualization__text :deep(li) {
  margin: 6px 0;
}

.text-visualization__data {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.text-visualization__item {
  padding: 16px;
  background: rgba(var(--v-theme-surface), 0.6);
  border-radius: 8px;
  border-left: 3px solid rgb(var(--v-theme-primary));
}

.text-visualization__item-header {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  font-size: 1rem;
}

.text-visualization__item-facets {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-left: 28px;
}

.text-visualization__facet {
  font-size: 0.875rem;
}

.text-visualization__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px;
}
</style>
