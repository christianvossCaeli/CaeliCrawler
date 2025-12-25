import { api } from './client'
import type {
  CrawlJobListParams,
  CrawlStartRequest,
  AiTaskListParams,
  UserListParams,
  UserCreate,
  UserUpdate,
  UserPasswordReset,
  NotificationRuleCreate,
  NotificationRuleUpdate,
  NotificationListParams,
  NotificationPreferences,
  PySisTemplateCreate,
  PySisTemplateUpdate,
  PySisProcessCreate,
  PySisFieldCreate,
  PySisFieldUpdate,
  PySisFieldValueUpdate,
  DashboardPreferences,
  PySisTemplateListParams,
  PySisApplyTemplateRequest,
} from '@/types/admin'

// Crawler
export const getCrawlerJobs = (params?: CrawlJobListParams) => api.get('/admin/crawler/jobs', { params })
export const getCrawlerJob = (id: string) => api.get(`/admin/crawler/jobs/${id}`)
export const startCrawl = (data: CrawlStartRequest) => api.post('/admin/crawler/start', data)
export const cancelJob = (id: string) => api.post(`/admin/crawler/jobs/${id}/cancel`)
export const getCrawlerStats = () => api.get('/admin/crawler/stats')
export const getCrawlerStatus = () => api.get('/admin/crawler/status')
export const reanalyzeDocuments = (params?: { category_id?: string; reanalyze_all?: boolean; limit?: number }) =>
  api.post('/admin/crawler/reanalyze', null, { params })
export const getRunningJobs = () => api.get('/admin/crawler/running')
export const getJobLog = (id: string, limit?: number) => api.get(`/admin/crawler/jobs/${id}/log`, { params: { limit } })

// AI Tasks
export const getAiTasks = (params?: AiTaskListParams) => api.get('/admin/crawler/ai-tasks', { params })
export const getRunningAiTasks = () => api.get('/admin/crawler/ai-tasks/running')
export const cancelAiTask = (id: string) => api.post(`/admin/crawler/ai-tasks/${id}/cancel`)

// Document Processing
export const processDocument = (id: string) => api.post(`/admin/crawler/documents/${id}/process`)
export const analyzeDocument = (id: string, skipRelevanceCheck = false) =>
  api.post(`/admin/crawler/documents/${id}/analyze`, null, { params: { skip_relevance_check: skipRelevanceCheck } })
export const processAllPending = () => api.post('/admin/crawler/documents/process-pending')
export const stopAllProcessing = () => api.post('/admin/crawler/documents/stop-all')
export const reanalyzeFiltered = (limit = 100) => api.post('/admin/crawler/documents/reanalyze-filtered', null, { params: { limit } })

// Users
export const getUsers = (params?: UserListParams) => api.get('/admin/users', { params })
export const getUser = (id: string) => api.get(`/admin/users/${id}`)
export const createUser = (data: UserCreate) => api.post('/admin/users', data)
export const updateUser = (id: string, data: UserUpdate) => api.put(`/admin/users/${id}`, data)
export const deleteUser = (id: string) => api.delete(`/admin/users/${id}`)
export const resetPassword = (id: string, data: UserPasswordReset) =>
  api.post(`/admin/users/${id}/reset-password`, data)

// Audit Log
export const getAuditLogs = (params?: {
  page?: number
  per_page?: number
  action?: string
  entity_type?: string
  entity_id?: string
  user_id?: string
  start_date?: string
  end_date?: string
}) => api.get('/admin/audit', { params })
export const getEntityAuditHistory = (entityType: string, entityId: string, params?: { page?: number; per_page?: number }) =>
  api.get(`/admin/audit/entity/${entityType}/${entityId}`, { params })
export const getUserAuditHistory = (userId: string, params?: { page?: number; per_page?: number }) =>
  api.get(`/admin/audit/user/${userId}`, { params })
export const getAuditStats = () => api.get('/admin/audit/stats')

// Version History
export const getVersions = (entityType: string, entityId: string, params?: { limit?: number; offset?: number }) =>
  api.get(`/admin/versions/${entityType}/${entityId}`, { params })
export const getVersion = (entityType: string, entityId: string, versionNumber: number) =>
  api.get(`/admin/versions/${entityType}/${entityId}/${versionNumber}`)
export const getEntityState = (entityType: string, entityId: string, versionNumber: number) =>
  api.get(`/admin/versions/${entityType}/${entityId}/${versionNumber}/state`)

// Notifications
export const getEmailAddresses = () => api.get('/admin/notifications/email-addresses')
export const addEmailAddress = (data: { email: string; label?: string }) =>
  api.post('/admin/notifications/email-addresses', data)
