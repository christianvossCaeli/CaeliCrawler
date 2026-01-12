<template>
  <Teleport to="body">
    <!-- Backdrop -->
    <Transition name="fade">
      <div
        v-if="modelValue"
        class="chat-history-sidebar__backdrop chat-history-sidebar__backdrop--visible"
        @click="$emit('update:modelValue', false)"
      />
    </Transition>

    <!-- Sidebar -->
    <Transition name="slide">
      <aside
        v-if="modelValue"
        class="chat-history-sidebar chat-history-sidebar--open"
      >
        <div class="chat-history-sidebar__header">
          <h3 class="chat-history-sidebar__title">{{ t('chatHome.history.title') }}</h3>
          <v-btn
            icon
            variant="text"
            size="small"
            @click="$emit('update:modelValue', false)"
          >
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </div>

        <div class="chat-history-sidebar__content">
          <!-- Favorites Section -->
          <div v-if="favorites.length > 0" class="history-section">
            <div class="history-section__title">
              <v-icon size="14" class="mr-1">mdi-star</v-icon>
              {{ t('chatHome.history.favorites') }}
            </div>
            <div
              v-for="item in favorites"
              :key="item.id"
              class="history-item"
              @click="$emit('select', item.query)"
            >
              <div class="history-item__query">{{ item.query }}</div>
              <div class="history-item__meta">
                <v-icon size="12">mdi-clock-outline</v-icon>
                {{ formatDate(item.timestamp) }}
              </div>
            </div>
          </div>

          <!-- Recent Section -->
          <div class="history-section">
            <div class="history-section__title">
              <v-icon size="14" class="mr-1">mdi-history</v-icon>
              {{ t('chatHome.history.recent') }}
            </div>
            <div v-if="recentItems.length === 0" class="history-empty">
              {{ t('chatHome.history.empty') }}
            </div>
            <div
              v-for="item in recentItems"
              :key="item.id"
              class="history-item"
              @click="$emit('select', item.query)"
            >
              <div class="history-item__query">{{ item.query }}</div>
              <div class="history-item__meta">
                <v-chip
                  size="x-small"
                  :color="getModeColor(item.mode)"
                  variant="tonal"
                  class="mr-2"
                >
                  {{ item.mode }}
                </v-chip>
                {{ formatDate(item.timestamp) }}
              </div>
            </div>
          </div>
        </div>
      </aside>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSmartQueryHistoryStore } from '@/stores/smartQueryHistory'

interface HistoryItem {
  id: string
  query: string
  mode: 'read' | 'write' | 'plan'
  timestamp: Date
  favorite?: boolean
}

defineProps<{
  modelValue: boolean
}>()

defineEmits<{
  'update:modelValue': [value: boolean]
  select: [query: string]
}>()

const { t } = useI18n()
const historyStore = useSmartQueryHistoryStore()

const favorites = computed<HistoryItem[]>(() => {
  return historyStore.favorites.map(item => ({
    id: item.id,
    query: item.command_text,
    mode: (item.operation_type || 'read') as 'read' | 'write' | 'plan',
    timestamp: new Date(item.last_executed_at),
    favorite: true
  }))
})

const recentItems = computed<HistoryItem[]>(() => {
  return historyStore.history.slice(0, 20).map(item => ({
    id: item.id,
    query: item.command_text,
    mode: (item.operation_type || 'read') as 'read' | 'write' | 'plan',
    timestamp: new Date(item.last_executed_at),
    favorite: item.is_favorite
  }))
})

function formatDate(date: Date): string {
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return t('chatHome.history.justNow')
  if (minutes < 60) return t('chatHome.history.minutesAgo', { count: minutes })
  if (hours < 24) return t('chatHome.history.hoursAgo', { count: hours })
  if (days < 7) return t('chatHome.history.daysAgo', { count: days })
  return date.toLocaleDateString()
}

function getModeColor(mode: string): string {
  switch (mode) {
    case 'write': return 'warning'
    case 'plan': return 'info'
    default: return 'primary'
  }
}

// Load history when component mounts
onMounted(() => {
  historyStore.loadHistory()
})
</script>

<style scoped>
.history-section {
  margin-bottom: 24px;
}

.history-section__title {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: rgba(var(--v-theme-on-surface), 0.5);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
}

.history-empty {
  font-size: 0.875rem;
  color: rgba(var(--v-theme-on-surface), 0.4);
  text-align: center;
  padding: 24px 16px;
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}
</style>
