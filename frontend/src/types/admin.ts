/**
 * Admin API Types
 *
 * TypeScript interfaces for the Admin API endpoints.
 * Replaces `any` types for type safety and better IDE support.
 */

// =============================================================================
// Common Types
// =============================================================================

export interface PaginationParams {
  page?: number
  per_page?: number
  limit?: number
  offset?: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

// =============================================================================
// Crawler Types
// =============================================================================

export type CrawlJobStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'

export interface CrawlJob {
  id: string
  source_id: string
  source_name: string
  source_url: string
  status: CrawlJobStatus
  created_at: string
  started_at: string | null
  completed_at: string | null
  documents_found: number
  documents_processed: number
  errors_count: number
  error_message: string | null
  progress: number
  crawl_type: string
}

export interface CrawlJobListParams extends PaginationParams {
  status?: CrawlJobStatus | CrawlJobStatus[] | string
  source_id?: string
  category_id?: string
  from_date?: string
  to_date?: string
  sort_by?: 'created_at' | 'started_at' | 'completed_at' | string
  sort_order?: 'asc' | 'desc'
}

export interface CrawlStartRequest {
  source_ids?: string[]
  category_ids?: string[]
  tags?: string[]
  match_mode?: 'all' | 'any'
  force_recrawl?: boolean
  priority?: number
}

export interface CrawlerStats {
  total_jobs: number
  pending_jobs: number
  running_jobs: number
  completed_jobs: number
  failed_jobs: number
  documents_processed_today: number
  avg_processing_time_ms: number
}

export interface CrawlerStatus {
  is_running: boolean
  active_workers: number
  queue_size: number
  current_jobs: Array<{
    job_id: string
    source_name: string
    progress: number
    status: CrawlJobStatus
  }>
}

export interface RunningJob {
  job_id: string
  source_id: string
  source_name: string
  source_url: string
  status: CrawlJobStatus
  progress: number
  documents_found: number
  documents_processed: number
  started_at: string
  current_url?: string
  log_tail: string[]
}

export interface JobLogEntry {
  timestamp: string
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR'
  message: string
  data?: Record<string, unknown>
}

export interface JobLog {
  job_id: string
  entries: JobLogEntry[]
  total: number
  has_more: boolean
}

// =============================================================================
// AI Tasks Types
// =============================================================================

export type AiTaskStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'

export type AiTaskType =
  | 'DOCUMENT_ANALYSIS'
  | 'PYSIS_EXTRACTION'
  | 'PYSIS_TO_FACETS'
  | 'BATCH_ANALYSIS'
  | 'ENTITY_DATA_ANALYSIS'
  | 'ATTACHMENT_ANALYSIS'

export interface AiTask {
  id: string
  task_type: AiTaskType
  status: AiTaskStatus
  entity_id?: string
  entity_type?: string
  document_id?: string
  created_at: string
  started_at: string | null
  completed_at: string | null
  progress: number
  result?: Record<string, unknown>
  error_message: string | null
}

export interface AiTaskListParams extends PaginationParams {
  status?: AiTaskStatus | AiTaskStatus[]
  task_type?: AiTaskType | AiTaskType[]
  entity_id?: string
  from_date?: string
  to_date?: string
}

// =============================================================================
// User Management Types
// =============================================================================

export type UserRole = 'ADMIN' | 'EDITOR' | 'VIEWER'
export type UserStatus = 'ACTIVE' | 'INACTIVE' | 'SUSPENDED'

export interface User {
  id: string
  email: string
  name: string
  role: UserRole
  status: UserStatus
  language: 'de' | 'en'
  created_at: string
  last_login_at: string | null
  login_count: number
}

export interface UserListParams extends PaginationParams {
  role?: UserRole | string
  status?: UserStatus | string
  search?: string
  is_active?: boolean
}

export interface UserCreate {
  email: string
  name: string
  password: string
  role: UserRole
  language?: 'de' | 'en'
}

export interface UserUpdate {
  email?: string
  name?: string
  role?: UserRole
  status?: UserStatus
  language?: 'de' | 'en'
}

export interface UserPasswordReset {
  new_password: string
  send_notification?: boolean
}

// =============================================================================
// Location Types
// =============================================================================

export interface Location {
  id: string
  name: string
  name_local?: string
  country: string
  admin_level_1?: string
  admin_level_2?: string
  admin_level_3?: string
  latitude?: number
  longitude?: number
  population?: number
  source_count: number
  entity_count: number
  created_at: string
  updated_at: string
}

export interface LocationListParams extends PaginationParams {
  country?: string
  admin_level_1?: string
  admin_level_2?: string
  search?: string
}

export interface LocationCreate {
  name: string
  name_local?: string
  country: string
  admin_level_1?: string
  admin_level_2?: string
  admin_level_3?: string
  latitude?: number
  longitude?: number
  population?: number
}

export type LocationUpdate = Partial<LocationCreate>

// =============================================================================
// Notification Types
// =============================================================================

export type NotificationChannel = 'EMAIL' | 'WEBHOOK' | 'IN_APP' | 'MS_TEAMS'
export type NotificationEventType =
  | 'NEW_DOCUMENT'
  | 'DOCUMENT_CHANGED'
  | 'DOCUMENT_REMOVED'
  | 'CRAWL_STARTED'
  | 'CRAWL_COMPLETED'
  | 'CRAWL_FAILED'
  | 'AI_ANALYSIS_COMPLETED'
  | 'HIGH_CONFIDENCE_RESULT'
  | 'SOURCE_STATUS_CHANGED'
  | 'SOURCE_ERROR'
  | 'SUMMARY_UPDATED'
  | 'SUMMARY_RELEVANT_CHANGES'
  | 'LLM_BUDGET_WARNING'
  | 'LLM_BUDGET_CRITICAL'
  | 'LLM_BUDGET_BLOCKED'
  | 'LLM_LIMIT_REQUEST_SUBMITTED'
  | 'LLM_LIMIT_REQUEST_APPROVED'
  | 'LLM_LIMIT_REQUEST_DENIED'

export interface NotificationRule {
  id: string
  name: string
  description?: string
  event_type: NotificationEventType
  channels: NotificationChannel[]
  conditions: Record<string, unknown>
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface NotificationRuleCreate {
  name?: string
  description?: string
  event_type?: NotificationEventType | string
  channels?: NotificationChannel[] | string[]
  conditions?: Record<string, unknown>
  is_active?: boolean
}

export interface NotificationRuleUpdate {
  name?: string
  description?: string
  event_type?: NotificationEventType | string
  channels?: NotificationChannel[] | string[]
  conditions?: Record<string, unknown>
  is_active?: boolean
}

export interface Notification {
  id: string
  rule_id?: string
  event_type: NotificationEventType
  title: string
  message: string
  data?: Record<string, unknown>
  is_read: boolean
  created_at: string
  read_at?: string
}

export interface NotificationListParams extends PaginationParams {
  is_read?: boolean
  event_type?: NotificationEventType | string
  channel?: string
  status?: string
  from_date?: string
  to_date?: string
}

export interface NotificationPreferences {
  email_notifications?: boolean
  push_notifications?: boolean
  in_app_notifications?: boolean
  digest_frequency?: 'INSTANT' | 'HOURLY' | 'DAILY' | 'WEEKLY' | string
  quiet_hours_start?: string
  quiet_hours_end?: string
  subscribed_events?: NotificationEventType[] | string[]
  [key: string]: unknown
}

// =============================================================================
// PySis Types
// =============================================================================

export interface PySisTemplate {
  id: string
  name: string
  description?: string
  process_type: string
  field_definitions: PySisFieldDefinition[]
  created_at: string
  updated_at: string
}

export interface PySisFieldDefinition {
  name: string
  field_type: string
  required: boolean
  default_value?: unknown
  validation_rules?: Record<string, unknown>
  ai_prompt?: string
}

export interface PySisTemplateCreate {
  name: string
  description?: string
  process_type: string
  field_definitions: PySisFieldDefinition[]
}

export type PySisTemplateUpdate = Partial<PySisTemplateCreate>

export interface PySisTemplateListParams extends PaginationParams {
  search?: string
  process_type?: string
  is_active?: boolean
}

export interface PySisApplyTemplateRequest {
  template_id: string
  overwrite_existing?: boolean
}

export interface PySisProcess {
  id: string
  pysis_process_id: string
  location_name: string
  template_id?: string
  status: 'DRAFT' | 'ACTIVE' | 'COMPLETED' | 'ARCHIVED'
  fields: PySisField[]
  created_at: string
  updated_at: string
  last_sync_at?: string
}

export interface PySisProcessCreate {
  pysis_process_id: string
  name?: string
  template_id?: string | null
}

export interface PySisProcessUpdate {
  status?: 'DRAFT' | 'ACTIVE' | 'COMPLETED' | 'ARCHIVED'
}

export interface PySisField {
  id: string
  process_id: string
  name: string
  field_type: string
  current_value?: unknown
  ai_suggested_value?: unknown
  ai_confidence?: number
  is_ai_generated: boolean
  human_verified: boolean
  pysis_field_id?: string
  created_at: string
  updated_at: string
}

export interface PySisFieldCreate {
  name?: string
  internal_name?: string
  pysis_field_name?: string
  field_type: string
  pysis_field_id?: string
  current_value?: unknown
  ai_extraction_enabled?: boolean
  ai_extraction_prompt?: string
}

export interface PySisFieldUpdate {
  current_value?: unknown
  human_verified?: boolean
  internal_name?: string
  pysis_field_name?: string
  field_type?: string
  ai_extraction_enabled?: boolean
  ai_extraction_prompt?: string
}

export interface PySisFieldValueUpdate {
  value: unknown
  source?: string
  push_to_pysis?: boolean
}

// =============================================================================
// Dashboard Types
// =============================================================================

export interface DashboardWidget {
  id: string
  type: 'STATS' | 'CHART' | 'ACTIVITY' | 'INSIGHTS' | 'QUICK_ACTIONS' | string
  title?: string
  enabled?: boolean
  position?: { row?: number; col?: number; x?: number; y?: number; w?: number; h?: number }
  size?: { width: number; height: number }
  config?: Record<string, unknown>
}

export interface DashboardPreferences {
  widgets: DashboardWidget[]
  theme?: 'light' | 'dark' | 'system'
  layout?: 'default' | 'compact' | 'expanded'
}

export interface DashboardStats {
  total_entities: number
  total_sources: number
  total_documents: number
  total_facets: number
  crawls_today: number
  documents_analyzed_today: number
  ai_tasks_pending: number
  storage_used_bytes: number
}

export interface DashboardActivity {
  id: string
  type: 'CRAWL' | 'ANALYSIS' | 'UPDATE' | 'CREATE' | 'DELETE'
  title: string
  description: string
  entity_type?: string
  entity_id?: string
  user_name?: string
  created_at: string
}

export interface DashboardInsight {
  id: string
  type: 'INFO' | 'WARNING' | 'SUCCESS' | 'SUGGESTION'
  title: string
  message: string
  action_label?: string
  action_route?: string
  priority: number
  expires_at?: string
}

// =============================================================================
// Audit Log Types
// =============================================================================

export type AuditAction =
  | 'CREATE'
  | 'UPDATE'
  | 'DELETE'
  | 'LOGIN'
  | 'LOGOUT'
  | 'PASSWORD_CHANGE'
  | 'SETTINGS_CHANGE'
  | 'EXPORT'
  | 'IMPORT'
  | 'CRAWL_START'
  | 'CRAWL_CANCEL'

export interface AuditLogEntry {
  id: string
  action: AuditAction
  entity_type: string
  entity_id: string
  user_id: string
  user_email: string
  ip_address?: string
  user_agent?: string
  changes?: {
    before?: Record<string, unknown>
    after?: Record<string, unknown>
    fields_changed?: string[]
  }
  metadata?: Record<string, unknown>
  created_at: string
}

export interface AuditLogListParams extends PaginationParams {
  action?: AuditAction | AuditAction[]
  entity_type?: string
  entity_id?: string
  user_id?: string
  start_date?: string
  end_date?: string
}

export interface AuditStats {
  total_entries: number
  entries_today: number
  top_actions: Array<{ action: AuditAction; count: number }>
  top_users: Array<{ user_id: string; user_email: string; count: number }>
  entries_by_day: Array<{ date: string; count: number }>
}

// =============================================================================
// Version History Types
// =============================================================================

export interface VersionEntry {
  id: string
  entity_type: string
  entity_id: string
  version_number: number
  action: 'CREATE' | 'UPDATE' | 'DELETE'
  user_id: string
  user_email: string
  changes: {
    before?: Record<string, unknown>
    after?: Record<string, unknown>
    fields_changed: string[]
  }
  created_at: string
}

export interface EntityState {
  entity_type: string
  entity_id: string
  version_number: number
  state: Record<string, unknown>
  reconstructed_at: string
}
