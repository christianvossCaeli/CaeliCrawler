<template>
  <div class="input-area">
    <!-- Attachment Button -->
    <button
      class="attachment-btn"
      :title="t('assistant.attachFile')"
      :disabled="isUploading"
      @click="triggerFileInput"
    >
      <v-icon size="20" :class="{ 'icon-spin': isUploading }">{{ isUploading ? 'mdi-loading' : 'mdi-paperclip' }}</v-icon>
    </button>
    <input
      ref="fileInputRef"
      type="file"
      accept="image/png,image/jpeg,image/gif,image/webp,application/pdf"
      style="display: none"
      multiple
      @change="handleFileSelect"
    />

    <textarea
      ref="textareaRef"
      :value="modelValue"
      :placeholder="placeholder"
      rows="4"
      @input="handleInput"
      @keydown.enter.exact.prevent="$emit('send')"
      @paste="handlePaste"
    ></textarea>
    <button
      class="send-btn"
      :disabled="(!modelValue.trim() && !hasAttachments) || isLoading"
      @click="$emit('send')"
    >
      <v-icon size="20">mdi-send</v-icon>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

defineProps<{
  modelValue: string
  isLoading: boolean
  isUploading: boolean
  hasAttachments: boolean
  placeholder: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  send: []
  upload: [file: File]
}>()

const { t } = useI18n()
const fileInputRef = ref<HTMLInputElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)

function handleInput(e: Event) {
  const target = e.target as HTMLTextAreaElement
  emit('update:modelValue', target.value)
  autoResize(target)
}

function autoResize(el: HTMLTextAreaElement) {
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

function triggerFileInput() {
  fileInputRef.value?.click()
}

async function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  const files = input.files
  if (!files) return

  for (const file of Array.from(files)) {
    emit('upload', file)
  }

  input.value = ''
}

async function handlePaste(event: ClipboardEvent) {
  const items = event.clipboardData?.items
  if (!items) return

  for (const item of Array.from(items)) {
    if (item.type.startsWith('image/')) {
      event.preventDefault()
      const file = item.getAsFile()
      if (file) {
        emit('upload', file)
      }
    }
  }
}

function focus() {
  textareaRef.value?.focus()
}

defineExpose({ focus })
</script>

<style scoped>
@import './styles/chat-assistant.css';
</style>
