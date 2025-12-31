<template>
  <v-alert type="info" variant="tonal" class="mb-4">
    {{ $t('categories.form.searchInfo') }}
  </v-alert>

  <v-combobox
    :model-value="formData.search_terms"
    :label="$t('categories.form.searchTerms')"
    chips
    multiple
    closable-chips
    :hint="$t('categories.form.searchTermsHint')"
    persistent-hint
    variant="outlined"
    @update:model-value="updateField('search_terms', $event)"
  >
    <template #chip="{ item, props }">
      <v-chip v-bind="props" color="primary" variant="tonal">
        <v-icon start size="small">mdi-magnify</v-icon>
        {{ item.raw }}
      </v-chip>
    </template>
  </v-combobox>

  <v-combobox
    :model-value="formData.document_types"
    :label="$t('categories.form.documentTypes')"
    chips
    multiple
    closable-chips
    :hint="$t('categories.form.documentTypesHint')"
    persistent-hint
    variant="outlined"
    class="mt-4"
    @update:model-value="updateField('document_types', $event)"
  >
    <template #chip="{ item, props }">
      <v-chip v-bind="props" color="secondary" variant="tonal">
        <v-icon start size="small">mdi-file-document</v-icon>
        {{ item.raw }}
      </v-chip>
    </template>
  </v-combobox>

  <v-card variant="outlined" class="mt-6">
    <v-card-title class="text-subtitle-2 pb-2">
      <v-icon start size="small">mdi-clock</v-icon>
      {{ $t('categories.form.scheduleTitle') }}
    </v-card-title>
    <v-card-text class="pt-4">
      <ScheduleBuilder
        :model-value="formData.schedule_cron"
        show-advanced
        @update:model-value="updateField('schedule_cron', $event)"
      />

      <v-divider class="my-4" />

      <v-switch
        :model-value="formData.schedule_enabled"
        :label="$t('categories.form.scheduleEnabled')"
        color="success"
        hide-details
        @update:model-value="updateField('schedule_enabled', $event)"
      >
        <template #prepend>
          <v-icon :color="formData.schedule_enabled ? 'success' : 'grey'">
            {{ formData.schedule_enabled ? 'mdi-play-circle' : 'mdi-pause-circle' }}
          </v-icon>
        </template>
      </v-switch>

      <v-alert
        v-if="formData.schedule_enabled"
        type="success"
        variant="tonal"
        density="compact"
        class="mt-3"
      >
        {{ $t('categories.form.scheduleEnabledHint') }}
      </v-alert>
      <v-alert
        v-else
        type="warning"
        variant="tonal"
        density="compact"
        class="mt-3"
      >
        {{ $t('categories.form.scheduleDisabledHint') }}
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import ScheduleBuilder from '@/components/common/ScheduleBuilder.vue'
import type { CategoryFormData } from '@/composables/useCategoriesView'

export interface CategoryFormSearchProps {
  formData: CategoryFormData
}

export interface CategoryFormSearchEmits {
  (e: 'update:formData', data: Partial<CategoryFormData>): void
}

defineProps<CategoryFormSearchProps>()
const emit = defineEmits<CategoryFormSearchEmits>()

const updateField = (field: keyof CategoryFormData, value: unknown) => {
  emit('update:formData', { [field]: value })
}
</script>
