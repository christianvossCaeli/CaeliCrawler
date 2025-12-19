import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Admin API
export const adminApi = {
  // Categories
  getCategories: (params?: any) => api.get('/admin/categories', { params }),
  getCategory: (id: string) => api.get(`/admin/categories/${id}`),
  createCategory: (data: any) => api.post('/admin/categories', data),
  updateCategory: (id: string, data: any) => api.put(`/admin/categories/${id}`, data),
  deleteCategory: (id: string) => api.delete(`/admin/categories/${id}`),
  getCategoryStats: (id: string) => api.get(`/admin/categories/${id}/stats`),

  // Sources
  getSources: (params?: any) => api.get('/admin/sources', { params }),
  getSource: (id: string) => api.get(`/admin/sources/${id}`),
  createSource: (data: any) => api.post('/admin/sources', data),
  updateSource: (id: string, data: any) => api.put(`/admin/sources/${id}`, data),
  deleteSource: (id: string) => api.delete(`/admin/sources/${id}`),
  bulkImportSources: (data: any) => api.post('/admin/sources/bulk-import', data),
  resetSource: (id: string) => api.post(`/admin/sources/${id}/reset`),
  getSourceCountries: () => api.get('/admin/sources/meta/countries'),
  getSourceLocations: (params?: { country?: string; search?: string; limit?: number }) =>
    api.get('/admin/sources/meta/locations', { params }),

  // Crawler
  getCrawlerJobs: (params?: any) => api.get('/admin/crawler/jobs', { params }),
  getCrawlerJob: (id: string) => api.get(`/admin/crawler/jobs/${id}`),
  startCrawl: (data: any) => api.post('/admin/crawler/start', data),
  cancelJob: (id: string) => api.post(`/admin/crawler/jobs/${id}/cancel`),
  getCrawlerStats: () => api.get('/admin/crawler/stats'),
  getCrawlerStatus: () => api.get('/admin/crawler/status'),
  reanalyzeDocuments: (params?: any) => api.post('/admin/crawler/reanalyze', null, { params }),
  getRunningJobs: () => api.get('/admin/crawler/running'),
  getJobLog: (id: string, limit?: number) => api.get(`/admin/crawler/jobs/${id}/log`, { params: { limit } }),

  // AI Tasks
  getAiTasks: (params?: any) => api.get('/admin/crawler/ai-tasks', { params }),
  getRunningAiTasks: () => api.get('/admin/crawler/ai-tasks/running'),
  cancelAiTask: (id: string) => api.post(`/admin/crawler/ai-tasks/${id}/cancel`),

  // Document Processing
  processDocument: (id: string) => api.post(`/admin/crawler/documents/${id}/process`),
  analyzeDocument: (id: string, skipRelevanceCheck = false) =>
    api.post(`/admin/crawler/documents/${id}/analyze`, null, { params: { skip_relevance_check: skipRelevanceCheck } }),
  processAllPending: () => api.post('/admin/crawler/documents/process-pending'),
  stopAllProcessing: () => api.post('/admin/crawler/documents/stop-all'),
  reanalyzeFiltered: (limit = 100) => api.post('/admin/crawler/documents/reanalyze-filtered', null, { params: { limit } }),
}

// Public API v1
export const dataApi = {
  // Extracted Data
  getExtractedData: (params?: any) => api.get('/v1/data/', { params }),
  getExtractionStats: (params?: any) => api.get('/v1/data/stats', { params }),
  getExtractionLocations: () => api.get('/v1/data/locations'),
  getExtractionCountries: () => api.get('/v1/data/countries'),

  // Documents
  getDocuments: (params?: any) => api.get('/v1/data/documents', { params }),
  getDocument: (id: string) => api.get(`/v1/data/documents/${id}`),
  getDocumentLocations: () => api.get('/v1/data/documents/locations'),
  searchDocuments: (params: any) => api.get('/v1/data/search', { params }),

  // Verification
  verifyExtraction: (id: string, data: any) => api.put(`/v1/data/extracted/${id}/verify`, data),

  // Municipalities (Gemeinden)
  getMunicipalities: (params?: any) => api.get('/v1/data/municipalities', { params }),
  getMunicipalityReport: (name: string, params?: any) => api.get(`/v1/data/municipalities/${encodeURIComponent(name)}/report`, { params }),
  getMunicipalityDocuments: (name: string, params?: any) => api.get(`/v1/data/municipalities/${encodeURIComponent(name)}/documents`, { params }),
  getOverviewReport: (params?: any) => api.get('/v1/data/report/overview', { params }),

  // History
  getMunicipalityHistory: (params?: any) => api.get('/v1/data/history/municipalities', { params }),
  getCrawlHistory: (params?: any) => api.get('/v1/data/history/crawls', { params }),
}

