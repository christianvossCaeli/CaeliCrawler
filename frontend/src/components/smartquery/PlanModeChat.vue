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
          <p class="text-body-1 text-medium-emphasis mb-6 mx-auto max-width-content">
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
            <!-- AI Provider Badge for assistant messages -->
            <AiProviderBadge
              v-if="message.role === 'assistant' && !message.isStreaming"
              purpose="plan_mode"
              compact
              variant="text"
              class="mt-2"
            />
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
      <SummarySuggestionCard
        v-if="summarySuggestion"
        :prompt="generatedPrompt?.prompt || getLastQuery()"
        @save="$emit('save-as-summary', $event)"
        @dismiss="dismissSummarySuggestion"
      />

      <!-- Generated Prompt Card -->
      <GeneratedPromptCard
        v-if="generatedPrompt"
        ref="generatedPromptRef"
        :prompt="generatedPrompt"
        :validating="validating"
        :validation-result="validationResult"
        @validate="(prompt, mode) => $emit('validate', prompt, mode)"
        @adopt="(prompt, mode) => $emit('adopt-prompt', prompt, mode)"
      />
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
import { escapeHtml, DOMPURIFY_CONFIG } from '@/utils/messageFormatting'
import AiProviderBadge from '@/components/common/AiProviderBadge.vue'
import GeneratedPromptCard from './GeneratedPromptCard.vue'
import SummarySuggestionCard from './SummarySuggestionCard.vue'

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
const { t } = useI18n()
const conversationRef = ref<HTMLElement | null>(null)
const generatedPromptRef = ref<InstanceType<typeof GeneratedPromptCard> | null>(null)

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

// Use centralized DOMPurify config from messageFormatting.ts
// DOMPURIFY_CONFIG.MARKDOWN provides consistent security settings

// Add DOMPurify hook to enforce noopener noreferrer on all links
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank')
    node.setAttribute('rel', 'noopener noreferrer')
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

// Format message content (supports markdown with DOMPurify sanitization)
function formatMessage(content: string): string {
  if (!content) return ''

  try {
    // Remove summary suggestion blocks - they're shown as a separate card
    const cleanedContent = content.replace(/\[SUMMARY_SUGGESTION\][\s\S]*?\[\/SUMMARY_SUGGESTION\]/g, '')

    // Parse markdown to HTML
    const html = marked.parse(cleanedContent) as string

    // Sanitize with DOMPurify - hook handles link security attributes
    return DOMPurify.sanitize(html, DOMPURIFY_CONFIG.MARKDOWN)
  } catch (error) {
    logger.error('Markdown parsing failed:', error)
    // Fallback: escape HTML and convert newlines to <br>
    return escapeHtml(content).replace(/\n/g, '<br>')
  }
}

// Optimized auto-scroll with smooth behavior and reduced motion support
const prefersReducedMotion = ref(false)

// Store mediaQuery reference for cleanup
let mediaQuery: MediaQueryList | null = null
function handleReducedMotionChange(e: MediaQueryListEvent) {
  prefersReducedMotion.value = e.matches
}

// Check for reduced motion preference
if (typeof window !== 'undefined') {
  mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
  prefersReducedMotion.value = mediaQuery.matches
  mediaQuery.addEventListener('change', handleReducedMotionChange)
}

// Auto-scroll to bottom when new messages arrive and announce to screen readers
watch(
  () => props.conversation.length,
  async (newLength, oldLength) => {
    // Clear messageRefs when conversation is reset or trimmed
    if (newLength < oldLength || newLength === 0) {
      messageRefs.value.clear()
    }

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
      generatedPromptRef.value?.focus?.()
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
  // Clean up mediaQuery listener to prevent memory leak
  if (mediaQuery) {
    mediaQuery.removeEventListener('change', handleReducedMotionChange)
    mediaQuery = null
  }
  // Clean up messageRefs Map
  messageRefs.value.clear()
})
</script>

<style scoped>
@import './styles/plan-mode-chat.css';
</style>
