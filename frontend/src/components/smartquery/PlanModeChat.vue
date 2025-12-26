<template>
  <div
    class="plan-mode-chat"
    role="region"
    :aria-label="t('smartQueryView.plan.ariaLabel', 'Plan Mode Chat')"
  >
    <!-- Screen reader announcements (ARIA live region) -->
    <div
      ref="liveRegionRef"
      class="sr-only"
      aria-live="polite"
      aria-atomic="false"
    >
      {{ liveAnnouncement }}
    </div>

    <!-- Welcome State -->
    <div v-if="conversation.length === 0 && !loading" class="welcome-section">
      <v-card variant="flat" class="welcome-card">
        <v-card-text class="text-center py-8">
          <v-avatar color="info" size="64" class="mb-4" aria-hidden="true">
            <v-icon size="32">mdi-lightbulb-on</v-icon>
          </v-avatar>
          <h2 id="plan-mode-title" class="text-h5 mb-2">{{ t('smartQueryView.plan.welcome.title') }}</h2>
          <p class="text-body-1 text-medium-emphasis mb-6 mx-auto" style="max-width: 500px">
            {{ t('smartQueryView.plan.welcome.description') }}
          </p>

          <!-- Starter suggestions -->
          <nav class="starter-suggestions" aria-labelledby="starter-suggestions-label">
            <div id="starter-suggestions-label" class="text-caption text-medium-emphasis mb-3">
              {{ t('smartQueryView.plan.starterSuggestions') }}
            </div>
            <div class="d-flex flex-wrap justify-center ga-2" role="group">
              <v-chip
                v-for="suggestion in starterSuggestions"
                :key="suggestion"
                variant="outlined"
                color="info"
                :disabled="loading"
                class="starter-chip"
                tabindex="0"
                role="button"
                :aria-label="t('smartQueryView.plan.suggestionAriaLabel', { suggestion }, `Vorschlag: ${suggestion}`)"
                @click="$emit('send', suggestion)"
                @keydown.enter="$emit('send', suggestion)"
                @keydown.space.prevent="$emit('send', suggestion)"
              >
                {{ suggestion }}
              </v-chip>
            </div>
          </nav>
        </v-card-text>
      </v-card>
    </div>

    <!-- Conversation -->
    <div
      v-else
      ref="conversationRef"
      class="conversation-container"
      role="log"
      aria-live="polite"
      aria-relevant="additions"
      :aria-label="t('smartQueryView.plan.conversationAriaLabel', 'Konversationsverlauf')"
      tabindex="0"
    >
      <div
        v-for="(message, index) in conversation"
        :key="index"
        :ref="el => setMessageRef(el, index)"
        class="message-wrapper"
        :class="{ 'message-wrapper--user': message.role === 'user' }"
        role="article"
        :aria-label="getMessageAriaLabel(message, index)"
      >
        <div class="message" :class="[`message--${message.role}`]">
          <v-avatar
            :color="message.role === 'user' ? 'primary' : 'info'"
            size="32"
            class="message-avatar"
            aria-hidden="true"
          >
            <v-icon size="18">{{ message.role === 'user' ? 'mdi-account' : 'mdi-lightbulb-on' }}</v-icon>
          </v-avatar>
          <div class="message-content">
            <!-- eslint-disable-next-line vue/no-v-html -- Content is sanitized via DOMPurify in formatMessage -->
            <div class="message-text" v-html="formatMessage(message.content)"></div>
            <!-- Streaming cursor indicator -->
            <span
              v-if="message.isStreaming"
              class="streaming-cursor"
              aria-hidden="true"
              role="presentation"
            >▋</span>
          </div>
        </div>
      </div>

      <!-- Loading indicator -->
      <div
        v-if="loading"
        class="message-wrapper"
        role="status"
        :aria-label="t('smartQueryView.plan.thinking', 'Assistent denkt nach...')"
      >
        <div class="message message--assistant">
          <v-avatar color="info" size="32" class="message-avatar" aria-hidden="true">
            <v-icon size="18">mdi-lightbulb-on</v-icon>
          </v-avatar>
          <div class="message-content">
            <div class="thinking-indicator" aria-hidden="true">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </div>
            <span class="sr-only">{{ t('smartQueryView.plan.thinking', 'Assistent denkt nach...') }}</span>
          </div>
        </div>
      </div>

      <!-- Summary Suggestion Card -->
      <div
        v-if="summarySuggestion"
        class="summary-suggestion-section"
        role="region"
        :aria-label="t('summaries.createDialog.title', 'Als Zusammenfassung speichern')"
      >
        <v-card
          class="summary-suggestion-card"
          color="info"
          variant="tonal"
        >
          <v-card-title class="d-flex align-center">
            <v-icon start aria-hidden="true">mdi-view-dashboard-variant</v-icon>
            {{ t('summaries.dashboard.suggestion', 'Als Zusammenfassung speichern?') }}
          </v-card-title>
          <v-card-text>
            <p class="text-body-2 mb-4">
              {{ t('summaries.dashboard.suggestionHint', 'Diese Abfrage kann als automatisch aktualisierte Zusammenfassung gespeichert werden.') }}
            </p>
            <div class="d-flex ga-2">
              <v-btn
                color="info"
                variant="elevated"
                @click="$emit('save-as-summary', generatedPrompt?.prompt || getLastQuery())"
              >
                <v-icon start>mdi-content-save</v-icon>
                {{ t('summaries.createNew', 'Als Zusammenfassung speichern') }}
              </v-btn>
              <v-btn
                variant="text"
                @click="dismissSummarySuggestion"
              >
                {{ t('common.dismiss', 'Später') }}
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </div>

      <!-- Generated Prompt Card -->
      <div
        v-if="generatedPrompt"
        class="generated-prompt-section"
        role="region"
        :aria-label="t('smartQueryView.plan.generatedPromptAriaLabel', 'Generierter Prompt')"
      >
        <v-card
          ref="generatedPromptRef"
          class="generated-prompt-card"
          color="success"
          variant="tonal"
          tabindex="-1"
        >
          <v-card-title class="d-flex align-center">
            <v-icon start aria-hidden="true">mdi-check-circle</v-icon>
            {{ t('smartQueryView.plan.generatedPrompt') }}
          </v-card-title>
          <v-card-text>
            <v-card variant="outlined" class="prompt-preview mb-4">
              <v-card-text class="text-body-1 font-weight-medium">
                {{ generatedPrompt.prompt }}
              </v-card-text>
            </v-card>

            <!-- Validation Result Display -->
            <v-expand-transition>
              <div v-if="validationResult" class="validation-result mb-4">
                <v-alert
                  :type="validationResult.valid ? 'success' : 'warning'"
                  variant="tonal"
                  density="compact"
                  class="mb-2"
                >
                  <template #title>
                    {{ validationResult.valid
                      ? t('smartQueryView.plan.validation.valid', 'Prompt ist gültig')
                      : t('smartQueryView.plan.validation.invalid', 'Prompt hat Probleme')
                    }}
                  </template>
                  <template v-if="validationResult.preview" #text>
                    <strong>{{ t('smartQueryView.plan.validation.preview', 'Vorschau') }}:</strong>
                    {{ validationResult.preview }}
                  </template>
                </v-alert>

                <!-- Warnings -->
                <v-alert
                  v-for="(warning, idx) in validationResult.warnings"
                  :key="idx"
                  type="warning"
                  variant="text"
                  density="compact"
                  class="mb-1"
                >
                  {{ warning }}
                </v-alert>
              </div>
            </v-expand-transition>

            <div class="d-flex ga-2 flex-wrap" role="group" :aria-label="t('smartQueryView.plan.adoptActionsAriaLabel', 'Prompt-Aktionen')">
              <!-- Test Button -->
              <v-btn
                variant="outlined"
                color="info"
                :loading="validating"
                :aria-label="t('smartQueryView.plan.testPromptAriaLabel', 'Prompt testen')"
                @click="$emit('validate', generatedPrompt.prompt, generatedPrompt.suggested_mode || 'read')"
              >
                <v-icon start aria-hidden="true">mdi-test-tube</v-icon>
                {{ t('smartQueryView.plan.testPrompt', 'Testen') }}
              </v-btn>

              <v-btn
                v-if="generatedPrompt.suggested_mode === 'read' || !generatedPrompt.suggested_mode"
                color="primary"
                variant="elevated"
                :aria-label="t('smartQueryView.plan.adoptToReadAriaLabel', 'Prompt im Lese-Modus ausführen')"
                @click="$emit('adopt-prompt', generatedPrompt.prompt, 'read')"
              >
                <v-icon start aria-hidden="true">mdi-magnify</v-icon>
                {{ t('smartQueryView.plan.adoptToRead') }}
              </v-btn>
              <v-btn
                v-if="generatedPrompt.suggested_mode === 'write' || !generatedPrompt.suggested_mode"
                color="warning"
                variant="elevated"
                :aria-label="t('smartQueryView.plan.adoptToWriteAriaLabel', 'Prompt im Schreib-Modus ausführen')"
                @click="$emit('adopt-prompt', generatedPrompt.prompt, 'write')"
              >
                <v-icon start aria-hidden="true">mdi-pencil-plus</v-icon>
                {{ t('smartQueryView.plan.adoptToWrite') }}
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </div>
    </div>

    <!-- Reset button -->
    <div v-if="conversation.length > 0" class="reset-section">
      <v-btn
        variant="text"
        size="small"
        color="medium-emphasis"
        :aria-label="t('smartQueryView.plan.newConversationAriaLabel', 'Neue Konversation starten')"
        @click="$emit('reset')"
      >
        <v-icon start size="16" aria-hidden="true">mdi-refresh</v-icon>
        {{ t('smartQueryView.plan.newConversation') }}
      </v-btn>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, computed, onMounted, onUnmounted, type ComponentPublicInstance } from 'vue'
