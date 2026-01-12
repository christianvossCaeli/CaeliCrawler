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
              :placeholder="maskedApiKey || (status?.is_configured ? '••••••••••••' : t('admin.llmConfig.form.apiKeyPlaceholder'))"
              :type="showApiKey ? 'text' : 'password'"
              :rules="[requiredUnlessConfigured]"
              :append-inner-icon="showApiKey ? 'mdi-eye-off' : 'mdi-eye'"
              :hint="status?.is_configured ? t('admin.llmConfig.form.overwriteHint') : undefined"
              :persistent-hint="status?.is_configured"
              variant="outlined"
              density="compact"
              @click:append-inner="showApiKey = !showApiKey"
            />
          </template>

          <!-- Azure - URL-based (supports OpenAI and Claude) -->
          <template v-else-if="selectedProvider === 'AZURE_OPENAI'">
            <v-text-field
              v-model="formData.api_key"
              :label="t('admin.llmConfig.form.apiKey')"
              :placeholder="maskedApiKey || (status?.is_configured ? '••••••••••••' : t('admin.llmConfig.form.apiKeyPlaceholder'))"
              :type="showApiKey ? 'text' : 'password'"
              :rules="[requiredUnlessConfigured]"
              :append-inner-icon="showApiKey ? 'mdi-eye-off' : 'mdi-eye'"
              :hint="status?.is_configured ? t('admin.llmConfig.form.overwriteHint') : undefined"
              :persistent-hint="status?.is_configured"
              variant="outlined"
              density="compact"
              class="mb-2"
              @click:append-inner="showApiKey = !showApiKey"
            />
            <!-- Chat URL - required for non-EMBEDDINGS purposes -->
            <v-text-field
              v-if="!isEmbeddingsPurpose"
              v-model="formData.chat_url"
              :label="t('admin.llmConfig.form.chatUrl')"
              :placeholder="t('admin.llmConfig.form.chatUrlPlaceholder')"
              :hint="t('admin.llmConfig.form.chatUrlHint')"
              persistent-hint
              :rules="[required]"
              variant="outlined"
              density="compact"
              class="mb-2"
            />
            <!-- Model field - shown when URL contains /anthropic/ (Claude) -->
            <v-text-field
              v-if="!isEmbeddingsPurpose && isAzureClaudeUrl"
              v-model="formData.model"
              :label="t('admin.llmConfig.form.model')"
              placeholder="claude-3-5-sonnet-v2"
              hint="Azure Claude Model (z.B. claude-3-5-sonnet-v2)"
              persistent-hint
              variant="outlined"
              density="compact"
              class="mb-2"
            />
            <!-- Embeddings URL - required for EMBEDDINGS purpose -->
            <v-text-field
              v-if="isEmbeddingsPurpose"
              v-model="formData.embeddings_url"
              :label="t('admin.llmConfig.form.embeddingsUrl')"
              :placeholder="t('admin.llmConfig.form.embeddingsUrlPlaceholder')"
              :hint="t('admin.llmConfig.form.embeddingsUrlHint')"
              persistent-hint
              :rules="[required]"
              variant="outlined"
              density="compact"
            />
          </template>

          <!-- OpenAI (Standard) - key, org, model -->
          <template v-else-if="selectedProvider === 'OPENAI'">
            <v-text-field
              v-model="formData.api_key"
              :label="t('admin.llmConfig.form.apiKey')"
              :placeholder="maskedApiKey || (status?.is_configured ? '••••••••••••' : t('admin.llmConfig.form.apiKeyPlaceholder'))"
              :type="showApiKey ? 'text' : 'password'"
              :rules="[requiredUnlessConfigured]"
              :append-inner-icon="showApiKey ? 'mdi-eye-off' : 'mdi-eye'"
              :hint="status?.is_configured ? t('admin.llmConfig.form.overwriteHint') : undefined"
              :persistent-hint="status?.is_configured"
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
              :class="isEmbeddingsPurpose ? 'mb-2' : ''"
            />
            <!-- Embeddings model only shown for EMBEDDINGS purpose -->
            <v-text-field
              v-if="isEmbeddingsPurpose"
              v-model="formData.embeddings_model"
              :label="t('admin.llmConfig.form.embeddingsModel')"
              :placeholder="t('admin.llmConfig.form.embeddingsModelPlaceholder')"
              :rules="[required]"
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
              :placeholder="maskedApiKey || (status?.is_configured ? '••••••••••••' : t('admin.llmConfig.form.apiKeyPlaceholder'))"
              :type="showApiKey ? 'text' : 'password'"
              :rules="[requiredUnlessConfigured]"
              :append-inner-icon="showApiKey ? 'mdi-eye-off' : 'mdi-eye'"
              :hint="status?.is_configured ? t('admin.llmConfig.form.overwriteHint') : undefined"
              :persistent-hint="status?.is_configured"
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
          type="info"
          variant="tonal"
          density="compact"
          class="mb-3"
        >
          <template #prepend>
            <v-progress-circular
              indeterminate
              size="20"
              width="2"
              color="info"
              class="mr-2"
            />
          </template>
          <div class="d-flex flex-column">
            <span class="font-weight-medium">{{ t('admin.llmConfig.embeddings.taskRunning') }}</span>
            <span v-if="embeddingStats?.task_id" class="text-caption text-medium-emphasis">
              Task-ID: {{ embeddingStats.task_id }}
            </span>
          </div>
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
        v-if="hasFormDataForTest"
        color="secondary"
        variant="tonal"
        size="small"
        :loading="isTesting"
        @click="handlePreviewTest"
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
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import type { PurposeInfo, PurposeConfigStatus, EmbeddingStats } from '@/services/api/admin'
import {
  getEmbeddingStats,
  generateEmbeddings,
  previewTestAzureOpenAI,
  previewTestAzureOpenAIEmbeddings,
  previewTestOpenAI,
  previewTestOpenAIEmbeddings,
  previewTestAnthropic,
} from '@/services/api/admin'
import { useDateFormatter } from '@/composables'
import { useSnackbar } from '@/composables/useSnackbar'

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

