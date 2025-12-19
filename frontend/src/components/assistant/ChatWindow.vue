<template>
  <div class="chat-window">
    <!-- Header -->
    <div class="chat-window__header">
      <div class="d-flex align-center">
        <v-icon class="mr-2" color="on-primary">mdi-robot-happy</v-icon>
        <div>
          <div class="text-subtitle-1 font-weight-medium">{{ t('assistant.title') }}</div>
          <div class="text-caption" style="opacity: 0.85">{{ contextLabel }}</div>
        </div>
      </div>
      <div class="d-flex align-center">
        <!-- Mode Toggle -->
        <v-btn-toggle
          v-model="localMode"
          mandatory
          density="compact"
          variant="outlined"
          divided
          class="mr-2 header-toggle"
        >
          <v-btn value="read" size="small">
            <v-icon size="small">mdi-magnify</v-icon>
            <v-tooltip activator="parent" location="bottom">{{ t('assistant.modeRead') }}</v-tooltip>
          </v-btn>
          <v-btn value="write" size="small">
            <v-icon size="small">mdi-pencil</v-icon>
            <v-tooltip activator="parent" location="bottom">{{ t('assistant.modeWrite') }}</v-tooltip>
          </v-btn>
        </v-btn-toggle>

        <!-- Clear Button -->
        <v-btn
          icon="mdi-refresh"
          variant="text"
          size="small"
          class="header-btn"
          @click="$emit('clear')"
        >
          <v-icon>mdi-refresh</v-icon>
          <v-tooltip activator="parent" location="bottom">{{ t('assistant.clear') }}</v-tooltip>
        </v-btn>

        <!-- Close Button -->
        <v-btn
          icon="mdi-close"
          variant="text"
          size="small"
          class="header-btn"
          @click="$emit('close')"
        >
          <v-icon>mdi-close</v-icon>
          <v-tooltip activator="parent" location="bottom">{{ t('assistant.close') }}</v-tooltip>
        </v-btn>
      </div>
    </div>

    <!-- Context Indicator -->
    <div v-if="context.current_entity_name" class="chat-window__context">
      <v-icon size="x-small" class="mr-1">mdi-map-marker</v-icon>
      <span>{{ context.current_entity_name }}</span>
      <v-chip size="x-small" variant="text" class="ml-1">
        {{ context.current_entity_type }}
      </v-chip>
    </div>

    <!-- Quick Actions Panel -->
    <QuickActionsPanel
      :context="context"
      :mode="mode"
      @action="handleQuickAction"
      @start-wizard="$emit('start-wizard', $event)"
    />

    <!-- Due Reminders Notification -->
    <ReminderNotification
      v-if="dueReminders && dueReminders.length > 0"
      :due-reminders="dueReminders"
      @dismiss="$emit('reminder-dismiss', $event)"
      @snooze="(id, minutes) => $emit('reminder-snooze', id, minutes)"
      @navigate="$emit('navigate', $event)"
    />

    <!-- Messages -->
    <div ref="messagesContainer" class="chat-window__messages">
      <!-- Welcome message if empty -->
      <div v-if="messages.length === 0" class="chat-window__welcome">
        <v-icon size="48" color="primary" class="mb-4">mdi-robot-happy-outline</v-icon>
        <div class="text-h6 mb-2">{{ t('assistant.welcomeTitle') }}</div>
        <div class="text-body-2 text-medium-emphasis mb-4">
          {{ t('assistant.welcomeText') }}
        </div>
        <i18n-t keypath="assistant.welcomeHint" tag="div" class="text-caption text-medium-emphasis">
          <template #command>
            <code>/help</code>
          </template>
        </i18n-t>

        <!-- Proactive Insights -->
        <div v-if="insights && insights.length > 0" class="chat-window__insights mt-4">
          <div class="text-subtitle-2 mb-2 d-flex align-center">
            <v-icon size="small" class="mr-1">mdi-lightbulb-outline</v-icon>
            {{ t('assistant.insightsTitle') }}
          </div>
          <v-list density="compact" class="insights-list">
            <v-list-item
              v-for="(insight, idx) in insights"
              :key="idx"
              :class="`insight-item insight-item--${insight.color}`"
              @click="$emit('insight-action', insight.action)"
            >
              <template v-slot:prepend>
                <v-icon :color="insight.color" size="small">{{ insight.icon }}</v-icon>
              </template>
              <v-list-item-title class="text-body-2">{{ insight.message }}</v-list-item-title>
            </v-list-item>
          </v-list>
        </div>
      </div>

      <!-- Message List -->
      <ChatMessage
        v-for="(msg, idx) in messages"
        :key="idx"
        :message="msg"
        @navigate="$emit('navigate', $event)"
        @item-click="handleItemClick"
        @command="handleCommand"
        @entity-click="handleEntityClick"
      />

      <!-- Pending Action Preview -->
      <ActionPreview
        v-if="pendingAction"
        :message="pendingActionMessage"
        :action="pendingAction"
        :loading="isLoading"
        @confirm="$emit('action-confirm', pendingAction)"
        @cancel="$emit('action-cancel')"
      />

      <!-- Batch Action Progress -->
      <BatchActionProgress
        v-if="activeBatch"
        :status="activeBatch"
        :preview="batchPreview || []"
        :is-dry-run="isBatchDryRun"
        @confirm="$emit('batch-confirm')"
        @cancel="$emit('batch-cancel')"
        @close="$emit('batch-close')"
      />

      <!-- Active Wizard Step -->
      <WizardStep
        v-if="activeWizard"
        :wizard-state="activeWizard.state"
        :current-step="activeWizard.currentStep"
        :can-go-back="activeWizard.canGoBack"
        :progress="activeWizard.progress"
        :is-loading="isWizardLoading"
        :wizard-name="activeWizard.name"
        :wizard-icon="activeWizard.icon"
        @next="$emit('wizard-next', $event)"
        @back="$emit('wizard-back')"
        @cancel="$emit('wizard-cancel')"
      />

      <!-- Loading indicator with streaming status -->
      <div v-if="isLoading && !pendingAction" class="chat-window__loading">
        <TypingIndicator />
        <div v-if="isStreaming && streamingStatus" class="chat-window__loading-status">
          {{ streamingStatus }}
        </div>
      </div>
    </div>

    <!-- Suggested Actions -->
    <div v-if="suggestedActions.length > 0" class="chat-window__suggestions">
      <v-chip
        v-for="action in suggestedActions"
        :key="action.value"
        size="small"
        variant="tonal"
        class="mr-1 mb-1"
        @click="$emit('action', action)"
      >
        {{ action.label }}
      </v-chip>
    </div>

    <!-- Attachment Preview -->
    <div v-if="pendingAttachments && pendingAttachments.length > 0" class="chat-window__attachments">
      <v-chip
        v-for="att in pendingAttachments"
        :key="att.id"
        size="small"
        closable
        class="mr-1 mb-1"
        @click:close="emit('remove-attachment', att.id)"
      >
        <v-avatar v-if="att.preview" start size="24">
          <v-img :src="att.preview" />
        </v-avatar>
        <v-icon v-else start size="small">{{ getFileIcon(att.contentType) }}</v-icon>
        <span class="attachment-name">{{ att.filename }}</span>
      </v-chip>
    </div>

    <!-- Input Area -->
    <div class="chat-window__input">
      <!-- Hidden file input -->
      <input
        ref="fileInput"
        type="file"
        accept="image/*,.pdf"
        hidden
        @change="handleFileSelect"
      />

      <!-- Attachment button -->
      <v-btn
        icon
        variant="text"
        size="small"
        :loading="isUploading"
        @click="triggerFileInput"
      >
        <v-icon>mdi-attachment</v-icon>
        <v-tooltip activator="parent" location="top">{{ t('assistant.attach') }}</v-tooltip>
      </v-btn>

      <v-textarea
        v-model="inputText"
        :placeholder="inputPlaceholder"
        variant="outlined"
        density="compact"
        rows="1"
        max-rows="4"
        auto-grow
        hide-details
        class="chat-window__textarea"
        @keydown.enter.exact.prevent="sendMessage"
      >
        <template v-slot:append-inner>
          <!-- Voice Input -->
          <v-btn
            v-if="hasMicrophone"
            :icon="isListening ? 'mdi-microphone-off' : 'mdi-microphone'"
            :color="isListening ? 'error' : 'default'"
            variant="text"
            size="small"
            :class="{ 'voice-listening': isListening }"
            @click="toggleVoice"
          >
            <v-tooltip activator="parent" location="top">
              {{ isListening ? t('assistant.voiceStop') : t('assistant.voiceStart') }}
            </v-tooltip>
          </v-btn>
        </template>
      </v-textarea>

      <v-btn
        :icon="true"
        color="primary"
        :disabled="!inputText.trim() || isLoading"
        class="ml-2"
        @click="sendMessage"
      >
        <v-icon>mdi-send</v-icon>
      </v-btn>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import ChatMessage from './ChatMessage.vue'