import { useI18n } from 'vue-i18n'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { useLogger } from '@/composables/useLogger'

const props = withDefaults(defineProps<{
  conversation?: Message[]
  loading?: boolean
  generatedPrompt?: GeneratedPrompt | null
  validating?: boolean
  validationResult?: ValidationResult | null
}>(), {
  conversation: () => [],
  loading: false
})

defineEmits<{
  (e: 'send', message: string): void
  (e: 'adopt-prompt', prompt: string, mode: 'read' | 'write'): void
  (e: 'validate', prompt: string, mode: 'read' | 'write'): void
  (e: 'reset'): void
  (e: 'save-as-summary', prompt: string): void
}>()

const logger = useLogger('PlanModeChat')

interface Message {
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
}

interface GeneratedPrompt {
  prompt: string
  suggested_mode?: 'read' | 'write'
}

interface ValidationResult {
  valid: boolean
  mode: string
  interpretation: Record<string, unknown> | null
  preview: string | null
  warnings: string[]
  original_prompt: string
}

const { t } = useI18n()
const conversationRef = ref<HTMLElement | null>(null)
const generatedPromptRef = ref<HTMLElement | null>(null)

// Summary suggestion state
const summarySuggestionDismissed = ref(false)

// Detect if any message contains a summary suggestion
const summarySuggestion = computed(() => {
  if (summarySuggestionDismissed.value) return false
  return props.conversation.some(msg =>
    msg.role === 'assistant' &&
    msg.content.includes('[SUMMARY_SUGGESTION]')
  )
})

