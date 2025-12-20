<script setup lang="ts">
/**
 * ActivityFeed Widget - Shows recent system activity
 */

import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDashboardStore } from '@/stores/dashboard'
import BaseWidget from '../BaseWidget.vue'
import type { WidgetDefinition, WidgetConfig, ActivityItem } from '../types'

const props = defineProps<{
  definition: WidgetDefinition
  config?: WidgetConfig
  isEditing?: boolean
}>()

const { t } = useI18n()
const store = useDashboardStore()
const loading = ref(true)

const refresh = async () => {
  loading.value = true
  try {
    await store.loadActivityFeed(10)
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

  return date.toLocaleDateString()
}
</script>

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

        <div class="d-flex align-start">
          <div class="flex-grow-1">
            <div class="text-body-2">{{ item.message }}</div>
            <div class="text-caption text-medium-emphasis">
              {{ formatTime(item.timestamp) }}
            </div>
          </div>
        </div>
      </v-timeline-item>
    </v-timeline>

    <div v-else class="text-center py-6 text-medium-emphasis">
      <v-icon size="32" class="mb-2">mdi-history</v-icon>
      <div>{{ $t('dashboard.noActivity') }}</div>
    </div>
  </BaseWidget>
</template>

<style scoped>
.activity-timeline {
  max-height: 300px;
  overflow-y: auto;
}

.activity-timeline :deep(.v-timeline-item__body) {
  padding-block: 4px;
}
</style>
