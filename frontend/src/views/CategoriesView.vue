<template>
  <div>
    <div class="d-flex justify-space-between align-center mb-6">
      <h1 class="text-h4">{{ $t('categories.title') }} ({{ filteredCategories.length }})</h1>
      <v-btn color="primary" @click="openCreateDialog">
        <v-icon left>mdi-plus</v-icon>{{ $t('categories.actions.create') }}
      </v-btn>
    </div>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row>
          <v-col cols="12" md="4">
            <v-text-field
              v-model="categoryFilters.search"
              :label="$t('categories.filters.search')"
              prepend-inner-icon="mdi-magnify"
              clearable
              hide-details
            ></v-text-field>
          </v-col>
          <v-col cols="12" md="3">
            <v-select
              v-model="categoryFilters.status"
              :items="statusFilterOptions"
              item-title="label"
              item-value="value"
              :label="$t('categories.filters.status')"
              clearable
              hide-details
            ></v-select>
          </v-col>
          <v-col cols="12" md="3">
            <v-select
              v-model="categoryFilters.hasDocuments"
              :items="documentFilterOptions"
              item-title="label"
              item-value="value"
              :label="$t('categories.filters.documents')"
              clearable
              hide-details
            ></v-select>
          </v-col>
          <v-col cols="12" md="2">
            <v-select
              v-model="categoryFilters.language"
              :items="languageFilterOptions"
              item-title="name"
              item-value="code"
              :label="$t('categories.filters.language')"
              clearable
              hide-details
            >
              <template v-slot:item="{ item, props }">
                <v-list-item v-bind="props">
                  <template v-slot:prepend>
                    <span class="mr-2">{{ item.raw.flag }}</span>
                  </template>
                </v-list-item>
              </template>
            </v-select>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Categories List -->
    <v-card>
      <v-data-table
        :headers="headers"
        :items="filteredCategories"
        :loading="loading"
        :items-per-page="20"
      >
        <template v-slot:item.languages="{ item }">
          <span v-for="lang in (item.languages || ['de'])" :key="lang" :title="lang" class="mr-1">
            {{ getLanguageFlag(lang) }}
          </span>
        </template>

        <template v-slot:item.is_active="{ item }">
          <v-chip :color="item.is_active ? 'success' : 'grey'" size="small">
            {{ item.is_active ? $t('categories.statusOptions.active') : $t('categories.statusOptions.inactive') }}
          </v-chip>
        </template>

        <template v-slot:item.source_count="{ item }">
          <v-chip color="primary" size="small">{{ item.source_count }}</v-chip>
        </template>

        <template v-slot:item.document_count="{ item }">
          <v-chip color="info" size="small">{{ item.document_count }}</v-chip>
        </template>

        <template v-slot:item.actions="{ item }">
          <div class="table-actions">
            <v-btn icon="mdi-database-outline" size="small" variant="text" color="primary" @click="showSourcesForCategory(item)" :title="$t('categories.actions.viewSources')"></v-btn>
            <v-btn icon="mdi-pencil" size="small" variant="text" @click="openEditDialog(item)" :title="$t('categories.actions.edit')"></v-btn>
            <v-btn icon="mdi-play" size="small" variant="text" color="success" @click="openCrawlerDialog(item)" :title="$t('categories.actions.startCrawl')"></v-btn>
            <v-btn icon="mdi-refresh" size="small" variant="text" color="warning" @click="confirmReanalyze(item)" :title="$t('categories.actions.reanalyze')"></v-btn>
            <v-btn icon="mdi-delete" size="small" variant="text" color="error" @click="confirmDelete(item)" :title="$t('categories.actions.delete')"></v-btn>
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Create/Edit Dialog -->
    <v-dialog v-model="dialog" max-width="800">
      <v-card>
        <v-card-title>{{ editMode ? $t('categories.dialog.edit') : $t('categories.dialog.create') }}</v-card-title>
        <v-card-text>
          <v-form ref="form">
            <v-text-field
              v-model="formData.name"
              :label="$t('categories.form.name')"
              required
              :rules="[v => !!v || t('categories.form.nameRequired')]"
            ></v-text-field>

            <v-textarea
              v-model="formData.description"
              :label="$t('categories.form.description')"
              rows="2"
            ></v-textarea>

            <v-textarea
              v-model="formData.purpose"
              :label="$t('categories.form.purpose')"
              required
              rows="2"
              :rules="[v => !!v || t('categories.form.purposeRequired')]"
            ></v-textarea>

            <v-combobox
              v-model="formData.search_terms"
              :label="$t('categories.form.searchTerms')"
              chips
              multiple
              :hint="$t('categories.form.searchTermsHint')"
            ></v-combobox>

            <v-combobox
              v-model="formData.document_types"
              :label="$t('categories.form.documentTypes')"
              chips
              multiple
              :hint="$t('categories.form.documentTypesHint')"
            ></v-combobox>

            <v-divider class="my-4"></v-divider>
            <h4 class="mb-2">{{ $t('categories.form.languages') }}</h4>
            <p class="text-caption text-grey mb-2">
              {{ $t('categories.form.languagesDescription') }}
            </p>
            <v-select
              v-model="formData.languages"
              :items="availableLanguages"
              item-title="name"
              item-value="code"
              :label="$t('categories.form.languages')"
              chips
              multiple
              closable-chips
              :hint="$t('categories.form.languagesHint')"
            >
              <template v-slot:chip="{ item, props }">
                <v-chip v-bind="props" color="primary" variant="outlined">
                  <span class="mr-1">{{ item.raw.flag }}</span>
                  {{ item.raw.name }}
                </v-chip>
              </template>
              <template v-slot:item="{ item, props }">
                <v-list-item v-bind="props">
                  <template v-slot:prepend>
                    <span class="mr-2">{{ item.raw.flag }}</span>
                  </template>
                </v-list-item>
              </template>
            </v-select>

            <v-divider class="my-4"></v-divider>
            <h4 class="mb-2">{{ $t('categories.form.urlFiltersTitle') }}</h4>
            <p class="text-caption text-grey mb-2">
              {{ $t('categories.form.urlFiltersDescription') }}
            </p>

            <v-combobox
              v-model="formData.url_include_patterns"
              :label="$t('categories.form.includePatterns')"
              chips
              multiple
              closable-chips
              :hint="$t('categories.form.includeHint')"
              persistent-hint
            >
              <template v-slot:chip="{ item, props }">
                <v-chip v-bind="props" color="success" variant="outlined">
                  <v-icon start size="small">mdi-check</v-icon>
                  {{ item.raw }}
                </v-chip>
              </template>
            </v-combobox>

            <v-combobox
              v-model="formData.url_exclude_patterns"
              :label="$t('categories.form.excludePatterns')"
              chips
              multiple
              closable-chips
              :hint="$t('categories.form.excludeHint')"
              persistent-hint
            >
              <template v-slot:chip="{ item, props }">
                <v-chip v-bind="props" color="error" variant="outlined">
                  <v-icon start size="small">mdi-close</v-icon>
                  {{ item.raw }}
                </v-chip>
              </template>
            </v-combobox>

            <v-alert v-if="!formData.url_include_patterns?.length && !formData.url_exclude_patterns?.length" type="warning" variant="tonal" density="compact" class="mt-2">
              <v-icon start>mdi-alert</v-icon>
              {{ $t('categories.form.noFiltersWarning') }}
            </v-alert>

            <v-divider class="my-4"></v-divider>

            <v-text-field
              v-model="formData.schedule_cron"
              :label="$t('categories.form.scheduleCron')"
              :hint="$t('categories.form.scheduleCronHint')"
            ></v-text-field>

            <v-divider class="my-4"></v-divider>
            <h4 class="mb-2">{{ $t('categories.form.aiPromptTitle') }}</h4>
            <p class="text-caption text-grey mb-2">
              {{ $t('categories.form.aiPromptDescription') }}
            </p>
            <v-textarea
              v-model="formData.ai_extraction_prompt"
              :label="$t('categories.form.aiPrompt')"
              rows="12"
              auto-grow
              variant="outlined"
              :hint="$t('categories.form.aiPromptHint')"
            ></v-textarea>

            <v-switch
              v-model="formData.is_active"
              :label="$t('categories.form.enabled')"
              color="success"
            ></v-switch>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="dialog = false">{{ $t('common.cancel') }}</v-btn>
          <v-btn color="primary" @click="saveCategory">{{ $t('common.save') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title>{{ $t('categories.dialog.delete') }}</v-card-title>
        <v-card-text>
          {{ $t('categories.dialog.deleteConfirm', { name: selectedCategory?.name }) }}
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="deleteDialog = false">{{ $t('common.cancel') }}</v-btn>
          <v-btn color="error" @click="deleteCategory">{{ $t('common.delete') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Reanalyze Confirmation -->
    <v-dialog v-model="reanalyzeDialog" max-width="500">
      <v-card>
        <v-card-title>{{ $t('categories.dialog.reanalyze') }}</v-card-title>
        <v-card-text>
          <p class="mb-4">
            {{ $t('categories.dialog.reanalyzeConfirm', { name: selectedCategory?.name }) }}
          </p>
          <v-switch
            v-model="reanalyzeAll"
            :label="$t('categories.dialog.reanalyzeAll')"
            color="warning"
          ></v-switch>
          <v-alert type="info" variant="tonal" class="mt-2">
            {{ reanalyzeAll ? $t('categories.dialog.reanalyzeAllDocs') : $t('categories.dialog.reanalyzeOnlyLow') }} {{ $t('categories.dialog.reanalyzeInfo') }}
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="reanalyzeDialog = false">{{ $t('common.cancel') }}</v-btn>
          <v-btn color="warning" @click="reanalyzeDocuments">{{ $t('categories.actions.reanalyze') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Sources for Category Dialog -->
    <v-dialog v-model="sourcesDialog" max-width="900">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">mdi-database-outline</v-icon>
          {{ $t('categories.dialog.sourcesFor') }} {{ selectedCategoryForSources?.name }}
          <v-chip color="primary" size="small" class="ml-2">
            {{ categorySources.length }} {{ $t('categories.crawler.sourcesCount') }}
          </v-chip>
        </v-card-title>
        <v-card-text>
          <!-- Category Summary -->
          <v-alert type="info" variant="tonal" density="compact" class="mb-4">
            <div class="text-body-2">{{ selectedCategoryForSources?.purpose }}</div>
          </v-alert>

          <!-- Search -->
          <v-text-field
            v-model="categorySourcesSearch"
            :label="$t('categories.dialog.searchSources')"
            prepend-inner-icon="mdi-magnify"
            variant="outlined"
            density="compact"
            clearable
            class="mb-4"
          ></v-text-field>

          <!-- Sources List -->
          <v-list v-if="filteredCategorySources.length > 0" lines="two" class="sources-list">
            <v-list-item
              v-for="source in filteredCategorySources"
              :key="source.id"
              :title="source.name"
              :subtitle="source.base_url"
            >
              <template v-slot:prepend>
                <v-avatar :color="getStatusColor(source.status)" size="36">
                  <v-icon size="small" color="white">{{ getSourceTypeIcon(source.source_type) }}</v-icon>
                </v-avatar>
              </template>
              <template v-slot:append>
                <div class="d-flex align-center">
                  <v-chip size="x-small" class="mr-2" :color="getStatusColor(source.status)">
                    {{ source.status }}
                  </v-chip>
                  <v-chip size="x-small" color="info" variant="outlined" class="mr-2">
                    {{ source.document_count || 0 }} {{ $t('categories.dialog.docs') }}
                  </v-chip>
                  <v-btn
                    icon="mdi-open-in-new"
                    size="x-small"
                    variant="text"
                    :href="source.base_url"
                    target="_blank"
                    :title="$t('categories.dialog.openUrl')"
                  ></v-btn>
                </div>
              </template>
            </v-list-item>
          </v-list>

          <v-alert v-else type="warning" variant="tonal">
            <span v-if="categorySourcesSearch">{{ $t('categories.dialog.noSourcesSearch') }} "{{ categorySourcesSearch }}"</span>
            <span v-else>{{ $t('categories.dialog.noSources') }}</span>
          </v-alert>

          <!-- Statistics -->
          <v-divider class="my-4"></v-divider>
          <v-row>
            <v-col cols="3">
              <div class="text-center">
                <div class="text-h5 text-primary">{{ categorySourcesStats.total }}</div>
                <div class="text-caption">{{ $t('categories.stats.total') }}</div>
              </div>
            </v-col>
            <v-col cols="3">
              <div class="text-center">
                <div class="text-h5 text-success">{{ categorySourcesStats.active }}</div>
                <div class="text-caption">{{ $t('categories.stats.active') }}</div>
              </div>
            </v-col>
            <v-col cols="3">
              <div class="text-center">
                <div class="text-h5 text-warning">{{ categorySourcesStats.pending }}</div>
                <div class="text-caption">{{ $t('categories.stats.pending') }}</div>
              </div>
            </v-col>
            <v-col cols="3">
              <div class="text-center">
                <div class="text-h5 text-error">{{ categorySourcesStats.error }}</div>
                <div class="text-caption">{{ $t('categories.stats.error') }}</div>
              </div>
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-btn
            color="primary"
            variant="text"
            @click="navigateToSourcesFiltered"
          >
            <v-icon left>mdi-filter</v-icon>{{ $t('categories.dialog.showAllInSourcesView') }}
          </v-btn>
          <v-spacer></v-spacer>
          <v-btn @click="sourcesDialog = false">{{ $t('common.close') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Start Crawler Dialog -->
    <v-dialog v-model="crawlerDialog" max-width="650">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">mdi-spider-web</v-icon>
          {{ $t('categories.crawler.title') }} {{ selectedCategoryForCrawler?.name }}
        </v-card-title>
        <v-card-text>
          <!-- Estimated count -->
          <v-alert :type="crawlerFilteredCount > 100 ? 'warning' : 'info'" class="mb-4">
            <div class="d-flex align-center justify-space-between">
              <span>
                <strong>{{ crawlerFilteredCount.toLocaleString() }}</strong> {{ $t('categories.crawler.estimatedCount') }}
              </span>
              <v-btn
                v-if="hasCrawlerFilter"
                size="small"
                variant="text"
                @click="resetCrawlerFilters"
              >
                {{ $t('categories.crawler.resetFilters') }}
              </v-btn>
            </div>
          </v-alert>

          <v-row>
            <v-col cols="12" md="6">
              <v-text-field
                v-model="crawlerFilter.search"
                :label="$t('categories.crawler.search')"
                prepend-inner-icon="mdi-magnify"
                clearable
                density="comfortable"
                :hint="$t('categories.crawler.searchHint')"
                @update:model-value="debouncedUpdateCrawlerCount"
              ></v-text-field>
            </v-col>
            <v-col cols="12" md="6">
              <v-text-field
                v-model.number="crawlerFilter.limit"
                :label="$t('categories.crawler.maxLimit')"
                type="number"
                :min="1"
                :max="10000"
                prepend-inner-icon="mdi-numeric"
                clearable
                density="comfortable"
                :hint="$t('categories.crawler.limitHint')"
                persistent-hint
                @update:model-value="updateCrawlerFilteredCount"
              ></v-text-field>
            </v-col>
          </v-row>

          <v-row>
            <v-col cols="12" md="6">
              <v-select
                v-model="crawlerFilter.status"
                :items="[
                  { value: 'ACTIVE', label: t('categories.sourceTypes.ACTIVE') },
                  { value: 'PENDING', label: t('categories.sourceTypes.PENDING') },
                  { value: 'ERROR', label: t('categories.sourceTypes.ERROR') },
                ]"
                item-title="label"
                item-value="value"
                :label="$t('categories.filters.status')"
                clearable
                density="comfortable"
                @update:model-value="updateCrawlerFilteredCount"
              ></v-select>
            </v-col>
            <v-col cols="12" md="6">
              <v-select
                v-model="crawlerFilter.source_type"
                :items="[
                  { value: 'WEBSITE', label: t('categories.sourceTypes.WEBSITE') },
                  { value: 'OPARL_API', label: t('categories.sourceTypes.OPARL_API') },
                  { value: 'RSS', label: t('categories.sourceTypes.RSS') },
                ]"
                item-title="label"
                item-value="value"
                :label="$t('categories.crawler.typeFilter')"
                clearable
                density="comfortable"
                @update:model-value="updateCrawlerFilteredCount"
              ></v-select>
            </v-col>
          </v-row>

          <v-divider class="my-4"></v-divider>

          <!-- URL Patterns Info -->
          <v-alert
            v-if="selectedCategoryForCrawler?.url_include_patterns?.length || selectedCategoryForCrawler?.url_exclude_patterns?.length"
            type="success"
            variant="tonal"
            density="compact"
            class="mb-2"
          >
            <v-icon start>mdi-filter-check</v-icon>
            {{ $t('categories.crawler.filterActive') }} {{ selectedCategoryForCrawler?.url_include_patterns?.length || 0 }} {{ $t('categories.crawler.includeCount') }}, {{ selectedCategoryForCrawler?.url_exclude_patterns?.length || 0 }} {{ $t('categories.crawler.excludeCount') }}
          </v-alert>
          <v-alert
            v-else
            type="warning"
            variant="tonal"
            density="compact"
            class="mb-2"
          >
            <v-icon start>mdi-alert</v-icon>
            {{ $t('categories.crawler.noFiltersWarning') }}
          </v-alert>

          <v-alert v-if="crawlerFilteredCount > 500" type="error" variant="tonal" density="compact">
            <v-icon>mdi-alert</v-icon>
            {{ $t('categories.crawler.tooManySources') }}
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-chip size="small" variant="tonal">
            {{ crawlerFilteredCount.toLocaleString() }} {{ $t('categories.crawler.sourcesCount') }}
          </v-chip>
          <v-spacer></v-spacer>
          <v-btn @click="crawlerDialog = false">{{ $t('common.cancel') }}</v-btn>
          <v-btn
            color="warning"
            :loading="startingCrawler"
            :disabled="crawlerFilteredCount === 0"
            @click="startFilteredCrawl"
          >
            <v-icon left>mdi-play</v-icon>{{ $t('categories.crawler.start') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar for feedback -->
    <v-snackbar v-model="snackbar" :color="snackbarColor" timeout="3000">
      {{ snackbarText }}
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { adminApi } from '@/services/api'

const { t } = useI18n()
const router = useRouter()

const loading = ref(false)
const categories = ref<any[]>([])
const dialog = ref(false)
const deleteDialog = ref(false)
const reanalyzeDialog = ref(false)
const sourcesDialog = ref(false)
const reanalyzeAll = ref(false)
const editMode = ref(false)
const selectedCategory = ref<any>(null)
const selectedCategoryForSources = ref<any>(null)
const categorySources = ref<any[]>([])
const categorySourcesSearch = ref('')
const categorySourcesLoading = ref(false)

// Category filters
const categoryFilters = ref({
  search: '',
  status: null as string | null,
  hasDocuments: null as string | null,
  language: null as string | null,
})

const statusFilterOptions = [
  { value: 'active', label: t('categories.statusOptions.active') },
  { value: 'inactive', label: t('categories.statusOptions.inactive') },
]

const documentFilterOptions = [
  { value: 'with', label: t('categories.filters.withDocuments') },
  { value: 'without', label: t('categories.filters.withoutDocuments') },
]

const languageFilterOptions = [
  { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
  { code: 'en', name: 'English', flag: '🇬🇧' },
  { code: 'fr', name: 'Français', flag: '🇫🇷' },
  { code: 'nl', name: 'Nederlands', flag: '🇳🇱' },
  { code: 'it', name: 'Italiano', flag: '🇮🇹' },
  { code: 'es', name: 'Español', flag: '🇪🇸' },
  { code: 'pl', name: 'Polski', flag: '🇵🇱' },
  { code: 'da', name: 'Dansk', flag: '🇩🇰' },
]

// Filtered categories
const filteredCategories = computed(() => {
  let result = categories.value

  // Search filter
  if (categoryFilters.value.search) {
    const search = categoryFilters.value.search.toLowerCase()
    result = result.filter(c =>
      c.name?.toLowerCase().includes(search) ||
      c.purpose?.toLowerCase().includes(search) ||
      c.description?.toLowerCase().includes(search)
    )
  }

  // Status filter
  if (categoryFilters.value.status) {
    const isActive = categoryFilters.value.status === 'active'
    result = result.filter(c => c.is_active === isActive)
  }

  // Documents filter
  if (categoryFilters.value.hasDocuments) {
    if (categoryFilters.value.hasDocuments === 'with') {
      result = result.filter(c => (c.document_count || 0) > 0)
    } else {
      result = result.filter(c => (c.document_count || 0) === 0)
    }
  }

  // Language filter
  if (categoryFilters.value.language) {
    result = result.filter(c =>
      (c.languages || ['de']).includes(categoryFilters.value.language)
    )
  }

  return result
})

// Snackbar
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

// Available languages
const availableLanguages = [
  { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
  { code: 'en', name: 'English', flag: '🇬🇧' },
  { code: 'fr', name: 'Français', flag: '🇫🇷' },
  { code: 'nl', name: 'Nederlands', flag: '🇳🇱' },
  { code: 'it', name: 'Italiano', flag: '🇮🇹' },
  { code: 'es', name: 'Español', flag: '🇪🇸' },
  { code: 'pl', name: 'Polski', flag: '🇵🇱' },
  { code: 'da', name: 'Dansk', flag: '🇩🇰' },
]

const formData = ref({
  name: '',
  description: '',
  purpose: '',
  search_terms: [] as string[],
  document_types: [] as string[],
  languages: ['de'] as string[],
  url_include_patterns: [] as string[],
  url_exclude_patterns: [] as string[],
  schedule_cron: '0 2 * * *',
  ai_extraction_prompt: '',
  is_active: true,
})

const headers = [
  { title: t('categories.columns.name'), key: 'name' },
  { title: t('categories.columns.purpose'), key: 'purpose', maxWidth: '300px' },
  { title: t('categories.columns.languages') },
  { title: t('categories.columns.status'), key: 'is_active' },
  { title: t('categories.columns.sources'), key: 'source_count' },
  { title: t('categories.columns.documents'), key: 'document_count' },
  { title: t('categories.columns.actions'), key: 'actions', sortable: false },
]

// Helper to get language flag
const getLanguageFlag = (code: string): string => {
  const lang = availableLanguages.find(l => l.code === code)
  return lang?.flag || code.toUpperCase()
}

const loadCategories = async () => {
  loading.value = true
  try {
    const response = await adminApi.getCategories({ per_page: 100 })
    categories.value = response.data.items
  } catch (error) {
    console.error('Failed to load categories:', error)
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  editMode.value = false
  formData.value = {
    name: '',
    description: '',
    purpose: '',
    search_terms: [],
    document_types: [],
    languages: ['de'],
    url_include_patterns: [],
    url_exclude_patterns: [],
    schedule_cron: '0 2 * * *',
    ai_extraction_prompt: '',
    is_active: true,
  }
  dialog.value = true
}

const openEditDialog = (category: any) => {
  editMode.value = true
  selectedCategory.value = category
  formData.value = {
    ...category,
    // Ensure arrays are initialized (in case API returns null)
    search_terms: category.search_terms || [],
    document_types: category.document_types || [],
    languages: category.languages || ['de'],
    url_include_patterns: category.url_include_patterns || [],
    url_exclude_patterns: category.url_exclude_patterns || [],
  }
  dialog.value = true
}

const saveCategory = async () => {
  try {
    if (editMode.value) {
      await adminApi.updateCategory(selectedCategory.value.id, formData.value)
    } else {
      await adminApi.createCategory(formData.value)
    }
    dialog.value = false
    loadCategories()
  } catch (error) {
    console.error('Failed to save category:', error)
  }
}

const confirmDelete = (category: any) => {
  selectedCategory.value = category
  deleteDialog.value = true
}

const deleteCategory = async () => {
  try {
    await adminApi.deleteCategory(selectedCategory.value.id)
    deleteDialog.value = false
    loadCategories()
  } catch (error) {
    console.error('Failed to delete category:', error)
  }
}

// Crawler dialog state
const crawlerDialog = ref(false)
const startingCrawler = ref(false)
const selectedCategoryForCrawler = ref<any>(null)
const crawlerFilteredCount = ref(0)
const crawlerFilter = ref({
  search: null as string | null,
  limit: null as number | null,
  status: null as string | null,
  source_type: null as string | null,
})

const hasCrawlerFilter = computed(() => {
  return crawlerFilter.value.search ||
         crawlerFilter.value.status ||
         crawlerFilter.value.source_type
})

const resetCrawlerFilters = () => {
  crawlerFilter.value = {
    search: null,
    limit: null,
    status: null,
    source_type: null,
  }
  updateCrawlerFilteredCount()
}

let crawlerFilterTimeout: ReturnType<typeof setTimeout> | null = null
const debouncedUpdateCrawlerCount = () => {
  if (crawlerFilterTimeout) clearTimeout(crawlerFilterTimeout)
  crawlerFilterTimeout = setTimeout(() => updateCrawlerFilteredCount(), 300)
}

const updateCrawlerFilteredCount = async () => {
  if (!selectedCategoryForCrawler.value) return

  try {
    const params: any = {
      category_id: selectedCategoryForCrawler.value.id,
      per_page: 1,  // We only need the count
    }
    if (crawlerFilter.value.search) params.search = crawlerFilter.value.search
    if (crawlerFilter.value.status) params.status = crawlerFilter.value.status
    if (crawlerFilter.value.source_type) params.source_type = crawlerFilter.value.source_type

    const response = await adminApi.getSources(params)
    let count = response.data.total || 0

    // Apply limit if set
    if (crawlerFilter.value.limit && crawlerFilter.value.limit > 0) {
      count = Math.min(count, crawlerFilter.value.limit)
    }

    crawlerFilteredCount.value = count
  } catch (error) {
    console.error('Failed to get filtered count:', error)
    crawlerFilteredCount.value = selectedCategoryForCrawler.value?.source_count || 0
  }
}

const openCrawlerDialog = (category: any) => {
  selectedCategoryForCrawler.value = category
  crawlerFilter.value = {
    search: null,
    limit: null,
    status: null,
    source_type: null,
  }
  crawlerFilteredCount.value = category.source_count || 0
  crawlerDialog.value = true
  updateCrawlerFilteredCount()
}

const startFilteredCrawl = async () => {
  if (!selectedCategoryForCrawler.value) return

  startingCrawler.value = true
  try {
    const params: any = {
      category_id: selectedCategoryForCrawler.value.id,
    }
    if (crawlerFilter.value.search) params.search = crawlerFilter.value.search
    if (crawlerFilter.value.status) params.status = crawlerFilter.value.status
    if (crawlerFilter.value.source_type) params.source_type = crawlerFilter.value.source_type
    if (crawlerFilter.value.limit) params.limit = crawlerFilter.value.limit

    await adminApi.startCrawl(params)
    crawlerDialog.value = false

    snackbarText.value = t('categories.crawler.started', { count: crawlerFilteredCount.value })
    snackbarColor.value = 'success'
    snackbar.value = true
  } catch (error) {
    console.error('Failed to start crawl:', error)
    snackbarText.value = t('categories.crawler.errorStarting')
    snackbarColor.value = 'error'
    snackbar.value = true
  } finally {
    startingCrawler.value = false
  }
}

// Legacy function - kept for backwards compatibility
const startCrawl = async (category: any) => {
  openCrawlerDialog(category)
}

const confirmReanalyze = (category: any) => {
  selectedCategory.value = category
  reanalyzeAll.value = false
  reanalyzeDialog.value = true
}

const reanalyzeDocuments = async () => {
  try {
    const response = await adminApi.reanalyzeDocuments({
      category_id: selectedCategory.value.id,
      reanalyze_all: reanalyzeAll.value,
    })
    reanalyzeDialog.value = false
    snackbarText.value = response.data.message || t('categories.messages.reanalyzeStarted')
    snackbarColor.value = 'success'
    snackbar.value = true
  } catch (error) {
    console.error('Failed to start reanalysis:', error)
    snackbarText.value = t('categories.messages.reanalyzeError')
    snackbarColor.value = 'error'
    snackbar.value = true
  }
}

// Computed properties for sources dialog
const filteredCategorySources = computed(() => {
  if (!categorySourcesSearch.value) {
    return categorySources.value
  }
  const search = categorySourcesSearch.value.toLowerCase()
  return categorySources.value.filter(s =>
    s.name?.toLowerCase().includes(search) ||
    s.base_url?.toLowerCase().includes(search) ||
    s.location_name?.toLowerCase().includes(search)
  )
})

const categorySourcesStats = computed(() => {
  const sources = categorySources.value
  return {
    total: sources.length,
    active: sources.filter(s => s.status === 'ACTIVE').length,
    pending: sources.filter(s => s.status === 'PENDING').length,
    error: sources.filter(s => s.status === 'ERROR').length,
  }
})

// Helper functions
const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    ACTIVE: 'success',
    PENDING: 'warning',
    ERROR: 'error',
    PAUSED: 'grey',
  }
  return colors[status] || 'grey'
}

const getSourceTypeIcon = (type: string) => {
  const icons: Record<string, string> = {
    WEBSITE: 'mdi-web',
    OPARL_API: 'mdi-api',
    RSS: 'mdi-rss',
    CUSTOM_API: 'mdi-code-json',
  }
  return icons[type] || 'mdi-database'
}

const showSourcesForCategory = async (category: any) => {
  selectedCategoryForSources.value = category
  categorySourcesSearch.value = ''
  categorySources.value = []
  sourcesDialog.value = true
  categorySourcesLoading.value = true

  try {
    const response = await adminApi.getSources({
      category_id: category.id,
      per_page: 10000, // Load all sources for this category (no artificial limit)
    })
    categorySources.value = response.data.items
  } catch (error) {
    console.error('Failed to load sources for category:', error)
    snackbarText.value = t('categories.messages.sourcesLoadError')
    snackbarColor.value = 'error'
    snackbar.value = true
  } finally {
    categorySourcesLoading.value = false
  }
}

const navigateToSourcesFiltered = () => {
  sourcesDialog.value = false
  router.push({
    path: '/sources',
    query: { category_id: selectedCategoryForSources.value?.id }
  })
}

onMounted(() => {
  loadCategories()
})
</script>

<style scoped>
.sources-list {
  max-height: 400px;
  overflow-y: auto;
}
</style>
