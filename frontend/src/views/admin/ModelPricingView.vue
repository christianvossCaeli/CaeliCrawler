<template>
  <v-container fluid>
    <!-- Header -->
    <PageHeader
      :title="t('admin.modelPricing.title')"
      :subtitle="t('admin.modelPricing.subtitle')"
      icon="mdi-currency-usd"
    >
      <template #actions>
        <v-btn variant="tonal" :loading="loading" @click="loadPricing">
          <v-icon start>mdi-refresh</v-icon>
          {{ t('common.refresh') }}
        </v-btn>
        <v-btn
          variant="tonal"
          color="info"
          :loading="syncing"
          @click="syncPrices"
        >
          <v-icon start>mdi-cloud-sync</v-icon>
          {{ t('admin.modelPricing.actions.syncAll') }}
        </v-btn>
        <v-btn
          variant="tonal"
          color="purple"
          :loading="syncingLiteLLM"
          @click="syncLiteLLM"
        >
          <v-icon start>mdi-database-sync</v-icon>
          {{ t('admin.modelPricing.actions.syncLiteLLM') }}
          <v-tooltip activator="parent" location="bottom">
            {{ t('admin.modelPricing.actions.syncLiteLLMTooltip') }}
          </v-tooltip>
        </v-btn>
        <v-btn
          variant="flat"
          color="primary"
          @click="openAddDialog"
        >
          <v-icon start>mdi-plus</v-icon>
          {{ t('admin.modelPricing.actions.add') }}
        </v-btn>
      </template>
    </PageHeader>

    <!-- Info Alert -->
    <v-alert type="info" variant="tonal" class="mb-4">
      <div class="d-flex align-center">
        <v-icon start>mdi-information-outline</v-icon>
        <div>
          <strong>{{ t('admin.modelPricing.info.title') }}</strong>
          <br>
          {{ t('admin.modelPricing.info.description') }}
        </div>
      </div>
    </v-alert>

    <!-- Stale Warning -->
    <v-alert
      v-if="staleCount > 0"
      type="warning"
      variant="tonal"
      class="mb-4"
      closable
    >
      <v-icon start>mdi-alert</v-icon>
      {{ t('admin.modelPricing.messages.staleWarning', { count: staleCount }) }}
    </v-alert>

    <!-- Error Alert -->
    <v-alert
      v-if="error"
      type="error"
      variant="tonal"
      class="mb-4"
      closable
      @click:close="error = null"
    >
      {{ error }}
    </v-alert>

    <!-- Statistics Cards -->
    <ModelPricingStatsCards
      :total-count="totalCount"
      :azure-count="azureCount"
      :openai-count="openaiCount"
      :anthropic-count="anthropicCount"
      :stale-count="staleCount"
    />

    <!-- Filters -->
    <ModelPricingFilters
      v-model:provider="filterProvider"
      v-model:include-deprecated="includeDeprecated"
      :show-seed-button="totalCount === 0"
      :seeding="seeding"
      @seed="seedDefaults"
    />

    <!-- Official URLs -->
    <v-expansion-panels class="mb-4" variant="accordion">
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon start>mdi-link-variant</v-icon>
          {{ t('admin.modelPricing.officialUrls.title') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <p class="text-caption text-medium-emphasis mb-2">
            {{ t('admin.modelPricing.officialUrls.hint') }}
          </p>
          <v-list density="compact">
            <v-list-item
              v-for="(url, provider) in officialUrls"
              :key="provider"
              :href="url"
              target="_blank"
              class="px-0"
            >
              <template #prepend>
                <v-icon :icon="getProviderIcon(provider)" size="small" class="mr-2" />
              </template>
              <v-list-item-title>{{ getProviderLabel(provider) }}</v-list-item-title>
              <v-list-item-subtitle>{{ url }}</v-list-item-subtitle>
              <template #append>
                <v-icon size="small">mdi-open-in-new</v-icon>
              </template>
            </v-list-item>
          </v-list>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <!-- Pricing Table -->
    <ModelPricingTable
      :entries="filteredEntries"
      :loading="loading"
      @edit="openEditDialog"
      @delete="confirmDelete"
    />

    <!-- Add/Edit Dialog -->
    <ModelPricingFormDialog
      v-model="dialogOpen"
      :editing-id="editingId"
      :initial-data="form"
      :saving="saving"
      @submit="saveEntry"
    />

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialogOpen" max-width="400">
      <v-card>
        <v-card-title>{{ t('admin.modelPricing.dialog.deleteTitle') }}</v-card-title>
        <v-card-text>
          {{ t('admin.modelPricing.dialog.deleteConfirm') }}
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="deleteDialogOpen = false">
            {{ t('common.cancel') }}
          </v-btn>
          <v-btn
            color="error"
            variant="flat"
            :loading="deleting"
            @click="deleteEntry"
          >
            {{ t('common.delete') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSnackbar } from '@/composables/useSnackbar'
import { useLogger } from '@/composables/useLogger'
import PageHeader from '@/components/common/PageHeader.vue'
import {
  ModelPricingStatsCards,
  ModelPricingFilters,
  ModelPricingTable,
  ModelPricingFormDialog,
  type PricingFormData,
} from '@/components/admin/model-pricing'
import {
  getModelPricing,
  createModelPricing,
  updateModelPricing,
  deleteModelPricing,
  syncAllPrices,
  syncLiteLLMPrices,
  seedModelPricing,
  type PricingEntry,
  type PricingListResponse,
  type SyncAllResultResponse,
  type SyncResultResponse,
} from '@/services/api/admin'
import {
  getProviderIcon,
  getProviderLabel,
} from '@/utils/llmProviders'

const { t } = useI18n()
const { showSuccess, showError } = useSnackbar()
const logger = useLogger('ModelPricingView')

// State
const loading = ref(false)
const syncing = ref(false)
const syncingLiteLLM = ref(false)
const seeding = ref(false)
const saving = ref(false)
const deleting = ref(false)
const error = ref<string | null>(null)

const entries = ref<PricingEntry[]>([])
const totalCount = ref(0)
const staleCount = ref(0)
const officialUrls = ref<Record<string, string>>({})

// Filters
const filterProvider = ref<string | null>(null)
const includeDeprecated = ref(false)

// Dialog state
const dialogOpen = ref(false)
const deleteDialogOpen = ref(false)
const editingId = ref<string | null>(null)
const deletingEntry = ref<PricingEntry | null>(null)

const form = ref<PricingFormData>({
  provider: '',
  model_name: '',
  display_name: '',
  input_price_per_1m: 0,
  output_price_per_1m: 0,
  cached_input_price_per_1m: undefined,
  source_url: '',
  notes: '',
})

// Computed
const filteredEntries = computed(() => {
  let result = entries.value
  if (filterProvider.value) {
    result = result.filter(e => e.provider === filterProvider.value)
  }
  if (!includeDeprecated.value) {
    result = result.filter(e => !e.is_deprecated)
  }
  return result
})

const azureCount = computed(() =>
  entries.value.filter(e => e.provider === 'azure_openai' && !e.is_deprecated).length
)
const openaiCount = computed(() =>
  entries.value.filter(e => e.provider === 'openai' && !e.is_deprecated).length
)
const anthropicCount = computed(() =>
  entries.value.filter(e => e.provider === 'anthropic' && !e.is_deprecated).length
)

// API functions
async function loadPricing() {
  loading.value = true
  error.value = null

  try {
    const response = await getModelPricing({ include_deprecated: true })
    const data = response.data as PricingListResponse
    entries.value = data.entries
    totalCount.value = data.total
    staleCount.value = data.stale_count
    officialUrls.value = data.official_urls
  } catch (err) {
    error.value = t('admin.modelPricing.messages.loadError')
    logger.error('Failed to load pricing', { error: err })
  } finally {
    loading.value = false
  }
}

async function syncPrices() {
  syncing.value = true

  try {
    const response = await syncAllPrices()
    const result = response.data as SyncAllResultResponse

    if (result.success || result.total_updated > 0) {
      showSuccess(t('admin.modelPricing.messages.syncSuccess', {
        updated: result.total_updated,
        added: result.total_added,
      }))
      await loadPricing()
    } else if (result.total_errors > 0) {
      showError(t('admin.modelPricing.messages.syncPartialFailed', {
        errors: result.total_errors,
      }))
      await loadPricing()
    } else {
      showError(t('admin.modelPricing.messages.syncFailed'))
    }
  } catch (err) {
    showError(t('admin.modelPricing.messages.syncFailed'))
    logger.error('Sync failed', { error: err })
  } finally {
    syncing.value = false
  }
}

async function syncLiteLLM() {
  syncingLiteLLM.value = true

  try {
    const response = await syncLiteLLMPrices()
    const result = response.data as SyncResultResponse

    if (result.success) {
      showSuccess(t('admin.modelPricing.messages.litellmSuccess', {
        updated: result.updated,
        added: result.added,
      }))
      await loadPricing()
    } else if (result.errors.length > 0) {
      showError(t('admin.modelPricing.messages.litellmPartialFailed', {
        errors: result.errors.length,
      }))
      await loadPricing()
    } else {
      showError(t('admin.modelPricing.messages.litellmFailed'))
    }
  } catch (err) {
    showError(t('admin.modelPricing.messages.litellmFailed'))
    logger.error('LiteLLM sync failed', { error: err })
  } finally {
    syncingLiteLLM.value = false
  }
}

async function seedDefaults() {
  seeding.value = true

  try {
    const response = await seedModelPricing()
    const result = response.data

    if (result.count > 0) {
      showSuccess(t('admin.modelPricing.messages.seeded', { count: result.count }))
      await loadPricing()
    } else {
      showSuccess(t('admin.modelPricing.messages.alreadySeeded'))
    }
  } catch (err) {
    showError(t('admin.modelPricing.messages.seedFailed'))
    logger.error('Seeding failed', { error: err })
  } finally {
    seeding.value = false
  }
}

function openAddDialog() {
  editingId.value = null
  form.value = {
    provider: '',
    model_name: '',
    display_name: '',
    input_price_per_1m: 0,
    output_price_per_1m: 0,
    cached_input_price_per_1m: undefined,
    source_url: '',
    notes: '',
  }
  dialogOpen.value = true
}

function openEditDialog(entry: PricingEntry) {
  editingId.value = entry.id
  form.value = {
    provider: entry.provider,
    model_name: entry.model_name,
    display_name: entry.display_name || '',
    input_price_per_1m: entry.input_price_per_1m,
    output_price_per_1m: entry.output_price_per_1m,
    cached_input_price_per_1m: entry.cached_input_price_per_1m || undefined,
    source_url: entry.source_url || '',
    notes: entry.notes || '',
  }
  dialogOpen.value = true
}

async function saveEntry(data: PricingFormData) {
  saving.value = true

  try {
    if (editingId.value) {
      await updateModelPricing(editingId.value, {
        input_price_per_1m: data.input_price_per_1m,
        output_price_per_1m: data.output_price_per_1m,
        cached_input_price_per_1m: data.cached_input_price_per_1m,
        display_name: data.display_name || undefined,
        notes: data.notes || undefined,
      })
      showSuccess(t('admin.modelPricing.messages.updated'))
    } else {
      await createModelPricing({
        provider: data.provider,
        model_name: data.model_name,
        display_name: data.display_name || undefined,
        input_price_per_1m: data.input_price_per_1m,
        output_price_per_1m: data.output_price_per_1m,
        cached_input_price_per_1m: data.cached_input_price_per_1m,
        source_url: data.source_url || undefined,
        notes: data.notes || undefined,
      })
      showSuccess(t('admin.modelPricing.messages.created'))
    }

    dialogOpen.value = false
    await loadPricing()
  } catch (err) {
    showError(t('admin.modelPricing.messages.saveFailed'))
    logger.error('Save failed', { error: err })
  } finally {
    saving.value = false
  }
}

function confirmDelete(entry: PricingEntry) {
  deletingEntry.value = entry
  deleteDialogOpen.value = true
}

async function deleteEntry() {
  if (!deletingEntry.value) return

  deleting.value = true

  try {
    await deleteModelPricing(deletingEntry.value.id)
    showSuccess(t('admin.modelPricing.messages.deleted'))
    deleteDialogOpen.value = false
    await loadPricing()
  } catch (err) {
    showError(t('admin.modelPricing.messages.deleteFailed'))
    logger.error('Delete failed', { error: err })
  } finally {
    deleting.value = false
    deletingEntry.value = null
  }
}

// Load on mount
onMounted(() => {
  loadPricing()
})
</script>
