/**
 * Smart Query Type Definitions
 *
 * Shared types used across the Smart Query composables and components.
 */

/**
 * Query mode - determines how the query is processed
 * - read: Read-only queries (search, filter, aggregate)
 * - write: Write operations (create, update, delete)
 * - plan: Interactive guide mode for prompt generation
 */
export type QueryMode = 'read' | 'write' | 'plan'

/**
 * Attachment information for uploaded files
 */
export interface AttachmentInfo {
  id: string
  filename: string
  contentType: string
  size: number
  preview?: string
}

/**
 * Visualization configuration for query results
 */
export interface SmartQueryVisualization {
  type:
    | 'table'
    | 'bar_chart'
    | 'line_chart'
    | 'pie_chart'
    | 'stat_card'
    | 'text'
    | 'comparison'
    | 'map'
    | 'calendar'
  title?: string
  subtitle?: string
  config?: Record<string, unknown>
  // Properties for compound queries
  id?: string
  data?: Record<string, unknown>[]
  source_info?: Record<string, unknown>
  explanation?: string
}

/**
 * Action suggestion from query results
 */
export interface SmartQueryAction {
  label: string
  action: string
  params: Record<string, unknown>
  icon?: string
}

/**
 * AI interpretation of the query
 */
export interface SmartQueryInterpretation {
  operation?: string
  query?: string
  entity_type?: string
  filters?: Record<string, unknown>
  [key: string]: unknown
}

/**
 * Created item from write operations
 */
export interface CreatedItem {
  id: string
  name?: string
  type: string
  entity_type?: string
  slug?: string
}

/**
 * Full query results structure
 */
export interface SmartQueryResults {
  mode: QueryMode
  success: boolean
  message?: string
  total?: number
  items?: Record<string, unknown>[]
  data?: Record<string, unknown>[] // Legacy field for result data
  created_items?: CreatedItem[]
  query_interpretation?: SmartQueryInterpretation
  interpretation?: SmartQueryInterpretation
  visualization?: SmartQueryVisualization
  visualizations?: SmartQueryVisualization[]
  is_compound?: boolean
  explanation?: string
  source_info?: Record<string, unknown>
  suggested_actions?: SmartQueryAction[]
  error?: string
  grouping?: string
}

/**
 * Preview data for write operations
 */
export interface SmartQueryPreview {
  mode: string
  success: boolean
  preview: Record<string, unknown>
  interpretation: SmartQueryInterpretation
  message?: string
}

/**
 * Loading phase for granular loading states
 */
export type LoadingPhase =
  | 'idle'
  | 'validating'
  | 'interpreting'
  | 'executing'
  | 'generating'
  | 'streaming'
  | 'processing'

/**
 * Granular loading state with phase tracking
 */
export interface LoadingState {
  isLoading: boolean
  phase: LoadingPhase
  progress?: number // 0-100 for determinate progress
  message?: string
}

/**
 * Default loading state
 */
export const DEFAULT_LOADING_STATE: LoadingState = {
  isLoading: false,
  phase: 'idle',
}

/**
 * Loading phase messages (German)
 */
export const LOADING_PHASE_MESSAGES = {
  idle: '',
  validating: 'Eingabe wird validiert...',
  interpreting: 'Anfrage wird analysiert...',
  executing: 'Abfrage wird ausgeführt...',
  generating: 'Antwort wird generiert...',
  streaming: 'Antwort wird empfangen...',
  processing: 'Ergebnisse werden verarbeitet...',
} satisfies Record<LoadingPhase, string>

/**
 * Helper function for type-safe error handling
 * Re-exported from centralized error utilities
 */
export { extractErrorMessage as getErrorDetail } from '@/utils/errorMessage'
