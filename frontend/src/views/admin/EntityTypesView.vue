<template>
  <div class="entity-types-view">
    <v-container fluid>
      <!-- Header -->
      <v-row class="mb-4">
        <v-col>
          <div class="d-flex align-center justify-space-between">
            <div>
              <h1 class="text-h4 mb-1">Entity-Typen</h1>
              <p class="text-body-2 text-medium-emphasis">
                Kategorien fuer Entitaeten verwalten (z.B. Gemeinden, Personen, Organisationen)
              </p>
            </div>
            <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">
              Neuer Entity-Typ
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
            <v-icon v-if="item.is_system" color="warning" icon="mdi-lock" size="small" title="System-Typ"></v-icon>
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
                title="Bearbeiten"
              ></v-btn>
              <v-btn
                icon="mdi-delete"
                size="small"
                variant="text"
                color="error"
                :disabled="item.is_system || (item.entity_count || 0) > 0"
                @click="confirmDelete(item)"
                :title="item.is_system ? 'System-Typ kann nicht geloescht werden' : (item.entity_count || 0) > 0 ? 'Hat noch Entities' : 'Loeschen'"
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
            {{ editingItem ? 'Entity-Typ bearbeiten' : 'Neuer Entity-Typ' }}
          </v-card-title>
          <v-card-text>
            <v-form ref="formRef" @submit.prevent="save">
              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="form.name"
                    label="Name *"
                    :rules="[v => !!v || 'Name ist erforderlich']"
                    placeholder="z.B. Windpark"
                  ></v-text-field>
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="form.name_plural"
                    label="Plural"
                    placeholder="z.B. Windparks"
                  ></v-text-field>
                </v-col>
              </v-row>

              <v-textarea
                v-model="form.description"
                label="Beschreibung"
                rows="2"
                placeholder="Kurze Beschreibung des Entity-Typs"
              ></v-textarea>

              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="form.icon"
                    label="Icon"
                    placeholder="mdi-wind-turbine"
                    hint="Material Design Icon Name (mdi-*)"
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
                    label="Farbe"
                    placeholder="#4CAF50"
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
                    label="Primaerer Typ"
                    hint="Wird in der Hauptnavigation angezeigt"
                    persistent-hint
                  ></v-checkbox>
                </v-col>
                <v-col cols="12" md="4">
                  <v-checkbox
                    v-model="form.supports_hierarchy"
                    label="Hierarchisch"
                    hint="Unterstuetzt Parent-Child Beziehungen"
                    persistent-hint
                  ></v-checkbox>
                </v-col>
                <v-col cols="12" md="4">
                  <v-checkbox
                    v-model="form.is_active"
                    label="Aktiv"
                  ></v-checkbox>
                </v-col>
              </v-row>

              <v-text-field
                v-model.number="form.display_order"
                label="Anzeigereihenfolge"
                type="number"
                min="0"
              ></v-text-field>
            </v-form>
          </v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn @click="closeDialog">Abbrechen</v-btn>
            <v-btn color="primary" :loading="saving" @click="save">
              {{ editingItem ? 'Speichern' : 'Erstellen' }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <!-- Delete Confirmation Dialog -->
      <v-dialog v-model="deleteDialog" max-width="400">
        <v-card>
          <v-card-title class="text-h6">
            <v-icon color="error" class="mr-2">mdi-alert</v-icon>
            Entity-Typ loeschen?
          </v-card-title>
          <v-card-text>
            Moechtest du <strong>{{ itemToDelete?.name }}</strong> wirklich loeschen?
            Diese Aktion kann nicht rueckgaengig gemacht werden.
          </v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn @click="deleteDialog = false">Abbrechen</v-btn>
            <v-btn color="error" :loading="deleting" @click="deleteItem">Loeschen</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </v-container>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { entityApi } from '@/services/api'
import { useSnackbar } from '@/composables/useSnackbar'

const { showSuccess, showError } = useSnackbar()

// State
const entityTypes = ref<any[]>([])
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

const headers = [
  { title: '', key: 'icon', width: '50px', sortable: false },
  { title: 'Name', key: 'name' },
  { title: 'Slug', key: 'slug' },
  { title: 'Farbe', key: 'color', width: '120px' },
  { title: 'Entities', key: 'entity_count', width: '100px', align: 'center' as const },
  { title: 'System', key: 'is_system', width: '80px', align: 'center' as const },
  { title: 'Aktiv', key: 'is_active', width: '80px', align: 'center' as const },
  { title: 'Aktionen', key: 'actions', width: '120px', sortable: false },
]

// Methods
async function loadEntityTypes() {
  loading.value = true
  try {
    const response = await entityApi.getEntityTypes({ per_page: 100 })
    entityTypes.value = response.data.items || []
  } catch (e) {
    console.error('Failed to load entity types', e)
    showError('Fehler beim Laden der Entity-Typen')
  } finally {
    loading.value = false
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
      showSuccess('Entity-Typ aktualisiert')
    } else {
      await entityApi.createEntityType(data)
      showSuccess('Entity-Typ erstellt')
    }

    closeDialog()
    await loadEntityTypes()
  } catch (e: any) {
    const detail = e.response?.data?.detail || 'Fehler beim Speichern'
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
    showSuccess(`"${itemToDelete.value.name}" geloescht`)
    deleteDialog.value = false
    itemToDelete.value = null
    await loadEntityTypes()
  } catch (e: any) {
    const detail = e.response?.data?.detail || 'Fehler beim Loeschen'
    showError(detail)
  } finally {
    deleting.value = false
  }
}

// Init
onMounted(() => {
  loadEntityTypes()
})
</script>

<style scoped>
.entity-types-view {
  min-height: 100%;
}
</style>
