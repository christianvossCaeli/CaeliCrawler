/**
 * Tests for Category Validation utilities
 */
import { describe, it, expect } from 'vitest'
import {
  createCategoryValidationRules,
  validateCategoryForm,
  useCategoryValidation,
} from './categoryValidation'
import type { Composer } from 'vue-i18n'

// Mock translation function with proper typing
const mockT = ((key: string, params?: Record<string, unknown> | number) => {
  if (typeof params === 'object' && params !== null) {
    return `${key}:${JSON.stringify(params)}`
  }
  return key
}) as Composer['t']

describe('createCategoryValidationRules', () => {
  const rules = createCategoryValidationRules(mockT)

  // ==========================================================================
  // Required Rule
  // ==========================================================================

  describe('required', () => {
    it('should return true for non-empty string', () => {
      const rule = rules.required('Name')
      expect(rule('test')).toBe(true)
    })

    it('should return error for null', () => {
      const rule = rules.required('Name')
      expect(rule(null)).toContain('validation.required')
    })

    it('should return error for undefined', () => {
      const rule = rules.required('Name')
      expect(rule(undefined)).toContain('validation.required')
    })

    it('should return error for empty string', () => {
      const rule = rules.required('Name')
      expect(rule('')).toContain('validation.required')
    })

    it('should return error for whitespace-only string', () => {
      const rule = rules.required('Name')
      expect(rule('   ')).toContain('validation.required')
    })

    it('should return error for empty array', () => {
      const rule = rules.required('Tags')
      expect(rule([])).toContain('validation.required')
    })

    it('should return true for non-empty array', () => {
      const rule = rules.required('Tags')
      expect(rule(['tag1'])).toBe(true)
    })
  })

  // ==========================================================================
  // Name Rules
  // ==========================================================================

  describe('name', () => {
    it('should return array of rules', () => {
      expect(rules.name()).toHaveLength(3)
    })

    it('should validate required', () => {
      const [required] = rules.name()
      expect(required('')).toContain('nameRequired')
      expect(required('Test')).toBe(true)
    })

    it('should validate minimum length', () => {
      const [, minLength] = rules.name()
      expect(minLength('')).toContain('nameMinLength')
      expect(minLength('A')).toBe(true)
    })

    it('should validate maximum length', () => {
      const [, , maxLength] = rules.name()
      const longName = 'a'.repeat(256)
      expect(maxLength(longName)).toContain('nameMaxLength')
      expect(maxLength('Valid Name')).toBe(true)
    })
  })

  // ==========================================================================
  // Purpose Rules
  // ==========================================================================

  describe('purpose', () => {
    it('should return array of rules', () => {
      expect(rules.purpose()).toHaveLength(2)
    })

    it('should validate required', () => {
      const [required] = rules.purpose()
      expect(required('')).toContain('purposeRequired')
      expect(required('A purpose')).toBe(true)
    })

    it('should validate minimum length', () => {
      const [, minLength] = rules.purpose()
      expect(minLength('short')).toContain('purposeMinLength')
      expect(minLength('A purpose that is long enough')).toBe(true)
    })
  })

  // ==========================================================================
  // Languages Rules
  // ==========================================================================

  describe('languages', () => {
    it('should return array with one rule', () => {
      expect(rules.languages()).toHaveLength(1)
    })

    it('should validate at least one language', () => {
      const [rule] = rules.languages()
      expect(rule([])).toContain('languagesRequired')
      expect(rule(['de'])).toBe(true)
    })
  })

  // ==========================================================================
  // Cron Expression Rules
  // ==========================================================================

  describe('cronExpression', () => {
    it('should allow empty value (optional)', () => {
      const [rule] = rules.cronExpression()
      expect(rule('')).toBe(true)
      expect(rule(null)).toBe(true)
    })

    it('should validate 5-field cron expressions', () => {
      const [rule] = rules.cronExpression()
      expect(rule('0 * * * *')).toBe(true) // Every hour
      expect(rule('*/15 * * * *')).toBe(true) // Every 15 minutes
      expect(rule('0 9 * * 1')).toBe(true) // 9am Monday
    })

    it('should validate 6-field cron expressions', () => {
      const [rule] = rules.cronExpression()
      expect(rule('0 0 * * * *')).toBe(true) // Every hour
    })

    it('should reject invalid field count', () => {
      const [rule] = rules.cronExpression()
      expect(rule('0 * *')).toContain('cronFieldCount')
      expect(rule('0 * * * * * *')).toContain('cronFieldCount')
    })

    it('should reject invalid cron syntax', () => {
      const [rule] = rules.cronExpression()
      expect(rule('invalid cron expression')).toContain('cron')
    })
  })

  // ==========================================================================
  // Regex Pattern Rule
  // ==========================================================================

  describe('regexPattern', () => {
    it('should allow empty value (optional)', () => {
      const rule = rules.regexPattern('Pattern')
      expect(rule('')).toBe(true)
      expect(rule(null)).toBe(true)
    })

    it('should validate valid regex', () => {
      const rule = rules.regexPattern('Pattern')
      expect(rule('.*\\.pdf$')).toBe(true)
      expect(rule('^https?://')).toBe(true)
    })

    it('should reject invalid regex', () => {
      const rule = rules.regexPattern('Pattern')
      expect(rule('[invalid')).toContain('regexInvalid')
    })
  })

  // ==========================================================================
  // Regex Patterns Array Rule
  // ==========================================================================

  describe('regexPatterns', () => {
    it('should allow empty value (optional)', () => {
      const rule = rules.regexPatterns('Patterns')
      expect(rule(null)).toBe(true)
      expect(rule([])).toBe(true)
    })

    it('should validate all patterns in array', () => {
      const rule = rules.regexPatterns('Patterns')
      expect(rule(['.*\\.pdf$', '^https?://'])).toBe(true)
    })

    it('should reject array with invalid pattern', () => {
      const rule = rules.regexPatterns('Patterns')
      expect(rule(['valid', '[invalid'])).toContain('regexPatternInvalid')
    })
  })

  // ==========================================================================
  // URL Patterns Rules
  // ==========================================================================

  describe('urlPatterns', () => {
    it('should allow empty value (optional)', () => {
      const [rule] = rules.urlPatterns()
      expect(rule(null)).toBe(true)
      expect(rule([])).toBe(true)
    })

    it('should validate valid URL patterns', () => {
      const [rule] = rules.urlPatterns()
      expect(rule(['.*\\.html$', '/news/.*'])).toBe(true)
    })

    it('should reject invalid URL patterns', () => {
      const [rule] = rules.urlPatterns()
      expect(rule(['[invalid'])).toContain('urlPatternInvalid')
    })
  })

  // ==========================================================================
  // Search Terms Rules
  // ==========================================================================

  describe('searchTerms', () => {
    it('should allow empty value (optional)', () => {
      const [rule] = rules.searchTerms()
      expect(rule(null)).toBe(true)
      expect(rule([])).toBe(true)
    })

    it('should validate valid search terms array', () => {
      const [rule] = rules.searchTerms()
      expect(rule(['term1', 'term2'])).toBe(true)
    })

    it('should reject non-array value', () => {
      const [rule] = rules.searchTerms()
      expect(rule('not an array')).toContain('searchTermsInvalid')
    })

    it('should reject non-string items', () => {
      const [rule] = rules.searchTerms()
      expect(rule([123, 'valid'])).toContain('searchTermsInvalid')
    })

    it('should reject terms exceeding 255 chars', () => {
      const [rule] = rules.searchTerms()
      const longTerm = 'a'.repeat(256)
      expect(rule([longTerm])).toContain('searchTermTooLong')
    })
  })

  // ==========================================================================
  // Document Types Rules
  // ==========================================================================

  describe('documentTypes', () => {
    it('should allow empty value (optional)', () => {
      const [rule] = rules.documentTypes()
      expect(rule(null)).toBe(true)
      expect(rule([])).toBe(true)
    })

    it('should validate valid document types array', () => {
      const [rule] = rules.documentTypes()
      expect(rule(['pdf', 'html', 'docx'])).toBe(true)
    })

    it('should reject non-array value', () => {
      const [rule] = rules.documentTypes()
      expect(rule('pdf')).toContain('documentTypesInvalid')
    })

    it('should reject non-string items', () => {
      const [rule] = rules.documentTypes()
      expect(rule([123])).toContain('documentTypesInvalid')
    })

    it('should reject empty string items', () => {
      const [rule] = rules.documentTypes()
      expect(rule(['pdf', ''])).toContain('documentTypeEmpty')
      expect(rule(['pdf', '   '])).toContain('documentTypeEmpty')
    })
  })

  // ==========================================================================
  // Extraction Handler Rules
  // ==========================================================================

  describe('extractionHandler', () => {
    it('should allow empty value (uses default)', () => {
      const [rule] = rules.extractionHandler()
      expect(rule('')).toBe(true)
      expect(rule(null)).toBe(true)
    })

    it('should accept valid handler values', () => {
      const [rule] = rules.extractionHandler()
      expect(rule('default')).toBe(true)
      expect(rule('event')).toBe(true)
    })

    it('should reject invalid handler values', () => {
      const [rule] = rules.extractionHandler()
      expect(rule('invalid')).toContain('extractionHandlerInvalid')
      expect(rule('custom')).toContain('extractionHandlerInvalid')
    })
  })

  // ==========================================================================
  // Target Entity Type ID Rules
  // ==========================================================================

  describe('targetEntityTypeId', () => {
    it('should allow empty value (optional)', () => {
      const [rule] = rules.targetEntityTypeId()
      expect(rule('')).toBe(true)
      expect(rule(null)).toBe(true)
    })

    it('should accept valid UUID', () => {
      const [rule] = rules.targetEntityTypeId()
      expect(rule('123e4567-e89b-12d3-a456-426614174000')).toBe(true)
      expect(rule('550e8400-e29b-41d4-a716-446655440000')).toBe(true)
    })

    it('should reject non-string values', () => {
      const [rule] = rules.targetEntityTypeId()
      expect(rule(12345)).toContain('targetEntityTypeInvalid')
    })

    it('should reject invalid UUID format', () => {
      const [rule] = rules.targetEntityTypeId()
      expect(rule('not-a-uuid')).toContain('targetEntityTypeInvalid')
      expect(rule('123e4567-e89b-12d3-a456')).toContain('targetEntityTypeInvalid')
      expect(rule('123e4567e89b12d3a456426614174000')).toContain('targetEntityTypeInvalid')
    })
  })

  // ==========================================================================
  // Extraction Prompt Rules
  // ==========================================================================

  describe('extractionPrompt', () => {
    it('should allow empty value (optional)', () => {
      const [rule] = rules.extractionPrompt()
      expect(rule('')).toBe(true)
      expect(rule(null)).toBe(true)
    })

    it('should allow valid length prompts', () => {
      const [rule] = rules.extractionPrompt()
      expect(rule('Extract the title and date.')).toBe(true)
    })

    it('should reject prompts exceeding 10000 chars', () => {
      const [rule] = rules.extractionPrompt()
      const longPrompt = 'a'.repeat(10001)
      expect(rule(longPrompt)).toContain('promptTooLong')
    })
  })
})

