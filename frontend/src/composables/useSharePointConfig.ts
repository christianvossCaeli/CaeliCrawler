/**
 * SharePoint Config Composable
 *
 * Centralized SharePoint connection testing and configuration.
 * Extracted from stores/sources.ts for better modularity.
 *
 * @module composables/useSharePointConfig
 *
 * ## Features
 * - Connection testing with detailed results
 * - Auto-fill drive name when single drive found
 * - Structured error handling
 *
 * ## Usage
 * ```typescript
 * const {
 *   testResult,
 *   isTesting,
 *   testConnection,
 *   clearResult
 * } = useSharePointConfig()
 * ```
 */

import { ref, computed } from 'vue'
import { adminApi } from '@/services/api'
import { getApiErrorMessage } from '@/types/sources'
import { useLogger } from './useLogger'

/**
 * SharePoint drive information
 */
export interface SharePointDrive {
  id: string
  name: string
  web_url?: string
}

/**
 * SharePoint connection test result details
 */
export interface SharePointTestDetails {
  /** Authentication successful */
  authentication: boolean
  /** Number of sites found */
  sites_found?: number
  /** Target site is accessible */
  target_site_accessible?: boolean
  /** Name of the target site */
  target_site_name?: string
  /** Available drives */
  drives?: SharePointDrive[]
  /** Error messages */
  errors?: string[]
}

/**
 * SharePoint connection test result
 */
export interface SharePointTestResult {
  /** Overall success status */
  success: boolean
  /** Human-readable message */
  message: string
  /** Detailed results */
  details?: SharePointTestDetails
}

/**
 * Options for useSharePointConfig composable
 */
export interface UseSharePointConfigOptions {
  /** Callback when connection test succeeds */
  onSuccess?: (result: SharePointTestResult) => void
  /** Callback when connection test fails */
  onError?: (error: Error) => void
}

/**
 * Composable for SharePoint configuration and testing
 */
export function useSharePointConfig(options: UseSharePointConfigOptions = {}) {
  const { onSuccess, onError } = options

  const logger = useLogger('SharePointConfig')

  // ==========================================================================
  // State
  // ==========================================================================

  const testResult = ref<SharePointTestResult | null>(null)
  const isTesting = ref(false)
  const error = ref<string | null>(null)

  // ==========================================================================
  // Computed
  // ==========================================================================

  /** Whether connection was successful */
  const isConnected = computed(() => testResult.value?.success === true)

  /** Whether authentication succeeded */
  const isAuthenticated = computed(() => testResult.value?.details?.authentication === true)

  /** Available drives from test result */
  const availableDrives = computed(() => testResult.value?.details?.drives || [])

  /** Whether there's only one drive available */
  const hasSingleDrive = computed(() => availableDrives.value.length === 1)

  // ==========================================================================
  // Functions
  // ==========================================================================

  /**
   * Test SharePoint connection
   * @param siteUrl - The SharePoint site URL to test
   * @returns Test result with success status and details
   */
  async function testConnection(siteUrl: string): Promise<SharePointTestResult> {
    if (!siteUrl) {
      throw new Error('Site URL is required')
    }

    isTesting.value = true
    testResult.value = null
    error.value = null

    try {
      const response = await adminApi.testSharePointConnection(siteUrl)
      const data = response.data

      const success =
        data.authentication &&
        (data.target_site_accessible || !siteUrl)

      const result: SharePointTestResult = {
        success,
        message: success ? 'Connection successful' : 'Connection failed',
        details: {
          authentication: data.authentication,
          sites_found: data.sites_found,
          target_site_accessible: data.target_site_accessible,
          target_site_name: data.target_site_name,
          drives: data.drives,
          errors: data.errors,
        },
      }

      testResult.value = result

      if (success) {
        logger.info('SharePoint connection successful', {
          siteName: data.target_site_name,
          drivesFound: data.drives?.length,
        })
        onSuccess?.(result)
      } else {
        logger.warn('SharePoint connection failed', { errors: data.errors })
      }

      return result
    } catch (err) {
      const errorMessage = getApiErrorMessage(err, 'Connection error')

      testResult.value = {
        success: false,
        message: errorMessage,
      }

      error.value = errorMessage
      logger.error('SharePoint connection error', err)

      const connectionError = err instanceof Error ? err : new Error(errorMessage)
      onError?.(connectionError)

      throw connectionError
    } finally {
      isTesting.value = false
    }
  }

  /**
   * Clear test result
   */
  function clearResult(): void {
    testResult.value = null
    error.value = null
  }

  /**
   * Get suggested drive name (first available or single drive)
   */
  function getSuggestedDrive(): string | null {
    if (hasSingleDrive.value) {
      return availableDrives.value[0].name
    }
    return null
  }

  // ==========================================================================
  // Return
  // ==========================================================================

  return {
    // State
    testResult,
    isTesting,
    error,

    // Computed
    isConnected,
    isAuthenticated,
    availableDrives,
    hasSingleDrive,

    // Functions
    testConnection,
    clearResult,
    getSuggestedDrive,
  }
}
