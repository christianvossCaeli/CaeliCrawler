<template>
  <div class="smart-query-history-panel">
    <!-- Header -->
    <div class="smart-query-history-panel__header">
      <div class="smart-query-history-panel__title">
        <v-icon size="small" class="mr-1">mdi-history</v-icon>
        {{ t('smartQuery.history.title') }}
      </div>
      <div class="smart-query-history-panel__actions">
        <v-btn
          v-if="historyStore.history.length > 0"
          icon
          variant="text"
          size="x-small"
          :title="t('smartQuery.history.clear')"
          @click="handleClearHistory"
        >
          <v-icon size="small">mdi-delete-sweep</v-icon>
        </v-btn>
        <v-btn
          icon
          variant="text"
          size="x-small"
          :title="t('common.close')"
          @click="$emit('close')"
        >
          <v-icon size="small">mdi-close</v-icon>
        </v-btn>
      </div>
    </div>

    <!-- Filter Tabs -->
    <div class="smart-query-history-panel__tabs">
      <button
        :class="{ active: filter === 'all' }"
        @click="filter = 'all'"
      >
        {{ t('smartQuery.history.all') }}
      </button>
      <button
        :class="{ active: filter === 'favorites' }"
        @click="filter = 'favorites'"
      >
        <v-icon size="x-small" class="mr-1">mdi-star</v-icon>
        {{ t('smartQuery.history.favorites') }}
      </button>
    </div>

    <!-- Search + Filters -->
    <div class="smart-query-history-panel__controls">
      <v-text-field
        v-model="searchQuery"
        density="compact"
        variant="outlined"
        hide-details
        clearable
        :placeholder="t('smartQuery.history.searchPlaceholder')"
        prepend-inner-icon="mdi-magnify"
        class="history-search"
      />
      <v-select
        v-model="operationFilter"
        :items="operationFilterOptions"
        item-title="title"
        item-value="value"
        density="compact"
        variant="outlined"
        hide-details
        :label="t('smartQuery.history.typeFilter')"
        class="history-filter"
      />
      <v-btn
        icon
        variant="text"
        size="small"
        :color="wrapQueries ? 'primary' : undefined"
        :title="t('smartQuery.history.wrapLines')"
        @click="wrapQueries = !wrapQueries"
      >
        <v-icon size="18">mdi-format-line-spacing</v-icon>
      </v-btn>
    </div>

    <!-- History List -->
    <div class="smart-query-history-panel__list">
      <div v-if="historyStore.isLoading" class="smart-query-history-panel__loading-overlay">
        <v-progress-circular indeterminate size="24" />
      </div>
      <div
        v-if="filteredHistory.length === 0 && !historyStore.isLoading"
        class="smart-query-history-panel__empty"
      >
        <v-icon size="large" color="grey-lighten-1">mdi-history</v-icon>
        <p>{{ emptyMessage }}</p>
      </div>

      <div
        v-for="item in filteredHistory"
        :key="item.id"
        class="history-item"
        :class="{ 'history-item--wrap': wrapQueries }"
        @click="handleRerun(item)"
      >
        <div class="history-item__content">
          <div class="history-item__query">
            {{ item.display_name || item.command_text }}
          </div>
          <div class="history-item__meta">
            <v-chip
              size="x-small"
              :color="getOperationColor(item.operation_type)"
              variant="tonal"
              class="mr-1"
            >
              {{ getOperationLabel(item.operation_type) }}
            </v-chip>
            <span class="history-item__time">
              {{ formatRelativeTime(item.last_executed_at) }}
            </span>
            <span v-if="item.execution_count > 1" class="history-item__count">
              {{ item.execution_count }}x
            </span>
            <v-icon
              v-if="!item.was_successful"
              size="x-small"
              color="error"
              class="ml-1"
              :title="t('smartQuery.history.failed')"
            >
              mdi-alert-circle
            </v-icon>
          </div>
        </div>
        <div class="history-item__actions">
          <v-btn
            icon
            variant="text"
            size="x-small"
            :color="item.is_favorite ? 'warning' : 'default'"
            :title="item.is_favorite
              ? t('smartQuery.history.unfavorite')
              : t('smartQuery.history.favorite')"
            @click.stop="handleToggleFavorite(item.id)"
          >
            <v-icon size="small">
              {{ item.is_favorite ? 'mdi-star' : 'mdi-star-outline' }}
            </v-icon>
          </v-btn>
          <v-btn
            icon
            variant="text"
            size="x-small"
            color="primary"
            :title="t('smartQuery.history.rerun')"
            @click.stop="handleRerun(item)"
          >
            <v-icon size="small">mdi-play</v-icon>
          </v-btn>
          <v-btn
            icon
            variant="text"
            size="x-small"
            :title="t('smartQuery.history.delete')"
            @click.stop="handleRemove(item.id)"
          >
            <v-icon size="small">mdi-close</v-icon>
          </v-btn>
        </div>
      </div>
    </div>

    <!-- Clear History Dialog -->
    <v-dialog v-model="showClearDialog" max-width="400">
      <v-card>
        <v-card-title>{{ t('smartQuery.history.clearTitle') }}</v-card-title>
        <v-card-text>
          {{ t('smartQuery.history.clearConfirm') }}
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showClearDialog = false">
            {{ t('common.cancel') }}
          </v-btn>
          <v-btn color="error" variant="tonal" @click="confirmClearHistory">
            {{ t('smartQuery.history.clear') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSmartQueryHistoryStore, type SmartQueryOperation } from '@/stores/smartQueryHistory'
import { useSnackbar } from '@/composables/useSnackbar'

const emit = defineEmits<{
  close: []
  rerun: [command: string, interpretation: Record<string, unknown>]
}>()
const { t, locale } = useI18n()
const historyStore = useSmartQueryHistoryStore()
const { showSuccess, showError } = useSnackbar()

const filter = ref<'all' | 'favorites'>('all')
const showClearDialog = ref(false)
const searchQuery = ref('')
const operationFilter = ref('all')
const wrapQueries = ref(false)

const filteredHistory = computed(() => {
  const searchValue = searchQuery.value.trim().toLowerCase()
  const sorted = [...historyStore.history].sort((a, b) =>
    new Date(b.last_executed_at).getTime() - new Date(a.last_executed_at).getTime()
  )

  return sorted
    .filter(item => filter.value !== 'favorites' || item.is_favorite)
    .filter(item => operationFilter.value === 'all' || item.operation_type === operationFilter.value)
    .filter(item => {
      if (!searchValue) return true
      const target = (item.display_name || item.command_text || '').toLowerCase()
      return target.includes(searchValue)
    })
})

// Operation type labels and colors
const operationLabels: Record<string, string> = {
  start_crawl: 'Crawl',
  create_category_setup: 'Setup',
  create_entity: 'Entity',
  create_entity_type: 'Type',
  create_facet: 'Facet',
  create_relation: 'Relation',
  fetch_and_create_from_api: 'Import',
  discover_sources: 'Discovery',
  combined: 'Combined',
  other: 'Other',
}

const operationFilterOptions = computed(() => {
  const baseOptions = Object.keys(operationLabels).map((type) => ({
    value: type,
    title: operationLabels[type],
  }))
  const extraTypes = [...new Set(historyStore.history.map(item => item.operation_type))]
    .filter((type) => !operationLabels[type])
    .sort()
  const extraOptions = extraTypes.map((type) => ({
    value: type,
    title: type,
  }))

  return [
    { value: 'all', title: t('smartQuery.history.allTypes') },
    ...baseOptions,
    ...extraOptions,
  ]
})

const operationColors: Record<string, string> = {
  start_crawl: 'blue',
  create_category_setup: 'purple',
  create_entity: 'green',
  create_entity_type: 'teal',
  create_facet: 'orange',
  create_relation: 'cyan',
  fetch_and_create_from_api: 'indigo',
  discover_sources: 'deep-purple',
  combined: 'grey',
  other: 'grey',
}

const emptyMessage = computed(() => {
  if (filter.value === 'favorites' && !searchQuery.value.trim() && operationFilter.value === 'all') {
    return t('smartQuery.history.noFavorites')
  }
  if (searchQuery.value.trim() || operationFilter.value !== 'all') {
    return t('smartQuery.history.noResults')
  }
  return t('smartQuery.history.empty')
})

function getOperationLabel(type: string): string {
  return operationLabels[type] || type
}

function getOperationColor(type: string): string {
  return operationColors[type] || 'grey'
}

function formatRelativeTime(dateStr: string): string {
  const now = new Date()
  const then = new Date(dateStr)
  const diffMs = now.getTime() - then.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) {
    return t('smartQuery.history.justNow')
  } else if (diffMins < 60) {
    return t('smartQuery.history.minutesAgo', { n: diffMins })
  } else if (diffHours < 24) {
    return t('smartQuery.history.hoursAgo', { n: diffHours })
  } else if (diffDays < 7) {
    return t('smartQuery.history.daysAgo', { n: diffDays })
  } else {
    return then.toLocaleDateString(locale.value === 'de' ? 'de-DE' : 'en-US')
  }
}

