<template>
  <v-dialog
    v-model="modelValue"
    :max-width="DIALOG_SIZES.XL"
    persistent
    scrollable
    role="dialog"
    :aria-labelledby="titleId"
    :aria-busy="loading"
  >
    <v-card>
      <v-card-title :id="titleId" class="d-flex align-center pa-4 bg-info">
        <v-avatar color="info-darken-1" size="40" class="mr-3" aria-hidden="true">
          <v-icon color="on-info">mdi-robot</v-icon>
        </v-avatar>
        <div>
          <div class="text-h6">{{ t('categories.aiPreview.title') }}</div>
          <div class="text-caption opacity-80">{{ t('categories.aiPreview.subtitle') }}</div>
        </div>
      </v-card-title>

      <v-card-text v-if="loading" class="pa-6 text-center">
        <v-progress-circular indeterminate color="info" size="64" class="mb-4"></v-progress-circular>
        <div class="text-h6">{{ t('categories.aiPreview.generating') }}</div>
        <div class="text-body-2 text-medium-emphasis">{{ t('categories.aiPreview.generatingHint') }}</div>
      </v-card-text>

      <v-card-text v-else-if="previewData" class="pa-6">
        <!-- EntityType Section -->
        <v-card variant="outlined" class="mb-4">
          <v-card-title class="text-subtitle-1 pb-2">
            <v-icon start color="primary">mdi-shape</v-icon>
            {{ t('categories.aiPreview.entityType') }}
          </v-card-title>
          <v-card-text>
            <v-radio-group :model-value="selectedEntityTypeOption" hide-details @update:model-value="handleEntityTypeChange">
              <v-radio value="new" :label="t('categories.aiPreview.createNew')">
                <template #label>
                  <div>
                    <span class="font-weight-medium">{{ t('categories.aiPreview.createNew') }}: </span>
                    <v-chip size="small" color="success" class="ml-1">{{ previewData.suggested_entity_type?.name }}</v-chip>
                    <span class="text-caption text-medium-emphasis ml-2">{{ previewData.suggested_entity_type?.description }}</span>
                  </div>
                </template>
              </v-radio>
              <v-radio
                v-for="et in (previewData.existing_entity_types ?? []).slice(0, 5)"
                :key="et.id"
                :value="et.id"
              >
                <template #label>
                  <div>
                    <span class="font-weight-medium">{{ t('categories.aiPreview.useExisting') }}: </span>
                    <v-chip size="small" color="primary" class="ml-1">{{ et.name }}</v-chip>
                    <span class="text-caption text-medium-emphasis ml-2">{{ et.description }}</span>
                  </div>
                </template>
              </v-radio>
            </v-radio-group>
          </v-card-text>
        </v-card>

        <!-- FacetTypes Section -->
        <v-card variant="outlined" class="mb-4">
          <v-card-title class="text-subtitle-1 pb-2">
            <v-icon start color="secondary">mdi-tag-multiple</v-icon>
            {{ t('categories.aiPreview.facetTypes') }}
          </v-card-title>
          <v-card-text>
            <p class="text-body-2 text-medium-emphasis mb-3">{{ t('categories.aiPreview.facetTypesHint') }}</p>
            <v-checkbox
              v-for="(ft, index) in previewData.suggested_facet_types"
              :key="ft.slug"
              :model-value="selectedFacetTypes[index] ?? false"
              hide-details
              density="compact"
              @update:model-value="updateFacetType(index, $event ?? false)"
            >
              <template #label>
                <div class="d-flex align-center">
                  <v-icon :color="ft.color" size="small" class="mr-2">{{ ft.icon }}</v-icon>
                  <span class="font-weight-medium">{{ ft.name }}</span>
                  <v-chip v-if="!ft.is_new" size="x-small" color="info" class="ml-2">{{ t('categories.aiPreview.exists') }}</v-chip>
                  <v-chip v-else size="x-small" color="success" class="ml-2">{{ t('categories.aiPreview.new') }}</v-chip>
                  <span class="text-caption text-medium-emphasis ml-2">{{ ft.description }}</span>
                </div>
              </template>
            </v-checkbox>
          </v-card-text>
        </v-card>

        <!-- Extraction Prompt Section -->
        <v-card variant="outlined" class="mb-4">
          <v-card-title class="text-subtitle-1 pb-2">
            <v-icon start color="info">mdi-text-box-edit</v-icon>
            {{ t('categories.aiPreview.extractionPrompt') }}
          </v-card-title>
          <v-card-text>
            <v-textarea
              :model-value="extractionPrompt"
              rows="8"
              variant="outlined"
              :hint="t('categories.aiPreview.promptHint')"
              persistent-hint
              @update:model-value="$emit('update:extractionPrompt', $event)"
            ></v-textarea>
          </v-card-text>
        </v-card>

        <!-- Search Terms & URL Patterns -->
        <v-row>
          <v-col cols="12" md="6">
            <v-card variant="outlined" class="h-100">
              <v-card-title class="text-subtitle-2 pb-2">
                <v-icon start size="small">mdi-magnify</v-icon>
                {{ t('categories.aiPreview.searchTerms') }}
              </v-card-title>
              <v-card-text>
                <v-chip
                  v-for="term in previewData.suggested_search_terms"
                  :key="term"
                  size="small"
                  color="primary"
                  variant="tonal"
                  class="mr-1 mb-1"
                >
                  {{ term }}
                </v-chip>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" md="6">
            <v-card variant="outlined" class="h-100">
              <v-card-title class="text-subtitle-2 pb-2">
                <v-icon start size="small">mdi-filter</v-icon>
                {{ t('categories.aiPreview.urlPatterns') }}
              </v-card-title>
              <v-card-text>
                <div class="mb-2">
                  <span class="text-caption font-weight-medium text-success">Include:</span>
                  <v-chip
                    v-for="pattern in previewData.suggested_url_include_patterns"
                    :key="pattern"
                    size="x-small"
                    color="success"
                    variant="tonal"
                    class="ml-1 mb-1"
                  >
                    {{ pattern }}
                  </v-chip>
                  <span v-if="!previewData.suggested_url_include_patterns?.length" class="text-caption text-medium-emphasis">-</span>
                </div>
                <div>
                  <span class="text-caption font-weight-medium text-error">Exclude:</span>
                  <v-chip
                    v-for="pattern in previewData.suggested_url_exclude_patterns"
                    :key="pattern"
                    size="x-small"
                    color="error"
                    variant="tonal"
                    class="ml-1 mb-1"
                  >
                    {{ pattern }}
                  </v-chip>
                  <span v-if="!previewData.suggested_url_exclude_patterns?.length" class="text-caption text-medium-emphasis">-</span>
                </div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <!-- Reasoning -->
        <v-alert v-if="previewData.reasoning" type="info" variant="tonal" class="mt-4">
          <div class="text-caption font-weight-medium mb-1">{{ t('categories.aiPreview.reasoning') }}</div>
          <div class="text-body-2">{{ previewData.reasoning }}</div>
        </v-alert>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions class="pa-4">
        <v-btn variant="tonal" @click="modelValue = false">{{ t('common.cancel') }}</v-btn>
        <v-btn variant="tonal" color="grey" @click="$emit('saveWithoutAi')">
          <v-icon start>mdi-content-save-outline</v-icon>
          {{ t('categories.aiPreview.saveWithoutAi') }}
        </v-btn>
        <v-spacer></v-spacer>
        <v-btn
          variant="tonal"
          color="primary"
          :loading="saving"
          :disabled="loading"
          @click="$emit('saveWithAi')"
        >
          <v-icon start>mdi-check</v-icon>
          {{ t('categories.aiPreview.applyAndSave') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'

const modelValue = defineModel<boolean>()

// Props
defineProps<{
  loading: boolean
  saving: boolean
  previewData: AiPreviewData | null
  selectedEntityTypeOption: string
  selectedFacetTypes: boolean[]
  extractionPrompt: string
}>()

// Emits
const emit = defineEmits<{
  'update:selectedEntityTypeOption': [value: string]
  'update:extractionPrompt': [value: string]
  'updateFacetType': [payload: { index: number; value: boolean }]
  'saveWithoutAi': []
  'saveWithAi': []
}>()

// Accessibility
const titleId = `ai-preview-dialog-title-${Math.random().toString(36).slice(2, 9)}`

// Types
interface EntityType {
  id: string
  name: string
  description?: string
}

interface FacetType {
  slug: string
  name: string
  icon?: string
  color?: string
  description?: string
  is_new?: boolean
  selected?: boolean
}

interface AiPreviewData {
  suggested_entity_type?: {
    name?: string
    description?: string
    is_new?: boolean
    id?: string
  }
  existing_entity_types?: EntityType[]
  suggested_facet_types?: FacetType[]
  suggested_extraction_prompt?: string
  suggested_search_terms?: string[]
  suggested_url_include_patterns?: string[]
  suggested_url_exclude_patterns?: string[]
  reasoning?: string
}

const { t } = useI18n()

// Methods
const handleEntityTypeChange = (value: string | null) => {
  if (value) {
    emit('update:selectedEntityTypeOption', value)
  }
}

const updateFacetType = (index: number, value: boolean) => {
  emit('updateFacetType', { index, value })
}
</script>
