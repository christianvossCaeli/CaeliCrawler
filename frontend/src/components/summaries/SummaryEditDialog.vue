<template>
  <v-dialog
    v-model="modelValue"
    max-width="600"
    role="dialog"
    aria-modal="true"
    :aria-labelledby="dialogTitleId"
  >
    <v-card>
      <v-card-title :id="dialogTitleId">
        <v-icon color="primary" class="mr-2">mdi-pencil</v-icon>
        {{ t('summaries.editSettings') }}
      </v-card-title>

      <v-card-text>
        <v-form ref="formRef" v-model="isValid">
          <!-- Name -->
          <v-text-field
            v-model="form.name"
            :label="t('summaries.name')"
            :rules="[v => !!v || t('validation.required')]"
            class="mb-4"
          />

          <!-- Description -->
          <v-textarea
            v-model="form.description"
            :label="t('summaries.description')"
            rows="2"
            class="mb-4"
          />

          <!-- Status -->
          <v-select
            v-model="form.status"
            :items="statusOptions"
            :label="t('summaries.status')"
            class="mb-4"
          />

          <v-divider class="mb-4" />

          <!-- Trigger Type -->
          <v-radio-group
            v-model="form.trigger_type"
            :label="t('summaries.triggerType')"
            class="mb-4"
          >
            <v-radio value="manual" :label="t('summaries.triggerManual')" />
            <v-radio value="cron" :label="t('summaries.triggerCron')" />
            <v-radio value="crawl_category" :label="t('summaries.triggerCrawlCategory')" />
          </v-radio-group>

          <!-- Cron Schedule (if cron selected) -->
          <v-select
            v-if="form.trigger_type === 'cron'"
            v-model="form.schedule_cron"
            :items="schedulePresets"
            item-title="description"
            item-value="cron"
            :label="t('summaries.schedule')"
            class="mb-4"
          >
            <template #item="{ item, props: itemProps }">
              <v-list-item v-bind="itemProps">
                <v-list-item-subtitle>{{ item.raw.cron }}</v-list-item-subtitle>
              </v-list-item>
            </template>
          </v-select>

          <!-- Schedule Enabled -->
          <v-switch
            v-if="form.trigger_type !== 'manual'"
            v-model="form.schedule_enabled"
            :label="t('summaries.scheduleEnabled')"
            color="primary"
            class="mb-4"
          />

          <v-divider class="mb-4" />

          <!-- Relevance Check -->
          <v-switch
            v-model="form.check_relevance"
            :label="t('summaries.checkRelevance')"
            :hint="t('summaries.checkRelevanceHint')"
            persistent-hint
            color="primary"
            class="mb-4"
          />

          <!-- Relevance Threshold -->
          <v-slider
            v-if="form.check_relevance"
            v-model="form.relevance_threshold"
            :label="t('summaries.relevanceThreshold')"
            :min="0"
            :max="1"
            :step="0.1"
            thumb-label
            class="mb-4"
          />

          <!-- Auto Expand -->
          <v-switch
            v-model="form.auto_expand"
            :label="t('summaries.autoExpand')"
            :hint="t('summaries.autoExpandHint')"
            persistent-hint
            color="primary"
          />
        </v-form>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-btn variant="text" @click="close">
          {{ t('common.cancel') }}
        </v-btn>
        <v-spacer />
        <v-btn
          color="primary"
          variant="flat"
          :disabled="!isValid"
          :loading="isSaving"
          @click="save"
        >
          {{ t('common.save') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCustomSummariesStore, type CustomSummary, type SummaryUpdate } from '@/stores/customSummaries'
import { useDialogFocus } from '@/composables'

const modelValue = defineModel<boolean>()
const props = defineProps<{
  summary: CustomSummary
}>()
const emit = defineEmits<{
  updated: []
}>()
const { t } = useI18n()
const store = useCustomSummariesStore()

// ARIA
const dialogTitleId = `summary-edit-dialog-title-${Math.random().toString(36).slice(2, 9)}`

// Focus management for accessibility
useDialogFocus({ isOpen: modelValue })

// Form state
const formRef = ref()
const isValid = ref(false)
const isSaving = ref(false)

const form = ref<SummaryUpdate>({
  name: '',
  description: '',
  status: 'draft',
  trigger_type: 'manual',
  schedule_cron: undefined,
  schedule_enabled: false,
  check_relevance: true,
  relevance_threshold: 0.3,
  auto_expand: false,
})

const statusOptions = [
  { title: t('summaries.statusDraft'), value: 'draft' },
  { title: t('summaries.statusActive'), value: 'active' },
  { title: t('summaries.statusPaused'), value: 'paused' },
  { title: t('summaries.statusArchived'), value: 'archived' },
]

const schedulePresets = computed(() => store.schedulePresets)

// Initialize form from summary
watch(() => props.summary, (summary) => {
  if (summary) {
    form.value = {
      name: summary.name,
      description: summary.description || '',
      status: summary.status,
      trigger_type: summary.trigger_type,
      schedule_cron: summary.schedule_cron ?? undefined,
      schedule_enabled: summary.schedule_enabled,
      check_relevance: summary.check_relevance,
      relevance_threshold: summary.relevance_threshold,
      auto_expand: summary.auto_expand,
    }
  }
}, { immediate: true })

async function save() {
  if (!formRef.value?.validate()) return

  isSaving.value = true
  try {
    const result = await store.updateSummary(props.summary.id, form.value)
    if (result) {
      emit('updated')
      close()
    }
  } finally {
    isSaving.value = false
  }
}

function close() {
  modelValue.value = false
}
</script>
