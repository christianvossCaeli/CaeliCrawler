/**
 * TypeScript interfaces for Category API
 *
 * These interfaces provide type safety for Category CRUD operations
 * and match the backend Pydantic schemas.
 */

/**
 * Valid extraction handler types
 */
export type ExtractionHandler = 'default' | 'event';

/**
 * ISO 639-1 language codes supported by the system
 */
export type LanguageCode = 'de' | 'en' | 'fr' | 'nl' | 'it' | 'es' | 'pl' | 'da' | 'pt' | 'sv' | 'no' | 'fi' | 'cs' | 'hu' | 'ro' | 'bg' | 'el' | 'tr' | 'ru' | 'uk' | 'ar' | 'zh' | 'ja' | 'ko' | string;

/**
 * Base category fields shared between create/update/response
 */
export interface CategoryBase {
  /** Category name (1-255 characters) */
  name: string;
  /** Optional description */
  description?: string | null;
  /** Purpose of this category (e.g., "Windkraft-Restriktionen analysieren") */
  purpose: string;
  /** Search terms for document matching */
  search_terms: string[];
  /** Document types to search for (e.g., ["html", "pdf"]) */
  document_types: string[];
  /** Regex patterns - URLs must match at least one (if set) */
  url_include_patterns: string[];
  /** Regex patterns - URLs matching any will be skipped */
  url_exclude_patterns: string[];
  /** Language codes (ISO 639-1) for this category */
  languages: LanguageCode[];
  /** Custom AI extraction prompt (JSON format) */
  ai_extraction_prompt?: string | null;
  /** Handler for processing extractions */
  extraction_handler: ExtractionHandler;
  /** Cron expression for scheduled crawls (5 or 6 fields, e.g., "0 2 * * *") */
  schedule_cron: string;
  /** If true, automatic crawls are enabled based on schedule_cron. Must be explicitly set. */
  schedule_enabled: boolean;
  /** If true, visible to all users */
  is_public: boolean;
  /** Target EntityType for extracted entities */
  target_entity_type_id?: string | null;
}

/**
 * Request body for creating a new category
 * All base fields are optional except name and purpose
 */
export interface CategoryCreate {
  /** Category name (1-255 characters) */
  name: string;
  /** Optional description */
  description?: string | null;
  /** Purpose of this category */
  purpose: string;
  /** Search terms for document matching */
  search_terms: string[];
  /** Document types to search for */
  document_types: string[];
  /** Regex patterns - URLs must match at least one (if set) */
  url_include_patterns?: string[];
  /** Regex patterns - URLs matching any will be skipped */
  url_exclude_patterns?: string[];
  /** Language codes for this category */
  languages: LanguageCode[];
  /** Custom AI extraction prompt */
  ai_extraction_prompt?: string | null;
  /** Handler for processing extractions (defaults to 'default') */
  extraction_handler?: ExtractionHandler;
  /** Cron expression for scheduled crawls */
  schedule_cron?: string;
  /** If true, automatic crawls are enabled based on schedule_cron */
  schedule_enabled?: boolean;
  /** If true, visible to all users */
  is_public?: boolean;
  /** Target EntityType for extracted entities */
  target_entity_type_id?: string | null;
  /** URL-friendly slug (auto-generated if not provided) */
  slug?: string | null;
}

/**
 * Request body for updating a category
 * Explicit interface to prevent updating immutable fields like id, slug, timestamps
 */
export interface CategoryUpdate {
  /** Category name (1-255 characters) */
  name?: string;
  /** Optional description */
  description?: string | null;
  /** Purpose of this category */
  purpose?: string;
  /** Search terms for document matching */
  search_terms?: string[];
  /** Document types to search for */
  document_types?: string[];
  /** Regex patterns - URLs must match at least one (if set) */
  url_include_patterns?: string[];
  /** Regex patterns - URLs matching any will be skipped */
  url_exclude_patterns?: string[];
  /** Language codes for this category */
  languages?: LanguageCode[];
  /** Custom AI extraction prompt */
  ai_extraction_prompt?: string | null;
  /** Handler for processing extractions */
  extraction_handler?: ExtractionHandler;
  /** Cron expression for scheduled crawls */
  schedule_cron?: string;
  /** If true, automatic crawls are enabled */
  schedule_enabled?: boolean;
  /** If true, visible to all users */
  is_public?: boolean;
  /** Target EntityType for extracted entities */
  target_entity_type_id?: string | null;
}

