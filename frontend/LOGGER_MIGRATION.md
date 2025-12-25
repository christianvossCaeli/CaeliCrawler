# Logger Migration Guide

This guide helps you replace existing `console.*` statements with the new `useLogger` composable.

## Quick Start

### 1. Import the Logger

```typescript
import { useLogger } from '@/composables'
```

### 2. Create a Logger Instance

```typescript
// At the top of your component or store
const logger = useLogger('YourComponentName')
```

### 3. Replace Console Calls

| Before | After |
|--------|-------|
| `console.log(...)` | `logger.debug(...)` or `logger.info(...)` |
| `console.debug(...)` | `logger.debug(...)` |
| `console.info(...)` | `logger.info(...)` |
| `console.warn(...)` | `logger.warn(...)` |
| `console.error(...)` | `logger.error(...)` |
| `console.group(...)` | `logger.group('label', () => { ... })` |
| `console.table(...)` | `logger.table('label', data)` |

## Migration Examples

### Example 1: Vue Component

**Before:**
```typescript
<script setup lang="ts">
import { onMounted, ref } from 'vue'

const entities = ref([])

onMounted(async () => {
  console.log('Component mounted')

  try {
    console.debug('Fetching entities...')
    const response = await api.getEntities()
    entities.value = response.data
    console.log('Loaded entities:', entities.value.length)
  } catch (error) {
    console.error('Failed to load entities:', error)
  }
})
</script>
```

**After:**
```typescript
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useLogger } from '@/composables'

const logger = useLogger('EntityListView')
const entities = ref([])

onMounted(async () => {
  logger.info('Component mounted')

  try {
    logger.debug('Fetching entities...')
    const response = await api.getEntities()
    entities.value = response.data
    logger.info('Loaded entities', { count: entities.value.length })
  } catch (error) {
    logger.error('Failed to load entities', error)
  }
})
</script>
```

### Example 2: Pinia Store

**Before:**
```typescript
import { defineStore } from 'pinia'

export const useEntityStore = defineStore('entity', () => {
  const entities = ref([])

  async function loadEntities() {
    console.log('Loading entities...')
    try {
      const response = await api.getEntities()
      entities.value = response.data
      console.log(`Loaded ${entities.value.length} entities`)
    } catch (error) {
      console.error('Error loading entities:', error)
      throw error
    }
  }

  return { entities, loadEntities }
})
```

**After:**
```typescript
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
      logger.info('Loaded entities', { count: entities.value.length })
    } catch (error) {
      logger.error('Error loading entities', error)
      throw error
    }
  }

  return { entities, loadEntities }
})
```

### Example 3: Service/API Client

**Before:**
```typescript
export async function fetchUser(id: number) {
  console.debug(`Fetching user ${id}`)

  try {
    const response = await axios.get(`/api/users/${id}`)
    console.log('User fetched:', response.data)
    return response.data
  } catch (error) {
    console.error('Failed to fetch user:', error)
    throw error
  }
}
```

**After:**
```typescript
import { useLogger } from '@/composables'

const logger = useLogger('UserService')

export async function fetchUser(id: number) {
  logger.debug('Fetching user', { id })

  try {
    const response = await axios.get(`/api/users/${id}`)
    logger.info('User fetched', { userId: response.data.id })
    return response.data
  } catch (error) {
    logger.error('Failed to fetch user', { id, error })
    throw error
  }
}
```

## Log Level Guidelines

### When to use each level:

- **`debug`**: Detailed information for debugging
  - Function entry/exit
  - Variable values
  - API request details
  - Cache hits/misses
  - Only visible in development by default

- **`info`**: Important state changes and events
  - Component mounted/unmounted
  - Successful operations
  - User actions
  - Data loaded successfully
  - Visible in both dev and production (configurable)

- **`warn`**: Potential issues or deprecated features
  - Deprecated API usage
  - Fallback values used
  - Performance warnings
  - Non-critical errors

- **`error`**: Actual errors that need attention
  - API failures
  - Validation errors
  - Uncaught exceptions
  - Critical issues
  - Automatically tracked in production

## Structured Data

Always include relevant context data as the second parameter:

