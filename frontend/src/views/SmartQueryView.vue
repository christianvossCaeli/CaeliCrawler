<template>
  <div class="smart-query-view">
    <!-- Toolbar -->
    <SmartQueryToolbar
      v-model:mode="currentMode"
      v-model:show-history="showHistory"
      :favorite-count="historyStore.favoriteCount"
      :hint="modeHint"
      :disabled="previewData !== null"
    />

    <!-- Input Section -->
    <SmartQueryInput
      v-model="question"
      :mode="currentMode"
      :attachments="pendingAttachments"
      :disabled="previewData !== null"
      :loading="loading"
      :uploading="isUploading"
      :is-listening="isListening"
      :has-microphone="hasMicrophone"
      :interim-transcript="interimTranscript"
      :show-examples="!results && !previewData && !loading"
      :examples="currentExamplesWithMeta"
      :plan-conversation="planConversation"
      :plan-loading="planLoading"
      :generated-prompt="planGeneratedPrompt"
      @submit="executeQuery"
      @paste="handlePaste"
      @remove-attachment="removeAttachment"
      @toggle-voice="handleVoiceInput"
      @file-select="handleFileSelect"
      @select-example="useExample"
      @plan-send="handlePlanSend"
      @adopt-prompt="adoptPrompt"
      @plan-reset="handlePlanReset"
      @save-as-summary="handleSaveAsSummary"
    />

    <!-- Results Section -->
    <SmartQueryResults
      :results="results"
      :preview="previewData"
      :loading="loading"
      :error="error"
      :mode="currentMode"
      :current-step="currentStep"
      :from-assistant="fromAssistant"
      @clear-error="error = null"
      @cancel-preview="cancelPreview"
      @confirm-write="confirmWrite"
      @new-query="resetAll"
      @back-to-assistant="sendResultsToAssistant"
      @visualization-action="handleVisualizationAction"
    />

    <!-- History Sidebar -->
    <SmartQuerySidebar
      v-model="showHistory"
      @rerun="handleHistoryRerun"
    />

    <!-- Summary Create Dialog -->
    <SummaryCreateDialog
      v-model="showSummaryCreateDialog"
      :initial-prompt="summaryInitialPrompt"
      @created="handleSummaryCreated"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { api } from '@/services/api'
import { useSmartQuery } from '@/composables/useSmartQuery'
import { usePageContextProvider, PAGE_FEATURES, PAGE_ACTIONS } from '@/composables/usePageContext'
import type { PageContextData } from '@/composables/assistant/types'
import SmartQueryToolbar from '@/components/smartquery/SmartQueryToolbar.vue'
import SmartQueryInput from '@/components/smartquery/SmartQueryInput.vue'
import SmartQueryResults from '@/components/smartquery/SmartQueryResults.vue'
import SmartQuerySidebar from '@/components/smartquery/SmartQuerySidebar.vue'
import SummaryCreateDialog from '@/components/summaries/SummaryCreateDialog.vue'

const { t } = useI18n()
const router = useRouter()

// Use the shared Smart Query composable
const {
  question,
  currentMode,
  loading,
  error,
  results,
  previewData,
  fromAssistant,
  currentStep,
  pendingAttachments,
  isUploading,
  showHistory,
  planConversation,
  planLoading,
  planGeneratedPrompt,
  isListening,
  hasMicrophone,
  interimTranscript,
  modeHint,
  historyStore,
  handleVoiceInput,
  uploadAttachment,
  removeAttachment,
  executeQuery,
  confirmWrite,
  cancelPreview,
  resetAll,
  adoptPrompt,
  handlePlanReset,
  handleVisualizationAction,
  handleHistoryRerun,
  sendResultsToAssistant,
  initializeFromContext,
  cleanup,
} = useSmartQuery()

// Page Context Provider für KI-Assistenten
usePageContextProvider(
  '/smart-query',
  (): PageContextData => ({
    current_route: '/smart-query',
    view_mode: currentMode.value,
    current_query: question.value || undefined,
    query_mode: currentMode.value as 'read' | 'write' | 'plan',
    query_result_count: Array.isArray(results.value) ? results.value.length : 0,
    available_features: [...PAGE_FEATURES.smartQuery],
    available_actions: [...PAGE_ACTIONS.base, 'execute_query', 'save_query', 'export_results']
  })
)

