<!-- eslint-disable vue/no-v-html -- formatQuestion returns safe formatted text -->
<template>
  <v-card class="wizard-step" elevation="1">
    <!-- Header with progress -->
    <v-card-title class="wizard-step__header">
      <div class="d-flex align-center">
        <v-icon :icon="wizardIcon" class="mr-2" color="primary" />
        <span>{{ wizardName }}</span>
      </div>
      <v-chip size="x-small" variant="tonal" color="primary">
        {{ t('assistant.wizardStep', { current: currentStepIndex + 1, total: totalSteps }) }}
      </v-chip>
    </v-card-title>

    <v-progress-linear
      :model-value="progress * 100"
      color="primary"
      height="4"
    />

    <v-card-text class="wizard-step__content">
      <!-- Question - eslint-disable-next-line vue/no-v-html -- formatQuestion returns safe formatted text -->
      <div class="wizard-step__question mb-4" v-html="formatQuestion(currentStep.question)" />

      <!-- Help text -->
      <div v-if="currentStep.help_text" class="wizard-step__help text-caption text-medium-emphasis mb-4">
        {{ currentStep.help_text }}
      </div>

      <!-- Input based on type -->

      <!-- TEXT Input -->
      <v-text-field
        v-if="currentStep.input_type === 'text'"
        v-model="answer"
        :placeholder="currentStep.placeholder"
        :rules="validationRules"
        variant="outlined"
        density="comfortable"
        autofocus
        @keydown.enter="handleNext"
      />

      <!-- TEXTAREA Input -->
      <v-textarea
        v-if="currentStep.input_type === 'textarea'"
        v-model="answer"
        :placeholder="currentStep.placeholder"
        :rules="validationRules"
        variant="outlined"
        density="comfortable"
        rows="3"
        auto-grow
        autofocus
      />

      <!-- NUMBER Input -->
      <v-number-input
        v-if="currentStep.input_type === 'number'"
        v-model="numericAnswer"
        :placeholder="currentStep.placeholder"
        :rules="validationRules"
        variant="outlined"
        density="comfortable"
        autofocus
        control-variant="stacked"
        @keydown.enter="handleNext"
      />

      <!-- DATE Input -->
      <v-text-field
        v-if="currentStep.input_type === 'date'"
        v-model="answer"
        :placeholder="currentStep.placeholder"
        type="date"
        variant="outlined"
        density="comfortable"
        autofocus
      />

      <!-- SELECT Input -->
      <v-select
        v-if="currentStep.input_type === 'select'"
        v-model="answer"
        :items="selectOptions"
        :placeholder="currentStep.placeholder"
        item-title="label"
        item-value="value"
        variant="outlined"
        density="comfortable"
        autofocus
      >
        <template #item="{ item, props: itemProps }">
          <v-list-item v-bind="itemProps">
            <template v-if="item.raw.icon" #prepend>
              <v-icon :icon="item.raw.icon" size="small" class="mr-2" />
            </template>
            <template v-if="item.raw.description" #subtitle>
              {{ item.raw.description }}
            </template>
          </v-list-item>
        </template>
      </v-select>

      <!-- MULTI_SELECT Input -->
      <v-select
        v-if="currentStep.input_type === 'multi_select'"
        v-model="answer"
        :items="selectOptions"
        :placeholder="currentStep.placeholder"
        item-title="label"
        item-value="value"
        variant="outlined"
        density="comfortable"
        multiple
        chips
        closable-chips
      />

      <!-- ENTITY_SEARCH Input -->
      <v-autocomplete
        v-if="currentStep.input_type === 'entity_search'"
        v-model="answer"
        v-model:search-input="entitySearchQuery"
        :items="entitySearchResults"
        :loading="isSearching"
        :placeholder="currentStep.placeholder || t('assistant.wizardSearchEntity')"
        item-title="name"
        item-value="id"
        variant="outlined"
        density="comfortable"
        no-filter
        return-object
        @update:search="onEntitySearch"
      >
        <template #item="{ item, props: itemProps }">
          <v-list-item v-bind="itemProps">
            <template #prepend>
              <v-icon size="small" class="mr-2">mdi-file-document-outline</v-icon>
            </template>
            <template #subtitle>
              {{ item.raw.entity_type }}
            </template>
          </v-list-item>
        </template>
      </v-autocomplete>

      <!-- CONFIRM Input -->
      <div v-if="currentStep.input_type === 'confirm'" class="wizard-step__confirm">
        <v-card variant="outlined" class="mb-4 pa-3">
          <div class="text-subtitle-2 mb-2">{{ t('assistant.wizardSummary') }}</div>
          <v-list density="compact" class="bg-transparent">
            <v-list-item
              v-for="(value, key) in previousAnswers"
              :key="key"
              class="px-0"
            >
              <template #prepend>
                <v-icon size="small" color="success" class="mr-2">mdi-check</v-icon>
              </template>
              <v-list-item-title class="text-body-2">
                <strong>{{ formatAnswerKey(key) }}:</strong> {{ formatAnswerValue(value) }}
              </v-list-item-title>
            </v-list-item>
          </v-list>
        </v-card>

        <div class="d-flex gap-2">
          <v-btn
            v-for="option in selectOptions"
            :key="option.value"
            :color="option.value === 'yes' ? 'primary' : 'default'"
            :variant="option.value === 'yes' ? 'elevated' : 'outlined'"
            @click="answer = option.value; handleNext()"
          >
            <v-icon v-if="option.icon" :icon="option.icon" start />
            {{ option.label }}
          </v-btn>
        </div>
      </div>
    </v-card-text>

    <v-card-actions v-if="currentStep.input_type !== 'confirm'" class="wizard-step__actions">
      <v-btn
        v-if="canGoBack"
        variant="tonal"
        @click="$emit('back')"
      >
        <v-icon start>mdi-chevron-left</v-icon>
        {{ t('assistant.wizardBack') }}
      </v-btn>

      <v-btn
        variant="tonal"
        color="error"
        @click="$emit('cancel')"
      >
        {{ t('assistant.wizardCancel') }}
      </v-btn>

      <v-spacer />

      <v-btn
        color="primary"
        :disabled="!isValid"
        :loading="isLoading"
        @click="handleNext"
      >
        {{ isLastStep ? t('assistant.wizardFinish') : t('assistant.wizardNext') }}
        <v-icon v-if="!isLastStep" end>mdi-chevron-right</v-icon>
        <v-icon v-else end>mdi-check</v-icon>
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { entityApi } from '@/services/api'
import { useLogger } from '@/composables/useLogger'
import { escapeHtml } from '@/utils/messageFormatting'

