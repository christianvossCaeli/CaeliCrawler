import { api } from './client'
import type { CategoryCreate, CategoryUpdate, CategoryListParams, DocumentListParams, ExportListParams } from '@/types/category'

// Categories
export const getCategories = (params?: CategoryListParams) => api.get('/admin/categories', { params })
export const getCategory = (id: string) => api.get(`/admin/categories/${id}`)
export const createCategory = (data: CategoryCreate | Record<string, unknown>) => api.post('/admin/categories', data)
export const updateCategory = (id: string, data: CategoryUpdate) => api.put(`/admin/categories/${id}`, data)
export const deleteCategory = (id: string) => api.delete(`/admin/categories/${id}`)
export const getCategoryStats = (id: string) => api.get(`/admin/categories/${id}/stats`)
export const previewCategoryAiSetup = (data: { name: string; purpose: string; description?: string }) =>
  api.post('/admin/categories/preview-ai-setup', data)
export const assignSourcesByTags = (categoryId: string, data: {
  tags: string[]
  match_mode?: 'all' | 'any'
  mode?: 'add' | 'replace'
}) => api.post(`/admin/categories/${categoryId}/assign-sources-by-tags`, data)

// Data Sources
export const getSources = (params?: import('@/types/sources').DataSourceListParams) =>
  api.get<import('@/types/sources').DataSourceListResponse>('/admin/sources', { params })
export const getSource = (id: string) =>
  api.get<import('@/types/sources').DataSourceResponse>(`/admin/sources/${id}`)
export const createSource = (data: import('@/types/sources').DataSourceCreate) =>
  api.post<import('@/types/sources').DataSourceResponse>('/admin/sources', data)
export const updateSource = (id: string, data: import('@/types/sources').DataSourceUpdate) =>
  api.put<import('@/types/sources').DataSourceResponse>(`/admin/sources/${id}`, data)
export const deleteSource = (id: string) => api.delete(`/admin/sources/${id}`)
export const bulkImportSources = (data: import('@/types/sources').DataSourceBulkImport) =>
  api.post<import('@/types/sources').DataSourceBulkImportResult>('/admin/sources/bulk-import', data)
export const resetSource = (id: string) => api.post(`/admin/sources/${id}/reset`)
export const getSourceCounts = () =>
  api.get<import('@/types/sources').SourceCountsResponse>('/admin/sources/meta/counts')
export const getAvailableTags = () =>
  api.get<import('@/types/sources').TagsResponse>('/admin/sources/meta/tags')
export const getSourcesByTags = (params: {
  tags: string[]
  match_mode?: 'all' | 'any'
  exclude_category_id?: string
  limit?: number
}) => api.get('/admin/sources/by-tags', { params })

// SharePoint
export const testSharePointConnection = (siteUrl?: string) =>
  api.post('/admin/sharepoint/test-connection', null, { params: { site_url: siteUrl } })
export const getSharePointStatus = () => api.get('/admin/sharepoint/status')
export const getSharePointSites = (query?: string) =>
  api.get('/admin/sharepoint/sites', { params: { query } })
export const getSharePointDrives = (siteId: string) =>
  api.get(`/admin/sharepoint/sites/${siteId}/drives`)
export const getSharePointFiles = (siteId: string, driveId: string, params?: {
  folder_path?: string
  recursive?: boolean
  limit?: number
}) => api.get(`/admin/sharepoint/sites/${siteId}/drives/${driveId}/files`, { params })

// API Import
export const getApiImportTemplates = () => api.get('/admin/api-import/templates')
export const getApiImportTemplate = (templateId: string) => api.get(`/admin/api-import/templates/${templateId}`)
export const previewApiImport = (data: {
  api_type: string
  api_url: string
  params?: Record<string, unknown>
  sample_size?: number
}) => api.post('/admin/api-import/preview', data)
export const executeApiImport = (data: {
  api_type: string
  api_url: string
  params?: Record<string, unknown>
  category_ids: string[]
  default_tags?: string[]
  field_mapping?: Record<string, string>
  skip_duplicates?: boolean
  max_items?: number
}) => api.post('/admin/api-import/execute', data)

// AI Discovery (V1 - Legacy)
export const getAiDiscoveryExamples = () => api.get('/admin/ai-discovery/examples')
export const discoverSources = (data: {
  prompt: string
  max_results?: number
  search_depth?: 'quick' | 'standard' | 'deep'
  include_category_suggestions?: boolean
}) => api.post('/admin/ai-discovery/discover', data)
export const importDiscoveredSources = (data: {
  sources: Array<{
    url?: string
    base_url?: string
    name: string
    description?: string
    confidence?: number
    source_type?: string
    tags?: string[]
    metadata?: Record<string, unknown>
  }>
  category_ids?: string[]
  skip_duplicates?: boolean
}) => api.post('/admin/ai-discovery/import', data)

// AI Discovery V2 (KI-First)
export const discoverSourcesV2 = (data: {
  prompt: string
  max_results?: number
  search_depth?: 'quick' | 'standard' | 'deep'
  skip_api_discovery?: boolean
}) => api.post('/admin/ai-discovery/discover-v2', data)
export const importApiData = (data: {
  api_name: string
  api_url: string
  field_mapping: Record<string, string>
  items: Array<Record<string, unknown>>
  category_ids?: string[]
  tags?: string[]
  skip_duplicates?: boolean
}) => api.post('/admin/ai-discovery/import-api-data', data)

// Save discovered API as a new configuration (used by AI-Discovery)
export const saveApiFromDiscovery = (data: {
  name: string
  description?: string
  api_type?: string
  base_url: string
  endpoint: string
  documentation_url?: string
  auth_required?: boolean
  field_mapping: Record<string, string>
  keywords: string[]
  default_tags?: string[]
  confidence?: number
  validation_item_count?: number
}) => api.post('/admin/external-apis/save-from-discovery', data)