// Get the last user query for summary creation
function getLastQuery(): string {
  const userMessages = props.conversation.filter(m => m.role === 'user')
  return userMessages.length > 0 ? userMessages[userMessages.length - 1].content : ''
}

// Dismiss summary suggestion
function dismissSummarySuggestion() {
  summarySuggestionDismissed.value = true
}

// ARIA live region announcement
const liveAnnouncement = ref('')

// Message element refs for focus management
const messageRefs = ref<Map<number, HTMLElement>>(new Map())

function setMessageRef(el: Element | ComponentPublicInstance | null, index: number) {
  if (el && el instanceof HTMLElement) {
    messageRefs.value.set(index, el)
  }
}

// Generate accessible label for messages
function getMessageAriaLabel(message: Message, index: number): string {
  const role = message.role === 'user'
    ? t('smartQueryView.plan.userMessage', 'Du')
    : t('smartQueryView.plan.assistantMessage', 'Assistent')

  const streaming = message.isStreaming
    ? ` (${t('smartQueryView.plan.streaming', 'wird gerade geschrieben')})`
    : ''

  // Truncate long messages for screen reader
  const contentPreview = message.content.length > 100
    ? message.content.substring(0, 100) + '...'
    : message.content

  return `${t('smartQueryView.plan.messageNumber', { number: index + 1 }, `Nachricht ${index + 1}`)}: ${role}${streaming}. ${contentPreview}`
}

