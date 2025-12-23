<template>
  <div class="facet-types-view">
    <v-container fluid>
      <!-- Header -->
      <PageHeader
        :title="t('admin.facetTypes.title')"
        :subtitle="t('admin.facetTypes.subtitle')"
        icon="mdi-tag-multiple"
      >
        <template #actions>
          <v-btn variant="tonal" color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">
            {{ t('admin.facetTypes.actions.create') }}
          </v-btn>
        </template>
      </PageHeader>

      <!-- Filters -->
      <v-card class="mb-4">
        <v-card-text>
          <v-row align="center">
            <v-col cols="12" md="4">
              <v-text-field
                v-model="filters.search"
                :label="t('common.search')"
                prepend-inner-icon="mdi-magnify"
                clearable
                hide-details
                @update:model-value="debouncedSearch"
              ></v-text-field>
            </v-col>
            <v-col cols="12" md="3">
              <v-select
                v-model="filters.entityTypeSlug"
                :items="entityTypeOptions"
                :label="t('admin.facetTypes.filters.entityType')"
                clearable
                hide-details
                @update:model-value="loadFacetTypes"
              ></v-select>
            </v-col>
            <v-col cols="12" md="2">
              <v-select
                v-model="filters.isActive"
                :items="activeOptions"
                :label="t('common.status')"
                clearable
                hide-details
                @update:model-value="loadFacetTypes"
              ></v-select>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <!-- Facet Types Table -->
      <v-card>
        <v-data-table
          :headers="headers"
          :items="facetTypes"
          :loading="loading"
          :items-per-page="25"
          class="elevation-0"
        >
          <template v-slot:item.icon="{ item }">
            <v-icon :icon="item.icon" :color="item.color" size="24"></v-icon>
          </template>

          <template v-slot:item.name="{ item }">
            <div>
              <strong>{{ item.name }}</strong>
              <div class="text-caption text-medium-emphasis">{{ item.slug }}</div>
            </div>
          </template>

          <template v-slot:item.applicable_entity_types="{ item }">
            <div class="d-flex flex-wrap gap-1">
              <v-chip
                v-for="slug in (item.applicable_entity_type_slugs || [])"
                :key="slug"
                size="x-small"
                variant="tonal"
              >
                {{ getEntityTypeName(slug) }}
              </v-chip>
              <v-chip
                v-if="!item.applicable_entity_type_slugs?.length"
                size="x-small"
                color="info"
                variant="tonal"
              >
                {{ t('admin.facetTypes.allTypes') }}
              </v-chip>
            </div>
          </template>

          <template v-slot:item.value_type="{ item }">
            <v-chip size="small" variant="outlined">
              {{ item.value_type }}
            </v-chip>
          </template>

          <template v-slot:item.value_count="{ item }">
            <v-chip size="small" variant="tonal">
              {{ item.value_count || 0 }}
            </v-chip>
          </template>

          <template v-slot:item.ai_extraction_enabled="{ item }">
            <v-icon
              :icon="item.ai_extraction_enabled ? 'mdi-robot' : 'mdi-robot-off'"
              :color="item.ai_extraction_enabled ? 'success' : 'grey'"
              size="small"
            ></v-icon>
          </template>

          <template v-slot:item.is_system="{ item }">
            <v-icon
              v-if="item.is_system"
              color="warning"
              icon="mdi-lock"
              size="small"
              :title="t('admin.facetTypes.systemType')"
            ></v-icon>
            <span v-else>-</span>
          </template>

          <template v-slot:item.is_active="{ item }">
            <v-icon
              :icon="item.is_active ? 'mdi-check-circle' : 'mdi-close-circle'"
              :color="item.is_active ? 'success' : 'error'"
              size="small"
            ></v-icon>
          </template>

          <template v-slot:item.actions="{ item }">
            <div class="d-flex justify-end ga-1">
              <v-btn icon="mdi-pencil" size="small" variant="tonal" :title="t('common.edit')" :aria-label="t('common.edit')" @click="openEditDialog(item)"></v-btn>
              <v-btn icon="mdi-delete" size="small" variant="tonal" color="error" :title="t('common.delete')" :aria-label="t('common.delete')" :disabled="item.is_system || (item.value_count || 0) > 0" @click="confirmDelete(item)"></v-btn>
            </div>
          </template>
        </v-data-table>
      </v-card>

      <!-- Create/Edit Dialog -->
      <v-dialog v-model="dialog" max-width="900" persistent scrollable>
        <v-card>
          <v-card-title class="d-flex align-center pa-4 bg-primary">
            <v-avatar :color="form.color || 'secondary'" size="40" class="mr-3">
              <v-icon :icon="form.icon || 'mdi-tag'" :color="getContrastColor(form.color || 'secondary')"></v-icon>
            </v-avatar>
            <div>
              <div class="text-h6">{{ editingItem ? t('admin.facetTypes.dialog.editTitle') : t('admin.facetTypes.dialog.createTitle') }}</div>
              <div v-if="form.name" class="text-caption opacity-80">{{ form.name }}</div>
            </div>
          </v-card-title>

          <v-tabs v-model="activeTab" class="dialog-tabs">
            <v-tab value="basic">
              <v-icon start>mdi-form-textbox</v-icon>
              {{ t('admin.facetTypes.tabs.basic') }}
            </v-tab>
            <v-tab value="appearance">
              <v-icon start>mdi-palette</v-icon>
              {{ t('admin.facetTypes.tabs.appearance') }}
            </v-tab>
            <v-tab value="schema">
              <v-icon start>mdi-code-json</v-icon>
              {{ t('admin.facetTypes.tabs.schema') }}
            </v-tab>
            <v-tab value="ai">
              <v-icon start>mdi-robot</v-icon>
              {{ t('admin.facetTypes.tabs.ai') }}
              <v-icon v-if="form.ai_extraction_enabled" size="x-small" color="success" class="ml-1">mdi-check-circle</v-icon>
            </v-tab>
          </v-tabs>

          <v-card-text class="pa-6 dialog-content-lg">
            <v-form ref="formRef" @submit.prevent="save">
              <v-window v-model="activeTab">
                <!-- Basic Tab -->
                <v-window-item value="basic">
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="form.name"
                        :label="t('admin.facetTypes.form.name')"
                        :rules="[v => !!v || t('admin.facetTypes.form.nameRequired')]"
                        :placeholder="t('admin.facetTypes.form.namePlaceholder')"
                        variant="outlined"
                      ></v-text-field>
                    </v-col>
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="form.name_plural"
                        :label="t('admin.facetTypes.form.namePlural')"
                        :placeholder="t('admin.facetTypes.form.namePluralPlaceholder')"
                        variant="outlined"
                      ></v-text-field>
                    </v-col>
                  </v-row>

                  <v-textarea
                    v-model="form.description"
                    :label="t('admin.facetTypes.form.description')"
                    rows="2"
                    variant="outlined"
                  ></v-textarea>

                  <v-select
                    v-model="form.applicable_entity_type_slugs"
                    :items="entityTypes"
                    :label="t('admin.facetTypes.form.applicableEntityTypes')"
                    :hint="t('admin.facetTypes.form.applicableEntityTypesHint')"
                    item-title="name"
                    item-value="slug"
                    multiple
                    chips
                    closable-chips
                    persistent-hint
                    variant="outlined"
                  ></v-select>

                  <!-- Preview -->
                  <v-card variant="outlined" class="mt-4">
                    <v-card-title class="text-subtitle-2 pb-2">
                      <v-icon start size="small">mdi-eye</v-icon>
                      {{ t('admin.facetTypes.form.preview') }}
                    </v-card-title>
                    <v-card-text>
                      <div class="d-flex align-center ga-3">
                        <v-avatar :color="form.color || 'secondary'" size="40">
                          <v-icon :icon="form.icon || 'mdi-tag'" :color="getContrastColor(form.color || 'secondary')"></v-icon>
                        </v-avatar>
                        <div>
                          <div class="text-body-1 font-weight-medium">{{ form.name || t('admin.facetTypes.form.namePlaceholder') }}</div>
                          <div class="text-caption text-medium-emphasis">{{ form.name_plural || (form.name ? form.name + 's' : '') }}</div>
                        </div>
                        <v-chip v-if="form.value_type" size="small" variant="outlined" class="ml-auto">
                          {{ form.value_type }}
                        </v-chip>
                      </div>
                    </v-card-text>
                  </v-card>
                </v-window-item>

                <!-- Appearance Tab -->
                <v-window-item value="appearance">
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="form.icon"
                        :label="t('admin.facetTypes.form.icon')"
                        :placeholder="t('admin.facetTypes.form.iconPlaceholder')"
                        variant="outlined"
                      >
                        <template v-slot:prepend-inner>
                          <v-icon :icon="form.icon || 'mdi-help'" :color="form.color"></v-icon>
                        </template>
                      </v-text-field>
                      <v-alert type="info" variant="tonal" density="compact" class="mt-2">
                        {{ t('admin.facetTypes.form.iconHint') }}
                      </v-alert>

                      <!-- Icon Suggestions -->
                      <v-card variant="outlined" class="mt-4">
                        <v-card-title class="text-subtitle-2 pb-2">
                          <v-icon start size="small">mdi-lightbulb</v-icon>
                          {{ t('admin.facetTypes.form.iconSuggestions') }}
                        </v-card-title>
                        <v-card-text>
                          <div class="d-flex flex-wrap ga-2">
                            <v-btn
                              v-for="icon in suggestedFacetIcons"
                              :key="icon"
                              :icon="icon"
                              size="small"
                              :variant="form.icon === icon ? 'flat' : 'tonal'"
                              :color="form.icon === icon ? 'primary' : undefined"
                              @click="form.icon = icon"
                            ></v-btn>
                          </div>
                        </v-card-text>
                      </v-card>
                    </v-col>
                    <v-col cols="12" md="6">
                      <v-label class="mb-2">{{ t('admin.facetTypes.form.color') }}</v-label>
                      <v-color-picker
                        v-model="form.color"
                        mode="hexa"
                        show-swatches
                        swatches-max-height="120"
                        hide-inputs
                      ></v-color-picker>
                    </v-col>
                  </v-row>
                </v-window-item>

                <!-- Schema Tab -->
                <v-window-item value="schema">
                  <!-- AI Schema Generator -->
                  <v-card variant="tonal" color="info" class="mb-4">
                    <v-card-text class="d-flex align-center">
                      <v-avatar color="info-darken-1" size="40" class="mr-3">
                        <v-icon color="on-info">mdi-auto-fix</v-icon>
                      </v-avatar>
                      <div class="flex-grow-1">
                        <div class="text-body-1 font-weight-medium">{{ t('admin.facetTypes.form.aiSchemaGenerator') }}</div>
                        <div class="text-caption">{{ t('admin.facetTypes.form.aiSchemaGeneratorHint') }}</div>
                      </div>
                      <v-btn
                        color="info-darken-1"
                        :loading="generatingSchema"
                        :disabled="!form.name"
                        @click="generateSchemaWithAI"
                      >
                        <v-icon start>mdi-creation</v-icon>
                        {{ t('admin.facetTypes.form.generateSchema') }}
                      </v-btn>
                    </v-card-text>
                  </v-card>

                  <v-row>
                    <v-col cols="12" sm="6">
                      <v-select
                        v-model="form.value_type"
                        :items="valueTypeOptions"
                        :label="t('admin.facetTypes.form.valueType')"
                        variant="outlined"
                        density="comfortable"
                      ></v-select>
                    </v-col>
                    <v-col cols="12" sm="6">
                      <v-select
                        v-model="form.aggregation_method"
                        :items="aggregationOptions"
                        :label="t('admin.facetTypes.form.aggregationMethod')"
                        variant="outlined"
                        density="comfortable"
                      ></v-select>
                    </v-col>
                  </v-row>

                  <v-alert type="info" variant="tonal" class="mb-4">
                    {{ t('admin.facetTypes.form.schemaInfo') }}
                  </v-alert>

                  <v-textarea
                    v-model="schemaJson"
                    :label="t('admin.facetTypes.form.valueSchema')"
                    :placeholder="t('admin.facetTypes.form.valueSchemePlaceholder')"
                    rows="10"
                    variant="outlined"
                    style="font-family: monospace;"
                    :error-messages="schemaError"
                  ></v-textarea>

                  <v-combobox
                    v-model="form.deduplication_fields"
                    :label="t('admin.facetTypes.form.deduplicationFields')"
                    :hint="t('admin.facetTypes.form.deduplicationFieldsHint')"
                    multiple
                    chips
                    closable-chips
                    persistent-hint
                    variant="outlined"
                    class="mt-4"
                  ></v-combobox>

                  <v-row class="mt-4">
                    <v-col cols="12" md="6">
                      <v-card variant="outlined" class="pa-4">
                        <v-switch
                          v-model="form.is_time_based"
                          :label="t('admin.facetTypes.form.isTimeBased')"
                          color="primary"
                          hide-details
                        ></v-switch>
                        <div class="text-caption text-medium-emphasis mt-2">
                          {{ t('admin.facetTypes.form.isTimeBasedHint') }}
                        </div>
                        <v-text-field
                          v-if="form.is_time_based"
                          v-model="form.time_field_path"
                          :label="t('admin.facetTypes.form.timeFieldPath')"
                          :placeholder="t('admin.facetTypes.form.timeFieldPathPlaceholder')"
                          variant="outlined"
                          density="compact"
                          class="mt-3"
                        ></v-text-field>
                      </v-card>
                    </v-col>
                    <v-col cols="12" md="6">
                      <v-row>
                        <v-col cols="6">
                          <v-number-input
                            v-model="form.display_order"
                            :label="t('admin.facetTypes.form.displayOrder')"
                            :min="0"
                            variant="outlined"
                            control-variant="stacked"
                          ></v-number-input>
                        </v-col>
                        <v-col cols="6">
                          <v-card variant="outlined" class="pa-4 h-100 d-flex align-center">
                            <v-switch
                              v-model="form.is_active"
                              :label="t('common.active')"
                              color="success"
                              hide-details
                            ></v-switch>
                          </v-card>
                        </v-col>
                      </v-row>
                    </v-col>
                  </v-row>
                </v-window-item>

                <!-- AI Tab -->
                <v-window-item value="ai">
                  <v-card variant="outlined" class="mb-4">
                    <v-card-text class="d-flex align-center">
                      <v-avatar color="info" size="48" class="mr-4">
                        <v-icon color="on-info">mdi-robot</v-icon>
                      </v-avatar>
                      <div class="flex-grow-1">
                        <div class="text-body-1 font-weight-medium">{{ t('admin.facetTypes.form.aiExtractionEnabled') }}</div>
                        <div class="text-caption text-medium-emphasis">{{ t('admin.facetTypes.form.aiExtractionEnabledHint') }}</div>
                      </div>
                      <v-switch
                        v-model="form.ai_extraction_enabled"
                        color="info"
                        hide-details
                      ></v-switch>
                    </v-card-text>
                  </v-card>

                  <v-expand-transition>
                    <div v-if="form.ai_extraction_enabled">
                      <v-alert type="info" variant="tonal" class="mb-4">
                        {{ t('admin.facetTypes.form.aiPromptInfo') }}
                      </v-alert>

                      <v-textarea
                        v-model="form.ai_extraction_prompt"
                        :label="t('admin.facetTypes.form.aiExtractionPrompt')"
                        :placeholder="t('admin.facetTypes.form.aiExtractionPromptPlaceholder')"
                        rows="12"
                        variant="outlined"
                      ></v-textarea>
                    </div>
                  </v-expand-transition>

                  <v-alert v-if="!form.ai_extraction_enabled" type="warning" variant="tonal" class="mt-4">
                    {{ t('admin.facetTypes.form.aiDisabledInfo') }}
                  </v-alert>
                </v-window-item>
              </v-window>
            </v-form>
          </v-card-text>

          <v-divider></v-divider>

          <v-card-actions class="pa-4">
            <v-btn variant="tonal" @click="closeDialog">{{ t('common.cancel') }}</v-btn>
            <v-spacer></v-spacer>
            <v-btn variant="tonal" color="primary" :loading="saving" @click="save">
              <v-icon start>mdi-check</v-icon>
              {{ editingItem ? t('common.save') : t('common.create') }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <!-- Delete Confirmation Dialog -->
      <v-dialog v-model="deleteDialog" max-width="400">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon color="error" class="mr-2">mdi-alert</v-icon>
            {{ t('admin.facetTypes.dialog.deleteTitle') }}
          </v-card-title>
          <v-card-text>
            {{ t('admin.facetTypes.dialog.deleteConfirm', { name: itemToDelete?.name }) }}
          </v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn variant="tonal" @click="deleteDialog = false">{{ t('common.cancel') }}</v-btn>
            <v-btn variant="tonal" color="error" :loading="deleting" @click="deleteItem">{{ t('common.delete') }}</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </v-container>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { facetApi, entityApi } from '@/services/api'
import { useSnackbar } from '@/composables/useSnackbar'
import { getContrastColor } from '@/composables/useColorHelpers'
import PageHeader from '@/components/common/PageHeader.vue'

const { t } = useI18n()
const { showSuccess, showError } = useSnackbar()

// Simple debounce function
function debounce<T extends (...args: any[]) => any>(fn: T, delay: number): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null
  return (...args: Parameters<T>) => {
    if (timeoutId) clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn(...args), delay)
  }
}

