<template>
  <div class="stat-card-visualization">
    <div class="stat-cards-grid">
      <v-card
        v-for="(card, idx) in statCards"
        :key="idx"
        class="stat-card"
        variant="tonal"
        :color="card.color || 'primary'"
      >
        <v-card-text class="stat-card__content">
          <div class="stat-card__icon" v-if="card.icon">
            <v-icon size="28" :color="card.color || 'primary'">{{ card.icon }}</v-icon>
          </div>
          <div class="stat-card__main">
            <div class="stat-card__value">
              {{ formatStatValue(card.value, card.unit) }}
            </div>
            <div class="stat-card__label text-body-2 text-medium-emphasis">
              {{ card.label }}
            </div>
          </div>
          <div v-if="card.trend" class="stat-card__trend" :class="`stat-card__trend--${card.trend}`">
            <v-icon size="16">{{ getTrendIcon(card.trend) }}</v-icon>
            <span v-if="card.trend_value">{{ card.trend_value }}</span>
          </div>
        </v-card-text>
      </v-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { VisualizationConfig, StatCard } from './types'
import { getNestedValue } from './types'

const props = defineProps<{
  data: Record<string, any>[]
  config?: VisualizationConfig
}>()

const statCards = computed((): StatCard[] => {
  // Use configured cards if available
  if (props.config?.cards && props.config.cards.length > 0) {
    return props.config.cards
  }

  // Auto-generate from data
  if (!props.data || props.data.length === 0) return []

  return props.data.slice(0, 4).map(item => {
    // Find first numeric facet value
    let value: any = null
    let unit: string | undefined

    if (item.facets) {
      for (const [facetKey, facetValue] of Object.entries(item.facets)) {
        if (typeof (facetValue as any)?.value === 'number') {
          value = (facetValue as any).value
          break
        }
      }
    }

    // Fallback to any numeric field
    if (value === null) {
      for (const [key, val] of Object.entries(item)) {
        if (typeof val === 'number' && key !== 'entity_id') {
          value = val
          break
        }
      }
    }

    return {
      label: item.entity_name || 'Wert',
      value: value ?? '-',
      unit,
      icon: getDefaultIcon(item),
    }
  })
})

function formatStatValue(value: any, unit?: string): string {
  if (value === null || value === undefined) return '-'

  let formatted: string
  if (typeof value === 'number') {
    formatted = value.toLocaleString('de-DE')
  } else {
    formatted = String(value)
  }

  return unit ? `${formatted} ${unit}` : formatted
}

function getTrendIcon(trend: string): string {
  switch (trend) {
    case 'up':
      return 'mdi-trending-up'
    case 'down':
      return 'mdi-trending-down'
    default:
      return 'mdi-minus'
  }
}

function getDefaultIcon(item: Record<string, any>): string {
  // Try to determine a sensible icon based on entity type or facets
  const type = item.entity_type?.toLowerCase() || ''

  if (type.includes('fussball') || type.includes('verein') || type.includes('sport')) {
    return 'mdi-soccer'
  }
  if (type.includes('person')) {
    return 'mdi-account'
  }
  if (type.includes('gemeinde') || type.includes('stadt') || type.includes('territorial')) {
    return 'mdi-city'
  }

  return 'mdi-chart-box'
}
</script>

<style scoped>
.stat-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.stat-card {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
}

.stat-card__content {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px !important;
}

.stat-card__icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  background: rgba(var(--v-theme-surface), 0.6);
  border-radius: 12px;
}

.stat-card__main {
  flex: 1;
  min-width: 0;
}

.stat-card__value {
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 1.2;
  color: rgb(var(--v-theme-on-surface));
}

.stat-card__label {
  margin-top: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stat-card__trend {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 16px;
  font-size: 0.75rem;
  font-weight: 600;
}

.stat-card__trend--up {
  background: rgba(76, 175, 80, 0.15);
  color: #388E3C;
}

.stat-card__trend--down {
  background: rgba(244, 67, 54, 0.15);
  color: #D32F2F;
}

.stat-card__trend--stable {
  background: rgba(158, 158, 158, 0.15);
  color: #757575;
}
</style>
