<template>
  <div class="smart-query-input">
    <SmartQueryInputCard
      :model-value="modelValue"
      :attachments="attachments"
      :mode="mode"
      :disabled="disabled"
      :loading="loading"
      :uploading="uploading"
      :is-listening="isListening"
      :has-microphone="hasMicrophone"
      :interim-transcript="interimTranscript"
      class="mb-6"
      @update:model-value="$emit('update:modelValue', $event ?? '')"
      @submit="$emit('submit')"
      @paste="handlePaste"
      @remove-attachment="$emit('remove-attachment', $event)"
      @trigger-file-input="triggerFileInput"
      @toggle-voice="$emit('toggle-voice')"
    />

    <input
      ref="fileInputRef"
      type="file"
      accept="image/png,image/jpeg,image/gif,image/webp,application/pdf"
      style="display: none"
      multiple
      @change="handleFileSelect"
    />

    <!-- Plan Mode Chat Interface -->
    <v-card v-if="mode === 'plan'" class="plan-mode-card mb-6">
      <PlanModeChat
        :conversation="planConversation"
        :loading="planLoading"
        :generated-prompt="generatedPrompt"
        @send="(msg) => $emit('plan-send', msg)"
        @adopt-prompt="(prompt, adoptMode) => $emit('adopt-prompt', prompt, adoptMode)"
        @reset="$emit('plan-reset')"
        @save-as-summary="(prompt) => $emit('save-as-summary', prompt)"
      />
    </v-card>

    <!-- Example Queries (only for read/write modes) -->
    <SmartQueryExamples
      v-if="showExamples && mode !== 'plan'"
      :examples="examples"
      :write-mode="mode === 'write'"
      class="mb-6"
      @select="$emit('select-example', $event)"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import SmartQueryInputCard from '@/components/smartquery/SmartQueryInputCard.vue'
import SmartQueryExamples from '@/components/smartquery/SmartQueryExamples.vue'
import PlanModeChat from '@/components/smartquery/PlanModeChat.vue'
import type { QueryMode, AttachmentInfo } from '@/composables/useSmartQuery'

export interface Message {
  role: 'user' | 'assistant'
  content: string
}

export interface GeneratedPrompt {
  prompt: string
  suggested_mode?: 'read' | 'write'
}

interface Props {
  modelValue: string
  mode: QueryMode
  attachments: AttachmentInfo[]
  disabled?: boolean
  loading?: boolean
  uploading?: boolean
  isListening?: boolean
  hasMicrophone?: boolean
  interimTranscript?: string
  showExamples?: boolean
  examples?: Array<{ question: string; icon: string; title: string }>
  planConversation?: Message[]
  planLoading?: boolean
  generatedPrompt?: GeneratedPrompt | null
}

defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'submit': []
  'paste': [event: ClipboardEvent]
  'remove-attachment': [attachmentId: string]
  'toggle-voice': []
  'file-select': [files: FileList]
  'select-example': [question: string]
  'plan-send': [message: string]
  'adopt-prompt': [prompt: string, mode: 'read' | 'write']
  'plan-reset': []
  'save-as-summary': [prompt: string]
}>()

const fileInputRef = ref<HTMLInputElement | null>(null)

function triggerFileInput() {
  fileInputRef.value?.click()
}

function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  const files = input.files
  if (!files) return

  emit('file-select', files)

  // Clear the input so the same file can be selected again
  input.value = ''
}

function handlePaste(event: ClipboardEvent) {
  emit('paste', event)
}
</script>

<style scoped>
.smart-query-input {
  position: relative;
}

.plan-mode-card {
  border-radius: 16px !important;
  border: 2px solid rgba(var(--v-theme-info), 0.2);
  min-height: clamp(300px, 50vh, 400px);
  overflow: hidden;
}

@media (max-width: 600px) {
  .plan-mode-card {
    min-height: 280px;
    border-radius: 12px !important;
  }
}
</style>
