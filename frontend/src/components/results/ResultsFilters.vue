<template>
  <v-card class="mb-4">
    <v-card-text>
      <!-- Primary Filters Row -->
      <v-row align="center">
        <v-col cols="12" md="3">
          <v-text-field
            :model-value="searchQuery"
            prepend-inner-icon="mdi-magnify"
            :label="$t('results.filters.fulltext')"
            clearable
            hide-details
            :placeholder="$t('results.filters.fulltextPlaceholder')"
            @update:model-value="$emit('update:searchQuery', $event)"
            @keyup.enter="$emit('search')"
          />
        </v-col>

        <v-col v-if="showLocationFilter" cols="6" md="2">
          <v-autocomplete
            :model-value="locationFilter"
            :items="locations"
            :label="$t('results.filters.location')"
            clearable
            hide-details
            @update:model-value="$emit('update:locationFilter', $event)"
          />
        </v-col>

        <v-col cols="6" md="2">
          <v-select
            :model-value="extractionTypeFilter"
            :items="extractionTypes"
            :label="$t('results.filters.analysisType')"
            clearable
            hide-details
            @update:model-value="$emit('update:extractionTypeFilter', $event)"
          />
        </v-col>

        <v-col cols="6" md="2">
          <v-select
            :model-value="categoryFilter"
            :items="categories"
            item-title="name"
            item-value="id"
            :label="$t('results.filters.category')"
            clearable
            hide-details
            @update:model-value="$emit('update:categoryFilter', $event)"
          />
        </v-col>

        <v-col cols="6" md="3">
          <div class="confidence-range-filter">
            <div class="confidence-range-label">
              <span>{{ $t('results.filters.confidence') }}</span>
              <span class="confidence-range-value">{{ confidenceRange[0] }}% - {{ confidenceRange[1] }}%</span>
            </div>
            <v-range-slider
              :model-value="confidenceRange"
              :min="0"
              :max="100"
              :step="5"
              density="compact"
              hide-details
              thumb-label
              color="primary"
              @update:model-value="$emit('update:confidenceRange', $event)"
            >
              <template #thumb-label="{ modelValue }">{{ modelValue }}%</template>
            </v-range-slider>
          </div>
        </v-col>
      </v-row>

      <!-- Secondary Filters Row -->
      <v-row align="center" class="mt-2">
        <v-col cols="6" md="2">
          <v-text-field
            :model-value="dateFrom"
            type="date"
            :label="$t('results.filters.dateFrom')"
            clearable
            hide-details
            @update:model-value="$emit('update:dateFrom', $event)"
          />
        </v-col>

        <v-col cols="6" md="2">
          <v-text-field
            :model-value="dateTo"
            type="date"
            :label="$t('results.filters.dateTo')"
            clearable
            hide-details
            @update:model-value="$emit('update:dateTo', $event)"
          />
        </v-col>

        <v-col cols="6" md="3">
          <v-checkbox
            :model-value="showRejected"
            :label="$t('results.filters.showRejected')"
            hide-details
            density="compact"
            color="error"
            @update:model-value="$emit('update:show-rejected', $event)"
          />
        </v-col>

        <v-col cols="6" md="5" class="d-flex align-center justify-end">
          <v-btn
            v-if="hasActiveFilters"
            variant="tonal"
            color="primary"
            size="small"
            @click="$emit('clear-filters')"
          >
            <v-icon size="small" class="mr-1">mdi-filter-off</v-icon>
            {{ $t('results.filters.resetFilters') }}
          </v-btn>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
/**
 * ResultsFilters - Filter card for the Results view
 *
 * Provides fulltext search, location, type, category, confidence,
 * and date range filters.
 */
import type { CategoryOption } from '@/composables/results'

defineProps<{
  searchQuery: string
  locationFilter: string | null
  extractionTypeFilter: string | null
  categoryFilter: string | null
  confidenceRange: [number, number]
  dateFrom: string | null
  dateTo: string | null
  showRejected: boolean
  locations: string[]
  categories: CategoryOption[]
  extractionTypes: string[]
  showLocationFilter: boolean
  hasActiveFilters: boolean
}>()

defineEmits<{
  'update:searchQuery': [value: string]
  'update:locationFilter': [value: string | null]
  'update:extractionTypeFilter': [value: string | null]
  'update:categoryFilter': [value: string | null]
  'update:confidenceRange': [value: [number, number]]
  'update:dateFrom': [value: string | null]
  'update:dateTo': [value: string | null]
  'update:show-rejected': [value: boolean]
  'search': []
  'clear-filters': []
}>()
</script>

<style scoped>
.confidence-range-filter {
  padding-top: 4px;
}
.confidence-range-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
  font-size: 0.875rem;
}
.confidence-range-value {
  font-size: 0.75rem;
  color: rgba(var(--v-theme-on-surface), 0.6);
  font-weight: 500;
}
</style>