export const deleteEmailAddress = (id: string) =>
  api.delete(`/admin/notifications/email-addresses/${id}`)
export const verifyEmailAddress = (id: string, token: string) =>
  api.post(`/admin/notifications/email-addresses/${id}/verify`, null, { params: { token } })
export const resendVerification = (id: string) =>
  api.post(`/admin/notifications/email-addresses/${id}/resend-verification`)
export const getRules = () => api.get('/admin/notifications/rules')
export const getRule = (id: string) => api.get(`/admin/notifications/rules/${id}`)
export const createRule = (data: NotificationRuleCreate) => api.post('/admin/notifications/rules', data)
export const updateRule = (id: string, data: NotificationRuleUpdate) =>
  api.put(`/admin/notifications/rules/${id}`, data)
export const deleteRule = (id: string) => api.delete(`/admin/notifications/rules/${id}`)
export const getNotifications = (params?: NotificationListParams) =>
  api.get('/admin/notifications/notifications', { params })
export const getNotification = (id: string) =>
  api.get(`/admin/notifications/notifications/${id}`)
export const getUnreadCount = () => api.get('/admin/notifications/notifications/unread-count')
export const markAsRead = (id: string) =>
  api.post(`/admin/notifications/notifications/${id}/read`)
export const markAllAsRead = () => api.post('/admin/notifications/notifications/read-all')
export const getNotificationPreferences = () => api.get('/admin/notifications/preferences')
export const updateNotificationPreferences = (data: NotificationPreferences) =>
  api.put('/admin/notifications/preferences', data)
export const getDeviceTokens = () => api.get('/admin/notifications/device-tokens')
export const addDeviceToken = (data: { token: string; platform: 'web' | 'ios' | 'android'; device_name?: string }) =>
  api.post('/admin/notifications/device-token', data)
export const deleteDeviceToken = (token: string) =>
  api.delete(`/admin/notifications/device-token/${encodeURIComponent(token)}`)
export const deactivateDeviceToken = (token: string) =>
  api.post(`/admin/notifications/device-token/${encodeURIComponent(token)}/deactivate`)
export const getEventTypes = () => api.get('/admin/notifications/event-types')
export const getChannels = () => api.get('/admin/notifications/channels')
export const testNotificationWebhook = (data: { url: string; auth?: { type: string; config: Record<string, string> } }) =>
  api.post('/admin/notifications/test-webhook', data)

// PySis
export const getPySisTemplates = (params?: PySisTemplateListParams) =>
  api.get('/admin/pysis/templates', { params })
export const getPySisTemplate = (id: string) => api.get(`/admin/pysis/templates/${id}`)
export const createPySisTemplate = (data: PySisTemplateCreate) => api.post('/admin/pysis/templates', data)
export const updatePySisTemplate = (id: string, data: PySisTemplateUpdate) => api.put(`/admin/pysis/templates/${id}`, data)
export const deletePySisTemplate = (id: string) => api.delete(`/admin/pysis/templates/${id}`)
export const getPySisProcesses = (locationName: string) =>
  api.get(`/admin/pysis/locations/${encodeURIComponent(locationName)}/processes`)
export const createPySisProcess = (locationName: string, data: PySisProcessCreate) =>
  api.post(`/admin/pysis/locations/${encodeURIComponent(locationName)}/processes`, data)
export const getPySisProcess = (id: string) => api.get(`/admin/pysis/processes/${id}`)
export const updatePySisProcess = (id: string, data: { status?: string }) =>
  api.put(`/admin/pysis/processes/${id}`, data)
export const deletePySisProcess = (id: string) => api.delete(`/admin/pysis/processes/${id}`)
export const applyPySisTemplate = (processId: string, data: PySisApplyTemplateRequest) =>
  api.post(`/admin/pysis/processes/${processId}/apply-template`, data)
export const getPySisFields = (processId: string) => api.get(`/admin/pysis/processes/${processId}/fields`)
export const createPySisField = (processId: string, data: PySisFieldCreate) =>
  api.post(`/admin/pysis/processes/${processId}/fields`, data)
export const updatePySisField = (fieldId: string, data: PySisFieldUpdate) => api.put(`/admin/pysis/fields/${fieldId}`, data)
export const updatePySisFieldValue = (fieldId: string, data: PySisFieldValueUpdate) =>
  api.put(`/admin/pysis/fields/${fieldId}/value`, data)
