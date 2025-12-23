<template>
  <v-dialog v-model="dialogOpen" :max-width="DIALOG_SIZES.LG" persistent scrollable>
    <v-card>
      <v-card-title class="d-flex align-center pa-4 bg-secondary">
        <v-avatar color="secondary-darken-1" size="40" class="mr-3">
          <v-icon color="on-secondary">mdi-upload-multiple</v-icon>
        </v-avatar>
        <div>
          <div class="text-h6">{{ $t('sources.dialog.bulkImport') }}</div>
          <div class="text-caption opacity-80">CSV-Format: Name;URL;SourceType;Tags</div>
        </div>
      </v-card-title>

      <v-card-text class="pa-6">
        <!-- Categories Selection (N:M) -->
        <v-card variant="outlined" class="mb-4">
          <v-card-title class="text-subtitle-2 pb-2">
            <v-icon start size="small">mdi-folder-multiple</v-icon>
            {{ $t('sources.form.categories') }}
          </v-card-title>
          <v-card-text>
            <v-select
              v-model="bulkImport.category_ids"
              :items="categories"
              item-title="name"
              item-value="id"
              multiple
              chips
              closable-chips
              variant="outlined"
              density="comfortable"
              :rules="[v => v.length > 0 || $t('common.required')]"
            >
              <template v-slot:chip="{ item, index }">
                <v-chip
                  :color="index === 0 ? 'primary' : 'default'"
                  closable
                  @click:close="bulkImport.category_ids.splice(index, 1)"
                >
                  {{ item.title }}
                  <v-icon v-if="index === 0" end size="x-small">mdi-star</v-icon>
                </v-chip>
              </template>
            </v-select>
          </v-card-text>
        </v-card>

        <!-- Default Tags -->
        <v-card variant="outlined" class="mb-4">
          <v-card-title class="text-subtitle-2 pb-2">
            <v-icon start size="small">mdi-tag-multiple</v-icon>
            {{ $t('sources.bulk.defaultTags') }}
          </v-card-title>
          <v-card-text>
            <v-combobox
              v-model="bulkImport.default_tags"
              :items="tagSuggestions"
              :label="$t('sources.bulk.defaultTagsHint')"
              multiple
              chips
              closable-chips
              variant="outlined"
              density="comfortable"
              prepend-inner-icon="mdi-tag"
            >
              <template #chip="{ props, item }">
                <v-chip
                  v-bind="props"
                  :color="getTagColor(item.value)"
                  size="small"
                >
                  {{ item.value }}
                </v-chip>
              </template>
            </v-combobox>
          </v-card-text>
        </v-card>

        <!-- CSV Input -->
        <v-card variant="outlined" class="mb-4">
          <v-card-title class="text-subtitle-2 pb-2">
            <v-icon start size="small">mdi-file-delimited</v-icon>
            {{ $t('sources.bulk.csvData') }}
          </v-card-title>
          <v-card-text>
            <v-radio-group v-model="bulkImport.inputMode" inline class="mb-3">
              <v-radio :label="$t('sources.bulk.csvText')" value="text" />
              <v-radio :label="$t('sources.bulk.csvFile')" value="file" />
            </v-radio-group>

            <v-textarea
              v-if="bulkImport.inputMode === 'text'"
              v-model="bulkImport.csvText"
              :label="$t('sources.bulk.csvFormat')"
              :placeholder="'Aachen;https://www.aachen.de;WEBSITE;stadt,nrw\nBielefeld;https://www.bielefeld.de;WEBSITE;stadt,nrw'"
              rows="8"
              variant="outlined"
              font-family="monospace"
              :hint="$t('sources.bulk.csvFormatHint')"
              persistent-hint
            />

            <v-file-input
              v-else
              v-model="csvFile"
              accept=".csv,.txt"
              :label="$t('sources.bulk.csvFileUpload')"
              variant="outlined"
              prepend-icon="mdi-file-upload"
              @update:model-value="onCsvFileSelected"
            />
          </v-card-text>
        </v-card>

        <!-- CSV Validation Error -->
        <v-alert
          v-if="csvValidationError"
          type="error"
          variant="tonal"
          class="mb-4"
          closable
          @click:close="csvValidationError = null"
        >
          <v-icon start>mdi-alert-circle</v-icon>
          {{ csvValidationError }}
        </v-alert>

        <!-- Preview Button -->
        <div class="d-flex justify-center mb-4">
          <v-btn
            variant="tonal"
            color="info"
            @click="parsePreview"
            :disabled="!canPreview"
          >
            <v-icon start>mdi-eye</v-icon>
            {{ $t('sources.bulk.loadPreview') }}
          </v-btn>
        </div>

        <!-- Preview Table -->
        <v-card v-if="bulkImport.preview.length > 0" variant="outlined">
          <v-card-title class="text-subtitle-2 pb-2 d-flex justify-space-between align-center">
            <span>
              <v-icon start size="small">mdi-table</v-icon>
              {{ $t('sources.bulk.preview') }} ({{ bulkImport.preview.length }} {{ $t('sources.bulk.entries') }})
            </span>
            <span class="text-caption">
              <v-chip size="x-small" color="success" class="mr-1">
                {{ bulkImport.validCount }} {{ $t('sources.bulk.valid') }}
              </v-chip>
              <v-chip
                v-if="bulkImport.duplicateCount > 0"
                size="x-small"
                color="warning"
                class="mr-1"
              >
                {{ bulkImport.duplicateCount }} {{ $t('sources.bulk.duplicates') }}
              </v-chip>
              <v-chip v-if="bulkImport.errorCount > 0" size="x-small" color="error">
                {{ bulkImport.errorCount }} {{ $t('sources.bulk.errors') }}
              </v-chip>
            </span>
          </v-card-title>
          <v-card-text class="pa-0">
            <v-table density="compact" class="preview-table">
              <thead>
                <tr>
                  <th style="width: 40px;"></th>
                  <th>{{ $t('sources.columns.name') }}</th>
                  <th>{{ $t('sources.columns.url') }}</th>
                  <th>{{ $t('sources.columns.type') }}</th>
                  <th>{{ $t('sources.form.tags') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(item, idx) in displayedPreview"
                  :key="idx"
                  :class="{ 'bg-error-lighten-5': item.error, 'bg-warning-lighten-5': item.duplicate }"
                >
                  <td>
                    <v-icon v-if="item.error" color="error" size="small">mdi-alert-circle</v-icon>
                    <v-icon v-else-if="item.duplicate" color="warning" size="small">mdi-content-duplicate</v-icon>
                    <v-icon v-else color="success" size="small">mdi-check-circle</v-icon>
                  </td>
                  <td class="text-truncate" style="max-width: 200px;">{{ item.name }}</td>
                  <td class="text-truncate text-caption" style="max-width: 250px;">{{ item.base_url }}</td>
                  <td>
                    <v-chip size="x-small" :color="getTypeColor(item.source_type)">
                      {{ item.source_type }}
                    </v-chip>
                  </td>
                  <td>
                    <v-chip
                      v-for="tag in item.allTags.slice(0, 3)"
                      :key="tag"
                      size="x-small"
                      :color="getTagColor(tag)"
                      class="mr-1"
                    >
                      {{ tag }}
                    </v-chip>
                    <span v-if="item.allTags.length > 3" class="text-caption">
                      +{{ item.allTags.length - 3 }}
                    </span>
                  </td>
                </tr>
                <tr v-if="hiddenPreviewCount > 0">
                  <td colspan="5" class="text-center text-caption">
                    ... {{ hiddenPreviewCount }} {{ $t('sources.bulk.moreEntries') }}
                  </td>
                </tr>
              </tbody>
            </v-table>
          </v-card-text>
        </v-card>

        <!-- Options -->
        <v-switch
          v-model="bulkImport.skip_duplicates"
          :label="$t('sources.form.skipDuplicates')"
          color="primary"
          class="mt-4"
        />
      </v-card-text>

      <v-divider />

      <v-card-actions class="pa-4">
        <v-btn variant="tonal" @click="close">{{ $t('common.cancel') }}</v-btn>
        <v-spacer />
        <v-btn
          variant="tonal"
          color="primary"
          @click="executeImport"
          :disabled="!canImport"
          :loading="bulkImport.importing"
        >
          <v-icon start>mdi-upload</v-icon>
          {{ bulkImport.validCount }} {{ $t('sources.bulk.sourcesImport') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSourceHelpers } from '@/composables/useSourceHelpers'
import { useLogger } from '@/composables/useLogger'
import type { BulkImportState } from '@/types/sources'
import type { CategoryResponse } from '@/types/category'
import { BULK_IMPORT, DIALOG_SIZES } from '@/config/sources'
import { parseCsv, validateCsvInput } from '@/utils/csvParser'

const logger = useLogger('BulkImportDialog')

// Props (non-model props only)
interface Props {
  categories: CategoryResponse[]
  tagSuggestions: string[]
  existingUrls: string[]
}

const props = defineProps<Props>()

// defineModel() for two-way binding (Vue 3.4+)
const dialogOpen = defineModel<boolean>({ default: false })

// Emits (non-model emits only)
const emit = defineEmits<{
  (e: 'import', data: BulkImportState): void
}>()

const { t } = useI18n()
const { getTypeColor, getTagColor } = useSourceHelpers()

// Bulk import state
const bulkImport = ref<BulkImportState>({
  category_ids: [],
  default_tags: [],
  inputMode: 'text',
  csvText: '',
  csvFile: null,
  preview: [],
  validCount: 0,
  duplicateCount: 0,
  errorCount: 0,
  importing: false,
  skip_duplicates: true,
})

const csvFile = ref<File | File[] | null>(null)
const csvValidationError = ref<string | null>(null)

// Computed
const canPreview = computed(() => {
  if (bulkImport.value.inputMode === 'text') {
    return bulkImport.value.csvText.trim().length > 0
  }
  return csvFile.value !== null
})

const canImport = computed(() => {
  return bulkImport.value.category_ids.length > 0 && bulkImport.value.validCount > 0
})

// Preview display with configurable limit
const displayedPreview = computed(() =>
  bulkImport.value.preview.slice(0, BULK_IMPORT.PREVIEW_DISPLAY_LIMIT)
)

const hiddenPreviewCount = computed(() =>
  Math.max(0, bulkImport.value.preview.length - BULK_IMPORT.PREVIEW_DISPLAY_LIMIT)
)

// Parse CSV file when selected
async function onCsvFileSelected(files: File | File[] | null) {
  if (!files) return
  const file = Array.isArray(files) ? files[0] : files
  if (!file) return

  // Validate file size BEFORE reading to prevent browser freeze
  if (file.size > BULK_IMPORT.MAX_FILE_SIZE) {
    const maxSizeMB = Math.round(BULK_IMPORT.MAX_FILE_SIZE / 1024 / 1024)
    const fileSizeMB = (file.size / 1024 / 1024).toFixed(2)
    csvValidationError.value = t('sources.bulk.fileTooLarge', { size: fileSizeMB, max: maxSizeMB })
    bulkImport.value.preview = []
    bulkImport.value.validCount = 0
    bulkImport.value.duplicateCount = 0
    bulkImport.value.errorCount = 1
    return
  }

  try {
    const text = await file.text()
    bulkImport.value.csvText = text
    bulkImport.value.csvFile = file
    parsePreview()
  } catch (error) {
    logger.error('Failed to read CSV file', error)
    csvValidationError.value = t('sources.bulk.readError')
  }
}

// Parse CSV and create preview using consolidated parser
function parsePreview() {
  const text = bulkImport.value.csvText
  csvValidationError.value = null

  if (!text.trim()) {
    bulkImport.value.preview = []
    bulkImport.value.validCount = 0
    bulkImport.value.duplicateCount = 0
    bulkImport.value.errorCount = 0
    return
  }

  // Validate input first
  const validation = validateCsvInput(text)
  if (!validation.valid) {
    csvValidationError.value = validation.error || t('sources.bulk.csvTooLarge', {
      size: Math.round(BULK_IMPORT.MAX_FILE_SIZE / 1024 / 1024),
    })
    bulkImport.value.preview = []
    bulkImport.value.validCount = 0
    bulkImport.value.duplicateCount = 0
    bulkImport.value.errorCount = 1
    return
  }

  // Parse CSV using consolidated parser
  const result = parseCsv(text, {
    defaultTags: bulkImport.value.default_tags,
    existingUrls: props.existingUrls,
    skipDuplicates: bulkImport.value.skip_duplicates,
  })

  if (result.error) {
    csvValidationError.value = result.error
    bulkImport.value.preview = []
    bulkImport.value.validCount = 0
    bulkImport.value.duplicateCount = 0
    bulkImport.value.errorCount = 1
    return
  }

  bulkImport.value.preview = result.items
  bulkImport.value.validCount = result.validCount
  bulkImport.value.duplicateCount = result.duplicateCount
  bulkImport.value.errorCount = result.errorCount
}

// Execute import
function executeImport() {
  if (!canImport.value) return
  emit('import', { ...bulkImport.value })
}

// Close dialog
function close() {
  dialogOpen.value = false
}

// Reset state when dialog opens
watch(dialogOpen, (open) => {
  if (open) {
    bulkImport.value = {
      category_ids: [],
      default_tags: [],
      inputMode: 'text',
      csvText: '',
      csvFile: null,
      preview: [],
      validCount: 0,
      duplicateCount: 0,
      errorCount: 0,
      importing: false,
      skip_duplicates: true,
    }
    csvFile.value = null
  }
})
</script>

<style scoped>
.preview-table {
  font-size: 0.85rem;
}
</style>
