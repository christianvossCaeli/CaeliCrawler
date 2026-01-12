<template>
  <v-slide-y-transition>
    <v-toolbar
      v-if="selectedResults.length > 0"
      density="compact"
      color="primary"
      class="results-bulk-actions mb-3"
      rounded
      role="toolbar"
      :aria-label="t('results.bulkActions.toolbarLabel')"
    >
      <v-toolbar-title class="text-body-1">
        <v-icon icon="mdi-checkbox-marked" class="mr-2" aria-hidden="true" />
        <span role="status" aria-live="polite">
          {{ t('results.bulkActions.selected', { count: selectedResults.length }) }}
        </span>
      </v-toolbar-title>

      <v-spacer />

      <!-- Bulk Verify Button -->
      <v-btn
        v-if="canVerify"
        variant="text"
        prepend-icon="mdi-check-all"
        :loading="bulkVerifying"
        :aria-label="t('results.bulkActions.verifySelected', { count: selectedResults.length })"
        @click="$emit('bulk-verify')"
      >
        {{ t('results.bulkActions.verify') }}
      </v-btn>

      <!-- Bulk Reject Button -->
      <v-btn
        v-if="canVerify"
        variant="text"
        prepend-icon="mdi-close-circle-multiple"
        :loading="bulkRejecting"
        :aria-label="t('results.bulkActions.rejectSelected', { count: selectedResults.length })"
        @click="$emit('bulk-reject')"
      >
        {{ t('results.bulkActions.reject') }}
      </v-btn>

      <v-divider vertical class="mx-2" aria-hidden="true" />

      <v-btn
        icon
        variant="text"
        :aria-label="t('results.bulkActions.clearSelection')"
        @click="$emit('clear')"
      >
        <v-icon aria-hidden="true">mdi-close</v-icon>
        <v-tooltip activator="parent" location="bottom">
          {{ t('results.bulkActions.clearSelection') }}
        </v-tooltip>
      </v-btn>
    </v-toolbar>
  </v-slide-y-transition>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

defineProps<{
  selectedResults: number[]
  canVerify: boolean
  bulkVerifying?: boolean
  bulkRejecting?: boolean
}>()

defineEmits<{
  'bulk-verify': []
  'bulk-reject': []
  'clear': []
}>()

const { t } = useI18n()
</script>

<style scoped>
.results-bulk-actions {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}
</style>
