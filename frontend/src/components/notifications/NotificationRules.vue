<template>
  <v-card>
    <v-card-title class="d-flex justify-space-between align-center">
      <span>Benachrichtigungs-Regeln</span>
      <v-btn color="primary" @click="openCreateDialog">
        <v-icon start>mdi-plus</v-icon>
        Neue Regel
      </v-btn>
    </v-card-title>

    <v-card-text>
      <v-progress-linear v-if="loading" indeterminate class="mb-4" />

      <v-data-table
        v-if="rules.length > 0"
        :headers="headers"
        :items="rules"
        :loading="loading"
        class="elevation-0"
      >
        <template v-slot:item.event_type="{ item }">
          <v-chip size="small" :color="getEventTypeColor(item.event_type)">
            {{ getEventTypeLabel(item.event_type) }}
          </v-chip>
        </template>

        <template v-slot:item.channel="{ item }">
          <v-chip size="small" :color="getChannelColor(item.channel)">
            <v-icon start size="small">{{ getChannelIcon(item.channel) }}</v-icon>
            {{ getChannelLabel(item.channel) }}
          </v-chip>
        </template>

        <template v-slot:item.is_active="{ item }">
          <v-switch
            :model-value="item.is_active"
            @update:model-value="handleToggleActive(item)"
            color="success"
            hide-details
            density="compact"
          />
        </template>

        <template v-slot:item.trigger_count="{ item }">
          <span>{{ item.trigger_count }}</span>
          <span v-if="item.last_triggered" class="text-caption text-medium-emphasis ml-1">
            (zuletzt: {{ formatDate(item.last_triggered) }})
          </span>
        </template>

        <template v-slot:item.actions="{ item }">
          <div class="d-flex justify-end">
            <v-btn
              icon="mdi-pencil"
              size="small"
              variant="text"
              title="Bearbeiten"
              @click="openEditDialog(item)"
            />
            <v-btn
              icon="mdi-delete"
              size="small"
              variant="text"
              color="error"
              title="Loeschen"
              @click="confirmDelete(item)"
            />
          </div>
        </template>
      </v-data-table>

      <v-alert v-else-if="!loading" type="info" variant="tonal">
        Noch keine Regeln erstellt. Klicken Sie auf "Neue Regel" um eine Benachrichtigungsregel zu erstellen.
      </v-alert>
    </v-card-text>
  </v-card>

  <!-- Create/Edit Rule Dialog -->
  <v-dialog v-model="ruleDialog" max-width="700" persistent>
    <v-card>
      <v-card-title>{{ editMode ? 'Regel bearbeiten' : 'Neue Regel erstellen' }}</v-card-title>
      <v-card-text>
        <v-form ref="formRef" v-model="formValid">
          <v-text-field
            v-model="formData.name"
            label="Name"
            :rules="[v => !!v || 'Name ist erforderlich']"
            class="mb-2"
          />

          <v-textarea
            v-model="formData.description"
            label="Beschreibung (optional)"
            rows="2"
            class="mb-2"
          />

          <v-select
            v-model="formData.event_type"
            :items="eventTypeOptions"
            label="Event-Typ"
            :rules="[v => !!v || 'Event-Typ ist erforderlich']"
            class="mb-2"
          >
            <template v-slot:item="{ item, props }">
              <v-list-item v-bind="props">
                <template v-slot:subtitle>
                  {{ item.raw.description }}
                </template>
              </v-list-item>
            </template>
          </v-select>

          <v-select
            v-model="formData.channel"
            :items="channelOptions"
            label="Benachrichtigungs-Kanal"
            :rules="[v => !!v || 'Kanal ist erforderlich']"
            class="mb-2"
          >
            <template v-slot:item="{ item, props }">
              <v-list-item v-bind="props" :disabled="!item.raw.available">
                <template v-slot:subtitle>
                  {{ item.raw.description }}
                </template>
              </v-list-item>
            </template>
          </v-select>

          <!-- Channel-specific config: EMAIL -->
          <template v-if="formData.channel === 'EMAIL'">
            <v-divider class="my-4" />
            <h4 class="mb-2">Email-Konfiguration</h4>
            <v-select
              v-model="formData.channel_config.email_address_ids"
              :items="emailAddressOptions"
              label="Email-Adressen"
              multiple
              chips
              hint="Leer lassen um an die Haupt-Email zu senden"
              persistent-hint
              class="mb-2"
            />
            <v-checkbox
              v-model="formData.channel_config.include_primary"
              label="Auch an Haupt-Email senden"
              hide-details
            />
          </template>

          <!-- Channel-specific config: WEBHOOK -->
          <template v-if="formData.channel === 'WEBHOOK'">
            <v-divider class="my-4" />
            <h4 class="mb-2">Webhook-Konfiguration</h4>
            <v-text-field
              v-model="formData.channel_config.url"
              label="Webhook URL"
              :rules="[v => !!v || 'URL ist erforderlich', v => isValidUrl(v) || 'Unguelige URL']"
              class="mb-2"
            />
            <v-select
              v-model="webhookAuthType"
              :items="webhookAuthOptions"
              label="Authentifizierung"
              class="mb-2"
            />
            <v-text-field
              v-if="webhookAuthType === 'bearer'"
              v-model="formData.channel_config.auth.token"
              label="Bearer Token"
              class="mb-2"
            />
            <v-row v-if="webhookAuthType === 'basic'">
              <v-col cols="6">
                <v-text-field
                  v-model="formData.channel_config.auth.username"
                  label="Benutzername"
                />
              </v-col>
              <v-col cols="6">
                <v-text-field
                  v-model="formData.channel_config.auth.password"
                  label="Passwort"
                  type="password"
                />
              </v-col>
            </v-row>
            <v-btn
              variant="outlined"
              size="small"
              :loading="testingWebhook"
              @click="handleTestWebhook"
              class="mt-2"
            >
              <v-icon start>mdi-test-tube</v-icon>
              Webhook testen
            </v-btn>
            <v-alert
              v-if="webhookTestResult"
              :type="webhookTestResult.success ? 'success' : 'error'"
              variant="tonal"
              class="mt-2"
              density="compact"
            >
              {{ webhookTestResult.success ? 'Webhook erfolgreich getestet!' : webhookTestResult.error || 'Webhook-Test fehlgeschlagen' }}
            </v-alert>
          </template>

          <!-- Filter Conditions -->
          <v-divider class="my-4" />
          <h4 class="mb-2">Filter-Bedingungen (optional)</h4>
          <p class="text-caption text-medium-emphasis mb-3">
            Lassen Sie die Felder leer, um alle Events dieses Typs zu erhalten.
          </p>

          <v-text-field
            v-model.number="formData.conditions.min_confidence"
            label="Mindest-Konfidenz"
            type="number"
            min="0"
            max="1"
            step="0.1"
            hint="z.B. 0.7 fuer 70% (nur fuer AI-Events relevant)"
            persistent-hint
            class="mb-2"
          />

          <v-combobox
            v-model="formData.conditions.keywords"
            label="Schlusselwoerter"
            chips
            multiple
            hint="Mindestens eines muss im Titel/Text vorkommen"
            persistent-hint
            class="mb-2"
          />

          <!-- Digest Settings -->
          <v-divider class="my-4" />
          <h4 class="mb-2">Sammelbenachrichtigungen</h4>

          <v-switch
            v-model="formData.digest_enabled"
            label="Sammelmeldungen aktivieren"
            color="primary"
            hint="Statt einzelner Benachrichtigungen eine Zusammenfassung senden"
            persistent-hint
          />

          <v-select
            v-if="formData.digest_enabled"
            v-model="formData.digest_frequency"
            :items="digestFrequencyOptions"
            label="Haeufigkeit"
            class="mt-2"
          />

          <v-divider class="my-4" />

          <v-switch
            v-model="formData.is_active"
            label="Regel aktiv"
            color="success"
          />
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="closeDialog">Abbrechen</v-btn>
        <v-btn color="primary" :disabled="!formValid" :loading="loading" @click="saveRule">
          Speichern
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Delete Confirmation -->
  <v-dialog v-model="deleteDialog" max-width="400">
    <v-card>
      <v-card-title>Regel loeschen?</v-card-title>
      <v-card-text>
        Moechten Sie die Regel "{{ ruleToDelete?.name }}" wirklich loeschen?
        Diese Aktion kann nicht rueckgaengig gemacht werden.
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="deleteDialog = false">Abbrechen</v-btn>
        <v-btn color="error" @click="handleDelete">Loeschen</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useNotifications, type NotificationRule } from '@/composables/useNotifications'
