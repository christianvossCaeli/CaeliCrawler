/**
 * Dashboard Widgets Module
 *
 * Re-exports all widget-related functionality
 */

// Types
export type {
  WidgetPosition,
  WidgetConfig,
  WidgetDefinition,
  DashboardPreferences,
  DashboardStats,
  ActivityItem,
  ActivityFeedResponse,
  InsightItem,
  InsightsResponse,
  ChartDataPoint,
  ChartDataResponse,
} from './types'

export { WIDGET_SIZE_OPTIONS } from './types'

// Registry
export {
  widgetRegistry,
  getWidget,
  getAllWidgets,
  getDefaultWidgets,
  sortWidgetsByPosition,
  getColumnClasses,
} from './registry'
