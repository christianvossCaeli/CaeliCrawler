<template>
  <v-dialog v-model="modelValue" max-width="800" scrollable>
    <v-card v-if="facetGroup">
      <v-card-title class="d-flex align-center">
        <v-icon :icon="facetGroup.facet_type_icon" :color="facetGroup.facet_type_color" class="mr-2"></v-icon>
        {{ facetGroup.facet_type_name }}
        <v-spacer></v-spacer>
        <v-btn icon="mdi-close" variant="tonal" :aria-label="t('common.close')" @click="modelValue = false"></v-btn>
      </v-card-title>
      <v-card-text>
        <div class="d-flex flex-column ga-3">
          <v-card
            v-for="fv in facetValues"
            :key="fv.id"
            variant="outlined"
            class="pa-3"
          >
            <!-- Pain Point Display -->
            <template v-if="facetGroup.facet_type_slug === 'pain_point'">
              <div class="d-flex align-start ga-2">
                <v-icon color="error">mdi-alert-circle</v-icon>
                <div class="flex-grow-1">
                  <div class="text-body-1">{{ getStructuredDescription(fv) }}</div>
                  <div class="d-flex flex-wrap ga-2 mt-2">
                    <v-chip v-if="getStructuredType(fv)" size="small" variant="outlined" color="error">
                      {{ getStructuredType(fv) }}
                    </v-chip>
                    <v-chip
                      v-if="getStructuredSeverity(fv)"
                      size="small"
                      :color="getSeverityColor(getStructuredSeverity(fv))"
                    >
                      <v-icon start size="x-small">{{ getSeverityIcon(getStructuredSeverity(fv)) }}</v-icon>
                      {{ getStructuredSeverity(fv) }}
                    </v-chip>
                  </div>
                  <div v-if="getStructuredQuote(fv)" class="mt-2 pa-2 rounded bg-surface-variant">
                    <v-icon size="small" class="mr-1">mdi-format-quote-open</v-icon>
                    <span class="text-body-2 font-italic">{{ getStructuredQuote(fv) }}</span>
                  </div>
                </div>
              </div>
            </template>

            <!-- Positive Signal Display -->
            <template v-else-if="facetGroup.facet_type_slug === 'positive_signal'">
              <div class="d-flex align-start ga-2">
                <v-icon color="success">mdi-lightbulb-on</v-icon>
                <div class="flex-grow-1">
                  <div class="text-body-1">{{ getStructuredDescription(fv) }}</div>
                  <div class="d-flex flex-wrap ga-2 mt-2">
                    <v-chip v-if="getStructuredType(fv)" size="small" variant="outlined" color="success">
                      {{ getStructuredType(fv) }}
                    </v-chip>
                  </div>
                  <div v-if="getStructuredQuote(fv)" class="mt-2 pa-2 rounded bg-surface-variant">
                    <v-icon size="small" class="mr-1">mdi-format-quote-open</v-icon>
                    <span class="text-body-2 font-italic">{{ getStructuredQuote(fv) }}</span>
                  </div>
                </div>
              </div>
            </template>

            <!-- Contact Display -->
            <template v-else-if="facetGroup.facet_type_slug === 'contact'">
              <div class="d-flex align-start ga-2">
                <v-avatar color="primary" size="40">
                  <v-icon color="on-primary">mdi-account</v-icon>
                </v-avatar>
                <div class="flex-grow-1">
                  <div class="text-body-1 font-weight-medium">{{ getContactName(fv) }}</div>
                  <div v-if="getContactRole(fv)" class="text-body-2 text-medium-emphasis">{{ getContactRole(fv) }}</div>
                  <div class="d-flex flex-wrap ga-2 mt-2">
                    <v-chip v-if="getContactEmail(fv)" size="small" variant="outlined" @click.stop="$emit('copyEmail', getContactEmail(fv)!)">
                      <v-icon start size="small">mdi-email</v-icon>
                      {{ getContactEmail(fv) }}
                    </v-chip>
                    <v-chip v-if="getContactPhone(fv)" size="small" variant="outlined">
                      <v-icon start size="small">mdi-phone</v-icon>
                      {{ getContactPhone(fv) }}
                    </v-chip>
                    <v-chip
                      v-if="getContactSentiment(fv)"
                      size="small"
                      :color="getSentimentColor(getContactSentiment(fv))"
                    >
                      {{ getContactSentiment(fv) }}
                    </v-chip>
                  </div>
                  <div v-if="getContactStatement(fv)" class="mt-2 pa-2 rounded bg-surface-variant">
                    <v-icon size="small" class="mr-1">mdi-format-quote-open</v-icon>
                    <span class="text-body-2 font-italic">{{ getContactStatement(fv) }}</span>
                  </div>
                </div>
              </div>
            </template>

            <!-- Default Display -->
            <template v-else>
              <div class="text-body-1">{{ fv.text_representation || formatFacetValue(fv) }}</div>
            </template>

            <!-- Meta Info (shown for all) -->
            <v-divider class="my-3"></v-divider>
            <div class="d-flex align-center ga-2 flex-wrap">
              <v-progress-linear
                :model-value="(fv.confidence_score || 0) * 100"
                :color="getConfidenceColor(fv.confidence_score)"
                height="4"
                style="max-width: 80px;"
              ></v-progress-linear>
              <span class="text-caption">{{ Math.round((fv.confidence_score || 0) * 100) }}%</span>
              <v-chip v-if="fv.human_verified" size="x-small" color="success">
                <v-icon start size="x-small">mdi-check</v-icon>
                {{ t('entityDetail.verified') }}
              </v-chip>
              <v-chip v-if="fv.source_url" size="x-small" variant="outlined" :href="fv.source_url" target="_blank" tag="a">
                <v-icon start size="x-small">mdi-link</v-icon>
                {{ t('entityDetail.source') }}
              </v-chip>
              <v-spacer></v-spacer>
              <v-btn
                v-if="!fv.human_verified"
                size="small"
                color="success"
                variant="tonal"
                @click="$emit('verify', fv.id)"
              >
                <v-icon start size="small">mdi-check</v-icon>
                {{ t('entityDetail.verify') }}
              </v-btn>
            </div>

            <!-- Timestamps / History -->
            <div v-if="fv.created_at || fv.updated_at" class="mt-2 d-flex align-center ga-3 text-caption text-medium-emphasis">
              <span v-if="fv.created_at">
                <v-icon size="x-small" class="mr-1">mdi-clock-plus-outline</v-icon>
                {{ t('entityDetail.created') }}: {{ formatDate(fv.created_at) }}
              </span>
              <span v-if="fv.updated_at && fv.updated_at !== fv.created_at">
                <v-icon size="x-small" class="mr-1">mdi-clock-edit-outline</v-icon>
                {{ t('entityDetail.updated') }}: {{ formatDate(fv.updated_at) }}
              </span>
            </div>
          </v-card>
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { format } from 'date-fns'
import { de } from 'date-fns/locale'

