<template>
  <div v-if="hasResults" class="chat-results" role="region" :aria-label="title">
    <div class="chat-results__header">
      <span id="results-title" class="chat-results__title">{{ title }}</span>
      <span v-if="resultCount" class="chat-results__count" aria-live="polite">
        {{ resultCount }} {{ t('chatHome.results.items') }}
      </span>
    </div>
    <div class="chat-results__content">
      <!-- Redirect to Smart Query -->
      <div v-if="isRedirectResponse" class="results-redirect" role="alert">
        <v-icon size="20" class="results-redirect__icon" aria-hidden="true">mdi-arrow-right-circle</v-icon>
        <div class="results-redirect__content">
          <span class="results-redirect__text">{{ t('chatHome.results.redirectToSmartQuery') }}</span>
          <v-btn
            variant="tonal"
            size="small"
            color="primary"
            @click="navigateToSmartQuery"
          >
            <v-icon start size="16">mdi-database-search</v-icon>
            {{ t('chatHome.results.openSmartQuery') }}
          </v-btn>
        </div>
      </div>

      <!-- Navigation Target -->
      <div v-else-if="isNavigationResponse" class="results-navigation">
        <v-btn
          variant="tonal"
          color="primary"
          @click="navigateToTarget"
        >
          <v-icon start>mdi-arrow-right</v-icon>
          {{ navigationLabel }}
        </v-btn>
      </div>

      <!-- Discussion Key Points -->
      <ul
        v-else-if="keyPoints.length > 0"
        class="results-keypoints"
        role="list"
        aria-label="Wichtige Punkte"
      >
        <li
          v-for="(point, index) in keyPoints"
          :key="index"
          class="results-keypoint"
        >
          <v-icon size="16" color="primary" aria-hidden="true">mdi-check-circle</v-icon>
          <span>{{ point }}</span>
        </li>
      </ul>

      <!-- Entities List -->
      <nav
        v-if="entities.length > 0"
        class="results-list"
        role="navigation"
        aria-label="Suchergebnisse"
      >
        <a
          v-for="entity in displayedEntities"
          :key="entity.id"
          href="#"
          class="result-item"
          role="link"
          :aria-label="`${entity.name}${entity.type_name ? ', ' + entity.type_name : ''}`"
          @click.prevent="navigateToEntity(entity)"
          @keydown.enter.prevent="navigateToEntity(entity)"
        >
          <v-icon size="18" class="result-item__icon" aria-hidden="true">{{ getEntityIcon(entity) }}</v-icon>
          <div class="result-item__content">
            <div class="result-item__name">{{ entity.name }}</div>
            <div v-if="entity.type_name" class="result-item__type">{{ entity.type_name }}</div>
          </div>
          <v-icon size="16" class="result-item__arrow" aria-hidden="true">mdi-chevron-right</v-icon>
        </a>
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
      </nav>

      <!-- Visualization Component -->
      <component
        :is="visualization.component"
        v-if="visualization"
        v-bind="visualization.props"
      />

      <!-- Recommendations -->
      <div v-if="recommendations.length > 0" class="results-recommendations mt-3">
        <div class="results-recommendations__title">{{ t('chatHome.results.recommendations') }}</div>
        <div
          v-for="(rec, index) in recommendations"
          :key="index"
          class="results-recommendation"
        >
          <v-icon size="14" color="info">mdi-lightbulb-outline</v-icon>
          <span>{{ rec }}</span>
        </div>
      </div>

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

interface SmartQueryItem {
  entity_id: string
  entity_name: string
  entity_slug?: string
  entity_type?: string
  [key: string]: unknown
}

interface NavigationTarget {
  route: string
  entity_name?: string
  entity_id?: string
}

interface ResultsData {
  // Response type from Assistant API
  type?: string
  // Legacy format
  entities?: Entity[]
  count?: number
  summary?: string
  visualization?: {
    component?: string
    props?: Record<string, unknown>
    type?: string
    title?: string
  }
  actions?: ResultAction[]
  // Smart Query API format
  items?: SmartQueryItem[]
  total?: number
  suggested_actions?: ResultAction[]
  // Discussion response
  key_points?: string[]
  recommendations?: string[]
  // Navigation response
  target?: NavigationTarget
  // Redirect response
  query?: string
  mode?: 'read' | 'write' | 'plan'
}

