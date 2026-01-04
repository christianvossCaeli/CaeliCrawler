<template>
  <v-menu location="bottom" :close-on-content-click="false">
    <template #activator="{ props: menuProps }">
      <v-chip
        v-bind="menuProps"
        size="small"
        :color="hasEntities ? 'primary' : 'grey'"
        :variant="hasEntities ? 'flat' : 'outlined'"
        class="cursor-pointer entity-trigger-chip"
      >
        <v-icon start size="small">mdi-domain</v-icon>
        {{ entityCount }}
      </v-chip>
    </template>

    <v-card min-width="280" max-width="400" class="entity-popup-card">
      <v-card-title class="text-subtitle-2 py-2 d-flex align-center">
        <v-icon size="small" class="mr-2">mdi-domain</v-icon>
        {{ $t('results.detail.relevantEntities') }}
      </v-card-title>

      <v-divider />

      <v-card-text class="pa-2">
        <template v-if="hasEntities">
          <v-chip
            v-for="(entityRef, idx) in entityReferences"
            :key="idx"
            :color="entityRef.entity_id ? getEntityTypeColor(entityRef.entity_type) : 'grey'"
            size="small"
            :variant="entityRef.entity_id ? 'elevated' : 'outlined'"
            :to="entityRef.entity_id ? `/entity/${entityRef.entity_id}` : undefined"
            class="ma-1 entity-chip"
          >
            <v-icon start size="x-small">{{ getEntityTypeIcon(entityRef.entity_type) }}</v-icon>
            {{ entityRef.entity_name }}
            <v-icon v-if="entityRef.entity_id" end size="x-small">mdi-open-in-new</v-icon>
          </v-chip>
        </template>

        <div v-else class="text-medium-emphasis text-caption pa-2">
          {{ $t('results.detail.noEntityReferences') }}
        </div>
      </v-card-text>
    </v-card>
  </v-menu>
</template>

<script setup lang="ts">
/**
 * EntityReferencePopup - Hover popup showing entity references
 *
 * Displays a chip with entity count that expands to show all
 * referenced entities with navigation links.
 */
import { computed } from 'vue'
import { useResultsHelpers, type EntityReference } from '@/composables/results'

const props = defineProps<{
  entityReferences: EntityReference[] | undefined
}>()

const { getEntityTypeColor, getEntityTypeIcon } = useResultsHelpers()

const entityCount = computed(() => props.entityReferences?.length || 0)
const hasEntities = computed(() => entityCount.value > 0)
</script>

<style scoped>
.entity-trigger-chip {
  transition: transform 0.15s ease;
}

.entity-trigger-chip:hover {
  transform: scale(1.05);
}

.entity-popup-card {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.entity-chip {
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.entity-chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}
</style>
