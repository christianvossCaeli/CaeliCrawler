<template>
  <div ref="containerRef" class="messages-area">
    <!-- Welcome -->
    <div v-if="messages.length === 0" class="welcome">
      <v-icon size="48" color="primary" class="mb-3">mdi-robot-happy-outline</v-icon>
      <div class="welcome__title">{{ t('assistant.welcomeTitle') }}</div>
      <div class="welcome__text">{{ t('assistant.welcomeText') }}</div>
    </div>

    <!-- Messages -->
    <div
      v-for="msg in messages"
      :key="msg.id"
      class="message"
      :class="{ 'message--user': msg.role === 'user' }"
    >
      <div class="message__avatar" :class="{ 'message__avatar--user': msg.role === 'user' }">
        <v-icon size="x-small">
          {{ msg.role === 'user' ? 'mdi-account' : 'mdi-robot' }}
        </v-icon>
      </div>

      <div
        class="message__bubble"
        :class="{
          'message__bubble--user': msg.role === 'user',
          'message__bubble--error': msg.response_type === 'error'
        }"
      >
        <!-- eslint-disable-next-line vue/no-v-html -- Content is sanitized via DOMPurify in formatMessage -->
        <div v-html="formatMessageContent(msg.content)"></div>

        <!-- Query Results -->
        <div v-if="getQueryResultData(msg)?.data?.items?.length" class="message__results">
          <button
            v-for="(item, i) in getQueryResultData(msg)!.data!.items"
            :key="i"
            class="result-item"
            @click="$emit('item-click', item)"
          >
            {{ item.entity_name || item.name || 'Entity' }}
          </button>
        </div>

        <!-- Navigation -->
        <button
          v-if="getNavigationData(msg)?.target"
          class="nav-btn"
          @click="$emit('navigate', getNavigationData(msg)!.target.route || '')"
        >
          <v-icon size="14">mdi-arrow-right</v-icon>
          {{ t('assistant.goTo', { name: getNavigationData(msg)!.target.entity_name || 'Seite' }) }}
        </button>

        <!-- Redirect to Smart Query -->
        <button
          v-if="msg.response_type === 'redirect_to_smart_query'"
          class="nav-btn nav-btn--smart-query"
          @click="$emit('smart-query-redirect', msg.response_data as Record<string, unknown> | undefined)"
        >
          <v-icon size="14">mdi-magnify</v-icon>
          {{ t('assistant.openSmartQuery') }}
        </button>

        <div class="message__footer">
          <div class="message__time">{{ formatTime(msg.timestamp) }}</div>
          <AiProviderBadge
            v-if="msg.role === 'assistant'"
            purpose="assistant"
            compact
            variant="text"
            class="message__provider"
          />
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="loading">
      <div class="loading__avatar">
        <v-icon size="14">mdi-robot</v-icon>
      </div>
      <div class="loading__dots">
        <span></span><span></span><span></span>
      </div>
      <span v-if="streamingStatus" class="loading__status">{{ streamingStatus }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatMessage, formatMessageTime } from '@/utils/messageFormatting'
import AiProviderBadge from '@/components/common/AiProviderBadge.vue'
import type {
  ConversationMessage,
  QueryResultResponse,
  NavigationResponse,
} from '@/composables/assistant/types'

const props = defineProps<{
  messages: ConversationMessage[]
  isLoading: boolean
  streamingStatus: string
  locale: string
}>()

defineEmits<{
  navigate: [route: string]
  'smart-query-redirect': [data: Record<string, unknown> | undefined]
  'item-click': [item: Record<string, unknown>]
}>()

const { t } = useI18n()
const containerRef = ref<HTMLElement | null>(null)

// Type guard helpers for response data
function getQueryResultData(msg: ConversationMessage): QueryResultResponse | undefined {
  if (msg.response_type === 'query_result' && msg.response_data) {
    return msg.response_data as QueryResultResponse
  }
  return undefined
}

function getNavigationData(msg: ConversationMessage): NavigationResponse | undefined {
  if (msg.response_type === 'navigation' && msg.response_data) {
    return msg.response_data as NavigationResponse
  }
  return undefined
}

function formatMessageContent(content: string): string {
  return formatMessage(content)
}

function formatTime(date: Date): string {
  return formatMessageTime(date, props.locale)
}

function scrollToBottom() {
  if (containerRef.value) {
    containerRef.value.scrollTop = containerRef.value.scrollHeight
  }
}

defineExpose({ scrollToBottom })
</script>

<style scoped>
@import './styles/chat-assistant.css';
</style>
