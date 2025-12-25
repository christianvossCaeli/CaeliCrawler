<template>
  <v-dialog
    :model-value="modelValue"
    max-width="800"
    persistent
    scrollable
    @update:model-value="$emit('update:model-value', $event)"
  >
    <v-card>
      <v-card-title class="d-flex align-center pa-4 bg-primary">
        <v-avatar :color="currentEntityType?.color || 'primary-darken-1'" size="40" class="mr-3">
          <v-icon
            :color="currentEntityType?.color ? (isLightColor(currentEntityType.color) ? 'black' : 'white') : 'on-primary'"
            :icon="currentEntityType?.icon || (editingEntity ? 'mdi-pencil' : 'mdi-plus')"
          ></v-icon>
        </v-avatar>
        <div>
          <div class="text-h6">
            {{
              editingEntity
                ? t('entities.editEntity', { type: currentEntityType?.name || 'Entity' })
                : t('entities.createEntity', { type: currentEntityType?.name || 'Entity' })
            }}
          </div>
          <div v-if="entityForm.name" class="text-caption opacity-80">{{ entityForm.name }}</div>
        </div>
      </v-card-title>

      <v-tabs v-model="localEntityTab" class="dialog-tabs">
        <v-tab value="general">
          <v-icon start>mdi-form-textbox</v-icon>
          {{ t('entities.tabs.general') }}
        </v-tab>
        <v-tab
          v-if="currentEntityType?.attribute_schema?.properties && Object.keys(currentEntityType.attribute_schema.properties).length > 0"
          value="attributes"
        >
          <v-icon start>mdi-tag-multiple</v-icon>
          {{ t('entities.tabs.attributes') }}
        </v-tab>
        <v-tab value="location">
          <v-icon start>mdi-map-marker</v-icon>
          {{ t('entities.tabs.location') }}
        </v-tab>
        <v-tab value="assignment">
          <v-icon start>mdi-account-check</v-icon>
          {{ t('entities.tabs.assignment') }}
        </v-tab>
      </v-tabs>

      <v-card-text class="pa-6 dialog-content-sm">
        <v-form ref="formRef" @submit.prevent="handleSubmit">
          <v-window v-model="localEntityTab">
            <!-- General Tab -->
            <v-window-item value="general">
              <v-row>
                <v-col
                  cols="12"
                  :md="flags.entityHierarchyEnabled && currentEntityType?.supports_hierarchy ? 6 : 12"
                >
                  <v-text-field
                    :model-value="entityForm.name"
                    :label="t('common.name') + ' *'"
                    :rules="[v => !!v || t('entities.nameRequired')]"
                    required
                    variant="outlined"
                    prepend-inner-icon="mdi-format-text"
                    @update:model-value="updateEntityForm('name', $event)"
                  ></v-text-field>
                </v-col>
                <v-col
                  cols="12"
                  md="6"
                  v-if="flags.entityHierarchyEnabled && currentEntityType?.supports_hierarchy"
                >
                  <v-select
                    :model-value="entityForm.parent_id"
                    :items="parentOptions"
                    item-title="name"
                    item-value="id"
                    :label="t('entities.parentElement')"
                    clearable
                    variant="outlined"
                    prepend-inner-icon="mdi-family-tree"
                    @update:model-value="updateEntityForm('parent_id', $event)"
                  ></v-select>
                </v-col>
              </v-row>

              <v-text-field
                :model-value="entityForm.external_id"
                :label="t('entities.externalId')"
                :hint="t('entities.externalIdHint')"
                persistent-hint
                variant="outlined"
                prepend-inner-icon="mdi-identifier"
                @update:model-value="updateEntityForm('external_id', $event)"
              ></v-text-field>

              <v-card variant="tonal" color="info" class="mt-4 pa-3">
                <div class="d-flex align-center">
                  <v-icon class="mr-3" color="info">mdi-information</v-icon>
                  <div class="text-body-2">
                    {{ t('entities.createInfo') }}
                  </div>
                </div>
              </v-card>
            </v-window-item>

            <!-- Attributes Tab -->
            <v-window-item value="attributes">
              <v-alert type="info" variant="tonal" class="mb-4">
                {{ t('entities.attributesInfo') }}
              </v-alert>

              <template v-if="currentEntityType?.attribute_schema?.properties">
                <v-row>
                  <v-col
                    v-for="(prop, key) in currentEntityType.attribute_schema.properties"
                    :key="key"
                    cols="12"
                    :md="prop.type === 'boolean' ? 6 : 12"
                  >
                    <v-text-field
                      v-if="prop.type === 'string'"
                      :model-value="entityForm.core_attributes[String(key)]"
                      :label="prop.title || key"
                      :hint="prop.description"
                      persistent-hint
                      variant="outlined"
                      @update:model-value="updateCoreAttribute(String(key), $event)"
                    ></v-text-field>
                    <v-number-input
                      v-else-if="prop.type === 'integer' || prop.type === 'number'"
                      :model-value="entityForm.core_attributes[String(key)]"
                      :label="prop.title || key"
                      :hint="prop.description"
                      persistent-hint
                      variant="outlined"
                      control-variant="stacked"
                      @update:model-value="updateCoreAttribute(String(key), $event)"
                    ></v-number-input>
                    <v-card v-else-if="prop.type === 'boolean'" variant="outlined" class="pa-3">
                      <div class="d-flex align-center justify-space-between">
                        <div>
                          <div class="text-body-2 font-weight-medium">{{ prop.title || key }}</div>
                          <div v-if="prop.description" class="text-caption text-medium-emphasis">
                            {{ prop.description }}
                          </div>
                        </div>
                        <v-switch
                          :model-value="entityForm.core_attributes[String(key)]"
                          color="primary"
                          hide-details
                          @update:model-value="updateCoreAttribute(String(key), $event)"
                        ></v-switch>
                      </div>
                    </v-card>
                  </v-col>
                </v-row>
              </template>

              <v-alert v-else type="warning" variant="tonal">
                {{ t('entities.noAttributesConfigured') }}
              </v-alert>
            </v-window-item>

            <!-- Location Tab -->
            <v-window-item value="location">
              <v-alert type="info" variant="tonal" class="mb-4">
                {{ t('entities.locationInfo') }}
              </v-alert>

              <v-row>
                <v-col cols="12" md="6">
                  <v-number-input
                    :model-value="entityForm.latitude"
                    :label="t('entities.latitude')"
                    :step="0.000001"
                    :min="-90"
                    :max="90"
                    variant="outlined"
                    prepend-inner-icon="mdi-latitude"
                    :hint="t('entities.latitudeHint')"
                    persistent-hint
                    control-variant="stacked"
                    @update:model-value="updateEntityForm('latitude', $event)"
                  ></v-number-input>
                </v-col>
                <v-col cols="12" md="6">
                  <v-number-input
                    :model-value="entityForm.longitude"
                    :label="t('entities.longitude')"
                    :step="0.000001"
                    :min="-180"
                    :max="180"
                    variant="outlined"
                    prepend-inner-icon="mdi-longitude"
                    :hint="t('entities.longitudeHint')"
                    persistent-hint
                    control-variant="stacked"
                    @update:model-value="updateEntityForm('longitude', $event)"
                  ></v-number-input>
                </v-col>
              </v-row>

              <v-card
                v-if="entityForm.latitude && entityForm.longitude"
                variant="tonal"
                color="success"
                class="mt-4"
              >
                <v-card-text class="d-flex align-center">
                  <v-icon color="success" class="mr-3">mdi-map-check</v-icon>
                  <div>
                    <div class="font-weight-medium">{{ t('entities.coordinatesSet') }}</div>
                    <div class="text-caption">{{ entityForm.latitude }}, {{ entityForm.longitude }}</div>
                  </div>
                </v-card-text>
              </v-card>
            </v-window-item>

            <!-- Assignment Tab -->
            <v-window-item value="assignment">
              <v-alert type="info" variant="tonal" class="mb-4">
                {{ t('entities.assignmentInfo') }}
              </v-alert>

              <v-autocomplete
                :model-value="entityForm.owner_id"
                :items="userOptions"
                :loading="loadingUsers"
                item-title="display"
                item-value="id"
                :label="t('entities.responsibleUser')"
                clearable
                :hint="t('entities.responsibleUserHint')"
                persistent-hint
                variant="outlined"
                prepend-inner-icon="mdi-account"
                @update:model-value="updateEntityForm('owner_id', $event)"
              >
                <template v-slot:item="{ props, item }">
                  <v-list-item v-bind="props">
                    <template v-slot:prepend>
                      <v-avatar color="primary" size="32">
                        <span class="text-caption">{{ item.raw.full_name?.charAt(0) || 'U' }}</span>
                      </v-avatar>
                    </template>
                    <template v-slot:subtitle>{{ item.raw.email }}</template>
                  </v-list-item>
                </template>
              </v-autocomplete>

              <v-card v-if="entityForm.owner_id" variant="tonal" color="primary" class="mt-4">
                <v-card-text class="d-flex align-center">
                  <v-avatar color="primary" size="40" class="mr-3">
                    <v-icon color="on-primary">mdi-account-check</v-icon>
                  </v-avatar>
                  <div>
                    <div class="font-weight-medium">{{ t('entities.assignedTo') }}</div>
                    <div class="text-caption">
                      {{ userOptions.find(u => u.id === entityForm.owner_id)?.display }}
                    </div>
                  </div>
                </v-card-text>
              </v-card>
            </v-window-item>
          </v-window>
        </v-form>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions class="pa-4">
        <v-btn variant="tonal" @click="$emit('cancel')">{{ t('common.cancel') }}</v-btn>
        <v-spacer></v-spacer>
        <v-btn color="primary" :loading="saving" @click="handleSubmit">
          <v-icon start>mdi-check</v-icon>
          {{ editingEntity ? t('common.save') : t('common.create') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { EntityForm } from '@/composables/useEntitiesView'

interface Props {
  modelValue: boolean
  entityForm: EntityForm
  entityTab: string
  editingEntity: any
  currentEntityType: any
  flags: any
  parentOptions: any[]
  userOptions: any[]
  loadingUsers: boolean
  saving: boolean
  isLightColor: (color: string | undefined) => boolean
}

interface Emits {
  (e: 'update:model-value', value: boolean): void
  (e: 'update:entity-form', value: EntityForm): void
  (e: 'update:entity-tab', value: string): void
  (e: 'save', formRef: any): void
  (e: 'cancel'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const { t } = useI18n()

const formRef = ref<any>(null)

const localEntityTab = computed({
  get: () => props.entityTab,
  set: (value) => emit('update:entity-tab', value),
})

function updateEntityForm(field: keyof EntityForm, value: any) {
  emit('update:entity-form', { ...props.entityForm, [field]: value })
}

function updateCoreAttribute(key: string, value: any) {
  emit('update:entity-form', {
    ...props.entityForm,
    core_attributes: { ...props.entityForm.core_attributes, [key]: value },
  })
}

function handleSubmit() {
  emit('save', formRef.value)
}
</script>

<style scoped>
.dialog-tabs {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