export const deletePySisField = (fieldId: string) => api.delete(`/admin/pysis/fields/${fieldId}`)
export const pullFromPySis = (processId: string) => api.post(`/admin/pysis/processes/${processId}/sync/pull`)
export const pushToPySis = (processId: string, fieldIds?: string[]) => api.post(`/admin/pysis/processes/${processId}/sync/push`, { field_ids: fieldIds })
export const pushFieldToPySis = (fieldId: string) => api.post(`/admin/pysis/fields/${fieldId}/sync/push`)
export const generatePySisFields = (processId: string, fieldIds?: string[]) => api.post(`/admin/pysis/processes/${processId}/generate`, { field_ids: fieldIds })
export const generatePySisField = (fieldId: string) => api.post(`/admin/pysis/fields/${fieldId}/generate`)
export const acceptPySisAiSuggestion = (fieldId: string, pushToPysis?: boolean) => api.post(`/admin/pysis/fields/${fieldId}/accept-ai`, { push_to_pysis: pushToPysis })
export const rejectPySisAiSuggestion = (fieldId: string) => api.post(`/admin/pysis/fields/${fieldId}/reject-ai`)
export const getPySisFieldHistory = (fieldId: string, limit?: number) => api.get(`/admin/pysis/fields/${fieldId}/history`, { params: { limit } })
export const restoreFromPySisHistory = (fieldId: string, historyId: string) => api.post(`/admin/pysis/fields/${fieldId}/restore/${historyId}`)
export const testPySisConnection = (processId?: string) => api.get('/admin/pysis/test-connection', { params: { process_id: processId } })
export const getPySisAvailableProcesses = () => api.get('/admin/pysis/available-processes')
export const analyzeForPySisFacets = (data: {
  entity_id: string
  process_id?: string
  include_empty?: boolean
  min_confidence?: number
}) => api.post('/v1/pysis-facets/analyze', data)
export const enrichFacetsFromPySis = (data: {
  entity_id: string
  facet_type_id?: string
  overwrite?: boolean
}) => api.post('/v1/pysis-facets/enrich', data)
export const getPysisFacetsPreview = (params: {
  entity_id: string
  operation: 'analyze' | 'enrich'
}) => api.get('/v1/pysis-facets/preview', { params })
export const getPysisFacetsStatus = (entityId: string) =>
  api.get('/v1/pysis-facets/status', { params: { entity_id: entityId } })
export const getPysisFacetsSummary = (entityId: string) =>
  api.get('/v1/pysis-facets/summary', { params: { entity_id: entityId } })

// Crawl Presets
export const listCrawlPresets = (params?: {
  page?: number
  per_page?: number
  favorites_only?: boolean
  status?: string
  search?: string
}) => api.get('/admin/crawl-presets', { params })
export const getCrawlPreset = (presetId: string) =>
  api.get(`/admin/crawl-presets/${presetId}`)
export const createCrawlPreset = (data: {
  name: string
  description?: string
  filters: Record<string, any>
  schedule_cron?: string
  schedule_enabled?: boolean
}) => api.post('/admin/crawl-presets', data)
export const updateCrawlPreset = (presetId: string, data: {
  name?: string
  description?: string
  filters?: Record<string, any>
  schedule_cron?: string
  schedule_enabled?: boolean
  is_favorite?: boolean
  status?: 'active' | 'archived'
}) => api.put(`/admin/crawl-presets/${presetId}`, data)
export const deleteCrawlPreset = (presetId: string) =>
  api.delete(`/admin/crawl-presets/${presetId}`)
export const executeCrawlPreset = (presetId: string, options?: { force?: boolean }) =>
  api.post<{
    preset_id: string
    jobs_created: number
    job_ids: string[]
    sources_matched: number
    message: string
  }>(`/admin/crawl-presets/${presetId}/execute`, options || {})
export const toggleCrawlPresetFavorite = (presetId: string) =>
  api.post<{
    id: string
    is_favorite: boolean
    message: string
  }>(`/admin/crawl-presets/${presetId}/toggle-favorite`)
export const createCrawlPresetFromFilters = (data: {
  name: string
  description?: string
  filters: Record<string, any>
  schedule_cron?: string
  schedule_enabled?: boolean
}) => api.post('/admin/crawl-presets/from-filters', data)
export const previewCrawlPreset = (presetId: string) =>
  api.get<{
    preset_id: string
    sources_count: number
    sources_preview: Array<{ id: string; name: string; url: string }>
    has_more: boolean
  }>(`/admin/crawl-presets/${presetId}/preview`)
export const getCrawlPresetSchedulePresets = () =>
  api.get<Array<{ label: string; cron: string; description: string }>>('/admin/crawl-presets/schedule-presets')
export const previewCrawlPresetFilters = (filters: Record<string, any>) =>
  api.post<{
    sources_count: number
    sources_preview: Array<{ id: string; name: string; url: string }>
    has_more: boolean
  }>('/admin/crawl-presets/preview-filters', filters)

