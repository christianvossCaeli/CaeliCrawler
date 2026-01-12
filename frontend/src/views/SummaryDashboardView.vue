<template>
  <div class="summary-dashboard" role="main" :aria-label="t('summaries.dashboard.ariaLabel')">
    <!-- Loading State (initial load) -->
    <div v-if="isLoading && !summary" class="d-flex justify-center align-center py-12" role="status" aria-live="polite">
      <v-progress-circular indeterminate size="64" color="primary" :aria-label="t('common.loading')" />
    </div>

    <!-- Loading Overlay (refresh) -->
    <v-overlay
      v-else-if="isLoading && summary"
      :model-value="true"
      contained
      class="align-center justify-center"
      persistent
    >
      <v-progress-circular indeterminate size="48" color="primary" />
    </v-overlay>

    <!-- Error State -->
    <v-alert
      v-else-if="store.error"
      type="error"
      variant="tonal"
      class="ma-4"
      closable
      @click:close="store.error = null"
    >
      <v-alert-title>{{ t('summaries.loadError') }}</v-alert-title>
      <div class="d-flex align-center mt-2">
        <span class="mr-4">{{ store.error }}</span>
        <v-btn
          variant="outlined"
          size="small"
          @click="loadSummary"
        >
          <v-icon start>mdi-refresh</v-icon>
          {{ t('common.retry') }}
        </v-btn>
        <v-btn
          variant="text"
          size="small"
          class="ml-2"
          @click="router.push({ name: 'summaries' })"
        >
          {{ t('summaries.backToList') }}
        </v-btn>
      </div>
    </v-alert>

    <!-- Not Found -->
    <v-alert v-else-if="!summary" type="error" variant="tonal" class="ma-4">
      {{ t('summaries.notFound') }}
      <template #append>
        <v-btn variant="text" @click="router.push({ name: 'summaries' })">
          {{ t('summaries.backToList') }}
        </v-btn>
      </template>
    </v-alert>

    <!-- Dashboard Content -->
    <template v-else>
      <!-- Header -->
      <div class="d-flex align-center mb-4 flex-wrap ga-2">
        <v-btn
          icon="mdi-arrow-left"
          variant="text"
          :aria-label="t('summaries.backToList')"
          @click="router.push({ name: 'summaries' })"
        />

        <div class="flex-grow-1">
          <h1 class="text-h5 font-weight-bold">{{ summary.name }}</h1>
          <p v-if="summary.description" class="text-body-2 text-medium-emphasis mb-0">
            {{ summary.description }}
          </p>
        </div>

        <v-chip
          :color="statusColor"
          size="small"
          variant="tonal"
          role="status"
        >
          {{ t(`summaries.status${summary.status.charAt(0)}${summary.status.slice(1).toLowerCase()}`) }}
        </v-chip>

        <v-btn
          :icon="summary.is_favorite ? 'mdi-star' : 'mdi-star-outline'"
          :color="summary.is_favorite ? 'amber' : undefined"
          variant="text"
          :aria-label="summary.is_favorite ? t('summaries.removeFromFavorites') : t('summaries.addToFavorites')"
          :aria-pressed="summary.is_favorite"
          @click="toggleFavorite"
        />

        <v-menu>
          <template #activator="{ props }">
            <v-btn icon="mdi-dots-vertical" variant="text" :aria-label="t('summaries.moreActions')" v-bind="props" />
          </template>
          <v-list density="compact">
            <v-list-item prepend-icon="mdi-pencil" :title="t('common.edit')" @click="showSettings = true" />
            <v-list-item prepend-icon="mdi-share-variant" :title="t('summaries.share')" @click="showShare = true" />
            <v-list-item prepend-icon="mdi-history" :title="t('summaries.executionHistory')" @click="showHistory = true" />
            <v-divider />
            <v-list-item prepend-icon="mdi-file-pdf-box" :title="t('summaries.exportPdf')" :loading="isExporting" @click="exportPdf" />
            <v-list-item prepend-icon="mdi-file-excel" :title="t('summaries.exportExcel')" :loading="isExporting" @click="exportExcel" />
          </v-list>
        </v-menu>
      </div>

      <!-- Action Bar -->
      <v-card class="mb-4">
        <v-card-text class="d-flex align-center flex-wrap ga-2">
          <v-btn
            color="primary"
            variant="flat"
            :loading="isExecuting"
            :aria-busy="isExecuting"
            @click="executeSummary(true)"
          >
            <v-icon start aria-hidden="true">mdi-refresh</v-icon>
            {{ t('summaries.refresh') }}
          </v-btn>

          <v-btn
            variant="outlined"
            :loading="isCheckingUpdates"
            :aria-busy="isCheckingUpdates"
            @click="startCheckUpdates"
          >
            <v-icon start aria-hidden="true">mdi-cloud-refresh</v-icon>
            {{ t('summaries.checkUpdates') }}
          </v-btn>

          <v-spacer />

          <v-btn
            v-if="editMode"
            variant="tonal"
            color="success"
            @click="editMode = false"
          >
            <v-icon start aria-hidden="true">mdi-check</v-icon>
            {{ t('summaries.doneEditing') }}
          </v-btn>
          <v-btn
            v-else
            variant="outlined"
            @click="editMode = true"
          >
            <v-icon start aria-hidden="true">mdi-pencil</v-icon>
            {{ t('summaries.editLayout') }}
          </v-btn>

          <v-btn
            v-if="editMode"
            variant="tonal"
            color="primary"
            @click="showAddWidget = true"
          >
            <v-icon start aria-hidden="true">mdi-plus</v-icon>
            {{ t('summaries.addWidget') }}
          </v-btn>

          <!-- Last Execution Info -->
          <div v-if="lastExecution" class="text-caption text-medium-emphasis">
            <v-icon size="small" class="mr-1">mdi-clock-outline</v-icon>
            {{ t('summaries.lastUpdated') }}: {{ formatRelativeTime(lastExecution.completed_at) }}
            <v-chip
              v-if="lastExecution.has_changes"
              size="x-small"
              color="success"
              variant="tonal"
              class="ml-2"
            >
              {{ t('summaries.hasChanges') }}
            </v-chip>
          </div>
        </v-card-text>
      </v-card>

      <!-- Widgets Grid -->
      <div
        v-if="widgets.length > 0"
        class="widgets-grid"
        :class="{ 'widgets-grid--editing': editMode }"
        role="region"
        :aria-label="t('summaries.dashboard.widgetsGrid')"
      >
        <SummaryWidgetRenderer
          v-for="widget in widgets"
          :key="widget.id"
          :widget="widget"
          :data="getWidgetData(widget.id)"
          :edit-mode="editMode"
          :style="getWidgetStyle(widget)"
          @edit="editWidget(widget)"
          @delete="deleteWidget(widget)"
        />
      </div>

      <!-- Empty Widgets State -->
      <v-card v-else class="text-center py-12">
        <v-icon size="80" color="grey-lighten-1" class="mb-4">mdi-widgets-outline</v-icon>
        <div class="text-h6 text-medium-emphasis mb-2">{{ t('summaries.noWidgets') }}</div>
        <div class="text-body-2 text-medium-emphasis mb-4">{{ t('summaries.noWidgetsHint') }}</div>
        <v-btn color="primary" @click="showAddWidget = true">
          <v-icon start>mdi-plus</v-icon>
          {{ t('summaries.addFirstWidget') }}
        </v-btn>
      </v-card>
    </template>

    <!-- Settings Dialog -->
    <SummaryEditDialog
      v-if="summary"
      v-model="showSettings"
      :summary="summary"
      @updated="loadSummary"
    />

    <!-- Share Dialog -->
    <SummaryShareDialog
      v-if="summary"
      v-model="showShare"
      :summary="summary"
    />

    <!-- Add Widget Dialog -->
    <SummaryAddWidgetDialog
      v-if="summary"
      v-model="showAddWidget"
      :summary-id="summary.id"
      @added="onWidgetAdded"
    />

    <!-- Edit Widget Dialog -->
    <SummaryWidgetEditDialog
      v-if="editingWidget && summary"
      v-model="showEditWidget"
      :summary-id="summary.id"
      :widget="editingWidget"
      :widget-data="getWidgetData(editingWidget.id)"
      @updated="onWidgetUpdated"
    />

    <!-- Execution History Dialog -->
    <SummaryHistoryDialog
      v-if="summary"
      v-model="showHistory"
      :summary-id="summary.id"
    />

    <!-- Delete Widget Confirmation Dialog -->
    <v-dialog v-model="showDeleteDialog" :max-width="DIALOG_SIZES.XS" role="alertdialog" aria-modal="true">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon color="warning" class="mr-2" aria-hidden="true">mdi-alert</v-icon>
          {{ t('summaries.deleteWidgetTitle') }}
        </v-card-title>
        <v-card-text>
          {{ t('summaries.deleteWidgetConfirm', { title: widgetToDelete?.title || '' }) }}
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="cancelDeleteWidget">
            {{ t('common.cancel') }}
          </v-btn>
          <v-btn color="error" variant="flat" @click="confirmDeleteWidget">
            {{ t('common.delete') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Check Updates Progress Dialog -->
    <v-dialog v-model="showCheckUpdatesDialog" :max-width="DIALOG_SIZES.XS" persistent>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon color="primary" class="mr-2" aria-hidden="true">mdi-cloud-refresh</v-icon>
          {{ t('summaries.checkUpdatesTitle') }}
        </v-card-title>
        <v-card-text>
          <v-progress-linear
            v-if="checkUpdatesProgress"
            :model-value="checkUpdatesProgressPercent"
            color="primary"
            height="8"
            rounded
            class="mb-4"
          />
          <div class="text-center mb-2">
            <span v-if="checkUpdatesProgress">
              {{ checkUpdatesProgress.completed_sources }} {{ t('summaries.of') }} {{ checkUpdatesProgress.total_sources }} {{ t('summaries.sourcesChecked') }}
            </span>
          </div>
          <div class="text-caption text-center text-medium-emphasis">
            <template v-if="checkUpdatesProgress?.current_source">
              {{ t('summaries.currentlyChecking') }}: {{ checkUpdatesProgress.current_source }}
            </template>
            <template v-else-if="checkUpdatesProgress?.message">
              {{ checkUpdatesProgress.message }}
            </template>
          </div>
          <v-alert
            v-if="checkUpdatesProgress?.error"
            type="error"
            variant="tonal"
            density="compact"
            class="mt-4"
          >
            {{ checkUpdatesProgress.error }}
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            :disabled="checkUpdatesProgress?.status === 'crawling' || checkUpdatesProgress?.status === 'updating'"
            @click="closeCheckUpdatesDialog"
          >
            {{ checkUpdatesProgress?.status === 'completed' || checkUpdatesProgress?.status === 'failed' ? t('common.close') : t('common.cancel') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useCustomSummariesStore, type SummaryWidget } from '@/stores/customSummaries'
import { useSnackbar } from '@/composables/useSnackbar'
import SummaryEditDialog from '@/components/summaries/SummaryEditDialog.vue'
import SummaryShareDialog from '@/components/summaries/SummaryShareDialog.vue'
import SummaryAddWidgetDialog from '@/components/summaries/SummaryAddWidgetDialog.vue'
import SummaryWidgetEditDialog from '@/components/summaries/SummaryWidgetEditDialog.vue'
import SummaryWidgetRenderer from '@/components/summaries/SummaryWidgetRenderer.vue'
import SummaryHistoryDialog from '@/components/summaries/SummaryHistoryDialog.vue'
import { DIALOG_SIZES } from '@/config/ui'
import { usePageContextProvider } from '@/composables/usePageContext'
import type { PageContextData, WidgetSummary } from '@/composables/assistant/types'
import { useDateFormatter } from '@/composables'

const { formatRelativeTime } = useDateFormatter()

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const store = useCustomSummariesStore()
const { showSuccess, showError } = useSnackbar()

// Responsive state
const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1200)

function handleResize() {
  windowWidth.value = window.innerWidth
}

// State
const editMode = ref(false)
const showSettings = ref(false)
const showShare = ref(false)
const showAddWidget = ref(false)
const showEditWidget = ref(false)
const showHistory = ref(false)
const editingWidget = ref<SummaryWidget | null>(null)
const isExporting = ref(false)
const showDeleteDialog = ref(false)
const widgetToDelete = ref<SummaryWidget | null>(null)
const showCheckUpdatesDialog = ref(false)
let checkUpdatesPollingInterval: ReturnType<typeof setInterval> | null = null

// Computed
const summary = computed(() => store.currentSummary)
const widgets = computed(() => summary.value?.widgets || [])
const lastExecution = computed(() => summary.value?.last_execution)
const isLoading = computed(() => store.isLoading)
const isExecuting = computed(() => store.isExecuting)
const isCheckingUpdates = computed(() => store.isCheckingUpdates)
const checkUpdatesProgress = computed(() => store.checkUpdatesProgress)
const checkUpdatesProgressPercent = computed(() => {
  const progress = store.checkUpdatesProgress
  if (!progress || progress.total_sources === 0) return 0
  return (progress.completed_sources / progress.total_sources) * 100
})

const statusColor = computed(() => {
  switch (summary.value?.status) {
    case 'ACTIVE': return 'success'
    case 'DRAFT': return 'grey'
    case 'PAUSED': return 'warning'
    case 'ARCHIVED': return 'error'
    default: return 'grey'
  }
})

// Page Context Provider for AI Assistant awareness
const { updateContext } = usePageContextProvider(
  '/summary-dashboard/',
  (): PageContextData => ({
    // Summary identification
    summary_id: summary.value?.id || undefined,
    summary_name: summary.value?.name || undefined,

    // Widget information
    widgets: widgets.value?.map((w): WidgetSummary => ({
      id: w.id,
      type: w.widget_type,
      title: w.title,
      position: {
        x: w.position?.x || 0,
        y: w.position?.y || 0,
        w: w.position?.w || 1,
        h: w.position?.h || 1
      }
    })) || [],

    // Available features for this view
    available_features: [
      'add_widget',
      'edit_widget',
      'remove_widget',
      'reorder_widgets',
      'configure_widget',
      'refresh_data',
      'share',
      'export',
      'check_updates'
    ],

    // Available actions based on context
    available_actions: [
      'add_widget',
      'edit_widget',
      'configure_widget',
      'refresh',
      ...(editMode.value ? ['reorder_widgets', 'remove_widget'] : [])
    ]
  })
)

// Update context when summary or widgets change
watch([summary, widgets, editMode], () => {
  if (summary.value) {
    updateContext({
      summary_id: summary.value.id,
      summary_name: summary.value.name,
      widgets: widgets.value?.map((w): WidgetSummary => ({
        id: w.id,
        type: w.widget_type,
        title: w.title,
        position: {
          x: w.position?.x || 0,
          y: w.position?.y || 0,
          w: w.position?.w || 1,
          h: w.position?.h || 1
        }
      })) || []
    })
  }
}, { deep: true })

// Methods
async function loadSummary() {
  const summaryId = route.params.id as string
  if (summaryId) {
    await store.loadSummary(summaryId)
  }
}

async function executeSummary(force: boolean) {
  if (!summary.value) return

  try {
    const result = await store.executeSummary(summary.value.id, force)
    if (result) {
      showSuccess(result.message)
      // Reload to get new data
      await loadSummary()
    }
  } catch (e) {
    showError(t('summaries.executeError'))
  }
}

async function toggleFavorite() {
  if (!summary.value) return
  await store.toggleFavorite(summary.value.id)
}

async function startCheckUpdates() {
  if (!summary.value) return

  showCheckUpdatesDialog.value = true

  try {
    const result = await store.checkForUpdates(summary.value.id)
    if (!result) {
      showCheckUpdatesDialog.value = false
      // Show error from store if available
      if (store.error) {
        showError(store.error)
      }
      return
    }

    // Start polling for progress
    const taskId = result.task_id
    checkUpdatesPollingInterval = setInterval(async () => {
      if (!summary.value) return

      const progress = await store.pollCheckUpdatesProgress(summary.value.id, taskId)

      if (progress?.status === 'completed') {
        stopCheckUpdatesPolling()
        showSuccess(t('summaries.checkUpdatesCompleted'))
        await loadSummary()
      } else if (progress?.status === 'failed') {
        stopCheckUpdatesPolling()
        showError(progress.error || t('summaries.checkUpdatesFailed'))
      }
    }, 2000) // Poll every 2 seconds
  } catch (e) {
    showCheckUpdatesDialog.value = false
    showError(t('summaries.checkUpdatesFailed'))
  }
}

function stopCheckUpdatesPolling() {
  if (checkUpdatesPollingInterval) {
    clearInterval(checkUpdatesPollingInterval)
    checkUpdatesPollingInterval = null
  }
}

function closeCheckUpdatesDialog() {
  stopCheckUpdatesPolling()
  showCheckUpdatesDialog.value = false
  if (summary.value) {
    store.cancelCheckUpdates(summary.value.id)
  }
}

function getWidgetData(widgetId: string): Record<string, unknown>[] {
  const widgetKey = `widget_${widgetId}`
  const cachedData = lastExecution.value?.cached_data?.[widgetKey]
  if (cachedData && typeof cachedData === 'object' && 'data' in cachedData && Array.isArray(cachedData.data)) {
    return cachedData.data as Record<string, unknown>[]
  }
  return []
}

function getWidgetStyle(widget: SummaryWidget): Record<string, string> {
  const pos = widget.position

  // Get current grid columns based on viewport width
  let gridCols = 4
  if (windowWidth.value <= 600) {
    gridCols = 1
  } else if (windowWidth.value <= 960) {
    gridCols = 2
  } else if (windowWidth.value <= 1280) {
    gridCols = 3
  }

  // On single-column layout, stack widgets vertically
  if (gridCols === 1) {
    return {
      gridColumn: '1 / -1',
      gridRow: 'auto',
    }
  }

  // Map and table widgets always get full width for better visibility
  if (widget.widget_type === 'map' || widget.widget_type === 'table') {
    return {
      gridColumn: '1 / -1',
      gridRow: `${pos.y + 1} / span ${Math.max(pos.h, widget.widget_type === 'map' ? 3 : 2)}`,
    }
  }

  // Clamp x position and width to available columns
  const clampedX = Math.min(pos.x, gridCols - 1)
  const maxWidth = gridCols - clampedX
  const clampedW = Math.min(pos.w, maxWidth)

  return {
    gridColumn: `${clampedX + 1} / span ${clampedW}`,
    gridRow: `${pos.y + 1} / span ${pos.h}`,
  }
}

function editWidget(widget: SummaryWidget) {
  editingWidget.value = widget
  showEditWidget.value = true
}

function deleteWidget(widget: SummaryWidget) {
  widgetToDelete.value = widget
  showDeleteDialog.value = true
}

async function confirmDeleteWidget() {
  if (!summary.value || !widgetToDelete.value) return

  const success = await store.deleteWidget(summary.value.id, widgetToDelete.value.id)
  if (success) {
    showSuccess(t('summaries.widgetDeleted'))
  }
  showDeleteDialog.value = false
  widgetToDelete.value = null
}

function cancelDeleteWidget() {
  showDeleteDialog.value = false
  widgetToDelete.value = null
}

function onWidgetAdded() {
  showAddWidget.value = false
  loadSummary()
}

function onWidgetUpdated() {
  showEditWidget.value = false
  editingWidget.value = null
  loadSummary()
}

async function exportPdf() {
  if (!summary.value) return

  isExporting.value = true
  try {
    const filename = `${summary.value.name.replace(/[^a-zA-Z0-9äöüÄÖÜß]/g, '_')}.pdf`
    const success = await store.exportPdf(summary.value.id, filename)
    if (success) {
      showSuccess(t('summaries.exportPdfSuccess'))
    } else {
      showError(t('summaries.exportPdfError'))
    }
  } catch (e) {
    showError(t('summaries.exportPdfError'))
  } finally {
    isExporting.value = false
  }
}

async function exportExcel() {
  if (!summary.value) return

  isExporting.value = true
  try {
    const filename = `${summary.value.name.replace(/[^a-zA-Z0-9äöüÄÖÜß]/g, '_')}.xlsx`
    const success = await store.exportExcel(summary.value.id, filename)
    if (success) {
      showSuccess(t('summaries.exportExcelSuccess'))
    } else {
      showError(t('summaries.exportExcelError'))
    }
  } catch (e) {
    showError(t('summaries.exportExcelError'))
  } finally {
    isExporting.value = false
  }
}

// formatRelativeTime is now from useDateFormatter

// Lifecycle
onMounted(() => {
  loadSummary()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  stopCheckUpdatesPolling()
})

watch(() => route.params.id, () => {
  loadSummary()
})
</script>

<style scoped>
.summary-dashboard {
  min-height: calc(100vh - 64px);
}

.widgets-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  grid-auto-rows: minmax(150px, auto);
  gap: 16px;
}

/* Responsive Grid Breakpoints */
@media (max-width: 1280px) {
  .widgets-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 960px) {
  .widgets-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
}

/* Tablet Portrait Breakpoint */
@media (max-width: 768px) {
  .widgets-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }

  .summary-dashboard .text-h5 {
    font-size: 1.15rem !important;
  }
}

@media (max-width: 600px) {
  .widgets-grid {
    grid-template-columns: 1fr;
    gap: 8px;
  }
}

.widgets-grid--editing {
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 149px,
    rgba(var(--v-theme-primary), 0.1) 150px
  ),
  repeating-linear-gradient(
    90deg,
    transparent,
    transparent calc(25% - 8px),
    rgba(var(--v-theme-primary), 0.1) calc(25% - 8px),
    rgba(var(--v-theme-primary), 0.1) calc(25%)
  );
  padding: 8px;
  border-radius: 8px;
}
</style>
