<script setup lang="ts">
/**
 * InsightsWidget - Shows personalized insights for the user
 */

import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '@/stores/dashboard'
import { handleKeyboardClick } from '../composables'
import BaseWidget from '../BaseWidget.vue'
import type { WidgetDefinition, WidgetConfig } from '../types'

const props = defineProps<{
  definition: WidgetDefinition
  config?: WidgetConfig
  isEditing?: boolean
}>()

const router = useRouter()
const store = useDashboardStore()
const loading = ref(true)
const error = ref<string | null>(null)

const refresh = async () => {
  loading.value = true
  error.value = null
  try {
    await store.loadInsights()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load'
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
  if (props.isEditing || !link) return
  router.push(link)
}

const isClickable = (link?: string): boolean => {
  return !!link && !props.isEditing
}

const handleKeydown = (event: KeyboardEvent, link?: string) => {
  handleKeyboardClick(event, () => navigateToLink(link))
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

    <div v-else-if="items.length > 0" class="insights-list" role="list">
      <v-card
        v-for="(item, index) in items"
        :key="index"
        variant="tonal"
        :color="getInsightColor(item.type)"
        class="mb-2 insight-card"
        :class="{
          'clickable-card': item.link,
          'non-interactive': isEditing
        }"
        :role="item.link ? 'button' : 'article'"
        :tabindex="isClickable(item.link) ? 0 : -1"
        :aria-label="item.title + ': ' + item.message + ' (' + item.count + ')'"
        @click="navigateToLink(item.link)"
        @keydown="handleKeydown($event, item.link)"
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

.insight-card {
  transition: opacity 0.2s ease, outline 0.2s ease;
}

.clickable-card {
  cursor: pointer;
}

.clickable-card:hover {
  opacity: 0.9;
}

.clickable-card:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.non-interactive {
  cursor: default;
  pointer-events: none;
}
</style>
