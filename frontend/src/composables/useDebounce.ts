/**
 * useDebounce - Centralized debounce and timeout management
 *
 * Provides consistent debouncing across the application with automatic cleanup.
 * Uses @vueuse/core internally for optimal performance.
 *
 * @example
 * ```ts
 * // Simple debounced function
 * const { debouncedFn, cancel } = useDebounce(
 *   async (query: string) => {
 *     await searchApi(query)
 *   },
 *   { delay: 300 }
 * )
 *
 * // In template
 * <input @input="debouncedFn($event.target.value)" />
 * ```
 */
import { ref, onUnmounted, type Ref } from 'vue'
import { useDebounceFn, useThrottleFn } from '@vueuse/core'

// ============================================================================
// Types
// ============================================================================

export interface UseDebounceOptions {
  /** Debounce delay in milliseconds */
  delay?: number
  /** Maximum wait time before forced execution */
  maxWait?: number
  /** Execute on leading edge */
  leading?: boolean
  /** Execute on trailing edge (default: true) */
  trailing?: boolean
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export interface UseDebounceReturn<T extends (...args: any[]) => any> {
  /** The debounced function */
  debouncedFn: T
  /** Cancel pending execution */
  cancel: () => void
  /** Whether there's a pending execution */
  isPending: Ref<boolean>
}

export interface UseTimeoutReturn {
  /** Start/restart the timeout */
  start: () => void
  /** Stop/cancel the timeout */
  stop: () => void
  /** Whether timeout is active */
  isActive: Ref<boolean>
}

// ============================================================================
// Centralized Config
// ============================================================================

/** Standard debounce delays for consistency */
export const DEBOUNCE_DELAYS = {
  /** Fast typing - autocomplete, instant search */
  FAST: 150,
  /** Normal search input */
  SEARCH: 300,
  /** Form validation */
  VALIDATION: 400,
  /** API calls, expensive operations */
  API: 500,
  /** Save operations, less frequent */
  SAVE: 1000,
} as const

// ============================================================================
// Composables
// ============================================================================

/**
 * Creates a debounced version of a function
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function useDebounce<T extends (...args: any[]) => any>(
  fn: T,
  options: UseDebounceOptions = {}
): UseDebounceReturn<T> {
  const { delay = DEBOUNCE_DELAYS.SEARCH, maxWait } = options

  const isPending = ref(false)
  let timeoutId: ReturnType<typeof setTimeout> | null = null

  // Use VueUse's optimized debounce
  const debouncedFn = useDebounceFn(
    (...args: Parameters<T>) => {
      isPending.value = false
      return fn(...args)
    },
    delay,
    { maxWait }
  ) as T

  // Wrap to track pending state
  const wrappedFn = ((...args: Parameters<T>) => {
    isPending.value = true
    return debouncedFn(...args)
  }) as T

  const cancel = () => {
    isPending.value = false
    if (timeoutId) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
  }

  // Auto cleanup
  onUnmounted(cancel)

  return {
    debouncedFn: wrappedFn,
    cancel,
    isPending,
  }
}

/**
 * Creates a throttled version of a function
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function useThrottle<T extends (...args: any[]) => any>(
  fn: T,
  delay: number = DEBOUNCE_DELAYS.API
): T {
  return useThrottleFn(fn, delay) as T
}

/**
 * Creates a managed timeout with start/stop controls
 */
export function useTimeout(
  callback: () => void,
  delay: number
): UseTimeoutReturn {
  const isActive = ref(false)
  let timeoutId: ReturnType<typeof setTimeout> | null = null

  const stop = () => {
    if (timeoutId) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
    isActive.value = false
  }

  const start = () => {
    stop() // Clear any existing timeout
    isActive.value = true
    timeoutId = setTimeout(() => {
      isActive.value = false
      callback()
    }, delay)
  }

  // Auto cleanup
  onUnmounted(stop)

  return {
    start,
    stop,
    isActive,
  }
}

/**
 * Creates a search debounce with standard config
 *
 * @example
 * ```ts
 * const { search, cancel, isPending } = useSearchDebounce(async (query) => {
 *   const results = await api.search(query)
 *   items.value = results
 * })
 *
 * // In template
 * <v-text-field @update:model-value="search" />
 * ```
 */
export function useSearchDebounce<T>(
  searchFn: (query: string) => Promise<T> | T,
  options: { minLength?: number; delay?: number } = {}
) {
  const { minLength = 2, delay = DEBOUNCE_DELAYS.SEARCH } = options
  const isPending = ref(false)
  const lastQuery = ref('')

  const { debouncedFn, cancel } = useDebounce(
    async (query: string) => {
      lastQuery.value = query

      if (!query || query.length < minLength) {
        isPending.value = false
        return null
      }

      isPending.value = true
      try {
        return await searchFn(query)
      } finally {
        isPending.value = false
      }
    },
    { delay }
  )

  return {
    search: debouncedFn as (query: string) => Promise<T | null>,
    cancel,
    isPending,
    lastQuery,
  }
}

/**
 * Creates a polling mechanism with configurable interval
 */
export function usePolling(
  callback: () => Promise<void> | void,
  interval: number = 5000
) {
  const isActive = ref(false)
  let intervalId: ReturnType<typeof setInterval> | null = null

  const start = () => {
    if (isActive.value) return
    isActive.value = true
    callback() // Execute immediately
    intervalId = setInterval(callback, interval)
  }

  const stop = () => {
    if (intervalId) {
      clearInterval(intervalId)
      intervalId = null
    }
    isActive.value = false
  }

  // Auto cleanup
  onUnmounted(stop)

  return {
    start,
    stop,
    isActive,
  }
}
