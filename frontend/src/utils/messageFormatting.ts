/**
 * Message Formatting Utilities
 *
 * Shared utilities for formatting chat messages, escaping HTML,
 * and time formatting in chat interfaces.
 */
import DOMPurify from 'dompurify'

/**
 * Centralized DOMPurify configuration for consistent XSS protection
 *
 * BASIC: For simple text formatting (bold, code, line breaks)
 * EXTENDED: Adds support for entity chips with data attributes
 * MARKDOWN: Full markdown support including links
 */
export const DOMPURIFY_CONFIG = {
  /** Basic config for simple message formatting */
  BASIC: {
    ALLOWED_TAGS: ['strong', 'code', 'br', 'span'],
    ALLOWED_ATTR: ['class'],
  },
  /** Extended config for entity chips with interactive attributes */
  EXTENDED: {
    ALLOWED_TAGS: ['strong', 'code', 'br', 'span'],
    ALLOWED_ATTR: ['class', 'data-type', 'data-slug', 'role', 'tabindex'],
  },
  /** Visualization config - text-only formatting without attributes */
  VISUALIZATION: {
    ALLOWED_TAGS: ['strong', 'em', 'b', 'i', 'br', 'ul', 'li', 'p'],
    ALLOWED_ATTR: [] as string[],
  },
  /** Full markdown config with links, lists and enhanced security */
  MARKDOWN: {
    ALLOWED_TAGS: [
      'p', 'br', 'strong', 'em', 'b', 'i', 'u', 's', 'del',
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'ul', 'ol', 'li',
      'blockquote', 'pre', 'code',
      'a', 'span', 'div',
      'table', 'thead', 'tbody', 'tr', 'th', 'td',
      'hr',
    ],
    ALLOWED_ATTR: ['href', 'target', 'rel', 'class', 'id'],
    ALLOW_DATA_ATTR: false,
    FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'form', 'input', 'style'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 'onblur', 'onchange', 'onsubmit'],
    ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto|tel):|[^a-z]|[a-z+.-]+(?:[^a-z+.-:]|$))/i,
  },
}

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
  return DOMPurify.sanitize(formatted, DOMPURIFY_CONFIG.BASIC)
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
