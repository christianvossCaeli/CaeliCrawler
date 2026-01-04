<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon :icon="facetGroup.facet_type_icon" :color="facetGroup.facet_type_color" class="mr-2"></v-icon>
      {{ facetGroup.facet_type_name }}
      <v-chip size="small" class="ml-2">{{ facetGroup.value_count }}</v-chip>
      <v-chip v-if="facetGroup.verified_count" size="x-small" color="success" class="ml-1">
        {{ facetGroup.verified_count }} {{ t('entityDetail.verified') }}
      </v-chip>
      <v-spacer></v-spacer>
      <!-- Add Value Button -->
      <v-btn
        v-if="canEdit"
        size="small"
        color="primary"
        variant="tonal"
        class="mr-2"
        @click.stop="$emit('add-value', facetGroup)"
      >
        <v-icon start size="small">mdi-plus</v-icon>
        {{ t('common.add') }}
      </v-btn>
      <v-btn size="small" variant="tonal" @click="$emit('toggle-expand')">
        <v-icon>{{ isExpanded ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
      </v-btn>
    </v-card-title>

    <v-expand-transition>
      <v-card-text v-show="isExpanded">
        <!-- History Facet Type - Show Chart -->
        <template v-if="facetGroup.facet_type_value_type === 'history'">
          <FacetHistoryChart
            :entity-id="entityId"
            :facet-type-id="facetGroup.facet_type_id"
            :facet-type="facetGroup"
            :can-edit="canEdit"
            @updated="$emit('facets-updated')"
          />
        </template>

        <!-- Regular Facet Values List -->
        <div v-else-if="displayedFacets.length" class="mb-4">
          <FacetValueItem
            v-for="(facet, idx) in displayedFacets"
            :key="`${facetGroup.facet_type_id}-${facet.id || idx}`"
            :facet="facet"
            :facet-group="facetGroup"
            :facet-type="facetType"
            :selected-facet-ids="selectedFacetIds"
            :bulk-mode="bulkMode"
            :can-edit="canEdit"
            @toggle-selection="$emit('toggle-selection', $event)"
            @navigate-to-entity="$emit('navigate-to-entity', $event)"
            @open-link-dialog="$emit('open-link-dialog', $event)"
            @unlink-entity="$emit('unlink-entity', $event)"
            @open-source-details="$emit('open-source-details', $event)"
            @verify="$emit('verify', $event)"
            @edit="$emit('edit', $event)"
            @delete="$emit('delete', $event)"
          />
        </div>

        <!-- Load More / Show Less Buttons -->
        <div class="d-flex align-center ga-2 flex-wrap">
          <v-btn
            v-if="canLoadMore"
            variant="tonal"
            size="small"
            :loading="loadingMore"
            @click="$emit('load-more')"
          >
            <v-icon start>mdi-plus</v-icon>
            {{ t('entityDetail.loadMore', { count: remainingCount }) }}
          </v-btn>
          <v-btn
            v-if="isLoadedMore"
            variant="tonal"
            size="small"
            @click="$emit('collapse')"
          >
            <v-icon start>mdi-chevron-up</v-icon>
            {{ t('entityDetail.showLess') }}
          </v-btn>
          <v-spacer></v-spacer>
          <v-btn
            v-if="canEdit && displayedFacets.length > 1"
            variant="tonal"
            size="small"
            @click="$emit('toggle-bulk-mode')"
          >
            <v-icon start>{{ bulkMode ? 'mdi-close' : 'mdi-checkbox-multiple-marked' }}</v-icon>
            {{ bulkMode ? t('common.cancel') : t('entityDetail.multiSelect') }}
          </v-btn>
        </div>

        <!-- Bulk Actions Bar -->
        <BulkActionsBar
          :bulk-mode="bulkMode"
          :selected-count="selectedFacetIds.length"
          :loading="bulkActionLoading"
          @verify="$emit('bulk-verify')"
          @delete="$emit('bulk-delete')"
        />
      </v-card-text>
    </v-expand-transition>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import FacetHistoryChart from '@/components/facets/FacetHistoryChart.vue'
import FacetValueItem from './FacetValueItem.vue'
import BulkActionsBar from './BulkActionsBar.vue'
import { useFacetTypeRenderer } from '@/composables/useFacetTypeRenderer'
import type { FacetValue, FacetGroup } from '@/types/entity'

const props = defineProps<{
  facetGroup: FacetGroup
  entityId: string
  displayedFacets: FacetValue[]
  selectedFacetIds: string[]
  isExpanded: boolean
  bulkMode: boolean
  bulkActionLoading: boolean
  canLoadMore: boolean
  isLoadedMore: boolean
  remainingCount: number
  loadingMore: boolean
  canEdit?: boolean
}>()

defineEmits<{
  (e: 'add-value', group: FacetGroup): void
  (e: 'toggle-expand'): void
  (e: 'toggle-selection', id: string): void
  (e: 'navigate-to-entity', facet: FacetValue): void
  (e: 'open-link-dialog', facet: FacetValue): void
  (e: 'unlink-entity', facet: FacetValue): void
  (e: 'open-source-details', facet: FacetValue): void
  (e: 'verify', id: string): void
  (e: 'edit', facet: FacetValue): void
  (e: 'delete', facet: FacetValue): void
  (e: 'load-more'): void
  (e: 'collapse'): void
  (e: 'toggle-bulk-mode'): void
  (e: 'bulk-verify'): void
  (e: 'bulk-delete'): void
  (e: 'facets-updated'): void
}>()

const { t } = useI18n()
const { facetGroupToFacetType } = useFacetTypeRenderer()

const facetType = computed(() => facetGroupToFacetType(props.facetGroup))
</script>
