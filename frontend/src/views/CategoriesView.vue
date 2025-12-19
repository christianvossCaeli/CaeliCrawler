<template>
  <div>
    <div class="d-flex justify-space-between align-center mb-6">
      <h1 class="text-h4">Kategorien ({{ filteredCategories.length }})</h1>
      <v-btn color="primary" @click="openCreateDialog">
        <v-icon left>mdi-plus</v-icon>
        Neue Kategorie
      </v-btn>
    </div>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row>
          <v-col cols="12" md="4">
            <v-text-field
              v-model="categoryFilters.search"
              label="Suche (Name/Zweck)"
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
              label="Status"
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
              label="Dokumente"
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
              label="Sprache"
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
            {{ item.is_active ? 'Aktiv' : 'Inaktiv' }}
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
            <v-btn icon="mdi-database-outline" size="small" variant="text" color="primary" @click="showSourcesForCategory(item)" title="Datenquellen anzeigen"></v-btn>
            <v-btn icon="mdi-pencil" size="small" variant="text" @click="openEditDialog(item)" title="Bearbeiten"></v-btn>
            <v-btn icon="mdi-play" size="small" variant="text" color="success" @click="startCrawl(item)" title="Crawlen starten"></v-btn>
            <v-btn icon="mdi-refresh" size="small" variant="text" color="warning" @click="confirmReanalyze(item)" title="Dokumente neu analysieren"></v-btn>
            <v-btn icon="mdi-delete" size="small" variant="text" color="error" @click="confirmDelete(item)" title="Löschen"></v-btn>
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Create/Edit Dialog -->
    <v-dialog v-model="dialog" max-width="800">
      <v-card>
        <v-card-title>{{ editMode ? 'Kategorie bearbeiten' : 'Neue Kategorie' }}</v-card-title>
        <v-card-text>
          <v-form ref="form">
            <v-text-field
              v-model="formData.name"
              label="Name"
              required
              :rules="[v => !!v || 'Name ist erforderlich']"
            ></v-text-field>

            <v-textarea
              v-model="formData.description"
              label="Beschreibung"
              rows="2"
            ></v-textarea>

            <v-textarea
              v-model="formData.purpose"
              label="Zweck (z.B. 'Windkraft-Restriktionen analysieren')"
              required
              rows="2"
              :rules="[v => !!v || 'Zweck ist erforderlich']"
            ></v-textarea>

            <v-combobox
              v-model="formData.search_terms"
              label="Suchbegriffe"
              chips
              multiple
              hint="Drücken Sie Enter um einen Begriff hinzuzufügen"
            ></v-combobox>

            <v-combobox
              v-model="formData.document_types"
              label="Dokumenttypen"
              chips
              multiple
              hint="z.B. Beschluss, Protokoll, Satzung"
            ></v-combobox>

            <v-divider class="my-4"></v-divider>
            <h4 class="mb-2">Sprachen</h4>
            <p class="text-caption text-grey mb-2">
              Welche Sprachen werden in dieser Kategorie verwendet? Die KI passt ihre Analyse entsprechend an.
            </p>
            <v-select
              v-model="formData.languages"
              :items="availableLanguages"
              item-title="name"
              item-value="code"
              label="Sprachen"
              chips
              multiple
              closable-chips
              hint="Wählen Sie die Sprachen für diese Kategorie"
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
            <h4 class="mb-2">URL-Filter (Regex)</h4>
            <p class="text-caption text-grey mb-2">
              Diese Filter gelten für alle Datenquellen in dieser Kategorie, sofern die Quelle keine eigenen Filter definiert hat.
              Ohne Filter wird die komplette Sitemap durchsucht.
            </p>

            <v-combobox
              v-model="formData.url_include_patterns"
              label="Include-Patterns (Whitelist)"
              chips
              multiple
              closable-chips
              hint="URLs müssen mindestens ein Pattern matchen. z.B. /dokumente/, /beschluesse/, /ratsinformation/"
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
              label="Exclude-Patterns (Blacklist)"
              chips
              multiple
              closable-chips
              hint="URLs die ein Pattern matchen werden übersprungen. z.B. /archiv/, /login/, /suche/, /\?page="
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
              Ohne URL-Filter wird die komplette Sitemap durchsucht - dies kann sehr lange dauern!
            </v-alert>

            <v-divider class="my-4"></v-divider>

            <v-text-field
              v-model="formData.schedule_cron"
              label="Zeitplan (Cron)"
              hint="z.B. '0 2 * * *' für täglich um 2 Uhr"
            ></v-text-field>

            <v-divider class="my-4"></v-divider>
            <h4 class="mb-2">KI-Extraktions-Prompt</h4>
            <p class="text-caption text-grey mb-2">
              Definiert, welche Informationen die KI aus Dokumenten extrahiert.
              Hier können Sie festlegen, auf welche Themen (z.B. Windenergie) sich
              Pain Points und Positive Signals beziehen sollen.
            </p>
            <v-textarea
              v-model="formData.ai_extraction_prompt"
              label="KI-Extraktions-Prompt"
              rows="12"
              auto-grow
              variant="outlined"
              hint="Definieren Sie das JSON-Format und die Extraktionsregeln"
            ></v-textarea>

            <v-switch
              v-model="formData.is_active"
              label="Aktiv"
              color="success"
            ></v-switch>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="dialog = false">Abbrechen</v-btn>
          <v-btn color="primary" @click="saveCategory">Speichern</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title>Kategorie löschen?</v-card-title>
        <v-card-text>
          Möchten Sie die Kategorie "{{ selectedCategory?.name }}" wirklich löschen?
          Alle zugehörigen Datenquellen und Dokumente werden ebenfalls gelöscht.
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="deleteDialog = false">Abbrechen</v-btn>
          <v-btn color="error" @click="deleteCategory">Löschen</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Reanalyze Confirmation -->
    <v-dialog v-model="reanalyzeDialog" max-width="500">
      <v-card>
        <v-card-title>Dokumente neu analysieren?</v-card-title>
        <v-card-text>
          <p class="mb-4">
            Alle Dokumente der Kategorie "{{ selectedCategory?.name }}" werden mit dem
            aktuellen KI-Prompt neu analysiert.
          </p>
          <v-switch
            v-model="reanalyzeAll"
            label="Alle Dokumente neu analysieren (nicht nur niedrige Konfidenz)"
            color="warning"
          ></v-switch>
          <v-alert type="info" variant="tonal" class="mt-2">
            {{ reanalyzeAll ? 'Alle Dokumente' : 'Nur Dokumente mit Konfidenz < 70%' }} werden neu analysiert.
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="reanalyzeDialog = false">Abbrechen</v-btn>
          <v-btn color="warning" @click="reanalyzeDocuments">Neu analysieren</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Sources for Category Dialog -->
    <v-dialog v-model="sourcesDialog" max-width="900">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">mdi-database-outline</v-icon>
          Datenquellen: {{ selectedCategoryForSources?.name }}
          <v-chip color="primary" size="small" class="ml-2">
            {{ categorySources.length }} Quellen
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
            label="Suchen..."
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
                    {{ source.document_count || 0 }} Docs
                  </v-chip>
                  <v-btn
                    icon="mdi-open-in-new"
                    size="x-small"
                    variant="text"
                    :href="source.base_url"
                    target="_blank"
                    title="URL öffnen"
                  ></v-btn>
                </div>
              </template>
            </v-list-item>
          </v-list>

          <v-alert v-else type="warning" variant="tonal">
            <span v-if="categorySourcesSearch">Keine Datenquellen gefunden für "{{ categorySourcesSearch }}"</span>
            <span v-else>Keine Datenquellen in dieser Kategorie</span>
          </v-alert>

          <!-- Statistics -->
          <v-divider class="my-4"></v-divider>
          <v-row>
            <v-col cols="3">
              <div class="text-center">
                <div class="text-h5 text-primary">{{ categorySourcesStats.total }}</div>
                <div class="text-caption">Gesamt</div>
              </div>
            </v-col>
            <v-col cols="3">
              <div class="text-center">
                <div class="text-h5 text-success">{{ categorySourcesStats.active }}</div>
                <div class="text-caption">Aktiv</div>
              </div>
            </v-col>
            <v-col cols="3">
              <div class="text-center">
                <div class="text-h5 text-warning">{{ categorySourcesStats.pending }}</div>
                <div class="text-caption">Ausstehend</div>
              </div>
            </v-col>
            <v-col cols="3">
              <div class="text-center">
                <div class="text-h5 text-error">{{ categorySourcesStats.error }}</div>
                <div class="text-caption">Fehler</div>
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
            <v-icon left>mdi-filter</v-icon>
            Alle in Datenquellen-Ansicht anzeigen
          </v-btn>
          <v-spacer></v-spacer>
          <v-btn @click="sourcesDialog = false">Schließen</v-btn>
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
import { adminApi } from '@/services/api'

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
  { value: 'active', label: 'Aktiv' },
  { value: 'inactive', label: 'Inaktiv' },
]

