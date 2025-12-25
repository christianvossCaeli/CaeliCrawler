<script setup lang="ts">
/**
 * RecentDocuments Widget - Shows recently crawled/added documents
 */

import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { dataApi } from '@/services/api'
import { handleKeyboardClick } from '../composables'
import BaseWidget from '../BaseWidget.vue'
import WidgetEmptyState from './WidgetEmptyState.vue'
import type { WidgetDefinition, WidgetConfig, RecentDocument } from '../types'
import { WIDGET_DEFAULT_LIMIT } from '../types'

const props = defineProps<{
  definition: WidgetDefinition
  config?: WidgetConfig
  isEditing?: boolean
}>()

const { t } = useI18n()
const router = useRouter()
const loading = ref(true)
const error = ref<string | null>(null)
const documents = ref<RecentDocument[]>([])

const refresh = async () => {
  loading.value = true
  error.value = null
  try {
    const response = await dataApi.getDocuments({
      per_page: WIDGET_DEFAULT_LIMIT,
      sort_by: 'created_at',
      sort_order: 'desc',
    })
    documents.value = response.data?.items || []
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('common.loadError')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  refresh()
})

const isEditMode = computed(() => props.isEditing ?? false)
const tabIndex = computed(() => (isEditMode.value ? -1 : 0))

const getFileIcon = (fileType?: string): string => {
  const iconMap: Record<string, string> = {
    pdf: 'mdi-file-pdf-box',
    doc: 'mdi-file-word',
    docx: 'mdi-file-word',
    xls: 'mdi-file-excel',
    xlsx: 'mdi-file-excel',
    ppt: 'mdi-file-powerpoint',
    pptx: 'mdi-file-powerpoint',
    txt: 'mdi-file-document-outline',
    html: 'mdi-language-html5',
    xml: 'mdi-file-xml-box',
  }
  return iconMap[fileType?.toLowerCase() || ''] || 'mdi-file-document'
}

const getStatusColor = (status: string): string => {
  const colorMap: Record<string, string> = {
    PROCESSED: 'success',
    PROCESSING: 'info',
    PENDING: 'grey',
    FAILED: 'error',
  }
  return colorMap[status] || 'grey'
}

const formatTime = (timestamp: string): string => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return t('common.justNow')
  if (diff < 3600000) return t('common.minutesAgo', { n: Math.floor(diff / 60000) })
  if (diff < 86400000) return t('common.hoursAgo', { n: Math.floor(diff / 3600000) })
  return t('common.daysAgo', { n: Math.floor(diff / 86400000) })
}

const navigateToDocument = (doc: RecentDocument) => {
  if (isEditMode.value) return
  router.push({ path: `/documents/${doc.id}` })
}

const navigateToDocuments = () => {
  if (isEditMode.value) return
  router.push({ path: '/documents' })
}

const handleKeydownDocument = (event: KeyboardEvent, doc: RecentDocument) => {
  handleKeyboardClick(event, () => navigateToDocument(doc))
}

const handleKeydownViewAll = (event: KeyboardEvent) => {
  handleKeyboardClick(event, () => navigateToDocuments())
}
</script>

<template>
  <BaseWidget
    :definition="definition"
    :config="config"
    :is-editing="isEditing"
    @refresh="refresh"
  >
    <div v-if="loading" class="d-flex justify-center py-6">
      <v-progress-circular indeterminate size="32" />
    </div>

    <v-list v-else-if="documents.length > 0" density="compact" class="documents-list" role="list">
      <v-list-item
        v-for="doc in documents"
        :key="doc.id"
        class="px-2 clickable-item"
        :class="{ 'non-interactive': isEditing }"
        role="button"
        :tabindex="tabIndex"
        :aria-label="doc.title + ' - ' + formatTime(doc.created_at)"
        @click="navigateToDocument(doc)"
        @keydown="handleKeydownDocument($event, doc)"
      >
        <template #prepend>
          <v-icon
            :icon="getFileIcon(doc.file_type)"
            :color="getStatusColor(doc.status)"
            size="small"
          />
        </template>

        <v-list-item-title class="text-body-2 text-truncate">
          {{ doc.title }}
        </v-list-item-title>
        <v-list-item-subtitle class="text-caption">
          <span v-if="doc.source_name">{{ doc.source_name }}</span>
          <span v-else-if="doc.category_name">{{ doc.category_name }}</span>
          <span class="ml-2 text-medium-emphasis">{{ formatTime(doc.created_at) }}</span>
        </v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <WidgetEmptyState
      v-else
      icon="mdi-file-document-outline"
      :message="t('dashboard.noDocuments')"
    />

    <!-- View All Link -->
    <div
      v-if="documents.length > 0"
      class="text-center mt-2 view-all-link"
      :class="{ 'non-interactive': isEditing }"
      role="button"
      :tabindex="tabIndex"
      :aria-label="t('common.viewAll')"
      @click="navigateToDocuments"
      @keydown="handleKeydownViewAll($event)"
    >
      <span class="text-caption text-primary">
        {{ t('common.viewAll') }}
      </span>
    </div>
  </BaseWidget>
</template>

<style scoped>
.documents-list {
  max-height: 280px;
  overflow-y: auto;
}

.clickable-item {
  cursor: pointer;
  border-radius: 8px;
  transition: background-color 0.2s ease;
}

.clickable-item:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.08);
}

.clickable-item:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.view-all-link {
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.view-all-link:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.08);
}

.view-all-link:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.non-interactive {
  cursor: default;
  pointer-events: none;
}
</style>
