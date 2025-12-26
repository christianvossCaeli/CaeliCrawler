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
        <v-icon color="primary" class="mr-2">mdi-plus-circle</v-icon>
        {{ t('summaries.addWidget') }}
      </v-card-title>

      <v-card-text>
        <v-form ref="formRef" v-model="isValid">
          <!-- Widget Type -->
          <v-select
            v-model="form.widget_type"
            :items="widgetTypeOptions"
            :label="t('summaries.widgetType')"
            :rules="[v => !!v || t('validation.required')]"
            class="mb-4"
          >
            <template #item="{ item, props: itemProps }">
              <v-list-item v-bind="itemProps">
                <template #prepend>
                  <v-icon :icon="item.raw.icon" :color="item.raw.color" size="small" />
                </template>
              </v-list-item>
            </template>
            <template #selection="{ item }">
              <v-icon :icon="item.raw.icon" :color="item.raw.color" size="small" class="mr-2" />
              {{ item.title }}
            </template>
          </v-select>

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
            v-model="form.query_config.entity_type"
            :label="t('summaries.entityType')"
            :hint="t('summaries.entityTypeHint')"
            persistent-hint
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
            v-model.number="form.query_config.limit"
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
          {{ t('common.add') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCustomSummariesStore, type WidgetCreate } from '@/stores/customSummaries'
import { VISUALIZATION_ICONS, VISUALIZATION_COLORS } from '@/components/smartquery/visualizations/types'
import { useDialogFocus } from '@/composables'

const modelValue = defineModel<boolean>()
const props = defineProps<{
  summaryId: string
}>()
const emit = defineEmits<{
  added: []
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

const dialogTitleId = `summary-add-widget-dialog-title-${Math.random().toString(36).slice(2, 9)}`

const formRef = ref()
const isValid = ref(false)
const isSaving = ref(false)
const facetTypesInput = ref('')

const form = ref<WidgetCreate & { query_config: NonNullable<WidgetCreate['query_config']> }>({
  widget_type: 'table',
  title: '',
  subtitle: '',
  position_x: 0,
  position_y: 0,
  width: 2,
  height: 2,
  query_config: {
    entity_type: '',
    facet_types: [],
    limit: 100,
  },
  visualization_config: {},
})

const widgetTypeOptions = computed(() => [
  { title: t('summaries.widgetTypes.table'), value: 'table', icon: VISUALIZATION_ICONS.table, color: VISUALIZATION_COLORS.table },
  { title: t('summaries.widgetTypes.bar_chart'), value: 'bar_chart', icon: VISUALIZATION_ICONS.bar_chart, color: VISUALIZATION_COLORS.bar_chart },
  { title: t('summaries.widgetTypes.line_chart'), value: 'line_chart', icon: VISUALIZATION_ICONS.line_chart, color: VISUALIZATION_COLORS.line_chart },
  { title: t('summaries.widgetTypes.pie_chart'), value: 'pie_chart', icon: VISUALIZATION_ICONS.pie_chart, color: VISUALIZATION_COLORS.pie_chart },
  { title: t('summaries.widgetTypes.stat_card'), value: 'stat_card', icon: VISUALIZATION_ICONS.stat_card, color: VISUALIZATION_COLORS.stat_card },
  { title: t('summaries.widgetTypes.text'), value: 'text', icon: VISUALIZATION_ICONS.text, color: VISUALIZATION_COLORS.text },
  { title: t('summaries.widgetTypes.comparison'), value: 'comparison', icon: VISUALIZATION_ICONS.comparison, color: VISUALIZATION_COLORS.comparison },
  { title: t('summaries.widgetTypes.map'), value: 'map', icon: VISUALIZATION_ICONS.map, color: VISUALIZATION_COLORS.map },
])

// Parse facet types from comma-separated string
watch(facetTypesInput, (val) => {
  if (form.value.query_config) {
    form.value.query_config.facet_types = val
      .split(',')
      .map(s => s.trim())
      .filter(s => s.length > 0)
  }
})

// Auto-adjust size for certain widget types
watch(() => form.value.widget_type, (widgetType) => {
  if (widgetType === 'map') {
    // Map widgets should be full width for better visibility
    form.value.width = 4
    form.value.height = 3
    form.value.position_x = 0
  } else if (widgetType === 'stat_card') {
    // Stat cards are typically small
    form.value.width = 1
    form.value.height = 1
  } else if (widgetType === 'table' || widgetType === 'comparison') {
    // Tables and comparisons benefit from more width
    form.value.width = 4
    form.value.height = 2
    form.value.position_x = 0
  }
})

async function save() {
  if (!formRef.value?.validate()) return

  isSaving.value = true
  try {
    const widget = await store.addWidget(props.summaryId, form.value)
    // Only update state if still mounted
    if (isMounted && widget) {
      emit('added')
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

function reset() {
  form.value = {
    widget_type: 'table',
    title: '',
    subtitle: '',
    position_x: 0,
    position_y: 0,
    width: 2,
    height: 2,
    query_config: {
      entity_type: '',
      facet_types: [],
      limit: 100,
    },
    visualization_config: {},
  }
  facetTypesInput.value = ''
}

watch(modelValue, (isOpen) => {
  if (isOpen) {
    reset()
  }
})
</script>
