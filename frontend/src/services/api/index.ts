// Export base client
import { api } from './client'
export { api }

// Entity API
import * as entityExports from './entities'
export const entityApi = {
  // Entity Types
  getEntityTypes: entityExports.getEntityTypes,
  getEntityType: entityExports.getEntityType,
  getEntityTypeBySlug: entityExports.getEntityTypeBySlug,
  createEntityType: entityExports.createEntityType,
  updateEntityType: entityExports.updateEntityType,
  deleteEntityType: entityExports.deleteEntityType,
  // Entities
  getEntities: entityExports.getEntities,
  getEntity: entityExports.getEntity,
  getEntityBySlug: entityExports.getEntityBySlug,
  getEntityBrief: entityExports.getEntityBrief,
  getEntityChildren: entityExports.getEntityChildren,
  getEntityHierarchy: entityExports.getEntityHierarchy,
  createEntity: entityExports.createEntity,
  updateEntity: entityExports.updateEntity,
  deleteEntity: entityExports.deleteEntity,
  getEntityExternalData: entityExports.getEntityExternalData,
  getEntityDocuments: entityExports.getEntityDocuments,
  getEntitySources: entityExports.getEntitySources,
  // Filter Options
  getLocationFilterOptions: entityExports.getLocationFilterOptions,
  getAttributeFilterOptions: entityExports.getAttributeFilterOptions,
  // Search
  searchEntities: entityExports.searchEntities,
  // GeoJSON
  getEntitiesGeoJSON: entityExports.getEntitiesGeoJSON,
}

// Entity Data Enrichment API
export const entityDataApi = {
  getEnrichmentSources: entityExports.getEnrichmentSources,
  analyzeForFacets: entityExports.analyzeEntityForFacets,
  getAnalysisPreview: entityExports.getAnalysisPreview,
  applyChanges: entityExports.applyEnrichmentChanges,
}

// Favorites API
export const favoritesApi = {
  list: entityExports.listFavorites,
  add: entityExports.addFavorite,
  check: entityExports.checkFavorite,
  remove: entityExports.removeFavorite,
  removeByEntity: entityExports.removeFavoriteByEntity,
}

// Entity Attachments API
export const attachmentApi = {
  upload: entityExports.uploadAttachment,
  list: entityExports.listAttachments,
  get: entityExports.getAttachment,
  download: entityExports.downloadAttachment,
  getThumbnailUrl: entityExports.getAttachmentThumbnailUrl,
  delete: entityExports.deleteAttachment,
  analyze: entityExports.analyzeAttachment,
  update: entityExports.updateAttachment,
  applyFacets: entityExports.applyAttachmentFacets,
}

// Facet API
import * as facetExports from './facets'
export const facetApi = {
  // Facet Types
  getFacetTypes: facetExports.getFacetTypes,
  getFacetType: facetExports.getFacetType,
  getFacetTypeBySlug: facetExports.getFacetTypeBySlug,
  createFacetType: facetExports.createFacetType,
  updateFacetType: facetExports.updateFacetType,
  deleteFacetType: facetExports.deleteFacetType,
  // Facet Values
  getFacetValues: facetExports.getFacetValues,
  getFacetValue: facetExports.getFacetValue,
  createFacetValue: facetExports.createFacetValue,
  updateFacetValue: facetExports.updateFacetValue,
  verifyFacetValue: facetExports.verifyFacetValue,
  deleteFacetValue: facetExports.deleteFacetValue,
  // Entity Facets Summary
  getEntityFacetsSummary: facetExports.getEntityFacetsSummary,
  // AI Schema Generation
  generateFacetTypeSchema: facetExports.generateFacetTypeSchema,
  // Full-Text Search
  searchFacetValues: facetExports.searchFacetValues,
  // History (Time-Series Data)
  getEntityHistory: facetExports.getEntityHistory,
  getEntityHistoryAggregated: facetExports.getEntityHistoryAggregated,
  addHistoryDataPoint: facetExports.addHistoryDataPoint,
  addHistoryDataPointsBulk: facetExports.addHistoryDataPointsBulk,
  updateHistoryDataPoint: facetExports.updateHistoryDataPoint,
  deleteHistoryDataPoint: facetExports.deleteHistoryDataPoint,
}

