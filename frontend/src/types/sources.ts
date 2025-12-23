/**
 * TypeScript interfaces for DataSource API
 *
 * These interfaces provide type safety for DataSource CRUD operations
 * and match the backend Pydantic schemas.
 */

// =============================================================================
// Enums
// =============================================================================

/**
 * Type of data source
 */
export type SourceType =
  | 'WEBSITE'
  | 'OPARL_API'
  | 'RSS'
  | 'CUSTOM_API'
  | 'REST_API'
  | 'SPARQL_API'
  | 'SHAREPOINT'

/**
 * Status of a data source
 */
export type SourceStatus = 'PENDING' | 'ACTIVE' | 'PAUSED' | 'ERROR'

// =============================================================================
// Crawl Configuration
// =============================================================================

/**
 * Crawl configuration for a data source
 */
export interface CrawlConfig {
  // CSS selectors for finding content
  content_selector?: string | null
  link_selector?: string | null
  title_selector?: string | null
  date_selector?: string | null

  // Crawl behavior
  max_depth: number
  max_pages: number
  follow_external_links?: boolean

  // URL filtering (regex patterns)
  url_include_patterns: string[]
  url_exclude_patterns: string[]

  // File types to download
  download_extensions?: string[]

  // Custom headers
  headers?: Record<string, string>

  // JavaScript rendering
  render_javascript: boolean
  wait_for_selector?: string | null

  // News/RSS Crawler settings
  crawl_type?: string | null
  news_path?: string | null
  rss_url?: string | null
  max_articles?: number
  filter_keywords?: string[]

  // API-specific settings (for CUSTOM_API)
  api_type?: string | null
  search_query?: string | null
  wahlperiode?: number | null
  vorgangstyp?: string | null
  max_results?: number

  // Entity API settings (for REST_API and SPARQL_API)
  entity_api_type?: string | null
  entity_api_endpoint?: string | null
  entity_api_method?: string
  entity_api_query?: string | null
  entity_api_template?: string | null
  entity_field_mapping?: Record<string, string>
  entity_type_slug?: string | null
  entity_update_strategy?: 'merge' | 'replace' | 'upsert'
  entity_id_field?: string | null

  // SharePoint settings (for SHAREPOINT source type)
  site_url?: string | null
  drive_name?: string | null
  folder_path?: string | null
  file_extensions?: string[]
  recursive?: boolean
  exclude_patterns?: string[]
  max_files?: number
  file_paths_text?: string // Frontend-only: text input for file paths

  // Allow additional fields
  [key: string]: unknown
}

/**
 * Default crawl configuration values
 */
export const DEFAULT_CRAWL_CONFIG: CrawlConfig = {
  max_depth: 3,
  max_pages: 100,
  render_javascript: false,
  url_include_patterns: [],
  url_exclude_patterns: [],
  // SharePoint defaults
  site_url: '',
  drive_name: '',
  folder_path: '',
  file_extensions: ['.pdf', '.docx', '.doc', '.xlsx', '.pptx'],
  recursive: true,
  exclude_patterns: ['~$*', '*.tmp', '.DS_Store'],
  max_files: 1000,
  file_paths_text: '',
}

// =============================================================================
// Category Link
// =============================================================================

/**
 * Category link in data source (N:M relationship)
 */
export interface CategoryLink {
  id: string
  name: string
  slug: string
  is_primary: boolean
}

// =============================================================================
// Extra Data (Entity linking)
// =============================================================================

/**
 * Extra data for data source (entity linking, etc.)
 */
export interface DataSourceExtraData {
  /** Legacy single entity ID */
  entity_id?: string | null
  /** N:M: Multiple entities can be linked */
  entity_ids?: string[]
  /** Allow additional fields */
  [key: string]: unknown
}

// =============================================================================
// Data Source Models
// =============================================================================

/**
 * Base data source fields
 */
