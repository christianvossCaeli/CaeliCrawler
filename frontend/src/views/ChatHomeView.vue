<template>
  <div
    class="chat-home"
    :class="{ 'chat-home--welcome': !hasConversation, 'chat-home--has-conversation': hasConversation }"
    role="main"
    aria-label="Chat"
  >
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
        :streaming-content="streamingContent"
        @action="handleResultAction"
      />

      <!-- Cancel Button (shown during streaming) -->
      <Transition name="fade">
        <div v-if="streaming" class="chat-cancel-wrapper">
          <v-btn
            variant="outlined"
            size="small"
            color="error"
            @click="handleCancel"
          >
            <v-icon start size="16">mdi-stop</v-icon>
            {{ t('chatHome.input.cancel') }}
          </v-btn>
        </div>
      </Transition>

      <!-- Main Input -->
      <ChatMainInput
        ref="inputRef"
        v-model="question"
        :attachments="pendingAttachments"
        :mode="currentMode"
        :disabled="streaming"
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

    <!-- Action Buttons (top right) -->
    <div class="chat-actions">
      <!-- New Chat Button (shown when conversation exists) -->
      <v-btn
        v-if="hasConversation"
        icon
        variant="text"
        size="small"
        :aria-label="t('chatHome.actions.newChat')"
        @click="handleNewChat"
      >
        <v-icon>mdi-plus</v-icon>
        <v-tooltip activator="parent" location="left">
          {{ t('chatHome.actions.newChat') }}
        </v-tooltip>
      </v-btn>

      <!-- History Toggle Button -->
      <v-btn
        icon
        variant="text"
        size="small"
        :aria-label="t('chatHome.history.toggle')"
        @click="showHistory = !showHistory"
      >
        <v-icon>mdi-history</v-icon>
        <v-tooltip activator="parent" location="left">
          {{ t('chatHome.history.toggle') }}
        </v-tooltip>
      </v-btn>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { assistantApi } from '@/services/api'
import { useSmartQueryAttachments } from '@/composables/smartquery'
import { useSpeechRecognition } from '@/composables/useSpeechRecognition'
import { useAssistantHistory } from '@/composables/assistant/useAssistantHistory'
import { usePageContextProvider, PAGE_FEATURES, PAGE_ACTIONS } from '@/composables/usePageContext'
import type { PageContextData, AssistantContext, ConversationMessage } from '@/composables/assistant/types'
import { generateMessageId } from '@/composables/assistant/types'
import ChatWelcome from '@/components/chathome/ChatWelcome.vue'
import ChatMainInput from '@/components/chathome/ChatMainInput.vue'
import ChatSuggestionCards from '@/components/chathome/ChatSuggestionCards.vue'
import ChatConversation from '@/components/chathome/ChatConversation.vue'
import ChatHistorySidebar from '@/components/chathome/ChatHistorySidebar.vue'
import '@/components/chathome/styles/chat-home.css'

const { t, locale } = useI18n()
const route = useRoute()

// Refs
const inputRef = ref<InstanceType<typeof ChatMainInput> | null>(null)
const showHistory = ref(false)

// Core state
const question = ref('')
const currentMode = ref<'read' | 'write'>('read')
const loading = ref(false)
const streaming = ref(false)
const streamingContent = ref('')

// Message interface for chat
interface Message {
  id: string
  type: 'user' | 'ai'
  content: string
  timestamp: Date
  results?: unknown
  responseType?: string
  error?: string
}

const messages = ref<Message[]>([])

// AbortController for streaming
const abortController = ref<AbortController | null>(null)

// Use attachments composable
const attachments = useSmartQueryAttachments()
const pendingAttachments = attachments.pendingAttachments
const isUploading = attachments.isUploading

// Use speech recognition
const speech = useSpeechRecognition()
const isListening = speech.isListening
const hasMicrophone = speech.hasMicrophone
const interimTranscript = speech.interimTranscript

// Use history
const historyMessages = ref<ConversationMessage[]>([])
const history = useAssistantHistory({ messages: historyMessages })

const hasConversation = computed(() => messages.value.length > 0)