// Relation API
import * as relationExports from './relations'
export const relationApi = {
  // Relation Types
  getRelationTypes: relationExports.getRelationTypes,
  getRelationType: relationExports.getRelationType,
  getRelationTypeBySlug: relationExports.getRelationTypeBySlug,
  createRelationType: relationExports.createRelationType,
  updateRelationType: relationExports.updateRelationType,
  deleteRelationType: relationExports.deleteRelationType,
  // Entity Relations
  getRelations: relationExports.getRelations,
  getRelation: relationExports.getRelation,
  createRelation: relationExports.createRelation,
  updateRelation: relationExports.updateRelation,
  verifyRelation: relationExports.verifyRelation,
  deleteRelation: relationExports.deleteRelation,
  // Relation Graph
  getEntityRelationsGraph: relationExports.getEntityRelationsGraph,
}

// Sources & Data API
import * as sourcesExports from './sources'
export const adminApi = {
  // Categories
  getCategories: sourcesExports.getCategories,
  getCategory: sourcesExports.getCategory,
  createCategory: sourcesExports.createCategory,
  updateCategory: sourcesExports.updateCategory,
  deleteCategory: sourcesExports.deleteCategory,
  getCategoryStats: sourcesExports.getCategoryStats,
  previewCategoryAiSetup: sourcesExports.previewCategoryAiSetup,
  assignSourcesByTags: sourcesExports.assignSourcesByTags,
  // Sources
  getSources: sourcesExports.getSources,
  getSource: sourcesExports.getSource,
  createSource: sourcesExports.createSource,
  updateSource: sourcesExports.updateSource,
  deleteSource: sourcesExports.deleteSource,
  bulkImportSources: sourcesExports.bulkImportSources,
  resetSource: sourcesExports.resetSource,
  getSourceCounts: sourcesExports.getSourceCounts,
  getAvailableTags: sourcesExports.getAvailableTags,
  getSourcesByTags: sourcesExports.getSourcesByTags,
  // SharePoint
  testSharePointConnection: sourcesExports.testSharePointConnection,
  getSharePointStatus: sourcesExports.getSharePointStatus,
  getSharePointSites: sourcesExports.getSharePointSites,
  getSharePointDrives: sourcesExports.getSharePointDrives,
  getSharePointFiles: sourcesExports.getSharePointFiles,
  // API Import
  getApiImportTemplates: sourcesExports.getApiImportTemplates,
  getApiImportTemplate: sourcesExports.getApiImportTemplate,
  previewApiImport: sourcesExports.previewApiImport,
  executeApiImport: sourcesExports.executeApiImport,
  // AI Discovery
  getAiDiscoveryExamples: sourcesExports.getAiDiscoveryExamples,
  discoverSources: sourcesExports.discoverSources,
  importDiscoveredSources: sourcesExports.importDiscoveredSources,
  discoverSourcesV2: sourcesExports.discoverSourcesV2,
  importApiData: sourcesExports.importApiData,
  // API Configurations (formerly API Templates)
  saveApiFromDiscovery: sourcesExports.saveApiFromDiscovery,
  // Crawler (from admin.ts)
  getCrawlerJobs: adminExports.getCrawlerJobs,
  getCrawlerJob: adminExports.getCrawlerJob,
  startCrawl: adminExports.startCrawl,
  cancelJob: adminExports.cancelJob,
  getCrawlerStats: adminExports.getCrawlerStats,
  getCrawlerStatus: adminExports.getCrawlerStatus,
  reanalyzeDocuments: adminExports.reanalyzeDocuments,
  getRunningJobs: adminExports.getRunningJobs,
  getJobLog: adminExports.getJobLog,
  // AI Tasks (from admin.ts)
  getAiTasks: adminExports.getAiTasks,
  getRunningAiTasks: adminExports.getRunningAiTasks,
  cancelAiTask: adminExports.cancelAiTask,
  // Document Processing (from admin.ts)
  processDocument: adminExports.processDocument,
  analyzeDocument: adminExports.analyzeDocument,
  processAllPending: adminExports.processAllPending,
  stopAllProcessing: adminExports.stopAllProcessing,
  reanalyzeFiltered: adminExports.reanalyzeFiltered,
}

// External APIs
export const externalApiApi = {
  list: sourcesExports.listExternalApis,
  get: sourcesExports.getExternalApi,
  create: sourcesExports.createExternalApi,
  update: sourcesExports.updateExternalApi,
  delete: sourcesExports.deleteExternalApi,
  triggerSync: sourcesExports.triggerExternalApiSync,
  testConnection: sourcesExports.testExternalApiConnection,
  getStats: sourcesExports.getExternalApiStats,
  listRecords: sourcesExports.listExternalApiRecords,
  getRecord: sourcesExports.getExternalApiRecord,
  deleteRecord: sourcesExports.deleteExternalApiRecord,
  getAvailableApiTypes: sourcesExports.getAvailableApiTypes,
}