const props = defineProps<{
  wizardState: WizardState
  currentStep: WizardStepDef
  canGoBack: boolean
  progress: number
  isLoading?: boolean
  wizardName?: string
  wizardIcon?: string
}>()

const emit = defineEmits<{
  next: [value: unknown]
  back: []
  cancel: []
}>()

const logger = useLogger('WizardStep')

const { t } = useI18n()

// Types
export interface WizardStepOption {
  value: string
  label: string
  description?: string
  icon?: string
}

export interface WizardValidation {
  min_length?: number
  max_length?: number
  min?: number
  max?: number
  pattern?: string
  [key: string]: unknown
}

export interface WizardStepDef {
  id: string
  question: string
  input_type: 'text' | 'textarea' | 'number' | 'date' | 'select' | 'multi_select' | 'entity_search' | 'confirm'
  options?: WizardStepOption[]
  placeholder?: string
  validation?: WizardValidation
  entity_type?: string
  default_value?: unknown
  required?: boolean
  help_text?: string
}

export interface WizardState {
  wizard_id: string
  wizard_type: string
  current_step_id: string
  current_step_index: number
  total_steps: number
  answers: Record<string, unknown>
  completed: boolean
  cancelled: boolean
}

// Entity search result interface
interface EntitySearchResult {
  id: string
  name: string
  entity_type?: string
}

// State - answer can be string, number, array (multi_select), or object (entity_search result)
type AnswerValue = string | number | string[] | { id?: string; [key: string]: unknown } | null
const answer = ref<AnswerValue>((props.currentStep.default_value ?? '') as AnswerValue)

// Computed for v-number-input (expects number | null | undefined)
const numericAnswer = computed({
  get: () => typeof answer.value === 'number' ? answer.value : null,
  set: (val) => { answer.value = val ?? 0 }
})
const entitySearchQuery = ref('')
const entitySearchResults = ref<EntitySearchResult[]>([])
const isSearching = ref(false)

// Computed
const currentStepIndex = computed(() => props.wizardState.current_step_index)
const totalSteps = computed(() => props.wizardState.total_steps)
const isLastStep = computed(() => currentStepIndex.value >= totalSteps.value - 1)
const previousAnswers = computed(() => props.wizardState.answers)

