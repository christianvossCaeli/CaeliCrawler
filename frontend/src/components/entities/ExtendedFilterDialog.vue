<template>
  <v-dialog
    :model-value="modelValue"
    max-width="520"
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
          @click="$emit('update:model-value', false)"
          :title="t('common.close')"
          :aria-label="t('common.close')"
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
                    :model-value="tempExtendedFilters.country"
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
                    :model-value="tempExtendedFilters.admin_level_1"
                    :items="locationOptions.admin_level_1"
                    :label="t('entities.region')"
                    density="compact"
                    variant="outlined"
                    :disabled="!tempExtendedFilters.country"
                    clearable
                    hide-details
                    @update:model-value="updateTempFilter('admin_level_1', $event)"
                  ></v-select>
                </v-col>
                <v-col v-if="hasAttribute('admin_level_2')" cols="12" sm="4">
                  <v-select
                    :model-value="tempExtendedFilters.admin_level_2"
                    :items="locationOptions.admin_level_2"
                    :label="t('entities.district')"
                    density="compact"
                    variant="outlined"
                    :disabled="!tempExtendedFilters.admin_level_1"
                    clearable
                    hide-details
                    @update:model-value="updateTempFilter('admin_level_2', $event)"
                  ></v-select>
                </v-col>
              </v-row>
            </div>
          </div>

          <!-- Other Attributes Section -->
          <div v-if="nonLocationAttributes.length > 0" class="filter-section">
            <div class="filter-section-header">
              <v-icon size="small" class="mr-2">mdi-tag-multiple</v-icon>
              {{ t('entities.attributes') }}
            </div>
            <div class="filter-section-content">
              <v-row dense>
                <v-col
                  v-for="attr in nonLocationAttributes"
                  :key="attr.key"
                  cols="12"
                  sm="6"
                >
                  <v-select
                    :model-value="tempExtendedFilters[attr.key]"
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
import { useI18n } from 'vue-i18n'
import type { SchemaAttribute, LocationOptions } from '@/composables/useEntitiesView'

interface Props {
  modelValue: boolean
  tempExtendedFilters: Record<string, string | null>
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
  (e: 'update:temp-extended-filters', value: Record<string, string | null>): void
  (e: 'load-location-options'): void
  (e: 'load-attribute-values', key: string): void
  (e: 'apply-filters'): void
  (e: 'clear-filters'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const { t } = useI18n()

function updateTempFilter(key: string, value: string | null) {
  emit('update:temp-extended-filters', { ...props.tempExtendedFilters, [key]: value })
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
</style>
