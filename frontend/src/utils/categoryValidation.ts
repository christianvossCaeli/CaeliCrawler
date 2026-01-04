/**
 * Category Form Validation Rules
 *
 * Provides reusable Vuetify validation rules for category forms.
 * Uses Vue I18n for localized error messages.
 */
import type { Composer } from 'vue-i18n'

/**
 * Validation rule type for Vuetify
 */
export type ValidationRule = (value: unknown) => boolean | string

/**
 * Create validation rules with i18n support
 */
export function createCategoryValidationRules(t: Composer['t']) {
  return {
    /**
     * Required field validation
     */
    required: (fieldName: string): ValidationRule => (value) => {
      if (value === null || value === undefined) return t('validation.required', { field: fieldName })
      if (typeof value === 'string' && !value.trim()) return t('validation.required', { field: fieldName })
      if (Array.isArray(value) && value.length === 0) return t('validation.required', { field: fieldName })
      return true
    },

    /**
     * Name validation (1-255 chars)
     */
    name: (): ValidationRule[] => [
      (v) => !!v || t('categories.validation.nameRequired'),
      (v) =>
        (typeof v === 'string' && v.length >= 1) ||
        t('categories.validation.nameMinLength'),
      (v) =>
        (typeof v === 'string' && v.length <= 255) ||
        t('categories.validation.nameMaxLength'),
    ],

    /**
     * Purpose validation (required)
     */
    purpose: (): ValidationRule[] => [
      (v) => !!v || t('categories.validation.purposeRequired'),
      (v) =>
        (typeof v === 'string' && v.length >= 10) ||
        t('categories.validation.purposeMinLength'),
    ],

    /**
     * Languages validation (at least one required)
     */
    languages: (): ValidationRule[] => [
      (v) =>
        (Array.isArray(v) && v.length > 0) ||
        t('categories.validation.languagesRequired'),
    ],

    /**
     * Cron expression validation
     */
    cronExpression: (): ValidationRule[] => [
      (v) => {
        if (!v) return true // Optional
        if (typeof v !== 'string') return t('categories.validation.cronInvalid')

        // 5-field cron: minute hour day month weekday
        // 6-field cron: second minute hour day month weekday
        const cronRegex5 =
          /^(\*|([0-9]|[1-5][0-9])|\*\/([0-9]|[1-5][0-9]))\s+(\*|([0-9]|1[0-9]|2[0-3])|\*\/([0-9]|1[0-9]|2[0-3]))\s+(\*|([1-9]|[12][0-9]|3[01])|\*\/([1-9]|[12][0-9]|3[01]))\s+(\*|([1-9]|1[0-2])|\*\/([1-9]|1[0-2]))\s+(\*|[0-6]|\*\/[0-6])$/
        const cronRegex6 =
          /^(\*|([0-9]|[1-5][0-9])|\*\/([0-9]|[1-5][0-9]))\s+(\*|([0-9]|[1-5][0-9])|\*\/([0-9]|[1-5][0-9]))\s+(\*|([0-9]|1[0-9]|2[0-3])|\*\/([0-9]|1[0-9]|2[0-3]))\s+(\*|([1-9]|[12][0-9]|3[01])|\*\/([1-9]|[12][0-9]|3[01]))\s+(\*|([1-9]|1[0-2])|\*\/([1-9]|1[0-2]))\s+(\*|[0-6]|\*\/[0-6])$/

        const parts = v.trim().split(/\s+/)
        if (parts.length !== 5 && parts.length !== 6) {
          return t('categories.validation.cronFieldCount')
        }

        // Simplified validation - just check if it looks like a cron
        const isValid = cronRegex5.test(v) || cronRegex6.test(v)
        if (!isValid) {
          // More lenient check for common patterns
          const laxCronRegex = /^[\d*,/-]+(\s+[\d*,/-]+){4,5}$/
          if (!laxCronRegex.test(v)) {
            return t('categories.validation.cronInvalid')
          }
        }

        return true
      },
    ],

    /**
     * Regex pattern validation
     */
    regexPattern: (fieldName: string): ValidationRule => (value) => {
      if (!value) return true // Optional
      if (typeof value !== 'string') return true

      try {
        new RegExp(value)
        return true
      } catch {
        return t('categories.validation.regexInvalid', { field: fieldName })
      }
    },

    /**
     * Regex patterns array validation
     */
    regexPatterns: (fieldName: string): ValidationRule => (value) => {
      if (!value) return true
      if (!Array.isArray(value)) return true

      for (const pattern of value) {
        if (typeof pattern !== 'string') continue
        try {
          new RegExp(pattern)
        } catch {
          return t('categories.validation.regexPatternInvalid', {
            field: fieldName,
            pattern,
          })
        }
      }

      return true
    },

    /**
     * URL pattern validation (must be valid regex)
     */
    urlPatterns: (): ValidationRule[] => [
      (v) => {
        if (!v) return true
        if (!Array.isArray(v)) return true

        for (const pattern of v) {
          if (typeof pattern !== 'string') continue
          try {
            new RegExp(pattern)
          } catch {
            return t('categories.validation.urlPatternInvalid', { pattern })
          }
        }
        return true
      },
    ],

    /**
     * Extraction prompt validation (max 10000 chars)
     */
    extractionPrompt: (): ValidationRule[] => [
      (v) => {
        if (!v) return true
        if (typeof v !== 'string') return true
        if (v.length > 10000) {
          return t('categories.validation.promptTooLong')
        }
        return true
      },
    ],

    /**
     * Search terms validation (optional, but if provided must be valid strings)
     */
    searchTerms: (): ValidationRule[] => [
      (v) => {
        if (!v) return true
        if (!Array.isArray(v)) return t('categories.validation.searchTermsInvalid')
        for (const term of v) {
          if (typeof term !== 'string') {
            return t('categories.validation.searchTermsInvalid')
          }
          if (term.length > 255) {
            return t('categories.validation.searchTermTooLong', { term: term.slice(0, 20) + '...' })
          }
        }
        return true
      },
    ],

    /**
     * Document types validation (optional, but if provided must be valid strings)
     */
    documentTypes: (): ValidationRule[] => [
      (v) => {
        if (!v) return true
        if (!Array.isArray(v)) return t('categories.validation.documentTypesInvalid')
        for (const docType of v) {
          if (typeof docType !== 'string') {
            return t('categories.validation.documentTypesInvalid')
          }
          // Allow any string, just validate it's not empty
          if (!docType.trim()) {
            return t('categories.validation.documentTypeEmpty')
          }
        }
        return true
      },
    ],

    /**
     * Extraction handler validation (must be 'default' or 'event')
     */
    extractionHandler: (): ValidationRule[] => [
      (v) => {
        if (!v) return true // Uses default
        if (v !== 'default' && v !== 'event') {
          return t('categories.validation.extractionHandlerInvalid')
        }
        return true
      },
    ],

    /**
     * Target entity type ID validation (optional UUID)
     */
    targetEntityTypeId: (): ValidationRule[] => [
      (v) => {
        if (!v) return true // Optional
        if (typeof v !== 'string') return t('categories.validation.targetEntityTypeInvalid')
        // Basic UUID format check
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
        if (!uuidRegex.test(v)) {
          return t('categories.validation.targetEntityTypeInvalid')
        }
        return true
      },
    ],
  }
}

