<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-file-document-multiple</v-icon>
      {{ t('entityDetail.tabs.documents') }}
      <v-chip v-if="documents.length" size="small" class="ml-2">{{ documents.length }}</v-chip>
    </v-card-title>
    <v-card-text>
      <div v-if="loading" class="text-center pa-4">
        <v-progress-circular indeterminate></v-progress-circular>
      </div>
      <v-data-table
        v-else-if="documents.length"
        :headers="headers"
        :items="documents"
        :items-per-page="10"
      >
        <template v-slot:item.title="{ item }">
          <a :href="item.url" target="_blank" class="text-decoration-none">
            {{ item.title || t('entityDetail.document') }}
          </a>
        </template>
        <template v-slot:item.created_at="{ item }">
          {{ formatDate(item.created_at) }}
        </template>
      </v-data-table>
      <!-- Empty State -->
      <div v-else class="text-center pa-8">
        <v-icon size="80" color="grey-lighten-1" class="mb-4">mdi-file-document-off-outline</v-icon>
        <h3 class="text-h6 mb-2">{{ t('entityDetail.emptyState.noDocuments', 'Keine Dokumente') }}</h3>
        <p class="text-body-2 text-medium-emphasis">
          {{ t('entityDetail.emptyState.noDocumentsDesc', 'Dieser Entity sind keine Dokumente zugeordnet.') }}
        </p>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { format } from 'date-fns'
import { de } from 'date-fns/locale'

// Types
interface Document {
  id: string
  title?: string
  url: string
  document_type?: string
  created_at?: string
}

// Props
defineProps<{
  documents: Document[]
  loading: boolean
}>()

const { t } = useI18n()

// Computed
const headers = computed(() => [
  { title: t('entityDetail.documentHeaders.title'), key: 'title' },
  { title: t('entityDetail.documentHeaders.type'), key: 'document_type' },
  { title: t('entityDetail.documentHeaders.date'), key: 'created_at' },
])

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
