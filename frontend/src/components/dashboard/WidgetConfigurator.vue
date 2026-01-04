<template>
  <v-dialog v-model="dialog" :max-width="DIALOG_SIZES.ML" scrollable>
    <v-card>
      <v-card-title class="d-flex align-center py-4">
        <v-icon icon="mdi-view-dashboard-edit" class="mr-3" size="28" />
        <div>
          <div>{{ $t('dashboard.customize') }}</div>
          <div class="text-caption text-medium-emphasis">
            {{ enabledCount }} {{ $t('dashboard.widgetsActive') }}
          </div>
        </div>
      </v-card-title>

      <v-divider />

      <!-- Hint -->
      <v-alert
        type="info"
        variant="tonal"
        density="compact"
        class="mx-4 mt-4"
        closable
      >
        <v-icon size="small" class="mr-1">mdi-gesture-swipe</v-icon>
        {{ $t('dashboard.dragToReorder') }}
      </v-alert>

      <v-card-text class="py-4" style="max-height: 55vh; overflow-y: auto">
        <div class="widget-list">
          <div
            v-for="(widget, index) in widgetList"
            :key="widget.id"
            class="widget-item"
            :class="{
              'widget-item--enabled': widget.enabled,
              'widget-item--dragging': draggedIndex === index,
              'widget-item--drag-over': dragOverIndex === index && draggedIndex !== index,
            }"
            draggable="true"
            @dragstart="onDragStart(index, $event)"
            @dragover="onDragOver(index, $event)"
            @dragleave="onDragLeave"
            @drop="onDrop(index, $event)"
            @dragend="onDragEnd"
          >
            <!-- Drag Handle -->
            <div class="widget-item__handle">
              <v-icon size="small" class="text-medium-emphasis">mdi-drag</v-icon>
            </div>

            <!-- Enable/Disable Toggle -->
            <v-switch
              :model-value="widget.enabled"
              hide-details
              density="compact"
              color="primary"
              class="widget-item__switch"
              @update:model-value="toggleWidget(widget)"
            />

            <!-- Widget Info -->
            <div class="widget-item__info" :class="{ 'text-medium-emphasis': !widget.enabled }">
              <div class="d-flex align-center">
                <v-icon :icon="widget.definition.icon" size="small" class="mr-2" />
                <span class="font-weight-medium">{{ $t(widget.definition.name) }}</span>
              </div>
              <div class="text-caption text-medium-emphasis mt-1">
                {{ $t(widget.definition.description) }}
              </div>
            </div>

            <!-- Size Selector -->
            <div class="widget-item__size">
              <v-btn-toggle
                :model-value="widget.width"
                mandatory
                density="compact"
                variant="outlined"
                divided
                :disabled="!widget.enabled"
                @update:model-value="setWidgetSize(widget, $event)"
              >
                <v-btn
                  v-for="size in sizeOptions"
                  :key="size.value"
                  :value="size.value"
                  size="small"
                  min-width="36"
                >
                  <v-tooltip activator="parent" location="top">
                    {{ $t(size.label) }}
                  </v-tooltip>
                  {{ size.value }}
                </v-btn>
              </v-btn-toggle>
            </div>

            <!-- Move Buttons (for accessibility) -->
            <div class="widget-item__move">
              <v-btn
                icon
                size="x-small"
                variant="text"
                :disabled="index === 0"
                @click="moveWidget(index, 'up')"
              >
                <v-icon size="x-small">mdi-chevron-up</v-icon>
              </v-btn>
              <v-btn
                icon
                size="x-small"
                variant="text"
                :disabled="index === widgetList.length - 1"
                @click="moveWidget(index, 'down')"
              >
                <v-icon size="x-small">mdi-chevron-down</v-icon>
              </v-btn>
            </div>
          </div>
        </div>
      </v-card-text>

      <!-- Preview -->
      <v-divider />

      <div class="px-4 py-3">
        <div class="text-caption text-medium-emphasis mb-2">
          <v-icon size="14" class="mr-1">mdi-eye</v-icon>
          {{ $t('dashboard.preview') }}
        </div>
        <div class="preview-grid">
          <template v-for="widget in widgetList" :key="widget.id">
            <div
              v-if="widget.enabled"
              class="preview-item"
              :style="{
                flex: `0 0 ${(widget.width / 4) * 100}%`,
                maxWidth: `${(widget.width / 4) * 100}%`
              }"
            >
              <div class="preview-item__content">
                <v-icon :icon="widget.definition.icon" size="12" class="mr-1" />
                <span class="text-truncate">{{ $t(widget.definition.name) }}</span>
              </div>
            </div>
          </template>
        </div>
      </div>

      <v-divider />

      <v-card-actions class="pa-4">
        <v-btn
          variant="tonal"
          color="warning"
          :loading="resetting"
          prepend-icon="mdi-restore"
          @click="resetToDefaults"
        >
          {{ $t('dashboard.resetToDefaults') }}
        </v-btn>

        <v-spacer />

        <v-btn variant="text" @click="cancel">
          {{ $t('common.cancel') }}
        </v-btn>

        <v-btn
          color="primary"
          variant="flat"
          :loading="saving"
          prepend-icon="mdi-check"
          @click="save"
        >
          {{ $t('common.save') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
/**
 * WidgetConfigurator - Dialog for customizing dashboard widgets
 * Features: Enable/disable, resize, drag-and-drop reordering
 */

import { ref, computed, watch } from 'vue'
import { DIALOG_SIZES } from '@/config/ui'
import { useDashboardStore } from '@/stores/dashboard'
import { getAllWidgets, WIDGET_SIZE_OPTIONS } from '@/widgets'
import type { WidgetConfig, WidgetDefinition } from '@/widgets/types'

interface WidgetState {
  id: string
  enabled: boolean
  width: number
  order: number
  definition: WidgetDefinition
}

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const store = useDashboardStore()

const dialog = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

// Local copy of widget states for editing
const widgetList = ref<WidgetState[]>([])

// Drag state
const draggedIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)

// Initialize widget states when dialog opens
watch(
  () => props.modelValue,
  (isOpen) => {
    if (isOpen) {
      initializeWidgetList()
    }
  }
)

const initializeWidgetList = () => {
  const allDefs = getAllWidgets()
  const storeWidgets = store.widgets
  const list: WidgetState[] = []

  // First add existing widgets in their current order
  storeWidgets.forEach((w, index) => {
    const def = allDefs.find((d) => d.id === w.id)
    if (def) {
      list.push({
        id: w.id,
        enabled: w.enabled,
        width: w.position.w,
        order: index,
        definition: def,
      })
    }
  })

  // Then add any missing widgets from registry
  allDefs.forEach((def) => {
    if (!list.find((w) => w.id === def.id)) {
      list.push({
        id: def.id,
        enabled: false,
        width: def.defaultSize.w,
        order: list.length,
        definition: def,
      })
    }
  })

  widgetList.value = list
}

// Size options for buttons
const sizeOptions = WIDGET_SIZE_OPTIONS

// Toggle widget
const toggleWidget = (widget: WidgetState) => {
  widget.enabled = !widget.enabled
}

// Set widget size
const setWidgetSize = (widget: WidgetState, size: number) => {
  widget.width = size
}

// Drag and drop handlers
const onDragStart = (index: number, event: DragEvent) => {
  draggedIndex.value = index
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', index.toString())
  }
}

