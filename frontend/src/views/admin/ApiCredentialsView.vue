<template>
  <v-container fluid>
    <!-- Header -->
    <PageHeader
      :title="t('admin.llmConfig.title')"
      :subtitle="t('admin.llmConfig.subtitle')"
      icon="mdi-brain"
    />

    <!-- Info Alert -->
    <v-alert
      type="info"
      variant="tonal"
      class="mb-6"
      :title="t('admin.llmConfig.info.title')"
    >
      {{ t('admin.llmConfig.info.description') }}
    </v-alert>

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
          <PurposeConfigCard
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
    <v-dialog v-model="deleteDialogOpen" max-width="400">
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
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSnackbar } from '@/composables/useSnackbar'
import PageHeader from '@/components/common/PageHeader.vue'
import PurposeConfigCard from '@/components/admin/PurposeConfigCard.vue'
import {
  getLLMPurposes,
  getLLMConfigStatus,
  saveLLMPurposeConfig,
  deleteLLMPurposeConfig,
  testLLMPurposeConfig,
  type PurposeInfo,
  type PurposeConfigStatus,
} from '@/services/api/admin'

const { t } = useI18n()
const { showSuccess, showError } = useSnackbar()

// State
const loading = ref(true)
const purposes = ref<PurposeInfo[]>([])
const configStatus = ref<PurposeConfigStatus[]>([])
const savingPurpose = ref<string | null>(null)
const testingPurpose = ref<string | null>(null)
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
    const [purposesResponse, statusResponse] = await Promise.all([
      getLLMPurposes(),
      getLLMConfigStatus(),
    ])
    purposes.value = purposesResponse.data.purposes
    configStatus.value = statusResponse.data.configs
  } catch {
    showError(t('admin.llmConfig.messages.loadError'))
  } finally {
    loading.value = false
  }
}

function getStatusForPurpose(purpose: string): PurposeConfigStatus | undefined {
  return configStatus.value.find(s => s.purpose === purpose)
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

function openDeleteDialog(purpose: string) {
  deletePurpose.value = purpose
  deleteDialogOpen.value = true
}

async function confirmDelete() {
  if (!deletePurpose.value) return

  deleting.value = true
  try {
    await deleteLLMPurposeConfig(deletePurpose.value)
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
