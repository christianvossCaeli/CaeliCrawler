<template>
  <v-dialog :model-value="modelValue" max-width="700" scrollable @update:model-value="$emit('update:modelValue', $event)">
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-note-text</v-icon>
        {{ t('entityDetail.notes') }}
        <v-spacer></v-spacer>
        <v-btn icon="mdi-close" variant="tonal" @click="$emit('update:modelValue', false)" :aria-label="t('common.close')"></v-btn>
      </v-card-title>
      <v-card-text>
        <!-- Add Note Form -->
        <v-textarea
          :model-value="newNote"
          @update:model-value="$emit('update:newNote', $event)"
          :label="t('entityDetail.dialog.addNote')"
          rows="3"
          variant="outlined"
          class="mb-4"
        ></v-textarea>
        <div class="d-flex justify-end mb-4">
          <v-btn
            color="primary"
            :disabled="!newNote?.trim()"
            :loading="savingNote"
            @click="$emit('saveNote')"
          >
            <v-icon start>mdi-plus</v-icon>
            {{ t('entityDetail.dialog.saveNote') }}
          </v-btn>
        </div>

        <v-divider class="mb-4"></v-divider>

        <!-- Notes List -->
        <div v-if="notes.length">
          <v-card
            v-for="note in notes"
            :key="note.id"
            variant="outlined"
            class="mb-3 pa-3"
          >
            <div class="d-flex align-start">
              <v-avatar size="32" color="primary" class="mr-3">
                <v-icon size="small" color="on-primary">mdi-account</v-icon>
              </v-avatar>
              <div class="flex-grow-1">
                <div class="d-flex align-center mb-1">
                  <span class="text-body-2 font-weight-medium">{{ note.author || t('entityDetail.systemAuthor') }}</span>
                  <span class="text-caption text-medium-emphasis ml-2">{{ formatDate(note.created_at) }}</span>
                  <v-spacer></v-spacer>
                  <v-btn
                    icon="mdi-delete"
                    size="x-small"
                    variant="tonal"
                    color="error"
                    @click="$emit('deleteNote', note.id)"
                  ></v-btn>
                </div>
                <p class="text-body-2 mb-0 text-pre-wrap">{{ note.content }}</p>
              </div>
            </div>
          </v-card>
        </div>
        <div v-else class="text-center pa-4 text-medium-emphasis">
          <v-icon size="48" color="grey-lighten-2" class="mb-2">mdi-note-off-outline</v-icon>
          <p>{{ t('entityDetail.emptyState.noNotes') }}</p>
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { format } from 'date-fns'
import { de } from 'date-fns/locale'

// Types
interface Note {
  id: string
  content: string
  author: string
  created_at: string
}

// Props
defineProps<{
  modelValue: boolean
  notes: Note[]
  newNote: string
  savingNote: boolean
}>()

// Emits
defineEmits<{
  'update:modelValue': [value: boolean]
  'update:newNote': [value: string]
  saveNote: []
  deleteNote: [noteId: string]
}>()

const { t } = useI18n()

// Helper functions
function formatDate(dateString?: string): string {
  if (!dateString) return ''
  try {
    return format(new Date(dateString), 'dd.MM.yyyy HH:mm', { locale: de })
  } catch {
    return dateString
  }
}
</script>

<style scoped>
.text-pre-wrap {
  white-space: pre-wrap;
}
</style>
