<template>
  <v-navigation-drawer
    :model-value="modelValue"
    location="right"
    temporary
    width="360"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <SmartQueryHistoryPanel
      @close="$emit('update:modelValue', false)"
      @rerun="(commandText, interpretation) => $emit('rerun', commandText, interpretation)"
    />
  </v-navigation-drawer>
</template>

<script setup lang="ts">
import SmartQueryHistoryPanel from '@/components/smartquery/SmartQueryHistoryPanel.vue'

interface Props {
  modelValue: boolean
}

defineProps<Props>()

defineEmits<{
  'update:modelValue': [value: boolean]
  'rerun': [commandText: string, interpretation: Record<string, any>]
}>()
</script>

<style scoped>
/* No additional styles needed - uses Vuetify navigation drawer styles */
</style>
