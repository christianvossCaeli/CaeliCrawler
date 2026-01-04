/**
 * Assistant Service - TypeScript Type Definitions
 *
 * This module contains all shared types and interfaces used
 * across the assistant composables.
 */

// Context for assistant interactions
export interface AssistantContext {
  current_route: string
  current_entity_id: string | null
  current_entity_type: string | null
  current_entity_name: string | null
  view_mode: 'dashboard' | 'list' | 'detail' | 'edit' | 'summary' | 'unknown'
  available_actions: string[]
  // Page-specific context data for deeper awareness
  page_data?: PageContextData
  // Index signature for compatibility with API types
  [key: string]: unknown
}

/**
 * Page-specific context data for context-aware assistant interactions.
 * This enables the assistant to understand what the user is currently viewing
 * and perform context-specific actions.
 */
export interface PageContextData {
  // Route/View Context
  current_route?: string
  view_mode?: string

  // Entity-Detail Context (EntityDetailView)
  entity_id?: string
  entity_type?: string
  entity_name?: string
  active_tab?: 'overview' | 'facets' | 'connections' | 'documents' | 'attachments'
  facets?: FacetSummary[]
  facet_count?: number
  relation_count?: number
  pysis_status?: 'none' | 'analyzing' | 'ready' | 'enriched'
  available_facet_types?: string[]

  // Summary/Dashboard Context
  summary_id?: string
  summary_name?: string
  widgets?: WidgetSummary[]

  // Category Context
  category_id?: string
  category_name?: string
  category_entity_count?: number
  crawl_status?: 'idle' | 'running' | 'paused'

  // Source Context
  source_id?: string
  source_type?: string
  source_status?: 'active' | 'error' | 'disabled'

  // Smart Query Context
  current_query?: string
  query_mode?: 'read' | 'write' | 'plan'
  query_result_count?: number

  // Crawler Context
  active_jobs?: CrawlJobSummary[]

  // List-Views Context (Entities, Documents, etc.)
  filters?: FilterState
  sort_field?: string
  sort_order?: 'asc' | 'desc'
  selected_ids?: string[]
  selected_count?: number
  total_count?: number

  // Generic Context
  available_features?: string[]
  available_actions?: string[]
}

/**
 * Summary of a facet for context awareness
 */
export interface FacetSummary {
  facet_type_slug: string
  facet_type_name: string
  value_count: number
  sample_values?: string[]
}

/**
 * Summary of a widget for context awareness
 */
export interface WidgetSummary {
  id: string
  type: string
  title: string
  position: { x: number; y: number; w: number; h: number }
}

/**
 * Summary of a crawl job for context awareness
 */
export interface CrawlJobSummary {
  job_id: string
  category_name: string
  status: string
  progress: number
}

/**
 * Filter state for list views
 */
export interface FilterState {
  entity_type?: string
  facet_filters?: Record<string, string[]>
  search_query?: string
  date_range?: { from: string; to: string }
  location_filter?: string
  category_id?: string
  entity_type_filter?: string
  extraction_type?: string
  min_confidence?: number
  human_verified_only?: boolean
  verified_filter?: boolean | null
}

/**
 * Discriminated union for response data types.
 * Each response type has specific fields, providing type safety.
 */
export type ResponseData =
  | StatusResponse
  | QueryResultResponse
  | NavigationResponse
  | ActionPreviewResponse
  | ActionConfirmedResponse
  | SmartQueryRedirectResponse
  | DiscussionResponse
  | HelpResponse
  | ErrorResponse
  | StreamingResponse
  | SuccessResponse
  | InfoResponse
  | SmartQueryResultResponse

/**
 * Base fields shared by all response types
 */
interface BaseResponse {
  message?: string
  suggested_actions?: SuggestedAction[]
}

/**
 * Status/info message response
 */
export interface StatusResponse extends BaseResponse {
  type: 'status' | 'info'
}

/**
 * Query result with items
 */
export interface QueryResultResponse extends BaseResponse {
  type: 'query_result'
  items?: QueryResultItem[]
  total?: number
  data?: {
    items?: QueryResultItem[]
    suggestions?: QuerySuggestion[]
  }
}

/**
 * Item in query results
 */
export interface QueryResultItem {
  entity_id?: string
  entity_name?: string
  name?: string
  entity_type?: string
  [key: string]: unknown
}

/**
 * Suggestion for query refinement
 */
export interface QuerySuggestion {
  type?: string
  suggestion?: string
  corrected_query?: string
}

/**
 * Navigation response to redirect user
 */
export interface NavigationResponse extends BaseResponse {
  type: 'navigation'
  target: {
    route: string
    entity_name?: string
    entity_id?: string
  }
}

/**
 * Action preview requiring confirmation
 */
export interface ActionPreviewResponse extends BaseResponse {
  type: 'action_preview'
  action: PreviewAction
  requires_confirmation: boolean
}

/**
 * Action that can be previewed
 */
export interface PreviewAction {
  action_type: string
  entity_id?: string
  entity_type?: string
  facet_type?: string
  value?: unknown
  description?: string
}

/**
 * Confirmed action result
 */
