/**
 * Composables Package - Reusable Vue Composition Functions
 *
 * ## Core Utilities
 * - useErrorHandler: Centralized error handling with i18n support
 * - useAbortController: Request cancellation management
 * - useAsyncOperation: Async state management with loading/error states
 * - useColorHelpers: Color manipulation and contrast utilities
 * - useLogger: Structured logging utility
 *
 * ## Sources Management
 * - useSourcesCrud: CRUD operations for data sources
 * - useSourcesFilters: Filter state for sources list
 * - useSourceHelpers: Source formatting and display utilities
 * - useEntitySearch: Entity search with debouncing for N:M linking
 * - useBulkImport: CSV bulk import functionality
 * - useSharePointConfig: SharePoint connection testing
 *
 * ## Data Views
 * - useFacetHelpers: Facet value formatting and display
 * - useEntitiesFilters: Entity list filtering state
 * - usePySisHelpers: PySis integration utilities
 *
 * ## AI Features
 * - useAssistant: Chat assistant state management
 */

export { useFacetHelpers, attributeTranslations, type FacetValue } from './useFacetHelpers'
export {
  useEntitiesFilters,
  facetFilterOptions,
  locationFieldKeys,
  type BasicFilters,
  type LocationOptions,
  type SchemaAttribute,
} from './useEntitiesFilters'
export { usePySisHelpers } from './usePySisHelpers'
export { useAssistant } from './useAssistant'
export { useColorHelpers, isLightColor, getContrastColor } from './useColorHelpers'
export { useSourcesCrud, type ActionLoadingStates, type UseSourcesCrudOptions } from './useSourcesCrud'
export { useSourcesFilters, type UseSourcesFiltersOptions } from './useSourcesFilters'
export { useSourceHelpers } from './useSourceHelpers'
export { useErrorHandler, type ApiError, type ErrorHandlerOptions, ERROR_MESSAGES } from './useErrorHandler'
export {
  useAbortController,
  useMultiAbortController,
  isAbortError,
  createTimeoutSignal,
  combineSignals,
  type UseAbortControllerReturn,
  type UseMultiAbortControllerReturn,
} from './useAbortController'
export {
  useAsyncOperation,
  useAsyncState,
  useDebouncedOperation,
  type UseAsyncOperationOptions,
  type UseAsyncOperationReturn,
  type UseAsyncStateOptions,
  type UseAsyncStateReturn,
  type UseDebouncedOperationOptions,
  type AsyncOperationFn,
} from './useAsyncOperation'
export {
  useDebounce,
  useThrottle,
  useTimeout,
  useSearchDebounce,
  usePolling,
  DEBOUNCE_DELAYS,
  type UseDebounceOptions,
  type UseDebounceReturn,
  type UseTimeoutReturn,
} from './useDebounce'
export {
  useLogger,
  configureLogger,
  resetLoggerConfig,
  logger,
} from './useLogger'
export {
  useEntitySearch,
  type EntityBrief,
  type UseEntitySearchOptions,
} from './useEntitySearch'
export {
  useBulkImport,
  type UseBulkImportOptions,
} from './useBulkImport'
export {
  useSharePointConfig,
  type SharePointDrive,
  type SharePointTestDetails,
  type SharePointTestResult,
  type UseSharePointConfigOptions,
} from './useSharePointConfig'
