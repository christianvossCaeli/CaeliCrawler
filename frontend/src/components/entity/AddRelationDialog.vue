<template>
  <v-dialog v-model="modelValue" :max-width="DIALOG_SIZES.MD" scrollable>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start>{{ editing ? 'mdi-pencil' : 'mdi-link-plus' }}</v-icon>
        {{ editing ? t('entityDetail.dialog.editRelation') : t('entityDetail.dialog.addRelation') }}
      </v-card-title>
      <v-card-text>
        <v-form ref="formRef" @submit.prevent="$emit('save')">
          <!-- Relation Type Selection -->
          <v-select
            :model-value="relationTypeId"
            :items="relationTypes"
            item-title="name"
            item-value="id"
            :label="t('entityDetail.dialog.relationType')"
            :rules="[v => !!v || t('common.required')]"
            variant="outlined"
            density="comfortable"
            class="mb-3"
            :loading="loadingRelationTypes"
            @update:model-value="$emit('update:relationTypeId', $event)"
          >
            <template #item="{ item, props }">
              <v-list-item v-bind="props">
                <template #prepend>
                  <v-icon :color="item.raw.color || 'primary'">mdi-link-variant</v-icon>
                </template>
                <v-list-item-subtitle v-if="item.raw.description">
                  {{ item.raw.description }}
                </v-list-item-subtitle>
              </v-list-item>
            </template>
          </v-select>

          <!-- Direction Selection -->
          <v-radio-group
            :model-value="direction"
            :label="t('entityDetail.dialog.relationDirection')"
            inline
            class="mb-3"
            @update:model-value="$emit('update:direction', $event as 'outgoing' | 'incoming')"
          >
            <v-radio :label="t('entityDetail.dialog.outgoing')" value="outgoing"></v-radio>
            <v-radio :label="t('entityDetail.dialog.incoming')" value="incoming"></v-radio>
          </v-radio-group>

          <!-- Target Entity Selection -->
          <v-autocomplete
            :model-value="targetEntityId"
            :items="targetEntities"
            item-title="name"
            item-value="id"
            :label="t('entityDetail.dialog.targetEntity')"
            :rules="[v => !!v || t('common.required')]"
            variant="outlined"
            density="comfortable"
            :loading="searchingEntities"
            no-filter
            class="mb-3"
            @update:model-value="$emit('update:targetEntityId', $event)"
            @update:search="$emit('search', $event)"
          >
            <template #item="{ item, props }">
              <v-list-item v-bind="props">
                <template #prepend>
                  <v-icon color="grey">mdi-domain</v-icon>
                </template>
                <v-list-item-subtitle>
                  {{ item.raw.entity_type_name }}
                </v-list-item-subtitle>
              </v-list-item>
            </template>
            <template #no-data>
              <v-list-item>
                <v-list-item-title>
                  {{ searchQuery?.length >= 2 ? t('entityDetail.dialog.noEntitiesFound') : t('entityDetail.dialog.typeToSearch') }}
                </v-list-item-title>
              </v-list-item>
            </template>
          </v-autocomplete>

          <!-- Optional Attributes (JSON) -->
          <v-textarea
            :model-value="attributesJson"
            :label="t('entityDetail.dialog.relationAttributes')"
            :hint="t('entityDetail.dialog.relationAttributesHint')"
            persistent-hint
            variant="outlined"
            rows="2"
            class="mb-3"
            @update:model-value="$emit('update:attributesJson', $event)"
          ></v-textarea>
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" @click="$emit('close')">{{ t('common.cancel') }}</v-btn>
        <v-btn variant="tonal" color="primary" :loading="saving" @click="$emit('save')">
          {{ t('common.save') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'

// Types
interface RelationType {
  id: string
  name: string
  color?: string | null
  description?: string | null
}

interface TargetEntity {
  id: string
  name: string
  entity_type_name?: string
}

const modelValue = defineModel<boolean>()

// Props
defineProps<{
  editing: boolean
  relationTypeId: string
  direction: 'outgoing' | 'incoming'
  targetEntityId: string
  attributesJson: string
  relationTypes: RelationType[]
  targetEntities: TargetEntity[]
  loadingRelationTypes: boolean
  searchingEntities: boolean
  searchQuery: string
  saving: boolean
}>()

// Emits
defineEmits<{
  'update:relationTypeId': [value: string]
  'update:direction': [value: 'outgoing' | 'incoming']
  'update:targetEntityId': [value: string]
  'update:attributesJson': [value: string]
  save: []
  close: []
  search: [query: string]
}>()

const { t } = useI18n()

// Expose form ref for validation
const formRef = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)

defineExpose({ formRef })
</script>
