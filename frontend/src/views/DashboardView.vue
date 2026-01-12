<template>
  <div>
    <!-- Header with Customize Button -->
    <PageHeader
      :title="$t('dashboard.title')"
      :subtitle="$t('dashboard.subtitle')"
      icon="mdi-view-dashboard"
    >
      <template #actions>
        <v-btn
          variant="tonal"
          :color="dashboardStore.isEditing ? 'warning' : 'default'"
          :aria-label="dashboardStore.isEditing ? $t('dashboard.finishEditing') : $t('dashboard.customize')"
          @click="toggleEditMode"
        >
          <v-icon :icon="dashboardStore.isEditing ? 'mdi-check' : 'mdi-pencil'" class="mr-2" aria-hidden="true" />
          {{ dashboardStore.isEditing ? $t('dashboard.finishEditing') : $t('dashboard.customize') }}
        </v-btn>
        <v-btn
          v-if="canEdit"
          variant="tonal"
          color="warning"
          :aria-label="$t('dashboard.quickActions.startCrawler')"
          @click="showStartCrawlerDialog = true"
        >
          <v-icon icon="mdi-play" class="mr-2" aria-hidden="true" />
          {{ $t('dashboard.quickActions.startCrawler') }}
        </v-btn>
      </template>
    </PageHeader>

    <!-- Info Box -->
    <PageInfoBox :storage-key="INFO_BOX_STORAGE_KEYS.DASHBOARD" :title="$t('dashboard.info.title')">
      {{ $t('dashboard.info.description') }}
    </PageInfoBox>

    <!-- Crawl Presets Quick Actions -->
    <CrawlPresetQuickActions v-if="canEdit" class="mb-4" />

    <!-- Loading State -->
    <div v-if="dashboardStore.isLoading" class="d-flex justify-center py-12" role="status" aria-live="polite">
      <v-progress-circular indeterminate size="48" color="primary" :aria-label="$t('common.loading')" />
    </div>

    <!-- Widget Grid -->
    <DashboardGrid
      v-else
      :widgets="dashboardStore.enabledWidgets"
      :is-editing="dashboardStore.isEditing"
    />

    <!-- Widget Configurator Dialog -->
    <WidgetConfigurator v-model="showConfigurator" />

    <!-- Start Crawler Dialog -->
    <v-dialog v-if="canEdit" v-model="showStartCrawlerDialog" :max-width="DIALOG_SIZES.ML" role="dialog" aria-modal="true">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2" aria-hidden="true">mdi-spider-web</v-icon>
          {{ $t('dashboard.startCrawlerDialog.title') }}
        </v-card-title>
        <v-card-text>
          <!-- Estimated count -->
          <v-alert :type="filteredSourceCount > 100 ? 'warning' : 'info'" class="mb-4">
            <div class="d-flex align-center justify-space-between">
              <span>
                <strong>{{ formatNumber(filteredSourceCount) }}</strong> {{ $t('dashboard.startCrawlerDialog.sourcesWillBeCrawled') }}
              </span>
              <v-btn
                v-if="hasAnyFilter"
                size="small"
                variant="tonal"
                :aria-label="$t('dashboard.startCrawlerDialog.resetFilters')"
                @click="resetCrawlerFilters"
              >
                {{ $t('dashboard.startCrawlerDialog.resetFilters') }}
              </v-btn>
            </div>
          </v-alert>

          <v-row>
            <v-col cols="12" md="6">
              <v-select
                v-model="crawlerFilter.category_id"
                :items="crawlerCategories"
                item-title="name"
                item-value="id"
                :label="$t('dashboard.startCrawlerDialog.category')"
                clearable
                density="comfortable"
                @update:model-value="updateFilteredCount"
              ></v-select>
            </v-col>
            <v-col cols="12" md="6">
              <v-select
                v-model="crawlerFilter.country"
                :items="countryOptions"
                item-title="label"
                item-value="value"
                :label="$t('dashboard.startCrawlerDialog.country')"
                clearable
                density="comfortable"
                @update:model-value="updateFilteredCount"
              ></v-select>
            </v-col>
          </v-row>

          <v-row>
            <v-col cols="12" md="6">
              <v-text-field
                v-model="crawlerFilter.search"
                :label="$t('dashboard.startCrawlerDialog.searchNameUrl')"
                prepend-inner-icon="mdi-magnify"
                clearable
                density="comfortable"
                :hint="$t('dashboard.startCrawlerDialog.filterHint')"
                @update:model-value="debouncedUpdateFilteredCount"
              ></v-text-field>
            </v-col>
            <v-col cols="12" md="6">
              <v-number-input
                v-model="crawlerFilter.limit"
                :label="$t('dashboard.startCrawlerDialog.maxCount')"
                :min="1"
                :max="10000"
                prepend-inner-icon="mdi-numeric"
                clearable
                density="comfortable"
                :hint="$t('dashboard.startCrawlerDialog.emptyAllLabel')"
                persistent-hint
                control-variant="stacked"
              ></v-number-input>
            </v-col>
          </v-row>

          <v-row>
            <v-col cols="12" md="6">
              <v-select
                v-model="crawlerFilter.status"
                :items="[
                  { value: 'ACTIVE', label: t('dashboard.startCrawlerDialog.statusOptions.active') },
                  { value: 'PENDING', label: t('dashboard.startCrawlerDialog.statusOptions.pending') },
                  { value: 'ERROR', label: t('dashboard.startCrawlerDialog.statusOptions.error') },
                ]"
                item-title="label"
                item-value="value"
                :label="$t('dashboard.startCrawlerDialog.status')"
                clearable
                density="comfortable"
                @update:model-value="updateFilteredCount"
              ></v-select>
            </v-col>
            <v-col cols="12" md="6">
              <v-select
                v-model="crawlerFilter.source_type"
                :items="[
                  { value: 'WEBSITE', label: t('dashboard.startCrawlerDialog.sourceTypes.website') },
                  { value: 'OPARL_API', label: t('dashboard.startCrawlerDialog.sourceTypes.oparlApi') },
                  { value: 'RSS', label: t('dashboard.startCrawlerDialog.sourceTypes.rssFeed') },
                ]"
                item-title="label"
                item-value="value"
                :label="$t('dashboard.startCrawlerDialog.sourceType')"
                clearable
                density="comfortable"
                @update:model-value="updateFilteredCount"
              ></v-select>
            </v-col>
          </v-row>

          <v-divider class="my-4"></v-divider>

          <v-alert v-if="filteredSourceCount > 500" type="error" variant="tonal" density="compact">
            <v-icon>mdi-alert</v-icon>
            {{ $t('dashboard.startCrawlerDialog.moreThan500Warning') }}
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-chip size="small" variant="tonal">
            {{ formatNumber(filteredSourceCount) }} {{ $t('dashboard.startCrawlerDialog.sources') }}
          </v-chip>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="showStartCrawlerDialog = false">{{ $t('dashboard.startCrawlerDialog.cancel') }}</v-btn>
          <v-btn
            color="warning"
            :loading="startingCrawlers"
            :disabled="filteredSourceCount === 0"
            @click="startFilteredCrawlers"
          >
            <v-icon left>mdi-play</v-icon>
            {{ $t('dashboard.quickActions.startCrawler') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi } from '@/services/api'
import { useDashboardStore } from '@/stores/dashboard'
import { useAuthStore } from '@/stores/auth'
import { useDebounce, DEBOUNCE_DELAYS } from '@/composables/useDebounce'
import DashboardGrid from '@/widgets/DashboardGrid.vue'
import WidgetConfigurator from '@/components/dashboard/WidgetConfigurator.vue'
import CrawlPresetQuickActions from '@/components/crawler/CrawlPresetQuickActions.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import PageInfoBox from '@/components/common/PageInfoBox.vue'
import { INFO_BOX_STORAGE_KEYS } from '@/config/infoBox'
import { useLogger } from '@/composables/useLogger'
import { useDateFormatter } from '@/composables'
import { emitCrawlerEvent } from '@/composables/useCrawlerEvents'
import { DIALOG_SIZES } from '@/config/ui'
import { usePageContextProvider, PAGE_FEATURES, PAGE_ACTIONS } from '@/composables/usePageContext'
import type { PageContextData } from '@/composables/assistant/types'

const logger = useLogger('DashboardView')

const { t } = useI18n()
const dashboardStore = useDashboardStore()
const auth = useAuthStore()
const { formatNumber } = useDateFormatter()
const canEdit = computed(() => auth.isEditor)

// Page Context Provider for KI-Assistant awareness
usePageContextProvider(
  '/',
  (): PageContextData => ({
    current_route: '/',
    view_mode: 'dashboard',
    widgets: dashboardStore.widgets.map(w => ({
      id: w.id,
      type: w.type,
      title: w.type,
      position: w.position
    })),
    available_features: [...PAGE_FEATURES.summary],
    available_actions: [...PAGE_ACTIONS.base, ...PAGE_ACTIONS.summary]
  })
)

// UI State
const showConfigurator = ref(false)
const showStartCrawlerDialog = ref(false)

// Toggle edit mode
const toggleEditMode = () => {
  if (dashboardStore.isEditing) {
    // Save changes when exiting edit mode
    if (dashboardStore.hasChanges) {
      dashboardStore.savePreferences()
    }
    dashboardStore.setEditMode(false)
  } else {
    showConfigurator.value = true
  }
}

// Crawler dialog state (kept from original)
const startingCrawlers = ref(false)
const crawlerCategories = ref<{ id: string; name: string }[]>([])
const filteredSourceCount = ref(0)
const totalSourceCount = ref(0)
const countryOptions = ref([
  { value: 'DE', label: t('dashboard.countries.germany') },
  { value: 'GB', label: t('dashboard.countries.unitedKingdom') },
])
const crawlerFilter = ref({
  category_id: null as string | null,
  country: null as string | null,
  search: null as string | null,
  limit: null as number | null,
  status: null as string | null,
  source_type: null as string | null,
})

const hasAnyFilter = computed(() => {
  return crawlerFilter.value.category_id ||
         crawlerFilter.value.country ||
         crawlerFilter.value.search ||
         crawlerFilter.value.status ||
         crawlerFilter.value.source_type
})

const resetCrawlerFilters = () => {
  crawlerFilter.value = {
    category_id: null,
    country: null,
    search: null,
    limit: null,
    status: null,
    source_type: null,
  }
  updateFilteredCount()
}

// Debounced filter count update - uses composable with automatic cleanup
const { debouncedFn: debouncedUpdateFilteredCount } = useDebounce(
  () => updateFilteredCount(),
  { delay: DEBOUNCE_DELAYS.SEARCH }
)

const updateFilteredCount = async () => {
  if (!canEdit.value) return
  try {
    const params: Record<string, unknown> = { per_page: 1 }
    if (crawlerFilter.value.category_id) params.category_id = crawlerFilter.value.category_id
    if (crawlerFilter.value.country) params.country = crawlerFilter.value.country
    if (crawlerFilter.value.search) params.search = crawlerFilter.value.search
    if (crawlerFilter.value.status) params.status = crawlerFilter.value.status
    if (crawlerFilter.value.source_type) params.source_type = crawlerFilter.value.source_type

    const response = await adminApi.getSources(params)
    let count = response.data.total || 0

    if (crawlerFilter.value.limit && crawlerFilter.value.limit > 0) {
      count = Math.min(count, crawlerFilter.value.limit)
    }

    filteredSourceCount.value = count
  } catch (error) {
    logger.error('Failed to get filtered count:', error)
    filteredSourceCount.value = totalSourceCount.value
  }
}

const startFilteredCrawlers = async () => {
  if (!canEdit.value) return
  startingCrawlers.value = true
  try {
    const params: Record<string, unknown> = {}
    if (crawlerFilter.value.category_id) params.category_id = crawlerFilter.value.category_id
    if (crawlerFilter.value.country) params.country = crawlerFilter.value.country
    if (crawlerFilter.value.search) params.search = crawlerFilter.value.search
    if (crawlerFilter.value.status) params.status = crawlerFilter.value.status
    if (crawlerFilter.value.source_type) params.source_type = crawlerFilter.value.source_type
    if (crawlerFilter.value.limit) params.limit = crawlerFilter.value.limit

    await adminApi.startCrawl(params)
    showStartCrawlerDialog.value = false
    resetCrawlerFilters()
    // Notify CrawlerView to refresh immediately
    emitCrawlerEvent('crawl-started')

    // Refresh stats
    await dashboardStore.loadStats()
  } catch (error) {
    logger.error('Failed to start crawlers:', error)
  } finally {
    startingCrawlers.value = false
  }
}

watch(showStartCrawlerDialog, (isOpen) => {
  if (!canEdit.value) return
  if (isOpen) {
    filteredSourceCount.value = totalSourceCount.value
    updateFilteredCount()
  }
})

const loadCategories = async () => {
  if (!canEdit.value) return
  try {
    const response = await adminApi.getCategories({ per_page: 100 })
    crawlerCategories.value = response.data.items
  } catch (error) {
    logger.error('Failed to load categories:', error)
  }
}

const loadTotalSources = async () => {
  if (!canEdit.value) return
  try {
    const response = await adminApi.getSourceCounts()
    totalSourceCount.value = response.data.total
    filteredSourceCount.value = response.data.total
  } catch (error) {
    logger.error('Failed to load sources count:', error)
  }
}

onMounted(async () => {
  // Initialize dashboard store (loads preferences and stats)
  await dashboardStore.initialize()

  // Load categories for crawler dialog
  if (canEdit.value) {
    loadCategories()
    loadTotalSources()
  }
})

// useDebounce handles cleanup automatically via its own onUnmounted
</script>
