<template>
  <div ref="conversationRef" class="chat-conversation">
    <div
      v-for="message in messages"
      :key="message.id"
      class="chat-message"
      :class="`chat-message--${message.type}`"
    >
      <!-- Avatar -->
      <div class="chat-message__avatar">
        <v-icon v-if="message.type === 'ai'" size="18">mdi-robot-outline</v-icon>
        <span v-else>{{ userInitial }}</span>
      </div>

      <!-- Bubble -->
      <div class="chat-message__bubble">
        <div class="chat-message__text" v-html="formatContent(message.content)" />

        <!-- Results Panel (for AI messages with results) -->
        <ChatResultsPanel
          v-if="message.type === 'ai' && message.results"
          :results="message.results"
          @action="(action, data) => $emit('action', action, data)"
        />
      </div>
    </div>

    <!-- Streaming Indicator -->
    <div v-if="loading || streaming" class="chat-message chat-message--ai">
      <div class="chat-message__avatar">
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
import ChatResultsPanel from './ChatResultsPanel.vue'

interface Message {
  id: string
  type: 'user' | 'ai'
  content: string
  timestamp: Date
  results?: unknown
  error?: string
}

const props = defineProps<{
  messages: Message[]
  loading?: boolean
  streaming?: boolean
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

function formatContent(content: string): string {
  // Basic markdown-like formatting
  return content
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
}

// Auto-scroll to bottom when new messages arrive
watch(
  () => props.messages.length,
  () => {
    nextTick(() => {
      if (conversationRef.value) {
        conversationRef.value.scrollTop = conversationRef.value.scrollHeight
      }
    })
  }
)

watch(
  () => props.loading,
  (isLoading) => {
    if (isLoading) {
      nextTick(() => {
        if (conversationRef.value) {
          conversationRef.value.scrollTop = conversationRef.value.scrollHeight
        }
      })
    }
  }
)
</script>
