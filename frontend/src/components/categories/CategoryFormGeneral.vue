<template>
  <v-row>
    <v-col cols="12" md="6">
      <v-text-field
        :model-value="formData.name"
        :label="$t('categories.form.name')"
        required
        :rules="[v => !!v || $t('categories.form.nameRequired')]"
        variant="outlined"
        prepend-inner-icon="mdi-folder"
        @update:model-value="updateField('name', $event)"
      />
    </v-col>
    <v-col cols="12" md="6">
      <v-card variant="outlined" class="pa-3 h-100 d-flex align-center justify-space-between">
        <div>
          <div class="text-body-2 font-weight-medium">{{ $t('categories.form.enabled') }}</div>
          <div class="text-caption text-medium-emphasis">{{ $t('categories.form.enabledHint') }}</div>
        </div>
        <v-switch
          :model-value="formData.is_active"
          color="success"
          hide-details
          @update:model-value="updateField('is_active', $event)"
        />
      </v-card>
    </v-col>
  </v-row>

  <v-textarea
    :model-value="formData.description"
    :label="$t('categories.form.description')"
    rows="2"
    variant="outlined"
    @update:model-value="updateField('description', $event)"
  />

  <v-textarea
    :model-value="formData.purpose"
    :label="$t('categories.form.purpose')"
    required
    rows="3"
    :rules="[v => !!v || $t('categories.form.purposeRequired')]"
    variant="outlined"
    :hint="$t('categories.form.purposeHint')"
    persistent-hint
    @update:model-value="updateField('purpose', $event)"
  />

  <v-card variant="outlined" class="mt-4">
    <v-card-title class="text-subtitle-2 pb-2">
      <v-icon start size="small">mdi-translate</v-icon>
      {{ $t('categories.form.languages') }}
    </v-card-title>
    <v-card-text>
      <p class="text-caption text-medium-emphasis mb-3">
        {{ $t('categories.form.languagesDescription') }}
      </p>
      <v-select
        :model-value="formData.languages"
        :items="availableLanguages"
        item-title="name"
        item-value="code"
        chips
        multiple
        closable-chips
        variant="outlined"
        :hint="$t('categories.form.languagesHint')"
        persistent-hint
        @update:model-value="updateField('languages', $event)"
      >
        <template #chip="{ item, props }">
          <v-chip v-bind="props" color="primary" variant="outlined">
            <span class="mr-1">{{ item.raw.flag }}</span>
            {{ item.raw.name }}
          </v-chip>
        </template>
        <template #item="{ item, props }">
          <v-list-item v-bind="props">
            <template #prepend>
              <span class="mr-2 text-h6">{{ item.raw.flag }}</span>
            </template>
          </v-list-item>
        </template>
      </v-select>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import type { CategoryFormData } from '@/composables/useCategoriesView'

export interface CategoryFormGeneralProps {
  formData: CategoryFormData
  availableLanguages: Array<{ code: string; name: string; flag: string }>
}

export interface CategoryFormGeneralEmits {
  (e: 'update:formData', data: Partial<CategoryFormData>): void
}

const props = defineProps<CategoryFormGeneralProps>()
const emit = defineEmits<CategoryFormGeneralEmits>()

const updateField = (field: keyof CategoryFormData, value: any) => {
  emit('update:formData', { [field]: value })
}
</script>
