<template>
  <v-dialog
    v-model="modelValue"
    :max-width="DIALOG_SIZES.ML"
    persistent
    role="dialog"
    aria-modal="true"
    :aria-labelledby="dialogTitleId"
  >
    <v-card>
      <v-card-title :id="dialogTitleId" class="d-flex align-center">
        <v-icon color="primary" class="mr-2">mdi-plus-circle</v-icon>
        {{ t('summaries.createNew') }}
      </v-card-title>

      <v-card-text>
        <v-window v-model="step">
          <!-- Step 1: Prompt Input -->
          <v-window-item :value="1">
            <div class="mb-4">
              <p class="text-body-1 mb-4">
                {{ t('summaries.createDescription') }}
              </p>

              <v-textarea
                v-model="prompt"
                :label="t('summaries.promptLabel')"
                :placeholder="t('summaries.promptPlaceholder')"
                rows="4"
                counter
                maxlength="2000"
                :aria-invalid="!!promptError"
                :error-messages="promptError"
                autofocus
              />

              <v-text-field
                v-model="customName"
                :label="t('summaries.customNameLabel')"
                :hint="t('summaries.customNameHint')"
                persistent-hint
                class="mt-4"
              />

              <!-- Examples -->
              <v-expansion-panels class="mt-4" variant="accordion">
                <v-expansion-panel>
                  <v-expansion-panel-title>
                    <v-icon start>mdi-lightbulb-outline</v-icon>
                    {{ t('summaries.examplesTitle') }}
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <v-list density="compact">
                      <v-list-item
                        v-for="(example, idx) in examples"
                        :key="idx"
                        @click="useExample(example)"
                      >
                        <template #prepend>
                          <v-icon color="primary" size="small">mdi-text-box-outline</v-icon>
                        </template>
                        <v-list-item-title class="text-body-2">{{ example }}</v-list-item-title>
                      </v-list-item>
                    </v-list>
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>
            </div>
          </v-window-item>

          <!-- Step 2: Processing -->
          <v-window-item :value="2">
            <div class="text-center py-8">
              <v-progress-circular
                indeterminate
                size="80"
                width="6"
                color="primary"
              />
              <p class="text-h6 mt-6">{{ t('summaries.interpreting') }}</p>
              <p class="text-body-2 text-medium-emphasis">
                {{ t('summaries.interpretingHint') }}
              </p>
            </div>
          </v-window-item>

          <!-- Step 3: Preview Result -->
          <v-window-item :value="3">
            <div v-if="interpretationResult" class="mb-4">
              <v-alert type="success" variant="tonal" class="mb-4">
                <v-alert-title>{{ interpretationResult.name }}</v-alert-title>
                {{ interpretationResult.message }}
              </v-alert>

              <!-- Interpretation Details -->
              <v-card variant="outlined" class="mb-4">
                <v-card-title class="text-subtitle-1">
                  <v-icon start>mdi-widgets</v-icon>
                  {{ interpretationResult.widgets_created }} {{ t('summaries.widgetsCreated') }}
                </v-card-title>
                <v-card-text v-if="interpretationResult.interpretation">
                  <div v-if="interpretationResult.interpretation.theme" class="mb-2">
                    <strong>{{ t('summaries.theme') }}:</strong>
                    {{ interpretationResult.interpretation.theme.context || interpretationResult.interpretation.theme.primary_entity_type }}
                  </div>
                  <div v-if="interpretationResult.interpretation.suggested_schedule" class="mb-2">
                    <strong>{{ t('summaries.suggestedSchedule') }}:</strong>
                    {{ interpretationResult.interpretation.suggested_schedule.reason }}
                  </div>
                  <div v-if="interpretationResult.interpretation.overall_reasoning" class="text-body-2 text-medium-emphasis">
                    {{ interpretationResult.interpretation.overall_reasoning }}
                  </div>
                </v-card-text>
              </v-card>
            </div>
          </v-window-item>
        </v-window>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-btn
          variant="text"
          :disabled="isCreating"
          @click="close"
        >
          {{ step === 3 ? t('common.close') : t('common.cancel') }}
        </v-btn>
        <v-spacer />
        <v-btn
          v-if="step === 1"
          color="primary"
          variant="flat"
          :disabled="!isValidPrompt"
          :loading="isCreating"
          @click="createSummary"
        >
          <v-icon start>mdi-auto-fix</v-icon>
          {{ t('summaries.createWithAI') }}
        </v-btn>
        <v-btn
          v-if="step === 3 && interpretationResult"
          color="primary"
          variant="flat"
          @click="openSummary"
        >
          {{ t('summaries.openDashboard') }}
          <v-icon end>mdi-arrow-right</v-icon>
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'
import { useCustomSummariesStore } from '@/stores/customSummaries'
import { useDialogFocus } from '@/composables'
import { useLogger } from '@/composables/useLogger'

const modelValue = defineModel<boolean>()

const props = defineProps<{
  initialPrompt?: string
}>()

const emit = defineEmits<{
  created: [result: { id: string; name: string }]
}>()

const logger = useLogger('SummaryCreateDialog')

const { t, tm } = useI18n()
const store = useCustomSummariesStore()

// ARIA
const dialogTitleId = `summary-create-dialog-title-${Math.random().toString(36).slice(2, 9)}`

// Focus management for accessibility
useDialogFocus({ isOpen: modelValue })

// State
const step = ref(1)
const prompt = ref('')
const customName = ref('')
const promptError = ref('')
interface InterpretationTheme {
  context?: string
  primary_entity_type?: string
}

interface SuggestedSchedule {
  reason?: string
  interval?: string
}

interface Interpretation {
  theme?: InterpretationTheme
  suggested_schedule?: SuggestedSchedule
  overall_reasoning?: string
  [key: string]: unknown
}

const interpretationResult = ref<{
  id: string
  name: string
  interpretation: Interpretation
  widgets_created: number
  message: string
} | null>(null)

const isCreating = computed(() => store.isCreating)

const isValidPrompt = computed(() => {
  return prompt.value.length >= 10 && prompt.value.length <= 2000
})

const examples = computed(() => tm('summaries.createDialog.examplePrompts') as string[])

function useExample(example: string) {
  prompt.value = example
}

async function createSummary() {
  if (!isValidPrompt.value) {
    promptError.value = t('summaries.promptTooShort')
    return
  }

  promptError.value = ''
  step.value = 2

  try {
    const result = await store.createFromPrompt({
      prompt: prompt.value,
      name: customName.value || undefined,
    })

    if (result) {
      interpretationResult.value = result
      step.value = 3
    } else {
      step.value = 1
      promptError.value = store.error || t('summaries.createError')
    }
  } catch (e) {
    logger.error('Failed to create summary:', e)
    step.value = 1
    promptError.value = t('summaries.createError')
  }
}

function openSummary() {
  if (interpretationResult.value) {
    emit('created', {
      id: interpretationResult.value.id,
      name: interpretationResult.value.name,
    })
  }
  close()
}

function close() {
  modelValue.value = false
}

function reset() {
  step.value = 1
  prompt.value = ''
  customName.value = ''
  promptError.value = ''
  interpretationResult.value = null
}

// Reset state when dialog opens
watch(modelValue, (isOpen) => {
  if (isOpen) {
    reset()
    // Pre-fill prompt if provided (e.g., from plan mode)
    if (props.initialPrompt) {
      prompt.value = props.initialPrompt
    }
  }
})
</script>
