<template>
  <v-card class="mt-4">
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-brain</v-icon>
      {{ t('entityDetail.extractions.title') }}
      <v-chip size="small" class="ml-2" color="primary">{{ total }}</v-chip>
    </v-card-title>

    <v-card-subtitle>
      {{ t('entityDetail.extractions.subtitle') }}
    </v-card-subtitle>

    <v-card-text>
      <!-- Loading State -->
      <div v-if="loading" class="text-center py-8">
        <v-progress-circular indeterminate color="primary"></v-progress-circular>
        <p class="mt-2 text-medium-emphasis">{{ t('common.loading') }}</p>
      </div>

      <!-- Empty State -->
      <v-alert v-else-if="!extractions.length" type="info" variant="tonal">
        {{ t('entityDetail.extractions.empty') }}
      </v-alert>

      <!-- Extractions List -->
      <div v-else>
        <v-list lines="three">
          <v-list-item
            v-for="extraction in extractions"
            :key="extraction.id"
            class="mb-2 rounded-lg"
            :class="{ 'bg-surface-light': !$vuetify.theme.current.dark, 'bg-grey-darken-4': $vuetify.theme.current.dark }"
          >
            <template #prepend>
              <v-avatar :color="getConfidenceColor(extraction.confidence_score)" variant="tonal">
                <v-icon>mdi-file-document-outline</v-icon>
              </v-avatar>
            </template>

            <v-list-item-title class="font-weight-medium">
              {{ extraction.document_title || t('results.detail.noTitle') }}
            </v-list-item-title>

            <v-list-item-subtitle>
              <div class="d-flex flex-wrap ga-2 mt-1">
                <!-- Extraction Type -->
                <v-chip size="small" color="primary" variant="tonal">
                  {{ extraction.extraction_type }}
                </v-chip>

                <!-- Source -->
                <v-chip v-if="extraction.source_name" size="small" variant="outlined">
                  <v-icon start size="small">mdi-web</v-icon>
                  {{ extraction.source_name }}
                </v-chip>

                <!-- Confidence -->
                <v-chip v-if="extraction.confidence_score" size="small" :color="getConfidenceColor(extraction.confidence_score)">
                  {{ Math.round(extraction.confidence_score * 100) }}%
                </v-chip>

                <!-- Verified Badge -->
                <v-chip v-if="extraction.human_verified" size="small" color="success" variant="flat">
                  <v-icon start size="small">mdi-check-circle</v-icon>
                  {{ t('entityDetail.verified') }}
                </v-chip>

                <!-- Date -->
                <v-chip size="small" variant="text">
                  <v-icon start size="small">mdi-calendar</v-icon>
                  {{ formatDate(extraction.created_at) }}
                </v-chip>
              </div>

              <!-- Summary if available -->
              <div v-if="getSummary(extraction)" class="mt-2 text-body-2">
                {{ getSummary(extraction) }}
              </div>
            </v-list-item-subtitle>

            <template #append>
              <v-btn
                icon
                variant="text"
                size="small"
                :to="`/results?search=${encodeURIComponent(extraction.document_title || '')}`"
              >
                <v-icon>mdi-eye</v-icon>
                <v-tooltip activator="parent" location="top">
                  {{ t('entityDetail.extractions.viewResult') }}
                </v-tooltip>
              </v-btn>
            </template>
          </v-list-item>
        </v-list>

        <!-- Pagination -->
        <v-pagination
          v-if="totalPages > 1"
          v-model="page"
          :length="totalPages"
          :total-visible="5"
          class="mt-4"
          @update:model-value="loadExtractions"
        ></v-pagination>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { dataApi } from '@/services/api'
import { useLogger } from '@/composables/useLogger'
import { useDateFormatter } from '@/composables/useDateFormatter'

interface Extraction {
  id: string
  document_id: string
  document_title?: string
  document_url?: string
  source_name?: string
  extraction_type: string
  extracted_content?: Record<string, unknown>
  final_content?: Record<string, unknown>
  confidence_score?: number
  human_verified: boolean
  created_at: string
}

const props = defineProps<{
  entityId: string
  entityName: string
}>()

const { t } = useI18n()
const logger = useLogger('EntityExtractionsTab')
const { formatDate } = useDateFormatter()

// State
const loading = ref(true)
const extractions = ref<Extraction[]>([])
const page = ref(1)
const perPage = ref(10)
const total = ref(0)
const totalPages = ref(1)

// Load extractions referencing this entity
async function loadExtractions() {
  loading.value = true
  try {
    const response = await dataApi.getExtractionsByEntity(props.entityId, {
      page: page.value,
      per_page: perPage.value,
    })
    extractions.value = response.data.items || []
    total.value = response.data.total || 0
    totalPages.value = response.data.pages || 1
  } catch (e) {
    logger.error('Failed to load extractions', e)
    extractions.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

// Get summary from extraction content
function getSummary(extraction: Extraction): string | null {
  const content = extraction.final_content || extraction.extracted_content
  if (!content) return null
  return (content.summary as string) || null
}

// Get confidence color
function getConfidenceColor(score?: number): string {
  if (!score) return 'grey'
  if (score >= 0.8) return 'success'
  if (score >= 0.5) return 'warning'
  return 'error'
}

onMounted(() => {
  loadExtractions()
})
</script>
