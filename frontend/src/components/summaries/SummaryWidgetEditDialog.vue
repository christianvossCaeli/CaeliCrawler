<template>
  <v-dialog
    v-model="modelValue"
    :max-width="DIALOG_SIZES.MD"
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

          <!-- Column Configuration (only for table/map/comparison widgets) -->
          <template v-if="supportsColumnConfig">
            <v-divider class="my-4" />

            <div class="text-subtitle-2 mb-2">{{ t('summaries.columnConfig.sectionTitle') }}</div>

            <div class="d-flex align-center ga-2 mb-2">
              <v-chip
                v-if="configuredColumnsCount > 0"
                size="small"
                color="primary"
                variant="tonal"
              >
                {{ t('summaries.columnConfig.columnsConfigured', { count: configuredColumnsCount }) }}
              </v-chip>
              <v-chip v-else size="small" variant="outlined">
                {{ t('summaries.columnConfig.autoDetect') }}
              </v-chip>
            </div>

            <v-btn
              variant="outlined"
              color="primary"
              prepend-icon="mdi-table-column"
              @click="showColumnConfig = true"
            >
              {{ t('summaries.columnConfig.configure') }}
            </v-btn>
          </template>
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

  <!-- Column Configuration Dialog -->
  <ColumnConfigDialog
    v-model="showColumnConfig"
    :current-columns="currentColumnsForDialog"
    :available-data="widgetData"
    @save="onColumnConfigSave"
  />
</template>

<script setup lang="ts">
import { ref, watch, computed, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'
import { useCustomSummariesStore, type SummaryWidget, type WidgetUpdate, type WidgetVisualizationConfig } from '@/stores/customSummaries'
import { useDialogFocus } from '@/composables'
import ColumnConfigDialog from './ColumnConfigDialog.vue'

const modelValue = defineModel<boolean>()
const props = defineProps<{
  summaryId: string
  widget: SummaryWidget
  /** Cached data for the widget (for column detection) */
  widgetData?: Record<string, unknown>[]
}>()
const emit = defineEmits<{
  updated: []
}>()
const { t } = useI18n()
const store = useCustomSummariesStore()

// Track if component is mounted to prevent state updates after unmount
let isMounted = true
onUnmounted(() => {
  isMounted = false
})

// Focus management for accessibility
useDialogFocus({ isOpen: modelValue })

const dialogTitleId = `summary-widget-edit-dialog-title-${Math.random().toString(36).slice(2, 9)}`

const formRef = ref()
const isValid = ref(false)
const isSaving = ref(false)
const showColumnConfig = ref(false)

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
const visualizationConfig = ref<WidgetVisualizationConfig>({})

// Widget types that support column configuration
const columnConfigWidgetTypes = new Set(['table', 'map', 'comparison'])

const supportsColumnConfig = computed(() => {
  return columnConfigWidgetTypes.has(props.widget?.widget_type)
})

const configuredColumnsCount = computed(() => {
  return visualizationConfig.value.columns?.length || 0
})

// Convert 'field' to 'key' for ColumnConfigDialog compatibility
const currentColumnsForDialog = computed(() => {
  if (!visualizationConfig.value.columns) return undefined
  return visualizationConfig.value.columns.map(c => ({
    key: c.field,
    label: c.label,
    sortable: c.sortable,
    width: c.width,
  }))
})

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
    visualizationConfig.value = { ...widget.visualization_config }
  }
}, { immediate: true })

function onColumnConfigSave(columns: Array<{ key: string; label: string; sortable?: boolean; width?: string }>) {
  // Convert 'key' to 'field' for API compatibility
  visualizationConfig.value = {
    ...visualizationConfig.value,
    columns: columns.length > 0 ? columns.map(c => ({ field: c.key, label: c.label, sortable: c.sortable, width: c.width })) : undefined,
  }
}

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
      visualization_config: visualizationConfig.value,
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
