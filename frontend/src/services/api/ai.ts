import { api } from './client'
import type {
  AssistantContext,
  ConversationMessage,
  AssistantAction,
  BatchActionRequest,
  CreateFacetTypeRequest,
} from '@/types/assistant'
import type {
  AnalysisTemplateListParams,
  AnalysisTemplateCreate,
  AnalysisTemplateUpdate,
} from '@/types/entity'

// AI Tasks - Task status polling
export const getAiTaskStatus = (taskId: string) =>
  api.get('/v1/ai-tasks/status', { params: { task_id: taskId } })

export const getAiTaskResult = (taskId: string) =>
  api.get('/v1/ai-tasks/result', { params: { task_id: taskId } })

export const getAiTasksByEntity = (entityId: string, params?: { task_type?: string; status?: string; limit?: number }) =>
  api.get('/v1/ai-tasks/by-entity', { params: { entity_id: entityId, ...params } })

// Assistant API
export const chat = (data: {
  message: string
  context: AssistantContext
  conversation_history?: ConversationMessage[]
  mode?: 'read' | 'write'
  language?: 'de' | 'en'
  attachment_ids?: string[]
}) => api.post('/v1/assistant/chat', data)

export const chatStream = (data: {
  message: string
  context: AssistantContext
  conversation_history?: ConversationMessage[]
  mode?: 'read' | 'write'
  language?: 'de' | 'en'
  attachment_ids?: string[]
}) => {
  // Return a fetch request for SSE
  const baseUrl = api.defaults.baseURL || '/api'
  // Get auth token from axios defaults or localStorage
  const authHeader = api.defaults.headers.common?.['Authorization'] as string | undefined
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (authHeader) {
    headers['Authorization'] = authHeader
  }
  return fetch(`${baseUrl}/v1/assistant/chat-stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify(data),
  })
}

export const executeAction = (data: { action: AssistantAction; context: AssistantContext }) =>
  api.post('/v1/assistant/execute-action', data)

export const createFacetType = (data: CreateFacetTypeRequest) => api.post('/v1/assistant/create-facet-type', data)

export const getCommands = () => api.get('/v1/assistant/commands')

export const getSuggestions = (params: {
  route: string
  entity_type?: string
  entity_id?: string
}) => api.get('/v1/assistant/suggestions', { params })

export const getInsights = (params: {
  route: string
  view_mode?: string
  entity_type?: string
  entity_id?: string
  language?: 'de' | 'en'
}) => api.get('/v1/assistant/insights', { params })

export const uploadAttachment = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/v1/assistant/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const deleteAttachment = (attachmentId: string) =>
  api.delete(`/v1/assistant/upload/${attachmentId}`)

export const saveToEntityAttachments = (entityId: string, attachmentIds: string[]) =>
  api.post<{
    success: boolean
    saved_count: number
    attachment_ids: string[]
    errors?: string[]
    message: string
  }>('/v1/assistant/save-to-entity-attachments', {
    entity_id: entityId,
    attachment_ids: attachmentIds,
  })

export const batchAction = (data: BatchActionRequest) => api.post('/v1/assistant/batch-action', data)

export const getBatchStatus = (batchId: string) =>
  api.get(`/v1/assistant/batch-action/${batchId}/status`)

export const cancelBatch = (batchId: string) =>
  api.post(`/v1/assistant/batch-action/${batchId}/cancel`)

// Wizard operations
export const getWizards = () => api.get('/v1/assistant/wizards')

export const startWizard = (wizardType: string, context?: Record<string, unknown>) =>
  api.post('/v1/assistant/wizards/start', context || null, {
    params: { wizard_type: wizardType },
  })

export const wizardRespond = (wizardId: string, value: unknown) =>
  api.post(`/v1/assistant/wizards/${wizardId}/respond`, { value })

export const wizardBack = (wizardId: string) =>
  api.post(`/v1/assistant/wizards/${wizardId}/back`)

export const wizardCancel = (wizardId: string) =>
  api.post(`/v1/assistant/wizards/${wizardId}/cancel`)

// Reminder operations
export const getReminders = (params?: { status?: string; include_past?: boolean; limit?: number }) =>
  api.get('/v1/assistant/reminders', { params })

export const createReminder = (data: {
  message: string
  remind_at: string
  title?: string
  entity_id?: string
  entity_type?: string
  repeat?: 'none' | 'daily' | 'weekly' | 'monthly'
}) => api.post('/v1/assistant/reminders', data)

export const deleteReminder = (reminderId: string) =>
  api.delete(`/v1/assistant/reminders/${reminderId}`)

export const dismissReminder = (reminderId: string) =>
  api.post(`/v1/assistant/reminders/${reminderId}/dismiss`)

export const snoozeReminder = (reminderId: string, newRemindAt: string) =>
  api.post(`/v1/assistant/reminders/${reminderId}/snooze`, { remind_at: newRemindAt })

export const getDueReminders = () => api.get('/v1/assistant/reminders/due')

// Analysis API
export const getAnalysisTemplates = (params?: AnalysisTemplateListParams) => api.get('/v1/analysis/templates', { params })
export const getAnalysisTemplate = (id: string) => api.get(`/v1/analysis/templates/${id}`)
export const getAnalysisTemplateBySlug = (slug: string) => api.get(`/v1/analysis/templates/by-slug/${slug}`)
export const createAnalysisTemplate = (data: AnalysisTemplateCreate) => api.post('/v1/analysis/templates', data)
export const updateAnalysisTemplate = (id: string, data: AnalysisTemplateUpdate) => api.put(`/v1/analysis/templates/${id}`, data)
export const deleteAnalysisTemplate = (id: string) => api.delete(`/v1/analysis/templates/${id}`)

export const getAnalysisOverview = (params?: { entity_type_slug?: string }) => api.get('/v1/analysis/overview', { params })
export const getEntityReport = (entityId: string, params?: { include_facets?: boolean; include_relations?: boolean }) =>
  api.get(`/v1/analysis/report/${entityId}`, { params })
export const getAnalysisStats = (params?: { entity_type_slug?: string }) => api.get('/v1/analysis/stats', { params })

// Smart Query - Natural Language Queries
export const smartQuery = (data: { question: string; allow_write?: boolean }) =>
  api.post('/v1/analysis/smart-query', data)

// Smart Write - Natural Language Commands with Preview
export const smartWrite = (data: { question: string; preview_only?: boolean; confirmed?: boolean }) =>
  api.post('/v1/analysis/smart-write', data)

export const getSmartQueryExamples = () => api.get('/v1/analysis/smart-query/examples')

// Smart Query History
export const getSmartQueryHistory = (params?: {
  page?: number
  per_page?: number
  favorites_only?: boolean
  operation_type?: string
  search?: string
}) => api.get('/v1/smart-query/history', { params })

export const getSmartQueryOperation = (operationId: string) =>
  api.get(`/v1/smart-query/history/${operationId}`)

export const toggleSmartQueryFavorite = (operationId: string) =>
  api.post<{
    id: string
    is_favorite: boolean
    message: string
  }>(`/v1/smart-query/history/${operationId}/toggle-favorite`)

export const executeSmartQueryOperation = (operationId: string) =>
  api.post<{
    operation_id: string
    success: boolean
    message: string
    result: Record<string, unknown>
  }>(`/v1/smart-query/history/${operationId}/execute`)

export const updateSmartQueryOperation = (operationId: string, data: { is_favorite?: boolean; display_name?: string }) =>
  api.patch(`/v1/smart-query/history/${operationId}`, data)

export const deleteSmartQueryOperation = (operationId: string) =>
  api.delete(`/v1/smart-query/history/${operationId}`)

export const clearSmartQueryHistory = (includeFavorites: boolean = false) =>
  api.delete('/v1/smart-query/history', { params: { include_favorites: includeFavorites } })
