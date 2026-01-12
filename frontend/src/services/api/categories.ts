/**
 * Categories API Client
 *
 * Provides typed API calls for category CRUD operations,
 * AI setup preview, and source assignment.
 */
import { api } from './client'
import type {
  CategoryCreate,
  CategoryUpdate,
  CategoryListParams,
  CategoryResponse,
  CategoryListResponse,
  CategoryStats,
  CategoryAiPreviewData,
} from '@/types/category'

// ============================================
// Category CRUD Operations
// ============================================

/**
 * List categories with pagination and filters
 */
export const getCategories = (params?: CategoryListParams) =>
  api.get<CategoryListResponse>('/admin/categories', { params })

/**
 * Get a single category by ID
 */
export const getCategory = (id: string) =>
  api.get<CategoryResponse>(`/admin/categories/${id}`)

/**
 * Create a new category
 */
export const createCategory = (data: CategoryCreate | Record<string, unknown>) =>
  api.post<CategoryResponse>('/admin/categories', data)

/**
 * Update an existing category
 */
export const updateCategory = (id: string, data: CategoryUpdate) =>
  api.put<CategoryResponse>(`/admin/categories/${id}`, data)

/**
 * Delete a category
 */
export const deleteCategory = (id: string) =>
  api.delete(`/admin/categories/${id}`)

// ============================================
// Category Statistics
// ============================================

/**
 * Get statistics for a category
 */
export const getCategoryStats = (id: string) =>
  api.get<CategoryStats>(`/admin/categories/${id}/stats`)

// ============================================
// AI Setup Preview
// ============================================

/**
 * Request body for AI setup preview
 */
export interface CategoryAiSetupRequest {
  /** Category name */
  name: string
  /** Category purpose */
  purpose: string
  /** Optional description */
  description?: string
}

/**
 * Preview AI-generated category setup
 * Returns suggested entity types, facet types, extraction prompt, etc.
 */
export const previewCategoryAiSetup = (data: CategoryAiSetupRequest) =>
  api.post<CategoryAiPreviewData>('/admin/categories/preview-ai-setup', data)

// ============================================
// Source Assignment
// ============================================

/**
 * Request body for assigning sources by tags
 */
export interface AssignSourcesByTagsRequest {
  /** Tags to match */
  tags: string[]
  /** Match mode: 'all' requires all tags, 'any' requires at least one */
  match_mode?: 'all' | 'any'
  /** Assignment mode: 'add' appends, 'replace' overwrites */
  mode?: 'add' | 'replace'
}

/**
 * Response for source assignment
 */
export interface AssignSourcesByTagsResponse {
  /** Number of sources assigned */
  assigned: number
  /** Number of sources already assigned */
  already_assigned: number
  /** Number of sources removed (only for replace mode) */
  removed: number
  /** Total sources matching the criteria */
  total: number
}

/**
 * Assign sources to a category based on tags
 */
export const assignSourcesByTags = (
  categoryId: string,
  data: AssignSourcesByTagsRequest
) =>
  api.post<AssignSourcesByTagsResponse>(
    `/admin/categories/${categoryId}/assign-sources-by-tags`,
    data
  )

/**
 * Request body for assigning sources by IDs
 */
export interface AssignSourcesByIdsRequest {
  /** Source IDs to assign */
  source_ids: string[]
}

/**
 * Assign sources to a category by their IDs
 */
export const assignSourcesById = (
  categoryId: string,
  data: AssignSourcesByIdsRequest
) =>
  api.post<AssignSourcesByTagsResponse>(
    `/admin/categories/${categoryId}/assign-sources`,
    data
  )

// ============================================
// Category Sources (Assigned)
// ============================================

/**
 * Parameters for getting category sources
 */
export interface GetCategorySourcesParams {
  /** Page number */
  page?: number
  /** Items per page */
  per_page?: number
  /** Search query */
  search?: string
  /** Filter by tags */
  tags?: string[]
}

/**
 * Response for category sources
 */
export interface CategorySourcesResponse {
  /** List of sources */
  items: Array<{
    id: string
    name: string
    base_url?: string
    status?: string
    source_type?: string
    tags?: string[]
    document_count?: number
  }>
  /** Total count */
  total: number
  /** Current page */
  page: number
  /** Items per page */
  per_page: number
}

/**
 * Get sources assigned to a category with pagination and filters
 */
export const getCategorySources = (
  categoryId: string,
  params?: GetCategorySourcesParams
) =>
  api.get<CategorySourcesResponse>(
    `/admin/categories/${categoryId}/sources`,
    { params }
  )

/**
 * Get available tags in sources assigned to a category
 */
export const getCategorySourcesTags = (categoryId: string) =>
  api.get<{ tags: string[] }>(`/admin/categories/${categoryId}/sources/tags`)

/**
 * Unassign a source from a category
 */
export const unassignSource = (categoryId: string, sourceId: string) =>
  api.delete(`/admin/categories/${categoryId}/sources/${sourceId}`)

/**
 * Request body for bulk unassigning sources
 */
export interface UnassignSourcesBulkRequest {
  /** Source IDs to unassign */
  source_ids: string[]
}

/**
 * Response for bulk unassign operation
 */
export interface UnassignSourcesBulkResponse {
  /** Number of sources successfully unassigned */
  removed: number
  /** Number of sources not found in category */
  not_found: number
  /** Human-readable result message */
  message: string
}

/**
 * Bulk unassign multiple sources from a category
 */
export const unassignSourcesBulk = (
  categoryId: string,
  data: UnassignSourcesBulkRequest
) =>
  api.post<UnassignSourcesBulkResponse>(
    `/admin/categories/${categoryId}/unassign-sources`,
    data
  )

// ============================================
// Grouped API Object (for import convenience)
// ============================================

/**
 * Category API object with all operations
 */
export const categoryApi = {
  // CRUD
  list: getCategories,
  get: getCategory,
  create: createCategory,
  update: updateCategory,
  delete: deleteCategory,
  // Stats
  getStats: getCategoryStats,
  // AI
  previewAiSetup: previewCategoryAiSetup,
  // Sources
  assignSourcesByTags,
  assignSourcesById,
  getCategorySources,
  getCategorySourcesTags,
  unassignSource,
  unassignSourcesBulk,
}

export default categoryApi
