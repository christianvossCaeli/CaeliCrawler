<template>
  <v-card :variant="variant" class="filter-card">
    <v-card-text :class="compact ? 'pa-3' : 'pa-4'">
      <div class="d-flex align-center flex-wrap ga-3">
        <!-- Search Field -->
        <v-text-field
          v-if="showSearch"
          v-model="localSearch"
          :label="searchLabel"
          :placeholder="searchPlaceholder"
          variant="outlined"
          density="compact"
          hide-details
          clearable
          prepend-inner-icon="mdi-magnify"
          :style="{ maxWidth: searchWidth }"
          @update:model-value="onSearchChange"
        />

        <!-- Filter Slots -->
        <slot name="filters" />

        <v-spacer />

        <!-- Action Buttons -->
        <div class="d-flex align-center ga-2">
          <slot name="actions" />

          <!-- Reset Button -->
          <v-btn
            v-if="showReset && hasActiveFilters"
            variant="tonal"
            size="small"
            @click="$emit('reset')"
          >
            <v-icon start>mdi-filter-remove</v-icon>
            {{ resetLabel }}
          </v-btn>

          <!-- Refresh Button -->
          <v-btn
            v-if="showRefresh"
            variant="tonal"
            size="small"
            :loading="loading"
            @click="$emit('refresh')"
          >
            <v-icon>mdi-refresh</v-icon>
          </v-btn>
        </div>
      </div>

      <!-- Active Filters Display -->
      <div v-if="activeFilters.length > 0 && showActiveFilters" class="mt-3">
        <v-chip
          v-for="(filter, index) in activeFilters"
          :key="index"
          closable
          size="small"
          class="mr-2 mb-1"
          @click:close="$emit('remove-filter', filter)"
        >
          <span class="text-medium-emphasis mr-1">{{ filter.label }}:</span>
          {{ filter.value }}
        </v-chip>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useDebounce, DEBOUNCE_DELAYS } from '@/composables/useDebounce'

export interface ActiveFilter {
  key: string
  label: string
  value: string
}

const props = withDefaults(defineProps<{
  /** Current search query (v-model) */
  search?: string
  /** Show search field */
  showSearch?: boolean
  /** Search field label */
  searchLabel?: string
  /** Search field placeholder */
  searchPlaceholder?: string
  /** Search field max width */
  searchWidth?: string
  /** Show reset button */
  showReset?: boolean
  /** Reset button label */
  resetLabel?: string
  /** Show refresh button */
  showRefresh?: boolean
  /** Loading state for refresh */
  loading?: boolean
  /** Card variant */
  variant?: 'flat' | 'elevated' | 'tonal' | 'outlined' | 'text' | 'plain'
  /** Compact mode (smaller padding) */
  compact?: boolean
  /** List of active filters to display as chips */
  activeFilters?: ActiveFilter[]
  /** Show active filters chips */
  showActiveFilters?: boolean
  /** Debounce delay for search */
  debounceDelay?: number
}>(), {
  search: '',
  showSearch: true,
  searchLabel: 'Suche',
  searchPlaceholder: 'Suchen...',
  searchWidth: '300px',
  showReset: true,
  resetLabel: 'Filter zurücksetzen',
  showRefresh: false,
  loading: false,
  variant: 'flat',
  compact: false,
  activeFilters: () => [],
  showActiveFilters: true,
  debounceDelay: DEBOUNCE_DELAYS.SEARCH,
})

const emit = defineEmits<{
  (e: 'update:search', value: string): void
  (e: 'search', value: string): void
  (e: 'reset'): void
  (e: 'refresh'): void
  (e: 'remove-filter', filter: ActiveFilter): void
}>()

const localSearch = ref(props.search)

// Debounced search
const { debouncedFn: debouncedSearch } = useDebounce(
  (value: string) => {
    emit('update:search', value)
    emit('search', value)
  },
  { delay: props.debounceDelay }
)

function onSearchChange(value: string | null) {
  const searchValue = value || ''
  localSearch.value = searchValue
  debouncedSearch(searchValue)
}

// Sync with prop changes
watch(() => props.search, (newVal) => {
  if (newVal !== localSearch.value) {
    localSearch.value = newVal
  }
})

// Check if any filters are active
const hasActiveFilters = computed(() => {
  return props.activeFilters.length > 0 || localSearch.value.length > 0
})
</script>

<style scoped>
.filter-card {
  background: rgb(var(--v-theme-surface));
}
</style>