// Export API
export const exportApi = {
  exportJson: (params?: any) => api.get('/v1/export/json', { params, responseType: 'blob' }),
  exportCsv: (params?: any) => api.get('/v1/export/csv', { params, responseType: 'blob' }),
  getChangesFeed: (params?: any) => api.get('/v1/export/changes', { params }),
  testWebhook: (url: string) => api.post('/v1/export/webhook/test', null, { params: { url } }),
}

// Location Admin API (International)
export const locationApi = {
  // List & Search
  search: (q: string, params?: { country?: string; admin_level_1?: string; limit?: number }) =>
    api.get('/admin/locations/search', { params: { q, ...params } }),
  list: (params?: { country?: string; admin_level_1?: string; search?: string; page?: number; per_page?: number }) =>
    api.get('/admin/locations', { params }),
  listWithSources: (params?: { country?: string; admin_level_1?: string; search?: string; page?: number; per_page?: number }) =>
    api.get('/admin/locations/with-sources', { params }),

  // CRUD
  get: (id: string) => api.get(`/admin/locations/${id}`),
  create: (data: any) => api.post('/admin/locations', data),
  update: (id: string, data: any) => api.put(`/admin/locations/${id}`, data),
  delete: (id: string) => api.delete(`/admin/locations/${id}`),

  // Country & Admin Levels
  getCountries: () => api.get('/admin/locations/countries'),
  getAdminLevels: (country: string, level: number, parent?: string) =>
    api.get('/admin/locations/admin-levels', { params: { country, level, parent } }),

  // Utilities
  linkSources: (country?: string) =>
    api.post('/admin/locations/link-sources', null, { params: { country } }),
  enrichAdminLevels: (country?: string, limit?: number) =>
    api.post('/admin/locations/enrich-admin-levels', null, { params: { country, limit } }),

  // Legacy alias (for backward compatibility)
  getStates: (country?: string) =>
    api.get('/admin/locations/states', { params: { country } }),
}

// Municipality Admin API (Legacy alias - redirects to locationApi)
export const municipalityApi = {
  search: (q: string, params?: any) => locationApi.search(q, params),
  list: (params?: any) => locationApi.list(params),
  listWithSources: (params?: any) => locationApi.listWithSources(params),
  linkSources: () => locationApi.linkSources(),
  enrichDistricts: (limit?: number) => locationApi.enrichAdminLevels('DE', limit),
  get: (id: string) => locationApi.get(id),
  create: (data: any) => locationApi.create(data),
  update: (id: string, data: any) => locationApi.update(id, data),
  delete: (id: string) => locationApi.delete(id),
  getStates: () => locationApi.getStates('DE'),
}

// Entity-Facet System API
export const entityApi = {
  // Entity Types
  getEntityTypes: (params?: any) => api.get('/v1/entity-types', { params }),
  getEntityType: (id: string) => api.get(`/v1/entity-types/${id}`),
  getEntityTypeBySlug: (slug: string) => api.get(`/v1/entity-types/by-slug/${slug}`),
  createEntityType: (data: any) => api.post('/v1/entity-types', data),
  updateEntityType: (id: string, data: any) => api.put(`/v1/entity-types/${id}`, data),
  deleteEntityType: (id: string) => api.delete(`/v1/entity-types/${id}`),

  // Entities
  getEntities: (params?: any) => api.get('/v1/entities', { params }),
  getEntity: (id: string) => api.get(`/v1/entities/${id}`),
  getEntityBySlug: (typeSlug: string, entitySlug: string) =>
    api.get(`/v1/entities/by-slug/${typeSlug}/${entitySlug}`),
  getEntityBrief: (id: string) => api.get(`/v1/entities/${id}/brief`),
  getEntityChildren: (id: string, params?: any) => api.get(`/v1/entities/${id}/children`, { params }),
  getEntityHierarchy: (entityTypeSlug: string, params?: any) =>
    api.get(`/v1/entities/hierarchy/${entityTypeSlug}`, { params }),
  createEntity: (data: any) => api.post('/v1/entities', data),
  updateEntity: (id: string, data: any) => api.put(`/v1/entities/${id}`, data),
  deleteEntity: (id: string, force?: boolean) =>
    api.delete(`/v1/entities/${id}`, { params: { force } }),

  // Filter Options
  getLocationFilterOptions: (params?: { country?: string; admin_level_1?: string }) =>
    api.get('/v1/entities/filter-options/location', { params }),
  getAttributeFilterOptions: (params: { entity_type_slug: string; attribute_key?: string }) =>
    api.get('/v1/entities/filter-options/attributes', { params }),
}