export interface DataSourceBase {
  /** Source name (1-255 characters) */
  name: string
  /** Type of data source */
  source_type: SourceType
  /** Base URL for the source */
  base_url: string
  /** API endpoint (for API sources) */
  api_endpoint?: string | null
  /** Crawl configuration */
  crawl_config: CrawlConfig
  /** Additional metadata */
  extra_data: DataSourceExtraData
  /** Crawl priority (higher = more important) */
  priority?: number
  /** Tags for filtering/categorization */
  tags: string[]
}

/**
 * Request body for creating a data source
 */
export interface DataSourceCreate extends DataSourceBase {
  /** Primary category ID (legacy) */
  category_id?: string | null
  /** List of category IDs (N:M) */
  category_ids?: string[]
  /** Authentication configuration */
  auth_config?: Record<string, unknown> | null
}

/**
 * Request body for updating a data source
 */
export interface DataSourceUpdate {
  name?: string
  source_type?: SourceType
  base_url?: string
  api_endpoint?: string | null
  crawl_config?: Partial<CrawlConfig>
  auth_config?: Record<string, unknown> | null
  extra_data?: DataSourceExtraData
  priority?: number
  status?: SourceStatus
  tags?: string[]
  /** List of category IDs (replaces existing) */
  category_ids?: string[]
  /** Primary category ID */
  primary_category_id?: string | null
}

/**
 * Data source response from API
 */
export interface DataSourceResponse extends DataSourceBase {
  /** Unique identifier */
  id: string
  /** Legacy primary category ID */
  category_id?: string | null
  /** Current status */
  status: SourceStatus
  /** Last crawl timestamp (ISO 8601) */
  last_crawl?: string | null
  /** Last change detected timestamp (ISO 8601) */
  last_change_detected?: string | null
  /** Error message if status is ERROR */
  error_message?: string | null
  /** Creation timestamp (ISO 8601) */
  created_at: string
  /** Last update timestamp (ISO 8601) */
  updated_at: string
  /** Number of documents */
  document_count: number
  /** Number of crawl jobs */
  job_count: number
  /** Primary category name (legacy) */
  category_name?: string | null
  /** All linked categories (N:M) */
  categories: CategoryLink[]
}

/**
 * Paginated list of data sources
 */
export interface DataSourceListResponse {
  items: DataSourceResponse[]
  total: number
  page: number
  per_page: number
  pages: number
}

// =============================================================================
// Bulk Import
// =============================================================================

/**
 * Single item for bulk import
 */
export interface DataSourceBulkImportItem {
  name: string
  base_url: string
  source_type?: SourceType
  tags?: string[]
  extra_data?: DataSourceExtraData
}

/**
 * Request body for bulk importing data sources
 */
export interface DataSourceBulkImport {
  /** Categories to assign (N:M) */
  category_ids: string[]
  /** Tags applied to all sources */
  default_tags?: string[]
  /** Sources to import */
  sources: DataSourceBulkImportItem[]
  /** Skip sources with duplicate URLs */
  skip_duplicates?: boolean
}

/**
 * Result of bulk import operation
 */
export interface DataSourceBulkImportResult {
  imported: number
  skipped: number
  errors: Array<{ url: string; error: string }>
}

// =============================================================================
// Source Counts & Meta
// =============================================================================

/**
 * Category with source count
 */
export interface CategoryCount {
  id: string
  name: string
  slug: string
  count: number
}

/**
 * Source type with count
 */
export interface TypeCount {
  type: SourceType | null
  count: number
}

/**
 * Source status with count
 */
export interface StatusCount {
  status: SourceStatus | null
  count: number
}

/**
 * Response for source counts endpoint
 */
export interface SourceCountsResponse {
  total: number
  categories: CategoryCount[]
  types: TypeCount[]
  statuses: StatusCount[]
}

/**
 * Tag with usage count
 */
export interface TagCount {
  tag: string
  count: number
}

/**
 * Response for available tags endpoint
 */
export interface TagsResponse {
  tags: TagCount[]
}

// =============================================================================
// Query Parameters
// =============================================================================

/**
 * Query parameters for listing data sources
 */
export interface DataSourceListParams {
  page?: number
  per_page?: number
  category_id?: string | null
  source_type?: SourceType | null
  status?: SourceStatus | null
  search?: string
  tags?: string[]
}

