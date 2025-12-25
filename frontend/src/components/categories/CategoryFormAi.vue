<template>
  <v-card variant="outlined" class="mb-4">
    <v-card-text class="d-flex align-center">
      <v-avatar color="info" size="48" class="mr-4">
        <v-icon color="on-info">mdi-robot</v-icon>
      </v-avatar>
      <div>
        <div class="text-body-1 font-weight-medium">{{ $t('categories.form.aiPromptTitle') }}</div>
        <div class="text-caption text-medium-emphasis">{{ $t('categories.form.aiPromptDescription') }}</div>
      </div>
    </v-card-text>
  </v-card>

  <v-textarea
    :model-value="formData.ai_extraction_prompt"
    :label="$t('categories.form.aiPrompt')"
    rows="14"
    variant="outlined"
    :hint="$t('categories.form.aiPromptHint')"
    persistent-hint
    @update:model-value="updateField('ai_extraction_prompt', $event)"
  />
</template>

<script setup lang="ts">
import type { CategoryFormData } from '@/composables/useCategoriesView'

export interface CategoryFormAiProps {
  formData: CategoryFormData
}

export interface CategoryFormAiEmits {
  (e: 'update:formData', data: Partial<CategoryFormData>): void
}

const props = defineProps<CategoryFormAiProps>()
const emit = defineEmits<CategoryFormAiEmits>()

const updateField = (field: keyof CategoryFormData, value: any) => {
  emit('update:formData', { [field]: value })
}
</script>
