<template>
  <v-dialog v-model="modelValue" max-width="600" scrollable>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start :color="getFacetSourceColor(sourceFacet?.source_type)">
          {{ getFacetSourceIcon(sourceFacet?.source_type) }}
        </v-icon>
        {{ t('entityDetail.source') }}
        <v-spacer></v-spacer>
        <v-btn icon="mdi-close" variant="tonal" :aria-label="t('common.close')" @click="modelValue = false"></v-btn>
      </v-card-title>
      <v-card-text v-if="sourceFacet">
        <!-- Source Type Info -->
        <v-chip
          size="small"
          :color="getFacetSourceColor(sourceFacet.source_type)"
          class="mb-4"
        >
          <v-icon start size="small">{{ getFacetSourceIcon(sourceFacet.source_type) }}</v-icon>
          {{ getFacetSourceLabel(sourceFacet.source_type) }}
        </v-chip>

        <!-- Document Source -->
        <template v-if="sourceFacet.source_type === 'DOCUMENT'">
          <div v-if="sourceFacet.document_title" class="mb-3">
            <div class="text-caption text-medium-emphasis mb-1">{{ t('entityDetail.document') }}</div>
            <div class="text-body-1">{{ sourceFacet.document_title }}</div>
          </div>
          <div v-if="sourceFacet.document_url" class="mb-3">
            <v-btn
              :href="sourceFacet.document_url"
              target="_blank"
              color="primary"
              variant="tonal"
              size="small"
            >
              <v-icon start>mdi-file-document</v-icon>
              {{ t('common.openDocument') }}
            </v-btn>
          </div>
        </template>

        <!-- PySis Source -->
        <template v-else-if="sourceFacet.source_type === 'PYSIS'">
          <v-alert type="info" variant="tonal" density="compact" class="mb-3">
            {{ t('entityDetail.sourceTypes.pysis') }}
          </v-alert>

          <!-- PySis Process Info -->
          <div v-if="pysisInfo" class="mb-3">
            <div v-if="pysisInfo.processTitle" class="mb-2">
              <div class="text-caption text-medium-emphasis">Prozess</div>
              <div class="text-body-1">{{ pysisInfo.processTitle }}</div>
            </div>
            <div v-if="pysisInfo.processId" class="mb-2">
              <div class="text-caption text-medium-emphasis">Prozess-ID</div>
              <code class="text-body-2">{{ pysisInfo.processId }}</code>
            </div>
            <div v-if="pysisInfo.fieldNames?.length" class="mb-2">
              <div class="text-caption text-medium-emphasis mb-1">Feldname(n)</div>
              <div class="d-flex flex-wrap ga-1">
                <v-chip
                  v-for="fieldName in pysisInfo.fieldNames"
                  :key="fieldName"
                  size="small"
                  variant="outlined"
                  color="secondary"
                >
                  {{ fieldName }}
                </v-chip>
              </div>
            </div>
          </div>

          <!-- PySis Field Values -->
          <div v-if="sourceFacet.value?.pysis_fields" class="mb-3">
            <div class="text-caption text-medium-emphasis mb-2">Feldwerte</div>
            <v-list density="compact" class="bg-surface-variant rounded">
              <v-list-item
                v-for="(fieldValue, fieldName) in sourceFacet.value.pysis_fields"
                :key="String(fieldName)"
              >
                <v-list-item-title class="text-caption font-weight-medium">{{ fieldName }}</v-list-item-title>
                <v-list-item-subtitle>{{ fieldValue }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </div>
        </template>

        <!-- Manual Source -->
        <template v-else-if="sourceFacet.source_type === 'MANUAL'">
          <v-alert type="success" variant="tonal" density="compact" class="mb-3">
            {{ t('entityDetail.sourceTypes.manual') }}
          </v-alert>
          <div v-if="sourceFacet.verified_by" class="text-body-2">
            {{ t('common.createdBy') }}: {{ sourceFacet.verified_by }}
          </div>
        </template>

        <!-- Smart Query Source -->
        <template v-else-if="sourceFacet.source_type === 'SMART_QUERY'">
          <v-alert type="info" variant="tonal" density="compact" class="mb-3">
            {{ t('entityDetail.sourceTypes.smartQuery') }}
          </v-alert>
        </template>

        <!-- AI Assistant Source -->
        <template v-else-if="sourceFacet.source_type === 'AI_ASSISTANT'">
          <v-alert color="info" variant="tonal" density="compact" class="mb-3">
            {{ t('entityDetail.sourceTypes.aiAssistant') }}
          </v-alert>
          <div v-if="sourceFacet.ai_model_used" class="text-body-2 mb-2">
            Model: {{ sourceFacet.ai_model_used }}
          </div>
        </template>

        <!-- Import Source -->
        <template v-else-if="sourceFacet.source_type === 'IMPORT'">
          <v-alert type="warning" variant="tonal" density="compact" class="mb-3">
            {{ t('entityDetail.sourceTypes.import') }}
          </v-alert>
        </template>

        <!-- Source URL (shown for web URLs, excluding PySis which shows structured info above) -->
        <div v-if="sourceFacet.source_url && isValidWebUrl(sourceFacet.source_url) && sourceFacet.source_type !== 'PYSIS'" class="mt-4">
          <div class="text-caption text-medium-emphasis mb-1">{{ t('entities.facet.sourceUrl') }}</div>
          <v-btn
            :href="sourceFacet.source_url"
            target="_blank"
            color="primary"
            variant="tonal"
            size="small"
            class="text-none"
          >
            <v-icon start size="small">mdi-open-in-new</v-icon>
            {{ sourceFacet.source_url }}
          </v-btn>
        </div>

        <!-- Confidence & Dates -->
        <v-divider class="my-4"></v-divider>
        <div class="d-flex flex-wrap ga-4">
          <div v-if="sourceFacet.confidence_score != null">
            <div class="text-caption text-medium-emphasis">{{ t('entities.facet.confidence') }}</div>
            <div class="text-body-2">{{ Math.round(sourceFacet.confidence_score * 100) }}%</div>
          </div>
          <div v-if="sourceFacet.created_at">
            <div class="text-caption text-medium-emphasis">{{ t('entityDetail.created') }}</div>
            <div class="text-body-2">{{ formatDate(sourceFacet.created_at) }}</div>
          </div>
          <div v-if="sourceFacet.human_verified">
            <div class="text-caption text-medium-emphasis">{{ t('entityDetail.verifiedLabel') }}</div>
            <div class="text-body-2">
              <v-icon color="success" size="small">mdi-check-circle</v-icon>
              {{ sourceFacet.verified_at ? formatDate(sourceFacet.verified_at) : 'Yes' }}
            </div>
          </div>
        </div>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" @click="modelValue = false">{{ t('common.close') }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { format } from 'date-fns'
import { de } from 'date-fns/locale'

const modelValue = defineModel<boolean>()

// Props
const props = defineProps<{
  sourceFacet: SourceFacet | null
}>()

// Emits
defineEmits<{
  (e: 'close'): void
}>()

// Types
interface SourceFacet {
  source_type: string
  source_url?: string | null
  document_title?: string | null
  document_url?: string | null
  verified_by?: string | null
  ai_model_used?: string | null
  confidence_score?: number | null
  created_at?: string | null
  verified_at?: string | null
  human_verified?: boolean
  value?: {
    pysis_fields?: Record<string, unknown>
    pysis_source?: {
      process_title?: string
      process_id?: string
      field_names?: string[]
    }
  } | null
}

interface PysisInfo {
  processTitle?: string
  processId?: string
  fieldNames?: string[]
}

const { t } = useI18n()

// Computed
const pysisInfo = computed<PysisInfo | null>(() => {
  if (!props.sourceFacet?.value?.pysis_source) return null
  const src = props.sourceFacet.value.pysis_source
  return {
    processTitle: src.process_title,
    processId: src.process_id,
    fieldNames: src.field_names
  }
})

// Helpers
function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return ''
  try {
    return format(new Date(dateStr), 'dd.MM.yyyy HH:mm', { locale: de })
  } catch {
    return dateStr
  }
}

