<template>
  <v-dialog v-model="modelValue" max-width="650">
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2">mdi-spider-web</v-icon>
        {{ t('categories.crawler.title') }} {{ category?.name }}
      </v-card-title>
      <v-card-text>
        <!-- Estimated count -->
        <v-alert :type="filteredCount > 100 ? 'warning' : 'info'" class="mb-4">
          <div class="d-flex align-center justify-space-between">
            <span>
              <strong>{{ filteredCount.toLocaleString() }}</strong> {{ t('categories.crawler.estimatedCount') }}
            </span>
            <v-btn
              v-if="hasFilter"
              size="small"
              variant="tonal"
              @click="$emit('resetFilters')"
            >
              {{ t('categories.crawler.resetFilters') }}
            </v-btn>
          </div>
        </v-alert>

        <v-row>
          <v-col cols="12" md="6">
            <v-text-field
              :model-value="filter.search"
              @update:model-value="$emit('update:filter', { ...filter, search: $event })"
              :label="t('categories.crawler.search')"
              prepend-inner-icon="mdi-magnify"
              clearable
              density="comfortable"
              :hint="t('categories.crawler.searchHint')"
            ></v-text-field>
          </v-col>
          <v-col cols="12" md="6">
            <v-number-input
              :model-value="filter.limit"
              @update:model-value="$emit('update:filter', { ...filter, limit: $event })"
              :label="t('categories.crawler.maxLimit')"
              :min="1"
              :max="10000"
              prepend-inner-icon="mdi-numeric"
              clearable
              density="comfortable"
              :hint="t('categories.crawler.limitHint')"
              persistent-hint
              control-variant="stacked"
            ></v-number-input>
          </v-col>
        </v-row>

        <v-row>
          <v-col cols="12" md="6">
            <v-select
              :model-value="filter.status"
              @update:model-value="$emit('update:filter', { ...filter, status: $event })"
              :items="statusOptions"
              item-title="label"
              item-value="value"
              :label="t('categories.filters.status')"
              clearable
              density="comfortable"
            ></v-select>
          </v-col>
          <v-col cols="12" md="6">
            <v-select
              :model-value="filter.source_type"
              @update:model-value="$emit('update:filter', { ...filter, source_type: $event })"
              :items="sourceTypeOptions"
              item-title="label"
              item-value="value"
              :label="t('categories.crawler.typeFilter')"
              clearable
              density="comfortable"
            ></v-select>
          </v-col>
        </v-row>

        <v-divider class="my-4"></v-divider>

        <!-- URL Patterns Info -->
        <v-alert
          v-if="category?.url_include_patterns?.length || category?.url_exclude_patterns?.length"
          type="success"
          variant="tonal"
          density="compact"
          class="mb-2"
        >
          <v-icon start>mdi-filter-check</v-icon>
          {{ t('categories.crawler.filterActive') }} {{ category?.url_include_patterns?.length || 0 }} {{ t('categories.crawler.includeCount') }}, {{ category?.url_exclude_patterns?.length || 0 }} {{ t('categories.crawler.excludeCount') }}
        </v-alert>
        <v-alert
          v-else
          type="warning"
          variant="tonal"
          density="compact"
          class="mb-2"
        >
          <v-icon start>mdi-alert</v-icon>
          {{ t('categories.crawler.noFiltersWarning') }}
        </v-alert>

        <v-alert v-if="filteredCount > 500" type="error" variant="tonal" density="compact">
          <v-icon>mdi-alert</v-icon>
          {{ t('categories.crawler.tooManySources') }}
        </v-alert>
      </v-card-text>
      <v-card-actions>
        <v-chip size="small" variant="tonal">
          {{ filteredCount.toLocaleString() }} {{ t('categories.crawler.sourcesCount') }}
        </v-chip>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" @click="modelValue = false">{{ t('common.cancel') }}</v-btn>
        <v-btn
          color="warning"
          :loading="starting"
          :disabled="filteredCount === 0"
          @click="$emit('start')"
        >
          <v-icon left>mdi-play</v-icon>{{ t('categories.crawler.start') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

// Types
interface Category {
  id: string
  name: string
  source_count?: number
  url_include_patterns?: string[]
  url_exclude_patterns?: string[]
}

interface CrawlerFilter {
  search: string | null
  limit: number | null
  status: string | null
  source_type: string | null
}

const modelValue = defineModel<boolean>()

// Props
const props = defineProps<{
  category: Category | null
  filter: CrawlerFilter
  filteredCount: number
  starting: boolean
}>()

// Emits
defineEmits<{
  'update:filter': [filter: CrawlerFilter]
  'resetFilters': []
  'start': []
}>()

const { t } = useI18n()

// Computed
const hasFilter = computed(() => {
  return props.filter.search ||
         props.filter.status ||
         props.filter.source_type
})

// Options
const statusOptions = computed(() => [
  { value: 'ACTIVE', label: t('categories.sourceTypes.ACTIVE') },
  { value: 'PENDING', label: t('categories.sourceTypes.PENDING') },
  { value: 'ERROR', label: t('categories.sourceTypes.ERROR') },
])

const sourceTypeOptions = computed(() => [
  { value: 'WEBSITE', label: t('categories.sourceTypes.WEBSITE') },
  { value: 'OPARL_API', label: t('categories.sourceTypes.OPARL_API') },
  { value: 'RSS', label: t('categories.sourceTypes.RSS') },
])
</script>
