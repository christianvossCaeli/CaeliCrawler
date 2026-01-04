<template>
  <v-dialog :model-value="modelValue" :max-width="DIALOG_SIZES.MD" @update:model-value="$emit('update:modelValue', $event)">
    <v-card v-if="field">
      <v-card-title>
        <v-icon start>mdi-history</v-icon>
        {{ t('pysis.history') }}: {{ field.internal_name }}
      </v-card-title>
      <v-card-text>
        <v-progress-linear v-if="loading" indeterminate></v-progress-linear>
        <v-list v-else-if="entries.length" density="compact">
          <v-list-item
            v-for="entry in entries"
            :key="entry.id"
            :class="getHistoryItemClass(entry.action)"
          >
            <template #prepend>
              <v-icon :color="getHistoryActionColor(entry.action)" size="small">
                {{ getHistoryActionIcon(entry.action) }}
              </v-icon>
            </template>
            <v-list-item-title class="text-caption">
              <v-chip size="x-small" :color="getSourceColor(entry.source)" class="mr-2">
                {{ entry.source }}
              </v-chip>
              <span class="text-medium-emphasis">{{ formatHistoryAction(entry.action) }}</span>
              <span v-if="entry.confidence_score" class="ml-2 text-medium-emphasis-darken-1">
                ({{ Math.round(entry.confidence_score * 100) }}% {{ t('pysis.confidence') }})
              </span>
            </v-list-item-title>
            <v-list-item-subtitle class="mt-1">
              <div class="history-value">{{ truncateValue(entry.value, 200) || t('pysis.empty') }}</div>
              <div class="text-caption text-medium-emphasis mt-1">{{ formatDate(entry.recorded_at) }}</div>
            </v-list-item-subtitle>
            <template #append>
              <v-btn
                v-if="entry.action !== 'rejected'"
                icon="mdi-restore"
                size="x-small"
                variant="tonal"
                :title="t('pysis.restoreValue')"
                @click="$emit('restore', entry)"
              ></v-btn>
            </template>
          </v-list-item>
        </v-list>
        <div v-else class="text-center text-medium-emphasis py-4">
          {{ t('pysis.noHistory') }}
        </div>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" @click="$emit('update:modelValue', false)">{{ t('common.close') }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'
import { useDateFormatter } from '@/composables/useDateFormatter'

interface Field {
  internal_name: string
}

interface HistoryEntry {
  id: string
  value: string
  recorded_at: string
  source: string
  action: string
  confidence_score?: number
  created_at?: string
}

defineProps<{
  modelValue: boolean
  field: Field | null
  entries: HistoryEntry[]
  loading?: boolean
}>()

defineEmits<{
  'update:modelValue': [value: boolean]
  restore: [entry: HistoryEntry]
}>()

const { t } = useI18n()
const { formatDateTime } = useDateFormatter()

function formatDate(date: string | Date): string {
  return formatDateTime(date)
}

function getSourceColor(source: string): string {
  const colors: Record<string, string> = {
    pysis: 'info',
    manual: 'success',
    ai: 'secondary',
    restored: 'warning',
  }
  return colors[source] || 'grey'
}

function getHistoryActionIcon(action: string): string {
  const icons: Record<string, string> = {
    created: 'mdi-plus',
    updated: 'mdi-pencil',
    ai_suggestion: 'mdi-auto-fix',
    accepted: 'mdi-check',
    rejected: 'mdi-close',
    restored: 'mdi-restore',
  }
  return icons[action] || 'mdi-circle'
}

function getHistoryActionColor(action: string): string {
  const colors: Record<string, string> = {
    created: 'success',
    updated: 'info',
    ai_suggestion: 'secondary',
    accepted: 'success',
    rejected: 'error',
    restored: 'warning',
  }
  return colors[action] || 'grey'
}

function formatHistoryAction(action: string): string {
  return t(`pysis.historyActions.${action}`, action)
}

function getHistoryItemClass(action: string): string {
  if (action === 'rejected') return 'bg-error-lighten-5'
  if (action === 'accepted') return 'bg-success-lighten-5'
  return ''
}

function truncateValue(value: string | null | undefined, maxLength: number): string {
  if (!value) return ''
  return value.length > maxLength ? value.slice(0, maxLength) + '...' : value
}
</script>

<style scoped>
.history-value {
  padding: 4px 8px;
  background-color: rgba(var(--v-theme-on-surface), 0.03);
  border-radius: 4px;
  font-size: 0.8rem;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
