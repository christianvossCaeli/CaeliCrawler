<template>
  <v-card variant="outlined" class="mt-4">
    <v-card-title class="text-subtitle-2 pb-2">
      <v-icon start size="small">mdi-link-variant</v-icon>
      {{ $t('sources.form.linkedEntities') }}
    </v-card-title>
    <v-card-text>
      <p class="text-caption text-medium-emphasis mb-3">{{ $t('sources.form.linkedEntitiesHint') }}</p>

      <!-- Selected Entities -->
      <div v-if="selectedEntities.length > 0" class="mb-3">
        <v-chip
          v-for="entity in selectedEntities"
          :key="entity.id"
          closable
          color="primary"
          variant="tonal"
          class="mr-2 mb-2"
          @click:close="removeEntity(entity.id)"
        >
          <v-icon start size="small">mdi-domain</v-icon>
          {{ entity.name }}
          <span v-if="entity.entity_type_name" class="text-caption ml-1 opacity-70">
            ({{ entity.entity_type_name }})
          </span>
        </v-chip>
        <v-btn
          icon="mdi-close-circle"
          variant="text"
          size="x-small"
          color="grey"
          @click="clearAllEntities"
        />
      </div>

      <!-- Entity Search -->
      <v-autocomplete
        v-model="entitySearchQuery"
        v-model:search="entitySearchText"
        :items="entitySearchResults"
        :loading="searchingEntities"
        :label="$t('sources.form.searchEntity')"
        item-title="name"
        item-value="id"
        return-object
        clearable
        hide-no-data
        variant="outlined"
        density="comfortable"
        prepend-inner-icon="mdi-magnify"
        @update:search="onSearch"
        @update:model-value="onEntitySelect"
      >
        <template #item="{ item, props: itemProps }">
          <v-list-item v-bind="itemProps">
            <template #prepend>
              <v-icon color="primary">mdi-domain</v-icon>
            </template>
            <template #subtitle>
              <span v-if="item.raw.entity_type_name">{{ item.raw.entity_type_name }}</span>
              <span v-if="item.raw.hierarchy_path" class="text-caption ml-2">{{ item.raw.hierarchy_path }}</span>
            </template>
          </v-list-item>
        </template>
        <template #no-data>
          <v-list-item>
            <v-list-item-title>
              {{ entitySearchText?.length < 2 ? $t('sources.form.typeToSearch') : $t('sources.form.noEntitiesFound') }}
            </v-list-item-title>
          </v-list-item>
        </template>
      </v-autocomplete>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
/**
 * SourceFormEntityLinking - Entity N:M linking component
 *
 * Provides entity search and selection for linking sources to entities.
 */
import { ref, onUnmounted } from 'vue'
import { entityApi } from '@/services/api'
import { ENTITY_SEARCH } from '@/config/sources'
import type { EntityBrief } from '@/stores/entity'
import { useLogger } from '@/composables/useLogger'

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:selectedEntities', value: EntityBrief[]): void
  (e: 'entityIdsChange', ids: string[]): void
}>()

const logger = useLogger('SourceFormEntityLinking')

interface Props {
  selectedEntities: EntityBrief[]
}

// Search state
const entitySearchQuery = ref<EntityBrief | null>(null)
const entitySearchText = ref('')
const entitySearchResults = ref<EntityBrief[]>([])
const searchingEntities = ref(false)
let searchTimeout: ReturnType<typeof setTimeout> | null = null

/** Debounced search handler */
const onSearch = (query: string) => {
  if (!query || query.length < ENTITY_SEARCH.MIN_QUERY_LENGTH) {
    entitySearchResults.value = []
    return
  }

  if (searchTimeout) clearTimeout(searchTimeout)

  searchTimeout = setTimeout(async () => {
    searchingEntities.value = true
    try {
      const response = await entityApi.searchEntities({
        q: query,
        per_page: ENTITY_SEARCH.MAX_RESULTS,
      })
      const selectedIds = new Set(props.selectedEntities.map((e) => e.id))
      entitySearchResults.value = (response.data.items || []).filter(
        (e: EntityBrief) => !selectedIds.has(e.id)
      )
    } catch (e) {
      logger.error('Failed to search entities:', e)
      entitySearchResults.value = []
    } finally {
      searchingEntities.value = false
    }
  }, ENTITY_SEARCH.DEBOUNCE_MS)
}

/** Handle entity selection */
const onEntitySelect = (entity: EntityBrief | null) => {
  if (entity && !props.selectedEntities.find((e) => e.id === entity.id)) {
    const newEntities = [...props.selectedEntities, entity]
    emit('update:selectedEntities', newEntities)
    emit('entityIdsChange', newEntities.map((e) => e.id))
  }
  entitySearchQuery.value = null
  entitySearchText.value = ''
  entitySearchResults.value = []
}

/** Remove entity from selection */
const removeEntity = (entityId: string) => {
  const newEntities = props.selectedEntities.filter((e) => e.id !== entityId)
  emit('update:selectedEntities', newEntities)
  emit('entityIdsChange', newEntities.map((e) => e.id))
}

/** Clear all entities */
const clearAllEntities = () => {
  emit('update:selectedEntities', [])
  emit('entityIdsChange', [])
}

// Cleanup
onUnmounted(() => {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
    searchTimeout = null
  }
})
</script>