function getFacetSourceColor(sourceType: string | undefined): string {
  if (!sourceType) return 'grey'
  const colors: Record<string, string> = {
    DOCUMENT: 'blue',
    PYSIS: 'purple',
    MANUAL: 'success',
    SMART_QUERY: 'info',
    AI_ASSISTANT: 'deep-purple',
    IMPORT: 'warning'
  }
  return colors[sourceType] || 'grey'
}

function getFacetSourceIcon(sourceType: string | undefined): string {
  if (!sourceType) return 'mdi-help-circle'
  const icons: Record<string, string> = {
    DOCUMENT: 'mdi-file-document',
    PYSIS: 'mdi-database',
    MANUAL: 'mdi-account-check',
    SMART_QUERY: 'mdi-brain',
    AI_ASSISTANT: 'mdi-robot',
    IMPORT: 'mdi-import'
  }
  return icons[sourceType] || 'mdi-help-circle'
}

function getFacetSourceLabel(sourceType: string | undefined): string {
  if (!sourceType) return 'Unknown'
  const labels: Record<string, string> = {
    DOCUMENT: 'Dokument',
    PYSIS: 'PySis',
    MANUAL: 'Manuell',
    SMART_QUERY: 'Smart Query',
    AI_ASSISTANT: 'KI-Assistent',
    IMPORT: 'Import'
  }
  return labels[sourceType] || sourceType
}

function isValidWebUrl(url: string | null | undefined): boolean {
  if (!url) return false
  try {
    const parsed = new URL(url)
    return ['http:', 'https:'].includes(parsed.protocol)
  } catch {
    return false
  }
}
</script>
