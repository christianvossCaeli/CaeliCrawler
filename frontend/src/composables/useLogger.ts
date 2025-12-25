/**
 * Logger Composable
 *
 * Structured logging utility for consistent error handling and debugging.
 * Replaces scattered console.* calls with a centralized, configurable logger.
 *
 * @module composables/useLogger
 *
 * ## Features
 * - Structured log messages with context
 * - Log levels (debug, info, warn, error)
 * - Production-safe (can disable debug/info in production)
 * - Production error tracking endpoint integration
 * - Consistent format across the application
 * - TypeScript strict mode compatible
 * - Performance tracking
 * - Child logger support
 *
 * ## Usage
 * ```typescript
 * const logger = useLogger('EntityDetailView')
 * logger.debug('Loading entity', { id: entityId })
 * logger.info('Entity loaded successfully')
 * logger.warn('Deprecated API used', { endpoint: '/old/api' })
 * logger.error('Failed to save entity', error)
 * ```
 *
 * ## Configuration
 * ```typescript
 * // Configure globally (e.g., in main.ts)
 * configureLogger({
 *   minLevel: 'info',
 *   includeTimestamp: true,
 *   errorTrackingUrl: '/api/v1/errors/track',
 *   enableErrorTracking: true,
 * })
 * ```
 */

export type LogLevel = 'debug' | 'info' | 'warn' | 'error'

export interface LogEntry {
  level: LogLevel
  context: string
  message: string
  data?: unknown
  timestamp: Date
  userAgent?: string
  url?: string
  stackTrace?: string
}

export interface PerformanceLogEntry {
  context: string
  operation: string
  duration: number
  timestamp: Date
  metadata?: Record<string, unknown>
}

/**
 * Logger configuration
 */
export interface LoggerConfig {
  /** Minimum log level to output (default: 'info' in production, 'debug' in development) */
  minLevel: LogLevel
  /** Whether to include timestamps (default: true) */
  includeTimestamp: boolean
  /** Custom log handler (for testing or external logging services) */
  handler?: (entry: LogEntry) => void
  /** Enable production error tracking */
  enableErrorTracking: boolean
  /** Error tracking endpoint URL */
  errorTrackingUrl: string
  /** Maximum number of errors to track per session */
  maxErrorsPerSession: number
  /** Include stack traces in error logs */
  includeStackTraces: boolean
  /** Custom metadata to include in all logs */
  globalMetadata?: Record<string, unknown>
}

const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
}

// Log level colors for console output
const LOG_COLORS: Record<LogLevel, string> = {
  debug: '#9E9E9E', // Gray
  info: '#2196F3',  // Blue
  warn: '#FF9800',  // Orange
  error: '#F44336', // Red
}

// Track errors sent in this session
let errorsSentThisSession = 0

// Default configuration
const defaultConfig: LoggerConfig = {
  minLevel: import.meta.env.PROD ? 'warn' : 'debug',
  includeTimestamp: true,
  enableErrorTracking: import.meta.env.PROD,
  errorTrackingUrl: '/api/v1/errors/track',
  maxErrorsPerSession: 50,
  includeStackTraces: true,
}

let globalConfig: LoggerConfig = { ...defaultConfig }

/**
 * Configure the global logger settings
 */
export function configureLogger(config: Partial<LoggerConfig>): void {
  globalConfig = { ...globalConfig, ...config }
}

/**
 * Reset logger to default configuration
 */
export function resetLoggerConfig(): void {
  globalConfig = { ...defaultConfig }
  errorsSentThisSession = 0
}

/**
 * Get current logger configuration (for testing)
 */
export function getLoggerConfig(): LoggerConfig {
  return { ...globalConfig }
}

/**
 * Format log message with context
 */
function formatMessage(context: string, message: string, includeTimestamp: boolean): string {
  const timestamp = includeTimestamp ? `[${new Date().toISOString()}] ` : ''
  return `${timestamp}[${context}] ${message}`
}

