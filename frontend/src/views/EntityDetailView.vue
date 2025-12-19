<template>
  <div>
    <!-- Loading State -->
    <v-overlay :model-value="loading" class="align-center justify-center" persistent scrim="rgba(0,0,0,0.7)">
      <v-card class="pa-8 text-center" min-width="320" elevation="24">
        <v-progress-circular indeterminate size="80" width="6" color="primary" class="mb-4"></v-progress-circular>
        <div class="text-h6 mb-2">Lade Details</div>
      </v-card>
    </v-overlay>

    <!-- Breadcrumbs -->
    <v-breadcrumbs :items="breadcrumbs" class="px-0">
      <template v-slot:prepend>
        <v-icon icon="mdi-home" size="small"></v-icon>
      </template>
    </v-breadcrumbs>

    <!-- Entity Header -->
    <v-card v-if="entity" class="mb-6">
      <v-card-text>
        <div class="d-flex align-center">
          <v-icon :icon="entityType?.icon || 'mdi-folder'" :color="entityType?.color" size="48" class="mr-4"></v-icon>
          <div class="flex-grow-1">
            <div class="d-flex align-center mb-1">
              <h1 class="text-h4 mr-3">{{ entity.name }}</h1>
              <v-chip v-if="entity.external_id" size="small" variant="outlined">
                {{ entity.external_id }}
              </v-chip>
            </div>
            <div v-if="entity.hierarchy_path" class="text-body-2 text-grey">
              {{ entity.hierarchy_path }}
            </div>
          </div>
          <div class="d-flex ga-2">
            <v-btn variant="outlined" @click="editDialog = true">
              <v-icon start>mdi-pencil</v-icon>
              Bearbeiten
            </v-btn>
            <v-btn color="primary" @click="addFacetDialog = true">
              <v-icon start>mdi-plus</v-icon>
              Facet hinzufuegen
            </v-btn>
          </div>
        </div>

        <!-- Stats Row -->
        <v-row class="mt-4">
          <v-col cols="6" sm="3" md="2">
            <div class="text-center">
              <div class="text-h5">{{ entity.facet_count || 0 }}</div>
              <div class="text-caption text-grey">Facet-Werte</div>
            </div>
          </v-col>
          <v-col cols="6" sm="3" md="2">
            <div class="text-center">
              <div class="text-h5">{{ entity.relation_count || 0 }}</div>
              <div class="text-caption text-grey">Verknuepfungen</div>
            </div>
          </v-col>
          <v-col cols="6" sm="3" md="2">
            <div class="text-center">
              <div class="text-h5">{{ facetsSummary?.verified_count || 0 }}</div>
              <div class="text-caption text-grey">Verifiziert</div>
            </div>
          </v-col>
          <v-col cols="6" sm="3" md="2">
            <div class="text-center">
              <div class="text-h5">{{ dataSources.length }}</div>
              <div class="text-caption text-grey">Datenquellen</div>
            </div>
          </v-col>
          <v-col v-if="entity.latitude && entity.longitude" cols="12" sm="6" md="4">
            <div class="text-center">
              <v-chip size="small" color="info">
                <v-icon start size="small">mdi-map-marker</v-icon>
                {{ entity.latitude.toFixed(4) }}, {{ entity.longitude.toFixed(4) }}
              </v-chip>
            </div>
          </v-col>
        </v-row>

        <!-- Core Attributes -->
        <v-row v-if="hasAttributes" class="mt-2">
          <v-col v-for="(value, key) in entity.core_attributes" :key="key" cols="auto">
            <v-chip size="small" variant="tonal">
              <strong class="mr-1">{{ formatAttributeKey(key) }}:</strong>
              {{ formatAttributeValue(value) }}
            </v-chip>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Tabs for Content -->
    <v-tabs v-model="activeTab" color="primary" class="mb-4">
      <v-tab value="facets">
        <v-icon start>mdi-tag-multiple</v-icon>
        Facets
        <v-chip v-if="facetsSummary" size="x-small" class="ml-2">{{ facetsSummary.total_facet_values }}</v-chip>
      </v-tab>
      <v-tab value="relations">
        <v-icon start>mdi-link</v-icon>
        Verknuepfungen
        <v-chip v-if="relations.length" size="x-small" class="ml-2">{{ relations.length }}</v-chip>
      </v-tab>
      <v-tab value="sources">
        <v-icon start>mdi-web</v-icon>
        Datenquellen
        <v-chip v-if="dataSources.length" size="x-small" class="ml-2">{{ dataSources.length }}</v-chip>
      </v-tab>
      <v-tab value="documents">
        <v-icon start>mdi-file-document-multiple</v-icon>
        Dokumente
      </v-tab>
      <v-tab v-if="entityType?.slug === 'municipality'" value="pysis">
        <v-icon start>mdi-database-sync</v-icon>
        PySis
      </v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <!-- Facets Tab -->
      <v-window-item value="facets">
        <v-row>
          <v-col
            v-for="facetGroup in facetsSummary?.facets_by_type || []"
            :key="facetGroup.facet_type_id"
            cols="12"
          >
            <v-card>
              <v-card-title class="d-flex align-center">
                <v-icon :icon="facetGroup.facet_type_icon" :color="facetGroup.facet_type_color" class="mr-2"></v-icon>
                {{ facetGroup.facet_type_name }}
                <v-chip size="small" class="ml-2">{{ facetGroup.value_count }}</v-chip>
                <v-chip v-if="facetGroup.verified_count" size="x-small" color="success" class="ml-1">
                  {{ facetGroup.verified_count }} verifiziert
                </v-chip>
                <v-spacer></v-spacer>
                <v-btn size="small" variant="text" @click="toggleFacetExpand(facetGroup.facet_type_slug)">
                  <v-icon>{{ expandedFacets.includes(facetGroup.facet_type_slug) ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
                </v-btn>
              </v-card-title>

              <v-expand-transition>
                <v-card-text v-show="expandedFacets.includes(facetGroup.facet_type_slug)">
                  <!-- Sample Values Preview -->
                  <div v-if="facetGroup.sample_values?.length" class="mb-4">
                    <div
                      v-for="(sample, idx) in facetGroup.sample_values.slice(0, 3)"
                      :key="idx"
                      class="mb-2 pa-3 rounded"
                      :style="{ backgroundColor: 'rgba(var(--v-theme-surface-variant), 0.3)' }"
                    >
                      <div class="text-body-1">{{ formatFacetValue(sample) }}</div>
                      <div v-if="sample.confidence_score" class="d-flex align-center mt-1">
                        <v-progress-linear
                          :model-value="sample.confidence_score * 100"
                          :color="getConfidenceColor(sample.confidence_score)"
                          height="4"
                          class="mr-2"
                          style="max-width: 100px;"
                        ></v-progress-linear>
                        <span class="text-caption text-grey">{{ Math.round(sample.confidence_score * 100) }}%</span>
                        <v-chip v-if="sample.human_verified" size="x-small" color="success" class="ml-2">
                          <v-icon size="x-small">mdi-check</v-icon>
                        </v-chip>
                      </div>
                    </div>
                  </div>

                  <!-- Show All Button -->
                  <v-btn
                    v-if="facetGroup.value_count > 3"
                    variant="text"
                    size="small"
                    @click="openFacetDetails(facetGroup)"
                  >
                    Alle {{ facetGroup.value_count }} anzeigen
                    <v-icon end>mdi-arrow-right</v-icon>
                  </v-btn>
                </v-card-text>
              </v-expand-transition>
            </v-card>
          </v-col>
        </v-row>

        <v-alert v-if="!facetsSummary?.facets_by_type?.length" type="info" variant="tonal" class="mt-4">
          Noch keine Facet-Werte vorhanden.
          <v-btn variant="text" size="small" @click="addFacetDialog = true">Facet hinzufuegen</v-btn>
        </v-alert>
      </v-window-item>

      <!-- Relations Tab -->
      <v-window-item value="relations">
        <v-card>
          <v-card-text>
            <div v-if="relations.length">
              <v-list>
                <v-list-item
                  v-for="rel in relations"
                  :key="rel.id"
                  @click="navigateToRelatedEntity(rel)"
                  class="cursor-pointer"
                >
                  <template v-slot:prepend>
                    <v-icon :color="rel.relation_type_color || 'primary'">mdi-link-variant</v-icon>
                  </template>
                  <v-list-item-title>
                    <span v-if="rel.source_entity_id === entity?.id">
                      {{ rel.relation_type_name }}: <strong>{{ rel.target_entity_name }}</strong>
                    </span>
                    <span v-else>
                      {{ rel.relation_type_name_inverse || rel.relation_type_name }}: <strong>{{ rel.source_entity_name }}</strong>
                    </span>
                  </v-list-item-title>
                  <v-list-item-subtitle v-if="rel.attributes && Object.keys(rel.attributes).length">
                    <v-chip v-for="(val, key) in rel.attributes" :key="key" size="x-small" class="mr-1">
                      {{ key }}: {{ val }}
                    </v-chip>
                  </v-list-item-subtitle>
                  <template v-slot:append>
                    <div class="d-flex align-center ga-2">
                      <v-chip v-if="rel.human_verified" size="x-small" color="success">
                        <v-icon size="x-small">mdi-check</v-icon>
                      </v-chip>
                      <v-icon>mdi-chevron-right</v-icon>
                    </div>
                  </template>
                </v-list-item>
              </v-list>
            </div>
            <v-alert v-else type="info" variant="tonal">
              Keine Verknuepfungen vorhanden.
              <v-btn variant="text" size="small" @click="addRelationDialog = true">Verknuepfung hinzufuegen</v-btn>
            </v-alert>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- Data Sources Tab -->
      <v-window-item value="sources">
        <v-card>
          <v-card-text>
            <div v-if="loadingDataSources" class="text-center pa-4">
              <v-progress-circular indeterminate></v-progress-circular>
            </div>
            <div v-else-if="dataSources.length">
              <v-list>
                <v-list-item
                  v-for="source in dataSources"
                  :key="source.id"
                >
                  <template v-slot:prepend>
                    <v-icon :color="getSourceStatusColor(source.status)">
                      {{ getSourceStatusIcon(source.status) }}
                    </v-icon>
                  </template>
                  <v-list-item-title>
                    {{ source.name }}
                    <v-chip v-if="source.hasRunningJob" size="x-small" color="info" class="ml-2">
                      Laeuft
                    </v-chip>
                  </v-list-item-title>
                  <v-list-item-subtitle>
                    <a :href="source.base_url" target="_blank" class="text-decoration-none">
                      {{ source.base_url }}
                    </a>
                  </v-list-item-subtitle>
                  <template v-slot:append>
                    <v-btn
                      v-if="!source.hasRunningJob"
                      size="small"
                      color="primary"
                      variant="tonal"
                      @click="startCrawl(source)"
                      :loading="startingCrawl === source.id"
                    >
                      <v-icon start>mdi-play</v-icon>
                      Crawlen
                    </v-btn>
                  </template>
                </v-list-item>
              </v-list>
            </div>
            <v-alert v-else type="info" variant="tonal">
              Keine Datenquellen verknuepft.
              <v-btn variant="text" size="small" @click="goToSources">Datenquelle hinzufuegen</v-btn>
            </v-alert>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- Documents Tab -->
      <v-window-item value="documents">
        <v-card>
          <v-card-text>
            <div v-if="loadingDocuments" class="text-center pa-4">
              <v-progress-circular indeterminate></v-progress-circular>
            </div>
            <v-data-table
              v-else
              :headers="documentHeaders"
              :items="documents"
              :items-per-page="10"
            >
              <template v-slot:item.title="{ item }">
                <a :href="item.url" target="_blank" class="text-decoration-none">
                  {{ item.title || 'Dokument' }}
                </a>
              </template>
              <template v-slot:item.created_at="{ item }">
                {{ formatDate(item.created_at) }}
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- PySis Tab (only for municipalities) -->
      <v-window-item v-if="entityType?.slug === 'municipality'" value="pysis" eager>
        <PySisTab
          v-if="entity"
          :municipality="entity.name"
        />
      </v-window-item>
    </v-window>

    <!-- Add Facet Dialog -->
    <v-dialog v-model="addFacetDialog" max-width="600">
      <v-card>
        <v-card-title>Facet hinzufuegen</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveFacetValue">
            <v-select
              v-model="newFacet.facet_type_id"
              :items="store.activeFacetTypes"
              item-title="name"
              item-value="id"
              label="Facet-Typ *"
              :rules="[v => !!v || 'Facet-Typ ist erforderlich']"
            ></v-select>

            <v-textarea
              v-model="newFacet.text_representation"
              label="Wert / Beschreibung *"
              :rules="[v => !!v || 'Wert ist erforderlich']"
              rows="3"
            ></v-textarea>

            <v-text-field
              v-model="newFacet.source_url"
              label="Quell-URL"
              placeholder="https://..."
            ></v-text-field>

            <v-slider
              v-model="newFacet.confidence_score"
              label="Konfidenz"
              :min="0"
              :max="1"
              :step="0.1"
              thumb-label
              :color="getConfidenceColor(newFacet.confidence_score)"
            ></v-slider>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="addFacetDialog = false">Abbrechen</v-btn>
          <v-btn
            color="primary"
            :loading="savingFacet"
            @click="saveFacetValue"
          >
            Speichern
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Facet Details Dialog -->
    <v-dialog v-model="facetDetailsDialog" max-width="800" scrollable>
      <v-card v-if="selectedFacetGroup">
        <v-card-title class="d-flex align-center">
          <v-icon :icon="selectedFacetGroup.facet_type_icon" :color="selectedFacetGroup.facet_type_color" class="mr-2"></v-icon>
          {{ selectedFacetGroup.facet_type_name }}
          <v-spacer></v-spacer>
          <v-btn icon="mdi-close" variant="text" @click="facetDetailsDialog = false"></v-btn>
        </v-card-title>
        <v-card-text>
          <v-list>
            <v-list-item
              v-for="fv in facetDetails"
              :key="fv.id"
            >
              <v-list-item-title>{{ fv.text_representation }}</v-list-item-title>
              <v-list-item-subtitle>
                <div class="d-flex align-center ga-2 mt-1">
                  <v-progress-linear
                    :model-value="(fv.confidence_score || 0) * 100"
                    :color="getConfidenceColor(fv.confidence_score)"
                    height="4"
                    style="max-width: 80px;"
                  ></v-progress-linear>
                  <span class="text-caption">{{ Math.round((fv.confidence_score || 0) * 100) }}%</span>
                  <v-chip v-if="fv.human_verified" size="x-small" color="success">Verifiziert</v-chip>
                  <v-chip v-if="fv.source_url" size="x-small" variant="outlined" :href="fv.source_url" target="_blank">
                    <v-icon start size="x-small">mdi-link</v-icon>
                    Quelle
                  </v-chip>
                </div>
              </v-list-item-subtitle>
              <template v-slot:append>
                <v-btn
                  v-if="!fv.human_verified"
                  icon="mdi-check"
                  size="small"
                  color="success"
                  variant="text"
                  title="Verifizieren"
                  @click="verifyFacet(fv.id)"
                ></v-btn>
              </template>
            </v-list-item>
          </v-list>
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- Edit Entity Dialog -->
    <v-dialog v-model="editDialog" max-width="500">
      <v-card>
        <v-card-title>{{ entityType?.name }} bearbeiten</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveEntity">
            <v-text-field
              v-model="editForm.name"
              label="Name *"
              :rules="[v => !!v || 'Name ist erforderlich']"
            ></v-text-field>
            <v-text-field
              v-model="editForm.external_id"
              label="Externe ID"
            ></v-text-field>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="editDialog = false">Abbrechen</v-btn>
          <v-btn color="primary" :loading="savingEntity" @click="saveEntity">
            Speichern
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEntityStore } from '@/stores/entity'
import { adminApi, facetApi, relationApi } from '@/services/api'
import { format } from 'date-fns'
import { de } from 'date-fns/locale'
import { useSnackbar } from '@/composables/useSnackbar'
import PySisTab from '@/components/PySisTab.vue'

const { showSuccess, showError } = useSnackbar()
const route = useRoute()
const router = useRouter()
const store = useEntityStore()

// Route params
const typeSlug = computed(() => route.params.typeSlug as string)
const entitySlug = computed(() => route.params.entitySlug as string)

// State
const loading = ref(true)
const activeTab = ref('facets')
const expandedFacets = ref<string[]>([])

// Entity data
const entity = computed(() => store.selectedEntity)
const entityType = computed(() => store.selectedEntityType)
const facetsSummary = ref<any>(null)
const relations = ref<any[]>([])
const dataSources = ref<any[]>([])
const documents = ref<any[]>([])

// Loading states
const loadingDataSources = ref(false)
const loadingDocuments = ref(false)
const startingCrawl = ref<string | null>(null)

// Dialogs
const addFacetDialog = ref(false)
const addRelationDialog = ref(false)
const facetDetailsDialog = ref(false)
const editDialog = ref(false)
const selectedFacetGroup = ref<any>(null)
const facetDetails = ref<any[]>([])

// Forms
const newFacet = ref({
  facet_type_id: '',
  text_representation: '',
  source_url: '',
  confidence_score: 0.8,
})

const editForm = ref({
  name: '',
  external_id: '',
})

const savingFacet = ref(false)
const savingEntity = ref(false)

// Computed
const breadcrumbs = computed(() => [
  { title: 'Dashboard', to: '/' },
  { title: entityType.value?.name_plural || 'Entities', to: `/entities/${typeSlug.value}` },
  { title: entity.value?.name || '...', disabled: true },
])

const hasAttributes = computed(() =>
  entity.value?.core_attributes && Object.keys(entity.value.core_attributes).length > 0
)

const documentHeaders = [
  { title: 'Titel', key: 'title' },
  { title: 'Typ', key: 'document_type' },
  { title: 'Datum', key: 'created_at' },
]

// Methods
async function loadEntityData() {
  loading.value = true
  try {
    // Load entity type first
    await store.fetchEntityTypeBySlug(typeSlug.value)

    // Load entity
    await store.fetchEntityBySlug(typeSlug.value, entitySlug.value)

    if (!entity.value) {
      showError('Entity nicht gefunden')
      router.push(`/entities/${typeSlug.value}`)
      return
    }

    // Load facet types if not loaded
    if (store.facetTypes.length === 0) {
      await store.fetchFacetTypes()
    }

    // Load facets summary
    facetsSummary.value = await store.fetchEntityFacetsSummary(entity.value.id)

    // Expand first facet group by default
    if (facetsSummary.value?.facets_by_type?.length) {
      expandedFacets.value = [facetsSummary.value.facets_by_type[0].facet_type_slug]
    }

    // Load relations
    await loadRelations()

    // Populate edit form
    editForm.value = {
      name: entity.value.name,
      external_id: entity.value.external_id || '',
    }
  } catch (e) {
    console.error('Failed to load entity', e)
    showError('Fehler beim Laden der Entity')
  } finally {
    loading.value = false
  }
}

async function loadRelations() {
  if (!entity.value) return
  try {
    const result = await store.fetchEntityRelations({
      entity_id: entity.value.id,
    })
    relations.value = result.items || []
  } catch (e) {
    console.error('Failed to load relations', e)
  }
}

async function loadDataSources() {
  if (!entity.value) return
  loadingDataSources.value = true
  try {
    // Sources linked via entity_id
    const response = await adminApi.getSources({ entity_id: entity.value.id, per_page: 10000 })
    dataSources.value = response.data.items || []

    // Also check for sources linked via location_name for backward compatibility
    if (dataSources.value.length === 0) {
      const byNameResponse = await adminApi.getSources({ location_name: entity.value.name, per_page: 10000 })
      dataSources.value = byNameResponse.data.items || []
    }
  } catch (e) {
    console.error('Failed to load data sources', e)
  } finally {
    loadingDataSources.value = false
  }
}

async function loadDocuments() {
  if (!entity.value) return
  loadingDocuments.value = true
  try {
    // This would need an endpoint to get documents by entity
    // For now we can use the location_name based endpoint
    const response = await adminApi.getSources({ location_name: entity.value.name })
    // This is a placeholder - would need proper document listing by entity
    documents.value = []
  } catch (e) {
    console.error('Failed to load documents', e)
  } finally {
    loadingDocuments.value = false
  }
}

function toggleFacetExpand(slug: string) {
  const idx = expandedFacets.value.indexOf(slug)
  if (idx >= 0) {
    expandedFacets.value.splice(idx, 1)
  } else {
    expandedFacets.value.push(slug)
  }
}

async function openFacetDetails(facetGroup: any) {
  selectedFacetGroup.value = facetGroup
  facetDetailsDialog.value = true

  try {
    const response = await facetApi.getFacetValues({
      entity_id: entity.value?.id,
      facet_type_slug: facetGroup.facet_type_slug,
      per_page: 10000,
    })
    facetDetails.value = response.data.items || []
  } catch (e) {
    console.error('Failed to load facet details', e)
    facetDetails.value = []
  }
}

async function saveFacetValue() {
  if (!newFacet.value.facet_type_id || !newFacet.value.text_representation) return
  if (!entity.value) return

  savingFacet.value = true
  try {
    await facetApi.createFacetValue({
      entity_id: entity.value.id,
      facet_type_id: newFacet.value.facet_type_id,
      value: { text: newFacet.value.text_representation },
      text_representation: newFacet.value.text_representation,
      source_url: newFacet.value.source_url || null,
      confidence_score: newFacet.value.confidence_score,
    })

    showSuccess('Facet-Wert hinzugefuegt')
    addFacetDialog.value = false

    // Reset form
    newFacet.value = {
      facet_type_id: '',
      text_representation: '',
      source_url: '',
      confidence_score: 0.8,
    }

    // Reload facets summary
    facetsSummary.value = await store.fetchEntityFacetsSummary(entity.value.id)
  } catch (e: any) {
    showError(e.response?.data?.detail || 'Fehler beim Speichern')
  } finally {
    savingFacet.value = false
  }
}

async function verifyFacet(facetValueId: string) {
  try {
    await store.verifyFacetValue(facetValueId, true)
    showSuccess('Facet verifiziert')
    // Reload details
    if (selectedFacetGroup.value) {
      await openFacetDetails(selectedFacetGroup.value)
    }
    // Reload summary
    if (entity.value) {
      facetsSummary.value = await store.fetchEntityFacetsSummary(entity.value.id)
    }
  } catch (e) {
    showError('Fehler beim Verifizieren')
  }
}

async function saveEntity() {
  if (!entity.value) return

  savingEntity.value = true
  try {
    await store.updateEntity(entity.value.id, {
      name: editForm.value.name,
      external_id: editForm.value.external_id || null,
    })
    showSuccess('Entity aktualisiert')
    editDialog.value = false
  } catch (e: any) {
    showError(e.response?.data?.detail || 'Fehler beim Speichern')
  } finally {
    savingEntity.value = false
  }
}

async function startCrawl(source: any) {
  startingCrawl.value = source.id
  try {
    await adminApi.startCrawl({ source_ids: [source.id] })
    showSuccess(`Crawl fuer "${source.name}" gestartet`)
    source.hasRunningJob = true
  } catch (e: any) {
    showError(e.response?.data?.detail || 'Fehler beim Starten')
  } finally {
    startingCrawl.value = null
  }
}

function navigateToRelatedEntity(rel: any) {
  const targetId = rel.source_entity_id === entity.value?.id
    ? rel.target_entity_id
    : rel.source_entity_id
  const targetSlug = rel.source_entity_id === entity.value?.id
    ? rel.target_entity_type_slug
    : rel.source_entity_type_slug
  const targetEntitySlug = rel.source_entity_id === entity.value?.id
    ? rel.target_entity_slug || targetId
    : rel.source_entity_slug || targetId

  router.push({
    name: 'entity-detail',
    params: { typeSlug: targetSlug, entitySlug: targetEntitySlug },
  })
}

function goToSources() {
  router.push({ path: '/sources', query: { location_name: entity.value?.name } })
}

// Helpers
function formatAttributeKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

function formatAttributeValue(value: any): string {
  if (typeof value === 'number') {
    return value.toLocaleString('de-DE')
  }
  return String(value)
}

function formatFacetValue(facet: any): string {
  if (facet.text_representation) return facet.text_representation
  if (typeof facet.value === 'string') return facet.value
  if (facet.value?.text) return facet.value.text
  return JSON.stringify(facet.value)
}

function formatDate(dateStr: string): string {
  return format(new Date(dateStr), 'dd.MM.yyyy HH:mm', { locale: de })
}

function getConfidenceColor(score: number | null): string {
  if (!score) return 'grey'
  if (score >= 0.8) return 'success'
  if (score >= 0.5) return 'warning'
  return 'error'
}

function getSourceStatusColor(status: string): string {
  const colors: Record<string, string> = {
    ACTIVE: 'success',
    INACTIVE: 'grey',
    ERROR: 'error',
    PENDING: 'warning',
  }
  return colors[status] || 'grey'
}

function getSourceStatusIcon(status: string): string {
  const icons: Record<string, string> = {
    ACTIVE: 'mdi-check-circle',
    INACTIVE: 'mdi-pause-circle',
    ERROR: 'mdi-alert-circle',
    PENDING: 'mdi-clock',
  }
  return icons[status] || 'mdi-help-circle'
}

// Watch for tab changes to load data lazily
watch(activeTab, (tab) => {
  if (tab === 'sources' && dataSources.value.length === 0) {
    loadDataSources()
  }
  if (tab === 'documents' && documents.value.length === 0) {
    loadDocuments()
  }
})

// Watch for route changes
watch([typeSlug, entitySlug], () => {
  loadEntityData()
})

// Init
onMounted(() => {
  loadEntityData()
})
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}
</style>
