<script setup lang="ts">
/**
 * Error Boundary Component
 *
 * Catches errors from child components and displays a fallback UI.
 * Prevents the entire application from crashing due to component errors.
 *
 * Usage:
 *   <ErrorBoundary>
 *     <SomeRiskyComponent />
 *   </ErrorBoundary>
 *
 * With custom fallback:
 *   <ErrorBoundary>
 *     <template #fallback="{ error, reset }">
 *       <MyCustomError :error="error" @retry="reset" />
 *     </template>
 *     <SomeRiskyComponent />
 *   </ErrorBoundary>
 */

import { ref, onErrorCaptured, type Ref } from 'vue'
import { useI18n } from 'vue-i18n'

interface Props {
  /** Show technical error details (only in development) */
  showDetails?: boolean
  /** Custom error title */
  title?: string
  /** Custom retry button text */
  retryText?: string
  /** Log errors to console */
  logErrors?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showDetails: import.meta.env.DEV,
  title: undefined,
  retryText: undefined,
  logErrors: true,
})

const emit = defineEmits<{
  error: [error: Error, info: string]
}>()

const { t } = useI18n()

const error: Ref<Error | null> = ref(null)
const errorInfo: Ref<string> = ref('')

/**
 * Capture errors from child components
 */
onErrorCaptured((err: Error, instance, info: string) => {
  error.value = err
  errorInfo.value = info

  if (props.logErrors) {
    console.error('[ErrorBoundary] Caught error:', err)
    console.error('[ErrorBoundary] Component info:', info)
    if (instance) {
      console.error('[ErrorBoundary] Component:', instance.$options?.name || 'Unknown')
    }
  }

  emit('error', err, info)

  // Return false to stop error propagation
  return false
})

/**
 * Reset error state and re-render children
 */
function reset() {
  error.value = null
  errorInfo.value = ''
}

/**
 * Copy error details to clipboard
 */
async function copyErrorDetails() {
  if (!error.value) return

  const details = [
    `Error: ${error.value.message}`,
    `Component: ${errorInfo.value}`,
    '',
    'Stack trace:',
    error.value.stack || 'No stack trace available',
    '',
    `Time: ${new Date().toISOString()}`,
    `URL: ${window.location.href}`,
    `User Agent: ${navigator.userAgent}`,
  ].join('\n')

  try {
    await navigator.clipboard.writeText(details)
  } catch (e) {
    console.error('Failed to copy error details:', e)
  }
}

defineExpose({
  error,
  reset,
})
</script>

<template>
  <slot v-if="!error" />

  <slot
    v-else
    name="fallback"
    :error="error"
    :error-info="errorInfo"
    :reset="reset"
  >
    <!-- Default Error UI -->
    <v-card
      class="error-boundary-card mx-auto my-8"
      max-width="600"
      variant="outlined"
      color="error"
    >
      <v-card-item>
        <template #prepend>
          <v-icon icon="mdi-alert-circle" color="error" size="large" />
        </template>
        <v-card-title class="text-error">
          {{ title || t('common.errorBoundary.title', 'Something went wrong') }}
        </v-card-title>
        <v-card-subtitle>
          {{ t('common.errorBoundary.subtitle', 'An error occurred in this section') }}
        </v-card-subtitle>
      </v-card-item>

      <v-card-text>
        <p class="mb-4">
          {{ t('common.errorBoundary.description', 'The application encountered an unexpected error. You can try again or refresh the page.') }}
        </p>

        <!-- Technical details (development only) -->
        <v-expand-transition>
          <div v-if="showDetails && error">
            <v-divider class="my-4" />

            <div class="text-caption text-medium-emphasis mb-2">
              {{ t('common.errorBoundary.technicalDetails', 'Technical Details') }}
            </div>

            <v-alert
              type="error"
              variant="tonal"
              density="compact"
              class="mb-2"
            >
              <div class="font-weight-bold">{{ error.name }}</div>
              <div class="text-body-2">{{ error.message }}</div>
            </v-alert>

            <v-expansion-panels variant="accordion">
              <v-expansion-panel>
                <v-expansion-panel-title class="text-caption">
                  Stack Trace
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <pre class="text-caption overflow-auto" style="max-height: 200px;">{{ error.stack }}</pre>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </div>
        </v-expand-transition>
      </v-card-text>

      <v-card-actions>
        <v-btn
          color="primary"
          variant="flat"
          @click="reset"
        >
          <v-icon start icon="mdi-refresh" />
          {{ retryText || t('common.errorBoundary.retry', 'Try Again') }}
        </v-btn>

        <v-btn
          variant="text"
          @click="() => window.location.reload()"
        >
          {{ t('common.errorBoundary.refresh', 'Refresh Page') }}
        </v-btn>

        <v-spacer />

        <v-btn
          v-if="showDetails"
          variant="text"
          size="small"
          @click="copyErrorDetails"
        >
          <v-icon start icon="mdi-content-copy" />
          {{ t('common.copy', 'Copy') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </slot>
</template>

<style scoped>
.error-boundary-card {
  border-width: 2px;
}
</style>
