/**
 * useAsyncOperation - Composable for managing async operations with state
 *
 * Combines loading state, error handling, and optional request cancellation
 * into a single unified interface.
 *
 * @example
 * ```ts
 * const { execute, loading, error, data, reset } = useAsyncOperation(
 *   async (params, signal) => {
 *     const response = await fetch('/api/data', { signal })
 *     return response.json()
 *   }
 * )
 *
 * // In template
 * <button @click="execute({ id: 1 })" :disabled="loading">
 *   {{ loading ? 'Loading...' : 'Fetch Data' }}
 * </button>
 * <div v-if="error">Error: {{ error.message }}</div>
 * <div v-if="data">{{ data }}</div>
 * ```
 */
import { ref, computed, onUnmounted, readonly, type Ref } from 'vue'
import { isAbortError } from './useAbortController'

/**
 * Options for useAsyncOperation
 */
export interface UseAsyncOperationOptions<T> {
  /** Initial data value */
  initialData?: T
  /** Whether to automatically abort previous request when executing new one */
  abortPrevious?: boolean
  /** Callback on successful execution */
  onSuccess?: (data: T) => void
  /** Callback on error */
  onError?: (error: Error) => void
  /** Whether to ignore abort errors (default: true) */
  ignoreAbortErrors?: boolean
}

/**
 * Return type for useAsyncOperation
 */
export interface UseAsyncOperationReturn<T, P> {
  /** The result data */
  data: Ref<T | null>
  /** Current error if any */
  error: Ref<Error | null>
  /** Whether operation is in progress */
  loading: Readonly<Ref<boolean>>
  /** Whether operation has been executed at least once */
  executed: Readonly<Ref<boolean>>
  /** Execute the async operation */
  execute: (params?: P) => Promise<T | null>
  /** Abort the current operation */
  abort: (reason?: string) => void
  /** Reset state to initial values */
  reset: () => void
  /** Whether the last execution was successful */
  isSuccess: Readonly<Ref<boolean>>
  /** Whether there is an error */
  isError: Readonly<Ref<boolean>>
}

/**
 * Type for the async function passed to useAsyncOperation
 */
export type AsyncOperationFn<T, P = void> = (
  params: P,
  signal: AbortSignal
) => Promise<T>

/**
 * Creates a composable for managing async operations
 */
