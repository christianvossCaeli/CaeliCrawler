/**
 * Logger Composable
 *
 * Structured logging utility for consistent error handling and debugging.
 * Replaces scattered console.error() calls with a centralized, configurable logger.
 *
 * @module composables/useLogger
 *
 * ## Features
 * - Structured log messages with context
 * - Log levels (debug, info, warn, error)
 * - Production-safe (can disable debug/info in production)
 * - Consistent format across the application
 *
 * ## Usage
 * ```typescript
 * const logger = useLogger('SourcesStore')
 * logger.info('Sources loaded', { count: 10 })
 * logger.error('Failed to load sources', error)
 * ```
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

interface LogEntry {
  level: LogLevel
  context: string
  message: string
  data?: unknown
  timestamp: Date
}

/**
 * Logger configuration
 */
interface LoggerConfig {
  /** Minimum log level to output (default: 'info' in production, 'debug' in development) */
  minLevel: LogLevel
  /** Whether to include timestamps (default: true) */
  includeTimestamp: boolean
  /** Custom log handler (for testing or external logging services) */
  handler?: (entry: LogEntry) => void
}

const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
}

// Default configuration
const defaultConfig: LoggerConfig = {
  minLevel: import.meta.env.PROD ? 'warn' : 'debug',
  includeTimestamp: true,
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
}

/**
 * Format log message with context
 */
function formatMessage(context: string, message: string, includeTimestamp: boolean): string {
  const timestamp = includeTimestamp ? `[${new Date().toISOString()}] ` : ''
  return `${timestamp}[${context}] ${message}`
}

/**
 * Create a logger instance for a specific context
 */
export function useLogger(context: string) {
  function shouldLog(level: LogLevel): boolean {
    return LOG_LEVELS[level] >= LOG_LEVELS[globalConfig.minLevel]
  }

  function log(level: LogLevel, message: string, data?: unknown): void {
    if (!shouldLog(level)) return

    const entry: LogEntry = {
      level,
      context,
      message,
      data,
      timestamp: new Date(),
    }

    // Use custom handler if provided
    if (globalConfig.handler) {
      globalConfig.handler(entry)
      return
    }

    const formattedMessage = formatMessage(context, message, globalConfig.includeTimestamp)

    switch (level) {
      case 'debug':
        if (data !== undefined) {
          console.debug(formattedMessage, data)
        } else {
          console.debug(formattedMessage)
        }
        break
      case 'info':
        if (data !== undefined) {
          console.info(formattedMessage, data)
        } else {
          console.info(formattedMessage)
        }
        break
      case 'warn':
        if (data !== undefined) {
          console.warn(formattedMessage, data)
        } else {
          console.warn(formattedMessage)
        }
        break
      case 'error':
        if (data !== undefined) {
          console.error(formattedMessage, data)
        } else {
          console.error(formattedMessage)
        }
        break
    }
  }

  return {
    /**
     * Log debug message (only in development)
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
     */
    child(childContext: string) {
      return useLogger(`${context}:${childContext}`)
    },
  }
}

/**
 * Default logger instance for quick usage
 */
export const logger = useLogger('App')