// State
const facetTypes = ref<any[]>([])
const entityTypes = ref<any[]>([])
const loading = ref(false)
const dialog = ref(false)
const deleteDialog = ref(false)
const editingItem = ref<any>(null)
const itemToDelete = ref<any>(null)
const saving = ref(false)
const deleting = ref(false)
const formRef = ref<any>(null)
const activeTab = ref('basic')
const schemaJson = ref('')
const schemaError = ref('')
const generatingSchema = ref(false)

// Suggested icons for facet types
const suggestedFacetIcons = [
  'mdi-tag',
  'mdi-label',
  'mdi-account',
  'mdi-calendar',
  'mdi-clock',
  'mdi-map-marker',
  'mdi-phone',
  'mdi-email',
  'mdi-link',
  'mdi-file-document',
  'mdi-currency-eur',
  'mdi-chart-line',
  'mdi-alert',
  'mdi-lightbulb',
  'mdi-check-circle',
  'mdi-information',
  'mdi-star',
  'mdi-heart',
  'mdi-flag',
  'mdi-bookmark',
]

const filters = ref({
  search: '',
  entityTypeSlug: null as string | null,
  isActive: null as boolean | null,
})

const form = ref({
  name: '',
  name_plural: '',
  description: '',
  icon: 'mdi-tag',
  color: '#9E9E9E',
  value_type: 'structured',
  value_schema: null as any,
  applicable_entity_type_slugs: [] as string[],
  aggregation_method: 'dedupe',
  deduplication_fields: [] as string[],
  is_time_based: false,
  time_field_path: '',
  default_time_filter: 'all',
  ai_extraction_enabled: true,
  ai_extraction_prompt: '',
  is_active: true,
  display_order: 0,
})

