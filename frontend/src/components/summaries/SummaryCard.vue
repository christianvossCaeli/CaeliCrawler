<template>
  <v-card
    class="summary-card"
    :class="{ 'summary-card--favorite': summary.is_favorite }"
    hover
    role="article"
    :aria-label="t('summaries.summaryCardLabel', { name: summary.name })"
    tabindex="0"
    @click="$emit('click')"
    @keydown.enter="$emit('click')"
    @keydown.space.prevent="$emit('click')"
  >
    <!-- Header -->
    <v-card-item>
      <template #prepend>
        <v-avatar
          :color="statusColor"
          variant="tonal"
          size="48"
        >
          <v-icon>mdi-view-dashboard</v-icon>
        </v-avatar>
      </template>

      <v-card-title class="text-truncate">{{ summary.name }}</v-card-title>
      <v-card-subtitle class="text-truncate">
        {{ summary.description || summary.original_prompt }}
      </v-card-subtitle>

      <template #append>
        <v-btn
          :icon="summary.is_favorite ? 'mdi-star' : 'mdi-star-outline'"
          :color="summary.is_favorite ? 'amber' : undefined"
          variant="text"
          size="small"
          :aria-label="summary.is_favorite ? t('summaries.removeFromFavorites') : t('summaries.addToFavorites')"
          :aria-pressed="summary.is_favorite"
          @click.stop="$emit('toggle-favorite')"
        />
        <v-menu location="bottom end">
          <template #activator="{ props }">
            <v-btn
              icon="mdi-dots-vertical"
              variant="text"
              size="small"
              :aria-label="t('summaries.moreActions')"
              v-bind="props"
              @click.stop
            />
          </template>
          <v-list density="compact">
            <v-list-item
              prepend-icon="mdi-pencil"
              :title="t('common.edit')"
              @click="$emit('edit')"
            />
            <v-list-item
              prepend-icon="mdi-share-variant"
              :title="t('summaries.share')"
              @click="$emit('share')"
            />
            <v-divider />
            <v-list-item
              prepend-icon="mdi-delete"
              :title="t('common.delete')"
              class="text-error"
              @click="$emit('delete')"
            />
          </v-list>
        </v-menu>
      </template>
    </v-card-item>

    <!-- Status & Trigger Info -->
    <v-card-text class="pt-0">
      <div class="d-flex align-center flex-wrap ga-2 mb-3">
        <v-chip
          :color="statusColor"
          size="small"
          variant="tonal"
        >
          {{ t(`summaries.status${capitalize(summary.status)}`) }}
        </v-chip>

        <v-chip
          v-if="summary.schedule_enabled"
          color="blue"
          size="small"
          variant="tonal"
        >
          <v-icon start size="small">mdi-clock-outline</v-icon>
          {{ triggerLabel }}
        </v-chip>

        <v-chip
          v-if="widgetCount > 0"
          color="grey"
          size="small"
          variant="tonal"
        >
          <v-icon start size="small">mdi-widgets</v-icon>
          {{ widgetCount }}
        </v-chip>
      </div>

      <!-- Stats -->
      <div class="d-flex justify-space-between text-caption text-medium-emphasis">
        <span v-if="summary.execution_count > 0">
          <v-icon size="x-small" class="mr-1">mdi-play-circle</v-icon>
          {{ summary.execution_count }}x {{ t('summaries.executed') }}
        </span>
        <span v-else>
          {{ t('summaries.neverExecuted') }}
        </span>
        <span v-if="summary.last_executed_at">
          {{ formatRelativeTime(summary.last_executed_at) }}
        </span>
      </div>
    </v-card-text>

    <!-- Actions -->
    <v-card-actions>
      <v-btn
        variant="tonal"
        color="primary"
        size="small"
        :loading="isExecuting"
        @click.stop="$emit('execute')"
      >
        <v-icon start>mdi-play</v-icon>
        {{ t('summaries.execute') }}
      </v-btn>
      <v-spacer />
      <v-btn
        variant="text"
        color="primary"
        size="small"
        @click.stop="$emit('click')"
      >
        {{ t('summaries.open') }}
        <v-icon end>mdi-arrow-right</v-icon>
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { CustomSummary } from '@/stores/customSummaries'
import { useRelativeTime } from '@/composables/useRelativeTime'
import { capitalize } from '@/composables/useStringUtils'
import { useStatusColors } from '@/composables'

const { t } = useI18n()
const { formatRelativeTime } = useRelativeTime()
const { getStatusColor } = useStatusColors()

const props = defineProps<{
  summary: CustomSummary
  isExecuting?: boolean
}>()

defineEmits<{
  click: []
  execute: []
  'toggle-favorite': []
  edit: []
  delete: []
  share: []
}>()

// Use centralized status colors
const statusColor = computed(() => getStatusColor(props.summary.status))

const triggerLabel = computed(() => {
  switch (props.summary.trigger_type) {
    case 'cron':
      return props.summary.schedule_cron || t('summaries.trigger.scheduled')
    case 'crawl_category':
      return t('summaries.trigger.afterCrawl')
    case 'crawl_preset':
      return t('summaries.trigger.afterPreset')
    default:
      return t('summaries.trigger.manual')
  }
})

const widgetCount = computed(() => {
  return props.summary.widgets?.length || 0
})
</script>

<style scoped>
.summary-card {
  transition: all 0.2s ease;
}

.summary-card--favorite {
  border-left: 3px solid rgb(var(--v-theme-warning));
}

.summary-card:hover {
  transform: translateY(-2px);
}
</style>
