/**
 * Dashboard Widget Registry
 *
 * Central registry for all available dashboard widgets.
 * Each widget is defined with its component, default size, and metadata.
 */

import { defineAsyncComponent } from 'vue'
import type { WidgetDefinition, WidgetConfig } from './types'

/**
 * Registry of all available widgets
 */
export const widgetRegistry: Map<string, WidgetDefinition> = new Map([
  [
    'stats-entities',
    {
      id: 'stats-entities',
      type: 'stats-entities',
      name: 'dashboard.widgets.statsEntities.name',
      description: 'dashboard.widgets.statsEntities.description',
      icon: 'mdi-database',
      defaultSize: { w: 1, h: 1 },
      minSize: { w: 1, h: 1 },
      maxSize: { w: 2, h: 1 },
      component: defineAsyncComponent(
        () => import('./components/StatsEntities.vue')
      ),
      refreshInterval: 60000,
    },
  ],
  [
    'stats-facets',
    {
      id: 'stats-facets',
      type: 'stats-facets',
      name: 'dashboard.widgets.statsFacets.name',
      description: 'dashboard.widgets.statsFacets.description',
      icon: 'mdi-tag-multiple',
      defaultSize: { w: 1, h: 1 },
      minSize: { w: 1, h: 1 },
      maxSize: { w: 2, h: 1 },
      component: defineAsyncComponent(
        () => import('./components/StatsFacets.vue')
      ),
      refreshInterval: 60000,
    },
  ],
  [
    'stats-documents',
    {
      id: 'stats-documents',
      type: 'stats-documents',
      name: 'dashboard.widgets.statsDocuments.name',
      description: 'dashboard.widgets.statsDocuments.description',
      icon: 'mdi-file-document-multiple',
      defaultSize: { w: 1, h: 1 },
      minSize: { w: 1, h: 1 },
      maxSize: { w: 2, h: 1 },
      component: defineAsyncComponent(
        () => import('./components/StatsDocuments.vue')
      ),
      refreshInterval: 60000,
    },
  ],
  [
    'stats-crawler',
    {
      id: 'stats-crawler',
      type: 'stats-crawler',
      name: 'dashboard.widgets.statsCrawler.name',
      description: 'dashboard.widgets.statsCrawler.description',
      icon: 'mdi-robot',
      defaultSize: { w: 1, h: 1 },
      minSize: { w: 1, h: 1 },
      maxSize: { w: 2, h: 1 },
      component: defineAsyncComponent(
        () => import('./components/StatsCrawler.vue')
      ),
      refreshInterval: 15000,
    },
  ],
  [
    'activity-feed',
    {
      id: 'activity-feed',
      type: 'activity-feed',
      name: 'dashboard.widgets.activityFeed.name',
      description: 'dashboard.widgets.activityFeed.description',
      icon: 'mdi-history',
      defaultSize: { w: 2, h: 2 },
      minSize: { w: 2, h: 1 },
      maxSize: { w: 4, h: 3 },
      component: defineAsyncComponent(
        () => import('./components/ActivityFeed.vue')
      ),
      refreshInterval: 30000,
    },
  ],
  [
    'crawler-status',
    {
      id: 'crawler-status',
      type: 'crawler-status',
      name: 'dashboard.widgets.crawlerStatus.name',
      description: 'dashboard.widgets.crawlerStatus.description',
      icon: 'mdi-cog-sync',
      defaultSize: { w: 2, h: 2 },
      minSize: { w: 2, h: 1 },
      maxSize: { w: 4, h: 3 },
      component: defineAsyncComponent(
        () => import('./components/CrawlerStatus.vue')
      ),
      refreshInterval: 10000,
    },
  ],
  [
    'insights',
    {
      id: 'insights',
      type: 'insights',
      name: 'dashboard.widgets.insights.name',
      description: 'dashboard.widgets.insights.description',
      icon: 'mdi-lightbulb',
      defaultSize: { w: 2, h: 1 },
      minSize: { w: 2, h: 1 },
      maxSize: { w: 4, h: 2 },
      component: defineAsyncComponent(
        () => import('./components/InsightsWidget.vue')
      ),
      refreshInterval: 60000,
    },
  ],
  [
    'chart-distribution',
    {
      id: 'chart-distribution',
      type: 'chart-distribution',
      name: 'dashboard.widgets.chartDistribution.name',
      description: 'dashboard.widgets.chartDistribution.description',
      icon: 'mdi-chart-pie',
      defaultSize: { w: 2, h: 2 },
      minSize: { w: 2, h: 2 },
      maxSize: { w: 4, h: 3 },
      component: defineAsyncComponent(
        () => import('./components/ChartDistribution.vue')
      ),
      refreshInterval: 120000,
    },
  ],
  [
    'system-health',
    {
      id: 'system-health',
      type: 'system-health',
      name: 'dashboard.widgets.systemHealth.name',
      description: 'dashboard.widgets.systemHealth.description',
      icon: 'mdi-heart-pulse',
      defaultSize: { w: 2, h: 1 },
      minSize: { w: 2, h: 1 },
      maxSize: { w: 4, h: 2 },
      component: defineAsyncComponent(
        () => import('./components/SystemHealth.vue')
      ),
      refreshInterval: 30000,
    },
  ],
  [
    'favorites',
    {
      id: 'favorites',
      type: 'favorites',
      name: 'dashboard.widgets.favorites.name',
      description: 'dashboard.widgets.favorites.description',
      icon: 'mdi-star',
      defaultSize: { w: 2, h: 2 },
      minSize: { w: 1, h: 1 },
      maxSize: { w: 4, h: 3 },
      component: defineAsyncComponent(
        () => import('./components/FavoritesWidget.vue')
      ),
      refreshInterval: 60000,
    },
  ],
])