const selectOptions = computed<WizardStepOption[]>(() => {
  return props.currentStep.options || []
})

const validationRules = computed(() => {
  const rules: ((v: unknown) => boolean | string)[] = []

  if (props.currentStep.required !== false) {
    rules.push((v: unknown) => !!v || t('assistant.wizardRequired'))
  }

  if (props.currentStep.validation) {
    const val = props.currentStep.validation
    if (val.min_length !== undefined) {
      const minLen = val.min_length
      rules.push((v: unknown) => {
        const str = v as string
        return !str || str.length >= minLen || t('assistant.wizardMinLength', { min: minLen })
      })
    }
    if (val.max_length !== undefined) {
      const maxLen = val.max_length
      rules.push((v: unknown) => {
        const str = v as string
        return !str || str.length <= maxLen || t('assistant.wizardMaxLength', { max: maxLen })
      })
    }
    if (val.min !== undefined) {
      const minVal = val.min
      rules.push((v: unknown) => (v as number) >= minVal || t('assistant.wizardMinValue', { min: minVal }))
    }
    if (val.max !== undefined) {
      const maxVal = val.max
      rules.push((v: unknown) => (v as number) <= maxVal || t('assistant.wizardMaxValue', { max: maxVal }))
    }
  }

  return rules
})

const isValid = computed(() => {
  if (props.currentStep.required === false && !answer.value) {
    return true
  }

  if (!answer.value && answer.value !== 0) {
    return false
  }

  // Run validation rules
  for (const rule of validationRules.value) {
    const result = rule(answer.value)
    if (result !== true) {
      return false
    }
  }

  return true
})

// Methods
function handleNext() {
  if (!isValid.value) return

  // For entity search, extract the ID
  let value: AnswerValue | undefined = answer.value
  if (props.currentStep.input_type === 'entity_search' && value && typeof value === 'object' && 'id' in value) {
    value = value.id as string | undefined
  }

  emit('next', value)
}

function formatQuestion(question: string): string {
  // First escape HTML to prevent XSS, then apply markdown-like formatting
  const formatted = escapeHtml(question)
  return formatted
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
}

function formatAnswerKey(key: string): string {
  // Convert snake_case to Title Case
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
}

function formatAnswerValue(value: unknown): string {
  if (typeof value === 'object' && value !== null) {
    const obj = value as { name?: string; label?: string }
    return obj.name || obj.label || JSON.stringify(value)
  }
  return String(value)
}

async function onEntitySearch(query: string) {
  if (!query || query.length < 2) {
    entitySearchResults.value = []
    return
  }

  isSearching.value = true
  try {
    const params: Record<string, unknown> = { search: query, per_page: 10 }
    if (props.currentStep.entity_type) {
      params.entity_type_slug = props.currentStep.entity_type
    }

    const response = await entityApi.getEntities(params)
    entitySearchResults.value = response.data.items.map((item: { id: string; name: string; entity_type?: { name?: string }; entity_type_slug?: string }) => ({
      id: item.id,
      name: item.name,
      entity_type: item.entity_type?.name || item.entity_type_slug,
    }))
  } catch (e) {
    logger.error('Entity search failed:', e)
    entitySearchResults.value = []
  } finally {
    isSearching.value = false
  }
}

// Watch for step changes to reset answer
watch(() => props.currentStep.id, () => {
  answer.value = (props.currentStep.default_value ?? '') as AnswerValue
  entitySearchResults.value = []
})
</script>

<style scoped>
.wizard-step {
  margin: 8px 0;
  border-radius: 12px;
  overflow: hidden;
}

.wizard-step__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgb(var(--v-theme-surface-variant));
}

.wizard-step__content {
  padding: 16px;
}

.wizard-step__question {
  font-size: 1rem;
  font-weight: 500;
  line-height: 1.5;
}

.wizard-step__question code {
  background: rgb(var(--v-theme-surface-variant));
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.875em;
}

.wizard-step__help {
  padding: 8px 12px;
  background: rgb(var(--v-theme-surface-variant));
  border-radius: 6px;
  border-left: 3px solid rgb(var(--v-theme-info));
}

.wizard-step__confirm {
  text-align: center;
}

.wizard-step__actions {
  padding: 12px 16px;
  border-top: 1px solid rgb(var(--v-theme-outline-variant));
}
</style>
