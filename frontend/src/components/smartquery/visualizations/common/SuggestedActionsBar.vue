<template>
  <div class="suggested-actions-bar">
    <span class="suggested-actions-bar__label text-caption text-medium-emphasis">
      <v-icon size="14" class="mr-1">mdi-lightbulb-outline</v-icon>
      {{ t('smartQuery.suggestedActions.label') }}
    </span>
    <div class="suggested-actions-bar__buttons">
      <v-btn
        v-for="action in actions"
        :key="action.action"
        size="small"
        variant="tonal"
        :color="getActionColor(action.action)"
        @click="handleClick(action)"
      >
        <v-icon v-if="action.icon" start size="16">{{ action.icon }}</v-icon>
        {{ action.label }}
        <v-tooltip v-if="action.description" activator="parent" location="top">
          {{ action.description }}
        </v-tooltip>
      </v-btn>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { SuggestedAction } from '../types'

const props = defineProps<{
  actions: SuggestedAction[]
  data?: Record<string, unknown>[]
}>()

const emit = defineEmits<{
  action: [action: string, params: Record<string, unknown>]
}>()

const { t } = useI18n()

function getActionColor(action: string): string {
  const colors: Record<string, string> = {
    export_csv: 'info',
    export_json: 'info',
    setup_sync: 'warning',
    setup_api_sync: 'warning',
    save_to_entities: 'success',
    change_visualization: 'secondary',
  }
  return colors[action] || 'primary'
}

function handleClick(action: SuggestedAction) {
  // Handle built-in actions
  if (action.action === 'export_csv') {
    exportToCsv()
    return
  }
  if (action.action === 'export_json') {
    exportToJson()
    return
  }

  // Emit for external handling
  emit('action', action.action, action.params)
}

function exportToCsv() {
  if (!props.data || props.data.length === 0) return

  // Get all keys from first item
  const headers = Object.keys(flattenObject(props.data[0]))

  // Build CSV content
  const rows = props.data.map(item => {
    const flat = flattenObject(item)
    return headers.map(h => {
      const val = flat[h]
      if (val === null || val === undefined) return ''
      if (typeof val === 'string' && (val.includes(',') || val.includes('"'))) {
        return `"${val.replace(/"/g, '""')}"`
      }
      return String(val)
    }).join(';')
  })

  const csv = [headers.join(';'), ...rows].join('\n')

  // Download
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `export_${new Date().toISOString().slice(0, 10)}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

function exportToJson() {
  if (!props.data || props.data.length === 0) return

  const json = JSON.stringify(props.data, null, 2)
  const blob = new Blob([json], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `export_${new Date().toISOString().slice(0, 10)}.json`
  link.click()
  URL.revokeObjectURL(url)
}

function flattenObject(obj: Record<string, unknown>, prefix = ''): Record<string, unknown> {
  const result: Record<string, unknown> = {}

  for (const [key, value] of Object.entries(obj)) {
    const newKey = prefix ? `${prefix}.${key}` : key

    if (value && typeof value === 'object' && !Array.isArray(value)) {
      Object.assign(result, flattenObject(value, newKey))
    } else if (Array.isArray(value)) {
      result[newKey] = value.join(', ')
    } else {
      result[newKey] = value
    }
  }

  return result
}
</script>

<style scoped>
.suggested-actions-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(var(--v-theme-surface-variant), 0.3);
  border-radius: 8px;
}

.suggested-actions-bar__label {
  display: flex;
  align-items: center;
}

.suggested-actions-bar__buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
