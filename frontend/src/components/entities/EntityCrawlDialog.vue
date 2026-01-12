<template>
  <v-dialog
    :model-value="modelValue"
    max-width="700"
    persistent
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon icon="mdi-sync" class="mr-2" />
        {{ t('entities.crawlDialog.title') }}
      </v-card-title>

      <v-card-text>
        <!-- Selected Entities Summary -->
        <v-alert
          type="info"
          variant="tonal"
          density="compact"
          class="mb-4"
        >
          <strong>{{ selectedEntities.length }}</strong>
          {{ t('entities.crawlDialog.entitiesSelected') }}
        </v-alert>

        <!-- Category Selection -->
        <v-select
          v-model="selectedCategory"
          :items="categories"
          item-title="name"
          item-value="id"
          :label="t('entities.crawlDialog.selectCategory')"
          :rules="[v => !!v || t('entities.crawlDialog.categoryRequired')]"
          :loading="loadingCategories"
          prepend-icon="mdi-folder-outline"
          class="mb-4"
          @update:model-value="loadPreview"
        />

        <!-- Preview -->
        <v-expand-transition>
          <v-alert
            v-if="loadingPreview"
            type="info"
            variant="tonal"
            density="compact"
            class="mb-4"
          >
            <v-progress-circular indeterminate size="16" class="mr-2" />
            {{ t('common.loading') }}
          </v-alert>
          <v-alert
            v-else-if="preview"
            :type="preview.sources_count > 0 ? 'success' : 'warning'"
            variant="tonal"
            density="compact"
            class="mb-4"
          >
            <template v-if="preview.sources_count > 0">
              <strong>{{ preview.sources_count }}</strong>
              {{ t('entities.crawlDialog.sourcesFound') }}
              <template v-if="preview.entities_without_sources > 0">
                <br />
                <small class="text-warning">
                  {{ t('entities.crawlDialog.entitiesWithoutSources', { count: preview.entities_without_sources }) }}
                </small>
              </template>
            </template>
            <template v-else>
              {{ t('entities.crawlDialog.noSourcesFound') }}
            </template>
          </v-alert>
        </v-expand-transition>
      </v-card-text>

      <v-card-actions class="px-4 pb-4">
        <v-btn
          variant="outlined"
          color="primary"
          prepend-icon="mdi-content-save-cog"
          :disabled="!selectedCategory || loadingPreview"
          @click="openPresetEditor"
        >
          {{ t('entities.crawlDialog.saveAsPreset') }}
        </v-btn>
        <v-spacer />
        <v-btn
          variant="text"
          @click="close"
        >
          {{ t('common.cancel') }}
        </v-btn>
        <v-btn
          color="primary"
          variant="elevated"
          :loading="loading"
          :disabled="!selectedCategory || loadingPreview"
          @click="executeCrawl"
        >
          <v-icon icon="mdi-sync" class="mr-1" />
          {{ t('entities.crawlDialog.startCrawl') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  previewEntitySources,
  startEntityCrawl,
  type EntityCrawlPreviewResponse,
} from '@/services/api/admin'
import { useSnackbar } from '@/composables/useSnackbar'
import { getErrorMessage } from '@/utils/errorMessage'
import type { Entity } from '@/types/entity'

interface Category {
  id: string
  name: string
}

const props = defineProps<{
  modelValue: boolean
  selectedEntities: Entity[]
  categories: Category[]
  loadingCategories?: boolean
}>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'crawl-started': [result: { jobsCreated: number; message: string }]
  'open-preset-editor': [data: { entityIds: string[]; categoryId: string }]
}>()
const { t } = useI18n()
const { showSuccess, showError } = useSnackbar()

// State
const selectedCategory = ref<string | null>(null)
const loading = ref(false)
const preview = ref<EntityCrawlPreviewResponse | null>(null)
const loadingPreview = ref(false)

// Load preview when category changes
async function loadPreview() {
  if (!selectedCategory.value || props.selectedEntities.length === 0) {
    preview.value = null
    return
  }

  loadingPreview.value = true
  try {
    const response = await previewEntitySources({
      entity_ids: props.selectedEntities.map(e => e.id),
      category_id: selectedCategory.value,
    })
    preview.value = response.data
  } catch (error) {
    console.error('Failed to load preview:', error)
    showError(getErrorMessage(error) || t('entities.crawlDialog.error'))
    preview.value = null
  } finally {
    loadingPreview.value = false
  }
}

async function executeCrawl() {
  if (!selectedCategory.value) return

  loading.value = true
  try {
    const response = await startEntityCrawl({
      entity_ids: props.selectedEntities.map(e => e.id),
      category_id: selectedCategory.value,
      save_as_preset: false,
    })

    showSuccess(response.data.message)
    emit('crawl-started', {
      jobsCreated: response.data.jobs_created,
      message: response.data.message,
    })
    close()
  } catch (error: unknown) {
    showError(getErrorMessage(error) || t('entities.crawlDialog.error'))
  } finally {
    loading.value = false
  }
}

function openPresetEditor() {
  if (!selectedCategory.value) return
  emit('open-preset-editor', {
    entityIds: props.selectedEntities.map(e => e.id),
    categoryId: selectedCategory.value,
  })
  close()
}

function close() {
  emit('update:modelValue', false)
}

// Reset form when dialog opens
watch(() => props.modelValue, (isOpen) => {
  if (isOpen) {
    selectedCategory.value = null
    preview.value = null
  }
})
</script>