export interface ActionConfirmedResponse extends BaseResponse {
  type: 'action_confirmed'
  success: boolean
  refresh_required?: boolean
  affected_entity_id?: string
}

/**
 * Redirect to Smart Query
 */
export interface SmartQueryRedirectResponse extends BaseResponse {
  type: 'redirect_to_smart_query'
  query?: string
  mode?: 'read' | 'write' | 'plan'
}

/**
 * Discussion/analysis response
 */
export interface DiscussionResponse extends BaseResponse {
  type: 'discussion'
  analysis_type?: string
  key_points?: string[]
  recommendations?: string[]
}

/**
 * Help response with commands
 */
export interface HelpResponse extends BaseResponse {
  type: 'help'
  suggested_commands?: string[]
}

/**
 * Error response
 */
export interface ErrorResponse extends BaseResponse {
  type: 'error'
  error_code?: string
}

/**
 * Streaming response (intermediate state)
 */
export interface StreamingResponse extends BaseResponse {
  type: 'streaming'
}

/**
 * Success response for completed actions
 */
export interface SuccessResponse extends BaseResponse {
  type: 'success'
}

/**
 * Generic info response
 */
export interface InfoResponse extends BaseResponse {
  type: 'redirect'
}

/**
 * Smart Query result from external context
 */
export interface SmartQueryResultResponse extends BaseResponse {
  type: 'smart_query_result'
  total?: number
  items?: unknown[]
  mode?: 'read' | 'write'
}

export interface ConversationMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  metadata?: Record<string, unknown>
  response_type?: string
  response_data?: ResponseData
}

export interface SuggestedAction {
  label: string
  action: string
  value: string
}

export interface SlashCommand {
  command: string
  description: string
  usage: string
  examples: string[]
}

export interface AttachmentInfo {
  id: string
  filename: string
  contentType: string
  size: number
  preview?: string // Data URL for image preview
}

export interface BatchStatus {
  batch_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  processed: number
  total: number
  errors: Array<{ entity_id?: string; entity_name?: string; error: string }>
  message: string
}

export interface BatchPreviewEntity {
  entity_id: string
  entity_name: string
  entity_type: string
}

export interface Insight {
  type: string
  icon: string
  message: string
  action: {
    type: string
    value: string
  }
  priority: number
  color: string
}

export interface WizardStepOption {
  value: string
  label: string
  description?: string
  icon?: string
}

export interface WizardStepDef {
  id: string
  question: string
  input_type: 'text' | 'textarea' | 'number' | 'date' | 'select' | 'multi_select' | 'entity_search' | 'confirm'
  options?: WizardStepOption[]
  placeholder?: string
  validation?: Record<string, unknown>
  entity_type?: string
  default_value?: unknown
  required?: boolean
  help_text?: string
}

export interface WizardState {
  wizard_id: string
  wizard_type: string
  current_step_id: string
  current_step_index: number
  total_steps: number
  answers: Record<string, unknown>
  completed: boolean
  cancelled: boolean
}

export interface WizardInfo {
  type: string
  name: string
  description: string
  icon?: string
}

export interface ActiveWizard {
  state: WizardState
  currentStep: WizardStepDef
  canGoBack: boolean
  progress: number
  message: string
  name: string
  icon: string
}

export interface Reminder {
  id: string
  message: string
  title?: string
  remind_at: string
  repeat: string
  status: string
  entity_id?: string
  entity_type?: string
  entity_name?: string
  created_at: string
}

export interface QueryHistoryItem {
  id: string
  query: string
  timestamp: Date
  resultCount: number
  queryType: 'read' | 'write' | 'plan'
  isFavorite: boolean
  entityType?: string
  facetTypes?: string[]
}

/**
 * Stored message structure for local storage
 */
export interface StoredMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  metadata?: Record<string, unknown>
  response_type?: string
  response_data?: ResponseData
}

/**
 * Stored query history item structure
 */
export interface StoredQueryHistoryItem {
  id: string
  query: string
  timestamp: string
  resultCount: number
  queryType: 'read' | 'write' | 'plan'
  isFavorite: boolean
  entityType?: string
  facetTypes?: string[]
}

// API Response Types
export interface ActionResult {
  message: string
  success: boolean
  refresh_required?: boolean
  affected_entity_id?: string
}

export interface AttachmentUploadResponse {
  attachment: {
    attachment_id: string
    filename: string
    content_type: string
    size: number
  }
}

export interface BatchActionResponse {
  batch_id?: string
  affected_count: number
  message?: string
  preview?: BatchPreviewEntity[]
}

export interface WizardResponseData {
  wizard_response: {
    wizard_state: WizardState
    current_step: WizardStepDef
    can_go_back: boolean
    progress: number
    message: string
  }
  result?: {
    success: boolean
    navigate_to?: string
  }
}

export interface ApiSuggestion {
  label: string
  query: string
}

// Storage Constants
export const STORAGE_KEY = 'assistant_conversation_history'
export const QUERY_HISTORY_KEY = 'assistant_query_history'
export const MAX_HISTORY_LENGTH = 50
export const MAX_QUERY_HISTORY_LENGTH = 100
