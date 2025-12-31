<template>
  <div
    :class="[
      'd-flex flex-column align-center justify-center text-center',
      inline ? 'py-4' : 'py-8',
    ]"
    :style="{ minHeight: minHeight }"
    role="alert"
  >
    <!-- Error Icon -->
    <v-icon
      :icon="icon"
      :size="inline ? 40 : 56"
      :color="iconColor"
      class="mb-3"
      aria-hidden="true"
    />

    <!-- Title -->
    <h4 v-if="title" :class="inline ? 'text-subtitle-1' : 'text-h6'" class="font-weight-medium mb-1">
      {{ title }}
    </h4>

    <!-- Error Message -->
    <p
      v-if="message"
      class="text-body-2 text-medium-emphasis mb-3"
      style="max-width: 400px"
    >
      {{ message }}
    </p>

    <!-- Technical Details (collapsible) -->
    <v-expand-transition>
      <div
        v-if="details && showDetails"
        class="text-caption text-error bg-error-lighten-5 pa-2 rounded mb-3"
        style="max-width: 400px; word-break: break-word"
      >
        {{ details }}
      </div>
    </v-expand-transition>

    <!-- Actions -->
    <div class="d-flex gap-2 flex-wrap justify-center">
      <!-- Retry Button -->
      <v-btn
        v-if="showRetry"
        :variant="inline ? 'text' : 'tonal'"
        :size="inline ? 'small' : 'default'"
        color="primary"
        prepend-icon="mdi-refresh"
        :loading="retrying"
        @click="$emit('retry')"
      >
        {{ retryText || t('common.retry') }}
      </v-btn>

      <!-- Show/Hide Details Toggle -->
      <v-btn
        v-if="details"
        variant="text"
        :size="inline ? 'small' : 'default'"
        color="grey"
        @click="showDetails = !showDetails"
      >
        {{ showDetails ? t('common.hideDetails') : t('common.showDetails') }}
      </v-btn>

      <!-- Custom Action Slot -->
      <slot name="actions"></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * TableErrorState Component
 *
 * A reusable component for displaying error states in data tables
 * and lists. Provides retry functionality and optional error details.
 *
 * @example
 * ```vue
 * <v-data-table :items="items" :loading="loading">
 *   <template #no-data>
 *     <TableErrorState
 *       v-if="error"
 *       :title="$t('common.loadError')"
 *       :message="error.message"
 *       :details="error.details"
 *       @retry="loadData"
 *     />
 *     <EmptyState v-else :title="$t('common.noData')" />
 *   </template>
 * </v-data-table>
 * ```
 */
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

withDefaults(
  defineProps<{
    /** Error icon (MDI) */
    icon?: string
    /** Icon color */
    iconColor?: string
    /** Main error title */
    title?: string
    /** User-friendly error message */
    message?: string
    /** Technical error details (shown on toggle) */
    details?: string
    /** Show retry button */
    showRetry?: boolean
    /** Custom retry button text */
    retryText?: string
    /** Whether retry is in progress */
    retrying?: boolean
    /** Use compact inline variant */
    inline?: boolean
    /** Minimum height */
    minHeight?: string
  }>(),
  {
    icon: 'mdi-alert-circle-outline',
    iconColor: 'error',
    showRetry: true,
    retrying: false,
    inline: false,
    minHeight: '150px',
  },
)

defineEmits<{
  /** Emitted when retry button is clicked */
  retry: []
}>()

const { t } = useI18n()

const showDetails = ref(false)
</script>

<style scoped>
.bg-error-lighten-5 {
  background-color: rgb(var(--v-theme-error), 0.05);
}
</style>
