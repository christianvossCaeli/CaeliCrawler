<template>
  <div class="chat-input-wrapper">
    <div
      class="chat-input-card"
      :class="{ 'chat-input-card--active': hasContent }"
    >
      <!-- Attachments Preview -->
      <div v-if="attachments.length > 0" class="chat-attachments">
        <div
          v-for="attachment in attachments"
          :key="attachment.id"
          class="chat-attachment"
        >
          <img
            v-if="attachment.preview"
            :src="attachment.preview"
            :alt="attachment.filename"
            class="chat-attachment__preview"
          />
          <v-icon v-else size="18">{{ getAttachmentIcon(attachment.contentType) }}</v-icon>
          <span>{{ attachment.filename }}</span>
          <v-icon
            size="16"
            class="chat-attachment__remove"
            @click="$emit('removeAttachment', attachment.id)"
          >
            mdi-close
          </v-icon>
        </div>
      </div>

      <!-- Main Textarea -->
      <v-textarea
        ref="textareaRef"
        v-model="internalValue"
        :placeholder="placeholder"
        rows="1"
        auto-grow
        max-rows="8"
        variant="plain"
        hide-details
        class="chat-input__textarea"
        :disabled="disabled"
        @paste="$emit('paste', $event)"
        @keydown.enter.exact.prevent="handleSubmit"
        @keydown.enter.shift.stop
      />

      <!-- Interim Transcript -->
      <div v-if="interimTranscript" class="interim-transcript px-6 pb-2">
        <span class="text-caption text-medium-emphasis font-italic">
          <v-icon size="12" class="mr-1">mdi-microphone</v-icon>
          {{ interimTranscript }}
        </span>
      </div>

      <!-- Actions Bar -->
      <div class="chat-input__actions">
        <div class="chat-input__left-actions">
          <!-- Attachment Button -->
          <v-btn
            icon
            variant="text"
            size="small"
            class="chat-input__action-btn"
            :disabled="disabled || loading || uploading"
            :loading="uploading"
            :aria-label="t('chatHome.input.attachFile')"
            @click="$emit('triggerFileInput')"
          >
            <v-icon size="20">mdi-paperclip</v-icon>
            <v-tooltip activator="parent" location="top">
              {{ t('chatHome.input.attachFile') }}
            </v-tooltip>
          </v-btn>

          <!-- Voice Button -->
          <v-btn
            v-if="hasMicrophone"
            icon
            variant="text"
            size="small"
            class="chat-input__action-btn"
            :color="isListening ? 'error' : undefined"
            :disabled="disabled || loading"
            :aria-label="isListening ? t('chatHome.input.stopRecording') : t('chatHome.input.startRecording')"
            @click="$emit('toggleVoice')"
          >
            <v-icon size="20">{{ isListening ? 'mdi-microphone-off' : 'mdi-microphone' }}</v-icon>
            <v-tooltip activator="parent" location="top">
              {{ isListening ? t('chatHome.input.stopRecording') : t('chatHome.input.startRecording') }}
            </v-tooltip>
          </v-btn>

          <!-- Mode Chip -->
          <v-chip
            v-if="mode !== 'read'"
            size="x-small"
            :color="mode === 'write' ? 'warning' : 'info'"
            variant="flat"
            class="chat-input__mode"
          >
            <v-icon start size="12">{{ mode === 'write' ? 'mdi-pencil' : 'mdi-lightbulb-outline' }}</v-icon>
            {{ mode === 'write' ? t('chatHome.mode.write') : t('chatHome.mode.plan') }}
          </v-chip>
        </div>

        <!-- Submit Button -->
        <v-btn
          :color="submitColor"
          :disabled="!canSubmit"
          :loading="loading"
          class="chat-input__submit"
          :class="{ 'chat-input__submit--icon-only': !hasContent }"
          @click="handleSubmit"
        >
          <v-icon :size="hasContent ? 18 : 20">mdi-arrow-up</v-icon>
          <span v-if="hasContent" class="ml-1">{{ t('chatHome.input.send') }}</span>
        </v-btn>
      </div>
    </div>

    <!-- Hidden File Input -->
    <input
      ref="fileInputRef"
      type="file"
      multiple
      accept="image/*,.pdf"
      style="display: none"
      @change="handleFileChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

interface Attachment {
  id: string
  filename: string
  contentType: string
  size: number
  preview?: string
}

type QueryMode = 'read' | 'write' | 'plan'

const props = withDefaults(defineProps<{
  modelValue: string
  attachments?: Attachment[]
  mode?: QueryMode
  disabled?: boolean
  loading?: boolean
  uploading?: boolean
  isListening?: boolean
  hasMicrophone?: boolean
  interimTranscript?: string
}>(), {
  attachments: () => [],
  mode: 'read',
  disabled: false,
  loading: false,
  uploading: false,
  isListening: false,
  hasMicrophone: false,
  interimTranscript: ''
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  submit: []
  paste: [event: ClipboardEvent]
  removeAttachment: [id: string]
  triggerFileInput: []
  toggleVoice: []
  fileSelect: [files: FileList]
}>()

const { t } = useI18n()

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const textareaRef = ref<any>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)

const internalValue = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value)
})

const hasContent = computed(() =>
  props.modelValue?.trim().length > 0 || props.attachments.length > 0
)

const canSubmit = computed(() =>
  hasContent.value && !props.disabled && !props.loading
)

const placeholder = computed(() => {
  if (props.isListening) return t('chatHome.input.listening')
  if (props.mode === 'plan') return t('chatHome.input.placeholderPlan')
  if (props.mode === 'write') return t('chatHome.input.placeholderWrite')
  return t('chatHome.input.placeholder')
})

const submitColor = computed(() => {
  if (props.mode === 'write') return 'warning'
  if (props.mode === 'plan') return 'info'
  return 'primary'
})

function handleSubmit() {
  if (canSubmit.value) {
    emit('submit')
  }
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    emit('fileSelect', input.files)
    input.value = ''
  }
}

function getAttachmentIcon(contentType: string): string {
  if (contentType.startsWith('image/')) return 'mdi-image'
  if (contentType === 'application/pdf') return 'mdi-file-pdf-box'
  return 'mdi-file'
}

// Expose method to trigger file input
watch(() => props.uploading, () => {
  // Potential cleanup
})

// Focus textarea on mount
onMounted(() => {
  nextTick(() => {
    const textarea = textareaRef.value?.$el?.querySelector('textarea')
    if (textarea) {
      textarea.focus()
    }
  })
})

// Expose file input trigger
defineExpose({
  triggerFileInput: () => fileInputRef.value?.click(),
  focus: () => {
    const textarea = textareaRef.value?.$el?.querySelector('textarea')
    if (textarea) textarea.focus()
  }
})
</script>
