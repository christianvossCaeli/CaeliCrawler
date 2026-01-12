<template>
  <v-card variant="outlined" class="mb-6">
    <v-card-title class="text-subtitle-1">
      <v-icon start color="info">mdi-auto-fix</v-icon>
      {{ t('categories.aiPrefill.title') }}
    </v-card-title>
    <v-card-text>
      <p class="text-body-2 text-medium-emphasis mb-3">
        {{ t('categories.aiPrefill.description') }}
      </p>

      <v-textarea
        :model-value="prompt"
        :label="t('categories.aiPrefill.promptLabel')"
        :hint="t('categories.aiPrefill.promptHint')"
        persistent-hint
        rows="3"
        variant="outlined"
        @update:model-value="emit('update:prompt', $event)"
      />

      <div class="d-flex flex-wrap align-center mt-3">
        <v-btn
          variant="tonal"
          color="primary"
          class="mr-2 mb-2"
          :loading="loading"
          :disabled="loading || !prompt.trim()"
          @click="emit('generate')"
        >
          <v-icon start>mdi-auto-fix</v-icon>
          {{ t('categories.aiPrefill.generate') }}
        </v-btn>
        <v-btn
          v-if="suggestions"
          variant="tonal"
          color="secondary"
          class="mr-2 mb-2"
          :disabled="loading"
          @click="emit('apply')"
        >
          <v-icon start>mdi-check</v-icon>
          {{ t('categories.aiPrefill.apply') }}
        </v-btn>
        <v-checkbox
          v-if="suggestions"
          v-model="overwriteModel"
          density="compact"
          hide-details
          class="mb-2"
          :label="t('categories.aiPrefill.overwrite')"
          :disabled="loading"
        />
      </div>

      <v-alert v-if="loading" type="info" variant="tonal" class="mt-3">
        {{ t('categories.aiPrefill.loadingHint') }}
      </v-alert>
      <v-alert v-else-if="error" type="error" variant="tonal" class="mt-3">
        {{ error }}
      </v-alert>

      <div v-if="examplePrompts.length" class="mt-4">
        <div class="text-caption text-medium-emphasis mb-2">
          {{ t('categories.aiPrefill.examplesTitle') }}
        </div>
        <div class="d-flex flex-wrap">
          <v-chip
            v-for="example in examplePrompts"
            :key="example"
            class="mr-2 mb-2"
            variant="outlined"
            @click="emit('update:prompt', example)"
          >
            {{ example }}
          </v-chip>
        </div>
      </div>

      <v-card v-if="suggestions" variant="tonal" class="mt-4">
        <v-card-title class="text-subtitle-2">
          {{ t('categories.aiPrefill.previewTitle') }}
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12" md="6">
              <div class="text-caption text-medium-emphasis">{{ t('categories.form.name') }}</div>
              <div class="text-body-2">
                {{ suggestions.name || t('common.notAvailable') }}
              </div>
            </v-col>
            <v-col cols="12" md="6">
              <div class="text-caption text-medium-emphasis">{{ t('categories.form.purpose') }}</div>
              <div class="text-body-2">
                {{ suggestions.purpose || t('common.notAvailable') }}
              </div>
            </v-col>
          </v-row>

          <div v-if="suggestions.description" class="mt-2">
            <div class="text-caption text-medium-emphasis">{{ t('categories.form.description') }}</div>
            <div class="text-body-2">{{ suggestions.description }}</div>
          </div>

          <div v-if="suggestions.search_terms?.length" class="mt-2">
            <div class="text-caption text-medium-emphasis">{{ t('categories.form.searchTerms') }}</div>
            <div class="d-flex flex-wrap mt-1">
              <v-chip
                v-for="term in suggestions.search_terms"
                :key="term"
                size="small"
                color="primary"
                variant="tonal"
                class="mr-1 mb-1"
              >
                {{ term }}
              </v-chip>
            </div>
          </div>

          <div v-if="suggestions.document_types?.length" class="mt-2">
            <div class="text-caption text-medium-emphasis">{{ t('categories.form.documentTypes') }}</div>
            <div class="d-flex flex-wrap mt-1">
              <v-chip
                v-for="docType in suggestions.document_types"
                :key="docType"
                size="small"
                color="secondary"
                variant="tonal"
                class="mr-1 mb-1"
              >
                {{ docType }}
              </v-chip>
            </div>
          </div>

          <div v-if="regionLabel" class="mt-2">
            <div class="text-caption text-medium-emphasis">{{ t('categories.aiPrefill.region') }}</div>
            <div class="text-body-2">{{ regionLabel }}</div>
          </div>

          <div v-if="suggestions.time_focus" class="mt-2">
            <div class="text-caption text-medium-emphasis">{{ t('categories.aiPrefill.timeFocus') }}</div>
            <div class="text-body-2">{{ suggestions.time_focus }}</div>
          </div>

          <div v-if="suggestions.schedule_cron || scheduleStatus" class="mt-2">
            <div class="text-caption text-medium-emphasis">{{ t('categories.form.scheduleTitle') }}</div>
            <div class="text-body-2">
              <span>{{ suggestions.schedule_cron || t('common.notAvailable') }}</span>
              <span v-if="scheduleStatus" class="text-caption text-medium-emphasis ml-2">
                ({{ scheduleStatus }})
              </span>
            </div>
          </div>
        </v-card-text>
      </v-card>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { CategoryAiPrefillSuggestion } from '@/types/category'

const props = defineProps<{
  prompt: string
  loading: boolean
  error: string | null
  suggestions: CategoryAiPrefillSuggestion | null
  overwrite: boolean
}>()

const emit = defineEmits<{
  'update:prompt': [value: string]
  'update:overwrite': [value: boolean]
  'generate': []
  'apply': []
}>()

const { t, tm } = useI18n()

const examplePrompts = computed(() => {
  const examples = tm('categories.aiPrefill.examples') as string[] | string | null
  if (Array.isArray(examples)) {
    return examples.filter(Boolean)
  }
  return []
})

const regionLabel = computed(() => {
  const geo = props.suggestions?.geographic_filter
  if (!geo) return ''
  return [geo.admin_level_2, geo.admin_level_1, geo.country].filter(Boolean).join(', ')
})

const scheduleStatus = computed(() => {
  if (typeof props.suggestions?.schedule_enabled !== 'boolean') return ''
  return props.suggestions.schedule_enabled ? t('common.enabled') : t('common.disabled')
})

const overwriteModel = computed({
  get: () => props.overwrite,
  set: (value: boolean) => emit('update:overwrite', value),
})
</script>