// Composables (declare early for use in functions below)
const { formatDateTime } = useDateFormatter()
const { showSuccess, showError } = useSnackbar()
const { t } = useI18n()

// Check if this is the EMBEDDINGS purpose
const isEmbeddingsPurpose = computed(() => props.purposeInfo.value === 'EMBEDDINGS')

// Check if Azure URL is for Claude (contains /anthropic/)
const isAzureClaudeUrl = computed(() => {
  const url = formData.chat_url || ''
  return url.includes('/anthropic/')
})

// Embedding stats state
const embeddingStats = ref<EmbeddingStats | null>(null)
const loadingStats = ref(false)
const generatingEmbeddings = ref(false)
let pollingInterval: ReturnType<typeof setInterval> | null = null

async function loadEmbeddingStats() {
  if (!isEmbeddingsPurpose.value) return

  loadingStats.value = true
  const wasRunning = embeddingStats.value?.task_running
  try {
    const response = await getEmbeddingStats()
    embeddingStats.value = response.data

    // Start polling if task is running
    if (response.data.task_running && !pollingInterval) {
      startPolling()
    }
    // Stop polling and show completion if task just finished
    if (wasRunning && !response.data.task_running) {
      stopPolling()
      showSuccess('Embedding-Generierung abgeschlossen!')
    }
  } catch {
    // Silently fail - stats are optional
  } finally {
    loadingStats.value = false
  }
}

function startPolling() {
  if (pollingInterval) return
  pollingInterval = setInterval(() => {
    loadEmbeddingStats()
  }, 3000) // Poll every 3 seconds
}

function stopPolling() {
  if (pollingInterval) {
    clearInterval(pollingInterval)
    pollingInterval = null
  }
}

async function handleGenerateEmbeddings() {
  generatingEmbeddings.value = true
  try {
    const response = await generateEmbeddings({ target: 'all', force: false })
    showSuccess(`Embedding-Generierung gestartet (Task-ID: ${response.data.task_id})`)
    // Reload stats after a short delay and start polling
    setTimeout(() => {
      loadEmbeddingStats()
    }, 1000)
  } catch {
    // Error handling is done by the API layer
  } finally {
    generatingEmbeddings.value = false
  }
}

// Clean up polling on unmount
onUnmounted(() => {
  stopPolling()
})

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

const formValid = ref(false)
const showApiKey = ref(false)
const selectedProvider = ref<string | null>(props.status?.provider || null)
const localTesting = ref(false)
// Track the last saved provider to avoid resetting form when watch sets the same provider
const lastSavedProvider = ref<string | null>(props.status?.provider || null)

// Initialize form data based on selected provider
const formData = reactive<Record<string, string>>({
  api_key: '',
  // Azure OpenAI (URL-based)
  chat_url: '',
  embeddings_url: '',
  // OpenAI
  model: '',
  organization: '',
  embeddings_model: 'text-embedding-3-large',
  // Anthropic
  endpoint: '',
})

// Create provider items for the select dropdown
const providerItems = computed(() => {
  return props.purposeInfo.valid_providers.map(p => ({
    value: p.value,
    title: p.name,
    description: p.description,
  }))
})

// Set default values when provider changes (only for actual user-initiated changes)
function onProviderChange(provider: string | null) {
  // Skip reset if this is just the watch setting the provider to match saved config
  // This prevents wiping form data when the component loads or status updates
  if (provider === lastSavedProvider.value) {
    return
  }

  // Reset form for actual provider change
  formData.api_key = ''
  formData.chat_url = ''
  formData.embeddings_url = ''
  formData.model = ''
  formData.organization = ''
  formData.embeddings_model = 'text-embedding-3-large'
  formData.endpoint = ''

  // Set defaults based on provider
  if (provider === 'ANTHROPIC') {
    formData.endpoint = 'https://api.anthropic.com'
    formData.model = 'claude-opus-4-5'
  } else if (provider === 'OPENAI') {
    formData.model = 'gpt-4o'
  }
}

