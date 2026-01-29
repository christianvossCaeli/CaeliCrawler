import { api } from './client'
import { deduplicatedGet } from './cache'
import type {
  EntityTypeListParams,
  EntityTypeCreate,
  EntityTypeUpdate,
  EntityListParams,
  EntityCreate,
  EntityUpdate,
} from '@/types/entity'

// Entity Types - uses deduplicatedGet as this is called frequently by many components
export const getEntityTypes = (params?: EntityTypeListParams) => deduplicatedGet('/v1/entity-types', { params })
export const getEntityType = (id: string) => api.get(`/v1/entity-types/${id}`)
export const getEntityTypeBySlug = (slug: string) => api.get(`/v1/entity-types/by-slug/${slug}`)
export const createEntityType = (data: EntityTypeCreate) => api.post('/v1/entity-types', data)
export const updateEntityType = (id: string, data: EntityTypeUpdate) => api.put(`/v1/entity-types/${id}`, data)
export const deleteEntityType = (id: string) => api.delete(`/v1/entity-types/${id}`)

// Entities - uses deduplicatedGet for frequently accessed lookups
export const getEntities = (params?: EntityListParams) => api.get('/v1/entities', { params })
export const getEntity = (id: string) => deduplicatedGet(`/v1/entities/${id}`)
export const getEntityBySlug = (typeSlug: string, entitySlug: string) =>
  deduplicatedGet(`/v1/entities/by-slug/${typeSlug}/${entitySlug}`)
export const getEntityBrief = (id: string) => deduplicatedGet(`/v1/entities/${id}/brief`)
export const getEntityChildren = (id: string, params?: EntityListParams) =>
  api.get(`/v1/entities/${id}/children`, { params })
export const getEntityHierarchy = (entityTypeSlug: string, params?: { max_depth?: number }) =>
  api.get(`/v1/entities/hierarchy/${entityTypeSlug}`, { params })
export const createEntity = (data: EntityCreate) => api.post('/v1/entities', data)
export const updateEntity = (id: string, data: EntityUpdate) => api.put(`/v1/entities/${id}`, data)
export const deleteEntity = (id: string, force?: boolean) =>
  api.delete(`/v1/entities/${id}`, { params: { force } })
export const getEntityExternalData = (id: string) => api.get(`/v1/entities/${id}/external-data`)
export const getEntityDocuments = (id: string) => api.get(`/v1/entities/${id}/documents`)
export const getEntitySources = (id: string) => api.get(`/v1/entities/${id}/sources`)

// Filter Options
export const getLocationFilterOptions = (params?: { country?: string; admin_level_1?: string }) =>
  api.get('/v1/entities/filter-options/location', { params })
export const getAttributeFilterOptions = (params: { entity_type_slug: string; attribute_key?: string }) =>
  api.get('/v1/entities/filter-options/attributes', { params })

// Search
export const searchEntities = (params: { q: string; per_page?: number; entity_type_slug?: string }) =>
  api.get('/v1/entities', { params: { search: params.q, per_page: params.per_page, entity_type_slug: params.entity_type_slug } })

// GeoJSON for map display
export const getEntitiesGeoJSON = (params?: {
  entity_type_slug?: string
  country?: string
  admin_level_1?: string
  admin_level_2?: string
  search?: string
  limit?: number
}) => api.get('/v1/entities/geojson', { params })

// Entity Attachments
export const uploadAttachment = (entityId: string, file: File, options?: { description?: string; autoAnalyze?: boolean }) => {
  const formData = new FormData()
  formData.append('file', file)

  const params = new URLSearchParams()
  if (options?.description) params.append('description', options.description)
  if (options?.autoAnalyze) params.append('auto_analyze', 'true')

  const queryString = params.toString()
  const url = `/v1/entities/${entityId}/attachments${queryString ? `?${queryString}` : ''}`

  return api.post(url, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const listAttachments = (entityId: string) =>
  api.get(`/v1/entities/${entityId}/attachments`)

export const getAttachment = (entityId: string, attachmentId: string) =>
  api.get(`/v1/entities/${entityId}/attachments/${attachmentId}`)

export const downloadAttachment = (entityId: string, attachmentId: string) =>
  api.get(`/v1/entities/${entityId}/attachments/${attachmentId}/download`, {
    responseType: 'blob',
  })

export const getAttachmentThumbnailUrl = (entityId: string, attachmentId: string) =>
  `/api/v1/entities/${entityId}/attachments/${attachmentId}/thumbnail`

export const deleteAttachment = (entityId: string, attachmentId: string) =>
  api.delete(`/v1/entities/${entityId}/attachments/${attachmentId}`)

export const analyzeAttachment = (entityId: string, attachmentId: string, extractFacets = true) =>
  api.post(`/v1/entities/${entityId}/attachments/${attachmentId}/analyze`, null, {
    params: { extract_facets: extractFacets },
  })

export const updateAttachment = (entityId: string, attachmentId: string, description: string) =>
  api.patch(`/v1/entities/${entityId}/attachments/${attachmentId}`, null, {
    params: { description },
  })

export const applyAttachmentFacets = (entityId: string, attachmentId: string, facetIndices: number[]) =>
  api.post(`/v1/entities/${entityId}/attachments/${attachmentId}/apply-facets`, null, {
    params: { facet_indices: facetIndices },
    paramsSerializer: (params) => {
      const searchParams = new URLSearchParams()
      if (params.facet_indices) {
        params.facet_indices.forEach((idx: number) => searchParams.append('facet_indices', idx.toString()))
      }
      return searchParams.toString()
    },
  })

// Entity Data Enrichment API
export const getEnrichmentSources = (entityId: string) =>
  api.get('/v1/entity-data/enrichment-sources', { params: { entity_id: entityId } })

export const analyzeEntityForFacets = (data: {
  entity_id: string
  source_types: string[]
}) => api.post('/v1/entity-data/analyze-for-facets', data)

export const getAnalysisPreview = (taskId: string) =>
  api.get('/v1/entity-data/analysis-preview', { params: { task_id: taskId } })

export const applyEnrichmentChanges = (data: {
  task_id: string
  accepted_new_facets: number[]
  accepted_updates: string[]
}) => api.post('/v1/entity-data/apply-changes', data)

// Favorites API
export const listFavorites = (params?: {
  page?: number
  per_page?: number
  entity_type_slug?: string
  search?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}) => api.get('/v1/favorites', { params })

export const addFavorite = (entityId: string) =>
  api.post('/v1/favorites', { entity_id: entityId })

export const checkFavorite = (entityId: string) =>
  api.get<{
    entity_id: string
    is_favorited: boolean
    favorite_id: string | null
  }>(`/v1/favorites/check/${entityId}`)

export const removeFavorite = (favoriteId: string) =>
  api.delete(`/v1/favorites/${favoriteId}`)

export const removeFavoriteByEntity = (entityId: string) =>
  api.delete(`/v1/favorites/entity/${entityId}`)
