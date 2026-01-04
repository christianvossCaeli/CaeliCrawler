<template>
  <div>
    <!-- Process List -->
    <v-card variant="outlined" class="mb-4">
      <v-card-title class="d-flex align-center">
        <span>{{ t('pysis.processes') }}</span>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" color="primary" size="small" @click="showAddProcessDialog = true">
          <v-icon start>mdi-plus</v-icon>
          {{ t('pysis.addProcess') }}
        </v-btn>
      </v-card-title>

      <v-list v-if="processes.length" density="compact">
        <v-list-item
          v-for="process in processes"
          :key="process.id"
          :class="{ 'bg-primary-lighten-5': selectedProcess?.id === process.id }"
          @click="selectProcess(process)"
        >
          <template #prepend>
            <v-icon :color="getSyncStatusColor(process.sync_status)">
              {{ getSyncStatusIcon(process.sync_status) }}
            </v-icon>
          </template>
          <v-list-item-title>
            {{ process.name || process.pysis_process_id }}
          </v-list-item-title>
          <v-list-item-subtitle>
            {{ process.field_count }} {{ t('pysis.fields') }} | {{ t('pysis.lastSynced') }}: {{ formatDate(process.last_synced_at) }}
          </v-list-item-subtitle>
          <template #append>
            <v-btn icon="mdi-delete" size="small" variant="tonal" color="error" :aria-label="t('common.delete')" @click.stop="handleDeleteProcess(process)"></v-btn>
          </template>
        </v-list-item>
      </v-list>
      <v-card-text v-else class="text-center text-medium-emphasis">
        {{ t('pysis.noProcesses') }}
      </v-card-text>
    </v-card>

    <!-- Selected Process Fields -->
    <v-card v-if="selectedProcess" variant="outlined">
      <v-card-title class="d-flex align-center flex-wrap ga-2">
        <span>{{ t('pysis.fieldsFor') }}: {{ selectedProcess.name || selectedProcess.pysis_process_id }}</span>
        <v-spacer></v-spacer>
        <v-btn-group density="compact" variant="outlined">
          <v-btn v-if="flags.pysisFieldTemplates" size="small" @click="showTemplateDialog = true">
            <v-icon start>mdi-content-copy</v-icon>
            {{ t('pysis.template') }}
          </v-btn>
          <v-btn size="small" @click="showAddFieldDialog = true">
            <v-icon start>mdi-plus</v-icon>
            {{ t('pysis.field') }}
          </v-btn>
        </v-btn-group>
        <v-btn-group density="compact" class="ml-2">
          <v-btn size="small" color="secondary" :loading="generating" @click="handleGenerateAllFields">
            <v-icon start>mdi-auto-fix</v-icon>
            {{ t('pysis.ai') }}
          </v-btn>
          <v-btn size="small" color="info" :loading="syncing" @click="handlePullFromPySis">
            <v-icon start>mdi-download</v-icon>
            {{ t('pysis.pull') }}
          </v-btn>
          <v-btn size="small" color="success" :loading="syncing" @click="handlePushToPySis">
            <v-icon start>mdi-upload</v-icon>
            {{ t('pysis.push') }}
          </v-btn>
        </v-btn-group>
        <!-- PySis-Facets Integration -->
        <v-btn-group density="compact" class="ml-2">
          <v-btn
            size="small"
            color="info"
            :loading="analyzingForFacets"
            :disabled="!selectedProcess?.entity_id"
            :title="!selectedProcess?.entity_id ? t('pysis.facets.needsEntity') : ''"
            @click="showAnalyzeForFacetsDialog = true"
          >
            <v-icon start>mdi-brain</v-icon>
            {{ t('pysis.facets.analyzeForFacets') }}
          </v-btn>
          <v-btn
            size="small"
            color="secondary"
            :loading="enrichingFacets"
            :disabled="!selectedProcess?.entity_id"
            :title="!selectedProcess?.entity_id ? t('pysis.facets.needsEntity') : ''"
            @click="showEnrichFacetsDialog = true"
          >
            <v-icon start>mdi-database-arrow-up</v-icon>
            {{ t('pysis.facets.enrichFacets') }}
          </v-btn>
        </v-btn-group>
      </v-card-title>

      <v-divider></v-divider>

      <!-- Generating Fields Indicator -->
      <v-alert
        v-if="generatingFieldIds.size > 0"
        type="info"
        variant="tonal"
        density="compact"
        class="ma-2"
      >
        <div class="d-flex align-center">
          <v-progress-circular size="18" width="2" indeterminate class="mr-3"></v-progress-circular>
          <span>
            <strong>{{ generatingFieldIds.size }}</strong> {{ t('pysis.fieldsGenerating', { count: generatingFieldIds.size }) }}
          </span>
        </div>
      </v-alert>

      <v-table v-if="fields.length" density="compact">
        <thead>
          <tr>
            <th class="col-width-xs">{{ t('pysis.ai') }}</th>
            <th class="col-width-lg">{{ t('pysis.field') }}</th>
            <th class="col-min-width-lg">{{ t('common.value') }}</th>
            <th class="col-width-sm">{{ t('pysis.source') }}</th>
            <th class="col-width-actions">{{ t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="field in sortedFields" :key="field.id">
            <td>
              <v-checkbox
                v-model="field.ai_extraction_enabled"
                density="compact"
                hide-details
                color="primary"
                @change="handleToggleAiExtraction(field)"
              ></v-checkbox>
            </td>
            <td>
              <div class="font-weight-medium">{{ field.internal_name }}</div>
              <code class="text-caption text-medium-emphasis">{{ field.pysis_field_name }}</code>
            </td>
            <td>
              <!-- Generating indicator -->
              <div v-if="generatingFieldIds.has(field.id)" class="generating-indicator mb-2">
                <v-progress-circular size="16" width="2" indeterminate color="info" class="mr-2"></v-progress-circular>
                <span class="text-info text-caption">{{ t('pysis.aiGenerating') }}</span>
              </div>
              <!-- Current Value -->
              <div class="field-value-preview" role="button" tabindex="0" :aria-label="t('pysis.editField')" @click="handleOpenFieldEditor(field)" @keydown.enter.prevent="handleOpenFieldEditor(field)" @keydown.space.prevent="handleOpenFieldEditor(field)">
                {{ truncateValue(field.current_value) || t('pysis.empty') }}
              </div>
              <!-- AI Suggestion (if different from current) -->
              <div v-if="!generatingFieldIds.has(field.id) && field.ai_extracted_value && field.ai_extracted_value !== field.current_value" class="ai-suggestion mt-2">
                <div class="d-flex align-center ga-1 mb-1">
                  <v-icon size="small" color="info">mdi-auto-fix</v-icon>
                  <span class="text-caption text-info font-weight-medium">{{ t('pysis.aiSuggestion') }}</span>
                  <v-chip v-if="field.confidence_score" size="x-small" :color="getConfidenceColor(field.confidence_score)" class="ml-1">
                    {{ Math.round(field.confidence_score * 100) }}%
                  </v-chip>
                </div>
                <div class="ai-suggestion-text text-caption">
                  {{ truncateValue(field.ai_extracted_value, 150) }}
                </div>
                <div class="d-flex ga-1 mt-1">
                  <v-btn size="x-small" color="success" variant="tonal" @click="handleAcceptAiSuggestion(field)">
                    <v-icon start size="small">mdi-check</v-icon>
                    {{ t('pysis.accept') }}
                  </v-btn>
                  <v-btn size="x-small" color="error" variant="tonal" @click="handleRejectAiSuggestion(field)">
                    <v-icon start size="small">mdi-close</v-icon>
                    {{ t('pysis.reject') }}
                  </v-btn>
                </div>
              </div>
            </td>
            <td>
              <v-chip size="x-small" :color="getSourceColor(field.value_source)">
                {{ field.value_source }}
              </v-chip>
              <v-icon v-if="field.needs_push" size="x-small" color="warning" class="ml-1" :title="t('pysis.notSynced')">
                mdi-alert-circle
              </v-icon>
            </td>
            <td>
              <div class="table-actions">
                <v-btn
                  icon="mdi-auto-fix"
                  size="x-small"
                  variant="tonal"
                  :title="t('pysis.generateAI')"
                  :aria-label="t('pysis.generateAI')"
                  :disabled="!field.ai_extraction_enabled || generatingFieldIds.has(field.id)"
                  :loading="generatingFieldIds.has(field.id)"
                  @click="handleGenerateField(field)"
                ></v-btn>
                <v-btn icon="mdi-cog" size="x-small" variant="tonal" :title="t('pysis.settings')" :aria-label="t('pysis.settings')" @click="handleOpenFieldSettings(field)"></v-btn>
                <v-btn icon="mdi-history" size="x-small" variant="tonal" :title="t('pysis.history')" :aria-label="t('pysis.history')" @click="handleShowHistory(field)"></v-btn>
                <v-btn icon="mdi-upload" size="x-small" variant="tonal" color="info" :title="t('pysis.pushToPySis')" :aria-label="t('pysis.pushToPySis')" @click="handlePushFieldToPySis(field)"></v-btn>
                <v-btn icon="mdi-delete" size="x-small" variant="tonal" color="error" :title="t('common.delete')" :aria-label="t('common.delete')" @click="handleDeleteField(field)"></v-btn>
              </div>
            </td>
          </tr>
        </tbody>
      </v-table>
      <v-card-text v-else class="text-center text-medium-emphasis">
        {{ t('pysis.noFields') }}
      </v-card-text>
    </v-card>

    <!-- Dialogs -->
    <AddProcessDialog
      v-model="showAddProcessDialog"
      :loading="loading"
      :show-templates="flags.pysisFieldTemplates"
      :templates="templates"
      @submit="handleCreateProcess"
    />

    <AddFieldDialog
      v-model="showAddFieldDialog"
      :loading="loading"
      :field-types="fieldTypes"
      @submit="handleCreateField"
    />

    <TemplateDialog
      v-if="flags.pysisFieldTemplates"
      v-model="showTemplateDialog"
      :loading="loading"
      :templates="templates"
      @submit="handleApplyTemplate"
    />

    <FieldEditorDialog
      v-model="showFieldEditorDialog"
      :field="editingField"
      @save="handleSaveFieldValue"
    />

    <HistoryDialog
      v-model="showHistoryDialog"
      :field="historyField"
      :entries="historyEntries"
      :loading="loadingHistory"
      @restore="handleRestoreFromHistory"
    />

    <FieldSettingsDialog
      v-model="showFieldSettingsDialog"
      :settings="editingFieldSettings"
      :field-types="fieldTypes"
      :loading="loading"
      @save="handleSaveFieldSettings"
    />

    <AnalyzeForFacetsDialog
      v-model="showAnalyzeForFacetsDialog"
      :loading="analyzingForFacets"
      @submit="handleAnalyzeForFacets"
    />

    <EnrichFacetsDialog
      v-model="showEnrichFacetsDialog"
      :loading="enrichingFacets"
      @submit="handleEnrichFacetsFromPysis"
    />

    <TaskStartedDialog
      v-model="showTaskStartedDialog"
      :message="taskStartedMessage"
      :task-id="startedTaskId"
    />

    <!-- Snackbar -->
    <v-snackbar v-model="snackbar" :color="snackbarColor" :timeout="3000">
      {{ snackbarText }}
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, toRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFeatureFlags } from '@/composables/useFeatureFlags'
import { getErrorMessage } from '@/utils/errorMessage'
import {
  usePySisProcess,
  type PySisField,
  type PySisProcess,
  type PySisHistoryEntry,
} from '@/composables/usePySisProcess'
import {
  AddProcessDialog,
  AddFieldDialog,
  TemplateDialog,
  FieldEditorDialog,
  HistoryDialog,
  FieldSettingsDialog,
  AnalyzeForFacetsDialog,
  EnrichFacetsDialog,
  TaskStartedDialog,
} from './pysis/dialogs'

const props = defineProps<{
  municipality: string
}>()

const emit = defineEmits<{
  updated: []
  'update:process-count': [count: number]
}>()

const { t } = useI18n()
const { flags } = useFeatureFlags()

// Use the composable for all business logic
const municipalityRef = toRef(props, 'municipality')
const pysis = usePySisProcess(municipalityRef, {
  onProcessCountChange: (count) => emit('update:process-count', count),
  onUpdated: () => emit('updated'),
})

// Destructure composable state and methods
const {
  loading,
  syncing,
  generating,
  processes,
  selectedProcess,
  fields,
  templates,
  generatingFieldIds,
  historyEntries,
  loadingHistory,
  historyField,
  analyzingForFacets,
  enrichingFacets,
  editingField,
  editingFieldSettings,
  sortedFields,
  fieldTypes,
  formatDate,
  getSyncStatusColor,
  getSyncStatusIcon,
  getSourceColor,
  getConfidenceColor,
  truncateValue,
  loadProcesses,
  loadTemplates,
  selectProcess,
  createProcess,
  deleteProcess,
  createField,
  toggleAiExtraction,
  updateFieldSettings,
  deleteField,
  saveFieldValue,
  restoreFromHistory,
  applyTemplate,
  pullFromPySis,
  pushToPySis,
  pushFieldToPySis,
  generateAllFields,
  generateField,
  acceptAiSuggestion,
  rejectAiSuggestion,
  analyzeForFacets,
  enrichFacetsFromPysis,
  loadHistory,
  openFieldEditor,
  openFieldSettings,
} = pysis

// Dialog state
const showAddProcessDialog = ref(false)
const showAddFieldDialog = ref(false)
const showTemplateDialog = ref(false)
const showFieldEditorDialog = ref(false)
const showHistoryDialog = ref(false)
const showFieldSettingsDialog = ref(false)
const showAnalyzeForFacetsDialog = ref(false)
const showEnrichFacetsDialog = ref(false)
const showTaskStartedDialog = ref(false)

// Task dialog state
const startedTaskId = ref('')
const taskStartedMessage = ref('')

// Snackbar
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

const showMessage = (text: string, color = 'success') => {
  snackbarText.value = text
  snackbarColor.value = color
  snackbar.value = true
}

// Handler functions
const handleCreateProcess = async (form: { pysis_process_id: string; name: string; template_id: string | null }) => {
  try {
    await createProcess(form)
    showMessage(t('pysis.processAdded'))
    showAddProcessDialog.value = false
  } catch (error) {
    showMessage(getErrorMessage(error) || t('pysis.error'), 'error')
  }
}

const handleDeleteProcess = async (process: PySisProcess) => {
  if (!confirm(t('pysis.confirmDeleteProcess', { name: process.name || process.pysis_process_id }))) return
  try {
    await deleteProcess(process)
    showMessage(t('pysis.processDeleted'))
  } catch (error) {
    showMessage(getErrorMessage(error) || t('pysis.error'), 'error')
  }
}

const handleCreateField = async (form: { internal_name: string; pysis_field_name: string; field_type: string; ai_extraction_enabled: boolean; ai_extraction_prompt: string }) => {
  try {
    await createField(form)
    showMessage(t('pysis.fieldAdded'))
    showAddFieldDialog.value = false
  } catch (error) {
    showMessage(getErrorMessage(error) || t('pysis.error'), 'error')
  }
}

const handleToggleAiExtraction = async (field: PySisField) => {
  try {
    await toggleAiExtraction(field)
  } catch {
    showMessage(t('pysis.error'), 'error')
  }
}

const handleOpenFieldEditor = (field: PySisField) => {
  openFieldEditor(field)
  showFieldEditorDialog.value = true
}

const handleOpenFieldSettings = (field: PySisField) => {
  openFieldSettings(field)
  showFieldSettingsDialog.value = true
}

const handleSaveFieldSettings = async (settings: { id: string; internal_name: string; field_type: string; ai_extraction_enabled?: boolean; ai_extraction_prompt?: string }) => {
  try {
    await updateFieldSettings(settings)
    showFieldSettingsDialog.value = false
    showMessage(t('pysis.settingsSaved'))
  } catch (error) {
    showMessage(getErrorMessage(error) || t('pysis.error'), 'error')
  }
}

const handleDeleteField = async (field: PySisField) => {
  if (!confirm(t('pysis.confirmDeleteField', { name: field.internal_name }))) return
  try {
    await deleteField(field)
    showMessage(t('pysis.fieldDeleted'))
  } catch (error) {
    showMessage(getErrorMessage(error) || t('pysis.error'), 'error')
  }
}

const handleApplyTemplate = async (templateId: string, overwrite: boolean) => {
  try {
    await applyTemplate(templateId, overwrite)
    showMessage(t('pysis.templateApplied'))
    showTemplateDialog.value = false
  } catch (error) {
    showMessage(getErrorMessage(error) || t('pysis.error'), 'error')
  }
}

const handlePullFromPySis = async () => {
  try {
    const result = await pullFromPySis()
    if (result) {
      let msg = ''
      if (result.created > 0 && result.updated > 0) {
        msg = t('pysis.newFieldsCreated', { created: result.created }) + ', ' + t('pysis.fieldsUpdated', { updated: result.updated })
      } else if (result.created > 0) {
        msg = t('pysis.newFieldsCreated', { created: result.created })
      } else if (result.updated > 0) {
        msg = t('pysis.fieldsUpdated', { updated: result.updated })
      } else {
        msg = t('pysis.noChanges')
      }
      showMessage(msg)
    }
  } catch (error) {
    showMessage(getErrorMessage(error) || t('pysis.error'), 'error')
  }
}

const handlePushToPySis = async () => {
  try {
    const count = await pushToPySis()
    showMessage(t('pysis.fieldsSynced', { count }))
  } catch (error) {
    showMessage(getErrorMessage(error) || t('pysis.error'), 'error')
  }
}

const handlePushFieldToPySis = async (field: PySisField) => {
  try {
    await pushFieldToPySis(field)
    showMessage(t('pysis.fieldsSynced', { count: 1 }))
  } catch (error) {
    showMessage(getErrorMessage(error) || t('pysis.error'), 'error')
  }
}

const handleGenerateAllFields = async () => {
  try {
    const count = await generateAllFields()
    showMessage(t('pysis.fieldsGenerated', { count }))
  } catch (error) {
    showMessage(getErrorMessage(error) || t('pysis.error'), 'error')
  }
}

const handleGenerateField = async (field: PySisField) => {
  try {
    await generateField(field)
    showMessage(t('pysis.aiGenerationStarted'), 'info')
  } catch (error) {
    showMessage(getErrorMessage(error) || t('pysis.error'), 'error')
  }
}

const handleAcceptAiSuggestion = async (field: PySisField) => {
  try {
    await acceptAiSuggestion(field)
    showMessage(t('pysis.aiSuggestionAccepted'))
  } catch (error) {
    showMessage(getErrorMessage(error) || t('pysis.error'), 'error')
  }
}

const handleRejectAiSuggestion = async (field: PySisField) => {
  try {
    await rejectAiSuggestion(field)
    showMessage(t('pysis.aiSuggestionRejected'))
  } catch (error) {
    showMessage(getErrorMessage(error) || t('pysis.error'), 'error')
  }
}

const handleShowHistory = async (field: PySisField) => {
  showHistoryDialog.value = true
  try {
    await loadHistory(field)
  } catch {
    showMessage(t('pysis.error'), 'error')
  }
}

const handleRestoreFromHistory = async (entry: PySisHistoryEntry) => {
  try {
    await restoreFromHistory(entry)
    showMessage(t('pysis.valueRestored'))
    showHistoryDialog.value = false
  } catch (error) {
    showMessage(getErrorMessage(error) || t('pysis.error'), 'error')
  }
}

const handleAnalyzeForFacets = async (options: { includeEmpty: boolean; minConfidence: number }) => {
  try {
    const taskId = await analyzeForFacets(options)
    startedTaskId.value = taskId
    taskStartedMessage.value = t('pysis.facets.analyzeTaskStartedMessage')
    showAnalyzeForFacetsDialog.value = false
    showTaskStartedDialog.value = true
  } catch (error) {
    showMessage(getErrorMessage(error) || t('pysis.error'), 'error')
  }
}

const handleEnrichFacetsFromPysis = async (overwrite: boolean) => {
  try {
    const taskId = await enrichFacetsFromPysis(overwrite)
    startedTaskId.value = taskId
    taskStartedMessage.value = t('pysis.facets.enrichTaskStartedMessage')
    showEnrichFacetsDialog.value = false
    showTaskStartedDialog.value = true
  } catch (error) {
    showMessage(getErrorMessage(error) || t('pysis.error'), 'error')
  }
}

const handleSaveFieldValue = async (value: string) => {
  if (!editingField.value) return
  try {
    await saveFieldValue(editingField.value, value)
    showFieldEditorDialog.value = false
    showMessage(t('pysis.valueSaved'))
  } catch (error) {
    showMessage(getErrorMessage(error) || t('pysis.error'), 'error')
  }
}

// Field Editor sync
watch(editingField, (field) => {
  if (!field) showFieldEditorDialog.value = false
})

watch(showFieldEditorDialog, (show) => {
  if (!show) editingField.value = null
})

// Initialize
onMounted(() => {
  loadProcesses()
  if (flags.value.pysisFieldTemplates) {
    loadTemplates()
  }
})
</script>

<style scoped>
@import './pysis/styles/pysis-tab.css';
</style>
