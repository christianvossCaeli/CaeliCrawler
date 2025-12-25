<template>
  <div
    class="chat-message"
    :class="{
      'chat-message--user': message.role === 'user',
      'chat-message--assistant': message.role === 'assistant',
      'chat-message--error': message.response_type === 'error'
    }"
  >
    <!-- Avatar -->
    <v-avatar
      :color="message.role === 'user' ? 'primary' : 'surface-variant'"
      size="32"
      class="chat-message__avatar"
    >
      <v-icon :color="message.role === 'user' ? 'on-primary' : 'on-surface-variant'" size="small">
        {{ message.role === 'user' ? 'mdi-account' : 'mdi-robot' }}
      </v-icon>
    </v-avatar>

    <!-- Content -->
    <div class="chat-message__content">
      <!-- Text content with markdown-like formatting -->
      <div
        class="chat-message__text"
        v-html="formatMessage(message.content)"
        @click="handleTextClick"
      ></div>

      <!-- Query Results -->
      <div v-if="message.response_type === 'query_result' && message.response_data?.data?.items?.length" class="mt-2">
        <v-chip
          v-for="(item, idx) in message.response_data.data.items.slice(0, 15)"
          :key="idx"
          size="small"
          variant="outlined"
          class="mr-1 mb-1"
          @click="$emit('item-click', item)"
        >
          {{ item.entity_name || item.name || t('entities.entity') }}
        </v-chip>
        <v-chip
          v-if="message.response_data.data.items.length > 15"
          size="small"
          variant="text"
          class="mr-1 mb-1"
        >
          {{ t('assistant.more', { count: message.response_data.data.items.length - 15 }) }}
        </v-chip>
      </div>

      <!-- Query Correction Suggestions (when no results found) -->
      <div
        v-if="message.response_type === 'query_result' && !message.response_data?.data?.items?.length && message.response_data?.data?.suggestions?.length"
        class="mt-3"
      >
        <div class="text-caption text-medium-emphasis mb-2">
          <v-icon size="small" class="mr-1">mdi-lightbulb-outline</v-icon>
          {{ t('assistant.didYouMean') }}
        </div>
        <v-chip
          v-for="(suggestion, idx) in message.response_data.data.suggestions"
          :key="idx"
          size="small"
          variant="tonal"
          color="primary"
          class="mr-1 mb-1 suggestion-chip"
          @click="$emit('suggestion-click', suggestion.corrected_query || '')"
        >
          <v-icon start size="small">
            {{ suggestion.type === 'geographic' ? 'mdi-map-marker' : suggestion.type === 'entity_type' ? 'mdi-folder-outline' : 'mdi-tag-outline' }}
          </v-icon>
          {{ suggestion.suggestion }}
        </v-chip>
      </div>

      <!-- Navigation Target -->
      <v-btn
        v-if="message.response_type === 'navigation' && message.response_data?.target"
        size="small"
        variant="tonal"
        color="primary"
        class="mt-2"
        @click="$emit('navigate', message.response_data?.target?.route || '')"
      >
        <v-icon start size="small">mdi-arrow-right</v-icon>
        {{ t('assistant.goTo', { name: message.response_data.target.entity_name || t('nav.entities') }) }}
      </v-btn>

      <!-- Redirect to Smart Query -->
      <v-btn
        v-if="message.response_type === 'redirect_to_smart_query'"
        size="small"
        variant="tonal"
        color="warning"
        class="mt-2"
        @click="$emit('smart-query-redirect', message.response_data)"
      >
        <v-icon start size="small">mdi-magnify</v-icon>
        {{ t('assistant.openSmartQuery') }}
      </v-btn>

      <!-- Help Topics -->
      <div v-if="message.response_type === 'help' && message.response_data?.suggested_commands?.length" class="mt-2">
        <v-chip
          v-for="cmd in message.response_data.suggested_commands"
          :key="cmd"
          size="small"
          variant="outlined"
          color="info"
          class="mr-1 mb-1"
          @click="$emit('command', cmd)"
        >
          {{ cmd }}
        </v-chip>
      </div>

      <!-- Discussion Response - Key Points & Recommendations -->
      <div v-if="message.response_type === 'discussion'" class="mt-3">
        <!-- Analysis Type Badge -->
        <v-chip
          v-if="message.response_data?.analysis_type"
          size="small"
          variant="tonal"
          :color="getAnalysisTypeColor(message.response_data.analysis_type)"
          class="mb-2"
        >
          <v-icon start size="small">{{ getAnalysisTypeIcon(message.response_data.analysis_type) }}</v-icon>
          {{ getAnalysisTypeLabel(message.response_data.analysis_type) }}
        </v-chip>

        <!-- Key Points -->
        <div v-if="message.response_data?.key_points?.length" class="discussion-section mb-2">
          <div class="text-caption text-medium-emphasis mb-1">
            <v-icon size="small" class="mr-1">mdi-lightbulb-outline</v-icon>
            {{ t('assistant.keyPoints') }}
          </div>
          <ul class="discussion-list">
            <li v-for="(point, idx) in message.response_data.key_points" :key="idx">
              {{ point }}
            </li>
          </ul>
        </div>

        <!-- Recommendations -->
        <div v-if="message.response_data?.recommendations?.length" class="discussion-section">
          <div class="text-caption text-medium-emphasis mb-1">
            <v-icon size="small" class="mr-1">mdi-clipboard-check-outline</v-icon>
            {{ t('assistant.recommendations') }}
          </div>
          <ul class="discussion-list">
            <li v-for="(rec, idx) in message.response_data.recommendations" :key="idx">
              {{ rec }}
            </li>
          </ul>
        </div>
      </div>

      <!-- Footer: Timestamp + Actions -->
      <div class="chat-message__footer">
        <span class="chat-message__time">{{ formatTime(message.timestamp) }}</span>
        <v-btn
          v-if="message.role === 'assistant'"
          :icon="copied ? 'mdi-check' : 'mdi-content-copy'"
          variant="tonal"
          size="x-small"
          :color="copied ? 'success' : 'default'"
          class="chat-message__copy-btn"
          @click="copyMessage"
        >
          <v-tooltip activator="parent" location="top">
            {{ copied ? t('assistant.copied') : t('assistant.copy') }}
          </v-tooltip>
        </v-btn>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import DOMPurify from 'dompurify'