// Public Data API
export const dataApi = {
  // Extracted Data
  getExtractedData: sourcesExports.getExtractedData,
  getExtractionStats: sourcesExports.getExtractionStats,
  getExtractionLocations: sourcesExports.getExtractionLocations,
  getExtractionCountries: sourcesExports.getExtractionCountries,
  getDisplayConfig: sourcesExports.getDisplayConfig,
  // Documents
  getDocuments: sourcesExports.getDocuments,
  getDocument: sourcesExports.getDocument,
  getDocumentLocations: sourcesExports.getDocumentLocations,
  searchDocuments: sourcesExports.searchDocuments,
  // Verification
  verifyExtraction: sourcesExports.verifyExtraction,
  // Municipalities
  getMunicipalities: sourcesExports.getMunicipalities,
  getMunicipalityReport: sourcesExports.getMunicipalityReport,
  getMunicipalityDocuments: sourcesExports.getMunicipalityDocuments,
  getOverviewReport: sourcesExports.getOverviewReport,
  // History
  getMunicipalityHistory: sourcesExports.getMunicipalityHistory,
  getCrawlHistory: sourcesExports.getCrawlHistory,
}

// Export API
export const exportApi = {
  exportJson: sourcesExports.exportJson,
  exportCsv: sourcesExports.exportCsv,
  getChangesFeed: sourcesExports.getChangesFeed,
  testWebhook: sourcesExports.testWebhook,
  // Async Export
  startAsyncExport: sourcesExports.startAsyncExport,
  getExportJobStatus: sourcesExports.getExportJobStatus,
  downloadExport: sourcesExports.downloadExport,
  cancelExportJob: sourcesExports.cancelExportJob,
  listExportJobs: sourcesExports.listExportJobs,
}

// Location API
export const locationApi = {
  search: sourcesExports.searchLocations,
  list: sourcesExports.listLocations,
  listWithSources: sourcesExports.listLocationsWithSources,
  get: sourcesExports.getLocation,
  create: sourcesExports.createLocation,
  update: sourcesExports.updateLocation,
  delete: sourcesExports.deleteLocation,
  getCountries: sourcesExports.getCountries,
  getAdminLevels: sourcesExports.getAdminLevels,
  linkSources: sourcesExports.linkSources,
  enrichAdminLevels: sourcesExports.enrichAdminLevels,
  getStates: sourcesExports.getStates,
}

// Municipality API (Legacy alias)
export const municipalityApi = {
  search: (q: string, params?: { country?: string; admin_level_1?: string; limit?: number }) =>
    locationApi.search(q, params),
  list: (params?: import('@/types/admin').LocationListParams) => locationApi.list(params),
  listWithSources: (params?: import('@/types/admin').LocationListParams) => locationApi.listWithSources(params),
  linkSources: () => locationApi.linkSources(),
  enrichDistricts: (limit?: number) => locationApi.enrichAdminLevels('DE', limit),
  get: (id: string) => locationApi.get(id),
  create: (data: import('@/types/admin').LocationCreate) => locationApi.create(data),
  update: (id: string, data: import('@/types/admin').LocationUpdate) => locationApi.update(id, data),
  delete: (id: string) => locationApi.delete(id),
  getStates: () => locationApi.getStates('DE'),
}

// Admin API - Import admin-specific functions
import * as adminExports from './admin'

// User API
export const userApi = {
  getUsers: adminExports.getUsers,
  getUser: adminExports.getUser,
  createUser: adminExports.createUser,
  updateUser: adminExports.updateUser,
  deleteUser: adminExports.deleteUser,
  resetPassword: adminExports.resetPassword,
}

// Audit Log API
export const auditApi = {
  getAuditLogs: adminExports.getAuditLogs,
  getEntityAuditHistory: adminExports.getEntityAuditHistory,
  getUserAuditHistory: adminExports.getUserAuditHistory,
  getAuditStats: adminExports.getAuditStats,
}

// Version History API
export const versionApi = {
  getVersions: adminExports.getVersions,
  getVersion: adminExports.getVersion,
  getEntityState: adminExports.getEntityState,
}