async function handleRerun(item: SmartQueryOperation) {
  emit('rerun', item.command_text, item.interpretation)
}

async function handleToggleFavorite(id: string) {
  const newState = await historyStore.toggleFavorite(id)
  if (newState) {
    showSuccess(t('smartQuery.history.addedToFavorites'))
  } else {
    showSuccess(t('smartQuery.history.removedFromFavorites'))
  }
}

async function handleRemove(id: string) {
  const success = await historyStore.deleteFromHistory(id)
  if (success) {
    showSuccess(t('smartQuery.history.deleted'))
  } else {
    showError(t('smartQuery.history.deleteError'))
  }
}

function handleClearHistory() {
  showClearDialog.value = true
}

async function confirmClearHistory() {
  const success = await historyStore.clearHistory(false)
  showClearDialog.value = false
  if (success) {
    showSuccess(t('smartQuery.history.cleared'))
  } else {
    showError(t('smartQuery.history.clearError'))
  }
}

onMounted(() => {
  historyStore.loadHistory()
})
</script>

<style scoped lang="scss">
.smart-query-history-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: rgb(var(--v-theme-surface));
  border-radius: 8px;
  overflow: hidden;

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  }

  &__title {
    display: flex;
    align-items: center;
    font-weight: 500;
    font-size: 0.875rem;
  }

  &__actions {
    display: flex;
    gap: 4px;
  }

  &__tabs {
    display: flex;
    border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));

    button {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 8px 12px;
      font-size: 0.75rem;
      font-weight: 500;
      color: rgba(var(--v-theme-on-surface), 0.7);
      background: transparent;
      border: none;
      cursor: pointer;
      transition: all 0.2s ease;

      &:hover {
        background: rgba(var(--v-theme-primary), 0.05);
      }

      &.active {
        color: rgb(var(--v-theme-primary));
        border-bottom: 2px solid rgb(var(--v-theme-primary));
      }
    }
  }

  &__controls {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    padding: 8px 12px;
    border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  }

  &__list {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
    position: relative;
  }

  &__empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 150px;
    color: rgba(var(--v-theme-on-surface), 0.5);
    text-align: center;

    p {
      margin-top: 8px;
      font-size: 0.8rem;
    }
  }

  &__loading-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(var(--v-theme-surface), 0.6);
    z-index: 1;
  }
}

