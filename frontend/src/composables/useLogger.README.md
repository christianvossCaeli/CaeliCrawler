# useLogger Composable

A production-ready, structured logging system for Vue.js applications that replaces scattered `console.*` statements with a centralized, configurable logger.

## Features

✨ **Structured Logging** - Consistent log format with context and metadata
🎯 **Log Levels** - Debug, Info, Warn, Error with filtering
🎨 **Development Colors** - Color-coded console output for better visibility
🚀 **Production Error Tracking** - Automatic error reporting to backend
📊 **Performance Tracking** - Built-in timing and measurement utilities
🔍 **Context Aware** - Know exactly where each log originated
🧪 **Test Friendly** - Easy to mock and test with custom handlers
📝 **TypeScript** - Full type safety and IntelliSense support
👶 **Child Loggers** - Nested contexts for complex operations

## Quick Start

```typescript
import { useLogger } from '@/composables'

// Create a logger instance
const logger = useLogger('MyComponent')

// Log at different levels
logger.debug('Detailed debug info', { userId: 123 })
logger.info('Operation successful')
logger.warn('Deprecated API used', { endpoint: '/old' })
logger.error('Operation failed', error)
```

## Installation

The logger is already installed and exported from `@/composables`. No additional setup required!

## Basic Usage

### In Vue Components

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { useLogger } from '@/composables'

const logger = useLogger('UserProfile')

onMounted(() => {
  logger.info('Component mounted')
  loadUserData()
})

async function loadUserData() {
  logger.debug('Loading user data...')
  try {
    const user = await fetchUser()
    logger.info('User loaded', { userId: user.id })
  } catch (error) {
    logger.error('Failed to load user', error)
  }
}
</script>
```

### In Pinia Stores

```typescript
import { defineStore } from 'pinia'
import { useLogger } from '@/composables'

export const useEntityStore = defineStore('entity', () => {
  const logger = useLogger('EntityStore')

  async function loadEntities() {
    logger.debug('Loading entities from API')

    try {
      const data = await api.getEntities()
      logger.info('Entities loaded', { count: data.length })
      return data
    } catch (error) {
      logger.error('Failed to load entities', error)
      throw error
    }
  }

  return { loadEntities }
})
```

## API Reference

### Log Methods

#### `logger.debug(message, data?)`
Log detailed debugging information. Only visible in development by default.

```typescript
logger.debug('Processing item', { itemId: 123, step: 'validation' })
```

#### `logger.info(message, data?)`
Log important state changes and successful operations.

```typescript
logger.info('User logged in', { userId: user.id, timestamp: Date.now() })
```

#### `logger.warn(message, data?)`
Log warnings about potential issues or deprecated features.

```typescript
logger.warn('Using deprecated API endpoint', { endpoint: '/v1/old' })
```

#### `logger.error(message, data?)`
Log errors that need attention. Automatically tracked in production.

```typescript
logger.error('Failed to save data', error)
```

### Advanced Methods

#### `logger.child(context)`
Create a child logger with nested context.

```typescript
const storeLogger = useLogger('EntityStore')
const apiLogger = storeLogger.child('API')

apiLogger.info('Request sent') // Logs: [EntityStore:API] Request sent
```

#### `logger.group(label, callback)`
Group related log messages together.

```typescript
logger.group('API Request Details', () => {
  logger.debug('URL', url)
  logger.debug('Headers', headers)
  logger.debug('Payload', payload)
})
```

#### `logger.table(label, data)`
Display array data as a formatted table (development only).

```typescript
logger.table('Users', [
  { id: 1, name: 'Alice' },
  { id: 2, name: 'Bob' }
])
```

#### `logger.time(operation)` → `PerformanceTimer`
Start a performance timer.

```typescript
const timer = logger.time('loadEntities')
await loadEntities()
const duration = timer.end() // Returns duration in ms
```

#### `logger.measure(operation, fn, metadata?)`
Measure and log async operation performance.

```typescript
const result = await logger.measure('fetchUser', async () => {
  return await api.getUser(userId)
}, { userId })
// Automatically logs: [Context] fetchUser completed in 234ms
```

#### `logger.measureSync(operation, fn, metadata?)`
Measure and log sync operation performance.

```typescript
const result = logger.measureSync('processData', () => {
  return expensiveCalculation(data)
})
```

#### `logger.assert(condition, message, data?)`
Assert a condition and throw if false.

```typescript
logger.assert(user !== null, 'User must be loaded', { userId })
```

## Configuration

### Global Configuration

Configure the logger once in your `main.ts`:

```typescript
import { configureLogger } from '@/composables'

