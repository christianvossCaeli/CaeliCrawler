<template>
  <div class="chat-assistant-wrapper">
    <!-- Chat Bubble (FAB) -->
    <v-btn
      icon
      color="primary"
      size="large"
      class="chat-fab"
      elevation="8"
      @click="isOpen = !isOpen"
    >
      <v-badge v-if="hasUnread && !isOpen" color="error" dot floating>
        <v-icon>mdi-robot-happy</v-icon>
      </v-badge>
      <v-icon v-else>{{ isOpen ? 'mdi-close' : 'mdi-robot-happy' }}</v-icon>
    </v-btn>

    <!-- Backdrop -->
    <Transition name="fade">
      <div v-if="isOpen" class="chat-backdrop" @click="isOpen = false"></div>
    </Transition>

    <!-- Chat Panel -->
    <Transition name="slide">
      <div v-if="isOpen" class="chat-panel">
        <!-- Header -->
        <div class="chat-header">
          <div class="chat-header__left">
            <v-icon class="mr-2">mdi-robot-happy</v-icon>
            <span class="chat-header__title">{{ t('assistant.title') }}</span>
          </div>

          <div class="chat-header__right">
            <!-- Mode Toggle -->
            <div class="mode-toggle">
              <button
                :class="{ active: localMode === 'read' }"
                @click="localMode = 'read'"
                :title="t('assistant.modeRead')"
              >
                <v-icon size="18">mdi-magnify</v-icon>
              </button>
              <button
                :class="{ active: localMode === 'write' }"
                @click="localMode = 'write'"
                :title="t('assistant.modeWrite')"
              >
                <v-icon size="18">mdi-pencil</v-icon>
              </button>
            </div>

            <button class="header-btn" @click="clearConversation" :title="t('assistant.clear')">
              <v-icon size="20">mdi-refresh</v-icon>
            </button>

            <button class="header-btn" @click="isOpen = false" :title="t('assistant.close')">
              <v-icon size="20">mdi-close</v-icon>
            </button>
          </div>
        </div>

        <!-- Context Indicator -->
        <div v-if="currentContext.current_entity_name" class="context-bar">
          <v-icon size="14" class="mr-1">mdi-map-marker</v-icon>
          <span>{{ currentContext.current_entity_name }}</span>
          <span class="context-type">{{ currentContext.current_entity_type }}</span>
        </div>

        <!-- Quick Actions -->
        <div class="quick-actions">
          <div class="quick-actions__header" @click="quickActionsExpanded = !quickActionsExpanded">
            <span>
              <v-icon size="16" class="mr-1">mdi-lightning-bolt</v-icon>
              {{ t('assistant.quickActions') }}
            </span>
            <v-icon size="16">{{ quickActionsExpanded ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
          </div>
          <div v-if="quickActionsExpanded" class="quick-actions__content">
            <button
              v-for="action in quickActions"
              :key="action.id"
              class="quick-action-btn"
              @click="handleQuickAction(action)"
            >
              <v-icon size="14">{{ action.icon }}</v-icon>
              {{ action.label }}
            </button>
          </div>
        </div>

        <!-- Messages Area -->
        <div ref="messagesContainer" class="messages-area">
          <!-- Welcome -->
          <div v-if="messages.length === 0" class="welcome">
            <v-icon size="48" color="primary" class="mb-3">mdi-robot-happy-outline</v-icon>
            <div class="welcome__title">{{ t('assistant.welcomeTitle') }}</div>
            <div class="welcome__text">{{ t('assistant.welcomeText') }}</div>
          </div>

          <!-- Messages -->
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="message"
            :class="{ 'message--user': msg.role === 'user' }"
          >
            <div class="message__avatar" :class="{ 'message__avatar--user': msg.role === 'user' }">
              <v-icon size="16">
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
              <div v-html="formatMessage(msg.content)"></div>

              <!-- Query Results -->
              <div v-if="msg.response_type === 'query_result' && msg.response_data?.data?.items?.length" class="message__results">
                <button
                  v-for="(item, i) in msg.response_data.data.items"
                  :key="i"
                  class="result-item"
                  @click="handleItemClick(item)"
                >
                  {{ item.entity_name || item.name || 'Entity' }}
                </button>
              </div>

              <!-- Navigation -->
              <button
                v-if="msg.response_type === 'navigation' && msg.response_data?.target"
                class="nav-btn"
                @click="handleNavigate(msg.response_data.target.route)"
              >
                <v-icon size="14">mdi-arrow-right</v-icon>
                {{ t('assistant.goTo', { name: msg.response_data.target.entity_name || 'Seite' }) }}
              </button>

              <div class="message__time">{{ formatTime(msg.timestamp) }}</div>
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

        <!-- Input -->
        <div class="input-area" :class="{ 'input-area--write': localMode === 'write' }">
          <textarea
            v-model="inputText"
            :placeholder="localMode === 'write' ? t('assistant.placeholderWrite') : t('assistant.placeholderRead')"
            :rows="localMode === 'write' ? 4 : 1"
            @keydown.enter.exact.prevent="sendMessage"
            @input="autoResize"
            ref="textareaRef"
          ></textarea>
          <button
            class="send-btn"
            :disabled="!inputText.trim() || isLoading"
            @click="sendMessage"
          >
            <v-icon size="20">mdi-send</v-icon>
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useDisplay, useTheme } from 'vuetify'
import { useI18n } from 'vue-i18n'
import { useAssistant } from '@/composables/useAssistant'

const { t, locale } = useI18n()
const router = useRouter()
const { mobile } = useDisplay()
const theme = useTheme()

const {
  isOpen,
  isLoading,
  streamingStatus,
  messages,
  mode,
  suggestedActions,
  hasUnread,
  currentContext,
  send,
  clearConversation,
  handleSuggestedAction,
} = useAssistant()

const isDark = computed(() => theme.global.current.value.dark)
const isMobile = computed(() => mobile.value)
const inputText = ref('')
const localMode = ref(mode.value)
const messagesContainer = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const quickActionsExpanded = ref(true)

const quickActions = computed(() => {
  const actions = []
  const viewMode = currentContext.value.view_mode

  if (viewMode === 'detail' && currentContext.value.current_entity_id) {
    actions.push(
      { id: 'summary', label: t('assistant.summary'), icon: 'mdi-text-box-outline', query: '/summary' },
      { id: 'painpoints', label: 'Pain Points', icon: 'mdi-alert-circle-outline', query: 'Zeige Pain Points' },
    )
  } else if (viewMode === 'dashboard') {
    actions.push(
      { id: 'overview', label: t('assistant.overview'), icon: 'mdi-view-dashboard-outline', query: 'Gib mir einen Überblick' },
      { id: 'help', label: t('assistant.help'), icon: 'mdi-help-circle-outline', query: '/help' },
    )
  } else {
    actions.push(
      { id: 'search', label: t('assistant.search'), icon: 'mdi-magnify', query: '/search ' },
      { id: 'help', label: t('assistant.help'), icon: 'mdi-help-circle-outline', query: '/help' },
    )
  }

  return actions
})

function handleQuickAction(action: { query: string }) {
  inputText.value = action.query
  if (!action.query.endsWith(' ')) {
    sendMessage()
  }
}

function sendMessage() {
  if (!inputText.value.trim() || isLoading.value) return
  send(inputText.value.trim())
  inputText.value = ''
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
  }
}