/**
 * Category response from API
 */
export interface CategoryResponse extends CategoryBase {
  /** Unique identifier */
  id: string;
  /** URL-friendly slug */
  slug: string;
  /** Creation timestamp (ISO 8601) */
  created_at: string;
  /** Last update timestamp (ISO 8601) */
  updated_at: string;
  /** User who created this category */
  created_by_id?: string | null;
  /** User who owns this category */
  owner_id?: string | null;
  /** Number of linked data sources */
  source_count: number;
  /** Number of crawled documents */
  document_count: number;
  /** Target entity type (populated when queried) */
  target_entity_type?: {
    id: string;
    name: string;
    slug?: string;
  } | null;
}

/**
 * Paginated list of categories
 */
export interface CategoryListResponse {
  /** List of categories */
  items: CategoryResponse[];
  /** Total number of categories (before pagination) */
  total: number;
  /** Current page number (1-based) */
  page: number;
  /** Items per page */
  per_page: number;
  /** Total number of pages */
  pages: number;
}

/**
 * Category statistics
 */
export interface CategoryStats {
  /** Category ID */
  id: string;
  /** Category name */
  name: string;
  /** Number of linked data sources */
  source_count: number;
  /** Number of crawled documents */
  document_count: number;
  /** Number of extracted data items */
  extracted_count: number;
  /** Last successful crawl timestamp (ISO 8601) */
  last_crawl?: string | null;
  /** Number of currently running jobs */
  active_jobs: number;
}

/**
 * Query parameters for listing categories
 */
export interface CategoryListParams {
  /** Page number (1-based) */
  page?: number;
  /** Items per page (1-100) */
  per_page?: number;
  /** Filter by scheduled categories only */
  scheduled_only?: boolean;
  /** Filter by public/private visibility */
  is_public?: boolean;
  /** Include user's private categories */
  include_private?: boolean;
  /** Search in name and description */
  search?: string;
}

/**
 * Parameters for starting a crawl
 */
export interface StartCrawlParams {
  /** Category ID to crawl */
  category_id: string;
  /** Filter sources by search term */
  search?: string;
  /** Filter sources by status */
  status?: 'ACTIVE' | 'PENDING' | 'ERROR' | 'PAUSED';
  /** Filter sources by type */
  source_type?: 'WEBSITE' | 'OPARL_API' | 'RSS' | 'CUSTOM_API' | 'SHAREPOINT';
  /** Maximum number of sources to crawl */
  limit?: number;
}

/**
 * Parameters for reanalyzing documents
 */
export interface ReanalyzeParams {
  /** Category ID */
  category_id: string;
  /** If true, reanalyze all documents; if false, only low-confidence ones */
  reanalyze_all?: boolean;
}

/**
 * API error response
 */
export interface CategoryApiError {
  /** Error message */
  message: string;
  /** HTTP status code */
  status_code: number;
  /** Detailed error description */
  detail?: string | null;
  /** Error code for programmatic handling */
  code?: string | null;
}

/**
 * Type guard to check if an error is a CategoryApiError
 */
export function isCategoryApiError(error: unknown): error is CategoryApiError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'message' in error &&
    'status_code' in error
  );
}

/**
 * Query parameters for listing documents
 */
