<template>
  <div class="async-wrapper">
    <!-- Loading State -->
    <template v-if="loading">
      <slot name="loading">
        <div class="d-flex justify-center align-center pa-8">
          <v-progress-circular
            indeterminate
            :color="loadingColor"
            :size="loadingSize"
          ></v-progress-circular>
          <span v-if="loadingText" class="ml-3 text-medium-emphasis">{{ loadingText }}</span>
        </div>
      </slot>
    </template>

    <!-- Error State -->
    <template v-else-if="error">
      <slot name="error" :error="error" :retry="retry">
        <v-alert
          type="error"
          variant="tonal"
          class="ma-4"
          :title="errorTitle"
        >
          <p class="mb-2">{{ errorMessage }}</p>

          <template v-if="retryable" #append>
            <v-btn
              variant="outlined"
              size="small"
              :loading="retrying"
              @click="retry"
            >
              <v-icon start>mdi-refresh</v-icon>
              {{ $t('common.retry') }}
            </v-btn>
          </template>
        </v-alert>
      </slot>
    </template>

    <!-- Empty State -->
    <template v-else-if="empty">
      <slot name="empty">
        <v-empty-state
          :icon="emptyIcon"
          :title="emptyTitle"
          :text="emptyText"
        >
          <template v-if="$slots.emptyActions" #actions>
            <slot name="emptyActions"></slot>
          </template>
        </v-empty-state>
      </slot>
    </template>

    <!-- Content -->
    <template v-else>
      <slot></slot>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * AsyncWrapper - Handles loading, error, and empty states for async content
 *
 * Provides consistent UI patterns for data loading scenarios.
 *
 * @example
 * <AsyncWrapper
 *   :loading="isLoading"
 *   :error="fetchError"
 *   :empty="items.length === 0"
 *   @retry="fetchData"
 * >
 *   <DataList :items="items" />
 * </AsyncWrapper>
 */
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'

interface Props {
  /** Whether data is currently loading */
  loading?: boolean
  /** Error object if request failed */
  error?: Error | string | null
  /** Whether data is empty */
  empty?: boolean
  /** Whether retry is allowed */
  retryable?: boolean
  /** Loading indicator color */
  loadingColor?: string
  /** Loading indicator size */
  loadingSize?: number | string
  /** Text to show while loading */
  loadingText?: string
  /** Error alert title */
  errorTitle?: string
  /** Empty state icon */
  emptyIcon?: string
  /** Empty state title */
  emptyTitle?: string
  /** Empty state description */
  emptyText?: string
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  error: null,
  empty: false,
  retryable: true,
  loadingColor: 'primary',
  loadingSize: 32,
  loadingText: '',
  errorTitle: '',
  emptyIcon: 'mdi-database-off',
  emptyTitle: '',
  emptyText: '',
})

const emit = defineEmits<{
  (e: 'retry'): void
}>()

const { t } = useI18n()

const retrying = ref(false)

/** Computed error message */
const errorMessage = computed(() => {
  if (!props.error) return ''
  if (typeof props.error === 'string') return props.error
  return props.error.message || t('common.unknownError')
})

/** Retry handler */
const retry = async () => {
  retrying.value = true
  emit('retry')
  // Reset after a short delay
  setTimeout(() => {
    retrying.value = false
  }, 1000)
}
</script>

<style scoped>
.async-wrapper {
  width: 100%;
  min-height: 100px;
}
</style>
