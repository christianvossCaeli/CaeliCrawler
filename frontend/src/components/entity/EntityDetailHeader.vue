<template>
  <v-card class="mb-6">
    <v-card-text>
      <div class="d-flex align-center">
        <v-icon :icon="entityType?.icon ?? 'mdi-folder'" :color="entityType?.color ?? undefined" size="48" class="mr-4"></v-icon>
        <div class="flex-grow-1">
          <div class="d-flex align-center mb-1">
            <h1 class="text-h4 mr-3">{{ entity.name }}</h1>
            <v-chip v-if="entity.external_id" size="small" variant="tonal" color="info">
              <span class="text-caption font-weight-medium">ID:</span>
              <span class="ml-1">{{ entity.external_id }}</span>
            </v-chip>
          </div>
          <div v-if="entity.hierarchy_path" class="text-body-2 text-medium-emphasis">
            {{ entity.hierarchy_path }}
          </div>
        </div>
        <div class="d-flex ga-2">
          <FavoriteButton
            :entity-id="entity.id"
            size="default"
            variant="tonal"
            show-tooltip
          />
          <v-btn variant="tonal" :title="t('entityDetail.notes')" @click="$emit('openNotes')">
            <v-icon>mdi-note-text</v-icon>
            <v-badge v-if="notesCount" :content="notesCount" color="primary" floating></v-badge>
          </v-btn>
          <v-btn variant="tonal" :title="t('entityDetail.export')" @click="$emit('openExport')">
            <v-icon>mdi-export</v-icon>
          </v-btn>
          <v-btn variant="outlined" @click="$emit('openEdit')">
            <v-icon start>mdi-pencil</v-icon>
            {{ t('entityDetail.edit') }}
          </v-btn>
          <v-menu>
            <template #activator="{ props: activatorProps }">
              <v-btn variant="tonal" color="primary" v-bind="activatorProps">
                <v-icon start>mdi-plus</v-icon>
                {{ t('entityDetail.addFacet') }}
                <v-icon end>mdi-chevron-down</v-icon>
              </v-btn>
            </template>
            <v-list>
              <v-list-item
                v-for="facetGroup in facetGroups"
                :key="facetGroup.facet_type_id"
                @click="$emit('addFacetValue', facetGroup)"
              >
                <template #prepend>
                  <v-icon :icon="facetGroup.facet_type_icon" :color="facetGroup.facet_type_color" size="small"></v-icon>
                </template>
                <v-list-item-title>{{ facetGroup.facet_type_name }}</v-list-item-title>
                <template #append>
                  <v-chip size="x-small" variant="text">{{ facetGroup.value_count }}</v-chip>
                </template>
              </v-list-item>
              <v-divider v-if="facetGroups?.length" class="my-1"></v-divider>
              <v-list-item @click="$emit('addFacet')">
                <template #prepend>
                  <v-icon icon="mdi-tag-plus" color="grey" size="small"></v-icon>
                </template>
                <v-list-item-title class="text-medium-emphasis">{{ t('entities.facet.title') }}</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </div>
      </div>

      <!-- Stats Row -->
      <v-row class="mt-4">
        <v-col cols="6" sm="3" md="2">
          <div class="text-center">
            <div class="text-h5">{{ totalPropertiesCount }}</div>
            <div class="text-caption text-medium-emphasis">{{ t('entityDetail.stats.properties', 'Eigenschaften') }}</div>
          </div>
        </v-col>
        <v-col cols="6" sm="3" md="2">
          <div class="text-center">
            <div class="text-h5">{{ totalConnectionsCount }}</div>
            <div class="text-caption text-medium-emphasis">{{ t('entityDetail.stats.connections', 'Verknüpfungen') }}</div>
          </div>
        </v-col>
        <v-col cols="6" sm="3" md="2">
          <div class="text-center">
            <div class="text-h5">{{ verifiedCount }}</div>
            <div class="text-caption text-medium-emphasis">{{ t('entityDetail.stats.verified') }}</div>
          </div>
        </v-col>
        <v-col cols="6" sm="3" md="2">
          <div class="text-center">
            <div class="text-h5">{{ dataSourcesCount }}</div>
            <div class="text-caption text-medium-emphasis">{{ t('entityDetail.stats.dataSources') }}</div>
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
      <div v-if="hasAttributes" class="d-flex flex-wrap ga-1 mt-2">
        <v-chip v-for="(value, key) in entity.core_attributes" :key="key" size="small" variant="tonal">
          <strong class="mr-1">{{ formatAttributeKey(String(key)) }}:</strong>
          {{ formatAttributeValue(value) }}
        </v-chip>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import FavoriteButton from '@/components/FavoriteButton.vue'