const modelValue = defineModel<boolean>()

// Props
defineProps<{
  facetGroup: FacetGroup | null
  facetValues: FacetValue[]
}>()

// Emits
defineEmits<{
  verify: [id: string]
  copyEmail: [email: string]
}>()

// Types
interface FacetGroup {
  facet_type_id: string
  facet_type_name: string
  facet_type_slug: string
  facet_type_icon?: string
  facet_type_color?: string
  icon?: string
  color?: string
  value_type?: string
  value_count?: number
  values?: FacetValue[]
}

interface FacetValue {
  id: string
  facet_type_id?: string
  text_representation?: string | null
  value?: Record<string, unknown> | string | number | boolean | null
  confidence_score?: number | null
  human_verified?: boolean
  source_url?: string | null
  created_at?: string | null
  updated_at?: string | null
}

const { t } = useI18n()

// Helper functions
function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return ''
  try {
    return format(new Date(dateStr), 'dd.MM.yyyy HH:mm', { locale: de })
  } catch {
    return dateStr
  }
}

function formatFacetValue(fv: FacetValue): string {
  if (fv.text_representation) return fv.text_representation
  if (fv.value) {
    if (typeof fv.value === 'object') {
      return Object.values(fv.value).filter(Boolean).join(', ')
    }
    return String(fv.value)
  }
  return ''
}

