<template>
  <div class="error-boundary">
    <!-- Error State -->
    <template v-if="error">
      <slot name="error" :error="error" :reset="reset">
        <v-alert
          type="error"
          variant="tonal"
          class="ma-4"
          :title="$t('common.errorOccurred')"
        >
          <template v-slot:prepend>
            <v-icon>mdi-alert-circle</v-icon>
          </template>

          <p class="mb-2">{{ errorMessage }}</p>

          <!-- Error Details (collapsible in development) -->
          <v-expansion-panels v-if="showDetails" variant="accordion" class="mb-3">
            <v-expansion-panel>
              <v-expansion-panel-title class="text-caption">
                {{ $t('common.errorDetails') }}
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <pre class="text-caption error-stack">{{ errorStack }}</pre>
                <div v-if="errorInfo" class="mt-2">
                  <strong>Component:</strong> {{ errorInfo }}
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>

          <template v-slot:append>
            <v-btn
              variant="outlined"
              size="small"
              @click="reset"
            >
              <v-icon start>mdi-refresh</v-icon>
              {{ $t('common.retry') }}
            </v-btn>
          </template>
        </v-alert>
      </slot>
    </template>

    <!-- Normal Content -->
    <template v-else>
      <slot></slot>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * ErrorBoundary - Catches and displays errors from child components
 *
 * Provides a graceful error handling experience with retry capability.
 * In development mode, shows detailed error information.
 *
 * @example
 * <ErrorBoundary>
 *   <SomeComponent />
 * </ErrorBoundary>
 *
 * @example Custom error slot
 * <ErrorBoundary>
 *   <template #error="{ error, reset }">
 *     <div>Error: {{ error.message }}</div>
 *     <button @click="reset">Try Again</button>
 *   </template>
 *   <SomeComponent />
 * </ErrorBoundary>
 */
import { ref, computed, onErrorCaptured } from 'vue'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('ErrorBoundary')

interface Props {
  /** Custom fallback message when error occurs */
  fallbackMessage?: string
  /** Whether to show error details (stack trace) */
  showDetails?: boolean
  /** Callback when error is caught */
  onError?: (error: Error, info: string) => void
}

const props = withDefaults(defineProps<Props>(), {
  showDetails: import.meta.env.DEV,
})

const emit = defineEmits<{
  (e: 'error', error: Error, info: string): void
  (e: 'reset'): void
}>()

const error = ref<Error | null>(null)
const errorInfo = ref<string>('')

/** Formatted error message */
const errorMessage = computed(() => {
  if (props.fallbackMessage) return props.fallbackMessage
  return error.value?.message || 'An unexpected error occurred'
})

/** Formatted stack trace */
const errorStack = computed(() => {
  return error.value?.stack || 'No stack trace available'
})

/** Reset error state to retry rendering */
const reset = () => {
  error.value = null
  errorInfo.value = ''
  emit('reset')
}

/** Capture errors from child components */
onErrorCaptured((err: Error, _instance, info: string) => {
  error.value = err
  errorInfo.value = info

  // Log error in development
  if (import.meta.env.DEV) {
    logger.error('[ErrorBoundary] Caught error:', err)
    logger.error('[ErrorBoundary] Component info:', info)
  }

  // Notify parent
  emit('error', err, info)
  props.onError?.(err, info)

  // Prevent error from propagating
  return false
})
</script>

<style scoped>
.error-boundary {
  width: 100%;
  height: 100%;
}

.error-stack {
  font-family: monospace;
  font-size: 0.75rem;
  white-space: pre-wrap;
  word-break: break-all;
  background: rgba(0, 0, 0, 0.05);
  padding: 8px;
  border-radius: 4px;
  max-height: 200px;
  overflow-y: auto;
}
</style>
