<template>
  <div>
    <div class="d-flex justify-space-between align-center mb-6">
      <div>
        <h1 class="text-h4">{{ t('smartQueryView.title') }}</h1>
        <p class="text-subtitle-1 text-medium-emphasis mt-1">
          {{ t('smartQueryView.subtitle') }}
        </p>
      </div>
    </div>

    <!-- Query Input -->
    <v-card class="mb-6">
      <v-card-text>
        <div class="d-flex align-start">
          <v-textarea
            v-model="question"
            :label="writeMode ? t('smartQueryView.input.labelWrite') : t('smartQueryView.input.labelRead')"
            :placeholder="isListening
              ? t('smartQueryView.input.placeholderListening')
              : (writeMode
                ? t('smartQueryView.input.placeholderWrite')
                : t('smartQueryView.input.placeholderRead'))"
            rows="3"
            variant="outlined"
            hide-details
            class="mb-4 flex-grow-1"
            :disabled="previewData !== null"
          >
            <template v-slot:append-inner v-if="interimTranscript">
              <span class="text-caption text-medium-emphasis font-italic">{{ interimTranscript }}</span>
            </template>
          </v-textarea>
          <v-btn
            v-if="hasMicrophone"
            :icon="isListening ? 'mdi-microphone-off' : 'mdi-microphone'"
            :color="isListening ? 'error' : 'default'"
            :class="{ 'voice-btn-listening': isListening }"
            variant="text"
            size="large"
            class="ml-2 mt-1"
            :disabled="previewData !== null || loading"
            @click="handleVoiceInput"
          >
            <v-tooltip activator="parent" location="top">
              {{ isListening ? t('smartQueryView.voice.stopRecording') : t('smartQueryView.voice.startRecording') }}
            </v-tooltip>
          </v-btn>
        </div>
        <div class="d-flex justify-space-between align-center">
          <div class="d-flex align-center">
            <v-switch
              v-model="writeMode"
              color="warning"
              hide-details
              density="compact"
              class="mr-3"
              :disabled="previewData !== null"
            >
              <template v-slot:label>
                <v-icon :color="writeMode ? 'warning' : 'grey'" class="mr-1">
                  {{ writeMode ? 'mdi-pencil-plus' : 'mdi-magnify' }}
                </v-icon>
                {{ writeMode ? t('smartQueryView.mode.write') : t('smartQueryView.mode.read') }}
              </template>
            </v-switch>
            <v-chip v-if="writeMode && !previewData" color="info" size="small" variant="tonal">
              <v-icon start size="small">mdi-eye</v-icon>
              {{ t('smartQueryView.mode.previewFirst') }}
            </v-chip>
          </div>
          <v-btn
            v-if="!previewData"
            :color="writeMode ? 'warning' : 'primary'"
            size="large"
            :loading="loading"
            :disabled="!question.trim()"
            @click="executeQuery"
          >
            <v-icon left>{{ writeMode ? 'mdi-eye' : 'mdi-magnify' }}</v-icon>
            {{ writeMode ? t('smartQueryView.actions.preview') : t('smartQueryView.actions.query') }}
          </v-btn>
        </div>
      </v-card-text>
    </v-card>

    <!-- Example Queries -->
    <v-card class="mb-6" v-if="!results && !previewData">
      <v-card-title class="text-h6">
        <v-icon left>mdi-lightbulb-outline</v-icon>
        {{ writeMode ? t('smartQueryView.examples.commandsTitle') : t('smartQueryView.examples.questionsTitle') }}
      </v-card-title>
      <v-card-text>
        <v-chip-group>
          <v-chip
            v-for="example in currentExamples"
            :key="example.question"
            @click="useExample(example.question)"
            variant="outlined"
            :color="writeMode ? 'warning' : 'primary'"
            class="ma-1"
          >
            {{ example.question }}
          </v-chip>
        </v-chip-group>
      </v-card-text>
    </v-card>

    <!-- Error -->
    <v-alert v-if="error" type="error" class="mb-6" closable @click:close="error = null">
      {{ error }}
    </v-alert>

    <!-- AI Generation Progress -->
    <v-card v-if="loading && writeMode" class="mb-6" color="info" variant="tonal">
      <v-card-title class="d-flex align-center">
        <v-progress-circular indeterminate size="24" width="2" class="mr-3" />
        {{ t('smartQueryView.generation.running') }}
      </v-card-title>
      <v-card-text>
        <v-stepper :model-value="currentStep" alt-labels>
          <v-stepper-header>
            <v-stepper-item
              :value="1"
              :complete="currentStep > 1"
              :color="currentStep >= 1 ? 'success' : 'grey'"
              :title="t('smartQueryView.generation.stepperTitles.entityType')"
              :subtitle="t('smartQueryView.generation.stepperSubtitles.entityType')"
            />
            <v-divider />
            <v-stepper-item
              :value="2"
              :complete="currentStep > 2"
              :color="currentStep >= 2 ? 'success' : 'grey'"
              :title="t('smartQueryView.generation.stepperTitles.category')"
              :subtitle="t('smartQueryView.generation.stepperSubtitles.category')"
            />
            <v-divider />
            <v-stepper-item
              :value="3"
              :complete="currentStep > 3"
              :color="currentStep >= 3 ? 'success' : 'grey'"
              :title="t('smartQueryView.generation.stepperTitles.crawlConfig')"
              :subtitle="t('smartQueryView.generation.stepperSubtitles.crawlConfig')"
            />
          </v-stepper-header>
        </v-stepper>
        <div class="text-center mt-4 text-body-2">
          {{ stepMessages[currentStep] || t('smartQueryView.generation.processing') }}
        </div>
      </v-card-text>
    </v-card>

    <!-- Preview Mode (Write) -->
    <template v-if="previewData">
      <v-card class="mb-4" color="warning" variant="tonal">
        <v-card-title>
          <v-icon left>mdi-eye-check</v-icon>
          {{ t('smartQueryView.preview.title') }}
        </v-card-title>
        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-4">
            <strong>{{ previewData.preview?.operation_de }}</strong>
            <div class="mt-1">{{ previewData.preview?.description }}</div>
          </v-alert>

          <v-card variant="outlined" class="mb-4">
            <v-card-title class="text-subtitle-1">
              <v-icon left size="small">mdi-format-list-bulleted</v-icon>
              {{ t('common.details') }}
            </v-card-title>
            <v-card-text>
              <v-list density="compact" class="bg-transparent">
                <v-list-item
                  v-for="(detail, idx) in previewData.preview?.details || []"
                  :key="idx"
                  :title="detail"
                >
                  <template v-slot:prepend>
                    <v-icon size="small" color="primary">mdi-check</v-icon>
                  </template>
                </v-list-item>
              </v-list>
            </v-card-text>
          </v-card>

          <!-- Technical Details -->
          <v-expansion-panels variant="accordion">
            <v-expansion-panel :title="t('smartQueryView.preview.technicalDetails')">
              <v-expansion-panel-text>
                <pre class="text-caption">{{ JSON.stringify(previewData.interpretation, null, 2) }}</pre>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="cancelPreview">
            <v-icon start>mdi-close</v-icon>
            {{ t('common.cancel') }}
          </v-btn>
          <v-btn color="success" variant="elevated" :loading="loading" @click="confirmWrite">
            <v-icon start>mdi-check</v-icon>
            {{ t('smartQueryView.preview.confirmAndCreate') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </template>

    <!-- Write Results -->
    <template v-if="results?.mode === 'write'">
      <v-card class="mb-4" :color="results.success ? 'success' : 'error'" variant="tonal">
        <v-card-title>
          <v-icon left>{{ results.success ? 'mdi-check-circle' : 'mdi-alert-circle' }}</v-icon>
          {{ results.success ? t('smartQueryView.results.successfullyCreated') : t('common.error') }}
        </v-card-title>
        <v-card-text>
          <div class="text-body-1 mb-3">{{ results.message }}</div>

          <!-- Created Items -->
          <template v-if="results.created_items?.length > 0">
            <div class="text-subtitle-2 mb-2">{{ t('smartQueryView.results.createdItems') }}</div>
            <v-list density="compact" class="bg-transparent">
              <v-list-item
                v-for="item in results.created_items"
                :key="item.id"
                :title="item.name || item.type"
                :subtitle="`${item.type}${item.entity_type ? ' (' + item.entity_type + ')' : ''}${item.slug ? ' [' + item.slug + ']' : ''} - ID: ${item.id.substring(0, 8)}...`"
              >
                <template v-slot:prepend>
                  <v-icon :color="getItemTypeColor(item.type)">
                    {{ getItemTypeIcon(item.type) }}
                  </v-icon>
                </template>
              </v-list-item>
            </v-list>
          </template>

          <!-- Crawl Information -->
          <template v-if="results.sources_count || results.crawl_jobs?.length > 0">
            <v-divider class="my-3" />
            <div class="text-subtitle-2 mb-2">
              <v-icon left size="small">mdi-spider-web</v-icon>
              {{ t('smartQueryView.results.crawlDetails') }}
            </div>
            <v-chip v-if="results.sources_count" class="mr-2 mb-2" color="info" size="small">
              {{ t('smartQueryView.results.dataSources', { count: results.sources_count }) }}
            </v-chip>
            <v-chip v-if="results.crawl_jobs?.length" class="mr-2 mb-2" color="success" size="small">
              {{ t('smartQueryView.results.jobsStarted', { count: results.crawl_jobs.length }) }}
            </v-chip>
          </template>

          <!-- Linked Sources -->
          <template v-if="results.linked_sources_count">
            <v-divider class="my-3" />
            <div class="text-subtitle-2 mb-2">
              <v-icon left size="small">mdi-link-variant</v-icon>
              {{ t('smartQueryView.results.dataSourcesLink') }}
            </div>
            <v-chip color="primary" size="small">
              {{ t('smartQueryView.results.dataSourcesLinked', { count: results.linked_sources_count }) }}
            </v-chip>
          </template>

          <!-- AI Generation Steps -->
          <template v-if="results.steps?.length > 0">
            <v-divider class="my-3" />
            <div class="text-subtitle-2 mb-2">
              <v-icon left size="small">mdi-robot</v-icon>
              {{ t('smartQueryView.results.aiGenerationSteps') }}
            </div>
            <v-timeline density="compact" side="end">
              <v-timeline-item
                v-for="(step, idx) in results.steps"
                :key="idx"
                :dot-color="step.success !== false ? 'success' : 'error'"
                size="x-small"
              >
                <div>
                  <div class="d-flex align-center">
                    <v-icon :color="step.success !== false ? 'success' : 'error'" size="small" class="mr-2">
                      {{ step.success !== false ? 'mdi-check' : 'mdi-close' }}
                    </v-icon>
                    <span class="text-body-2 font-weight-medium">{{ t('smartQueryView.results.step', { current: step.step, total: step.total }) }}</span>
                  </div>
                  <div class="text-caption text-medium-emphasis ml-6">{{ step.message }}</div>
                  <div v-if="step.result" class="text-caption text-success ml-6">{{ step.result }}</div>
                </div>
              </v-timeline-item>
            </v-timeline>
          </template>

          <!-- AI-Generated Search Terms -->
          <template v-if="results.search_terms?.length > 0">
            <v-divider class="my-3" />
            <div class="text-subtitle-2 mb-2">
              <v-icon left size="small">mdi-magnify</v-icon>
              {{ t('smartQueryView.results.aiSearchTerms') }}
            </div>
            <v-chip
              v-for="term in results.search_terms"
              :key="term"
              size="small"
              class="mr-1 mb-1"
              color="info"
              variant="outlined"
            >
              {{ term }}
            </v-chip>
          </template>

          <!-- AI-Generated URL Patterns -->
          <template v-if="results.url_patterns?.include?.length > 0 || results.url_patterns?.exclude?.length > 0">
            <v-divider class="my-3" />
            <div class="text-subtitle-2 mb-2">
              <v-icon left size="small">mdi-web</v-icon>
              {{ t('smartQueryView.results.urlPatternConfig') }}
            </div>
            <div v-if="results.url_patterns?.reasoning" class="text-caption text-medium-emphasis mb-3">
              {{ results.url_patterns.reasoning }}
            </div>
            <div v-if="results.url_patterns?.include?.length > 0" class="mb-2">
              <div class="text-caption text-success mb-1">{{ t('smartQueryView.results.includePatterns') }}</div>
              <v-chip
                v-for="pattern in results.url_patterns.include"
                :key="pattern"
                size="small"
                class="mr-1 mb-1"
                color="success"
                variant="tonal"
              >
                <code>{{ pattern }}</code>
              </v-chip>
            </div>
            <div v-if="results.url_patterns?.exclude?.length > 0">
              <div class="text-caption text-error mb-1">{{ t('smartQueryView.results.excludePatterns') }}</div>
              <v-chip
                v-for="pattern in results.url_patterns.exclude"
                :key="pattern"
                size="small"
                class="mr-1 mb-1"
                color="error"
                variant="tonal"
              >
                <code>{{ pattern }}</code>
              </v-chip>
            </div>
          </template>

          <!-- AI Extraction Prompt -->
          <template v-if="results.ai_extraction_prompt">
            <v-divider class="my-3" />
            <v-expansion-panels variant="accordion">
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon left size="small" class="mr-2">mdi-brain</v-icon>
                  {{ t('smartQueryView.results.aiExtractionPrompt') }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <pre class="text-caption" style="white-space: pre-wrap;">{{ results.ai_extraction_prompt }}</pre>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </template>

          <!-- Combined Operation Results -->
          <template v-if="results.operation_results?.length > 0">
            <v-divider class="my-3" />
            <div class="text-subtitle-2 mb-2">
              <v-icon left size="small">mdi-format-list-checks</v-icon>
              {{ t('smartQueryView.results.executedOperations') }}
            </div>
            <v-list density="compact" class="bg-transparent">
              <v-list-item
                v-for="(opResult, idx) in results.operation_results"
                :key="idx"
                :title="opResult.operation"
                :subtitle="opResult.message"
              >
                <template v-slot:prepend>
                  <v-icon :color="opResult.success ? 'success' : 'error'" size="small">
                    {{ opResult.success ? 'mdi-check' : 'mdi-close' }}
                  </v-icon>
                </template>
              </v-list-item>
            </v-list>
          </template>

          <!-- Interpretation -->
          <v-expansion-panels variant="accordion" class="mt-3">
            <v-expansion-panel :title="t('smartQueryView.results.interpretation')">
              <v-expansion-panel-text>
                <pre class="text-caption">{{ JSON.stringify(results.interpretation, null, 2) }}</pre>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>
        <v-card-actions>
          <v-btn variant="text" @click="resetAll">{{ t('smartQueryView.results.newCommand') }}</v-btn>
          <v-spacer />
          <v-btn
            v-if="fromAssistant"
            color="primary"
            variant="elevated"
            @click="sendResultsToAssistant"
          >
            <v-icon start>mdi-arrow-left</v-icon>
            {{ t('smartQueryView.results.backToAssistant') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </template>

    <!-- Read Results -->
    <template v-if="results?.mode === 'read' || (!results?.mode && results && !previewData)">
      <!-- Query Interpretation -->
      <v-card class="mb-4">
        <v-card-title class="text-subtitle-1">
          <v-icon left size="small">mdi-brain</v-icon>
          {{ t('smartQueryView.read.aiInterpretation') }}
        </v-card-title>
        <v-card-text>
          <v-chip class="mr-2" size="small" color="primary">
            {{ t('smartQueryView.read.entity') }}: {{ results.query_interpretation?.primary_entity_type }}
          </v-chip>
          <v-chip
            v-for="facet in results.query_interpretation?.facet_types || []"
            :key="facet"
            class="mr-2"
            size="small"
            color="secondary"
          >
            {{ t('smartQueryView.read.facet') }}: {{ facet }}
          </v-chip>
          <v-chip class="mr-2" size="small" :color="getTimeFilterColor(results.query_interpretation?.time_filter)">
            {{ results.query_interpretation?.time_filter || 'all' }}
          </v-chip>
          <div class="text-caption mt-2" v-if="results.query_interpretation?.explanation">
            {{ results.query_interpretation.explanation }}
          </div>
        </v-card-text>
      </v-card>

      <!-- Results Count -->
      <v-card class="mb-4">
        <v-card-text class="d-flex align-center">
          <v-icon class="mr-2" color="success">mdi-check-circle</v-icon>
          <span class="text-h6">{{ t('smartQueryView.read.resultsCount', { count: results.total }) }}</span>
          <v-spacer />
          <v-chip size="small" variant="outlined">
            {{ t('smartQueryView.read.grouping') }}: {{ results.grouping || 'flat' }}
          </v-chip>
        </v-card-text>
      </v-card>

      <!-- Event-grouped Results -->
      <template v-if="results.grouping === 'by_event'">
        <v-card v-for="event in results.items" :key="event.event_name" class="mb-4">
          <v-card-title>
            <v-icon left color="orange">mdi-calendar-star</v-icon>
            {{ event.event_name }}
          </v-card-title>
          <v-card-subtitle>
            <v-icon size="small">mdi-calendar</v-icon>
            {{ event.event_date || t('smartQueryView.read.dateUnknown') }}
            <span class="mx-2">|</span>
            <v-icon size="small">mdi-map-marker</v-icon>
            {{ event.event_location || t('smartQueryView.read.locationUnknown') }}
          </v-card-subtitle>
          <v-card-text>
            <v-list density="compact">
              <v-list-subheader>{{ t('smartQueryView.read.attendees', { count: event.attendees?.length || 0 }) }}</v-list-subheader>
              <v-list-item
                v-for="attendee in event.attendees"
                :key="attendee.person_id"
                :title="attendee.person_name"
                :subtitle="formatAttendeeSubtitle(attendee)"
              >
                <template v-slot:prepend>
                  <v-avatar color="primary" size="32">
                    <span class="text-caption">{{ getInitials(attendee.person_name) }}</span>
                  </v-avatar>
                </template>
                <template v-slot:append>
                  <v-chip v-if="attendee.role" size="x-small" color="info">
                    {{ attendee.role }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </template>

      <!-- Flat Results -->
      <template v-else>
        <v-card v-for="item in results.items" :key="item.entity_id" class="mb-4">
          <v-card-title>
            <v-icon left :color="getEntityTypeColor(item.entity_type)">
              {{ getEntityTypeIcon(item.entity_type) }}
            </v-icon>
            {{ item.entity_name }}
          </v-card-title>
          <v-card-subtitle v-if="item.attributes?.position">
            {{ item.attributes.position }}
            <span v-if="item.relations?.works_for">
              @ {{ item.relations.works_for.entity_name }}
            </span>
          </v-card-subtitle>
          <v-card-text v-if="Object.keys(item.facets || {}).length > 0">
            <template v-for="(values, facetType) in item.facets" :key="facetType">
              <div v-if="values.length > 0" class="mb-3">
                <div class="text-subtitle-2 mb-1">{{ facetType }} ({{ values.length }})</div>
                <v-chip
                  v-for="fv in values.slice(0, 5)"
                  :key="fv.id"
                  size="small"
                  class="mr-1 mb-1"
                  variant="outlined"
                >
                  {{ fv.text?.substring(0, 50) }}{{ fv.text?.length > 50 ? '...' : '' }}
                </v-chip>
                <v-chip v-if="values.length > 5" size="small" variant="text">
                  {{ t('smartQueryView.read.moreItems', { count: values.length - 5 }) }}
                </v-chip>
              </div>
            </template>
          </v-card-text>
        </v-card>
      </template>

      <!-- No Results -->
      <v-card v-if="results.total === 0" class="text-center pa-8">
        <v-icon size="64" color="grey">mdi-database-search</v-icon>
        <div class="text-h6 mt-4">{{ t('smartQueryView.read.noResults') }}</div>
        <div class="text-body-2 text-medium-emphasis">
          {{ t('smartQueryView.read.noResultsHint') }}
        </div>
      </v-card>

      <!-- Back to Assistant Button -->
      <v-card v-if="fromAssistant" class="mt-4">
        <v-card-actions class="justify-center">
          <v-btn variant="text" @click="resetAll">{{ t('smartQueryView.results.newQuery') }}</v-btn>
          <v-btn
            color="primary"
            variant="elevated"
            @click="sendResultsToAssistant"
          >
            <v-icon start>mdi-arrow-left</v-icon>
            {{ t('smartQueryView.results.backToAssistant') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/services/api'
import { useSpeechRecognition } from '@/composables/useSpeechRecognition'
import { useQueryContextStore } from '@/stores/queryContext'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const queryContextStore = useQueryContextStore()

const question = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
const results = ref<any>(null)
const previewData = ref<any>(null)
const writeMode = ref(false)
const fromAssistant = ref(false)

// Speech Recognition
const {
  isListening,
  hasMicrophone,
  transcript,
  interimTranscript,
  error: speechError,
  toggleListening,
  clearTranscript
} = useSpeechRecognition()

// Watch transcript changes and update question
watch(transcript, (newVal) => {
  if (newVal) {
    question.value = newVal
  }
})

// Watch speech errors and show them
watch(speechError, (newVal) => {
  if (newVal) {
    error.value = newVal
  }
})

// Handle voice input toggle
function handleVoiceInput() {
  if (isListening.value) {
    toggleListening()
  } else {
    // Clear previous content when starting new voice input
    clearTranscript()
    question.value = ''
    toggleListening()
  }
}

// AI Generation Progress
const currentStep = ref(1)
const stepMessages: Record<number, string> = {
  1: t('smartQueryView.generation.step1'),
  2: t('smartQueryView.generation.step2'),
  3: t('smartQueryView.generation.step3'),
  4: t('smartQueryView.generation.step4')
}

const readExamples = ref([
  { question: t('smartQueryView.examples.read.futureEvents') },
  { question: t('smartQueryView.examples.read.mayorsOnEvents') },
  { question: t('smartQueryView.examples.read.allPainPoints') },
  { question: t('smartQueryView.examples.read.gummersbachPainPoints') },
])

const writeExamples = ref([
  { question: t('smartQueryView.examples.write.createPerson') },
  { question: t('smartQueryView.examples.write.addPainPoint') },
  { question: t('smartQueryView.examples.write.findEvents') },
  { question: t('smartQueryView.examples.write.startCrawls') },
  { question: t('smartQueryView.examples.write.createCategory') },
])

const currentExamples = computed(() => writeMode.value ? writeExamples.value : readExamples.value)

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

async function executeQuery() {
  if (!question.value.trim()) return

  loading.value = true
  error.value = null
  results.value = null
  previewData.value = null

  try {
    if (writeMode.value) {
      // Write mode - get preview first
      const response = await api.post('/v1/analysis/smart-write', {
        question: question.value,
        preview_only: true,
        confirmed: false
      })

      if (response.data.mode === 'preview' && response.data.success) {
        previewData.value = response.data
      } else {
        error.value = response.data.message || t('smartQueryView.errors.noWriteOperation')
      }
    } else {
      // Read mode - execute directly
      const response = await api.post('/v1/analysis/smart-query', {
        question: question.value,
        allow_write: false
      })
      results.value = response.data
    }
  } catch (e: any) {
    error.value = e.response?.data?.detail || e.message || t('smartQueryView.errors.queryError')
  } finally {
    loading.value = false
  }
}

async function confirmWrite() {
  if (!question.value.trim()) return

  loading.value = true
  error.value = null
  currentStep.value = 1

  // Step progression simulation for category_setup operations
  const isAiGeneration = previewData.value?.interpretation?.operation === 'create_category_setup'
  let stepInterval: ReturnType<typeof setInterval> | null = null

  if (isAiGeneration) {
    // Simulate step progression during AI generation
    stepInterval = setInterval(() => {
      if (currentStep.value < 4) {
        currentStep.value++
      }
    }, 2500) // Advance every 2.5 seconds
  }

  try {
    const response = await api.post('/v1/analysis/smart-write', {
      question: question.value,
      preview_only: false,
      confirmed: true
    })
    results.value = response.data
    previewData.value = null
    currentStep.value = 4 // Show complete
  } catch (e: any) {
    error.value = e.response?.data?.detail || e.message || t('smartQuery.createError')
  } finally {
    if (stepInterval) {
      clearInterval(stepInterval)
    }
    loading.value = false
  }
}

function cancelPreview() {
  previewData.value = null
}

function resetAll() {
  results.value = null
  previewData.value = null
  question.value = ''
}

function useExample(q: string) {
  question.value = q
  executeQuery()
}

function getTimeFilterColor(filter?: string): string {
  switch (filter) {
    case 'future_only': return 'success'
    case 'past_only': return 'grey'
    default: return 'info'
  }
}

function getEntityTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    person: 'mdi-account',
    municipality: 'mdi-city',
    event: 'mdi-calendar-star',
    organization: 'mdi-domain',
  }
  return icons[type] || 'mdi-circle'
}

function getEntityTypeColor(type: string): string {
  const colors: Record<string, string> = {
    person: 'blue',
    municipality: 'green',
    event: 'orange',
    organization: 'purple',
  }
  return colors[type] || 'grey'
}

function getItemTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    entity: 'mdi-shape',
    entity_type: 'mdi-folder-multiple',
    facet_value: 'mdi-tag',
    relation: 'mdi-arrow-right-bold',
    category: 'mdi-shape-outline',
    crawl_job: 'mdi-spider-web',
  }
  return icons[type] || 'mdi-check'
}

function getItemTypeColor(type: string): string {
  const colors: Record<string, string> = {
    entity: 'primary',
    entity_type: 'purple',
    facet_value: 'secondary',
    relation: 'info',
    category: 'orange',
    crawl_job: 'success',
  }
  return colors[type] || 'grey'
}

function getInitials(name: string): string {
  return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
}

function formatAttendeeSubtitle(attendee: any): string {
  const parts = []
  if (attendee.position) parts.push(attendee.position)
  if (attendee.municipality?.name) parts.push(attendee.municipality.name)
  if (attendee.topic) parts.push(`"${attendee.topic}"`)
  return parts.join(' | ') || t('smartQueryView.read.noDetails')
}

/**
 * Send results back to the assistant and navigate back
 */
function sendResultsToAssistant() {
  if (!results.value) return

  // Build result summary
  const isWriteMode = results.value.mode === 'write'
  const summary = isWriteMode
    ? (results.value.success
      ? t('smartQueryView.assistant.elementsCreated', { count: results.value.created_items?.length || 0 })
      : results.value.message || t('smartQueryView.assistant.executionError'))
    : t('smartQueryView.assistant.resultsFound', { count: results.value.total || 0 })

  // Store results for assistant to pick up
  queryContextStore.setResults({
    summary,
    total: results.value.total || results.value.created_items?.length || 0,
    items: results.value.items?.slice(0, 5) || results.value.created_items?.slice(0, 5) || [],
    interpretation: results.value.query_interpretation || results.value.interpretation,
    success: results.value.success !== false,
    mode: isWriteMode ? 'write' : 'read',
  })

  // Navigate back (the assistant will check for results)
  router.back()
}

/**
 * Initialize from URL params and assistant context
 */
function initializeFromContext() {
  // Check for context from assistant store
  const assistantContext = queryContextStore.consumeContext()
  if (assistantContext) {
    question.value = assistantContext.query
    writeMode.value = assistantContext.mode === 'write'
    fromAssistant.value = true
    return true
  }

  // Check URL params
  const urlQuery = route.query.q as string
  const urlMode = route.query.mode as string
  const urlFrom = route.query.from as string

  if (urlQuery) {
    question.value = urlQuery
    fromAssistant.value = urlFrom === 'assistant'
  }
  if (urlMode === 'write') {
    writeMode.value = true
  }

  return !!urlQuery
}

onMounted(() => {
  loadExamples()

  // Initialize from context/URL
  const hasContext = initializeFromContext()

  // Auto-execute if we have a query from the assistant
  if (hasContext && fromAssistant.value && question.value.trim()) {
    executeQuery()
  }
})
</script>

<style scoped>
.voice-btn-listening {
  animation: pulse-voice 1.5s ease-in-out infinite;
}

@keyframes pulse-voice {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.15);
    opacity: 0.85;
  }
}
</style>
