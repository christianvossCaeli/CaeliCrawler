<!-- eslint-disable vue/no-v-html -- All v-html content is sanitized via DOMPurify in formatMessage -->
<template>
  <div
    ref="conversationRef"
    class="chat-conversation"
    role="log"
    aria-live="polite"
    aria-label="Chat-Verlauf"
  >
    <div
      v-for="message in displayMessages"
      :key="message.id"
      class="chat-message"
      :class="[
        `chat-message--${message.type}`,
        { 'chat-message--error': message.error }
      ]"
      role="article"
      :aria-label="message.type === 'user' ? 'Ihre Nachricht' : 'Assistent-Antwort'"
    >
      <!-- Avatar -->
      <div class="chat-message__avatar" aria-hidden="true">
        <v-icon v-if="message.type === 'ai'" size="18">mdi-robot-outline</v-icon>
        <span v-else>{{ userInitial }}</span>
      </div>

      <!-- Bubble -->
      <div class="chat-message__bubble">
        <!-- Error indicator -->
        <div v-if="message.error" class="chat-message__error" role="alert">
          <v-icon size="16" color="error">mdi-alert-circle</v-icon>
          <span>{{ message.error }}</span>
        </div>

        <!-- Message content -->
        <!-- eslint-disable-next-line vue/no-v-html -- Content is sanitized via DOMPurify -->
        <div
          v-if="message.content && !message.error"
          class="chat-message__text"
          v-html="formatMessage(message.content)"
        />

        <!-- Results Panel (for AI messages with results) -->
        <ChatResultsPanel
          v-if="message.type === 'ai' && message.results && !message.error"
          :results="message.results"
          :response-type="message.responseType"
          @action="(action, data) => $emit('action', action, data)"
        />
      </div>
    </div>

    <!-- Streaming Message (shows while streaming with content) -->
    <div
      v-if="streaming && streamingContent"
      class="chat-message chat-message--ai chat-message--streaming"
      role="status"
      aria-label="Assistent schreibt..."
    >
      <div class="chat-message__avatar" aria-hidden="true">
        <v-icon size="18">mdi-robot-outline</v-icon>
      </div>
      <div class="chat-message__bubble">
        <!-- eslint-disable-next-line vue/no-v-html -- Content is sanitized via DOMPurify -->
        <div class="chat-message__text" v-html="formatMessage(streamingContent)" />
        <span class="chat-message__cursor" aria-hidden="true" />
      </div>
    </div>

    <!-- Loading Indicator (shows when waiting for first token) -->
    <div
      v-else-if="loading && !streamingContent"
      class="chat-message chat-message--ai"
      role="status"
      aria-label="Assistent denkt nach..."
    >
      <div class="chat-message__avatar" aria-hidden="true">
        <v-icon size="18">mdi-robot-outline</v-icon>
      </div>
      <div class="chat-message__bubble">
        <div class="chat-message__streaming">
          <span class="chat-message__streaming-dot" />
          <span class="chat-message__streaming-dot" />
          <span class="chat-message__streaming-dot" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { formatMessage } from '@/utils/messageFormatting'
import ChatResultsPanel from './ChatResultsPanel.vue'

interface Message {
  id: string
  type: 'user' | 'ai'
  content: string
  timestamp: Date
  results?: unknown
  responseType?: string
  error?: string
}

const props = defineProps<{
  messages: Message[]
  loading?: boolean
  streaming?: boolean
  streamingContent?: string
}>()

defineEmits<{
  action: [action: string, data: unknown]
}>()

const auth = useAuthStore()
const conversationRef = ref<HTMLElement | null>(null)

const userInitial = computed(() => {
  const name = auth.user?.full_name || auth.user?.email || 'U'
  return name.charAt(0).toUpperCase()
})

// Filter out the last AI message if it's empty and we're streaming
// (prevents duplicate display with streaming indicator)
const displayMessages = computed(() => {
  if (!props.streaming || !props.streamingContent) {
    return props.messages
  }
  // When streaming, hide the last empty AI message (it's shown as streaming)
  const msgs = [...props.messages]
  const lastMsg = msgs[msgs.length - 1]
  if (lastMsg?.type === 'ai' && !lastMsg.content) {
    return msgs.slice(0, -1)
  }
  return msgs
})

// Optimized scroll using requestAnimationFrame
function scrollToBottom() {
  if (!conversationRef.value) return
  requestAnimationFrame(() => {
    if (conversationRef.value) {
      conversationRef.value.scrollTop = conversationRef.value.scrollHeight
    }
  })
}

// Auto-scroll when messages change
watch(
  () => props.messages.length,
  () => nextTick(scrollToBottom)
)

// Auto-scroll during streaming
watch(
  () => props.streamingContent,
  () => scrollToBottom
)

// Auto-scroll when loading starts
watch(
  () => props.loading,
  (isLoading) => {
    if (isLoading) nextTick(scrollToBottom)
  }
)
</script>