import { format } from 'date-fns'
import { de } from 'date-fns/locale'

const {
  rules,
  emailAddresses,
  eventTypes,
  channels,
  loading,
  loadRules,
  loadEmailAddresses,
  loadMeta,
  createRule,
  updateRule,
  deleteRule,
  toggleRuleActive,
  testWebhook,
} = useNotifications()

// Table headers
const headers = [
  { title: 'Name', key: 'name', sortable: true },
  { title: 'Event-Typ', key: 'event_type', sortable: true },
  { title: 'Kanal', key: 'channel', sortable: true },
  { title: 'Aktiv', key: 'is_active', sortable: true, width: '80px', align: 'center' },
  { title: 'Ausloesungen', key: 'trigger_count', sortable: true },
  { title: '', key: 'actions', sortable: false, width: '90px', align: 'end' },
]

// Dialog state
const ruleDialog = ref(false)
const deleteDialog = ref(false)
const editMode = ref(false)
const editingRuleId = ref<string | null>(null)
const ruleToDelete = ref<NotificationRule | null>(null)
const formRef = ref()
const formValid = ref(false)

// Webhook testing
const testingWebhook = ref(false)
const webhookTestResult = ref<{ success: boolean; error?: string } | null>(null)
const webhookAuthType = ref('none')

