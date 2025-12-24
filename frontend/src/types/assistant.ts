/**
 * Assistant API Types
 *
 * TypeScript interfaces for the AI Assistant endpoints.
 * Replaces `any` types for type safety and better IDE support.
 */

// =============================================================================
// Chat Types
// =============================================================================

export type AssistantMode = 'read' | 'write'
export type AssistantLanguage = 'de' | 'en'

export interface AssistantContext {
  route?: string
  current_route?: string
  view_mode?: string
  entity_type?: string
  entity_id?: string
  category_id?: string
  filters?: Record<string, unknown>
  selected_items?: string[]
  current_data?: unknown
  [key: string]: unknown
}

export interface ConversationMessage {
  role: 'user' | 'assistant' | 'system' | string
  content: string
  timestamp?: string
  attachments?: AttachmentInfo[]
  actions?: AssistantAction[]
  metadata?: Record<string, unknown>
}

export interface AttachmentInfo {
  id: string
  filename: string
  mime_type: string
  size_bytes: number
  thumbnail_url?: string
  analysis_status?: 'PENDING' | 'ANALYZING' | 'COMPLETED' | 'FAILED'
  analysis_result?: AttachmentAnalysis
}

export interface AttachmentAnalysis {
  summary?: string
  extracted_text?: string
  detected_entities?: Array<{
    name: string
    type: string
    confidence: number
  }>
  suggested_facets?: Array<{
    facet_type_slug: string
    value: unknown
    confidence: number
  }>
}

export interface ChatRequest {
  message: string
  context: AssistantContext
  conversation_history?: ConversationMessage[]
  mode?: AssistantMode
  language?: AssistantLanguage
  attachment_ids?: string[]
}

export interface ChatResponse {
  message: string
  actions?: AssistantAction[]
  suggestions?: string[]
  insights?: AssistantInsight[]
  data?: unknown
  metadata?: {
    tokens_used?: number
    processing_time_ms?: number
    model_used?: string
  }
}

// =============================================================================
// Action Types
// =============================================================================

export type ActionType =
  | 'navigate'
  | 'create'
  | 'update'
  | 'delete'
  | 'search'
  | 'filter'
  | 'export'
  | 'analyze'
  | 'enrich'
  | 'link'
  | 'custom'

export interface AssistantAction {
  type: ActionType
  label: string
  description?: string
  icon?: string
  params: ActionParams
  confirmation_required?: boolean
  confirmation_message?: string
}

export interface ActionParams {
  entity_type?: string
  entity_id?: string
  route?: string
  query?: string
  filters?: Record<string, unknown>
  data?: Record<string, unknown>
  options?: Record<string, unknown>
}

export interface ExecuteActionRequest {
  action: AssistantAction
  context: AssistantContext
}

export interface ExecuteActionResponse {
  success: boolean
  message: string
  result?: unknown
  redirect?: string
  updates?: Array<{
    entity_type: string
    entity_id: string
    action: 'created' | 'updated' | 'deleted'
  }>
  errors?: string[]
}

// =============================================================================
// Suggestion Types
// =============================================================================

export interface SuggestionsRequest {
  route: string
  entity_type?: string
  entity_id?: string
}

export interface AssistantSuggestion {
  text: string
  category: string
  icon?: string
  priority: number
}

// =============================================================================
// Insight Types
// =============================================================================

export type InsightType = 'INFO' | 'WARNING' | 'SUCCESS' | 'SUGGESTION' | 'TREND'
export type InsightPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export interface InsightsRequest {
  route: string
  view_mode?: string
  entity_type?: string
  entity_id?: string
  language?: AssistantLanguage
}

export interface AssistantInsight {
  id: string
  type: InsightType
  priority: InsightPriority
  title: string
  message: string
  action_label?: string
  action?: AssistantAction
  data?: Record<string, unknown>
  expires_at?: string
}

// =============================================================================
// Batch Operation Types
// =============================================================================

export type BatchActionType =
  | 'update_facets'
  | 'add_relations'
  | 'remove_relations'
  | 'assign_category'
  | 'update_status'
  | 'enrich_data'
  | 'export'
  | 'delete'
  | string

