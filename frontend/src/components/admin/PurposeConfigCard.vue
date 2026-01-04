<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon :color="status?.is_configured ? 'success' : 'grey'" class="mr-2">
        {{ status?.is_configured ? 'mdi-check-circle' : 'mdi-circle-outline' }}
      </v-icon>
      <v-icon :icon="purposeInfo.icon" class="mr-2" size="small" />
      {{ purposeInfo.name }}
      <v-spacer />
      <v-chip
        :color="status?.is_configured ? 'success' : 'grey'"
        size="small"
        variant="tonal"
      >
        {{ status?.is_configured
          ? t('admin.llmConfig.status.configured')
          : t('admin.llmConfig.status.notConfigured')
        }}
      </v-chip>
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
          <template v-if="selectedProvider === 'serpapi' || selectedProvider === 'serper'">
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
          <template v-else-if="selectedProvider === 'azure_openai'">
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
          <template v-else-if="selectedProvider === 'openai'">
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
          <template v-else-if="selectedProvider === 'anthropic'">
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
import { ref, reactive, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { PurposeInfo, PurposeConfigStatus } from '@/services/api/admin'

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
  if (provider === 'anthropic') {
    formData.endpoint = 'https://api.anthropic.com'
    formData.model = 'claude-opus-4-5'
  } else if (provider === 'openai') {
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
  return new Date(dateStr).toLocaleString()
}

function handleSave() {
  if (!formValid.value || !selectedProvider.value) return

  const credentials: Record<string, string> = { api_key: formData.api_key }

  if (selectedProvider.value === 'azure_openai') {
    credentials.endpoint = formData.endpoint
    credentials.api_version = formData.api_version
    credentials.deployment_name = formData.deployment_name
    credentials.embeddings_deployment = formData.embeddings_deployment
  } else if (selectedProvider.value === 'openai') {
    if (formData.organization) credentials.organization = formData.organization
    if (formData.model) credentials.model = formData.model
    if (formData.embeddings_model) credentials.embeddings_model = formData.embeddings_model
  } else if (selectedProvider.value === 'anthropic') {
    credentials.endpoint = formData.endpoint
    credentials.model = formData.model
  }

  emit('save', selectedProvider.value, credentials)
}
</script>
