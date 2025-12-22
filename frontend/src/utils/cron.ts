/**
 * Utility functions for cron expression handling
 * Uses cronstrue for human-readable descriptions
 */

import cronstrue from 'cronstrue'
import 'cronstrue/locales/de'

const CRON_FIELD_PATTERN = /^[A-Za-z0-9*\/,\-?#]+$/

function splitCronExpression(
  cronExpression: string
): { parts: string[]; hasSeconds: boolean } | null {
  const trimmed = cronExpression.trim()
  if (!trimmed) return null
  const parts = trimmed.split(/\s+/)
  if (parts.length !== 5 && parts.length !== 6) return null
  return { parts, hasSeconds: parts.length === 6 }
}

function parseNumber(value: string): number | null {
  return /^\d+$/.test(value) ? parseInt(value, 10) : null
}

function parseStep(value: string): number | null {
  if (!/^\*\/\d+$/.test(value)) return null
  const step = parseInt(value.slice(2), 10)
  return Number.isFinite(step) && step > 0 ? step : null
}

/**
 * Parse a cron expression and return the next run time as a formatted string
 * @param cronExpression - Cron expression (5 fields, optional leading seconds)
 * @param locale - Locale for formatting (default: 'de')
 * @returns Formatted next run time or empty string if invalid
 */
export function cronToNextRun(cronExpression: string, locale: string = 'de'): string {
  try {
    const parsed = splitCronExpression(cronExpression)
    if (!parsed) return ''

    const { parts, hasSeconds } = parsed
    const [second, minute, hour, dayOfMonth, month, dayOfWeek] = hasSeconds
      ? parts
      : ['0', ...parts]

    const secondStep = parseStep(second)
    const minuteStep = parseStep(minute)
    const hourStep = parseStep(hour)

    const secondNum = parseNumber(second)
    const minuteNum = parseNumber(minute)
    const hourNum = parseNumber(hour)
    const dayOfMonthNum = parseNumber(dayOfMonth)
    const dayOfWeekNum = parseNumber(dayOfWeek)

    const now = new Date()
    let next = new Date(now)

    if (
      secondStep &&
      minute === '*' &&
      hour === '*' &&
      dayOfMonth === '*' &&
      month === '*' &&
      dayOfWeek === '*'
    ) {
      const stepMs = secondStep * 1000
      const nextMs = Math.ceil((now.getTime() + 1) / stepMs) * stepMs
      next = new Date(nextMs)
    } else if (
      minuteStep &&
      hour === '*' &&
      dayOfMonth === '*' &&
      month === '*' &&
      dayOfWeek === '*'
    ) {
      const step = minuteStep
      const secondValue = secondNum ?? 0
      next = new Date(now)
      next.setSeconds(secondValue, 0)
      const currentMinute = next.getMinutes()
      const nextMinute = Math.ceil((currentMinute + 1) / step) * step
      next.setMinutes(nextMinute, secondValue, 0)
      if (next <= now) {
        next.setMinutes(nextMinute + step, secondValue, 0)
      }
    } else if (
      hourStep &&
      dayOfMonth === '*' &&
      month === '*' &&
      dayOfWeek === '*'
    ) {
      const step = hourStep
      const minuteValue = minuteNum ?? 0
      const secondValue = secondNum ?? 0
      next = new Date(now)
      next.setMinutes(minuteValue, secondValue, 0)
      const currentHour = next.getHours()
      const nextHour = Math.ceil((currentHour + 1) / step) * step
      next.setHours(nextHour % 24, minuteValue, secondValue, 0)
      if (next <= now) {
        const bumpedHour = nextHour + step
        next.setHours(bumpedHour % 24, minuteValue, secondValue, 0)
        if (bumpedHour >= 24 || next <= now) {
          next.setDate(next.getDate() + 1)
        }
      }
    } else if (
      hourNum !== null &&
      minuteNum !== null &&
      dayOfMonth === '*' &&
      month === '*' &&
      dayOfWeek === '*'
    ) {
      const secondValue = secondNum ?? 0
      next.setHours(hourNum, minuteNum, secondValue, 0)
      if (next <= now) {
        next.setDate(next.getDate() + 1)
      }
    } else if (
      dayOfWeekNum !== null &&
      dayOfMonth === '*' &&
      month === '*' &&
      hourNum !== null &&
      minuteNum !== null
    ) {
      const secondValue = secondNum ?? 0
      next.setHours(hourNum, minuteNum, secondValue, 0)
      let daysToAdd = dayOfWeekNum - next.getDay()
      if (daysToAdd < 0) daysToAdd += 7
      if (daysToAdd === 0 && next <= now) daysToAdd = 7
      next.setDate(next.getDate() + daysToAdd)
    } else if (
      dayOfMonthNum !== null &&
      month === '*' &&
      dayOfWeek === '*' &&
      hourNum !== null &&
      minuteNum !== null
    ) {
      const secondValue = secondNum ?? 0
      next.setDate(dayOfMonthNum)
      next.setHours(hourNum, minuteNum, secondValue, 0)
      if (next <= now) {
        next.setMonth(next.getMonth() + 1)
      }
    } else {
      return ''
    }

    return next.toLocaleString(locale === 'de' ? 'de-DE' : 'en-US', {
      weekday: 'short',
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      ...(hasSeconds ? { second: '2-digit' } : {}),
    })
  } catch {
    return ''
  }
}

/**
 * Human-readable description of a cron expression using cronstrue
 * @param cronExpression - Cron expression (5 fields, optional leading seconds)
 * @param locale - Locale for output ('de' or 'en')
 * @returns Human-readable description or the original expression if invalid
 */
export function cronToHumanReadable(cronExpression: string, locale: string = 'de'): string {
  const parsed = splitCronExpression(cronExpression)
  if (!parsed) return cronExpression
  try {
    return cronstrue.toString(cronExpression, {
      locale: locale === 'de' ? 'de' : 'en',
      use24HourTimeFormat: true,
      verbose: false,
      useSeconds: parsed.hasSeconds,
      throwExceptionOnParseError: true,
    })
  } catch {
    // Fallback for invalid expressions
    return cronExpression
  }
}

/**
 * Validate a cron expression
 * @param cronExpression - Cron expression (5 fields, optional leading seconds)
 * @returns true if valid, false otherwise
 */
export function isValidCron(cronExpression: string): boolean {
  const parsed = splitCronExpression(cronExpression)
  if (!parsed) return false
  return parsed.parts.every((part) => CRON_FIELD_PATTERN.test(part))
}

/**
 * Get a formatted preview of when a cron job will run
 * @param cronExpression - Cron expression (5 fields, optional leading seconds)
 * @param locale - Locale for output
 * @returns Object with human-readable description and next run time
 */
export function getCronPreview(
  cronExpression: string,
  locale: string = 'de'
): { description: string; nextRun: string; isValid: boolean } {
  const isValid = isValidCron(cronExpression)

  if (!isValid) {
    return {
      description: locale === 'de' ? 'Ungültiger Cron-Ausdruck' : 'Invalid cron expression',
      nextRun: '',
      isValid: false,
    }
  }

  return {
    description: cronToHumanReadable(cronExpression, locale),
    nextRun: cronToNextRun(cronExpression, locale),
    isValid: true,
  }
}
