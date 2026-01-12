<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon :color="isConfigured ? 'success' : 'grey'" class="mr-2">
        {{ isConfigured ? 'mdi-check-circle' : 'mdi-circle-outline' }}
      </v-icon>
      <v-icon :icon="purposeInfo.icon" class="mr-2" size="small" />
      {{ purposeInfo.name }}
      <v-spacer />
      <v-chip
        :color="isConfigured ? 'success' : 'grey'"
        size="small"
        variant="tonal"
      >
        {{ isConfigured
          ? t('admin.llmConfig.status.configured')
          : t('admin.llmConfig.status.notConfigured')
        }}
      </v-chip>
    </v-card-title>

    <v-card-text>
      <p class="text-body-2 text-medium-emphasis mb-4">
        {{ purposeInfo.description }}
      </p>

      <v-alert
        v-if="isConfigured"
        type="info"
        variant="tonal"
        density="compact"
        class="mb-4"
      >
        <strong>{{ t('admin.llmConfig.currentProvider') }}:</strong>
        {{ configuredProvidersLabel }}
      </v-alert>

      <p class="text-caption text-medium-emphasis mb-4">
        {{ t('admin.llmConfig.webSearch.fallbackHint') }}
      </p>

      <div class="mb-4 d-flex flex-wrap">
        <v-chip
          size="x-small"
          variant="outlined"
          class="mr-2 mb-2"
          :color="serpapiConfigured ? 'success' : 'grey'"
        >
          {{ serpapiLabel }}: {{ serpapiConfigured
            ? t('admin.llmConfig.status.configured')
            : t('admin.llmConfig.status.notConfigured')
          }}
        </v-chip>
        <v-chip
          size="x-small"
          variant="outlined"
          class="mb-2"
          :color="serperConfigured ? 'success' : 'grey'"
        >
          {{ serperLabel }}: {{ serperConfigured
            ? t('admin.llmConfig.status.configured')
            : t('admin.llmConfig.status.notConfigured')
          }}
        </v-chip>
      </div>

      <div v-if="serpapiStatus?.last_used_at || serperStatus?.last_used_at" class="mb-4">
        <v-chip v-if="serpapiStatus?.last_used_at" size="x-small" variant="outlined" class="mr-2">
          <v-icon start size="x-small">mdi-clock-outline</v-icon>
          {{ serpapiLabel }}: {{ formatDate(serpapiStatus.last_used_at) }}
        </v-chip>
        <v-chip v-if="serperStatus?.last_used_at" size="x-small" variant="outlined">
          <v-icon start size="x-small">mdi-clock-outline</v-icon>
          {{ serperLabel }}: {{ formatDate(serperStatus.last_used_at) }}
        </v-chip>
      </div>

      <div v-if="serpapiStatus?.last_error" class="mb-4">
        <v-alert type="error" variant="tonal" density="compact">
          <strong>{{ serpapiLabel }}:</strong>
          {{ serpapiStatus.last_error }}
        </v-alert>
      </div>
      <div v-if="serperStatus?.last_error" class="mb-4">
        <v-alert type="error" variant="tonal" density="compact">
          <strong>{{ serperLabel }}:</strong>
          {{ serperStatus.last_error }}
        </v-alert>
      </div>

      <v-form v-model="formValid" @submit.prevent="handleSave">
        <v-text-field
          v-model="formData.serpapi_key"
          :label="serpapiLabel"
          :placeholder="serpapiMaskedKey || (serpapiConfigured ? '••••••••••••' : t('admin.llmConfig.form.apiKeyPlaceholder'))"
          :type="showSerpapiKey ? 'text' : 'password'"
          :rules="[requireSerpapiOrSerperUnlessConfigured]"
          :append-inner-icon="showSerpapiKey ? 'mdi-eye-off' : 'mdi-eye'"
          :hint="serpapiConfigured ? t('admin.llmConfig.form.overwriteHint') : undefined"
          :persistent-hint="serpapiConfigured"
          variant="outlined"
          density="compact"
          class="mb-2"
          @click:append-inner="showSerpapiKey = !showSerpapiKey"
        />
        <v-text-field
          v-model="formData.serper_key"
          :label="serperLabel"
          :placeholder="serperMaskedKey || (serperConfigured ? '••••••••••••' : t('admin.llmConfig.form.apiKeyPlaceholder'))"
          :type="showSerperKey ? 'text' : 'password'"
          :rules="[requireSerperOrSerpapiUnlessConfigured]"
          :append-inner-icon="showSerperKey ? 'mdi-eye-off' : 'mdi-eye'"
          :hint="serperConfigured ? t('admin.llmConfig.form.overwriteHint') : undefined"
          :persistent-hint="serperConfigured"
          variant="outlined"
          density="compact"
          @click:append-inner="showSerperKey = !showSerperKey"
        />
      </v-form>
    </v-card-text>

    <v-card-actions>
      <v-btn
        v-if="isConfigured"
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
        v-if="serpapiConfigured || formData.serpapi_key.trim()"
        color="secondary"
        variant="tonal"
        size="small"
        :loading="testingProvider === 'serpapi'"
        @click="handlePreviewTest('serpapi')"
      >
        <v-icon start>mdi-connection</v-icon>
        {{ serpapiLabel }}
      </v-btn>
      <v-btn
        v-if="serperConfigured || formData.serper_key.trim()"
        color="secondary"
        variant="tonal"
        size="small"
        :loading="testingProvider === 'serper'"
        @click="handlePreviewTest('serper')"
      >
        <v-icon start>mdi-connection</v-icon>
        {{ serperLabel }}
      </v-btn>
      <v-btn
        color="primary"
        variant="tonal"
        size="small"
        :loading="saving"
        :disabled="!formValid"
        @click="handleSave"
      >
        <v-icon start>mdi-content-save</v-icon>
        {{ t('admin.llmConfig.actions.save') }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDateFormatter } from '@/composables'
