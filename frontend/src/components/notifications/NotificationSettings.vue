<template>
  <v-card>
    <v-card-title>Einstellungen</v-card-title>

    <v-card-text>
      <!-- Global Preferences -->
      <v-card variant="outlined" class="mb-6">
        <v-card-title class="text-subtitle-1">Allgemeine Einstellungen</v-card-title>
        <v-card-text>
          <v-switch
            v-model="localPreferences.notifications_enabled"
            label="Benachrichtigungen aktiviert"
            color="primary"
            hide-details
            class="mb-4"
            @update:model-value="handlePreferencesChange"
          />

          <v-text-field
            v-model="localPreferences.notification_digest_time"
            label="Digest-Uhrzeit"
            type="time"
            hint="Uhrzeit fuer taegliche Zusammenfassungen"
            persistent-hint
            :disabled="!localPreferences.notifications_enabled"
            @update:model-value="handlePreferencesChange"
          />
        </v-card-text>
      </v-card>

      <!-- Email Addresses -->
      <v-card variant="outlined">
        <v-card-title class="d-flex justify-space-between align-center">
          <span class="text-subtitle-1">E-Mail-Adressen</span>
          <v-btn
            color="primary"
            size="small"
            prepend-icon="mdi-plus"
            @click="openAddEmailDialog"
          >
            Hinzufuegen
          </v-btn>
        </v-card-title>

        <v-card-text>
          <v-alert v-if="emailAddresses.length === 0" type="info" variant="tonal" class="mb-4">
            Keine zusaetzlichen E-Mail-Adressen konfiguriert. Benachrichtigungen werden an Ihre
            Haupt-E-Mail-Adresse gesendet.
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
                  Primaer
                </v-chip>
                <v-chip
                  v-if="!email.is_verified"
                  size="x-small"
                  color="warning"
                  class="ml-2"
                >
                  Nicht verifiziert
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
                  title="Verifizierungs-E-Mail erneut senden"
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
      <v-card-title>E-Mail-Adresse hinzufuegen</v-card-title>
      <v-card-text>
        <v-form ref="emailForm" @submit.prevent="handleAddEmail">
          <v-text-field
            v-model="newEmail.email"
            label="E-Mail-Adresse"
            type="email"
            :rules="emailRules"
            required
            class="mb-4"
          />
          <v-text-field
            v-model="newEmail.label"
            label="Bezeichnung (optional)"
            hint="z.B. 'Arbeit', 'Privat'"
            persistent-hint
          />
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="addEmailDialog = false">Abbrechen</v-btn>
        <v-btn color="primary" :loading="saving" @click="handleAddEmail">
          Hinzufuegen
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Delete Confirmation Dialog -->
  <v-dialog v-model="deleteEmailDialog" max-width="400">
    <v-card>
      <v-card-title>E-Mail-Adresse loeschen?</v-card-title>
      <v-card-text>
        Moechten Sie die E-Mail-Adresse <strong>{{ emailToDelete?.email }}</strong> wirklich loeschen?
        Benachrichtigungen werden nicht mehr an diese Adresse gesendet.
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="deleteEmailDialog = false">Abbrechen</v-btn>
        <v-btn color="error" :loading="saving" @click="handleDeleteEmail">
          Loeschen
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
import { useNotifications, type UserEmailAddress, type NotificationPreferences } from '@/composables/useNotifications'

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
const emailRules = [
  (v: string) => !!v || 'E-Mail-Adresse ist erforderlich',
  (v: string) => /.+@.+\..+/.test(v) || 'Ungueltige E-Mail-Adresse',
]

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
    showSnackbar('Einstellungen gespeichert')
  } catch (e) {
    showSnackbar('Fehler beim Speichern der Einstellungen', 'error')
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
    showSnackbar('E-Mail-Adresse hinzugefuegt. Bitte bestaetigen Sie die Verifizierungs-E-Mail.')
  } catch (e) {
    showSnackbar('Fehler beim Hinzufuegen der E-Mail-Adresse', 'error')
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
    showSnackbar('E-Mail-Adresse geloescht')
  } catch (e) {
    showSnackbar('Fehler beim Loeschen der E-Mail-Adresse', 'error')
  } finally {
    saving.value = false
  }
}

const resendVerification = async (email: UserEmailAddress) => {
  // TODO: Implement resend verification endpoint
  showSnackbar('Verifizierungs-E-Mail wurde erneut gesendet')
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