// Notification API
export const notificationApi = {
  // Email Addresses
  getEmailAddresses: adminExports.getEmailAddresses,
  addEmailAddress: adminExports.addEmailAddress,
  deleteEmailAddress: adminExports.deleteEmailAddress,
  verifyEmailAddress: adminExports.verifyEmailAddress,
  resendVerification: adminExports.resendVerification,
  // Rules
  getRules: adminExports.getRules,
  getRule: adminExports.getRule,
  createRule: adminExports.createRule,
  updateRule: adminExports.updateRule,
  deleteRule: adminExports.deleteRule,
  // Notifications
  getNotifications: adminExports.getNotifications,
  getNotification: adminExports.getNotification,
  getUnreadCount: adminExports.getUnreadCount,
  markAsRead: adminExports.markAsRead,
  markAllAsRead: adminExports.markAllAsRead,
  // Preferences
  getPreferences: adminExports.getNotificationPreferences,
  updatePreferences: adminExports.updateNotificationPreferences,
  // Device Tokens
  getDeviceTokens: adminExports.getDeviceTokens,
  addDeviceToken: adminExports.addDeviceToken,
  deleteDeviceToken: adminExports.deleteDeviceToken,
  deactivateDeviceToken: adminExports.deactivateDeviceToken,
  // Meta
  getEventTypes: adminExports.getEventTypes,
  getChannels: adminExports.getChannels,
  // Testing
  testWebhook: adminExports.testNotificationWebhook,
}

// PySis API
export const pysisApi = {
  // Templates
  getTemplates: adminExports.getPySisTemplates,
  getTemplate: adminExports.getPySisTemplate,
  createTemplate: adminExports.createPySisTemplate,
  updateTemplate: adminExports.updatePySisTemplate,
  deleteTemplate: adminExports.deletePySisTemplate,
  // Processes
  getProcesses: adminExports.getPySisProcesses,
  createProcess: adminExports.createPySisProcess,
  getProcess: adminExports.getPySisProcess,
  updateProcess: adminExports.updatePySisProcess,
  deleteProcess: adminExports.deletePySisProcess,
  applyTemplate: adminExports.applyPySisTemplate,
  // Fields
  getFields: adminExports.getPySisFields,
  createField: adminExports.createPySisField,
  updateField: adminExports.updatePySisField,
  updateFieldValue: adminExports.updatePySisFieldValue,
  deleteField: adminExports.deletePySisField,
  // Sync
  pullFromPySis: adminExports.pullFromPySis,
  pushToPySis: adminExports.pushToPySis,
  pushFieldToPySis: adminExports.pushFieldToPySis,
  // AI Generation
  generateFields: adminExports.generatePySisFields,
  generateField: adminExports.generatePySisField,
  // Accept/Reject AI Suggestions
  acceptAiSuggestion: adminExports.acceptPySisAiSuggestion,
  rejectAiSuggestion: adminExports.rejectPySisAiSuggestion,
  // Field History
  getFieldHistory: adminExports.getPySisFieldHistory,
  restoreFromHistory: adminExports.restoreFromPySisHistory,
  // Test
  testConnection: adminExports.testPySisConnection,
  // Available Processes
  getAvailableProcesses: adminExports.getPySisAvailableProcesses,
  // PySis-Facets Integration
  analyzeForFacets: adminExports.analyzeForPySisFacets,
  enrichFacetsFromPysis: adminExports.enrichFacetsFromPySis,
  getPysisFacetsPreview: adminExports.getPysisFacetsPreview,
  getPysisFacetsStatus: adminExports.getPysisFacetsStatus,
  getPysisFacetsSummary: adminExports.getPysisFacetsSummary,
}

// Crawl Presets API
export const crawlPresetsApi = {
  list: adminExports.listCrawlPresets,
  get: adminExports.getCrawlPreset,
  create: adminExports.createCrawlPreset,
  update: adminExports.updateCrawlPreset,
  delete: adminExports.deleteCrawlPreset,
  execute: adminExports.executeCrawlPreset,
  toggleFavorite: adminExports.toggleCrawlPresetFavorite,
  createFromFilters: adminExports.createCrawlPresetFromFilters,
  preview: adminExports.previewCrawlPreset,
  getSchedulePresets: adminExports.getCrawlPresetSchedulePresets,
  previewFilters: adminExports.previewCrawlPresetFilters,
}