import type { ConversationMessage } from '@/composables/useAssistant'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('ChatMessage')

const { t, locale } = useI18n()

const props = defineProps<{
  message: ConversationMessage
}>()

const emit = defineEmits<{
  'item-click': [item: any]
  'navigate': [route: string]
  'command': [command: string]
  'entity-click': [entityType: string, entitySlug: string]
  'suggestion-click': [correctedQuery: string]
  'smart-query-redirect': [responseData: any]
}>()

// Copy functionality
const copied = ref(false)

async function copyMessage() {
  try {
    await navigator.clipboard.writeText(props.message.content)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (e) {
    logger.error('Failed to copy message:', e)
  }
}

// Handle clicks on entity chips within the message text
function handleTextClick(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (target.classList.contains('entity-chip')) {
    const entityType = target.dataset.type
    const entitySlug = target.dataset.slug
    if (entityType && entitySlug) {
      emit('entity-click', entityType, entitySlug)
    }
  }
}

function escapeHtml(text: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }
  return text.replace(/[&<>"']/g, (char) => map[char])
}

function formatMessage(content: string): string {
  // 1. First escape HTML to prevent XSS
  let formatted = escapeHtml(content)

  // 2. Then apply markdown-like formatting (safe patterns only)
  formatted = formatted
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Code
    .replace(/`(.+?)`/g, '<code>$1</code>')
    // Line breaks
    .replace(/\n/g, '<br>')

  // 3. Entity-Links: [[entity_type:slug:name]] -> clickable chip
  formatted = formatted.replace(
    /\[\[(\w+):([^:]+):([^\]]+)\]\]/g,
    '<span class="entity-chip" data-type="$1" data-slug="$2" role="button" tabindex="0">$3</span>'
  )

  // 4. Final sanitization with DOMPurify for defense-in-depth
  return DOMPurify.sanitize(formatted, {
    ALLOWED_TAGS: ['strong', 'code', 'br', 'span'],
    ALLOWED_ATTR: ['class', 'data-type', 'data-slug', 'role', 'tabindex']
  })
}

function formatTime(date: Date): string {
  const localeMap: Record<string, string> = { de: 'de-DE', en: 'en-US' }
  return new Date(date).toLocaleTimeString(localeMap[locale.value] || 'de-DE', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Discussion response helpers
function getAnalysisTypeColor(type: string): string {
  const colors: Record<string, string> = {
    requirements: 'purple',
    planning: 'blue',
    document: 'teal',
    general: 'grey'
  }
  return colors[type] || 'grey'
}

function getAnalysisTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    requirements: 'mdi-clipboard-list',
    planning: 'mdi-calendar-check',
    document: 'mdi-file-document',
    general: 'mdi-chat'
  }
  return icons[type] || 'mdi-chat'
}

function getAnalysisTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    requirements: t('assistant.analysisType.requirements'),
    planning: t('assistant.analysisType.planning'),
    document: t('assistant.analysisType.document'),
    general: t('assistant.analysisType.general')
  }
  return labels[type] || type
}
</script>