function getConfidenceColor(score: number | null | undefined): string {
  if (score === null || score === undefined) return 'grey'
  if (score >= 0.8) return 'success'
  if (score >= 0.5) return 'warning'
  return 'error'
}

// Structured value helpers
function getStructuredDescription(fv: FacetValue): string {
  if (fv.value && typeof fv.value === 'object') {
    return (fv.value as Record<string, unknown>).description as string || fv.text_representation || ''
  }
  return fv.text_representation || ''
}

function getStructuredType(fv: FacetValue): string | null {
  if (fv.value && typeof fv.value === 'object') {
    return (fv.value as Record<string, unknown>).type as string || null
  }
  return null
}

function getStructuredSeverity(fv: FacetValue): string | null {
  if (fv.value && typeof fv.value === 'object') {
    return (fv.value as Record<string, unknown>).severity as string || null
  }
  return null
}

function getStructuredQuote(fv: FacetValue): string | null {
  if (fv.value && typeof fv.value === 'object') {
    return (fv.value as Record<string, unknown>).quote as string || null
  }
  return null
}

function getSeverityColor(severity: string | null): string {
  if (!severity) return 'grey'
  const lower = severity.toLowerCase()
  if (lower === 'high' || lower === 'hoch' || lower === 'critical' || lower === 'kritisch') return 'error'
  if (lower === 'medium' || lower === 'mittel') return 'warning'
  return 'info'
}

function getSeverityIcon(severity: string | null): string {
  if (!severity) return 'mdi-alert'
  const lower = severity.toLowerCase()
  if (lower === 'high' || lower === 'hoch' || lower === 'critical' || lower === 'kritisch') return 'mdi-alert-octagon'
  if (lower === 'medium' || lower === 'mittel') return 'mdi-alert'
  return 'mdi-information'
}

// Contact helpers
function getContactName(fv: FacetValue): string {
  if (fv.value && typeof fv.value === 'object') {
    const val = fv.value as Record<string, unknown>
    const firstName = val.first_name || val.firstName || ''
    const lastName = val.last_name || val.lastName || ''
    const name = val.name || ''
    if (firstName || lastName) return `${firstName} ${lastName}`.trim()
    return name as string || fv.text_representation || ''
  }
  return fv.text_representation || ''
}

function getContactRole(fv: FacetValue): string | null {
  if (fv.value && typeof fv.value === 'object') {
    const val = fv.value as Record<string, unknown>
    return (val.role || val.position || val.title) as string || null
  }
  return null
}

function getContactEmail(fv: FacetValue): string | null {
  if (fv.value && typeof fv.value === 'object') {
    return (fv.value as Record<string, unknown>).email as string || null
  }
  return null
}

function getContactPhone(fv: FacetValue): string | null {
  if (fv.value && typeof fv.value === 'object') {
    const val = fv.value as Record<string, unknown>
    return (val.phone || val.telephone) as string || null
  }
  return null
}

function getContactSentiment(fv: FacetValue): string | null {
  if (fv.value && typeof fv.value === 'object') {
    return (fv.value as Record<string, unknown>).sentiment as string || null
  }
  return null
}

function getSentimentColor(sentiment: string | null): string {
  if (!sentiment) return 'grey'
  const lower = sentiment.toLowerCase()
  if (lower === 'positive' || lower === 'positiv') return 'success'
  if (lower === 'negative' || lower === 'negativ') return 'error'
  return 'grey'
}

function getContactStatement(fv: FacetValue): string | null {
  if (fv.value && typeof fv.value === 'object') {
    const val = fv.value as Record<string, unknown>
    return (val.statement || val.quote || val.notes) as string || null
  }
  return null
}
</script>