// SSE Event Types
const SSE_EVENT = {
  STATUS: 'status',
  TOKEN: 'token',
  COMPLETE: 'complete',
  ERROR: 'error',
} as const

// Max conversation history to send to API
const MAX_HISTORY_LENGTH = 10

// Build context for API
function buildContext(): AssistantContext {
  return {
    current_route: route.fullPath,
    current_entity_id: null,
    current_entity_type: null,
    current_entity_name: null,
    view_mode: 'dashboard',
    available_actions: ['search', 'help', 'navigate']
  }
}

// Build conversation history for API (returns type expected by API)
function buildConversationHistory() {
  return messages.value.slice(-MAX_HISTORY_LENGTH).map(m => ({
    role: m.type === 'user' ? 'user' as const : 'assistant' as const,
    content: m.content,
    timestamp: m.timestamp.toISOString()
  }))
}

// Page Context Provider
usePageContextProvider(
  '/',
  (): PageContextData => ({
    current_route: '/',
    view_mode: currentMode.value,
    current_query: question.value || undefined,
    query_mode: currentMode.value,
    query_result_count: 0,
    available_features: [...PAGE_FEATURES.smartQuery],
    available_actions: [...PAGE_ACTIONS.base, 'execute_query', 'save_query', 'export_results']
  })
)

// Handle voice input toggle
function handleVoiceInput() {
  if (isListening.value) {
    speech.toggleListening()
  } else {
    speech.clearTranscript()
    question.value = ''
    speech.toggleListening()
  }
}

