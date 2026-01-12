<template>
  <v-card variant="outlined" class="mb-4">
    <v-card-title class="text-subtitle-1 pb-2">
      <v-icon start color="primary">mdi-magnify</v-icon>
      {{ $t('categories.dataSourcesTab.directSelection') }}
    </v-card-title>
    <v-card-text>
      <v-autocomplete
        v-model="localSelectedSources"
        v-model:search="searchQuery"
        :items="searchResults"
        :loading="searching"
        :label="$t('categories.dataSourcesTab.searchSources')"
        item-title="name"
        item-value="id"
        return-object
        multiple
        chips
        closable-chips
        clearable
        hide-no-data
        variant="outlined"
        density="compact"
        prepend-inner-icon="mdi-magnify"
        :aria-label="$t('categories.dataSourcesTab.searchSources')"
        @update:search="handleSearch"
      >
        <template #chip="{ props: chipProps, item }">
          <v-chip v-bind="chipProps" closable color="primary" variant="tonal">
            {{ item.raw.name }}
          </v-chip>
        </template>
        <template #item="{ item, props: itemProps }">
          <v-list-item v-bind="itemProps">
            <template #prepend>
              <v-avatar :color="getStatusColor(item.raw.status)" size="32">
                <v-icon size="x-small">{{ getSourceTypeIcon(item.raw.source_type) }}</v-icon>
              </v-avatar>
            </template>
            <template #subtitle>
              <span class="text-truncate">{{ item.raw.base_url }}</span>
            </template>
            <template #append>
              <v-chip v-if="item.raw.is_assigned" size="x-small" color="success" variant="tonal">
                {{ $t('categories.dataSourcesTab.alreadyAssigned') }}
              </v-chip>
            </template>
          </v-list-item>
        </template>
      </v-autocomplete>

      <v-btn
        v-if="localSelectedSources.length > 0"
        class="mt-2"
        size="small"
        variant="tonal"
        color="primary"
        :loading="assigning"
        :disabled="localSelectedSources.every(s => s.is_assigned)"
        :aria-label="$t('categories.dataSourcesTab.assignSelected')"
        @click="handleAssign"
      >
        <v-icon start>mdi-link-plus</v-icon>
        {{ $t('categories.dataSourcesTab.assignSelected') }} ({{ assignableCount }})
      </v-btn>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useDebounce } from '@/composables/useDebounce'
import type { CategorySource } from '@/types/category'

interface Props {
  selectedSources?: CategorySource[]
  searchResults?: CategorySource[]
  searching?: boolean
  assigning?: boolean
  getStatusColor: (status?: string) => string
  getSourceTypeIcon: (type?: string) => string
}

interface Emits {
  (e: 'update:selectedSources', sources: CategorySource[]): void
  (e: 'search', query: string): void
  (e: 'assign', sources: CategorySource[]): void
}

const props = withDefaults(defineProps<Props>(), {
  selectedSources: () => [],
  searchResults: () => [],
  searching: false,
  assigning: false,
})

const emit = defineEmits<Emits>()

// === Constants ===
const SEARCH_DEBOUNCE_MS = 300

// Local state
const searchQuery = ref('')
const localSelectedSources = ref<CategorySource[]>([])

// Sync with props
watch(() => props.selectedSources, (newVal) => {
  localSelectedSources.value = newVal || []
}, { immediate: true })

watch(localSelectedSources, (newVal) => {
  emit('update:selectedSources', newVal)
})

// Computed
const assignableCount = computed(() =>
  localSelectedSources.value.filter(s => !s.is_assigned).length
)

// Methods
const { debouncedFn: handleSearch } = useDebounce((query: string) => {
  emit('search', query)
}, { delay: SEARCH_DEBOUNCE_MS })

const handleAssign = () => {
  emit('assign', localSelectedSources.value)
  localSelectedSources.value = []
}
</script>
