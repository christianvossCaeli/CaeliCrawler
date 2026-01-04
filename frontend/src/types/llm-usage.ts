/**
 * LLM Usage Analytics Types
 */

export type LLMProvider = 'AZURE_OPENAI' | 'OPENAI' | 'ANTHROPIC'

export type LLMTaskType =
  | 'SUMMARIZE'
  | 'EXTRACT'
  | 'CLASSIFY'
  | 'EMBEDDING'
  | 'VISION'
  | 'CHAT'
  | 'PLAN_MODE'
  | 'DISCOVERY'
  | 'ENTITY_ANALYSIS'
  | 'ATTACHMENT_ANALYSIS'
  | 'RELEVANCE_CHECK'
  | 'CUSTOM'

export type BudgetType = 'GLOBAL' | 'CATEGORY' | 'TASK_TYPE' | 'MODEL' | 'USER'

export type LimitRequestStatus = 'PENDING' | 'APPROVED' | 'DENIED'

// === Analytics Types ===

export interface LLMUsageSummary {
  total_requests: number
  total_tokens: number
  total_prompt_tokens: number
  total_completion_tokens: number
  total_cost_cents: number
  avg_duration_ms: number
  error_count: number
  error_rate: number
}

export interface LLMUsageByModel {
  model: string
  provider: LLMProvider
  request_count: number
  total_tokens: number
  cost_cents: number
  avg_tokens_per_request: number
}

export interface LLMUsageByTask {
  task_type: LLMTaskType
  request_count: number
  total_tokens: number
  cost_cents: number
  avg_duration_ms: number
}

export interface LLMUsageByCategory {
  category_id: string | null
  category_name: string | null
  request_count: number
  total_tokens: number
  cost_cents: number
}

export interface LLMUsageTrend {
  date: string
  request_count: number
  total_tokens: number
  cost_cents: number
  error_count: number
}

export interface LLMUsageTopConsumer {
  task_name: string
  task_type: LLMTaskType
  request_count: number
  total_tokens: number
  cost_cents: number
}

export interface LLMUsageByUser {
  user_id: string | null
  user_email: string | null
  user_name: string | null
  request_count: number
  total_tokens: number
  prompt_tokens: number
  completion_tokens: number
  cost_cents: number
  models_used: string[]
  has_credentials: boolean
}

export interface LLMUsageAnalytics {
  period_start: string
  period_end: string
  summary: LLMUsageSummary
  by_model: LLMUsageByModel[]
  by_task: LLMUsageByTask[]
  by_category: LLMUsageByCategory[]
  by_user: LLMUsageByUser[]
  daily_trend: LLMUsageTrend[]
  top_consumers: LLMUsageTopConsumer[]
}

export interface LLMCostProjection {
  current_month_cost_cents: number
  projected_month_cost_cents: number
  daily_avg_cost_cents: number
  budget_warning: boolean
  budget_limit_cents: number | null
}

// === Budget Types ===

export interface LLMBudgetConfig {
  id: string
  name: string
  budget_type: BudgetType
  reference_id: string | null
  reference_value: string | null
  monthly_limit_cents: number
  warning_threshold_percent: number
  critical_threshold_percent: number
  alert_emails: string[]
  is_active: boolean
  blocks_on_limit: boolean
  last_warning_sent_at: string | null
  last_critical_sent_at: string | null
  description: string | null
  created_at: string
  updated_at: string
}

export interface BudgetStatus {
  budget_id: string
  budget_name: string
  budget_type: BudgetType
  monthly_limit_cents: number
  current_usage_cents: number
  usage_percent: number
  warning_threshold_percent: number
  critical_threshold_percent: number
  is_warning: boolean
  is_critical: boolean
  is_blocked: boolean
  blocks_on_limit: boolean
  projected_month_end_cents: number
}

export interface BudgetStatusList {
  budgets: BudgetStatus[]
  any_warning: boolean
  any_critical: boolean
  any_blocked: boolean
}

export interface BudgetAlert {
  id: string
  budget_id: string
  alert_type: 'warning' | 'critical'
  threshold_percent: number
  current_usage_cents: number
  budget_limit_cents: number
  usage_percent: number
  email_sent: boolean
  created_at: string
}

// === Request Types ===

export interface LLMBudgetCreateRequest {
  name: string
  budget_type: BudgetType
  reference_id?: string
  reference_value?: string
  monthly_limit_cents: number
  warning_threshold_percent?: number
  critical_threshold_percent?: number
  alert_emails?: string[]
  description?: string
  is_active?: boolean
}

export interface LLMBudgetUpdateRequest {
  name?: string
  monthly_limit_cents?: number
  warning_threshold_percent?: number
  critical_threshold_percent?: number
  alert_emails?: string[]
  description?: string
  is_active?: boolean
}

export interface LLMUsageQueryParams {
  period?: '24h' | '7d' | '30d' | '90d'
  provider?: LLMProvider
  model?: string
  task_type?: LLMTaskType
  category_id?: string
}

// === Utility Types ===

export type PeriodOption = {
  label: string
  value: '24h' | '7d' | '30d' | '90d'
}

export const PERIOD_OPTIONS: PeriodOption[] = [
  { label: '24 Stunden', value: '24h' },
  { label: '7 Tage', value: '7d' },
  { label: '30 Tage', value: '30d' },
  { label: '90 Tage', value: '90d' },
]

export const PROVIDER_LABELS: Record<LLMProvider, string> = {
  AZURE_OPENAI: 'Azure OpenAI',
  OPENAI: 'OpenAI',
  ANTHROPIC: 'Anthropic Claude',
}

export const TASK_TYPE_LABELS: Record<LLMTaskType, string> = {
  SUMMARIZE: 'Zusammenfassen',
  EXTRACT: 'Extrahieren',
  CLASSIFY: 'Klassifizieren',
  EMBEDDING: 'Embeddings',
  VISION: 'Bildanalyse',
  CHAT: 'Chat',
  PLAN_MODE: 'Plan Mode',
  DISCOVERY: 'Discovery',
  ENTITY_ANALYSIS: 'Entity-Analyse',
  ATTACHMENT_ANALYSIS: 'Anhang-Analyse',
  RELEVANCE_CHECK: 'Relevanz-Check',
  CUSTOM: 'Benutzerdefiniert',
}

export const BUDGET_TYPE_LABELS: Record<BudgetType, string> = {
  GLOBAL: 'Global',
  CATEGORY: 'Pro Kategorie',
  TASK_TYPE: 'Pro Task-Typ',
  MODEL: 'Pro Modell',
  USER: 'Pro Benutzer',
}

// === User Budget Types ===

export interface UserBudgetStatus {
  budget_id: string
  monthly_limit_cents: number
  current_usage_cents: number
  usage_percent: number
  is_warning: boolean
  is_critical: boolean
  is_blocked: boolean
}

export interface LimitIncreaseRequest {
  id: string
  user_id: string
  budget_id: string
  requested_limit_cents: number
  current_limit_cents: number
  reason: string
  status: LimitRequestStatus
  reviewed_by: string | null
  reviewed_at: string | null
  admin_notes: string | null
  created_at: string
  user_email?: string | null
}

export interface LimitIncreaseRequestCreate {
  requested_limit_cents: number
  reason: string
}

export interface LimitRequestListResponse {
  requests: LimitIncreaseRequest[]
  total: number
  pending_count: number
}

export const LIMIT_REQUEST_STATUS_LABELS = {
  PENDING: 'Ausstehend',
  APPROVED: 'Genehmigt',
  DENIED: 'Abgelehnt',
} satisfies Record<LimitRequestStatus, string>
