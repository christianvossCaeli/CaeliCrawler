<script setup lang="ts">
/**
 * SavedSearches Widget - Shows user's saved/recent searches
 * Uses localStorage to persist searches across sessions with proper error handling
 */

import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { handleKeyboardClick } from '../composables'
import BaseWidget from '../BaseWidget.vue'
import WidgetEmptyState from './WidgetEmptyState.vue'
import type { WidgetDefinition, WidgetConfig, SavedSearch } from '../types'
import { MAX_SAVED_SEARCHES, WIDGET_DEFAULT_LIMIT } from '../types'

const STORAGE_KEY = 'caeli-saved-searches'

const props = defineProps<{
  definition: WidgetDefinition
  config?: WidgetConfig
  isEditing?: boolean
}>()

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const searches = ref<SavedSearch[]>([])
const storageAvailable = ref(true)
const storageError = ref<string | null>(null)

/**
 * Check if localStorage is available
 */
const checkStorageAvailability = (): boolean => {
  try {
    const testKey = '__storage_test__'
    localStorage.setItem(testKey, testKey)
    localStorage.removeItem(testKey)
    return true
  } catch {
    return false
  }
}

/**
 * Validate saved search data structure
 */
const isValidSavedSearch = (item: unknown): item is SavedSearch => {
  if (typeof item !== 'object' || item === null) return false
  const s = item as Record<string, unknown>
  return (
    typeof s.id === 'string' &&
    typeof s.query === 'string' &&
    typeof s.createdAt === 'string' &&
    typeof s.lastUsed === 'string' &&
    typeof s.useCount === 'number' &&
    typeof s.isPinned === 'boolean'
  )
}

/**
 * Load searches from localStorage with validation
 */
const loadSearches = () => {
  if (!storageAvailable.value) return

  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      // Validate data structure
      if (Array.isArray(parsed)) {
        searches.value = parsed.filter(isValidSavedSearch)
      } else {
        // Invalid data, reset
        searches.value = []
        saveSearches()
      }
    }
    storageError.value = null
  } catch (e) {
    storageError.value = t('dashboard.storageError')
    searches.value = []
  }
}

/**
 * Save searches to localStorage with error handling
 * Shows warnings when data is truncated or storage is unavailable
 */
const saveSearches = () => {
  if (!storageAvailable.value) {
    // Warn user that changes won't be persisted
    storageError.value = t('dashboard.storageUnavailable')
    return
  }

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(searches.value))
    storageError.value = null
  } catch (e) {
    // Storage full or disabled
    if (e instanceof Error && e.name === 'QuotaExceededError') {
      // Try to free up space by removing oldest non-pinned searches
      const pinned = searches.value.filter(s => s.isPinned)
      const unpinned = searches.value.filter(s => !s.isPinned)
      const removedCount = unpinned.length - Math.floor(unpinned.length / 2)
      if (unpinned.length > 2) {
        searches.value = [...pinned, ...unpinned.slice(0, Math.floor(unpinned.length / 2))]
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(searches.value))
          // Warn user that some searches were removed
          storageError.value = t('dashboard.storageQuotaWarning', { count: removedCount })
          return
        } catch {
          // Still failing, show error
        }
      }
    }
    storageError.value = t('dashboard.storageSaveError')
  }
}

/**
 * Add or update a search
 */
const trackSearch = (query: string) => {
  if (!query.trim()) return

  const existing = searches.value.find(s => s.query === query)
  if (existing) {
    existing.lastUsed = new Date().toISOString()
    existing.useCount++
  } else {
    searches.value.unshift({
      id: Date.now().toString(),
      query,
      createdAt: new Date().toISOString(),
      lastUsed: new Date().toISOString(),
      useCount: 1,
      isPinned: false,
    })
    // Keep only MAX_SAVED_SEARCHES (but keep pinned ones)
    const pinned = searches.value.filter(s => s.isPinned)
    const unpinned = searches.value.filter(s => !s.isPinned).slice(0, MAX_SAVED_SEARCHES - pinned.length)
    searches.value = [...pinned, ...unpinned]
  }
  saveSearches()
}

// Watch for search route changes to auto-track searches
watch(
  () => route.query.q,
  (newQuery) => {
    if (typeof newQuery === 'string' && newQuery.trim()) {
      trackSearch(newQuery)
    }
  }
)

onMounted(() => {
  // Check storage availability first
  storageAvailable.value = checkStorageAvailability()
  if (!storageAvailable.value) {
    storageError.value = t('dashboard.storageUnavailable')
  }

  loadSearches()
  // Track current search if on search page
  if (route.path === '/search' && typeof route.query.q === 'string') {
    trackSearch(route.query.q)
  }
})

const isEditMode = computed(() => props.isEditing ?? false)
const tabIndex = computed(() => (isEditMode.value ? -1 : 0))