// =============================================================================
// SharePoint Connection Test
// =============================================================================

/**
 * SharePoint drive info
 */
export interface SharePointDrive {
  id: string
  name: string
  type: string
}

/**
 * SharePoint connection test result
 */
export interface SharePointTestResult {
  success: boolean
  message: string
  details?: {
    authentication: boolean
    sites_found: number
    target_site_accessible?: boolean
    target_site_name?: string
    drives?: SharePointDrive[]
    errors?: string[]
  }
}

// =============================================================================
// Bulk Import Preview (Frontend-only)
// =============================================================================

/**
 * Preview item for bulk import (frontend-only)
 */
export interface BulkImportPreviewItem {
  name: string
  base_url: string
  source_type: string
  tags: string[]
  allTags: string[] // combined with default_tags
  error?: string
  duplicate?: boolean
}

/**
 * Bulk import state (frontend-only)
 */
export interface BulkImportState {
  category_ids: string[]
  default_tags: string[]
  inputMode: 'text' | 'file'
  csvText: string
  csvFile: File | null
  preview: BulkImportPreviewItem[]
  validCount: number
  duplicateCount: number
  errorCount: number
  importing: boolean
  skip_duplicates: boolean
}

// =============================================================================
// Form Data (Frontend-only)
// =============================================================================

/**
 * Form data for create/edit dialog (frontend-only)
 */
export interface DataSourceFormData {
  category_id: string
  category_ids: string[]
  name: string
  source_type: SourceType
  base_url: string
  api_endpoint: string
  tags: string[]
  extra_data: DataSourceExtraData
  crawl_config: CrawlConfig
}

/**
 * Create default form data
 */
export function createDefaultFormData(): DataSourceFormData {
  return {
    category_id: '',
    category_ids: [],
    name: '',
    source_type: 'WEBSITE',
    base_url: '',
    api_endpoint: '',
    tags: [],
    extra_data: {
      entity_ids: [],
    },
    crawl_config: { ...DEFAULT_CRAWL_CONFIG },
  }
}

// =============================================================================
// Filters State (Frontend-only)
// =============================================================================

/**
 * Filters state for sources view (frontend-only)
 */
export interface SourcesFiltersState {
  category_id: string | null
  source_type: SourceType | null
  status: SourceStatus | null
  search: string
  tags: string[]
}

/**
 * Create default filters state
 */
export function createDefaultFilters(): SourcesFiltersState {
  return {
    category_id: null,
    source_type: null,
    status: null,
    search: '',
    tags: [],
  }
}

// =============================================================================
// Sidebar Counts (Frontend-only)
// =============================================================================

/**
 * Sidebar counts for sources view (frontend-only)
 */
export interface SidebarCounts {
  total: number
  categories: CategoryCount[]
  types: TypeCount[]
  statuses: StatusCount[]
}

// =============================================================================
// Source Type Options (Frontend-only)
// =============================================================================

/**
 * Source type option for select dropdown
 */
export interface SourceTypeOption {
  value: SourceType
  label: string
  icon: string
}

/**
 * Available source type options
 */
export const SOURCE_TYPE_OPTIONS: SourceTypeOption[] = [
  { value: 'WEBSITE', label: 'Website', icon: 'mdi-web' },
  { value: 'OPARL_API', label: 'OParl API', icon: 'mdi-api' },
  { value: 'RSS', label: 'RSS Feed', icon: 'mdi-rss' },
  { value: 'CUSTOM_API', label: 'Custom API', icon: 'mdi-code-json' },
  { value: 'SHAREPOINT', label: 'SharePoint', icon: 'mdi-microsoft-sharepoint' },
]

// =============================================================================
// Type Guards
// =============================================================================

/**
 * Type guard to check if a value is a valid SourceType
 */
export function isSourceType(value: unknown): value is SourceType {
  const validTypes: SourceType[] = [
    'WEBSITE',
    'OPARL_API',
    'RSS',
    'CUSTOM_API',
    'REST_API',
    'SPARQL_API',
    'SHAREPOINT',
  ]
  return typeof value === 'string' && validTypes.includes(value as SourceType)
}

