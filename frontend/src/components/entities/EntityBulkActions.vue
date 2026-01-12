<template>
  <v-slide-y-transition>
    <v-toolbar
      v-if="selectedEntities.length > 0"
      density="compact"
      color="primary"
      class="entity-bulk-actions mb-3"
      rounded
      role="toolbar"
      :aria-label="t('entities.bulkActions.toolbarLabel', 'Bulk actions for selected entities')"
    >
      <v-toolbar-title class="text-body-1">
        <v-icon icon="mdi-checkbox-marked" class="mr-2" aria-hidden="true" />
        <span role="status" aria-live="polite">
          {{ t('entities.bulkActions.selected', { count: selectedEntities.length }) }}
        </span>
      </v-toolbar-title>

      <v-spacer />

      <v-btn
        variant="text"
        prepend-icon="mdi-sync"
        :aria-label="t('entities.bulkActions.startCrawlFor', { count: selectedEntities.length })"
        @click="$emit('start-crawl')"
      >
        {{ t('entities.bulkActions.startCrawl') }}
      </v-btn>

      <v-divider vertical class="mx-2" aria-hidden="true" />

      <v-btn
        icon
        variant="text"
        :aria-label="t('entities.bulkActions.clearSelection')"
        @click="$emit('clear')"
      >
        <v-icon aria-hidden="true">mdi-close</v-icon>
        <v-tooltip activator="parent" location="bottom">
          {{ t('entities.bulkActions.clearSelection') }}
        </v-tooltip>
      </v-btn>
    </v-toolbar>
  </v-slide-y-transition>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { Entity } from '@/types/entity'

defineProps<{
  selectedEntities: Entity[]
}>()

defineEmits<{
  'start-crawl': []
  'clear': []
}>()

const { t } = useI18n()

</script>

<style scoped>
.entity-bulk-actions {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}
</style>