const headers = computed(() => [
  { title: '', key: 'icon', width: '50px', sortable: false },
  { title: t('admin.facetTypes.columns.name'), key: 'name' },
  { title: t('admin.facetTypes.columns.entityTypes'), key: 'applicable_entity_types', sortable: false },
  { title: t('admin.facetTypes.columns.valueType'), key: 'value_type', width: '120px' },
  { title: t('admin.facetTypes.columns.values'), key: 'value_count', width: '100px', align: 'center' as const },
  { title: t('admin.facetTypes.columns.ai'), key: 'ai_extraction_enabled', width: '60px', align: 'center' as const },
  { title: t('admin.facetTypes.columns.system'), key: 'is_system', width: '80px', align: 'center' as const },
  { title: t('admin.facetTypes.columns.active'), key: 'is_active', width: '80px', align: 'center' as const },
  { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' as const },
])

const valueTypeOptions = [
  { title: 'Text', value: 'text' },
  { title: 'Structured', value: 'structured' },
  { title: 'List', value: 'list' },
  { title: 'Reference', value: 'reference' },
]

const aggregationOptions = [
  { title: 'Count', value: 'count' },
  { title: 'Sum', value: 'sum' },
  { title: 'Average', value: 'avg' },
  { title: 'List', value: 'list' },
  { title: 'Deduplicate', value: 'dedupe' },
]

const activeOptions = computed(() => [
  { title: t('common.active'), value: true },
  { title: t('common.inactive'), value: false },
])

const entityTypeOptions = computed(() =>
  entityTypes.value.map(et => ({
    title: et.name,
    value: et.slug,
  }))
)

// Methods
async function loadFacetTypes() {
  loading.value = true
  try {
    const params: any = { per_page: 100 }
    if (filters.value.search) params.search = filters.value.search
    if (filters.value.isActive !== null) params.is_active = filters.value.isActive

    const response = await facetApi.getFacetTypes(params)
    let items = response.data.items || []

    // Filter by entity type if selected
    if (filters.value.entityTypeSlug) {
      items = items.filter((ft: any) =>
        !ft.applicable_entity_type_slugs?.length ||
        ft.applicable_entity_type_slugs.includes(filters.value.entityTypeSlug)
      )
    }

    facetTypes.value = items
  } catch (e) {
    console.error('Failed to load facet types', e)
    showError(t('admin.facetTypes.messages.loadError'))
  } finally {
    loading.value = false
  }
}

async function loadEntityTypes() {
  try {
    const response = await entityApi.getEntityTypes({ per_page: 100, is_active: true })
    entityTypes.value = response.data.items || []
  } catch (e) {
    console.error('Failed to load entity types', e)
  }
}

const debouncedSearch = debounce(() => {
  loadFacetTypes()
}, 300)

function getEntityTypeName(slug: string): string {
  const et = entityTypes.value.find(e => e.slug === slug)
  return et?.name || slug
}

function openCreateDialog() {
  editingItem.value = null
  activeTab.value = 'basic'
  schemaJson.value = ''
  schemaError.value = ''
  form.value = {
    name: '',
    name_plural: '',
    description: '',
    icon: 'mdi-tag',
    color: '#9E9E9E',
    value_type: 'structured',
    value_schema: null,
    applicable_entity_type_slugs: [],
    aggregation_method: 'dedupe',
    deduplication_fields: [],
    is_time_based: false,
    time_field_path: '',
    default_time_filter: 'all',
    ai_extraction_enabled: true,
    ai_extraction_prompt: '',
    is_active: true,
    display_order: 0,
  }
  dialog.value = true
}

function openEditDialog(item: any) {
  editingItem.value = item
  activeTab.value = 'basic'
  schemaError.value = ''
  // Convert Vuetify color names to HEX for the color picker
  const colorValue = item.color || '#9E9E9E'
  const resolvedColor = colorValue.startsWith('#') ? colorValue : '#9E9E9E'
  form.value = {
    name: item.name,
    name_plural: item.name_plural || '',
    description: item.description || '',
    icon: item.icon || 'mdi-tag',
    color: resolvedColor,
    value_type: item.value_type || 'structured',
    value_schema: item.value_schema,
    applicable_entity_type_slugs: item.applicable_entity_type_slugs || [],
    aggregation_method: item.aggregation_method || 'dedupe',
    deduplication_fields: item.deduplication_fields || [],
    is_time_based: item.is_time_based ?? false,
    time_field_path: item.time_field_path || '',
    default_time_filter: item.default_time_filter || 'all',
    ai_extraction_enabled: item.ai_extraction_enabled ?? true,
    ai_extraction_prompt: item.ai_extraction_prompt || '',
    is_active: item.is_active ?? true,
    display_order: item.display_order ?? 0,
  }
  schemaJson.value = item.value_schema ? JSON.stringify(item.value_schema, null, 2) : ''
  dialog.value = true
}

function closeDialog() {
  dialog.value = false
  editingItem.value = null
}

// Watch schema JSON for validation
watch(schemaJson, (val) => {
  if (!val) {
    form.value.value_schema = null
    schemaError.value = ''
    return
  }
  try {
    form.value.value_schema = JSON.parse(val)
    schemaError.value = ''
  } catch (e) {
    schemaError.value = t('admin.facetTypes.form.invalidJson')
  }
})

async function save() {
  if (!formRef.value?.validate()) return
  if (schemaError.value) {
    showError(t('admin.facetTypes.form.invalidJson'))
    return
  }

  saving.value = true
  try {
    const data = {
      ...form.value,
      name_plural: form.value.name_plural || `${form.value.name}s`,
    }

    if (editingItem.value) {
      await facetApi.updateFacetType(editingItem.value.id, data)
      showSuccess(t('admin.facetTypes.messages.updated'))
    } else {
      await facetApi.createFacetType(data)
      showSuccess(t('admin.facetTypes.messages.created'))
    }

    closeDialog()
    await loadFacetTypes()
  } catch (e: any) {
    const detail = e.response?.data?.detail || t('admin.facetTypes.messages.saveError')
    showError(detail)
  } finally {
    saving.value = false
  }
}

function confirmDelete(item: any) {
  itemToDelete.value = item
  deleteDialog.value = true
}

async function deleteItem() {
  if (!itemToDelete.value) return

  deleting.value = true
  try {
    await facetApi.deleteFacetType(itemToDelete.value.id)
    showSuccess(t('admin.facetTypes.messages.deleted', { name: itemToDelete.value.name }))
    deleteDialog.value = false
    itemToDelete.value = null
    await loadFacetTypes()
  } catch (e: any) {
    const detail = e.response?.data?.detail || t('admin.facetTypes.messages.deleteError')
    showError(detail)
  } finally {
    deleting.value = false
  }
}

async function generateSchemaWithAI() {
  if (!form.value.name) {
    showError(t('admin.facetTypes.form.nameRequired'))
    return
  }

  generatingSchema.value = true
  try {
    // Get entity type names for context
    const entityTypeNames = form.value.applicable_entity_type_slugs
      .map(slug => entityTypes.value.find(et => et.slug === slug)?.name || slug)

    const response = await facetApi.generateFacetTypeSchema({
      name: form.value.name,
      name_plural: form.value.name_plural,
      description: form.value.description,
      applicable_entity_types: entityTypeNames,
    })

    const generated = response.data

    // Apply generated values
    if (generated.value_schema) {
      form.value.value_schema = generated.value_schema
      schemaJson.value = JSON.stringify(generated.value_schema, null, 2)
    }
    if (generated.value_type) {
      form.value.value_type = generated.value_type
    }
    if (generated.deduplication_fields) {
      form.value.deduplication_fields = generated.deduplication_fields
    }
    if (generated.is_time_based !== undefined) {
      form.value.is_time_based = generated.is_time_based
    }
    if (generated.time_field_path) {
      form.value.time_field_path = generated.time_field_path
    }
    if (generated.ai_extraction_prompt) {
      form.value.ai_extraction_prompt = generated.ai_extraction_prompt
    }
    if (generated.icon) {
      form.value.icon = generated.icon
    }
    if (generated.color) {
      form.value.color = generated.color
    }

    showSuccess(t('admin.facetTypes.messages.schemaGenerated'))
  } catch (e: any) {
    const detail = e.response?.data?.detail || t('admin.facetTypes.messages.schemaGenerationError')
    showError(detail)
  } finally {
    generatingSchema.value = false
  }
}

// Init
onMounted(() => {
  loadEntityTypes()
  loadFacetTypes()
})
</script>

<style scoped>
.facet-types-view {
  min-height: 100%;
}

.dialog-tabs {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
