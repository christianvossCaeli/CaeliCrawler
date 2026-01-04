<template>
  <v-dialog
    v-model="modelValue"
    :max-width="DIALOG_SIZES.ML"
    scrollable
    role="dialog"
    aria-modal="true"
    :aria-labelledby="dialogTitleId"
  >
    <v-card>
      <v-card-title :id="dialogTitleId" class="d-flex align-center">
        <v-icon color="primary" class="mr-2">mdi-table-column</v-icon>
        {{ t('summaries.columnConfig.title') }}
      </v-card-title>

      <v-card-subtitle class="pb-0">
        {{ t('summaries.columnConfig.subtitle') }}
      </v-card-subtitle>

      <v-divider class="mt-4" />

      <v-card-text class="pa-0" style="max-height: 500px; overflow-y: auto;">
        <!-- Available columns list -->
        <v-list density="compact" class="py-0">
          <v-list-item
            v-for="(element, index) in columns"
            :key="element.key"
            :class="{ 'bg-grey-lighten-4': !element.enabled }"
            class="column-item"
          >
            <template #prepend>
              <div class="d-flex align-center">
                <!-- Move buttons -->
                <div class="d-flex flex-column mr-1">
                  <v-btn
                    icon="mdi-chevron-up"
                    size="x-small"
                    variant="text"
                    :disabled="index === 0"
                    @click="moveColumn(index, -1)"
                  />
                  <v-btn
                    icon="mdi-chevron-down"
                    size="x-small"
                    variant="text"
                    :disabled="index === columns.length - 1"
                    @click="moveColumn(index, 1)"
                  />
                </div>
                <v-checkbox
                  v-model="element.enabled"
                  density="compact"
                  hide-details
                  class="mr-2"
                />
              </div>
            </template>

            <v-list-item-title class="d-flex align-center flex-wrap ga-1">
              <!-- Editable label -->
              <v-text-field
                v-model="element.label"
                density="compact"
                variant="outlined"
                hide-details
                :placeholder="element.originalLabel"
                class="column-label-input"
                style="max-width: 180px; min-width: 120px;"
              />

              <!-- Key info -->
              <v-chip
                size="x-small"
                variant="outlined"
                :title="element.key"
              >
                {{ formatKeyDisplay(element.key) }}
              </v-chip>

              <!-- Type badge -->
              <v-chip
                v-if="element.type"
                size="x-small"
                :color="getTypeColor(element.type)"
                variant="tonal"
              >
                {{ element.type }}
              </v-chip>
            </v-list-item-title>

            <template #append>
              <div class="d-flex align-center ga-1">
                <!-- Width selector -->
                <v-select
                  v-model="element.width"
                  :items="widthOptions"
                  density="compact"
                  variant="outlined"
                  hide-details
                  style="max-width: 90px;"
                />

                <!-- Sortable toggle -->
                <v-tooltip :text="t('summaries.columnConfig.sortable')">
                  <template #activator="{ props: activatorProps }">
                    <v-btn
                      v-bind="activatorProps"
                      :icon="element.sortable ? 'mdi-sort' : 'mdi-sort-off'"
                      :color="element.sortable ? 'primary' : 'grey'"
                      variant="text"
                      size="small"
                      @click="element.sortable = !element.sortable"
                    />
                  </template>
                </v-tooltip>
              </div>
            </template>
          </v-list-item>
        </v-list>

        <!-- Empty state -->
        <div v-if="columns.length === 0" class="text-center py-8 text-medium-emphasis">
          <v-icon size="48" color="grey-lighten-1">mdi-table-column-remove</v-icon>
          <p class="mt-2">{{ t('summaries.columnConfig.noColumns') }}</p>
        </div>
      </v-card-text>

      <v-divider />

      <v-card-actions class="px-4 py-3">
        <v-btn
          variant="text"
          size="small"
          @click="resetToDefault"
        >
          <v-icon start>mdi-refresh</v-icon>
          {{ t('summaries.columnConfig.resetDefault') }}
        </v-btn>

        <v-btn
          variant="text"
          size="small"
          @click="selectAll(true)"
        >
          {{ t('summaries.columnConfig.selectAll') }}
        </v-btn>

        <v-btn
          variant="text"
          size="small"
          @click="selectAll(false)"
        >
          {{ t('summaries.columnConfig.deselectAll') }}
        </v-btn>

        <v-spacer />

        <v-btn variant="text" @click="close">
          {{ t('common.cancel') }}
        </v-btn>

        <v-btn
          color="primary"
          variant="flat"
          @click="save"
        >
          {{ t('common.apply') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'
import type { ColumnType } from '@/components/smartquery/visualizations/types'

const modelValue = defineModel<boolean>()

const props = defineProps<{
  /** Current columns configuration (from visualization_config.columns) */
  currentColumns?: Array<{ key: string; label: string; sortable?: boolean; width?: string }>
  /** Available data to detect columns from */
  availableData?: Record<string, unknown>[]
}>()

const emit = defineEmits<{
  save: [columns: Array<{ key: string; label: string; sortable?: boolean; width?: string; type?: ColumnType }>]
}>()

const { t } = useI18n()

interface ColumnConfig {
  key: string
  label: string
  originalLabel: string
  type: ColumnType
  enabled: boolean
  sortable: boolean
  width?: string
}

const dialogTitleId = `column-config-dialog-title-${Math.random().toString(36).slice(2, 9)}`

const columns = ref<ColumnConfig[]>([])

const widthOptions = [
  { title: 'Auto', value: undefined },
  { title: '80px', value: '80px' },
  { title: '100px', value: '100px' },
  { title: '120px', value: '120px' },
  { title: '150px', value: '150px' },
  { title: '200px', value: '200px' },
  { title: '250px', value: '250px' },
]

// Initialize columns from props
watch([() => props.currentColumns, () => props.availableData, modelValue], () => {
  if (modelValue.value) {
    initializeColumns()
  }
}, { immediate: true })

function initializeColumns() {
  const detectedColumns = detectColumnsFromData()

  if (props.currentColumns && props.currentColumns.length > 0) {
    // Use existing config, but merge with detected columns
    const existingKeys = new Set(props.currentColumns.map(c => c.key))

    columns.value = [
      // First: existing columns in their order
      ...props.currentColumns.map(col => {
        const detected = detectedColumns.find(d => d.key === col.key)
        return {
          key: col.key,
          label: col.label,
          originalLabel: detected?.originalLabel || formatKeyToLabel(col.key),
          type: detected?.type || 'text' as ColumnType,
          enabled: true,
          sortable: col.sortable !== false,
          width: col.width,
        }
      }),
      // Then: newly detected columns that aren't in existing config
      ...detectedColumns
        .filter(d => !existingKeys.has(d.key))
        .map(d => ({ ...d, enabled: false }))
    ]
  } else {
    // No existing config - use all detected columns
    columns.value = detectedColumns
  }
}

function detectColumnsFromData(): ColumnConfig[] {
  if (!props.availableData || props.availableData.length === 0) {
    return []
  }

  const sample = props.availableData[0]
  const detected: ColumnConfig[] = []
  const excludedKeys = new Set(['entity_id', 'facets', 'coords_from_parent'])

  // Add name/entity_name first
  if ('name' in sample) {
    detected.push({
      key: 'name',
      label: t('summaries.columnConfig.columns.name'),
      originalLabel: t('summaries.columnConfig.columns.name'),
      type: 'text',
      enabled: true,
      sortable: true,
    })
  } else if ('entity_name' in sample) {
    detected.push({
      key: 'entity_name',
      label: t('summaries.columnConfig.columns.name'),
      originalLabel: t('summaries.columnConfig.columns.name'),
      type: 'text',
      enabled: true,
      sortable: true,
    })
  }

  // Add other direct fields
  for (const [key, value] of Object.entries(sample)) {
    if (excludedKeys.has(key) || key === 'name' || key === 'entity_name') continue

    if (key === 'facets') continue // Handle separately

    const type = detectValueType(value)
    detected.push({
      key,
      label: formatKeyToLabel(key),
      originalLabel: formatKeyToLabel(key),
      type,
      enabled: isDefaultEnabled(key),
      sortable: true,
    })
  }

  // Add facet fields
  if (sample.facets && typeof sample.facets === 'object') {
    for (const [facetKey, facetValue] of Object.entries(sample.facets)) {
      const value = (facetValue as { value?: unknown })?.value
      const type = detectValueType(value)
      detected.push({
        key: `facets.${facetKey}.value`,
        label: formatKeyToLabel(facetKey),
        originalLabel: formatKeyToLabel(facetKey),
        type,
        enabled: true,
        sortable: true,
      })
    }
  }

  return detected
}

function detectValueType(value: unknown): ColumnType {
  if (value === null || value === undefined) return 'text'
  if (typeof value === 'number') return 'number'
  if (typeof value === 'boolean') return 'boolean'
  if (typeof value === 'string') {
    // Check for date patterns
    if (/^\d{4}-\d{2}-\d{2}/.test(value)) return 'date'
  }
  return 'text'
}

function isDefaultEnabled(key: string): boolean {
  // Enable common important fields by default
  const importantFields = new Set([
    'name', 'entity_name', 'status', 'admin_level_1', 'country',
    'latitude', 'longitude', 'power_mw', 'area_ha', 'wea_count'
  ])
  return importantFields.has(key)
}

function formatKeyToLabel(key: string): string {
  // Remove facets prefix if present
  const label = key.replace(/^facets\./, '').replace(/\.value$/, '')
  // Convert snake_case and kebab-case to Title Case
  return label
    .replace(/[-_]/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

function formatKeyDisplay(key: string): string {
  // Shorten long keys for display
  if (key.length > 20) {
    return key.slice(0, 17) + '...'
  }
  return key
}

function getTypeColor(type: ColumnType): string {
  const colors: Record<ColumnType, string> = {
    text: 'grey',
    number: 'blue',
    date: 'green',
    datetime: 'green',
    currency: 'amber',
    percent: 'purple',
    boolean: 'cyan',
    link: 'indigo',
  }
  return colors[type] || 'grey'
}

function moveColumn(index: number, direction: number) {
  const newIndex = index + direction
  if (newIndex < 0 || newIndex >= columns.value.length) return

  const temp = columns.value[index]
  columns.value[index] = columns.value[newIndex]
  columns.value[newIndex] = temp
}

function selectAll(enabled: boolean) {
  columns.value.forEach(col => {
    col.enabled = enabled
  })
}

function resetToDefault() {
  initializeColumns()
  // Reset all to detected defaults
  columns.value.forEach(col => {
    col.label = col.originalLabel
    col.enabled = isDefaultEnabled(col.key) || col.key.startsWith('facets.')
    col.sortable = true
    col.width = undefined
  })
}

function save() {
  // Only include enabled columns, in current order
  const enabledColumns = columns.value
    .filter(col => col.enabled)
    .map(col => ({
      key: col.key,
      label: col.label,
      sortable: col.sortable,
      width: col.width,
      type: col.type,
    }))

  emit('save', enabledColumns)
  close()
}

function close() {
  modelValue.value = false
}
</script>

<style scoped>
.column-item {
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.column-item:last-child {
  border-bottom: none;
}

.column-label-input :deep(.v-field__input) {
  font-size: 0.875rem;
  padding: 4px 8px;
}
</style>
