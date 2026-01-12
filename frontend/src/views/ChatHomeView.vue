<template>
  <div class="chat-home" :class="{ 'chat-home--welcome': !hasConversation, 'chat-home--has-conversation': hasConversation }">
    <div class="chat-home__container">
      <!-- Welcome Section (shown when no conversation) -->
      <ChatWelcome v-if="!hasConversation && !loading" />

      <!-- Suggestions (shown when no conversation) -->
      <ChatSuggestionCards
        v-if="!hasConversation && !loading"
        @select="handleSuggestionSelect"
      />

      <!-- Conversation Area -->
      <ChatConversation
        v-if="hasConversation || loading"
        :messages="messages"
        :loading="loading"
        :streaming="streaming"
        @action="handleResultAction"
      />

      <!-- Main Input -->
      <ChatMainInput
        ref="inputRef"
        v-model="question"
        :attachments="pendingAttachments"
        :mode="currentMode"
        :disabled="false"
        :loading="loading"
        :uploading="isUploading"
        :is-listening="isListening"
        :has-microphone="hasMicrophone"
        :interim-transcript="interimTranscript"
        @submit="handleSubmit"
        @paste="handlePaste"
        @remove-attachment="removeAttachment"
        @toggle-voice="handleVoiceInput"
        @file-select="handleFileSelect"
        @trigger-file-input="triggerFileInput"
      />
    </div>

    <!-- History Sidebar -->
    <ChatHistorySidebar
      v-model="showHistory"
      @select="handleHistorySelect"
    />

    <!-- History Toggle Button -->
    <v-btn
      icon
      variant="text"
      size="small"
      class="history-toggle"
      :aria-label="t('chatHome.history.toggle')"
      @click="showHistory = !showHistory"
    >
      <v-icon>mdi-history</v-icon>
      <v-tooltip activator="parent" location="left">
        {{ t('chatHome.history.toggle') }}
      </v-tooltip>
    </v-btn>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSmartQuery } from '@/composables/useSmartQuery'
import { usePageContextProvider, PAGE_FEATURES, PAGE_ACTIONS } from '@/composables/usePageContext'
import type { PageContextData } from '@/composables/assistant/types'
import ChatWelcome from '@/components/chathome/ChatWelcome.vue'
import ChatMainInput from '@/components/chathome/ChatMainInput.vue'
import ChatSuggestionCards from '@/components/chathome/ChatSuggestionCards.vue'
import ChatConversation from '@/components/chathome/ChatConversation.vue'
import ChatHistorySidebar from '@/components/chathome/ChatHistorySidebar.vue'
import '@/components/chathome/styles/chat-home.css'

const { t } = useI18n()

// Refs
const inputRef = ref<InstanceType<typeof ChatMainInput> | null>(null)
const showHistory = ref(false)

// Use SmartQuery composable for core functionality
const {
  question,
  currentMode,
  loading,
  error,
  results,
  pendingAttachments,
  isUploading,
  isListening,
  hasMicrophone,
  interimTranscript,
  handleVoiceInput,
  uploadAttachment,
  removeAttachment,
  executeQuery,
  cleanup,
} = useSmartQuery()

// Local conversation state
interface Message {
  id: string
  type: 'user' | 'ai'
  content: string
  timestamp: Date
  results?: unknown
  error?: string
}

const messages = ref<Message[]>([])
const streaming = ref(false)

const hasConversation = computed(() => messages.value.length > 0)

// Page Context Provider
usePageContextProvider(
  '/',
  (): PageContextData => ({
    current_route: '/',
    view_mode: currentMode.value,
    current_query: question.value || undefined,
    query_mode: currentMode.value as 'read' | 'write' | 'plan',
    query_result_count: Array.isArray(results.value) ? results.value.length : 0,
    available_features: [...PAGE_FEATURES.smartQuery],
    available_actions: [...PAGE_ACTIONS.base, 'execute_query', 'save_query', 'export_results']
  })
)

// Handlers
async function handleSubmit() {
  if (!question.value.trim() && pendingAttachments.value.length === 0) return

  const userMessage: Message = {
    id: `user-${Date.now()}`,
    type: 'user',
    content: question.value,
    timestamp: new Date()
  }
  messages.value.push(userMessage)

  question.value = ''
  streaming.value = true

  try {
    await executeQuery()

    // Extract message from results - handle different result structures
    const resultMessage = results.value?.message
      || (results.value && 'summary' in results.value ? (results.value as { summary?: string }).summary : undefined)
      || t('chatHome.messages.complete')

    const aiMessage: Message = {
      id: `ai-${Date.now()}`,
      type: 'ai',
      content: resultMessage,
      timestamp: new Date(),
      results: results.value
    }
    messages.value.push(aiMessage)
  } catch (e) {
    const errorMessage: Message = {
      id: `error-${Date.now()}`,
      type: 'ai',
      content: error.value || t('chatHome.messages.error'),
      timestamp: new Date(),
      error: error.value || undefined
    }
    messages.value.push(errorMessage)
  } finally {
    streaming.value = false
  }
}

function handleSuggestionSelect(query: string) {
  question.value = query
  handleSubmit()
}

function handleHistorySelect(query: string) {
  question.value = query
  showHistory.value = false
  inputRef.value?.focus()
}

function handleResultAction(action: string, data: unknown) {
  // Handle result actions like navigation, export etc.
  console.log('Result action:', action, data)
}

async function handleFileSelect(files: FileList) {
  for (const file of Array.from(files)) {
    await uploadAttachment(file)
  }
}

async function handlePaste(event: ClipboardEvent) {
  const items = event.clipboardData?.items
  if (!items) return

  for (const item of Array.from(items)) {
    if (item.type.startsWith('image/')) {
      event.preventDefault()
      const file = item.getAsFile()
      if (file) {
        await uploadAttachment(file)
      }
    }
  }
}

function triggerFileInput() {
  inputRef.value?.triggerFileInput()
}

// Lifecycle
onMounted(() => {
  // Focus input on mount
  inputRef.value?.focus()
})

onBeforeUnmount(() => {
  cleanup()
})
</script>

<style scoped>
.history-toggle {
  position: fixed;
  top: calc(var(--v-layout-top, 64px) + 16px);
  right: 16px;
  z-index: 50;
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-theme-on-surface), 0.1);
}
</style>
