<template>
  <div>
    <!-- Loading Overlay for large data loads -->
    <v-overlay :model-value="loading" class="align-center justify-center" persistent scrim="rgba(0,0,0,0.7)">
      <v-card class="pa-8 text-center" min-width="320" elevation="24">
        <v-progress-circular indeterminate size="80" width="6" color="primary" class="mb-4"></v-progress-circular>
        <div class="text-h6 mb-2">{{ $t('sources.loading.title') }}</div>
        <div class="text-body-2 text-grey">
          {{ totalSources > 0 ? `${totalSources.toLocaleString()} ${$t('sources.sources')}` : $t('sources.loading.subtitle') }}
        </div>
      </v-card>
    </v-overlay>

    <div class="d-flex justify-space-between align-center mb-6">
      <h1 class="text-h4">{{ $t('sources.title') }} ({{ totalSources.toLocaleString() }})</h1>
      <div>
        <v-btn color="secondary" class="mr-2" @click="openBulkImportDialog">
          <v-icon left>mdi-upload</v-icon>{{ $t('sources.actions.bulkImport') }}
        </v-btn>
        <v-btn color="primary" @click="openCreateDialog">
          <v-icon left>mdi-plus</v-icon>{{ $t('sources.actions.create') }}
        </v-btn>
      </div>
    </div>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row>
          <v-col cols="12" md="2">
            <v-select
              v-model="filters.country"
              :items="countryOptions"
              item-title="label"
              item-value="value"
              :label="$t('sources.filters.country')"
              clearable
              @update:model-value="onCountryChange"
            >
              <template v-slot:item="{ item, props }">
                <v-list-item v-bind="props">
                  <template v-slot:append>
                    <v-chip size="x-small" variant="tonal">{{ item.raw.count?.toLocaleString() }}</v-chip>
                  </template>
                </v-list-item>
              </template>
            </v-select>
          </v-col>
          <v-col cols="12" md="3">
            <v-autocomplete
              v-model="filters.location_name"
              v-model:search="locationFilterSearch"
              :items="locationFilterItems"
              :loading="locationFilterLoading"
              item-title="name"
              item-value="name"
              :label="$t('sources.filters.municipality')"
              prepend-inner-icon="mdi-map-marker"
              clearable
              no-filter
              @update:model-value="onFilterChange"
            >
              <template v-slot:item="{ item, props }">
                <v-list-item v-bind="props" :title="item.raw.name">
                  <template v-slot:append>
                    <v-chip size="x-small" variant="tonal">{{ item.raw.source_count }}</v-chip>
                  </template>
                </v-list-item>
              </template>
              <template v-slot:no-data>
                <v-list-item v-if="locationFilterSearch && locationFilterSearch.length >= 2">
                  <v-list-item-title>{{ $t('sources.filters.noResults') }} "{{ locationFilterSearch }}"</v-list-item-title>
                </v-list-item>
                <v-list-item v-else>
                  <v-list-item-title>{{ $t('sources.filters.typeToSearch') }}</v-list-item-title>
                </v-list-item>
              </template>
            </v-autocomplete>
          </v-col>
          <v-col cols="12" md="2">
            <v-select
              v-model="filters.category_id"
              :items="categories"
              item-title="name"
              item-value="id"
              :label="$t('sources.filters.category')"
              clearable
              @update:model-value="onFilterChange"
            ></v-select>
          </v-col>
          <v-col cols="12" md="2">
            <v-select
              v-model="filters.status"
              :items="statusOptions"
              :label="$t('sources.filters.status')"
              clearable
              @update:model-value="onFilterChange"
            ></v-select>
          </v-col>
          <v-col cols="12" md="3">
            <v-text-field
              v-model="filters.search"
              :label="$t('sources.filters.search')"
              prepend-inner-icon="mdi-magnify"
              clearable
              @update:model-value="debouncedLoadSources"
            ></v-text-field>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Sources Table -->
    <v-card>
      <v-data-table-server
        :headers="headers"
        :items="sources"
        :items-length="totalSources"
        :loading="loading"
        :items-per-page="itemsPerPage"
        :page="currentPage"
        @update:options="onTableOptionsUpdate"
      >
        <template v-slot:item.categories="{ item }">
          <div class="d-flex flex-wrap gap-1">
            <v-chip
              v-for="cat in (item.categories || [])"
              :key="cat.id"
              :color="cat.is_primary ? 'primary' : 'default'"
              size="x-small"
              variant="tonal"
            >
              {{ cat.name }}
              <v-icon v-if="cat.is_primary" end size="x-small">mdi-star</v-icon>
            </v-chip>
            <v-chip v-if="!item.categories?.length && item.category_name" size="x-small" variant="tonal">
              {{ item.category_name }}
            </v-chip>
          </div>
        </template>

        <template v-slot:item.source_type="{ item }">
          <v-chip :color="getTypeColor(item.source_type)" size="small">
            {{ item.source_type }}
          </v-chip>
        </template>

        <template v-slot:item.status="{ item }">
          <v-chip :color="getStatusColor(item.status)" size="small">
            {{ item.status }}
          </v-chip>
        </template>

        <template v-slot:item.last_crawl="{ item }">
          {{ item.last_crawl ? formatDate(item.last_crawl) : $t('sources.never') }}
        </template>

        <template v-slot:item.actions="{ item }">
          <div class="table-actions d-flex justify-end ga-1">
            <v-btn icon="mdi-pencil" size="small" variant="tonal" :title="$t('common.edit')" @click="openEditDialog(item)"></v-btn>
            <v-btn icon="mdi-play" size="small" variant="tonal" color="success" :title="$t('sources.actions.startCrawl')" @click="startCrawl(item)"></v-btn>
            <v-btn v-if="item.status === 'ERROR'" icon="mdi-refresh" size="small" variant="tonal" color="warning" :title="$t('sources.actions.reset')" @click="resetSource(item)"></v-btn>
            <v-btn icon="mdi-delete" size="small" variant="tonal" color="error" :title="$t('common.delete')" @click="confirmDelete(item)"></v-btn>
          </div>
        </template>
      </v-data-table-server>
    </v-card>

    <!-- Create/Edit Dialog -->
    <v-dialog v-model="dialog" max-width="900" persistent scrollable>
      <v-card>
        <v-card-title class="d-flex align-center pa-4 bg-primary">
          <v-avatar color="rgba(255,255,255,0.2)" size="40" class="mr-3">
            <v-icon color="white">{{ editMode ? 'mdi-database-edit' : 'mdi-database-plus' }}</v-icon>
          </v-avatar>
          <div>
            <div class="text-h6">{{ editMode ? $t('sources.dialog.edit') : $t('sources.dialog.create') }}</div>
            <div v-if="formData.name" class="text-caption opacity-80">{{ formData.name }}</div>
          </div>
        </v-card-title>

        <v-tabs v-model="sourceTab" class="dialog-tabs">
          <v-tab value="general">
            <v-icon start>mdi-form-textbox</v-icon>
            {{ $t('sources.tabs.general') }}
          </v-tab>
          <v-tab value="location">
            <v-icon start>mdi-map-marker</v-icon>
            {{ $t('sources.tabs.location') }}
          </v-tab>
          <v-tab value="crawl">
            <v-icon start>mdi-cog</v-icon>
            {{ $t('sources.tabs.crawl') }}
          </v-tab>
        </v-tabs>

        <v-card-text class="pa-6" style="min-height: 400px;">
          <v-form ref="form">
            <v-window v-model="sourceTab">
              <!-- General Tab -->
              <v-window-item value="general">
                <v-row>
                  <v-col cols="12" md="8">
                    <v-text-field
                      v-model="formData.name"
                      :label="$t('sources.form.name')"
                      required
                      variant="outlined"
                      prepend-inner-icon="mdi-database"
                    ></v-text-field>
                  </v-col>
                  <v-col cols="12" md="4">
                    <v-select
                      v-model="formData.source_type"
                      :items="sourceTypeOptions"
                      item-title="label"
                      item-value="value"
                      :label="$t('sources.form.sourceType')"
                      required
                      variant="outlined"
                    >
                      <template v-slot:item="{ item, props }">
                        <v-list-item v-bind="props">
                          <template v-slot:prepend>
                            <v-icon :color="getTypeColor(item.raw.value)">{{ item.raw.icon }}</v-icon>
                          </template>
                        </v-list-item>
                      </template>
                    </v-select>
                  </v-col>
                </v-row>

                <v-text-field
                  v-model="formData.base_url"
                  :label="$t('sources.form.baseUrl')"
                  required
                  variant="outlined"
                  :hint="$t('sources.form.baseUrlHint')"
                  persistent-hint
                  prepend-inner-icon="mdi-link"
                ></v-text-field>

                <v-text-field
                  v-model="formData.api_endpoint"
                  :label="$t('sources.form.apiEndpoint')"
                  v-if="formData.source_type === 'OPARL_API' || formData.source_type === 'CUSTOM_API'"
                  variant="outlined"
                  prepend-inner-icon="mdi-api"
                  class="mt-3"
                ></v-text-field>

                <v-card variant="outlined" class="mt-4">
                  <v-card-title class="text-subtitle-2 pb-2">
                    <v-icon start size="small">mdi-folder-multiple</v-icon>
                    {{ $t('sources.form.categories') }}
                  </v-card-title>
                  <v-card-text>
                    <p class="text-caption text-medium-emphasis mb-3">{{ $t('sources.form.categoriesHint') }}</p>
                    <div class="d-flex align-center">
                      <v-select
                        v-model="formData.category_ids"
                        :items="categories"
                        item-title="name"
                        item-value="id"
                        multiple
                        chips
                        closable-chips
                        class="flex-grow-1"
                        variant="outlined"
                        density="comfortable"
                      >
                        <template v-slot:chip="{ item, index }">
                          <v-chip
                            :color="index === 0 ? 'primary' : 'default'"
                            closable
                            @click:close="formData.category_ids.splice(index, 1)"
                          >
                            {{ item.title }}
                            <v-icon v-if="index === 0" end size="x-small">mdi-star</v-icon>
                          </v-chip>
                        </template>
                      </v-select>
                      <v-btn
                        icon="mdi-information-outline"
                        variant="tonal"
                        color="primary"
                        size="small"
                        class="ml-2"
                        :disabled="formData.category_ids.length === 0"
                        @click="showCategoryInfo(formData.category_ids[0])"
                        :title="$t('sources.form.primaryCategory')"
                      ></v-btn>
                    </div>
                  </v-card-text>
                </v-card>
              </v-window-item>

              <!-- Location Tab -->
              <v-window-item value="location">
                <v-alert type="info" variant="tonal" class="mb-4">
                  {{ $t('sources.form.locationInfo') }}
                </v-alert>

                <v-row>
                  <v-col cols="12" md="4">
                    <v-select
                      v-model="formData.country"
                      :items="countryOptions"
                      item-title="label"
                      item-value="value"
                      :label="$t('sources.filters.country')"
                      variant="outlined"
                      prepend-inner-icon="mdi-flag"
                    ></v-select>
                  </v-col>
                  <v-col cols="12" md="8">
                    <v-autocomplete
                      v-model="selectedLocation"
                      v-model:search="locationSearch"
                      :items="locationItems"
                      :loading="locationLoading"
                      item-title="name"
                      item-value="id"
                      return-object
                      :label="$t('sources.form.location')"
                      :hint="$t('sources.form.locationHint')"
                      persistent-hint
                      clearable
                      no-filter
                      variant="outlined"
                      prepend-inner-icon="mdi-map-marker"
                      @update:model-value="(val: any) => {
                        formData.location_id = val?.id || null
                        formData.location_name = val?.name || ''
                        formData.admin_level_1 = val?.admin_level_1 || ''
                      }"
                    >
                      <template v-slot:item="{ item, props }">
                        <v-list-item v-bind="props" :title="item.raw.name" :subtitle="`${item.raw.admin_level_1 || ''} ${item.raw.admin_level_2 ? '• ' + item.raw.admin_level_2 : ''}`"></v-list-item>
                      </template>
                      <template v-slot:no-data>
                        <v-list-item>
                          <v-list-item-title>
                            {{ locationSearch?.length >= 2 ? $t('sources.filters.noLocations') : $t('sources.filters.minChars') }}
                          </v-list-item-title>
                        </v-list-item>
                      </template>
                    </v-autocomplete>
                  </v-col>
                </v-row>

                <v-card v-if="selectedLocation" variant="tonal" color="success" class="mt-4">
                  <v-card-text class="d-flex align-center">
                    <v-icon color="success" class="mr-3">mdi-check-circle</v-icon>
                    <div>
                      <div class="font-weight-medium">{{ selectedLocation.name }}</div>
                      <div class="text-caption">{{ selectedLocation.admin_level_1 }}</div>
                    </div>
                  </v-card-text>
                </v-card>
              </v-window-item>

              <!-- Crawl Settings Tab -->
              <v-window-item value="crawl">
                <v-row>
                  <v-col cols="12" md="6">
                    <v-number-input
                      v-model="formData.crawl_config.max_depth"
                      :label="$t('sources.form.maxDepth')"
                      :min="1"
                      :max="10"
                      variant="outlined"
                      :hint="$t('sources.form.maxDepthHint')"
                      persistent-hint
                      prepend-inner-icon="mdi-arrow-expand-down"
                      control-variant="stacked"
                    ></v-number-input>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-number-input
                      v-model="formData.crawl_config.max_pages"
                      :label="$t('sources.form.maxPages')"
                      :min="1"
                      :max="10000"
                      variant="outlined"
                      :hint="$t('sources.form.maxPagesHint')"
                      persistent-hint
                      prepend-inner-icon="mdi-file-multiple"
                      control-variant="stacked"
                    ></v-number-input>
                  </v-col>
                </v-row>

                <v-card variant="outlined" class="mt-4 pa-3">
                  <div class="d-flex align-center justify-space-between">
                    <div>
                      <div class="text-body-2 font-weight-medium">{{ $t('sources.form.renderJs') }}</div>
                      <div class="text-caption text-medium-emphasis">{{ $t('sources.form.renderJsHint') }}</div>
                    </div>
                    <v-switch
                      v-model="formData.crawl_config.render_javascript"
                      color="primary"
                      hide-details
                    ></v-switch>
                  </div>
                </v-card>

                <v-divider class="my-6"></v-divider>

                <div class="text-subtitle-2 mb-4">
                  <v-icon start size="small">mdi-filter</v-icon>
                  {{ $t('sources.form.urlFilters') }}
                </div>

                <v-card variant="outlined" color="success" class="mb-4">
                  <v-card-title class="text-subtitle-2 pb-2">
                    <v-icon start size="small" color="success">mdi-check-circle</v-icon>
                    {{ $t('sources.form.includePatterns') }}
                  </v-card-title>
                  <v-card-text>
                    <v-combobox
                      v-model="formData.crawl_config.url_include_patterns"
                      :hint="$t('sources.form.includeHint')"
                      persistent-hint
                      multiple
                      chips
                      closable-chips
                      clearable
                      variant="outlined"
                      density="comfortable"
                    >
                      <template v-slot:chip="{ item, props }">
                        <v-chip v-bind="props" color="success" variant="tonal">
                          <v-icon start size="small">mdi-check</v-icon>
                          {{ item.raw }}
                        </v-chip>
                      </template>
                    </v-combobox>
                  </v-card-text>
                </v-card>

                <v-card variant="outlined" color="error">
                  <v-card-title class="text-subtitle-2 pb-2">
                    <v-icon start size="small" color="error">mdi-close-circle</v-icon>
                    {{ $t('sources.form.excludePatterns') }}
                  </v-card-title>
                  <v-card-text>
                    <v-combobox
                      v-model="formData.crawl_config.url_exclude_patterns"
                      :hint="$t('sources.form.excludeHint')"
                      persistent-hint
                      multiple
                      chips
                      closable-chips
                      clearable
                      variant="outlined"
                      density="comfortable"
                    >
                      <template v-slot:chip="{ item, props }">
                        <v-chip v-bind="props" color="error" variant="tonal">
                          <v-icon start size="small">mdi-close</v-icon>
                          {{ item.raw }}
                        </v-chip>
                      </template>
                    </v-combobox>
                  </v-card-text>
                </v-card>
              </v-window-item>
            </v-window>
          </v-form>
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions class="pa-4">
          <v-btn variant="text" @click="dialog = false">{{ $t('common.cancel') }}</v-btn>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="saveSource">
            <v-icon start>mdi-check</v-icon>
            {{ $t('common.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Bulk Import Dialog -->
    <v-dialog v-model="bulkDialog" max-width="600">
      <v-card>
        <v-card-title>{{ $t('sources.dialog.bulkImport') }}</v-card-title>
        <v-card-text>
          <v-select
            v-model="bulkImport.category_id"
            :items="categories"
            item-title="name"
            item-value="id"
            :label="$t('sources.filters.category')"
            required
          ></v-select>

          <v-textarea
            v-model="bulkImport.urls"
            :label="$t('sources.form.urls')"
            rows="10"
            :hint="$t('sources.form.urlsFormat')"
          ></v-textarea>

          <v-switch
            v-model="bulkImport.skip_duplicates"
            :label="$t('sources.form.skipDuplicates')"
          ></v-switch>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="bulkDialog = false">{{ $t('common.cancel') }}</v-btn>
          <v-btn color="primary" @click="executeBulkImport">{{ $t('common.import') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Dialog -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title>{{ $t('sources.dialog.delete') }}</v-card-title>
        <v-card-text>
          {{ $t('sources.dialog.deleteConfirm', { name: selectedSource?.name }) }}
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="deleteDialog = false">{{ $t('common.cancel') }}</v-btn>
          <v-btn color="error" @click="deleteSource">{{ $t('common.delete') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Category Info Dialog -->
    <v-dialog v-model="categoryInfoDialog" max-width="700">
      <v-card v-if="selectedCategoryInfo">
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">mdi-folder-outline</v-icon>
          {{ selectedCategoryInfo.name }}
          <v-chip :color="selectedCategoryInfo.is_active ? 'success' : 'grey'" size="small" class="ml-2">
            {{ selectedCategoryInfo.is_active ? t('sources.dialog.active') : t('sources.dialog.inactive') }}
          </v-chip>
        </v-card-title>
        <v-card-text>
          <!-- Purpose -->
          <div class="mb-4">
            <div class="text-overline text-grey">{{ $t('sources.dialog.purpose') }}</div>
            <div class="text-body-1">{{ selectedCategoryInfo.purpose || $t('sources.dialog.noPurpose') }}</div>
          </div>

          <!-- Description -->
          <div class="mb-4" v-if="selectedCategoryInfo.description">
            <div class="text-overline text-grey">{{ $t('common.description') }}</div>
            <div class="text-body-2">{{ selectedCategoryInfo.description }}</div>
          </div>

          <!-- Statistics -->
          <v-row class="mb-4">
            <v-col cols="4">
              <v-card variant="tonal" color="primary" class="pa-3 text-center">
                <div class="text-h5">{{ selectedCategoryInfo.source_count || 0 }}</div>
                <div class="text-caption">{{ $t('sources.dialog.dataSources') }}</div>
              </v-card>
            </v-col>
            <v-col cols="4">
              <v-card variant="tonal" color="info" class="pa-3 text-center">
                <div class="text-h5">{{ selectedCategoryInfo.document_count || 0 }}</div>
                <div class="text-caption">{{ $t('sources.columns.documents') }}</div>
              </v-card>
            </v-col>
            <v-col cols="4">
              <v-card variant="tonal" color="secondary" class="pa-3 text-center">
                <div class="text-h5">
                  <span v-for="lang in (selectedCategoryInfo.languages || ['de'])" :key="lang" class="mr-1">
                    {{ getLanguageFlag(lang) }}
                  </span>
                </div>
                <div class="text-caption">{{ $t('sources.dialog.languages') }}</div>
              </v-card>
            </v-col>
          </v-row>

          <!-- Search Terms -->
          <div class="mb-4" v-if="selectedCategoryInfo.search_terms?.length">
            <div class="text-overline text-grey">{{ $t('sources.dialog.searchTerms') }}</div>
            <div>
              <v-chip v-for="term in selectedCategoryInfo.search_terms" :key="term" size="small" class="mr-1 mb-1" color="primary" variant="outlined">
                {{ term }}
              </v-chip>
            </div>
          </div>

          <!-- Document Types -->
          <div class="mb-4" v-if="selectedCategoryInfo.document_types?.length">
            <div class="text-overline text-grey">{{ $t('sources.dialog.documentTypes') }}</div>
            <div>
              <v-chip v-for="type in selectedCategoryInfo.document_types" :key="type" size="small" class="mr-1 mb-1" color="secondary" variant="outlined">
                {{ type }}
              </v-chip>
            </div>
          </div>

          <!-- URL Patterns -->
          <v-expansion-panels variant="accordion" class="mb-4" v-if="selectedCategoryInfo.url_include_patterns?.length || selectedCategoryInfo.url_exclude_patterns?.length">
            <v-expansion-panel>
              <v-expansion-panel-title>
                <v-icon size="small" class="mr-2">mdi-filter</v-icon>{{ $t('sources.dialog.urlPatterns') }}
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div v-if="selectedCategoryInfo.url_include_patterns?.length" class="mb-3">
                  <div class="text-caption text-grey mb-1">{{ $t('sources.dialog.includePatterns') }}</div>
                  <v-chip v-for="p in selectedCategoryInfo.url_include_patterns" :key="p" size="small" class="mr-1 mb-1" color="success" variant="outlined">
                    <v-icon start size="x-small">mdi-check</v-icon>{{ p }}
                  </v-chip>
                </div>
                <div v-if="selectedCategoryInfo.url_exclude_patterns?.length">
                  <div class="text-caption text-grey mb-1">{{ $t('sources.dialog.excludePatterns') }}</div>
                  <v-chip v-for="p in selectedCategoryInfo.url_exclude_patterns" :key="p" size="small" class="mr-1 mb-1" color="error" variant="outlined">
                    <v-icon start size="x-small">mdi-close</v-icon>{{ p }}
                  </v-chip>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>

          <!-- AI Extraction Prompt Preview -->
          <v-expansion-panels variant="accordion" v-if="selectedCategoryInfo.ai_extraction_prompt">
            <v-expansion-panel>
              <v-expansion-panel-title>
                <v-icon size="small" class="mr-2">mdi-robot</v-icon>{{ $t('sources.dialog.aiPrompt') }}
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <pre class="text-caption" style="white-space: pre-wrap; max-height: 300px; overflow-y: auto;">{{ selectedCategoryInfo.ai_extraction_prompt }}</pre>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="categoryInfoDialog = false">{{ $t('common.close') }}</v-btn>
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
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { adminApi, locationApi } from '@/services/api'
import { format } from 'date-fns'
import { de } from 'date-fns/locale'

const { t } = useI18n()
const route = useRoute()

const loading = ref(false)
const sources = ref<any[]>([])
const totalSources = ref(0)
const currentPage = ref(1)
const itemsPerPage = ref(50)
const categories = ref<any[]>([])
const dialog = ref(false)
const sourceTab = ref('general')

const sourceTypeOptions = [
  { value: 'WEBSITE', label: 'Website', icon: 'mdi-web' },
  { value: 'OPARL_API', label: 'OParl API', icon: 'mdi-api' },
  { value: 'RSS', label: 'RSS Feed', icon: 'mdi-rss' },
  { value: 'CUSTOM_API', label: 'Custom API', icon: 'mdi-code-json' },
]
const bulkDialog = ref(false)
const deleteDialog = ref(false)
const categoryInfoDialog = ref(false)
const editMode = ref(false)
const selectedSource = ref<any>(null)
const selectedCategoryInfo = ref<any>(null)

// Language flag helper
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

const getLanguageFlag = (code: string): string => {
  const lang = availableLanguages.find(l => l.code === code)
  return lang?.flag || code.toUpperCase()
}

const showCategoryInfo = (categoryId: string) => {
  const category = categories.value.find(c => c.id === categoryId)
  if (category) {
    selectedCategoryInfo.value = category
    categoryInfoDialog.value = true
  }
}

// Snackbar
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

// Country options (dynamically loaded - only countries with data sources)
const countryOptions = ref<{ value: string, label: string, count: number }[]>([])

const loadCountries = async () => {
  try {
    const response = await adminApi.getSourceCountries()
    countryOptions.value = response.data.map((c: any) => ({
      value: c.code,
      label: `${c.name}`,
      count: c.source_count,
    }))
  } catch (e) {
    console.error('Failed to load countries:', e)
    // Fallback
    countryOptions.value = [
      { value: 'DE', label: t('sources.fallback.germany'), count: 0 },
    ]
  }
}

// Location filter autocomplete
const locationFilterSearch = ref('')
const locationFilterItems = ref<any[]>([])
const locationFilterLoading = ref(false)
let locationFilterTimeout: ReturnType<typeof setTimeout> | null = null

const searchLocationFilter = async (search: string) => {
  if (!search || search.length < 2) {
    // Load top locations when no search
    locationFilterLoading.value = true
    try {
      const response = await adminApi.getSourceLocations({
        country: filters.value.country || undefined,
        limit: 50,
      })
      locationFilterItems.value = response.data
    } catch (e) {
      console.error('Location filter search failed:', e)
    } finally {
      locationFilterLoading.value = false
    }
    return
  }

  locationFilterLoading.value = true
  try {
    const response = await adminApi.getSourceLocations({
      country: filters.value.country || undefined,
      search,
      limit: 50,
    })
    locationFilterItems.value = response.data
  } catch (e) {
    console.error('Location filter search failed:', e)
  } finally {
    locationFilterLoading.value = false
  }
}

watch(locationFilterSearch, (val) => {
  if (locationFilterTimeout) clearTimeout(locationFilterTimeout)
  locationFilterTimeout = setTimeout(() => searchLocationFilter(val || ''), 300)
})

const onCountryChange = () => {
  // Clear location filter when country changes
  filters.value.location_name = null
  locationFilterItems.value = []
  // Reload locations for new country
  searchLocationFilter('')
  // Reset to page 1 and reload
  currentPage.value = 1
  loadSources(1)
}

// Filter change handler - resets to page 1
const onFilterChange = () => {
  currentPage.value = 1
  loadSources(1)
}

// Debounced search
let searchTimeout: ReturnType<typeof setTimeout> | null = null
const debouncedLoadSources = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    loadSources(1)
  }, 300)
}

// Location autocomplete
const locationSearch = ref('')
const locationItems = ref<any[]>([])
const locationLoading = ref(false)
const selectedLocation = ref<any>(null)

const searchLocations = async (search: string) => {
  if (!search || search.length < 2) {
    locationItems.value = []
    return
  }
  locationLoading.value = true
  try {
    const response = await locationApi.search(search, { country: filters.value.country ?? undefined })
    locationItems.value = response.data.items
  } catch (e) {
    console.error('Location search failed:', e)
  } finally {
    locationLoading.value = false
  }
}

watch(locationSearch, (val) => {
  if (val) searchLocations(val)
})

const filters = ref({
  country: null as string | null,
  category_id: null as string | null,
  status: null as string | null,
  search: '',
  location_name: null as string | null,
})

const statusOptions = ['PENDING', 'ACTIVE', 'PAUSED', 'ERROR']

const formData = ref({
  category_id: '',  // Legacy - primary category
  category_ids: [] as string[],  // N:M categories
  name: '',
  source_type: 'WEBSITE',
  base_url: '',
  api_endpoint: '',
  country: 'DE',
  location_id: null as string | null,
  location_name: '',
  admin_level_1: '',
  crawl_config: {
    max_depth: 3,
    max_pages: 100,
    render_javascript: false,
    url_include_patterns: [] as string[],
    url_exclude_patterns: [] as string[],
  },
})

const bulkImport = ref({
  category_id: '',
  urls: '',
  skip_duplicates: true,
})

const headers = [
  { title: t('sources.columns.name'), key: 'name' },
  { title: t('sources.columns.categories'), key: 'categories' },
  { title: t('sources.columns.type'), key: 'source_type' },
  { title: t('sources.columns.status'), key: 'status' },
  { title: t('sources.columns.lastCrawl'), key: 'last_crawl' },
  { title: t('sources.columns.documents'), key: 'document_count' },
  { title: t('sources.columns.actions'), key: 'actions', sortable: false, align: 'end' as const },
]

const getTypeColor = (type: string) => {
  const colors: Record<string, string> = {
    WEBSITE: 'primary',
    OPARL_API: 'success',
    RSS: 'info',
    CUSTOM_API: 'warning',
  }
  return colors[type] || 'grey'
}

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    ACTIVE: 'success',
    PENDING: 'warning',
    ERROR: 'error',
    PAUSED: 'grey',
  }
  return colors[status] || 'grey'
}

const formatDate = (dateStr: string) => {
  return format(new Date(dateStr), 'dd.MM.yyyy HH:mm', { locale: de })
}

const loadCategories = async () => {
  const response = await adminApi.getCategories({ per_page: 100 })
  categories.value = response.data.items
}

const loadSources = async (page = 1, perPage = itemsPerPage.value) => {
  loading.value = true
  try {
    const response = await adminApi.getSources({
      ...filters.value,
      page,
      per_page: perPage,
    })
    sources.value = response.data.items
    totalSources.value = response.data.total
    currentPage.value = page
    console.log(`Loaded ${sources.value.length} of ${totalSources.value} sources (page ${page})`)
  } finally {
    loading.value = false
  }
}

const onTableOptionsUpdate = (options: { page: number, itemsPerPage: number }) => {
  if (options.itemsPerPage !== itemsPerPage.value) {
    itemsPerPage.value = options.itemsPerPage
  }
  loadSources(options.page, options.itemsPerPage)
}

const openCreateDialog = () => {
  editMode.value = false
  formData.value = {
    category_id: '',
    category_ids: [],
    name: '',
    source_type: 'WEBSITE',
    base_url: '',
    api_endpoint: '',
    country: 'DE',
    location_id: null,
    location_name: '',
    admin_level_1: '',
    crawl_config: {
      max_depth: 3,
      max_pages: 100,
      render_javascript: false,
      url_include_patterns: [],
      url_exclude_patterns: [],
    },
  }
  selectedLocation.value = null
  locationSearch.value = ''
  locationItems.value = []
  dialog.value = true
}

const openEditDialog = (source: any) => {
  editMode.value = true
  selectedSource.value = source
  const defaultCrawlConfig = {
    max_depth: 3,
    max_pages: 100,
    render_javascript: false,
    url_include_patterns: [],
    url_exclude_patterns: [],
  }

  // Extract category IDs from N:M categories array
  const categoryIds = source.categories?.map((c: any) => c.id) || []
  // Fallback to legacy category_id if no N:M categories
  if (categoryIds.length === 0 && source.category_id) {
    categoryIds.push(source.category_id)
  }

  formData.value = {
    ...source,
    category_ids: categoryIds,
    country: source.country || 'DE',
    location_id: source.location_id || null,
    location_name: source.location_name || '',
    admin_level_1: source.admin_level_1 || '',
    crawl_config: { ...defaultCrawlConfig, ...(source.crawl_config || {}) },
  }
  // Set location autocomplete if source has location
  if (source.location_name) {
    selectedLocation.value = {
      id: source.location_id,
      name: source.location_name,
      admin_level_1: source.admin_level_1,
    }
    locationItems.value = [selectedLocation.value]
  } else {
    selectedLocation.value = null
    locationItems.value = []
  }
  locationSearch.value = ''
  dialog.value = true
}

const saveSource = async () => {
  try {
    if (editMode.value) {
      await adminApi.updateSource(selectedSource.value.id, formData.value)
    } else {
      await adminApi.createSource(formData.value)
    }
    dialog.value = false
    loadSources()
  } catch (error) {
    console.error('Failed to save source:', error)
  }
}

const openBulkImportDialog = () => {
  bulkImport.value = { category_id: '', urls: '', skip_duplicates: true }
  bulkDialog.value = true
}

const executeBulkImport = async () => {
  const lines = bulkImport.value.urls.split('\n').filter(l => l.trim())
  const sources = lines.map(line => {
    const parts = line.split('|').map(p => p.trim())
    if (parts.length === 2) {
      return { name: parts[0], base_url: parts[1], source_type: 'WEBSITE' }
    }
    return { name: parts[0], base_url: parts[0], source_type: 'WEBSITE' }
  })

  try {
    await adminApi.bulkImportSources({
      category_id: bulkImport.value.category_id,
      sources,
      skip_duplicates: bulkImport.value.skip_duplicates,
    })
    bulkDialog.value = false
    loadSources()
  } catch (error) {
    console.error('Bulk import failed:', error)
  }
}

const startCrawl = async (source: any) => {
  try {
    await adminApi.startCrawl({ source_ids: [source.id] })
    snackbarText.value = t('sources.messages.crawlStarted', { name: source.name })
    snackbarColor.value = 'success'
    snackbar.value = true
  } catch (error) {
    console.error('Failed to start crawl:', error)
    snackbarText.value = t('sources.messages.crawlError')
    snackbarColor.value = 'error'
    snackbar.value = true
  }
}

const resetSource = async (source: any) => {
  try {
    await adminApi.resetSource(source.id)
    snackbarText.value = t('sources.messages.reset', { name: source.name })
    snackbarColor.value = 'success'
    snackbar.value = true
    loadSources()
  } catch (error) {
    console.error('Failed to reset source:', error)
    snackbarText.value = t('sources.messages.resetError')
    snackbarColor.value = 'error'
    snackbar.value = true
  }
}

const confirmDelete = (source: any) => {
  selectedSource.value = source
  deleteDialog.value = true
}

const deleteSource = async () => {
  await adminApi.deleteSource(selectedSource.value.id)
  deleteDialog.value = false
  loadSources()
}

onMounted(() => {
  loadCountries()
  loadCategories()

  // Check for query parameters to pre-filter
  if (route.query.category_id) {
    filters.value.category_id = route.query.category_id as string
  }
  if (route.query.country) {
    filters.value.country = route.query.country as string
  }
  if (route.query.location_name) {
    filters.value.location_name = route.query.location_name as string
  }

  loadSources()
  // Load initial location filter items (top locations)
  searchLocationFilter('')
})
</script>

<style scoped>
.dialog-tabs {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
