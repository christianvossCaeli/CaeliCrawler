<template>
  <v-card variant="outlined">
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-paperclip</v-icon>
      {{ t('entityDetail.attachments.title') }}
      <v-chip size="small" class="ml-2">{{ attachments.length }}</v-chip>
      <v-spacer></v-spacer>
      <v-btn v-if="canEdit" color="primary" variant="tonal" size="small" @click="openUploadDialog">
        <v-icon start>mdi-upload</v-icon>
        {{ t('entityDetail.attachments.upload') }}
      </v-btn>
    </v-card-title>

    <v-card-text>
      <!-- Drop Zone -->
      <div
        v-if="canEdit"
        class="drop-zone mb-4"
        :class="{ 'drop-zone--active': isDragging }"
        @dragover.prevent="isDragging = true"
        @dragleave="isDragging = false"
        @drop.prevent="onDrop"
      >
        <v-icon size="48" color="grey-lighten-1">mdi-cloud-upload</v-icon>
        <p class="text-body-2 text-medium-emphasis mt-2">
          {{ t('entityDetail.attachments.dropHint') }}
        </p>
      </div>

      <!-- Loading -->
      <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4"></v-progress-linear>

      <!-- Attachment List -->
      <v-list v-if="attachments.length" lines="two">
        <v-list-item v-for="att in attachments" :key="att.id" class="attachment-item">
          <template #prepend>
            <!-- Thumbnail for images -->
            <v-avatar v-if="att.is_image" size="56" rounded class="mr-3">
              <v-img :src="getThumbnailUrl(att.id)" cover></v-img>
            </v-avatar>
            <!-- Icon for PDFs -->
            <v-avatar v-else size="56" color="red-lighten-4" rounded class="mr-3">
              <v-icon color="red">mdi-file-pdf-box</v-icon>
            </v-avatar>
          </template>

          <v-list-item-title>{{ att.filename }}</v-list-item-title>
          <v-list-item-subtitle>
            {{ formatFileSize(att.file_size) }} -
            {{ formatDate(att.created_at) }}
            <v-chip size="x-small" :color="getStatusColor(att.analysis_status)" class="ml-2">
              <v-progress-circular
                v-if="att.analysis_status === 'ANALYZING'"
                :size="12"
                :width="2"
                indeterminate
                class="mr-1"
              ></v-progress-circular>
              {{ getStatusLabel(att.analysis_status) }}
            </v-chip>
          </v-list-item-subtitle>

          <template #append>
            <div class="d-flex ga-1">
              <!-- Analyze Button -->
              <v-btn
                v-if="canEdit && (att.analysis_status === 'PENDING' || att.analysis_status === 'FAILED')"
                icon
                size="small"
                variant="text"
                color="primary"
                :loading="analyzingIds.includes(att.id)"
                @click="analyzeAttachment(att)"
              >
                <v-icon>mdi-brain</v-icon>
                <v-tooltip activator="parent">{{ t('entityDetail.attachments.analyze') }}</v-tooltip>
              </v-btn>

              <!-- View Analysis -->
              <v-btn
                v-if="att.analysis_status === 'COMPLETED'"
                icon
                size="small"
                variant="text"
                color="success"
                @click="viewAnalysis(att)"
              >
                <v-icon>mdi-eye</v-icon>
                <v-tooltip activator="parent">{{ t('entityDetail.attachments.viewAnalysis') }}</v-tooltip>
              </v-btn>

              <!-- Download -->
              <v-btn icon size="small" variant="text" @click="downloadAttachment(att)">
                <v-icon>mdi-download</v-icon>
                <v-tooltip activator="parent">{{ t('common.download') }}</v-tooltip>
              </v-btn>

              <!-- Delete -->
              <v-btn v-if="canEdit" icon size="small" variant="text" color="error" @click="confirmDelete(att)">
                <v-icon>mdi-delete</v-icon>
                <v-tooltip activator="parent">{{ t('common.delete') }}</v-tooltip>
              </v-btn>
            </div>
          </template>
        </v-list-item>
      </v-list>

      <!-- Empty State -->
      <div v-else-if="!loading" class="text-center py-8">
        <v-icon size="64" color="grey-lighten-1">mdi-paperclip</v-icon>
        <p class="text-body-1 text-medium-emphasis mt-2">
          {{ t('entityDetail.attachments.empty') }}
        </p>
      </div>
    </v-card-text>

    <!-- Upload Dialog -->
    <v-dialog v-model="uploadDialog" max-width="500">
      <v-card>
        <v-card-title>{{ t('entityDetail.attachments.uploadTitle') }}</v-card-title>
        <v-card-text>
          <v-file-input
            v-model="selectedFile"
            :label="t('entityDetail.attachments.selectFile')"
            accept="image/*,application/pdf"
            prepend-icon="mdi-paperclip"
            show-size
          ></v-file-input>
          <v-textarea
            v-model="uploadDescription"
            :label="t('entityDetail.attachments.description')"
            rows="2"
          ></v-textarea>
          <v-checkbox v-model="autoAnalyze" :label="t('entityDetail.attachments.autoAnalyze')"></v-checkbox>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="uploadDialog = false">
            {{ t('common.cancel') }}
          </v-btn>
          <v-btn
            color="primary"
            variant="tonal"
            :loading="uploading"
            :disabled="!selectedFile"
            @click="uploadFile"
          >
            {{ t('entityDetail.attachments.upload') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Analysis Result Dialog -->
    <v-dialog v-model="analysisDialog" max-width="800" scrollable>
      <v-card v-if="selectedAttachment">
        <v-card-title class="d-flex align-center">
          <v-icon start>mdi-chart-box</v-icon>
          {{ t('entityDetail.attachments.analysisTitle') }}: {{ selectedAttachment.filename }}
        </v-card-title>
        <v-card-text>
          <template v-if="selectedAttachment.analysis_result">
            <!-- Description -->
            <div class="mb-4">
              <h4 class="text-subtitle-2 mb-1">{{ t('entityDetail.attachments.analysisDescription') }}</h4>
              <p class="text-body-2">{{ selectedAttachment.analysis_result.description }}</p>
            </div>

            <!-- Detected Text -->
            <div v-if="selectedAttachment.analysis_result.detected_text?.length" class="mb-4">
              <h4 class="text-subtitle-2 mb-1">{{ t('entityDetail.attachments.detectedText') }}</h4>
              <v-chip
                v-for="(text, i) in selectedAttachment.analysis_result.detected_text.slice(0, 10)"
                :key="i"
                size="small"
                class="ma-1"
              >
                {{ text }}
              </v-chip>
            </div>

            <!-- Entities -->
            <div v-if="hasEntities" class="mb-4">
              <h4 class="text-subtitle-2 mb-1">{{ t('entityDetail.attachments.extractedEntities') }}</h4>
              <div v-for="(values, key) in selectedAttachment.analysis_result.entities" :key="key" class="mb-1">
                <span class="text-caption text-medium-emphasis mr-2">{{ getEntityLabel(key) }}:</span>
                <v-chip
                  v-for="(value, i) in (values || []).slice(0, 5)"
                  :key="i"
                  size="small"
                  :color="getEntityColor(key)"
                  class="ma-1"
                >
                  {{ value }}
                </v-chip>
              </div>
            </div>

            <!-- Facet Suggestions -->
            <v-divider v-if="hasFacetSuggestions" class="my-4"></v-divider>
            <div v-if="hasFacetSuggestions" class="mb-4">
              <h4 class="text-subtitle-2 mb-2 d-flex align-center">
                <v-icon start size="small">mdi-lightbulb-on</v-icon>
                {{ t('entityDetail.attachments.facetSuggestions') }}
                <v-chip size="x-small" class="ml-2">{{ facetSuggestions.length }}</v-chip>
              </h4>

              <v-alert type="info" variant="tonal" density="compact" class="mb-3">
                {{ t('entityDetail.attachments.facetSuggestionsHint') }}
              </v-alert>

              <v-list density="compact" class="facet-suggestions-list">
                <v-list-item
                  v-for="(suggestion, idx) in facetSuggestions"
                  :key="idx"
                  class="facet-suggestion-item"
                >
                  <template #prepend>
                    <v-checkbox
                      v-if="canEdit"
                      v-model="selectedFacetIndices"
                      :value="idx"
                      hide-details
                      density="compact"
                    ></v-checkbox>
                  </template>

                  <v-list-item-title class="text-body-2">
                    <v-chip size="x-small" :color="getFacetTypeColor(suggestion.facet_type_slug)" class="mr-2">
                      {{ suggestion.facet_type_name || suggestion.facet_type_slug }}
                    </v-chip>
                    {{ suggestion.text_representation || getSuggestionText(suggestion) }}
                  </v-list-item-title>

                  <v-list-item-subtitle>
                    <v-chip size="x-small" variant="outlined" class="mr-1">
                      {{ Math.round((suggestion.confidence || 0.7) * 100) }}% {{ t('common.confidence') }}
                    </v-chip>
                    <span v-if="suggestion.source_text" class="text-caption text-medium-emphasis">
                      {{ suggestion.source_text.slice(0, 50) }}...
                    </span>
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>

              <div v-if="canEdit" class="d-flex justify-end mt-3 ga-2">
                <v-btn
                  size="small"
                  variant="text"
                  @click="selectAllFacets"
                >
                  {{ t('common.selectAll') }}
                </v-btn>
                <v-btn
                  size="small"
                  variant="text"
                  @click="deselectAllFacets"
                >
                  {{ t('common.deselectAll') }}
                </v-btn>
              </div>
            </div>

            <div v-else-if="selectedAttachment.analysis_result && !hasFacetSuggestions" class="text-center py-4">
              <v-icon color="grey-lighten-1">mdi-lightbulb-off-outline</v-icon>
              <p class="text-body-2 text-medium-emphasis mt-1">
                {{ t('entityDetail.attachments.noFacetSuggestions') }}
              </p>
            </div>
          </template>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="analysisDialog = false">
            {{ t('common.close') }}
          </v-btn>
          <v-btn
            v-if="canEdit && hasFacetSuggestions && selectedFacetIndices.length > 0"
            color="primary"
            variant="tonal"
            :loading="applyingFacets"
            @click="applySelectedFacets"
          >
            <v-icon start>mdi-check-all</v-icon>
            {{ t('entityDetail.attachments.applyFacets') }} ({{ selectedFacetIndices.length }})
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title>{{ t('entityDetail.attachments.deleteConfirm') }}</v-card-title>
        <v-card-text>
          {{ t('entityDetail.attachments.deleteMessage', { filename: attachmentToDelete?.filename }) }}
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="deleteDialog = false">
            {{ t('common.cancel') }}
          </v-btn>
          <v-btn color="error" variant="tonal" :loading="deleting" @click="deleteAttachment">
            {{ t('common.delete') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Success Snackbar -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000">
      {{ snackbar.message }}
    </v-snackbar>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { attachmentApi } from '@/services/api'
import { useStatusColors } from '@/composables'
import { useLogger } from '@/composables/useLogger'
import { getErrorMessage } from '@/composables/useApiErrorHandler'

const props = withDefaults(defineProps<{
  entityId: string
  canEdit?: boolean
}>(), {
  canEdit: true,
})

const emit = defineEmits<{
  (e: 'attachments-changed'): void
  (e: 'facets-applied'): void
}>()

const logger = useLogger('EntityAttachmentsTab')

interface FacetSuggestion {
  facet_type_id?: string
  facet_type_slug: string
  facet_type_name?: string
  value: Record<string, unknown>
  text_representation?: string
  confidence?: number
  source_text?: string
}

interface Attachment {
  id: string
  filename: string
  content_type: string
  file_size: number
  description?: string
  analysis_status: string
  analysis_result?: {
    description?: string
    detected_text?: string[]
    entities?: Record<string, string[]>
    facet_suggestions?: FacetSuggestion[]
  }
  analyzed_at?: string
  uploaded_by_id?: string
  created_at: string
  is_image: boolean
  is_pdf: boolean
}

const { t } = useI18n()
const { getStatusColor } = useStatusColors()

// State
const loading = ref(false)
const attachments = ref<Attachment[]>([])
const isDragging = ref(false)
let pollInterval: ReturnType<typeof setInterval> | null = null

// Upload
const uploadDialog = ref(false)
const selectedFile = ref<File | null>(null)
const uploadDescription = ref('')
const autoAnalyze = ref(false)
const uploading = ref(false)

// Analysis
const analyzingIds = ref<string[]>([])
const analysisDialog = ref(false)
const selectedAttachment = ref<Attachment | null>(null)
const selectedFacetIndices = ref<number[]>([])
const applyingFacets = ref(false)

// Delete
const deleteDialog = ref(false)
const attachmentToDelete = ref<Attachment | null>(null)
const deleting = ref(false)

// Snackbar
const snackbar = ref({
  show: false,
  message: '',
  color: 'success',
})

// Computed
const facetSuggestions = computed<FacetSuggestion[]>(() => {
  return selectedAttachment.value?.analysis_result?.facet_suggestions || []
})

const hasFacetSuggestions = computed(() => facetSuggestions.value.length > 0)

const hasEntities = computed(() => {
  const entities = selectedAttachment.value?.analysis_result?.entities
  if (!entities) return false
  return Object.values(entities).some((arr) => arr && arr.length > 0)
})

const hasAnalyzingAttachments = computed(() => {
  return attachments.value.some((att) => att.analysis_status === 'ANALYZING')
})

// Watch for analyzing attachments to start/stop polling
watch(hasAnalyzingAttachments, (isAnalyzing) => {
  if (isAnalyzing) {
    startPolling()
  } else {
    stopPolling()
  }
})

// Load attachments
async function loadAttachments() {
  loading.value = true
  try {
    const response = await attachmentApi.list(props.entityId)
    attachments.value = response.data.items
  } catch (error) {
    logger.error('Failed to load attachments:', error)
  } finally {
    loading.value = false
  }
}

// Polling for status updates
function startPolling() {
  if (pollInterval) return
  pollInterval = setInterval(async () => {
    try {
      const response = await attachmentApi.list(props.entityId)
      attachments.value = response.data.items
    } catch (error) {
      logger.error('Polling failed:', error)
    }
  }, 3000)
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

// Upload
function openUploadDialog() {
  if (!props.canEdit) return
  selectedFile.value = null
  uploadDescription.value = ''
  autoAnalyze.value = false
  uploadDialog.value = true
}

async function uploadFile() {
  if (!props.canEdit) return
  if (!selectedFile.value) return

  uploading.value = true
  try {
    await attachmentApi.upload(props.entityId, selectedFile.value, {
      description: uploadDescription.value || undefined,
      autoAnalyze: autoAnalyze.value,
    })
    uploadDialog.value = false
    await loadAttachments()
    emit('attachments-changed')
    showSnackbar(t('entityDetail.attachments.uploadSuccess'), 'success')
  } catch (error) {
    logger.error('Upload failed:', error)
    showSnackbar(getErrorMessage(error) || t('entityDetail.attachments.uploadError'), 'error')
  } finally {
    uploading.value = false
  }
}

async function onDrop(event: DragEvent) {
  if (!props.canEdit) return
  isDragging.value = false
  const files = event.dataTransfer?.files
  if (files && files.length > 0) {
    const file = files[0]
    uploading.value = true
    try {
      await attachmentApi.upload(props.entityId, file)
      await loadAttachments()
      emit('attachments-changed')
      showSnackbar(t('entityDetail.attachments.uploadSuccess'), 'success')
    } catch (error) {
      logger.error('Upload failed:', error)
      showSnackbar(getErrorMessage(error) || t('entityDetail.attachments.uploadError'), 'error')
    } finally {
      uploading.value = false
    }
  }
}

// Analysis
async function analyzeAttachment(att: Attachment) {
  if (!props.canEdit) return
  analyzingIds.value.push(att.id)
  try {
    await attachmentApi.analyze(props.entityId, att.id)
    // Update local status
    att.analysis_status = 'ANALYZING'
    showSnackbar(t('entityDetail.attachments.analysisStarted'), 'info')
  } catch (error) {
    logger.error('Analysis failed:', error)
    showSnackbar(getErrorMessage(error) || t('entityDetail.attachments.analysisError'), 'error')
  } finally {
    analyzingIds.value = analyzingIds.value.filter((id) => id !== att.id)
  }
}

function viewAnalysis(att: Attachment) {
  selectedAttachment.value = att
  selectedFacetIndices.value = []
  analysisDialog.value = true
}

// Facet application
function selectAllFacets() {
  if (!props.canEdit) return
  selectedFacetIndices.value = facetSuggestions.value.map((_, idx) => idx)
}

function deselectAllFacets() {
  if (!props.canEdit) return
  selectedFacetIndices.value = []
}

async function applySelectedFacets() {
  if (!props.canEdit) return
  if (!selectedAttachment.value || selectedFacetIndices.value.length === 0) return

  applyingFacets.value = true
  try {
    const response = await attachmentApi.applyFacets(
      props.entityId,
      selectedAttachment.value.id,
      selectedFacetIndices.value
    )

    const data = response.data
    showSnackbar(
      t('entityDetail.attachments.facetsApplied', { count: data.created_count }),
      'success'
    )

    // Remove applied suggestions from selection
    selectedFacetIndices.value = []
    analysisDialog.value = false

    emit('facets-applied')
  } catch (error) {
    logger.error('Apply facets failed:', error)
    showSnackbar(getErrorMessage(error) || t('entityDetail.attachments.facetsApplyError'), 'error')
  } finally {
    applyingFacets.value = false
  }
}

// Download
async function downloadAttachment(att: Attachment) {
  try {
    const response = await attachmentApi.download(props.entityId, att.id)
    const blob = new Blob([response.data], { type: att.content_type })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = att.filename
    a.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    logger.error('Download failed:', error)
  }
}

// Delete
function confirmDelete(att: Attachment) {
  if (!props.canEdit) return
  attachmentToDelete.value = att
  deleteDialog.value = true
}

async function deleteAttachment() {
  if (!props.canEdit) return
  if (!attachmentToDelete.value) return

  deleting.value = true
  try {
    await attachmentApi.delete(props.entityId, attachmentToDelete.value.id)
    deleteDialog.value = false
    await loadAttachments()
    emit('attachments-changed')
    showSnackbar(t('entityDetail.attachments.deleteSuccess'), 'success')
  } catch (error) {
    logger.error('Delete failed:', error)
  } finally {
    deleting.value = false
  }
}

// Helpers
function getThumbnailUrl(attachmentId: string): string {
  return attachmentApi.getThumbnailUrl(props.entityId, attachmentId)
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString()
}

// getStatusColor now from useStatusColors composable

function getStatusLabel(status: string): string {
  return t(`attachments.status.${status.toLowerCase()}`)
}

function getEntityLabel(entityType: string): string {
  const labels: Record<string, string> = {
    persons: t('entityDetail.attachments.entityTypes.persons'),
    organizations: t('entityDetail.attachments.entityTypes.organizations'),
    locations: t('entityDetail.attachments.entityTypes.locations'),
    dates: t('entityDetail.attachments.entityTypes.dates'),
  }
  return labels[entityType] || entityType
}

function getEntityColor(entityType: string): string {
  switch (entityType) {
    case 'persons':
      return 'blue'
    case 'organizations':
      return 'purple'
    case 'locations':
      return 'green'
    case 'dates':
      return 'orange'
    default:
      return 'grey'
  }
}

function getFacetTypeColor(slug: string): string {
  const colors: Record<string, string> = {
    pain_point: 'red',
    positive_signal: 'green',
    contact: 'blue',
    summary: 'purple',
    timeline: 'orange',
  }
  return colors[slug] || 'grey'
}

function getSuggestionText(suggestion: FacetSuggestion): string {
  const value = suggestion.value
  const text = value?.text
  const description = value?.description
  const name = value?.name
  if (typeof text === 'string' && text) return text
  if (typeof description === 'string' && description) return description
  if (typeof name === 'string' && name) return name
  return JSON.stringify(value).slice(0, 100)
}

function showSnackbar(message: string, color: string) {
  snackbar.value = { show: true, message, color }
}

// Lifecycle
onMounted(() => {
  loadAttachments()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.drop-zone {
  border: 2px dashed #ccc;
  border-radius: 8px;
  padding: 32px;
  text-align: center;
  transition: all 0.2s;
  cursor: pointer;
}

.drop-zone:hover,
.drop-zone--active {
  border-color: rgb(var(--v-theme-primary));
  background-color: rgba(var(--v-theme-primary), 0.05);
}

.attachment-item {
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.attachment-item:last-child {
  border-bottom: none;
}

.facet-suggestions-list {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 8px;
}

.facet-suggestion-item {
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.facet-suggestion-item:last-child {
  border-bottom: none;
}
</style>
