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
        {{ t('summaries.editWidget') }}
      </v-card-title>

      <v-card-text>
        <v-form ref="formRef" v-model="isValid">
          <!-- Title -->
          <v-text-field
            v-model="form.title"
            :label="t('summaries.widgetTitle')"
            :rules="[v => !!v || t('validation.required')]"
            class="mb-4"
          />

          <!-- Subtitle -->
          <v-text-field
            v-model="form.subtitle"
            :label="t('summaries.widgetSubtitle')"
            class="mb-4"
          />

          <v-divider class="mb-4" />

          <!-- Position -->
          <v-row>
            <v-col cols="6">
              <v-text-field
                v-model.number="form.position_x"
                :label="t('summaries.positionX')"
                type="number"
                min="0"
                max="3"
              />
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model.number="form.position_y"
                :label="t('summaries.positionY')"
                type="number"
                min="0"
              />
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model.number="form.width"
                :label="t('summaries.widgetWidth')"
                type="number"
                min="1"
                max="4"
              />
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model.number="form.height"
                :label="t('summaries.widgetHeight')"
                type="number"
                min="1"
                max="6"
              />
            </v-col>
          </v-row>

          <v-divider class="my-4" />

          <!-- Query Config (simplified) -->
          <div class="text-subtitle-2 mb-2">{{ t('summaries.queryConfig') }}</div>

          <v-text-field
            v-model="queryEntityType"
            :label="t('summaries.entityType')"
            class="mb-4"
          />

          <v-text-field
            v-model="facetTypesInput"
            :label="t('summaries.facetTypes')"
            :hint="t('summaries.facetTypesHint')"
            persistent-hint
            class="mb-4"
          />

          <v-text-field
            v-model.number="queryLimit"
            :label="t('summaries.limit')"
            type="number"
            min="1"
            max="1000"
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
import { ref, watch, toRef, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCustomSummariesStore, type SummaryWidget, type WidgetUpdate } from '@/stores/customSummaries'
import { useDialogFocus } from '@/composables'

const { t } = useI18n()
const store = useCustomSummariesStore()

// Track if component is mounted to prevent state updates after unmount
let isMounted = true
onUnmounted(() => {
  isMounted = false
})

const modelValue = defineModel<boolean>()

const props = defineProps<{
  summaryId: string
  widget: SummaryWidget
}>()

// Focus management for accessibility
useDialogFocus({ isOpen: modelValue })

const emit = defineEmits<{
  updated: []
}>()

const dialogTitleId = `summary-widget-edit-dialog-title-${Math.random().toString(36).slice(2, 9)}`

const formRef = ref()
const isValid = ref(false)
const isSaving = ref(false)

const form = ref<WidgetUpdate>({
  title: '',
  subtitle: '',
  position_x: 0,
  position_y: 0,
  width: 2,
  height: 2,
})

const queryEntityType = ref('')
const facetTypesInput = ref('')
const queryLimit = ref(100)

// Initialize form from widget
watch(() => props.widget, (widget) => {
  if (widget) {
    form.value = {
      title: widget.title,
      subtitle: widget.subtitle || '',
      position_x: widget.position.x,
      position_y: widget.position.y,
      width: widget.position.w,
      height: widget.position.h,
    }
    queryEntityType.value = widget.query_config.entity_type || ''
    facetTypesInput.value = (widget.query_config.facet_types || []).join(', ')
    queryLimit.value = widget.query_config.limit || 100
  }
}, { immediate: true })

async function save() {
  if (!formRef.value?.validate()) return

  // Build query config
  const queryConfig = {
    ...props.widget.query_config,
    entity_type: queryEntityType.value,
    facet_types: facetTypesInput.value.split(',').map(s => s.trim()).filter(s => s),
    limit: queryLimit.value,
  }

  isSaving.value = true
  try {
    const updated = await store.updateWidget(props.summaryId, props.widget.id, {
      ...form.value,
      query_config: queryConfig,
    })
    // Only update state if still mounted
    if (isMounted && updated) {
      emit('updated')
      close()
    }
  } finally {
    if (isMounted) {
      isSaving.value = false
    }
  }
}

function close() {
  modelValue.value = false
}
</script>