export const facetApi = {
  // Facet Types
  getFacetTypes: (params?: any) => api.get('/v1/facets/types', { params }),
  getFacetType: (id: string) => api.get(`/v1/facets/types/${id}`),
  getFacetTypeBySlug: (slug: string) => api.get(`/v1/facets/types/by-slug/${slug}`),
  createFacetType: (data: any) => api.post('/v1/facets/types', data),
  updateFacetType: (id: string, data: any) => api.put(`/v1/facets/types/${id}`, data),
  deleteFacetType: (id: string) => api.delete(`/v1/facets/types/${id}`),

  // Facet Values
  getFacetValues: (params?: any) => api.get('/v1/facets/values', { params }),
  getFacetValue: (id: string) => api.get(`/v1/facets/values/${id}`),
  createFacetValue: (data: any) => api.post('/v1/facets/values', data),
  updateFacetValue: (id: string, data: any) => api.put(`/v1/facets/values/${id}`, data),
  verifyFacetValue: (id: string, params?: any) => api.put(`/v1/facets/values/${id}/verify`, null, { params }),
  deleteFacetValue: (id: string) => api.delete(`/v1/facets/values/${id}`),

  // Entity Facets Summary
  getEntityFacetsSummary: (entityId: string, params?: any) =>
    api.get(`/v1/facets/entity/${entityId}/summary`, { params }),

  // AI Schema Generation
  generateFacetTypeSchema: (data: { name: string; name_plural?: string; description?: string; applicable_entity_types?: string[] }) =>
    api.post('/v1/facets/types/generate-schema', data),
}

export const relationApi = {
  // Relation Types
  getRelationTypes: (params?: any) => api.get('/v1/relations/types', { params }),
  getRelationType: (id: string) => api.get(`/v1/relations/types/${id}`),
  getRelationTypeBySlug: (slug: string) => api.get(`/v1/relations/types/by-slug/${slug}`),
  createRelationType: (data: any) => api.post('/v1/relations/types', data),
  updateRelationType: (id: string, data: any) => api.put(`/v1/relations/types/${id}`, data),
  deleteRelationType: (id: string) => api.delete(`/v1/relations/types/${id}`),

  // Entity Relations
  getRelations: (params?: any) => api.get('/v1/relations', { params }),
  getRelation: (id: string) => api.get(`/v1/relations/${id}`),
  createRelation: (data: any) => api.post('/v1/relations', data),
  updateRelation: (id: string, data: any) => api.put(`/v1/relations/${id}`, data),
  verifyRelation: (id: string, params?: any) => api.put(`/v1/relations/${id}/verify`, null, { params }),
  deleteRelation: (id: string) => api.delete(`/v1/relations/${id}`),

  // Relation Graph
  getEntityRelationsGraph: (entityId: string, params?: any) =>
    api.get(`/v1/relations/graph/${entityId}`, { params }),
}

export const analysisApi = {
  // Analysis Templates
  getTemplates: (params?: any) => api.get('/v1/analysis/templates', { params }),
  getTemplate: (id: string) => api.get(`/v1/analysis/templates/${id}`),
  getTemplateBySlug: (slug: string) => api.get(`/v1/analysis/templates/by-slug/${slug}`),
  createTemplate: (data: any) => api.post('/v1/analysis/templates', data),
  updateTemplate: (id: string, data: any) => api.put(`/v1/analysis/templates/${id}`, data),
  deleteTemplate: (id: string) => api.delete(`/v1/analysis/templates/${id}`),

  // Analysis Overview & Reports
  getOverview: (params?: any) => api.get('/v1/analysis/overview', { params }),
  getEntityReport: (entityId: string, params?: any) =>
    api.get(`/v1/analysis/report/${entityId}`, { params }),
  getStats: (params?: any) => api.get('/v1/analysis/stats', { params }),
}

