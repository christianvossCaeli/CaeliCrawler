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
          <template v-slot:prepend>
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
          <template v-slot:append>
            <v-btn icon="mdi-delete" size="small" variant="tonal" color="error" @click.stop="deleteProcess(process)" :aria-label="t('common.delete')"></v-btn>
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
          <v-btn size="small" color="secondary" @click="generateAllFields" :loading="generating">
            <v-icon start>mdi-auto-fix</v-icon>
            {{ t('pysis.ai') }}
          </v-btn>
          <v-btn size="small" color="info" @click="pullFromPySis" :loading="syncing">
            <v-icon start>mdi-download</v-icon>
            {{ t('pysis.pull') }}
          </v-btn>
          <v-btn size="small" color="success" @click="pushToPySis" :loading="syncing">
            <v-icon start>mdi-upload</v-icon>
            {{ t('pysis.push') }}
          </v-btn>
        </v-btn-group>
        <!-- PySis-Facets Integration -->
        <v-btn-group density="compact" class="ml-2">
          <v-btn
            size="small"
            color="info"
            @click="showAnalyzeForFacetsDialog = true"
            :loading="analyzingForFacets"
            :disabled="!selectedProcess?.entity_id"
            :title="!selectedProcess?.entity_id ? t('pysis.facets.needsEntity') : ''"
          >
            <v-icon start>mdi-brain</v-icon>
            {{ t('pysis.facets.analyzeForFacets') }}
          </v-btn>
          <v-btn
            size="small"
            color="secondary"
            @click="showEnrichFacetsDialog = true"
            :loading="enrichingFacets"
            :disabled="!selectedProcess?.entity_id"
            :title="!selectedProcess?.entity_id ? t('pysis.facets.needsEntity') : ''"
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
                @change="toggleAiExtraction(field)"
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
              <div class="field-value-preview" role="button" tabindex="0" :aria-label="t('pysis.editField')" @click="openFieldEditor(field)" @keydown.enter.prevent="openFieldEditor(field)" @keydown.space.prevent="openFieldEditor(field)">
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
                  <v-btn size="x-small" color="success" variant="tonal" @click="acceptAiSuggestion(field)">
                    <v-icon start size="small">mdi-check</v-icon>
                    {{ t('pysis.accept') }}
                  </v-btn>
                  <v-btn size="x-small" color="error" variant="tonal" @click="rejectAiSuggestion(field)">
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
                  @click="generateField(field)"
                  :title="t('pysis.generateAI')"
                  :aria-label="t('pysis.generateAI')"
                  :disabled="!field.ai_extraction_enabled || generatingFieldIds.has(field.id)"
                  :loading="generatingFieldIds.has(field.id)"
                ></v-btn>
                <v-btn icon="mdi-cog" size="x-small" variant="tonal" @click="openFieldSettings(field)" :title="t('pysis.settings')" :aria-label="t('pysis.settings')"></v-btn>
                <v-btn icon="mdi-history" size="x-small" variant="tonal" @click="showHistory(field)" :title="t('pysis.history')" :aria-label="t('pysis.history')"></v-btn>
                <v-btn icon="mdi-upload" size="x-small" variant="tonal" color="info" @click="pushFieldToPySis(field)" :title="t('pysis.pushToPySis')" :aria-label="t('pysis.pushToPySis')"></v-btn>
                <v-btn icon="mdi-delete" size="x-small" variant="tonal" color="error" @click="deleteField(field)" :title="t('common.delete')" :aria-label="t('common.delete')"></v-btn>
              </div>
            </td>
          </tr>
        </tbody>
      </v-table>
      <v-card-text v-else class="text-center text-medium-emphasis">
        {{ t('pysis.noFields') }}
      </v-card-text>
    </v-card>

    <!-- Add Process Dialog -->
    <v-dialog v-model="showAddProcessDialog" max-width="500">
      <v-card>
        <v-card-title>{{ t('pysis.addProcess') }}</v-card-title>
        <v-card-text class="pt-4">
          <v-text-field
            v-model="newProcess.pysis_process_id"
            :label="t('pysis.processId')"
            :placeholder="t('pysis.processIdPlaceholder')"
            :hint="t('pysis.processIdHint')"
            persistent-hint
            class="mb-3"
          ></v-text-field>
          <v-text-field
            v-model="newProcess.name"
            :label="t('pysis.displayName')"
            :placeholder="t('pysis.displayNamePlaceholder')"
          ></v-text-field>
          <v-select
            v-if="flags.pysisFieldTemplates"
            v-model="newProcess.template_id"
            :items="templates"
            item-title="name"
            item-value="id"
            :label="t('pysis.applyTemplate')"
            clearable
            class="mt-3"
          ></v-select>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="showAddProcessDialog = false">{{ t('common.cancel') }}</v-btn>
          <v-btn variant="tonal" color="primary" @click="createProcess" :loading="loading">{{ t('common.add') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Add Field Dialog -->
    <v-dialog v-model="showAddFieldDialog" max-width="500">
      <v-card>
        <v-card-title>{{ t('pysis.addField') }}</v-card-title>
        <v-card-text class="pt-4">
          <v-text-field
            v-model="newField.internal_name"
            :label="t('pysis.internalName')"
            :placeholder="t('pysis.internalNamePlaceholder')"
            class="mb-3"
          ></v-text-field>
          <v-text-field
            v-model="newField.pysis_field_name"
            :label="t('pysis.pysisFieldName')"
            :placeholder="t('pysis.pysisFieldNamePlaceholder')"
            :hint="t('pysis.pysisFieldNameHint')"
            persistent-hint
            class="mb-3"
          ></v-text-field>
          <v-select
            v-model="newField.field_type"
            :items="fieldTypes"
            :label="t('pysis.fieldType')"
            class="mb-3"
          ></v-select>
          <v-switch
            v-model="newField.ai_extraction_enabled"
            :label="t('pysis.aiExtractionEnabled')"
            color="primary"
          ></v-switch>
          <v-textarea
            v-if="newField.ai_extraction_enabled"
            v-model="newField.ai_extraction_prompt"
            :label="t('pysis.aiPrompt')"
            :placeholder="t('pysis.aiPromptPlaceholder')"
            rows="3"
          ></v-textarea>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="showAddFieldDialog = false">{{ t('common.cancel') }}</v-btn>
          <v-btn variant="tonal" color="primary" @click="createField" :loading="loading">{{ t('common.add') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Apply Template Dialog -->
    <v-dialog v-if="flags.pysisFieldTemplates" v-model="showTemplateDialog" max-width="500">
      <v-card>
        <v-card-title>{{ t('pysis.template') }}</v-card-title>
        <v-card-text class="pt-4">
          <v-select
            v-model="selectedTemplateId"
            :items="templates"
            item-title="name"
            item-value="id"
            :label="t('pysis.selectTemplate')"
            class="mb-3"
          >
            <template v-slot:item="{ item, props }">
              <v-list-item v-bind="props">
                <v-list-item-subtitle>
                  {{ item.raw.fields?.length || 0 }} {{ t('pysis.fields') }}
                </v-list-item-subtitle>
              </v-list-item>
            </template>
          </v-select>
          <v-switch
            v-model="overwriteExisting"
            :label="t('pysis.overwriteExisting')"
            color="warning"
          ></v-switch>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="showTemplateDialog = false">{{ t('common.cancel') }}</v-btn>
          <v-btn variant="tonal" color="primary" @click="applyTemplate" :loading="loading" :disabled="!selectedTemplateId">{{ t('pysis.apply') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Field Editor Dialog -->
    <v-dialog v-model="showFieldEditorDialog" max-width="700">
      <v-card v-if="editingField">
        <v-card-title>
          {{ editingField.internal_name }}
          <v-chip size="small" class="ml-2" :color="getSourceColor(editingField.value_source)">
            {{ editingField.value_source }}
          </v-chip>
        </v-card-title>
        <v-card-subtitle>
          <code>{{ editingField.pysis_field_name }}</code>
        </v-card-subtitle>
        <v-card-text>
          <v-textarea
            v-model="editingField.current_value"
            :label="t('common.value')"
            variant="outlined"
            rows="10"
            auto-grow
          ></v-textarea>
          <v-alert v-if="editingField.ai_extracted_value && editingField.ai_extracted_value !== editingField.current_value" type="info" density="compact" class="mt-3">
            <strong>{{ t('pysis.aiSuggestion') }}:</strong>
            <div class="text-body-2 mt-1">{{ editingField.ai_extracted_value }}</div>
            <v-btn size="small" class="mt-2" @click="useAiValue">{{ t('pysis.useAiValue') }}</v-btn>
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-btn variant="tonal" @click="showFieldEditorDialog = false">{{ t('common.cancel') }}</v-btn>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" color="primary" @click="saveFieldValue">{{ t('common.save') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- History Dialog -->
    <v-dialog v-model="showHistoryDialog" max-width="600">
      <v-card v-if="historyField">
        <v-card-title>
          <v-icon start>mdi-history</v-icon>
          {{ t('pysis.history') }}: {{ historyField.internal_name }}
        </v-card-title>
        <v-card-text>
          <v-progress-linear v-if="loadingHistory" indeterminate></v-progress-linear>
          <v-list v-else-if="historyEntries.length" density="compact">
            <v-list-item
              v-for="entry in historyEntries"
              :key="entry.id"
              :class="getHistoryItemClass(entry.action)"
            >
              <template v-slot:prepend>
                <v-icon :color="getHistoryActionColor(entry.action)" size="small">
                  {{ getHistoryActionIcon(entry.action) }}
                </v-icon>
              </template>
              <v-list-item-title class="text-caption">
                <v-chip size="x-small" :color="getSourceColor(entry.source)" class="mr-2">
                  {{ entry.source }}
                </v-chip>
                <span class="text-medium-emphasis">{{ formatHistoryAction(entry.action) }}</span>
                <span v-if="entry.confidence_score" class="ml-2 text-medium-emphasis-darken-1">
                  ({{ Math.round(entry.confidence_score * 100) }}% {{ t('pysis.confidence') }})
                </span>
              </v-list-item-title>
              <v-list-item-subtitle class="mt-1">
                <div class="history-value">{{ truncateValue(entry.value, 200) || t('pysis.empty') }}</div>
                <div class="text-caption text-medium-emphasis mt-1">{{ formatDate(entry.created_at) }}</div>
              </v-list-item-subtitle>
              <template v-slot:append>
                <v-btn
                  v-if="entry.action !== 'rejected'"
                  icon="mdi-restore"
                  size="x-small"
                  variant="tonal"
                  @click="restoreFromHistory(entry)"
                  :title="t('pysis.restoreValue')"
                ></v-btn>
              </template>
            </v-list-item>
          </v-list>
          <div v-else class="text-center text-medium-emphasis py-4">
            {{ t('pysis.noHistory') }}
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="showHistoryDialog = false">{{ t('common.close') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Field Settings Dialog -->
    <v-dialog v-model="showFieldSettingsDialog" max-width="600">
      <v-card v-if="editingFieldSettings">
        <v-card-title>
          <v-icon start>mdi-cog</v-icon>
          {{ t('pysis.fieldSettings') }}: {{ editingFieldSettings.internal_name }}
        </v-card-title>
        <v-card-text class="pt-4">
          <v-text-field
            v-model="editingFieldSettings.internal_name"
            :label="t('pysis.internalName')"
            variant="outlined"
            density="compact"
            class="mb-3"
          ></v-text-field>
          <v-select
            v-model="editingFieldSettings.field_type"
            :items="fieldTypes"
            :label="t('pysis.fieldType')"
            variant="outlined"
            density="compact"
            class="mb-3"
          ></v-select>
          <v-switch
            v-model="editingFieldSettings.ai_extraction_enabled"
            :label="t('pysis.aiExtractionEnabled')"
            color="primary"
            class="mb-3"
          ></v-switch>
          <v-textarea
            v-model="editingFieldSettings.ai_extraction_prompt"
            :label="t('pysis.aiPrompt')"
            variant="outlined"
            rows="6"
            :placeholder="getDefaultPromptPlaceholder()"
            :hint="t('pysis.aiPromptHint')"
            persistent-hint
          ></v-textarea>
          <v-alert v-if="!editingFieldSettings.ai_extraction_prompt" type="warning" variant="tonal" density="compact" class="mt-3">
            {{ t('pysis.noPromptWarning', { name: editingFieldSettings.internal_name }) }}
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-btn variant="tonal" @click="showFieldSettingsDialog = false">{{ t('common.cancel') }}</v-btn>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" color="primary" @click="saveFieldSettings" :loading="loading">{{ t('common.save') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Analyze for Facets Dialog -->
    <v-dialog v-model="showAnalyzeForFacetsDialog" max-width="500">
      <v-card>
        <v-card-title>
          <v-icon start color="info">mdi-brain</v-icon>
          {{ t('pysis.facets.analyzeForFacetsTitle') }}
        </v-card-title>
        <v-card-text>
          <v-alert type="info" variant="tonal" density="compact" class="mb-4">
            {{ t('pysis.facets.analyzeForFacetsDescription') }}
          </v-alert>
          <v-checkbox
            v-model="analyzeIncludeEmpty"
            :label="t('pysis.facets.includeEmptyFields')"
            density="compact"
            hide-details
            class="mb-2"
          ></v-checkbox>
          <v-slider
            v-model="analyzeMinConfidence"
            :label="t('pysis.facets.minConfidence')"
            :min="0"
            :max="1"
            :step="0.1"
            thumb-label
            density="compact"
            class="mt-4"
          >
            <template v-slot:thumb-label="{ modelValue }">
              {{ Math.round(modelValue * 100) }}%
            </template>
          </v-slider>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="showAnalyzeForFacetsDialog = false">{{ t('common.cancel') }}</v-btn>
          <v-btn variant="tonal" color="info" @click="analyzeForFacets" :loading="analyzingForFacets">
            <v-icon start>mdi-brain</v-icon>
            {{ t('pysis.facets.startAnalysis') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Enrich Facets Dialog -->
    <v-dialog v-model="showEnrichFacetsDialog" max-width="500">
      <v-card>
        <v-card-title>
          <v-icon start color="secondary">mdi-database-arrow-up</v-icon>
          {{ t('pysis.facets.enrichFacetsTitle') }}
        </v-card-title>
        <v-card-text>
          <v-alert type="info" variant="tonal" density="compact" class="mb-4">
            {{ t('pysis.facets.enrichFacetsDescription') }}
          </v-alert>
          <v-checkbox
            v-model="enrichOverwrite"
            :label="t('pysis.facets.overwriteExisting')"
            density="compact"
            hide-details
            color="warning"
          ></v-checkbox>
          <v-alert v-if="enrichOverwrite" type="warning" variant="tonal" density="compact" class="mt-3">
            {{ t('pysis.facets.overwriteWarning') }}
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="showEnrichFacetsDialog = false">{{ t('common.cancel') }}</v-btn>
          <v-btn variant="tonal" color="secondary" @click="enrichFacetsFromPysis" :loading="enrichingFacets">
            <v-icon start>mdi-database-arrow-up</v-icon>
            {{ t('pysis.facets.startEnrichment') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Task Started Info Dialog -->
    <v-dialog v-model="showTaskStartedDialog" max-width="400">
      <v-card>
        <v-card-title>
          <v-icon start color="success">mdi-check-circle</v-icon>
          {{ t('pysis.facets.taskStarted') }}
        </v-card-title>
        <v-card-text>
          <p>{{ taskStartedMessage }}</p>
          <p class="text-caption text-medium-emphasis mt-2">
            {{ t('pysis.facets.taskId') }}: <code>{{ startedTaskId }}</code>
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" color="primary" @click="showTaskStartedDialog = false">{{ t('common.ok') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar -->
    <v-snackbar v-model="snackbar" :color="snackbarColor" :timeout="3000">
      {{ snackbarText }}
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { pysisApi } from '@/services/api'
import { format } from 'date-fns'
import { de } from 'date-fns/locale'
import { useFeatureFlags } from '@/composables/useFeatureFlags'

const { t } = useI18n()
const { flags } = useFeatureFlags()

const props = defineProps<{
  municipality: string
}>()

const emit = defineEmits<{
  updated: []
  'update:process-count': [count: number]
}>()

// State
const loading = ref(false)
const syncing = ref(false)
const generating = ref(false)
const processes = ref<any[]>([])
const selectedProcess = ref<any>(null)
const fields = ref<any[]>([])
const templates = ref<any[]>([])
const availableProcesses = ref<any[]>([])
const loadingAvailableProcesses = ref(false)

// Computed: Sort fields with AI enabled first
const sortedFields = computed(() => {
  return [...fields.value].sort((a, b) => {
    // AI-enabled fields first
    if (a.ai_extraction_enabled && !b.ai_extraction_enabled) return -1
    if (!a.ai_extraction_enabled && b.ai_extraction_enabled) return 1
    // Then sort by internal name
    return (a.internal_name || '').localeCompare(b.internal_name || '')
  })
})

// Dialogs
const showAddProcessDialog = ref(false)
const showAddFieldDialog = ref(false)
const showTemplateDialog = ref(false)
const showFieldEditorDialog = ref(false)
const showManualInput = ref(false)
const showHistoryDialog = ref(false)
const showFieldSettingsDialog = ref(false)

// PySis-Facets Dialogs
const showAnalyzeForFacetsDialog = ref(false)
const showEnrichFacetsDialog = ref(false)
const showTaskStartedDialog = ref(false)

// PySis-Facets State
const analyzingForFacets = ref(false)
const enrichingFacets = ref(false)
const analyzeIncludeEmpty = ref(false)
const analyzeMinConfidence = ref(0)
const enrichOverwrite = ref(false)
const startedTaskId = ref('')
const taskStartedMessage = ref('')

// Field Settings
const editingFieldSettings = ref<any>(null)

// History
const historyField = ref<any>(null)
const historyEntries = ref<any[]>([])
const loadingHistory = ref(false)

// Track fields currently being generated
const generatingFieldIds = ref<Set<string>>(new Set())

// Field Editor
const editingField = ref<any>(null)

// New Process Form
const newProcess = ref({
  pysis_process_id: '',
  name: '',
  template_id: null as string | null,
})

// New Field Form
const newField = ref({
  internal_name: '',
  pysis_field_name: '',
  field_type: 'text',
  ai_extraction_enabled: true,
  ai_extraction_prompt: '',
})

// Template application
const selectedTemplateId = ref<string | null>(null)
const overwriteExisting = ref(false)

// Snackbar
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

const fieldTypes = computed(() => [
  { title: t('pysis.fieldTypes.text'), value: 'text' },
  { title: t('pysis.fieldTypes.number'), value: 'number' },
  { title: t('pysis.fieldTypes.date'), value: 'date' },
  { title: t('pysis.fieldTypes.boolean'), value: 'boolean' },
  { title: t('pysis.fieldTypes.list'), value: 'list' },
])

// Methods
const showMessage = (text: string, color = 'success') => {
  snackbarText.value = text
  snackbarColor.value = color
  snackbar.value = true
}

const formatDate = (dateStr: string | null) => {
  if (!dateStr) return t('results.never')
  return format(new Date(dateStr), 'dd.MM.yyyy HH:mm', { locale: de })
}

const getSyncStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    SYNCED: 'success',
    PENDING: 'warning',
    ERROR: 'error',
    NEVER: 'grey',
  }
  return colors[status] || 'grey'
}

const getSyncStatusIcon = (status: string) => {
  const icons: Record<string, string> = {
    SYNCED: 'mdi-check-circle',
    PENDING: 'mdi-clock',
    ERROR: 'mdi-alert-circle',
    NEVER: 'mdi-help-circle',
  }
  return icons[status] || 'mdi-help-circle'
}

const getSourceColor = (source: string) => {
  const colors: Record<string, string> = {
    AI: 'info',
    MANUAL: 'primary',
    PYSIS: 'purple',
  }
  return colors[source] || 'grey'
}

const getConfidenceColor = (score: number) => {
  if (score >= 0.8) return 'success'
  if (score >= 0.5) return 'warning'
  return 'error'
}

const truncateValue = (value: string | null, maxLength = 100) => {
  if (!value) return null
  if (value.length <= maxLength) return value
  return value.substring(0, maxLength) + '...'
}

const openFieldEditor = (field: any) => {
  // Create a copy to edit
  editingField.value = { ...field }
  showFieldEditorDialog.value = true
}

const saveFieldValue = async () => {
  if (!editingField.value) return

  try {
    await pysisApi.updateFieldValue(editingField.value.id, {
      value: editingField.value.current_value,
      source: 'MANUAL',
    })
    // Update the field in the list
    const field = fields.value.find((f) => f.id === editingField.value.id)
    if (field) {
      field.current_value = editingField.value.current_value
      field.value_source = 'MANUAL'
      field.needs_push = true
    }
    showFieldEditorDialog.value = false
    showMessage(t('pysis.valueSaved'))
  } catch (error: any) {
    showMessage(error.response?.data?.error || t('pysis.error'), 'error')
  }
}

const useAiValue = () => {
  if (editingField.value?.ai_extracted_value) {
    editingField.value.current_value = editingField.value.ai_extracted_value
  }
}

const loadProcesses = async () => {
  if (!props.municipality) return
  try {
    const response = await pysisApi.getProcesses(props.municipality)
    processes.value = response.data.items || []
    emit('update:process-count', processes.value.length)
  } catch (error) {
    console.error('Failed to load processes', error)
    emit('update:process-count', 0)
  }
}

const loadTemplates = async () => {
  try {
    const response = await pysisApi.getTemplates({ is_active: true })
    templates.value = response.data.items || []
  } catch (error) {
    console.error('Failed to load templates', error)
  }
}

const loadAvailableProcesses = async () => {
  if (loadingAvailableProcesses.value) return
  loadingAvailableProcesses.value = true
  try {
    const response = await pysisApi.getAvailableProcesses()
    availableProcesses.value = response.data.items || []
    if (response.data.error) {
      console.warn('PySis API error:', response.data.error)
    }
  } catch (error) {
    console.error('Failed to load available processes', error)
    availableProcesses.value = []
  } finally {
    loadingAvailableProcesses.value = false
  }
}

const selectProcess = async (process: any) => {
  selectedProcess.value = process
  await loadFields()
}

const loadFields = async () => {
  if (!selectedProcess.value) return
  try {
    const response = await pysisApi.getFields(selectedProcess.value.id)
    fields.value = response.data || []
  } catch (error) {
    console.error('Failed to load fields', error)
  }
}

const createProcess = async () => {
  if (!newProcess.value.pysis_process_id) {
    showMessage(t('pysis.enterProcessId'), 'error')
    return
  }

  loading.value = true
  try {
    await pysisApi.createProcess(props.municipality, newProcess.value)
    showMessage(t('pysis.processAdded'))
    showAddProcessDialog.value = false
    newProcess.value = { pysis_process_id: '', name: '', template_id: null }
    await loadProcesses()
    emit('updated')
  } catch (error: any) {
    showMessage(error.response?.data?.error || t('pysis.error'), 'error')
  } finally {
    loading.value = false
  }
}

const deleteProcess = async (process: any) => {
  if (!confirm(t('pysis.confirmDeleteProcess', { name: process.name || process.pysis_process_id }))) return

  try {
    await pysisApi.deleteProcess(process.id)
    showMessage(t('pysis.processDeleted'))
    if (selectedProcess.value?.id === process.id) {
      selectedProcess.value = null
      fields.value = []
    }
    await loadProcesses()
    emit('updated')
  } catch (error: any) {
    showMessage(error.response?.data?.error || t('pysis.error'), 'error')
  }
}

const createField = async () => {
  if (!selectedProcess.value || !newField.value.internal_name || !newField.value.pysis_field_name) {
    showMessage(t('pysis.fillRequired'), 'error')
    return
  }

  loading.value = true
  try {
    await pysisApi.createField(selectedProcess.value.id, newField.value)
    showMessage(t('pysis.fieldAdded'))
    showAddFieldDialog.value = false
    newField.value = { internal_name: '', pysis_field_name: '', field_type: 'text', ai_extraction_enabled: true, ai_extraction_prompt: '' }
    await loadFields()
    await loadProcesses()
  } catch (error: any) {
    showMessage(error.response?.data?.error || t('pysis.error'), 'error')
  } finally {
    loading.value = false
  }
}

const toggleAiExtraction = async (field: any) => {
  try {
    await pysisApi.updateField(field.id, { ai_extraction_enabled: field.ai_extraction_enabled })
  } catch (error) {
    console.error('Failed to toggle AI extraction', error)
    // Revert on error
    field.ai_extraction_enabled = !field.ai_extraction_enabled
    showMessage(t('pysis.error'), 'error')
  }
}

const openFieldSettings = (field: any) => {
  // Create a copy to edit
  editingFieldSettings.value = {
    id: field.id,
    internal_name: field.internal_name,
    field_type: field.field_type,
    ai_extraction_enabled: field.ai_extraction_enabled,
    ai_extraction_prompt: field.ai_extraction_prompt || '',
  }
  showFieldSettingsDialog.value = true
}

const saveFieldSettings = async () => {
  if (!editingFieldSettings.value) return

  loading.value = true
  try {
    await pysisApi.updateField(editingFieldSettings.value.id, {
      internal_name: editingFieldSettings.value.internal_name,
      field_type: editingFieldSettings.value.field_type,
      ai_extraction_enabled: editingFieldSettings.value.ai_extraction_enabled,
      ai_extraction_prompt: editingFieldSettings.value.ai_extraction_prompt || null,
    })

    // Update the field in the local list
    const field = fields.value.find((f) => f.id === editingFieldSettings.value.id)
    if (field) {
      field.internal_name = editingFieldSettings.value.internal_name
      field.field_type = editingFieldSettings.value.field_type
      field.ai_extraction_enabled = editingFieldSettings.value.ai_extraction_enabled
      field.ai_extraction_prompt = editingFieldSettings.value.ai_extraction_prompt
    }

    showFieldSettingsDialog.value = false
    showMessage(t('pysis.settingsSaved'))
  } catch (error: any) {
    showMessage(error.response?.data?.error || t('pysis.error'), 'error')
  } finally {
    loading.value = false
  }
}

const getDefaultPromptPlaceholder = () => {
  if (!editingFieldSettings.value) return ''
  return t('pysis.defaultPromptPlaceholder', { name: editingFieldSettings.value.internal_name })
}

const deleteField = async (field: any) => {
  if (!confirm(t('pysis.confirmDeleteField', { name: field.internal_name }))) return

  try {
    await pysisApi.deleteField(field.id)
    showMessage(t('pysis.fieldDeleted'))
    await loadFields()
    await loadProcesses()
  } catch (error: any) {
    showMessage(error.response?.data?.error || t('pysis.error'), 'error')
  }
}

const applyTemplate = async () => {
  if (!selectedProcess.value || !selectedTemplateId.value) return

  loading.value = true
  try {
    await pysisApi.applyTemplate(selectedProcess.value.id, {
      template_id: selectedTemplateId.value,
      overwrite_existing: overwriteExisting.value,
    })
    showMessage(t('pysis.templateApplied'))
    showTemplateDialog.value = false
    selectedTemplateId.value = null
    overwriteExisting.value = false
    await loadFields()
    await loadProcesses()
  } catch (error: any) {
    showMessage(error.response?.data?.error || t('pysis.error'), 'error')
  } finally {
    loading.value = false
  }
}

const pullFromPySis = async () => {
  if (!selectedProcess.value) return

  syncing.value = true
  try {
    const response = await pysisApi.pullFromPySis(selectedProcess.value.id)
    if (response.data.success) {
      const created = response.data.fields_created || 0
      const updated = response.data.fields_updated || 0
      let msg = ''
      if (created > 0 && updated > 0) {
        msg = t('pysis.newFieldsCreated', { created }) + ', ' + t('pysis.fieldsUpdated', { updated })
      } else if (created > 0) {
        msg = t('pysis.newFieldsCreated', { created })
      } else if (updated > 0) {
        msg = t('pysis.fieldsUpdated', { updated })
      } else {
        msg = t('pysis.noChanges')
      }
      showMessage(msg)
      await loadFields()
      await loadProcesses()
    } else {
      showMessage(response.data.errors?.join(', ') || t('pysis.error'), 'error')
    }
  } catch (error: any) {
    showMessage(error.response?.data?.error || t('pysis.error'), 'error')
  } finally {
    syncing.value = false
  }
}

const pushToPySis = async () => {
  if (!selectedProcess.value) return

  syncing.value = true
  try {
    const response = await pysisApi.pushToPySis(selectedProcess.value.id)
    if (response.data.success) {
      showMessage(t('pysis.fieldsSynced', { count: response.data.fields_synced }))
      await loadFields()
      await loadProcesses()
    } else {
      showMessage(response.data.errors?.join(', ') || t('pysis.error'), 'error')
    }
  } catch (error: any) {
    showMessage(error.response?.data?.error || t('pysis.error'), 'error')
  } finally {
    syncing.value = false
  }
}

const pushFieldToPySis = async (field: any) => {
  try {
    const response = await pysisApi.pushFieldToPySis(field.id)
    if (response.data.success) {
      showMessage(t('pysis.fieldsSynced', { count: 1 }))
      await loadFields()
    } else {
      showMessage(response.data.errors?.join(', ') || t('pysis.error'), 'error')
    }
  } catch (error: any) {
    showMessage(error.response?.data?.error || t('pysis.error'), 'error')
  }
}

const generateAllFields = async () => {
  if (!selectedProcess.value) return

  generating.value = true
  try {
    const response = await pysisApi.generateFields(selectedProcess.value.id)
    if (response.data.success) {
      showMessage(t('pysis.fieldsGenerated', { count: response.data.fields_generated }))
      // Poll for updates after a delay
      setTimeout(loadFields, 5000)
    } else {
      showMessage(response.data.errors?.join(', ') || t('pysis.error'), 'error')
    }
  } catch (error: any) {
    showMessage(error.response?.data?.error || t('pysis.error'), 'error')
  } finally {
    generating.value = false
  }
}

const generateField = async (field: any) => {
  try {
    const response = await pysisApi.generateField(field.id)
    if (response.data.success) {
      // Mark field as generating
      generatingFieldIds.value.add(field.id)
      showMessage(t('pysis.aiGenerationStarted'), 'info')

      // Poll for completion
      pollForFieldCompletion(field.id, field.internal_name)
    } else {
      showMessage(response.data.errors?.join(', ') || t('pysis.error'), 'error')
    }
  } catch (error: any) {
    showMessage(error.response?.data?.error || t('pysis.error'), 'error')
  }
}

// Track active polling intervals for cleanup
const pollingIntervals = new Map<string, number>()

const pollForFieldCompletion = (fieldId: string, fieldName: string) => {
  // Clear any existing interval for this field
  if (pollingIntervals.has(fieldId)) {
    clearInterval(pollingIntervals.get(fieldId))
  }

  const checkField = async () => {
    // Stop if field is no longer in generating state
    if (!generatingFieldIds.value.has(fieldId)) {
      clearInterval(pollingIntervals.get(fieldId))
      pollingIntervals.delete(fieldId)
      return
    }

    // Stop if no process selected
    if (!selectedProcess.value) {
      stopGenerating(fieldId)
      return
    }

    try {
      const response = await pysisApi.getFields(selectedProcess.value.id)
      const updatedFields = response.data || []
      const updatedField = updatedFields.find((f: any) => f.id === fieldId)

      if (updatedField?.ai_extracted_value) {
        // AI suggestion is ready!
        stopGenerating(fieldId)
        fields.value = updatedFields
        showMessage(t('pysis.aiReady', { name: fieldName }), 'success')
      }
    } catch (error) {
      console.error('Polling error', error)
      // Don't stop on error - keep trying
    }
  }

  // Start polling every 2 seconds
  const intervalId = setInterval(checkField, 2000) as unknown as number
  pollingIntervals.set(fieldId, intervalId)

  // Also check immediately after a short delay
  setTimeout(checkField, 1500)
}

const stopGenerating = (fieldId: string) => {
  generatingFieldIds.value.delete(fieldId)
  if (pollingIntervals.has(fieldId)) {
    clearInterval(pollingIntervals.get(fieldId))
    pollingIntervals.delete(fieldId)
  }
}

const stopAllGenerating = () => {
  pollingIntervals.forEach((intervalId) => clearInterval(intervalId))
  pollingIntervals.clear()
  generatingFieldIds.value.clear()
}

const acceptAiSuggestion = async (field: any) => {
  try {
    const response = await pysisApi.acceptAiSuggestion(field.id)
    if (response.data.success) {
      showMessage(t('pysis.aiSuggestionAccepted'))
      // Update field in list
      field.current_value = response.data.accepted_value
      field.value_source = 'AI'
      field.ai_extracted_value = null
      field.needs_push = true
    } else {
      showMessage(response.data.message || t('pysis.error'), 'error')
    }
  } catch (error: any) {
    showMessage(error.response?.data?.error || t('pysis.error'), 'error')
  }
}

const rejectAiSuggestion = async (field: any) => {
  try {
    const response = await pysisApi.rejectAiSuggestion(field.id)
    if (response.data.success) {
      showMessage(t('pysis.aiSuggestionRejected'))
      // Update field in list
      field.ai_extracted_value = null
      field.confidence_score = null
    } else {
      showMessage(response.data.message || t('pysis.error'), 'error')
    }
  } catch (error: any) {
    showMessage(error.response?.data?.error || t('pysis.error'), 'error')
  }
}

// History functions
const showHistory = async (field: any) => {
  historyField.value = field
  historyEntries.value = []
  showHistoryDialog.value = true
  loadingHistory.value = true

  try {
    const response = await pysisApi.getFieldHistory(field.id, 20)
    historyEntries.value = response.data.items || []
  } catch (error) {
    console.error('Failed to load history', error)
    showMessage(t('pysis.error'), 'error')
  } finally {
    loadingHistory.value = false
  }
}

const restoreFromHistory = async (entry: any) => {
  if (!historyField.value) return

  try {
    const response = await pysisApi.restoreFromHistory(historyField.value.id, entry.id)
    if (response.data.success) {
      showMessage(t('pysis.valueRestored'))
      // Update field in list
      const field = fields.value.find((f) => f.id === historyField.value.id)
      if (field) {
        field.current_value = response.data.accepted_value
        field.value_source = 'MANUAL'
        field.needs_push = true
      }
      showHistoryDialog.value = false
    } else {
      showMessage(response.data.message || t('pysis.error'), 'error')
    }
  } catch (error: any) {
    showMessage(error.response?.data?.error || t('pysis.error'), 'error')
  }
}

const getHistoryActionIcon = (action: string) => {
  const icons: Record<string, string> = {
    accepted: 'mdi-check-circle',
    rejected: 'mdi-close-circle',
    replaced: 'mdi-swap-horizontal',
    restored: 'mdi-restore',
    manual_edit: 'mdi-pencil',
    generated: 'mdi-auto-fix',
    pulled: 'mdi-download',
    pushed: 'mdi-upload',
  }
  return icons[action] || 'mdi-circle'
}

const getHistoryActionColor = (action: string) => {
  const colors: Record<string, string> = {
    accepted: 'success',
    rejected: 'error',
    replaced: 'grey',
    restored: 'info',
    manual_edit: 'primary',
    generated: 'info',
    pulled: 'purple',
    pushed: 'success',
  }
  return colors[action] || 'grey'
}

const formatHistoryAction = (action: string) => {
  const key = `pysis.historyActions.${action}`
  const translated = t(key)
  return translated !== key ? translated : action
}

const getHistoryItemClass = (action: string) => {
  if (action === 'rejected') return 'bg-red-lighten-5'
  if (action === 'accepted') return 'bg-green-lighten-5'
  return ''
}

// PySis-Facets Functions
const analyzeForFacets = async () => {
  if (!selectedProcess.value?.entity_id) {
    showMessage(t('pysis.facets.needsEntity'), 'error')
    return
  }

  analyzingForFacets.value = true
  try {
    const response = await pysisApi.analyzeForFacets({
      entity_id: selectedProcess.value.entity_id,
      process_id: selectedProcess.value.id,
      include_empty: analyzeIncludeEmpty.value,
      min_confidence: analyzeMinConfidence.value,
    })

    if (response.data.success) {
      startedTaskId.value = response.data.task_id
      taskStartedMessage.value = t('pysis.facets.analyzeTaskStartedMessage')
      showAnalyzeForFacetsDialog.value = false
      showTaskStartedDialog.value = true
    } else {
      showMessage(response.data.message || t('pysis.error'), 'error')
    }
  } catch (error: any) {
    showMessage(error.response?.data?.error || t('pysis.error'), 'error')
  } finally {
    analyzingForFacets.value = false
  }
}

const enrichFacetsFromPysis = async () => {
  if (!selectedProcess.value?.entity_id) {
    showMessage(t('pysis.facets.needsEntity'), 'error')
    return
  }

  enrichingFacets.value = true
  try {
    const response = await pysisApi.enrichFacetsFromPysis({
      entity_id: selectedProcess.value.entity_id,
      overwrite: enrichOverwrite.value,
    })

    if (response.data.success) {
      startedTaskId.value = response.data.task_id
      taskStartedMessage.value = t('pysis.facets.enrichTaskStartedMessage')
      showEnrichFacetsDialog.value = false
      showTaskStartedDialog.value = true
    } else {
      showMessage(response.data.message || t('pysis.error'), 'error')
    }
  } catch (error: any) {
    showMessage(error.response?.data?.error || t('pysis.error'), 'error')
  } finally {
    enrichingFacets.value = false
  }
}

// Watch for municipality changes
watch(() => props.municipality, () => {
  selectedProcess.value = null
  fields.value = []
  loadProcesses()
})

// Reset manual input when dialog opens
watch(showAddProcessDialog, (isOpen) => {
  if (isOpen) {
    showManualInput.value = false
    // Pre-load available processes when dialog opens
    if (availableProcesses.value.length === 0) {
      loadAvailableProcesses()
    }
  }
})

onMounted(() => {
  loadProcesses()
  if (flags.value.pysisFieldTemplates) {
    loadTemplates()
  }
})

onUnmounted(() => {
  // Cleanup: Stop all polling intervals when component is destroyed
  stopAllGenerating()
})
</script>

<style scoped>
.field-value-input {
  font-size: 0.85rem;
}

.field-value-preview {
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  background-color: rgba(var(--v-theme-on-surface), 0.03);
  font-size: 0.85rem;
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-word;
  min-height: 32px;
  transition: background-color 0.2s;
}

.field-value-preview:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.08);
}

.field-value-preview:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: -2px;
}

.ai-suggestion {
  padding: 8px;
  border-radius: 4px;
  background-color: rgba(var(--v-theme-info), 0.08);
  border-left: 3px solid rgb(var(--v-theme-info));
}

.ai-suggestion-text {
  padding: 4px;
  background-color: rgba(var(--v-theme-surface), 0.8);
  border-radius: 2px;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 80px;
  overflow-y: auto;
}

.table-actions {
  display: flex;
  gap: 2px;
}

.history-value {
  padding: 4px 8px;
  background-color: rgba(var(--v-theme-on-surface), 0.03);
  border-radius: 4px;
  font-size: 0.8rem;
  white-space: pre-wrap;
  word-break: break-word;
}

.generating-indicator {
  display: flex;
  align-items: center;
  padding: 4px 8px;
  background-color: rgba(var(--v-theme-info), 0.1);
  border-radius: 4px;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
</style>
