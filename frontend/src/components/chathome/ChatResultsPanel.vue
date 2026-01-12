<template>
  <div v-if="hasResults" class="chat-results">
    <div class="chat-results__header">
      <span class="chat-results__title">{{ title }}</span>
      <span v-if="resultCount" class="chat-results__count">{{ resultCount }} {{ t('chatHome.results.items') }}</span>
    </div>
    <div class="chat-results__content">
      <!-- Entities List -->
      <div v-if="entities.length > 0" class="results-list">
        <div
          v-for="entity in displayedEntities"
          :key="entity.id"
          class="result-item"
          @click="navigateToEntity(entity)"
        >
          <v-icon size="18" class="result-item__icon">{{ getEntityIcon(entity) }}</v-icon>
          <div class="result-item__content">
            <div class="result-item__name">{{ entity.name }}</div>
            <div v-if="entity.type_name" class="result-item__type">{{ entity.type_name }}</div>
          </div>
          <v-icon size="16" class="result-item__arrow">mdi-chevron-right</v-icon>
        </div>
        <v-btn
          v-if="entities.length > maxDisplay"
          variant="text"
          size="small"
          block
          class="mt-2"
          @click="$emit('action', 'showAll', { entities })"
        >
          {{ t('chatHome.results.showAll', { count: entities.length }) }}
        </v-btn>
      </div>

      <!-- Visualization Component -->
      <component
        :is="visualization.component"
        v-if="visualization"
        v-bind="visualization.props"
      />

      <!-- Actions -->
      <div v-if="actions.length > 0" class="results-actions mt-3">
        <v-btn
          v-for="action in actions"
          :key="action.id"
          variant="tonal"
          size="small"
          :color="action.color || 'primary'"
          class="mr-2 mb-2"
          @click="$emit('action', action.id, action.data)"
        >
          <v-icon v-if="action.icon" start size="16">{{ action.icon }}</v-icon>
          {{ action.label }}
        </v-btn>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

interface Entity {
  id: number | string
  name: string
  type_name?: string
  type_slug?: string
  slug?: string
}

interface ResultAction {
  id: string
  label: string
  icon?: string
  color?: string
  data?: unknown
}

interface ResultsData {
  entities?: Entity[]
  count?: number
  summary?: string
  visualization?: {
    component: string
    props: Record<string, unknown>
  }
  actions?: ResultAction[]
}

const props = defineProps<{
  results: ResultsData | unknown
}>()

defineEmits<{
  action: [action: string, data: unknown]
}>()

const { t } = useI18n()
const router = useRouter()

const maxDisplay = 5

const typedResults = computed((): ResultsData => {
  if (!props.results || typeof props.results !== 'object') return {}
  return props.results as ResultsData
})

const hasResults = computed(() => {
  const r = typedResults.value
  return r.entities?.length || r.visualization || r.actions?.length
})

const entities = computed(() => typedResults.value.entities || [])
const displayedEntities = computed(() => entities.value.slice(0, maxDisplay))
const resultCount = computed(() => typedResults.value.count || entities.value.length || 0)
const visualization = computed(() => typedResults.value.visualization)
const actions = computed(() => typedResults.value.actions || [])

const title = computed(() => {
  if (entities.value.length > 0) return t('chatHome.results.entities')
  if (visualization.value) return t('chatHome.results.visualization')
  return t('chatHome.results.results')
})

function getEntityIcon(entity: Entity): string {
  const typeIconMap: Record<string, string> = {
    person: 'mdi-account',
    organization: 'mdi-domain',
    event: 'mdi-calendar',
    location: 'mdi-map-marker',
    document: 'mdi-file-document',
  }
  return typeIconMap[entity.type_slug || ''] || 'mdi-circle-small'
}

function navigateToEntity(entity: Entity) {
  if (entity.type_slug && entity.slug) {
    router.push(`/entities/${entity.type_slug}/${entity.slug}`)
  } else if (entity.id) {
    router.push(`/entity/${entity.id}`)
  }
}
</script>

<style scoped>
.results-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.result-item:hover {
  background: rgba(var(--v-theme-on-surface), 0.05);
}

.result-item__icon {
  color: rgba(var(--v-theme-on-surface), 0.6);
}

.result-item__content {
  flex: 1;
  min-width: 0;
}

.result-item__name {
  font-size: 0.875rem;
  font-weight: 500;
  color: rgb(var(--v-theme-on-surface));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.result-item__type {
  font-size: 0.75rem;
  color: rgba(var(--v-theme-on-surface), 0.5);
}

.result-item__arrow {
  color: rgba(var(--v-theme-on-surface), 0.3);
}

.results-actions {
  display: flex;
  flex-wrap: wrap;
}
</style>
