<template>
  <v-card class="input-card" :class="{ 'input-card--active': modelValue?.trim() || attachments.length > 0 }">
    <!-- Attachment Preview inside card -->
    <div v-if="attachments.length > 0" class="attachment-preview pa-3 pb-0">
      <div class="d-flex flex-wrap ga-2">
        <v-chip
          v-for="attachment in attachments"
          :key="attachment.id"
          closable
          @click:close="$emit('removeAttachment', attachment.id)"
          color="primary"
          variant="tonal"
          size="small"
        >
          <v-avatar start size="20" v-if="attachment.preview">
            <v-img :src="attachment.preview" />
          </v-avatar>
          <v-icon v-else start size="16">{{ getAttachmentIcon(attachment.contentType) }}</v-icon>
          {{ attachment.filename }}
        </v-chip>
      </div>
    </div>

    <!-- Textarea -->
    <v-textarea
      v-model="modelValue"
      :placeholder="placeholder"
      rows="2"
      auto-grow
      max-rows="8"
      variant="plain"
      hide-details
      class="input-textarea"
      :disabled="disabled"
      @paste="$emit('paste', $event)"
      @keydown.enter.ctrl="$emit('submit')"
      @keydown.enter.meta="$emit('submit')"
    />

    <!-- Interim transcript overlay -->
    <div v-if="interimTranscript" class="interim-transcript px-4 pb-2">
      <span class="text-caption text-medium-emphasis font-italic">
        <v-icon size="12" class="mr-1">mdi-microphone</v-icon>
        {{ interimTranscript }}
      </span>
    </div>

    <v-divider />

    <!-- Action Bar -->
    <div class="input-actions">
      <div class="action-buttons d-flex ga-1">
        <!-- Attachment Button -->
        <v-btn
          icon
          variant="text"
          size="small"
          :disabled="disabled || loading || uploading"
          :loading="uploading"
          :aria-label="t('assistant.attachFile')"
          :aria-busy="uploading"
          @click="$emit('triggerFileInput')"
        >
          <v-icon size="20" aria-hidden="true">mdi-paperclip</v-icon>
          <v-tooltip activator="parent" location="top">
            {{ t('assistant.attachFile') }}
          </v-tooltip>
        </v-btn>

        <!-- Voice Button -->
        <v-btn
          v-if="hasMicrophone"
          icon
          variant="text"
          size="small"
          :color="isListening ? 'error' : undefined"
          :class="{ 'voice-btn-listening': isListening }"
          :disabled="disabled || loading"
          :aria-label="isListening ? t('smartQueryView.voice.stopRecording') : t('smartQueryView.voice.startRecording')"
          :aria-pressed="isListening"
          @click="$emit('toggleVoice')"
        >
          <v-icon size="20" aria-hidden="true">{{ isListening ? 'mdi-microphone-off' : 'mdi-microphone' }}</v-icon>
          <v-tooltip activator="parent" location="top">
            {{ isListening ? t('smartQueryView.voice.stopRecording') : t('smartQueryView.voice.startRecording') }}
          </v-tooltip>
        </v-btn>

        <!-- Write Mode Indicator -->
        <v-chip v-if="writeMode && !disabled" color="warning" size="x-small" variant="flat" class="ml-2">
          <v-icon start size="12">mdi-eye</v-icon>
          {{ t('smartQueryView.mode.previewFirst') }}
        </v-chip>
      </div>

      <!-- Submit Button -->
      <v-btn
        v-if="!disabled"
        :color="submitButtonColor"
        rounded="pill"
        :loading="loading"
        :disabled="!modelValue?.trim() && attachments.length === 0"
        @click="$emit('submit')"
        class="submit-btn"
      >
        <v-icon start>{{ submitButtonIcon }}</v-icon>
        {{ submitButtonText }}
      </v-btn>
    </div>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

interface Attachment {
  id: string
  filename: string
  contentType: string
  size: number
  preview?: string
}

type QueryMode = 'read' | 'write' | 'plan'

const modelValue = defineModel<string>()

const props = defineProps<{
  attachments: Attachment[]
  mode: QueryMode
  disabled: boolean
  loading: boolean
  uploading: boolean
  isListening: boolean
  hasMicrophone: boolean
  interimTranscript: string
}>()

defineEmits<{
  submit: []
  paste: [event: ClipboardEvent]
  removeAttachment: [id: string]
  triggerFileInput: []
  toggleVoice: []
}>()

const { t } = useI18n()

const writeMode = computed(() => props.mode === 'write')

const placeholder = computed(() => {
  if (props.isListening) return t('smartQueryView.input.placeholderListening')
  if (props.mode === 'plan') return t('smartQueryView.plan.placeholder')
  return props.mode === 'write'
    ? t('smartQueryView.input.placeholderWrite')
    : t('smartQueryView.input.placeholderRead')
})

const submitButtonColor = computed(() => {
  if (props.attachments.length > 0) return 'info'
  if (props.mode === 'plan') return 'info'
  return props.mode === 'write' ? 'warning' : 'primary'
})

const submitButtonIcon = computed(() => {
  if (props.attachments.length > 0) return 'mdi-image-search'
  if (props.mode === 'plan') return 'mdi-send'
  return props.mode === 'write' ? 'mdi-eye' : 'mdi-send'
})

const submitButtonText = computed(() => {
  if (props.attachments.length > 0) return t('smartQueryView.actions.analyzeImage')
  if (props.mode === 'plan') return t('smartQueryView.actions.query')
  return props.mode === 'write' ? t('smartQueryView.actions.preview') : t('smartQueryView.actions.query')
})

function getAttachmentIcon(contentType: string): string {
  if (contentType.startsWith('image/')) {
    return 'mdi-image'
  }
  if (contentType === 'application/pdf') {
    return 'mdi-file-pdf-box'
  }
  return 'mdi-file'
}
</script>

<style scoped>
.input-card {
  border-radius: 16px !important;
  overflow: hidden;
  transition: box-shadow 0.3s ease, border-color 0.3s ease;
  border: 2px solid transparent;
  position: sticky;
  top: calc(var(--v-layout-top, 0px) + 12px);
  z-index: 5;
}

.input-card--active {
  border-color: rgba(var(--v-theme-primary), 0.3);
  box-shadow: 0 4px 20px rgba(var(--v-theme-primary), 0.1);
}

.input-textarea {
  padding: 16px 20px 8px;
}

.input-textarea :deep(.v-field__input) {
  font-size: 1rem;
  line-height: 1.6;
}

.interim-transcript {
  background: rgba(var(--v-theme-error), 0.05);
  margin: 0 16px 8px;
  padding: 8px 12px;
  border-radius: 8px;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: rgba(var(--v-theme-surface-variant), 0.3);
}

.submit-btn {
  padding-left: 20px;
  padding-right: 20px;
}

/* Voice Button Animation */
.voice-btn-listening {
  animation: pulse-voice 1.5s ease-in-out infinite;
}

@keyframes pulse-voice {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.15);
    opacity: 0.85;
  }
}
</style>
