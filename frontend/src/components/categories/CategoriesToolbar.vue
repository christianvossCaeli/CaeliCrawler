<template>
  <v-card class="mb-4">
    <v-card-text>
      <v-row align="center">
        <v-col cols="12" md="4">
          <v-text-field
            :model-value="filters.search"
            :label="$t('categories.filters.search')"
            prepend-inner-icon="mdi-magnify"
            clearable
            hide-details
            @update:model-value="updateFilter('search', $event)"
          />
        </v-col>

        <v-col cols="12" md="3">
          <v-select
            :model-value="filters.status"
            :items="statusOptions"
            item-title="label"
            item-value="value"
            :label="$t('categories.filters.status')"
            clearable
            hide-details
            @update:model-value="updateFilter('status', $event)"
          />
        </v-col>

        <v-col cols="12" md="3">
          <v-select
            :model-value="filters.hasDocuments"
            :items="documentOptions"
            item-title="label"
            item-value="value"
            :label="$t('categories.filters.documents')"
            clearable
            hide-details
            @update:model-value="updateFilter('hasDocuments', $event)"
          />
        </v-col>

        <v-col cols="12" md="2">
          <v-select
            :model-value="filters.language"
            :items="languageOptions"
            item-title="name"
            item-value="code"
            :label="$t('categories.filters.language')"
            clearable
            hide-details
            @update:model-value="updateFilter('language', $event)"
          >
            <template #item="{ item, props: itemProps }">
              <v-list-item v-bind="itemProps">
                <template #prepend>
                  <span class="mr-2">{{ item.raw.flag }}</span>
                </template>
              </v-list-item>
            </template>
          </v-select>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import type { CategoryFilters } from '@/composables/useCategoriesView'

export interface CategoriesToolbarProps {
  filters: CategoryFilters
  statusOptions: Array<{ value: string; label: string }>
  documentOptions: Array<{ value: string; label: string }>
  languageOptions: Array<{ code: string; name: string; flag: string }>
}

export interface CategoriesToolbarEmits {
  (e: 'update:filters', filters: CategoryFilters): void
}

const props = defineProps<CategoriesToolbarProps>()
const emit = defineEmits<CategoriesToolbarEmits>()

const updateFilter = (key: keyof CategoryFilters, value: unknown) => {
  emit('update:filters', {
    ...props.filters,
    [key]: value,
  })
}
</script>
