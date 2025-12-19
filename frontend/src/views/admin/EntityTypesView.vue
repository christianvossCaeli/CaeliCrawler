<template>
  <div class="entity-types-view">
    <v-container fluid>
      <!-- Header -->
      <v-row class="mb-4">
        <v-col>
          <div class="d-flex align-center justify-space-between">
            <div>
              <h1 class="text-h4 mb-1">{{ t('admin.entityTypes.title') }}</h1>
              <p class="text-body-2 text-medium-emphasis">
                {{ t('admin.entityTypes.subtitle') }}
              </p>
            </div>
            <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">
              {{ t('admin.entityTypes.actions.create') }}
            </v-btn>
          </div>
        </v-col>
      </v-row>

      <!-- Entity Types Table -->
      <v-card>
        <v-data-table
          :headers="headers"
          :items="entityTypes"
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
              <div class="text-caption text-medium-emphasis">{{ item.name_plural }}</div>
            </div>
          </template>

          <template v-slot:item.facets="{ item }">
            <div class="d-flex flex-wrap gap-1">
              <v-chip
                v-for="facet in getFacetsForEntityType(item.slug)"
                :key="facet.id"
                size="x-small"
                :color="facet.color"
                variant="tonal"
              >
                <v-icon :icon="facet.icon" size="x-small" start></v-icon>
                {{ facet.name }}
              </v-chip>
              <v-chip
                v-if="getFacetsForEntityType(item.slug).length === 0"
                size="x-small"
                color="grey"
                variant="outlined"
              >
                {{ t('common.none') }}
              </v-chip>
            </div>
          </template>

          <template v-slot:item.color="{ item }">
            <v-chip :color="item.color" size="small" variant="flat">
              {{ item.color }}
            </v-chip>
          </template>

          <template v-slot:item.entity_count="{ item }">
            <v-chip size="small" variant="tonal">
              {{ item.entity_count || 0 }}
            </v-chip>
          </template>

          <template v-slot:item.is_system="{ item }">
            <v-icon v-if="item.is_system" color="warning" icon="mdi-lock" size="small" :title="t('admin.entityTypes.systemType')"></v-icon>
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
                :disabled="item.is_system || (item.entity_count || 0) > 0"
                @click="confirmDelete(item)"
                :title="item.is_system ? t('admin.entityTypes.cannotDeleteSystem') : (item.entity_count || 0) > 0 ? t('admin.entityTypes.hasEntities') : t('common.delete')"
              ></v-btn>
            </div>
          </template>
        </v-data-table>
      </v-card>

      <!-- Create/Edit Dialog -->
      <v-dialog v-model="dialog" max-width="600" persistent>
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon :icon="editingItem ? 'mdi-pencil' : 'mdi-plus'" class="mr-2"></v-icon>
            {{ editingItem ? t('admin.entityTypes.dialog.editTitle') : t('admin.entityTypes.dialog.createTitle') }}
          </v-card-title>
          <v-card-text>
            <v-form ref="formRef" @submit.prevent="save">
              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="form.name"
                    :label="t('admin.entityTypes.form.name')"
                    :rules="[v => !!v || t('admin.entityTypes.form.nameRequired')]"
                    :placeholder="t('admin.entityTypes.form.namePlaceholder')"
                  ></v-text-field>
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="form.name_plural"
                    :label="t('admin.entityTypes.form.namePlural')"
                    :placeholder="t('admin.entityTypes.form.namePluralPlaceholder')"
                  ></v-text-field>
                </v-col>
              </v-row>

              <v-textarea
                v-model="form.description"
                :label="t('admin.entityTypes.form.description')"
                rows="2"
                :placeholder="t('admin.entityTypes.form.descriptionPlaceholder')"
              ></v-textarea>

              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="form.icon"
                    :label="t('admin.entityTypes.form.icon')"
                    :placeholder="t('admin.entityTypes.form.iconPlaceholder')"
                    :hint="t('admin.entityTypes.form.iconHint')"
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
                    :label="t('admin.entityTypes.form.color')"
                    :placeholder="t('admin.entityTypes.form.colorPlaceholder')"
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

              <v-row>
                <v-col cols="12" md="4">
                  <v-checkbox
                    v-model="form.is_primary"
                    :label="t('admin.entityTypes.form.isPrimary')"
                    :hint="t('admin.entityTypes.form.isPrimaryHint')"
                    persistent-hint
                  ></v-checkbox>
                </v-col>
                <v-col cols="12" md="4">
                  <v-checkbox
                    v-model="form.supports_hierarchy"
                    :label="t('admin.entityTypes.form.supportsHierarchy')"
                    :hint="t('admin.entityTypes.form.supportsHierarchyHint')"
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
                v-model.number="form.display_order"
                :label="t('admin.entityTypes.form.displayOrder')"
                type="number"
                min="0"
              ></v-text-field>
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
            {{ t('admin.entityTypes.dialog.deleteTitle') }}
          </v-card-title>
          <v-card-text>
            {{ t('admin.entityTypes.dialog.deleteConfirm', { name: itemToDelete?.name }) }}
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
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { entityApi, facetApi } from '@/services/api'
import { useSnackbar } from '@/composables/useSnackbar'

