<template>
  <div class="sources-page d-flex">
    <!-- Loading Overlay for large data loads -->
    <v-overlay :model-value="loading" class="align-center justify-center" persistent >
      <v-card class="pa-8 text-center" min-width="320" elevation="24">
        <v-progress-circular indeterminate size="80" width="6" color="primary" class="mb-4"></v-progress-circular>
        <div class="text-h6 mb-2">{{ $t('sources.loading.title') }}</div>
        <div class="text-body-2 text-medium-emphasis">
          {{ totalSources > 0 ? `${totalSources.toLocaleString()} ${$t('sources.sources')}` : $t('sources.loading.subtitle') }}
        </div>
      </v-card>
    </v-overlay>

    <!-- Sidebar Navigation -->
    <SourcesSidebar
      v-model="sidebarOpen"
      :counts="sidebarCounts"
      :selected-category="filters.category_id"
      :selected-type="filters.source_type"
      :selected-status="filters.status"
      :selected-tags="filters.tags"
      :available-tags="availableTags"
      @update:selected-category="onCategorySelect"
      @update:selected-type="onTypeSelect"
      @update:selected-status="onStatusSelect"
      @update:selected-tags="onTagsSelect"
    />

    <!-- Main Content -->
    <div class="sources-main flex-grow-1">
      <div class="d-flex justify-space-between align-center mb-6">
        <div class="d-flex align-center">
          <v-btn
            icon="mdi-menu"
            variant="text"
            class="d-md-none mr-2"
            @click="sidebarOpen = !sidebarOpen"
          />
          <h1 class="text-h4">{{ $t('sources.title') }} ({{ totalSources.toLocaleString() }})</h1>
        </div>
        <div class="d-flex gap-2">
          <!-- Import Dropdown Menu -->
          <v-menu>
            <template v-slot:activator="{ props }">
              <v-btn v-bind="props" variant="tonal" color="secondary">
                <v-icon start>mdi-import</v-icon>
                {{ $t('sources.import.title') }}
                <v-icon end>mdi-chevron-down</v-icon>
              </v-btn>
            </template>
            <v-list density="compact">
              <v-list-item @click="openBulkImportDialog">
                <template v-slot:prepend>
                  <v-icon color="secondary">mdi-file-upload</v-icon>
                </template>
                <v-list-item-title>{{ $t('sources.import.bulkImport') }}</v-list-item-title>
                <v-list-item-subtitle>{{ $t('sources.import.bulkImportDesc') }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item @click="apiImportDialog = true">
                <template v-slot:prepend>
                  <v-icon color="info">mdi-api</v-icon>
                </template>
                <v-list-item-title>{{ $t('sources.import.apiImport') }}</v-list-item-title>
                <v-list-item-subtitle>{{ $t('sources.import.apiImportDesc') }}</v-list-item-subtitle>
              </v-list-item>
              <v-divider />
              <v-list-item @click="aiDiscoveryDialog = true">
                <template v-slot:prepend>
                  <v-icon color="primary">mdi-robot</v-icon>
                </template>
                <v-list-item-title class="text-primary font-weight-bold">{{ $t('sources.import.aiDiscovery') }}</v-list-item-title>
                <v-list-item-subtitle>{{ $t('sources.import.aiDiscoveryDesc') }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-menu>

          <v-btn variant="tonal" color="primary" @click="openCreateDialog">
            <v-icon start>mdi-plus</v-icon>{{ $t('sources.actions.create') }}
          </v-btn>
        </div>
      </div>

      <!-- Active Filters Display -->
      <div class="d-flex flex-wrap gap-2 mb-4" v-if="hasActiveFilters">
        <v-chip
          v-if="filters.category_id"
          closable
          color="primary"
          variant="tonal"
          @click:close="onCategorySelect(null)"
        >
          {{ getCategoryName(filters.category_id) }}
        </v-chip>
        <v-chip
          v-if="filters.source_type"
          closable
          :color="getTypeColor(filters.source_type)"
          variant="tonal"
          @click:close="onTypeSelect(null)"
        >
          {{ getTypeLabel(filters.source_type) }}
        </v-chip>
        <v-chip
          v-if="filters.status"
          closable
          :color="getStatusColor(filters.status)"
          variant="tonal"
          @click:close="onStatusSelect(null)"
        >
          {{ getStatusLabel(filters.status) }}
        </v-chip>
        <v-chip
          v-for="tag in filters.tags"
          :key="tag"
          closable
          :color="getTagColor(tag)"
          variant="tonal"
          @click:close="onTagsSelect(filters.tags.filter(t => t !== tag))"
        >
          <v-icon start size="x-small">mdi-tag</v-icon>
          {{ tag }}
        </v-chip>
        <v-btn
          variant="text"
          size="small"
          color="grey"
          @click="clearAllFilters"
        >
          {{ $t('sources.filters.clearAll') }}
        </v-btn>
      </div>

      <!-- Search Filter -->
      <v-card class="mb-4">
        <v-card-text class="py-3">
          <v-row align="center">
            <v-col cols="12" md="6">
              <v-text-field
                v-model="filters.search"
                :label="$t('sources.filters.search')"
                prepend-inner-icon="mdi-magnify"
                clearable
                density="compact"
                hide-details
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
              {{ getTypeLabel(item.source_type) }}
            </v-chip>
          </template>

          <template v-slot:item.status="{ item }">
            <v-chip :color="getStatusColor(item.status)" size="small">
              {{ getStatusLabel(item.status) }}
            </v-chip>
          </template>

          <template v-slot:item.last_crawl="{ item }">
            {{ item.last_crawl ? formatDate(item.last_crawl) : $t('sources.never') }}
          </template>

          <template v-slot:item.actions="{ item }">
            <div class="table-actions d-flex justify-end ga-1">
              <v-btn icon="mdi-pencil" size="small" variant="tonal" :title="$t('common.edit')" :aria-label="$t('common.edit')" @click="openEditDialog(item)"></v-btn>
              <v-btn icon="mdi-play" size="small" variant="tonal" color="success" :title="$t('sources.actions.startCrawl')" :aria-label="$t('sources.actions.startCrawl')" @click="startCrawl(item)"></v-btn>
              <v-btn v-if="item.status === 'ERROR'" icon="mdi-refresh" size="small" variant="tonal" color="warning" :title="$t('sources.actions.reset')" :aria-label="$t('sources.actions.reset')" @click="resetSource(item)"></v-btn>
              <v-btn icon="mdi-delete" size="small" variant="tonal" color="error" :title="$t('common.delete')" :aria-label="$t('common.delete')" @click="confirmDelete(item)"></v-btn>
            </div>
          </template>
        </v-data-table-server>
      </v-card>

    <!-- Create/Edit Dialog -->
    <v-dialog v-model="dialog" max-width="900" persistent scrollable>
      <v-card>
        <v-card-title class="d-flex align-center pa-4 bg-primary">
          <v-avatar color="primary-darken-1" size="40" class="mr-3">
            <v-icon color="on-primary">{{ editMode ? 'mdi-database-edit' : 'mdi-database-plus' }}</v-icon>
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
          <v-tab value="crawl">
            <v-icon start>mdi-cog</v-icon>
            {{ $t('sources.tabs.crawl') }}
          </v-tab>
        </v-tabs>

        <v-card-text class="pa-6 dialog-content-md">
          <v-form ref="form" v-model="formValid" @submit.prevent="saveSource">
            <v-window v-model="sourceTab">
              <!-- General Tab -->
              <v-window-item value="general">
                <v-row>
                  <v-col cols="12" md="8">
                    <v-text-field
                      v-model="formData.name"
                      :label="$t('sources.form.name')"
                      :rules="nameRules"
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
                      :rules="[v => !!v || $t('sources.validation.sourceTypeRequired')]"
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
                  :rules="urlRules"
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

                <!-- Tags Section -->
                <v-card variant="outlined" class="mt-4">
                  <v-card-title class="text-subtitle-2">
                    <v-icon start size="small">mdi-tag-multiple</v-icon>
                    {{ $t('sources.form.tags') }}
                  </v-card-title>
                  <v-card-text>
                    <v-combobox
                      v-model="formData.tags"
                      :items="tagSuggestions"
                      :label="$t('sources.form.tagsLabel')"
                      multiple
                      chips
                      closable-chips
                      variant="outlined"
                      :hint="$t('sources.form.tagsHint')"
                      persistent-hint
                      prepend-inner-icon="mdi-tag"
                    >
                      <template #chip="{ props, item }">
                        <v-chip
                          v-bind="props"
                          :color="getTagColor(item.value)"
                          size="small"
                        >
                          {{ item.value }}
                        </v-chip>
                      </template>
                    </v-combobox>
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
                  <v-card-text class="pt-4">
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
                  <v-card-text class="pt-4">
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
          <v-btn variant="tonal" @click="dialog = false">{{ $t('common.cancel') }}</v-btn>
          <v-spacer></v-spacer>
          <v-btn
            variant="tonal"
            color="primary"
            :disabled="!formValid"
            :loading="saving"
            @click="saveSource"
          >
            <v-icon start>mdi-check</v-icon>
            {{ $t('common.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Bulk Import Dialog -->
    <v-dialog v-model="bulkDialog" max-width="900" persistent scrollable>
      <v-card>
        <v-card-title class="d-flex align-center pa-4 bg-secondary">
          <v-avatar color="secondary-darken-1" size="40" class="mr-3">
            <v-icon color="on-secondary">mdi-upload-multiple</v-icon>
          </v-avatar>
          <div>
            <div class="text-h6">{{ $t('sources.dialog.bulkImport') }}</div>
            <div class="text-caption opacity-80">CSV-Format: Name;URL;SourceType;Tags</div>
          </div>
        </v-card-title>

        <v-card-text class="pa-6">
          <!-- Categories Selection (N:M) -->
          <v-card variant="outlined" class="mb-4">
            <v-card-title class="text-subtitle-2 pb-2">
              <v-icon start size="small">mdi-folder-multiple</v-icon>
              {{ $t('sources.form.categories') }}
            </v-card-title>
            <v-card-text>
              <v-select
                v-model="bulkImport.category_ids"
                :items="categories"
                item-title="name"
                item-value="id"
                multiple
                chips
                closable-chips
                variant="outlined"
                density="comfortable"
                :rules="[v => v.length > 0 || $t('common.required')]"
              >
                <template v-slot:chip="{ item, index }">
                  <v-chip
                    :color="index === 0 ? 'primary' : 'default'"
                    closable
                    @click:close="bulkImport.category_ids.splice(index, 1)"
                  >
                    {{ item.title }}
                    <v-icon v-if="index === 0" end size="x-small">mdi-star</v-icon>
                  </v-chip>
                </template>
              </v-select>
            </v-card-text>
          </v-card>

          <!-- Default Tags -->
          <v-card variant="outlined" class="mb-4">
            <v-card-title class="text-subtitle-2 pb-2">
              <v-icon start size="small">mdi-tag-multiple</v-icon>
              {{ $t('sources.bulk.defaultTags') }}
            </v-card-title>
            <v-card-text>
              <v-combobox
                v-model="bulkImport.default_tags"
                :items="tagSuggestions"
                :label="$t('sources.bulk.defaultTagsHint')"
                multiple
                chips
                closable-chips
                variant="outlined"
                density="comfortable"
                prepend-inner-icon="mdi-tag"
              >
                <template #chip="{ props, item }">
                  <v-chip
                    v-bind="props"
                    :color="getTagColor(item.value)"
                    size="small"
                  >
                    {{ item.value }}
                  </v-chip>
                </template>
              </v-combobox>
            </v-card-text>
          </v-card>

          <!-- CSV Input -->
          <v-card variant="outlined" class="mb-4">
            <v-card-title class="text-subtitle-2 pb-2">
              <v-icon start size="small">mdi-file-delimited</v-icon>
              {{ $t('sources.bulk.csvData') }}
            </v-card-title>
            <v-card-text>
              <v-radio-group v-model="bulkImport.inputMode" inline class="mb-3">
                <v-radio :label="$t('sources.bulk.csvText')" value="text"></v-radio>
                <v-radio :label="$t('sources.bulk.csvFile')" value="file"></v-radio>
              </v-radio-group>

              <v-textarea
                v-if="bulkImport.inputMode === 'text'"
                v-model="bulkImport.csvText"
                :label="$t('sources.bulk.csvFormat')"
                :placeholder="'Aachen;https://www.aachen.de;WEBSITE;stadt,nrw\nBielefeld;https://www.bielefeld.de;WEBSITE;stadt,nrw'"
                rows="8"
                variant="outlined"
                font-family="monospace"
                :hint="$t('sources.bulk.csvFormatHint')"
                persistent-hint
              ></v-textarea>

              <v-file-input
                v-else
                v-model="bulkImport.csvFile"
                accept=".csv,.txt"
                :label="$t('sources.bulk.csvFileUpload')"
                variant="outlined"
                prepend-icon="mdi-file-upload"
                @update:model-value="onCsvFileSelected"
              ></v-file-input>
            </v-card-text>
          </v-card>

          <!-- Preview Button -->
          <div class="d-flex justify-center mb-4">
            <v-btn
              variant="tonal"
              color="info"
              @click="parseBulkImportPreview"
              :disabled="!canPreview"
            >
              <v-icon start>mdi-eye</v-icon>
              {{ $t('sources.bulk.loadPreview') }}
            </v-btn>
          </div>

          <!-- Preview Table -->
          <v-card v-if="bulkImport.preview.length > 0" variant="outlined">
            <v-card-title class="text-subtitle-2 pb-2 d-flex justify-space-between align-center">
              <span>
                <v-icon start size="small">mdi-table</v-icon>
                {{ $t('sources.bulk.preview') }} ({{ bulkImport.preview.length }} {{ $t('sources.bulk.entries') }})
              </span>
              <span class="text-caption">
                <v-chip size="x-small" color="success" class="mr-1">{{ bulkImport.validCount }} {{ $t('sources.bulk.valid') }}</v-chip>
                <v-chip size="x-small" color="warning" class="mr-1" v-if="bulkImport.duplicateCount > 0">{{ bulkImport.duplicateCount }} {{ $t('sources.bulk.duplicates') }}</v-chip>
                <v-chip size="x-small" color="error" v-if="bulkImport.errorCount > 0">{{ bulkImport.errorCount }} {{ $t('sources.bulk.errors') }}</v-chip>
              </span>
            </v-card-title>
            <v-card-text class="pa-0">
              <v-table density="compact" class="preview-table">
                <thead>
                  <tr>
                    <th style="width: 40px;"></th>
                    <th>{{ $t('sources.columns.name') }}</th>
                    <th>{{ $t('sources.columns.url') }}</th>
                    <th>{{ $t('sources.columns.type') }}</th>
                    <th>{{ $t('sources.form.tags') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(item, idx) in bulkImport.preview.slice(0, 20)" :key="idx" :class="{ 'bg-error-lighten-5': item.error, 'bg-warning-lighten-5': item.duplicate }">
                    <td>
                      <v-icon v-if="item.error" color="error" size="small">mdi-alert-circle</v-icon>
                      <v-icon v-else-if="item.duplicate" color="warning" size="small">mdi-content-duplicate</v-icon>
                      <v-icon v-else color="success" size="small">mdi-check-circle</v-icon>
                    </td>
                    <td class="text-truncate" style="max-width: 200px;">{{ item.name }}</td>
                    <td class="text-truncate text-caption" style="max-width: 250px;">{{ item.base_url }}</td>
                    <td>
                      <v-chip size="x-small" :color="getTypeColor(item.source_type)">{{ item.source_type }}</v-chip>
                    </td>
                    <td>
                      <v-chip v-for="tag in item.allTags.slice(0, 3)" :key="tag" size="x-small" :color="getTagColor(tag)" class="mr-1">{{ tag }}</v-chip>
                      <span v-if="item.allTags.length > 3" class="text-caption">+{{ item.allTags.length - 3 }}</span>
                    </td>
                  </tr>
                  <tr v-if="bulkImport.preview.length > 20">
                    <td colspan="5" class="text-center text-caption">
                      ... {{ bulkImport.preview.length - 20 }} {{ $t('sources.bulk.moreEntries') }}
                    </td>
                  </tr>
                </tbody>
              </v-table>
            </v-card-text>
          </v-card>

          <!-- Options -->
          <v-switch
            v-model="bulkImport.skip_duplicates"
            :label="$t('sources.form.skipDuplicates')"
            color="primary"
            class="mt-4"
          ></v-switch>
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions class="pa-4">
          <v-btn variant="tonal" @click="closeBulkDialog">{{ $t('common.cancel') }}</v-btn>
          <v-spacer></v-spacer>
          <v-btn
            variant="tonal"
            color="primary"
            @click="executeBulkImport"
            :disabled="!canImport"
            :loading="bulkImport.importing"
          >
            <v-icon start>mdi-upload</v-icon>
            {{ bulkImport.validCount }} {{ $t('sources.bulk.sourcesImport') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Dialog -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon color="error" class="mr-2">mdi-alert</v-icon>
          {{ $t('sources.dialog.delete') }}
        </v-card-title>
        <v-card-text>
          {{ $t('sources.dialog.deleteConfirm', { name: selectedSource?.name }) }}
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="deleteDialog = false">{{ $t('common.cancel') }}</v-btn>
          <v-btn variant="tonal" color="error" @click="deleteSource">{{ $t('common.delete') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- API Import Dialog -->
    <ApiImportDialog
      v-model="apiImportDialog"
      :categories="categories"
      :available-tags="tagSuggestions"
      @imported="onApiImported"
    />

    <!-- AI Discovery Dialog -->
    <AiDiscoveryDialog
      v-model="aiDiscoveryDialog"
      :categories="categories"
      @imported="onAiDiscoveryImported"
    />

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
            <div class="text-overline text-medium-emphasis">{{ $t('sources.dialog.purpose') }}</div>
            <div class="text-body-1">{{ selectedCategoryInfo.purpose || $t('sources.dialog.noPurpose') }}</div>
          </div>

          <!-- Description -->
          <div class="mb-4" v-if="selectedCategoryInfo.description">
            <div class="text-overline text-medium-emphasis">{{ $t('common.description') }}</div>
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
            <div class="text-overline text-medium-emphasis">{{ $t('sources.dialog.searchTerms') }}</div>
            <div>
              <v-chip v-for="term in selectedCategoryInfo.search_terms" :key="term" size="small" class="mr-1 mb-1" color="primary" variant="outlined">
                {{ term }}
              </v-chip>
            </div>
          </div>

          <!-- Document Types -->
          <div class="mb-4" v-if="selectedCategoryInfo.document_types?.length">
            <div class="text-overline text-medium-emphasis">{{ $t('sources.dialog.documentTypes') }}</div>
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
                  <div class="text-caption text-medium-emphasis mb-1">{{ $t('sources.dialog.includePatterns') }}</div>
                  <v-chip v-for="p in selectedCategoryInfo.url_include_patterns" :key="p" size="small" class="mr-1 mb-1" color="success" variant="outlined">
                    <v-icon start size="x-small">mdi-check</v-icon>{{ p }}
                  </v-chip>
                </div>
                <div v-if="selectedCategoryInfo.url_exclude_patterns?.length">
                  <div class="text-caption text-medium-emphasis mb-1">{{ $t('sources.dialog.excludePatterns') }}</div>
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
                <pre class="text-caption scrollable-code">{{ selectedCategoryInfo.ai_extraction_prompt }}</pre>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="categoryInfoDialog = false">{{ $t('common.close') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

      <!-- Snackbar for feedback -->
      <v-snackbar v-model="snackbar" :color="snackbarColor" timeout="3000">
        {{ snackbarText }}
      </v-snackbar>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { adminApi } from '@/services/api'
import { format } from 'date-fns'
import { de } from 'date-fns/locale'
import SourcesSidebar from '@/components/sources/SourcesSidebar.vue'
import ApiImportDialog from '@/components/sources/ApiImportDialog.vue'
import AiDiscoveryDialog from '@/components/sources/AiDiscoveryDialog.vue'
import { useSourceHelpers } from '@/composables/useSourceHelpers'

const {
  getTypeColor,
  getTypeLabel,
  getStatusColor,
  getStatusLabel,
} = useSourceHelpers()

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

// Sidebar state
const sidebarOpen = ref(true)
const sidebarCounts = ref({
  total: 0,
  categories: [] as { id: string; name: string; slug: string; count: number }[],
  types: [] as { type: string; count: number }[],
  statuses: [] as { status: string; count: number }[],
})

const sourceTypeOptions = [
  { value: 'WEBSITE', label: 'Website', icon: 'mdi-web' },
  { value: 'OPARL_API', label: 'OParl API', icon: 'mdi-api' },
  { value: 'RSS', label: 'RSS Feed', icon: 'mdi-rss' },
  { value: 'CUSTOM_API', label: 'Custom API', icon: 'mdi-code-json' },
]
const bulkDialog = ref(false)
const deleteDialog = ref(false)
const categoryInfoDialog = ref(false)
const apiImportDialog = ref(false)
const aiDiscoveryDialog = ref(false)
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


// Debounced search
let searchTimeout: ReturnType<typeof setTimeout> | null = null
const debouncedLoadSources = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    loadSources(1)
  }, 300)
}


const filters = ref({
  category_id: null as string | null,
  source_type: null as string | null,
  status: null as string | null,
  search: '',
  tags: [] as string[],
})

// Computed property for active filters check
const hasActiveFilters = computed(() => {
  return !!(
    filters.value.category_id ||
    filters.value.source_type ||
    filters.value.status ||
    filters.value.tags.length > 0
  )
})

// Sidebar filter handlers
const onCategorySelect = (categoryId: string | null) => {
  filters.value.category_id = categoryId
  currentPage.value = 1
  loadSources(1)
}

const onTypeSelect = (type: string | null) => {
  filters.value.source_type = type
  currentPage.value = 1
  loadSources(1)
}

const onStatusSelect = (status: string | null) => {
  filters.value.status = status
  currentPage.value = 1
  loadSources(1)
}

const onTagsSelect = (tags: string[]) => {
  filters.value.tags = tags
  currentPage.value = 1
  loadSources(1)
}

const clearAllFilters = () => {
  filters.value.category_id = null
  filters.value.source_type = null
  filters.value.status = null
  filters.value.search = ''
  filters.value.tags = []
  currentPage.value = 1
  loadSources(1)
}

// Helper functions
const getCategoryName = (categoryId: string) => {
  const cat = sidebarCounts.value.categories.find(c => c.id === categoryId)
  return cat?.name || categoryId
}

// Load sidebar counts
const loadSidebarCounts = async () => {
  try {
    const response = await adminApi.getSourceCounts()
    sidebarCounts.value = response.data
  } catch (e) {
    console.error('Failed to load sidebar counts:', e)
  }
}

const formData = ref({
  category_id: '',  // Legacy - primary category
  category_ids: [] as string[],  // N:M categories
  name: '',
  source_type: 'WEBSITE',
  base_url: '',
  api_endpoint: '',
  tags: [] as string[],  // Tags for filtering/categorization
  crawl_config: {
    max_depth: 3,
    max_pages: 100,
    render_javascript: false,
    url_include_patterns: [] as string[],
    url_exclude_patterns: [] as string[],
  },
})

// Form validation state
const formValid = ref(false)
const saving = ref(false)
const form = ref<InstanceType<typeof import('vuetify/components').VForm> | null>(null)

// Validation rules
const nameRules = computed(() => [
  (v: string) => !!v || t('sources.validation.nameRequired'),
  (v: string) => (v && v.length >= 2) || t('sources.validation.nameTooShort'),
  (v: string) => (v && v.length <= 200) || t('sources.validation.nameTooLong'),
])

const urlRules = computed(() => [
  (v: string) => !!v || t('sources.validation.urlRequired'),
  (v: string) => isValidUrl(v) || t('sources.validation.urlInvalid'),
])

/**
 * Validate URL format
 */
const isValidUrl = (url: string): boolean => {
  if (!url) return false
  try {
    const parsed = new URL(url)
    return ['http:', 'https:'].includes(parsed.protocol)
  } catch {
    return false
  }
}

// Dynamic tag suggestions from existing DataSources
const availableTags = ref<{ tag: string; count: number }[]>([])

// Computed: tag labels for combobox (sorted by usage)
const tagSuggestions = computed(() => availableTags.value.map(t => t.tag))

// Load available tags from backend
const loadAvailableTags = async () => {
  try {
    const response = await adminApi.getAvailableTags()
    availableTags.value = response.data.tags || []
  } catch (e) {
    console.error('Failed to load available tags:', e)
  }
}

// Color mapping for tags based on type
const getTagColor = (tag: string): string => {
  const tagLower = tag?.toLowerCase() || ''
  // Geographic regions
  if (['nrw', 'bayern', 'baden-württemberg', 'niedersachsen', 'hessen', 'sachsen',
       'rheinland-pfalz', 'berlin', 'schleswig-holstein', 'brandenburg',
       'sachsen-anhalt', 'thüringen', 'hamburg', 'mecklenburg-vorpommern',
       'saarland', 'bremen', 'nordrhein-westfalen'].includes(tagLower)) {
    return 'blue'
  }
  // Countries
  if (['deutschland', 'österreich', 'schweiz', 'de', 'at', 'ch'].includes(tagLower)) {
    return 'indigo'
  }
  // Source types
  if (['kommunal', 'gemeinde', 'stadt', 'landkreis', 'landesebene', 'kreis'].includes(tagLower)) {
    return 'green'
  }
  return 'grey' // Default for custom tags
}

interface BulkImportPreviewItem {
  name: string
  base_url: string
  source_type: string
  tags: string[]
  allTags: string[]  // combined with default_tags
  error?: string
  duplicate?: boolean
}

const bulkImport = ref({
  category_ids: [] as string[],
  default_tags: [] as string[],
  inputMode: 'text' as 'text' | 'file',
  csvText: '',
  csvFile: null as File | null,
  preview: [] as BulkImportPreviewItem[],
  validCount: 0,
  duplicateCount: 0,
  errorCount: 0,
  importing: false,
  skip_duplicates: true,
})

// Computed properties for bulk import
const canPreview = computed(() => {
  if (bulkImport.value.inputMode === 'text') {
    return bulkImport.value.csvText.trim().length > 0
  }
  return bulkImport.value.csvFile !== null
})

const canImport = computed(() => {
  return bulkImport.value.category_ids.length > 0 && bulkImport.value.validCount > 0
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
    // Build params, only include tags if not empty
    const params: Record<string, any> = {
      ...filters.value,
      page,
      per_page: perPage,
    }
    // Don't send empty tags array
    if (!params.tags || params.tags.length === 0) {
      delete params.tags
    }
    const response = await adminApi.getSources(params)
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
    tags: [],
    crawl_config: {
      max_depth: 3,
      max_pages: 100,
      render_javascript: false,
      url_include_patterns: [],
      url_exclude_patterns: [],
    },
  }
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
    crawl_config: { ...defaultCrawlConfig, ...(source.crawl_config || {}) },
  }
  dialog.value = true
}

const saveSource = async () => {
  // Validate form before saving
  if (form.value) {
    const { valid } = await form.value.validate()
    if (!valid) {
      return
    }
  }

  saving.value = true

  try {
    if (editMode.value) {
      await adminApi.updateSource(selectedSource.value.id, formData.value)
    } else {
      await adminApi.createSource(formData.value)
    }
    dialog.value = false
    loadSources()
  } catch (error: unknown) {
    console.error('Failed to save source:', error)
    // Show error to user via snackbar or alert
    const err = error as { response?: { data?: { detail?: string } } }
    const message = err.response?.data?.detail || t('sources.errors.saveFailed')
    alert(message) // TODO: Replace with proper snackbar
  } finally {
    saving.value = false
  }
}

const openBulkImportDialog = () => {
  bulkImport.value = {
    category_ids: [],
    default_tags: [],
    inputMode: 'text',
    csvText: '',
    csvFile: null,
    preview: [],
    validCount: 0,
    duplicateCount: 0,
    errorCount: 0,
    importing: false,
    skip_duplicates: true,
  }
  bulkDialog.value = true
}

const closeBulkDialog = () => {
  bulkImport.value.preview = []
  bulkDialog.value = false
}

// Parse CSV file when selected
const onCsvFileSelected = async (files: File[] | null) => {
  if (!files || files.length === 0) return
  const file = files[0]

  try {
    const text = await file.text()
    bulkImport.value.csvText = text
    // Auto-parse preview when file is loaded
    parseBulkImportPreview()
  } catch (error) {
    console.error('Failed to read CSV file:', error)
  }
}

// Parse CSV text and create preview
const parseBulkImportPreview = async () => {
  const text = bulkImport.value.csvText
  if (!text.trim()) {
    bulkImport.value.preview = []
    return
  }

  const lines = text.split('\n').filter(l => l.trim())
  const existingUrls = new Set(sources.value.map(s => s.base_url?.toLowerCase()))
  const seenUrls = new Set<string>()

  const items: BulkImportPreviewItem[] = []
  let validCount = 0
  let duplicateCount = 0
  let errorCount = 0

  for (const line of lines) {
    // Skip header line if detected
    if (line.toLowerCase().includes('name;url') || line.toLowerCase().includes('name,url')) {
      continue
    }

    // Support both ; and , as delimiter
    const delimiter = line.includes(';') ? ';' : ','
    const parts = line.split(delimiter).map(p => p.trim())

    if (parts.length < 2) {
      // Try simple format: Name | URL or just URL
      const pipesParts = line.split('|').map(p => p.trim())
      if (pipesParts.length >= 2) {
        const [name, url] = pipesParts
        items.push({
          name,
          base_url: url,
          source_type: 'WEBSITE',
          tags: [],
          allTags: [...bulkImport.value.default_tags],
          error: !url.startsWith('http') ? 'Invalid URL' : undefined,
          duplicate: existingUrls.has(url.toLowerCase()) || seenUrls.has(url.toLowerCase()),
        })
        seenUrls.add(url.toLowerCase())
      } else if (line.startsWith('http')) {
        // Just URL
        items.push({
          name: new URL(line).hostname,
          base_url: line,
          source_type: 'WEBSITE',
          tags: [],
          allTags: [...bulkImport.value.default_tags],
          duplicate: existingUrls.has(line.toLowerCase()) || seenUrls.has(line.toLowerCase()),
        })
        seenUrls.add(line.toLowerCase())
      } else {
        items.push({
          name: line,
          base_url: '',
          source_type: 'WEBSITE',
          tags: [],
          allTags: [],
          error: 'Invalid format',
        })
      }
      continue
    }

    // CSV format: Name;URL;SourceType;Tags
    const [name, url, sourceType, tagsStr] = parts
    const itemTags = tagsStr ? tagsStr.split(',').map(t => t.trim()).filter(Boolean) : []
    const allTags = [...new Set([...bulkImport.value.default_tags, ...itemTags])]

    const item: BulkImportPreviewItem = {
      name: name || new URL(url || '').hostname,
      base_url: url || '',
      source_type: sourceType?.toUpperCase() || 'WEBSITE',
      tags: itemTags,
      allTags,
    }

    // Validate URL
    if (!url || !url.startsWith('http')) {
      item.error = 'Invalid URL'
    }

    // Check for duplicates
    if (!item.error && (existingUrls.has(url.toLowerCase()) || seenUrls.has(url.toLowerCase()))) {
      item.duplicate = true
    }

    if (!item.error) {
      seenUrls.add(url.toLowerCase())
    }

    items.push(item)
  }

  // Count statistics
  for (const item of items) {
    if (item.error) {
      errorCount++
    } else if (item.duplicate) {
      duplicateCount++
    } else {
      validCount++
    }
  }

  bulkImport.value.preview = items
  bulkImport.value.validCount = validCount
  bulkImport.value.duplicateCount = duplicateCount
  bulkImport.value.errorCount = errorCount
}

const executeBulkImport = async () => {
  if (!canImport.value) return

  bulkImport.value.importing = true

  try {
    // Filter valid items (not errors, and either not duplicates or skip_duplicates is false)
    const validItems = bulkImport.value.preview.filter(item => {
      if (item.error) return false
      if (item.duplicate && bulkImport.value.skip_duplicates) return false
      return true
    })

    // Build sources array for API
    const sourcesToImport = validItems.map(item => ({
      name: item.name,
      base_url: item.base_url,
      source_type: item.source_type,
      tags: item.tags,  // per-item tags (without default_tags - backend will merge)
    }))

    const result = await adminApi.bulkImportSources({
      category_ids: bulkImport.value.category_ids,
      default_tags: bulkImport.value.default_tags,
      sources: sourcesToImport,
      skip_duplicates: bulkImport.value.skip_duplicates,
    })

    // Show success message
    snackbarText.value = t('sources.messages.bulkImportSuccess', {
      imported: result.data.imported,
      skipped: result.data.skipped,
    })
    snackbarColor.value = 'success'
    snackbar.value = true

    bulkDialog.value = false
    loadSources()
    loadSidebarCounts()
    loadAvailableTags()
  } catch (error) {
    console.error('Bulk import failed:', error)
    snackbarText.value = t('sources.messages.bulkImportError')
    snackbarColor.value = 'error'
    snackbar.value = true
  } finally {
    bulkImport.value.importing = false
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

const onApiImported = (count: number) => {
  snackbarText.value = t('sources.messages.apiImportSuccess', { count })
  snackbarColor.value = 'success'
  snackbar.value = true
  loadSources()
  loadSidebarCounts()
  loadAvailableTags()
}

const onAiDiscoveryImported = (count: number) => {
  snackbarText.value = t('sources.aiDiscovery.importSuccess', { count })
  snackbarColor.value = 'success'
  snackbar.value = true
  loadSources()
  loadSidebarCounts()
  loadAvailableTags()
}

onMounted(() => {
  loadCategories()
  loadSidebarCounts()
  loadAvailableTags()

  // Check for query parameters to pre-filter
  if (route.query.category_id) {
    filters.value.category_id = route.query.category_id as string
  }
  if (route.query.source_type) {
    filters.value.source_type = route.query.source_type as string
  }
  if (route.query.status) {
    filters.value.status = route.query.status as string
  }

  loadSources()
})
</script>

<style scoped>
.sources-page {
  min-height: 100%;
}

.sources-main {
  padding: 16px;
  overflow-x: hidden;
}

.dialog-tabs {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

@media (max-width: 960px) {
  .sources-main {
    padding: 8px;
  }
}
</style>
