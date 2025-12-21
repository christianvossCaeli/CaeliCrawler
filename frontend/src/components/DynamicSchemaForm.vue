<template>
  <div class="dynamic-schema-form">
    <template v-for="(field, key) in schemaProperties" :key="key">
      <!-- String with enum (Select/Dropdown) -->
      <v-select
        v-if="field.type === 'string' && field.enum"
        v-model="formData[key]"
        :items="field.enum"
        :label="getFieldLabel(key, field)"
        :hint="field.description"
        :rules="isRequired(key) ? [v => !!v || t('validation.required')] : []"
        :required="isRequired(key)"
        persistent-hint
        variant="outlined"
        density="comfortable"
        class="mb-3"
        clearable
      ></v-select>

      <!-- String with format email -->
      <v-text-field
        v-else-if="field.type === 'string' && field.format === 'email'"
        v-model="formData[key]"
        :label="getFieldLabel(key, field)"
        :hint="field.description"
        :rules="getEmailRules(key)"
        :required="isRequired(key)"
        type="email"
        persistent-hint
        variant="outlined"
        density="comfortable"
        class="mb-3"
      ></v-text-field>

      <!-- String with format date or date-time -->
      <v-text-field
        v-else-if="field.type === 'string' && (field.format === 'date' || field.format === 'date-time')"
        v-model="formData[key]"
        :label="getFieldLabel(key, field)"
        :hint="field.description"
        :rules="isRequired(key) ? [v => !!v || t('validation.required')] : []"
        :required="isRequired(key)"
        :type="field.format === 'date' ? 'date' : 'datetime-local'"
        persistent-hint
        variant="outlined"
        density="comfortable"
        class="mb-3"
      ></v-text-field>

      <!-- Long text string (description, quote, etc.) -->
      <v-textarea
        v-else-if="field.type === 'string' && isLongTextField(key)"
        v-model="formData[key]"
        :label="getFieldLabel(key, field)"
        :hint="field.description"
        :rules="isRequired(key) ? [v => !!v || t('validation.required')] : []"
        :required="isRequired(key)"
        rows="3"
        auto-grow
        persistent-hint
        variant="outlined"
        density="comfortable"
        class="mb-3"
      ></v-textarea>

      <!-- Regular string -->
      <v-text-field
        v-else-if="field.type === 'string'"
        v-model="formData[key]"
        :label="getFieldLabel(key, field)"
        :hint="field.description"
        :rules="isRequired(key) ? [v => !!v || t('validation.required')] : []"
        :required="isRequired(key)"
        persistent-hint
        variant="outlined"
        density="comfortable"
        class="mb-3"
      ></v-text-field>

      <!-- Integer -->
      <v-text-field
        v-else-if="field.type === 'integer'"
        v-model.number="formData[key]"
        :label="getFieldLabel(key, field)"
        :hint="field.description"
        :rules="getIntegerRules(key)"
        :required="isRequired(key)"
        type="number"
        step="1"
        persistent-hint
        variant="outlined"
        density="comfortable"
        class="mb-3"
      ></v-text-field>

      <!-- Number (float) -->
      <v-text-field
        v-else-if="field.type === 'number'"
        v-model.number="formData[key]"
        :label="getFieldLabel(key, field)"
        :hint="field.description"
        :rules="getNumberRules(key)"
        :required="isRequired(key)"
        type="number"
        step="any"
        persistent-hint
        variant="outlined"
        density="comfortable"
        class="mb-3"
      ></v-text-field>

      <!-- Boolean -->
      <v-checkbox
        v-else-if="field.type === 'boolean'"
        v-model="formData[key]"
        :label="getFieldLabel(key, field)"
        :hint="field.description"
        persistent-hint
        density="comfortable"
        class="mb-3"
      ></v-checkbox>

      <!-- Array of strings -->
      <v-combobox
        v-else-if="field.type === 'array' && field.items?.type === 'string'"
        v-model="formData[key]"
        :label="getFieldLabel(key, field)"
        :hint="field.description || t('dynamicForm.arrayHint')"
        :items="field.items?.enum || []"
        :rules="isRequired(key) ? [v => (v && v.length > 0) || t('validation.required')] : []"
        :required="isRequired(key)"
        multiple
        chips
        closable-chips
        persistent-hint
        variant="outlined"
        density="comfortable"
        class="mb-3"
      ></v-combobox>

      <!-- Fallback for unknown types -->
      <v-text-field
        v-else
        v-model="formData[key]"
        :label="getFieldLabel(key, field)"
        :hint="field.description || t('dynamicForm.unknownType', { type: field.type })"
        persistent-hint
        variant="outlined"
        density="comfortable"
        class="mb-3"
      ></v-text-field>
    </template>

    <!-- Empty state if no schema properties -->
    <v-alert
      v-if="!hasProperties"
      type="info"
      variant="tonal"
      density="compact"
    >
      {{ t('dynamicForm.noSchema') }}
    </v-alert>
  </div>