/**
 * Extract stack trace from error
 */
function extractStackTrace(error: unknown): string | undefined {
  if (!globalConfig.includeStackTraces) return undefined

  if (error instanceof Error && error.stack) {
    return error.stack
  }

  if (typeof error === 'object' && error !== null && 'stack' in error) {
    return String((error as { stack: unknown }).stack)
  }

  return undefined
}

/**
 * Send error to tracking endpoint
 */
async function sendErrorToTracking(entry: LogEntry): Promise<void> {
  // Check if error tracking is enabled
  if (!globalConfig.enableErrorTracking) return

  // Check if we've exceeded the maximum errors per session
  if (errorsSentThisSession >= globalConfig.maxErrorsPerSession) {
    console.warn('[Logger] Maximum errors per session reached. Skipping error tracking.')
    return
  }

  try {
    const payload = {
      level: entry.level,
      context: entry.context,
      message: entry.message,
      data: entry.data,
      timestamp: entry.timestamp.toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      stackTrace: entry.stackTrace,
      metadata: globalConfig.globalMetadata,
    }

    // Use fetch instead of axios to avoid circular dependencies
    await fetch(globalConfig.errorTrackingUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })

    errorsSentThisSession++
  } catch (trackingError) {
    // Silently fail - we don't want error tracking to break the app
    console.warn('[Logger] Failed to send error to tracking endpoint:', trackingError)
  }
}

/**
 * Format console output with colors (development mode)
 */
function logToConsole(
  level: LogLevel,
  formattedMessage: string,
  data?: unknown,
  stackTrace?: string
): void {
  const color = LOG_COLORS[level]
  const styles = `color: ${color}; font-weight: bold;`

  const consoleMethod = console[level] || console.log

  if (import.meta.env.DEV) {
    // Enhanced formatting in development
    if (data !== undefined && stackTrace) {
      consoleMethod(`%c${formattedMessage}`, styles, '\nData:', data, '\nStack:', stackTrace)
    } else if (data !== undefined) {
      consoleMethod(`%c${formattedMessage}`, styles, '\nData:', data)
    } else if (stackTrace) {
      consoleMethod(`%c${formattedMessage}`, styles, '\nStack:', stackTrace)
    } else {
      consoleMethod(`%c${formattedMessage}`, styles)
    }
  } else {
    // Simple formatting in production
    if (data !== undefined) {
      consoleMethod(formattedMessage, data)
    } else {
      consoleMethod(formattedMessage)
    }
  }
}

/**
 * Performance timer for tracking operation duration
 */
export interface PerformanceTimer {
  /** Stop the timer and log the duration */
  end: (metadata?: Record<string, unknown>) => number
  /** Get elapsed time without stopping */
  elapsed: () => number
}

/**
 * Logger instance type
 */
export type Logger = ReturnType<typeof useLogger>

/**
 * Create a logger instance for a specific context
 */
