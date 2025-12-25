<template>
  <div class="smart-query-results">
    <!-- Error -->
    <v-alert v-if="error" type="error" class="mb-6" closable @click:close="$emit('clear-error')">
      {{ error }}
    </v-alert>

    <!-- Loading State - Read Mode -->
    <div v-if="loading && mode !== 'write'" class="loading-section mb-6">
      <v-card class="loading-card">
        <v-card-text class="text-center py-8">
          <div class="loading-animation mb-4">
            <v-progress-circular
              indeterminate
              size="56"
              width="4"
              color="primary"
            />
          </div>
          <div class="text-h6 mb-2">{{ t('smartQueryView.loading.analyzing') }}</div>
          <div class="text-body-2 text-medium-emphasis">{{ t('smartQueryView.loading.pleaseWait') }}</div>
        </v-card-text>
      </v-card>
    </div>

    <!-- AI Generation Progress - Write Mode -->
    <SmartQueryGenerationProgress
      v-if="loading && mode === 'write'"
      :current-step="currentStep"
      class="mb-6"
    />

    <!-- Preview Mode (Write) -->
    <SmartQueryPreview
      v-if="preview"
      :preview="preview.preview || {}"
      :interpretation="preview.interpretation || {}"
      :loading="loading"
      @cancel="$emit('cancel-preview')"
      @confirm="$emit('confirm-write')"
    />

    <!-- Write Results -->
    <SmartQueryWriteResults
      v-if="results?.mode === 'write'"
      :results="results"
      :show-back-to-assistant="fromAssistant"
      @new-command="$emit('new-query')"
      @back-to-assistant="$emit('back-to-assistant')"
    />

    <!-- Compound Query Results -->
    <transition v-if="results?.is_compound" name="compound-result" appear>
      <div class="compound-results-wrapper">
        <template v-if="(results?.visualizations?.length ?? 0) > 0">
          <v-card class="mb-4 content-reveal">
            <CompoundQueryResult
              :visualizations="results?.visualizations ?? []"
              :explanation="results.explanation"
              :suggested-actions="results.suggested_actions || []"
              @action="(action, params) => $emit('visualization-action', action, params)"
            />
          </v-card>
        </template>

        <template v-else>
          <v-alert type="warning" variant="tonal" class="mb-4">
            <v-alert-title>{{ t('smartQueryView.errors.noVisualizationsTitle') }}</v-alert-title>
            {{ results.error || results.explanation || t('smartQueryView.errors.noVisualizationsHint') }}
          </v-alert>
        </template>

        <div class="d-flex justify-center">
          <v-btn variant="tonal" @click="$emit('new-query')">
            <v-icon start>mdi-refresh</v-icon>
            {{ t('smartQueryView.results.newQuery') }}
          </v-btn>
        </div>
      </div>
    </transition>

    <!-- Visualization Results (single query) -->
    <template v-else-if="results?.visualization && !results?.is_compound && results?.mode === 'read'">
      <v-card class="mb-4">
        <SmartQueryResult
          :data="results.items || results.data || []"
          :visualization="results.visualization"
          :explanation="results.explanation"
          :source-info="results.source_info"
          :suggested-actions="results.suggested_actions || []"
          @action="(action, params) => $emit('visualization-action', action, params)"
        />
      </v-card>
      <v-card-actions class="justify-center">
        <v-btn variant="tonal" @click="$emit('new-query')">
          <v-icon start>mdi-refresh</v-icon>
          {{ t('smartQueryView.results.newQuery') }}
        </v-btn>
      </v-card-actions>
    </template>

    <!-- Legacy Read Results (without visualization) -->
    <template v-else-if="results?.mode === 'read' && !results?.visualization && !results?.is_compound">
      <!-- Interpretation Bar -->
      <div class="interpretation-bar mb-4 pa-4 d-flex align-center flex-wrap ga-2">
        <v-icon size="20" class="mr-2" color="primary">mdi-brain</v-icon>
        <v-chip size="small" color="primary" variant="flat" class="mr-1">
          <v-icon start size="14">{{ getEntityTypeIcon(results.query_interpretation?.primary_entity_type) }}</v-icon>
          {{ results.query_interpretation?.primary_entity_type }}
        </v-chip>
        <v-chip
          v-for="facet in results.query_interpretation?.facet_types || []"
          :key="facet"
          size="small"
          color="secondary"
          variant="tonal"
          class="mr-1"
        >
          <v-icon start size="14">mdi-tag</v-icon>
          {{ facet }}
        </v-chip>
        <v-chip size="small" :color="getTimeFilterColor(results.query_interpretation?.time_filter)" variant="tonal">
          <v-icon start size="14">mdi-clock-outline</v-icon>
          {{ results.query_interpretation?.time_filter || 'all' }}
        </v-chip>
        <v-spacer />
        <span class="text-body-2 text-medium-emphasis" v-if="results.query_interpretation?.explanation">
          {{ results.query_interpretation.explanation }}
        </span>
      </div>

      <!-- Results Summary Card -->
      <v-card class="results-summary-card mb-6">
        <v-card-text class="d-flex align-center py-4">
          <v-avatar color="success" size="44" class="mr-4" variant="tonal">
            <v-icon>mdi-check</v-icon>
          </v-avatar>
          <div>
            <div class="text-h5 font-weight-bold">{{ results.total }}</div>
            <div class="text-body-2 text-medium-emphasis">{{ t('smartQueryView.read.resultsFound') }}</div>
          </div>
          <v-spacer />
          <v-chip size="small" variant="outlined" class="text-capitalize">
            <v-icon start size="14">mdi-view-list</v-icon>
            {{ results.grouping || 'flat' }}
          </v-chip>
          <v-btn
            variant="tonal"
            size="small"
            class="ml-3"
            @click="$emit('new-query')"
          >
            <v-icon start size="18">mdi-refresh</v-icon>
            {{ t('smartQueryView.results.newQuery') }}
          </v-btn>
        </v-card-text>
      </v-card>

      <!-- Event-grouped Results -->
      <transition-group name="result-list" tag="div" v-if="results.grouping === 'by_event'">
        <v-card
          v-for="(event, index) in results.items"
          :key="event.event_name"
          class="result-card mb-4"
          :style="{ '--animation-delay': `${index * 50}ms` }"
        >
          <v-card-text class="pa-0">
            <div class="result-card-header pa-4 d-flex align-center">
              <v-avatar color="orange" size="48" variant="tonal" class="mr-4">
                <v-icon>mdi-calendar-star</v-icon>
              </v-avatar>
              <div class="flex-grow-1">
                <div class="text-h6">{{ event.event_name }}</div>
                <div class="d-flex align-center ga-3 text-body-2 text-medium-emphasis">
                  <span><v-icon size="14" class="mr-1">mdi-calendar</v-icon>{{ event.event_date || t('smartQueryView.read.dateUnknown') }}</span>
                  <span><v-icon size="14" class="mr-1">mdi-map-marker</v-icon>{{ event.event_location || t('smartQueryView.read.locationUnknown') }}</span>
                </div>
              </div>
              <v-chip size="small" color="primary" variant="tonal">
                {{ event.attendees?.length || 0 }} {{ t('smartQueryView.read.attendeesLabel') }}
              </v-chip>
            </div>
            <v-divider />
            <v-list density="compact" class="py-0">
              <v-list-item
                v-for="attendee in event.attendees"
                :key="attendee.person_id"
                class="attendee-item"
              >
                <template v-slot:prepend>
                  <v-avatar color="primary" size="36" variant="tonal">
                    <span class="text-caption font-weight-bold">{{ getInitials(attendee.person_name) }}</span>
                  </v-avatar>
                </template>
                <v-list-item-title class="font-weight-medium">{{ attendee.person_name }}</v-list-item-title>
                <v-list-item-subtitle>{{ formatAttendeeSubtitle(attendee) }}</v-list-item-subtitle>
                <template v-slot:append>
                  <v-chip v-if="attendee.role" size="x-small" color="info" variant="tonal">
                    {{ attendee.role }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </transition-group>

      <!-- Flat Results Grid -->
      <div v-else class="results-grid">
        <transition-group name="result-list" tag="div" class="results-grid-inner">
          <v-card
            v-for="(item, index) in results.items"
            :key="item.entity_id"
            class="result-card"
            :style="{ '--animation-delay': `${index * 50}ms` }"
          >
            <v-card-text class="pa-4">
              <div class="d-flex align-start mb-3">
                <v-avatar
                  :color="getEntityTypeColor(item.entity_type)"
                  size="44"
                  variant="tonal"
                  class="mr-3"
                >
                  <v-icon size="22">{{ getEntityTypeIcon(item.entity_type) }}</v-icon>
                </v-avatar>
                <div class="flex-grow-1 overflow-hidden">
                  <div class="text-subtitle-1 font-weight-bold text-truncate">{{ item.entity_name }}</div>
                  <div v-if="item.attributes?.position" class="text-body-2 text-medium-emphasis">
                    {{ item.attributes.position }}
                    <span v-if="item.relations?.works_for" class="text-primary">
                      @ {{ item.relations.works_for.entity_name }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- Facets -->
              <template v-if="Object.keys(item.facets || {}).length > 0">
                <template v-for="(values, facetType) in item.facets" :key="facetType">
                  <div v-if="values.length > 0" class="facet-group mb-2">
                    <div class="text-caption text-medium-emphasis mb-1 d-flex align-center">
                      <v-icon size="12" class="mr-1">mdi-tag-outline</v-icon>
                      {{ facetType }}
                      <span class="ml-1">({{ values.length }})</span>
                    </div>
                    <div class="d-flex flex-wrap ga-1">
                      <v-chip
                        v-for="fv in values.slice(0, 3)"
                        :key="fv.id"
                        size="x-small"
                        variant="tonal"
                        :color="getSourceTypeColor(fv.source_type)"
                      >
                        <v-icon v-if="fv.source_type" start size="10">{{ getSourceTypeIcon(fv.source_type) }}</v-icon>
                        {{ fv.text?.substring(0, 40) }}{{ fv.text?.length > 40 ? '...' : '' }}
                        <v-tooltip activator="parent" location="top">
                          {{ fv.text }} ({{ getSourceTypeLabel(fv.source_type) }})
                        </v-tooltip>
                      </v-chip>
                      <v-chip v-if="values.length > 3" size="x-small" variant="text" color="primary">
                        +{{ values.length - 3 }}
                      </v-chip>
                    </div>
                  </div>
                </template>
              </template>
            </v-card-text>
          </v-card>
        </transition-group>
      </div>

      <!-- No Results -->
      <v-card v-if="results.total === 0" class="no-results-card text-center py-12">
        <v-avatar size="80" color="grey-lighten-3" class="mb-4">
          <v-icon size="40" color="grey">mdi-database-search</v-icon>
        </v-avatar>
        <div class="text-h6 mb-2">{{ t('smartQueryView.read.noResults') }}</div>
        <div class="text-body-2 text-medium-emphasis mb-4">
          {{ t('smartQueryView.read.noResultsHint') }}
        </div>
        <v-btn variant="tonal" @click="$emit('new-query')">
          <v-icon start>mdi-refresh</v-icon>
          {{ t('smartQueryView.results.newQuery') }}
        </v-btn>
      </v-card>

      <!-- Back to Assistant Button -->
      <v-card v-if="fromAssistant" class="mt-4">
        <v-card-actions class="justify-center">
          <v-btn variant="tonal" @click="$emit('new-query')">{{ t('smartQueryView.results.newQuery') }}</v-btn>
          <v-btn
            color="primary"
            variant="elevated"
            @click="$emit('back-to-assistant')"
          >
            <v-icon start>mdi-arrow-left</v-icon>
            {{ t('smartQueryView.results.backToAssistant') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { SmartQueryResult } from '@/components/smartquery/visualizations'
import CompoundQueryResult from '@/components/smartquery/CompoundQueryResult.vue'
import SmartQueryGenerationProgress from '@/components/smartquery/SmartQueryGenerationProgress.vue'
import SmartQueryPreview from '@/components/smartquery/SmartQueryPreview.vue'
import SmartQueryWriteResults from '@/components/smartquery/SmartQueryWriteResults.vue'
import type { QueryMode, SmartQueryResults, SmartQueryPreview as PreviewType } from '@/composables/useSmartQuery'

interface Props {
  results: SmartQueryResults | null
  preview: PreviewType | null
  loading?: boolean
  error?: string | null
  mode: QueryMode
  currentStep?: number
  fromAssistant?: boolean
}

defineProps<Props>()

defineEmits<{
  'clear-error': []
  'cancel-preview': []
  'confirm-write': []
  'new-query': []
  'back-to-assistant': []
  'visualization-action': [action: string, params: Record<string, any>]
}>()

const { t } = useI18n()

// Helper functions
function getEntityTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    person: 'mdi-account',
    municipality: 'mdi-city',
    event: 'mdi-calendar-star',
    organization: 'mdi-domain',
  }
  return icons[type] || 'mdi-circle'
}

function getEntityTypeColor(type: string): string {
  const colors: Record<string, string> = {
    person: 'blue',
    municipality: 'green',
    event: 'orange',
    organization: 'purple',
  }
  return colors[type] || 'grey'
}

function getTimeFilterColor(filter?: string): string {
  switch (filter) {
    case 'future_only': return 'success'
    case 'past_only': return 'grey'
    default: return 'info'
  }
}

function getSourceTypeColor(sourceType?: string): string {
  const colors: Record<string, string> = {
    PYSIS: 'info',
    DOCUMENT: 'secondary',
    MANUAL: 'success',
    SMART_QUERY: 'warning',
    AI_ASSISTANT: 'purple',
    IMPORT: 'blue-grey',
    ATTACHMENT: 'teal',
  }
  return colors[sourceType || ''] || 'secondary'
}

function getSourceTypeIcon(sourceType?: string): string {
  const icons: Record<string, string> = {
    PYSIS: 'mdi-database-sync',
    DOCUMENT: 'mdi-file-document',
    MANUAL: 'mdi-account-edit',
    SMART_QUERY: 'mdi-brain',
    AI_ASSISTANT: 'mdi-robot',
    IMPORT: 'mdi-import',
    ATTACHMENT: 'mdi-paperclip',
  }
  return icons[sourceType || ''] || 'mdi-tag'
}

function getSourceTypeLabel(sourceType?: string): string {
  const labels: Record<string, string> = {
    PYSIS: 'PySis',
    DOCUMENT: t('smartQueryView.sourceTypes.document'),
    MANUAL: t('smartQueryView.sourceTypes.manual'),
    SMART_QUERY: 'Smart Query',
    AI_ASSISTANT: t('smartQueryView.sourceTypes.aiAssistant'),
    IMPORT: t('smartQueryView.sourceTypes.import'),
    ATTACHMENT: t('smartQueryView.sourceTypes.attachment'),
  }
  return labels[sourceType || ''] || sourceType || t('smartQueryView.sourceTypes.unknown')
}

function getInitials(name: string): string {
  return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
}

function formatAttendeeSubtitle(attendee: any): string {
  const parts = []
  if (attendee.position) parts.push(attendee.position)
  if (attendee.municipality?.name) parts.push(attendee.municipality.name)
  if (attendee.topic) parts.push(`"${attendee.topic}"`)
  return parts.join(' | ') || t('smartQueryView.read.noDetails')
}
</script>

<style scoped>
/* Loading */
.loading-card {
  border-radius: 16px !important;
}

.loading-animation {
  animation: pulse 1.5s ease-in-out infinite;
}

/* Interpretation Bar */
.interpretation-bar {
  background: rgba(var(--v-theme-surface-variant), 0.4);
  border-radius: 12px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
}

/* Results */
.results-summary-card {
  border-radius: 16px !important;
  border-left: 4px solid rgb(var(--v-theme-success));
}

.results-grid-inner {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.result-card {
  border-radius: 12px !important;
  transition: all 0.2s ease;
  animation: slideUp 0.3s ease backwards;
  animation-delay: var(--animation-delay, 0ms);
}

.result-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(var(--v-theme-on-surface), 0.1);
}

.result-card-header {
  background: rgba(var(--v-theme-surface-variant), 0.2);
}

.attendee-item {
  transition: background-color 0.2s ease;
}

.attendee-item:hover {
  background: rgba(var(--v-theme-primary), 0.04);
}

.facet-group {
  padding: 8px;
  background: rgba(var(--v-theme-surface-variant), 0.3);
  border-radius: 8px;
}

.no-results-card {
  border-radius: 16px !important;
}

/* Animations */
@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}

.result-list-enter-active {
  animation: slideUp 0.3s ease;
}

.result-list-leave-active {
  animation: slideUp 0.2s ease reverse;
}

.result-list-move {
  transition: transform 0.3s ease;
}

.compound-result-enter-active,
.compound-result-leave-active {
  transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.compound-result-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.compound-result-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.content-reveal {
  animation: contentReveal 0.4s ease-out;
}

@keyframes contentReveal {
  from {
    opacity: 0;
    clip-path: inset(0 0 100% 0);
  }
  to {
    opacity: 1;
    clip-path: inset(0 0 0 0);
  }
}

@media (max-width: 768px) {
  .results-grid-inner {
    grid-template-columns: 1fr;
  }

  .interpretation-bar {
    flex-direction: column;
    align-items: flex-start !important;
  }
}
</style>