// Announce changes to screen readers
function announce(message: string) {
  liveAnnouncement.value = ''
  // Small delay to ensure the change is detected
  requestAnimationFrame(() => {
    liveAnnouncement.value = message
  })
}

// Keyboard navigation handler
function handleKeyboardNavigation(event: KeyboardEvent) {
  // Allow Escape to move focus to the input (handled by parent)
  if (event.key === 'Escape') {
    return
  }

  // Arrow key navigation within conversation
  if (conversationRef.value && document.activeElement === conversationRef.value) {
    const messages = Array.from(messageRefs.value.values())
    if (messages.length === 0) return

    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      const currentIdx = messages.findIndex(el => el === document.activeElement)
      let newIdx: number

      if (event.key === 'ArrowDown') {
        newIdx = currentIdx < messages.length - 1 ? currentIdx + 1 : 0
      } else {
        newIdx = currentIdx > 0 ? currentIdx - 1 : messages.length - 1
      }

      messages[newIdx]?.focus()
    }
  }
}

// Starter suggestions for the user
const starterSuggestions = computed(() => [
  t('smartQueryView.plan.suggestions.findEntities'),
  t('smartQueryView.plan.suggestions.createData'),
  t('smartQueryView.plan.suggestions.queryRelations'),
  t('smartQueryView.plan.suggestions.explainSyntax'),
])

// Configure DOMPurify for safe HTML output with strict security
// Using object literal to avoid readonly array type issues
const purifyConfig = {
  ALLOWED_TAGS: [
    'p', 'br', 'strong', 'em', 'b', 'i', 'u', 's', 'del',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li',
    'blockquote', 'pre', 'code',
    'a', 'span', 'div',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'hr'
  ] as string[],
  ALLOWED_ATTR: ['href', 'target', 'rel', 'class', 'id'] as string[],
  ALLOW_DATA_ATTR: false,
  FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'form', 'input', 'style'] as string[],
  FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 'onblur', 'onchange', 'onsubmit'] as string[],
  // Only allow safe URL protocols - prevents javascript: and data: URLs
  ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto|tel):|[^a-z]|[a-z+.-]+(?:[^a-z+.-:]|$))/i,
}

// Add DOMPurify hook to enforce noopener noreferrer on all links
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank')
    node.setAttribute('rel', 'noopener noreferrer')
    // Double-check href doesn't contain javascript:
    const href = node.getAttribute('href') || ''
    if (href.toLowerCase().startsWith('javascript:') || href.toLowerCase().startsWith('data:')) {
      node.removeAttribute('href')
    }
  }
})

// Configure marked once at module level for performance
marked.setOptions({
  breaks: true,
  gfm: true,
  async: false,
})