import { useSnackbar } from '@/composables/useSnackbar'
import {
  previewTestSerpApi,
  previewTestSerper,
  type CredentialStatus,
  type PurposeInfo,
} from '@/services/api/admin'

const props = defineProps<{
  purposeInfo: PurposeInfo
  serpapiStatus?: CredentialStatus
  serperStatus?: CredentialStatus
  saving?: boolean
  testingProvider?: 'serpapi' | 'serper' | null
}>()

const emit = defineEmits<{
  save: [payload: { serpapi_key: string; serper_key: string }]
  test: [provider: 'serpapi' | 'serper']
  delete: []
}>()

const { t } = useI18n()
const { formatDateTime } = useDateFormatter()
const { showSuccess, showError } = useSnackbar()

const formValid = ref(false)
const showSerpapiKey = ref(false)
const showSerperKey = ref(false)
const localTestingProvider = ref<'serpapi' | 'serper' | null>(null)

const formData = reactive({
  serpapi_key: '',
  serper_key: '',
})

const serpapiConfigured = computed(() => props.serpapiStatus?.is_configured ?? false)
const serperConfigured = computed(() => props.serperStatus?.is_configured ?? false)
const isConfigured = computed(() => serpapiConfigured.value || serperConfigured.value)

// Get masked API keys from config
const serpapiMaskedKey = computed(() => props.serpapiStatus?.config?.api_key_masked)
const serperMaskedKey = computed(() => props.serperStatus?.config?.api_key_masked)

const providerNames = computed(() => {
  const names: Record<string, string> = {}
  for (const provider of props.purposeInfo.valid_providers) {
    names[provider.value.toUpperCase()] = provider.name
  }
  return {
    serpapi: names.SERPAPI || 'SerpAPI',
    serper: names.SERPER || 'Serper',
  }
})

const serpapiLabel = computed(() => `${providerNames.value.serpapi} (${t('admin.llmConfig.webSearch.primary')})`)
const serperLabel = computed(() => `${providerNames.value.serper} (${t('admin.llmConfig.webSearch.fallback')})`)

const configuredProvidersLabel = computed(() => {
  const providers: string[] = []
  if (serpapiConfigured.value) providers.push(serpapiLabel.value)
  if (serperConfigured.value) providers.push(serperLabel.value)
  return providers.join(', ')
})

// Validation: require at least one key, unless at least one is already configured
const requireSerpapiOrSerperUnlessConfigured = (v: string) =>
  !!v || !!formData.serper_key || isConfigured.value || t('admin.llmConfig.webSearch.atLeastOne')
const requireSerperOrSerpapiUnlessConfigured = (v: string) =>
  !!v || !!formData.serpapi_key || isConfigured.value || t('admin.llmConfig.webSearch.atLeastOne')

function formatDate(dateStr: string): string {
  return formatDateTime(dateStr)
}

function handleSave() {
  if (!formValid.value) return
  emit('save', { serpapi_key: formData.serpapi_key, serper_key: formData.serper_key })
}

// Combined testing state from local and props
const testingProvider = computed(() => localTestingProvider.value || props.testingProvider)

async function handlePreviewTest(provider: 'serpapi' | 'serper') {
  const key = provider === 'serpapi' ? formData.serpapi_key.trim() : formData.serper_key.trim()
  const isConfigured = provider === 'serpapi' ? serpapiConfigured.value : serperConfigured.value

  // If there's a new value entered, use preview test
  if (key) {
    localTestingProvider.value = provider
    try {
      const response = provider === 'serpapi'
        ? await previewTestSerpApi({ api_key: key })
        : await previewTestSerper({ api_key: key })

      if (response.data.success) {
        showSuccess(t('admin.llmConfig.messages.testSuccess'))
      } else {
        showError(response.data.error || t('admin.llmConfig.messages.testFailed'))
      }
    } catch {
      showError(t('admin.llmConfig.messages.testFailed'))
    } finally {
      localTestingProvider.value = null
    }
  } else if (isConfigured) {
    // If no new value but is configured, test saved credentials
    emit('test', provider)
  }
}
</script>
