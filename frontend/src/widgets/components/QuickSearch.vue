<template>
  <BaseWidget
    :definition="definition"
    :config="config"
    :is-editing="isEditing"
  >
    <div class="quick-search-content">
      <!-- Search Input -->
      <v-text-field
        v-model="searchQuery"
        :placeholder="t('dashboard.searchPlaceholder')"
        density="compact"
        variant="outlined"
        hide-details
        prepend-inner-icon="mdi-magnify"
        :append-inner-icon="searchQuery ? 'mdi-close' : undefined"
        :loading="searching"
        :disabled="isEditing"
        class="mb-3"
        @keydown="handleSearchKeydown"
        @click:append-inner="clearSearch"
      />

      <!-- Results -->
      <div v-if="searching" class="d-flex justify-center py-4">
        <v-progress-circular indeterminate size="24" />
      </div>

      <v-list v-else-if="results.length > 0" density="compact" class="results-list" role="list">
        <v-list-item
          v-for="result in results"
          :key="result.id"
          class="px-2 clickable-item"
          :class="{ 'non-interactive': isEditing }"
          role="button"
          :tabindex="tabIndex"
          :aria-label="result.title"
          @click="navigateToResult(result)"
          @keydown="handleKeydownResult($event, result)"
        >
          <template #prepend>
            <v-icon :icon="getResultIcon(result.type)" size="small" color="primary" />
          </template>

          <v-list-item-title class="text-body-2 text-truncate">
            {{ result.title }}
          </v-list-item-title>
          <v-list-item-subtitle v-if="result.type_name" class="text-caption">
            {{ result.type_name }}
          </v-list-item-subtitle>
        </v-list-item>

        <!-- View All Results -->
        <v-list-item
          class="px-2 clickable-item"
          :class="{ 'non-interactive': isEditing }"
          role="button"
          :tabindex="tabIndex"
          :aria-label="t('dashboard.viewAllResults')"
          @click="navigateToFullSearch"
          @keydown="handleKeydownFullSearch($event)"
        >
          <v-list-item-title class="text-body-2 text-primary">
            {{ t('dashboard.viewAllResults') }}
          </v-list-item-title>
        </v-list-item>
      </v-list>

      <div v-else-if="hasSearched && !searching" class="text-center py-4 text-medium-emphasis">
        <v-icon size="24" class="mb-1">mdi-magnify-close</v-icon>
        <div class="text-caption">{{ t('common.noResults') }}</div>
      </div>

      <div v-else class="text-center py-4 text-medium-emphasis">
        <v-icon size="24" class="mb-1">mdi-magnify</v-icon>
        <div class="text-caption">{{ t('dashboard.searchHint') }}</div>
      </div>
    </div>
  </BaseWidget>
</template>

<script setup lang="ts">
/**
 * QuickSearch Widget - Search directly from the dashboard
 */

import { ref, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { dataApi } from '@/services/api'
import { handleKeyboardClick } from '../composables'
import BaseWidget from '../BaseWidget.vue'
import type { WidgetDefinition, WidgetConfig, QuickSearchResult } from '../types'

const props = defineProps<{
  definition: WidgetDefinition
  config?: WidgetConfig
  isEditing?: boolean
}>()

const { t } = useI18n()
const router = useRouter()
const searchQuery = ref('')
const searching = ref(false)
const results = ref<QuickSearchResult[]>([])
const hasSearched = ref(false)
const error = ref<string | null>(null)

// AbortController for cancelling in-flight requests
let abortController: AbortController | null = null

const isEditMode = computed(() => props.isEditing ?? false)
const tabIndex = computed(() => (isEditMode.value ? -1 : 0))

const search = async () => {
  if (!searchQuery.value.trim() || isEditMode.value) return

  // Cancel any pending request
  if (abortController) {
    abortController.abort()
  }
  abortController = new AbortController()

  searching.value = true
  hasSearched.value = true
  error.value = null

  try {
    const response = await dataApi.searchDocuments(
      { q: searchQuery.value.trim(), limit: 5 },
      abortController.signal
    )
    results.value = response.data?.items || []
  } catch (e) {
    // Ignore aborted requests (axios uses CanceledError)
    if (e instanceof Error && (e.name === 'AbortError' || e.name === 'CanceledError')) {
      return
    }
    error.value = e instanceof Error ? e.message : t('common.searchError')
    results.value = []
  } finally {
    searching.value = false
  }
}

// Cleanup on unmount
onUnmounted(() => {
  if (abortController) {
    abortController.abort()
    abortController = null
  }
})

const handleSearchKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter') {
    search()
  }
}

const getResultIcon = (type: string): string => {
  const iconMap: Record<string, string> = {
    entity: 'mdi-domain',
    document: 'mdi-file-document',
    facet: 'mdi-tag',
  }
  return iconMap[type] || 'mdi-magnify'
}

const navigateToResult = (result: QuickSearchResult) => {
  if (isEditMode.value) return

  if (result.type === 'entity' && result.type_slug && result.slug) {
    router.push({
      name: 'entity-detail',
      params: { typeSlug: result.type_slug, entitySlug: result.slug },
    })
  } else if (result.type === 'document') {
    // Navigate to documents list - no detail view available
    router.push({ path: '/documents' })
  } else {
    router.push({ path: '/smart-query', query: { q: searchQuery.value } })
  }
}

const navigateToFullSearch = () => {
  if (isEditMode.value || !searchQuery.value.trim()) return
  router.push({ path: '/smart-query', query: { q: searchQuery.value } })
}

const handleKeydownResult = (event: KeyboardEvent, result: QuickSearchResult) => {
  handleKeyboardClick(event, () => navigateToResult(result))
}

const handleKeydownFullSearch = (event: KeyboardEvent) => {
  handleKeyboardClick(event, () => navigateToFullSearch())
}

const clearSearch = () => {
  searchQuery.value = ''
  results.value = []
  hasSearched.value = false
}
</script>

<style scoped>
.quick-search-content {
  min-height: 100px;
}

.results-list {
  max-height: 200px;
  overflow-y: auto;
}

.clickable-item {
  cursor: pointer;
  border-radius: 8px;
  transition: background-color 0.2s ease;
}

.clickable-item:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.08);
}

.clickable-item:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.non-interactive {
  cursor: default;
  pointer-events: none;
}
</style>