const onDragOver = (index: number, event: DragEvent) => {
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
  dragOverIndex.value = index
}

const onDragLeave = () => {
  dragOverIndex.value = null
}

const onDrop = (targetIndex: number, event: DragEvent) => {
  event.preventDefault()

  if (draggedIndex.value !== null && draggedIndex.value !== targetIndex) {
    const items = [...widgetList.value]
    const [movedItem] = items.splice(draggedIndex.value, 1)
    items.splice(targetIndex, 0, movedItem)
    widgetList.value = items
  }

  draggedIndex.value = null
  dragOverIndex.value = null
}

const onDragEnd = () => {
  draggedIndex.value = null
  dragOverIndex.value = null
}

// Move widget up/down (alternative to drag)
const moveWidget = (index: number, direction: 'up' | 'down') => {
  const newIndex = direction === 'up' ? index - 1 : index + 1
  if (newIndex < 0 || newIndex >= widgetList.value.length) return

  const items = [...widgetList.value]
  const [movedItem] = items.splice(index, 1)
  items.splice(newIndex, 0, movedItem)
  widgetList.value = items
}

// Computed: enabled widgets count
const enabledCount = computed(() => widgetList.value.filter((w) => w.enabled).length)

// Save changes
const saving = ref(false)

const save = async () => {
  saving.value = true

  // Build updated widgets list maintaining order
  const updatedWidgets: WidgetConfig[] = []
  let y = 0
  let x = 0

  widgetList.value.forEach((widget) => {
    // Calculate position based on order and width
    if (x + widget.width > 4) {
      x = 0
      y++
    }

    updatedWidgets.push({
      id: widget.id,
      type: widget.definition.type,
      enabled: widget.enabled,
      position: {
        x,
        y,
        w: widget.width,
        h: widget.definition.defaultSize.h,
      },
    })

    x += widget.width
    if (x >= 4) {
      x = 0
      y++
    }
  })

  store.widgets = updatedWidgets
  await store.savePreferences()

  saving.value = false
  dialog.value = false
  store.setEditMode(true)
}

// Reset to defaults
const resetting = ref(false)

const resetToDefaults = async () => {
  resetting.value = true
  await store.resetToDefaults()
  initializeWidgetList()
  resetting.value = false
}

// Cancel
const cancel = () => {
  dialog.value = false
}
</script>

<style scoped>
.widget-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.widget-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  background-color: rgba(var(--v-theme-on-surface), 0.03);
  border: 1px solid transparent;
  cursor: grab;
  transition: all 0.2s ease;
}

.widget-item:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.06);
}

.widget-item--enabled {
  background-color: rgba(var(--v-theme-primary), 0.08);
  border-color: rgba(var(--v-theme-primary), 0.2);
}

.widget-item--dragging {
  opacity: 0.5;
  cursor: grabbing;
}

.widget-item--drag-over {
  border-color: rgb(var(--v-theme-primary));
  background-color: rgba(var(--v-theme-primary), 0.15);
}

.widget-item__handle {
  cursor: grab;
  padding: 4px;
}

.widget-item__handle:active {
  cursor: grabbing;
}

.widget-item__switch {
  flex-shrink: 0;
}

.widget-item__info {
  flex: 1;
  min-width: 0;
}

.widget-item__size {
  flex-shrink: 0;
}

.widget-item__move {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

/* Preview Grid */
.preview-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  min-height: 32px;
  padding: 8px;
  border-radius: 8px;
  background-color: rgba(var(--v-theme-on-surface), 0.03);
}

.preview-item {
  padding: 2px;
}

.preview-item__content {
  display: flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 4px;
  background-color: rgba(var(--v-theme-primary), 0.15);
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
}

/* Responsive */
@media (max-width: 600px) {
  .widget-item {
    flex-wrap: wrap;
  }

  .widget-item__info {
    order: 1;
    flex-basis: calc(100% - 100px);
  }

  .widget-item__size {
    order: 3;
    flex-basis: 100%;
    margin-top: 8px;
  }

  .widget-item__move {
    display: none;
  }
}
</style>
