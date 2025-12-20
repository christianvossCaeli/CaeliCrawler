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
export type LanguageCode = 'de' | 'en' | 'fr' | 'nl' | 'it' | 'es' | 'pl' | 'da' | 'pt' | 'sv' | 'no' | 'fi' | 'cs' | 'hu' | 'ro' | 'bg' | 'el' | 'tr' | 'ru' | 'uk' | 'ar' | 'zh' | 'ja' | 'ko';

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
  /** Cron expression for scheduled crawls (e.g., "0 2 * * *") */
  schedule_cron: string;
  /** Whether category is active for crawling */
  is_active: boolean;
  /** If true, visible to all users */
  is_public: boolean;
  /** Target EntityType for extracted entities */
  target_entity_type_id?: string | null;
}

/**
 * Request body for creating a new category
 */
export interface CategoryCreate extends CategoryBase {
  /** URL-friendly slug (auto-generated if not provided) */
  slug?: string | null;
}

/**
 * Request body for updating a category (all fields optional)
 */
export interface CategoryUpdate extends Partial<CategoryBase> {
  // All fields from CategoryBase are optional
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
  /** Filter by active status */
  is_active?: boolean;
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
  source_type?: 'WEBSITE' | 'OPARL_API' | 'RSS' | 'CUSTOM_API';
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
