<template>
  <v-card class="mb-4">
    <v-card-text>
      <v-row align="center">
        <v-col cols="12" md="3">
          <v-text-field
            :model-value="searchQuery"
            :label="t('common.search')"
            prepend-inner-icon="mdi-magnify"
            clearable
            hide-details
            @update:model-value="handleSearchUpdate"
            @keyup.enter="$emit('load-entities')"
            @click:clear="handleSearchClear"
          ></v-text-field>
        </v-col>
        <v-col cols="12" md="2">
          <v-select
            :model-value="filters.category_id"
            :items="categories"
            item-title="name"
            item-value="id"
            :label="t('entities.category')"
            clearable
            hide-details
            @update:model-value="handleCategoryChange"
          ></v-select>
        </v-col>
        <v-col
          v-if="flags.entityHierarchyEnabled && currentEntityType?.supports_hierarchy"
          cols="12"
          md="2"
        >
          <v-autocomplete
            :model-value="filters.parent_id"
            :items="parentOptions"
            :loading="loadingParents"
            item-title="name"
            item-value="id"
            :label="t('entities.parent')"
            clearable
            hide-details
            @update:search="handleParentSearch"
            @update:model-value="handleParentChange"
          ></v-autocomplete>
        </v-col>
        <v-col cols="12" md="2">
          <v-select
            :model-value="filters.has_facets"
            :items="facetFilterOptions"
            item-title="label"
            item-value="value"
            :label="t('entities.withFacets')"
            hide-details
            @update:model-value="handleFacetFilterChange"
          ></v-select>
        </v-col>
        <v-col cols="auto">
          <v-btn
            variant="outlined"
            :color="hasExtendedFilters ? 'primary' : undefined"
            height="56"
            min-width="56"
            @click="$emit('open-extended-filters')"
          >
            <v-icon>mdi-tune</v-icon>
            <v-badge
              v-if="activeExtendedFilterCount > 0"
              :content="activeExtendedFilterCount"
              color="primary"
              floating
            ></v-badge>
          </v-btn>
        </v-col>
        <v-col cols="auto" class="d-flex align-center">
          <v-btn
            v-if="hasAnyFilters"
            variant="outlined"
            color="error"
            size="small"
            @click="$emit('clear-all-filters')"
          >
            <v-icon start>mdi-filter-off</v-icon>
            {{ t('entities.resetAllFilters') }}
          </v-btn>
        </v-col>
      </v-row>

      <!-- Active Extended Filters Display -->
      <v-row v-if="hasExtendedFilters" class="mt-2">
        <v-col cols="12">
          <div class="d-flex ga-2 flex-wrap">
            <v-chip
              v-for="(value, key) in allExtendedFilters"
              :key="key"
              closable
              size="small"
              color="primary"
              variant="tonal"
              @click:close="$emit('remove-extended-filter', key)"
            >
              <v-icon start size="small">mdi-filter</v-icon>
              {{ getFilterTitle(key) }}: {{ value }}
            </v-chip>
          </div>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { EntityFilters } from '@/composables/useEntitiesView'

interface Category {
  id: string
  name: string
}

interface ParentOption {
  id: string
  name: string
}

interface EntityTypeLocal {
  slug: string
  name: string
  supports_hierarchy?: boolean
}

interface Props {
  searchQuery: string
  filters: EntityFilters
  categories: Category[]
  parentOptions: ParentOption[]
  loadingParents: boolean
  facetFilterOptions: Array<{ label: string; value: string | boolean | null }>
  hasExtendedFilters: boolean
  activeExtendedFilterCount: number
  allExtendedFilters: Record<string, string>
  hasAnyFilters: boolean
  currentEntityType: EntityTypeLocal | null
  flags: { entityHierarchyEnabled?: boolean }
  getFilterTitle: (key: string) => string
}

interface Emits {
  (e: 'update:search-query', value: string): void
  (e: 'update:filters', value: EntityFilters): void
  (e: 'search-parents', query: string): void
  (e: 'load-entities'): void
  (e: 'open-extended-filters'): void
  (e: 'clear-all-filters'): void
  (e: 'remove-extended-filter', key: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const { t } = useI18n()

function handleSearchUpdate(value: string | null) {
  emit('update:search-query', value || '')
}

function handleSearchClear() {
  emit('update:search-query', '')
  emit('load-entities')
}

function handleCategoryChange(value: string | null) {
  emit('update:filters', { ...props.filters, category_id: value })
  emit('load-entities')
}

function handleParentChange(value: string | null) {
  emit('update:filters', { ...props.filters, parent_id: value })
  emit('load-entities')
}

function handleFacetFilterChange(value: boolean | null) {
  emit('update:filters', { ...props.filters, has_facets: value })
  emit('load-entities')
}

function handleParentSearch(query: string) {
  emit('search-parents', query)
}
</script>
