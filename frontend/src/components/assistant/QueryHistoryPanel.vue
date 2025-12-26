<template>
  <div class="query-history-panel">
    <!-- Header -->
    <div class="query-history-panel__header">
      <div class="query-history-panel__title">
        <v-icon size="small" class="mr-1">mdi-history</v-icon>
        {{ t('assistant.queryHistory.title') }}
      </div>
      <div class="query-history-panel__actions">
        <v-btn
          v-if="queryHistory.length > 0"
          icon
          variant="text"
          size="x-small"
          :title="t('assistant.queryHistory.clear')"
          @click="handleClearHistory"
        >
          <v-icon size="small">mdi-delete-sweep</v-icon>
        </v-btn>
        <v-btn
          icon
          variant="text"
          size="x-small"
          :title="t('assistant.close')"
          @click="$emit('close')"
        >
          <v-icon size="small">mdi-close</v-icon>
        </v-btn>
      </div>
    </div>

    <!-- Filter Tabs -->
    <div class="query-history-panel__tabs">
      <button
        :class="{ active: filter === 'all' }"
        @click="filter = 'all'"
      >
        {{ t('assistant.queryHistory.all') }}
      </button>
      <button
        :class="{ active: filter === 'favorites' }"
        @click="filter = 'favorites'"
      >
        <v-icon size="x-small" class="mr-1">mdi-star</v-icon>
        {{ t('assistant.queryHistory.favorites') }}
      </button>
    </div>

    <!-- History List -->
    <div class="query-history-panel__list">
      <div
        v-if="filteredHistory.length === 0"
        class="query-history-panel__empty"
      >
        <v-icon size="large" color="grey-lighten-1">mdi-history</v-icon>
        <p>{{ filter === 'favorites'
          ? t('assistant.queryHistory.noFavorites')
          : t('assistant.queryHistory.empty')
        }}</p>
      </div>

      <div
        v-for="item in filteredHistory"
        :key="item.id"
        class="query-history-item"
        @click="handleRerun(item)"
      >
        <div class="query-history-item__content">
          <div class="query-history-item__query">{{ item.query }}</div>
          <div class="query-history-item__meta">
            <span class="query-history-item__time">
              {{ formatRelativeTime(item.timestamp) }}
            </span>
            <span v-if="item.resultCount !== undefined" class="query-history-item__count">
              {{ item.resultCount }} {{ t('assistant.queryHistory.results') }}
            </span>
            <v-chip
              v-if="item.entityType"
              size="x-small"
              variant="outlined"
              class="ml-1"
            >
              {{ item.entityType }}
            </v-chip>
          </div>
        </div>
        <div class="query-history-item__actions">
          <v-btn
            icon
            variant="text"
            size="x-small"
            :color="item.isFavorite ? 'warning' : 'default'"
            :title="item.isFavorite
              ? t('assistant.queryHistory.unfavorite')
              : t('assistant.queryHistory.favorite')"
            @click.stop="handleToggleFavorite(item.id)"
          >
            <v-icon size="small">
              {{ item.isFavorite ? 'mdi-star' : 'mdi-star-outline' }}
            </v-icon>
          </v-btn>
          <v-btn
            icon
            variant="text"
            size="x-small"
            :title="t('assistant.queryHistory.remove')"
            @click.stop="handleRemove(item.id)"
          >
            <v-icon size="small">mdi-close</v-icon>
          </v-btn>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { QueryHistoryItem } from '@/composables/useAssistant'

const props = defineProps<{
  queryHistory: QueryHistoryItem[]
}>()

const emit = defineEmits<{
  close: []
  rerun: [query: string]
  'toggle-favorite': [id: string]
  remove: [id: string]
  clear: []
}>()

const { t, locale } = useI18n()

const filter = ref<'all' | 'favorites'>('all')

const filteredHistory = computed(() => {
  const sorted = [...props.queryHistory].sort((a, b) =>
    new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  )

  if (filter.value === 'favorites') {
    return sorted.filter(item => item.isFavorite)
  }
  return sorted
})

function formatRelativeTime(date: Date): string {
  const now = new Date()
  const then = new Date(date)
  const diffMs = now.getTime() - then.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) {
    return t('assistant.queryHistory.justNow')
  } else if (diffMins < 60) {
    return t('assistant.queryHistory.minutesAgo', { n: diffMins })
  } else if (diffHours < 24) {
    return t('assistant.queryHistory.hoursAgo', { n: diffHours })
  } else if (diffDays < 7) {
    return t('assistant.queryHistory.daysAgo', { n: diffDays })
  } else {
    return then.toLocaleDateString(locale.value === 'de' ? 'de-DE' : 'en-US')
  }
}

function handleRerun(item: QueryHistoryItem) {
  emit('rerun', item.query)
}

function handleToggleFavorite(id: string) {
  emit('toggle-favorite', id)
}

function handleRemove(id: string) {
  emit('remove', id)
}

function handleClearHistory() {
  emit('clear')
}
</script>

<style scoped lang="scss">
.query-history-panel {
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

  &__list {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
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
}

.query-history-item {
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
