/**
 * Runtime validation schemas using Zod.
 *
 * These schemas validate API responses at runtime to catch
 * data inconsistencies early and provide better error messages.
 */

import { z } from 'zod'

// =============================================================================
// Common Schemas
// =============================================================================

export const UUIDSchema = z.string().uuid()

export const PaginationSchema = z.object({
  page: z.number().int().min(1),
  per_page: z.number().int().min(1).max(100),
  total: z.number().int().min(0),
  pages: z.number().int().min(0),
})

// =============================================================================
// AI Discovery Schemas
// =============================================================================

export const SourceWithTagsSchema = z.object({
  name: z.string().min(1).max(500),
  base_url: z.string().url().max(2048),
  source_type: z.string().default('WEBSITE'),
  tags: z.array(z.string()).max(50).default([]),
  suggested_category_ids: z.array(z.string().uuid()).max(10).default([]),
  metadata: z.record(z.unknown()).default({}),
  confidence: z.number().min(0).max(1).default(0.5),
})

export const DiscoveryStatsSchema = z.object({
  pages_searched: z.number().int().min(0),
  sources_extracted: z.number().int().min(0),
  sources_validated: z.number().int().min(0),
  duplicates_removed: z.number().int().min(0),
})

export const DiscoveryResponseSchema = z.object({
  sources: z.array(SourceWithTagsSchema),
  search_strategy: z.object({
    search_queries: z.array(z.string()),
    expected_data_type: z.string(),
    preferred_sources: z.array(z.string()),
    entity_schema: z.record(z.string()),
    base_tags: z.array(z.string()),
  }).nullable(),
  stats: DiscoveryStatsSchema,
  warnings: z.array(z.string()),
})

export const ImportResultSchema = z.object({
  imported: z.number().int().min(0),
  skipped: z.number().int().min(0),
  errors: z.array(z.object({
    name: z.string().optional(),
    url: z.string().optional(),
    error: z.string(),
  })),
})

// =============================================================================
// API Import Schemas
// =============================================================================

export const ApiTemplateSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  api_type: z.string(),
  default_url: z.string().nullable(),
  parameters: z.record(z.unknown()),
  default_tags: z.array(z.string()),
})

export const ApiImportPreviewItemSchema = z.object({
  name: z.string(),
  base_url: z.string(),
  source_type: z.string().default('WEBSITE'),
  suggested_tags: z.array(z.string()),
  extra_data: z.record(z.unknown()),
  error: z.string().nullable(),
})

export const ApiImportPreviewResponseSchema = z.object({
  items: z.array(ApiImportPreviewItemSchema),
  total_available: z.number().int().min(0),
  field_mapping: z.record(z.string()),
  suggested_tags: z.array(z.string()),
})

// =============================================================================
// Entity Schemas
// =============================================================================

export const EntityBriefSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  slug: z.string(),
  entity_type_id: z.string().uuid(),
  entity_type_slug: z.string(),
  entity_type_name: z.string(),
})

export const EntitySchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  slug: z.string(),
  entity_type_id: z.string().uuid(),
  entity_type: z.object({
    id: z.string().uuid(),
    name: z.string(),
    slug: z.string(),
  }).optional(),
  core_attributes: z.record(z.unknown()).nullable(),
  created_at: z.string(),
  updated_at: z.string(),
})

export const EntityListResponseSchema = z.object({
  items: z.array(EntitySchema),
  total: z.number().int().min(0),
  page: z.number().int().min(1),
  per_page: z.number().int().min(1),
  pages: z.number().int().min(0),
})

// =============================================================================
// Auth Schemas
// =============================================================================

export const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  full_name: z.string().nullable(),
  role: z.enum(['admin', 'editor', 'viewer']),
  is_active: z.boolean(),
  language: z.enum(['de', 'en']).nullable(),
  created_at: z.string(),
})

export const LoginResponseSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  token_type: z.literal('bearer'),
  expires_in: z.number().int().positive(),
  refresh_expires_in: z.number().int().positive(),
  user: UserSchema,
})

export const SessionSchema = z.object({
  id: z.string(),
  device_type: z.string(),
  device_name: z.string().nullable(),
  ip_address: z.string().nullable(),
  location: z.string().nullable(),
  created_at: z.string(),
  last_used_at: z.string(),
  is_current: z.boolean(),
})

export const SessionListResponseSchema = z.object({
  sessions: z.array(SessionSchema),
  total: z.number().int().min(0),
  max_sessions: z.number().int().positive(),
})

// =============================================================================
// Dashboard Schemas
// =============================================================================

export const DashboardStatsSchema = z.object({
  total_entities: z.number().int().min(0),
  total_documents: z.number().int().min(0),
  total_sources: z.number().int().min(0),
  total_facet_values: z.number().int().min(0),
  recent_crawls: z.number().int().min(0),
  pending_verifications: z.number().int().min(0),
})

export const ActivityItemSchema = z.object({
  id: z.string(),
  action: z.string(),
  entity_type: z.string(),
  entity_id: z.string().nullable(),
  entity_name: z.string().nullable(),
  user_email: z.string().nullable(),
  timestamp: z.string(),
  details: z.record(z.unknown()).nullable(),
})

export const ActivityFeedResponseSchema = z.object({
  items: z.array(ActivityItemSchema),
  total: z.number().int().min(0),
})

// =============================================================================
// Validation Helper
// =============================================================================

/**
 * Safely parse and validate API response data.
 *
 * @param schema - Zod schema to validate against
 * @param data - Data to validate
 * @param fallback - Optional fallback value on error
 * @returns Validated data or fallback
 *
 * @example
 * const response = await api.get('/discovery')
 * const validated = safeValidate(DiscoveryResponseSchema, response.data, { sources: [], warnings: [] })
 */
export function safeValidate<T>(
  schema: z.ZodType<T>,
  data: unknown,
  fallback?: T
): T {
  const result = schema.safeParse(data)

  if (result.success) {
    return result.data
  }

  console.warn('[Validation] API response validation failed:', result.error.errors)

  if (fallback !== undefined) {
    return fallback
  }

  throw new ValidationError(
    'API response validation failed',
    result.error.errors
  )
}

/**
 * Parse and validate API response, throwing on error.
 *
 * @param schema - Zod schema to validate against
 * @param data - Data to validate
 * @returns Validated and typed data
 */
export function validateResponse<T>(schema: z.ZodType<T>, data: unknown): T {
  return schema.parse(data)
}

/**
 * Custom error for validation failures.
 */
export class ValidationError extends Error {
  public readonly issues: z.ZodIssue[]

  constructor(message: string, issues: z.ZodIssue[]) {
    super(message)
    this.name = 'ValidationError'
    this.issues = issues
  }
}

// =============================================================================
// Type Exports
// =============================================================================

export type SourceWithTags = z.infer<typeof SourceWithTagsSchema>
export type DiscoveryResponse = z.infer<typeof DiscoveryResponseSchema>
export type ImportResult = z.infer<typeof ImportResultSchema>
export type ApiTemplate = z.infer<typeof ApiTemplateSchema>
export type ApiImportPreviewResponse = z.infer<typeof ApiImportPreviewResponseSchema>
export type Entity = z.infer<typeof EntitySchema>
export type EntityListResponse = z.infer<typeof EntityListResponseSchema>
export type User = z.infer<typeof UserSchema>
export type LoginResponse = z.infer<typeof LoginResponseSchema>
export type DashboardStats = z.infer<typeof DashboardStatsSchema>
export type ActivityFeedResponse = z.infer<typeof ActivityFeedResponseSchema>
