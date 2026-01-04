import { describe, it, expect, beforeEach } from 'vitest'
import { useSourceHelpers } from './useSourceHelpers'

describe('useSourceHelpers', () => {
  let helpers: ReturnType<typeof useSourceHelpers>

  beforeEach(() => {
    helpers = useSourceHelpers()
  })

  // ==========================================================================
  // Type Helpers
  // ==========================================================================

  describe('getTypeColor', () => {
    it('returns correct color for known types', () => {
      expect(helpers.getTypeColor('WEBSITE')).toBe('primary')
      expect(helpers.getTypeColor('OPARL_API')).toBe('success')
      expect(helpers.getTypeColor('RSS')).toBe('info')
      expect(helpers.getTypeColor('CUSTOM_API')).toBe('warning')
      expect(helpers.getTypeColor('SHAREPOINT')).toBe('teal')
    })

    it('returns grey for unknown types', () => {
      expect(helpers.getTypeColor('UNKNOWN_TYPE')).toBe('grey')
    })

    it('returns grey for null', () => {
      expect(helpers.getTypeColor(null)).toBe('grey')
    })
  })

  describe('getTypeIcon', () => {
    it('returns correct icon for known types', () => {
      expect(helpers.getTypeIcon('WEBSITE')).toBe('mdi-web')
      expect(helpers.getTypeIcon('OPARL_API')).toBe('mdi-api')
      expect(helpers.getTypeIcon('RSS')).toBe('mdi-rss')
      expect(helpers.getTypeIcon('SHAREPOINT')).toBe('mdi-microsoft-sharepoint')
    })

    it('returns help icon for unknown types', () => {
      expect(helpers.getTypeIcon('UNKNOWN_TYPE')).toBe('mdi-help-circle')
    })

    it('returns help icon for null', () => {
      expect(helpers.getTypeIcon(null)).toBe('mdi-help-circle')
    })
  })

  describe('getTypeLabel', () => {
    it('returns empty string for null', () => {
      expect(helpers.getTypeLabel(null)).toBe('')
    })

    it('returns fallback label for known types', () => {
      // The mock returns the key, so fallback is used
      expect(helpers.getTypeLabel('WEBSITE')).toBe('Website')
      expect(helpers.getTypeLabel('OPARL_API')).toBe('OParl API')
      expect(helpers.getTypeLabel('RSS')).toBe('RSS Feed')
    })

    it('returns type itself for unknown types', () => {
      expect(helpers.getTypeLabel('UNKNOWN_TYPE')).toBe('UNKNOWN_TYPE')
    })
  })

  // ==========================================================================
  // Status Helpers
  // ==========================================================================

  describe('getStatusColor', () => {
    it('returns correct color for known statuses', () => {
      expect(helpers.getStatusColor('ACTIVE')).toBe('success')
      expect(helpers.getStatusColor('PENDING')).toBe('warning')
      expect(helpers.getStatusColor('ERROR')).toBe('error')
      expect(helpers.getStatusColor('PAUSED')).toBe('warning') // PAUSED requires attention
    })

    it('returns grey for unknown statuses', () => {
      expect(helpers.getStatusColor('UNKNOWN')).toBe('grey')
    })

    it('returns grey for null', () => {
      expect(helpers.getStatusColor(null)).toBe('grey')
    })
  })

  describe('getStatusIcon', () => {
    it('returns correct icon for known statuses', () => {
      expect(helpers.getStatusIcon('ACTIVE')).toBe('mdi-check-circle')
      expect(helpers.getStatusIcon('PENDING')).toBe('mdi-clock-outline')
      expect(helpers.getStatusIcon('ERROR')).toBe('mdi-alert-circle')
      expect(helpers.getStatusIcon('PAUSED')).toBe('mdi-pause-circle')
    })

    it('returns help icon for unknown statuses', () => {
      expect(helpers.getStatusIcon('UNKNOWN')).toBe('mdi-help-circle')
    })

    it('returns help icon for null', () => {
      expect(helpers.getStatusIcon(null)).toBe('mdi-help-circle')
    })
  })

  describe('getStatusLabel', () => {
    it('returns empty string for null', () => {
      expect(helpers.getStatusLabel(null)).toBe('')
    })

    it('returns status as fallback when translation not found', () => {
      // Mock returns the key, so fallback to status value is used
      expect(helpers.getStatusLabel('ACTIVE')).toBe('ACTIVE')
      expect(helpers.getStatusLabel('ERROR')).toBe('ERROR')
    })
  })

  // ==========================================================================
  // Tag Helpers
  // ==========================================================================

  describe('getTagColor', () => {
    it('returns blue for geographic regions', () => {
      expect(helpers.getTagColor('nrw')).toBe('blue')
      expect(helpers.getTagColor('bayern')).toBe('blue')
      expect(helpers.getTagColor('NRW')).toBe('blue') // case insensitive
    })

    it('returns indigo for country tags', () => {
      expect(helpers.getTagColor('deutschland')).toBe('indigo')
      expect(helpers.getTagColor('de')).toBe('indigo')
      expect(helpers.getTagColor('DEUTSCHLAND')).toBe('indigo') // case insensitive
    })

    it('returns green for administrative tags', () => {
      expect(helpers.getTagColor('kommunal')).toBe('green')
      expect(helpers.getTagColor('stadt')).toBe('green')
      expect(helpers.getTagColor('KOMMUNAL')).toBe('green') // case insensitive
    })

    it('returns grey for custom tags', () => {
      expect(helpers.getTagColor('custom-tag')).toBe('grey')
      expect(helpers.getTagColor('something')).toBe('grey')
    })

    it('handles empty or undefined tags', () => {
      expect(helpers.getTagColor('')).toBe('grey')
    })
  })

  describe('getTagIcon', () => {
    it('returns map-marker for geographic regions', () => {
      expect(helpers.getTagIcon('nrw')).toBe('mdi-map-marker')
    })

    it('returns flag for country tags', () => {
      expect(helpers.getTagIcon('deutschland')).toBe('mdi-flag')
    })

    it('returns office-building for administrative tags', () => {
      expect(helpers.getTagIcon('kommunal')).toBe('mdi-office-building')
    })

    it('returns tag icon for custom tags', () => {
      expect(helpers.getTagIcon('custom-tag')).toBe('mdi-tag')
    })
  })

  // ==========================================================================
  // Language Helpers
  // ==========================================================================

  describe('getLanguageFlag', () => {
    it('returns correct flag for known languages', () => {
      expect(helpers.getLanguageFlag('de')).toBe('🇩🇪')
      expect(helpers.getLanguageFlag('en')).toBe('🇬🇧')
      expect(helpers.getLanguageFlag('fr')).toBe('🇫🇷')
    })

    it('returns uppercase code for unknown languages', () => {
      expect(helpers.getLanguageFlag('xx')).toBe('XX')
    })
  })

  describe('getLanguageName', () => {
    it('returns correct name for known languages', () => {
      expect(helpers.getLanguageName('de')).toBe('Deutsch')
      expect(helpers.getLanguageName('en')).toBe('English')
      expect(helpers.getLanguageName('fr')).toBe('Français')
    })

    it('returns uppercase code for unknown languages', () => {
      expect(helpers.getLanguageName('xx')).toBe('XX')
    })
  })

  // ==========================================================================
  // URL Helpers
  // ==========================================================================

  describe('isValidUrl', () => {
    it('returns true for valid HTTP URLs', () => {
      expect(helpers.isValidUrl('http://example.com')).toBe(true)
      expect(helpers.isValidUrl('https://example.com/path')).toBe(true)
      expect(helpers.isValidUrl('https://sub.example.com:8080/path?query=1')).toBe(true)
    })

    it('returns false for invalid URLs', () => {
      expect(helpers.isValidUrl('not-a-url')).toBe(false)
      expect(helpers.isValidUrl('ftp://example.com')).toBe(false)
      expect(helpers.isValidUrl('')).toBe(false)
    })
  })

  describe('getHostname', () => {
    it('extracts hostname from valid URLs', () => {
      expect(helpers.getHostname('https://example.com/path')).toBe('example.com')
      expect(helpers.getHostname('http://sub.example.com:8080')).toBe('sub.example.com')
    })

    it('returns original string for invalid URLs', () => {
      expect(helpers.getHostname('not-a-url')).toBe('not-a-url')
    })
  })

  describe('truncateUrl', () => {
    it('does not truncate short URLs', () => {
      expect(helpers.truncateUrl('https://a.com', 50)).toBe('https://a.com')
    })

    it('truncates long URLs', () => {
      const longUrl = 'https://example.com/very/long/path/that/exceeds/maximum/length'
      const truncated = helpers.truncateUrl(longUrl, 30)
      expect(truncated.length).toBeLessThanOrEqual(30)
      expect(truncated).toContain('...')
    })

    it('handles empty URLs', () => {
      expect(helpers.truncateUrl('', 50)).toBe('')
    })
  })

  // ==========================================================================
  // Date Formatting
  // ==========================================================================

  describe('formatDate', () => {
    it('formats valid date strings', () => {
      const result = helpers.formatDate('2024-01-15T10:30:00Z')
      expect(result).toMatch(/15\.01\.2024/)
    })

    it('returns empty string for null', () => {
      expect(helpers.formatDate(null)).toBe('')
    })

    it('returns empty string for undefined', () => {
      expect(helpers.formatDate(undefined)).toBe('')
    })

    it('returns original string for invalid dates', () => {
      expect(helpers.formatDate('not-a-date')).toBe('not-a-date')
    })
  })

  describe('formatRelativeDate', () => {
    it('returns empty string for null', () => {
      expect(helpers.formatRelativeDate(null)).toBe('')
    })

    it('returns empty string for undefined', () => {
      expect(helpers.formatRelativeDate(undefined)).toBe('')
    })

    it('formats recent dates relatively', () => {
      const recentDate = new Date(Date.now() - 30 * 60000).toISOString() // 30 minutes ago
      const result = helpers.formatRelativeDate(recentDate)
      // Should contain some indication of minutes or hours
      expect(result).toBeTruthy()
    })
  })

  // ==========================================================================
  // Available Languages
  // ==========================================================================

  describe('availableLanguages', () => {
    it('contains German and English', () => {
      const codes = helpers.availableLanguages.map((l) => l.code)
      expect(codes).toContain('de')
      expect(codes).toContain('en')
    })

    it('has name, code and flag for each language', () => {
      helpers.availableLanguages.forEach((lang) => {
        expect(lang.code).toBeTruthy()
        expect(lang.name).toBeTruthy()
        expect(lang.flag).toBeTruthy()
      })
    })
  })
})
