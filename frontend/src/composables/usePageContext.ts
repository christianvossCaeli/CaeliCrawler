/**
 * Page Context Composable
 *
 * Provides a centralized registry for page-specific context data.
 * Views can register their context providers, and the assistant
 * can access the current page context for context-aware interactions.
 */
import { ref, computed, watch, onUnmounted, type ComputedRef, type WatchStopHandle } from 'vue'
import { useRoute } from 'vue-router'
import type { PageContextData } from './assistant/types'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('usePageContext')

// Global registry for context providers (singleton pattern for SSR safety)
const contextProviders = ref<Map<string, () => PageContextData>>(new Map())

// Watcher management with reference counting
let activeWatcher: WatchStopHandle | null = null
let watcherRefCount = 0

/**
 * Available features by view type - centralized for consistency
 */
export const PAGE_FEATURES = {
  entityDetail: [
    'view_facets', 'edit_facets', 'view_relations', 'add_relations',
    'view_documents', 'pysis_analysis', 'enrich_facets', 'start_crawl'
  ],
  entityList: ['filter', 'sort', 'bulk_select', 'bulk_edit', 'export', 'create'],
  summary: [
    'add_widget', 'edit_widget', 'remove_widget', 'reorder_widgets',
    'configure_widget', 'refresh_data', 'share', 'export'
  ],
  category: ['view_entities', 'start_crawl', 'configure_crawl', 'view_sources'],
  source: ['add_source', 'edit_source', 'test_connection', 'view_documents'],
  smartQuery: ['execute_query', 'save_query', 'export_results', 'create_summary'],
  crawler: ['start_job', 'pause_job', 'cancel_job', 'view_logs']
} as const

/** Type for page feature keys */
export type PageFeatureKey = keyof typeof PAGE_FEATURES

/** Type for individual features */
export type PageFeature = typeof PAGE_FEATURES[PageFeatureKey][number]

/**
 * Available actions by context - centralized for consistency
 */
export const PAGE_ACTIONS = {
  base: ['search', 'help', 'navigate'],
  entityDetail: ['summarize', 'edit_entity'],
  facetsTab: ['add_facet', 'edit_facet', 'remove_facet'],
  connectionsTab: ['add_relation', 'remove_relation'],
  pysisReady: ['enrich_facets'],
  summary: ['add_widget', 'edit_widget', 'configure_widget', 'refresh'],
  category: ['start_crawl', 'view_entities', 'configure'],
  bulkSelection: ['bulk_add_facet', 'bulk_edit', 'bulk_export']
} as const

/** Type for page action keys */
export type PageActionKey = keyof typeof PAGE_ACTIONS

/** Type for individual actions */
export type PageAction = typeof PAGE_ACTIONS[PageActionKey][number]

// Current page context (reactive)
const currentPageContext = ref<PageContextData | undefined>(undefined)

// Context loading and error states (global for all providers)
const isContextLoading = ref(false)
const contextError = ref<string | null>(null)
const lastContextUpdate = ref<Date | null>(null)

// Error callback registry
const errorCallbacks = new Map<string, (error: Error) => void>()

/**
 * Hook for registering and accessing page context
 */
export function usePageContext() {
  const route = useRoute()

  /**
   * Register a context provider for a specific route pattern.
   * The provider function will be called whenever the route matches.
   *
   * @param routePattern - Route pattern to match (supports regex or string prefix)
   * @param provider - Function that returns the current page context data
   */
  function registerContextProvider(
    routePattern: string | RegExp,
    provider: () => PageContextData
  ) {
    const key = routePattern instanceof RegExp ? routePattern.source : routePattern
    contextProviders.value.set(key, provider)

    // Update context immediately if current route matches
    updateContextForRoute(route.path)
  }

  /**
   * Unregister a context provider
   */
  function unregisterContextProvider(routePattern: string | RegExp) {
    const key = routePattern instanceof RegExp ? routePattern.source : routePattern
    contextProviders.value.delete(key)
  }

  /**
   * Update the current page context based on the current route
   */
  function updateContextForRoute(path: string) {
    isContextLoading.value = true
    contextError.value = null

    for (const [pattern, provider] of contextProviders.value) {
      // Check if pattern matches (either as prefix or regex)
      const matches =
        path.startsWith(pattern) ||
        (pattern.startsWith('^') && new RegExp(pattern).test(path))

      if (matches) {
        try {
          currentPageContext.value = provider()
          lastContextUpdate.value = new Date()
          isContextLoading.value = false
          return
        } catch (err) {
          const error = err instanceof Error ? err : new Error(String(err))
          logger.warn(`Error getting context for ${pattern}:`, error)
          contextError.value = error.message

          // Call registered error callback for this pattern
          const callback = errorCallbacks.get(pattern)
          if (callback) {
            callback(error)
          }

          isContextLoading.value = false
        }
      }
    }

    // No matching provider found
    currentPageContext.value = undefined
    isContextLoading.value = false
  }

  /**
   * Manually update the current context (for dynamic updates within a view)
   */
  function updateContext(contextData: Partial<PageContextData>) {
    currentPageContext.value = {
      ...currentPageContext.value,
      ...contextData
    }
  }

  /**
   * Clear the current context
   */
  function clearContext() {
    currentPageContext.value = undefined
  }

  // Watch for route changes and update context (reference-counted singleton)
  watcherRefCount++

  if (!activeWatcher) {
    activeWatcher = watch(
      () => route.path,
      (newPath) => {
        updateContextForRoute(newPath)
      },
      { immediate: true }
    )
  } else {
    // If watcher exists, just trigger an update for current route
    updateContextForRoute(route.path)
  }

  // Cleanup: decrement ref count and stop watcher when no more consumers
  onUnmounted(() => {
    watcherRefCount--
    if (watcherRefCount <= 0 && activeWatcher) {
      activeWatcher()
      activeWatcher = null
      watcherRefCount = 0 // Reset to prevent negative counts
    }
  })

  return {
    // Registration
    registerContextProvider,
    unregisterContextProvider,

    // Context access
    currentPageContext: computed(() => currentPageContext.value),

    // Loading and error states
    isContextLoading: computed(() => isContextLoading.value),
    contextError: computed(() => contextError.value),
    lastContextUpdate: computed(() => lastContextUpdate.value),

    // Manual updates
    updateContext,
    clearContext,

    // Clear error state
    clearError: () => { contextError.value = null }
  }
}

