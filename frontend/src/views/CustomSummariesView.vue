<template>
  <v-container fluid>
    <!-- Header -->
    <PageHeader
      :title="t('summaries.title')"
      :subtitle="t('summaries.subtitle', { count: total })"
      icon="mdi-view-dashboard-variant"
      avatar-color="deep-purple"
    >
      <template #actions>
        <v-btn
          color="primary"
          variant="flat"
          @click="openCreateDialog"
        >
          <v-icon start>mdi-plus</v-icon>
          {{ t('summaries.create') }}
        </v-btn>
      </template>
    </PageHeader>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row align="center">
          <v-col cols="12" md="4">
            <v-text-field
              v-model="searchQuery"
              :label="t('common.search')"
              prepend-inner-icon="mdi-magnify"
              clearable
              hide-details
              @update:model-value="debouncedSearch"
            />
          </v-col>
          <v-col cols="12" md="2">
            <v-select
              v-model="statusFilter"
              :items="statusOptions"
              :label="t('summaries.status')"
              clearable
              hide-details
              @update:model-value="loadSummaries(1)"
            />
          </v-col>
          <v-col cols="12" md="2">
            <v-select
              v-model="sortBy"
              :items="sortOptions"
              :label="t('summaries.sortBy')"
              hide-details
              @update:model-value="loadSummaries(1)"
            >
              <template #item="{ item, props }">
                <v-list-item v-bind="props" :prepend-icon="item.raw.icon" />
              </template>
            </v-select>
          </v-col>
          <v-col cols="auto">
            <v-btn-toggle v-model="favoritesOnly" variant="outlined" divided>
              <v-btn :value="false" size="small">
                <v-icon>mdi-view-grid</v-icon>
              </v-btn>
              <v-btn :value="true" size="small">
                <v-icon color="amber">mdi-star</v-icon>
              </v-btn>
            </v-btn-toggle>
          </v-col>
          <v-spacer />
          <v-col cols="auto">
            <v-btn
              variant="tonal"
              color="primary"
              @click="loadSummaries()"
            >
              <v-icon start>mdi-refresh</v-icon>
              {{ t('common.refresh') }}
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Error State -->
    <v-alert
      v-if="store.error && !isLoading"
      type="error"
      variant="tonal"
      class="mb-4"
      closable
      @click:close="store.error = null"
    >
      <v-alert-title>{{ t('summaries.loadError') }}</v-alert-title>
      <div class="d-flex align-center mt-2">
        <span class="mr-4">{{ store.error }}</span>
        <v-btn
          variant="outlined"
          size="small"
          @click="loadSummaries()"
        >
          <v-icon start>mdi-refresh</v-icon>
          {{ t('common.retry') }}
        </v-btn>
      </div>
    </v-alert>

    <!-- Loading State (initial) - Skeleton Cards -->
    <v-row v-if="isLoading && summaries.length === 0">
      <v-col
        v-for="n in skeletonCount"
        :key="`skeleton-${n}`"
        cols="12"
        md="6"
        lg="4"
      >
        <v-card class="pa-4">
          <div class="d-flex align-center mb-3">
            <v-skeleton-loader type="avatar" class="mr-3" />
            <div class="flex-grow-1">
              <v-skeleton-loader type="text" width="60%" />
              <v-skeleton-loader type="text" width="40%" class="mt-1" />
            </div>
          </div>
          <v-skeleton-loader type="chip, chip" class="mb-3" />
          <v-skeleton-loader type="text" width="80%" />
          <div class="d-flex justify-space-between mt-4">
            <v-skeleton-loader type="button" width="100" />
            <v-skeleton-loader type="button" width="80" />
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Loading Overlay (pagination) -->
    <v-overlay
      v-if="isLoading && summaries.length > 0"
      v-model="isLoading"
      contained
      class="align-center justify-center"
      persistent
    >
      <v-progress-circular indeterminate size="48" color="primary" />
    </v-overlay>

    <!-- Empty State -->
    <v-card v-else-if="summaries.length === 0" class="text-center py-12">
      <v-icon size="80" color="grey-lighten-1" class="mb-4">mdi-view-dashboard-outline</v-icon>
      <div class="text-h5 text-medium-emphasis mb-2">{{ t('summaries.noSummaries') }}</div>
      <div class="text-body-1 text-medium-emphasis mb-6">{{ t('summaries.noSummariesHint') }}</div>
      <v-btn color="primary" size="large" @click="openCreateDialog">
        <v-icon start>mdi-plus</v-icon>
        {{ t('summaries.createFirst') }}
      </v-btn>
    </v-card>

    <!-- Summaries Grid -->
    <v-row v-else>
      <v-col
        v-for="summary in summaries"
        :key="summary.id"
        cols="12"
        md="6"
        lg="4"
      >
        <SummaryCard
          :summary="summary"
          :is-executing="store.isExecutingSummary(summary.id)"
          @click="openSummary(summary)"
          @execute="executeSummary(summary)"
          @toggle-favorite="toggleFavorite(summary)"
          @edit="openEditDialog(summary)"
          @delete="confirmDelete(summary)"
          @share="openShareDialog(summary)"
        />
      </v-col>
    </v-row>

    <!-- Pagination -->
    <v-pagination
      v-if="totalPages > 1"
      v-model="currentPage"
      :length="totalPages"
      class="mt-4"
      @update:model-value="loadSummaries"
    />

    <!-- Create Dialog -->
    <SummaryCreateDialog
      v-model="showCreateDialog"
      @created="onSummaryCreated"
    />

    <!-- Edit Dialog -->
    <SummaryEditDialog
      v-if="editingSummary"
      v-model="showEditDialog"
      :summary="editingSummary"
      @updated="onSummaryUpdated"
    />

    <!-- Share Dialog -->
    <SummaryShareDialog
      v-if="sharingSummary"
      v-model="showShareDialog"
      :summary="sharingSummary"
    />

    <!-- Delete Confirmation -->
    <v-dialog v-model="showDeleteDialog" max-width="400">
      <v-card>
        <v-card-title>{{ t('summaries.deleteConfirm') }}</v-card-title>
        <v-card-text>
          {{ t('summaries.deleteWarning', { name: deletingSummary?.name }) }}
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDeleteDialog = false">
            {{ t('common.cancel') }}
          </v-btn>
          <v-btn
            color="error"
            variant="flat"
            :loading="isDeleting"
            @click="deleteSummary"
          >
            {{ t('common.delete') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useCustomSummariesStore, type CustomSummary } from '@/stores/customSummaries'
import { useSnackbar } from '@/composables/useSnackbar'
import { useDebounce, DEBOUNCE_DELAYS } from '@/composables/useDebounce'
import PageHeader from '@/components/common/PageHeader.vue'
import SummaryCard from '@/components/summaries/SummaryCard.vue'
import SummaryCreateDialog from '@/components/summaries/SummaryCreateDialog.vue'
import SummaryEditDialog from '@/components/summaries/SummaryEditDialog.vue'
import SummaryShareDialog from '@/components/summaries/SummaryShareDialog.vue'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger('CustomSummariesView')

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const store = useCustomSummariesStore()
const { showSuccess, showError } = useSnackbar()

// Responsive state for dynamic skeleton count
const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1200)