// ==========================================================================
// validateCategoryForm
// ==========================================================================

describe('validateCategoryForm', () => {
  it('should return valid for complete form', () => {
    const result = validateCategoryForm(
      {
        name: 'Test Category',
        purpose: 'A purpose for testing',
        languages: ['de'],
      },
      mockT
    )

    expect(result.valid).toBe(true)
    expect(result.errors).toEqual({})
  })

  it('should return errors for missing name', () => {
    const result = validateCategoryForm(
      {
        name: '',
        purpose: 'A purpose for testing',
        languages: ['de'],
      },
      mockT
    )

    expect(result.valid).toBe(false)
    expect(result.errors.name).toBeDefined()
  })

  it('should return errors for name too long', () => {
    const result = validateCategoryForm(
      {
        name: 'a'.repeat(256),
        purpose: 'A purpose for testing',
        languages: ['de'],
      },
      mockT
    )

    expect(result.valid).toBe(false)
    expect(result.errors.name).toContain('nameMaxLength')
  })

  it('should return errors for missing purpose', () => {
    const result = validateCategoryForm(
      {
        name: 'Test',
        purpose: '',
        languages: ['de'],
      },
      mockT
    )

    expect(result.valid).toBe(false)
    expect(result.errors.purpose).toBeDefined()
  })

  it('should return errors for missing languages', () => {
    const result = validateCategoryForm(
      {
        name: 'Test',
        purpose: 'A purpose',
        languages: [],
      },
      mockT
    )

    expect(result.valid).toBe(false)
    expect(result.errors.languages).toBeDefined()
  })

  it('should validate cron expression', () => {
    const result = validateCategoryForm(
      {
        name: 'Test',
        purpose: 'A purpose for testing',
        languages: ['de'],
        schedule_cron: 'invalid',
      },
      mockT
    )

    expect(result.valid).toBe(false)
    expect(result.errors.schedule_cron).toBeDefined()
  })

  it('should validate URL include patterns', () => {
    const result = validateCategoryForm(
      {
        name: 'Test',
        purpose: 'A purpose for testing',
        languages: ['de'],
        url_include_patterns: ['[invalid'],
      },
      mockT
    )

    expect(result.valid).toBe(false)
    expect(result.errors.url_include_patterns).toBeDefined()
  })

  it('should validate URL exclude patterns', () => {
    const result = validateCategoryForm(
      {
        name: 'Test',
        purpose: 'A purpose for testing',
        languages: ['de'],
        url_exclude_patterns: ['[invalid'],
      },
      mockT
    )

    expect(result.valid).toBe(false)
    expect(result.errors.url_exclude_patterns).toBeDefined()
  })

  it('should validate prompt length', () => {
    const result = validateCategoryForm(
      {
        name: 'Test',
        purpose: 'A purpose for testing',
        languages: ['de'],
        ai_extraction_prompt: 'a'.repeat(10001),
      },
      mockT
    )

    expect(result.valid).toBe(false)
    expect(result.errors.ai_extraction_prompt).toBeDefined()
  })
})

// ==========================================================================
// useCategoryValidation
// ==========================================================================

describe('useCategoryValidation', () => {
  it('should return rules and validate function', () => {
    const { rules, validate } = useCategoryValidation(mockT)

    expect(rules).toBeDefined()
    expect(rules.name).toBeDefined()
    expect(validate).toBeInstanceOf(Function)
  })

  it('should validate form data', () => {
    const { validate } = useCategoryValidation(mockT)

    const result = validate({
      name: 'Test',
      purpose: 'A valid purpose here',
      languages: ['de'],
    })

    expect(result.valid).toBe(true)
  })
})