<style scoped>
.chat-message {
  display: flex;
  gap: 8px;
  padding: 8px 0;
}

.chat-message--user {
  flex-direction: row-reverse;
}

.chat-message--user .chat-message__content {
  align-items: flex-end;
}

.chat-message--user .chat-message__text {
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
}

.chat-message--assistant .chat-message__text {
  background: rgb(var(--v-theme-surface-variant));
  color: rgb(var(--v-theme-on-surface-variant));
}

.chat-message--error .chat-message__text {
  background: rgb(var(--v-theme-error-container));
  color: rgb(var(--v-theme-on-error-container));
}

.chat-message__avatar {
  flex-shrink: 0;
}

.chat-message__content {
  display: flex;
  flex-direction: column;
  max-width: 85%;
}

.chat-message__text {
  padding: 10px 14px;
  border-radius: 16px;
  font-size: 0.875rem;
  line-height: 1.4;
  word-break: break-word;
}

.chat-message__text :deep(code) {
  background: rgba(var(--v-theme-on-surface), 0.1);
  padding: 2px 4px;
  border-radius: 4px;
  font-size: 0.8em;
}

.chat-message__text :deep(.entity-chip) {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  margin: 0 2px;
  background: rgb(var(--v-theme-primary-container));
  color: rgb(var(--v-theme-on-primary-container));
  border-radius: 12px;
  font-size: 0.85em;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.chat-message__text :deep(.entity-chip:hover) {
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
  transform: translateY(-1px);
}

.chat-message__text :deep(.entity-chip:focus) {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.chat-message__footer {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
  padding: 0 4px;
}

.chat-message__time {
  font-size: 0.7rem;
  color: rgb(var(--v-theme-on-surface-variant));
}

.chat-message__copy-btn {
  opacity: 0;
  transition: opacity 0.2s ease;
}

.chat-message:hover .chat-message__copy-btn {
  opacity: 1;
}

/* Discussion response styles */
.discussion-section {
  padding: 8px;
  background: rgba(var(--v-theme-surface-variant), 0.3);
  border-radius: 8px;
}

.discussion-list {
  margin: 0;
  padding-left: 20px;
  font-size: 0.85rem;
}

.discussion-list li {
  margin-bottom: 4px;
}
</style>