export function useLogger(context: string) {
  function shouldLog(level: LogLevel): boolean {
    return LOG_LEVELS[level] >= LOG_LEVELS[globalConfig.minLevel]
  }

  function log(level: LogLevel, message: string, data?: unknown): void {
    if (!shouldLog(level)) return

    const stackTrace = level === 'error' && data ? extractStackTrace(data) : undefined

    const entry: LogEntry = {
      level,
      context,
      message,
      data,
      timestamp: new Date(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      stackTrace,
    }

    // Use custom handler if provided
    if (globalConfig.handler) {
      globalConfig.handler(entry)
      return
    }

    const formattedMessage = formatMessage(context, message, globalConfig.includeTimestamp)

    // Log to console
    logToConsole(level, formattedMessage, data, stackTrace)

    // Send errors to tracking endpoint in production
    if (level === 'error' && import.meta.env.PROD) {
      // Don't await - fire and forget
      void sendErrorToTracking(entry)
    }
  }

  return {
    /**
     * Log debug message (only in development by default)
     */
    debug(message: string, data?: unknown): void {
      log('debug', message, data)
    },

    /**
     * Log info message
     */
    info(message: string, data?: unknown): void {
      log('info', message, data)
    },

    /**
     * Log warning message
     */
    warn(message: string, data?: unknown): void {
      log('warn', message, data)
    },

    /**
     * Log error message
     */
    error(message: string, data?: unknown): void {
      log('error', message, data)
    },

    /**
     * Create a child logger with additional context
     *
     * @example
     * const logger = useLogger('UserStore')
     * const childLogger = logger.child('fetchUser')
     * childLogger.info('Fetching user data') // Logs: [UserStore:fetchUser] Fetching user data
     */
    child(childContext: string) {
      return useLogger(`${context}:${childContext}`)
    },

    /**
     * Log a group of related messages
     *
     * @example
     * logger.group('API Request', () => {
     *   logger.debug('URL', url)
     *   logger.debug('Headers', headers)
     *   logger.debug('Payload', payload)
     * })
     */
    group(label: string, fn: () => void): void {
      if (!shouldLog('debug')) return

      if (import.meta.env.DEV) {
        console.group(`[${context}] ${label}`)
        try {
          fn()
        } finally {
          console.groupEnd()
        }
      } else {
        // In production, just execute without grouping
        fn()
      }
    },

    /**
     * Log a table (useful for arrays of objects)
     *
     * @example
     * logger.table('Users', users)
     */
    table(label: string, data: unknown): void {
      if (!shouldLog('debug')) return

      if (import.meta.env.DEV && Array.isArray(data)) {
        console.group(`[${context}] ${label}`)
        console.table(data)
        console.groupEnd()
      } else {
        this.debug(label, data)
      }
    },

    /**
     * Start a performance timer
     *
     * @example
     * const timer = logger.time('loadEntities')
     * await loadEntities()
     * const duration = timer.end() // Logs: [EntityStore] loadEntities completed in 234ms
     */
    time(operation: string): PerformanceTimer {
      const startTime = performance.now()

      return {
        end: (metadata?: Record<string, unknown>): number => {
          const duration = performance.now() - startTime

          if (shouldLog('debug')) {
            const message = `${operation} completed in ${duration.toFixed(2)}ms`
            log('debug', message, metadata)
          }

          return duration
        },
        elapsed: (): number => {
          return performance.now() - startTime
        },
      }
    },

    /**
     * Measure and log async operation performance
     *
     * @example
     * await logger.measure('loadEntities', async () => {
     *   return await api.getEntities()
     * })
     */
    async measure<T>(
      operation: string,
      fn: () => Promise<T>,
      metadata?: Record<string, unknown>
    ): Promise<T> {
      const timer = this.time(operation)
      try {
        const result = await fn()
        timer.end(metadata)
        return result
      } catch (error) {
        const duration = timer.elapsed()
        this.error(`${operation} failed after ${duration.toFixed(2)}ms`, { error, metadata })
        throw error
      }
    },

    /**
     * Measure and log sync operation performance
     *
     * @example
     * const result = logger.measureSync('processData', () => {
     *   return processComplexData(data)
     * })
     */
    measureSync<T>(
      operation: string,
      fn: () => T,
      metadata?: Record<string, unknown>
    ): T {
      const timer = this.time(operation)
      try {
        const result = fn()
        timer.end(metadata)
        return result
      } catch (error) {
        const duration = timer.elapsed()
        this.error(`${operation} failed after ${duration.toFixed(2)}ms`, { error, metadata })
        throw error
      }
    },

    /**
     * Assert a condition and log error if false
     *
     * @example
     * logger.assert(user !== null, 'User should be loaded')
     */
    assert(condition: boolean, message: string, data?: unknown): asserts condition {
      if (!condition) {
        this.error(`Assertion failed: ${message}`, data)
        throw new Error(`[${context}] Assertion failed: ${message}`)
      }
    },
  }
}

/**
 * Default logger instance for quick usage
 */
export const logger = useLogger('App')
