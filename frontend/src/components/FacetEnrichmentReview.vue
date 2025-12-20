<template>
  <v-dialog
    v-model="dialogModel"
    max-width="900"
    scrollable
    :persistent="isRunning"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon
          start
          :color="statusColor"
        >
          {{ statusIcon }}
        </v-icon>
        {{ dialogTitle }}
        <v-spacer></v-spacer>
        <v-btn
          v-if="!isRunning"
          icon
          variant="text"
          @click="handleClose"
        >
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text>
        <!-- Running State -->
        <template v-if="isRunning">
          <v-progress-linear
            :model-value="progressPercent"
            :indeterminate="!taskStatus?.progress_total"
            color="primary"
            class="mb-4"
            rounded
            height="8"
          ></v-progress-linear>

          <div class="text-center py-4">
            <v-icon size="64" color="primary" class="mb-4">mdi-cog-sync</v-icon>
            <p class="text-h6 mb-2">{{ t('facetEnrichment.analyzing') }}</p>
            <p v-if="taskStatus?.current_item" class="text-body-2 text-medium-emphasis">
              {{ taskStatus.current_item }}
            </p>
            <p v-if="taskStatus?.progress_total" class="text-caption text-medium-emphasis mt-2">
              {{ taskStatus.progress_current || 0 }} / {{ taskStatus.progress_total }}
            </p>
          </div>
        </template>

        <!-- Failed State -->
        <template v-else-if="taskStatus?.status === 'FAILED'">
          <v-alert type="error" variant="tonal" class="mb-4">
            <v-alert-title>{{ t('facetEnrichment.failed') }}</v-alert-title>
            {{ taskStatus.error_message || t('facetEnrichment.unknownError') }}
          </v-alert>
        </template>

        <!-- Completed State - Show Preview -->
        <template v-else-if="previewData">
          <!-- Summary -->
          <v-alert
            v-if="previewData.analysis_summary"
            type="info"
            variant="tonal"
            density="compact"
            class="mb-4"
          >
            {{ t('facetEnrichment.analysisSummary', {
              sources: previewData.analysis_summary.sources_analyzed?.length || 0,
              new: previewData.new_facets?.length || 0,
              updates: previewData.updates?.length || 0
            }) }}
          </v-alert>

          <!-- No results -->
          <template v-if="!hasResults">
            <div class="text-center py-8">
              <v-icon size="64" color="grey" class="mb-4">mdi-magnify-close</v-icon>
              <p class="text-h6 text-medium-emphasis">{{ t('facetEnrichment.noResults') }}</p>
              <p class="text-body-2 text-medium-emphasis">{{ t('facetEnrichment.noResultsHint') }}</p>
            </div>
          </template>

          <!-- Tabs for new facets and updates -->
          <template v-else>
            <v-tabs v-model="reviewTab" class="mb-4">
              <v-tab value="new" :disabled="!previewData.new_facets?.length">
                <v-icon start>mdi-plus-circle</v-icon>
                {{ t('facetEnrichment.newFacets') }}
                <v-chip size="x-small" class="ml-2">{{ previewData.new_facets?.length || 0 }}</v-chip>
              </v-tab>
              <v-tab value="updates" :disabled="!previewData.updates?.length">
                <v-icon start>mdi-pencil</v-icon>
                {{ t('facetEnrichment.updates') }}
                <v-chip size="x-small" class="ml-2">{{ previewData.updates?.length || 0 }}</v-chip>
              </v-tab>
            </v-tabs>

            <v-tabs-window v-model="reviewTab">
              <!-- New Facets Tab -->
              <v-tabs-window-item value="new">
                <div class="d-flex align-center mb-3">
                  <v-btn size="small" variant="text" @click="selectAllNew">
                    {{ t('facetEnrichment.selectAll') }}
                  </v-btn>
                  <v-btn size="small" variant="text" @click="selectNoneNew">
                    {{ t('facetEnrichment.selectNone') }}
                  </v-btn>
                  <v-spacer></v-spacer>
                  <span class="text-caption text-medium-emphasis">
                    {{ acceptedNewFacets.length }} / {{ previewData.new_facets?.length || 0 }} {{ t('facetEnrichment.selected') }}
                  </span>
                </div>

                <v-list lines="two" class="border rounded">
                  <v-list-item
                    v-for="(facet, idx) in previewData.new_facets"
                    :key="idx"
                    class="py-2"
                  >
                    <template #prepend>
                      <v-checkbox
                        v-model="acceptedNewFacets"
                        :value="idx"
                        hide-details
                        density="compact"
                      ></v-checkbox>
                    </template>

                    <v-list-item-title class="d-flex align-center">
                      <v-chip size="x-small" :color="getFacetTypeColor(facet.facet_type)" class="mr-2">
                        {{ facet.facet_type_name || facet.facet_type }}
                      </v-chip>
                      <span class="text-truncate">{{ facet.text }}</span>
                    </v-list-item-title>

                    <v-list-item-subtitle>
                      <div v-if="facet.value" class="text-caption font-italic">
                        {{ formatValue(facet.value) }}
                      </div>
                    </v-list-item-subtitle>

                    <template #append>
                      <v-chip size="x-small" :color="getConfidenceColor(facet.confidence)">
                        {{ Math.round((facet.confidence || 0) * 100) }}%
                      </v-chip>
                    </template>
                  </v-list-item>
                </v-list>
              </v-tabs-window-item>

              <!-- Updates Tab -->
              <v-tabs-window-item value="updates">
                <div class="d-flex align-center mb-3">
                  <v-btn size="small" variant="text" @click="selectAllUpdates">
                    {{ t('facetEnrichment.selectAll') }}
                  </v-btn>
                  <v-btn size="small" variant="text" @click="selectNoneUpdates">
                    {{ t('facetEnrichment.selectNone') }}
                  </v-btn>
                  <v-spacer></v-spacer>
                  <span class="text-caption text-medium-emphasis">
                    {{ acceptedUpdates.length }} / {{ previewData.updates?.length || 0 }} {{ t('facetEnrichment.selected') }}
                  </span>
                </div>

                <v-list lines="three" class="border rounded">
                  <v-list-item
                    v-for="update in previewData.updates"
                    :key="update.facet_value_id"
                    class="py-3"
                  >
                    <template #prepend>
                      <v-checkbox
                        v-model="acceptedUpdates"
                        :value="update.facet_value_id"
                        hide-details
                        density="compact"
                      ></v-checkbox>
                    </template>

                    <v-list-item-title class="d-flex align-center mb-2">
                      <v-chip size="x-small" :color="getFacetTypeColor(update.facet_type)" class="mr-2">
                        {{ update.facet_type_name || update.facet_type }}
                      </v-chip>
                      <span class="text-truncate">{{ update.text }}</span>
                    </v-list-item-title>

                    <v-list-item-subtitle>
                      <!-- Diff view -->
                      <div class="d-flex gap-4 mt-2">
                        <div class="flex-1 pa-2 bg-red-lighten-5 rounded">
                          <div class="text-caption text-medium-emphasis mb-1">{{ t('facetEnrichment.current') }}:</div>
                          <pre class="text-body-2 text-wrap">{{ formatValue(update.current_value) }}</pre>
                        </div>
                        <v-icon class="align-self-center">mdi-arrow-right</v-icon>
                        <div class="flex-1 pa-2 bg-green-lighten-5 rounded">
                          <div class="text-caption text-medium-emphasis mb-1">{{ t('facetEnrichment.proposed') }}:</div>
                          <pre class="text-body-2 text-wrap">{{ formatValue(update.proposed_value) }}</pre>
                        </div>
                      </div>
                      <div v-if="update.changes?.length" class="mt-2">
                        <v-chip
                          v-for="change in update.changes"
                          :key="change"
                          size="x-small"
                          color="warning"
                          variant="outlined"
                          class="mr-1"
                        >
                          {{ change }}
                        </v-chip>
                      </div>
                    </v-list-item-subtitle>

                    <template #append>
                      <v-chip size="x-small" :color="getConfidenceColor(update.confidence)">
                        {{ Math.round((update.confidence || 0) * 100) }}%
                      </v-chip>
                    </template>
                  </v-list-item>
                </v-list>
              </v-tabs-window-item>
            </v-tabs-window>
          </template>
        </template>

        <!-- Task ID for reference -->
        <p v-if="taskId" class="text-caption text-medium-emphasis mt-4">
          Task-ID: <code>{{ taskId }}</code>
        </p>
      </v-card-text>

      <v-card-actions>
        <template v-if="isRunning">
          <v-btn
            variant="tonal"
            @click="handleMinimize"
          >
            <v-icon start>mdi-window-minimize</v-icon>
            {{ t('facetEnrichment.minimize') }}
          </v-btn>
        </template>
        <template v-else-if="hasResults && previewData">
          <v-btn variant="text" @click="handleClose">
            {{ t('common.cancel') }}
          </v-btn>
          <v-spacer></v-spacer>
          <v-btn
            variant="tonal"
            color="primary"
            :loading="applying"
            :disabled="totalSelected === 0"
            @click="applyChanges"
          >
            <v-icon start>mdi-check</v-icon>
            {{ t('facetEnrichment.applyChanges', { count: totalSelected }) }}
          </v-btn>
        </template>
        <template v-else>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" color="primary" @click="handleClose">
            {{ t('common.close') }}
          </v-btn>
        </template>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { entityDataApi } from '@/services/api'