// HTML escape function for fallback
function escapeHtml(text: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }
  return text.replace(/[&<>"']/g, (c) => map[c])
}

// Format message content (supports markdown with DOMPurify sanitization)
function formatMessage(content: string): string {
  if (!content) return ''

  try {
    // Remove summary suggestion blocks - they're shown as a separate card
    const cleanedContent = content.replace(/\[SUMMARY_SUGGESTION\][\s\S]*?\[\/SUMMARY_SUGGESTION\]/g, '')

    // Parse markdown to HTML
    const html = marked.parse(cleanedContent) as string

    // Sanitize with DOMPurify - hook handles link security attributes
    return DOMPurify.sanitize(html, purifyConfig)
  } catch (error) {
    logger.error('Markdown parsing failed:', error)
    // Fallback: escape HTML and convert newlines to <br>
    return escapeHtml(content).replace(/\n/g, '<br>')
  }
}

// Optimized auto-scroll with smooth behavior and reduced motion support
const prefersReducedMotion = ref(false)

// Check for reduced motion preference
if (typeof window !== 'undefined') {
  const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
  prefersReducedMotion.value = mediaQuery.matches
  mediaQuery.addEventListener('change', (e) => {
    prefersReducedMotion.value = e.matches
  })
}

// Auto-scroll to bottom when new messages arrive and announce to screen readers
watch(
  () => props.conversation.length,
  async (newLength, oldLength) => {
    await nextTick()
    if (conversationRef.value) {
      const scrollOptions: ScrollToOptions = {
        top: conversationRef.value.scrollHeight,
        behavior: prefersReducedMotion.value ? 'auto' : 'smooth'
      }
      conversationRef.value.scrollTo(scrollOptions)
    }

    // Announce new messages to screen readers
    if (newLength > oldLength) {
      const lastMessage = props.conversation[newLength - 1]
      if (lastMessage && !lastMessage.isStreaming) {
        const role = lastMessage.role === 'user'
          ? t('smartQueryView.plan.userMessage', 'Du')
          : t('smartQueryView.plan.assistantMessage', 'Assistent')
        announce(t('smartQueryView.plan.newMessage', { role }, `Neue Nachricht von ${role}`))
      }
    }
  }
)

// Announce when loading starts/ends
watch(
  () => props.loading,
  (isLoading) => {
    if (isLoading) {
      announce(t('smartQueryView.plan.thinking', 'Assistent denkt nach...'))
    }
  }
)

// Announce and focus when generated prompt appears
watch(
  () => props.generatedPrompt,
  async (newPrompt) => {
    if (newPrompt) {
      await nextTick()
      announce(t('smartQueryView.plan.promptGenerated', 'Ein fertiger Prompt wurde generiert'))
      // Focus the generated prompt card for keyboard users
      if (generatedPromptRef.value) {
        (generatedPromptRef.value as HTMLElement).focus?.()
      }
    }
  }
)

// Setup keyboard navigation
onMounted(() => {
  if (conversationRef.value) {
    conversationRef.value.addEventListener('keydown', handleKeyboardNavigation)
  }
})

onUnmounted(() => {
  if (conversationRef.value) {
    conversationRef.value.removeEventListener('keydown', handleKeyboardNavigation)
  }
})

</script>

<style scoped>
.plan-mode-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 300px;
}