const { t } = useI18n()
const { showSuccess, showError } = useSnackbar()

// State
const entityTypes = ref<any[]>([])
const facetTypes = ref<any[]>([])
const loading = ref(false)
const dialog = ref(false)
const deleteDialog = ref(false)
const editingItem = ref<any>(null)
const itemToDelete = ref<any>(null)
const saving = ref(false)
const deleting = ref(false)
const formRef = ref<any>(null)

const form = ref({
  name: '',
  name_plural: '',
  description: '',
  icon: 'mdi-folder',
  color: '#4CAF50',
  is_primary: true,
  supports_hierarchy: false,
  is_active: true,
  display_order: 10,
})

// Get facets that are applicable to a given entity type
function getFacetsForEntityType(entityTypeSlug: string): any[] {
  return facetTypes.value.filter(ft =>
    ft.applicable_entity_type_slugs?.length === 0 ||
    ft.applicable_entity_type_slugs?.includes(entityTypeSlug)
  )
}

const headers = computed(() => [
  { title: '', key: 'icon', width: '50px', sortable: false },
  { title: t('admin.entityTypes.columns.name'), key: 'name' },
  { title: t('admin.entityTypes.columns.slug'), key: 'slug' },
  { title: t('admin.entityTypes.facets'), key: 'facets', sortable: false },
  { title: t('admin.entityTypes.columns.color'), key: 'color', width: '120px' },
  { title: t('admin.entityTypes.columns.entities'), key: 'entity_count', width: '100px', align: 'center' as const },
  { title: t('admin.entityTypes.columns.system'), key: 'is_system', width: '80px', align: 'center' as const },
  { title: t('admin.entityTypes.columns.active'), key: 'is_active', width: '80px', align: 'center' as const },
  { title: t('common.actions'), key: 'actions', width: '120px', sortable: false },
])

// Methods
async function loadEntityTypes() {
  loading.value = true
  try {
    const response = await entityApi.getEntityTypes({ per_page: 100 })
    entityTypes.value = response.data.items || []
  } catch (e) {
    console.error('Failed to load entity types', e)
    showError(t('admin.entityTypes.messages.loadError'))
  } finally {
    loading.value = false
  }
}

async function loadFacetTypes() {
  try {
    const response = await facetApi.getFacetTypes({ per_page: 100, is_active: true })
    facetTypes.value = response.data.items || []
  } catch (e) {
    console.error('Failed to load facet types', e)
  }
}

function openCreateDialog() {
  editingItem.value = null
  form.value = {
    name: '',
    name_plural: '',
    description: '',
    icon: 'mdi-folder',
    color: '#4CAF50',
    is_primary: true,
    supports_hierarchy: false,
    is_active: true,
    display_order: 10,
  }
  dialog.value = true
}

function openEditDialog(item: any) {
  editingItem.value = item
  form.value = {
    name: item.name,
    name_plural: item.name_plural || '',
    description: item.description || '',
    icon: item.icon || 'mdi-folder',
    color: item.color || '#4CAF50',
    is_primary: item.is_primary ?? true,
    supports_hierarchy: item.supports_hierarchy ?? false,
    is_active: item.is_active ?? true,
    display_order: item.display_order ?? 10,
  }
  dialog.value = true
}

function closeDialog() {
  dialog.value = false
  editingItem.value = null
}

async function save() {
  if (!formRef.value?.validate()) return

  saving.value = true
  try {
    const data = {
      ...form.value,
      name_plural: form.value.name_plural || `${form.value.name}s`,
    }

    if (editingItem.value) {
      await entityApi.updateEntityType(editingItem.value.id, data)
      showSuccess(t('admin.entityTypes.messages.updated'))
    } else {
      await entityApi.createEntityType(data)
      showSuccess(t('admin.entityTypes.messages.created'))
    }

    closeDialog()
    await loadEntityTypes()
  } catch (e: any) {
    const detail = e.response?.data?.detail || t('admin.entityTypes.messages.saveError')
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
    await entityApi.deleteEntityType(itemToDelete.value.id)
    showSuccess(t('admin.entityTypes.messages.deleted', { name: itemToDelete.value.name }))
    deleteDialog.value = false
    itemToDelete.value = null
    await loadEntityTypes()
  } catch (e: any) {
    const detail = e.response?.data?.detail || t('admin.entityTypes.messages.deleteError')
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
.entity-types-view {
  min-height: 100%;
}
</style>
