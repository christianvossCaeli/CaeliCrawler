<template>
  <div class="facet-types-view">
    <!-- Header -->
    <PageHeader
      :title="t('admin.facetTypes.title')"
      :subtitle="t('admin.facetTypes.subtitle')"
      icon="mdi-tag-multiple"
    >
      <template #actions>
        <v-btn
          v-if="canEdit"
          variant="tonal"
          color="primary"
          prepend-icon="mdi-plus"
          @click="openCreateDialog"
        >
          {{ t("admin.facetTypes.actions.create") }}
        </v-btn>
      </template>
    </PageHeader>

    <!-- Info Box -->
    <PageInfoBox :storage-key="INFO_BOX_STORAGE_KEYS.FACET_TYPES" :title="t('admin.facetTypes.info.title')">
      {{ t('admin.facetTypes.info.description') }}
    </PageInfoBox>

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
              @keyup.enter="loadFacetTypes"
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
        <template #item.icon="{ item }">
          <v-icon :icon="item.icon" :color="item.color" size="24"></v-icon>
        </template>

        <template #item.name="{ item }">
          <div>
            <strong>{{ item.name }}</strong>
            <div class="text-caption text-medium-emphasis">{{ item.slug }}</div>
          </div>
        </template>

        <template #item.applicable_entity_types="{ item }">
          <div class="d-flex flex-wrap gap-1">
            <v-chip
              v-for="slug in item.applicable_entity_type_slugs || []"
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
              {{ t("admin.facetTypes.allTypes") }}
            </v-chip>
          </div>
        </template>

        <template #item.value_type="{ item }">
          <v-chip size="small" variant="outlined">
            {{ item.value_type }}
          </v-chip>
        </template>

        <template #item.value_count="{ item }">
          <v-chip size="small" variant="tonal">
            {{ item.value_count || 0 }}
          </v-chip>
        </template>

        <template #item.ai_extraction_enabled="{ item }">
          <v-icon
            :icon="item.ai_extraction_enabled ? 'mdi-robot' : 'mdi-robot-off'"
            :color="item.ai_extraction_enabled ? 'success' : 'grey'"
            size="small"
          ></v-icon>
        </template>

        <template #item.is_system="{ item }">
          <v-icon
            v-if="item.is_system"
            color="warning"
            icon="mdi-lock"
            size="small"
            :title="t('admin.facetTypes.systemType')"
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
              v-if="canEdit && !item.is_system"
              icon="mdi-delete"
              size="small"
              variant="tonal"
              color="error"
              :title="t('common.delete')"
              :aria-label="t('common.delete')"
              @click="confirmDelete(item)"
            ></v-btn>
          </div>
        </template>

        <template #no-data>
          <div class="text-center py-8">
            <v-icon size="64" color="grey-lighten-1" class="mb-4"
              >mdi-tag-outline</v-icon
            >
            <h3 class="text-h6 mb-2">
              {{
                t("admin.facetTypes.emptyState.title", "Keine Facetten-Typen")
              }}
            </h3>
            <p class="text-body-2 text-medium-emphasis mb-4">
              {{
                t(
                  "admin.facetTypes.emptyState.description",
                  "Erstellen Sie einen neuen Facetten-Typ um Entity-Attribute zu definieren.",
                )
              }}
            </p>
            <v-btn color="primary" @click="openCreateDialog()">
              <v-icon start>mdi-plus</v-icon>
              {{ t("admin.facetTypes.actions.create") }}
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
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">{{
            editingItem ? "mdi-pencil" : "mdi-plus"
          }}</v-icon>
          {{
            editingItem
              ? t("admin.facetTypes.dialog.editTitle")
              : t("admin.facetTypes.dialog.createTitle")
          }}
        </v-card-title>

        <v-tabs v-model="activeTab" class="dialog-tabs">
          <v-tab value="basic">{{ t("admin.facetTypes.tabs.basic") }}</v-tab>
          <v-tab value="schema">{{ t("admin.facetTypes.tabs.schema") }}</v-tab>
          <v-tab value="behavior">{{
            t("admin.facetTypes.tabs.behavior")
          }}</v-tab>
          <v-tab value="ai">{{ t("admin.facetTypes.tabs.ai") }}</v-tab>
          <v-tab value="entity-ref">{{
            t("admin.facetTypes.tabs.entityRef", "Entity-Ref")
          }}</v-tab>
        </v-tabs>

        <v-card-text style="max-height: 60vh; overflow-y: auto">
          <v-form ref="formRef">
            <v-window v-model="activeTab">
              <!-- Basic Tab -->
              <v-window-item value="basic">
                <v-row>
                  <v-col cols="12" md="8">
                    <v-text-field
                      v-model="form.name"
                      :label="t('admin.facetTypes.form.name')"
                      :rules="[(v: string) => !!v || t('common.required')]"
                      variant="outlined"
                    ></v-text-field>
                  </v-col>
                  <v-col cols="12" md="4">
                    <v-text-field
                      v-model="form.name_plural"
                      :label="t('admin.facetTypes.form.namePlural')"
                      :placeholder="form.name ? `${form.name}s` : ''"
                      variant="outlined"
                    ></v-text-field>
                  </v-col>
                  <v-col cols="12">
                    <v-textarea
                      v-model="form.description"
                      :label="t('admin.facetTypes.form.description')"
                      rows="2"
                      variant="outlined"
                    ></v-textarea>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-label class="mb-2">{{
                      t("admin.facetTypes.form.icon")
                    }}</v-label>
                    <div class="d-flex flex-wrap gap-1 mb-2">
                      <v-btn
                        v-for="icon in suggestedFacetIcons"
                        :key="icon"
                        :icon="icon"
                        :color="form.icon === icon ? 'primary' : undefined"
                        :variant="form.icon === icon ? 'flat' : 'tonal'"
                        size="small"
                        @click="form.icon = icon"
                      ></v-btn>
                    </div>
                    <v-text-field
                      v-model="form.icon"
                      :label="t('admin.facetTypes.form.customIcon')"
                      variant="outlined"
                      density="compact"
                      hint="MDI icon name (e.g., mdi-account)"
                      persistent-hint
                    >
                      <template #prepend-inner>
                        <v-icon :icon="form.icon"></v-icon>
                      </template>
                    </v-text-field>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-label class="mb-2">{{
                      t("admin.facetTypes.form.color")
                    }}</v-label>
                    <v-color-picker
                      v-model="form.color"
                      mode="hexa"
                      show-swatches
                      hide-inputs
                      hide-canvas
                      swatches-max-height="120"
                    ></v-color-picker>
                    <div class="mt-2 d-flex align-center gap-2">
                      <v-chip
                        :color="form.color"
                        :style="{ color: getContrastColor(form.color) }"
                      >
                        <v-icon start :icon="form.icon" size="small"></v-icon>
                        {{ form.name || t("admin.facetTypes.form.preview") }}
                      </v-chip>
                    </div>
                  </v-col>
                  <v-col cols="12">
                    <v-select
                      v-model="form.applicable_entity_type_slugs"
                      :items="entityTypes"
                      :label="t('admin.facetTypes.form.entityTypes')"
                      :hint="t('admin.facetTypes.form.entityTypesHint')"
                      item-title="name"
                      item-value="slug"
                      multiple
                      chips
                      closable-chips
                      persistent-hint
                      variant="outlined"
                    ></v-select>
                  </v-col>
                </v-row>
              </v-window-item>

              <!-- Schema Tab -->
              <v-window-item value="schema">
                <v-row>
                  <v-col cols="12">
                    <v-btn
                      color="info"
                      variant="tonal"
                      prepend-icon="mdi-robot"
                      :loading="generatingSchema"
                      class="mb-4"
                      @click="generateSchemaWithAI"
                    >
                      {{ t("admin.facetTypes.actions.generateSchema") }}
                    </v-btn>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-select
                      v-model="form.value_type"
                      :items="valueTypeOptions"
                      :label="t('admin.facetTypes.form.valueType')"
                      variant="outlined"
                    ></v-select>
                  </v-col>
                  <v-col cols="12">
                    <v-textarea
                      v-model="schemaJson"
                      :label="t('admin.facetTypes.form.valueSchema')"
                      :aria-invalid="!!schemaError"
                      :error-messages="schemaError ? [schemaError] : []"
                      rows="12"
                      variant="outlined"
                      font="monospace"
                      :placeholder="
                        t('admin.facetTypes.form.schemaPlaceholder')
                      "
                    ></v-textarea>
                  </v-col>
                </v-row>
              </v-window-item>

              <!-- Behavior Tab -->
              <v-window-item value="behavior">
                <v-row>
                  <v-col cols="12" md="6">
                    <v-select
                      v-model="form.aggregation_method"
                      :items="aggregationOptions"
                      :label="t('admin.facetTypes.form.aggregationMethod')"
                      variant="outlined"
                    ></v-select>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-combobox
                      v-model="form.deduplication_fields"
                      :label="t('admin.facetTypes.form.deduplicationFields')"
                      :hint="t('admin.facetTypes.form.deduplicationFieldsHint')"
                      multiple
                      chips
                      closable-chips
                      persistent-hint
                      variant="outlined"
                    ></v-combobox>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-card variant="outlined" class="pa-4">
                      <v-switch
                        v-model="form.is_time_based"
                        :label="t('admin.facetTypes.form.isTimeBased')"
                        color="primary"
                        hide-details
                      ></v-switch>
                      <div class="text-caption text-medium-emphasis mt-2">
                        {{ t("admin.facetTypes.form.isTimeBasedHint") }}
                      </div>
                      <v-text-field
                        v-if="form.is_time_based"
                        v-model="form.time_field_path"
                        :label="t('admin.facetTypes.form.timeFieldPath')"
                        :placeholder="
                          t('admin.facetTypes.form.timeFieldPathPlaceholder')
                        "
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
                        <v-card
                          variant="outlined"
                          class="pa-4 h-100 d-flex align-center"
                        >
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
                      <div class="text-body-1 font-weight-medium">
                        {{ t("admin.facetTypes.form.aiExtractionEnabled") }}
                      </div>
                      <div class="text-caption text-medium-emphasis">
                        {{ t("admin.facetTypes.form.aiExtractionEnabledHint") }}
                      </div>
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
                      {{ t("admin.facetTypes.form.aiPromptInfo") }}
                    </v-alert>

                    <v-textarea
                      v-model="form.ai_extraction_prompt"
                      :label="t('admin.facetTypes.form.aiExtractionPrompt')"
                      :placeholder="
                        t('admin.facetTypes.form.aiExtractionPromptPlaceholder')
                      "
                      rows="12"
                      variant="outlined"
                    ></v-textarea>
                  </div>
                </v-expand-transition>

                <v-alert
                  v-if="!form.ai_extraction_enabled"
                  type="warning"
                  variant="tonal"
                  class="mt-4"
                >
                  {{ t("admin.facetTypes.form.aiDisabledInfo") }}
                </v-alert>
              </v-window-item>

              <!-- Entity Reference Tab -->
              <v-window-item value="entity-ref">
                <v-card variant="outlined" class="mb-4">
                  <v-card-text class="d-flex align-center">
                    <v-avatar color="primary" size="48" class="mr-4">
                      <v-icon color="on-primary">mdi-link-variant</v-icon>
                    </v-avatar>
                    <div class="flex-grow-1">
                      <div class="text-body-1 font-weight-medium">
                        {{
                          t(
                            "admin.facetTypes.form.allowsEntityReference",
                            "Entity-Referenz erlauben",
                          )
                        }}
                      </div>
                      <div class="text-caption text-medium-emphasis">
                        {{
                          t(
                            "admin.facetTypes.form.allowsEntityReferenceHint",
                            "Facet-Werte können auf andere Datensätze verweisen (z.B. Kontakt → Person)",
                          )
                        }}
                      </div>
                    </div>
                    <v-switch
                      v-model="form.allows_entity_reference"
                      color="primary"
                      hide-details
                    ></v-switch>
                  </v-card-text>
                </v-card>

                <v-expand-transition>
                  <div v-if="form.allows_entity_reference">
                    <v-alert type="info" variant="tonal" class="mb-4">
                      {{
                        t(
                          "admin.facetTypes.form.entityRefInfo",
                          "Wenn aktiviert, können Facet-Werte auf andere Entities verweisen. Zum Beispiel kann ein Kontakt-Facet auf eine Person-Entity verweisen.",
                        )
                      }}
                    </v-alert>

                    <v-select
                      v-model="form.target_entity_type_slugs"
                      :items="entityTypes"
                      :label="
                        t(
                          'admin.facetTypes.form.targetEntityTypes',
                          'Erlaubte Ziel-Entity-Typen',
                        )
                      "
                      :hint="
                        t(
                          'admin.facetTypes.form.targetEntityTypesHint',
                          'Leer = alle Typen erlaubt',
                        )
                      "
                      item-title="name"
                      item-value="slug"
                      multiple
                      chips
                      closable-chips
                      persistent-hint
                      variant="outlined"
                      class="mb-4"
                    ></v-select>

                    <v-card variant="outlined" class="pa-4">
                      <v-switch
                        v-model="form.auto_create_entity"
                        :label="
                          t(
                            'admin.facetTypes.form.autoCreateEntity',
                            'Entities automatisch erstellen',
                          )
                        "
                        color="primary"
                        hide-details
                      ></v-switch>
                      <div class="text-caption text-medium-emphasis mt-2">
                        {{
                          t(
                            "admin.facetTypes.form.autoCreateEntityHint",
                            "Wenn aktiviert, wird automatisch eine neue Entity erstellt, wenn keine passende gefunden wird.",
                          )
                        }}
                      </div>
                    </v-card>
                  </div>
                </v-expand-transition>

                <v-alert
                  v-if="!form.allows_entity_reference"
                  type="info"
                  variant="tonal"
                  class="mt-4"
                >
                  {{
                    t(
                      "admin.facetTypes.form.entityRefDisabledInfo",
                      "Facet-Werte dieses Typs werden nicht mit anderen Entities verknüpft.",
                    )
                  }}
                </v-alert>
              </v-window-item>
            </v-window>
          </v-form>
        </v-card-text>

        <v-divider></v-divider>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="closeDialog">{{
            t("common.cancel")
          }}</v-btn>
          <v-btn variant="flat" color="primary" :loading="saving" @click="save">
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
          {{ t("admin.facetTypes.dialog.deleteTitle") }}
        </v-card-title>
        <v-card-text>
          {{
            t("admin.facetTypes.dialog.deleteConfirm", {
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
 * FacetTypesView - Admin view for managing facet types
 *
 * Uses useFacetTypesAdmin composable for all state and logic.
 */
import { onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { useFacetTypesAdmin } from "@/composables/useFacetTypesAdmin";
import { getContrastColor } from "@/composables/useColorHelpers";
import PageHeader from "@/components/common/PageHeader.vue";
import PageInfoBox from "@/components/common/PageInfoBox.vue";
import { INFO_BOX_STORAGE_KEYS } from "@/config/infoBox";
import { DIALOG_SIZES } from "@/config/ui";

const { t } = useI18n();

// Initialize composable with all state and methods
const {
  // State
  facetTypes,
  entityTypes,
  loading,
  dialog,
  deleteDialog,
  editingItem,
  itemToDelete,
  saving,
  deleting,
  formRef, // Used in template via ref="formRef"
  activeTab,
  schemaJson,
  schemaError,
  generatingSchema,
  filters,
  form,

  // Computed
  canEdit,
  headers,
  activeOptions,
  entityTypeOptions,

  // Static Options
  valueTypeOptions,
  aggregationOptions,
  suggestedFacetIcons,

  // Helper Functions
  getEntityTypeName,

  // Data Loading
  loadFacetTypes,
  debouncedSearch,

  // Dialog Actions
  openCreateDialog,
  openEditDialog,
  closeDialog,
  confirmDelete,

  // CRUD Operations
  save,
  deleteItem,

  // AI
  generateSchemaWithAI,

  // Initialization
  initialize,
} = useFacetTypesAdmin();

// Explicitly mark formRef as used (it's bound to template via ref="formRef")
void formRef;

// Initialize on mount
onMounted(() => initialize());
</script>

<style scoped>
.facet-types-view {
  min-height: 100%;
}

.dialog-tabs {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