import ActionPreview from './ActionPreview.vue'
import TypingIndicator from './TypingIndicator.vue'
import QuickActionsPanel from './QuickActionsPanel.vue'
import BatchActionProgress from './BatchActionProgress.vue'
import WizardStep from './WizardStep.vue'
import ReminderNotification from './ReminderNotification.vue'
import type { QuickAction } from './QuickActionsPanel.vue'
import type { BatchStatus, BatchPreviewEntity } from './BatchActionProgress.vue'
import type { WizardStepDef, WizardState } from './WizardStep.vue'
import { useSpeechRecognition } from '@/composables/useSpeechRecognition'
import type { ConversationMessage, SuggestedAction, AssistantContext, AttachmentInfo, Insight, ActiveWizard, Reminder } from '@/composables/useAssistant'

const { t } = useI18n()

const props = defineProps<{
  messages: ConversationMessage[]
  context: AssistantContext
  isLoading: boolean
  isStreaming?: boolean
  isUploading?: boolean
  streamingStatus?: string
  mode: 'read' | 'write'
  suggestedActions: SuggestedAction[]
  pendingAction: any
  pendingAttachments?: AttachmentInfo[]
  // Batch operation props
  activeBatch?: BatchStatus | null
  batchPreview?: BatchPreviewEntity[]
  isBatchDryRun?: boolean
  // Insights props
  insights?: Insight[]
  // Wizard props
  activeWizard?: ActiveWizard | null
  isWizardLoading?: boolean
  // Reminder props
  dueReminders?: Reminder[]
}>()