**Before:**
```typescript
console.log(`Loading entity ${id}`)
console.error(`Failed to save entity ${id}:`, error)
```

**After:**
```typescript
logger.debug('Loading entity', { id })
logger.error('Failed to save entity', { id, error })
```

## Context Naming Conventions

Use clear, consistent context names:

- Vue Components: Component name (e.g., `'EntityDetailView'`, `'UserProfile'`)
- Pinia Stores: Store name (e.g., `'EntityStore'`, `'AuthStore'`)
- Services: Service name (e.g., `'ApiClient'`, `'UserService'`)
- Utilities: Module name (e.g., `'DateUtils'`, `'Validators'`)

## Advanced Features

### Child Loggers

For nested operations within the same context:

```typescript
const storeLogger = useLogger('EntityStore')
const apiLogger = storeLogger.child('API')
const cacheLogger = storeLogger.child('Cache')

apiLogger.debug('Fetching from API')     // [EntityStore:API] Fetching from API
cacheLogger.debug('Checking cache')      // [EntityStore:Cache] Checking cache
```

### Performance Measurement

Replace manual timing:

**Before:**
```typescript
const start = performance.now()
await loadData()
console.log(`Loading took ${performance.now() - start}ms`)
```

**After:**
```typescript
await logger.measure('loadData', async () => {
  return await loadData()
})
// Automatically logs: [Context] loadData completed in 234.56ms
```

### Grouping Related Logs

**Before:**
```typescript
console.group('API Request')
console.log('URL:', url)
console.log('Headers:', headers)
console.log('Body:', body)
console.groupEnd()
```

**After:**
```typescript
logger.group('API Request', () => {
  logger.debug('URL', { url })
  logger.debug('Headers', { headers })
  logger.debug('Body', { body })
})
```

## Configuration

### Global Configuration (in `main.ts`)

```typescript
import { configureLogger } from '@/composables'

configureLogger({
  minLevel: import.meta.env.PROD ? 'warn' : 'debug',
  includeTimestamp: true,
  enableErrorTracking: import.meta.env.PROD,
  errorTrackingUrl: '/api/v1/errors/track',
  maxErrorsPerSession: 50,
  globalMetadata: {
    appVersion: import.meta.env.VITE_APP_VERSION,
    environment: import.meta.env.MODE,
  },
})
```

## Finding Console Calls to Replace

Use these commands to find console statements in your codebase:

```bash
# Find all console.log calls
grep -r "console\.log" src/

# Find all console.* calls
grep -r "console\." src/ --include="*.ts" --include="*.vue"

# Count console calls by type
grep -roh "console\.[a-z]*" src/ --include="*.ts" --include="*.vue" | sort | uniq -c
```

## Testing

The logger is fully testable with custom handlers:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { useLogger, configureLogger } from '@/composables'

describe('MyComponent', () => {
  it('should log errors', () => {
    const handler = vi.fn()
    configureLogger({ handler })

    const logger = useLogger('MyComponent')
    logger.error('Test error')

    expect(handler).toHaveBeenCalledWith(
      expect.objectContaining({
        level: 'error',
        context: 'MyComponent',
        message: 'Test error',
      })
    )
  })
})
```

## Benefits

✅ **Consistent formatting** - All logs follow the same pattern
✅ **Context awareness** - Know exactly where each log came from
✅ **Production error tracking** - Errors automatically sent to backend
✅ **Filterable** - Control log levels per environment
✅ **Performance tracking** - Built-in timing utilities
✅ **TypeScript support** - Full type safety
✅ **Testing friendly** - Easy to mock and test
✅ **Better debugging** - Colored output in development

## Checklist

- [ ] Import `useLogger` from `@/composables`
- [ ] Create logger instance with descriptive context
- [ ] Replace all `console.log` with appropriate log level
- [ ] Include structured data as second parameter
- [ ] Use child loggers for nested contexts (if applicable)
- [ ] Remove any remaining direct `console.*` calls
- [ ] Test in both development and production modes
- [ ] Configure error tracking endpoint (if needed)

## Need Help?

- See `useLogger.example.ts` for more examples
- See `useLogger.test.ts` for testing patterns
- Check the inline documentation in `useLogger.ts`
