/**
 * LLM Usage Analytics Types
 */

export type LLMProvider = 'azure_openai' | 'anthropic'

export type LLMTaskType =
  | 'summarize'
  | 'extract'
  | 'classify'
  | 'embedding'
  | 'vision'
  | 'chat'
  | 'plan_mode'
  | 'discovery'
  | 'entity_analysis'
  | 'attachment_analysis'
  | 'relevance_check'
  | 'custom'

export type BudgetType = 'global' | 'category' | 'task_type' | 'model'

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

export interface LLMUsageAnalytics {
  period_start: string
  period_end: string
  summary: LLMUsageSummary
  by_model: LLMUsageByModel[]
  by_task: LLMUsageByTask[]
  by_category: LLMUsageByCategory[]
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
  projected_month_end_cents: number
}

export interface BudgetStatusList {
  budgets: BudgetStatus[]
  any_warning: boolean
  any_critical: boolean
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
  azure_openai: 'Azure OpenAI',
  anthropic: 'Anthropic Claude',
}

export const TASK_TYPE_LABELS: Record<LLMTaskType, string> = {
  summarize: 'Zusammenfassen',
  extract: 'Extrahieren',
  classify: 'Klassifizieren',
  embedding: 'Embeddings',
  vision: 'Bildanalyse',
  chat: 'Chat',
  plan_mode: 'Plan Mode',
  discovery: 'Discovery',
  entity_analysis: 'Entity-Analyse',
  attachment_analysis: 'Anhang-Analyse',
  relevance_check: 'Relevanz-Check',
  custom: 'Benutzerdefiniert',
}

export const BUDGET_TYPE_LABELS: Record<BudgetType, string> = {
  global: 'Global',
  category: 'Pro Kategorie',
  task_type: 'Pro Task-Typ',
  model: 'Pro Modell',
}
