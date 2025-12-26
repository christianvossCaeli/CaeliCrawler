<template>
  <div class="source-form-basic-info">
    <!-- Name & Source Type -->
    <v-row>
      <v-col cols="12" md="8">
        <v-text-field
          :model-value="name"
          :label="$t('sources.form.name')"
          :rules="nameRules"
          required
          variant="outlined"
          prepend-inner-icon="mdi-database"
          @update:model-value="emitName($event)"
        />
      </v-col>
      <v-col cols="12" md="4">
        <v-select
          :model-value="sourceType"
          :items="sourceTypeOptions"
          item-title="label"
          item-value="value"
          :label="$t('sources.form.sourceType')"
          :rules="[v => !!v || $t('sources.validation.sourceTypeRequired')]"
          required
          variant="outlined"
          @update:model-value="emitSourceType($event)"
        >
          <template #item="{ item, props }">
            <v-list-item v-bind="props">
              <template #prepend>
                <v-icon :color="getTypeColor(item.raw.value)">{{ item.raw.icon }}</v-icon>
              </template>
            </v-list-item>
          </template>
        </v-select>
      </v-col>
    </v-row>

    <!-- Base URL (not for SharePoint) -->
    <v-text-field
      v-if="sourceType !== 'SHAREPOINT'"
      :model-value="baseUrl"
      :label="$t('sources.form.baseUrl')"
      :rules="urlRules"
      required
      variant="outlined"
      :hint="$t('sources.form.baseUrlHint')"
      persistent-hint
      prepend-inner-icon="mdi-link"
      @update:model-value="emitBaseUrl($event)"
    />

    <!-- API Endpoint (for API types) -->
    <v-text-field
      v-if="sourceType === 'OPARL_API' || sourceType === 'CUSTOM_API'"
      :model-value="apiEndpoint"
      :label="$t('sources.form.apiEndpoint')"
      variant="outlined"
      prepend-inner-icon="mdi-api"
      class="mt-3"
      @update:model-value="emitApiEndpoint($event)"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * SourceFormBasicInfo - Basic source information fields
 *
 * Handles name, source type, base URL, and API endpoint inputs.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSourceHelpers } from '@/composables/useSourceHelpers'
import type { SourceTypeOption, SourceType } from '@/types/sources'

interface Props {
  name: string
  sourceType: SourceType | ''
  baseUrl: string
  apiEndpoint: string
}

defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:name', value: string): void
  (e: 'update:sourceType', value: SourceType | '' | null): void
  (e: 'update:baseUrl', value: string): void
  (e: 'update:apiEndpoint', value: string): void
}>()

// Emit wrappers for type safety in templates
const emitName = (value: string) => emit('update:name', value)
const emitSourceType = (value: SourceType | '' | null) => emit('update:sourceType', value)
const emitBaseUrl = (value: string) => emit('update:baseUrl', value)
const emitApiEndpoint = (value: string) => emit('update:apiEndpoint', value)

const { t } = useI18n()
const { getTypeColor, isValidUrl } = useSourceHelpers()

/** Source type options */
const sourceTypeOptions: SourceTypeOption[] = [
  { value: 'WEBSITE', label: 'Website', icon: 'mdi-web' },
  { value: 'OPARL_API', label: 'OParl API', icon: 'mdi-api' },
  { value: 'RSS', label: 'RSS Feed', icon: 'mdi-rss' },
  { value: 'CUSTOM_API', label: 'Custom API', icon: 'mdi-code-json' },
  { value: 'SHAREPOINT', label: 'SharePoint', icon: 'mdi-microsoft-sharepoint' },
]

/** Name validation rules */
const nameRules = computed(() => [
  (v: string) => !!v || t('sources.validation.nameRequired'),
  (v: string) => (v && v.length >= 2) || t('sources.validation.nameTooShort'),
  (v: string) => (v && v.length <= 200) || t('sources.validation.nameTooLong'),
])

/** URL validation rules */
const urlRules = computed(() => [
  (v: string) => !!v || t('sources.validation.urlRequired'),
  (v: string) => isValidUrl(v) || t('sources.validation.urlInvalid'),
])
</script>