configureLogger({
  // Minimum log level to display
  minLevel: import.meta.env.PROD ? 'warn' : 'debug',

  // Include timestamps in logs
  includeTimestamp: true,

  // Enable error tracking in production
  enableErrorTracking: import.meta.env.PROD,

  // Backend endpoint for error tracking
  errorTrackingUrl: '/api/v1/errors/track',

  // Maximum errors to send per session
  maxErrorsPerSession: 50,

  // Include stack traces in errors
  includeStackTraces: true,

  // Global metadata for all logs
  globalMetadata: {
    appVersion: '1.0.0',
    environment: import.meta.env.MODE,
  },
})
```

### Log Levels

The logger supports four log levels with hierarchical filtering:

| Level | Priority | Use Case | Default Visibility |
|-------|----------|----------|-------------------|
| `debug` | 0 | Detailed debugging | Development only |
| `info` | 1 | Important events | Dev + Production |
| `warn` | 2 | Potential issues | Dev + Production |
| `error` | 3 | Actual errors | Dev + Production |

Set `minLevel` to control what gets logged:
- `debug`: Show everything
- `info`: Hide debug logs
- `warn`: Only warnings and errors
- `error`: Only errors

## Production Error Tracking

In production, all errors logged with `logger.error()` are automatically sent to the configured backend endpoint.

### Backend Endpoint Example (FastAPI)

```python
from fastapi import APIRouter
from pydantic import BaseModel

class ErrorLog(BaseModel):
    level: str
    context: str
    message: str
    data: dict | None
    timestamp: str
    userAgent: str
    url: str
    stackTrace: str | None

router = APIRouter()

@router.post("/api/v1/errors/track")
async def track_frontend_error(error: ErrorLog):
    # Log to database, send to Sentry, etc.
    logger.error(
        f"Frontend error in {error.context}: {error.message}",
        extra={
            "user_agent": error.userAgent,
            "url": error.url,
            "stack_trace": error.stackTrace,
            "data": error.data,
        }
    )
    return {"status": "logged"}
```

### Rate Limiting

The logger automatically limits error tracking to prevent overwhelming your backend:
- Maximum errors per session: 50 (configurable)
- Errors beyond the limit are logged to console only

## Testing

The logger is fully testable with custom handlers:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { useLogger, configureLogger, resetLoggerConfig } from '@/composables'

describe('MyComponent', () => {
  beforeEach(() => {
    resetLoggerConfig() // Reset between tests
  })

  it('should log errors with context', () => {
    const handler = vi.fn()
    configureLogger({ handler })

    const logger = useLogger('MyComponent')
    logger.error('Test error', { id: 123 })

    expect(handler).toHaveBeenCalledWith(
      expect.objectContaining({
        level: 'error',
        context: 'MyComponent',
        message: 'Test error',
        data: { id: 123 },
      })
    )
  })
})
```

## Best Practices

### 1. One Logger Per Context

Create a single logger instance per component/store:

```typescript
// ✅ Good
const logger = useLogger('EntityStore')

// ❌ Bad
function someMethod() {
  const logger = useLogger('EntityStore') // Don't recreate
}
```

### 2. Use Appropriate Log Levels

```typescript
// ✅ Good
logger.debug('Cache hit', { key })           // Debugging details
logger.info('Entity saved', { id })          // Important events
logger.warn('Rate limit approaching', { remaining }) // Warnings
logger.error('Save failed', error)           // Errors

// ❌ Bad
logger.info('x = 5')                         // Use debug for this
logger.error('User clicked button')          // Not an error
```

### 3. Include Structured Data

```typescript
// ✅ Good
logger.error('Failed to load entity', { entityId, error })

// ❌ Bad
logger.error(`Failed to load entity ${entityId}: ${error.message}`)
```

### 4. Use Child Loggers for Nested Contexts

```typescript
// ✅ Good
const apiLogger = logger.child('API')
const cacheLogger = logger.child('Cache')

// ❌ Bad
logger.debug('[API] Making request')
logger.debug('[Cache] Checking cache')
```

### 5. Measure Performance for Critical Operations

```typescript
// ✅ Good
await logger.measure('fetchEntities', async () => {
  return await api.getEntities()
})

// ❌ Bad (manual timing)
const start = Date.now()
await api.getEntities()
console.log(`Took ${Date.now() - start}ms`)
```

## Migration from console.*

Replace all `console.*` calls with logger methods:

| Before | After |
|--------|-------|
| `console.log('Message')` | `logger.info('Message')` or `logger.debug('Message')` |
| `console.debug('Debug')` | `logger.debug('Debug')` |
| `console.info('Info')` | `logger.info('Info')` |
| `console.warn('Warning')` | `logger.warn('Warning')` |
| `console.error('Error', err)` | `logger.error('Error', err)` |

See [LOGGER_MIGRATION.md](../../../LOGGER_MIGRATION.md) for detailed migration guide.

## Examples

See [useLogger.example.ts](./useLogger.example.ts) for comprehensive usage examples.

## Files

- **useLogger.ts** - Main implementation
- **useLogger.test.ts** - Comprehensive test suite (45 tests)
- **useLogger.example.ts** - Usage examples
- **useLogger.README.md** - This file
- **../../LOGGER_MIGRATION.md** - Migration guide

## Performance

The logger is designed to be lightweight and production-safe:

- **Zero overhead** when log level filters out the message
- **Async error tracking** - doesn't block the main thread
- **Minimal memory footprint** - no log history retention
- **Fast formatting** - optimized string concatenation

## Browser Support

The logger uses modern browser APIs:
- `console.*` methods
- `performance.now()` for timing
- `fetch` for error tracking
- `navigator.userAgent`

All features gracefully degrade if APIs are unavailable.

## License

Part of CaeliCrawler frontend application.

## Support

For questions or issues:
1. Check the [migration guide](../../../LOGGER_MIGRATION.md)
2. Review [examples](./useLogger.example.ts)
3. Check [tests](./useLogger.test.ts) for usage patterns