.history-search {
  flex: 1 1 200px;
  min-width: 180px;
}

.history-filter {
  flex: 0 1 160px;
  min-width: 140px;
}

.history-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 10px 12px;
  margin-bottom: 4px;
  background: rgba(var(--v-theme-surface-variant), 0.3);
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s ease;

  &:hover {
    background: rgba(var(--v-theme-primary), 0.08);
  }

  &__content {
    flex: 1;
    min-width: 0;
  }

  &__query {
    font-size: 0.8rem;
    font-weight: 500;
    color: rgb(var(--v-theme-on-surface));
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 4px;
  }

  &--wrap .history-item__query {
    white-space: normal;
    overflow: visible;
    text-overflow: unset;
    overflow-wrap: anywhere;
    line-height: 1.35;
  }

  &__meta {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
    font-size: 0.7rem;
    color: rgba(var(--v-theme-on-surface), 0.6);
  }

  &__time {
    // Default styling
  }

  &__count {
    padding: 1px 6px;
    background: rgba(var(--v-theme-primary), 0.1);
    border-radius: 10px;
    font-size: 0.65rem;
  }

  &__actions {
    display: flex;
    gap: 2px;
    margin-left: 8px;
    opacity: 0;
    transition: opacity 0.2s ease;
  }

  &:hover &__actions {
    opacity: 1;
  }
}
</style>
