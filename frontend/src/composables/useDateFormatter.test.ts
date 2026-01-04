/**
 * Tests for useDateFormatter composable
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useDateFormatter } from './useDateFormatter'

// Mock vue-i18n
vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string, params?: Record<string, unknown>, fallback?: string) => {
      const translations: Record<string, string> = {
        'common.justNow': 'just now',
        'common.minutesAgo': `${params?.count} min ago`,
        'common.hoursAgo': `${params?.count}h ago`,
        'common.daysAgo': `${params?.count}d ago`,
      }
      return translations[key] || fallback || key
    },
    locale: { value: 'en' },
  }),
}))

describe('useDateFormatter', () => {
  const FIXED_TIME = new Date('2025-01-15T12:00:00Z').getTime()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    vi.setSystemTime(FIXED_TIME)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('formatRelativeTime', () => {
    it('should return "just now" for very recent times', () => {
      const { formatRelativeTime } = useDateFormatter()
      const dateStr = new Date(FIXED_TIME - 30000).toISOString() // 30 seconds ago

      const result = formatRelativeTime(dateStr)

      expect(result).toBe('just now')
    })

    it('should return minutes ago for times within the last hour', () => {
      const { formatRelativeTime } = useDateFormatter()
      const dateStr = new Date(FIXED_TIME - 5 * 60000).toISOString() // 5 minutes ago

      const result = formatRelativeTime(dateStr)

      expect(result).toBe('5 min ago')
    })

    it('should return hours ago for times within the last 24 hours', () => {
      const { formatRelativeTime } = useDateFormatter()
      const dateStr = new Date(FIXED_TIME - 3 * 3600000).toISOString() // 3 hours ago

      const result = formatRelativeTime(dateStr)

      expect(result).toBe('3h ago')
    })

    it('should return days ago for times within the last week', () => {
      const { formatRelativeTime } = useDateFormatter()
      const dateStr = new Date(FIXED_TIME - 3 * 86400000).toISOString() // 3 days ago

      const result = formatRelativeTime(dateStr)

      expect(result).toBe('3d ago')
    })

    it('should return localized date for times older than a week', () => {
      const { formatRelativeTime } = useDateFormatter()
      const dateStr = new Date(FIXED_TIME - 8 * 86400000).toISOString() // 8 days ago

      const result = formatRelativeTime(dateStr)

      expect(result).toBeTruthy()
      expect(typeof result).toBe('string')
    })

    it('should handle empty/null input', () => {
      const { formatRelativeTime } = useDateFormatter()

      expect(formatRelativeTime(null)).toBe('')
      expect(formatRelativeTime(undefined)).toBe('')
      expect(formatRelativeTime('')).toBe('')
    })
  })

  describe('formatDateTime', () => {
    it('should format date and time', () => {
      const { formatDateTime } = useDateFormatter()
      const dateStr = '2025-01-15T12:00:00Z'

      const result = formatDateTime(dateStr)

      expect(result).toBeTruthy()
      expect(result).toMatch(/\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}/)
    })

    it('should handle empty input', () => {
      const { formatDateTime } = useDateFormatter()

      expect(formatDateTime(null)).toBe('')
      expect(formatDateTime(undefined)).toBe('')
    })
  })

  describe('formatDateShort', () => {
    it('should format date only', () => {
      const { formatDateShort } = useDateFormatter()
      const dateStr = '2025-01-15T12:00:00Z'

      const result = formatDateShort(dateStr)

      expect(result).toBeTruthy()
      expect(result).toMatch(/\d{2}\.\d{2}\.\d{4}/)
    })
  })

  describe('formatTime', () => {
    it('should format time only', () => {
      const { formatTime } = useDateFormatter()
      const dateStr = '2025-01-15T14:30:00Z'

      const result = formatTime(dateStr)

      expect(result).toBeTruthy()
      expect(result).toMatch(/\d{2}:\d{2}/)
    })
  })

  describe('Edge Cases', () => {
    it('should handle invalid date strings gracefully', () => {
      const { formatRelativeTime } = useDateFormatter()

      expect(() => formatRelativeTime('invalid-date')).not.toThrow()
    })

    it('should handle Date objects', () => {
      const { formatDateTime } = useDateFormatter()
      const date = new Date('2025-01-15T12:00:00Z')

      const result = formatDateTime(date)

      expect(result).toBeTruthy()
    })

    it('should handle very old dates', () => {
      const { formatRelativeTime } = useDateFormatter()
      const dateStr = new Date('1970-01-01T00:00:00Z').toISOString()

      const result = formatRelativeTime(dateStr)

      expect(result).toBeTruthy()
    })
  })
})