/**
 * Type guard to check if a value is a valid SourceStatus
 */
export function isSourceStatus(value: unknown): value is SourceStatus {
  const validStatuses: SourceStatus[] = ['PENDING', 'ACTIVE', 'PAUSED', 'ERROR']
  return typeof value === 'string' && validStatuses.includes(value as SourceStatus)
}

/**
 * Type guard to check if an object is a DataSourceResponse
 */
export function isDataSourceResponse(obj: unknown): obj is DataSourceResponse {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'id' in obj &&
    'name' in obj &&
    'source_type' in obj &&
    'status' in obj
  )
}

// =============================================================================
// CSV Validation Constants
// =============================================================================

/** Maximum CSV file size in bytes (5MB) */
export const CSV_MAX_SIZE = 5 * 1024 * 1024

/** Maximum number of lines in CSV */
export const CSV_MAX_LINES = 10000

// =============================================================================
// API Error Types
// =============================================================================
//
// Utilities for handling API errors from Axios/fetch responses.
//
// ## Usage
// ```typescript
// import {
//   isApiError,
//   getApiErrorMessage,
//   getFieldErrors,
//   isNetworkError,
//   isRetryableError,
//   HTTP_STATUS
// } from '@/types/sources'
//
// try {
//   await api.saveData(payload)
// } catch (error) {
//   if (isNetworkError(error)) {
//     showOfflineMessage()
//   } else if (isHttpStatus(error, HTTP_STATUS.CONFLICT)) {
//     showConflictDialog()
//   } else {
//     errorMessage.value = getApiErrorMessage(error, 'Save failed')
//     fieldErrors.value = getFieldErrors(error)
//   }
// }
// ```
// =============================================================================

/**
 * HTTP status code categories for error classification
 */
export type HttpStatusCategory = 'success' | 'client_error' | 'server_error' | 'network_error'

/**
 * Common HTTP error status codes as constants
 * Use with `isHttpStatus()` for type-safe status checks
 */
export const HTTP_STATUS = {
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  UNPROCESSABLE_ENTITY: 422,
  TOO_MANY_REQUESTS: 429,
  INTERNAL_SERVER_ERROR: 500,
  BAD_GATEWAY: 502,
  SERVICE_UNAVAILABLE: 503,
} as const

/**
 * Structured API error response from Axios/fetch
 */
export interface ApiError {
  response?: {
    status: number
    data?: {
      detail?: string
      message?: string
      /** Field-level validation errors */
      errors?: Record<string, string | string[]>
      /** Pydantic validation errors format */
      detail_errors?: Array<{
        loc: (string | number)[]
        msg: string
        type: string
      }>
    }
    statusText?: string
  }
  message?: string
  code?: string // Axios error code (e.g., 'ERR_NETWORK')
  isAxiosError?: boolean
}

/**
 * Type guard to check if an error is an API error
 *
 * @param error - Unknown error to check
 * @returns True if error has API error shape (response, message, or isAxiosError)
 */
export function isApiError(error: unknown): error is ApiError {
  if (typeof error !== 'object' || error === null) {
    return false
  }
  const e = error as Record<string, unknown>
  return (
    ('response' in e && typeof e.response === 'object') ||
    ('message' in e && typeof e.message === 'string') ||
    ('isAxiosError' in e && e.isAxiosError === true)
  )
}

/**
 * Get HTTP status category from status code
 *
 * @param status - HTTP status code (or undefined for network errors)
 * @returns Category: 'success' (2xx), 'client_error' (4xx), 'server_error' (5xx), or 'network_error'
 */
export function getHttpStatusCategory(status: number | undefined): HttpStatusCategory {
  if (!status) return 'network_error'
  if (status >= 200 && status < 300) return 'success'
  if (status >= 400 && status < 500) return 'client_error'
  if (status >= 500) return 'server_error'
  return 'network_error'
}

