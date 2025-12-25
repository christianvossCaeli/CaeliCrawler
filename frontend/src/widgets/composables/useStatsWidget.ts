/**
 * Composable for stats widgets with common loading, error, and navigation patterns
 */

import { ref, onMounted, type Ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '@/stores/dashboard'

export interface UseStatsWidgetOptions {
  isEditing: Ref<boolean> | boolean
}

/**
 * Unwrap a value that may be a ref or a plain value
 */
function unwrap<T>(value: Ref<T> | T): T {
  return typeof value === 'object' && value !== null && 'value' in value
    ? (value as Ref<T>).value
    : value
}

/**
 * Composable for stats-based widgets
 * Provides common state management for loading, errors, and refresh
 */
export function useStatsWidget() {
  const store = useDashboardStore()
  const loading = ref(true)
  const error = ref<string | null>(null)

  const refresh = async () => {
    loading.value = true
    error.value = null
    try {
      await store.loadStats()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load'
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    if (!store.stats) {
      refresh()
    } else {
      loading.value = false
    }
  })

  return {
    store,
    loading,
    error,
    refresh,
    stats: store.stats,
  }
}

/**
 * Composable for navigation in widgets
 */
export function useWidgetNavigation(isEditing: Ref<boolean> | boolean) {
  const router = useRouter()

  const navigateWithQuery = (path: string, query?: Record<string, string>) => {
    if (unwrap(isEditing)) return
    router.push({ path, query })
  }

  const navigateToRoute = (name: string, params?: Record<string, string>) => {
    if (unwrap(isEditing)) return
    router.push({ name, params })
  }

  const handleKeydown = (
    event: KeyboardEvent,
    callback: () => void
  ) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      callback()
    }
  }

  return {
    navigateWithQuery,
    navigateToRoute,
    handleKeydown,
  }
}
