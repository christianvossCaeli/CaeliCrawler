<template>
  <v-dialog v-model="modelValue" max-width="500">
    <v-card>
      <v-card-title>
        <v-icon start>mdi-export</v-icon>
        {{ t('entityDetail.dialog.exportData') }}
      </v-card-title>
      <v-card-text>
        <p class="mb-4">{{ t('entityDetail.dialog.selectExport') }}</p>

        <v-select
          :model-value="format"
          :items="formats"
          item-title="label"
          item-value="value"
          :label="t('entityDetail.dialog.format')"
          variant="outlined"
          class="mb-4"
          @update:model-value="$emit('update:format', $event)"
        ></v-select>

        <v-checkbox
          :model-value="options.facets"
          :label="t('entityDetail.dialog.exportProperties')"
          hide-details
          @update:model-value="updateOption('facets', $event)"
        ></v-checkbox>
        <v-checkbox
          :model-value="options.relations"
          :label="t('entityDetail.dialog.exportRelations')"
          hide-details
          @update:model-value="updateOption('relations', $event)"
        ></v-checkbox>
        <v-checkbox
          :model-value="options.dataSources"
          :label="t('entityDetail.dialog.exportDataSources')"
          hide-details
          @update:model-value="updateOption('dataSources', $event)"
        ></v-checkbox>
        <v-checkbox
          :model-value="options.notes"
          :label="t('entityDetail.dialog.exportNotes')"
          hide-details
          @update:model-value="updateOption('notes', $event)"
        ></v-checkbox>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" @click="modelValue = false">{{ t('common.cancel') }}</v-btn>
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

const modelValue = defineModel<boolean>()

// Props
const props = defineProps<{
  format: string
  options: ExportOptions
  exporting: boolean
}>()

// Emits
const emit = defineEmits<{
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
