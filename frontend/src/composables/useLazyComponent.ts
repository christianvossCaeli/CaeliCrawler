/**
 * Lazy Component Loading Composable
 *
 * Provides utilities for lazy-loading heavy components like dialogs.
 * Components are only imported when first needed, reducing initial bundle size.
 *
 * @example
 * ```typescript
 * const { AsyncAiDiscoveryDialog, dialogLoading } = useLazyDialogs()
 *
 * // In template:
 * <Suspense>
 *   <AsyncAiDiscoveryDialog v-if="showDialog" v-model="showDialog" />
 *   <template #fallback>
 *     <v-progress-circular indeterminate />
 *   </template>
 * </Suspense>
 * ```
 */

import { defineAsyncComponent, defineComponent, ref, h, type Component, type AsyncComponentLoader } from 'vue'
import { VProgressCircular, VCard, VCardText } from 'vuetify/components'

/**
 * Default loading component for async components
 */
const DefaultLoadingComponent = defineComponent({
  name: 'DefaultLoading',
  setup() {
    return () =>
      h(
        VCard,
        { class: 'd-flex align-center justify-center pa-8', flat: true },
        () => h(VProgressCircular, { indeterminate: true, color: 'primary', size: 48 })
      )
  },
})

/**
 * Default error component for failed async loads
 */
const DefaultErrorComponent = defineComponent({
  name: 'DefaultError',
  props: {
    error: { type: Error, default: null },
  },
  setup(props) {
    return () =>
      h(
        VCard,
        { class: 'pa-4 text-center', color: 'error', variant: 'tonal' },
        () =>
          h(VCardText, {}, () => [
            h('div', { class: 'text-h6 mb-2' }, 'Fehler beim Laden'),
            h('div', { class: 'text-body-2' }, props.error?.message || 'Unbekannter Fehler'),
          ])
      )
  },
})

export interface LazyComponentOptions {
  /** Delay before showing loading component (ms) */
  delay?: number
  /** Timeout before showing error (ms) */
  timeout?: number
  /** Custom loading component */
  loadingComponent?: Component
  /** Custom error component */
  errorComponent?: Component
}

/**
 * Create a lazy-loaded component with loading/error states.
 *
 * @param loader - Async component loader function
 * @param options - Configuration options
 * @returns Async component definition
 */
export function createLazyComponent<T extends Component>(
  loader: AsyncComponentLoader<T>,
  options: LazyComponentOptions = {}
): Component {
  const { delay = 200, timeout = 10000, loadingComponent, errorComponent } = options

  return defineAsyncComponent({
    loader,
    loadingComponent: loadingComponent || DefaultLoadingComponent,
    errorComponent: errorComponent || DefaultErrorComponent,
    delay,
    timeout,
  })
}

/**
 * Composable for lazy-loading heavy dialog components.
 *
 * Provides pre-configured lazy components for common dialogs.
 */
export function useLazyDialogs() {
  const dialogsLoading = ref<Record<string, boolean>>({})

  // Sources dialogs
  const AsyncAiDiscoveryDialog = createLazyComponent(
    () => import('@/components/sources/AiDiscoveryDialog.vue')
  )

  const AsyncSourceFormDialog = createLazyComponent(
    () => import('@/components/sources/SourceFormDialog.vue')
  )

  const AsyncSourcesBulkImportDialog = createLazyComponent(
    () => import('@/components/sources/SourcesBulkImportDialog.vue')
  )

  const AsyncApiImportDialog = createLazyComponent(
    () => import('@/components/sources/ApiImportDialog.vue')
  )

  return {
    // State
    dialogsLoading,

    // Source dialogs
    AsyncAiDiscoveryDialog,
    AsyncSourceFormDialog,
    AsyncSourcesBulkImportDialog,
    AsyncApiImportDialog,
  }
}

/**
 * Composable for lazy-loading visualization components.
 */
export function useLazyVisualizations() {
  const AsyncMapVisualization = createLazyComponent(
    () => import('@/components/smartquery/visualizations/MapVisualization.vue'),
    { delay: 100, timeout: 15000 }
  )

  const AsyncBarChartVisualization = createLazyComponent(
    () => import('@/components/smartquery/visualizations/BarChartVisualization.vue'),
    { delay: 100 }
  )

  const AsyncLineChartVisualization = createLazyComponent(
    () => import('@/components/smartquery/visualizations/LineChartVisualization.vue'),
    { delay: 100 }
  )

  return {
    AsyncMapVisualization,
    AsyncBarChartVisualization,
    AsyncLineChartVisualization,
  }
}