// PySis API
export const pysisApi = {
  // Templates
  getTemplates: (params?: any) => api.get('/admin/pysis/templates', { params }),
  getTemplate: (id: string) => api.get(`/admin/pysis/templates/${id}`),
  createTemplate: (data: any) => api.post('/admin/pysis/templates', data),
  updateTemplate: (id: string, data: any) => api.put(`/admin/pysis/templates/${id}`, data),
  deleteTemplate: (id: string) => api.delete(`/admin/pysis/templates/${id}`),

  // Processes
  getProcesses: (locationName: string) => api.get(`/admin/pysis/locations/${encodeURIComponent(locationName)}/processes`),
  createProcess: (locationName: string, data: any) => api.post(`/admin/pysis/locations/${encodeURIComponent(locationName)}/processes`, data),
  getProcess: (id: string) => api.get(`/admin/pysis/processes/${id}`),
  updateProcess: (id: string, data: any) => api.put(`/admin/pysis/processes/${id}`, data),
  deleteProcess: (id: string) => api.delete(`/admin/pysis/processes/${id}`),
  applyTemplate: (processId: string, data: any) => api.post(`/admin/pysis/processes/${processId}/apply-template`, data),

  // Fields
  getFields: (processId: string) => api.get(`/admin/pysis/processes/${processId}/fields`),
  createField: (processId: string, data: any) => api.post(`/admin/pysis/processes/${processId}/fields`, data),
  updateField: (fieldId: string, data: any) => api.put(`/admin/pysis/fields/${fieldId}`, data),
  updateFieldValue: (fieldId: string, data: any) => api.put(`/admin/pysis/fields/${fieldId}/value`, data),
  deleteField: (fieldId: string) => api.delete(`/admin/pysis/fields/${fieldId}`),

  // Sync
  pullFromPySis: (processId: string) => api.post(`/admin/pysis/processes/${processId}/sync/pull`),
  pushToPySis: (processId: string, fieldIds?: string[]) => api.post(`/admin/pysis/processes/${processId}/sync/push`, { field_ids: fieldIds }),
  pushFieldToPySis: (fieldId: string) => api.post(`/admin/pysis/fields/${fieldId}/sync/push`),

  // AI Generation
  generateFields: (processId: string, fieldIds?: string[]) => api.post(`/admin/pysis/processes/${processId}/generate`, { field_ids: fieldIds }),
  generateField: (fieldId: string) => api.post(`/admin/pysis/fields/${fieldId}/generate`),

  // Accept/Reject AI Suggestions
  acceptAiSuggestion: (fieldId: string, pushToPysis?: boolean) => api.post(`/admin/pysis/fields/${fieldId}/accept-ai`, { push_to_pysis: pushToPysis }),
  rejectAiSuggestion: (fieldId: string) => api.post(`/admin/pysis/fields/${fieldId}/reject-ai`),

  // Field History
  getFieldHistory: (fieldId: string, limit?: number) => api.get(`/admin/pysis/fields/${fieldId}/history`, { params: { limit } }),
  restoreFromHistory: (fieldId: string, historyId: string) => api.post(`/admin/pysis/fields/${fieldId}/restore/${historyId}`),

  // Test
  testConnection: (processId?: string) => api.get('/admin/pysis/test-connection', { params: { process_id: processId } }),

  // Available Processes from PySis
  getAvailableProcesses: () => api.get('/admin/pysis/available-processes'),
}