// Custom Summaries API
export const customSummariesApi = {
  createFromPrompt: adminExports.createSummaryFromPrompt,
  create: adminExports.createSummary,
  list: adminExports.listSummaries,
  get: adminExports.getSummary,
  update: adminExports.updateSummary,
  delete: adminExports.deleteSummary,
  execute: adminExports.executeSummary,
  listExecutions: adminExports.listSummaryExecutions,
  toggleFavorite: adminExports.toggleSummaryFavorite,
  // Widget Management
  addWidget: adminExports.addSummaryWidget,
  updateWidget: adminExports.updateSummaryWidget,
  deleteWidget: adminExports.deleteSummaryWidget,
  // Share Management
  createShare: adminExports.createSummaryShare,
  listShares: adminExports.listSummaryShares,
  deactivateShare: adminExports.deactivateSummaryShare,
  // Schedule
  getSchedulePresets: adminExports.getSummarySchedulePresets,
  // Export
  exportPdf: adminExports.exportSummaryPdf,
  exportExcel: adminExports.exportSummaryExcel,
  // Check Updates
  checkUpdates: adminExports.checkSummaryUpdates,
  getCheckUpdatesStatus: adminExports.getCheckUpdatesStatus,
}

// Dashboard API
export const dashboardApi = {
  getPreferences: adminExports.getDashboardPreferences,
  updatePreferences: adminExports.updateDashboardPreferences,
  getStats: adminExports.getDashboardStats,
  getActivityFeed: adminExports.getDashboardActivityFeed,
  getInsights: adminExports.getDashboardInsights,
  getChartData: adminExports.getDashboardChartData,
}

// AI API
import * as aiExports from './ai'

// AI Tasks API
export const aiTasksApi = {
  getStatus: aiExports.getAiTaskStatus,
  getResult: aiExports.getAiTaskResult,
  getByEntity: aiExports.getAiTasksByEntity,
}

// Assistant API
export const assistantApi = {
  chat: aiExports.chat,
  chatStream: aiExports.chatStream,
  executeAction: aiExports.executeAction,
  createFacetType: aiExports.createFacetType,
  getCommands: aiExports.getCommands,
  getSuggestions: aiExports.getSuggestions,
  getInsights: aiExports.getInsights,
  uploadAttachment: aiExports.uploadAttachment,
  deleteAttachment: aiExports.deleteAttachment,
  saveToEntityAttachments: aiExports.saveToEntityAttachments,
  batchAction: aiExports.batchAction,
  getBatchStatus: aiExports.getBatchStatus,
  cancelBatch: aiExports.cancelBatch,
  // Wizards
  getWizards: aiExports.getWizards,
  startWizard: aiExports.startWizard,
  wizardRespond: aiExports.wizardRespond,
  wizardBack: aiExports.wizardBack,
  wizardCancel: aiExports.wizardCancel,
  // Reminders
  getReminders: aiExports.getReminders,
  createReminder: aiExports.createReminder,
  deleteReminder: aiExports.deleteReminder,
  dismissReminder: aiExports.dismissReminder,
  snoozeReminder: aiExports.snoozeReminder,
  getDueReminders: aiExports.getDueReminders,
}

// Analysis API
export const analysisApi = {
  // Templates
  getTemplates: aiExports.getAnalysisTemplates,
  getTemplate: aiExports.getAnalysisTemplate,
  getTemplateBySlug: aiExports.getAnalysisTemplateBySlug,
  createTemplate: aiExports.createAnalysisTemplate,
  updateTemplate: aiExports.updateAnalysisTemplate,
  deleteTemplate: aiExports.deleteAnalysisTemplate,
  // Analysis
  getOverview: aiExports.getAnalysisOverview,
  getEntityReport: aiExports.getEntityReport,
  getStats: aiExports.getAnalysisStats,
  // Smart Query
  smartQuery: aiExports.smartQuery,
  smartWrite: aiExports.smartWrite,
  getSmartQueryExamples: aiExports.getSmartQueryExamples,
}

// Smart Query History API
export const smartQueryHistoryApi = {
  getHistory: aiExports.getSmartQueryHistory,
  getOperation: aiExports.getSmartQueryOperation,
  toggleFavorite: aiExports.toggleSmartQueryFavorite,
  execute: aiExports.executeSmartQueryOperation,
  update: aiExports.updateSmartQueryOperation,
  delete: aiExports.deleteSmartQueryOperation,
  clearHistory: aiExports.clearSmartQueryHistory,
}

// Auth API
import * as authExports from './auth'
export const authApi = {
  login: authExports.login,
  logout: authExports.logout,
  getMe: authExports.getMe,
  changePassword: authExports.changePassword,
  checkPasswordStrength: authExports.checkPasswordStrength,
  updateLanguage: authExports.updateLanguage,
  refresh: authExports.refresh,
  listSessions: authExports.listSessions,
  revokeSession: authExports.revokeSession,
  revokeAllSessions: authExports.revokeAllSessions,
}

// Default export - re-export the api instance
export default api
