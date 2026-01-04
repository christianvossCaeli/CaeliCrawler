<template>
  <v-card variant="flat" class="mb-4">
    <v-card-title class="text-subtitle-1 d-flex align-center pa-4 pb-2">
      <v-icon size="small" :color="field.color" class="mr-2">{{ field.icon }}</v-icon>
      <span class="text-medium-emphasis">{{ field.label }}</span>
      <v-chip size="x-small" variant="tonal" :color="field.color" class="ml-2">
        {{ field.values.length }}
      </v-chip>
    </v-card-title>

    <v-card-text class="pt-0">
      <!-- Chip-based display (for entity references, contacts) -->
      <template v-if="field.displayType === 'chips'">
        <div class="d-flex flex-wrap ga-2">
          <v-chip
            v-for="(val, idx) in field.values"
            :key="idx"
            variant="tonal"
            :color="field.color"
            size="small"
          >
            <v-avatar start :color="field.color" size="20">
              <v-icon size="x-small">mdi-account</v-icon>
            </v-avatar>
            {{ getValueText(val) }}
          </v-chip>
        </div>
      </template>

      <!-- List-based display (default) -->
      <template v-else>
        <div class="d-flex flex-column">
          <div
            v-for="(val, idx) in field.values"
            :key="idx"
            class="field-item d-flex align-start px-3 py-3"
          >
            <div
              class="field-indicator mr-3"
              :style="{ backgroundColor: `rgb(var(--v-theme-${field.color}))` }"
            />
            <div class="flex-grow-1">
              <div class="text-body-2">{{ getValueText(val) }}</div>
              <!-- Additional chips for structured data -->
              <div v-if="isObject(val)" class="d-flex flex-wrap ga-1 mt-2">
                <template
                  v-for="(propVal, propKey) in (val as Record<string, unknown>)"
                  :key="propKey"
                >
                  <v-chip
                    v-if="shouldShowProperty(propKey, propVal)"
                    size="x-small"
                    variant="tonal"
                    color="grey"
                  >
                    {{ propKey }}: {{ propVal }}
                  </v-chip>
                </template>
              </div>
            </div>
          </div>
        </div>
      </template>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
/**
 * DynamicContentCard - Renders dynamic content fields
 *
 * Supports both chip-based display (for contacts, decision makers)
 * and list-based display (for other fields).
 */
import { useResultsHelpers, type DynamicContentField } from '@/composables/results'

defineProps<{
  field: DynamicContentField
}>()

const { getValueText } = useResultsHelpers()

/**
 * Check if value is an object.
 */
function isObject(val: unknown): val is Record<string, unknown> {
  return typeof val === 'object' && val !== null
}

/**
 * Determine if a property should be shown as a chip.
 */
function shouldShowProperty(key: string, value: unknown): boolean {
  // Skip common text fields and nullish values
  const skipKeys = ['description', 'text', 'aenderungen']
  if (skipKeys.includes(key)) return false
  if (value === null || value === undefined) return false
  if (typeof value === 'object') return false
  return true
}
</script>

<style scoped>
.field-item {
  background: rgba(var(--v-theme-on-surface), 0.04);
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 8px;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.field-item:hover {
  background: rgba(var(--v-theme-on-surface), 0.08);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.field-item:not(:last-child) {
  margin-bottom: 8px;
}

.field-indicator {
  width: 4px;
  height: 100%;
  min-height: 24px;
  border-radius: 2px;
  flex-shrink: 0;
}
</style>
