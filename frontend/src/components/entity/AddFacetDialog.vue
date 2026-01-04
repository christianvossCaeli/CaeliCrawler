<template>
  <v-dialog v-model="modelValue" :max-width="DIALOG_SIZES.ML" scrollable>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-plus-circle</v-icon>
        {{ t('entityDetail.dialog.addFacet') }}
      </v-card-title>
      <v-card-text>
        <v-form ref="formRef" @submit.prevent="$emit('save')">
          <!-- Facet Type Selection -->
          <v-select
            :model-value="facetTypeId"
            :items="facetTypes"
            item-title="name"
            item-value="id"
            :label="t('entityDetail.dialog.facetType')"
            :rules="[v => !!v || t('entityDetail.dialog.facetTypeRequired')]"
            variant="outlined"
            density="comfortable"
            class="mb-4"
            @update:model-value="$emit('update:facetTypeId', $event)"
          >
            <template #item="{ item, props: itemProps }">
              <v-list-item v-bind="itemProps">
                <template #prepend>
                  <v-icon :icon="item.raw.icon ?? 'mdi-tag'" :color="item.raw.color ?? undefined" size="small"></v-icon>
                </template>
              </v-list-item>
            </template>
            <template #selection="{ item }">
              <v-icon :icon="item.raw.icon ?? 'mdi-tag'" :color="item.raw.color ?? undefined" size="small" class="mr-2"></v-icon>
              {{ item.raw.name }}
            </template>
          </v-select>

          <!-- Entity Reference Selection (when facet type allows entity reference) -->
          <template v-if="selectedFacetType?.allows_entity_reference && facetTypeId">
            <v-divider class="mb-4"></v-divider>
            <div class="text-subtitle-2 mb-3 text-medium-emphasis-darken-1">
              <v-icon start size="small">mdi-link</v-icon>
              {{ t('entityDetail.dialog.linkToEntity', 'Mit Datensatz verknüpfen') }}
            </div>
            <v-autocomplete
              v-model="selectedEntity"
              :items="entitySearchResults"
              item-title="name"
              item-value="id"
              :label="t('entityDetail.dialog.selectEntity', 'Datensatz auswählen')"
              :placeholder="t('entityDetail.dialog.searchEntity', 'Suchen...')"
              :loading="entitySearchLoading"
              variant="outlined"
              density="comfortable"
              class="mb-3"
              clearable
              return-object
              :no-data-text="t('common.noResults', 'Keine Ergebnisse')"
              @update:search="onEntitySearch"
              @update:model-value="onEntitySelect"
            >
              <template #item="{ item, props: itemProps }">
                <v-list-item v-bind="itemProps">
                  <template #prepend>
                    <v-icon size="small" color="primary">mdi-account</v-icon>
                  </template>
                  <template #subtitle>
                    {{ item.raw.entity_type_name || item.raw.entity_type_slug }}
                  </template>
                </v-list-item>
              </template>
            </v-autocomplete>
            <v-alert v-if="!selectedEntity" type="info" variant="tonal" density="compact" class="mb-3">
              {{ t('entityDetail.dialog.entityLinkHint', 'Wählen Sie einen bestehenden Datensatz aus oder füllen Sie die Felder unten manuell aus.') }}
            </v-alert>
          </template>

          <!-- Dynamic Schema Form (when facet type has a schema) -->
          <template v-if="selectedFacetType?.value_schema">
            <v-divider class="mb-4"></v-divider>
            <div class="text-subtitle-2 mb-3 text-medium-emphasis-darken-1">
              {{ t('entityDetail.dialog.facetDetails') }}
            </div>
            <DynamicSchemaForm
              :model-value="value"
              :schema="selectedFacetType.value_schema"
              @update:model-value="$emit('update:value', $event)"
            />
          </template>

          <!-- Simple text input (when no schema) -->
          <template v-else-if="facetTypeId && !selectedFacetType?.allows_entity_reference">
            <v-textarea
              :model-value="textRepresentation"
              :label="t('entityDetail.dialog.facetValue')"
              :rules="[v => !!v || t('entityDetail.dialog.facetValueRequired')]"
              rows="3"
              variant="outlined"
              density="comfortable"
              class="mb-3"
              @update:model-value="$emit('update:textRepresentation', $event)"
            ></v-textarea>
          </template>

          <v-divider class="my-4"></v-divider>

          <!-- Source URL -->
          <v-text-field
            :model-value="sourceUrl"
            :label="t('entityDetail.dialog.sourceUrl')"
            placeholder="https://..."
            variant="outlined"
            density="comfortable"
            class="mb-3"
            prepend-inner-icon="mdi-link"
            @update:model-value="$emit('update:sourceUrl', $event)"
          ></v-text-field>

          <!-- Confidence Score -->
          <div class="d-flex align-center ga-4">
            <span class="text-body-2">{{ t('entityDetail.dialog.confidence') }}:</span>
            <v-slider
              :model-value="confidenceScore"
              :min="0"
              :max="1"
              :step="0.1"
              thumb-label
              :color="getConfidenceColor(confidenceScore)"
              hide-details
              class="flex-grow-1"
              @update:model-value="$emit('update:confidenceScore', $event)"
            ></v-slider>
            <v-chip size="small" :color="getConfidenceColor(confidenceScore)">
              {{ Math.round(confidenceScore * 100) }}%
            </v-chip>
          </div>
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" @click="$emit('close')">{{ t('common.cancel') }}</v-btn>
        <v-btn
          color="primary"
          :loading="saving"
          :disabled="!canSave"
          @click="$emit('save')"
        >
          <v-icon start>mdi-check</v-icon>
          {{ t('common.save') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { DIALOG_SIZES } from '@/config/ui'
import DynamicSchemaForm from '@/components/DynamicSchemaForm.vue'
import { entityApi } from '@/services/api'

// Types
interface FacetType {
  id: string
  name: string
  icon?: string | null
  color?: string | null
  value_schema?: Record<string, unknown> | null
  allows_entity_reference?: boolean
  target_entity_type_slugs?: string[]
}

interface EntitySearchResult {
  id: string
  name: string
  entity_type_name?: string
  entity_type_slug?: string
}

const modelValue = defineModel<boolean>()

// Props
const props = defineProps<{
  facetTypeId: string
  facetTypes: FacetType[]
  selectedFacetType: FacetType | null
  value: Record<string, unknown>
  textRepresentation: string
  sourceUrl: string
  confidenceScore: number
  saving: boolean
}>()

// Emits
const emit = defineEmits<{
  'update:facetTypeId': [value: string]
  'update:value': [value: Record<string, unknown>]
  'update:textRepresentation': [value: string]
  'update:sourceUrl': [value: string]
  'update:confidenceScore': [value: number]
  'update:targetEntityId': [value: string | null]
  save: []
  close: []
}>()

// Local state for entity search
const entitySearchResults = ref<EntitySearchResult[]>([])
const entitySearchLoading = ref(false)
const selectedEntity = ref<EntitySearchResult | null>(null)

// Reset entity selection when dialog closes or facet type changes
watch(() => props.facetTypeId, () => {
  selectedEntity.value = null
  entitySearchResults.value = []
})

watch(modelValue, (isOpen) => {
  if (!isOpen) {
    selectedEntity.value = null
    entitySearchResults.value = []
  }
})

const { t } = useI18n()

// Form ref for validation
const formRef = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)

// Computed
const canSave = computed(() => {
  if (!props.facetTypeId) return false

  // If entity reference is allowed and selected, that's enough
  if (props.selectedFacetType?.allows_entity_reference && selectedEntity.value) {
    return true
  }

  if (props.selectedFacetType?.value_schema) {
    // Schema form - value should have some content
    return Object.keys(props.value).length > 0
  }
  // Simple text - needs text representation
  return !!props.textRepresentation
})

// Entity search debounce
let searchTimeout: ReturnType<typeof setTimeout> | null = null
async function onEntitySearch(query: string) {
  if (searchTimeout) clearTimeout(searchTimeout)
  if (!query || query.length < 2) {
    entitySearchResults.value = []
    return
  }

  searchTimeout = setTimeout(async () => {
    entitySearchLoading.value = true
    try {
      // Filter by target entity types if specified
      const typeFilter = props.selectedFacetType?.target_entity_type_slugs?.join(',')
      const response = await entityApi.searchEntities({
        q: query,
        per_page: 20,
        entity_type_slug: typeFilter || undefined,
      })
      entitySearchResults.value = (response.data.items || []).map((e: {
        id: string
        name: string
        entity_type_name?: string
        entity_type?: { name?: string; slug?: string }
      }) => ({
        id: e.id,
        name: e.name,
        entity_type_name: e.entity_type_name || e.entity_type?.name || '',
        entity_type_slug: e.entity_type?.slug || '',
      }))
    } catch {
      entitySearchResults.value = []
    } finally {
      entitySearchLoading.value = false
    }
  }, 300)
}

function onEntitySelect(entity: EntitySearchResult | null) {
  selectedEntity.value = entity
  emit('update:targetEntityId', entity?.id || null)

  if (entity) {
    // Always set text_representation to entity name for non-schema facet types
    emit('update:textRepresentation', entity.name)

    // Auto-fill the form when an entity is selected
    if (props.selectedFacetType?.value_schema) {
      // Auto-fill name field if it exists in the schema
      const newValue = { ...props.value }
      const schema = props.selectedFacetType.value_schema as { properties?: Record<string, unknown> }
      if (schema.properties && 'name' in schema.properties) {
        newValue.name = entity.name
      }
      emit('update:value', newValue)
    }
  }
}

// Helpers
function getConfidenceColor(score: number): string {
  if (score >= 0.8) return 'success'
  if (score >= 0.5) return 'warning'
  return 'error'
}

defineExpose({ formRef })
</script>
