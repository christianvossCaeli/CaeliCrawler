<template>
  <BaseWidget
    :definition="definition"
    :config="config"
    :is-editing="isEditing"
    @refresh="refresh"
  >
    <div v-if="loading" class="d-flex justify-center py-6">
      <v-progress-circular indeterminate size="32" />
    </div>

    <v-timeline
      v-else-if="items.length > 0"
      density="compact"
      side="end"
      class="activity-timeline"
    >
      <v-timeline-item
        v-for="item in items"
        :key="item.id"
        :dot-color="getActionColor(item.action)"
        size="x-small"
      >
        <template #icon>
          <v-icon :icon="getActionIcon(item.action)" size="x-small" />
        </template>

        <div
          class="d-flex align-start activity-item"
          :class="{
            'clickable-item': isClickable(item),
            'non-interactive': isEditing
          }"
          :role="isClickable(item) ? 'button' : undefined"
          :tabindex="isClickable(item) && !isEditing ? 0 : -1"
          :aria-label="item.message + ' - ' + formatTime(item.timestamp)"
          @click="navigateToItem(item)"
          @keydown="handleKeydownItem($event, item)"
        >
          <div class="flex-grow-1">
            <div class="text-body-2">{{ item.message }}</div>
            <div class="text-caption text-medium-emphasis">
              {{ formatTime(item.timestamp) }}
            </div>
          </div>
          <v-icon
            v-if="isClickable(item)"
            icon="mdi-chevron-right"
            size="x-small"
            class="text-medium-emphasis ml-1"
          />
        </div>
      </v-timeline-item>
    </v-timeline>

    <div v-else class="text-center py-6 text-medium-emphasis">
      <v-icon size="32" class="mb-2">mdi-history</v-icon>
      <div>{{ $t('dashboard.noActivity') }}</div>
    </div>

    <!-- View All Link -->
    <div
      v-if="items.length > 0"
      class="text-center mt-2 view-all-link"
      :class="{ 'non-interactive': isEditing }"
      role="button"
      :tabindex="isEditing ? -1 : 0"
      :aria-label="$t('common.viewAll')"
      @click="navigateToAuditLog"
      @keydown="handleKeydownAuditLog($event)"
    >
      <span class="text-caption text-primary">
        {{ $t('common.viewAll') }}
      </span>
    </div>
  </BaseWidget>
</template>

<script setup lang="ts">
/**
 * ActivityFeed Widget - Shows recent system activity
 */

import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useDashboardStore } from '@/stores/dashboard'
import { handleKeyboardClick } from '../composables'
import BaseWidget from '../BaseWidget.vue'
import type { WidgetDefinition, WidgetConfig, ActivityItem } from '../types'

const props = defineProps<{
  definition: WidgetDefinition
  config?: WidgetConfig
  isEditing?: boolean
}>()

const router = useRouter()
const { t } = useI18n()
const store = useDashboardStore()
const loading = ref(true)
const error = ref<string | null>(null)

const refresh = async () => {
  loading.value = true
  error.value = null
  try {
    await store.loadActivityFeed(10)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (!store.activityFeed) {
    refresh()
  } else {
    loading.value = false
  }
})

const items = computed(() => store.activityFeed?.items || [])

const getActionIcon = (action: string): string => {
  const iconMap: Record<string, string> = {
    CREATE: 'mdi-plus-circle',
    UPDATE: 'mdi-pencil',
    DELETE: 'mdi-delete',
    VERIFY: 'mdi-check-circle',
    LOGIN: 'mdi-login',
    LOGOUT: 'mdi-logout',
  }
  return iconMap[action] || 'mdi-information'
}

const getActionColor = (action: string): string => {
  const colorMap: Record<string, string> = {
    CREATE: 'success',
    UPDATE: 'info',
    DELETE: 'error',
    VERIFY: 'success',
    LOGIN: 'primary',
    LOGOUT: 'grey',
  }
  return colorMap[action] || 'grey'
}

const formatTime = (timestamp: string): string => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return t('common.justNow')
  if (diff < 3600000) return t('common.minutesAgo', { n: Math.floor(diff / 60000) })
  if (diff < 86400000) return t('common.hoursAgo', { n: Math.floor(diff / 3600000) })
  if (diff < 604800000) return t('common.daysAgo', { n: Math.floor(diff / 86400000) })

  // Use i18n date formatting for older dates
  return t('common.dateFormat', { date: date.toLocaleDateString() })
}

// Entity types that can be navigated to (model class names from audit log)
const navigableEntityTypes = new Set(['Entity', 'FacetValue'])

const isClickable = (item: ActivityItem): boolean => {
  return !!(item.entity_type && item.entity_id && navigableEntityTypes.has(item.entity_type))
}

const navigateToItem = (item: ActivityItem) => {
  if (props.isEditing || !isClickable(item)) return

  // Navigate to entity detail page for Entity items (use ID-based route)
  if (item.entity_type === 'Entity' && item.entity_id) {
    router.push({
      path: `/entity/${item.entity_id}`
    })
  } else if (item.entity_type === 'FacetValue' && item.entity_id) {
    // Navigate to results page for FacetValue items
    router.push({
      path: '/results'
    })
  }
}

const navigateToAuditLog = () => {
  if (props.isEditing) return
  router.push({ path: '/admin/audit-log' })
}

const handleKeydownItem = (event: KeyboardEvent, item: ActivityItem) => {
  handleKeyboardClick(event, () => navigateToItem(item))
}

const handleKeydownAuditLog = (event: KeyboardEvent) => {
  handleKeyboardClick(event, () => navigateToAuditLog())
}
</script>

<style scoped>
.activity-timeline {
  max-height: 300px;
  overflow-y: auto;
}

.activity-timeline :deep(.v-timeline-item__body) {
  padding-block: 4px;
}

.activity-item {
  padding: 4px 8px;
  margin: -4px -8px;
  border-radius: 8px;
  transition: background-color 0.2s ease;
}

.clickable-item {
  cursor: pointer;
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