// Sort: pinned first, then by lastUsed
const sortedSearches = computed(() => {
  return [...searches.value].sort((a, b) => {
    if (a.isPinned && !b.isPinned) return -1
    if (!a.isPinned && b.isPinned) return 1
    return new Date(b.lastUsed).getTime() - new Date(a.lastUsed).getTime()
  }).slice(0, WIDGET_DEFAULT_LIMIT)
})

const togglePin = (search: SavedSearch, event: Event) => {
  event.stopPropagation()
  if (isEditMode.value) return
  search.isPinned = !search.isPinned
  saveSearches()
}

const removeSearch = (search: SavedSearch, event: Event) => {
  event.stopPropagation()
  if (isEditMode.value) return
  searches.value = searches.value.filter(s => s.id !== search.id)
  saveSearches()
}

const navigateToSearch = (search: SavedSearch) => {
  if (isEditMode.value) return
  search.lastUsed = new Date().toISOString()
  search.useCount++
  saveSearches()
  router.push({ path: '/search', query: { q: search.query } })
}

const navigateToSearchPage = () => {
  if (isEditMode.value) return
  router.push({ path: '/search' })
}

const handleKeydownSearch = (event: KeyboardEvent, search: SavedSearch) => {
  handleKeyboardClick(event, () => navigateToSearch(search))
}

const handleKeydownViewAll = (event: KeyboardEvent) => {
  handleKeyboardClick(event, () => navigateToSearchPage())
}

const formatTime = (timestamp: string): string => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return t('common.justNow')
  if (diff < 3600000) return t('common.minutesAgo', { n: Math.floor(diff / 60000) })
  if (diff < 86400000) return t('common.hoursAgo', { n: Math.floor(diff / 3600000) })
  return t('common.daysAgo', { n: Math.floor(diff / 86400000) })
}
</script>

<template>
  <BaseWidget
    :definition="definition"
    :config="config"
    :is-editing="isEditing"
  >
    <!-- Storage Error Alert -->
    <v-alert
      v-if="storageError"
      type="warning"
      density="compact"
      variant="tonal"
      class="mb-2"
      closable
      @click:close="storageError = null"
    >
      {{ storageError }}
    </v-alert>

    <v-list v-if="sortedSearches.length > 0" density="compact" class="searches-list" role="list">
      <v-list-item
        v-for="search in sortedSearches"
        :key="search.id"
        class="px-2 clickable-item"
        :class="{ 'non-interactive': isEditing }"
        role="button"
        :tabindex="tabIndex"
        :aria-label="search.query"
        @click="navigateToSearch(search)"
        @keydown="handleKeydownSearch($event, search)"
      >
        <template #prepend>
          <v-icon
            :icon="search.isPinned ? 'mdi-pin' : 'mdi-magnify'"
            :color="search.isPinned ? 'primary' : undefined"
            size="small"
          />
        </template>

        <v-list-item-title class="text-body-2 text-truncate">
          {{ search.query }}
        </v-list-item-title>
        <v-list-item-subtitle class="text-caption">
          {{ formatTime(search.lastUsed) }}
          <span v-if="search.useCount > 1" class="text-medium-emphasis ml-1">
            ({{ search.useCount }}x)
          </span>
        </v-list-item-subtitle>

        <template #append>
          <div class="d-flex">
            <v-btn
              icon
              size="x-small"
              variant="text"
              :color="search.isPinned ? 'primary' : undefined"
              :aria-label="search.isPinned ? t('common.unpin') : t('common.pin')"
              @click="togglePin(search, $event)"
            >
              <v-icon size="small">{{ search.isPinned ? 'mdi-pin-off' : 'mdi-pin' }}</v-icon>
            </v-btn>
            <v-btn
              icon
              size="x-small"
              variant="text"
              :aria-label="t('common.remove')"
              @click="removeSearch(search, $event)"
            >
              <v-icon size="small">mdi-close</v-icon>
            </v-btn>
          </div>
        </template>
      </v-list-item>
    </v-list>

    <WidgetEmptyState
      v-else
      icon="mdi-magnify"
      :message="t('dashboard.noSavedSearches')"
      :hint="t('dashboard.savedSearchesHint')"
    />

    <!-- View All / New Search Link -->
    <div
      class="text-center mt-2 view-all-link"
      :class="{ 'non-interactive': isEditing }"
      role="button"
      :tabindex="tabIndex"
      :aria-label="t('dashboard.newSearch')"
      @click="navigateToSearchPage"
      @keydown="handleKeydownViewAll($event)"
    >
      <span class="text-caption text-primary">
        {{ t('dashboard.newSearch') }}
      </span>
    </div>
  </BaseWidget>
</template>

<style scoped>
.searches-list {
  max-height: 280px;
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

.view-all-link {
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.view-all-link:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.08);
}

.view-all-link:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.non-interactive {
  cursor: default;
  pointer-events: none;
}
</style>
