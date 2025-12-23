<template>
  <v-card variant="outlined" class="mt-4">
    <v-card-title class="text-subtitle-2 pb-2">
      <v-icon start size="small" color="teal">mdi-microsoft-sharepoint</v-icon>
      {{ $t('sources.sharepoint.config') }}
    </v-card-title>
    <v-card-text>
      <!-- Site URL -->
      <v-text-field
        v-model="config.site_url"
        :label="$t('sources.sharepoint.siteUrl')"
        :hint="$t('sources.sharepoint.siteUrlHint')"
        persistent-hint
        variant="outlined"
        prepend-inner-icon="mdi-link"
        placeholder="contoso.sharepoint.com:/sites/Documents"
        :rules="[v => !!v || $t('sources.sharepoint.siteUrlRequired')]"
        @update:model-value="emitUpdate"
      />

      <!-- Drive Name & Folder Path -->
      <v-row class="mt-2">
        <v-col cols="12" md="6">
          <v-text-field
            v-model="config.drive_name"
            :label="$t('sources.sharepoint.driveName')"
            :hint="$t('sources.sharepoint.driveNameHint')"
            persistent-hint
            variant="outlined"
            prepend-inner-icon="mdi-folder"
            placeholder="Shared Documents"
            @update:model-value="emitUpdate"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-text-field
            v-model="config.folder_path"
            :label="$t('sources.sharepoint.folderPath')"
            :hint="$t('sources.sharepoint.folderPathHint')"
            persistent-hint
            variant="outlined"
            prepend-inner-icon="mdi-folder-outline"
            placeholder="/Windprojekte"
            @update:model-value="emitUpdate"
          />
        </v-col>
      </v-row>

      <!-- File Extensions & Max Files -->
      <v-row class="mt-2">
        <v-col cols="12" md="6">
          <v-combobox
            v-model="config.file_extensions"
            :label="$t('sources.sharepoint.fileExtensions')"
            :hint="$t('sources.sharepoint.fileExtensionsHint')"
            persistent-hint
            multiple
            chips
            closable-chips
            variant="outlined"
            prepend-inner-icon="mdi-file-document-multiple"
            @update:model-value="emitUpdateImmediate"
          >
            <template v-slot:chip="{ item, props }">
              <v-chip v-bind="props" color="teal" variant="tonal" size="small">
                {{ item.raw }}
              </v-chip>
            </template>
          </v-combobox>
        </v-col>
        <v-col cols="12" md="6">
          <v-number-input
            v-model="config.max_files"
            :label="$t('sources.sharepoint.maxFiles')"
            :min="1"
            :max="10000"
            variant="outlined"
            prepend-inner-icon="mdi-file-multiple"
            control-variant="stacked"
            @update:model-value="emitUpdateImmediate"
          />
        </v-col>
      </v-row>

      <!-- Recursive Switch -->
      <v-switch
        v-model="config.recursive"
        :label="$t('sources.sharepoint.recursive')"
        color="teal"
        hide-details
        class="mt-2"
        @update:model-value="emitUpdateImmediate"
      />

      <!-- Exclude Patterns -->
      <v-combobox
        v-model="config.exclude_patterns"
        :label="$t('sources.sharepoint.excludePatterns')"
        :hint="$t('sources.sharepoint.excludePatternsHint')"
        persistent-hint
        multiple
        chips
        closable-chips
        variant="outlined"
        prepend-inner-icon="mdi-file-hidden"
        class="mt-4"
        @update:model-value="emitUpdateImmediate"
      >
        <template v-slot:chip="{ item, props }">
          <v-chip v-bind="props" color="grey" variant="tonal" size="small">
            {{ item.raw }}
          </v-chip>
        </template>
      </v-combobox>

      <!-- Specific File Paths (Expandable) -->
      <v-expansion-panels variant="accordion" class="mt-4">
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon start size="small">mdi-file-document-multiple-outline</v-icon>
            {{ $t('sources.sharepoint.filePaths') }}
            <v-chip
              v-if="filePathsCount > 0"
              size="x-small"
              color="teal"
              class="ml-2"
            >
              {{ filePathsCount }}
            </v-chip>
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-textarea
              v-model="config.file_paths_text"
              :hint="$t('sources.sharepoint.filePathsHint')"
              persistent-hint
              variant="outlined"
              rows="4"
              auto-grow
              placeholder="/Dokumente/Report.pdf&#10;/Projekte/Analyse.docx&#10;# Kommentare werden ignoriert"
              @update:model-value="emitUpdate"
            />
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <!-- Connection Test -->
      <v-divider class="my-4" />
      <div class="d-flex align-center gap-3">
        <v-btn
          variant="tonal"
          color="teal"
          :loading="testing"
          :disabled="!config.site_url"
          @click="testConnection"
        >
          <v-icon start>mdi-connection</v-icon>
          {{ $t('sources.sharepoint.testConnection') }}
        </v-btn>
        <v-chip
          v-if="testResult"
          :color="testResult.success ? 'success' : 'error'"
          variant="tonal"
        >
          <v-icon start size="small">
            {{ testResult.success ? 'mdi-check-circle' : 'mdi-alert-circle' }}
          </v-icon>
          {{ testResult.message }}
        </v-chip>
      </div>

      <!-- Test Result Details -->
      <v-expand-transition>
        <v-alert
          v-if="testResult?.details"
          :type="testResult.success ? 'success' : 'warning'"
          variant="tonal"
          class="mt-3"
          density="compact"
        >
          <div class="text-caption">
            <div>
              <strong>{{ $t('sources.sharepoint.authentication') }}:</strong>
              {{ testResult.details.authentication ? '✓' : '✗' }}
            </div>
            <div v-if="testResult.details.target_site_name">
              <strong>{{ $t('sources.sharepoint.site') }}:</strong>
              {{ testResult.details.target_site_name }}
            </div>
            <div v-if="testResult.details.drives?.length">
              <strong>{{ $t('sources.sharepoint.libraries') }}:</strong>
              <v-chip
                v-for="drive in testResult.details.drives"
                :key="drive.id"
                size="x-small"
                class="ml-1"
                variant="outlined"
              >
                {{ drive.name }}
              </v-chip>
            </div>
            <div v-if="testResult.details.errors?.length" class="text-error mt-1">
              <strong>{{ $t('sources.sharepoint.errors') }}:</strong>
              {{ testResult.details.errors.join(', ') }}
            </div>
          </div>
        </v-alert>
      </v-expand-transition>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi } from '@/services/api'
