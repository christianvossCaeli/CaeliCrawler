<template>
  <v-dialog
    :model-value="modelValue"
    :max-width="DIALOG_SIZES.SM"
    @update:model-value="$emit('update:model-value', $event)"
  >
    <v-card>
      <v-toolbar color="primary" density="compact">
        <v-icon class="ml-4">mdi-tune</v-icon>
        <v-toolbar-title>{{ t('entities.extendedFilters') }}</v-toolbar-title>
        <v-spacer></v-spacer>
        <v-btn
          icon
          variant="tonal"
          :title="t('common.close')"
          :aria-label="t('common.close')"
          @click="$emit('update:model-value', false)"
        >
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text class="pa-0">
        <div v-if="schemaAttributes.length === 0" class="text-medium-emphasis text-center py-8">
          <v-icon size="48" color="grey-lighten-1" class="mb-2">mdi-filter-off</v-icon>
          <div>{{ t('entities.noFilterableAttributes') }}</div>
        </div>

        <template v-else>
          <!-- Location Section -->
          <div v-if="locationAttributes.length > 0" class="filter-section">
            <div class="filter-section-header">
              <v-icon size="small" class="mr-2">mdi-map-marker</v-icon>
              {{ t('entities.location') }}
            </div>
            <div class="filter-section-content">
              <v-row dense>
                <v-col v-if="hasAttribute('country')" cols="12" sm="4">
                  <v-select
                    :model-value="getStringFilter('country')"
                    :items="locationOptions.countries"
                    :label="t('entities.country')"
                    density="compact"
                    variant="outlined"
                    clearable
                    hide-details
                    @update:model-value="updateTempFilter('country', $event)"
                    @focus="$emit('load-location-options')"
                  ></v-select>
                </v-col>
                <v-col v-if="hasAttribute('admin_level_1')" cols="12" sm="4">
                  <v-select
                    :model-value="getStringFilter('admin_level_1')"
                    :items="locationOptions.admin_level_1"
                    :label="t('entities.region')"
                    density="compact"
                    variant="outlined"
                    :disabled="!getStringFilter('country')"
                    clearable
                    hide-details
                    @update:model-value="updateTempFilter('admin_level_1', $event)"
                  ></v-select>
                </v-col>
                <v-col v-if="hasAttribute('admin_level_2')" cols="12" sm="4">
                  <v-select
                    :model-value="getStringFilter('admin_level_2')"
                    :items="locationOptions.admin_level_2"
                    :label="t('entities.district')"
                    density="compact"
                    variant="outlined"
                    :disabled="!getStringFilter('admin_level_1')"
                    clearable
                    hide-details
                    @update:model-value="updateTempFilter('admin_level_2', $event)"
                  ></v-select>
                </v-col>
              </v-row>
            </div>
          </div>

          <!-- Numeric Attributes Section (Range Sliders) -->
          <div v-if="numericAttributes.length > 0" class="filter-section">
            <div class="filter-section-header">
              <v-icon size="small" class="mr-2">mdi-tune-vertical</v-icon>
              {{ t('entities.filters.ranges', 'Wertebereiche') }}
            </div>
            <div class="filter-section-content">
              <div
                v-for="attr in numericAttributes"
                :key="attr.key"
                class="range-filter-item"
              >
                <div class="range-filter-label">
                  <span>{{ attr.title }}</span>
                  <span class="range-filter-value">
                    {{ formatRangeDisplay(attr) }}
                  </span>
                </div>
                <v-range-slider
                  :model-value="getRangeValue(attr)"
                  :min="attr.min_value ?? 0"
                  :max="attr.max_value ?? 100"
                  :step="getStepForAttribute(attr)"
                  density="compact"
                  hide-details
                  thumb-label
                  color="primary"
                  @update:model-value="updateRangeFilter(attr.key, $event)"
                ></v-range-slider>
              </div>
            </div>
          </div>

          <!-- String Attributes Section (Dropdowns) -->
          <div v-if="stringAttributes.length > 0" class="filter-section">
            <div class="filter-section-header">
              <v-icon size="small" class="mr-2">mdi-tag-multiple</v-icon>
              {{ t('entities.attributes') }}
            </div>
            <div class="filter-section-content">
              <v-row dense>
                <v-col
                  v-for="attr in stringAttributes"
                  :key="attr.key"
                  cols="12"
                  sm="6"
                >
                  <v-select
                    :model-value="getStringFilter(attr.key)"
                    :items="attributeValueOptions[attr.key] || []"
                    :label="attr.title"
                    density="compact"
                    variant="outlined"
                    clearable
                    hide-details
                    @focus="$emit('load-attribute-values', attr.key)"
                    @update:model-value="updateTempFilter(attr.key, $event)"
                  ></v-select>
                </v-col>
              </v-row>
            </div>
          </div>
        </template>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions class="pa-4">
        <v-chip
          v-if="activeExtendedFilterCount > 0"
          size="small"
          color="primary"
          variant="tonal"
        >
          {{ activeExtendedFilterCount }} {{ t('entities.filtersActive') }}
        </v-chip>
        <v-spacer></v-spacer>
        <v-btn
          v-if="hasExtendedFilters"
          variant="tonal"
          color="error"
          size="small"
          @click="$emit('clear-filters')"
        >
          {{ t('common.reset') }}
        </v-btn>
        <v-btn variant="outlined" @click="$emit('update:model-value', false)">
          {{ t('common.cancel') }}
        </v-btn>
        <v-btn color="primary" variant="flat" @click="$emit('apply-filters')">
          {{ t('entities.apply') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'
import type { SchemaAttribute, LocationOptions, RangeFilterValue } from '@/composables/useEntitiesView'

type FilterValue = string | RangeFilterValue | null

interface Props {
  modelValue: boolean
  tempExtendedFilters: Record<string, FilterValue>
  schemaAttributes: SchemaAttribute[]
  attributeValueOptions: Record<string, string[]>
  locationOptions: LocationOptions
  locationAttributes: SchemaAttribute[]
  nonLocationAttributes: SchemaAttribute[]
  hasAttribute: (key: string) => boolean
  activeExtendedFilterCount: number
  hasExtendedFilters: boolean
}

interface Emits {
  (e: 'update:model-value', value: boolean): void
  (e: 'update:temp-extended-filters', value: Record<string, FilterValue>): void
  (e: 'load-location-options'): void
  (e: 'load-attribute-values', key: string): void
  (e: 'apply-filters'): void
  (e: 'clear-filters'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const { t } = useI18n()

// Separate numeric and string attributes
const numericAttributes = computed(() =>
  props.nonLocationAttributes.filter(attr => attr.is_numeric)
)

const stringAttributes = computed(() =>
  props.nonLocationAttributes.filter(attr => !attr.is_numeric)
)

// Get string filter value
function getStringFilter(key: string): string | null {
  const value = props.tempExtendedFilters[key]
  return typeof value === 'string' ? value : null
}

// Get range value for slider [min, max]
function getRangeValue(attr: SchemaAttribute): [number, number] {
  const value = props.tempExtendedFilters[attr.key]
  const minDefault = attr.min_value ?? 0
  const maxDefault = attr.max_value ?? 100

  if (value && typeof value === 'object' && 'min' in value) {
    return [value.min ?? minDefault, value.max ?? maxDefault]
  }
  return [minDefault, maxDefault]
}

// Format range display for label - always show current values
function formatRangeDisplay(attr: SchemaAttribute): string {
  const [min, max] = getRangeValue(attr)
  return `${formatNumber(min)} - ${formatNumber(max)}`
}

// Format number for display
function formatNumber(value: number): string {
  if (value >= 1000000) {
    return (value / 1000000).toFixed(1) + 'M'
  }
  if (value >= 1000) {
    return (value / 1000).toFixed(1) + 'k'
  }
  return value.toFixed(value % 1 === 0 ? 0 : 1)
}

// Calculate appropriate step for slider
function getStepForAttribute(attr: SchemaAttribute): number {
  const range = (attr.max_value ?? 100) - (attr.min_value ?? 0)
  if (range <= 10) return 0.1
  if (range <= 100) return 1
  if (range <= 1000) return 10
  if (range <= 10000) return 100
  return 1000
}

function updateTempFilter(key: string, value: string | null) {
  emit('update:temp-extended-filters', { ...props.tempExtendedFilters, [key]: value })
}

function updateRangeFilter(key: string, value: [number, number]) {
  const attr = props.schemaAttributes.find(a => a.key === key)
  const minDefault = attr?.min_value ?? 0
  const maxDefault = attr?.max_value ?? 100

  // If range is at defaults, clear the filter
  if (value[0] === minDefault && value[1] === maxDefault) {
    emit('update:temp-extended-filters', { ...props.tempExtendedFilters, [key]: null })
  } else {
    const rangeValue: RangeFilterValue = { min: value[0], max: value[1] }
    emit('update:temp-extended-filters', { ...props.tempExtendedFilters, [key]: rangeValue })
  }
}
</script>

<style scoped>
.filter-section {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.filter-section:last-child {
  border-bottom: none;
}
.filter-section-header {
  display: flex;
  align-items: center;
  padding: 12px 16px 8px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: rgba(var(--v-theme-on-surface), 0.6);
  background: rgba(var(--v-theme-surface-variant), 0.3);
}
.filter-section-content {
  padding: 12px 16px 16px;
}

.range-filter-item {
  margin-bottom: 16px;
}
.range-filter-item:last-child {
  margin-bottom: 0;
}
.range-filter-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
  font-size: 0.875rem;
}
.range-filter-value {
  font-size: 0.75rem;
  color: rgba(var(--v-theme-on-surface), 0.6);
  font-weight: 500;
}
</style>
