<template>
  <div>
    <!-- Header with Customize Button -->
    <div class="d-flex align-center mb-6">
      <h1 class="text-h4">{{ $t('dashboard.title') }}</h1>
      <v-spacer />
      <v-btn
        variant="tonal"
        :color="dashboardStore.isEditing ? 'warning' : 'default'"
        class="mr-2"
        @click="toggleEditMode"
      >
        <v-icon :icon="dashboardStore.isEditing ? 'mdi-check' : 'mdi-pencil'" class="mr-2" />
        {{ dashboardStore.isEditing ? $t('dashboard.finishEditing') : $t('dashboard.customize') }}
      </v-btn>
      <v-btn
        variant="tonal"
        color="warning"
        @click="showStartCrawlerDialog = true"
      >
        <v-icon icon="mdi-play" class="mr-2" />
        {{ $t('dashboard.quickActions.startCrawler') }}
      </v-btn>
    </div>

    <!-- Crawl Presets Quick Actions -->
    <CrawlPresetQuickActions class="mb-4" />

    <!-- Loading State -->
    <div v-if="dashboardStore.isLoading" class="d-flex justify-center py-12">
      <v-progress-circular indeterminate size="48" color="primary" />
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
    <v-dialog v-model="showStartCrawlerDialog" max-width="650">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">mdi-spider-web</v-icon>
          {{ $t('dashboard.startCrawlerDialog.title') }}
        </v-card-title>
        <v-card-text>
          <!-- Estimated count -->
          <v-alert :type="filteredSourceCount > 100 ? 'warning' : 'info'" class="mb-4">
            <div class="d-flex align-center justify-space-between">
              <span>
                <strong>{{ filteredSourceCount.toLocaleString() }}</strong> {{ $t('dashboard.startCrawlerDialog.sourcesWillBeCrawled') }}
              </span>
              <v-btn
                v-if="hasAnyFilter"
                size="small"
                variant="tonal"
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
            {{ filteredSourceCount.toLocaleString() }} {{ $t('dashboard.startCrawlerDialog.sources') }}
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
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi } from '@/services/api'
import { useDashboardStore } from '@/stores/dashboard'
import DashboardGrid from '@/widgets/DashboardGrid.vue'
import WidgetConfigurator from '@/components/dashboard/WidgetConfigurator.vue'
import CrawlPresetQuickActions from '@/components/crawler/CrawlPresetQuickActions.vue'

const { t } = useI18n()
const dashboardStore = useDashboardStore()

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
const crawlerCategories = ref<any[]>([])
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

let filterTimeout: ReturnType<typeof setTimeout> | null = null
const debouncedUpdateFilteredCount = () => {
  if (filterTimeout) clearTimeout(filterTimeout)
  filterTimeout = setTimeout(() => updateFilteredCount(), 300)
}

const updateFilteredCount = async () => {
  try {
    const params: any = { per_page: 1 }
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
    console.error('Failed to get filtered count:', error)
    filteredSourceCount.value = totalSourceCount.value
  }
}

const startFilteredCrawlers = async () => {
  startingCrawlers.value = true
  try {
    const params: any = {}
    if (crawlerFilter.value.category_id) params.category_id = crawlerFilter.value.category_id
    if (crawlerFilter.value.country) params.country = crawlerFilter.value.country
    if (crawlerFilter.value.search) params.search = crawlerFilter.value.search
    if (crawlerFilter.value.status) params.status = crawlerFilter.value.status
    if (crawlerFilter.value.source_type) params.source_type = crawlerFilter.value.source_type
    if (crawlerFilter.value.limit) params.limit = crawlerFilter.value.limit

    await adminApi.startCrawl(params)
    showStartCrawlerDialog.value = false
    resetCrawlerFilters()

    // Refresh stats
    await dashboardStore.loadStats()
  } catch (error) {
    console.error('Failed to start crawlers:', error)
  } finally {
    startingCrawlers.value = false
  }
}

watch(showStartCrawlerDialog, (isOpen) => {
  if (isOpen) {
    filteredSourceCount.value = totalSourceCount.value
    updateFilteredCount()
  }
})

const loadCategories = async () => {
  try {
    const response = await adminApi.getCategories({ per_page: 100 })
    crawlerCategories.value = response.data.items
  } catch (error) {
    console.error('Failed to load categories:', error)
  }
}

const loadTotalSources = async () => {
  try {
    const response = await adminApi.getSources({ per_page: 1 })
    totalSourceCount.value = response.data.total
    filteredSourceCount.value = response.data.total
  } catch (error) {
    console.error('Failed to load sources count:', error)
  }
}

onMounted(async () => {
  // Initialize dashboard store (loads preferences and stats)
  await dashboardStore.initialize()

  // Load categories for crawler dialog
  loadCategories()
  loadTotalSources()
})

onUnmounted(() => {
  if (filterTimeout) {
    clearTimeout(filterTimeout)
    filterTimeout = null
  }
})
</script>
