/**
 * Usage Examples for useLogger Composable
 *
 * This file demonstrates various ways to use the logger in your Vue.js application.
 */

import { useLogger, configureLogger, logger } from './useLogger'

// =============================================================================
// 1. BASIC USAGE
// =============================================================================

function basicUsageExample() {
  // Create a logger for your component or store
  const logger = useLogger('EntityDetailView')

  // Log at different levels
  logger.debug('Component mounted', { timestamp: Date.now() })
  logger.info('Entity loaded successfully', { id: 123 })
  logger.warn('Using deprecated API endpoint', { endpoint: '/old/api' })
  logger.error('Failed to save entity', new Error('Network error'))
}

// =============================================================================
// 2. IN A VUE COMPONENT
// =============================================================================

/*
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useLogger } from '@/composables'

const logger = useLogger('UserProfile')
const user = ref(null)

onMounted(async () => {
  logger.info('Component mounted')

  try {
    logger.debug('Fetching user data...')
    user.value = await fetchUser()
    logger.info('User data loaded', { userId: user.value.id })
  } catch (error) {
    logger.error('Failed to load user', error)
  }
})
</script>
*/

// =============================================================================
// 3. IN A PINIA STORE
// =============================================================================

/*
import { defineStore } from 'pinia'
import { useLogger } from '@/composables'

export const useEntityStore = defineStore('entity', () => {
  const logger = useLogger('EntityStore')
  const entities = ref([])

  async function loadEntities() {
    logger.debug('Loading entities...')

    try {
      const response = await api.getEntities()
      entities.value = response.data
      logger.info('Entities loaded', { count: entities.value.length })
    } catch (error) {
      logger.error('Failed to load entities', error)
      throw error
    }
  }

  return { entities, loadEntities }
})
*/

// =============================================================================
// 4. CHILD LOGGERS FOR NESTED CONTEXTS
// =============================================================================

function childLoggerExample() {
  const storeLogger = useLogger('EntityStore')

  // Create a child logger for a specific operation
  const apiLogger = storeLogger.child('API')
  const cacheLogger = storeLogger.child('Cache')

  apiLogger.debug('Fetching from API')    // Logs: [EntityStore:API] Fetching from API
  cacheLogger.debug('Checking cache')     // Logs: [EntityStore:Cache] Checking cache

  // You can nest even deeper
  const retryLogger = apiLogger.child('Retry')
  retryLogger.warn('Retrying request', { attempt: 2 }) // [EntityStore:API:Retry] Retrying...
}

// =============================================================================
// 5. PERFORMANCE MEASUREMENT
// =============================================================================

async function performanceExample() {
  const logger = useLogger('DataProcessor')

  // Method 1: Manual timing
  const timer = logger.time('processData')
  await processLargeDataset()
  const duration = timer.end({ items: 1000 })
  console.log(`Processing took ${duration}ms`)

  // Method 2: Measure async function
  await logger.measure('fetchAndProcess', async () => {
    const fetchedData = await fetchData()
    return processData(fetchedData)
  }, { source: 'api' })

  // Method 3: Measure sync function
  logger.measureSync('transformData', () => {
    return expensiveTransformation({})
  })
}

// =============================================================================
// 6. GROUPING RELATED LOGS
// =============================================================================

function groupingExample() {
  const logger = useLogger('ApiClient')

  logger.group('POST /api/entities', () => {
    logger.debug('Request URL', { url: '/api/entities' })
    logger.debug('Request Headers', { 'Content-Type': 'application/json' })
    logger.debug('Request Payload', { name: 'New Entity' })
  })

  // In development, this will create a collapsible console group
}

// =============================================================================
// 7. TABLE LOGGING
// =============================================================================

function tableExample() {
  const logger = useLogger('UserList')

  const users = [
    { id: 1, name: 'Alice', role: 'Admin' },
    { id: 2, name: 'Bob', role: 'User' },
    { id: 3, name: 'Charlie', role: 'User' },
  ]

  // Logs a formatted table in the console (development only)
  logger.table('Users', users)
}

// =============================================================================
// 8. ASSERTIONS
// =============================================================================

