/**
 * TypeScript interfaces for AI Discovery components
 */

export interface DiscoverySource {
  name: string
  base_url: string
  source_type: string
  tags: string[]
  metadata: Record<string, unknown>
  confidence: number
}

export interface APISuggestion {
  api_name: string
  base_url: string
  endpoint: string
  description: string
  api_type: string
  auth_required: boolean
  confidence: number
  documentation_url?: string
}

export interface APIValidation {
  api_name: string
  is_valid: boolean
  status_code?: number
  item_count?: number
  error_message?: string
  field_mapping: Record<string, string>
}

export interface ValidatedAPISource {
  api_name: string
  api_url: string
  api_type: string
  item_count: number
  sample_items: Record<string, unknown>[]
  tags: string[]
  field_mapping: Record<string, string>
}

export interface DiscoveryResultV2 {
  api_sources: ValidatedAPISource[]
  web_sources: DiscoverySource[]
  api_suggestions: APISuggestion[]
  api_validations: APIValidation[]
  stats: Record<string, number>
  warnings: string[]
  used_fallback: boolean
  from_template: boolean
}

export interface DiscoveryExample {
  prompt: string
  description?: string
  expected_tags?: string[]
}

export interface Category {
  id: string
  name: string
}

export interface SearchStep {
  text: string
  done: boolean
  active: boolean
}

export interface TemplateFormData {
  name: string
  description: string
  keywords: string[]
  source: ValidatedAPISource | null
}
