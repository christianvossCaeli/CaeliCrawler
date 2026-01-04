<template>
  <div class="attachments-preview">
    <div
      v-for="attachment in attachments"
      :key="attachment.id"
      class="attachment-item"
    >
      <img
        v-if="attachment.preview"
        :src="attachment.preview"
        :alt="attachment.filename"
        class="attachment-thumbnail"
      />
      <v-icon v-else size="24" color="primary">{{ getAttachmentIcon(attachment.contentType) }}</v-icon>
      <span class="attachment-name">{{ attachment.filename }}</span>
      <button
        class="attachment-remove"
        :title="t('assistant.removeAttachment')"
        @click="$emit('remove', attachment.id)"
      >
        <v-icon size="14">mdi-close</v-icon>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

interface Attachment {
  id: string
  filename: string
  contentType: string
  preview?: string
}

defineProps<{
  attachments: Attachment[]
}>()

defineEmits<{
  remove: [id: string]
}>()

const { t } = useI18n()

function getAttachmentIcon(contentType: string): string {
  if (contentType.startsWith('image/')) return 'mdi-image'
  if (contentType === 'application/pdf') return 'mdi-file-pdf-box'
  return 'mdi-file'
}
</script>

<style scoped>
@import './styles/chat-assistant.css';
</style>
