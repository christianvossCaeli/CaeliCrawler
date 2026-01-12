<template>
  <div class="result-facets-tab">
    <!-- Header with toggle -->
    <div class="d-flex align-center justify-space-between mb-4">
      <div class="d-flex align-center ga-2">
        <span class="text-h6">{{ $t('results.facets.title') }}</span>
        <v-chip size="small" color="primary" variant="tonal">
          {{ facetCount }}
        </v-chip>
        <v-chip v-if="verifiedCount > 0" size="small" color="success" variant="tonal">
          {{ verifiedCount }} {{ $t('results.facets.verifiedCount') }}
        </v-chip>
      </div>

      <v-checkbox
        v-model="includeInactive"
        :label="$t('results.facets.showInactive')"
        hide-details
        density="compact"
        @update:model-value="loadFacets"
      />
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="d-flex justify-center py-8">
      <v-progress-circular indeterminate color="primary" />
    </div>

    <!-- Error State -->
    <v-alert v-else-if="error" type="error" variant="tonal" class="mb-4">
      {{ error }}
      <template #append>
        <v-btn variant="text" size="small" @click="loadFacets">
          {{ $t('common.retry') }}
        </v-btn>
      </template>
    </v-alert>

    <!-- Empty State -->
    <v-alert v-else-if="facetCount === 0" type="info" variant="tonal">
      <v-icon start>mdi-information-outline</v-icon>
      {{ $t('results.facets.noFacets') }}
    </v-alert>

    <!-- Facet Groups -->
    <template v-else>
      <div v-for="group in groupedFacets" :key="group.facet_type_id" class="mb-6">
        <!-- Group Header -->
        <div class="d-flex align-center ga-2 mb-3">
          <v-icon size="small" color="primary">mdi-tag-multiple</v-icon>
          <span class="font-weight-medium">{{ group.facet_type_name }}</span>
          <v-chip size="x-small" variant="outlined">{{ group.values.length }}</v-chip>
        </div>

        <!-- Facet Items -->
        <ResultFacetItem
          v-for="facet in group.values"
          :key="facet.id"
          :facet="facet"
          :can-edit="canEdit"
          :verifying="actionInProgress === `verify-${facet.id}`"
          :rejecting="actionInProgress === `reject-${facet.id}`"
          :reactivating="actionInProgress === `reactivate-${facet.id}`"
          @verify="handleVerify"
          @reject="handleReject"
          @reactivate="handleReactivate"
        />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, toRef, watch } from 'vue'
import { useResultFacets } from '@/composables/results'
import ResultFacetItem from './ResultFacetItem.vue'

const props = defineProps<{
  extractionId: string | null
  canEdit?: boolean
}>()

// Convert extractionId to ref for composable
const extractionIdRef = toRef(props, 'extractionId')

const {
  loading,
  includeInactive,
  error,
  facetCount,
  verifiedCount,
  groupedFacets,
  loadFacets,
  verifyFacet,
  rejectFacet,
  reactivateFacet,
} = useResultFacets(extractionIdRef)

// Track which action is in progress
const actionInProgress = ref<string | null>(null)

// Load facets when extractionId changes
watch(() => props.extractionId, () => {
  if (props.extractionId) {
    loadFacets()
  }
}, { immediate: true })

// Action handlers with loading state
async function handleVerify(facetId: string): Promise<void> {
  actionInProgress.value = `verify-${facetId}`
  try {
    await verifyFacet(facetId)
  } finally {
    actionInProgress.value = null
  }
}

async function handleReject(facetId: string): Promise<void> {
  actionInProgress.value = `reject-${facetId}`
  try {
    await rejectFacet(facetId)
  } finally {
    actionInProgress.value = null
  }
}

async function handleReactivate(facetId: string): Promise<void> {
  actionInProgress.value = `reactivate-${facetId}`
  try {
    await reactivateFacet(facetId)
  } finally {
    actionInProgress.value = null
  }
}
</script>

<style scoped>
.result-facets-tab {
  min-height: 200px;
}
</style>
