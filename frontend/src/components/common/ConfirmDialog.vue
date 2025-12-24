<template>
  <v-dialog :model-value="modelValue" :max-width="maxWidth" @update:model-value="$emit('update:modelValue', $event)">
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon :color="iconColor" class="mr-2">{{ icon }}</v-icon>
        {{ title }}
      </v-card-title>
      <v-card-text>
        <p>{{ message }}</p>
        <p v-if="subtitle" class="text-caption text-medium-emphasis mt-2">{{ subtitle }}</p>
        <slot name="content"></slot>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="tonal" @click="$emit('update:modelValue', false)">{{ cancelText }}</v-btn>
        <v-btn
          variant="tonal"
          :color="confirmColor"
          :loading="loading"
          @click="$emit('confirm')"
        >
          <v-icon v-if="confirmIcon" start>{{ confirmIcon }}</v-icon>
          {{ confirmText }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  modelValue: boolean
  title: string
  message: string
  subtitle?: string
  icon?: string
  iconColor?: string
  confirmText?: string
  confirmIcon?: string
  confirmColor?: string
  cancelText?: string
  loading?: boolean
  maxWidth?: number | string
}>(), {
  icon: 'mdi-alert',
  iconColor: 'error',
  confirmColor: 'error',
  confirmIcon: '',
  loading: false,
  maxWidth: 400,
})

defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: []
}>()
</script>
