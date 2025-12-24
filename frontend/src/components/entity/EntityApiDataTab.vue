<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon start color="primary">mdi-api</v-icon>
      {{ t('entityDetail.apiData.title', 'Externe API-Daten') }}
    </v-card-title>
    <v-card-text>
      <!-- Source Info -->
      <v-alert type="info" variant="tonal" class="mb-4">
        <div class="d-flex align-center">
          <v-icon start>mdi-cloud-sync</v-icon>
          <div>
            <strong>{{ externalData.external_source?.name }}</strong>
            <div class="text-caption">
              {{ t('entityDetail.apiData.externalId', 'Externe ID') }}: {{ externalData.sync_record?.external_id }}
              <span v-if="externalData.sync_record?.last_seen_at" class="ml-2">
                | {{ t('entityDetail.apiData.lastSync', 'Letzter Sync') }}: {{ formatDate(externalData.sync_record.last_seen_at) }}
              </span>
            </div>
          </div>
        </div>
      </v-alert>

      <!-- Raw JSON Data -->
      <v-expansion-panels>
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon start>mdi-code-json</v-icon>
            {{ t('entityDetail.apiData.rawResponse', 'Rohe API-Antwort') }}
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <pre class="json-viewer pa-3 rounded">{{ JSON.stringify(externalData.raw_data, null, 2) }}</pre>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <!-- Field Overview -->
      <v-card variant="outlined" class="mt-4">
        <v-card-title class="text-subtitle-1">
          <v-icon start size="small">mdi-format-list-bulleted</v-icon>
          {{ t('entityDetail.apiData.fields', 'Verfügbare Felder') }}
        </v-card-title>
        <v-card-text>
          <v-table density="compact">
            <thead>
              <tr>
                <th>{{ t('entityDetail.apiData.fieldName', 'Feldname') }}</th>
                <th>{{ t('entityDetail.apiData.fieldType', 'Typ') }}</th>
                <th>{{ t('entityDetail.apiData.fieldValue', 'Wert') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(value, key) in externalData.raw_data" :key="key">
                <td class="font-weight-medium">{{ key }}</td>
                <td>
                  <v-chip size="x-small" :color="getFieldTypeColor(value)">
                    {{ getFieldType(value) }}
                  </v-chip>
                </td>
                <td class="text-truncate" style="max-width: 400px;">
                  <template v-if="typeof value === 'object'">
                    <v-chip size="x-small" variant="outlined">
                      {{ Array.isArray(value) ? `Array[${value.length}]` : 'Object' }}
                    </v-chip>
                  </template>
                  <template v-else>{{ formatFieldValue(value) }}</template>
                </td>
              </tr>
            </tbody>
          </v-table>
        </v-card-text>
      </v-card>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { format } from 'date-fns'
import { de } from 'date-fns/locale'

// Types
interface ExternalData {
  has_external_data: boolean
  external_source?: {
    name: string
  }
  sync_record?: {
    external_id: string
    last_seen_at?: string
  }
  raw_data?: Record<string, unknown>
}

// Props
defineProps<{
  externalData: ExternalData
}>()

const { t } = useI18n()

// Helper functions
function formatDate(dateString?: string): string {
  if (!dateString) return ''
  try {
    return format(new Date(dateString), 'dd.MM.yyyy HH:mm', { locale: de })
  } catch {
    return dateString
  }
}

function getFieldType(value: unknown): string {
  if (value === null) return 'null'
  if (Array.isArray(value)) return 'array'
  return typeof value
}

function getFieldTypeColor(value: unknown): string {
  const type = getFieldType(value)
  const colors: Record<string, string> = {
    string: 'blue',
    number: 'green',
    boolean: 'purple',
    object: 'orange',
    array: 'teal',
    null: 'grey',
  }
  return colors[type] || 'grey'
}

function formatFieldValue(value: unknown): string {
  if (value === null) return 'null'
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  if (typeof value === 'number') return value.toLocaleString('de-DE')
  return String(value)
}
</script>

<style scoped>
.json-viewer {
  background: rgba(0, 0, 0, 0.05);
  font-family: monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 400px;
  overflow-y: auto;
}
</style>
