<template>
  <div>
    <!-- Header -->
    <PageHeader
      :title="t('admin.llmConfig.title')"
      :subtitle="t('admin.llmConfig.subtitle')"
      icon="mdi-brain"
    />

    <PageInfoBox :storage-key="INFO_BOX_STORAGE_KEYS.AI_CONFIG" :title="t('admin.llmConfig.info.title')">
      {{ t('admin.llmConfig.info.description') }}
    </PageInfoBox>

    <!-- Loading State -->
    <v-skeleton-loader v-if="loading" type="card, card, card" />

    <template v-else>
      <!-- Purpose Cards Grid -->
      <v-row>
        <v-col
          v-for="purpose in purposes"
          :key="purpose.value"
          cols="12"
          md="6"
          lg="4"
        >
          <WebSearchCredentialsCard
            v-if="isWebSearchPurpose(purpose.value)"
            :purpose-info="purpose"
            :serpapi-status="credentialStatus?.serpapi"
            :serper-status="credentialStatus?.serper"
            :saving="savingPurpose === purpose.value"
            :testing-provider="testingWebSearchProvider"
            @save="credentials => handleSaveWebSearch(purpose.value, credentials)"
            @test="handleTestWebSearch"
            @delete="openDeleteDialog(purpose.value)"
          />
          <PurposeConfigCard
            v-else
            :purpose-info="purpose"
            :status="getStatusForPurpose(purpose.value)"
            :saving="savingPurpose === purpose.value"
            :testing="testingPurpose === purpose.value"
            @save="(provider, credentials) => handleSave(purpose.value, provider, credentials)"
            @test="handleTest(purpose.value)"
            @delete="openDeleteDialog(purpose.value)"
          />
        </v-col>
      </v-row>
    </template>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialogOpen" :max-width="DIALOG_SIZES.XS">
      <v-card>
        <v-card-title>{{ t('admin.llmConfig.dialog.deleteTitle') }}</v-card-title>
        <v-card-text>{{ t('admin.llmConfig.dialog.deleteConfirm') }}</v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="deleteDialogOpen = false">
            {{ t('common.cancel') }}
          </v-btn>
          <v-btn color="error" variant="tonal" :loading="deleting" @click="confirmDelete">
            {{ t('admin.llmConfig.actions.delete') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSnackbar } from '@/composables/useSnackbar'
import PageHeader from '@/components/common/PageHeader.vue'
import PageInfoBox from '@/components/common/PageInfoBox.vue'
import PurposeConfigCard from '@/components/admin/PurposeConfigCard.vue'
import WebSearchCredentialsCard from '@/components/admin/WebSearchCredentialsCard.vue'
import {
  getApiCredentialsStatus,
  getLLMPurposes,
  getLLMConfigStatus,
  saveSerpApiCredentials,
  saveSerperCredentials,
  saveLLMPurposeConfig,
  deleteApiCredential,
  deleteLLMPurposeConfig,
  testApiCredential,
  testLLMPurposeConfig,
  type AllCredentialsStatus,
  type PurposeInfo,
  type PurposeConfigStatus,
} from '@/services/api/admin'
import { DIALOG_SIZES } from '@/config/ui'
import { INFO_BOX_STORAGE_KEYS } from '@/config/infoBox'

const { t } = useI18n()
const { showSuccess, showError } = useSnackbar()

// State
const loading = ref(true)
const purposes = ref<PurposeInfo[]>([])
const configStatus = ref<PurposeConfigStatus[]>([])
const credentialStatus = ref<AllCredentialsStatus | null>(null)
const savingPurpose = ref<string | null>(null)
const testingPurpose = ref<string | null>(null)
const testingWebSearchProvider = ref<'serpapi' | 'serper' | null>(null)
const deleting = ref(false)
const deleteDialogOpen = ref(false)
const deletePurpose = ref<string | null>(null)

// Load data on mount
onMounted(async () => {
  await fetchData()
})

async function fetchData() {
  loading.value = true
  try {
    const [purposesResponse, statusResponse, credentialsResponse] = await Promise.all([
      getLLMPurposes(),
      getLLMConfigStatus(),
      getApiCredentialsStatus(),
    ])
    purposes.value = purposesResponse.data.purposes
    configStatus.value = statusResponse.data.configs
    credentialStatus.value = credentialsResponse.data
  } catch {
    showError(t('admin.llmConfig.messages.loadError'))
  } finally {
    loading.value = false
  }
}

function getStatusForPurpose(purpose: string): PurposeConfigStatus | undefined {
  return configStatus.value.find(s => s.purpose === purpose)
}

function isWebSearchPurpose(purpose: string | null): boolean {
  return (purpose ?? '').toLowerCase() === 'web_search'
}

async function handleSave(purpose: string, provider: string, credentials: Record<string, string>) {
  savingPurpose.value = purpose
  try {
    await saveLLMPurposeConfig(purpose, { provider, credentials })
    showSuccess(t('admin.llmConfig.messages.saved'))
    await fetchData()
  } catch {
    showError(t('admin.llmConfig.messages.saveError'))
  } finally {
    savingPurpose.value = null
  }
}

async function handleSaveWebSearch(
  purpose: string,
  credentials: { serpapi_key: string; serper_key: string }
) {
  savingPurpose.value = purpose

  const serpapiKey = credentials.serpapi_key.trim()
  const serperKey = credentials.serper_key.trim()

  // Get current credential status for web search
  const serpapiConfigured = credentialStatus.value?.serpapi?.is_configured
  const serperConfigured = credentialStatus.value?.serper?.is_configured

  // If nothing is entered and nothing is configured, show error
  if (!serpapiKey && !serperKey && !serpapiConfigured && !serperConfigured) {
    showError(t('admin.llmConfig.webSearch.atLeastOne'))
    savingPurpose.value = null
    return
  }

  // If nothing new is entered but something is already configured, just return success
  if (!serpapiKey && !serperKey) {
    showSuccess(t('admin.llmConfig.messages.saved'))
    savingPurpose.value = null
    return
  }

  try {
    const requests = []
    // Only save what was actually entered
    if (serpapiKey) requests.push(saveSerpApiCredentials({ api_key: serpapiKey }))
    if (serperKey) requests.push(saveSerperCredentials({ api_key: serperKey }))
    await Promise.all(requests)
    showSuccess(t('admin.llmConfig.messages.saved'))
    await fetchData()
  } catch {
    showError(t('admin.llmConfig.messages.saveError'))
  } finally {
    savingPurpose.value = null
  }
}

async function handleTest(purpose: string) {
  testingPurpose.value = purpose
  try {
    const response = await testLLMPurposeConfig(purpose)
    if (response.data.success) {
      showSuccess(t('admin.llmConfig.messages.testSuccess'))
    } else {
      showError(response.data.error || t('admin.llmConfig.messages.testFailed'))
    }
  } catch (error: unknown) {
    const axiosError = error as { response?: { data?: { detail?: string } } }
    showError(axiosError.response?.data?.detail || t('admin.llmConfig.messages.testFailed'))
  } finally {
    testingPurpose.value = null
  }
}

async function handleTestWebSearch(provider: 'serpapi' | 'serper') {
  testingWebSearchProvider.value = provider
  try {
    const response = await testApiCredential(provider)
    if (response.data.success) {
      showSuccess(t('admin.llmConfig.messages.testSuccess'))
    } else {
      showError(response.data.error || t('admin.llmConfig.messages.testFailed'))
    }
  } catch (error: unknown) {
    const axiosError = error as { response?: { data?: { detail?: string } } }
    showError(axiosError.response?.data?.detail || t('admin.llmConfig.messages.testFailed'))
  } finally {
    testingWebSearchProvider.value = null
  }
}

function openDeleteDialog(purpose: string) {
  deletePurpose.value = purpose
  deleteDialogOpen.value = true
}

async function confirmDelete() {
  if (!deletePurpose.value) return

  deleting.value = true
  try {
    if (isWebSearchPurpose(deletePurpose.value)) {
      const requests = []
      if (credentialStatus.value?.serpapi?.is_configured) {
        requests.push(deleteApiCredential('SERPAPI'))
      }
      if (credentialStatus.value?.serper?.is_configured) {
        requests.push(deleteApiCredential('SERPER'))
      }
      if (requests.length) {
        await Promise.all(requests)
      }
    } else {
      await deleteLLMPurposeConfig(deletePurpose.value)
    }
    showSuccess(t('admin.llmConfig.messages.deleted'))
    await fetchData()
    deleteDialogOpen.value = false
  } catch {
    showError(t('admin.llmConfig.messages.deleteError'))
  } finally {
    deleting.value = false
    deletePurpose.value = null
  }
}
</script>
