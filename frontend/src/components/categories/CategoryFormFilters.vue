<template>
  <v-alert type="info" variant="tonal" class="mb-4">
    {{ $t('categories.form.urlFiltersDescription') }}
  </v-alert>

  <v-card variant="outlined" color="success" class="mb-4">
    <v-card-title class="text-subtitle-2 pb-2">
      <v-icon start size="small" color="success">mdi-check-circle</v-icon>
      {{ $t('categories.form.includePatterns') }}
    </v-card-title>
    <v-card-text class="pt-4">
      <v-combobox
        :model-value="formData.url_include_patterns"
        chips
        multiple
        closable-chips
        :hint="$t('categories.form.includeHint')"
        persistent-hint
        variant="outlined"
        :placeholder="$t('categories.form.includePlaceholder')"
        @update:model-value="updateField('url_include_patterns', $event)"
      >
        <template #chip="{ item, props }">
          <v-chip v-bind="props" color="success" variant="tonal">
            <v-icon start size="small">mdi-check</v-icon>
            {{ item.raw }}
          </v-chip>
        </template>
      </v-combobox>
    </v-card-text>
  </v-card>

  <v-card variant="outlined" color="error">
    <v-card-title class="text-subtitle-2 pb-2">
      <v-icon start size="small" color="error">mdi-close-circle</v-icon>
      {{ $t('categories.form.excludePatterns') }}
    </v-card-title>
    <v-card-text class="pt-4">
      <v-combobox
        :model-value="formData.url_exclude_patterns"
        chips
        multiple
        closable-chips
        :hint="$t('categories.form.excludeHint')"
        persistent-hint
        variant="outlined"
        :placeholder="$t('categories.form.excludePlaceholder')"
        @update:model-value="updateField('url_exclude_patterns', $event)"
      >
        <template #chip="{ item, props }">
          <v-chip v-bind="props" color="error" variant="tonal">
            <v-icon start size="small">mdi-close</v-icon>
            {{ item.raw }}
          </v-chip>
        </template>
      </v-combobox>
    </v-card-text>
  </v-card>

  <v-alert
    v-if="!formData.url_include_patterns?.length && !formData.url_exclude_patterns?.length"
    type="warning"
    variant="tonal"
    class="mt-4"
  >
    <v-icon start>mdi-alert</v-icon>
    {{ $t('categories.form.noFiltersWarning') }}
  </v-alert>
</template>

<script setup lang="ts">
import type { CategoryFormData } from '@/composables/useCategoriesView'

export interface CategoryFormFiltersProps {
  formData: CategoryFormData
}

export interface CategoryFormFiltersEmits {
  (e: 'update:formData', data: Partial<CategoryFormData>): void
}

defineProps<CategoryFormFiltersProps>()
const emit = defineEmits<CategoryFormFiltersEmits>()

const updateField = (field: keyof CategoryFormData, value: unknown) => {
  emit('update:formData', { [field]: value })
}
</script>
