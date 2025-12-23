/**
 * CSV Parser Unit Tests
 *
 * Tests for the CSV parsing utilities used in bulk source import.
 * Covers edge cases, validation, delimiter detection, and URL handling.
 */
import { describe, it, expect } from 'vitest'
import {
  validateCsvInput,
  detectDelimiter,
  isValidUrl,
  normalizeUrl,
  parseSourceType,
  parseTags,
  parseCsvLine,
  parseCsv,
  isValidRegexPattern,
  validateRegexPatterns,
} from './csvParser'
import { BULK_IMPORT } from '@/config/sources'

describe('csvParser', () => {
  // ===========================================================================
  // validateCsvInput
  // ===========================================================================
  describe('validateCsvInput', () => {
    it('should reject empty content', () => {
      expect(validateCsvInput('')).toEqual({ valid: false, error: 'CSV content is empty' })
      expect(validateCsvInput('   ')).toEqual({ valid: false, error: 'CSV content is empty' })
      expect(validateCsvInput('\n\n')).toEqual({ valid: false, error: 'CSV content is empty' })
    })

    it('should accept valid content', () => {
      const result = validateCsvInput('Name;URL\nTest;https://example.com')
      expect(result.valid).toBe(true)
      expect(result.lineCount).toBe(2)
    })

    it('should count lines correctly', () => {
      const csv = 'Line1\nLine2\nLine3\nLine4\nLine5'
      const result = validateCsvInput(csv)
      expect(result.valid).toBe(true)
      expect(result.lineCount).toBe(5)
    })

    it('should calculate byte size', () => {
      const csv = 'Test content with special chars äöü'
      const result = validateCsvInput(csv)
      expect(result.valid).toBe(true)
      expect(result.byteSize).toBeGreaterThan(0)
    })

    it('should reject content exceeding max lines', () => {
      // Create content with MAX_LINES + 1 lines
      const lines = Array(BULK_IMPORT.MAX_LINES + 1).fill('Line').join('\n')
      const result = validateCsvInput(lines)
      expect(result.valid).toBe(false)
      expect(result.error).toContain('Too many lines')
    })
  })

  // ===========================================================================
  // detectDelimiter
  // ===========================================================================
  describe('detectDelimiter', () => {
    it('should detect semicolon delimiter', () => {
      expect(detectDelimiter('Name;URL;Type')).toBe(';')
    })

    it('should detect comma delimiter', () => {
      expect(detectDelimiter('Name,URL,Type')).toBe(',')
    })

    it('should detect pipe delimiter', () => {
      expect(detectDelimiter('Name|URL|Type')).toBe('|')
    })

    it('should detect tab delimiter', () => {
      expect(detectDelimiter('Name\tURL\tType')).toBe('\t')
    })

    it('should use majority delimiter when mixed', () => {
      // More semicolons than commas
      expect(detectDelimiter('Name;URL;Type,extra')).toBe(';')
      // More commas than semicolons
      expect(detectDelimiter('Name,URL,Type;extra')).toBe(',')
    })

    it('should default to semicolon when no delimiters found', () => {
      expect(detectDelimiter('SingleValue')).toBe(';')
    })

    it('should handle empty string', () => {
      expect(detectDelimiter('')).toBe(';')
    })

    it('should only consider first line for detection', () => {
      const csv = 'Name,URL,Type\nValue;Value;Value'
      expect(detectDelimiter(csv)).toBe(',')
    })
  })

  // ===========================================================================
  // isValidUrl
  // ===========================================================================
  describe('isValidUrl', () => {
    it('should validate correct URLs', () => {
      expect(isValidUrl('https://example.com')).toBe(true)
      expect(isValidUrl('http://example.com')).toBe(true)
      expect(isValidUrl('https://sub.example.com/path?query=1')).toBe(true)
      expect(isValidUrl('https://www.example.co.uk')).toBe(true)
    })

    it('should reject URLs without protocol', () => {
      expect(isValidUrl('example.com')).toBe(false)
      expect(isValidUrl('www.example.com')).toBe(false)
    })

    it('should reject non-http protocols', () => {
      expect(isValidUrl('ftp://example.com')).toBe(false)
      expect(isValidUrl('file:///path/to/file')).toBe(false)
      expect(isValidUrl('mailto:test@example.com')).toBe(false)
    })

    it('should reject URLs without dot in hostname', () => {
      expect(isValidUrl('http://localhost')).toBe(false)
      expect(isValidUrl('https://intranet')).toBe(false)
    })

    it('should reject empty and invalid inputs', () => {
      expect(isValidUrl('')).toBe(false)
      expect(isValidUrl('not a url')).toBe(false)
      expect(isValidUrl('://missing-protocol.com')).toBe(false)
    })

    it('should handle edge cases', () => {
      expect(isValidUrl('https://example.com:8080')).toBe(true)
      expect(isValidUrl('https://example.com/path/to/resource')).toBe(true)
      expect(isValidUrl('https://example.com#anchor')).toBe(true)
    })
  })

  // ===========================================================================
  // normalizeUrl
  // ===========================================================================
  describe('normalizeUrl', () => {
    it('should lowercase URLs', () => {
      expect(normalizeUrl('HTTPS://EXAMPLE.COM')).toBe('https://example.com')
    })

    it('should trim whitespace', () => {
      expect(normalizeUrl('  https://example.com  ')).toBe('https://example.com')
    })

    it('should add https protocol if missing', () => {
      expect(normalizeUrl('example.com')).toBe('https://example.com')
      expect(normalizeUrl('www.example.com')).toBe('https://www.example.com')
    })

    it('should not double protocol', () => {
      expect(normalizeUrl('https://example.com')).toBe('https://example.com')
      expect(normalizeUrl('http://example.com')).toBe('http://example.com')
    })

    it('should handle empty string', () => {
      expect(normalizeUrl('')).toBe('')
    })
  })

  // ===========================================================================
  // parseSourceType
  // ===========================================================================
  describe('parseSourceType', () => {
    it('should return WEBSITE for undefined', () => {
      expect(parseSourceType(undefined)).toBe('WEBSITE')
    })

    it('should return WEBSITE for empty string', () => {
      expect(parseSourceType('')).toBe('WEBSITE')
    })

    it('should normalize case', () => {
      expect(parseSourceType('website')).toBe('WEBSITE')
      expect(parseSourceType('WEBSITE')).toBe('WEBSITE')
      expect(parseSourceType('Website')).toBe('WEBSITE')
    })

    it('should map common variations', () => {
      expect(parseSourceType('WEB')).toBe('WEBSITE')
      expect(parseSourceType('RSS_FEED')).toBe('RSS')
      expect(parseSourceType('RSS-FEED')).toBe('RSS')
      expect(parseSourceType('FEED')).toBe('RSS')
      expect(parseSourceType('API')).toBe('CUSTOM_API')
      expect(parseSourceType('OPARL')).toBe('OPARL_API')
    })

    it('should handle whitespace', () => {
      expect(parseSourceType('  WEBSITE  ')).toBe('WEBSITE')
    })

    it('should return WEBSITE for unknown types', () => {
      expect(parseSourceType('UNKNOWN_TYPE')).toBe('WEBSITE')
      expect(parseSourceType('random')).toBe('WEBSITE')
    })
  })

  // ===========================================================================
  // parseTags
  // ===========================================================================
  describe('parseTags', () => {
    it('should return empty array for undefined', () => {
      expect(parseTags(undefined)).toEqual([])
    })

    it('should return empty array for empty string', () => {
      expect(parseTags('')).toEqual([])
    })

    it('should split by comma', () => {
      expect(parseTags('tag1,tag2,tag3')).toEqual(['tag1', 'tag2', 'tag3'])
    })

    it('should split by semicolon', () => {
      expect(parseTags('tag1;tag2;tag3')).toEqual(['tag1', 'tag2', 'tag3'])
    })

    it('should trim whitespace from tags', () => {
      expect(parseTags(' tag1 , tag2 , tag3 ')).toEqual(['tag1', 'tag2', 'tag3'])
    })

    it('should filter empty tags', () => {
      expect(parseTags('tag1,,tag2,,')).toEqual(['tag1', 'tag2'])
    })

    it('should handle mixed delimiters', () => {
      expect(parseTags('tag1,tag2;tag3')).toEqual(['tag1', 'tag2', 'tag3'])
    })
  })

  // ===========================================================================
  // parseCsvLine
  // ===========================================================================
  describe('parseCsvLine', () => {
    const defaultOptions = { defaultTags: [], existingUrls: [], skipDuplicates: false }
    const emptySet = new Set<string>()

    it('should return null for empty line', () => {
      expect(parseCsvLine('', ';', defaultOptions, emptySet)).toBeNull()
      expect(parseCsvLine('   ', ';', defaultOptions, emptySet)).toBeNull()
    })

    it('should skip header lines', () => {
      expect(parseCsvLine('Name;URL;Type', ';', defaultOptions, emptySet)).toBeNull()
      expect(parseCsvLine('name,url,tags', ',', defaultOptions, emptySet)).toBeNull()
      expect(parseCsvLine('base_url;source_type', ';', defaultOptions, emptySet)).toBeNull()
    })

    it('should parse URL-only line and extract name', () => {
      const result = parseCsvLine('https://example.com', ';', defaultOptions, emptySet)
      expect(result).not.toBeNull()
      expect(result!.name).toBe('example.com')
      expect(result!.base_url).toBe('https://example.com')
    })

    it('should parse Name;URL format', () => {
      const result = parseCsvLine('My Site;https://example.com', ';', defaultOptions, emptySet)
      expect(result).not.toBeNull()
      expect(result!.name).toBe('My Site')
      expect(result!.base_url).toBe('https://example.com')
      expect(result!.source_type).toBe('WEBSITE')
    })

    it('should parse Name;URL;Type format', () => {
      const result = parseCsvLine('My Feed;https://example.com/rss;RSS', ';', defaultOptions, emptySet)
      expect(result).not.toBeNull()
      expect(result!.source_type).toBe('RSS')
    })

    it('should parse Name;URL;Type;Tags format', () => {
      const result = parseCsvLine('Site;https://example.com;WEBSITE;tag1,tag2', ';', defaultOptions, emptySet)
      expect(result).not.toBeNull()
      expect(result!.tags).toEqual(['tag1', 'tag2'])
    })

    it('should merge default tags with line tags', () => {
      const options = { defaultTags: ['default1', 'default2'], existingUrls: [], skipDuplicates: false }
      const result = parseCsvLine('Site;https://example.com;WEBSITE;tag1', ';', options, emptySet)
      expect(result).not.toBeNull()
      expect(result!.allTags).toEqual(['default1', 'default2', 'tag1'])
    })

    it('should mark invalid URLs with error', () => {
      const result = parseCsvLine('Bad Site;invalid-url', ';', defaultOptions, emptySet)
      expect(result).not.toBeNull()
      expect(result!.error).toBe('Invalid URL format')
    })

    it('should detect duplicates', () => {
      const existingSet = new Set(['https://example.com'])
      const result = parseCsvLine('Site;https://example.com', ';', defaultOptions, existingSet)
      expect(result).not.toBeNull()
      expect(result!.duplicate).toBe(true)
    })

    it('should add https protocol to URLs without protocol', () => {
      const result = parseCsvLine('Site;example.com', ';', defaultOptions, emptySet)
      expect(result).not.toBeNull()
      expect(result!.base_url).toBe('https://example.com')
    })
  })

  // ===========================================================================
  // parseCsv
  // ===========================================================================
  describe('parseCsv', () => {
    it('should parse valid CSV', () => {
      const csv = 'Site1;https://example1.com\nSite2;https://example2.com'
      const result = parseCsv(csv)
      expect(result.items).toHaveLength(2)
      expect(result.validCount).toBe(2)
      expect(result.errorCount).toBe(0)
    })

    it('should skip header line', () => {
      const csv = 'Name;URL\nSite1;https://example.com'
      const result = parseCsv(csv)
      expect(result.items).toHaveLength(1)
    })

    it('should count errors correctly', () => {
      const csv = 'Valid;https://example.com\nInvalid;not-a-url'
      const result = parseCsv(csv)
      expect(result.validCount).toBe(1)
      expect(result.errorCount).toBe(1)
    })

    it('should detect duplicates within the same import', () => {
      const csv = 'Site1;https://example.com\nSite2;https://example.com'
      const result = parseCsv(csv)
      expect(result.duplicateCount).toBe(1)
    })

    it('should detect duplicates against existing URLs', () => {
      const csv = 'Site1;https://example.com'
      const result = parseCsv(csv, { existingUrls: ['https://example.com'] })
      expect(result.duplicateCount).toBe(1)
    })

    it('should handle empty input', () => {
      const result = parseCsv('')
      expect(result.parseError).toBe('CSV content is empty')
      expect(result.error).toBe('CSV content is empty') // deprecated but still works
      expect(result.items).toHaveLength(0)
    })

    it('should return invalidLineCount and deprecated errorCount', () => {
      const csv = 'Valid;https://example.com\nInvalid;not-a-url'
      const result = parseCsv(csv)
      expect(result.invalidLineCount).toBe(1)
      expect(result.errorCount).toBe(1) // deprecated alias
    })

    it('should handle different delimiters', () => {
      const csvComma = 'Site1,https://example.com'
      expect(parseCsv(csvComma).items).toHaveLength(1)

      const csvPipe = 'Site1|https://example.com'
      expect(parseCsv(csvPipe).items).toHaveLength(1)
    })

    it('should apply default tags to all items', () => {
      const csv = 'Site1;https://example1.com\nSite2;https://example2.com'
      const result = parseCsv(csv, { defaultTags: ['common-tag'] })
      expect(result.items[0].allTags).toContain('common-tag')
      expect(result.items[1].allTags).toContain('common-tag')
    })

    it('should count duplicates as valid when skipDuplicates is false', () => {
      const csv = 'Site1;https://example.com\nSite2;https://example.com'
      const result = parseCsv(csv, { skipDuplicates: false })
      // First one is valid, second is duplicate but still counted as valid
      expect(result.validCount).toBe(2)
    })

    it('should not count duplicates as valid when skipDuplicates is true', () => {
      const csv = 'Site1;https://example.com\nSite2;https://example.com'
      const result = parseCsv(csv, { skipDuplicates: true })
      // First one is valid, second is duplicate and not counted
      expect(result.validCount).toBe(1)
    })
  })

  // ===========================================================================
  // isValidRegexPattern
  // ===========================================================================
  describe('isValidRegexPattern', () => {
    it('should return true for empty pattern', () => {
      expect(isValidRegexPattern('')).toBe(true)
    })

    it('should return true for valid regex', () => {
      expect(isValidRegexPattern('.*')).toBe(true)
      expect(isValidRegexPattern('/path/to/')).toBe(true)
      expect(isValidRegexPattern('\\d+')).toBe(true)
      expect(isValidRegexPattern('[a-z]+')).toBe(true)
    })

    it('should return false for invalid regex', () => {
      expect(isValidRegexPattern('[')).toBe(false)
      expect(isValidRegexPattern('(?P<name)')).toBe(false)
      expect(isValidRegexPattern('*invalid')).toBe(false)
    })
  })

  // ===========================================================================
  // validateRegexPatterns
  // ===========================================================================
  describe('validateRegexPatterns', () => {
    it('should return valid for empty array', () => {
      const result = validateRegexPatterns([])
      expect(result.valid).toBe(true)
      expect(result.invalidPatterns).toHaveLength(0)
    })

    it('should return valid for all valid patterns', () => {
      const result = validateRegexPatterns(['.*', '/path/', '\\d+'])
      expect(result.valid).toBe(true)
      expect(result.invalidPatterns).toHaveLength(0)
    })

    it('should identify invalid patterns', () => {
      const result = validateRegexPatterns(['valid.*', '[invalid', 'also-valid'])
      expect(result.valid).toBe(false)
      expect(result.invalidPatterns).toEqual(['[invalid'])
    })

    it('should return all invalid patterns', () => {
      const result = validateRegexPatterns(['[', '*', 'valid'])
      expect(result.valid).toBe(false)
      expect(result.invalidPatterns).toHaveLength(2)
      expect(result.invalidPatterns).toContain('[')
      expect(result.invalidPatterns).toContain('*')
    })
  })
})
