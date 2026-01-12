<template>
  <div class="entity-selector">
    <!-- Selected Entities as Chips -->
    <div v-if="selectedEntities.length > 0" class="mb-3">
      <div class="text-caption text-medium-emphasis mb-1">
        {{ t('entities.selector.selected', { count: selectedEntities.length }) }}
      </div>
      <div class="d-flex flex-wrap ga-1">
        <v-chip
          v-for="entity in selectedEntities.slice(0, maxChips)"
          :key="entity.id"
          size="small"
          closable
          @click:close="removeEntity(entity.id)"
        >
          {{ entity.name }}
        </v-chip>
        <v-chip
          v-if="selectedEntities.length > maxChips"
          size="small"
          color="primary"
          variant="outlined"
        >
          +{{ selectedEntities.length - maxChips }}
        </v-chip>
      </div>
    </div>

    <!-- Search & Entity Type Filter -->
    <div class="d-flex ga-2 mb-3">
      <v-text-field
        v-model="searchQuery"
        :label="t('entities.selector.search')"
        prepend-inner-icon="mdi-magnify"
        density="compact"
        hide-details
        clearable
        class="flex-grow-1"
        @update:model-value="debouncedSearch"
      />
      <v-select
        v-model="selectedEntityType"
        :items="entityTypes"
        item-title="name_plural"
        item-value="slug"
        :label="t('entities.selector.entityType')"
        density="compact"
        hide-details
        clearable
        style="max-width: 200px"
        @update:model-value="loadEntities"
      />
    </div>

    <!-- Entity List -->
    <v-card variant="outlined" class="entity-list">
      <v-list
        v-model:selected="internalSelection"
        select-strategy="classic"
        :lines="false"
        density="compact"
        max-height="300"
        class="overflow-y-auto"
      >
        <template v-if="loading">
          <v-list-item>
            <v-progress-circular indeterminate size="20" class="mr-2" />
            {{ t('common.loading') }}
          </v-list-item>
        </template>
        <template v-else-if="loadError">
          <v-list-item>
            <v-list-item-title class="text-error">
              <v-icon icon="mdi-alert-circle" class="mr-1" />
              {{ loadError }}
            </v-list-item-title>
          </v-list-item>
        </template>
        <template v-else-if="entities.length === 0">
          <v-list-item>
            <v-list-item-title class="text-medium-emphasis">
              {{ t('entities.selector.noEntities') }}
            </v-list-item-title>
          </v-list-item>
        </template>
        <template v-else>
          <v-list-item
            v-for="entity in entities"
            :key="entity.id"
            :value="entity.id"
          >
            <template #prepend="{ isSelected }">
              <v-list-item-action start>
                <v-checkbox-btn :model-value="isSelected" />
              </v-list-item-action>
            </template>
            <v-list-item-title>{{ entity.name }}</v-list-item-title>
            <v-list-item-subtitle v-if="entity.hierarchy_path">
              {{ entity.hierarchy_path }}
            </v-list-item-subtitle>
          </v-list-item>
        </template>
      </v-list>

      <!-- Pagination -->
      <v-divider v-if="totalPages > 1" />
      <div v-if="totalPages > 1" class="d-flex align-center justify-center pa-2">
        <v-pagination
          v-model="currentPage"
          :length="totalPages"
          :total-visible="5"
          density="compact"
          @update:model-value="loadEntities"
        />
      </div>
    </v-card>

    <!-- Quick Actions -->
    <div class="d-flex justify-space-between mt-2">
      <v-btn
        v-if="selectedEntities.length > 0"
        variant="text"
        size="small"
        color="error"
        @click="clearAll"
      >
        {{ t('entities.selector.clearAll') }}
      </v-btn>
      <span v-else />
      <span class="text-caption text-medium-emphasis">
        {{ t('entities.selector.total', { count: totalEntities }) }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { entityApi } from '@/services/api'
import { useEntityStore } from '@/stores/entity'
import { useDebounce, DEBOUNCE_DELAYS } from '@/composables/useDebounce'
import { useSnackbar } from '@/composables/useSnackbar'
import { getErrorMessage } from '@/utils/errorMessage'
import type { EntityType } from '@/types/entity'

// Minimal entity representation for selector list items
interface EntityListItem {
  id: string
  name: string
  hierarchy_path?: string
}

const props = defineProps<{
  modelValue: string[]
  maxChips?: number
}>()
const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()
const { t } = useI18n()
const entityStore = useEntityStore()
const { showError } = useSnackbar()

// Configuration
const maxChips = computed(() => props.maxChips ?? 5)

// State
const searchQuery = ref('')
const selectedEntityType = ref<string | null>(null)
const entities = ref<EntityListItem[]>([])
const selectedEntities = ref<EntityListItem[]>([])
const loading = ref(false)
const currentPage = ref(1)
const totalEntities = ref(0)
const itemsPerPage = 20
const loadError = ref<string | null>(null)

// Computed
const entityTypes = computed<EntityType[]>(() => entityStore.entityTypes || [])
const totalPages = computed(() => Math.ceil(totalEntities.value / itemsPerPage))

// Internal selection model (array of IDs)
const internalSelection = computed({
  get: () => props.modelValue,
  set: (value: string[]) => {
    emit('update:modelValue', value)
    updateSelectedEntities(value)
  }
})

// Load entities from API
async function loadEntities() {
  if (!selectedEntityType.value) {
    entities.value = []
    totalEntities.value = 0
    loadError.value = null
    return
  }

  loading.value = true
  loadError.value = null
  try {
    const response = await entityApi.getEntities({
      entity_type_slug: selectedEntityType.value,
      page: currentPage.value,
      per_page: itemsPerPage,
      search: searchQuery.value || undefined,
    })
    entities.value = response.data.items
    totalEntities.value = response.data.total
  } catch (error) {
    console.error('Failed to load entities:', error)
    const errorMsg = getErrorMessage(error) || t('entities.selector.loadError')
    loadError.value = errorMsg
    showError(errorMsg)
    entities.value = []
    totalEntities.value = 0
  } finally {
    loading.value = false
  }
}

// Update selectedEntities when IDs change
function updateSelectedEntities(ids: string[]) {
  // Keep existing entities that are still selected
  const existingMap = new Map(selectedEntities.value.map(e => [e.id, e]))

  // Add any new entities from current list
  for (const entity of entities.value) {
    if (ids.includes(entity.id) && !existingMap.has(entity.id)) {
      existingMap.set(entity.id, entity)
    }
  }

  // Filter to only selected IDs
  selectedEntities.value = ids
    .map(id => existingMap.get(id))
    .filter((e): e is EntityListItem => e !== undefined)
}

// Remove entity from selection
function removeEntity(id: string) {
  const newSelection = props.modelValue.filter(eid => eid !== id)
  emit('update:modelValue', newSelection)
  selectedEntities.value = selectedEntities.value.filter(e => e.id !== id)
}

// Clear all selections
function clearAll() {
  emit('update:modelValue', [])
  selectedEntities.value = []
}

// Debounced search
const { debouncedFn: debouncedSearch } = useDebounce(
  () => {
    currentPage.value = 1
    loadEntities()
  },
  { delay: DEBOUNCE_DELAYS.SEARCH }
)

// Load entity types on mount
onMounted(async () => {
  if (entityStore.entityTypes.length === 0) {
    await entityStore.fetchEntityTypes()
  }
  // Auto-select first entity type if available
  if (entityTypes.value.length > 0 && !selectedEntityType.value) {
    selectedEntityType.value = entityTypes.value[0].slug
    await loadEntities()
  }
})

// Watch for external modelValue changes
watch(() => props.modelValue, (newIds) => {
  if (newIds.length > 0 && selectedEntities.value.length === 0) {
    // Need to load entity details for pre-selected IDs
    // This happens when editing an existing preset
    updateSelectedEntities(newIds)
  }
}, { immediate: true })
</script>

<style scoped>
.entity-selector {
  min-height: 200px;
}

.entity-list {
  max-height: 350px;
}
</style>