// Custom Summaries
export const createSummaryFromPrompt = (data: { prompt: string; name?: string }) =>
  api.post<{
    id: string
    name: string
    interpretation: Record<string, any>
    widgets_created: number
    message: string
  }>('/admin/summaries/from-prompt', data)
export const createSummary = (data: {
  name: string
  description?: string
  original_prompt: string
  interpreted_config?: Record<string, any>
  layout_config?: Record<string, any>
  trigger_type?: string
  schedule_cron?: string
  trigger_category_id?: string
  trigger_preset_id?: string
}) => api.post('/admin/summaries', data)
export const listSummaries = (params?: {
  page?: number
  per_page?: number
  favorites_only?: boolean
  status?: string
  search?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}, options?: { signal?: AbortSignal }) =>
  api.get('/admin/summaries', { params, signal: options?.signal })
export const getSummary = (summaryId: string, params?: {
  include_widgets?: boolean
  include_last_execution?: boolean
}, options?: { signal?: AbortSignal }) =>
  api.get(`/admin/summaries/${summaryId}`, { params, signal: options?.signal })
export const updateSummary = (summaryId: string, data: {
  name?: string
  description?: string
  layout_config?: Record<string, any>
  trigger_type?: string
  schedule_cron?: string
  trigger_category_id?: string
  trigger_preset_id?: string
  schedule_enabled?: boolean
  check_relevance?: boolean
  relevance_threshold?: number
  auto_expand?: boolean
  is_favorite?: boolean
  status?: string
}) => api.put(`/admin/summaries/${summaryId}`, data)
export const deleteSummary = (summaryId: string) => api.delete(`/admin/summaries/${summaryId}`)
export const executeSummary = (summaryId: string, options?: { force?: boolean }) =>
  api.post<{
    execution_id: string
    status: string
    has_changes: boolean
    cached_data?: Record<string, any>
    message: string
  }>(`/admin/summaries/${summaryId}/execute`, options || {})
export const listSummaryExecutions = (summaryId: string, params?: { limit?: number }) =>
  api.get(`/admin/summaries/${summaryId}/executions`, { params })
export const toggleSummaryFavorite = (summaryId: string) =>
  api.post<{
    id: string
    is_favorite: boolean
    message: string
  }>(`/admin/summaries/${summaryId}/toggle-favorite`)
export const addSummaryWidget = (summaryId: string, data: {
  widget_type: string
  title: string
  subtitle?: string
  position_x?: number
  position_y?: number
  width?: number
  height?: number
  query_config?: Record<string, any>
  visualization_config?: Record<string, any>
}) => api.post(`/admin/summaries/${summaryId}/widgets`, data)
export const updateSummaryWidget = (summaryId: string, widgetId: string, data: {
  title?: string
  subtitle?: string
  position_x?: number
  position_y?: number
  width?: number
  height?: number
  query_config?: Record<string, any>
  visualization_config?: Record<string, any>
}) => api.put(`/admin/summaries/${summaryId}/widgets/${widgetId}`, data)
export const deleteSummaryWidget = (summaryId: string, widgetId: string) =>
  api.delete(`/admin/summaries/${summaryId}/widgets/${widgetId}`)
export const createSummaryShare = (summaryId: string, data: {
  password?: string
  expires_days?: number
  allow_export?: boolean
}) => api.post(`/admin/summaries/${summaryId}/share`, data)
export const listSummaryShares = (summaryId: string) =>
  api.get(`/admin/summaries/${summaryId}/shares`)
export const deactivateSummaryShare = (summaryId: string, shareId: string) =>
  api.delete(`/admin/summaries/${summaryId}/shares/${shareId}`)
export const getSummarySchedulePresets = () =>
  api.get<Array<{ label: string; cron: string; description: string }>>('/admin/summaries/schedule-presets')
export const exportSummaryPdf = (summaryId: string) =>
  api.get(`/admin/summaries/${summaryId}/export/pdf`, { responseType: 'blob' })
export const exportSummaryExcel = (summaryId: string) =>
  api.get(`/admin/summaries/${summaryId}/export/excel`, { responseType: 'blob' })

// Dashboard
export const getDashboardPreferences = () => api.get('/v1/dashboard/preferences')
export const updateDashboardPreferences = (data: DashboardPreferences) =>
  api.put('/v1/dashboard/preferences', data)
export const getDashboardStats = () => api.get('/v1/dashboard/stats')
export const getDashboardActivityFeed = (params?: { limit?: number; offset?: number }) =>
  api.get('/v1/dashboard/activity', { params })
export const getDashboardInsights = (params?: { period_days?: number }) =>
  api.get('/v1/dashboard/insights', { params })
export const getDashboardChartData = (chartType: string) =>
  api.get(`/v1/dashboard/charts/${chartType}`)