/**
 * Options for context provider registration
 */
export interface ContextProviderOptions {
  /** Called when an error occurs during context update */
  onError?: (error: Error) => void
}

/**
 * Hook for providing page context from a specific view.
 * Use this in view components to expose their context to the assistant.
 *
 * @param routePattern - Route pattern this view handles
 * @param contextProvider - Reactive function that returns context data
 * @param options - Optional configuration including error callback
 */
export function usePageContextProvider(
  routePattern: string | RegExp,
  contextProvider: () => PageContextData,
  options?: ContextProviderOptions
) {
  const { registerContextProvider, unregisterContextProvider, updateContext, clearContext } = usePageContext()

  // Register error callback if provided
  const key = routePattern instanceof RegExp ? routePattern.source : routePattern
  if (options?.onError) {
    errorCallbacks.set(key, options.onError)
  }

  // Register on mount
  registerContextProvider(routePattern, contextProvider)

  // Automatic cleanup on unmount (Vue 3 Composition API best practice)
  onUnmounted(() => {
    unregisterContextProvider(routePattern)
    errorCallbacks.delete(key)
    clearContext()
  })

  // Provide a way to update context dynamically
  return {
    updateContext,

    // Manual cleanup function (for edge cases)
    cleanup: () => {
      unregisterContextProvider(routePattern)
      errorCallbacks.delete(key)
      clearContext()
    }
  }
}

/**
 * Get the current page context (read-only access)
 * Use this in the assistant composable to access context.
 */
export function useCurrentPageContext(): ComputedRef<PageContextData | undefined> {
  return computed(() => currentPageContext.value)
}

/**
 * Helper to detect available features based on route
 */
export function getAvailableFeaturesForRoute(path: string): string[] {
  const features: string[] = []

  // Entity detail features
  if (path.match(/^\/entities\/[^/]+\/[^/]+$/)) {
    features.push(...PAGE_FEATURES.entityDetail)
  }

  // Entity list features
  if (path.match(/^\/entities(\/[^/]+)?$/)) {
    features.push(...PAGE_FEATURES.entityList)
  }

  // Summary features
  if (path.includes('/summaries') || path.includes('/summary-dashboard')) {
    features.push(...PAGE_FEATURES.summary)
  }

  // Category features
  if (path.includes('/categories')) {
    features.push(...PAGE_FEATURES.category)
  }

  // Source features
  if (path.includes('/sources')) {
    features.push(...PAGE_FEATURES.source)
  }

  // Smart Query features
  if (path.includes('/smart-query')) {
    features.push(...PAGE_FEATURES.smartQuery)
  }

  // Crawler features
  if (path.includes('/crawler')) {
    features.push(...PAGE_FEATURES.crawler)
  }

  return features
}

/**
 * Helper to detect available actions based on route and context
 */
export function getAvailableActionsForContext(
  _path: string,
  context?: PageContextData
): string[] {
  const actions: string[] = [...PAGE_ACTIONS.base]

  // Entity detail actions
  if (context?.entity_id) {
    actions.push(...PAGE_ACTIONS.entityDetail)

    if (context.active_tab === 'facets') {
      actions.push(...PAGE_ACTIONS.facetsTab)
    }

    if (context.active_tab === 'connections') {
      actions.push(...PAGE_ACTIONS.connectionsTab)
    }

    if (context.pysis_status === 'ready') {
      actions.push(...PAGE_ACTIONS.pysisReady)
    }
  }

  // Summary actions
  if (context?.summary_id) {
    actions.push(...PAGE_ACTIONS.summary)
  }

  // Category actions
  if (context?.category_id) {
    actions.push(...PAGE_ACTIONS.category)
  }

  // Bulk selection actions
  if (context?.selected_count && context.selected_count > 0) {
    actions.push(...PAGE_ACTIONS.bulkSelection)
  }

  return actions
}
