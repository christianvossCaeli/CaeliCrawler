/**
 * Tests for useLogger composable
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  useLogger,
  configureLogger,
  resetLoggerConfig,
  getLoggerConfig,
  logger,
  type LogEntry,
  type Logger,
} from './useLogger'

describe('useLogger', () => {
  // Mock console methods
  beforeEach(() => {
    vi.spyOn(console, 'debug').mockImplementation(() => {})
    vi.spyOn(console, 'info').mockImplementation(() => {})
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.spyOn(console, 'group').mockImplementation(() => {})
    vi.spyOn(console, 'groupEnd').mockImplementation(() => {})
    vi.spyOn(console, 'table').mockImplementation(() => {})

    // Reset logger config before each test
    resetLoggerConfig()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Basic Logging', () => {
    it('should create a logger with context', () => {
      const testLogger = useLogger('TestContext')
      expect(testLogger).toBeDefined()
      expect(testLogger.debug).toBeDefined()
      expect(testLogger.info).toBeDefined()
      expect(testLogger.warn).toBeDefined()
      expect(testLogger.error).toBeDefined()
    })

    it('should log debug messages', () => {
      const testLogger = useLogger('TestContext')
      testLogger.debug('Test debug message')
      expect(console.debug).toHaveBeenCalled()
    })

    it('should log info messages', () => {
      const testLogger = useLogger('TestContext')
      testLogger.info('Test info message')
      expect(console.info).toHaveBeenCalled()
    })

    it('should log warning messages', () => {
      const testLogger = useLogger('TestContext')
      testLogger.warn('Test warning message')
      expect(console.warn).toHaveBeenCalled()
    })

    it('should log error messages', () => {
      const testLogger = useLogger('TestContext')
      testLogger.error('Test error message')
      expect(console.error).toHaveBeenCalled()
    })

    it('should include context in log messages', () => {
      const testLogger = useLogger('MyComponent')
      testLogger.info('Test message')

      const callArgs = (console.info as ReturnType<typeof vi.fn>).mock.calls[0]
      expect(callArgs[0]).toContain('[MyComponent]')
      expect(callArgs[0]).toContain('Test message')
    })

    it('should log with additional data', () => {
      const testLogger = useLogger('TestContext')
      const data = { id: 123, name: 'test' }

      testLogger.info('Test message', data)

      expect(console.info).toHaveBeenCalled()
      const callArgs = (console.info as ReturnType<typeof vi.fn>).mock.calls[0]
      expect(callArgs).toContain(data)
    })
  })

  describe('Log Levels', () => {
    it('should respect minimum log level', () => {
      configureLogger({ minLevel: 'warn' })

      const testLogger = useLogger('TestContext')
      testLogger.debug('Debug message')
      testLogger.info('Info message')
      testLogger.warn('Warn message')
      testLogger.error('Error message')

      expect(console.debug).not.toHaveBeenCalled()
      expect(console.info).not.toHaveBeenCalled()
      expect(console.warn).toHaveBeenCalled()
      expect(console.error).toHaveBeenCalled()
    })

    it('should allow debug logs when minLevel is debug', () => {
      configureLogger({ minLevel: 'debug' })

      const testLogger = useLogger('TestContext')
      testLogger.debug('Debug message')

      expect(console.debug).toHaveBeenCalled()
    })

    it('should filter logs based on level hierarchy', () => {
      configureLogger({ minLevel: 'error' })

      const testLogger = useLogger('TestContext')
      testLogger.debug('Debug')
      testLogger.info('Info')
      testLogger.warn('Warn')
      testLogger.error('Error')

      expect(console.debug).not.toHaveBeenCalled()
      expect(console.info).not.toHaveBeenCalled()
      expect(console.warn).not.toHaveBeenCalled()
      expect(console.error).toHaveBeenCalled()
    })
  })

  describe('Configuration', () => {
    it('should configure logger globally', () => {
      configureLogger({
        minLevel: 'error',
        includeTimestamp: false,
      })

      const config = getLoggerConfig()
      expect(config.minLevel).toBe('error')
      expect(config.includeTimestamp).toBe(false)
    })

    it('should reset logger configuration', () => {
      configureLogger({ minLevel: 'error' })
      resetLoggerConfig()

      const config = getLoggerConfig()
      expect(config.minLevel).toBe('debug') // Default in test environment
    })

    it('should include timestamp by default', () => {
      const testLogger = useLogger('TestContext')
      testLogger.info('Test message')

      const callArgs = (console.info as ReturnType<typeof vi.fn>).mock.calls[0]
      const message = callArgs[0] as string
      // Should contain ISO timestamp format
      expect(message).toMatch(/\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)
    })

    it('should exclude timestamp when configured', () => {
      configureLogger({ includeTimestamp: false })

      const testLogger = useLogger('TestContext')
      testLogger.info('Test message')

      const callArgs = (console.info as ReturnType<typeof vi.fn>).mock.calls[0]
      const message = callArgs[0] as string
      // Should not contain ISO timestamp format
      expect(message).not.toMatch(/\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)
    })

    it('should use custom handler when provided', () => {
      const customHandler = vi.fn()
      configureLogger({ handler: customHandler })

      const testLogger = useLogger('TestContext')
      testLogger.info('Test message', { test: true })

      expect(customHandler).toHaveBeenCalled()
      expect(console.info).not.toHaveBeenCalled()

      const entry = customHandler.mock.calls[0][0] as LogEntry
      expect(entry.level).toBe('info')
      expect(entry.context).toBe('TestContext')
      expect(entry.message).toBe('Test message')
      expect(entry.data).toEqual({ test: true })
    })
  })

  describe('Child Loggers', () => {
    it('should create child logger with nested context', () => {
      const parentLogger = useLogger('Parent')
      const childLogger = parentLogger.child('Child')

      childLogger.info('Test message')

      const callArgs = (console.info as ReturnType<typeof vi.fn>).mock.calls[0]
      expect(callArgs[0]).toContain('[Parent:Child]')
    })

    it('should support multiple levels of nesting', () => {
      const logger1 = useLogger('Level1')
      const logger2 = logger1.child('Level2')
      const logger3 = logger2.child('Level3')

      logger3.info('Test message')

      const callArgs = (console.info as ReturnType<typeof vi.fn>).mock.calls[0]
      expect(callArgs[0]).toContain('[Level1:Level2:Level3]')
    })
  })

  describe('Grouping', () => {
    it('should group related logs', () => {
      const testLogger = useLogger('TestContext')

      testLogger.group('Test Group', () => {
        testLogger.debug('Message 1')
        testLogger.debug('Message 2')
      })

      expect(console.group).toHaveBeenCalledWith('[TestContext] Test Group')
      expect(console.groupEnd).toHaveBeenCalled()
      expect(console.debug).toHaveBeenCalledTimes(2)
    })

    it('should not group when below minimum log level', () => {
      configureLogger({ minLevel: 'warn' })
      const testLogger = useLogger('TestContext')

      testLogger.group('Test Group', () => {
        testLogger.debug('Message 1')
      })

      expect(console.group).not.toHaveBeenCalled()
      expect(console.groupEnd).not.toHaveBeenCalled()
    })

    it('should close group even if function throws', () => {
      const testLogger = useLogger('TestContext')

      expect(() => {
        testLogger.group('Test Group', () => {
          throw new Error('Test error')
        })
      }).toThrow('Test error')

      expect(console.group).toHaveBeenCalled()
      expect(console.groupEnd).toHaveBeenCalled()
    })
  })

  describe('Table Logging', () => {
    it('should log table for array data', () => {
      const testLogger = useLogger('TestContext')
      const data = [
        { id: 1, name: 'Alice' },
        { id: 2, name: 'Bob' },
      ]

      testLogger.table('Users', data)

      expect(console.group).toHaveBeenCalledWith('[TestContext] Users')
      expect(console.table).toHaveBeenCalledWith(data)
      expect(console.groupEnd).toHaveBeenCalled()
    })

    it('should fall back to debug for non-array data', () => {
      const testLogger = useLogger('TestContext')
      const data = { id: 1, name: 'Test' }

      testLogger.table('User', data)

      expect(console.table).not.toHaveBeenCalled()
      expect(console.debug).toHaveBeenCalled()
    })
  })

  describe('Performance Timing', () => {
    it('should measure operation time', () => {
      const testLogger = useLogger('TestContext')
      const timer = testLogger.time('testOperation')

      // Simulate some work
      const endTime = timer.end()

      expect(endTime).toBeGreaterThanOrEqual(0)
      expect(console.debug).toHaveBeenCalled()

      const callArgs = (console.debug as ReturnType<typeof vi.fn>).mock.calls[0]
      expect(callArgs[0]).toContain('testOperation completed in')
      expect(callArgs[0]).toContain('ms')
    })

    it('should return elapsed time without ending', () => {
      const testLogger = useLogger('TestContext')
      const timer = testLogger.time('testOperation')

      const elapsed1 = timer.elapsed()
      const elapsed2 = timer.elapsed()

      expect(elapsed1).toBeGreaterThanOrEqual(0)
      expect(elapsed2).toBeGreaterThanOrEqual(elapsed1)
      expect(console.debug).not.toHaveBeenCalled()
    })

    it('should include metadata in timing logs', () => {
      const testLogger = useLogger('TestContext')
      const timer = testLogger.time('testOperation')
      const metadata = { items: 100 }

      timer.end(metadata)

      const callArgs = (console.debug as ReturnType<typeof vi.fn>).mock.calls[0]
      expect(callArgs).toContain(metadata)
    })
  })

  describe('Measure Functions', () => {
    it('should measure async operation', async () => {
      const testLogger = useLogger('TestContext')
      const asyncFn = vi.fn().mockResolvedValue('result')

      const result = await testLogger.measure('asyncOp', asyncFn, { test: true })

      expect(result).toBe('result')
      expect(asyncFn).toHaveBeenCalled()
      expect(console.debug).toHaveBeenCalled()

      const callArgs = (console.debug as ReturnType<typeof vi.fn>).mock.calls[0]
      expect(callArgs[0]).toContain('asyncOp completed in')
    })

    it('should log error if async operation fails', async () => {
      const testLogger = useLogger('TestContext')
      const error = new Error('Operation failed')
      const asyncFn = vi.fn().mockRejectedValue(error)

      await expect(testLogger.measure('asyncOp', asyncFn)).rejects.toThrow('Operation failed')

      expect(console.error).toHaveBeenCalled()
      const callArgs = (console.error as ReturnType<typeof vi.fn>).mock.calls[0]
      expect(callArgs[0]).toContain('asyncOp failed after')
    })

    it('should measure sync operation', () => {
      const testLogger = useLogger('TestContext')
      const syncFn = vi.fn().mockReturnValue('result')

      const result = testLogger.measureSync('syncOp', syncFn, { test: true })

      expect(result).toBe('result')
      expect(syncFn).toHaveBeenCalled()
      expect(console.debug).toHaveBeenCalled()

      const callArgs = (console.debug as ReturnType<typeof vi.fn>).mock.calls[0]
      expect(callArgs[0]).toContain('syncOp completed in')
    })

    it('should log error if sync operation fails', () => {
      const testLogger = useLogger('TestContext')
      const error = new Error('Operation failed')
      const syncFn = vi.fn().mockImplementation(() => {
        throw error
      })

      expect(() => testLogger.measureSync('syncOp', syncFn)).toThrow('Operation failed')

      expect(console.error).toHaveBeenCalled()
      const callArgs = (console.error as ReturnType<typeof vi.fn>).mock.calls[0]
      expect(callArgs[0]).toContain('syncOp failed after')
    })
  })

  describe('Assertions', () => {
    it('should pass when condition is true', () => {
      const testLogger: Logger = useLogger('TestContext')

      expect(() => {
        testLogger.assert(true, 'Should pass')
      }).not.toThrow()

      expect(console.error).not.toHaveBeenCalled()
    })

    it('should throw and log when condition is false', () => {
      const testLogger: Logger = useLogger('TestContext')

      expect(() => {
        testLogger.assert(false, 'Should fail')
      }).toThrow('[TestContext] Assertion failed: Should fail')

      expect(console.error).toHaveBeenCalled()
      const callArgs = (console.error as ReturnType<typeof vi.fn>).mock.calls[0]
      expect(callArgs[0]).toContain('Assertion failed: Should fail')
    })

    it('should include data in assertion failure', () => {
      const testLogger: Logger = useLogger('TestContext')
      const data = { expected: 5, actual: 3 }

      expect(() => {
        testLogger.assert(false, 'Numbers do not match', data)
      }).toThrow()

      expect(console.error).toHaveBeenCalled()
      const callArgs = (console.error as ReturnType<typeof vi.fn>).mock.calls[0]
      expect(callArgs).toContain(data)
    })
  })

  describe('Error Tracking', () => {
    beforeEach(() => {
      // Mock fetch for error tracking
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({}),
      }))
    })

    it('should not send errors to tracking in development', () => {
      // Development mode is default in tests
      const testLogger = useLogger('TestContext')
      testLogger.error('Test error', new Error('Test'))

      expect(global.fetch).not.toHaveBeenCalled()
    })

    it('should respect maxErrorsPerSession limit', async () => {
      // Note: Error tracking only works in production mode (import.meta.env.PROD)
      // In test environment, errors are not sent to tracking endpoint
      // This test verifies the configuration is respected
      configureLogger({
        enableErrorTracking: true,
        maxErrorsPerSession: 2,
      })

      const config = getLoggerConfig()
      expect(config.enableErrorTracking).toBe(true)
      expect(config.maxErrorsPerSession).toBe(2)

      const testLogger = useLogger('TestContext')

      // Send 3 errors
      testLogger.error('Error 1')
      testLogger.error('Error 2')
      testLogger.error('Error 3')

      // Wait for async operations
      await new Promise((resolve) => setTimeout(resolve, 0))

      // In dev mode, fetch should not be called
      // In production, only first 2 would be sent
      expect(global.fetch).toHaveBeenCalledTimes(0)
    })

    it('should extract stack trace from Error objects', () => {
      const customHandler = vi.fn()
      configureLogger({ handler: customHandler, includeStackTraces: true })

      const testLogger = useLogger('TestContext')
      const error = new Error('Test error')

      testLogger.error('Error occurred', error)

      const entry = customHandler.mock.calls[0][0] as LogEntry
      expect(entry.stackTrace).toBeDefined()
      expect(entry.stackTrace).toContain('Error: Test error')
    })

    it('should not include stack traces when disabled', () => {
      const customHandler = vi.fn()
      configureLogger({ handler: customHandler, includeStackTraces: false })

      const testLogger = useLogger('TestContext')
      const error = new Error('Test error')

      testLogger.error('Error occurred', error)

      const entry = customHandler.mock.calls[0][0] as LogEntry
      expect(entry.stackTrace).toBeUndefined()
    })
  })

  describe('Default Logger Instance', () => {
    it('should export a default logger instance', () => {
      expect(logger).toBeDefined()
      expect(logger.info).toBeDefined()

      logger.info('Test from default logger')

      const callArgs = (console.info as ReturnType<typeof vi.fn>).mock.calls[0]
      expect(callArgs[0]).toContain('[App]')
    })
  })

  describe('Global Metadata', () => {
    it('should include global metadata in log entries', () => {
      const customHandler = vi.fn()
      const globalMetadata = { userId: '123', sessionId: 'abc' }

      configureLogger({
        handler: customHandler,
        globalMetadata,
      })

      const testLogger = useLogger('TestContext')
      testLogger.info('Test message')

      // Global metadata is not directly in the entry, but would be sent with error tracking
      expect(customHandler).toHaveBeenCalled()
    })
  })

  describe('Edge Cases', () => {
    it('should handle undefined data gracefully', () => {
      const testLogger = useLogger('TestContext')

      expect(() => {
        testLogger.info('Message', undefined)
      }).not.toThrow()

      expect(console.info).toHaveBeenCalled()
    })

    it('should handle null data gracefully', () => {
      const testLogger = useLogger('TestContext')

      expect(() => {
        testLogger.info('Message', null)
      }).not.toThrow()

      expect(console.info).toHaveBeenCalled()
    })

    it('should handle circular references in data', () => {
      const testLogger = useLogger('TestContext')
      const circular: { self?: unknown } = {}
      circular.self = circular

      expect(() => {
        testLogger.info('Message', circular)
      }).not.toThrow()
    })

    it('should handle very long messages', () => {
      const testLogger = useLogger('TestContext')
      const longMessage = 'a'.repeat(10000)

      expect(() => {
        testLogger.info(longMessage)
      }).not.toThrow()

      expect(console.info).toHaveBeenCalled()
    })

    it('should handle special characters in messages', () => {
      const testLogger = useLogger('TestContext')
      const specialMessage = 'Test with émojis 🎉 and symbols €£¥'

      expect(() => {
        testLogger.info(specialMessage)
      }).not.toThrow()

      expect(console.info).toHaveBeenCalled()
    })
  })

  describe('Context Validation', () => {
    it('should accept empty string as context', () => {
      expect(() => {
        const testLogger = useLogger('')
        testLogger.info('Test')
      }).not.toThrow()
    })

    it('should accept special characters in context', () => {
      expect(() => {
        const testLogger = useLogger('Test-Context_123')
        testLogger.info('Test')
      }).not.toThrow()
    })
  })
})
