/**
 * Dashboard Widget Type Definitions
 */

import type { Component } from 'vue'

/**
 * Position of a widget in the grid
 */
export interface WidgetPosition {
  x: number // Column position (0-3)
  y: number // Row position
  w: number // Width in columns (1-4)
  h: number // Height in rows (1-4)
}

/**
 * Configuration for a single widget instance
 */
export interface WidgetConfig {
  id: string
  type: string
  enabled: boolean
  position: WidgetPosition
  config?: Record<string, unknown>
}

/**
 * Widget definition in the registry
 */
export interface WidgetDefinition {
  id: string
  type: string
  name: string // i18n key
  description: string // i18n key
  icon: string // mdi icon name
  defaultSize: { w: number; h: number }
  minSize: { w: number; h: number }
  maxSize: { w: number; h: number }
  component: Component
  refreshInterval?: number // in milliseconds
  configurable?: boolean
}

/**
 * Dashboard preferences from the API
 */
export interface DashboardPreferences {
  widgets: WidgetConfig[]
  updated_at?: string
}

/**
 * Dashboard statistics from the API
 */
export interface DashboardStats {
  entities: {
    total: number
    by_type: Record<string, number>
    active: number
    inactive: number
  }
  facets: {
    total: number
    verified: number
    verification_rate: number
    by_type: Record<string, number>
  }
  documents: {
    total: number
    by_status: Record<string, number>
    processing_rate: number
  }
  crawler: {
    total_jobs: number
    running_jobs: number
    completed_jobs: number
    failed_jobs: number
    total_documents: number
    avg_duration_seconds?: number
  }
  ai_tasks: {
    total: number
    running: number
    completed: number
    failed: number
    avg_confidence?: number
  }
  updated_at: string
}

/**
 * Activity item from the API
 */
export interface ActivityItem {
  id: string
  action: string
  entity_type?: string
  entity_id?: string
  entity_name?: string
  user_email?: string
  message: string
  timestamp: string
}

/**
 * Activity feed response
 */
export interface ActivityFeedResponse {
  items: ActivityItem[]
  total: number
  has_more: boolean
}

/**
 * Insight item from the API
 */
export interface InsightItem {
  type: string
  title: string
  count: number
  message: string
  entity_type?: string
  link?: string
}

/**
 * Insights response
 */
export interface InsightsResponse {
  items: InsightItem[]
  last_login?: string
  period_days: number
}

/**
 * Chart data point
 */
export interface ChartDataPoint {
  label: string
  value: number
  color?: string
}

/**
 * Chart data response
 */
export interface ChartDataResponse {
  chart_type: string
  title: string
  data: ChartDataPoint[]
  total?: number
}

/**
 * Widget size options for the configurator
 */
export const WIDGET_SIZE_OPTIONS = [
  { value: 1, label: 'dashboard.size.small', description: '1 Spalte' },
  { value: 2, label: 'dashboard.size.medium', description: '2 Spalten' },
  { value: 3, label: 'dashboard.size.large', description: '3 Spalten' },
  { value: 4, label: 'dashboard.size.full', description: '4 Spalten' },
] as const
