<template>
  <div>
    <!-- Loading Overlay -->
    <v-overlay :model-value="loading" class="align-center justify-center" persistent scrim="rgba(0,0,0,0.7)">
      <v-card class="pa-8 text-center" min-width="320" elevation="24">
        <v-progress-circular indeterminate size="80" width="6" color="primary" class="mb-4"></v-progress-circular>
        <div class="text-h6 mb-2">{{ t('entities.loadingData') }}</div>
        <div class="text-body-2 text-grey">
          {{ totalEntities > 0 ? `${totalEntities.toLocaleString()} ${currentEntityType?.name_plural || t('entities.entries')}` : t('common.pleaseWait') }}
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
          {{ t('entities.createNew') }}
        </v-btn>
      </div>
    </div>

    <!-- Entity Type Tabs (if no specific type selected) -->
    <v-tabs v-if="!typeSlug" v-model="selectedTypeTab" color="primary" class="mb-4" show-arrows>
      <v-tab
        v-for="entityType in store.activeEntityTypes"
        :key="entityType.slug"
        :value="entityType.slug"
      >
        <v-icon start :icon="entityType.icon" :color="entityType.color"></v-icon>
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
            <div class="text-subtitle-1">{{ t('entities.facetValues') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card class="stats-card stats-card--success">
          <v-card-text class="text-center">
            <div class="text-h4">{{ stats.verified_count || 0 }}</div>
            <div class="text-subtitle-1">{{ t('entities.verified') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card class="stats-card stats-card--tertiary">
          <v-card-text class="text-center">
            <div class="text-h4">{{ stats.relation_count || 0 }}</div>
            <div class="text-subtitle-1">{{ t('entities.relations') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row align="center">
          <v-col cols="12" md="3">
            <v-text-field
              v-model="searchQuery"
              :label="t('common.search')"
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
              :label="t('entities.category')"
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
              :label="t('entities.parent')"
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
              :label="t('entities.withFacets')"
              hide-details
              @update:model-value="loadEntities"
            ></v-select>
          </v-col>
          <v-col cols="auto">
            <v-btn
              variant="outlined"
              :color="hasExtendedFilters ? 'primary' : undefined"
              @click="openExtendedFilterDialog"
              height="56"
              min-width="56"
            >
              <v-icon>mdi-tune</v-icon>
              <v-badge
                v-if="activeExtendedFilterCount > 0"
                :content="activeExtendedFilterCount"
                color="primary"
                floating
              ></v-badge>
            </v-btn>
          </v-col>
          <v-col cols="auto" class="d-flex align-center">
            <v-btn
              v-if="hasAnyFilters"
              variant="text"
              color="error"
              size="small"
              @click="clearAllFilters"
              :title="t('entities.resetAllFilters')"
            >
              <v-icon>mdi-filter-off</v-icon>
            </v-btn>
          </v-col>
        </v-row>
        <!-- Active Extended Filters Display -->
        <v-row v-if="hasExtendedFilters" class="mt-2">
          <v-col cols="12">
            <div class="d-flex ga-2 flex-wrap">
              <v-chip
                v-for="(value, key) in allExtendedFilters"
                :key="key"
                closable
                size="small"
                color="primary"
                variant="tonal"
                @click:close="removeExtendedFilter(key)"
              >
                <v-icon start size="small">mdi-filter</v-icon>
                {{ getExtendedFilterTitle(key) }}: {{ value }}
              </v-chip>
            </div>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Extended Filter Dialog (Schema Attributes) -->
    <v-dialog v-model="extendedFilterDialog" max-width="520">
      <v-card>
        <v-toolbar color="primary" density="compact">
          <v-icon class="ml-4">mdi-tune</v-icon>
          <v-toolbar-title>{{ $t('entities.extendedFilters') }}</v-toolbar-title>
          <v-spacer></v-spacer>
          <v-btn icon @click="extendedFilterDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-toolbar>

        <v-card-text class="pa-0">
          <div v-if="schemaAttributes.length === 0" class="text-grey text-center py-8">
            <v-icon size="48" color="grey-lighten-1" class="mb-2">mdi-filter-off</v-icon>
            <div>{{ $t('entities.noFilterableAttributes') }}</div>
          </div>

          <template v-else>
            <!-- Location Section -->
            <div v-if="locationAttributes.length > 0" class="filter-section">
              <div class="filter-section-header">
                <v-icon size="small" class="mr-2">mdi-map-marker</v-icon>
                {{ $t('entities.location') }}
              </div>
              <div class="filter-section-content">
                <v-row dense>
                  <v-col v-if="hasAttribute('country')" cols="12" sm="4">
                    <v-select
                      v-model="tempExtendedFilters.country"
                      :items="locationOptions.countries"
                      :label="$t('entities.country')"
                      density="compact"
                      variant="outlined"
                      clearable
                      hide-details
                      @update:model-value="onCountryChange"
                      @focus="loadLocationOptions"
                    ></v-select>
                  </v-col>
                  <v-col v-if="hasAttribute('admin_level_1')" cols="12" sm="4">
                    <v-select
                      v-model="tempExtendedFilters.admin_level_1"
                      :items="locationOptions.admin_level_1"
                      :label="$t('entities.region')"
                      density="compact"
                      variant="outlined"
                      :disabled="!tempExtendedFilters.country"
                      clearable
                      hide-details
                      @update:model-value="onAdminLevel1Change"
                    ></v-select>
                  </v-col>
                  <v-col v-if="hasAttribute('admin_level_2')" cols="12" sm="4">
                    <v-select
                      v-model="tempExtendedFilters.admin_level_2"
                      :items="locationOptions.admin_level_2"
                      :label="$t('entities.district')"
                      density="compact"
                      variant="outlined"
                      :disabled="!tempExtendedFilters.admin_level_1"
                      clearable
                      hide-details
                    ></v-select>
                  </v-col>
                </v-row>
              </div>
            </div>

            <!-- Other Attributes Section -->
            <div v-if="nonLocationAttributes.length > 0" class="filter-section">
              <div class="filter-section-header">
                <v-icon size="small" class="mr-2">mdi-tag-multiple</v-icon>
                {{ $t('entities.attributes') }}
              </div>
              <div class="filter-section-content">
                <v-row dense>
                  <v-col
                    v-for="attr in nonLocationAttributes"
                    :key="attr.key"
                    cols="12"
                    sm="6"
                  >
                    <v-select
                      v-model="tempExtendedFilters[attr.key]"
                      :items="attributeValueOptions[attr.key] || []"
                      :label="attr.title"
                      density="compact"
                      variant="outlined"
                      clearable
                      hide-details
                      @focus="loadAttributeValues(attr.key)"
                    ></v-select>
                  </v-col>
                </v-row>
              </div>
            </div>
          </template>
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions class="pa-4">
          <v-chip
            v-if="activeExtendedFilterCount > 0"
            size="small"
            color="primary"
            variant="tonal"
          >
            {{ activeExtendedFilterCount }} {{ t('entities.filtersActive') }}
          </v-chip>
          <v-spacer></v-spacer>
          <v-btn
            v-if="hasExtendedFilters"
            variant="text"
            color="error"
            size="small"
            @click="clearExtendedFilters"
          >
            {{ t('common.reset') }}
          </v-btn>
          <v-btn variant="outlined" @click="extendedFilterDialog = false">
            {{ t('common.cancel') }}
          </v-btn>
          <v-btn color="primary" variant="flat" @click="applyExtendedFilters">
            {{ t('entities.apply') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Entities Table -->
    <v-card>
      <v-card-title class="d-flex align-center">
        {{ currentEntityType?.name_plural || t('entities.title') }} - {{ t('entities.overview') }}
        <v-spacer></v-spacer>
        <v-btn-toggle v-model="viewMode" density="compact" mandatory>
          <v-btn value="table" icon="mdi-table"></v-btn>
          <v-btn value="cards" icon="mdi-view-grid"></v-btn>
          <v-btn v-if="hasGeoData" value="map" icon="mdi-map"></v-btn>
        </v-btn-toggle>
        <v-btn color="primary" variant="text" class="ml-2" @click="loadEntities">
          <v-icon start>mdi-refresh</v-icon>
          {{ t('common.refresh') }}
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
            <v-btn icon="mdi-eye" size="small" variant="text" :title="t('common.details')" @click.stop="openEntityDetail(item)"></v-btn>
            <v-btn icon="mdi-pencil" size="small" variant="text" :title="t('common.edit')" @click.stop="openEditDialog(item)"></v-btn>
            <v-btn icon="mdi-delete" size="small" variant="text" color="error" :title="t('common.delete')" @click.stop="confirmDelete(item)"></v-btn>
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
                    {{ entity.facet_count || 0 }} {{ t('entities.properties') }}
                  </v-chip>
                  <v-chip size="small" color="info" variant="tonal">
                    <v-icon start size="small">mdi-link</v-icon>
                    {{ entity.relation_count || 0 }} {{ t('entities.relations') }}
                  </v-chip>
                </div>
              </v-card-text>
              <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn size="small" color="primary" variant="text" @click.stop="openEntityDetail(entity)">
                  {{ t('common.details') }}
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
          {{ editingEntity ? t('entities.editEntity', { type: currentEntityType?.name || 'Entity' }) : t('entities.createEntity', { type: currentEntityType?.name || 'Entity' }) }}
        </v-card-title>
        <v-card-text>
          <v-form ref="formRef" @submit.prevent="saveEntity">
            <v-text-field
              v-model="entityForm.name"
              :label="t('common.name') + ' *'"
              :rules="[v => !!v || t('entities.nameRequired')]"
              required
            ></v-text-field>

            <v-text-field
              v-model="entityForm.external_id"
              :label="t('entities.externalId')"
              :hint="t('entities.externalIdHint')"
            ></v-text-field>

            <v-select
              v-if="currentEntityType?.supports_hierarchy"
              v-model="entityForm.parent_id"
              :items="parentOptions"
              item-title="name"
              item-value="id"
              :label="$t('entities.parentElement')"
              clearable
            ></v-select>

            <!-- Dynamic core_attributes based on attribute_schema -->
            <template v-if="currentEntityType?.attribute_schema?.properties">
              <v-divider class="my-4"></v-divider>
              <div class="text-subtitle-2 mb-2">{{ $t('entities.attributes') }}</div>
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
            <div class="text-subtitle-2 mb-2">{{ $t('entities.responsibility') }}</div>
            <v-autocomplete
              v-model="entityForm.owner_id"
              :items="userOptions"
              :loading="loadingUsers"
              item-title="display"
              item-value="id"
              :label="$t('entities.responsibleUser')"
              clearable
              :hint="$t('entities.responsibleUserHint')"
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
            <div class="text-subtitle-2 mb-2">{{ $t('entities.geoCoordinates') }}</div>
            <v-row>
              <v-col cols="6">
                <v-text-field
                  v-model.number="entityForm.latitude"
                  :label="$t('entities.latitude')"
                  type="number"
                  step="0.000001"
                ></v-text-field>
              </v-col>
              <v-col cols="6">
                <v-text-field
                  v-model.number="entityForm.longitude"
                  :label="$t('entities.longitude')"
                  type="number"
                  step="0.000001"
                ></v-text-field>
              </v-col>
            </v-row>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="closeDialog">{{ t('common.cancel') }}</v-btn>
          <v-btn
            color="primary"
            :loading="saving"
            @click="saveEntity"
          >
            {{ editingEntity ? t('common.save') : t('common.create') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Template Selection Dialog -->
    <v-dialog v-model="templateDialog" max-width="500">
      <v-card>
        <v-card-title>{{ t('entities.selectAnalysisTemplate') }}</v-card-title>
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
                  {{ t('entities.default') }}
                </v-chip>
              </template>
            </v-list-item>
          </v-list>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="templateDialog = false">{{ t('common.close') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" max-width="450">
      <v-card>
        <v-card-title class="text-h6">
          <v-icon color="error" class="mr-2">mdi-alert</v-icon>
          {{ t('entities.deleteConfirmTitle') }}
        </v-card-title>
        <v-card-text>
          <p>{{ t('entities.deleteConfirmMessage', { name: entityToDelete?.name }) }}</p>
          <v-alert v-if="entityToDelete?.facet_count > 0 || entityToDelete?.relation_count > 0" type="warning" variant="tonal" density="compact" class="mt-3">
            <strong>{{ t('entities.warning') }}:</strong> {{ t('entities.entityHas') }}
            <span v-if="entityToDelete?.facet_count > 0">{{ entityToDelete.facet_count }} {{ t('entities.facetValues') }}</span>
            <span v-if="entityToDelete?.facet_count > 0 && entityToDelete?.relation_count > 0"> {{ t('entities.and') }} </span>
            <span v-if="entityToDelete?.relation_count > 0">{{ entityToDelete.relation_count }} {{ t('entities.relations') }}</span>.
            {{ t('entities.willBeDeleted') }}
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="deleteDialog = false">{{ t('common.cancel') }}</v-btn>
          <v-btn color="error" :loading="deleting" @click="deleteEntity">
            <v-icon start>mdi-delete</v-icon>
            {{ t('common.delete') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useEntityStore } from '@/stores/entity'
import { adminApi, userApi, entityApi } from '@/services/api'
import { useSnackbar } from '@/composables/useSnackbar'

const { t } = useI18n()

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
const extendedFilterDialog = ref(false)
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

// Extended Filters (Location + Schema Attributes combined)
const extendedFilters = ref<Record<string, string | null>>({})
const tempExtendedFilters = ref<Record<string, string | null>>({})

const locationOptions = ref({
  countries: [] as string[],
  admin_level_1: [] as string[],
  admin_level_2: [] as string[],
})

// Schema-based attributes
const schemaAttributes = ref<Array<{ key: string; title: string; description?: string; type: string }>>([])
const attributeValueOptions = ref<Record<string, string[]>>({})

// Location field keys (these map to Entity columns, not core_attributes)
const locationFieldKeys = ['country', 'admin_level_1', 'admin_level_2']

const facetFilterOptions = computed(() => [
  { label: t('entities.allFacets'), value: null },
  { label: t('entities.withFacets'), value: true },
  { label: t('entities.withoutFacets'), value: false },
])

// Stats
const stats = ref({
  total_facet_values: 0,
  verified_count: 0,
  relation_count: 0,
})

// Computed
const currentEntityType = computed(() => {
  const slug = typeSlug.value || selectedTypeTab.value
  return store.entityTypes.find(et => et.slug === slug) || store.activeEntityTypes[0]
})

const totalEntities = computed(() => store.entitiesTotal)
const totalPages = computed(() => Math.ceil(totalEntities.value / itemsPerPage.value))

const hasGeoData = computed(() =>
  store.entities.some(e => e.latitude !== null && e.longitude !== null)
)

// Extended filters: combines location + schema attributes
const hasExtendedFilters = computed(() =>
  Object.values(extendedFilters.value).some(v => v !== null && v !== undefined && v !== '')
)

const activeExtendedFilterCount = computed(() =>
  Object.values(extendedFilters.value).filter(v => v !== null && v !== undefined && v !== '').length
)

const allExtendedFilters = computed(() => {
  const result: Record<string, string> = {}
  for (const [key, value] of Object.entries(extendedFilters.value)) {
    if (value !== null && value !== undefined && value !== '') {
      result[key] = value
    }
  }
  return result
})

const hasAnyFilters = computed(() =>
  searchQuery.value ||
  filters.value.category_id !== null ||
  filters.value.parent_id !== null ||
  filters.value.has_facets !== null ||
  filters.value.facet_type_slugs.length > 0 ||
  hasExtendedFilters.value
)

// Split schema attributes into location and non-location
const locationAttributes = computed(() =>
  schemaAttributes.value.filter(attr => locationFieldKeys.includes(attr.key))
)

const nonLocationAttributes = computed(() =>
  schemaAttributes.value.filter(attr => !locationFieldKeys.includes(attr.key))
)

function hasAttribute(key: string): boolean {
  return schemaAttributes.value.some(attr => attr.key === key)
}

const tableHeaders = computed(() => {
  const headers = [
    { title: t('common.name'), key: 'name' },
  ]

  if (currentEntityType.value?.supports_hierarchy) {
    headers.push({ title: t('entities.path'), key: 'hierarchy_path' })
  }

  headers.push(
    { title: t('entities.properties'), key: 'facet_count', align: 'center' as const },
    { title: t('entities.relations'), key: 'relation_count', align: 'center' as const },
    { title: t('entities.summary'), key: 'facet_summary', sortable: false },
    { title: '', key: 'actions', sortable: false, width: '120px' },
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

    // Extended filters (location + schema attributes)
    if (hasExtendedFilters.value) {
      // Separate location filters from attribute filters
      const locationParams: Record<string, string> = {}
      const attrParams: Record<string, string> = {}

      for (const [key, value] of Object.entries(extendedFilters.value)) {
        if (value !== null && value !== undefined && value !== '') {
          if (locationFieldKeys.includes(key)) {
            locationParams[key] = value
          } else {
            attrParams[key] = value
          }
        }
      }

      // Apply location filters directly as query params
      if (locationParams.country) params.country = locationParams.country
      if (locationParams.admin_level_1) params.admin_level_1 = locationParams.admin_level_1
      if (locationParams.admin_level_2) params.admin_level_2 = locationParams.admin_level_2

      // Apply attribute filters as JSON
      if (Object.keys(attrParams).length > 0) {
        params.core_attr_filters = JSON.stringify(attrParams)
      }
    }

    await store.fetchEntities(params)
    currentPage.value = page

    // Load stats
    await loadStats()
  } catch (e) {
    console.error('Failed to load entities', e)
    showError(t('entities.loadError'))
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
      showSuccess(t('entities.entityUpdated'))
    } else {
      await store.createEntity(data)
      showSuccess(t('entities.entityCreated'))
    }

    closeDialog()
    await loadEntities()
  } catch (e: any) {
    showError(e.response?.data?.detail || t('entities.saveError'))
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
    showSuccess(t('entities.entityDeleted', { name: entityToDelete.value.name }))
    deleteDialog.value = false
    entityToDelete.value = null
    await loadEntities()
  } catch (e: any) {
    const detail = e.response?.data?.detail || t('entities.deleteError')
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

// Extended Filter Functions (Location + Schema Attributes)
async function loadLocationOptions() {
  try {
    const params: any = {}
    if (tempExtendedFilters.value.country) {
      params.country = tempExtendedFilters.value.country
    }
    if (tempExtendedFilters.value.admin_level_1) {
      params.admin_level_1 = tempExtendedFilters.value.admin_level_1
    }

    const response = await entityApi.getLocationFilterOptions(params)
    const data = response.data

    locationOptions.value.countries = data.countries || []
    locationOptions.value.admin_level_1 = data.admin_level_1 || []
    locationOptions.value.admin_level_2 = data.admin_level_2 || []
  } catch (e) {
    console.error('Failed to load location options', e)
  }
}

async function onCountryChange() {
  // Reset dependent filters when country changes
  tempExtendedFilters.value.admin_level_1 = null
  tempExtendedFilters.value.admin_level_2 = null
  await loadLocationOptions()
}

async function onAdminLevel1Change() {
  // Reset admin_level_2 when admin_level_1 changes
  tempExtendedFilters.value.admin_level_2 = null
  await loadLocationOptions()
}

function openExtendedFilterDialog() {
  // Copy current filters to temp
  tempExtendedFilters.value = { ...extendedFilters.value }
  extendedFilterDialog.value = true
  loadLocationOptions()
}

function applyExtendedFilters() {
  // Copy temp filters to actual filters, removing empty values
  const newFilters: Record<string, string | null> = {}
  for (const [key, value] of Object.entries(tempExtendedFilters.value)) {
    if (value !== null && value !== undefined && value !== '') {
      newFilters[key] = value
    }
  }
  extendedFilters.value = newFilters
  extendedFilterDialog.value = false
  loadEntities(1)
}

function clearExtendedFilters() {
  extendedFilters.value = {}
  tempExtendedFilters.value = {}
}

function removeExtendedFilter(key: string) {
  const newFilters = { ...extendedFilters.value }
  delete newFilters[key]
  extendedFilters.value = newFilters
  loadEntities()
}

function getExtendedFilterTitle(key: string): string {
  const attr = schemaAttributes.value.find(a => a.key === key)
  return attr?.title || key
}

function clearAllFilters() {
  searchQuery.value = ''
  filters.value.category_id = null
  filters.value.parent_id = null
  filters.value.has_facets = null
  filters.value.facet_type_slugs = []
  clearExtendedFilters()
  loadEntities(1)
}

// Schema Attribute Functions
async function loadSchemaAttributes() {
  if (!currentEntityType.value?.slug) {
    schemaAttributes.value = []
    return
  }

  try {
    const response = await entityApi.getAttributeFilterOptions({
      entity_type_slug: currentEntityType.value.slug,
    })
    schemaAttributes.value = response.data.attributes || []
  } catch (e) {
    console.error('Failed to load schema attributes', e)
    schemaAttributes.value = []
  }
}

async function loadAttributeValues(attributeKey: string) {
  if (!currentEntityType.value?.slug) return

  // Skip if already loaded
  if (attributeValueOptions.value[attributeKey]?.length > 0) return

  try {
    const response = await entityApi.getAttributeFilterOptions({
      entity_type_slug: currentEntityType.value.slug,
      attribute_key: attributeKey,
    })
    if (response.data.attribute_values?.[attributeKey]) {
      attributeValueOptions.value[attributeKey] = response.data.attribute_values[attributeKey]
    }
  } catch (e) {
    console.error(`Failed to load values for attribute ${attributeKey}`, e)
  }
}

// Watchers
watch(selectedTypeTab, () => {
  if (selectedTypeTab.value) {
    // Clear extended filters when switching entity type
    clearExtendedFilters()
    attributeValueOptions.value = {}
    loadEntities(1)
    loadParentOptions()
    loadSchemaAttributes()
  }
})

watch(() => route.params.typeSlug, () => {
  if (typeSlug.value) {
    // Clear extended filters when switching entity type
    clearExtendedFilters()
    attributeValueOptions.value = {}
    loadEntities(1)
    loadParentOptions()
    loadSchemaAttributes()
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
  } else if (store.activeEntityTypes.length > 0) {
    selectedTypeTab.value = store.activeEntityTypes[0].slug
  }

  // Load entities
  await loadEntities()
  await loadParentOptions()
  await loadSchemaAttributes()
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

/* Filter Dialog Sections */
.filter-section {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.filter-section:last-child {
  border-bottom: none;
}
.filter-section-header {
  display: flex;
  align-items: center;
  padding: 12px 16px 8px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: rgba(var(--v-theme-on-surface), 0.6);
  background: rgba(var(--v-theme-surface-variant), 0.3);
}
.filter-section-content {
  padding: 12px 16px 16px;
}
</style>
