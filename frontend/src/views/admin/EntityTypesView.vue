<template>
  <div class="entity-types-view">
    <!-- Header -->
    <PageHeader
      :title="t('admin.entityTypes.title')"
      :subtitle="t('admin.entityTypes.subtitle')"
      icon="mdi-shape"
    >
      <template #actions>
        <v-btn
          v-if="canEdit"
          variant="tonal"
          color="primary"
          prepend-icon="mdi-plus"
          @click="openCreateDialog"
        >
          {{ t("admin.entityTypes.actions.create") }}
        </v-btn>
      </template>
    </PageHeader>

    <!-- Entity Types Table -->
    <v-card>
      <v-data-table
        :headers="headers"
        :items="entityTypes"
        :loading="loading"
        :items-per-page="25"
        class="elevation-0"
      >
        <template #item.icon="{ item }">
          <v-icon :icon="item.icon" :color="item.color" size="24"></v-icon>
        </template>

        <template #item.name="{ item }">
          <div>
            <strong>{{ item.name }}</strong>
            <div class="text-caption text-medium-emphasis">
              {{ item.name_plural }}
            </div>
          </div>
        </template>

        <template #item.facets="{ item }">
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
              {{ t("common.none") }}
            </v-chip>
          </div>
        </template>

        <template #item.color="{ item }">
          <v-chip :color="item.color" size="small" variant="flat">
            {{ item.color }}
          </v-chip>
        </template>

        <template #item.entity_count="{ item }">
          <v-chip size="small" variant="tonal">
            {{ item.entity_count || 0 }}
          </v-chip>
        </template>

        <template #item.is_system="{ item }">
          <v-icon
            v-if="item.is_system"
            color="warning"
            icon="mdi-lock"
            size="small"
            :title="t('admin.entityTypes.systemType')"
          ></v-icon>
          <span v-else>-</span>
        </template>

        <template #item.is_active="{ item }">
          <v-icon
            :icon="item.is_active ? 'mdi-check-circle' : 'mdi-close-circle'"
            :color="item.is_active ? 'success' : 'error'"
            size="small"
          ></v-icon>
        </template>

        <template #item.actions="{ item }">
          <div class="d-flex justify-end ga-1">
            <v-btn
              v-if="canEdit"
              icon="mdi-pencil"
              size="small"
              variant="tonal"
              :title="t('common.edit')"
              :aria-label="t('common.edit')"
              @click="openEditDialog(item)"
            ></v-btn>
            <v-btn
              v-if="canDelete"
              icon="mdi-delete"
              size="small"
              variant="tonal"
              color="error"
              :title="t('common.delete')"
              :aria-label="t('common.delete')"
              :disabled="item.is_system || (item.entity_count || 0) > 0"
              @click="confirmDelete(item)"
            ></v-btn>
          </div>
        </template>

        <template #no-data>
          <div class="text-center py-8">
            <v-icon size="64" color="grey-lighten-1" class="mb-4"
              >mdi-shape-outline</v-icon
            >
            <h3 class="text-h6 mb-2">
              {{
                t("admin.entityTypes.emptyState.title", "Keine Entity-Typen")
              }}
            </h3>
            <p class="text-body-2 text-medium-emphasis mb-4">
              {{
                t(
                  "admin.entityTypes.emptyState.description",
                  "Erstellen Sie einen neuen Entity-Typ um Daten zu strukturieren.",
                )
              }}
            </p>
            <v-btn color="primary" @click="openCreateDialog()">
              <v-icon start>mdi-plus</v-icon>
              {{ t("admin.entityTypes.actions.create") }}
            </v-btn>
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Create/Edit Dialog -->
    <v-dialog
      v-model="dialog"
      :max-width="DIALOG_SIZES.XL"
      persistent
      scrollable
    >
      <v-card>
        <v-card-title class="d-flex align-center pa-4 bg-primary">
          <v-icon
            :icon="form.icon || 'mdi-folder'"
            class="mr-3"
            size="28"
          ></v-icon>
          <div>
            <div class="text-h6">
              {{
                editingItem
                  ? t("admin.entityTypes.dialog.editTitle")
                  : t("admin.entityTypes.dialog.createTitle")
              }}
            </div>
            <div v-if="form.name" class="text-caption opacity-80">
              {{ form.name }}
            </div>
          </div>
        </v-card-title>

        <v-tabs v-model="activeTab" class="dialog-tabs">
          <v-tab value="basic">
            <v-icon start>mdi-form-textbox</v-icon>
            {{ t("admin.entityTypes.tabs.basic") }}
          </v-tab>
          <v-tab value="appearance">
            <v-icon start>mdi-palette</v-icon>
            {{ t("admin.entityTypes.tabs.appearance") }}
          </v-tab>
          <v-tab value="facets">
            <v-icon start>mdi-tag-multiple</v-icon>
            {{ t("admin.entityTypes.tabs.facets") }}
            <v-chip
              v-if="selectedFacetIds.length > 0"
              size="x-small"
              class="ml-2"
              color="primary"
            >
              {{ selectedFacetIds.length }}
            </v-chip>
          </v-tab>
          <v-tab value="settings">
            <v-icon start>mdi-cog</v-icon>
            {{ t("admin.entityTypes.tabs.settings") }}
          </v-tab>
        </v-tabs>

        <v-card-text class="pa-6 dialog-content-md">
          <v-form ref="formRef" @submit.prevent="save">
            <v-window v-model="activeTab">
              <!-- Basic Tab -->
              <v-window-item value="basic">
                <v-row>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model="form.name"
                      :label="t('admin.entityTypes.form.name')"
                      :rules="[
                        (v) => !!v || t('admin.entityTypes.form.nameRequired'),
                      ]"
                      :placeholder="t('admin.entityTypes.form.namePlaceholder')"
                      variant="outlined"
                    ></v-text-field>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model="form.name_plural"
                      :label="t('admin.entityTypes.form.namePlural')"
                      :placeholder="
                        t('admin.entityTypes.form.namePluralPlaceholder')
                      "
                      variant="outlined"
                    ></v-text-field>
                  </v-col>
                </v-row>

                <v-textarea
                  v-model="form.description"
                  :label="t('admin.entityTypes.form.description')"
                  rows="3"
                  :placeholder="
                    t('admin.entityTypes.form.descriptionPlaceholder')
                  "
                  variant="outlined"
                ></v-textarea>

                <!-- Preview Card -->
                <v-card variant="outlined" class="mt-4">
                  <v-card-title class="text-subtitle-2 pb-2">
                    <v-icon start size="small">mdi-eye</v-icon>
                    {{ t("admin.entityTypes.form.preview") }}
                  </v-card-title>
                  <v-card-text>
                    <div class="d-flex align-center ga-3">
                      <v-avatar :color="form.color" size="48">
                        <v-icon
                          :icon="form.icon || 'mdi-folder'"
                          :color="getContrastColor(form.color)"
                        ></v-icon>
                      </v-avatar>
                      <div>
                        <div class="text-h6">
                          {{
                            form.name ||
                            t("admin.entityTypes.form.namePlaceholder")
                          }}
                        </div>
                        <div class="text-caption text-medium-emphasis">
                          {{ form.name_plural || form.name + "s" }}
                        </div>
                      </div>
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
                      :label="t('admin.entityTypes.form.icon')"
                      :placeholder="t('admin.entityTypes.form.iconPlaceholder')"
                      variant="outlined"
                    >
                      <template #prepend-inner>
                        <v-icon
                          :icon="form.icon || 'mdi-help'"
                          :color="form.color"
                        ></v-icon>
                      </template>
                    </v-text-field>
                    <v-alert
                      type="info"
                      variant="tonal"
                      density="compact"
                      class="mt-2"
                    >
                      {{ t("admin.entityTypes.form.iconHint") }}
                    </v-alert>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-label class="mb-2">{{
                      t("admin.entityTypes.form.color")
                    }}</v-label>
                    <v-color-picker
                      v-model="form.color"
                      mode="hexa"
                      show-swatches
                      swatches-max-height="150"
                      hide-inputs
                    ></v-color-picker>
                  </v-col>
                </v-row>

                <!-- Icon Suggestions -->
                <v-card variant="outlined" class="mt-4">
                  <v-card-title class="text-subtitle-2 pb-2">
                    <v-icon start size="small">mdi-lightbulb</v-icon>
                    {{ t("admin.entityTypes.form.iconSuggestions") }}
                  </v-card-title>
                  <v-card-text>
                    <div class="d-flex flex-wrap ga-2">
                      <v-btn
                        v-for="icon in suggestedIcons"
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
              </v-window-item>

              <!-- Facets Tab -->
              <v-window-item value="facets">
                <v-alert type="info" variant="tonal" class="mb-4">
                  {{ t("admin.entityTypes.form.facetsInfo") }}
                </v-alert>

                <v-text-field
                  v-model="facetSearch"
                  :label="t('common.search')"
                  prepend-inner-icon="mdi-magnify"
                  variant="outlined"
                  density="compact"
                  clearable
                  hide-details
                  class="mb-4"
                ></v-text-field>

                <v-list lines="two" class="border rounded">
                  <v-list-item
                    v-for="facet in filteredFacets"
                    :key="facet.id"
                    :value="facet.id"
                    @click="toggleFacet(facet.id)"
                  >
                    <template #prepend>
                      <v-checkbox-btn
                        :model-value="selectedFacetIds.includes(facet.id)"
                        @click.stop="toggleFacet(facet.id)"
                      ></v-checkbox-btn>
                      <v-avatar :color="facet.color" size="36" class="mr-3">
                        <v-icon
                          :icon="facet.icon"
                          :color="getContrastColor(facet.color)"
                          size="small"
                        ></v-icon>
                      </v-avatar>
                    </template>

                    <v-list-item-title>{{ facet.name }}</v-list-item-title>
                    <v-list-item-subtitle>
                      {{ facet.description || facet.slug }}
                      <v-chip
                        v-if="facet.value_type"
                        size="x-small"
                        class="ml-2"
                        variant="outlined"
                      >
                        {{ facet.value_type }}
                      </v-chip>
                    </v-list-item-subtitle>

                    <template #append>
                      <v-chip
                        v-if="!facet.applicable_entity_type_slugs?.length"
                        size="x-small"
                        color="info"
                        variant="tonal"
                        class="mr-2"
                      >
                        {{ t("admin.entityTypes.form.appliesToAll") }}
                      </v-chip>
                      <v-chip
                        v-if="facet.is_system"
                        size="x-small"
                        color="warning"
                        variant="tonal"
                      >
                        System
                      </v-chip>
                    </template>
                  </v-list-item>

                  <v-list-item v-if="filteredFacets.length === 0">
                    <v-list-item-title class="text-center text-medium-emphasis">
                      {{ t("admin.entityTypes.form.noFacetsFound") }}
                    </v-list-item-title>
                  </v-list-item>
                </v-list>

                <div class="d-flex justify-space-between align-center mt-4">
                  <span class="text-caption text-medium-emphasis">
                    {{ selectedFacetIds.length }}
                    {{ t("admin.entityTypes.form.facetsSelected") }}
                  </span>
                  <div class="d-flex ga-2">
                    <v-btn
                      size="small"
                      variant="tonal"
                      @click="selectedFacetIds = []"
                    >
                      {{ t("admin.entityTypes.form.deselectAll") }}
                    </v-btn>
                    <v-btn
                      size="small"
                      variant="tonal"
                      @click="selectAllFacets"
                    >
                      {{ t("admin.entityTypes.form.selectAll") }}
                    </v-btn>
                  </div>
                </div>
              </v-window-item>

              <!-- Settings Tab -->
              <v-window-item value="settings">
                <v-row>
                  <v-col cols="12" md="6">
                    <v-card variant="outlined" class="pa-4">
                      <v-switch
                        v-model="form.is_primary"
                        :label="t('admin.entityTypes.form.isPrimary')"
                        color="primary"
                        hide-details
                      ></v-switch>
                      <div class="text-caption text-medium-emphasis mt-2">
                        {{ t("admin.entityTypes.form.isPrimaryHint") }}
                      </div>
                    </v-card>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-card variant="outlined" class="pa-4">
                      <v-switch
                        v-model="form.supports_hierarchy"
                        :label="t('admin.entityTypes.form.supportsHierarchy')"
                        color="primary"
                        hide-details
                      ></v-switch>
                      <div class="text-caption text-medium-emphasis mt-2">
                        {{ t("admin.entityTypes.form.supportsHierarchyHint") }}
                      </div>
                    </v-card>
                  </v-col>
                </v-row>

                <v-row class="mt-4">
                  <v-col cols="12" md="6">
                    <v-card variant="outlined" class="pa-4">
                      <v-switch
                        v-model="form.is_active"
                        :label="t('common.active')"
                        color="success"
                        hide-details
                      ></v-switch>
                      <div class="text-caption text-medium-emphasis mt-2">
                        {{ t("admin.entityTypes.form.isActiveHint") }}
                      </div>
                    </v-card>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-card variant="outlined" class="pa-4">
                      <v-switch
                        v-model="form.supports_pysis"
                        :label="t('admin.entityTypes.form.supportsPysis')"
                        color="primary"
                        hide-details
                      ></v-switch>
                      <div class="text-caption text-medium-emphasis mt-2">
                        {{ t("admin.entityTypes.form.supportsPysisHint") }}
                      </div>
                    </v-card>
                  </v-col>
                </v-row>

                <v-row class="mt-4">
                  <v-col cols="12" md="6">
                    <v-number-input
                      v-model="form.display_order"
                      :label="t('admin.entityTypes.form.displayOrder')"
                      :min="0"
                      variant="outlined"
                      :hint="t('admin.entityTypes.form.displayOrderHint')"
                      persistent-hint
                      control-variant="stacked"
                    ></v-number-input>
                  </v-col>
                </v-row>
              </v-window-item>
            </v-window>
          </v-form>
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions class="pa-4">
          <v-btn variant="tonal" @click="closeDialog">{{
            t("common.cancel")
          }}</v-btn>
          <v-spacer></v-spacer>
          <v-btn
            v-if="activeTab !== 'basic'"
            variant="tonal"
            @click="activeTab = getPrevTab()"
          >
            <v-icon start>mdi-chevron-left</v-icon>
            {{ t("common.back") }}
          </v-btn>
          <v-btn
            v-if="activeTab !== 'settings'"
            color="primary"
            variant="tonal"
            @click="activeTab = getNextTab()"
          >
            {{ t("common.next") }}
            <v-icon end>mdi-chevron-right</v-icon>
          </v-btn>
          <v-btn
            v-if="activeTab === 'settings'"
            color="primary"
            :loading="saving"
            @click="save"
          >
            <v-icon start>mdi-check</v-icon>
            {{ editingItem ? t("common.save") : t("common.create") }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" :max-width="DIALOG_SIZES.XS">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon color="error" class="mr-2">mdi-alert</v-icon>
          {{ t("admin.entityTypes.dialog.deleteTitle") }}
        </v-card-title>
        <v-card-text>
          {{
            t("admin.entityTypes.dialog.deleteConfirm", {
              name: itemToDelete?.name,
            })
          }}
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="deleteDialog = false">{{
            t("common.cancel")
          }}</v-btn>
          <v-btn
            variant="tonal"
            color="error"
            :loading="deleting"
            @click="deleteItem"
            >{{ t("common.delete") }}</v-btn
          >
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
/**
 * EntityTypesView - Admin view for managing entity types
 *
 * Uses useEntityTypesAdmin composable for all state and logic.
 */
import { onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { useEntityTypesAdmin } from "@/composables/useEntityTypesAdmin";
import { getContrastColor } from "@/composables/useColorHelpers";
import PageHeader from "@/components/common/PageHeader.vue";
import { DIALOG_SIZES } from "@/config/ui";

const { t } = useI18n();

// Initialize composable with all state and methods
const {
  // State
  entityTypes,
  facetTypes,
  loading,
  dialog,
  deleteDialog,
  editingItem,
  itemToDelete,
  saving,
  deleting,
  formRef,
  activeTab,
  selectedFacetIds,
  facetSearch,
  form,

  // Computed
  canEdit,
  canDelete,
  headers,
  filteredFacets,

  // Static Options
  suggestedIcons,

  // Helper Functions
  getNextTab,
  getPrevTab,
  getFacetsForEntityType,
  toggleFacet,
  selectAllFacets,

  // Dialog Actions
  openCreateDialog,
  openEditDialog,
  closeDialog,
  confirmDelete,

  // CRUD Operations
  save,
  deleteItem,

  // Initialization
  initialize,
} = useEntityTypesAdmin();

// Explicitly mark formRef as used (it's bound to template via ref="formRef")
void formRef;

// Explicitly mark unused but template-required variables
void facetTypes;

// Initialize on mount
onMounted(() => initialize());
</script>

<style scoped>
.entity-types-view {
  min-height: 100%;
}

.dialog-tabs {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

:deep(.v-theme--light) .dialog-tabs {
  background-color: rgb(var(--v-theme-surface-light));
}

:deep(.v-theme--dark) .dialog-tabs {
  background-color: rgb(var(--v-theme-surface-dark));
}
</style>