// Assistant API
export const assistantApi = {
  chat: (data: {
    message: string
    context: any
    conversation_history?: any[]
    mode?: 'read' | 'write'
    language?: 'de' | 'en'
  }) => api.post('/v1/assistant/chat', data),
  chatStream: (data: {
    message: string
    context: any
    conversation_history?: any[]
    mode?: 'read' | 'write'
    language?: 'de' | 'en'
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
  },
  executeAction: (data: { action: any; context: any }) =>
    api.post('/v1/assistant/execute-action', data),
  getCommands: () => api.get('/v1/assistant/commands'),
  getSuggestions: (params: {
    route: string
    entity_type?: string
    entity_id?: string
  }) => api.get('/v1/assistant/suggestions', { params }),

  getInsights: (params: {
    route: string
    view_mode?: string
    entity_type?: string
    entity_id?: string
  }) => api.get('/v1/assistant/insights', { params }),
  uploadAttachment: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/v1/assistant/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  deleteAttachment: (attachmentId: string) =>
    api.delete(`/v1/assistant/upload/${attachmentId}`),

  // Batch operations
  batchAction: (data: {
    action_type: string
    target_filter: Record<string, any>
    action_data: Record<string, any>
    dry_run?: boolean
  }) => api.post('/v1/assistant/batch-action', data),

  getBatchStatus: (batchId: string) =>
    api.get(`/v1/assistant/batch-action/${batchId}/status`),

  cancelBatch: (batchId: string) =>
    api.post(`/v1/assistant/batch-action/${batchId}/cancel`),

  // Wizard operations
  getWizards: () => api.get('/v1/assistant/wizards'),

  startWizard: (wizardType: string, context?: Record<string, any>) =>
    api.post('/v1/assistant/wizards/start', null, {
      params: { wizard_type: wizardType },
      ...(context && { data: context }),
    }),

  wizardRespond: (wizardId: string, value: any) =>
    api.post(`/v1/assistant/wizards/${wizardId}/respond`, { value }),

  wizardBack: (wizardId: string) =>
    api.post(`/v1/assistant/wizards/${wizardId}/back`),

  wizardCancel: (wizardId: string) =>
    api.post(`/v1/assistant/wizards/${wizardId}/cancel`),

  // Reminder operations
  getReminders: (params?: { status?: string; include_past?: boolean; limit?: number }) =>
    api.get('/v1/assistant/reminders', { params }),

  createReminder: (data: {
    message: string
    remind_at: string
    title?: string
    entity_id?: string
    entity_type?: string
    repeat?: 'none' | 'daily' | 'weekly' | 'monthly'
  }) => api.post('/v1/assistant/reminders', data),

  deleteReminder: (reminderId: string) =>
    api.delete(`/v1/assistant/reminders/${reminderId}`),

  dismissReminder: (reminderId: string) =>
    api.post(`/v1/assistant/reminders/${reminderId}/dismiss`),

  snoozeReminder: (reminderId: string, newRemindAt: string) =>
    api.post(`/v1/assistant/reminders/${reminderId}/snooze`, { remind_at: newRemindAt }),

  getDueReminders: () => api.get('/v1/assistant/reminders/due'),
}

// Auth API
export const authApi = {
  login: (data: { email: string; password: string }) => api.post('/auth/login', data),
  logout: () => api.post('/auth/logout'),
  getMe: () => api.get('/auth/me'),
  changePassword: (data: { current_password: string; new_password: string }) =>
    api.post('/auth/change-password', data),
  checkPasswordStrength: (password: string) =>
    api.post<{
      is_valid: boolean
      score: number
      errors: string[]
      suggestions: string[]
      requirements: string
    }>('/auth/check-password-strength', { password }),
}

// Users API
export const userApi = {
  getUsers: (params?: any) => api.get('/admin/users', { params }),
  getUser: (id: string) => api.get(`/admin/users/${id}`),
  createUser: (data: any) => api.post('/admin/users', data),
  updateUser: (id: string, data: any) => api.put(`/admin/users/${id}`, data),
  deleteUser: (id: string) => api.delete(`/admin/users/${id}`),
  resetPassword: (id: string, data: any) => api.post(`/admin/users/${id}/reset-password`, data),
}

// Notification API
export const notificationApi = {
  // Email Addresses
  getEmailAddresses: () => api.get('/admin/notifications/email-addresses'),
  addEmailAddress: (data: { email: string; label?: string }) =>
    api.post('/admin/notifications/email-addresses', data),
  deleteEmailAddress: (id: string) =>
    api.delete(`/admin/notifications/email-addresses/${id}`),
  verifyEmailAddress: (id: string, token: string) =>
    api.post(`/admin/notifications/email-addresses/${id}/verify`, null, { params: { token } }),
  resendVerification: (id: string) =>
    api.post(`/admin/notifications/email-addresses/${id}/resend-verification`),

  // Rules
  getRules: () => api.get('/admin/notifications/rules'),
  getRule: (id: string) => api.get(`/admin/notifications/rules/${id}`),
  createRule: (data: any) => api.post('/admin/notifications/rules', data),
  updateRule: (id: string, data: any) =>
    api.put(`/admin/notifications/rules/${id}`, data),
  deleteRule: (id: string) => api.delete(`/admin/notifications/rules/${id}`),

  // Notifications
  getNotifications: (params?: any) =>
    api.get('/admin/notifications/notifications', { params }),
  getNotification: (id: string) =>
    api.get(`/admin/notifications/notifications/${id}`),
  getUnreadCount: () => api.get('/admin/notifications/notifications/unread-count'),
  markAsRead: (id: string) =>
    api.post(`/admin/notifications/notifications/${id}/read`),
  markAllAsRead: () => api.post('/admin/notifications/notifications/read-all'),

  // Preferences
  getPreferences: () => api.get('/admin/notifications/preferences'),
  updatePreferences: (data: any) =>
    api.put('/admin/notifications/preferences', data),

  // Meta
  getEventTypes: () => api.get('/admin/notifications/event-types'),
  getChannels: () => api.get('/admin/notifications/channels'),

  // Testing
  testWebhook: (data: { url: string; auth?: any }) =>
    api.post('/admin/notifications/test-webhook', data),
}

export default api