/**
 * Validate category form data
 */
export function validateCategoryForm(
  formData: {
    name?: string
    purpose?: string
    languages?: string[]
    schedule_cron?: string
    url_include_patterns?: string[]
    url_exclude_patterns?: string[]
    ai_extraction_prompt?: string
  },
  t: Composer['t']
): { valid: boolean; errors: Record<string, string> } {
  const errors: Record<string, string> = {}
  const rules = createCategoryValidationRules(t)

  // Name validation
  if (!formData.name?.trim()) {
    errors.name = t('categories.validation.nameRequired')
  } else if (formData.name.length > 255) {
    errors.name = t('categories.validation.nameMaxLength')
  }

  // Purpose validation
  if (!formData.purpose?.trim()) {
    errors.purpose = t('categories.validation.purposeRequired')
  }

  // Languages validation
  if (!formData.languages?.length) {
    errors.languages = t('categories.validation.languagesRequired')
  }

  // Cron validation
  if (formData.schedule_cron) {
    const cronRules = rules.cronExpression()
    for (const rule of cronRules) {
      const result = rule(formData.schedule_cron)
      if (typeof result === 'string') {
        errors.schedule_cron = result
        break
      }
    }
  }

  // URL patterns validation
  const patternsRule = rules.regexPatterns('URL Include Patterns')
  const includeResult = patternsRule(formData.url_include_patterns)
  if (typeof includeResult === 'string') {
    errors.url_include_patterns = includeResult
  }

  const excludeResult = patternsRule(formData.url_exclude_patterns)
  if (typeof excludeResult === 'string') {
    errors.url_exclude_patterns = excludeResult
  }

  // Prompt validation
  if (
    formData.ai_extraction_prompt &&
    formData.ai_extraction_prompt.length > 10000
  ) {
    errors.ai_extraction_prompt = t('categories.validation.promptTooLong')
  }

  return {
    valid: Object.keys(errors).length === 0,
    errors,
  }
}

/**
 * Composable for category form validation
 */
export function useCategoryValidation(t: Composer['t']) {
  const rules = createCategoryValidationRules(t)

  return {
    rules,
    validate: (formData: Parameters<typeof validateCategoryForm>[0]) =>
      validateCategoryForm(formData, t),
  }
}

export default useCategoryValidation