function handleResize() {
  windowWidth.value = window.innerWidth
}

// State
const searchQuery = ref('')
const statusFilter = ref<string | null>(null)
const favoritesOnly = ref(false)
const sortBy = ref('updated_at_desc')
const currentPage = ref(1)
const isDeleting = ref(false)

// Dialogs
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const showShareDialog = ref(false)
const showDeleteDialog = ref(false)
const editingSummary = ref<CustomSummary | null>(null)
const sharingSummary = ref<CustomSummary | null>(null)
const deletingSummary = ref<CustomSummary | null>(null)

// Computed
const summaries = computed(() => store.summaries)
const total = computed(() => store.total)
const isLoading = computed(() => store.isLoading)
const totalPages = computed(() => Math.ceil(total.value / store.perPage))

// Dynamic skeleton count based on screen size
// Mobile: 2, Tablet: 4, Desktop: 6
const skeletonCount = computed(() => {
  if (windowWidth.value < 960) return 2  // md breakpoint
  if (windowWidth.value < 1280) return 4 // lg breakpoint
  return 6
})

const statusOptions = [
  { title: t('summaries.statusDraft'), value: 'draft' },
  { title: t('summaries.statusActive'), value: 'active' },
  { title: t('summaries.statusPaused'), value: 'paused' },
  { title: t('summaries.statusArchived'), value: 'archived' },
]

