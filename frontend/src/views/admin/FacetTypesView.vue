<template>
  <div class="facet-types-view">
    <v-container fluid>
      <!-- Header -->
      <v-row class="mb-4">
        <v-col>
          <div class="d-flex align-center justify-space-between">
            <div>
              <h1 class="text-h4 mb-1">{{ t('admin.facetTypes.title') }}</h1>
              <p class="text-body-2 text-medium-emphasis">
                {{ t('admin.facetTypes.subtitle') }}
              </p>
            </div>
            <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">
              {{ t('admin.facetTypes.actions.create') }}
            </v-btn>
          </div>
        </v-col>
      </v-row>

      <!-- Filters -->
      <v-card class="mb-4">
        <v-card-text>
          <v-row>
            <v-col cols="12" md="4">
              <v-text-field
                v-model="filters.search"
                :label="t('common.search')"
                prepend-inner-icon="mdi-magnify"
                clearable
                hide-details
                density="compact"
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
                density="compact"
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
                density="compact"
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
            <div class="d-flex gap-1">
              <v-btn
                icon="mdi-pencil"
                size="small"
                variant="text"
                @click="openEditDialog(item)"
                :title="t('common.edit')"
              ></v-btn>
              <v-btn
                icon="mdi-delete"
                size="small"
                variant="text"
                color="error"
                :disabled="item.is_system || (item.value_count || 0) > 0"
                @click="confirmDelete(item)"
                :title="getDeleteTooltip(item)"
              ></v-btn>
            </div>
          </template>
        </v-data-table>
      </v-card>

      <!-- Create/Edit Dialog -->
      <v-dialog v-model="dialog" max-width="800" persistent scrollable>
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon :icon="editingItem ? 'mdi-pencil' : 'mdi-plus'" class="mr-2"></v-icon>
            {{ editingItem ? t('admin.facetTypes.dialog.editTitle') : t('admin.facetTypes.dialog.createTitle') }}
          </v-card-title>
          <v-card-text>
            <v-form ref="formRef" @submit.prevent="save">
              <v-tabs v-model="activeTab" class="mb-4">
                <v-tab value="basic">{{ t('admin.facetTypes.tabs.basic') }}</v-tab>
                <v-tab value="schema">{{ t('admin.facetTypes.tabs.schema') }}</v-tab>
                <v-tab value="ai">{{ t('admin.facetTypes.tabs.ai') }}</v-tab>
              </v-tabs>

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
                      ></v-text-field>
                    </v-col>
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="form.name_plural"
                        :label="t('admin.facetTypes.form.namePlural')"
                        :placeholder="t('admin.facetTypes.form.namePluralPlaceholder')"
                      ></v-text-field>
                    </v-col>
                  </v-row>

                  <v-textarea
                    v-model="form.description"
                    :label="t('admin.facetTypes.form.description')"
                    rows="2"
                  ></v-textarea>

                  <v-row>
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="form.icon"
                        :label="t('admin.facetTypes.form.icon')"
                        :placeholder="t('admin.facetTypes.form.iconPlaceholder')"
                        :hint="t('admin.facetTypes.form.iconHint')"
                        persistent-hint
                      >
                        <template v-slot:prepend-inner>
                          <v-icon :icon="form.icon || 'mdi-help'" size="small"></v-icon>
                        </template>
                      </v-text-field>
                    </v-col>
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="form.color"
                        :label="t('admin.facetTypes.form.color')"
                        type="color"
                      >
                        <template v-slot:prepend-inner>
                          <div
                            :style="{ backgroundColor: form.color, width: '20px', height: '20px', borderRadius: '4px' }"
                          ></div>
                        </template>
                      </v-text-field>
                    </v-col>
                  </v-row>

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
                  ></v-select>

                  <v-row class="mt-2">
                    <v-col cols="12" md="4">
                      <v-select
                        v-model="form.value_type"
                        :items="valueTypeOptions"
                        :label="t('admin.facetTypes.form.valueType')"
                      ></v-select>
                    </v-col>
                    <v-col cols="12" md="4">
                      <v-select
                        v-model="form.aggregation_method"
                        :items="aggregationOptions"
                        :label="t('admin.facetTypes.form.aggregationMethod')"
                      ></v-select>
                    </v-col>
                    <v-col cols="12" md="4">
                      <v-text-field
                        v-model.number="form.display_order"
                        :label="t('admin.facetTypes.form.displayOrder')"
                        type="number"
                        min="0"
                      ></v-text-field>
                    </v-col>
                  </v-row>

                  <v-row>
                    <v-col cols="12" md="4">
                      <v-checkbox
                        v-model="form.is_time_based"
                        :label="t('admin.facetTypes.form.isTimeBased')"
                        :hint="t('admin.facetTypes.form.isTimeBasedHint')"
                        persistent-hint
                      ></v-checkbox>
                    </v-col>
                    <v-col cols="12" md="4">
                      <v-checkbox
                        v-model="form.is_active"
                        :label="t('common.active')"
                      ></v-checkbox>
                    </v-col>
                  </v-row>

                  <v-text-field
                    v-if="form.is_time_based"
                    v-model="form.time_field_path"
                    :label="t('admin.facetTypes.form.timeFieldPath')"
                    :placeholder="t('admin.facetTypes.form.timeFieldPathPlaceholder')"
                    class="mt-2"
                  ></v-text-field>
                </v-window-item>

                <!-- Schema Tab -->
                <v-window-item value="schema">
                  <v-alert type="info" variant="tonal" class="mb-4">
                    {{ t('admin.facetTypes.form.schemaInfo') }}
                  </v-alert>
                  <v-textarea
                    v-model="schemaJson"
                    :label="t('admin.facetTypes.form.valueSchema')"
                    :placeholder="t('admin.facetTypes.form.valueSchemePlaceholder')"
                    rows="12"
                    font="monospace"
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
                    class="mt-4"
                  ></v-combobox>
                </v-window-item>

                <!-- AI Tab -->
                <v-window-item value="ai">
                  <v-checkbox
                    v-model="form.ai_extraction_enabled"
                    :label="t('admin.facetTypes.form.aiExtractionEnabled')"
                    :hint="t('admin.facetTypes.form.aiExtractionEnabledHint')"
                    persistent-hint
                  ></v-checkbox>

                  <v-textarea
                    v-if="form.ai_extraction_enabled"
                    v-model="form.ai_extraction_prompt"
                    :label="t('admin.facetTypes.form.aiExtractionPrompt')"
                    :placeholder="t('admin.facetTypes.form.aiExtractionPromptPlaceholder')"
                    rows="8"
                    class="mt-4"
                  ></v-textarea>
                </v-window-item>
              </v-window>
            </v-form>
          </v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn @click="closeDialog">{{ t('common.cancel') }}</v-btn>
            <v-btn color="primary" :loading="saving" @click="save">
              {{ editingItem ? t('common.save') : t('common.create') }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <!-- Delete Confirmation Dialog -->
      <v-dialog v-model="deleteDialog" max-width="400">
        <v-card>
          <v-card-title class="text-h6">
            <v-icon color="error" class="mr-2">mdi-alert</v-icon>
            {{ t('admin.facetTypes.dialog.deleteTitle') }}
          </v-card-title>
          <v-card-text>
            {{ t('admin.facetTypes.dialog.deleteConfirm', { name: itemToDelete?.name }) }}
          </v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn @click="deleteDialog = false">{{ t('common.cancel') }}</v-btn>
            <v-btn color="error" :loading="deleting" @click="deleteItem">{{ t('common.delete') }}</v-btn>
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
import { useDebounceFn } from '@vueuse/core'

const { t } = useI18n()
const { showSuccess, showError } = useSnackbar()

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
  color: '#607D8B',
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
  { title: t('common.actions'), key: 'actions', width: '120px', sortable: false },
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

const debouncedSearch = useDebounceFn(() => {
  loadFacetTypes()
}, 300)

function getEntityTypeName(slug: string): string {
  const et = entityTypes.value.find(e => e.slug === slug)
  return et?.name || slug
}

function getDeleteTooltip(item: any): string {
  if (item.is_system) return t('admin.facetTypes.cannotDeleteSystem')
  if ((item.value_count || 0) > 0) return t('admin.facetTypes.hasValues')
  return t('common.delete')
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
    color: '#607D8B',
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
  form.value = {
    name: item.name,
    name_plural: item.name_plural || '',
    description: item.description || '',
    icon: item.icon || 'mdi-tag',
    color: item.color || '#607D8B',
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
</style>