/**
 * Check if error is a specific HTTP status
 *
 * @param error - Error to check
 * @param status - HTTP status code to match (use HTTP_STATUS constants)
 * @returns True if error has the specified status code
 *
 * @example
 * ```typescript
 * if (isHttpStatus(error, HTTP_STATUS.NOT_FOUND)) {
 *   showNotFoundMessage()
 * }
 * ```
 */
export function isHttpStatus(error: unknown, status: number): boolean {
  return isApiError(error) && error.response?.status === status
}

/**
 * Check if error is a network/connection error
 * Detects: ERR_NETWORK, ECONNABORTED, or missing response
 *
 * @param error - Error to check
 * @returns True if error indicates network connectivity issue
 */
export function isNetworkError(error: unknown): boolean {
  if (!isApiError(error)) return false
  return (
    error.code === 'ERR_NETWORK' ||
    error.code === 'ECONNABORTED' ||
    !error.response
  )
}

/**
 * Check if error should trigger a retry (network or 5xx errors)
 * Useful for implementing automatic retry logic
 *
 * @param error - Error to check
 * @returns True if error is network error, 5xx, or 429 (rate limit)
 */
export function isRetryableError(error: unknown): boolean {
  if (isNetworkError(error)) return true
  if (!isApiError(error)) return false
  const status = error.response?.status
  return status !== undefined && (status >= 500 || status === HTTP_STATUS.TOO_MANY_REQUESTS)
}

/**
 * Extract field-level validation errors from API response
 * Supports both simple error objects and Pydantic validation format
 *
 * @param error - API error to extract field errors from
 * @returns Map of field names to error messages (empty object if none)
 *
 * @example
 * ```typescript
 * const fieldErrors = getFieldErrors(error)
 * // { name: "Name is required", email: "Invalid email format" }
 *
 * // Use in form validation
 * nameError.value = fieldErrors.name || null
 * emailError.value = fieldErrors.email || null
 * ```
 */
export function getFieldErrors(error: unknown): Record<string, string> {
  if (!isApiError(error)) return {}

  const data = error.response?.data
  if (!data) return {}

  // Handle simple errors object: { errors: { field: "message" } }
  if (data.errors) {
    const result: Record<string, string> = {}
    for (const [field, msg] of Object.entries(data.errors)) {
      result[field] = Array.isArray(msg) ? msg[0] : msg
    }
    return result
  }

  // Handle Pydantic validation errors: { detail_errors: [{ loc: ["body", "field"], msg: "..." }] }
  if (data.detail_errors && Array.isArray(data.detail_errors)) {
    const result: Record<string, string> = {}
    for (const err of data.detail_errors) {
      const field = err.loc[err.loc.length - 1]?.toString() || 'unknown'
      result[field] = err.msg
    }
    return result
  }

  return {}
}

/**
 * Extract user-friendly error message from API error
 * Checks: network errors → response.data.detail → response.data.message → error.message → fallback
 *
 * @param error - Error to extract message from
 * @param fallback - Fallback message if no message can be extracted
 * @returns Human-readable error message
 *
 * @example
 * ```typescript
 * errorMessage.value = getApiErrorMessage(error, 'Operation failed')
 * ```
 */
export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (isApiError(error)) {
    // Check for network errors first
    if (isNetworkError(error)) {
      return 'Netzwerkfehler - bitte Verbindung prüfen'
    }
    // Extract message from response
    return (
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      fallback
    )
  }
  if (error instanceof Error) {
    return error.message
  }
  return fallback
}

// =============================================================================
// Bulk Import Default State
// =============================================================================

/**
 * Create default bulk import state
 */
export function createDefaultBulkImportState(): BulkImportState {
  return {
    category_ids: [],
    default_tags: [],
    inputMode: 'text',
    csvText: '',
    csvFile: null,
    preview: [],
    validCount: 0,
    duplicateCount: 0,
    errorCount: 0,
    importing: false,
    skip_duplicates: true,
  }
}

// =============================================================================
// Entity Types (for linking)
// =============================================================================

/**
 * Linked entity for source-entity relationship
 */
export interface LinkedEntity {
  id: string
  name: string
  entity_type_name?: string
  entity_type_color?: string
  entity_type_icon?: string
}