import { SEARCH } from '@/config/sources'
import type { CrawlConfig, SharePointTestResult } from '@/types/sources'

// Props
interface Props {
  modelValue: Partial<CrawlConfig>
}

const props = defineProps<Props>()

// Emits
const emit = defineEmits<{
  (e: 'update:modelValue', value: Partial<CrawlConfig>): void
  (e: 'test-result', result: SharePointTestResult): void
}>()

const { t } = useI18n()

// Default SharePoint config
const defaultConfig: Partial<CrawlConfig> = {
  site_url: '',
  drive_name: '',
  folder_path: '',
  file_extensions: ['.pdf', '.docx', '.doc', '.xlsx', '.pptx'],
  recursive: true,
  exclude_patterns: ['~$*', '*.tmp', '.DS_Store'],
  max_files: 1000,
  file_paths_text: '',
}

// Local config state
const config = ref<Partial<CrawlConfig>>({ ...defaultConfig, ...props.modelValue })

// Watch for external changes
watch(
  () => props.modelValue,
  (newValue) => {
    config.value = { ...defaultConfig, ...newValue }
  },
  { deep: true }
)

// Computed
const filePathsCount = computed(() => {
  if (!config.value.file_paths_text) return 0
  return config.value.file_paths_text.split('\n').filter((l) => l.trim()).length
})

// Test state
const testing = ref(false)
const testResult = ref<SharePointTestResult | null>(null)

// Debounced emit update to prevent excessive parent re-renders
let emitTimeout: ReturnType<typeof setTimeout> | null = null

function emitUpdate() {
  if (emitTimeout) clearTimeout(emitTimeout)
  emitTimeout = setTimeout(() => {
    emit('update:modelValue', { ...config.value })
  }, SEARCH.DEBOUNCE_MS)
}

// Immediate emit for switches and selects (not text inputs)
function emitUpdateImmediate() {
  if (emitTimeout) clearTimeout(emitTimeout)
  emit('update:modelValue', { ...config.value })
}

// Test connection
async function testConnection() {
  if (!config.value.site_url) return

  testing.value = true
  testResult.value = null

  try {
    const response = await adminApi.testSharePointConnection(config.value.site_url)
    const data = response.data

    const success =
      data.authentication && (data.target_site_accessible || !config.value.site_url)

    testResult.value = {
      success,
      message: success
        ? t('sources.sharepoint.connectionSuccess')
        : t('sources.sharepoint.connectionFailed'),
      details: {
        authentication: data.authentication,
        sites_found: data.sites_found,
        target_site_accessible: data.target_site_accessible,
        target_site_name: data.target_site_name,
        drives: data.drives,
        errors: data.errors,
      },
    }

    // Auto-fill drive_name if only one drive and none selected
    if (success && data.drives?.length === 1 && !config.value.drive_name) {
      config.value.drive_name = data.drives[0].name
      emitUpdate()
    }

    emit('test-result', testResult.value)
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } } }
    testResult.value = {
      success: false,
      message: err.response?.data?.detail || t('sources.sharepoint.connectionError'),
    }
    emit('test-result', testResult.value)
  } finally {
    testing.value = false
  }
}

// Reset test result when site_url changes
watch(
  () => config.value.site_url,
  () => {
    testResult.value = null
  }
)
</script>
