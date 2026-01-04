<template>
  <v-dialog :model-value="modelValue" :max-width="DIALOG_SIZES.MD" scrollable @update:model-value="$emit('update:modelValue', $event)">
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-link-plus</v-icon>
        {{ t('entityDetail.facets.linkEntityTitle', 'Facet mit Entity verknüpfen') }}
      </v-card-title>
      <v-card-text>
        <v-alert type="info" variant="tonal" class="mb-4">
          {{ t('entityDetail.facets.linkEntityDescription', 'Suchen Sie nach einer Entity, um dieses Facet zu verknüpfen.') }}
        </v-alert>

        <v-autocomplete
          :model-value="selectedEntityId"
          :search="searchQuery"
          :items="searchResults"
          :loading="searching"
          item-title="name"
          item-value="id"
          :label="t('entityDetail.facets.searchEntity', 'Entity suchen...')"
          prepend-inner-icon="mdi-magnify"
          variant="outlined"
          clearable
          no-filter
          @update:model-value="$emit('update:selectedEntityId', $event)"
          @update:search="$emit('search', $event)"
        >
          <template #item="{ item, props: itemProps }">
            <v-list-item v-bind="itemProps">
              <template #prepend>
                <v-avatar size="32" :color="item.raw.entity_type_color || 'primary'">
                  <v-icon size="small" color="white">{{ item.raw.entity_type_icon || 'mdi-folder' }}</v-icon>
                </v-avatar>
              </template>
              <template #subtitle>
                {{ item.raw.entity_type_name }}
              </template>
            </v-list-item>
          </template>
        </v-autocomplete>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" @click="$emit('update:modelValue', false)">{{ t('common.cancel') }}</v-btn>
        <v-btn
          color="primary"
          variant="tonal"
          :loading="saving"
          :disabled="!selectedEntityId"
          @click="$emit('save')"
        >
          {{ t('common.save') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'
import type { EntitySearchResult } from '@/composables/facets'

defineProps<{
  modelValue: boolean
  selectedEntityId: string | null
  searchQuery: string
  searchResults: EntitySearchResult[]
  searching: boolean
  saving: boolean
}>()

defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'update:selectedEntityId', value: string | null): void
  (e: 'search', query: string): void
  (e: 'save'): void
}>()

const { t } = useI18n()
</script>
