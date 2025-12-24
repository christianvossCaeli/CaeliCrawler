<template>
  <v-dialog :model-value="modelValue" max-width="500" @update:model-value="$emit('update:modelValue', $event)">
    <v-card>
      <v-card-title>
        <v-icon start>mdi-export</v-icon>
        {{ t('entityDetail.dialog.exportData') }}
      </v-card-title>
      <v-card-text>
        <p class="mb-4">{{ t('entityDetail.dialog.selectExport') }}</p>

        <v-select
          :model-value="format"
          @update:model-value="$emit('update:format', $event)"
          :items="formats"
          item-title="label"
          item-value="value"
          :label="t('entityDetail.dialog.format')"
          variant="outlined"
          class="mb-4"
        ></v-select>

        <v-checkbox
          :model-value="options.facets"
          @update:model-value="updateOption('facets', $event)"
          :label="t('entityDetail.dialog.exportProperties')"
          hide-details
        ></v-checkbox>
        <v-checkbox
          :model-value="options.relations"
          @update:model-value="updateOption('relations', $event)"
          :label="t('entityDetail.dialog.exportRelations')"
          hide-details
        ></v-checkbox>
        <v-checkbox
          :model-value="options.dataSources"
          @update:model-value="updateOption('dataSources', $event)"
          :label="t('entityDetail.dialog.exportDataSources')"
          hide-details
        ></v-checkbox>
        <v-checkbox
          :model-value="options.notes"
          @update:model-value="updateOption('notes', $event)"
          :label="t('entityDetail.dialog.exportNotes')"
          hide-details
        ></v-checkbox>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" @click="$emit('update:modelValue', false)">{{ t('common.cancel') }}</v-btn>
        <v-btn variant="tonal" color="primary" :loading="exporting" @click="$emit('export')">
          <v-icon start>mdi-download</v-icon>
          {{ t('common.export') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

// Types
interface ExportOptions {
  facets: boolean
  relations: boolean
  dataSources: boolean
  notes: boolean
}

interface ExportFormat {
  label: string
  value: string
}

// Props
const props = defineProps<{
  modelValue: boolean
  format: string
  options: ExportOptions
  exporting: boolean
}>()

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'update:format': [value: string]
  'update:options': [value: ExportOptions]
  export: []
}>()

const { t } = useI18n()

// Computed
const formats = computed<ExportFormat[]>(() => [
  { label: t('entityDetail.formats.csvExcel'), value: 'csv' },
  { label: t('entityDetail.formats.json'), value: 'json' },
  { label: t('entityDetail.formats.pdfReport'), value: 'pdf' },
])

// Methods
function updateOption(key: keyof ExportOptions, value: boolean | null) {
  emit('update:options', { ...props.options, [key]: value ?? false })
}
</script>
