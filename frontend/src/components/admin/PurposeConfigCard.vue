<template>
  <v-card>
    <v-card-title class="d-flex align-center flex-wrap">
      <v-icon :color="status?.is_configured ? 'success' : 'grey'" class="mr-2 flex-shrink-0">
        {{ status?.is_configured ? 'mdi-check-circle' : 'mdi-circle-outline' }}
      </v-icon>
      <v-icon :icon="purposeInfo.icon" class="mr-2 flex-shrink-0" size="small" />
      <span class="purpose-title">{{ purposeInfo.name }}</span>
    </v-card-title>

    <v-card-text>
      <p class="text-body-2 text-medium-emphasis mb-4">
        {{ purposeInfo.description }}
      </p>

      <!-- Current Provider Info -->
      <v-alert
        v-if="status?.is_configured && status?.provider_name"
        type="info"
        variant="tonal"
        density="compact"
        class="mb-4"
      >
        <strong>{{ t('admin.llmConfig.currentProvider') }}:</strong>
        {{ status.provider_name }}
      </v-alert>

      <!-- Status Info -->
      <div v-if="status?.is_configured && status?.last_used_at" class="mb-4">
        <v-chip size="x-small" variant="outlined" class="mr-2">
          <v-icon start size="x-small">mdi-clock-outline</v-icon>
          {{ t('admin.llmConfig.status.lastUsed') }}: {{ formatDate(status.last_used_at) }}
        </v-chip>
      </div>

      <div v-if="status?.last_error" class="mb-4">
        <v-alert type="error" variant="tonal" density="compact">
          {{ status.last_error }}
        </v-alert>
      </div>

      <v-form ref="formRef" v-model="formValid" @submit.prevent="handleSave">
        <!-- Provider Selection -->
        <v-select
          v-model="selectedProvider"
          :items="providerItems"
          :label="t('admin.llmConfig.form.selectProvider')"
          variant="outlined"
          density="compact"
          class="mb-4"
          @update:model-value="onProviderChange"
        >
          <template #item="{ props: itemProps, item }">
            <v-list-item v-bind="itemProps">
              <v-list-item-subtitle>{{ item.raw.description }}</v-list-item-subtitle>
            </v-list-item>
          </template>
        </v-select>

        <!-- Dynamic Credentials Form based on selected provider -->
        <template v-if="selectedProvider">
          <!-- SerpAPI / Serper - simple API key only -->
          <template v-if="selectedProvider === 'SERPAPI' || selectedProvider === 'SERPER'">
            <v-text-field
              v-model="formData.api_key"
              :label="t('admin.llmConfig.form.apiKey')"
              :placeholder="t('admin.llmConfig.form.apiKeyPlaceholder')"
              :type="showApiKey ? 'text' : 'password'"
              :rules="[required]"
              :append-inner-icon="showApiKey ? 'mdi-eye-off' : 'mdi-eye'"
              variant="outlined"
              density="compact"
              @click:append-inner="showApiKey = !showApiKey"
            />
          </template>

          <!-- Azure OpenAI - multiple fields -->
          <template v-else-if="selectedProvider === 'AZURE_OPENAI'">
            <v-text-field
              v-model="formData.endpoint"
              :label="t('admin.llmConfig.form.endpoint')"
              :placeholder="t('admin.llmConfig.form.endpointPlaceholder')"
              :rules="[required]"
              variant="outlined"
              density="compact"
              class="mb-2"
            />
            <v-text-field
              v-model="formData.api_key"
              :label="t('admin.llmConfig.form.apiKey')"
              :placeholder="t('admin.llmConfig.form.apiKeyPlaceholder')"
              :type="showApiKey ? 'text' : 'password'"
              :rules="[required]"
              :append-inner-icon="showApiKey ? 'mdi-eye-off' : 'mdi-eye'"
              variant="outlined"
              density="compact"
              class="mb-2"
              @click:append-inner="showApiKey = !showApiKey"
            />
            <v-text-field
              v-model="formData.api_version"
              :label="t('admin.llmConfig.form.apiVersion')"
              variant="outlined"
              density="compact"
              class="mb-2"
            />
            <v-text-field
              v-model="formData.deployment_name"
              :label="t('admin.llmConfig.form.deploymentName')"
              :placeholder="t('admin.llmConfig.form.deploymentNamePlaceholder')"
              :rules="[required]"
              variant="outlined"
              density="compact"
              class="mb-2"
            />
            <v-text-field
              v-model="formData.embeddings_deployment"
              :label="t('admin.llmConfig.form.embeddingsDeployment')"
              :placeholder="t('admin.llmConfig.form.embeddingsDeploymentPlaceholder')"
              variant="outlined"
              density="compact"
            />
          </template>

          <!-- OpenAI (Standard) - key, org, model -->
          <template v-else-if="selectedProvider === 'OPENAI'">
            <v-text-field
              v-model="formData.api_key"
              :label="t('admin.llmConfig.form.apiKey')"
              :placeholder="t('admin.llmConfig.form.apiKeyPlaceholder')"
              :type="showApiKey ? 'text' : 'password'"
              :rules="[required]"
              :append-inner-icon="showApiKey ? 'mdi-eye-off' : 'mdi-eye'"
              variant="outlined"
              density="compact"
              class="mb-2"
              @click:append-inner="showApiKey = !showApiKey"
            />
            <v-text-field
              v-model="formData.organization"
              :label="t('admin.llmConfig.form.organization')"
              :placeholder="t('admin.llmConfig.form.organizationPlaceholder')"
              variant="outlined"
              density="compact"
              class="mb-2"
            />
            <v-text-field
              v-model="formData.model"
              :label="t('admin.llmConfig.form.model')"
              :placeholder="t('admin.llmConfig.form.openaiModelPlaceholder')"
              variant="outlined"
              density="compact"
              class="mb-2"
            />
            <v-text-field
              v-model="formData.embeddings_model"
              :label="t('admin.llmConfig.form.embeddingsModel')"
              :placeholder="t('admin.llmConfig.form.embeddingsModelPlaceholder')"
              variant="outlined"
              density="compact"
            />
          </template>

          <!-- Anthropic - endpoint, key, model -->
          <template v-else-if="selectedProvider === 'ANTHROPIC'">
            <v-text-field
              v-model="formData.endpoint"
              :label="t('admin.llmConfig.form.endpoint')"
              :placeholder="t('admin.llmConfig.form.endpointPlaceholder')"
              :rules="[required]"
              variant="outlined"
              density="compact"
              class="mb-2"
            />
            <v-text-field
              v-model="formData.api_key"
              :label="t('admin.llmConfig.form.apiKey')"
              :placeholder="t('admin.llmConfig.form.apiKeyPlaceholder')"
              :type="showApiKey ? 'text' : 'password'"
              :rules="[required]"
              :append-inner-icon="showApiKey ? 'mdi-eye-off' : 'mdi-eye'"
              variant="outlined"
              density="compact"
              class="mb-2"
              @click:append-inner="showApiKey = !showApiKey"
            />
            <v-text-field
              v-model="formData.model"
              :label="t('admin.llmConfig.form.model')"
              :placeholder="t('admin.llmConfig.form.modelPlaceholder')"
              variant="outlined"
              density="compact"
            />
          </template>
        </template>
      </v-form>

      <!-- Embeddings Statistics (only for EMBEDDINGS purpose) -->
      <template v-if="isEmbeddingsPurpose && status?.is_configured">
        <v-divider class="my-4" />

        <div class="d-flex align-center justify-space-between mb-3">
          <span class="text-subtitle-2">{{ t('admin.llmConfig.embeddings.statsTitle') }}</span>
          <v-btn
            variant="text"
            size="x-small"
            :loading="loadingStats"
            @click="loadEmbeddingStats"
          >
            <v-icon size="small">mdi-refresh</v-icon>
          </v-btn>
        </div>

        <v-alert
          v-if="embeddingStats"
          type="info"
          variant="tonal"
          density="compact"
          class="mb-3"
        >
          <div class="d-flex flex-wrap ga-2">
            <v-chip size="x-small" label>
              {{ t('admin.llmConfig.embeddings.entities') }}:
              {{ embeddingStats.entities_with_embedding }}/{{ embeddingStats.entities_total }}
            </v-chip>
            <v-chip size="x-small" label>
              {{ t('admin.llmConfig.embeddings.types') }}:
              {{ embeddingStats.entity_types_with_embedding + embeddingStats.facet_types_with_embedding + embeddingStats.categories_with_embedding }}/{{ embeddingStats.entity_types_total + embeddingStats.facet_types_total + embeddingStats.categories_total }}
            </v-chip>
            <v-chip size="x-small" label>
              {{ t('admin.llmConfig.embeddings.facetValues') }}:
              {{ embeddingStats.facet_values_with_embedding }}/{{ embeddingStats.facet_values_total }}
            </v-chip>
          </div>
        </v-alert>

        <v-alert
          v-if="embeddingStats?.task_running"
          type="warning"
          variant="tonal"
          density="compact"
          class="mb-3"
        >
          <v-icon start size="small">mdi-cog-sync</v-icon>
          {{ t('admin.llmConfig.embeddings.taskRunning') }}
        </v-alert>

        <v-btn
          color="secondary"
          variant="tonal"
          size="small"
          block
          :loading="generatingEmbeddings"
          :disabled="embeddingStats?.task_running || !status?.is_configured"
          @click="handleGenerateEmbeddings"
        >
          <v-icon start>mdi-vector-polyline</v-icon>
          {{ t('admin.llmConfig.embeddings.generate') }}
        </v-btn>
      </template>
    </v-card-text>

    <v-card-actions>
      <v-btn
        v-if="status?.is_configured"
        color="error"
        variant="text"
        size="small"
        @click="$emit('delete')"
      >
        <v-icon start>mdi-delete</v-icon>
        {{ t('admin.llmConfig.actions.delete') }}
      </v-btn>
      <v-spacer />
      <v-chip
        :color="status?.is_configured ? 'success' : 'grey'"
        size="small"
        variant="tonal"
        class="mr-2"
      >
        {{ status?.is_configured
          ? t('admin.llmConfig.status.configured')
          : t('admin.llmConfig.status.notConfigured')
        }}
      </v-chip>
      <v-btn
        v-if="status?.is_configured"
        color="secondary"
        variant="tonal"
        size="small"
        :loading="testing"
        @click="$emit('test')"
      >
        <v-icon start>mdi-connection</v-icon>
        {{ t('admin.llmConfig.actions.test') }}
      </v-btn>
      <v-btn
        color="primary"
        variant="tonal"
        size="small"
        :loading="saving"
        :disabled="!formValid || !selectedProvider"
        @click="handleSave"
      >
        <v-icon start>mdi-content-save</v-icon>
        {{ t('admin.llmConfig.actions.save') }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import type { PurposeInfo, PurposeConfigStatus, EmbeddingStats } from '@/services/api/admin'
import { getEmbeddingStats, generateEmbeddings } from '@/services/api/admin'
import { useDateFormatter } from '@/composables'

const props = defineProps<{
  purposeInfo: PurposeInfo
  status?: PurposeConfigStatus
  saving?: boolean
  testing?: boolean
}>()

const emit = defineEmits<{
  save: [provider: string, credentials: Record<string, string>]
  test: []
  delete: []
}>()

// Check if this is the EMBEDDINGS purpose
const isEmbeddingsPurpose = computed(() => props.purposeInfo.value === 'EMBEDDINGS')

// Embedding stats state
const embeddingStats = ref<EmbeddingStats | null>(null)
const loadingStats = ref(false)
const generatingEmbeddings = ref(false)

async function loadEmbeddingStats() {
  if (!isEmbeddingsPurpose.value) return

  loadingStats.value = true
  try {
    const response = await getEmbeddingStats()
    embeddingStats.value = response.data
  } catch {
    // Silently fail - stats are optional
  } finally {
    loadingStats.value = false
  }
}

async function handleGenerateEmbeddings() {
  generatingEmbeddings.value = true
  try {
    await generateEmbeddings({ target: 'all', force: false })
    // Reload stats after a short delay to show the task is running
    setTimeout(() => loadEmbeddingStats(), 1000)
  } catch {
    // Error handling is done by the API layer
  } finally {
    generatingEmbeddings.value = false
  }
}

// Load embedding stats when component mounts (only for EMBEDDINGS purpose)
onMounted(() => {
  if (isEmbeddingsPurpose.value && props.status?.is_configured) {
    loadEmbeddingStats()
  }
})

// Reload stats when status changes to configured
watch(() => props.status?.is_configured, (isConfigured) => {
  if (isConfigured && isEmbeddingsPurpose.value) {
    loadEmbeddingStats()
  }
})

const { formatDateTime } = useDateFormatter()

const { t } = useI18n()

const formValid = ref(false)
const showApiKey = ref(false)
const selectedProvider = ref<string | null>(props.status?.provider || null)

// Initialize form data based on selected provider
const formData = reactive<Record<string, string>>({
  api_key: '',
  endpoint: '',
  api_version: '2025-04-01-preview',
  deployment_name: '',
  embeddings_deployment: 'text-embedding-3-large',
  model: '',
  organization: '',
  embeddings_model: 'text-embedding-3-large',
})

// Create provider items for the select dropdown
const providerItems = computed(() => {
  return props.purposeInfo.valid_providers.map(p => ({
    value: p.value,
    title: p.name,
    description: p.description,
  }))
})

// Set default values when provider changes
function onProviderChange(provider: string | null) {
  // Reset form
  formData.api_key = ''
  formData.endpoint = ''
  formData.api_version = '2025-04-01-preview'
  formData.deployment_name = ''
  formData.embeddings_deployment = 'text-embedding-3-large'
  formData.model = ''
  formData.organization = ''
  formData.embeddings_model = 'text-embedding-3-large'

  // Set defaults based on provider
  if (provider === 'ANTHROPIC') {
    formData.endpoint = 'https://api.anthropic.com'
    formData.model = 'claude-opus-4-5'
  } else if (provider === 'OPENAI') {
    formData.model = 'gpt-4o'
  }
}

// Reset when status changes (e.g., after save)
watch(() => props.status, () => {
  formData.api_key = ''
  if (props.status?.provider) {
    selectedProvider.value = props.status.provider
  }
})

const required = (v: string) => !!v || t('common.required')

function formatDate(dateStr: string): string {
  return formatDateTime(dateStr)
}

function handleSave() {
  if (!formValid.value || !selectedProvider.value) return

  const credentials: Record<string, string> = { api_key: formData.api_key }

  if (selectedProvider.value === 'AZURE_OPENAI') {
    credentials.endpoint = formData.endpoint
    credentials.api_version = formData.api_version
    credentials.deployment_name = formData.deployment_name
    credentials.embeddings_deployment = formData.embeddings_deployment
  } else if (selectedProvider.value === 'OPENAI') {
    if (formData.organization) credentials.organization = formData.organization
    if (formData.model) credentials.model = formData.model
    if (formData.embeddings_model) credentials.embeddings_model = formData.embeddings_model
  } else if (selectedProvider.value === 'ANTHROPIC') {
    credentials.endpoint = formData.endpoint
    credentials.model = formData.model
  }

  emit('save', selectedProvider.value, credentials)
}
</script>

<style scoped>
.purpose-title {
  word-break: break-word;
  line-height: 1.3;
}
</style>