// Update provider and form fields when status changes (e.g., after save or initial load)
watch(() => props.status, (newStatus) => {
  if (newStatus?.provider) {
    // Update the saved provider first so onProviderChange won't reset the form
    lastSavedProvider.value = newStatus.provider
    selectedProvider.value = newStatus.provider
  }
  // Populate form with saved config values (except api_key which stays empty for security)
  if (newStatus?.config) {
    const config = newStatus.config
    // Azure OpenAI (URL-based)
    if (config.chat_url) formData.chat_url = config.chat_url
    if (config.embeddings_url) formData.embeddings_url = config.embeddings_url
    // OpenAI & Azure Claude (model field)
    if (config.model) formData.model = config.model
    if (config.organization) formData.organization = config.organization
    if (config.embeddings_model) formData.embeddings_model = config.embeddings_model
    // Anthropic
    if (config.endpoint) formData.endpoint = config.endpoint
    // api_key stays empty - user must re-enter to change
  }
}, { immediate: true })

const required = (v: string) => !!v || t('common.required')
const requiredUnlessConfigured = (v: string) => !!v || props.status?.is_configured || t('common.required')

// Get masked API key from config for placeholder
const maskedApiKey = computed(() => props.status?.config?.api_key_masked)

// Combined testing state from local and props
const isTesting = computed(() => localTesting.value || props.testing)

// Check if we have enough form data to enable test button
const hasFormDataForTest = computed(() => {
  if (!selectedProvider.value) return false

  // Check if we have either a new api_key entered OR the provider is already configured
  const hasApiKey = !!formData.api_key.trim() || props.status?.is_configured
  if (!hasApiKey) return false

  // Provider-specific required fields
  switch (selectedProvider.value) {
    case 'AZURE_OPENAI':
      // For EMBEDDINGS purpose, need embeddings_url; otherwise need chat_url
      if (isEmbeddingsPurpose.value) {
        return !!formData.embeddings_url.trim()
      }
      return !!formData.chat_url.trim()
    case 'ANTHROPIC':
      return !!formData.endpoint.trim()
    case 'OPENAI':
    case 'SERPAPI':
    case 'SERPER':
      return true
    default:
      return true
  }
})

// Check if we need to use preview test (has new data) or regular test
const shouldUsePreviewTest = computed(() => {
  return !!formData.api_key.trim()
})

async function handlePreviewTest() {
  if (!selectedProvider.value || !hasFormDataForTest.value) return

  // If we have a new API key, use preview test
  if (shouldUsePreviewTest.value) {
    localTesting.value = true
    try {
      let response
      switch (selectedProvider.value) {
        case 'AZURE_OPENAI':
          // For EMBEDDINGS purpose, test the embeddings URL
          if (isEmbeddingsPurpose.value && formData.embeddings_url.trim()) {
            response = await previewTestAzureOpenAIEmbeddings({
              api_key: formData.api_key,
              chat_url: formData.chat_url || formData.embeddings_url, // fallback
              embeddings_url: formData.embeddings_url,
            })
          } else {
            response = await previewTestAzureOpenAI({
              api_key: formData.api_key,
              chat_url: formData.chat_url,
              embeddings_url: formData.embeddings_url || undefined,
              model: formData.model || undefined,  // For Azure Claude
            })
          }
          break
        case 'OPENAI':
          // For EMBEDDINGS purpose, test the embeddings model
          if (isEmbeddingsPurpose.value) {
            response = await previewTestOpenAIEmbeddings({
              api_key: formData.api_key,
              organization: formData.organization || undefined,
              model: formData.model || undefined,
              embeddings_model: formData.embeddings_model || undefined,
            })
          } else {
            response = await previewTestOpenAI({
              api_key: formData.api_key,
              organization: formData.organization || undefined,
              model: formData.model || undefined,
              embeddings_model: formData.embeddings_model || undefined,
            })
          }
          break
        case 'ANTHROPIC':
          response = await previewTestAnthropic({
            endpoint: formData.endpoint || undefined,
            api_key: formData.api_key,
            model: formData.model || undefined,
          })
          break
        default:
          showError(t('admin.llmConfig.messages.testFailed'))
          return
      }

      if (response.data.success) {
        showSuccess(t('admin.llmConfig.messages.testSuccess'))
      } else {
        showError(response.data.error || t('admin.llmConfig.messages.testFailed'))
      }
    } catch {
      showError(t('admin.llmConfig.messages.testFailed'))
    } finally {
      localTesting.value = false
    }
  } else if (props.status?.is_configured) {
    // No new API key but configured - use the regular test (emit to parent)
    emit('test')
  }
}

function formatDate(dateStr: string): string {
  return formatDateTime(dateStr)
}

function handleSave() {
  if (!formValid.value || !selectedProvider.value) return

  const credentials: Record<string, string> = { api_key: formData.api_key }

  if (selectedProvider.value === 'AZURE_OPENAI') {
    credentials.chat_url = formData.chat_url
    if (formData.embeddings_url) credentials.embeddings_url = formData.embeddings_url
    if (formData.model) credentials.model = formData.model  // For Azure Claude
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
