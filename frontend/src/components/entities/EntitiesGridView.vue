<template>
  <v-container fluid>
    <v-row>
      <v-col
        v-for="entity in entities"
        :key="entity.id"
        cols="12"
        sm="6"
        md="4"
        lg="3"
      >
        <v-card
          :elevation="2"
          class="entity-card cursor-pointer"
          @click="$emit('entity-click', entity)"
        >
          <v-card-title class="d-flex align-center">
            <v-icon
              :color="currentEntityType?.color"
              :icon="currentEntityType?.icon"
              class="mr-2"
            ></v-icon>
            {{ entity.name }}
          </v-card-title>
          <v-card-subtitle v-if="entity.hierarchy_path">
            {{ entity.hierarchy_path }}
          </v-card-subtitle>
          <v-card-text>
            <div class="d-flex ga-2 mb-2">
              <v-chip size="small" color="primary" variant="tonal">
                <v-icon start size="small">mdi-tag-multiple</v-icon>
                {{ (entity.facet_count || 0) + (entity.core_attributes ? Object.keys(entity.core_attributes).length : 0) }}
                {{ t('entities.properties') }}
              </v-chip>
              <v-chip size="small" color="info" variant="tonal">
                <v-icon start size="small">mdi-sitemap</v-icon>
                {{ (entity.relation_count || 0) + (entity.children_count || 0) + (entity.parent_id ? 1 : 0) }}
                {{ t('entities.connections', 'Verknüpfungen') }}
              </v-chip>
            </div>
          </v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn
              size="small"
              color="primary"
              variant="tonal"
              @click.stop="$emit('entity-click', entity)"
            >
              {{ t('common.details') }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
    <v-pagination
      v-if="totalPages > 1"
      :model-value="currentPage"
      :length="totalPages"
      class="mt-4"
      @update:model-value="$emit('update:current-page', $event)"
    ></v-pagination>
  </v-container>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { Entity, EntityType } from '@/types/entity'

interface Props {
  entities: Entity[]
  currentPage: number
  totalPages: number
  currentEntityType: EntityType | null
}

interface Emits {
  (e: 'update:current-page', value: number): void
  (e: 'entity-click', entity: Entity): void
}

defineProps<Props>()
defineEmits<Emits>()

const { t } = useI18n()
</script>

<style scoped>
.entity-card {
  transition: transform 0.2s, box-shadow 0.2s;
}
.entity-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(var(--v-theme-on-surface), 0.15);
}
</style>
