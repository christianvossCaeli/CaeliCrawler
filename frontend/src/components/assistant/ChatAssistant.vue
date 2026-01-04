<template>
  <div class="chat-assistant-wrapper">
    <!-- AI Assistant Trigger -->
    <Transition name="trigger-fade">
      <button
        v-show="!isOpen"
        class="ai-trigger"
        :class="{ 'ai-trigger--unread': hasUnread }"
        :aria-label="t('assistant.open')"
        aria-expanded="false"
        @click="isOpen = true"
      >
        <!-- Animated background orbs -->
        <span class="ai-trigger__orb ai-trigger__orb--1"></span>
        <span class="ai-trigger__orb ai-trigger__orb--2"></span>
        <span class="ai-trigger__orb ai-trigger__orb--3"></span>

        <!-- Main content -->
        <span class="ai-trigger__inner">
          <span class="ai-trigger__sparkles">
            <span class="sparkle sparkle--1">✦</span>
            <span class="sparkle sparkle--2">✦</span>
            <span class="sparkle sparkle--3">✦</span>
          </span>
          <span class="ai-trigger__icon-wrap">
            <svg class="ai-trigger__icon" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2L9.19 8.63L2 9.24L7.46 13.97L5.82 21L12 17.27L18.18 21L16.54 13.97L22 9.24L14.81 8.63L12 2Z" />
            </svg>
          </span>
          <span class="ai-trigger__text">AI</span>
        </span>

        <!-- Notification badge -->
        <span v-if="hasUnread" class="ai-trigger__badge">
          <span class="ai-trigger__badge-ping"></span>
          <span class="ai-trigger__badge-dot"></span>
        </span>
      </button>
    </Transition>

    <!-- Backdrop -->
    <Transition name="fade">
      <div v-if="isOpen" class="chat-backdrop" @click="isOpen = false"></div>
    </Transition>

    <!-- Chat Panel -->
    <Transition name="slide">
      <div v-if="isOpen" class="chat-panel">
        <!-- Header -->
        <ChatHeader
          v-model:mode="localMode"
          @clear="clearConversation"
          @close="isOpen = false"
        />

        <!-- Context Indicator -->
        <div v-if="currentContext.current_entity_name" class="context-bar">
          <v-icon size="14" class="mr-1">mdi-map-marker</v-icon>
          <span>{{ currentContext.current_entity_name }}</span>
          <span class="context-type">{{ currentContext.current_entity_type }}</span>
        </div>

        <!-- Quick Actions -->
        <ChatQuickActions
          v-if="localMode !== 'plan'"
          :current-context="currentContext"
          @action="handleQuickAction"
        />

        <!-- Plan Mode Hint -->
        <div v-if="localMode === 'plan'" class="plan-mode-hint">
          <v-icon size="small" class="mr-2">mdi-lightbulb-on</v-icon>
          <span>{{ t('assistant.planModeHint') }}</span>
        </div>

        <!-- Messages Area -->
        <ChatMessages
          ref="messagesContainer"
          :messages="messages"
          :is-loading="isLoading"
          :streaming-status="streamingStatus"
          :locale="locale"
          @navigate="handleNavigate"
          @smart-query-redirect="handleSmartQueryRedirect"
          @item-click="handleItemClick"
        />

        <!-- Suggestions -->
        <div v-if="suggestedActions.length > 0" class="suggestions">
          <button
            v-for="action in suggestedActions"
            :key="action.value"
            class="suggestion-btn"
            @click="handleSuggestedAction(action)"
          >
            {{ action.label }}
          </button>
        </div>

        <!-- Attachment Preview -->
        <ChatAttachments
          v-if="pendingAttachments.length > 0"
          :attachments="pendingAttachments"
          @remove="removeAttachment"
        />

        <!-- Input -->
        <ChatInput
          v-model="inputText"
          :is-loading="isLoading"
          :is-uploading="isUploading"
          :has-attachments="pendingAttachments.length > 0"
          :placeholder="getPlaceholder"
          @send="sendMessage"
          @upload="uploadAttachment"
        />
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAssistant } from '@/composables/useAssistant'
import { useQueryContextStore } from '@/stores/queryContext'

// Sub-components
import ChatHeader from './ChatHeader.vue'
import ChatMessages from './ChatMessages.vue'
import ChatInput from './ChatInput.vue'
import ChatQuickActions from './ChatQuickActions.vue'
import ChatAttachments from './ChatAttachments.vue'

const { t, locale } = useI18n()
const router = useRouter()
const queryContextStore = useQueryContextStore()

const {
  isOpen,
  isLoading,
  isUploading,
  streamingStatus,
  messages,
  mode,
  suggestedActions,
  hasUnread,
  currentContext,
  pendingAttachments,
  send,
  clearConversation,
  handleSuggestedAction,
  uploadAttachment,
  removeAttachment,
} = useAssistant()

const inputText = ref('')
const localMode = ref(mode.value)
const messagesContainer = ref<InstanceType<typeof ChatMessages> | null>(null)

const getPlaceholder = computed(() => {
  switch (localMode.value) {
    case 'plan':
      return t('assistant.placeholderPlan')
    case 'write':
      return t('assistant.placeholderWrite')
    default:
      return t('assistant.placeholderRead')
  }
})

function handleQuickAction(action: { query: string }) {
  inputText.value = action.query
  if (!action.query.endsWith(' ')) {
    sendMessage()
  }
}

function sendMessage() {
  if ((!inputText.value.trim() && pendingAttachments.value.length === 0) || isLoading.value) return
  send(inputText.value.trim() || 'Analysiere das Bild')
  inputText.value = ''
}

function handleNavigate(route: string) {
  router.push(route)
  isOpen.value = false
}

function handleSmartQueryRedirect(responseData: Record<string, unknown> | undefined) {
  const query = (responseData?.prefilled_query as string) || (responseData?.message as string) || ''
  const writeMode = responseData?.write_mode === true
  queryContextStore.setFromAssistant(
    query,
    writeMode ? 'write' : 'read',
    {
      entityId: currentContext.value.current_entity_id,
      entityType: currentContext.value.current_entity_type,
      entityName: currentContext.value.current_entity_name
    }
  )
  router.push('/smart-query')
  isOpen.value = false
}

function handleItemClick(item: { [key: string]: unknown }) {
  const entityType = item.entity_type as string | undefined
  const entitySlug = (item.entity_slug || item.slug) as string | undefined
  if (entityType && entitySlug) {
    handleNavigate(`/entities/${entityType}/${entitySlug}`)
  }
}

watch(localMode, (m) => { mode.value = m })

watch(() => messages.value.length, async () => {
  await nextTick()
  messagesContainer.value?.scrollToBottom()
})
</script>

<style scoped>
@import './styles/chat-assistant.css';
</style>