</template>

<script setup lang="ts">
import { computed, watch, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

// ============================================================================
// Props & Emits
// ============================================================================

interface SchemaProperty {
  type: string
  title?: string
  description?: string
  enum?: string[]
  format?: string
  items?: {
    type: string
    enum?: string[]
  }
  minimum?: number
  maximum?: number
}

interface JsonSchema {
  type?: string
  properties?: Record<string, SchemaProperty>
  required?: string[]
}

const props = defineProps<{
  schema: JsonSchema | null
  modelValue: Record<string, any>
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: Record<string, any>): void
}>()

// ============================================================================
// State
// ============================================================================

const formData = ref<Record<string, any>>({})

// ============================================================================
// Computed
// ============================================================================

const schemaProperties = computed(() => {
  if (!props.schema?.properties) return {}
  return props.schema.properties
})

const hasProperties = computed(() => {
  return Object.keys(schemaProperties.value).length > 0
})

const requiredFields = computed(() => {
  return props.schema?.required || []
})

// ============================================================================
// Methods
// ============================================================================

function getFieldLabel(key: string, field: SchemaProperty): string {
  if (field.title) return field.title
  // Convert snake_case or camelCase to Title Case
  return key
    .replace(/_/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .replace(/^\w/, c => c.toUpperCase())
    .trim()
}

function isRequired(key: string): boolean {
  return requiredFields.value.includes(key)
}

function isLongTextField(key: string): boolean {
  // Fields that typically need multiline input
  const longFields = ['description', 'beschreibung', 'quote', 'zitat', 'statement', 'text', 'notes', 'notizen', 'comment', 'kommentar']
  return longFields.includes(key.toLowerCase())
}

function getEmailRules(key: string) {
  const rules: ((v: any) => boolean | string)[] = []
  if (isRequired(key)) {
    rules.push(v => !!v || t('validation.required'))
  }
  rules.push(v => {
    if (!v) return true
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return emailPattern.test(v) || t('validation.email')
  })
  return rules
}

function getIntegerRules(key: string) {
  const rules: ((v: any) => boolean | string)[] = []
  if (isRequired(key)) {
    rules.push(v => v !== null && v !== undefined && v !== '' || t('validation.required'))
  }
  rules.push(v => {
    if (v === null || v === undefined || v === '') return true
    return Number.isInteger(Number(v)) || t('validation.integer')
  })
  return rules
}

function getNumberRules(key: string) {
  const rules: ((v: any) => boolean | string)[] = []
  if (isRequired(key)) {
    rules.push(v => v !== null && v !== undefined && v !== '' || t('validation.required'))
  }
  rules.push(v => {
    if (v === null || v === undefined || v === '') return true
    return !isNaN(Number(v)) || t('validation.number')
  })
  return rules
}

function initFormData() {
  const data: Record<string, any> = {}
  for (const [key, field] of Object.entries(schemaProperties.value)) {
    // Initialize with existing value or default based on type
    if (props.modelValue && props.modelValue[key] !== undefined) {
      data[key] = props.modelValue[key]
    } else {
      switch (field.type) {
        case 'boolean':
          data[key] = false
          break
        case 'array':
          data[key] = []
          break
        case 'integer':
        case 'number':
          data[key] = null
          break
        default:
          data[key] = ''
      }
    }
  }
  formData.value = data
}

// ============================================================================
// Watchers
// ============================================================================

// Watch for schema changes
watch(() => props.schema, () => {
  initFormData()
}, { immediate: true })

// Watch for external modelValue changes
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    for (const key of Object.keys(schemaProperties.value)) {
      if (newVal[key] !== undefined) {
        formData.value[key] = newVal[key]
      }
    }
  }
}, { deep: true })

// Emit changes
watch(formData, (newVal) => {
  // Filter out empty values for cleaner output
  const cleanedData: Record<string, any> = {}
  for (const [key, value] of Object.entries(newVal)) {
    if (value !== '' && value !== null && value !== undefined) {
      // For arrays, only include if not empty
      if (Array.isArray(value) && value.length === 0) continue
      cleanedData[key] = value
    }
  }
  emit('update:modelValue', cleanedData)
}, { deep: true })
</script>

<style scoped>
.dynamic-schema-form {
  display: flex;
  flex-direction: column;
}
</style>
