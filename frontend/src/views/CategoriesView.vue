<template>
  <div>
    <PageHeader
      :title="$t('categories.title')"
      :subtitle="$t('categories.subtitle')"
      icon="mdi-folder-multiple"
      :count="filteredCategories.length"
    >
      <template #actions>
        <v-btn variant="tonal" color="primary" @click="openCreateDialog">
          <v-icon left>mdi-plus</v-icon>{{ $t('categories.actions.create') }}
        </v-btn>
      </template>
    </PageHeader>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row align="center">
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
          <div class="table-actions d-flex justify-end ga-1">
            <v-btn icon="mdi-database-outline" size="small" variant="tonal" color="primary" :title="$t('categories.actions.viewSources')" :aria-label="$t('categories.actions.viewSources')" @click="showSourcesForCategory(item)"></v-btn>
            <v-btn icon="mdi-pencil" size="small" variant="tonal" :title="$t('common.edit')" :aria-label="$t('common.edit')" @click="openEditDialog(item)"></v-btn>
            <v-btn icon="mdi-play" size="small" variant="tonal" color="success" :title="$t('categories.actions.startCrawl')" :aria-label="$t('categories.actions.startCrawl')" @click="openCrawlerDialog(item)"></v-btn>
            <v-btn icon="mdi-refresh" size="small" variant="tonal" color="warning" :title="$t('categories.actions.reanalyze')" :aria-label="$t('categories.actions.reanalyze')" @click="confirmReanalyze(item)"></v-btn>
            <v-btn icon="mdi-delete" size="small" variant="tonal" color="error" :title="$t('common.delete')" :aria-label="$t('common.delete')" @click="confirmDelete(item)"></v-btn>
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Create/Edit Dialog -->
    <v-dialog v-model="dialog" max-width="900" persistent scrollable>
      <v-card>
        <v-card-title class="d-flex align-center pa-4 bg-primary">
          <v-avatar color="primary-darken-1" size="40" class="mr-3">
            <v-icon color="on-primary">{{ editMode ? 'mdi-folder-edit' : 'mdi-folder-plus' }}</v-icon>
          </v-avatar>
          <div>
            <div class="text-h6">{{ editMode ? $t('categories.dialog.edit') : $t('categories.dialog.create') }}</div>
            <div v-if="formData.name" class="text-caption opacity-80">{{ formData.name }}</div>
          </div>
        </v-card-title>

        <v-tabs v-model="categoryTab" class="dialog-tabs">
          <v-tab value="general">
            <v-icon start>mdi-form-textbox</v-icon>
            {{ $t('categories.tabs.general') }}
          </v-tab>
          <v-tab value="search">
            <v-icon start>mdi-magnify</v-icon>
            {{ $t('categories.tabs.search') }}
          </v-tab>
          <v-tab value="filters">
            <v-icon start>mdi-filter</v-icon>
            {{ $t('categories.tabs.filters') }}
            <v-icon v-if="!formData.url_include_patterns?.length && !formData.url_exclude_patterns?.length" color="warning" size="x-small" class="ml-1">mdi-alert</v-icon>
          </v-tab>
          <v-tab value="ai">
            <v-icon start>mdi-robot</v-icon>
            {{ $t('categories.tabs.ai') }}
          </v-tab>
          <v-tab v-if="editMode" value="dataSources">
            <v-icon start>mdi-database</v-icon>
            {{ $t('categories.tabs.dataSources') }}
            <v-chip v-if="selectedCategory?.source_count" size="x-small" color="primary" class="ml-1">
              {{ selectedCategory.source_count }}
            </v-chip>
          </v-tab>
        </v-tabs>

        <v-card-text class="pa-6 dialog-content-lg">
          <v-form ref="form">
            <v-window v-model="categoryTab">
              <!-- General Tab -->
              <v-window-item value="general">
                <v-row>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model="formData.name"
                      :label="$t('categories.form.name')"
                      required
                      :rules="[v => !!v || t('categories.form.nameRequired')]"
                      variant="outlined"
                      prepend-inner-icon="mdi-folder"
                    ></v-text-field>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-card variant="outlined" class="pa-3 h-100 d-flex align-center justify-space-between">
                      <div>
                        <div class="text-body-2 font-weight-medium">{{ $t('categories.form.enabled') }}</div>
                        <div class="text-caption text-medium-emphasis">{{ $t('categories.form.enabledHint') }}</div>
                      </div>
                      <v-switch
                        v-model="formData.is_active"
                        color="success"
                        hide-details
                      ></v-switch>
                    </v-card>
                  </v-col>
                </v-row>

                <v-textarea
                  v-model="formData.description"
                  :label="$t('categories.form.description')"
                  rows="2"
                  variant="outlined"
                ></v-textarea>

                <v-textarea
                  v-model="formData.purpose"
                  :label="$t('categories.form.purpose')"
                  required
                  rows="3"
                  :rules="[v => !!v || t('categories.form.purposeRequired')]"
                  variant="outlined"
                  :hint="$t('categories.form.purposeHint')"
                  persistent-hint
                ></v-textarea>

                <v-card variant="outlined" class="mt-4">
                  <v-card-title class="text-subtitle-2 pb-2">
                    <v-icon start size="small">mdi-translate</v-icon>
                    {{ $t('categories.form.languages') }}
                  </v-card-title>
                  <v-card-text>
                    <p class="text-caption text-medium-emphasis mb-3">
                      {{ $t('categories.form.languagesDescription') }}
                    </p>
                    <v-select
                      v-model="formData.languages"
                      :items="availableLanguages"
                      item-title="name"
                      item-value="code"
                      chips
                      multiple
                      closable-chips
                      variant="outlined"
                      :hint="$t('categories.form.languagesHint')"
                      persistent-hint
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
                            <span class="mr-2 text-h6">{{ item.raw.flag }}</span>
                          </template>
                        </v-list-item>
                      </template>
                    </v-select>
                  </v-card-text>
                </v-card>
              </v-window-item>

              <!-- Search Tab -->
              <v-window-item value="search">
                <v-alert type="info" variant="tonal" class="mb-4">
                  {{ $t('categories.form.searchInfo') }}
                </v-alert>

                <v-combobox
                  v-model="formData.search_terms"
                  :label="$t('categories.form.searchTerms')"
                  chips
                  multiple
                  closable-chips
                  :hint="$t('categories.form.searchTermsHint')"
                  persistent-hint
                  variant="outlined"
                >
                  <template v-slot:chip="{ item, props }">
                    <v-chip v-bind="props" color="primary" variant="tonal">
                      <v-icon start size="small">mdi-magnify</v-icon>
                      {{ item.raw }}
                    </v-chip>
                  </template>
                </v-combobox>

                <v-combobox
                  v-model="formData.document_types"
                  :label="$t('categories.form.documentTypes')"
                  chips
                  multiple
                  closable-chips
                  :hint="$t('categories.form.documentTypesHint')"
                  persistent-hint
                  variant="outlined"
                  class="mt-4"
                >
                  <template v-slot:chip="{ item, props }">
                    <v-chip v-bind="props" color="secondary" variant="tonal">
                      <v-icon start size="small">mdi-file-document</v-icon>
                      {{ item.raw }}
                    </v-chip>
                  </template>
                </v-combobox>

                <v-card variant="outlined" class="mt-6">
                  <v-card-title class="text-subtitle-2 pb-2">
                    <v-icon start size="small">mdi-clock</v-icon>
                    {{ $t('categories.form.scheduleTitle') }}
                  </v-card-title>
                  <v-card-text class="pt-4">
                    <ScheduleBuilder
                      v-model="formData.schedule_cron"
                      :show-advanced="true"
                    />
                  </v-card-text>
                </v-card>
              </v-window-item>

              <!-- URL Filters Tab -->
              <v-window-item value="filters">
                <v-alert type="info" variant="tonal" class="mb-4">
                  {{ $t('categories.form.urlFiltersDescription') }}
                </v-alert>

                <v-card variant="outlined" color="success" class="mb-4">
                  <v-card-title class="text-subtitle-2 pb-2">
                    <v-icon start size="small" color="success">mdi-check-circle</v-icon>
                    {{ $t('categories.form.includePatterns') }}
                  </v-card-title>
                  <v-card-text class="pt-4">
                    <v-combobox
                      v-model="formData.url_include_patterns"
                      chips
                      multiple
                      closable-chips
                      :hint="$t('categories.form.includeHint')"
                      persistent-hint
                      variant="outlined"
                      :placeholder="$t('categories.form.includePlaceholder')"
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
                    {{ $t('categories.form.excludePatterns') }}
                  </v-card-title>
                  <v-card-text class="pt-4">
                    <v-combobox
                      v-model="formData.url_exclude_patterns"
                      chips
                      multiple
                      closable-chips
                      :hint="$t('categories.form.excludeHint')"
                      persistent-hint
                      variant="outlined"
                      :placeholder="$t('categories.form.excludePlaceholder')"
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

                <v-alert v-if="!formData.url_include_patterns?.length && !formData.url_exclude_patterns?.length" type="warning" variant="tonal" class="mt-4">
                  <v-icon start>mdi-alert</v-icon>
                  {{ $t('categories.form.noFiltersWarning') }}
                </v-alert>
              </v-window-item>

              <!-- AI Tab -->
              <v-window-item value="ai">
                <v-card variant="outlined" class="mb-4">
                  <v-card-text class="d-flex align-center">
                    <v-avatar color="info" size="48" class="mr-4">
                      <v-icon color="on-info">mdi-robot</v-icon>
                    </v-avatar>
                    <div>
                      <div class="text-body-1 font-weight-medium">{{ $t('categories.form.aiPromptTitle') }}</div>
                      <div class="text-caption text-medium-emphasis">{{ $t('categories.form.aiPromptDescription') }}</div>
                    </div>
                  </v-card-text>
                </v-card>

                <v-textarea
                  v-model="formData.ai_extraction_prompt"
                  :label="$t('categories.form.aiPrompt')"
                  rows="14"
                  variant="outlined"
                  :hint="$t('categories.form.aiPromptHint')"
                  persistent-hint
                ></v-textarea>
              </v-window-item>

              <!-- DataSources Tab (only in edit mode) -->
              <v-window-item v-if="editMode" value="dataSources">
                <v-alert type="info" variant="tonal" class="mb-4">
                  <div class="d-flex align-center">
                    <v-icon start>mdi-tag-multiple</v-icon>
                    {{ $t('categories.dataSourcesTab.description') }}
                  </div>
                </v-alert>

                <!-- Tag Filter Section -->
                <v-card variant="outlined" class="mb-4">
                  <v-card-title class="text-subtitle-1 pb-2">
                    <v-icon start color="primary">mdi-filter</v-icon>
                    {{ $t('categories.dataSourcesTab.filterByTags') }}
                  </v-card-title>
                  <v-card-text>
                    <v-row>
                      <v-col cols="12" md="8">
                        <v-combobox
                          v-model="dataSourcesTab.selectedTags"
                          :items="availableTags"
                          :label="$t('categories.dataSourcesTab.filterByTags')"
                          multiple
                          chips
                          closable-chips
                          variant="outlined"
                          density="compact"
                          @update:model-value="searchSourcesByTags"
                        >
                          <template v-slot:chip="{ item, props }">
                            <v-chip v-bind="props" color="primary" variant="tonal">
                              <v-icon start size="small">mdi-tag</v-icon>
                              {{ item.raw }}
                            </v-chip>
                          </template>
                        </v-combobox>
                      </v-col>
                      <v-col cols="12" md="4">
                        <v-radio-group v-model="dataSourcesTab.matchMode" inline hide-details>
                          <v-radio value="all" :label="$t('categories.dataSourcesTab.matchAll')">
                            <template v-slot:label>
                              <span class="text-caption">{{ $t('categories.dataSourcesTab.matchAll') }}</span>
                            </template>
                          </v-radio>
                          <v-radio value="any" :label="$t('categories.dataSourcesTab.matchAny')">
                            <template v-slot:label>
                              <span class="text-caption">{{ $t('categories.dataSourcesTab.matchAny') }}</span>
                            </template>
                          </v-radio>
                        </v-radio-group>
                      </v-col>
                    </v-row>
                  </v-card-text>
                </v-card>

                <!-- Results Section -->
                <v-card variant="outlined">
                  <v-card-title class="text-subtitle-1 d-flex align-center justify-space-between">
                    <div>
                      <v-icon start color="secondary">mdi-database-search</v-icon>
                      {{ $t('categories.dataSourcesTab.foundSources') }}
                      <v-chip v-if="dataSourcesTab.foundSources.length" size="small" color="info" class="ml-2">
                        {{ dataSourcesTab.foundSources.length }}
                      </v-chip>
                    </div>
                    <div v-if="dataSourcesTab.foundSources.length > 0">
                      <v-btn
                        size="small"
                        variant="tonal"
                        color="primary"
                        :loading="dataSourcesTab.assigning"
                        @click="assignSourcesByTags"
                      >
                        <v-icon start>mdi-link-plus</v-icon>
                        {{ $t('categories.dataSourcesTab.assignAll') }} ({{ dataSourcesTab.foundSources.length }})
                      </v-btn>
                    </div>
                  </v-card-title>
                  <v-card-text>
                    <!-- Loading state -->
                    <div v-if="dataSourcesTab.loading" class="text-center py-8">
                      <v-progress-circular indeterminate color="primary" class="mb-2"></v-progress-circular>
                      <div class="text-caption">{{ $t('categories.dataSourcesTab.loading') }}</div>
                    </div>

                    <!-- No tags selected -->
                    <v-alert v-else-if="!dataSourcesTab.selectedTags.length" type="info" variant="tonal">
                      {{ $t('categories.dataSourcesTab.noTagsSelected') }}
                    </v-alert>

                    <!-- No results -->
                    <v-alert v-else-if="!dataSourcesTab.foundSources.length" type="warning" variant="tonal">
                      {{ $t('categories.dataSourcesTab.noSourcesFound') }}
                    </v-alert>

                    <!-- Results list -->
                    <v-list v-else lines="two" class="sources-result-list">
                      <v-list-item
                        v-for="source in dataSourcesTab.foundSources.slice(0, 50)"
                        :key="source.id"
                        :title="source.name"
                        :subtitle="source.base_url"
                      >
                        <template v-slot:prepend>
                          <v-avatar :color="getStatusColor(source.status)" size="36">
                            <v-icon size="small" :color="getContrastColor(getStatusColor(source.status))">
                              {{ getSourceTypeIcon(source.source_type) }}
                            </v-icon>
                          </v-avatar>
                        </template>
                        <template v-slot:append>
                          <div class="d-flex align-center ga-2">
                            <div class="d-flex flex-wrap ga-1">
                              <v-chip
                                v-for="tag in (source.tags || []).slice(0, 3)"
                                :key="tag"
                                size="x-small"
                                color="primary"
                                variant="outlined"
                              >
                                {{ tag }}
                              </v-chip>
                              <v-chip
                                v-if="(source.tags || []).length > 3"
                                size="x-small"
                                color="grey"
                              >
                                +{{ source.tags.length - 3 }}
                              </v-chip>
                            </div>
                            <v-chip
                              v-if="source.is_assigned"
                              size="x-small"
                              color="success"
                              variant="tonal"
                            >
                              <v-icon start size="x-small">mdi-check</v-icon>
                              {{ $t('categories.dataSourcesTab.alreadyAssigned') }}
                            </v-chip>
                          </div>
                        </template>
                      </v-list-item>
                      <v-list-item v-if="dataSourcesTab.foundSources.length > 50" class="text-center text-medium-emphasis">
                        ... {{ $t('sources.bulk.moreEntries', { count: dataSourcesTab.foundSources.length - 50 }) }}
                      </v-list-item>
                    </v-list>
                  </v-card-text>
                </v-card>

                <!-- Current assigned count -->
                <v-alert v-if="selectedCategory?.source_count" type="success" variant="tonal" class="mt-4">
                  <v-icon start>mdi-check-circle</v-icon>
                  {{ $t('categories.dataSourcesTab.currentlyAssigned') }}: <strong>{{ selectedCategory.source_count }}</strong> {{ $t('categories.crawler.sourcesCount') }}
                </v-alert>
              </v-window-item>
            </v-window>
          </v-form>
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions class="pa-4">
          <v-btn variant="tonal" @click="dialog = false">{{ $t('common.cancel') }}</v-btn>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" color="primary" @click="saveCategory">
            <v-icon start>mdi-check</v-icon>
            {{ $t('common.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon color="error" class="mr-2">mdi-alert</v-icon>
          {{ $t('categories.dialog.delete') }}
        </v-card-title>
        <v-card-text>
          {{ $t('categories.dialog.deleteConfirm', { name: selectedCategory?.name }) }}
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="deleteDialog = false">{{ $t('common.cancel') }}</v-btn>
          <v-btn variant="tonal" color="error" @click="deleteCategory">{{ $t('common.delete') }}</v-btn>
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
          <v-btn variant="tonal" @click="reanalyzeDialog = false">{{ $t('common.cancel') }}</v-btn>
          <v-btn variant="tonal" color="warning" @click="reanalyzeDocuments">{{ $t('categories.actions.reanalyze') }}</v-btn>
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
                  <v-icon size="small" :color="getContrastColor(getStatusColor(source.status))">{{ getSourceTypeIcon(source.source_type) }}</v-icon>
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
                    variant="tonal"
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
            variant="tonal"
            @click="navigateToSourcesFiltered"
          >
            <v-icon left>mdi-filter</v-icon>{{ $t('categories.dialog.showAllInSourcesView') }}
          </v-btn>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="sourcesDialog = false">{{ $t('common.close') }}</v-btn>
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
                variant="tonal"
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
              <v-number-input
                v-model="crawlerFilter.limit"
                :label="$t('categories.crawler.maxLimit')"
                :min="1"
                :max="10000"
                prepend-inner-icon="mdi-numeric"
                clearable
                density="comfortable"
                :hint="$t('categories.crawler.limitHint')"
                persistent-hint
                control-variant="stacked"
                @update:model-value="updateCrawlerFilteredCount"
              ></v-number-input>
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
          <v-btn variant="tonal" @click="crawlerDialog = false">{{ $t('common.cancel') }}</v-btn>
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

    <!-- AI Setup Preview Dialog -->
    <v-dialog v-model="aiPreviewDialog" max-width="900" persistent scrollable>
      <v-card>
        <v-card-title class="d-flex align-center pa-4 bg-info">
          <v-avatar color="info-darken-1" size="40" class="mr-3">
            <v-icon color="on-info">mdi-robot</v-icon>
          </v-avatar>
          <div>
            <div class="text-h6">{{ $t('categories.aiPreview.title') }}</div>
            <div class="text-caption opacity-80">{{ $t('categories.aiPreview.subtitle') }}</div>
          </div>
        </v-card-title>

        <v-card-text v-if="aiPreviewLoading" class="pa-6 text-center">
          <v-progress-circular indeterminate color="info" size="64" class="mb-4"></v-progress-circular>
          <div class="text-h6">{{ $t('categories.aiPreview.generating') }}</div>
          <div class="text-body-2 text-medium-emphasis">{{ $t('categories.aiPreview.generatingHint') }}</div>
        </v-card-text>

        <v-card-text v-else-if="aiPreviewData" class="pa-6">
          <!-- EntityType Section -->
          <v-card variant="outlined" class="mb-4">
            <v-card-title class="text-subtitle-1 pb-2">
              <v-icon start color="primary">mdi-shape</v-icon>
              {{ $t('categories.aiPreview.entityType') }}
            </v-card-title>
            <v-card-text>
              <v-radio-group v-model="selectedEntityTypeOption" hide-details>
                <v-radio value="new" :label="$t('categories.aiPreview.createNew')">
                  <template v-slot:label>
                    <div>
                      <span class="font-weight-medium">{{ $t('categories.aiPreview.createNew') }}: </span>
                      <v-chip size="small" color="success" class="ml-1">{{ aiPreviewData.suggested_entity_type.name }}</v-chip>
                      <span class="text-caption text-medium-emphasis ml-2">{{ aiPreviewData.suggested_entity_type.description }}</span>
                    </div>
                  </template>
                </v-radio>
                <v-radio
                  v-for="et in aiPreviewData.existing_entity_types.slice(0, 5)"
                  :key="et.id"
                  :value="et.id"
                >
                  <template v-slot:label>
                    <div>
                      <span class="font-weight-medium">{{ $t('categories.aiPreview.useExisting') }}: </span>
                      <v-chip size="small" color="primary" class="ml-1">{{ et.name }}</v-chip>
                      <span class="text-caption text-medium-emphasis ml-2">{{ et.description }}</span>
                    </div>
                  </template>
                </v-radio>
              </v-radio-group>
            </v-card-text>
          </v-card>

          <!-- FacetTypes Section -->
          <v-card variant="outlined" class="mb-4">
            <v-card-title class="text-subtitle-1 pb-2">
              <v-icon start color="secondary">mdi-tag-multiple</v-icon>
              {{ $t('categories.aiPreview.facetTypes') }}
            </v-card-title>
            <v-card-text>
              <p class="text-body-2 text-medium-emphasis mb-3">{{ $t('categories.aiPreview.facetTypesHint') }}</p>
              <v-checkbox
                v-for="(ft, index) in aiPreviewData.suggested_facet_types"
                :key="ft.slug"
                v-model="selectedFacetTypes[index]"
                hide-details
                density="compact"
              >
                <template v-slot:label>
                  <div class="d-flex align-center">
                    <v-icon :color="ft.color" size="small" class="mr-2">{{ ft.icon }}</v-icon>
                    <span class="font-weight-medium">{{ ft.name }}</span>
                    <v-chip v-if="!ft.is_new" size="x-small" color="info" class="ml-2">{{ $t('categories.aiPreview.exists') }}</v-chip>
                    <v-chip v-else size="x-small" color="success" class="ml-2">{{ $t('categories.aiPreview.new') }}</v-chip>
                    <span class="text-caption text-medium-emphasis ml-2">{{ ft.description }}</span>
                  </div>
                </template>
              </v-checkbox>
            </v-card-text>
          </v-card>

          <!-- Extraction Prompt Section -->
          <v-card variant="outlined" class="mb-4">
            <v-card-title class="text-subtitle-1 pb-2">
              <v-icon start color="info">mdi-text-box-edit</v-icon>
              {{ $t('categories.aiPreview.extractionPrompt') }}
            </v-card-title>
            <v-card-text>
              <v-textarea
                v-model="editableExtractionPrompt"
                rows="8"
                variant="outlined"
                :hint="$t('categories.aiPreview.promptHint')"
                persistent-hint
              ></v-textarea>
            </v-card-text>
          </v-card>

          <!-- Search Terms & URL Patterns -->
          <v-row>
            <v-col cols="12" md="6">
              <v-card variant="outlined" class="h-100">
                <v-card-title class="text-subtitle-2 pb-2">
                  <v-icon start size="small">mdi-magnify</v-icon>
                  {{ $t('categories.aiPreview.searchTerms') }}
                </v-card-title>
                <v-card-text>
                  <v-chip
                    v-for="term in aiPreviewData.suggested_search_terms"
                    :key="term"
                    size="small"
                    color="primary"
                    variant="tonal"
                    class="mr-1 mb-1"
                  >
                    {{ term }}
                  </v-chip>
                </v-card-text>
              </v-card>
            </v-col>
            <v-col cols="12" md="6">
              <v-card variant="outlined" class="h-100">
                <v-card-title class="text-subtitle-2 pb-2">
                  <v-icon start size="small">mdi-filter</v-icon>
                  {{ $t('categories.aiPreview.urlPatterns') }}
                </v-card-title>
                <v-card-text>
                  <div class="mb-2">
                    <span class="text-caption font-weight-medium text-success">Include:</span>
                    <v-chip
                      v-for="pattern in aiPreviewData.suggested_url_include_patterns"
                      :key="pattern"
                      size="x-small"
                      color="success"
                      variant="tonal"
                      class="ml-1 mb-1"
                    >
                      {{ pattern }}
                    </v-chip>
                    <span v-if="!aiPreviewData.suggested_url_include_patterns?.length" class="text-caption text-medium-emphasis">-</span>
                  </div>
                  <div>
                    <span class="text-caption font-weight-medium text-error">Exclude:</span>
                    <v-chip
                      v-for="pattern in aiPreviewData.suggested_url_exclude_patterns"
                      :key="pattern"
                      size="x-small"
                      color="error"
                      variant="tonal"
                      class="ml-1 mb-1"
                    >
                      {{ pattern }}
                    </v-chip>
                    <span v-if="!aiPreviewData.suggested_url_exclude_patterns?.length" class="text-caption text-medium-emphasis">-</span>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

          <!-- Reasoning -->
          <v-alert v-if="aiPreviewData.reasoning" type="info" variant="tonal" class="mt-4">
            <div class="text-caption font-weight-medium mb-1">{{ $t('categories.aiPreview.reasoning') }}</div>
            <div class="text-body-2">{{ aiPreviewData.reasoning }}</div>
          </v-alert>
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions class="pa-4">
          <v-btn variant="tonal" @click="aiPreviewDialog = false">{{ $t('common.cancel') }}</v-btn>
          <v-btn variant="tonal" color="grey" @click="saveWithoutAiSetup">
            <v-icon start>mdi-content-save-outline</v-icon>
            {{ $t('categories.aiPreview.saveWithoutAi') }}
          </v-btn>
          <v-spacer></v-spacer>
          <v-btn
            variant="tonal"
            color="primary"
            :loading="savingWithAi"
            :disabled="aiPreviewLoading"
            @click="saveWithAiSetup"
          >
            <v-icon start>mdi-check</v-icon>
            {{ $t('categories.aiPreview.applyAndSave') }}
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
import { getContrastColor } from '@/composables/useColorHelpers'
import ScheduleBuilder from '@/components/common/ScheduleBuilder.vue'
import PageHeader from '@/components/common/PageHeader.vue'

const { t } = useI18n()
const router = useRouter()

const loading = ref(false)
const categories = ref<any[]>([])
const dialog = ref(false)
const categoryTab = ref('general')
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

// DataSources Tab state
const availableTags = ref<string[]>([])
const dataSourcesTab = ref({
  selectedTags: [] as string[],
  matchMode: 'all' as 'all' | 'any',
  foundSources: [] as any[],
  loading: false,
  assigning: false,
})

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

// AI Preview state
const aiPreviewDialog = ref(false)
const aiPreviewLoading = ref(false)
const aiPreviewData = ref<any>(null)
const savingWithAi = ref(false)
const selectedEntityTypeOption = ref<string>('new')
const selectedFacetTypes = ref<boolean[]>([])
const editableExtractionPrompt = ref('')

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
  { title: t('categories.columns.actions'), key: 'actions', sortable: false, align: 'end' as const },
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

const openEditDialog = async (category: any) => {
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
  // Reset DataSources tab state
  dataSourcesTab.value = {
    selectedTags: [],
    matchMode: 'all',
    foundSources: [],
    loading: false,
    assigning: false,
  }
  dialog.value = true
  // Load available tags for the DataSources tab
  await loadAvailableTags()
}

const saveCategory = async () => {
  try {
    if (editMode.value) {
      // For edit mode, just save directly
      await adminApi.updateCategory(selectedCategory.value.id, formData.value)
      dialog.value = false
      loadCategories()
    } else {
      // For new categories, show AI preview dialog
      dialog.value = false
      await showAiPreview()
    }
  } catch (error) {
    console.error('Failed to save category:', error)
    snackbarText.value = t('categories.messages.saveError')
    snackbarColor.value = 'error'
    snackbar.value = true
  }
}

const showAiPreview = async () => {
  aiPreviewDialog.value = true
  aiPreviewLoading.value = true
  aiPreviewData.value = null

  try {
    const response = await adminApi.previewCategoryAiSetup({
      name: formData.value.name,
      purpose: formData.value.purpose,
      description: formData.value.description || undefined,
    })

    aiPreviewData.value = response.data
    editableExtractionPrompt.value = response.data.suggested_extraction_prompt || ''

    // Initialize facet type selections (all selected by default)
    selectedFacetTypes.value = response.data.suggested_facet_types.map((ft: any) => ft.selected !== false)

    // Default to creating new EntityType if suggested
    selectedEntityTypeOption.value = response.data.suggested_entity_type.is_new ? 'new' : (response.data.suggested_entity_type.id || 'new')
  } catch (error: any) {
    console.error('Failed to get AI preview:', error)
    aiPreviewDialog.value = false
    dialog.value = true // Re-open the original dialog

    const errorMessage = error.response?.data?.detail || t('categories.aiPreview.error')
    snackbarText.value = errorMessage
    snackbarColor.value = 'error'
    snackbar.value = true
  } finally {
    aiPreviewLoading.value = false
  }
}

const saveWithoutAiSetup = async () => {
  try {
    await adminApi.createCategory(formData.value)
    aiPreviewDialog.value = false
    loadCategories()
    snackbarText.value = t('categories.messages.created')
    snackbarColor.value = 'success'
    snackbar.value = true
  } catch (error) {
    console.error('Failed to save category:', error)
    snackbarText.value = t('categories.messages.saveError')
    snackbarColor.value = 'error'
    snackbar.value = true
  }
}

const saveWithAiSetup = async () => {
  if (!aiPreviewData.value) return

  savingWithAi.value = true
  try {
    // Build the category data with AI suggestions
    const categoryData: Record<string, unknown> = {
      ...formData.value,
      // Apply AI-generated data
      ai_extraction_prompt: editableExtractionPrompt.value,
      search_terms: formData.value.search_terms?.length
        ? formData.value.search_terms
        : aiPreviewData.value.suggested_search_terms,
      url_include_patterns: formData.value.url_include_patterns?.length
        ? formData.value.url_include_patterns
        : aiPreviewData.value.suggested_url_include_patterns,
      url_exclude_patterns: formData.value.url_exclude_patterns?.length
        ? formData.value.url_exclude_patterns
        : aiPreviewData.value.suggested_url_exclude_patterns,
    }

    // Set target_entity_type_id based on selection
    if (selectedEntityTypeOption.value !== 'new') {
      // Use existing EntityType
      categoryData.target_entity_type_id = selectedEntityTypeOption.value
    }

    await adminApi.createCategory(categoryData)
    aiPreviewDialog.value = false
    loadCategories()
    snackbarText.value = t('categories.messages.createdWithAi')
    snackbarColor.value = 'success'
    snackbar.value = true
  } catch (error) {
    console.error('Failed to save category with AI setup:', error)
    snackbarText.value = t('categories.messages.saveError')
    snackbarColor.value = 'error'
    snackbar.value = true
  } finally {
    savingWithAi.value = false
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
    s.base_url?.toLowerCase().includes(search)
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

// DataSources Tab methods
const loadAvailableTags = async () => {
  try {
    const response = await adminApi.getAvailableTags()
    availableTags.value = (response.data.tags || []).map(t => t.tag)
  } catch (error) {
    console.error('Failed to load available tags:', error)
    availableTags.value = []
  }
}

const searchSourcesByTags = async () => {
  if (!dataSourcesTab.value.selectedTags.length) {
    dataSourcesTab.value.foundSources = []
    return
  }

  dataSourcesTab.value.loading = true
  try {
    const response = await adminApi.getSourcesByTags({
      tags: dataSourcesTab.value.selectedTags,
      match_mode: dataSourcesTab.value.matchMode,
      exclude_category_id: selectedCategory.value?.id,
      limit: 1000,
    })
    // Mark sources that are already assigned to this category
    const assignedSourceIds = new Set(categorySources.value.map(s => s.id))
    dataSourcesTab.value.foundSources = response.data.map((source: any) => ({
      ...source,
      is_assigned: assignedSourceIds.has(source.id),
    }))
  } catch (error) {
    console.error('Failed to search sources by tags:', error)
    dataSourcesTab.value.foundSources = []
    snackbarText.value = t('categories.dataSourcesTab.assignError')
    snackbarColor.value = 'error'
    snackbar.value = true
  } finally {
    dataSourcesTab.value.loading = false
  }
}

const assignSourcesByTags = async () => {
  if (!selectedCategory.value || !dataSourcesTab.value.selectedTags.length) return

  dataSourcesTab.value.assigning = true
  try {
    const response = await adminApi.assignSourcesByTags(selectedCategory.value.id, {
      tags: dataSourcesTab.value.selectedTags,
      match_mode: dataSourcesTab.value.matchMode,
      mode: 'add',
    })

    const assignedCount = response.data.assigned_count || dataSourcesTab.value.foundSources.length
    snackbarText.value = t('categories.dataSourcesTab.assignSuccess', { count: assignedCount })
    snackbarColor.value = 'success'
    snackbar.value = true

    // Refresh categories to update source_count
    await loadCategories()

    // Update selected category with new source count
    const updatedCategory = categories.value.find(c => c.id === selectedCategory.value.id)
    if (updatedCategory) {
      selectedCategory.value = updatedCategory
    }

    // Re-search to mark newly assigned sources
    await searchSourcesByTags()
  } catch (error) {
    console.error('Failed to assign sources:', error)
    snackbarText.value = t('categories.dataSourcesTab.assignError')
    snackbarColor.value = 'error'
    snackbar.value = true
  } finally {
    dataSourcesTab.value.assigning = false
  }
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

.sources-result-list {
  max-height: 350px;
  overflow-y: auto;
}

.dialog-tabs {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
