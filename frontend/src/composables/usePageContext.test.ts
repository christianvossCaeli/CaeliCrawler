/**
 * Tests for usePageContext composable
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ref } from 'vue'
import {
  usePageContext,
  useCurrentPageContext,
  getAvailableFeaturesForRoute,
  getAvailableActionsForContext,
  PAGE_FEATURES,
  PAGE_ACTIONS,
} from './usePageContext'
import type { PageContextData } from './assistant/types'

// Mock vue-router
const mockRoute = ref({ path: '/' })
vi.mock('vue-router', () => ({
  useRoute: () => mockRoute.value,
}))

// Mock Vue lifecycle
vi.mock('vue', async () => {
  const actual = await vi.importActual('vue')
  return {
    ...actual,
    onUnmounted: vi.fn((callback) => {
      // Store callback for manual invocation in tests
      ;(global as unknown as { _unmountCallbacks: (() => void)[] })._unmountCallbacks =
        (global as unknown as { _unmountCallbacks: (() => void)[] })._unmountCallbacks || []
      ;(global as unknown as { _unmountCallbacks: (() => void)[] })._unmountCallbacks.push(callback)
    }),
  }
})

describe('usePageContext', () => {
  beforeEach(() => {
    mockRoute.value = { path: '/' }
    ;(global as unknown as { _unmountCallbacks: (() => void)[] })._unmountCallbacks = []
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('PAGE_FEATURES', () => {
    it('should have correct feature sets for each view type', () => {
      expect(PAGE_FEATURES.entityDetail).toContain('view_facets')
      expect(PAGE_FEATURES.entityDetail).toContain('edit_facets')
      expect(PAGE_FEATURES.entityDetail).toContain('pysis_analysis')

      expect(PAGE_FEATURES.entityList).toContain('filter')
      expect(PAGE_FEATURES.entityList).toContain('bulk_select')
      expect(PAGE_FEATURES.entityList).toContain('export')

      expect(PAGE_FEATURES.summary).toContain('add_widget')
      expect(PAGE_FEATURES.summary).toContain('configure_widget')

      expect(PAGE_FEATURES.category).toContain('start_crawl')
      expect(PAGE_FEATURES.category).toContain('view_entities')

      expect(PAGE_FEATURES.source).toContain('add_source')
      expect(PAGE_FEATURES.source).toContain('test_connection')

      expect(PAGE_FEATURES.smartQuery).toContain('execute_query')
      expect(PAGE_FEATURES.smartQuery).toContain('export_results')

      expect(PAGE_FEATURES.crawler).toContain('start_job')
      expect(PAGE_FEATURES.crawler).toContain('view_logs')
    })
  })

  describe('PAGE_ACTIONS', () => {
    it('should have correct action sets for each context', () => {
      expect(PAGE_ACTIONS.base).toContain('search')
      expect(PAGE_ACTIONS.base).toContain('help')
      expect(PAGE_ACTIONS.base).toContain('navigate')

      expect(PAGE_ACTIONS.entityDetail).toContain('summarize')
      expect(PAGE_ACTIONS.entityDetail).toContain('edit_entity')

      expect(PAGE_ACTIONS.facetsTab).toContain('add_facet')
      expect(PAGE_ACTIONS.facetsTab).toContain('edit_facet')

      expect(PAGE_ACTIONS.connectionsTab).toContain('add_relation')

      expect(PAGE_ACTIONS.pysisReady).toContain('enrich_facets')

      expect(PAGE_ACTIONS.summary).toContain('add_widget')
      expect(PAGE_ACTIONS.summary).toContain('refresh')

      expect(PAGE_ACTIONS.category).toContain('start_crawl')

      expect(PAGE_ACTIONS.bulkSelection).toContain('bulk_add_facet')
      expect(PAGE_ACTIONS.bulkSelection).toContain('bulk_edit')
    })
  })

  describe('usePageContext()', () => {
    it('should return context management functions', () => {
      const context = usePageContext()

      expect(context.registerContextProvider).toBeDefined()
      expect(context.unregisterContextProvider).toBeDefined()
      expect(context.updateContext).toBeDefined()
      expect(context.clearContext).toBeDefined()
      expect(context.currentPageContext).toBeDefined()
    })

    it('should register and provide context', () => {
      mockRoute.value = { path: '/entities' }

      const { registerContextProvider, currentPageContext } = usePageContext()

      const provider = (): PageContextData => ({
        entity_type: 'person',
        total_count: 10,
      })

      registerContextProvider('/entities', provider)

      expect(currentPageContext.value).toEqual({
        entity_type: 'person',
        total_count: 10,
      })
    })

    it('should unregister context provider', () => {
      mockRoute.value = { path: '/entities' }

      const { registerContextProvider, unregisterContextProvider, currentPageContext } = usePageContext()

      registerContextProvider('/entities', () => ({ entity_type: 'test' }))
      expect(currentPageContext.value?.entity_type).toBe('test')

      unregisterContextProvider('/entities')
      // After unregistering, context should be cleared on next route check
    })

    it('should update context manually', () => {
      const { updateContext, currentPageContext } = usePageContext()

      updateContext({ entity_id: '123', entity_name: 'Test Entity' })

      expect(currentPageContext.value?.entity_id).toBe('123')
      expect(currentPageContext.value?.entity_name).toBe('Test Entity')
    })

    it('should clear context', () => {
      const { updateContext, clearContext, currentPageContext } = usePageContext()

      updateContext({ entity_id: '123' })
      expect(currentPageContext.value?.entity_id).toBe('123')

      clearContext()
      expect(currentPageContext.value).toBeUndefined()
    })
  })

  describe('useCurrentPageContext()', () => {
    it('should return computed ref with current context', () => {
      const { updateContext } = usePageContext()
      const context = useCurrentPageContext()

      updateContext({ summary_id: 'sum-1', summary_name: 'Test Summary' })

      expect(context.value?.summary_id).toBe('sum-1')
      expect(context.value?.summary_name).toBe('Test Summary')
    })
  })

  describe('getAvailableFeaturesForRoute()', () => {
    it('should return entity detail features for entity detail routes', () => {
      const features = getAvailableFeaturesForRoute('/entities/person/max-mustermann')

      expect(features).toContain('view_facets')
      expect(features).toContain('edit_facets')
      expect(features).toContain('pysis_analysis')
    })

    it('should return entity list features for entity list routes', () => {
      const features = getAvailableFeaturesForRoute('/entities')

      expect(features).toContain('filter')
      expect(features).toContain('sort')
      expect(features).toContain('bulk_select')
    })

    it('should return summary features for summary routes', () => {
      const features = getAvailableFeaturesForRoute('/summaries/wind-analyse')

      expect(features).toContain('add_widget')
      expect(features).toContain('configure_widget')
      expect(features).toContain('share')
    })

    it('should return category features for category routes', () => {
      const features = getAvailableFeaturesForRoute('/categories')

      expect(features).toContain('view_entities')
      expect(features).toContain('start_crawl')
    })

    it('should return source features for source routes', () => {
      const features = getAvailableFeaturesForRoute('/sources')

      expect(features).toContain('add_source')
      expect(features).toContain('test_connection')
    })

    it('should return smart query features for smart query routes', () => {
      const features = getAvailableFeaturesForRoute('/smart-query')

      expect(features).toContain('execute_query')
      expect(features).toContain('save_query')
      expect(features).toContain('export_results')
    })

    it('should return crawler features for crawler routes', () => {
      const features = getAvailableFeaturesForRoute('/crawler')

      expect(features).toContain('start_job')
      expect(features).toContain('pause_job')
      expect(features).toContain('view_logs')
    })

    it('should return empty array for unknown routes', () => {
      const features = getAvailableFeaturesForRoute('/unknown-route')

      expect(features).toEqual([])
    })
  })

  describe('getAvailableActionsForContext()', () => {
    it('should always include base actions', () => {
      const actions = getAvailableActionsForContext('/', undefined)

      expect(actions).toContain('search')
      expect(actions).toContain('help')
      expect(actions).toContain('navigate')
    })

    it('should include entity detail actions when entity_id is present', () => {
      const context: PageContextData = {
        entity_id: '123',
      }

      const actions = getAvailableActionsForContext('/entities/person/test', context)

      expect(actions).toContain('summarize')
      expect(actions).toContain('edit_entity')
    })

    it('should include facets tab actions when on facets tab', () => {
      const context: PageContextData = {
        entity_id: '123',
        active_tab: 'facets',
      }

      const actions = getAvailableActionsForContext('/entities/person/test', context)

      expect(actions).toContain('add_facet')
      expect(actions).toContain('edit_facet')
      expect(actions).toContain('remove_facet')
    })

    it('should include connections tab actions when on connections tab', () => {
      const context: PageContextData = {
        entity_id: '123',
        active_tab: 'connections',
      }

      const actions = getAvailableActionsForContext('/entities/person/test', context)

      expect(actions).toContain('add_relation')
      expect(actions).toContain('remove_relation')
    })

    it('should include pysis actions when pysis is ready', () => {
      const context: PageContextData = {
        entity_id: '123',
        pysis_status: 'ready',
      }

      const actions = getAvailableActionsForContext('/entities/person/test', context)

      expect(actions).toContain('enrich_facets')
    })

    it('should include summary actions when summary_id is present', () => {
      const context: PageContextData = {
        summary_id: 'sum-1',
      }

      const actions = getAvailableActionsForContext('/summaries/test', context)

      expect(actions).toContain('add_widget')
      expect(actions).toContain('edit_widget')
      expect(actions).toContain('refresh')
    })

    it('should include category actions when category_id is present', () => {
      const context: PageContextData = {
        category_id: 'cat-1',
      }

      const actions = getAvailableActionsForContext('/categories', context)

      expect(actions).toContain('start_crawl')
      expect(actions).toContain('view_entities')
      expect(actions).toContain('configure')
    })

    it('should include bulk selection actions when entities are selected', () => {
      const context: PageContextData = {
        selected_count: 5,
      }

      const actions = getAvailableActionsForContext('/entities', context)

      expect(actions).toContain('bulk_add_facet')
      expect(actions).toContain('bulk_edit')
      expect(actions).toContain('bulk_export')
    })

    it('should not include bulk selection actions when no entities are selected', () => {
      const context: PageContextData = {
        selected_count: 0,
      }

      const actions = getAvailableActionsForContext('/entities', context)

      expect(actions).not.toContain('bulk_add_facet')
      expect(actions).not.toContain('bulk_edit')
    })
  })
})