export function useAsyncOperation<T, P = void>(
  fn: AsyncOperationFn<T, P>,
  options: UseAsyncOperationOptions<T> = {}
): UseAsyncOperationReturn<T, P> {
  const {
    initialData = null,
    abortPrevious = true,
    onSuccess,
    onError,
    ignoreAbortErrors = true,
  } = options

  // State
  const data = ref<T | null>(initialData) as Ref<T | null>
  const error = ref<Error | null>(null)
  const loading = ref(false)
  const executed = ref(false)

  // Abort controller management
  let controller: AbortController | null = null

  /**
   * Create a new abort controller
   */
  const createController = (): AbortSignal => {
    if (abortPrevious && controller) {
      controller.abort('New request started')
    }
    controller = new AbortController()
    return controller.signal
  }

  /**
   * Execute the async operation
   */
  const execute = async (params?: P): Promise<T | null> => {
    const signal = createController()
    loading.value = true
    error.value = null
    executed.value = true

    try {
      const result = await fn(params as P, signal)
      data.value = result
      onSuccess?.(result)
      return result
    } catch (err) {
      const caughtError = err instanceof Error ? err : new Error(String(err))

      // Optionally ignore abort errors
      if (ignoreAbortErrors && isAbortError(caughtError)) {
        return null
      }

      error.value = caughtError
      onError?.(caughtError)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Abort the current operation
   */
  const abort = (reason?: string) => {
    if (controller) {
      controller.abort(reason || 'Operation aborted')
    }
  }

  /**
   * Reset state to initial values
   */
  const reset = () => {
    abort()
    data.value = initialData as T | null
    error.value = null
    loading.value = false
    executed.value = false
  }

  // Computed states
  const isSuccess = computed(() => executed.value && !error.value && !loading.value)
  const isError = computed(() => error.value !== null)

  // Cleanup on unmount
  onUnmounted(() => {
    abort('Component unmounted')
  })

  return {
    data,
    error,
    loading: readonly(loading),
    executed: readonly(executed),
    execute,
    abort,
    reset,
    isSuccess: readonly(isSuccess),
    isError: readonly(isError),
  }
}

/**
 * useAsyncState - Simpler version that auto-executes on mount
 *
 * @example
 * ```ts
 * const { data, loading, error, refresh } = useAsyncState(
 *   () => fetchUsers(),
 *   [],
 *   { immediate: true }
 * )
 * ```
 */
export interface UseAsyncStateOptions<T> extends UseAsyncOperationOptions<T> {
  /** Execute immediately on creation */
  immediate?: boolean
  /** Delay before execution (ms) */
  delay?: number
}

export interface UseAsyncStateReturn<T> extends Omit<UseAsyncOperationReturn<T, void>, 'execute'> {
  /** Refresh/re-execute the operation */
  refresh: () => Promise<T | null>
}

export function useAsyncState<T>(
  fn: () => Promise<T>,
  initialData: T | null = null,
  options: UseAsyncStateOptions<T> = {}
): UseAsyncStateReturn<T> {
  const { immediate = true, delay = 0, ...operationOptions } = options

  const operation = useAsyncOperation<T, void>(
    async (_params, _signal) => {
      // Wrap the function to use abort signal if possible
      return fn()
    },
    { ...operationOptions, initialData: initialData ?? undefined }
  )

  // Track timeout for cleanup
  let delayTimeoutId: ReturnType<typeof setTimeout> | null = null

  // Auto-execute on mount
  if (immediate) {
    if (delay > 0) {
      delayTimeoutId = setTimeout(() => {
        delayTimeoutId = null
        operation.execute()
      }, delay)
    } else {
      operation.execute()
    }
  }

  // Cleanup on unmount to prevent memory leaks
  onUnmounted(() => {
    if (delayTimeoutId !== null) {
      clearTimeout(delayTimeoutId)
      delayTimeoutId = null
    }
  })

  return {
    ...operation,
    refresh: () => operation.execute(),
  }
}

/**
 * useDebouncedOperation - Debounced async operation
 *
 * Useful for search inputs and other rapid-fire operations.
 *
 * @example
 * ```ts
 * const { execute, loading, data } = useDebouncedOperation(
 *   async (query, signal) => searchApi(query, { signal }),
 *   { debounce: 300 }
 * )
 *
 * watch(searchQuery, (query) => execute(query))
 * ```
 */
export interface UseDebouncedOperationOptions<T> extends UseAsyncOperationOptions<T> {
  /** Debounce delay in ms */
  debounce?: number
}

export function useDebouncedOperation<T, P = void>(
  fn: AsyncOperationFn<T, P>,
  options: UseDebouncedOperationOptions<T> = {}
): UseAsyncOperationReturn<T, P> {
  const { debounce = 300, ...operationOptions } = options

  const operation = useAsyncOperation(fn, operationOptions)
  let timeoutId: ReturnType<typeof setTimeout> | null = null

  const debouncedExecute = async (params?: P): Promise<T | null> => {
    // Cancel pending debounce
    if (timeoutId) {
      clearTimeout(timeoutId)
    }

    // Cancel pending request
    operation.abort()

    return new Promise((resolve) => {
      timeoutId = setTimeout(async () => {
        const result = await operation.execute(params)
        resolve(result)
      }, debounce)
    })
  }

  // Cleanup timeout on unmount
  onUnmounted(() => {
    if (timeoutId) {
      clearTimeout(timeoutId)
    }
  })

  return {
    ...operation,
    execute: debouncedExecute,
  }
}