export interface DocumentListParams {
  /** Filter by category ID */
  category_id?: string;
  /** Filter by source ID */
  source_id?: string;
  /** Filter by location */
  location?: string;
  /** Filter by status */
  status?: string;
  /** Filter by processing status */
  processing_status?: string;
  /** Filter from date (ISO 8601) */
  from_date?: string;
  /** Filter to date (ISO 8601) */
  to_date?: string;
  /** Page number (1-based) */
  page?: number;
  /** Items per page */
  per_page?: number;
  /** Search in document content */
  search?: string;
  /** Sort by field */
  sort_by?: string;
  /** Sort order */
  sort_order?: 'asc' | 'desc';
}

/**
 * Query parameters for export
 */
export interface ExportListParams {
  /** Filter from date (ISO 8601) */
  from_date?: string;
  /** Filter to date (ISO 8601) */
  to_date?: string;
  /** Filter by entity type */
  entity_type?: string;
  /** Limit number of results */
  limit?: number;
}

// ============================================
// AI Preview Types
// ============================================

/**
 * Suggested facet type from AI generation
 */
export interface SuggestedFacetType {
  /** Whether this facet type is selected for creation */
  selected?: boolean;
  /** Facet type name */
  name?: string;
  /** URL-friendly slug */
  slug?: string;
  /** Description of the facet type */
  description?: string;
  /** Icon identifier */
  icon?: string;
  /** Color hex code */
  color?: string;
  /** Whether this is a new facet type to create */
  is_new?: boolean;
}

/**
 * Suggested entity type from AI generation
 */
export interface SuggestedEntityType {
  /** Entity type name */
  name?: string;
  /** Description */
  description?: string;
  /** Whether this is a new entity type to create */
  is_new?: boolean;
  /** Existing entity type ID (if not new) */
  id?: string;
}

/**
 * Existing entity type option for selection
 */
export interface ExistingEntityType {
  /** Entity type ID */
  id?: string;
  /** Entity type name */
  name?: string;
  /** URL-friendly slug */
  slug?: string;
  /** Description */
  description?: string;
}

/**
 * AI Preview data from category AI setup endpoint
 * All fields optional as they come from AI generation
 */
export interface CategoryAiPreviewData {
  /** AI-generated extraction prompt */
  suggested_extraction_prompt?: string;
  /** Suggested facet types to create */
  suggested_facet_types?: SuggestedFacetType[];
  /** Suggested entity type configuration */
  suggested_entity_type?: SuggestedEntityType;
  /** Suggested search terms for crawling */
  suggested_search_terms?: string[];
  /** Suggested URL include patterns */
  suggested_url_include_patterns?: string[];
  /** Suggested URL exclude patterns */
  suggested_url_exclude_patterns?: string[];
  /** Existing entity types for selection */
  existing_entity_types?: ExistingEntityType[];
}

/**
 * AI Prefill suggestion from Smart Write preview (create_category_setup)
 */
export interface CategoryAiPrefillSuggestion {
  /** Suggested category name */
  name?: string;
  /** Suggested purpose */
  purpose?: string;
  /** Optional description */
  description?: string;
  /** Suggested search terms */
  search_terms?: string[];
  /** Suggested document types */
  document_types?: string[];
  /** Suggested languages */
  languages?: LanguageCode[];
  /** Suggested schedule cron */
  schedule_cron?: string;
  /** Suggested schedule enabled flag */
  schedule_enabled?: boolean;
  /** Suggested include patterns */
  url_include_patterns?: string[];
  /** Suggested exclude patterns */
  url_exclude_patterns?: string[];
  /** Suggested geographic filter */
  geographic_filter?: {
    country?: string;
    admin_level_1?: string;
    admin_level_2?: string;
  };
  /** Suggested time focus */
  time_focus?: string;
  /** Suggested target entity types */
  target_entity_types?: string[];
}

/**
 * Adapted AI preview data with required fields for CategoryAiPreviewDialog
 * Ensures all required fields have default values
 */
