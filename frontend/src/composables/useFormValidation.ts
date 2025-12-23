import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { isValidRegexPattern } from '@/utils/csvParser'

/**
 * Vuetify validation rule type
 * Returns true if valid, or an error message string if invalid
 */
export type ValidationRule<T = string> = (value: T) => true | string

/**
 * Composable for reusable form validation rules
 *
 * Provides factory functions for common validation patterns with i18n support.
 * All rules return either `true` (valid) or a localized error message string.
 *
 * @example
 * ```typescript
 * const { required, minLength, maxLength, url, createRules } = useFormValidation()
 *
 * // Individual rules
 * const nameRules = [required('name'), minLength(2), maxLength(200)]
 * const urlRules = [required('url'), url()]
 *
 * // Combined with createRules helper
 * const nameRules = createRules.name({ min: 2, max: 200 })
 * const urlRules = createRules.url()
 * ```
 */
export function useFormValidation() {
  const { t } = useI18n()

  // ==========================================================================
  // Basic Rule Builders
  // ==========================================================================

  /**
   * Required field validation
   * @param fieldKey - i18n key for the field name (used in error message)
   */
  const required = (fieldKey = 'field'): ValidationRule => {
    return (v: string) => {
      if (!v || (typeof v === 'string' && !v.trim())) {
        return t(`sources.validation.${fieldKey}Required`, t('common.fieldRequired', 'This field is required'))
      }
      return true
    }
  }

  /**
   * Minimum length validation
   * @param min - Minimum character count
   */
  const minLength = (min: number): ValidationRule => {
    return (v: string) => {
      if (!v || v.length < min) {
        return t('sources.validation.nameTooShort', { min }, `Must be at least ${min} characters`)
      }
      return true
    }
  }

  /**
   * Maximum length validation
   * @param max - Maximum character count
   */
  const maxLength = (max: number): ValidationRule => {
    return (v: string) => {
      if (v && v.length > max) {
        return t('sources.validation.nameTooLong', { max }, `Must be at most ${max} characters`)
      }
      return true
    }
  }

  /**
   * URL validation (http/https only)
   */
  const url = (): ValidationRule => {
    return (v: string) => {
      if (!v) return true // Use required() for mandatory fields
      try {
        const parsed = new URL(v)
        if (!['http:', 'https:'].includes(parsed.protocol)) {
          return t('sources.validation.urlInvalid', 'Please enter a valid URL (http:// or https://)')
        }
        return true
      } catch {
        return t('sources.validation.urlInvalid', 'Please enter a valid URL (http:// or https://)')
      }
    }
  }

  /**
   * Email validation
   */
  const email = (): ValidationRule => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return (v: string) => {
      if (!v) return true // Use required() for mandatory fields
      if (!emailRegex.test(v)) {
        return t('common.invalidEmail', 'Please enter a valid email address')
      }
      return true
    }
  }

  /**
   * Regex pattern validation (validates that a string is a valid regex)
   */
  const regexPattern = (): ValidationRule => {
    return (v: string) => {
      if (!v) return true
      if (!isValidRegexPattern(v)) {
        return t('common.invalidRegex', 'Invalid regex pattern')
      }
      return true
    }
  }

  /**
   * Custom pattern validation (validates value against a regex)
   * @param pattern - Regex pattern to match
   * @param message - Error message or i18n key
   */
  const pattern = (patternRegex: RegExp, message: string): ValidationRule => {
    return (v: string) => {
      if (!v) return true
      if (!patternRegex.test(v)) {
        return t(message, message)
      }
      return true
    }
  }

  /**
   * Numeric range validation
   * @param min - Minimum value (inclusive)
   * @param max - Maximum value (inclusive)
   */
  const range = (min: number, max: number): ValidationRule<number> => {
    return (v: number) => {
      if (v < min || v > max) {
        return t('common.outOfRange', { min, max }, `Value must be between ${min} and ${max}`)
      }
      return true
    }
  }

  // ==========================================================================
  // Composite Rule Builders
  // ==========================================================================

  interface NameRuleOptions {
    min?: number
    max?: number
    required?: boolean
  }

  interface UrlRuleOptions {
    required?: boolean
  }

  /**
   * Pre-configured rule sets for common field types
   */
  const createRules = {
    /**
     * Name field rules (required, min/max length)
     */
    name: (options: NameRuleOptions = {}) => {
      const { min = 2, max = 200, required: isRequired = true } = options
      const rules: ValidationRule[] = []
      if (isRequired) rules.push(required('name'))
      rules.push(minLength(min))
      rules.push(maxLength(max))
      return computed(() => rules)
    },

    /**
     * URL field rules (required, valid URL)
     */
    url: (options: UrlRuleOptions = {}) => {
      const { required: isRequired = true } = options
      const rules: ValidationRule[] = []
      if (isRequired) rules.push(required('url'))
      rules.push(url())
      return computed(() => rules)
    },

    /**
     * Source type field rules (required)
     */
    sourceType: () => {
      return computed(() => [
        (v: string) => !!v || t('sources.validation.sourceTypeRequired', 'Source type is required'),
      ])
    },
  }

  // ==========================================================================
  // Regex Pattern List Helpers
  // ==========================================================================

  /**
   * Create computed properties for validating regex pattern lists
   * Useful for include/exclude patterns in crawl config
   *
   * @param patterns - Reactive array of pattern strings
   * @returns Object with hasInvalid computed and getInvalidMessage function
   */
  const usePatternListValidation = (patterns: () => string[]) => {
    const hasInvalidPatterns = computed(() => {
      const list = patterns()
      return list.some((p) => !isValidRegexPattern(p))
    })

    const getInvalidPatternsMessage = computed(() => {
      if (!hasInvalidPatterns.value) return []
      const list = patterns()
      const invalid = list.filter((p) => !isValidRegexPattern(p))
      return [`Invalid regex pattern(s): ${invalid.join(', ')}`]
    })

    return {
      hasInvalidPatterns,
      getInvalidPatternsMessage,
    }
  }

  return {
    // Basic rule builders
    required,
    minLength,
    maxLength,
    url,
    email,
    regexPattern,
    pattern,
    range,
    // Composite rule builders
    createRules,
    // Pattern list validation
    usePatternListValidation,
  }
}