const emit = defineEmits<{
  send: [text: string]
  clear: []
  close: []
  'file-upload': [file: File]
  'remove-attachment': [attachmentId: string]
  navigate: [route: string]
  action: [action: SuggestedAction]
  'action-confirm': [action: any]
  'action-cancel': []
  'mode-change': [mode: 'read' | 'write']
  // Batch operation emits
  'batch-confirm': []
  'batch-cancel': []
  'batch-close': []
  // Insights emit
  'insight-action': [action: { type: string; value: string }]
  // Wizard emits
  'wizard-next': [value: any]
  'wizard-back': []
  'wizard-cancel': []
  'start-wizard': [wizardType: string]
  // Reminder emits
  'reminder-dismiss': [reminderId: string]
  'reminder-snooze': [reminderId: string, minutes: number]
}>()

// Local state
const inputText = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const localMode = ref(props.mode)
const fileInput = ref<HTMLInputElement | null>(null)

// Computed
const isUploading = computed(() => props.isUploading ?? false)

// Speech recognition
const {
  isListening,
  hasMicrophone,
  transcript,
  toggleListening,
  clearTranscript
} = useSpeechRecognition()

// Computed
const contextLabel = computed(() => {
  if (props.context.current_entity_name) {
    return `${props.context.current_entity_name} (${props.context.current_entity_type})`
  }
  return props.context.view_mode === 'dashboard' ? t('assistant.dashboard') : props.context.current_route
})

const inputPlaceholder = computed(() => {
  if (isListening.value) {
    return t('assistant.placeholderVoice')
  }
  return localMode.value === 'write'
    ? t('assistant.placeholderWrite')
    : t('assistant.placeholderRead')
})

const pendingActionMessage = computed(() => {
  if (!props.pendingAction) return ''
  return t('assistant.confirmAction')
})

// Methods
function sendMessage() {
  if (!inputText.value.trim() || props.isLoading) return

  emit('send', inputText.value.trim())
  inputText.value = ''
  clearTranscript()
}

function handleCommand(command: string) {
  inputText.value = command
  sendMessage()
}

function handleItemClick(item: any) {
  // Navigate to entity detail page if possible
  if (item.entity_type && (item.entity_slug || item.slug)) {
    const slug = item.entity_slug || item.slug
    emit('navigate', `/entities/${item.entity_type}/${slug}`)
  } else if (item.entity_id) {
    // Fallback: search for this entity
    inputText.value = t('assistant.showDetailsFor', { name: item.entity_name || item.name || 'Entity' })
    sendMessage()
  }
}

function handleEntityClick(entityType: string, entitySlug: string) {
  // Navigate to the entity detail page
  emit('navigate', `/entities/${entityType}/${entitySlug}`)
}