const sortOptions = [
  { title: t('summaries.sortUpdatedDesc'), value: 'updated_at_desc', icon: 'mdi-sort-clock-descending' },
  { title: t('summaries.sortUpdatedAsc'), value: 'updated_at_asc', icon: 'mdi-sort-clock-ascending' },
  { title: t('summaries.sortNameAsc'), value: 'name_asc', icon: 'mdi-sort-alphabetical-ascending' },
  { title: t('summaries.sortNameDesc'), value: 'name_desc', icon: 'mdi-sort-alphabetical-descending' },
  { title: t('summaries.sortExecutions'), value: 'execution_count_desc', icon: 'mdi-chart-line' },
  { title: t('summaries.sortCreatedDesc'), value: 'created_at_desc', icon: 'mdi-calendar-plus' },
]

// Methods
async function loadSummaries(page = currentPage.value) {
  try {
    // Parse sort parameter
    const [sortField, sortOrder] = sortBy.value.split('_').reduce((acc, part, idx, arr) => {
      if (idx === arr.length - 1 && (part === 'asc' || part === 'desc')) {
        return [acc[0], part]
      }
      return [acc[0] ? `${acc[0]}_${part}` : part, acc[1]]
    }, ['', 'desc'] as [string, string])

    await store.loadSummaries({
      page,
      search: searchQuery.value || undefined,
      status: statusFilter.value || undefined,
      favorites_only: favoritesOnly.value || undefined,
      sort_by: sortField || undefined,
      sort_order: sortOrder as 'asc' | 'desc',
    })
    currentPage.value = page
  } catch (e) {
    logger.error('Failed to load summaries:', e)
    showError(t('summaries.loadError'))
  }
}

function openSummary(summary: CustomSummary) {
  router.push({ name: 'summary-dashboard', params: { id: summary.id } })
}

function openCreateDialog() {
  showCreateDialog.value = true
}

function openEditDialog(summary: CustomSummary) {
  editingSummary.value = summary
  showEditDialog.value = true
}

function openShareDialog(summary: CustomSummary) {
  sharingSummary.value = summary
  showShareDialog.value = true
}

function confirmDelete(summary: CustomSummary) {
  deletingSummary.value = summary
  showDeleteDialog.value = true
}

async function deleteSummary() {
  if (!deletingSummary.value) return

  isDeleting.value = true
  try {
    const success = await store.deleteSummary(deletingSummary.value.id)
    if (success) {
      showSuccess(t('summaries.deleted'))
      showDeleteDialog.value = false
      deletingSummary.value = null
    }
  } catch (e) {
    showError(t('summaries.deleteError'))
  } finally {
    isDeleting.value = false
  }
}

async function executeSummary(summary: CustomSummary) {
  try {
    const result = await store.executeSummary(summary.id)
    if (result) {
      showSuccess(result.message)
    }
  } catch (e) {
    showError(t('summaries.executeError'))
  }
}

async function toggleFavorite(summary: CustomSummary) {
  try {
    await store.toggleFavorite(summary.id)
  } catch (e) {
    showError(t('summaries.favoriteError'))
  }
}

function onSummaryCreated(result: { id: string }) {
  showSuccess(t('summaries.created'))
  router.push({ name: 'summary-dashboard', params: { id: result.id } })
}

function onSummaryUpdated() {
  showSuccess(t('summaries.updated'))
  loadSummaries()
}

// Watchers
watch(favoritesOnly, () => loadSummaries(1))

// Debounce search
const { debouncedFn: debouncedSearch } = useDebounce(
  () => loadSummaries(1),
  { delay: DEBOUNCE_DELAYS.SEARCH }
)

// Init
onMounted(() => {
  loadSummaries()
  store.loadSchedulePresets()
  // Listen for window resize for responsive skeleton count
  window.addEventListener('resize', handleResize)

  // Check for create query parameter from MySummaries widget
  if (route.query.create === 'true') {
    showCreateDialog.value = true
  }
})

onUnmounted(() => {
  // Cleanup resize listener
  window.removeEventListener('resize', handleResize)
})
</script>