export interface BatchActionRequest {
  action_type: BatchActionType
  target_filter: BatchTargetFilter
  action_data: Record<string, unknown>
  dry_run?: boolean
}

export interface BatchTargetFilter {
  entity_type_slug?: string
  entity_ids?: string[]
  location_filter?: string
  facet_filter?: Record<string, unknown>
  search_query?: string
  [key: string]: unknown
}

export interface BatchActionResponse {
  batch_id: string
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'
  total_items: number
  processed_items: number
  success_count: number
  error_count: number
  errors?: Array<{
    entity_id: string
    error: string
  }>
  started_at?: string
  completed_at?: string
  estimated_completion?: string
}

export interface BatchStatusResponse extends BatchActionResponse {
  progress_percent: number
  current_item?: string
  can_cancel: boolean
}

// =============================================================================
// Wizard Types
// =============================================================================

export type WizardType =
  | 'create_entity'
  | 'import_data'
  | 'configure_facets'
  | 'setup_relations'
  | 'bulk_update'
  | 'generate_report'

export interface Wizard {
  id: string
  type: WizardType
  name: string
  description: string
  steps: WizardStep[]
  current_step: number
  data: Record<string, unknown>
  status: 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED'
  created_at: string
  updated_at: string
}

export interface WizardStep {
  id: string
  title: string
  description?: string
  type: 'INPUT' | 'SELECT' | 'MULTI_SELECT' | 'CONFIRM' | 'PREVIEW'
  config: WizardStepConfig
  validation?: WizardValidation
  is_optional?: boolean
}

export interface WizardStepConfig {
  field_name?: string
  label?: string
  placeholder?: string
  options?: Array<{ value: string; label: string }>
  default_value?: unknown
  help_text?: string
}

export interface WizardValidation {
  required?: boolean
  min_length?: number
  max_length?: number
  pattern?: string
  custom_validator?: string
}

export interface WizardStartResponse {
  wizard_id: string
  wizard: Wizard
  first_step: WizardStep
}

export interface WizardRespondRequest {
  value: unknown
}

export interface WizardRespondResponse {
  wizard_id: string
  status: 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED'
  current_step?: number
  next_step?: WizardStep
  result?: unknown
  errors?: string[]
}

// =============================================================================
// Reminder Types
// =============================================================================

export type ReminderRepeat = 'none' | 'daily' | 'weekly' | 'monthly'
export type ReminderStatus = 'PENDING' | 'DUE' | 'DISMISSED' | 'SNOOZED'

export interface Reminder {
  id: string
  user_id: string
  title?: string
  message: string
  remind_at: string
  entity_id?: string
  entity_type?: string
  entity_name?: string
  repeat: ReminderRepeat
  status: ReminderStatus
  dismissed_at?: string
  snoozed_until?: string
  created_at: string
  updated_at: string
}

export interface ReminderCreate {
  message: string
  remind_at: string
  title?: string
  entity_id?: string
  entity_type?: string
  repeat?: ReminderRepeat
}

export interface ReminderListParams {
  status?: ReminderStatus
  include_past?: boolean
  limit?: number
}

// =============================================================================
// Create Facet Type Types
// =============================================================================

export interface CreateFacetTypeRequest {
  name: string
  slug?: string
  name_plural?: string
  description?: string
  value_type?: string
  value_schema?: Record<string, unknown>
  applicable_entity_type_slugs?: string[]
  icon?: string
  color?: string
}

export interface CreateFacetTypeResponse {
  success: boolean
  facet_type_id?: string
  facet_type_slug?: string
  message: string
  errors?: string[]
}

// =============================================================================
// Command Types
// =============================================================================

export interface AssistantCommand {
  name: string
  description: string
  category: string
  examples: string[]
  parameters?: Array<{
    name: string
    description: string
    required: boolean
    type: string
  }>
}

// =============================================================================
// Save Attachments Types
// =============================================================================

export interface SaveAttachmentsRequest {
  entity_id: string
  attachment_ids: string[]
}

export interface SaveAttachmentsResponse {
  success: boolean
  saved_count: number
  attachment_ids: string[]
  errors?: string[]
  message: string
}