import type { FacetGroup } from '@/types/entity'

// Types - Use relaxed types to be compatible with store types
interface EntityType {
  slug: string
  name: string
  icon?: string | null
  color?: string | null
  attribute_schema?: {
    properties?: Record<string, { title?: string }>
  } | null
}

interface Entity {
  id: string
  name: string
  external_id?: string | null
  hierarchy_path?: string | null
  latitude?: number | null
  longitude?: number | null
  core_attributes?: Record<string, unknown> | null
  facet_count?: number
  relation_count?: number
  children_count?: number
  parent_id?: string | null
}

// Props
const props = defineProps<{
  entity: Entity
  entityType?: EntityType | null
  facetGroups?: FacetGroup[]
  notesCount: number
  verifiedCount: number
  dataSourcesCount: number
  childrenCount?: number
}>()

// Emits
defineEmits<{
  openNotes: []
  openExport: []
  openEdit: []
  addFacet: []
  addFacetValue: [facetGroup: FacetGroup]
}>()

const { t } = useI18n()

// Computed
const hasAttributes = computed(() =>
  props.entity?.core_attributes && Object.keys(props.entity.core_attributes).length > 0
)

const totalConnectionsCount = computed(() => {
  const relationCount = props.entity?.relation_count || 0
  const childCount = props.entity?.children_count || props.childrenCount || 0
  const hasParent = props.entity?.parent_id ? 1 : 0
  return relationCount + childCount + hasParent
})

const totalPropertiesCount = computed(() => {
  const facetCount = props.entity?.facet_count || 0
  const coreAttrCount = props.entity?.core_attributes
    ? Object.keys(props.entity.core_attributes).length
    : 0
  return facetCount + coreAttrCount
})

// Attribute translations
const attributeTranslations = computed<Record<string, string>>(() => ({
  population: t('entityDetail.attributes.population'),
  area_km2: t('entityDetail.attributes.area'),
  official_code: t('entityDetail.attributes.officialCode'),
  locality_type: t('entityDetail.attributes.localityType'),
  website: t('entityDetail.attributes.website'),
  academic_title: t('entityDetail.attributes.academicTitle'),
  first_name: t('entityDetail.attributes.firstName'),
  last_name: t('entityDetail.attributes.lastName'),
  email: t('entityDetail.attributes.email'),
  phone: t('entityDetail.attributes.phone'),
  role: t('entityDetail.attributes.role'),
  org_type: t('entityDetail.attributes.orgType'),
  address: t('entityDetail.attributes.address'),
  event_date: t('entityDetail.attributes.eventDate'),
  event_end_date: t('entityDetail.attributes.eventEndDate'),
  location: t('entityDetail.attributes.location'),
  organizer: t('entityDetail.attributes.organizer'),
  event_type: t('entityDetail.attributes.eventType'),
  description: t('entityDetail.attributes.description'),
}))

// Helpers
function formatAttributeKey(key: string): string {
  // First try to get title from entity type's attribute_schema
  const schema = props.entityType?.attribute_schema
  if (schema?.properties?.[key]?.title) {
    return schema.properties[key].title
  }
  // Then try the translation map
  if (attributeTranslations.value[key]) {
    return attributeTranslations.value[key]
  }
  // Finally, fallback to basic formatting
  return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

function formatAttributeValue(value: unknown): string {
  if (typeof value === 'number') {
    return value.toLocaleString('de-DE')
  }
  return String(value)
}
</script>
