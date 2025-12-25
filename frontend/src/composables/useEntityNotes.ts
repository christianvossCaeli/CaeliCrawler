import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSnackbar } from './useSnackbar'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('useEntityNotes')

export interface Note {
  id: string
  content: string
  author: string
  created_at: string
}

export function useEntityNotes(entityId: string | undefined) {
  const { t } = useI18n()
  const { showSuccess, showError } = useSnackbar()

  const notes = ref<Note[]>([])
  const newNote = ref('')
  const savingNote = ref(false)

  async function loadNotes() {
    if (!entityId) return
    try {
      // Notes are stored as a special facet type or in a separate endpoint
      // For now, we'll store them in localStorage as a simple solution
      const key = `entity_notes_${entityId}`
      const stored = localStorage.getItem(key)
      notes.value = stored ? JSON.parse(stored) : []
    } catch (e) {
      logger.error('Failed to load notes', e)
      notes.value = []
    }
  }

  async function saveNote() {
    if (!entityId || !newNote.value.trim()) return
    savingNote.value = true

    try {
      const note: Note = {
        id: crypto.randomUUID(),
        content: newNote.value.trim(),
        author: t('entityDetail.currentUser'), // Would come from auth
        created_at: new Date().toISOString(),
      }

      notes.value.unshift(note)

      // Save to localStorage (would be API in production)
      const key = `entity_notes_${entityId}`
      localStorage.setItem(key, JSON.stringify(notes.value))

      newNote.value = ''
      showSuccess(t('entityDetail.messages.noteSaved'))
    } catch (e) {
      showError(t('entityDetail.messages.noteSaveError'))
    } finally {
      savingNote.value = false
    }
  }

  async function deleteNote(noteId: string) {
    if (!entityId) return

    try {
      notes.value = notes.value.filter(n => n.id !== noteId)

      // Save to localStorage
      const key = `entity_notes_${entityId}`
      localStorage.setItem(key, JSON.stringify(notes.value))

      showSuccess(t('entityDetail.messages.noteDeleted'))
    } catch (e) {
      showError(t('entityDetail.messages.noteDeleteError'))
    }
  }

  return {
    notes,
    newNote,
    savingNote,
    loadNotes,
    saveNote,
    deleteNote,
  }
}