// Form data
const getEmptyFormData = () => ({
  name: '',
  description: '',
  event_type: '',
  channel: '',
  conditions: {
    min_confidence: null as number | null,
    keywords: [] as string[],
  },
  channel_config: {
    email_address_ids: [] as string[],
    include_primary: true,
    url: '',
    auth: {
      type: 'none',
      token: '',
      username: '',
      password: '',
    },
  },
  digest_enabled: false,
  digest_frequency: 'daily',
  is_active: true,
})

const formData = ref(getEmptyFormData())

// Options
const eventTypeOptions = computed(() =>
  eventTypes.value.map((e) => ({
    title: e.label,
    value: e.value,
    description: e.description,
  }))
)

const channelOptions = computed(() =>
  channels.value.map((c) => ({
    title: c.label,
    value: c.value,
    description: c.description,
    available: c.available,
  }))
)

const emailAddressOptions = computed(() =>
  emailAddresses.value
    .filter((ea) => ea.is_verified)
    .map((ea) => ({
      title: ea.label ? `${ea.email} (${ea.label})` : ea.email,
      value: ea.id,
    }))
)

const webhookAuthOptions = [
  { title: 'Keine', value: 'none' },
  { title: 'Bearer Token', value: 'bearer' },
  { title: 'Basic Auth', value: 'basic' },
]

const digestFrequencyOptions = [
  { title: 'Stuendlich', value: 'hourly' },
  { title: 'Taeglich', value: 'daily' },
  { title: 'Woechentlich', value: 'weekly' },
]

// Methods
const openCreateDialog = () => {
  editMode.value = false
  editingRuleId.value = null
  formData.value = getEmptyFormData()
  webhookAuthType.value = 'none'
  webhookTestResult.value = null
  ruleDialog.value = true
}

const openEditDialog = (rule: NotificationRule) => {
  editMode.value = true
  editingRuleId.value = rule.id
  formData.value = {
    name: rule.name,
    description: rule.description || '',
    event_type: rule.event_type,
    channel: rule.channel,
    conditions: {
      min_confidence: rule.conditions.min_confidence || null,
      keywords: rule.conditions.keywords || [],
    },
    channel_config: {
      email_address_ids: rule.channel_config.email_address_ids || [],
      include_primary: rule.channel_config.include_primary !== false,
      url: rule.channel_config.url || '',
      auth: rule.channel_config.auth || { type: 'none', token: '', username: '', password: '' },
    },
    digest_enabled: rule.digest_enabled,
    digest_frequency: rule.digest_frequency || 'daily',
    is_active: rule.is_active,
  }
  webhookAuthType.value = rule.channel_config.auth?.type || 'none'
  webhookTestResult.value = null
  ruleDialog.value = true
}

const closeDialog = () => {
  ruleDialog.value = false
  formData.value = getEmptyFormData()
}

