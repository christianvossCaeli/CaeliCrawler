<script setup lang="ts">
/**
 * SummaryQuickCreate Widget - Quick creation of custom summaries from dashboard
 */

import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useCustomSummariesStore } from '@/stores/customSummaries'
import BaseWidget from '../BaseWidget.vue'
import type { WidgetDefinition, WidgetConfig } from '../types'

const props = defineProps<{
  definition: WidgetDefinition
  config?: WidgetConfig
  isEditing?: boolean
}>()

const { t } = useI18n()
const router = useRouter()
const store = useCustomSummariesStore()

/** Prompt length constraints */
const MIN_PROMPT_LENGTH = 10
const MAX_PROMPT_LENGTH = 2000

const prompt = ref('')
const creating = ref(false)
const error = ref<string | null>(null)
const success = ref<{ id: string; name: string } | null>(null)

const isEditMode = computed(() => props.isEditing ?? false)

const examplePrompts = [
  'dashboard.summaryExamples.topEntities',
  'dashboard.summaryExamples.recentChanges',
  'dashboard.summaryExamples.dataOverview',
]

const createSummary = async () => {
  if (!prompt.value.trim() || creating.value || isEditMode.value) return

  const trimmedLength = prompt.value.trim().length
  if (trimmedLength < MIN_PROMPT_LENGTH) {
    error.value = t('summaries.promptTooShort', { min: MIN_PROMPT_LENGTH })
    return
  }
  if (trimmedLength > MAX_PROMPT_LENGTH) {
    error.value = t('summaries.promptTooLong', { max: MAX_PROMPT_LENGTH })
    return
  }

  creating.value = true
  error.value = null
  success.value = null

  try {
    const result = await store.createFromPrompt({
      prompt: prompt.value.trim(),
    })

    if (result) {
      success.value = { id: result.id, name: result.name }
      prompt.value = ''
    } else {
      error.value = store.error || t('summaries.createError')
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('summaries.createError')
  } finally {
    creating.value = false
  }
}

const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    createSummary()
  }
}

const openSummary = () => {
  if (success.value) {
    router.push({ path: `/summaries/${success.value.id}` })
  }
}

const useExample = (exampleKey: string) => {
  if (isEditMode.value) return
  prompt.value = t(exampleKey)
}

const clearSuccess = () => {
  success.value = null
}
</script>

<template>
  <BaseWidget
    :definition="definition"
    :config="config"
    :is-editing="isEditing"
  >
    <div class="quick-create-content">
      <!-- Success State -->
      <div v-if="success" class="text-center py-4">
        <v-icon size="48" color="success" class="mb-2">mdi-check-circle</v-icon>
        <div class="text-body-1 font-weight-medium mb-1">
          {{ t('summaries.created') }}
        </div>
        <div class="text-body-2 text-medium-emphasis mb-3">
          "{{ success.name }}"
        </div>
        <div class="d-flex justify-center gap-2">
          <v-btn
            variant="tonal"
            color="primary"
            size="small"
            :disabled="isEditing"
            @click="openSummary"
          >
            {{ t('summaries.openDashboard') }}
          </v-btn>
          <v-btn
            variant="text"
            size="small"
            :disabled="isEditing"
            @click="clearSuccess"
          >
            {{ t('summaries.createNew') }}
          </v-btn>
        </div>
      </div>

      <!-- Create Form -->
      <template v-else>
        <v-textarea
          v-model="prompt"
          :placeholder="t('summaries.promptPlaceholder')"
          :disabled="isEditing || creating"
          variant="outlined"
          density="compact"
          rows="2"
          hide-details
          class="mb-2"
          @keydown="handleKeydown"
        />

        <v-alert
          v-if="error"
          type="error"
          density="compact"
          variant="tonal"
          closable
          class="mb-2"
          @click:close="error = null"
        >
          {{ error }}
        </v-alert>

        <v-btn
          block
          color="primary"
          :loading="creating"
          :disabled="isEditing || !prompt.trim()"
          class="mb-3"
          @click="createSummary"
        >
          <v-icon start size="small">mdi-auto-fix</v-icon>
          {{ t('summaries.createWithAI') }}
        </v-btn>

        <!-- Example Prompts -->
        <div class="text-caption text-medium-emphasis mb-1">
          {{ t('summaries.examplesTitle') }}:
        </div>
        <div class="d-flex flex-wrap gap-1">
          <v-chip
            v-for="example in examplePrompts"
            :key="example"
            size="x-small"
            variant="outlined"
            :disabled="isEditing"
            class="example-chip"
            @click="useExample(example)"
          >
            {{ t(example) }}
          </v-chip>
        </div>
      </template>
    </div>
  </BaseWidget>
</template>

<style scoped>
.quick-create-content {
  min-height: 100px;
}

.example-chip {
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.example-chip:hover:not(:disabled) {
  background-color: rgba(var(--v-theme-primary), 0.1);
}
</style>
