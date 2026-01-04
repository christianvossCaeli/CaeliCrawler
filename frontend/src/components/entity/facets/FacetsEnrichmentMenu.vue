<template>
  <v-menu
    v-if="visible"
    :model-value="open"
    :close-on-content-click="false"
    location="bottom end"
    @update:model-value="$emit('update:open', $event)"
  >
    <template #activator="{ props: activatorProps }">
      <v-btn
        v-bind="activatorProps"
        color="secondary"
        size="small"
        variant="tonal"
        :loading="loading"
      >
        <v-icon start>mdi-auto-fix</v-icon>
        {{ t('entityDetail.enrichment.buttonLabel') }}
        <v-icon end>mdi-chevron-down</v-icon>
      </v-btn>
    </template>

    <v-card min-width="380" max-width="450">
      <v-card-title class="text-subtitle-1 pb-0">
        {{ t('entityDetail.enrichment.dropdownTitle') }}
      </v-card-title>

      <v-card-text v-if="sources" class="pb-2">
        <!-- PySIS Source -->
        <v-checkbox
          v-if="sources.pysis?.available"
          :model-value="selectedSources"
          value="pysis"
          hide-details
          density="compact"
          class="mb-1"
          @update:model-value="handleSourceChange($event)"
        >
          <template #label>
            <div class="d-flex align-center justify-space-between w-100">
              <span class="d-flex align-center">
                <v-icon start size="small" color="deep-purple">mdi-database</v-icon>
                {{ t('entityDetail.enrichment.sourcePysis') }}
                <v-chip size="x-small" class="ml-2">{{ sources.pysis.count }}</v-chip>
              </span>
              <span v-if="sources.pysis.last_updated" class="text-caption text-medium-emphasis ml-2">
                {{ formatDate(sources.pysis.last_updated) }}
              </span>
            </div>
          </template>
        </v-checkbox>

        <!-- Relations Source -->
        <v-checkbox
          v-if="sources.relations?.available"
          :model-value="selectedSources"
          value="relations"
          hide-details
          density="compact"
          class="mb-1"
          @update:model-value="handleSourceChange($event)"
        >
          <template #label>
            <div class="d-flex align-center justify-space-between w-100">
              <span class="d-flex align-center">
                <v-icon start size="small" color="blue">mdi-link-variant</v-icon>
                {{ t('entityDetail.enrichment.sourceRelations') }}
                <v-chip size="x-small" class="ml-2">{{ sources.relations.count }}</v-chip>
              </span>
              <span v-if="sources.relations.last_updated" class="text-caption text-medium-emphasis ml-2">
                {{ formatDate(sources.relations.last_updated) }}
              </span>
            </div>
          </template>
        </v-checkbox>

        <!-- Documents Source -->
        <v-checkbox
          v-if="sources.documents?.available"
          :model-value="selectedSources"
          value="documents"
          hide-details
          density="compact"
          class="mb-1"
          @update:model-value="handleSourceChange($event)"
        >
          <template #label>
            <div class="d-flex align-center justify-space-between w-100">
              <span class="d-flex align-center">
                <v-icon start size="small" color="orange">mdi-file-document-multiple</v-icon>
                {{ t('entityDetail.enrichment.sourceDocuments') }}
                <v-chip size="x-small" class="ml-2">{{ sources.documents.count }}</v-chip>
              </span>
              <span v-if="sources.documents.last_updated" class="text-caption text-medium-emphasis ml-2">
                {{ formatDate(sources.documents.last_updated) }}
              </span>
            </div>
          </template>
        </v-checkbox>

        <!-- Extractions Source -->
        <v-checkbox
          v-if="sources.extractions?.available"
          :model-value="selectedSources"
          value="extractions"
          hide-details
          density="compact"
          class="mb-1"
          @update:model-value="handleSourceChange($event)"
        >
          <template #label>
            <div class="d-flex align-center justify-space-between w-100">
              <span class="d-flex align-center">
                <v-icon start size="small" color="teal">mdi-brain</v-icon>
                {{ t('entityDetail.enrichment.sourceExtractions') }}
                <v-chip size="x-small" class="ml-2">{{ sources.extractions.count }}</v-chip>
              </span>
              <span v-if="sources.extractions.last_updated" class="text-caption text-medium-emphasis ml-2">
                {{ formatDate(sources.extractions.last_updated) }}
              </span>
            </div>
          </template>
        </v-checkbox>

        <!-- Attachments Source -->
        <v-checkbox
          v-if="sources.attachments?.available"
          :model-value="selectedSources"
          value="attachments"
          hide-details
          density="compact"
          class="mb-1"
          @update:model-value="handleSourceChange($event)"
        >
          <template #label>
            <div class="d-flex align-center justify-space-between w-100">
              <span class="d-flex align-center">
                <v-icon start size="small" color="deep-purple">mdi-paperclip</v-icon>
                {{ t('entityDetail.enrichment.sourceAttachments') }}
                <v-chip size="x-small" class="ml-2">{{ sources.attachments.count }}</v-chip>
              </span>
              <span v-if="sources.attachments.last_updated" class="text-caption text-medium-emphasis ml-2">
                {{ formatDate(sources.attachments.last_updated) }}
              </span>
            </div>
          </template>
        </v-checkbox>

        <!-- No sources available message -->
        <v-alert
          v-if="!hasAnySource"
          type="info"
          variant="tonal"
          density="compact"
        >
          {{ t('entityDetail.enrichment.noSourcesAvailable') }}
        </v-alert>
      </v-card-text>

      <v-card-text v-else class="text-center py-4">
        <v-progress-circular indeterminate size="24"></v-progress-circular>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions class="px-4 py-2">
        <v-chip size="small" variant="tonal">
          {{ t('entityDetail.enrichment.existingFacets', { count: sources?.existing_facets || 0 }) }}
        </v-chip>
        <v-spacer></v-spacer>
        <v-btn
          variant="tonal"
          color="primary"
          :disabled="selectedSources.length === 0"
          :loading="starting"
          @click="$emit('start')"
        >
          <v-icon start>mdi-play</v-icon>
          {{ t('entityDetail.enrichment.startAnalysis') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-menu>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { EnrichmentSources } from '@/composables/facets'
import { useDateFormatter } from '@/composables/useDateFormatter'

const props = defineProps<{
  visible: boolean
  open: boolean
  sources: EnrichmentSources | null
  selectedSources: string[]
  loading: boolean
  starting: boolean
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'update:selectedSources', value: string[]): void
  (e: 'start'): void
}>()

const { t } = useI18n()
const { formatRelativeTime } = useDateFormatter()

const hasAnySource = computed(() => {
  if (!props.sources) return false
  return (
    props.sources.pysis?.available ||
    props.sources.relations?.available ||
    props.sources.documents?.available ||
    props.sources.extractions?.available ||
    props.sources.attachments?.available
  )
})

function formatDate(date: string): string {
  return formatRelativeTime(date)
}

function handleSourceChange(value: string[] | null) {
  emit('update:selectedSources', value || [])
}
</script>
