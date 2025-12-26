/**
 * API Service Barrel Export
 *
 * This file re-exports all API modules for convenient importing.
 * Usage: import { adminApi, entityApi } from '@/services/api'
 *
 * Individual modules are located in '@/services/api/*'
 */

// Re-export everything from the new modular structure
export {
  api,
  adminApi,
  dataApi,
  exportApi,
  locationApi,
  municipalityApi,
  entityApi,
  facetApi,
  relationApi,
  analysisApi,
  pysisApi,
  aiTasksApi,
  entityDataApi,
  assistantApi,
  authApi,
  userApi,
  auditApi,
  versionApi,
  notificationApi,
  dashboardApi,
  favoritesApi,
  smartQueryHistoryApi,
  crawlPresetsApi,
  customSummariesApi,
  attachmentApi,
} from './api/index'

// Re-export the default api instance
import { api } from './api/index'
export default api