function toggleVoice() {
  if (isListening.value) {
    toggleListening()
  } else {
    clearTranscript()
    inputText.value = ''
    toggleListening()
  }
}

// Trigger file input click
function triggerFileInput() {
  fileInput.value?.click()
}

// Handle file selection
function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) {
    emit('file-upload', file)
  }
  // Reset input so same file can be selected again
  input.value = ''
}

// Get icon for file type
function getFileIcon(contentType: string): string {
  if (contentType.startsWith('image/')) {
    return 'mdi-image'
  }
  if (contentType === 'application/pdf') {
    return 'mdi-file-pdf-box'
  }
  return 'mdi-file'
}

// Handle quick action click
function handleQuickAction(action: QuickAction) {
  // If action has a specific action type, handle it
  if (action.action === 'edit' || action.action === 'create') {
    // For edit/create, put the query in input for user to complete
    inputText.value = action.query
  } else {
    // For other actions, send directly
    emit('send', action.query)
  }
}

// Watch transcript
watch(transcript, (newVal) => {
  if (newVal) {
    inputText.value = newVal
  }
})

// Watch mode
watch(localMode, (newMode) => {
  emit('mode-change', newMode)
})

// Scroll to bottom when messages change or during streaming
watch(
  () => [props.messages.length, props.messages[props.messages.length - 1]?.content],
  async () => {
    await nextTick()
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  },
  { deep: true }
)
</script>

<style scoped>
.chat-window {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface));
}

.chat-window__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid rgb(var(--v-theme-outline-variant));
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
}

.chat-window__context {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  background: rgb(var(--v-theme-primary-container));
  color: rgb(var(--v-theme-on-primary-container));
  font-size: 0.75rem;
}

.chat-window__messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  scroll-behavior: smooth;
}

.chat-window__welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  padding: 24px;
}

.chat-window__welcome code {
  background: rgb(var(--v-theme-surface-variant));
  padding: 2px 6px;
  border-radius: 4px;
}

.chat-window__suggestions {
  padding: 8px 16px;
  border-top: 1px solid rgb(var(--v-theme-outline-variant));
  background: rgb(var(--v-theme-surface-variant));
}

.chat-window__attachments {
  display: flex;
  flex-wrap: wrap;
  padding: 8px 16px 0;
  border-top: 1px solid rgb(var(--v-theme-outline-variant));
  background: rgb(var(--v-theme-surface-variant));
}

.chat-window__attachments .attachment-name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-window__input {
  display: flex;
  align-items: flex-end;
  padding: 12px 16px;
  border-top: 1px solid rgb(var(--v-theme-outline-variant));
  background: rgb(var(--v-theme-surface));
}

.chat-window__textarea {
  flex: 1;
}

.chat-window__loading {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.chat-window__loading-status {
  font-size: 0.75rem;
  color: rgb(var(--v-theme-primary));
  animation: fade-in 0.3s ease-out;
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.voice-listening {
  animation: pulse-voice 1.5s ease-in-out infinite;
}

@keyframes pulse-voice {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.15); }
}

.chat-window__insights {
  width: 100%;
  max-width: 320px;
}

.insights-list {
  background: transparent !important;
  padding: 0;
}

.insight-item {
  border-radius: 8px;
  margin-bottom: 4px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.insight-item:hover {
  background: rgb(var(--v-theme-surface-variant));
}

.insight-item--primary {
  border-left: 3px solid rgb(var(--v-theme-primary));
}

.insight-item--info {
  border-left: 3px solid rgb(var(--v-theme-info));
}

.insight-item--success {
  border-left: 3px solid rgb(var(--v-theme-success));
}

.insight-item--warning {
  border-left: 3px solid rgb(var(--v-theme-warning));
}

.insight-item--error {
  border-left: 3px solid rgb(var(--v-theme-error));
}

/* Header button styles for proper contrast */
.header-btn {
  color: rgb(var(--v-theme-on-primary)) !important;
}

.header-btn:hover {
  background: rgba(var(--v-theme-on-primary), 0.1) !important;
}

.header-toggle {
  border-color: rgba(var(--v-theme-on-primary), 0.4) !important;
}

.header-toggle :deep(.v-btn) {
  color: rgb(var(--v-theme-on-primary)) !important;
  border-color: rgba(var(--v-theme-on-primary), 0.4) !important;
}

.header-toggle :deep(.v-btn--active) {
  background: rgba(var(--v-theme-on-primary), 0.2) !important;
}
</style>