const { t } = useI18n()

interface Props {
  modelValue: boolean
  taskId: string | null
  taskStatus: {
    status: string
    progress_current?: number
    progress_total?: number
    current_item?: string
    error_message?: string
  } | null
  previewData: {
    new_facets?: Array<{
      facet_type: string
      facet_type_name?: string
      value: any
      text: string
      confidence?: number
    }>
    updates?: Array<{
      facet_value_id: string
      facet_type: string
      facet_type_name?: string
      current_value: any
      proposed_value: any
      changes?: string[]
      text: string
      confidence?: number
    }>
    analysis_summary?: {
      sources_analyzed: string[]
      new_suggestions: number
      update_suggestions: number
    }
  } | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'close': []
  'minimize': []
  'applied': [result: { created: number; updated: number }]
}>()

const dialogModel = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const reviewTab = ref<'new' | 'updates'>('new')
const acceptedNewFacets = ref<number[]>([])
const acceptedUpdates = ref<string[]>([])
const applying = ref(false)

// Watch for preview data changes to auto-select all
watch(() => props.previewData, (newData) => {
  if (newData) {
    // Auto-select all high-confidence items
    acceptedNewFacets.value = (newData.new_facets || [])
      .map((_, idx) => idx)
      .filter((idx) => (newData.new_facets![idx].confidence || 0) >= 0.7)

    acceptedUpdates.value = (newData.updates || [])
      .filter((u) => (u.confidence || 0) >= 0.7)
      .map((u) => u.facet_value_id)

    // Switch to tab with content
    if (newData.new_facets?.length) {
      reviewTab.value = 'new'
    } else if (newData.updates?.length) {
      reviewTab.value = 'updates'
    }
  }
}, { immediate: true })