// Summary creation
const showSummaryCreateDialog = ref(false)
const summaryInitialPrompt = ref('')

// Examples state
const readExamples = ref([
  {
    question: t('smartQueryView.examples.read.futureEvents'),
    icon: 'mdi-calendar-clock',
    title: t('smartQueryView.examples.read.futureEventsTitle')
  },
  {
    question: t('smartQueryView.examples.read.mayorsOnEvents'),
    icon: 'mdi-account-tie',
    title: t('smartQueryView.examples.read.mayorsOnEventsTitle')
  },
  {
    question: t('smartQueryView.examples.read.allPainPoints'),
    icon: 'mdi-alert-circle-outline',
    title: t('smartQueryView.examples.read.allPainPointsTitle')
  },
  {
    question: t('smartQueryView.examples.read.gummersbachPainPoints'),
    icon: 'mdi-map-marker',
    title: t('smartQueryView.examples.read.gummersbachPainPointsTitle')
  },
])

const writeExamples = ref([
  {
    question: t('smartQueryView.examples.write.createPerson'),
    icon: 'mdi-account-plus',
    title: t('smartQueryView.examples.write.createPersonTitle')
  },
  {
    question: t('smartQueryView.examples.write.addPainPoint'),
    icon: 'mdi-comment-plus-outline',
    title: t('smartQueryView.examples.write.addPainPointTitle')
  },
  {
    question: t('smartQueryView.examples.write.findEvents'),
    icon: 'mdi-calendar-search',
    title: t('smartQueryView.examples.write.findEventsTitle')
  },
  {
    question: t('smartQueryView.examples.write.startCrawls'),
    icon: 'mdi-spider-web',
    title: t('smartQueryView.examples.write.startCrawlsTitle')
  },
  {
    question: t('smartQueryView.examples.write.createCategory'),
    icon: 'mdi-folder-plus',
    title: t('smartQueryView.examples.write.createCategoryTitle')
  },
  {
    question: t('smartQueryView.examples.write.analyzePysis'),
    icon: 'mdi-database-sync',
    title: t('smartQueryView.examples.write.analyzePysisTitle')
  },
])

const currentExamplesWithMeta = computed(() =>
  currentMode.value === 'write' ? writeExamples.value : readExamples.value
)

// Load examples from API
async function loadExamples() {
  try {
    const response = await api.get('/v1/analysis/smart-query/examples')
    if (response.data?.read_examples) {
      readExamples.value = response.data.read_examples
    }
    if (response.data?.write_examples) {
      writeExamples.value = response.data.write_examples
    }
  } catch (e) {
    // Use default examples
  }
}

// Attachment handlers
async function handleFileSelect(files: FileList) {
  for (const file of Array.from(files)) {
    await uploadAttachment(file)
  }
}

async function handlePaste(event: ClipboardEvent) {
  const items = event.clipboardData?.items
  if (!items) return

  for (const item of Array.from(items)) {
    if (item.type.startsWith('image/')) {
      event.preventDefault()
      const file = item.getAsFile()
      if (file) {
        await uploadAttachment(file)
      }
    }
  }
}

// Plan mode handlers
function handlePlanSend(msg: string) {
  question.value = msg
  executeQuery()
}

// Summary handlers
function handleSaveAsSummary(prompt: string) {
  summaryInitialPrompt.value = prompt
  showSummaryCreateDialog.value = true
}

function handleSummaryCreated() {
  showSummaryCreateDialog.value = false
  router.push('/summaries')
}

// Example selection
function useExample(q: string) {
  question.value = q
  executeQuery()
}

// Lifecycle
onMounted(() => {
  loadExamples()

  const hasContext = initializeFromContext()

  // Auto-execute if we have a query from the assistant
  if (hasContext && fromAssistant.value && question.value.trim()) {
    executeQuery()
  }
})

// Cleanup on unmount - cancel active streams and clear resources
onBeforeUnmount(() => {
  cleanup()
})
</script>

<style scoped>
.smart-query-view {
  position: relative;
}
</style>
