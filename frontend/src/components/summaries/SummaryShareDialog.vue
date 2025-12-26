<template>
  <v-dialog
    v-model="modelValue"
    max-width="500"
    role="dialog"
    aria-modal="true"
    :aria-labelledby="dialogTitleId"
  >
    <v-card>
      <v-card-title :id="dialogTitleId">
        <v-icon color="primary" class="mr-2">mdi-share-variant</v-icon>
        {{ t('summaries.shareSummary') }}
      </v-card-title>

      <v-card-text>
        <!-- Existing Shares -->
        <div v-if="shares.length > 0" class="mb-6">
          <div class="text-subtitle-2 mb-2">{{ t('summaries.existingShares') }}</div>
          <v-list density="compact" variant="outlined" rounded>
            <v-list-item
              v-for="share in shares"
              :key="share.id"
              :class="{ 'text-disabled': !share.is_active }"
            >
              <template #prepend>
                <v-icon
                  :icon="share.has_password ? 'mdi-lock' : 'mdi-lock-open'"
                  :color="share.is_active ? 'primary' : 'grey'"
                  size="small"
                />
              </template>

              <v-list-item-title class="text-body-2">
                {{ share.share_url }}
              </v-list-item-title>
              <v-list-item-subtitle>
                {{ share.view_count }} {{ t('summaries.views') }}
                <span v-if="share.expires_at">
                  &bull; {{ t('summaries.expiresAt') }} {{ formatDate(share.expires_at) }}
                </span>
              </v-list-item-subtitle>

              <template #append>
                <v-btn
                  icon="mdi-content-copy"
                  size="small"
                  variant="text"
                  :disabled="!share.is_active"
                  :aria-label="t('summaries.copyShareLink')"
                  @click="copyShareUrl(share)"
                />
                <v-btn
                  icon="mdi-close"
                  size="small"
                  variant="text"
                  color="error"
                  :disabled="!share.is_active"
                  :aria-label="t('summaries.deactivateShareLink')"
                  @click="deactivateShare(share)"
                />
              </template>
            </v-list-item>
          </v-list>
        </div>

        <!-- Create New Share -->
        <div class="text-subtitle-2 mb-2">{{ t('summaries.createNewShare') }}</div>

        <v-text-field
          v-model="newShare.password"
          :label="t('summaries.sharePassword')"
          :hint="t('summaries.sharePasswordHint')"
          persistent-hint
          type="password"
          class="mb-4"
        />

        <v-select
          v-model="newShare.expires_days"
          :items="expiryOptions"
          :label="t('summaries.shareExpiry')"
          class="mb-4"
        />

        <v-switch
          v-model="newShare.allow_export"
          :label="t('summaries.allowExport')"
          :hint="t('summaries.allowExportHint')"
          persistent-hint
          color="primary"
        />
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-btn variant="text" @click="close">
          {{ t('common.close') }}
        </v-btn>
        <v-spacer />
        <v-btn
          color="primary"
          variant="flat"
          :loading="isCreating"
          @click="createShare"
        >
          <v-icon start>mdi-link-plus</v-icon>
          {{ t('summaries.createShareLink') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCustomSummariesStore, type CustomSummary, type SummaryShare } from '@/stores/customSummaries'
import { useSnackbar } from '@/composables/useSnackbar'
import { useDialogFocus } from '@/composables'
import { useLogger } from '@/composables/useLogger'

const modelValue = defineModel<boolean>()

const props = defineProps<{
  summary: CustomSummary
}>()

const logger = useLogger('SummaryShareDialog')

const { t } = useI18n()
const store = useCustomSummariesStore()
const { showSuccess, showError } = useSnackbar()

// ARIA
const dialogTitleId = `summary-share-dialog-title-${Math.random().toString(36).slice(2, 9)}`

// Focus management for accessibility
useDialogFocus({ isOpen: modelValue })

// State
const shares = ref<SummaryShare[]>([])
const isCreating = ref(false)
const isLoading = ref(false)

const newShare = ref({
  password: '',
  expires_days: 30,
  allow_export: false,
})

const expiryOptions = computed(() => [
  { title: t('summaries.expiry7Days'), value: 7 },
  { title: t('summaries.expiry30Days'), value: 30 },
  { title: t('summaries.expiry90Days'), value: 90 },
  { title: t('summaries.expiry1Year'), value: 365 },
  { title: t('summaries.expiryNever'), value: null },
])

async function loadShares() {
  isLoading.value = true
  try {
    shares.value = await store.listShareLinks(props.summary.id)
  } finally {
    isLoading.value = false
  }
}

async function createShare() {
  isCreating.value = true
  try {
    const share = await store.createShareLink(props.summary.id, {
      password: newShare.value.password || undefined,
      expires_days: newShare.value.expires_days || undefined,
      allow_export: newShare.value.allow_export,
    })

    if (share) {
      shares.value.unshift(share)
      copyShareUrl(share)
      showSuccess(t('summaries.shareLinkCreated'))

      // Reset form
      newShare.value = {
        password: '',
        expires_days: 30,
        allow_export: false,
      }
    }
  } catch (e) {
    showError(t('summaries.shareLinkError'))
  } finally {
    isCreating.value = false
  }
}

async function deactivateShare(share: SummaryShare) {
  try {
    const success = await store.deactivateShareLink(props.summary.id, share.id)
    if (success) {
      share.is_active = false
      showSuccess(t('summaries.shareLinkDeactivated'))
    }
  } catch (e) {
    showError(t('summaries.shareLinkDeactivateError'))
  }
}

async function copyShareUrl(share: SummaryShare) {
  const fullUrl = `${window.location.origin}${share.share_url}`

  // Try modern Clipboard API first
  if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
    try {
      await navigator.clipboard.writeText(fullUrl)
      showSuccess(t('summaries.shareLinkCopied'))
      return
    } catch (e) {
      logger.warn('Clipboard API failed, using fallback:', e)
    }
  }

  // Fallback for older browsers or when Clipboard API is unavailable
  try {
    const textArea = document.createElement('textarea')
    textArea.value = fullUrl
    textArea.style.position = 'fixed'
    textArea.style.left = '-9999px'
    textArea.style.top = '0'
    textArea.setAttribute('readonly', '')
    document.body.appendChild(textArea)
    textArea.select()
    const success = document.execCommand('copy')
    document.body.removeChild(textArea)

    if (success) {
      showSuccess(t('summaries.shareLinkCopied'))
    } else {
      showError(t('common.copyFailed'))
    }
  } catch (e) {
    logger.error('Copy fallback failed:', e)
    showError(t('common.copyFailed'))
  }
}

function formatDate(dateStr: string): string {
  // Use browser locale for consistent date formatting
  return new Date(dateStr).toLocaleDateString(undefined, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

function close() {
  modelValue.value = false
}

// Load shares when dialog opens
watch(modelValue, (isOpen) => {
  if (isOpen) {
    loadShares()
  }
})
</script>
