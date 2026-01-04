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
          <v-slider
            :model-value="minConfidence"
            :min="0"
            :max="100"
            :step="5"
            :label="$t('results.filters.minConfidence')"
            thumb-label="always"
            hide-details
            @update:model-value="$emit('update:minConfidence', $event)"
          >
            <template #thumb-label="{ modelValue }">{{ modelValue }}%</template>
          </v-slider>
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

        <v-col cols="12" md="8" class="d-flex align-center">
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
  minConfidence: number
  dateFrom: string | null
  dateTo: string | null
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
  'update:minConfidence': [value: number]
  'update:dateFrom': [value: string | null]
  'update:dateTo': [value: string | null]
  'search': []
  'clear-filters': []
}>()
</script>
