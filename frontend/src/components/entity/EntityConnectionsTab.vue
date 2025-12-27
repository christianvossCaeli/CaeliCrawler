<template>
  <v-card>
    <v-card-text>
      <!-- Loading State -->
      <div v-if="loadingRelations || loadingChildren" class="text-center pa-8">
        <v-progress-circular indeterminate color="primary" size="48"></v-progress-circular>
        <p class="mt-4 text-medium-emphasis">{{ t('entityDetail.loadingConnections', 'Lade Verknüpfungen...') }}</p>
      </div>

      <div v-else>
        <!-- Hierarchy Tree Visualization -->
        <div class="hierarchy-tree mb-6">
          <!-- Parent (Übergeordnet) -->
          <div v-if="entity?.parent_id" class="tree-level tree-parent">
            <div class="tree-connector tree-connector-down"></div>
            <v-card
              variant="outlined"
              class="tree-node tree-node-parent mx-auto"
              max-width="400"
              style="cursor: pointer;"
              @click="navigateToParent"
            >
              <v-card-text class="d-flex align-center pa-3">
                <v-avatar :color="entityType?.color || 'primary'" size="44" class="mr-3">
                  <v-icon :icon="entityType?.icon || 'mdi-folder'" color="white"></v-icon>
                </v-avatar>
                <div class="flex-grow-1">
                  <div class="text-overline text-medium-emphasis mb-0">
                    {{ entityType?.hierarchy_config?.parent_label || t('entityDetail.connections.parent', 'Übergeordnet') }}
                  </div>
                  <div class="text-subtitle-1 font-weight-medium">{{ entity.parent_name || 'Übergeordnete Entity' }}</div>
                </div>
                <v-icon color="primary">mdi-arrow-up</v-icon>
              </v-card-text>
            </v-card>
          </div>

          <!-- Current Entity (Zentrum) -->
          <div class="tree-level tree-current my-4">
            <div v-if="entity?.parent_id" class="tree-connector tree-connector-vertical"></div>
            <v-card
              variant="outlined"
              class="tree-node tree-node-current mx-auto elevation-2"
              max-width="450"
              :style="{ borderColor: entityType?.color || 'var(--v-theme-primary)', borderWidth: '2px' }"
            >
              <v-card-text class="d-flex align-center pa-4">
                <v-avatar :color="entityType?.color || 'primary'" size="52" class="mr-4">
                  <v-icon :icon="entityType?.icon || 'mdi-folder'" color="white" size="28"></v-icon>
                </v-avatar>
                <div class="flex-grow-1">
                  <div class="text-overline text-medium-emphasis mb-0">{{ entityType?.name || 'Entity' }}</div>
                  <div class="text-h6 font-weight-bold">{{ entity?.name }}</div>
                  <div v-if="entity?.external_id" class="text-caption text-medium-emphasis">{{ entity.external_id }}</div>
                </div>
                <v-chip :color="entityType?.color || 'primary'" variant="tonal" size="small" class="ml-2">
                  <v-icon start size="x-small">mdi-sitemap</v-icon>
                  {{ totalConnectionsCount }}
                </v-chip>
              </v-card-text>
            </v-card>
            <div v-if="childrenCount > 0 || relations.length > 0" class="tree-connector tree-connector-vertical tree-connector-down-from-current"></div>
          </div>

          <!-- Children (Untergeordnete) - Tree Branch Style -->
          <div v-if="hierarchyEnabled && entityType?.supports_hierarchy && childrenCount > 0" class="tree-level tree-children">
            <div class="d-flex justify-center mb-3">
              <v-chip color="success" variant="tonal" size="small">
                <v-icon start size="small">mdi-arrow-down</v-icon>
                {{ entityType?.hierarchy_config?.children_label || t('entityDetail.connections.children', 'Untergeordnete') }}
                ({{ childrenCount }})
              </v-chip>
            </div>

            <!-- Search for children -->
            <v-text-field
              v-if="children.length > 5"
              :model-value="childrenSearchQuery"
              prepend-inner-icon="mdi-magnify"
              :label="t('common.search')"
              clearable
              hide-details
              density="compact"
              variant="outlined"
              class="mb-3 mx-auto"
              style="max-width: 400px;"
              @update:model-value="$emit('update:childrenSearchQuery', $event)"
            ></v-text-field>

            <!-- Children Grid -->
            <div class="tree-children-grid">
              <v-card
                v-for="child in filteredChildren"
                :key="child.id"
                variant="outlined"
                class="tree-node tree-node-child"
                :to="`/entities/${typeSlug}/${child.slug}`"
              >
                <v-card-text class="d-flex align-center pa-3">
                  <v-avatar :color="entityType?.color || 'success'" size="36" class="mr-3">
                    <v-icon :icon="entityType?.icon || 'mdi-folder'" color="white" size="small"></v-icon>
                  </v-avatar>
                  <div class="flex-grow-1 overflow-hidden">
                    <div class="text-subtitle-2 font-weight-medium text-truncate">{{ child.name }}</div>
                    <div class="text-caption text-medium-emphasis">
                      <span v-if="child.external_id">{{ child.external_id }}</span>
                      <v-chip v-if="child.children_count" size="x-small" variant="text" class="ml-1 pa-0">
                        <v-icon size="x-small">mdi-file-tree</v-icon>
                        {{ child.children_count }}
                      </v-chip>
                    </div>
                  </div>
                  <v-icon size="small" color="grey">mdi-chevron-right</v-icon>
                </v-card-text>
              </v-card>
            </div>

            <!-- Pagination -->
            <div v-if="childrenTotalPages > 1" class="d-flex justify-center mt-4">
              <v-pagination
                :model-value="childrenPage"
                :length="childrenTotalPages"
                :total-visible="5"
                density="compact"
                @update:model-value="(page: number) => { $emit('update:childrenPage', page); $emit('loadChildren') }"
              ></v-pagination>
            </div>
          </div>
        </div>

        <v-divider v-if="relations.length > 0" class="my-6"></v-divider>

        <!-- Relations Section (Other Connections) -->
        <div v-if="relations.length > 0" class="relations-section">
          <div class="d-flex align-center justify-space-between mb-4">
            <div class="d-flex align-center">
              <v-icon color="info" size="small" class="mr-2">mdi-link-variant</v-icon>
              <span class="text-subtitle-1 font-weight-medium">{{ t('entityDetail.connections.otherRelations', 'Weitere Verknüpfungen') }}</span>
              <v-chip size="x-small" class="ml-2">{{ relations.length }}</v-chip>
            </div>
            <v-btn variant="tonal" color="primary" size="small" @click="$emit('addRelation')">
              <v-icon start size="small">mdi-link-plus</v-icon>
              {{ t('entityDetail.addRelation') }}
            </v-btn>
          </div>

          <div class="relations-grid">
            <v-card
              v-for="rel in relations"
              :key="rel.id"
              variant="outlined"
              class="relation-card"
              style="cursor: pointer;"
              @click="$emit('navigateRelation', rel)"
            >
              <v-card-text class="d-flex align-center pa-3">
                <v-avatar :color="rel.relation_type_color || 'info'" size="36" class="mr-3">
                  <v-icon color="white" size="small">mdi-link-variant</v-icon>
                </v-avatar>
                <div class="flex-grow-1 overflow-hidden">
                  <div class="text-caption text-medium-emphasis">{{ rel.relation_type_name }}</div>
                  <div class="text-subtitle-2 font-weight-medium text-truncate">
                    {{ rel.source_entity_id === entity?.id ? rel.target_entity_name : rel.source_entity_name }}
                  </div>
                </div>
                <div class="d-flex align-center ga-1">
                  <v-chip v-if="rel.human_verified" size="x-small" color="success" variant="flat">
                    <v-icon size="x-small">mdi-check</v-icon>
                  </v-chip>
                  <v-btn icon size="x-small" variant="text" @click.stop="$emit('editRelation', rel)">
                    <v-icon size="x-small">mdi-pencil</v-icon>
                  </v-btn>
                  <v-btn icon size="x-small" variant="text" color="error" @click.stop="$emit('deleteRelation', rel)">
                    <v-icon size="x-small">mdi-delete</v-icon>
                  </v-btn>
                </div>
              </v-card-text>
            </v-card>
          </div>
        </div>

        <!-- Empty State when no connections at all -->
        <div v-if="totalConnectionsCount === 0" class="text-center pa-8">
          <v-icon size="80" color="grey-lighten-1" class="mb-4">mdi-sitemap</v-icon>
          <h3 class="text-h6 mb-2">{{ t('entityDetail.emptyState.noConnections', 'Keine Verknüpfungen') }}</h3>
          <p class="text-body-2 text-medium-emphasis mb-4">
            {{ t('entityDetail.emptyState.noConnectionsDesc', 'Diese Entity hat noch keine Verknüpfungen zu anderen Entities.') }}
          </p>
          <v-btn variant="tonal" color="primary" @click="$emit('addRelation')">
            <v-icon start>mdi-link-plus</v-icon>
            {{ t('entityDetail.addRelation') }}
          </v-btn>
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

