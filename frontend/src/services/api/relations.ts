import { api } from './client'
import type {
  RelationTypeListParams,
  RelationTypeCreate,
  RelationTypeUpdate,
  RelationListParams,
  RelationCreate,
  RelationUpdate,
  RelationVerify,
} from '@/types/entity'

// Relation Types
export const getRelationTypes = (params?: RelationTypeListParams) => api.get('/v1/relations/types', { params })
export const getRelationType = (id: string) => api.get(`/v1/relations/types/${id}`)
export const getRelationTypeBySlug = (slug: string) => api.get(`/v1/relations/types/by-slug/${slug}`)
export const createRelationType = (data: RelationTypeCreate) => api.post('/v1/relations/types', data)
export const updateRelationType = (id: string, data: RelationTypeUpdate) => api.put(`/v1/relations/types/${id}`, data)
export const deleteRelationType = (id: string) => api.delete(`/v1/relations/types/${id}`)

// Entity Relations
export const getRelations = (params?: RelationListParams) => api.get('/v1/relations', { params })
export const getRelation = (id: string) => api.get(`/v1/relations/${id}`)
export const createRelation = (data: RelationCreate) => api.post('/v1/relations', data)
export const updateRelation = (id: string, data: RelationUpdate) => api.put(`/v1/relations/${id}`, data)
export const verifyRelation = (id: string, params?: RelationVerify) =>
  api.put(`/v1/relations/${id}/verify`, null, { params })
export const deleteRelation = (id: string) => api.delete(`/v1/relations/${id}`)

// Relation Graph
export const getEntityRelationsGraph = (entityId: string, params?: { depth?: number; relation_types?: string[] }) =>
  api.get(`/v1/relations/graph/${entityId}`, { params })
