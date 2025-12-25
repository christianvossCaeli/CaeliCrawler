<template>
  <div>
    <!-- Loading Overlay -->
    <v-overlay :model-value="loading" class="align-center justify-center" persistent>
      <v-card class="pa-8 text-center" min-width="320" elevation="24" role="status" aria-live="polite">
        <v-progress-circular
          indeterminate
          size="80"
          width="6"
          color="primary"
          class="mb-4"
          :aria-label="t('common.loading')"
        ></v-progress-circular>
        <div class="text-h6 mb-2">{{ t('entities.loadingData') }}</div>
        <div class="text-body-2 text-medium-emphasis">
          {{
            totalEntities > 0
              ? `${totalEntities.toLocaleString()} ${currentEntityType?.name_plural || t('entities.entries')}`
              : t('common.pleaseWait')
          }}
        </div>
      </v-card>
    </v-overlay>

    <!-- Header -->
    <PageHeader
      :title="currentEntityType?.name_plural || 'Entities'"
      :subtitle="currentEntityType?.description ?? undefined"
      :icon="currentEntityType?.icon || 'mdi-shape'"
      :avatar-color="currentEntityType?.color || 'primary'"
    >
      <template #actions>
        <v-btn v-if="store.selectedTemplate" variant="outlined" @click="templateDialog = true">
          <v-icon start aria-hidden="true">mdi-view-dashboard</v-icon>
          {{ store.selectedTemplate.name }}
        </v-btn>
        <v-btn
          variant="tonal"
          color="primary"
          :aria-label="t('entities.createNew')"
          @click="createDialog = true"
        >
          <v-icon start aria-hidden="true">mdi-plus</v-icon>
          {{ t('entities.createNew') }}
        </v-btn>
      </template>
    </PageHeader>

    <!-- Entity Type Tabs (if no specific type selected) -->
    <v-tabs
      v-if="!typeSlug"
      v-model="selectedTypeTab"
      color="primary"
      class="mb-4"
      show-arrows
      role="navigation"
      :aria-label="t('entities.entityTypeNavigation')"
    >
      <v-tab
        v-for="entityType in store.activeEntityTypes"
        :key="entityType.slug"
        :value="entityType.slug"
        :aria-label="`${entityType.name_plural} - ${entityType.entity_count} ${t('entities.items')}`"
      >
        <v-icon start :icon="entityType.icon" :color="entityType.color" aria-hidden="true"></v-icon>
        {{ entityType.name_plural }}
        <v-chip size="x-small" class="ml-2" role="status">{{ entityType.entity_count }}</v-chip>
      </v-tab>
    </v-tabs>

    <!-- Stats Cards -->
    <v-row class="mb-4" role="region" :aria-label="t('entities.statistics')">
      <v-col cols="6" sm="3">
        <v-card variant="outlined" role="status">
          <v-card-text class="text-center py-3">
            <div class="text-h5 text-primary">{{ totalEntities }}</div>
            <div class="text-caption">{{ currentEntityType?.name_plural || 'Entities' }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="3">
        <v-card variant="outlined" role="status">
          <v-card-text class="text-center py-3">
            <div class="text-h5 text-info">{{ stats.total_facet_values || 0 }}</div>
            <div class="text-caption">{{ t('entities.facetValues') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="3">
        <v-card variant="outlined" role="status">
          <v-card-text class="text-center py-3">
            <div class="text-h5 text-success">{{ stats.verified_count || 0 }}</div>
            <div class="text-caption">{{ t('entities.verified') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="3">
        <v-card variant="outlined" role="status">
          <v-card-text class="text-center py-3">
            <div class="text-h5">{{ stats.relation_count || 0 }}</div>
            <div class="text-caption">{{ t('entities.relations') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Filters Component -->
    <EntitiesFilters
      v-model:search-query="searchQuery"
      v-model:filters="filters"
      :categories="categories"
      :parent-options="parentOptions"
      :loading-parents="loadingParents"
      :facet-filter-options="facetFilterOptions"
      :has-extended-filters="hasExtendedFilters"
      :active-extended-filter-count="activeExtendedFilterCount"
      :all-extended-filters="allExtendedFilters"
      :has-any-filters="hasAnyFilters"
      :current-entity-type="currentEntityType"
      :flags="flags"
      :get-filter-title="getExtendedFilterTitle"
      @search-parents="searchParents"
      @load-entities="debouncedLoadEntities"
      @open-extended-filters="openExtendedFilterDialog"
      @clear-all-filters="clearAllFilters"
      @remove-extended-filter="removeExtendedFilter"
    />

    <!-- Entities Table/Grid/Map Container -->
    <EntitiesToolbar
      v-model:view-mode="viewMode"
      :current-entity-type="currentEntityType"
      :has-geo-data="hasGeoData"
      @refresh="loadEntities"
    >
      <!-- Table View -->
      <EntitiesTable
        v-if="viewMode === 'table'"
        :entities="store.entities"
        :total-entities="totalEntities"
        :loading="store.entitiesLoading"
        :items-per-page="itemsPerPage"
        :current-page="currentPage"
        :current-entity-type="currentEntityType"
        :flags="flags"
        :get-top-facet-counts="getTopFacetCounts"
        @update:items-per-page="itemsPerPage = $event"
        @update:current-page="loadEntities"
        @entity-click="openEntityDetail"
        @entity-edit="openEditDialog"
        @entity-delete="confirmDelete"
      />

      <!-- Cards View -->
      <EntitiesGridView
        v-else-if="viewMode === 'cards'"
        :entities="store.entities"
        :current-page="currentPage"
        :total-pages="totalPages"
        :current-entity-type="currentEntityType"
        @update:current-page="loadEntities"
        @entity-click="openEntityDetail"
      />

      <!-- Map View -->
      <v-card-text v-else-if="viewMode === 'map'" class="pa-0">
        <EntityMapView
          :entity-type-slug="currentEntityType?.slug"
          :country="extendedFilters.country || undefined"
          :admin-level1="extendedFilters.admin_level_1 || undefined"
          :admin-level2="extendedFilters.admin_level_2 || undefined"
          :search="searchQuery || undefined"
        />
      </v-card-text>
    </EntitiesToolbar>

    <!-- Entity Form Dialog -->
    <EntityFormDialog
      v-model="createDialog"
      v-model:entity-form="entityForm"
      v-model:entity-tab="entityTab"
      :editing-entity="editingEntity"
      :current-entity-type="currentEntityType"
      :flags="flags"
      :parent-options="parentOptions"
      :user-options="userOptions"
      :loading-users="loadingUsers"
      :saving="saving"
      :is-light-color="isLightColor"
      @save="saveEntity"
      @cancel="closeDialog"
    />

    <!-- Extended Filter Dialog -->
    <ExtendedFilterDialog
      v-model="extendedFilterDialog"
      v-model:temp-extended-filters="tempExtendedFilters"
      :schema-attributes="schemaAttributes"
      :attribute-value-options="attributeValueOptions"
      :location-options="locationOptions"
      :location-attributes="locationAttributes"
      :non-location-attributes="nonLocationAttributes"
      :has-attribute="hasAttribute"
      :active-extended-filter-count="activeExtendedFilterCount"
      :has-extended-filters="hasExtendedFilters"
      @load-location-options="loadLocationOptions"
      @load-attribute-values="loadAttributeValues"
      @apply-filters="applyExtendedFilters"
      @clear-filters="clearExtendedFilters"
    />

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
          <v-btn variant="tonal" @click="templateDialog = false">{{ t('common.close') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" max-width="450">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon color="error" class="mr-2">mdi-alert</v-icon>
          {{ t('entities.deleteConfirmTitle') }}
        </v-card-title>
        <v-card-text>
          <p>{{ t('entities.deleteConfirmMessage', { name: entityToDelete?.name }) }}</p>
          <v-alert
            v-if="entityToDelete?.facet_count > 0 || entityToDelete?.relation_count > 0"
            type="warning"
            variant="tonal"
            density="compact"
            class="mt-3"
          >
            <strong>{{ t('entities.warning') }}:</strong> {{ t('entities.entityHas') }}
            <span v-if="entityToDelete?.facet_count > 0"
              >{{ entityToDelete.facet_count }} {{ t('entities.facetValues') }}</span
            >
            <span v-if="entityToDelete?.facet_count > 0 && entityToDelete?.relation_count > 0">
              {{ t('entities.and') }}
            </span>
            <span v-if="entityToDelete?.relation_count > 0"
              >{{ entityToDelete.relation_count }} {{ t('entities.relations') }}</span
            >.
            {{ t('entities.willBeDeleted') }}
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="deleteDialog = false">{{ t('common.cancel') }}</v-btn>
          <v-btn variant="tonal" color="error" :loading="deleting" @click="deleteEntity">
            <v-icon start>mdi-delete</v-icon>
            {{ t('common.delete') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useEntitiesView } from '@/composables/useEntitiesView'
import EntityMapView from '@/components/entities/EntityMapView.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import EntitiesFilters from '@/components/entities/EntitiesFilters.vue'
import EntitiesToolbar from '@/components/entities/EntitiesToolbar.vue'
import EntitiesTable from '@/components/entities/EntitiesTable.vue'
import EntitiesGridView from '@/components/entities/EntitiesGridView.vue'
import EntityFormDialog from '@/components/entities/EntityFormDialog.vue'
import ExtendedFilterDialog from '@/components/entities/ExtendedFilterDialog.vue'

const { t } = useI18n()
const router = useRouter()

// Use the composable for all state and logic
const {
  typeSlug,
  selectedTypeTab,
  store,
  flags,
  loading,
  searchQuery,
  currentPage,
  itemsPerPage,
  viewMode,
  hasGeoData,
  categories,
  parentOptions,
  loadingParents,
  userOptions,
  loadingUsers,
  createDialog,
  templateDialog,
  deleteDialog,
  extendedFilterDialog,
  entityTab,
  editingEntity,
  entityToDelete,
  saving,
  deleting,
  entityForm,
  filters,
  extendedFilters,
  tempExtendedFilters,
  locationOptions,
  schemaAttributes,
  attributeValueOptions,
  stats,
  currentEntityType,
  totalEntities,
  totalPages,
  hasExtendedFilters,
  activeExtendedFilterCount,
  allExtendedFilters,
  hasAnyFilters,
  locationAttributes,
  nonLocationAttributes,
  facetFilterOptions,
  loadEntities,
  loadCategories,
  loadUsers,
  loadParentOptions,
  searchParents,
  checkGeoDataAvailable,
  loadSchemaAttributes,
  loadAttributeValues,
  loadLocationOptions,
  saveEntity,
  deleteEntity,
  openEditDialog,
  closeDialog,
  confirmDelete,
  selectTemplate,
  clearAllFilters,
  clearExtendedFilters,
  removeExtendedFilter,
  getExtendedFilterTitle,
  hasAttribute,
  onCountryChange,
  onAdminLevel1Change,
  debouncedLoadEntities,
  isLightColor,
  getTopFacetCounts,
} = useEntitiesView()

// Extended filter dialog management
function openExtendedFilterDialog() {
  tempExtendedFilters.value = { ...extendedFilters.value }
  extendedFilterDialog.value = true
  loadLocationOptions()
}

function applyExtendedFilters() {
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

// Navigation
function openEntityDetail(entity: any) {
  router.push({
    name: 'entity-detail',
    params: {
      typeSlug: currentEntityType.value?.slug,
      entitySlug: entity.slug,
    },
  })
}

// Watch for extended filter changes in dialog
watch(
  () => tempExtendedFilters.value.country,
  () => {
    onCountryChange()
  }
)

watch(
  () => tempExtendedFilters.value.admin_level_1,
  () => {
    onAdminLevel1Change()
  }
)

// Initialization
onMounted(async () => {
  await Promise.all([
    store.fetchEntityTypes(),
    store.fetchFacetTypes(),
    store.fetchAnalysisTemplates({ is_active: true }),
    loadCategories(),
    loadUsers(),
  ])

  if (typeSlug.value) {
    await store.fetchEntityTypeBySlug(typeSlug.value)
  } else if (store.activeEntityTypes.length > 0) {
    selectedTypeTab.value = store.activeEntityTypes[0].slug
  }

  await loadEntities()
  await loadParentOptions()
  await loadSchemaAttributes()
  await checkGeoDataAvailable()
})
</script>
