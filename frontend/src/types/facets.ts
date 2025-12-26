/**
 * TypeScript types for Facet History (Time-Series Data)
 */

export interface HistoryDataPoint {
  id: string
  entity_id: string
  facet_type_id: string
  track_key: string
  recorded_at: string
  value: number
  value_label?: string
  annotations: Record<string, unknown>
  source_type: string
  source_document_id?: string
  source_url?: string
  confidence_score: number
  ai_model_used?: string
  human_verified: boolean
  verified_by?: string
  verified_at?: string
  created_at: string
  updated_at: string
}

export interface HistoryTrack {
  track_key: string
  label: string
  color: string
  style: 'solid' | 'dashed' | 'dotted'
  data_points: HistoryDataPoint[]
  point_count: number
}

export interface DateRange {
  from_date?: string
  to_date?: string
}

export interface HistoryStatistics {
  total_points: number
  min_value?: number
  max_value?: number
  avg_value?: number
  latest_value?: number
  oldest_value?: number
  trend: 'up' | 'down' | 'stable'
  change_percent?: number
  change_absolute?: number
}

export interface EntityHistoryResponse {
  entity_id: string
  entity_name: string
  facet_type_id: string
  facet_type_slug: string
  facet_type_name: string
  unit: string
  unit_label: string
  precision: number
  tracks: HistoryTrack[]
  date_range: DateRange
  statistics: HistoryStatistics
  total_points: number
}

export interface AggregatedDataPoint {
  interval_start: string
  interval_end: string
  track_key: string
  value: number
  point_count: number
  min_value?: number
  max_value?: number
}

export interface AggregatedHistoryResponse {
  entity_id: string
  facet_type_id: string
  interval: string
  method: string
  data: AggregatedDataPoint[]
  date_range: DateRange
}

export interface HistoryFacetTypeSchema {
  type: 'history'
  properties: {
    unit: string
    unit_label: string
    precision: number
    min_value?: number
    max_value?: number
    tracks: Record<string, {
      label: string
      color: string
      style?: string
    }>
    aggregation?: {
      default_interval: string
      allowed_intervals: string[]
      method: string
    }
    visualization?: {
      chart_type: 'line' | 'area' | 'bar'
      show_trend: boolean
      show_annotations: boolean
    }
  }
}

export interface HistoryDataPointCreate {
  recorded_at: string
  value: number
  track_key?: string
  value_label?: string
  annotations?: Record<string, unknown>
  source_type?: string
  source_url?: string
  confidence_score?: number
}

export interface HistoryBulkImport {
  data_points: HistoryDataPointCreate[]
  skip_duplicates?: boolean
}

export interface HistoryBulkImportResponse {
  created: number
  skipped: number
  errors: string[]
}
