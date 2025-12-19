<template>
  <div>
    <!-- Loading Overlay -->
    <v-overlay :model-value="loading" class="align-center justify-center" persistent scrim="rgba(0,0,0,0.7)">
      <v-card class="pa-8 text-center" min-width="320" elevation="24">
        <v-progress-circular indeterminate size="80" width="6" color="primary" class="mb-4"></v-progress-circular>
        <div class="text-h6 mb-2">Daten werden geladen</div>
        <div class="text-body-2 text-grey">
          {{ totalEntities > 0 ? `${totalEntities.toLocaleString()} ${currentEntityType?.name_plural || 'Eintraege'}` : 'Bitte warten...' }}
        </div>
      </v-card>
    </v-overlay>

    <!-- Header -->
    <div class="d-flex justify-space-between align-center mb-6">
      <div class="d-flex align-center">
        <v-icon v-if="currentEntityType" :icon="currentEntityType.icon" :color="currentEntityType.color" size="32" class="mr-3"></v-icon>
        <div>
          <h1 class="text-h4">{{ currentEntityType?.name_plural || 'Entities' }}</h1>
          <div v-if="currentEntityType?.description" class="text-body-2 text-grey">
            {{ currentEntityType.description }}
          </div>
        </div>
      </div>
      <div class="d-flex ga-2">
        <v-btn v-if="store.selectedTemplate" variant="outlined" @click="templateDialog = true">
          <v-icon start>mdi-view-dashboard</v-icon>
          {{ store.selectedTemplate.name }}
        </v-btn>
        <v-btn color="primary" @click="createDialog = true">
          <v-icon start>mdi-plus</v-icon>
          Neu anlegen
        </v-btn>
      </div>
    </div>

    <!-- Entity Type Tabs (if no specific type selected) -->
    <v-tabs v-if="!typeSlug" v-model="selectedTypeTab" color="primary" class="mb-4">
      <v-tab
        v-for="entityType in store.primaryEntityTypes"
        :key="entityType.slug"
        :value="entityType.slug"
      >
        <v-icon start :icon="entityType.icon"></v-icon>
        {{ entityType.name_plural }}
        <v-chip size="x-small" class="ml-2">{{ entityType.entity_count }}</v-chip>
      </v-tab>
    </v-tabs>

    <!-- Stats Cards -->
    <v-row class="mb-4">
      <v-col cols="12" md="3">
        <v-card class="stats-card">
          <v-card-text class="text-center">
            <div class="text-h4">{{ totalEntities }}</div>
            <div class="text-subtitle-1">{{ currentEntityType?.name_plural || 'Entities' }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card class="stats-card stats-card--primary">
          <v-card-text class="text-center">
            <div class="text-h4">{{ stats.total_facet_values || 0 }}</div>
            <div class="text-subtitle-1">Facet-Werte</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card class="stats-card stats-card--success">
          <v-card-text class="text-center">
            <div class="text-h4">{{ stats.verified_count || 0 }}</div>
            <div class="text-subtitle-1">Verifiziert</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card class="stats-card stats-card--tertiary">
          <v-card-text class="text-center">
            <div class="text-h4">{{ stats.relation_count || 0 }}</div>
            <div class="text-subtitle-1">Verknuepfungen</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row>
          <v-col cols="12" md="3">
            <v-text-field
              v-model="searchQuery"
              label="Suchen"
              prepend-inner-icon="mdi-magnify"
              clearable
              hide-details
              @update:model-value="debouncedLoadEntities"
            ></v-text-field>
          </v-col>
          <v-col cols="12" md="2">
            <v-select
              v-model="filters.category_id"
              :items="categories"
              item-title="name"
              item-value="id"
              label="Kategorie"
              clearable
              hide-details
              @update:model-value="loadEntities"
            ></v-select>
          </v-col>
          <v-col cols="12" md="2" v-if="currentEntityType?.supports_hierarchy">
            <v-autocomplete
              v-model="filters.parent_id"
              :items="parentOptions"
              :loading="loadingParents"
              item-title="name"
              item-value="id"
              label="Uebergeordnet"
              clearable
              hide-details
              @update:search="searchParents"
              @update:model-value="loadEntities"
            ></v-autocomplete>
          </v-col>
          <v-col cols="12" md="2">
            <v-select
              v-model="filters.has_facets"
              :items="facetFilterOptions"
              item-title="label"
              item-value="value"
              label="Mit Facets"
              hide-details
              @update:model-value="loadEntities"
            ></v-select>
          </v-col>
          <v-col cols="12" md="3">
            <v-select
              v-model="filters.facet_type_slugs"
              :items="store.activeFacetTypes"
              item-title="name"
              item-value="slug"
              label="Facet-Typen"
              multiple
              chips
              closable-chips
              hide-details
              @update:model-value="loadEntities"
            ></v-select>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Entities Table -->
    <v-card>
      <v-card-title class="d-flex align-center">
        {{ currentEntityType?.name_plural || 'Entities' }}-Uebersicht
        <v-spacer></v-spacer>
        <v-btn-toggle v-model="viewMode" density="compact" mandatory>
          <v-btn value="table" icon="mdi-table"></v-btn>
          <v-btn value="cards" icon="mdi-view-grid"></v-btn>
          <v-btn v-if="hasGeoData" value="map" icon="mdi-map"></v-btn>
        </v-btn-toggle>
        <v-btn color="primary" variant="text" class="ml-2" @click="loadEntities">
          <v-icon start>mdi-refresh</v-icon>
          Aktualisieren
        </v-btn>
      </v-card-title>

      <!-- Table View -->
      <v-data-table-server
        v-if="viewMode === 'table'"
        :headers="tableHeaders"
        :items="store.entities"
        :items-length="totalEntities"
        :loading="store.entitiesLoading"
        :items-per-page="itemsPerPage"
        :page="currentPage"
        @update:options="onTableOptionsUpdate"
        @click:row="(event, { item }) => openEntityDetail(item)"
        class="cursor-pointer"
      >
        <template v-slot:item.name="{ item }">
          <div class="d-flex align-center">
            <v-icon class="mr-2" :color="currentEntityType?.color || 'primary'" :icon="currentEntityType?.icon || 'mdi-folder'"></v-icon>
            <div>
              <strong>{{ item.name }}</strong>
              <div v-if="item.external_id" class="text-caption text-grey">
                {{ item.external_id }}
              </div>
            </div>
          </div>
        </template>

        <template v-slot:item.hierarchy_path="{ item }">
          <span class="text-grey-darken-1 text-caption">{{ item.hierarchy_path || '-' }}</span>
        </template>

        <template v-slot:item.facet_count="{ item }">
          <v-chip size="small" color="primary" variant="tonal">
            <v-icon start size="small">mdi-tag-multiple</v-icon>
            {{ item.facet_count || 0 }}
          </v-chip>
        </template>

        <template v-slot:item.relation_count="{ item }">
          <v-chip size="small" color="info" variant="tonal">
            <v-icon start size="small">mdi-link</v-icon>
            {{ item.relation_count || 0 }}
          </v-chip>
        </template>

        <template v-slot:item.facet_summary="{ item }">
          <div class="d-flex ga-1 flex-wrap">
            <v-tooltip
              v-for="facet in getTopFacetCounts(item)"
              :key="facet.slug"
              location="top"
            >
              <template v-slot:activator="{ props }">
                <v-chip
                  v-bind="props"
                  size="x-small"
                  :color="facet.color"
                  variant="tonal"
                >
                  <v-icon start size="x-small" :icon="facet.icon"></v-icon>
                  {{ facet.count }}
                </v-chip>
              </template>
              <span>{{ facet.name }}: {{ facet.count }}</span>
            </v-tooltip>
          </div>
        </template>

        <template v-slot:item.actions="{ item }">
          <div class="table-actions">
            <v-btn icon="mdi-eye" size="small" variant="text" title="Details" @click.stop="openEntityDetail(item)"></v-btn>
            <v-btn icon="mdi-pencil" size="small" variant="text" title="Bearbeiten" @click.stop="openEditDialog(item)"></v-btn>
            <v-btn icon="mdi-delete" size="small" variant="text" color="error" title="Loeschen" @click.stop="confirmDelete(item)"></v-btn>
          </div>
        </template>
      </v-data-table-server>

      <!-- Cards View -->
      <v-container v-else-if="viewMode === 'cards'" fluid>
        <v-row>
          <v-col
            v-for="entity in store.entities"
            :key="entity.id"
            cols="12"
            sm="6"
            md="4"
            lg="3"
          >
            <v-card
              :elevation="2"
              class="entity-card cursor-pointer"
              @click="openEntityDetail(entity)"
            >
              <v-card-title class="d-flex align-center">
                <v-icon :color="currentEntityType?.color" :icon="currentEntityType?.icon" class="mr-2"></v-icon>
                {{ entity.name }}
              </v-card-title>
              <v-card-subtitle v-if="entity.hierarchy_path">
                {{ entity.hierarchy_path }}
              </v-card-subtitle>
              <v-card-text>
                <div class="d-flex ga-2 mb-2">
                  <v-chip size="small" color="primary" variant="tonal">
                    <v-icon start size="small">mdi-tag-multiple</v-icon>
                    {{ entity.facet_count || 0 }} Facets
                  </v-chip>
                  <v-chip size="small" color="info" variant="tonal">
                    <v-icon start size="small">mdi-link</v-icon>
                    {{ entity.relation_count || 0 }}
                  </v-chip>
                </div>
              </v-card-text>
              <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn size="small" color="primary" variant="text" @click.stop="openEntityDetail(entity)">
                  Details
                </v-btn>
              </v-card-actions>
            </v-card>
          </v-col>
        </v-row>
        <v-pagination
          v-if="totalPages > 1"
          v-model="currentPage"
          :length="totalPages"
          class="mt-4"
          @update:model-value="loadEntities"
        ></v-pagination>
      </v-container>
    </v-card>

    <!-- Create/Edit Dialog -->
    <v-dialog v-model="createDialog" max-width="600">
      <v-card>
        <v-card-title>
          {{ editingEntity ? `${currentEntityType?.name || 'Entity'} bearbeiten` : `${currentEntityType?.name || 'Entity'} anlegen` }}
        </v-card-title>
        <v-card-text>
          <v-form ref="formRef" @submit.prevent="saveEntity">
            <v-text-field
              v-model="entityForm.name"
              label="Name *"
              :rules="[v => !!v || 'Name ist erforderlich']"
              required
            ></v-text-field>

            <v-text-field
              v-model="entityForm.external_id"
              label="Externe ID"
              hint="z.B. AGS, Code, etc."
            ></v-text-field>

            <v-select
              v-if="currentEntityType?.supports_hierarchy"
              v-model="entityForm.parent_id"
              :items="parentOptions"
              item-title="name"
              item-value="id"
              label="Uebergeordnetes Element"
              clearable
            ></v-select>

            <!-- Dynamic core_attributes based on attribute_schema -->
            <template v-if="currentEntityType?.attribute_schema?.properties">
              <v-divider class="my-4"></v-divider>
              <div class="text-subtitle-2 mb-2">Eigenschaften</div>
              <template v-for="(prop, key) in currentEntityType.attribute_schema.properties" :key="key">
                <v-text-field
                  v-if="prop.type === 'string'"
                  v-model="entityForm.core_attributes[key]"
                  :label="prop.title || key"
                  :hint="prop.description"
                ></v-text-field>
                <v-text-field
                  v-else-if="prop.type === 'integer' || prop.type === 'number'"
                  v-model.number="entityForm.core_attributes[key]"
                  :label="prop.title || key"
                  :hint="prop.description"
                  type="number"
                ></v-text-field>
                <v-checkbox
                  v-else-if="prop.type === 'boolean'"
                  v-model="entityForm.core_attributes[key]"
                  :label="prop.title || key"
                  :hint="prop.description"
                ></v-checkbox>
              </template>
            </template>

            <!-- Owner selection -->
            <v-divider class="my-4"></v-divider>
            <div class="text-subtitle-2 mb-2">Zustaendigkeit (optional)</div>
            <v-autocomplete
              v-model="entityForm.owner_id"
              :items="userOptions"
              :loading="loadingUsers"
              item-title="display"
              item-value="id"
              label="Verantwortlicher Benutzer"
              clearable
              hint="Benutzer, der fuer diesen Eintrag zustaendig ist"
              persistent-hint
            >
              <template v-slot:item="{ props, item }">
                <v-list-item v-bind="props">
                  <template v-slot:subtitle>{{ item.raw.email }}</template>
                </v-list-item>
              </template>
            </v-autocomplete>

            <!-- Geo coordinates -->
            <v-divider class="my-4"></v-divider>
            <div class="text-subtitle-2 mb-2">Geo-Koordinaten (optional)</div>
            <v-row>
              <v-col cols="6">
                <v-text-field
                  v-model.number="entityForm.latitude"
                  label="Breitengrad"
                  type="number"
                  step="0.000001"
                ></v-text-field>
              </v-col>
              <v-col cols="6">
                <v-text-field
                  v-model.number="entityForm.longitude"
                  label="Laengengrad"
                  type="number"
                  step="0.000001"
                ></v-text-field>
              </v-col>
            </v-row>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="closeDialog">Abbrechen</v-btn>
          <v-btn
            color="primary"
            :loading="saving"
            @click="saveEntity"
          >
            {{ editingEntity ? 'Speichern' : 'Anlegen' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Template Selection Dialog -->
    <v-dialog v-model="templateDialog" max-width="500">
      <v-card>
        <v-card-title>Analyse-Template waehlen</v-card-title>
        <v-card-text>
          <v-list>
            <v-list-item
              v-for="template in store.analysisTemplates"
              :key="template.id"
              :active="store.selectedTemplate?.id === template.id"
              @click="selectTemplate(template)"
            >
              <v-list-item-title>{{ template.name }}</v-list-item-title>
              <v-list-item-subtitle v-if="template.description">
                {{ template.description }}
              </v-list-item-subtitle>
              <template v-slot:append>
                <v-chip v-if="template.is_default" size="x-small" color="primary">
                  Standard
                </v-chip>
              </template>
            </v-list-item>
          </v-list>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="templateDialog = false">Schliessen</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" max-width="450">
      <v-card>
        <v-card-title class="text-h6">
          <v-icon color="error" class="mr-2">mdi-alert</v-icon>
          Entity loeschen?
        </v-card-title>
        <v-card-text>
          <p>Moechtest du <strong>{{ entityToDelete?.name }}</strong> wirklich loeschen?</p>
          <v-alert v-if="entityToDelete?.facet_count > 0 || entityToDelete?.relation_count > 0" type="warning" variant="tonal" density="compact" class="mt-3">
            <strong>Achtung:</strong> Diese Entity hat
            <span v-if="entityToDelete?.facet_count > 0">{{ entityToDelete.facet_count }} Facet-Werte</span>
            <span v-if="entityToDelete?.facet_count > 0 && entityToDelete?.relation_count > 0"> und </span>
            <span v-if="entityToDelete?.relation_count > 0">{{ entityToDelete.relation_count }} Verknuepfungen</span>.
            Diese werden ebenfalls geloescht.
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="deleteDialog = false">Abbrechen</v-btn>
          <v-btn color="error" :loading="deleting" @click="deleteEntity">
            <v-icon start>mdi-delete</v-icon>
            Loeschen
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
import { adminApi, userApi } from '@/services/api'
import { useSnackbar } from '@/composables/useSnackbar'

const { showSuccess, showError } = useSnackbar()
const route = useRoute()
const router = useRouter()
const store = useEntityStore()

// Props and route params
const typeSlug = computed(() => route.params.typeSlug as string | undefined)
const selectedTypeTab = ref<string>('')

// State
const loading = ref(false)
const searchQuery = ref('')
const currentPage = ref(1)
const itemsPerPage = ref(25)
const viewMode = ref<'table' | 'cards' | 'map'>('table')
const categories = ref<any[]>([])
const parentOptions = ref<any[]>([])
const loadingParents = ref(false)
const userOptions = ref<any[]>([])
const loadingUsers = ref(false)

// Dialogs
const createDialog = ref(false)
const templateDialog = ref(false)
const deleteDialog = ref(false)
const editingEntity = ref<any>(null)
const entityToDelete = ref<any>(null)
const saving = ref(false)
const deleting = ref(false)
const formRef = ref<any>(null)

// Form
const entityForm = ref({
  name: '',
  external_id: '',
  parent_id: null as string | null,
  core_attributes: {} as Record<string, any>,
  latitude: null as number | null,
  longitude: null as number | null,
  owner_id: null as string | null,
})

// Filters
const filters = ref({
  category_id: null as string | null,
  parent_id: null as string | null,
  has_facets: null as boolean | null,
  facet_type_slugs: [] as string[],
})

const facetFilterOptions = [
  { label: 'Alle', value: null },
  { label: 'Mit Facets', value: true },
  { label: 'Ohne Facets', value: false },
]

// Stats
const stats = ref({
  total_facet_values: 0,
  verified_count: 0,
  relation_count: 0,
})

// Computed
const currentEntityType = computed(() => {
  const slug = typeSlug.value || selectedTypeTab.value
  return store.entityTypes.find(et => et.slug === slug) || store.primaryEntityTypes[0]
})

const totalEntities = computed(() => store.entitiesTotal)
const totalPages = computed(() => Math.ceil(totalEntities.value / itemsPerPage.value))

const hasGeoData = computed(() =>
  store.entities.some(e => e.latitude !== null && e.longitude !== null)
)

const tableHeaders = computed(() => {
  const headers = [
    { title: 'Name', key: 'name' },
  ]

  if (currentEntityType.value?.supports_hierarchy) {
    headers.push({ title: 'Pfad', key: 'hierarchy_path' })
  }

  headers.push(
    { title: 'Facets', key: 'facet_count', align: 'center' as const },
    { title: 'Verknuepfungen', key: 'relation_count', align: 'center' as const },
    { title: 'Facet-Uebersicht', key: 'facet_summary', sortable: false },
    { title: '', key: 'actions', sortable: false, width: '80px' },
  )

  return headers
})

// Debounce helper
let searchTimeout: ReturnType<typeof setTimeout> | null = null
const debouncedLoadEntities = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => loadEntities(), 300)
}

// Methods
async function loadEntities(page = currentPage.value) {
  if (!currentEntityType.value) return

  loading.value = true
  try {
    const params: any = {
      entity_type_slug: currentEntityType.value.slug,
      page,
      per_page: itemsPerPage.value,
    }

    if (searchQuery.value) params.search = searchQuery.value
    if (filters.value.category_id) params.category_id = filters.value.category_id
    if (filters.value.parent_id) params.parent_id = filters.value.parent_id
    if (filters.value.has_facets !== null) params.has_facets = filters.value.has_facets
    if (filters.value.facet_type_slugs.length > 0) {
      params.facet_type_slugs = filters.value.facet_type_slugs.join(',')
    }

    await store.fetchEntities(params)
    currentPage.value = page

    // Load stats
    await loadStats()
  } catch (e) {
    console.error('Failed to load entities', e)
    showError('Fehler beim Laden der Daten')
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    const result = await store.fetchAnalysisStats({
      entity_type_slug: currentEntityType.value?.slug,
    })
    stats.value = {
      total_facet_values: result.total_facet_values || 0,
      verified_count: result.verified_count || 0,
      relation_count: result.total_relations || 0,
    }
  } catch (e) {
    console.error('Failed to load stats', e)
  }
}

async function loadCategories() {
  try {
    const response = await adminApi.getCategories({ per_page: 100 })
    categories.value = response.data.items || []
  } catch (e) {
    console.error('Failed to load categories', e)
  }
}

async function loadUsers() {
  loadingUsers.value = true
  try {
    const response = await userApi.getUsers({ per_page: 100, is_active: true })
    userOptions.value = (response.data.items || []).map((u: any) => ({
      id: u.id,
      full_name: u.full_name,
      email: u.email,
      display: `${u.full_name} (${u.email})`,
    }))
  } catch (e) {
    console.error('Failed to load users', e)
  } finally {
    loadingUsers.value = false
  }
}

async function loadParentOptions() {
  if (!currentEntityType.value?.supports_hierarchy) {
    parentOptions.value = []
    return
  }

  try {
    // Load initial options (empty search)
    await searchParents('')
  } catch (e) {
    console.error('Failed to load parent options', e)
  }
}

let parentSearchTimeout: ReturnType<typeof setTimeout> | null = null
async function searchParents(query: string) {
  if (!currentEntityType.value?.supports_hierarchy) return

  if (parentSearchTimeout) clearTimeout(parentSearchTimeout)

  parentSearchTimeout = setTimeout(async () => {
    loadingParents.value = true
    try {
      const response = await store.fetchEntities({
        entity_type_slug: currentEntityType.value!.slug,
        search: query || undefined,
        per_page: 50,
      })
      parentOptions.value = response.items || []
    } catch (e) {
      console.error('Failed to search parents', e)
    } finally {
      loadingParents.value = false
    }
  }, 300)
}

function onTableOptionsUpdate(options: { page: number; itemsPerPage: number }) {
  if (options.itemsPerPage !== itemsPerPage.value) {
    itemsPerPage.value = options.itemsPerPage
  }
  loadEntities(options.page)
}

function openEntityDetail(entity: any) {
  router.push({
    name: 'entity-detail',
    params: {
      typeSlug: currentEntityType.value?.slug,
      entitySlug: entity.slug,
    },
  })
}

function openEditDialog(entity: any) {
  editingEntity.value = entity
  entityForm.value = {
    name: entity.name,
    external_id: entity.external_id || '',
    parent_id: entity.parent_id,
    core_attributes: { ...entity.core_attributes },
    latitude: entity.latitude,
    longitude: entity.longitude,
    owner_id: entity.owner_id || null,
  }
  createDialog.value = true
}

function closeDialog() {
  createDialog.value = false
  editingEntity.value = null
  entityForm.value = {
    name: '',
    external_id: '',
    parent_id: null,
    core_attributes: {},
    latitude: null,
    longitude: null,
    owner_id: null,
  }
}

async function saveEntity() {
  if (!formRef.value?.validate()) return
  if (!currentEntityType.value) return

  saving.value = true
  try {
    const data = {
      entity_type_id: currentEntityType.value.id,
      name: entityForm.value.name,
      external_id: entityForm.value.external_id || null,
      parent_id: entityForm.value.parent_id,
      core_attributes: entityForm.value.core_attributes,
      latitude: entityForm.value.latitude,
      longitude: entityForm.value.longitude,
      owner_id: entityForm.value.owner_id,
    }

    if (editingEntity.value) {
      await store.updateEntity(editingEntity.value.id, data)
      showSuccess('Entity erfolgreich aktualisiert')
    } else {
      await store.createEntity(data)
      showSuccess('Entity erfolgreich angelegt')
    }

    closeDialog()
    await loadEntities()
  } catch (e: any) {
    showError(e.response?.data?.detail || 'Fehler beim Speichern')
  } finally {
    saving.value = false
  }
}

function selectTemplate(template: any) {
  store.selectedTemplate = template
  templateDialog.value = false
  loadEntities()
}

function confirmDelete(entity: any) {
  entityToDelete.value = entity
  deleteDialog.value = true
}

async function deleteEntity() {
  if (!entityToDelete.value) return

  deleting.value = true
  try {
    await store.deleteEntity(entityToDelete.value.id)
    showSuccess(`"${entityToDelete.value.name}" wurde geloescht`)
    deleteDialog.value = false
    entityToDelete.value = null
    await loadEntities()
  } catch (e: any) {
    const detail = e.response?.data?.detail || 'Fehler beim Loeschen'
    showError(detail)
  } finally {
    deleting.value = false
  }
}

function getTopFacetCounts(entity: any): Array<{ slug: string; name: string; icon: string; color: string; count: number }> {
  // This would ideally come from the API with aggregated facet counts
  // For now, we return an empty array - would be populated from facet_summary in real data
  return []
}

// Watchers
watch(selectedTypeTab, () => {
  if (selectedTypeTab.value) {
    loadEntities(1)
    loadParentOptions()
  }
})

watch(() => route.params.typeSlug, () => {
  if (typeSlug.value) {
    loadEntities(1)
    loadParentOptions()
  }
})

// Init
onMounted(async () => {
  // Load metadata
  await Promise.all([
    store.fetchEntityTypes(),
    store.fetchFacetTypes(),
    store.fetchAnalysisTemplates({ is_active: true }),
    loadCategories(),
    loadUsers(),
  ])

  // Set initial type
  if (typeSlug.value) {
    await store.fetchEntityTypeBySlug(typeSlug.value)
  } else if (store.primaryEntityTypes.length > 0) {
    selectedTypeTab.value = store.primaryEntityTypes[0].slug
  }

  // Load entities
  await loadEntities()
  await loadParentOptions()
})
</script>

<style scoped>
.cursor-pointer :deep(tbody tr) {
  cursor: pointer;
}
.cursor-pointer :deep(tbody tr:hover) {
  background-color: rgba(var(--v-theme-primary), 0.1);
}

.entity-card {
  transition: transform 0.2s, box-shadow 0.2s;
}
.entity-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.stats-card {
  border-left: 4px solid rgb(var(--v-theme-surface-variant));
}
.stats-card--primary {
  border-left-color: rgb(var(--v-theme-primary));
}
.stats-card--success {
  border-left-color: rgb(var(--v-theme-success));
}
.stats-card--tertiary {
  border-left-color: rgb(var(--v-theme-info));
}
</style>