// Extracted Data & Documents (Public API)
export interface ExtractedDataParams {
  category_id?: string
  source_id?: string
  extraction_type?: string
  min_confidence?: number
  human_verified?: boolean
  created_from?: string
  created_to?: string
  search?: string
  page?: number
  per_page?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface ExtractionStatsParams {
  category_id?: string | null
  source_id?: string
  extraction_type?: string
  min_confidence?: number
  human_verified?: boolean | null
  created_from?: string
  created_to?: string
  search?: string
}

export const getExtractedData = (params?: ExtractedDataParams) => api.get('/v1/data/', { params })
export const getExtractionStats = (params?: ExtractionStatsParams) => api.get('/v1/data/stats', { params })
export const getExtractionLocations = () => api.get('/v1/data/locations')
export const getExtractionCountries = () => api.get('/v1/data/countries')
export const getDisplayConfig = (categoryId: string) => api.get(`/v1/data/display-config/${categoryId}`)
export const getDocuments = (params?: DocumentListParams) => api.get('/v1/data/documents', { params })
export const getDocument = (id: string) => api.get(`/v1/data/documents/${id}`)
export const getDocumentLocations = () => api.get('/v1/data/documents/locations')
export const searchDocuments = (params: { q: string; category_id?: string; limit?: number }, signal?: AbortSignal) =>
  api.get('/v1/data/search', { params, signal })
export const verifyExtraction = (id: string, data: { verified: boolean; corrections?: Record<string, unknown> }) =>
  api.put(`/v1/data/extracted/${id}/verify`, data)

// Municipalities (Gemeinden)
export const getMunicipalities = (params?: { country?: string; admin_level_1?: string; search?: string; page?: number; per_page?: number }) =>
  api.get('/v1/data/municipalities', { params })
export const getMunicipalityReport = (name: string, params?: { category_id?: string }) =>
  api.get(`/v1/data/municipalities/${encodeURIComponent(name)}/report`, { params })
export const getMunicipalityDocuments = (name: string, params?: { category_id?: string; page?: number; per_page?: number }) =>
  api.get(`/v1/data/municipalities/${encodeURIComponent(name)}/documents`, { params })
export const getOverviewReport = (params?: { category_id?: string; country?: string }) =>
  api.get('/v1/data/report/overview', { params })

// History
export const getMunicipalityHistory = (params?: { municipality?: string; from_date?: string; to_date?: string }) =>
  api.get('/v1/data/history/municipalities', { params })
export const getCrawlHistory = (params?: { category_id?: string; source_id?: string; from_date?: string; to_date?: string }) =>
  api.get('/v1/data/history/crawls', { params })

// Export
export const exportJson = (params?: {
  entity_type?: string
  category_id?: string
  location_filter?: string
  include_facets?: boolean
}) => api.get('/v1/export/json', { params, responseType: 'blob' })
export const exportCsv = (params?: {
  entity_type?: string
  category_id?: string
  location_filter?: string
  include_facets?: boolean
}) => api.get('/v1/export/csv', { params, responseType: 'blob' })
export const getChangesFeed = (params?: ExportListParams) =>
  api.get('/v1/export/changes', { params })
export const testWebhook = (url: string) => api.post('/v1/export/webhook/test', null, { params: { url } })
export const startAsyncExport = (data: {
  entity_type?: string
  format?: string
  location_filter?: string
  facet_types?: string[]
  position_keywords?: string[]
  country?: string
  include_facets?: boolean
  filename?: string
}) => api.post('/v1/export/async', data)
export const getExportJobStatus = (jobId: string) => api.get(`/v1/export/async/${jobId}`)
export const downloadExport = (jobId: string) => api.get(`/v1/export/async/${jobId}/download`, { responseType: 'blob' })
export const cancelExportJob = (jobId: string) => api.delete(`/v1/export/async/${jobId}`)
export const listExportJobs = (params?: { status_filter?: string; limit?: number }) =>
  api.get('/v1/export/async', { params })

// Locations
export const searchLocations = (q: string, params?: { country?: string; admin_level_1?: string; limit?: number }) =>
  api.get('/admin/locations/search', { params: { q, ...params } })
export const listLocations = (params?: { country?: string; admin_level_1?: string; search?: string; page?: number; per_page?: number }) =>
  api.get('/admin/locations', { params })
export const listLocationsWithSources = (params?: { country?: string; admin_level_1?: string; search?: string; page?: number; per_page?: number }) =>
  api.get('/admin/locations/with-sources', { params })
export const getLocation = (id: string) => api.get(`/admin/locations/${id}`)
export const createLocation = (data: import('@/types/admin').LocationCreate) => api.post('/admin/locations', data)
export const updateLocation = (id: string, data: import('@/types/admin').LocationUpdate) => api.put(`/admin/locations/${id}`, data)
export const deleteLocation = (id: string) => api.delete(`/admin/locations/${id}`)
export const getCountries = () => api.get('/admin/locations/countries')
export const getAdminLevels = (country: string, level: number, parent?: string) =>
  api.get('/admin/locations/admin-levels', { params: { country, level, parent } })
export const linkSources = (country?: string) =>
  api.post('/admin/locations/link-sources', null, { params: { country } })
export const enrichAdminLevels = (country?: string, limit?: number) =>
  api.post('/admin/locations/enrich-admin-levels', null, { params: { country, limit } })
export const getStates = (country?: string) =>
  api.get('/admin/locations/states', { params: { country } })
