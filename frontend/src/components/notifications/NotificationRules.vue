<template>
  <v-card>
    <v-card-title class="d-flex justify-space-between align-center">
      <span>{{ t('notifications.rules.title') }}</span>
      <v-btn variant="tonal" color="primary" @click="openCreateDialog">
        <v-icon start>mdi-plus</v-icon>
        {{ t('notifications.rules.create') }}
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
        <template #item.event_type="{ item }">
          <v-chip size="small" :color="getEventTypeColor(item.event_type)">
            {{ getEventTypeLabel(item.event_type) }}
          </v-chip>
        </template>

        <template #item.channel="{ item }">
          <v-chip size="small" :color="getChannelColor(item.channel)">
            <v-icon start size="small">{{ getChannelIcon(item.channel) }}</v-icon>
            {{ getChannelLabel(item.channel) }}
          </v-chip>
        </template>

        <template #item.is_active="{ item }">
          <v-switch
            :model-value="item.is_active"
            color="success"
            hide-details
            density="compact"
            @update:model-value="handleToggleActive(item)"
          />
        </template>

        <template #item.trigger_count="{ item }">
          <span>{{ item.trigger_count }}</span>
          <span v-if="item.last_triggered" class="text-caption text-medium-emphasis ml-1">
            ({{ t('notifications.rules.lastTriggered') }}: {{ formatDate(item.last_triggered) }})
          </span>
        </template>

        <template #item.actions="{ item }">
          <div class="d-flex justify-end">
            <v-btn
              icon="mdi-pencil"
              size="small"
              variant="tonal"
              :title="t('common.edit')"
              @click="openEditDialog(item)"
            />
            <v-btn
              icon="mdi-delete"
              size="small"
              variant="tonal"
              color="error"
              :title="t('common.delete')"
              @click="confirmDelete(item)"
            />
          </div>
        </template>
      </v-data-table>

      <v-alert v-else-if="!loading" type="info" variant="tonal">
        {{ t('notifications.rules.noRules') }}
      </v-alert>
    </v-card-text>
  </v-card>

  <!-- Create/Edit Rule Dialog -->
  <v-dialog v-model="ruleDialog" max-width="700" persistent>
    <v-card>
      <v-card-title>{{ editMode ? t('notifications.rules.edit') : t('notifications.rules.createNew') }}</v-card-title>
      <v-card-text>
        <v-form ref="formRef" v-model="formValid">
          <v-text-field
            v-model="formData.name"
            :label="t('common.name')"
            :rules="[v => !!v || t('notifications.rules.nameRequired')]"
            class="mb-2"
          />

          <v-textarea
            v-model="formData.description"
            :label="t('notifications.rules.descriptionOptional')"
            rows="2"
            class="mb-2"
          />

          <v-select
            v-model="formData.event_type"
            :items="eventTypeOptions"
            :label="t('notifications.rules.eventType')"
            :rules="[v => !!v || t('notifications.rules.eventTypeRequired')]"
            class="mb-2"
          >
            <template #item="{ item, props }">
              <v-list-item v-bind="props">
                <template #subtitle>
                  {{ item.raw.description }}
                </template>
              </v-list-item>
            </template>
          </v-select>

          <v-select
            v-model="formData.channel"
            :items="channelOptions"
            :label="t('notifications.rules.channel')"
            :rules="[v => !!v || t('notifications.rules.channelRequired')]"
            class="mb-2"
          >
            <template #item="{ item, props }">
              <v-list-item v-bind="props" :disabled="!item.raw.available">
                <template #subtitle>
                  {{ item.raw.description }}
                </template>
              </v-list-item>
            </template>
          </v-select>

          <!-- Channel-specific config: EMAIL -->
          <template v-if="formData.channel === 'EMAIL'">
            <v-divider class="my-4" />
            <h4 class="mb-2">{{ t('notifications.rules.emailConfig') }}</h4>
            <v-select
              v-model="formData.channel_config.email_address_ids"
              :items="emailAddressOptions"
              :label="t('notifications.rules.emailAddresses')"
              multiple
              chips
              :hint="t('notifications.rules.emailAddressesHint')"
              persistent-hint
              class="mb-2"
            />
            <v-checkbox
              v-model="formData.channel_config.include_primary"
              :label="t('notifications.rules.includePrimary')"
              hide-details
            />
          </template>

          <!-- Channel-specific config: WEBHOOK -->
          <template v-if="formData.channel === 'WEBHOOK'">
            <v-divider class="my-4" />
            <h4 class="mb-2">{{ t('notifications.rules.webhookConfig') }}</h4>
            <v-text-field
              v-model="formData.channel_config.url"
              :label="t('notifications.rules.webhookUrl')"
              :rules="[v => !!v || t('notifications.rules.urlRequired'), v => isValidUrl(v) || t('notifications.rules.invalidUrl')]"
              class="mb-2"
            />
            <v-select
              v-model="webhookAuthType"
              :items="webhookAuthOptions"
              :label="t('notifications.rules.authentication')"
              class="mb-2"
            />
            <v-text-field
              v-if="webhookAuthType === 'bearer'"
              v-model="formData.channel_config.auth.token"
              :label="t('notifications.rules.bearerToken')"
              class="mb-2"
            />
            <v-row v-if="webhookAuthType === 'basic'">
              <v-col cols="6">
                <v-text-field
                  v-model="formData.channel_config.auth.username"
                  :label="t('notifications.rules.username')"
                />
              </v-col>
              <v-col cols="6">
                <v-text-field
                  v-model="formData.channel_config.auth.password"
                  :label="t('notifications.rules.password')"
                  type="password"
                />
              </v-col>
            </v-row>
            <v-btn
              variant="outlined"
              size="small"
              :loading="testingWebhook"
              class="mt-2"
              @click="handleTestWebhook"
            >
              <v-icon start>mdi-test-tube</v-icon>
              {{ t('notifications.rules.testWebhook') }}
            </v-btn>
            <v-alert
              v-if="webhookTestResult"
              :type="webhookTestResult.success ? 'success' : 'error'"
              variant="tonal"
              class="mt-2"
              density="compact"
            >
              {{ webhookTestResult.success ? t('notifications.rules.webhookTestSuccess') : webhookTestResult.error || t('notifications.rules.webhookTestFailed') }}
            </v-alert>
          </template>

          <!-- Filter Conditions -->
          <v-divider class="my-4" />
          <h4 class="mb-2">{{ t('notifications.rules.filterConditions') }}</h4>
          <p class="text-caption text-medium-emphasis mb-3">
            {{ t('notifications.rules.filterConditionsHint') }}
          </p>

          <v-number-input
            v-model="formData.conditions.min_confidence"
            :label="t('notifications.rules.minConfidence')"
            :min="0"
            :max="1"
            :step="0.1"
            :hint="t('notifications.rules.minConfidenceHint')"
            persistent-hint
            class="mb-2"
            control-variant="stacked"
          />

          <v-combobox
            v-model="formData.conditions.keywords"
            :label="t('notifications.rules.keywords')"
            chips
            multiple
            :hint="t('notifications.rules.keywordsHint')"
            persistent-hint
            class="mb-2"
          />

          <!-- Digest Settings -->
          <v-divider class="my-4" />
          <h4 class="mb-2">{{ t('notifications.rules.digestSettings') }}</h4>

          <v-switch
            v-model="formData.digest_enabled"
            :label="t('notifications.rules.digestEnabled')"
            color="primary"
            :hint="t('notifications.rules.digestEnabledHint')"
            persistent-hint
          />

          <v-select
            v-if="formData.digest_enabled"
            v-model="formData.digest_frequency"
            :items="digestFrequencyOptions"
            :label="t('notifications.rules.frequency')"
            class="mt-2"
          />

          <v-divider class="my-4" />

          <v-switch
            v-model="formData.is_active"
            :label="t('notifications.rules.ruleActive')"
            color="success"
          />
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="tonal" @click="closeDialog">{{ t('common.cancel') }}</v-btn>
        <v-btn variant="tonal" color="primary" :disabled="!formValid" :loading="loading" @click="saveRule">
          {{ t('common.save') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Delete Confirmation -->
  <v-dialog v-model="deleteDialog" max-width="400">
    <v-card>
      <v-card-title>{{ t('notifications.rules.deleteTitle') }}</v-card-title>
      <v-card-text>
        {{ t('notifications.rules.deleteConfirm', { name: ruleToDelete?.name }) }}
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="tonal" @click="deleteDialog = false">{{ t('common.cancel') }}</v-btn>
        <v-btn variant="tonal" color="error" @click="handleDelete">{{ t('common.delete') }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNotifications, type NotificationRule } from '@/composables/useNotifications'
import { useDialogFocus } from '@/composables'
import { format } from 'date-fns'
import { de } from 'date-fns/locale'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('NotificationRules')

const { t } = useI18n()

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
const headers = computed(() => [
  { title: t('common.name'), key: 'name', sortable: true },
  { title: t('notifications.rules.eventType'), key: 'event_type', sortable: true },
  { title: t('notifications.rules.channel'), key: 'channel', sortable: true },
  { title: t('notifications.rules.active'), key: 'is_active', sortable: true, width: '80px', align: 'center' as const },
  { title: t('notifications.rules.triggerCount'), key: 'trigger_count', sortable: true },
  { title: '', key: 'actions', sortable: false, width: '90px', align: 'end' as const },
])

// Dialog state
const ruleDialog = ref(false)
const deleteDialog = ref(false)
const editMode = ref(false)
const editingRuleId = ref<string | null>(null)
const ruleToDelete = ref<NotificationRule | null>(null)
const formRef = ref()
const formValid = ref(false)

// Focus management for accessibility (WCAG 2.1)
useDialogFocus({ isOpen: ruleDialog })
useDialogFocus({ isOpen: deleteDialog })

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

const webhookAuthOptions = computed(() => [
  { title: t('notifications.rules.authNone'), value: 'none' },
  { title: t('notifications.rules.authBearer'), value: 'bearer' },
  { title: t('notifications.rules.authBasic'), value: 'basic' },
])

const digestFrequencyOptions = computed(() => [
  { title: t('notifications.rules.frequencyHourly'), value: 'hourly' },
  { title: t('notifications.rules.frequencyDaily'), value: 'daily' },
  { title: t('notifications.rules.frequencyWeekly'), value: 'weekly' },
])

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
      auth: {
        type: rule.channel_config.auth?.type || 'none',
        token: rule.channel_config.auth?.token || '',
        username: rule.channel_config.auth?.username || '',
        password: rule.channel_config.auth?.password || '',
      },
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

  // Build typed conditions object
  const conditions: { min_confidence?: number | null; keywords?: string[] } = {}
  if (formData.value.conditions.min_confidence) {
    conditions.min_confidence = formData.value.conditions.min_confidence
  }
  if (formData.value.conditions.keywords?.length > 0) {
    conditions.keywords = formData.value.conditions.keywords
  }

  // Build typed channel config object
  const channelConfig: {
    email_address_ids?: string[]
    include_primary?: boolean
    url?: string
    auth?: { type: string; token?: string; username?: string; password?: string }
  } = {}

  if (formData.value.channel === 'EMAIL') {
    if (formData.value.channel_config.email_address_ids.length > 0) {
      channelConfig.email_address_ids = formData.value.channel_config.email_address_ids
    }
    channelConfig.include_primary = formData.value.channel_config.include_primary
  } else if (formData.value.channel === 'WEBHOOK') {
    channelConfig.url = formData.value.channel_config.url
    if (webhookAuthType.value !== 'none') {
      const { type: _existingType, ...authWithoutType } = formData.value.channel_config.auth || {}
      channelConfig.auth = {
        ...authWithoutType,
        type: webhookAuthType.value,
      }
    }
  }

  // Build the rule data
  const data = {
    name: formData.value.name,
    description: formData.value.description || undefined,
    event_type: formData.value.event_type,
    channel: formData.value.channel,
    conditions,
    channel_config: channelConfig,
    digest_enabled: formData.value.digest_enabled,
    digest_frequency: formData.value.digest_enabled ? formData.value.digest_frequency : undefined,
    is_active: formData.value.is_active,
  }

  try {
    if (editMode.value && editingRuleId.value) {
      await updateRule(editingRuleId.value, data)
    } else {
      await createRule(data)
    }
    closeDialog()
  } catch (e) {
    logger.error('Failed to save rule:', e)
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
    logger.error('Failed to delete rule:', e)
  }
}

const handleToggleActive = async (rule: NotificationRule) => {
  try {
    await toggleRuleActive(rule)
  } catch (e) {
    logger.error('Failed to toggle rule:', e)
  }
}

const handleTestWebhook = async () => {
  if (!formData.value.channel_config.url) return

  testingWebhook.value = true
  webhookTestResult.value = null

  try {
    const authConfig = formData.value.channel_config.auth || {}
    const { type: _existingAuthType, ...authConfigWithoutType } = authConfig
    const auth = webhookAuthType.value !== 'none'
      ? { ...authConfigWithoutType, type: webhookAuthType.value }
      : undefined

    const result = await testWebhook(formData.value.channel_config.url, auth)
    webhookTestResult.value = result
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e)
    webhookTestResult.value = { success: false, error: message }
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