const props = defineProps<{
  results: ResultsData | unknown
  responseType?: string
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

// Response type detection
const effectiveResponseType = computed(() => {
  return props.responseType || typedResults.value.type
})

const isRedirectResponse = computed(() => {
  return effectiveResponseType.value === 'redirect_to_smart_query'
})

const isNavigationResponse = computed(() => {
  return effectiveResponseType.value === 'navigation' && typedResults.value.target
})

const hasResults = computed(() => {
  const r = typedResults.value
  return r.entities?.length ||
    r.items?.length ||
    r.visualization ||
    r.actions?.length ||
    r.suggested_actions?.length ||
    r.key_points?.length ||
    r.recommendations?.length ||
    isRedirectResponse.value ||
    isNavigationResponse.value
})

// Support both legacy (entities) and Smart Query (items) format
const entities = computed((): Entity[] => {
  const r = typedResults.value
  if (r.entities?.length) return r.entities

  // Transform Smart Query items to entities format
  if (r.items?.length) {
    return r.items.map(item => ({
      id: item.entity_id,
      name: item.entity_name,
      type_name: item.entity_type,
      type_slug: item.entity_type,
      slug: item.entity_slug,
    }))
  }
  return []
})
const displayedEntities = computed(() => entities.value.slice(0, maxDisplay))
const resultCount = computed(() => typedResults.value.count || typedResults.value.total || entities.value.length || 0)
const visualization = computed(() => typedResults.value.visualization)
const actions = computed(() => typedResults.value.actions || typedResults.value.suggested_actions || [])

// Discussion response data
const keyPoints = computed(() => typedResults.value.key_points || [])
const recommendations = computed(() => typedResults.value.recommendations || [])

// Navigation response
const navigationLabel = computed(() => {
  const target = typedResults.value.target
  if (target?.entity_name) {
    return t('chatHome.results.navigateTo', { name: target.entity_name })
  }
  return t('chatHome.results.navigate')
})

const title = computed(() => {
  if (isRedirectResponse.value) return t('chatHome.results.smartQuery')
  if (isNavigationResponse.value) return t('chatHome.results.navigation')
  if (keyPoints.value.length > 0) return t('chatHome.results.analysis')
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

function navigateToSmartQuery() {
  const r = typedResults.value
  const query = r.query ? `?q=${encodeURIComponent(r.query)}` : ''
  const mode = r.mode ? `&mode=${r.mode}` : ''
  router.push(`/smart-query${query}${mode}`)
}

function navigateToTarget() {
  const target = typedResults.value.target
  if (target?.route) {
    router.push(target.route)
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
  text-decoration: none;
  color: inherit;
}

.result-item:hover {
  background: rgba(var(--v-theme-on-surface), 0.05);
}

.result-item:focus {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.result-item:focus-visible {
  background: rgba(var(--v-theme-primary), 0.08);
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

/* Redirect to Smart Query */
.results-redirect {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(var(--v-theme-primary), 0.05);
  border-radius: 8px;
}

.results-redirect__icon {
  color: rgb(var(--v-theme-primary));
}

.results-redirect__content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.results-redirect__text {
  font-size: 0.875rem;
  color: rgba(var(--v-theme-on-surface), 0.8);
}

/* Navigation */
.results-navigation {
  padding: 8px 0;
}

/* Key Points */
.results-keypoints {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.results-keypoint {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 0.875rem;
  color: rgb(var(--v-theme-on-surface));
  line-height: 1.5;
}

.results-keypoint .v-icon {
  flex-shrink: 0;
  margin-top: 2px;
}

/* Recommendations */
.results-recommendations {
  padding-top: 12px;
  border-top: 1px solid rgba(var(--v-theme-on-surface), 0.08);
}

.results-recommendations__title {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: rgba(var(--v-theme-on-surface), 0.5);
  margin-bottom: 8px;
}

.results-recommendation {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 0.8125rem;
  color: rgba(var(--v-theme-on-surface), 0.8);
  margin-bottom: 6px;
  line-height: 1.4;
}

.results-recommendation .v-icon {
  flex-shrink: 0;
  margin-top: 1px;
}
</style>