export interface AdaptedCategoryAiPreviewData {
  /** AI-generated extraction prompt */
  suggested_extraction_prompt?: string;
  /** Facet types with required name/slug fields */
  suggested_facet_types: Array<{
    selected?: boolean;
    name: string;
    slug: string;
    description?: string;
    icon?: string;
    color?: string;
    is_new?: boolean;
  }>;
  /** Entity type with required name field */
  suggested_entity_type: {
    name: string;
    description?: string;
    is_new?: boolean;
    id?: string;
  };
  /** Suggested search terms */
  suggested_search_terms?: string[];
  /** Suggested URL include patterns */
  suggested_url_include_patterns?: string[];
  /** Suggested URL exclude patterns */
  suggested_url_exclude_patterns?: string[];
  /** Existing entity types with required id/name */
  existing_entity_types: Array<{
    id: string;
    name: string;
    slug?: string;
    description?: string;
  }>;
}

/**
 * Helper function to adapt AI preview data to required format
 */
export function adaptCategoryAiPreviewData(
  data: CategoryAiPreviewData | null
): AdaptedCategoryAiPreviewData | null {
  if (!data) return null;

  return {
    ...data,
    suggested_entity_type: {
      name: data.suggested_entity_type?.name || 'Unbekannt',
      description: data.suggested_entity_type?.description,
      is_new: data.suggested_entity_type?.is_new,
      id: data.suggested_entity_type?.id,
    },
    suggested_facet_types: (data.suggested_facet_types || []).map((ft) => ({
      ...ft,
      name: ft.name || '',
      slug: ft.slug || '',
    })),
    existing_entity_types: (data.existing_entity_types || []).map((et) => ({
      id: et.id || '',
      name: et.name || '',
      slug: et.slug,
      description: et.description,
    })),
  };
}

// ============================================
// Form Types
// ============================================

/**
 * Category form data for create/edit operations
 */
export interface CategoryFormData {
  /** Category name */
  name: string;
  /** Description */
  description: string;
  /** Purpose of this category */
  purpose: string;
  /** Search terms for crawling */
  search_terms: string[];
  /** Document types to search for */
  document_types: string[];
  /** Language codes */
  languages: LanguageCode[];
  /** URL include patterns (regex) */
  url_include_patterns: string[];
  /** URL exclude patterns (regex) */
  url_exclude_patterns: string[];
  /** Cron schedule expression */
  schedule_cron: string;
  /** Whether schedule is enabled */
  schedule_enabled: boolean;
  /** AI extraction prompt */
  ai_extraction_prompt: string;
  /** Handler for processing extractions */
  extraction_handler: ExtractionHandler;
  /** If true, visible to all users */
  is_public: boolean;
  /** Target EntityType ID for extracted entities */
  target_entity_type_id: string | null;
}

/**
 * Default form data for new category
 */
export const DEFAULT_CATEGORY_FORM_DATA: CategoryFormData = {
  name: '',
  description: '',
  purpose: '',
  search_terms: [],
  document_types: [],
  languages: ['de'],
  url_include_patterns: [],
  url_exclude_patterns: [],
  schedule_cron: '0 2 * * *',
  schedule_enabled: false,
  ai_extraction_prompt: '',
  extraction_handler: 'default',
  is_public: false,
  target_entity_type_id: null,
};

/**
 * Category filter state
 */
export interface CategoryFilters {
  /** Search query */
  search: string;
  /** Status filter (active/inactive/paused) */
  status: string | null;
  /** Scheduled filter (scheduled/not-scheduled) */
  scheduled: string | null;
  /** Has documents filter (with/without) */
  hasDocuments: string | null;
  /** Language filter */
  language: string | null;
}

/**
 * Default filter state
 */
export const DEFAULT_CATEGORY_FILTERS: CategoryFilters = {
  search: '',
  status: null,
  scheduled: null,
  hasDocuments: null,
  language: null,
};

// ============================================
// Composable State Types
// ============================================

/**
 * Category source item for display
 */