function handleNavigate(route: string) {
  router.push(route)
  isOpen.value = false
}

function handleItemClick(item: any) {
  if (item.entity_type && (item.entity_slug || item.slug)) {
    const slug = item.entity_slug || item.slug
    handleNavigate(`/entities/${item.entity_type}/${slug}`)
  }
}

function autoResize(e: Event) {
  const el = e.target as HTMLTextAreaElement
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

function escapeHtml(text: string): string {
  const map: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }
  return text.replace(/[&<>"']/g, (c) => map[c])
}

function formatMessage(content: string): string {
  let f = escapeHtml(content)
  f = f.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
       .replace(/`(.+?)`/g, '<code>$1</code>')
       .replace(/\n/g, '<br>')
       .replace(/\[\[(\w+):([^:]+):([^\]]+)\]\]/g, '<span class="entity-link">$3</span>')
  return f
}

function formatTime(date: Date): string {
  return new Date(date).toLocaleTimeString(locale.value === 'de' ? 'de-DE' : 'en-US', {
    hour: '2-digit', minute: '2-digit'
  })
}

watch(localMode, (m) => { mode.value = m })

watch(() => messages.value.length, async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
})
</script>

<style scoped>
.chat-fab {
  position: fixed !important;
  bottom: 24px;
  right: 24px;
  z-index: 1000;
}

.chat-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 2000;
}

.chat-panel {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: 400px;
  max-width: 100vw;
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface));
  display: flex;
  flex-direction: column;
  z-index: 2001;
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.15);
}

@media (max-width: 500px) {
  .chat-panel {
    width: 100vw;
  }
}

/* Header - uses primary color */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
  flex-shrink: 0;
}

.chat-header__left {
  display: flex;
  align-items: center;
}

.chat-header__title {
  font-weight: 600;
  font-size: 1rem;
}

.chat-header__right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mode-toggle {
  display: flex;
  border: 1px solid rgba(var(--v-theme-on-primary), 0.4);
  border-radius: 6px;
  overflow: hidden;
}

