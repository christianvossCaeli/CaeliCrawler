<template>
  <div class="table-actions d-flex justify-end ga-1" role="group" :aria-label="$t('sources.actions.rowActions')">
    <!-- Edit Button -->
    <v-tooltip location="top" :text="$t('common.edit')">
      <template #activator="{ props: tooltipProps }">
        <v-btn
          v-bind="tooltipProps"
          icon="mdi-pencil"
          size="small"
          variant="tonal"
          :aria-label="$t('sources.actions.editSource', { name: source.name })"
          @click="$emit('edit', source)"
        />
      </template>
    </v-tooltip>

    <!-- Start Crawl Button -->
    <v-tooltip location="top" :text="$t('sources.actions.startCrawl')">
      <template #activator="{ props: tooltipProps }">
        <v-btn
          v-bind="tooltipProps"
          :icon="isStarting ? undefined : 'mdi-play'"
          size="small"
          variant="tonal"
          color="success"
          :loading="isStarting"
          :disabled="isStarting"
          :aria-label="$t('sources.actions.startCrawlFor', { name: source.name })"
          :aria-busy="isStarting"
          @click="$emit('start-crawl', source)"
        />
      </template>
    </v-tooltip>

    <!-- Reset Button -->
    <v-tooltip location="top" :text="$t('sources.actions.reset')">
      <template #activator="{ props: tooltipProps }">
        <v-btn
          v-bind="tooltipProps"
          :icon="isResetting ? undefined : 'mdi-refresh'"
          size="small"
          variant="tonal"
          color="warning"
          :loading="isResetting"
          :disabled="isResetting"
          :aria-label="$t('sources.actions.resetSource', { name: source.name })"
          :aria-busy="isResetting"
          @click="$emit('reset', source)"
        />
      </template>
    </v-tooltip>

    <!-- Delete Button -->
    <v-tooltip location="top" :text="$t('common.delete')">
      <template #activator="{ props: tooltipProps }">
        <v-btn
          v-bind="tooltipProps"
          icon="mdi-delete"
          size="small"
          variant="tonal"
          color="error"
          :aria-label="$t('sources.actions.deleteSource', { name: source.name })"
          @click="$emit('delete', source)"
        />
      </template>
    </v-tooltip>
  </div>
</template>

<script setup lang="ts">
import type { DataSourceResponse } from '@/types/sources'

interface Props {
  source: DataSourceResponse
  isStarting: boolean
  isResetting: boolean
}

defineProps<Props>()

defineEmits<{
  (e: 'edit', source: DataSourceResponse): void
  (e: 'start-crawl', source: DataSourceResponse): void
  (e: 'reset', source: DataSourceResponse): void
  (e: 'delete', source: DataSourceResponse): void
}>()
</script>

<style scoped>
.table-actions {
  min-width: 140px;
}
</style>