/**
 * Get a widget definition by type
 */
export function getWidget(type: string): WidgetDefinition | undefined {
  return widgetRegistry.get(type)
}

/**
 * Get all widget definitions as an array
 */
export function getAllWidgets(): WidgetDefinition[] {
  return Array.from(widgetRegistry.values())
}

/**
 * Get default widget configurations for a new user
 */
export function getDefaultWidgets(): WidgetConfig[] {
  return [
    {
      id: 'stats-entities',
      type: 'stats-entities',
      enabled: true,
      position: { x: 0, y: 0, w: 1, h: 1 },
    },
    {
      id: 'stats-facets',
      type: 'stats-facets',
      enabled: true,
      position: { x: 1, y: 0, w: 1, h: 1 },
    },
    {
      id: 'stats-documents',
      type: 'stats-documents',
      enabled: true,
      position: { x: 2, y: 0, w: 1, h: 1 },
    },
    {
      id: 'stats-crawler',
      type: 'stats-crawler',
      enabled: true,
      position: { x: 3, y: 0, w: 1, h: 1 },
    },
    {
      id: 'activity-feed',
      type: 'activity-feed',
      enabled: true,
      position: { x: 0, y: 1, w: 2, h: 2 },
    },
    {
      id: 'crawler-status',
      type: 'crawler-status',
      enabled: true,
      position: { x: 2, y: 1, w: 2, h: 2 },
    },
    {
      id: 'insights',
      type: 'insights',
      enabled: true,
      position: { x: 0, y: 3, w: 2, h: 1 },
    },
    {
      id: 'chart-distribution',
      type: 'chart-distribution',
      enabled: true,
      position: { x: 2, y: 3, w: 2, h: 2 },
    },
    {
      id: 'favorites',
      type: 'favorites',
      enabled: true,
      position: { x: 0, y: 5, w: 2, h: 2 },
    },
  ]
}

/**
 * Sort widgets by position (top to bottom, left to right)
 */
export function sortWidgetsByPosition(widgets: WidgetConfig[]): WidgetConfig[] {
  return [...widgets].sort((a, b) => {
    if (a.position.y !== b.position.y) {
      return a.position.y - b.position.y
    }
    return a.position.x - b.position.x
  })
}

/**
 * Calculate column classes for Vuetify grid based on widget width
 */
export function getColumnClasses(width: number): Record<string, number> {
  // Map widget width (1-4) to Vuetify column sizes
  const colsMap: Record<number, { cols: number; sm: number; md: number }> = {
    1: { cols: 12, sm: 6, md: 3 },
    2: { cols: 12, sm: 12, md: 6 },
    3: { cols: 12, sm: 12, md: 9 },
    4: { cols: 12, sm: 12, md: 12 },
  }

  return colsMap[width] || colsMap[1]
}