.mode-toggle button {
  background: transparent;
  border: none;
  color: rgba(var(--v-theme-on-primary), 0.7);
  padding: 4px 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mode-toggle button.active {
  background: rgba(var(--v-theme-on-primary), 0.2);
  color: rgb(var(--v-theme-on-primary));
}

.mode-toggle button:first-child {
  border-right: 1px solid rgba(var(--v-theme-on-primary), 0.4);
}

.header-btn {
  background: transparent;
  border: none;
  color: rgba(var(--v-theme-on-primary), 0.8);
  padding: 6px;
  cursor: pointer;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-btn:hover {
  background: rgba(var(--v-theme-on-primary), 0.1);
  color: rgb(var(--v-theme-on-primary));
}

/* Context Bar */
.context-bar {
  display: flex;
  align-items: center;
  padding: 6px 16px;
  background: rgb(var(--v-theme-secondary));
  color: rgb(var(--v-theme-on-secondary));
  font-size: 0.75rem;
  flex-shrink: 0;
}

.context-type {
  margin-left: 8px;
  opacity: 0.7;
  font-size: 0.7rem;
}

/* Quick Actions */
.quick-actions {
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  background: rgba(var(--v-theme-on-surface), 0.04);
  flex-shrink: 0;
}

.quick-actions__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 500;
  color: rgba(var(--v-theme-on-surface), 0.7);
}

.quick-actions__content {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 0 16px 10px;
}

.quick-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-theme-on-surface), 0.2);
  border-radius: 16px;
  font-size: 0.75rem;
  color: rgb(var(--v-theme-on-surface));
  cursor: pointer;
}

.quick-action-btn:hover {
  background: rgb(var(--v-theme-secondary));
  border-color: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-secondary));
}

/* Messages Area */
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  padding: 24px;
}

.welcome__title {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 8px;
}

.welcome__text {
  font-size: 0.85rem;
  opacity: 0.7;
}

/* Messages */
.message {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.message--user {
  flex-direction: row-reverse;
}

.message__avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message__avatar--user {
  background: rgb(var(--v-theme-secondary));
  color: rgb(var(--v-theme-on-secondary));
}

.message__bubble {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 16px;
  font-size: 0.875rem;
  line-height: 1.5;
  word-break: break-word;
  background: rgba(var(--v-theme-on-surface), 0.08);
  color: rgb(var(--v-theme-on-surface));
  border-bottom-left-radius: 4px;
}

.message--user .message__bubble {
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
  border-bottom-left-radius: 16px;
  border-bottom-right-radius: 4px;
}

.message__bubble--error {
  background: rgba(var(--v-theme-error), 0.15) !important;
  color: rgb(var(--v-theme-error)) !important;
}

.message__bubble :deep(code) {
  background: rgba(var(--v-theme-on-surface), 0.1);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 0.85em;
}

.message__bubble :deep(.entity-link) {
  color: rgb(var(--v-theme-primary));
  font-weight: 500;
  cursor: pointer;
}

.message--user .message__bubble :deep(.entity-link) {
  color: rgb(var(--v-theme-on-primary));
  text-decoration: underline;
}

.message__time {
  font-size: 0.65rem;
  opacity: 0.6;
  margin-top: 4px;
}

.message__results {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
}

.result-item {
  padding: 3px 8px;
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-theme-on-surface), 0.2);
  border-radius: 12px;
  font-size: 0.75rem;
  cursor: pointer;
  color: rgb(var(--v-theme-on-surface));
}

.result-item:hover {
  background: rgb(var(--v-theme-secondary));
  border-color: rgb(var(--v-theme-primary));
}

.nav-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  padding: 6px 12px;
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
  border: none;
  border-radius: 16px;
  font-size: 0.8rem;
  cursor: pointer;
}

/* Loading */
.loading {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
}

.loading__avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading__dots {
  display: flex;
  gap: 4px;
}

.loading__dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgb(var(--v-theme-primary));
  animation: bounce 1.4s infinite ease-in-out both;
}

.loading__dots span:nth-child(1) { animation-delay: -0.32s; }
.loading__dots span:nth-child(2) { animation-delay: -0.16s; }
.loading__dots span:nth-child(3) { animation-delay: 0s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.5); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

.loading__status {
  font-size: 0.75rem;
  color: rgb(var(--v-theme-primary));
}

/* Suggestions */
.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 10px 16px;
  border-top: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  background: rgba(var(--v-theme-on-surface), 0.04);
  flex-shrink: 0;
}

.suggestion-btn {
  padding: 4px 10px;
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-theme-on-surface), 0.2);
  border-radius: 14px;
  font-size: 0.75rem;
  color: rgb(var(--v-theme-on-surface));
  cursor: pointer;
}

.suggestion-btn:hover {
  background: rgb(var(--v-theme-secondary));
  border-color: rgb(var(--v-theme-primary));
}

/* Input */
.input-area {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  background: rgb(var(--v-theme-surface));
  flex-shrink: 0;
}

.input-area textarea {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.2);
  border-radius: 20px;
  background: rgba(var(--v-theme-on-surface), 0.04);
  color: rgb(var(--v-theme-on-surface));
  font-size: 0.875rem;
  resize: none;
  outline: none;
  max-height: 120px;
  font-family: inherit;
}

.input-area--write textarea {
  min-height: 100px;
  max-height: 200px;
  border-radius: 12px;
}

.input-area textarea:focus {
  border-color: rgb(var(--v-theme-primary));
}

.input-area textarea::placeholder {
  color: rgba(var(--v-theme-on-surface), 0.5);
}

.send-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.send-btn:not(:disabled):hover {
  opacity: 0.9;
}

/* Transitions */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

.slide-enter-active, .slide-leave-active {
  transition: transform 0.3s ease;
}
.slide-enter-from, .slide-leave-to {
  transform: translateX(100%);
}
</style>
