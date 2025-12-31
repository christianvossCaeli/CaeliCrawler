<template>
  <v-card class="mt-4">
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-link-variant</v-icon>
      {{ t('entityDetail.referencedBy.title', 'Referenziert in') }}
      <v-chip size="small" class="ml-2">{{ total }}</v-chip>
    </v-card-title>

    <v-card-subtitle>
      {{ t('entityDetail.referencedBy.subtitle', 'Zeigt alle Facets, die auf diesen Datensatz verweisen') }}
    </v-card-subtitle>

    <v-card-text>
      <!-- Loading State -->
      <div v-if="loading" class="text-center py-8">
        <v-progress-circular indeterminate color="primary"></v-progress-circular>
        <p class="mt-2 text-medium-emphasis">{{ t('common.loading') }}</p>
      </div>

      <!-- Empty State -->
      <v-alert v-else-if="!facetValues.length" type="info" variant="tonal">
        {{ t('entityDetail.referencedBy.empty', 'Dieser Datensatz wird derzeit in keinen Facets referenziert.') }}
      </v-alert>

      <!-- Facet Values List -->
      <div v-else>
        <v-list lines="three">
          <v-list-item
            v-for="facet in facetValues"
            :key="facet.id"
            class="mb-2 rounded-lg"
            :class="{ 'bg-surface-light': !$vuetify.theme.current.dark, 'bg-grey-darken-4': $vuetify.theme.current.dark }"
          >
            <template #prepend>
              <v-avatar color="primary" variant="tonal">
                <v-icon>mdi-tag</v-icon>
              </v-avatar>
            </template>

            <v-list-item-title class="font-weight-medium">
              {{ facet.text_representation || getValueDisplay(facet) }}
            </v-list-item-title>

            <v-list-item-subtitle>
              <div class="d-flex flex-wrap ga-2 mt-1">
                <!-- Facet Type Badge -->
                <v-chip size="small" variant="outlined">
                  <v-icon start size="small">mdi-tag-outline</v-icon>
                  {{ facet.facet_type_name }}
                </v-chip>

                <!-- Source Entity Link -->
                <v-chip
                  size="small"
                  color="primary"
                  variant="tonal"
                  class="cursor-pointer"
                  @click="navigateToEntity(facet)"
                >
                  <v-icon start size="small">mdi-database</v-icon>
                  {{ facet.entity_name }}
                </v-chip>

                <!-- Source Document -->
                <v-chip v-if="facet.document_title" size="small" variant="outlined">
                  <v-icon start size="small">mdi-file-document</v-icon>
                  {{ facet.document_title }}
                </v-chip>

                <!-- Confidence -->
                <v-chip v-if="facet.confidence_score" size="small" :color="getConfidenceColor(facet.confidence_score)">
                  {{ Math.round(facet.confidence_score * 100) }}%
                </v-chip>

                <!-- Verified Badge -->
                <v-chip v-if="facet.human_verified" size="small" color="success" variant="flat">
                  <v-icon start size="small">mdi-check-circle</v-icon>
                  {{ t('entityDetail.verified') }}
                </v-chip>
              </div>
            </v-list-item-subtitle>

            <template #append>
              <v-btn
                icon
                variant="text"
                size="small"
                @click="navigateToEntity(facet)"
              >
                <v-icon>mdi-arrow-right</v-icon>
                <v-tooltip activator="parent" location="top">
                  {{ t('entityDetail.referencedBy.goToSource', 'Zum Quell-Datensatz') }}
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
          @update:model-value="loadFacets"
        ></v-pagination>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { facetApi } from '@/services/api'
import type { FacetValue } from '@/types/entity'
import { useLogger } from '@/composables/useLogger'

const props = defineProps<{
  entityId: string
  entityName: string
}>()

const { t } = useI18n()
const router = useRouter()
const logger = useLogger('EntityReferencedByTab')

// State
const loading = ref(true)
const facetValues = ref<FacetValue[]>([])
const page = ref(1)
const perPage = ref(20)
const total = ref(0)
const totalPages = ref(1)

// Load facets that reference this entity
async function loadFacets() {
  loading.value = true
  try {
    const response = await facetApi.getFacetsReferencingEntity(props.entityId, {
      page: page.value,
      per_page: perPage.value,
    })
    facetValues.value = response.data.items || []
    total.value = response.data.total || 0
    totalPages.value = response.data.pages || 1
  } catch (e) {
    logger.error('Failed to load referencing facets', e)
    facetValues.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

// Navigate to the entity that contains this facet
function navigateToEntity(facet: FacetValue) {
  if (!facet.entity_id) return

  // Use the generic entity-by-id route for navigation
  router.push({
    name: 'entity-by-id',
    params: { id: facet.entity_id },
  })
}

// Get display value from facet
function getValueDisplay(facet: FacetValue): string {
  if (typeof facet.value === 'string') return facet.value
  if (facet.value && typeof facet.value === 'object') {
    const v = facet.value as Record<string, unknown>
    return (v.name || v.description || v.text || JSON.stringify(facet.value)) as string
  }
  return '-'
}

// Get confidence color
function getConfidenceColor(score: number): string {
  if (score >= 0.8) return 'success'
  if (score >= 0.5) return 'warning'
  return 'error'
}

onMounted(() => {
  loadFacets()
})
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}
</style>
