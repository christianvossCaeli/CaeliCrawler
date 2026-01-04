<template>
  <v-slide-y-transition>
    <div v-if="show" class="mt-3 pa-3 rounded bg-primary-lighten-5">
      <div class="d-flex align-center ga-2">
        <span class="text-body-2">{{ t('entityDetail.selected', { count: selectedCount }) }}</span>
        <v-spacer></v-spacer>
        <v-btn
          size="small"
          color="success"
          variant="tonal"
          :loading="loading"
          @click="$emit('verify')"
        >
          <v-icon start>mdi-check-all</v-icon>
          {{ t('entityDetail.verifyAll') }}
        </v-btn>
        <v-btn
          size="small"
          color="error"
          variant="tonal"
          :loading="loading"
          @click="$emit('delete')"
        >
          <v-icon start>mdi-delete</v-icon>
          {{ t('common.delete') }}
        </v-btn>
      </div>
    </div>
  </v-slide-y-transition>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  bulkMode: boolean
  selectedCount: number
  loading?: boolean
}>()

defineEmits<{
  (e: 'verify'): void
  (e: 'delete'): void
}>()

const { t } = useI18n()

const show = computed(() => props.bulkMode && props.selectedCount > 0)
</script>

<style scoped>
.bg-primary-lighten-5 {
  background-color: rgba(var(--v-theme-primary), 0.1);
}
</style>
