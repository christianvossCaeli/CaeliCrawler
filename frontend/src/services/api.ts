/**
 * @deprecated This file is now a re-export wrapper for backward compatibility.
 * Import from '@/services/api' to use the modular API structure.
 * Individual modules are located in '@/services/api/*'
 */

// Re-export everything from the new modular structure
export {
  api,
  adminApi,
  externalApiApi,
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
