import { ref, computed } from 'vue'

/**
 * useLoadingState - Composable for consistent loading state management
 *
 * Provides a standardized pattern for handling initial load vs. subsequent loads,
 * enabling proper skeleton/spinner display logic.
 *
 * @example
 * ```ts
 * const { loading, initialLoad, isInitialLoading, startLoading, stopLoading } = useLoadingState()
 *
 * async function loadData() {
 *   startLoading()
 *   try {
 *     await fetchData()
 *   } finally {
 *     stopLoading()
 *   }
 * }
 *
 * // In template:
 * // <MySkeleton v-if="isInitialLoading" />
 * // <MyContent v-else :loading="loading" />
 * ```
 */
export function useLoadingState() {
  const loading = ref(false)
  const initialLoad = ref(true)

  /**
   * Whether this is the initial load (show skeleton)
   */
  const isInitialLoading = computed(() => loading.value && initialLoad.value)

  /**
   * Whether data is refreshing (show overlay or inline loader)
   */
  const isRefreshing = computed(() => loading.value && !initialLoad.value)

  /**
   * Start a loading operation
   */
  function startLoading() {
    loading.value = true
  }

  /**
   * Stop loading and mark initial load as complete
   */
  function stopLoading() {
    loading.value = false
    initialLoad.value = false
  }

  /**
   * Reset to initial state (useful for route changes)
   */
  function reset() {
    loading.value = false
    initialLoad.value = true
  }

  /**
   * Wrap an async function with loading state management
   */
  async function withLoading<T>(fn: () => Promise<T>): Promise<T> {
    startLoading()
    try {
      return await fn()
    } finally {
      stopLoading()
    }
  }

  return {
    // State
    loading,
    initialLoad,

    // Computed
    isInitialLoading,
    isRefreshing,

    // Methods
    startLoading,
    stopLoading,
    reset,
    withLoading,
  }
}