const documentFilterOptions = [
  { value: 'with', label: 'Mit Dokumenten' },
  { value: 'without', label: 'Ohne Dokumente' },
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
  { title: 'Name', key: 'name' },
  { title: 'Zweck', key: 'purpose', maxWidth: '300px' },
  { title: 'Sprachen', key: 'languages' },
  { title: 'Status', key: 'is_active' },
  { title: 'Quellen', key: 'source_count' },
  { title: 'Dokumente', key: 'document_count' },
  { title: 'Aktionen', key: 'actions', sortable: false },
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

const startCrawl = async (category: any) => {
  try {
    await adminApi.startCrawl({ category_id: category.id })
    snackbarText.value = 'Crawl gestartet'
    snackbarColor.value = 'success'
    snackbar.value = true
  } catch (error) {
    console.error('Failed to start crawl:', error)
    snackbarText.value = 'Fehler beim Starten des Crawls'
    snackbarColor.value = 'error'
    snackbar.value = true
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
    snackbarText.value = response.data.message || 'Neu-Analyse gestartet'
    snackbarColor.value = 'success'
    snackbar.value = true
  } catch (error) {
    console.error('Failed to start reanalysis:', error)
    snackbarText.value = 'Fehler beim Starten der Neu-Analyse'
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
    snackbarText.value = 'Fehler beim Laden der Datenquellen'
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
