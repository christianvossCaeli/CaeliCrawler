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
  view_mode: 'dashboard' | 'list' | 'detail' | 'edit' | 'unknown'
  available_actions: string[]
  // Index signature for compatibility with API types
  [key: string]: unknown
}

/**
 * Response data structure for different response types
 */
export interface ResponseData {
  type?: string
  message?: string
  items?: unknown[]
  total?: number
  mode?: string
  action?: unknown
  requires_confirmation?: boolean
  target?: {
    route?: string
    entity_name?: string
    [key: string]: unknown
  }
  suggested_actions?: SuggestedAction[]
  // Nested data for query results
  data?: {
    items?: Array<{ entity_name?: string; name?: string; [key: string]: unknown }>
    suggestions?: Array<{ type?: string; suggestion?: string; corrected_query?: string }>
    [key: string]: unknown
  }
  // Discussion response fields
  analysis_type?: string
  key_points?: string[]
  recommendations?: string[]
  // Help response fields
  suggested_commands?: string[]
  [key: string]: unknown
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