const isRunning = computed(() =>
  props.taskStatus?.status === 'RUNNING' || props.taskStatus?.status === 'PENDING'
)

const hasResults = computed(() =>
  (props.previewData?.new_facets?.length || 0) > 0 ||
  (props.previewData?.updates?.length || 0) > 0
)

const totalSelected = computed(() =>
  acceptedNewFacets.value.length + acceptedUpdates.value.length
)

const progressPercent = computed(() => {
  if (!props.taskStatus?.progress_total) return 0
  return Math.round((props.taskStatus.progress_current || 0) / props.taskStatus.progress_total * 100)
})

const statusColor = computed(() => {
  if (isRunning.value) return 'primary'
  if (props.taskStatus?.status === 'FAILED') return 'error'
  if (props.taskStatus?.status === 'COMPLETED') return 'success'
  return 'grey'
})

const statusIcon = computed(() => {
  if (isRunning.value) return 'mdi-cog-sync'
  if (props.taskStatus?.status === 'FAILED') return 'mdi-alert-circle'
  if (props.taskStatus?.status === 'COMPLETED') return 'mdi-check-circle'
  return 'mdi-help-circle'
})

const dialogTitle = computed(() => {
  if (isRunning.value) return t('facetEnrichment.analyzing')
  if (props.taskStatus?.status === 'FAILED') return t('facetEnrichment.failed')
  if (props.taskStatus?.status === 'COMPLETED') return t('facetEnrichment.reviewChanges')
  return t('facetEnrichment.title')
})

function selectAllNew() {
  acceptedNewFacets.value = (props.previewData?.new_facets || []).map((_, idx) => idx)
}

function selectNoneNew() {
  acceptedNewFacets.value = []
}

function selectAllUpdates() {
  acceptedUpdates.value = (props.previewData?.updates || []).map((u) => u.facet_value_id)
}

function selectNoneUpdates() {
  acceptedUpdates.value = []
}

function handleClose() {
  emit('close')
  emit('update:modelValue', false)
}

function handleMinimize() {
  emit('minimize')
  emit('update:modelValue', false)
}

async function applyChanges() {
  if (!props.taskId) return

  applying.value = true
  try {
    const response = await entityDataApi.applyChanges({
      task_id: props.taskId,
      accepted_new_facets: acceptedNewFacets.value,
      accepted_updates: acceptedUpdates.value,
    })

    emit('applied', {
      created: response.data.created || 0,
      updated: response.data.updated || 0,
    })
    handleClose()
  } catch (error) {
    console.error('Failed to apply changes:', error)
  } finally {
    applying.value = false
  }
}

function getFacetTypeColor(slug: string): string {
  const colors: Record<string, string> = {
    pain_point: 'red',
    positive_signal: 'green',
    contact: 'blue',
    summary: 'purple',
    news: 'orange',
    event: 'teal',
  }
  return colors[slug] || 'grey'
}

function getConfidenceColor(confidence?: number): string {
  if (!confidence) return 'grey'
  if (confidence >= 0.8) return 'success'
  if (confidence >= 0.6) return 'warning'
  return 'error'
}

function formatValue(value: any): string {
  if (!value) return '-'
  if (typeof value === 'string') return value

  // Format object for display
  const display: string[] = []
  for (const [key, val] of Object.entries(value)) {
    if (key.startsWith('pysis_') || key === 'source_fields' || key === 'confidence') continue
    if (val) {
      display.push(`${key}: ${typeof val === 'object' ? JSON.stringify(val) : val}`)
    }
  }
  return display.join('\n') || JSON.stringify(value, null, 2)
}
</script>

<style scoped>
pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  margin: 0;
}

.flex-1 {
  flex: 1;
}
</style>