// Main submit handler - uses Assistant API with streaming
async function handleSubmit() {
  if (!question.value.trim() && pendingAttachments.value.length === 0) return

  // Cancel any ongoing request
  if (abortController.value) {
    abortController.value.abort()
  }
  abortController.value = new AbortController()

  const currentQuestion = question.value.trim()
  question.value = ''

  // Add user message
  const userMessage: Message = {
    id: `user-${Date.now()}`,
    type: 'user',
    content: currentQuestion,
    timestamp: new Date()
  }
  messages.value.push(userMessage)

  // Add placeholder for AI response
  const aiMessageIndex = messages.value.length
  const aiMessage: Message = {
    id: `ai-${Date.now()}`,
    type: 'ai',
    content: '',
    timestamp: new Date(),
    responseType: 'streaming'
  }
  messages.value.push(aiMessage)

  loading.value = true
  streaming.value = true
  streamingContent.value = ''

  try {
    const lang = (locale.value === 'de' || locale.value === 'en') ? locale.value : 'de'
    const attachmentIds = pendingAttachments.value.map(a => a.id)

    const response = await assistantApi.chatStream(
      {
        message: currentQuestion,
        context: buildContext(),
        conversation_history: buildConversationHistory(),
        mode: currentMode.value,
        language: lang,
        attachment_ids: attachmentIds.length > 0 ? attachmentIds : undefined
      },
      abortController.value.signal
    )

    // Clear attachments after starting request
    if (attachmentIds.length > 0) {
      attachments.clearAttachments()
    }

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('No response body reader available')
    }

    const decoder = new TextDecoder()
    let buffer = ''
    let finalContent = ''
    let finalResults: unknown = null
    let finalResponseType = 'text'

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6).trim()
          if (dataStr === '[DONE]') continue

          try {
            const parsed = JSON.parse(dataStr)

            switch (parsed.type) {
              case SSE_EVENT.STATUS:
                // Status update - could show loading indicator
                break

              case SSE_EVENT.TOKEN:
                // Append token to streaming content (not to messages yet)
                finalContent += parsed.content || ''
                streamingContent.value = finalContent
                break

              case SSE_EVENT.COMPLETE: {
                // Final response with full data
                const completeData = parsed.data
                if (completeData?.response) {
                  const resp = completeData.response
                  if (resp.message) {
                    finalContent = resp.message
                  }
                  finalResults = resp
                  finalResponseType = resp.type || 'text'
                }
                break
              }

              case SSE_EVENT.ERROR:
                messages.value[aiMessageIndex].error = parsed.message || t('chatHome.messages.error')
                break
            }
          } catch {
            // Ignore parse errors for incomplete JSON
          }
        }
      }
    }

    // Update final message
    messages.value[aiMessageIndex].content = finalContent || streamingContent.value || t('chatHome.messages.complete')
    messages.value[aiMessageIndex].results = finalResults
    messages.value[aiMessageIndex].responseType = finalResponseType

    // Save to history
    historyMessages.value = messages.value.map(m => ({
      id: generateMessageId(),
      role: m.type === 'user' ? 'user' as const : 'assistant' as const,
      content: m.content,
      timestamp: m.timestamp,
      response_type: m.responseType
    }))
    history.saveHistory()
    history.addQueryToHistory(currentQuestion, 1, currentMode.value)

  } catch (e: unknown) {
    if (e instanceof Error && e.name === 'AbortError') {
      // Request was cancelled, ignore
      return
    }
    const errorMsg = e instanceof Error ? e.message : t('chatHome.messages.error')
    messages.value[aiMessageIndex].content = ''
    messages.value[aiMessageIndex].error = errorMsg
  } finally {
    loading.value = false
    streaming.value = false
    abortController.value = null
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

// Cancel ongoing streaming request
function handleCancel() {
  if (abortController.value) {
    abortController.value.abort()
    abortController.value = null
  }

  // Update the last AI message with what we have so far
  const lastMessage = messages.value[messages.value.length - 1]
  if (lastMessage?.type === 'ai') {
    if (streamingContent.value) {
      lastMessage.content = streamingContent.value + '\n\n*[Abgebrochen]*'
    } else {
      lastMessage.content = '*[Abgebrochen]*'
    }
  }

  loading.value = false
  streaming.value = false
  streamingContent.value = ''
}

function handleResultAction(_action: string, _data: unknown) {
  // TODO: Handle result actions (e.g., navigate to entity, execute follow-up query)
}

// Start a new chat (reset conversation)
function handleNewChat() {
  // Cancel any ongoing request
  if (abortController.value) {
    abortController.value.abort()
    abortController.value = null
  }

  // Clear conversation from localStorage and state
  history.clearConversation()

  // Clear local state
  messages.value = []
  historyMessages.value = []
  question.value = ''
  streamingContent.value = ''
  loading.value = false
  streaming.value = false
  attachments.clearAttachments()

  // Focus input
  inputRef.value?.focus()
}

async function handleFileSelect(files: FileList) {
  for (const file of Array.from(files)) {
    await attachments.uploadAttachment(file)
  }
}

function removeAttachment(id: string) {
  attachments.removeAttachment(id)
}

async function handlePaste(event: ClipboardEvent) {
  const items = event.clipboardData?.items
  if (!items) return

  for (const item of Array.from(items)) {
    if (item.type.startsWith('image/')) {
      event.preventDefault()
      const file = item.getAsFile()
      if (file) {
        await attachments.uploadAttachment(file)
      }
    }
  }
}

function triggerFileInput() {
  inputRef.value?.triggerFileInput()
}

// Lifecycle
onMounted(() => {
  inputRef.value?.focus()
  // Load history
  history.loadHistory()
  history.loadQueryHistory()

  // Convert loaded history to display format
  if (historyMessages.value.length > 0) {
    messages.value = historyMessages.value.map((m, index) => ({
      id: `loaded-${index}-${m.timestamp.getTime()}`,
      type: m.role === 'user' ? 'user' as const : 'ai' as const,
      content: m.content,
      timestamp: m.timestamp,
      responseType: m.response_type,
      results: m.response_data
    }))
  }
})

onBeforeUnmount(() => {
  if (abortController.value) {
    abortController.value.abort()
  }
  attachments.clearAttachments()
})
</script>

<style scoped>
.chat-actions {
  position: fixed;
  top: calc(var(--v-layout-top, 64px) + 16px);
  right: 16px;
  z-index: 50;
  display: flex;
  gap: 4px;
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-theme-on-surface), 0.1);
  border-radius: 8px;
  padding: 4px;
}

.chat-cancel-wrapper {
  display: flex;
  justify-content: center;
  padding: 8px 0;
}

/* Fade transition for cancel button */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
