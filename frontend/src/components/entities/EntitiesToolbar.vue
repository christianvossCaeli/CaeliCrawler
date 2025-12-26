<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      {{ currentEntityType?.name_plural || t('entities.title') }} - {{ t('entities.overview') }}
      <v-spacer></v-spacer>
      <v-btn-toggle v-model="localViewMode" density="compact" mandatory>
        <v-btn value="table" icon="mdi-table" :aria-label="t('entities.viewModes.table')"></v-btn>
        <v-btn value="cards" icon="mdi-view-grid" :aria-label="t('entities.viewModes.cards')"></v-btn>
        <v-btn
          v-if="hasGeoData"
          value="map"
          icon="mdi-map"
          :aria-label="t('entities.viewModes.map')"
        ></v-btn>
      </v-btn-toggle>
      <v-btn color="primary" variant="tonal" class="ml-2" @click="$emit('refresh')">
        <v-icon start>mdi-refresh</v-icon>
        {{ t('common.refresh') }}
      </v-btn>
    </v-card-title>

    <slot></slot>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

interface Props {
  viewMode: 'table' | 'cards' | 'map'
  currentEntityType: { slug?: string; name?: string; name_plural?: string; icon?: string; color?: string } | null
  hasGeoData: boolean
}

interface Emits {
  (e: 'update:view-mode', value: 'table' | 'cards' | 'map'): void
  (e: 'refresh'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const { t } = useI18n()

const localViewMode = computed({
  get: () => props.viewMode,
  set: (value) => emit('update:view-mode', value),
})
</script>
