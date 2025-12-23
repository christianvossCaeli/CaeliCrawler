import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useFormValidation } from './useFormValidation'

// Mock vue-i18n
vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string, fallback?: string | Record<string, unknown>) => {
      // Return fallback if string, otherwise return key
      if (typeof fallback === 'string') return fallback
      return key
    },
  }),
}))

describe('useFormValidation', () => {
  let validation: ReturnType<typeof useFormValidation>

  beforeEach(() => {
    validation = useFormValidation()
  })

  describe('required', () => {
    it('should fail for empty string', () => {
      const rule = validation.required('name')
      expect(rule('')).not.toBe(true)
    })

    it('should fail for whitespace only', () => {
      const rule = validation.required('name')
      expect(rule('   ')).not.toBe(true)
    })

    it('should pass for non-empty string', () => {
      const rule = validation.required('name')
      expect(rule('test')).toBe(true)
    })
  })

  describe('minLength', () => {
    it('should fail for string shorter than minimum', () => {
      const rule = validation.minLength(3)
      expect(rule('ab')).not.toBe(true)
    })

    it('should pass for string equal to minimum', () => {
      const rule = validation.minLength(3)
      expect(rule('abc')).toBe(true)
    })

    it('should pass for string longer than minimum', () => {
      const rule = validation.minLength(3)
      expect(rule('abcd')).toBe(true)
    })
  })

  describe('maxLength', () => {
    it('should fail for string longer than maximum', () => {
      const rule = validation.maxLength(5)
      expect(rule('abcdef')).not.toBe(true)
    })

    it('should pass for string equal to maximum', () => {
      const rule = validation.maxLength(5)
      expect(rule('abcde')).toBe(true)
    })

    it('should pass for string shorter than maximum', () => {
      const rule = validation.maxLength(5)
      expect(rule('abc')).toBe(true)
    })

    it('should pass for empty string', () => {
      const rule = validation.maxLength(5)
      expect(rule('')).toBe(true)
    })
  })

  describe('url', () => {
    it('should pass for valid http URL', () => {
      const rule = validation.url()
      expect(rule('http://example.com')).toBe(true)
    })

    it('should pass for valid https URL', () => {
      const rule = validation.url()
      expect(rule('https://example.com/path?query=1')).toBe(true)
    })

    it('should fail for invalid URL', () => {
      const rule = validation.url()
      expect(rule('not-a-url')).not.toBe(true)
    })

    it('should fail for ftp protocol', () => {
      const rule = validation.url()
      expect(rule('ftp://example.com')).not.toBe(true)
    })

    it('should pass for empty string (use required for mandatory)', () => {
      const rule = validation.url()
      expect(rule('')).toBe(true)
    })
  })

  describe('email', () => {
    it('should pass for valid email', () => {
      const rule = validation.email()
      expect(rule('test@example.com')).toBe(true)
    })

    it('should fail for invalid email', () => {
      const rule = validation.email()
      expect(rule('not-an-email')).not.toBe(true)
    })

    it('should fail for email without domain', () => {
      const rule = validation.email()
      expect(rule('test@')).not.toBe(true)
    })

    it('should pass for empty string', () => {
      const rule = validation.email()
      expect(rule('')).toBe(true)
    })
  })

  describe('regexPattern', () => {
    it('should pass for valid regex', () => {
      const rule = validation.regexPattern()
      expect(rule('/documents/')).toBe(true)
    })

    it('should pass for valid regex with special chars', () => {
      const rule = validation.regexPattern()
      expect(rule('.*\\.pdf$')).toBe(true)
    })

    it('should fail for invalid regex', () => {
      const rule = validation.regexPattern()
      expect(rule('[')).not.toBe(true)
    })

    it('should pass for empty string', () => {
      const rule = validation.regexPattern()
      expect(rule('')).toBe(true)
    })
  })

  describe('pattern', () => {
    it('should pass for matching pattern', () => {
      const rule = validation.pattern(/^\d+$/, 'Must be numeric')
      expect(rule('12345')).toBe(true)
    })

    it('should fail for non-matching pattern', () => {
      const rule = validation.pattern(/^\d+$/, 'Must be numeric')
      expect(rule('abc')).not.toBe(true)
    })
  })

  describe('range', () => {
    it('should pass for value within range', () => {
      const rule = validation.range(1, 10)
      expect(rule(5)).toBe(true)
    })

    it('should pass for value at minimum', () => {
      const rule = validation.range(1, 10)
      expect(rule(1)).toBe(true)
    })

    it('should pass for value at maximum', () => {
      const rule = validation.range(1, 10)
      expect(rule(10)).toBe(true)
    })

    it('should fail for value below minimum', () => {
      const rule = validation.range(1, 10)
      expect(rule(0)).not.toBe(true)
    })

    it('should fail for value above maximum', () => {
      const rule = validation.range(1, 10)
      expect(rule(11)).not.toBe(true)
    })
  })

  describe('createRules.name', () => {
    it('should create name rules with defaults', () => {
      const rules = validation.createRules.name()
      expect(rules.value).toHaveLength(3) // required, minLength, maxLength
    })

    it('should create name rules with custom min/max', () => {
      const rules = validation.createRules.name({ min: 5, max: 50 })
      const [, minRule, maxRule] = rules.value

      expect(minRule('abcd')).not.toBe(true) // too short
      expect(minRule('abcde')).toBe(true) // exactly 5

      expect(maxRule('a'.repeat(50))).toBe(true) // exactly 50
      expect(maxRule('a'.repeat(51))).not.toBe(true) // too long
    })

    it('should create name rules without required when specified', () => {
      const rules = validation.createRules.name({ required: false })
      expect(rules.value).toHaveLength(2) // only minLength, maxLength
    })
  })

  describe('createRules.url', () => {
    it('should create url rules with required by default', () => {
      const rules = validation.createRules.url()
      expect(rules.value).toHaveLength(2) // required, url
    })

    it('should create url rules without required when specified', () => {
      const rules = validation.createRules.url({ required: false })
      expect(rules.value).toHaveLength(1) // only url
    })
  })

  describe('createRules.sourceType', () => {
    it('should create sourceType rules', () => {
      const rules = validation.createRules.sourceType()
      expect(rules.value).toHaveLength(1)

      const [rule] = rules.value
      expect(rule('')).not.toBe(true) // fails for empty
      expect(rule('WEBSITE')).toBe(true) // passes for valid type
    })
  })

  describe('usePatternListValidation', () => {
    it('should report no invalid patterns for valid list', () => {
      const patterns = () => ['/documents/', '/archive/', '.*\\.pdf$']
      const { hasInvalidPatterns, getInvalidPatternsMessage } =
        validation.usePatternListValidation(patterns)

      expect(hasInvalidPatterns.value).toBe(false)
      expect(getInvalidPatternsMessage.value).toEqual([])
    })

    it('should report invalid patterns for list with invalid regex', () => {
      const patterns = () => ['/documents/', '[invalid', '.*\\.pdf$']
      const { hasInvalidPatterns, getInvalidPatternsMessage } =
        validation.usePatternListValidation(patterns)

      expect(hasInvalidPatterns.value).toBe(true)
      expect(getInvalidPatternsMessage.value).toHaveLength(1)
      expect(getInvalidPatternsMessage.value[0]).toContain('[invalid')
    })

    it('should report no invalid patterns for empty list', () => {
      const patterns = () => [] as string[]
      const { hasInvalidPatterns, getInvalidPatternsMessage } =
        validation.usePatternListValidation(patterns)

      expect(hasInvalidPatterns.value).toBe(false)
      expect(getInvalidPatternsMessage.value).toEqual([])
    })
  })
})
