<script setup lang="ts">
/**
 * InsightsWidget - Shows personalized insights for the user
 */

import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '@/stores/dashboard'
import BaseWidget from '../BaseWidget.vue'
import type { WidgetDefinition, WidgetConfig, InsightItem } from '../types'

const props = defineProps<{
  definition: WidgetDefinition
  config?: WidgetConfig
  isEditing?: boolean
}>()

const router = useRouter()
const store = useDashboardStore()
const loading = ref(true)

const refresh = async () => {
  loading.value = true
  try {
    await store.loadInsights()
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (!store.insights) {
    refresh()
  } else {
    loading.value = false
  }
})

const items = computed(() => store.insights?.items || [])

const getInsightIcon = (type: string): string => {
  const iconMap: Record<string, string> = {
    new_entities: 'mdi-database-plus',
    new_facets: 'mdi-tag-plus',
    completed_crawls: 'mdi-check-all',
    action_needed: 'mdi-alert-circle',
  }
  return iconMap[type] || 'mdi-lightbulb'
}

const getInsightColor = (type: string): string => {
  const colorMap: Record<string, string> = {
    new_entities: 'success',
    new_facets: 'info',
    completed_crawls: 'primary',
    action_needed: 'warning',
  }
  return colorMap[type] || 'grey'
}

const navigateToLink = (link?: string) => {
  if (link) {
    router.push(link)
  }
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

    <div v-else-if="items.length > 0" class="insights-list">
      <v-card
        v-for="(item, index) in items"
        :key="index"
        variant="tonal"
        :color="getInsightColor(item.type)"
        class="mb-2 insight-card"
        :class="{ 'cursor-pointer': item.link }"
        @click="navigateToLink(item.link)"
      >
        <v-card-text class="d-flex align-center py-2 px-3">
          <v-icon
            :icon="getInsightIcon(item.type)"
            :color="getInsightColor(item.type)"
            size="small"
            class="mr-3"
          />
          <div class="flex-grow-1">
            <div class="text-body-2 font-weight-medium">
              {{ item.title }}
            </div>
            <div class="text-caption">
              {{ item.message }}
            </div>
          </div>
          <v-chip
            :color="getInsightColor(item.type)"
            size="small"
            class="ml-2"
          >
            {{ item.count }}
          </v-chip>
        </v-card-text>
      </v-card>
    </div>

    <div v-else class="text-center py-6 text-medium-emphasis">
      <v-icon size="32" class="mb-2">mdi-check-circle</v-icon>
      <div>{{ $t('dashboard.noNewInsights') }}</div>
    </div>
  </BaseWidget>
</template>

<style scoped>
.insights-list {
  max-height: 200px;
  overflow-y: auto;
}

.insight-card:hover {
  opacity: 0.9;
}

.cursor-pointer {
  cursor: pointer;
}
</style>
