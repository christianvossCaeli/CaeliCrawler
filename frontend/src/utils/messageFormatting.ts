/**
 * Message Formatting Utilities
 *
 * Shared utilities for formatting chat messages, escaping HTML,
 * and time formatting in chat interfaces.
 */
import DOMPurify from 'dompurify'

/**
 * Escapes HTML special characters to prevent XSS
 */
export function escapeHtml(text: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  }
  return text.replace(/[&<>"']/g, (c) => map[c])
}

/**
 * Formats a message with markdown-like syntax and sanitizes for XSS
 *
 * Supported formatting:
 * - **bold** -> <strong>bold</strong>
 * - `code` -> <code>code</code>
 * - Newlines -> <br>
 * - [[type:id:name]] -> Entity link span
 */
export function formatMessage(content: string): string {
  // 1. First escape HTML to prevent XSS
  let formatted = escapeHtml(content)

  // 2. Apply safe formatting patterns
  formatted = formatted
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
    .replace(/\[\[(\w+):([^:]+):([^\]]+)\]\]/g, '<span class="entity-link">$3</span>')

  // 3. Final sanitization with DOMPurify for defense-in-depth
  return DOMPurify.sanitize(formatted, {
    ALLOWED_TAGS: ['strong', 'code', 'br', 'span'],
    ALLOWED_ATTR: ['class'],
  })
}

/**
 * Formats a timestamp for display in chat messages
 */
export function formatMessageTime(
  date: Date,
  locale: string = 'de',
): string {
  const resolvedLocale = locale === 'de' ? 'de-DE' : 'en-US'
  return new Date(date).toLocaleTimeString(resolvedLocale, {
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Formats a date relative to now (e.g., "2 minutes ago", "yesterday")
 */
export function formatRelativeTime(
  date: Date,
  locale: string = 'de',
): string {
  const now = new Date()
  const diff = now.getTime() - new Date(date).getTime()
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  const translations = {
    de: {
      justNow: 'Gerade eben',
      minutesAgo: (n: number) => `Vor ${n} Minute${n === 1 ? '' : 'n'}`,
      hoursAgo: (n: number) => `Vor ${n} Stunde${n === 1 ? '' : 'n'}`,
      yesterday: 'Gestern',
      daysAgo: (n: number) => `Vor ${n} Tagen`,
    },
    en: {
      justNow: 'Just now',
      minutesAgo: (n: number) => `${n} minute${n === 1 ? '' : 's'} ago`,
      hoursAgo: (n: number) => `${n} hour${n === 1 ? '' : 's'} ago`,
      yesterday: 'Yesterday',
      daysAgo: (n: number) => `${n} days ago`,
    },
  }

  const t = translations[locale as keyof typeof translations] || translations.en

  if (seconds < 60) return t.justNow
  if (minutes < 60) return t.minutesAgo(minutes)
  if (hours < 24) return t.hoursAgo(hours)
  if (days === 1) return t.yesterday
  if (days < 7) return t.daysAgo(days)

  return formatMessageTime(date, locale)
}