const saveRule = async () => {
  if (!formRef.value) return

  const { valid } = await formRef.value.validate()
  if (!valid) return

  // Build the rule data
  const data: any = {
    name: formData.value.name,
    description: formData.value.description || null,
    event_type: formData.value.event_type,
    channel: formData.value.channel,
    conditions: {},
    channel_config: {},
    digest_enabled: formData.value.digest_enabled,
    digest_frequency: formData.value.digest_enabled ? formData.value.digest_frequency : null,
    is_active: formData.value.is_active,
  }

  // Add conditions if set
  if (formData.value.conditions.min_confidence) {
    data.conditions.min_confidence = formData.value.conditions.min_confidence
  }
  if (formData.value.conditions.keywords?.length > 0) {
    data.conditions.keywords = formData.value.conditions.keywords
  }

  // Add channel config based on channel type
  if (formData.value.channel === 'EMAIL') {
    if (formData.value.channel_config.email_address_ids.length > 0) {
      data.channel_config.email_address_ids = formData.value.channel_config.email_address_ids
    }
    data.channel_config.include_primary = formData.value.channel_config.include_primary
  } else if (formData.value.channel === 'WEBHOOK') {
    data.channel_config.url = formData.value.channel_config.url
    if (webhookAuthType.value !== 'none') {
      data.channel_config.auth = {
        type: webhookAuthType.value,
        ...formData.value.channel_config.auth,
      }
    }
  }

  try {
    if (editMode.value && editingRuleId.value) {
      await updateRule(editingRuleId.value, data)
    } else {
      await createRule(data)
    }
    closeDialog()
  } catch (e) {
    console.error('Failed to save rule:', e)
  }
}

const confirmDelete = (rule: NotificationRule) => {
  ruleToDelete.value = rule
  deleteDialog.value = true
}

const handleDelete = async () => {
  if (!ruleToDelete.value) return

  try {
    await deleteRule(ruleToDelete.value.id)
    deleteDialog.value = false
    ruleToDelete.value = null
  } catch (e) {
    console.error('Failed to delete rule:', e)
  }
}

const handleToggleActive = async (rule: NotificationRule) => {
  try {
    await toggleRuleActive(rule)
  } catch (e) {
    console.error('Failed to toggle rule:', e)
  }
}

const handleTestWebhook = async () => {
  if (!formData.value.channel_config.url) return

  testingWebhook.value = true
  webhookTestResult.value = null

  try {
    const auth = webhookAuthType.value !== 'none'
      ? { type: webhookAuthType.value, ...formData.value.channel_config.auth }
      : undefined

    const result = await testWebhook(formData.value.channel_config.url, auth)
    webhookTestResult.value = result
  } catch (e: any) {
    webhookTestResult.value = { success: false, error: e.message }
  } finally {
    testingWebhook.value = false
  }
}

// Helpers
const formatDate = (dateStr: string) => {
  return format(new Date(dateStr), 'dd.MM.yy HH:mm', { locale: de })
}

const isValidUrl = (url: string) => {
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}

const getEventTypeColor = (eventType: string): string => {
  const colors: Record<string, string> = {
    NEW_DOCUMENT: 'success',
    DOCUMENT_CHANGED: 'info',
    DOCUMENT_REMOVED: 'error',
    CRAWL_COMPLETED: 'success',
    CRAWL_FAILED: 'error',
    AI_ANALYSIS_COMPLETED: 'cyan',
    HIGH_CONFIDENCE_RESULT: 'orange',
  }
  return colors[eventType] || 'grey'
}

const getEventTypeLabel = (eventType: string): string => {
  const type = eventTypes.value.find((e) => e.value === eventType)
  return type?.label || eventType
}

const getChannelColor = (channel: string): string => {
  const colors: Record<string, string> = {
    EMAIL: 'blue',
    WEBHOOK: 'purple',
    IN_APP: 'green',
    MS_TEAMS: 'indigo',
  }
  return colors[channel] || 'grey'
}

const getChannelIcon = (channel: string): string => {
  const icons: Record<string, string> = {
    EMAIL: 'mdi-email',
    WEBHOOK: 'mdi-webhook',
    IN_APP: 'mdi-bell',
    MS_TEAMS: 'mdi-microsoft-teams',
  }
  return icons[channel] || 'mdi-bell'
}

const getChannelLabel = (channel: string): string => {
  const ch = channels.value.find((c) => c.value === channel)
  return ch?.label || channel
}

// Watch for auth type changes
watch(webhookAuthType, (newType) => {
  formData.value.channel_config.auth.type = newType
})

// Init
onMounted(async () => {
  await loadMeta()
  await loadEmailAddresses()
  await loadRules()
})
</script>
