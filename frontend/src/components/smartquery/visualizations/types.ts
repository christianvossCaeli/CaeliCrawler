/**
 * Type definitions for Smart Query visualizations.
 * These mirror the backend schemas from visualization.py
 */

export type VisualizationType =
  | 'table'
  | 'bar_chart'
  | 'line_chart'
  | 'pie_chart'
  | 'stat_card'
  | 'text'
  | 'comparison'
  | 'map'
  | 'heatmap'
  | 'calendar'

export type ColumnType =
  | 'text'
  | 'number'
  | 'date'
  | 'datetime'
  | 'currency'
  | 'percent'
  | 'boolean'
  | 'link'

export interface VisualizationColumn {
  key: string
  label: string
  type: ColumnType
  format?: string
  sortable?: boolean
  width?: string
  align?: 'left' | 'center' | 'right'
}

export interface ChartAxis {
  key: string
  label: string
  type: 'category' | 'number' | 'time'
  min?: number
  max?: number
  format?: string
}

export interface ChartSeries {
  key: string
  label: string
  color: string
  type: 'line' | 'bar' | 'area'
  stack?: string
}

export interface StatCard {
  label: string
  value: unknown
  unit?: string
  trend?: 'up' | 'down' | 'stable'
  trend_value?: string
  icon?: string
  color?: string
}

export interface ComparisonEntity {
  entity_id: string
  entity_name: string
  entity_type?: string
  facets: Record<string, unknown>
  core_attributes: Record<string, unknown>
  tags?: string[]
}

export interface VisualizationConfig {
  type: VisualizationType
  title: string
  subtitle?: string

  // For tables
  columns?: VisualizationColumn[]
  sort_column?: string
  sort_order?: 'asc' | 'desc'

  // For charts
  x_axis?: ChartAxis
  y_axis?: ChartAxis
  series?: ChartSeries[]

  // For stat cards
  cards?: StatCard[]

  // For text
  text_content?: string

  // For comparison
  entities_to_compare?: ComparisonEntity[]
  comparison_facets?: string[]
}

export interface SourceInfo {
  type: 'facet_history' | 'live_api' | 'internal'
  last_updated?: string
  data_freshness?: string
  api_name?: string
  api_url?: string
  template_id?: string
}

export interface SuggestedAction {
  label: string
  action: string
  icon?: string
  params: Record<string, unknown>
  description?: string
}

export interface QueryDataResponse {
  success: boolean
  error?: string
  data_source: 'internal' | 'external_api'
  entity_type?: string
  data: Record<string, unknown>[]
  total_count: number
  returned_count: number
  visualization?: VisualizationConfig
  explanation?: string
  source_info?: SourceInfo
  suggested_actions: SuggestedAction[]
}

/**
 * A single visualization block with its data (for compound queries)
 */
export interface VisualizationWithData {
  id: string
  title: string
  visualization?: VisualizationConfig
  data: Record<string, unknown>[]
  source_info?: SourceInfo
  explanation?: string
}

/**
 * Response for compound queries with multiple visualizations
 */
export interface CompoundQueryResponse {
  success: boolean
  is_compound: boolean
  visualizations: VisualizationWithData[]
  explanation?: string
  suggested_actions: SuggestedAction[]
}

/**
 * Get a nested value from an object using dot notation
 * e.g., getNestedValue({ facets: { points: { value: 42 } } }, 'facets.points.value') => 42
 */
export function getNestedValue(obj: Record<string, unknown>, path: string): unknown {
  return path.split('.').reduce((acc: unknown, part) => (acc as Record<string, unknown>)?.[part], obj)
}

/**
 * Format a value based on column type
 */
export function formatValue(value: unknown, type: ColumnType, format?: string): string {
  if (value === null || value === undefined) return '-'

  switch (type) {
    case 'number':
      if (typeof value === 'number') {
        // Use browser locale for consistent number formatting
        return format
          ? value.toLocaleString(undefined, { minimumFractionDigits: parseInt(format) || 0 })
          : value.toLocaleString()
      }
      return String(value)

    case 'currency':
      if (typeof value === 'number') {
        // Use browser locale; currency should ideally come from config
        return value.toLocaleString(undefined, { style: 'currency', currency: 'EUR' })
      }
      return String(value)

    case 'percent':
      if (typeof value === 'number') {
        return `${(value * 100).toFixed(1)}%`
      }
      return String(value)

    case 'date':
      try {
        const date = new Date(value)
        // Use browser locale for consistent date formatting
        return date.toLocaleDateString(undefined, {
          day: '2-digit',
          month: '2-digit',
          year: 'numeric',
        })
      } catch {
        return String(value)
      }

    case 'datetime':
      try {
        const date = new Date(value)
        // Use browser locale for consistent datetime formatting
        return date.toLocaleString(undefined, {
          day: '2-digit',
          month: '2-digit',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        })
      } catch {
        return String(value)
      }

    case 'boolean':
      // Note: These should ideally come from i18n
      return value ? '✓' : '✗'

    default:
      return String(value)
  }
}

// =============================================================================
// Shared Visualization Utilities
// =============================================================================

/**
 * Icon mapping for visualization types.
 * Used across multiple components to ensure consistent iconography.
 */
export const VISUALIZATION_ICONS: Record<VisualizationType, string> = {
  table: 'mdi-table',
  bar_chart: 'mdi-chart-bar',
  line_chart: 'mdi-chart-line',
  pie_chart: 'mdi-chart-pie',
  stat_card: 'mdi-card-text-outline',
  text: 'mdi-text',
  comparison: 'mdi-compare',
  map: 'mdi-map',
  heatmap: 'mdi-grid',
  calendar: 'mdi-calendar',
}

/**
 * Get the icon for a visualization type.
 * Falls back to a default icon if type is unknown.
 */
export function getVisualizationIcon(type?: VisualizationType): string {
  if (!type) return 'mdi-chart-box'
  return VISUALIZATION_ICONS[type] || 'mdi-chart-box'
}

/**
 * Color mapping for visualization types (for use in chips, badges, etc.)
 */
export const VISUALIZATION_COLORS: Record<VisualizationType, string> = {
  table: 'blue-grey',
  bar_chart: 'blue',
  line_chart: 'green',
  pie_chart: 'purple',
  stat_card: 'orange',
  text: 'grey',
  comparison: 'cyan',
  map: 'teal',
  heatmap: 'deep-orange',
  calendar: 'light-green',
}

/**
 * Get the color for a visualization type.
 */
export function getVisualizationColor(type?: VisualizationType): string {
  if (!type) return 'grey'
  return VISUALIZATION_COLORS[type] || 'grey'
}