// Types - Use relaxed types to be compatible with store types
interface Entity {
  id: string
  name: string
  external_id?: string | null
  parent_id?: string | null
  parent_name?: string | null
  parent_slug?: string | null
  slug?: string | null
  children_count?: number
}

interface EntityType {
  slug: string
  name: string
  icon?: string | null
  color?: string | null
  supports_hierarchy?: boolean | null
  hierarchy_config?: {
    parent_label?: string
    children_label?: string
  } | null
}

interface Relation {
  id: string
  relation_type_id: string
  source_entity_id: string
  source_entity_name: string
  source_entity_slug: string
  source_entity_type_slug: string
  target_entity_id: string
  target_entity_name: string
  target_entity_slug: string
  target_entity_type_slug: string
  relation_type_name: string
  relation_type_name_inverse: string | null
  relation_type_color: string | null
  attributes: Record<string, unknown>
  human_verified: boolean
}

// Props
const props = defineProps<{
  entity: Entity | null
  entityType: EntityType | null
  typeSlug: string
  relations: Relation[]
  children: Entity[]
  childrenCount: number
  childrenPage: number
  childrenTotalPages: number
  childrenSearchQuery: string
  loadingRelations: boolean
  loadingChildren: boolean
  hierarchyEnabled: boolean
}>()

