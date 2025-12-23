<template>
  <div v-if="validations.length > 0">
    <v-card
      v-for="(validation, index) in validations"
      :key="index"
      variant="outlined"
      class="mb-3"
      :color="validation.is_valid ? 'success' : 'error'"
    >
      <v-card-title class="d-flex align-center text-body-1">
        <v-icon :color="validation.is_valid ? 'success' : 'error'" class="mr-2">
          {{ validation.is_valid ? 'mdi-check-circle' : 'mdi-close-circle' }}
        </v-icon>
        {{ validation.api_name }}
        <v-spacer />
        <v-chip
          :color="validation.is_valid ? 'success' : 'error'"
          size="small"
          variant="outlined"
        >
          {{ validation.is_valid ? $t('sources.aiDiscovery.valid') : $t('sources.aiDiscovery.invalid') }}
        </v-chip>
      </v-card-title>
      <v-card-text class="text-body-2">
        <div v-if="validation.status_code" class="mb-1">
          <strong>Status:</strong> {{ validation.status_code }}
        </div>
        <div v-if="validation.item_count" class="mb-1">
          <strong>{{ $t('sources.aiDiscovery.itemCount') }}:</strong> {{ validation.item_count }}
        </div>
        <div v-if="validation.error_message" class="text-error">
          <strong>{{ $t('common.error') }}:</strong> {{ validation.error_message }}
        </div>
      </v-card-text>
    </v-card>
  </div>
  <v-alert v-else type="info" variant="tonal">
    {{ $t('sources.aiDiscovery.noSuggestions') }}
  </v-alert>
</template>

<script setup lang="ts">
/**
 * AiDiscoveryValidations - Display API validation results
 *
 * Shows validation status for each discovered API with status codes and error messages.
 */
import type { APIValidation } from './types'

interface Props {
  validations: APIValidation[]
}

defineProps<Props>()
</script>
