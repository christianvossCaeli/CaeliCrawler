<template>
  <v-card>
    <v-card-title>{{ t('notificationsView.settings') }}</v-card-title>

    <v-card-text>
      <!-- Global Preferences -->
      <v-card variant="outlined" class="mb-6">
        <v-card-title class="text-subtitle-1">{{ t('notifications.settings.generalSettings') }}</v-card-title>
        <v-card-text>
          <v-switch
            v-model="localPreferences.notifications_enabled"
            :label="t('notifications.settings.notificationsEnabled')"
            color="primary"
            hide-details
            class="mb-4"
            @update:model-value="handlePreferencesChange"
          />

          <v-text-field
            v-model="localPreferences.notification_digest_time"
            :label="t('notifications.settings.digestTime')"
            type="time"
            :hint="t('notifications.settings.digestTimeHint')"
            persistent-hint
            :disabled="!localPreferences.notifications_enabled"
            @update:model-value="handlePreferencesChange"
          />
        </v-card-text>
      </v-card>

      <!-- Email Addresses -->
      <v-card variant="outlined">
        <v-card-title class="d-flex justify-space-between align-center">
          <span class="text-subtitle-1">{{ t('notifications.settings.emailAddresses') }}</span>
          <v-btn
            color="primary"
            size="small"
            prepend-icon="mdi-plus"
            @click="openAddEmailDialog"
          >
            {{ t('common.add') }}
          </v-btn>
        </v-card-title>

        <v-card-text>
          <v-alert v-if="emailAddresses.length === 0" type="info" variant="tonal" class="mb-4">
            {{ t('notifications.settings.noEmailAddresses') }}
          </v-alert>

          <v-list v-else>
            <v-list-item
              v-for="email in emailAddresses"
              :key="email.id"
              class="mb-2 rounded"
              :class="getPrimaryEmailClass(email)"
            >
              <template v-slot:prepend>
                <v-icon :color="email.is_verified ? 'success' : 'warning'">
                  {{ email.is_verified ? 'mdi-email-check' : 'mdi-email-alert' }}
                </v-icon>
              </template>

              <v-list-item-title>
                {{ email.email }}
                <v-chip v-if="email.is_primary" size="x-small" color="primary" class="ml-2">
                  {{ t('notifications.settings.primary') }}
                </v-chip>
                <v-chip
                  v-if="!email.is_verified"
                  size="x-small"
                  color="warning"
                  class="ml-2"
                >
                  {{ t('notifications.settings.notVerified') }}
                </v-chip>
              </v-list-item-title>
              <v-list-item-subtitle v-if="email.label">
                {{ email.label }}
              </v-list-item-subtitle>

              <template v-slot:append>
                <v-btn
                  v-if="!email.is_verified"
                  icon="mdi-email-send"
                  variant="text"
                  size="small"
                  color="primary"
                  :title="t('notifications.settings.resendVerification')"
                  @click="resendVerification(email)"
                />
                <v-btn
                  v-if="!email.is_primary"
                  icon="mdi-delete"
                  variant="text"
                  size="small"
                  color="error"
                  @click="confirmDeleteEmail(email)"
                />
              </template>
            </v-list-item>
          </v-list>
        </v-card-text>
      </v-card>
    </v-card-text>
  </v-card>

  <!-- Add Email Dialog -->
  <v-dialog v-model="addEmailDialog" max-width="500">
    <v-card>
      <v-card-title>{{ t('notifications.settings.addEmailTitle') }}</v-card-title>
      <v-card-text>
        <v-form ref="emailForm" @submit.prevent="handleAddEmail">
          <v-text-field
            v-model="newEmail.email"
            :label="t('notifications.settings.emailAddress')"
            type="email"
            :rules="emailRules"
            required
            class="mb-4"
          />
          <v-text-field
            v-model="newEmail.label"
            :label="t('notifications.settings.labelOptional')"
            :hint="t('notifications.settings.labelHint')"
            persistent-hint
          />
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="addEmailDialog = false">{{ t('common.cancel') }}</v-btn>
        <v-btn color="primary" :loading="saving" @click="handleAddEmail">
          {{ t('common.add') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Delete Confirmation Dialog -->
  <v-dialog v-model="deleteEmailDialog" max-width="400">
    <v-card>
      <v-card-title>{{ t('notifications.settings.deleteEmailTitle') }}</v-card-title>
      <v-card-text>
        {{ t('notifications.settings.deleteEmailConfirm', { email: emailToDelete?.email }) }}
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="deleteEmailDialog = false">{{ t('common.cancel') }}</v-btn>
        <v-btn color="error" :loading="saving" @click="handleDeleteEmail">
          {{ t('common.delete') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Snackbar -->
  <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000">
    {{ snackbar.message }}
  </v-snackbar>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useTheme } from 'vuetify'
import { useI18n } from 'vue-i18n'
import { useNotifications, type UserEmailAddress, type NotificationPreferences } from '@/composables/useNotifications'

const { t } = useI18n()

const theme = useTheme()
const isDark = computed(() => theme.global.current.value.dark)

const {
  emailAddresses,
  preferences,
  loadEmailAddresses,
  loadPreferences,
  addEmailAddress,
  deleteEmailAddress,
  updatePreferences,
} = useNotifications()

// Local state
const saving = ref(false)
const addEmailDialog = ref(false)
const deleteEmailDialog = ref(false)
const emailToDelete = ref<UserEmailAddress | null>(null)
const emailForm = ref()

const localPreferences = ref<NotificationPreferences>({
  notifications_enabled: true,
  notification_digest_time: undefined,
})

const newEmail = ref({
  email: '',
  label: '',
})

const snackbar = ref({
  show: false,
  message: '',
  color: 'success',
})

// Validation rules
const emailRules = computed(() => [
  (v: string) => !!v || t('notifications.settings.emailRequired'),
  (v: string) => /.+@.+\..+/.test(v) || t('notifications.settings.emailInvalid'),
])

// Watch preferences changes
watch(preferences, (newVal) => {
  localPreferences.value = { ...newVal }
}, { immediate: true })

// Methods
const showSnackbar = (message: string, color: string = 'success') => {
  snackbar.value = { show: true, message, color }
}

const handlePreferencesChange = async () => {
  try {
    await updatePreferences(localPreferences.value)
    showSnackbar(t('notifications.settings.settingsSaved'))
  } catch (e) {
    showSnackbar(t('notifications.settings.settingsError'), 'error')
  }
}

const openAddEmailDialog = () => {
  newEmail.value = { email: '', label: '' }
  addEmailDialog.value = true
}

const handleAddEmail = async () => {
  const { valid } = await emailForm.value.validate()
  if (!valid) return

  saving.value = true
  try {
    await addEmailAddress({
      email: newEmail.value.email,
      label: newEmail.value.label || undefined,
    })
    addEmailDialog.value = false
    showSnackbar(t('notifications.settings.emailAdded'))
  } catch (e) {
    showSnackbar(t('notifications.settings.emailAddError'), 'error')
  } finally {
    saving.value = false
  }
}

const confirmDeleteEmail = (email: UserEmailAddress) => {
  emailToDelete.value = email
  deleteEmailDialog.value = true
}

const handleDeleteEmail = async () => {
  if (!emailToDelete.value) return

  saving.value = true
  try {
    await deleteEmailAddress(emailToDelete.value.id)
    deleteEmailDialog.value = false
    showSnackbar(t('notifications.settings.emailDeleted'))
  } catch (e) {
    showSnackbar(t('notifications.settings.emailDeleteError'), 'error')
  } finally {
    saving.value = false
  }
}

const resendVerification = async (_email: UserEmailAddress) => {
  // TODO: Implement resend verification endpoint - _email will be used when endpoint is added
  showSnackbar(t('notifications.settings.verificationResent'))
}

// Dark mode aware styling
const getPrimaryEmailClass = (email: UserEmailAddress): string => {
  if (!email.is_primary) return ''
  return isDark.value ? 'bg-grey-darken-3' : 'bg-grey-lighten-4'
}

// Init
onMounted(async () => {
  await loadPreferences()
  await loadEmailAddresses()
})
</script>