// Emits
defineEmits<{
  addRelation: []
  editRelation: [relation: Relation]
  deleteRelation: [relation: Relation]
  navigateRelation: [relation: Relation]
  loadChildren: []
  'update:childrenPage': [page: number]
  'update:childrenSearchQuery': [query: string]
}>()

const { t } = useI18n()
const router = useRouter()

// Computed
const totalConnectionsCount = computed(() => {
  const relationCount = props.relations.length
  const childCount = props.entity?.children_count || props.childrenCount || 0
  const hasParent = props.entity?.parent_id ? 1 : 0
  return relationCount + childCount + hasParent
})

const filteredChildren = computed(() => {
  if (!props.childrenSearchQuery) return props.children
  const query = props.childrenSearchQuery.toLowerCase()
  return props.children.filter(child =>
    child.name.toLowerCase().includes(query) ||
    child.external_id?.toLowerCase().includes(query)
  )
})

// Methods
function navigateToParent() {
  if (props.entity?.parent_id) {
    // Navigate using parent slug if available, otherwise fall back to parent_id
    const parentSlug = props.entity.parent_slug || props.entity.parent_id
    router.push(`/entities/${props.typeSlug}/${parentSlug}`)
  }
}
</script>

<style scoped>
/* Hierarchy Tree Styles */
.hierarchy-tree {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.tree-level {
  position: relative;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.tree-connector {
  position: absolute;
  left: 50%;
  width: 2px;
  background: linear-gradient(180deg, var(--v-theme-primary) 0%, var(--v-theme-success) 100%);
}

.tree-connector-down {
  bottom: 0;
  height: 30px;
  transform: translateX(-50%);
}

.tree-connector-vertical {
  top: -30px;
  height: 30px;
  transform: translateX(-50%);
}

.tree-connector-down-from-current {
  top: auto;
  bottom: -30px;
  transform: translateX(-50%);
}

.tree-node {
  transition: all 0.2s ease;
}

.tree-node:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.tree-node-current {
  transform: none !important;
}

.tree-children-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
}

.tree-node-child {
  cursor: pointer;
}

/* Relations Grid */
.relations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.relation-card {
  transition: all 0.2s ease;
}

.relation-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
</style>
