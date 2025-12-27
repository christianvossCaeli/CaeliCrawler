import { api } from './client'
import type {
  FacetTypeListParams,
  FacetTypeCreate,
  FacetTypeUpdate,
  FacetValueListParams,
  FacetValueCreate,
  FacetValueUpdate,
  FacetValueVerify,
} from '@/types/entity'

// Facet Types
export const getFacetTypes = (params?: FacetTypeListParams) => api.get('/v1/facets/types', { params })
export const getFacetType = (id: string) => api.get(`/v1/facets/types/${id}`)
export const getFacetTypeBySlug = (slug: string) => api.get(`/v1/facets/types/by-slug/${slug}`)
export const createFacetType = (data: FacetTypeCreate) => api.post('/v1/facets/types', data)
export const updateFacetType = (id: string, data: FacetTypeUpdate) => api.put(`/v1/facets/types/${id}`, data)
export const deleteFacetType = (id: string) => api.delete(`/v1/facets/types/${id}`)

// Facet Values
export const getFacetValues = (params?: FacetValueListParams) => api.get('/v1/facets/values', { params })
export const getFacetValue = (id: string) => api.get(`/v1/facets/values/${id}`)
export const createFacetValue = (data: FacetValueCreate) => api.post('/v1/facets/values', data)
export const updateFacetValue = (id: string, data: FacetValueUpdate) => api.put(`/v1/facets/values/${id}`, data)
export const verifyFacetValue = (id: string, params?: FacetValueVerify) =>
  api.put(`/v1/facets/values/${id}/verify`, null, { params })
export const deleteFacetValue = (id: string) => api.delete(`/v1/facets/values/${id}`)

// Entity Facets Summary
export const getEntityFacetsSummary = (entityId: string, params?: { include_empty?: boolean }) =>
  api.get(`/v1/facets/entity/${entityId}/summary`, { params })

// AI Schema Generation
export const generateFacetTypeSchema = (data: { name: string; name_plural?: string; description?: string; applicable_entity_types?: string[] }) =>
  api.post('/v1/facets/types/generate-schema', data)

// Full-Text Search
export const searchFacetValues = (params: { q: string; entity_id?: string; facet_type_slug?: string; limit?: number }) =>
  api.get('/v1/facets/search', { params })

// History (Time-Series Data)
export const getEntityHistory = (entityId: string, facetTypeId: string, params?: {
  from_date?: string
  to_date?: string
  tracks?: string[]
  limit?: number
}) => api.get(`/v1/facets/entity/${entityId}/history/${facetTypeId}`, { params })

export const getEntityHistoryAggregated = (entityId: string, facetTypeId: string, params?: {
  interval?: 'day' | 'week' | 'month' | 'quarter' | 'year'
  method?: 'avg' | 'sum' | 'min' | 'max'
  from_date?: string
  to_date?: string
  tracks?: string[]
}) => api.get(`/v1/facets/entity/${entityId}/history/${facetTypeId}/aggregated`, { params })

export const addHistoryDataPoint = (entityId: string, facetTypeId: string, data: {
  recorded_at: string
  value: number
  track_key?: string
  value_label?: string
  annotations?: Record<string, unknown>
  source_type?: string
  source_url?: string
  confidence_score?: number
}) => api.post(`/v1/facets/entity/${entityId}/history/${facetTypeId}`, data)

export const addHistoryDataPointsBulk = (entityId: string, facetTypeId: string, data: {
  data_points: Array<{
    recorded_at: string
    value: number
    track_key?: string
    value_label?: string
    annotations?: Record<string, unknown>
  }>
  skip_duplicates?: boolean
}) => api.post(`/v1/facets/entity/${entityId}/history/${facetTypeId}/bulk`, data)

export const updateHistoryDataPoint = (entityId: string, facetTypeId: string, pointId: string, data: {
  value?: number
  value_label?: string
  annotations?: Record<string, unknown>
  human_verified?: boolean
}) => api.put(`/v1/facets/entity/${entityId}/history/${facetTypeId}/${pointId}`, data)

export const deleteHistoryDataPoint = (entityId: string, facetTypeId: string, pointId: string) =>
  api.delete(`/v1/facets/entity/${entityId}/history/${facetTypeId}/${pointId}`)

// Get facets that reference a specific entity (via target_entity_id)
export const getFacetsReferencingEntity = (entityId: string, params?: {
  page?: number
  per_page?: number
  facet_type_slug?: string
}) => api.get(`/v1/facets/entity/${entityId}/referenced-by`, { params })