/* Screen reader only - visually hidden but accessible */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* Welcome Section */
.welcome-section {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.welcome-card {
  max-width: 600px;
  width: 100%;
  background: rgba(var(--v-theme-info), 0.04);
  border: 1px solid rgba(var(--v-theme-info), 0.12);
  border-radius: 16px;
}

.starter-suggestions {
  margin-top: 16px;
}

.starter-chip {
  cursor: pointer;
  transition: all 0.2s ease;
}

.starter-chip:hover {
  transform: translateY(-1px);
  border-color: rgba(var(--v-theme-info), 0.5) !important;
}

/* Conversation Container */
.conversation-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Message Styling */
.message-wrapper {
  display: flex;
  justify-content: flex-start;
  outline: none;
  border-radius: 8px;
  transition: box-shadow 0.2s ease;
}

.message-wrapper:focus {
  box-shadow: 0 0 0 2px rgba(var(--v-theme-primary), 0.5);
}

.message-wrapper:focus-visible {
  box-shadow: 0 0 0 2px rgba(var(--v-theme-primary), 0.5);
}

.message-wrapper--user {
  justify-content: flex-end;
}

/* Conversation container focus styles */
.conversation-container:focus {
  outline: 2px solid rgba(var(--v-theme-primary), 0.3);
  outline-offset: 2px;
}

.conversation-container:focus-visible {
  outline: 2px solid rgba(var(--v-theme-primary), 0.3);
  outline-offset: 2px;
}

.message {
  display: flex;
  gap: 12px;
  max-width: 85%;
}

.message--user {
  flex-direction: row-reverse;
}

.message--user .message-content {
  background: rgba(var(--v-theme-primary), 0.1);
  border-color: rgba(var(--v-theme-primary), 0.2);
}

.message--assistant .message-content {
  background: rgba(var(--v-theme-info), 0.05);
  border-color: rgba(var(--v-theme-info), 0.1);
}

.message-avatar {
  flex-shrink: 0;
}

.message-content {
  padding: 12px 16px;
  border-radius: 12px;
  border: 1px solid;
}

.message-text {
  line-height: 1.6;
}

.message-text :deep(p) {
  margin: 0 0 8px;
}

.message-text :deep(p:last-child) {
  margin-bottom: 0;
}

.message-text :deep(code) {
  background: rgba(var(--v-theme-on-surface), 0.08);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.9em;
}

.message-text :deep(pre) {
  background: rgba(var(--v-theme-on-surface), 0.05);
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
}

.message-text :deep(blockquote) {
  border-left: 3px solid rgba(var(--v-theme-info), 0.5);
  padding-left: 12px;
  margin: 8px 0;
  color: rgba(var(--v-theme-on-surface), 0.8);
}

.message-text :deep(ul), .message-text :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

/* Streaming Cursor */
.streaming-cursor {
  display: inline-block;
  color: rgba(var(--v-theme-info), 0.8);
  animation: blink 1s infinite;
  margin-left: 2px;
  font-weight: normal;
}

@keyframes blink {
  0%, 50% {
    opacity: 1;
  }
  51%, 100% {
    opacity: 0;
  }
}

/* Respect reduced motion preference for cursor */
@media (prefers-reduced-motion: reduce) {
  .streaming-cursor {
    animation: none;
    opacity: 0.7;
  }
}

/* Thinking Indicator */
.thinking-indicator {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}

.thinking-indicator .dot {
  width: 8px;
  height: 8px;
  background: rgba(var(--v-theme-info), 0.6);
  border-radius: 50%;
  animation: bounce 1.4s ease-in-out infinite;
  will-change: transform; /* Performance optimization */
}

.thinking-indicator .dot:nth-child(1) {
  animation-delay: 0s;
}

.thinking-indicator .dot:nth-child(2) {
  animation-delay: 0.2s;
}

.thinking-indicator .dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes bounce {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-6px);
  }
}

/* Respect reduced motion preference */
@media (prefers-reduced-motion: reduce) {
  .thinking-indicator .dot {
    animation: none;
    opacity: 0.6;
  }

  .thinking-indicator .dot:nth-child(2) {
    opacity: 0.8;
  }

  .thinking-indicator .dot:nth-child(3) {
    opacity: 1;
  }
}

/* Summary Suggestion Section */
.summary-suggestion-section {
  padding: 0 16px;
  margin-bottom: 16px;
}

.summary-suggestion-card {
  border-radius: 12px !important;
}

/* Generated Prompt Section */
.generated-prompt-section {
  padding: 0 16px;
}

.generated-prompt-card {
  border-radius: 12px !important;
}

.prompt-preview {
  background: rgba(var(--v-theme-surface), 0.9) !important;
}

/* Reset Section */
.reset-section {
  padding: 8px 16px;
  text-align: center;
  border-top: 1px solid rgba(var(--v-theme-on-surface), 0.08);
}

/* Mobile Responsiveness */
@media (max-width: 600px) {
  .plan-mode-chat {
    min-height: 250px;
  }

  .welcome-section {
    padding: 16px;
  }

  .welcome-card {
    border-radius: 12px;
  }

  .starter-chip {
    font-size: 0.75rem;
  }

  .conversation-container {
    padding: 12px;
    gap: 12px;
  }

  .message {
    max-width: 92%;
  }

  .message-content {
    padding: 10px 12px;
    font-size: 0.875rem;
  }

  .message-avatar {
    width: 28px;
    height: 28px;
  }

  .generated-prompt-section {
    padding: 0 12px;
  }

  .generated-prompt-card .v-card-text {
    padding: 12px;
  }

  .generated-prompt-card .d-flex {
    flex-direction: column;
  }

  .generated-prompt-card .v-btn {
    width: 100%;
  }
}

/* Very small screens */
@media (max-width: 360px) {
  .welcome-card h2 {
    font-size: 1.1rem;
  }

  .starter-suggestions .d-flex {
    flex-direction: column;
    align-items: stretch;
  }

  .starter-chip {
    justify-content: center;
  }
}
</style>
