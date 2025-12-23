<template>
  <v-dialog v-model="dialogOpen" :max-width="DIALOG_SIZES.SM" persistent>
    <v-card>
      <v-card-title>
        <v-icon start>mdi-bookmark-plus</v-icon>
        {{ $t('sources.aiDiscovery.saveAsTemplate') }}
      </v-card-title>
      <v-card-text>
        <v-text-field
          :model-value="form.name"
          @update:model-value="updateForm('name', $event)"
          :label="$t('common.name')"
          variant="outlined"
          class="mb-3"
        ></v-text-field>
        <v-textarea
          :model-value="form.description"
          @update:model-value="updateForm('description', $event)"
          :label="$t('common.description')"
          variant="outlined"
          rows="2"
          class="mb-3"
        ></v-textarea>
        <v-combobox
          :model-value="form.keywords"
          @update:model-value="updateForm('keywords', $event)"
          :label="$t('sources.aiDiscovery.keywords')"
          variant="outlined"
          chips
          multiple
          closable-chips
          :hint="$t('sources.aiDiscovery.keywordsHint')"
        ></v-combobox>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="dialogOpen = false">
          {{ $t('common.cancel') }}
        </v-btn>
        <v-btn
          color="primary"
          variant="elevated"
          :loading="saving"
          :disabled="!form.name"
          @click="$emit('confirm')"
        >
          {{ $t('common.save') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
/**
 * AiDiscoverySaveTemplateDialog - Dialog for saving API as template
 *
 * Allows users to save a discovered API configuration as a reusable template.
 */
import { DIALOG_SIZES } from '@/config/sources'
import type { TemplateFormData } from './types'

// Props (non-model props only)
interface Props {
  form: TemplateFormData
  saving: boolean
}

const props = defineProps<Props>()

// defineModel() for two-way binding (Vue 3.4+)
const dialogOpen = defineModel<boolean>({ default: false })

// Emits (non-model emits only)
const emit = defineEmits<{
  (e: 'update:form', value: TemplateFormData): void
  (e: 'confirm'): void
}>()

/** Update form field */
const updateForm = <K extends keyof TemplateFormData>(key: K, value: TemplateFormData[K]) => {
  emit('update:form', { ...props.form, [key]: value })
}
</script>