export interface CategorySource {
  /** Source ID */
  id: string;
  /** Source name */
  name: string;
  /** Source status */
  status?: string;
  /** Source type */
  source_type?: string;
  /** Base URL */
  base_url?: string;
  /** Tags assigned to the source */
  tags?: string[];
  /** Document count */
  document_count?: number;
  /** Last crawl timestamp */
  last_crawled_at?: string;
  /** Whether source is assigned to category */
  is_assigned?: boolean;
}

/**
 * Data sources tab state for category editing
 */
export interface DataSourcesTabState {
  /** Selected tag names for filtering */
  selectedTags: string[];
  /** Match mode for tags (all = AND, any = OR) */
  matchMode: 'all' | 'any';
  /** Sources found by tag search */
  foundSources: CategorySource[];
  /** Loading state */
  loading: boolean;
  /** Assigning state */
  assigning: boolean;
  /** Available tags for selection */
  availableTags: string[];
  /** Pending source IDs for create mode (to be assigned after save) */
  pendingSourceIds: string[];
  /** Directly selected sources via autocomplete */
  directSelectedSources: CategorySource[];
  /** Search results for direct source search */
  sourceSearchResults: CategorySource[];
  /** Loading state for direct source search */
  searchingDirectSources: boolean;
  /** Currently assigned sources (for edit mode) */
  assignedSources: CategorySource[];
  /** Total count of assigned sources */
  assignedSourcesTotal: number;
  /** Loading state for assigned sources */
  assignedSourcesLoading: boolean;
  /** Current page for assigned sources */
  assignedSourcesPage: number;
  /** Items per page for assigned sources */
  assignedSourcesPerPage: number;
  /** Search query for assigned sources */
  assignedSourcesSearch: string;
  /** Tag filter for assigned sources */
  assignedSourcesTagFilter: string[];
  /** Available tags in assigned sources */
  availableTagsInAssigned: string[];
}

/**
 * Default data sources tab state
 */
export const DEFAULT_DATA_SOURCES_TAB_STATE: DataSourcesTabState = {
  selectedTags: [],
  matchMode: 'all',
  foundSources: [],
  loading: false,
  assigning: false,
  availableTags: [],
  pendingSourceIds: [],
  directSelectedSources: [],
  sourceSearchResults: [],
  searchingDirectSources: false,
  assignedSources: [],
  assignedSourcesTotal: 0,
  assignedSourcesLoading: false,
  assignedSourcesPage: 1,
  assignedSourcesPerPage: 25,
  assignedSourcesSearch: '',
  assignedSourcesTagFilter: [],
  availableTagsInAssigned: [],
};

/**
 * Crawler filter state
 */
export interface CrawlerFilter {
  /** Search query for sources */
  search: string | null;
  /** Maximum sources to crawl */
  limit: number | null;
  /** Filter by source status */
  status: string | null;
  /** Filter by source type */
  source_type: string | null;
}

/**
 * Default crawler filter state
 */
export const DEFAULT_CRAWLER_FILTER: CrawlerFilter = {
  search: null,
  limit: null,
  status: null,
  source_type: null,
};

/**
 * Snackbar state for notifications
 */
export interface SnackbarState {
  /** Whether to show snackbar */
  show: boolean;
  /** Message text */
  text: string;
  /** Color variant */
  color: 'success' | 'error' | 'warning' | 'info';
}

/**
 * Default snackbar state
 */
export const DEFAULT_SNACKBAR_STATE: SnackbarState = {
  show: false,
  text: '',
  color: 'success',
};

// ============================================
// Operation Result Types
// ============================================

/**
 * Standardized result type for async operations
 * Used by composable functions to provide consistent return values
 */
export interface OperationResult {
  /** Whether the operation succeeded */
  success: boolean;
  /** Number of items affected (for bulk operations) */
  count?: number;
  /** Human-readable message for display */
  message?: string;
}

/**
 * Result indicating no operation was performed
 * Used when preconditions aren't met (e.g., empty selection)
 */
export const NO_OP_RESULT: OperationResult = {
  success: true,
  count: 0,
};
