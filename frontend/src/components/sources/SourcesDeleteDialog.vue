<template>
  <v-dialog v-model="dialogOpen" :max-width="DIALOG_SIZES.SM" persistent role="alertdialog" aria-modal="true">
    <v-card>
      <v-card-title class="d-flex align-center pa-4 bg-error">
        <v-avatar color="error-darken-1" size="40" class="mr-3">
          <v-icon color="on-error" aria-hidden="true">mdi-delete-alert</v-icon>
        </v-avatar>
        <div>
          <div class="text-h6">{{ $t('sources.dialog.delete') }}</div>
          <div v-if="source" class="text-caption opacity-80">{{ source.name }}</div>
        </div>
      </v-card-title>

      <v-card-text class="pa-6">
        <v-alert type="warning" variant="tonal" class="mb-4" role="alert">
          <v-icon start aria-hidden="true">mdi-alert</v-icon>
          {{ $t('sources.messages.deleteWarning') }}
        </v-alert>

        <div v-if="source" class="mb-4">
          <div class="d-flex align-center mb-2">
            <v-icon size="small" class="mr-2" aria-hidden="true">mdi-database</v-icon>
            <span class="font-weight-medium">{{ source.name }}</span>
          </div>
          <div class="d-flex align-center mb-2 text-medium-emphasis">
            <v-icon size="small" class="mr-2" aria-hidden="true">mdi-link</v-icon>
            <span class="text-caption text-truncate">{{ source.base_url }}</span>
          </div>
          <div v-if="source.document_count" class="d-flex align-center text-medium-emphasis">
            <v-icon size="small" class="mr-2" aria-hidden="true">mdi-file-document-multiple</v-icon>
            <span class="text-caption">
              {{ source.document_count }} {{ $t('sources.messages.documentsWillBeDeleted') }}
            </span>
          </div>
        </div>

        <v-text-field
          v-model="confirmText"
          :label="$t('sources.messages.typeToConfirm', { text: 'DELETE' })"
          :placeholder="'DELETE'"
          variant="outlined"
          density="comfortable"
          :error="confirmText.length > 0 && confirmText !== 'DELETE'"
          :error-messages="confirmText.length > 0 && confirmText !== 'DELETE' ? [$t('sources.messages.confirmMismatch')] : []"
          :aria-invalid="confirmText.length > 0 && confirmText !== 'DELETE'"
          :aria-describedby="confirmText.length > 0 && confirmText !== 'DELETE' ? 'confirm-error' : undefined"
        />
      </v-card-text>

      <v-divider />

      <v-card-actions class="pa-4">
        <v-btn variant="tonal" @click="close">
          {{ $t('common.cancel') }}
        </v-btn>
        <v-spacer />
        <v-btn
          variant="flat"
          color="error"
          @click="confirmDelete"
          :disabled="confirmText !== 'DELETE'"
          :loading="deleting"
          :aria-busy="deleting"
        >
          <v-icon start aria-hidden="true">mdi-delete</v-icon>
          {{ $t('common.delete') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch, toRef } from 'vue'
import type { DataSourceResponse } from '@/types/sources'
import { DIALOG_SIZES } from '@/config/sources'
import { useDialogFocus } from '@/composables'

// Props (non-model props only)
interface Props {
  source: DataSourceResponse | null
  deleting?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  deleting: false,
})

// defineModel() for two-way binding (Vue 3.4+)
const dialogOpen = defineModel<boolean>({ default: false })

// Emits (non-model emits only)
const emit = defineEmits<{
  (e: 'confirm'): void
}>()

const confirmText = ref('')

// Focus management for accessibility (WCAG 2.1)
useDialogFocus({ isOpen: toRef(() => dialogOpen.value) })

// Close dialog
function close() {
  dialogOpen.value = false
}

// Confirm delete
function confirmDelete() {
  if (confirmText.value === 'DELETE') {
    emit('confirm')
  }
}

// Reset confirm text when dialog opens/closes
watch(dialogOpen, (open) => {
  if (!open) {
    confirmText.value = ''
  }
})
</script>