function assertionExample() {
  const logger: ReturnType<typeof useLogger> = useLogger('DataValidator')

  function validateUser(user: unknown) {
    logger.assert(user !== null, 'User should not be null')
    logger.assert(typeof user === 'object', 'User should be an object')

    const typedUser = user as { id?: number; name?: string }
    logger.assert(typedUser.id !== undefined, 'User should have an ID', { user })
    logger.assert(typedUser.name !== undefined, 'User should have a name', { user })
  }

  try {
    validateUser({ id: 123 }) // Will throw: User should have a name
  } catch (error) {
    console.error('Validation failed:', error)
  }
}

// =============================================================================
// 9. GLOBAL CONFIGURATION (in main.ts)
// =============================================================================

/*
import { configureLogger } from '@/composables'

// Configure logger once at app startup
configureLogger({
  minLevel: import.meta.env.PROD ? 'warn' : 'debug',
  includeTimestamp: true,
  enableErrorTracking: import.meta.env.PROD,
  errorTrackingUrl: '/api/v1/errors/track',
  maxErrorsPerSession: 50,
  includeStackTraces: true,
  globalMetadata: {
    appVersion: '1.0.0',
    environment: import.meta.env.MODE,
  },
})
*/

// =============================================================================
// 10. USING THE DEFAULT LOGGER
// =============================================================================

function defaultLoggerExample() {
  // For quick logging without creating a context
  logger.info('Application started')
  logger.error('Unhandled error', new Error('Something went wrong'))
}

// =============================================================================
// 11. CUSTOM HANDLER (e.g., for testing)
// =============================================================================

export function customHandlerExample() {
  const logs: unknown[] = []

  configureLogger({
    handler: (entry) => {
      logs.push(entry)
      // You could also send to external service, write to file, etc.
    },
  })

  const logger = useLogger('Test')
  logger.info('Test message')

  console.log('Captured logs:', logs)
}

// =============================================================================
// 12. ERROR TRACKING IN PRODUCTION
// =============================================================================

/*
In production, errors are automatically sent to the configured endpoint.

Backend endpoint example (FastAPI):

@app.post("/api/v1/errors/track")
async def track_error(error: ErrorLog):
    # Log to database, send to Sentry, etc.
    logger.error(f"Frontend error: {error.message}", extra={
        "context": error.context,
        "data": error.data,
        "user_agent": error.userAgent,
        "url": error.url,
        "stack_trace": error.stackTrace,
    })
    return {"status": "logged"}
*/

// =============================================================================
// 13. REPLACING EXISTING CONSOLE.* CALLS
// =============================================================================

/*
BEFORE:
  console.log('Loading entities...')
  console.error('Failed to load:', error)

AFTER:
  const logger = useLogger('EntityStore')
  logger.debug('Loading entities...')
  logger.error('Failed to load:', error)

Benefits:
- Consistent formatting
- Context information
- Production error tracking
- Can be filtered by log level
- Better debugging in development
*/

// =============================================================================
// 14. BEST PRACTICES
// =============================================================================

/*
1. Create one logger per component/store with a descriptive context
2. Use appropriate log levels:
   - debug: Detailed debugging info (only in development)
   - info: Important state changes, successful operations
   - warn: Deprecation warnings, potential issues
   - error: Actual errors that need attention

3. Include relevant data with logs
4. Use child loggers for nested operations
5. Measure performance of critical operations
6. Use assertions for invariants in development

7. Log levels by use case:
   - User actions → info
   - API calls → debug (request) / info (success) / error (failure)
   - State changes → info
   - Performance metrics → debug
   - Deprecated features → warn
   - Caught errors → error
*/

// Helper functions for examples (used in examples above)
export async function fetchUser() {
  return { id: 123, name: 'John Doe' }
}

async function processLargeDataset() {
  return new Promise(resolve => setTimeout(resolve, 100))
}

async function fetchData() {
  return [1, 2, 3]
}

function processData(data: number[]) {
  return data.map(x => x * 2)
}

function expensiveTransformation(data: any) {
  return data
}

export {
  basicUsageExample,
  childLoggerExample,
  performanceExample,
  groupingExample,
  tableExample,
  assertionExample,
  defaultLoggerExample,
}
