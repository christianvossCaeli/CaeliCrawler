<template>
  <v-slide-y-transition>
    <v-toolbar
      v-if="selectedDocuments.length > 0"
      density="compact"
      color="primary"
      class="documents-bulk-actions mb-3"
      rounded
      role="toolbar"
      :aria-label="t('documents.bulkActions.toolbarLabel')"
    >
      <v-toolbar-title class="text-body-1">
        <v-icon icon="mdi-checkbox-marked" class="mr-2" aria-hidden="true" />
        <span role="status" aria-live="polite">
          {{ t('documents.bulkActions.selected', { count: selectedDocuments.length }) }}
        </span>
      </v-toolbar-title>

      <v-spacer />

      <!-- Bulk Process Button -->
      <v-btn
        variant="text"
        prepend-icon="mdi-play"
        :loading="bulkProcessing"
        :aria-label="t('documents.bulkActions.processSelected', { count: selectedDocuments.length })"
        @click="$emit('bulk-process')"
      >
        {{ t('documents.bulkActions.process') }}
      </v-btn>

      <!-- Bulk Analyze Button -->
      <v-btn
        variant="text"
        prepend-icon="mdi-brain"
        :loading="bulkAnalyzing"
        :aria-label="t('documents.bulkActions.analyzeSelected', { count: selectedDocuments.length })"
        @click="$emit('bulk-analyze')"
      >
        {{ t('documents.bulkActions.analyze') }}
      </v-btn>

      <v-divider vertical class="mx-2" aria-hidden="true" />

      <v-btn
        icon
        variant="text"
        :aria-label="t('documents.bulkActions.clearSelection')"
        @click="$emit('clear')"
      >
        <v-icon aria-hidden="true">mdi-close</v-icon>
        <v-tooltip activator="parent" location="bottom">
          {{ t('documents.bulkActions.clearSelection') }}
        </v-tooltip>
      </v-btn>
    </v-toolbar>
  </v-slide-y-transition>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

interface Document {
  id: string
  [key: string]: unknown
}

defineProps<{
  selectedDocuments: Document[]
  bulkProcessing?: boolean
  bulkAnalyzing?: boolean
}>()

defineEmits<{
  'bulk-process': []
  'bulk-analyze': []
  'clear': []
}>()

const { t } = useI18n()
</script>

<style scoped>
.documents-bulk-actions {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}
</style>
